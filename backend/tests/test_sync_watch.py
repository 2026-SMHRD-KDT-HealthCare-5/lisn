"""라이프로그 미수신 감지 — NFR-DV-002 (구현_갭 갭3).

상태 기계를 단계별로 고정한다.

    OK ──(3시간 미갱신)──> NUDGED ──(유예 뒤에도 미갱신)──> RETRY_FAILED
     ^                        │                                  │
     └──────────(데이터가 들어오면 어느 상태에서든 OK)─────────────┘

⚠ **시각을 주입한다.** `scan(db, now=...)` 로 기준 시각을 넘긴다. 벽시계를
  그대로 쓰면 특정 시간대에만 깨지는 테스트가 된다 — 선제 접촉 테스트가
  실제로 그렇게 깨진 적이 있다(학습자료 사례 20).

FCM 은 부르지 않는다. `push.send_silent` 를 갈아끼워 막는다 — 상태 전이를
재는 테스트이지 발송을 재는 테스트가 아니다.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.core.database import AsyncSessionLocal
from app.models import DeviceHealthConnection
from app.services import push, sync_watch

BASE = "http://test/api/v1"
NOW = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _no_push(monkeypatch):
    """무음 푸시를 막는다. 발송된 것만 세어 둔다."""
    sent = []

    async def fake(token, data):
        sent.append((token, data))
        return "fake-message-id"

    monkeypatch.setattr(push, "send_silent", fake)
    monkeypatch.setattr(sync_watch.push, "send_silent", fake)
    return sent


async def _uid(client, user) -> uuid.UUID:
    r = await client.get(f"{BASE}/users/me", headers=user["headers"])
    assert r.status_code == 200, r.text
    return uuid.UUID(r.json()["user_id"])


async def _make_conn(user_id, *, synced_ago_hours, status="OK", nudged_ago_hours=None):
    """연동 한 건을 만든다. `synced_ago_hours=None` 이면 한 번도 안 들어온 것."""
    async with AsyncSessionLocal() as db:
        conn = DeviceHealthConnection(
            user_id=user_id,
            device_name="테스트 기기",
            platform_type="HEALTH_CONNECT",
            permission_granted=True,
            agreed_at=NOW - timedelta(days=30),
            last_synced_at=(
                None if synced_ago_hours is None
                else NOW - timedelta(hours=synced_ago_hours)
            ),
            consent_scopes={"activity": True, "sleep": True, "body_composition": False},
            sync_status=status,
            nudged_at=(
                None if nudged_ago_hours is None
                else NOW - timedelta(hours=nudged_ago_hours)
            ),
        )
        db.add(conn)
        await db.commit()
        return conn.connection_id


async def _give_token(user_id, token="test-fcm-token"):
    """FCM 토큰을 심는다. 무음 푸시가 나가려면 토큰이 있어야 한다."""
    from app.models import User as UserModel
    async with AsyncSessionLocal() as db:
        u = await db.get(UserModel, user_id)
        u.fcm_token = token
        await db.commit()


async def _status(connection_id) -> str:
    async with AsyncSessionLocal() as db:
        conn = await db.get(DeviceHealthConnection, connection_id)
        return conn.sync_status


@pytest.mark.asyncio
async def test_정상_동기화는_건드리지_않는다(client, user):
    """3시간 안에 들어오고 있으면 아무 일도 없어야 한다."""
    uid = await _uid(client, user)
    cid = await _make_conn(uid, synced_ago_hours=1)

    async with AsyncSessionLocal() as db:
        counts = await sync_watch.scan(db, now=NOW)

    assert counts["nudged"] == 0
    assert await _status(cid) == "OK"


@pytest.mark.asyncio
async def test_3시간_넘으면_무음_푸시를_보낸다(client, user, _no_push):
    """① 감지 → ② 무음 푸시. NFR-DV-002 가 명시한 3시간이다."""
    uid = await _uid(client, user)
    await _give_token(uid)
    cid = await _make_conn(uid, synced_ago_hours=4)

    async with AsyncSessionLocal() as db:
        counts = await sync_watch.scan(db, now=NOW)

    assert counts["nudged"] == 1
    assert await _status(cid) == "NUDGED"
    assert len(_no_push) == 1
    assert _no_push[0][1]["type"] == "sync_nudge"


@pytest.mark.asyncio
async def test_경계값_3시간_직전에는_보내지_않는다(client, user):
    """2시간 59분은 아직 미수신이 아니다. 경계에서 새는지 본다."""
    uid = await _uid(client, user)
    cid = await _make_conn(uid, synced_ago_hours=2.9)

    async with AsyncSessionLocal() as db:
        await sync_watch.scan(db, now=NOW)

    assert await _status(cid) == "OK"


@pytest.mark.asyncio
async def test_푸시_후에도_안_들어오면_재시도_실패로_표시한다(client, user):
    """③ 재시도 실패 → ④ 관리자 알림 대상이 된다."""
    uid = await _uid(client, user)
    cid = await _make_conn(
        uid, synced_ago_hours=10, status="NUDGED", nudged_ago_hours=2
    )

    async with AsyncSessionLocal() as db:
        counts = await sync_watch.scan(db, now=NOW)

    assert counts["retry_failed"] == 1
    assert await _status(cid) == "RETRY_FAILED"


@pytest.mark.asyncio
async def test_유예_안에는_재시도_실패로_몰지_않는다(client, user):
    """방금 푸시를 보냈으면 기다린다. 한 주기 걸렀다고 실패는 아니다."""
    uid = await _uid(client, user)
    cid = await _make_conn(
        uid, synced_ago_hours=5, status="NUDGED", nudged_ago_hours=0.2
    )

    async with AsyncSessionLocal() as db:
        await sync_watch.scan(db, now=NOW)

    assert await _status(cid) == "NUDGED"


@pytest.mark.asyncio
async def test_데이터가_들어오면_OK_로_되돌린다(client, user):
    """RETRY_FAILED 에서도 회복된다. 한 번 실패했다고 영영 남으면 안 된다."""
    uid = await _uid(client, user)
    cid = await _make_conn(
        uid, synced_ago_hours=0.5, status="RETRY_FAILED", nudged_ago_hours=5
    )

    async with AsyncSessionLocal() as db:
        counts = await sync_watch.scan(db, now=NOW)

    assert counts["recovered"] == 1
    assert await _status(cid) == "OK"


@pytest.mark.asyncio
async def test_권한이_없으면_대상이_아니다(client, user):
    """연동을 안 한 사람에게 동기화를 재촉할 수 없다."""
    uid = await _uid(client, user)
    async with AsyncSessionLocal() as db:
        conn = DeviceHealthConnection(
            user_id=uid,
            platform_type="HEALTH_CONNECT",
            permission_granted=False,
            agreed_at=NOW - timedelta(days=30),
            last_synced_at=NOW - timedelta(hours=99),
            consent_scopes={"activity": True, "sleep": True, "body_composition": False},
        )
        db.add(conn)
        await db.commit()
        cid = conn.connection_id

    async with AsyncSessionLocal() as db:
        counts = await sync_watch.scan(db, now=NOW)

    assert counts["nudged"] == 0
    assert await _status(cid) == "OK"


@pytest.mark.asyncio
async def test_토큰이_없어도_상태는_넘어간다(client, user, _no_push):
    """⚠ FCM 토큰이 없다는 것 자체가 「앱이 안 돌고 있다」는 신호다.

    여기서 OK 로 남겨두면 영영 재시도 실패까지 못 가서, 정작 문제가 있는
    사용자가 관리자 목록에 안 뜬다.
    """
    uid = await _uid(client, user)
    cid = await _make_conn(uid, synced_ago_hours=6)
    #  user 픽스처는 fcm_token 을 넣지 않는다 — 그대로가 이 테스트의 조건이다.

    async with AsyncSessionLocal() as db:
        await sync_watch.scan(db, now=NOW)

    assert await _status(cid) == "NUDGED"
    assert _no_push == []  # 토큰이 없으니 보내지 않았다


@pytest.mark.asyncio
async def test_관리자_목록에_재시도_실패만_나온다(client, user, admin):
    """NFR-DV-002 ④ — 관리자가 실제로 볼 수 있어야 알림이다."""
    uid = await _uid(client, user)
    await _make_conn(uid, synced_ago_hours=10, status="NUDGED", nudged_ago_hours=2)

    async with AsyncSessionLocal() as db:
        await sync_watch.scan(db, now=NOW)

    r = await client.get(f"{BASE}/admin/sync-failures", headers=admin["headers"])
    assert r.status_code == 200, r.text
    rows = r.json()
    assert any(row["user_id"] == str(uid) for row in rows)


@pytest.mark.asyncio
async def test_일반_사용자는_미수신_목록을_못_본다(client, user):
    """관제 정보다. 남의 동기화 상태가 보이면 안 된다."""
    r = await client.get(f"{BASE}/admin/sync-failures", headers=user["headers"])
    assert r.status_code == 403
