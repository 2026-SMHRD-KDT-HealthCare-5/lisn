"""선제 접촉 조건 — MLCM_220.

`maybe_outreach` 는 **보내지 않기로 한 것도 기록**한다. 조건을 하나씩
고정해두지 않으면 나중에 한 줄 고칠 때 조용히 사라진다.

LLM 은 호출하지 않는다. 발화 생성은 `llm.outreach_opener` 를 갈아끼워
막는다 — 조건 판정을 재는 테스트이지 문장 품질을 재는 테스트가 아니다.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import ChatSession, OutreachLog, User
from app.services import llm, outreach

BASE = "http://test/api/v1"


def _result(**over) -> dict:
    r = {
        "emotion_code": "SADNESS",
        "emotion_score": 60.0,
        "risk_level": "CAUTION",
        "risk_score": 55.0,
        "model_version": "rule-baseline-v1",
        "streak_days": 5,
        "deviant_features": ["수면효율", "입면지연"],
    }
    r.update(over)
    return r


@pytest.fixture(autouse=True)
def _no_llm(monkeypatch):
    """발화 생성을 고정한다. 실제 호출하면 테스트가 API 키에 묶인다."""
    async def fake(persona_type, deviant_features, streak_days):
        return f"[{persona_type}] 요즘 어떠셨어요"
    monkeypatch.setattr(llm, "outreach_opener", fake)


async def _run(user_id, result):
    async with AsyncSessionLocal() as db:
        row = await outreach.maybe_outreach(db, user_id, result)
        await db.commit()
        return row


async def _uid(client, user) -> uuid.UUID:
    r = await client.get(f"{BASE}/users/me", headers=user["headers"])
    assert r.status_code == 200, r.text
    return uuid.UUID(r.json()["user_id"])


@pytest.mark.asyncio
async def test_연속_이탈이_짧으면_기록도_안_남긴다(client, user):
    """매 판정마다 SKIPPED 를 쌓으면 로그가 쓸모없어진다."""
    uid = await _uid(client, user)
    assert await _run(uid, _result(streak_days=2)) is None

    async with AsyncSessionLocal() as db:
        rows = (await db.scalars(
            select(OutreachLog).where(OutreachLog.user_id == uid))).all()
    assert rows == []


@pytest.mark.asyncio
async def test_조건을_넘기면_세션을_선생성한다(client, user):
    uid = await _uid(client, user)
    row = await _run(uid, _result())

    assert row is not None
    assert row.session_id is not None
    assert row.streak_days == 5
    assert row.deviant_features == ["수면효율", "입면지연"]

    async with AsyncSessionLocal() as db:
        s = await db.get(ChatSession, row.session_id)
        assert s is not None
        # 사용자가 열면 이미 첫 마디가 있어야 한다.
        assert len(s.messages) == 1
        assert s.messages[0]["role"] == "assistant"
        assert s.messages[0]["content"]


@pytest.mark.asyncio
async def test_FCM_이_없으므로_발송은_실패로_남는다(client, user):
    """`SENT` 로 적으면 보내지도 않고 보냈다고 기록하는 것이다."""
    uid = await _uid(client, user)
    row = await _run(uid, _result())
    assert row.delivery_status == "FAILED"
    assert row.skip_reason == "fcm_미구현"


@pytest.mark.asyncio
async def test_CRITICAL_이면_보내지_않는다(client, user):
    """긴급 상담 연결(MLCM_510)이 이미 개입한 상태다."""
    uid = await _uid(client, user)
    row = await _run(uid, _result(risk_level="CRITICAL"))
    assert row.delivery_status == "SKIPPED"
    assert row.skip_reason == "risk_critical"
    assert row.session_id is None


@pytest.mark.asyncio
async def test_케어_알림을_끄면_보내지_않는다(client, user):
    """콘텐츠 알림과 따로 둔 이유가 여기서 지켜져야 한다."""
    uid = await _uid(client, user)
    async with AsyncSessionLocal() as db:
        u = await db.get(User, uid)
        u.care_alert_agreed = False
        await db.commit()

    row = await _run(uid, _result())
    assert row.delivery_status == "SKIPPED"
    assert row.skip_reason == "케어알림_미동의"


@pytest.mark.asyncio
async def test_쿨다운_중이면_보내지_않는다(client, user):
    """이탈이 지속되는 동안 매일 보내면 앱을 닫는다."""
    uid = await _uid(client, user)
    first = await _run(uid, _result())
    assert first.delivery_status == "FAILED"  # 첫 접촉은 나갔다

    second = await _run(uid, _result())
    assert second.delivery_status == "SKIPPED"
    assert second.skip_reason == "쿨다운_중"
    assert second.session_id is None


@pytest.mark.asyncio
async def test_쿨다운이_지나면_다시_보낸다(client, user):
    uid = await _uid(client, user)
    row = await _run(uid, _result())

    async with AsyncSessionLocal() as db:
        r = await db.get(OutreachLog, row.outreach_id)
        r.sent_at = datetime.now(timezone.utc) - timedelta(
            days=outreach.COOLDOWN_DAYS + 1
        )
        await db.commit()

    again = await _run(uid, _result())
    assert again.delivery_status == "FAILED"
    assert again.session_id is not None


@pytest.mark.asyncio
async def test_발화_생성이_실패해도_접촉을_취소하지_않는다(client, user, monkeypatch):
    """말을 걸기로 판정된 사람에게 아무 말도 안 하는 것보다 낫다."""
    uid = await _uid(client, user)

    async def boom(*a, **k):
        raise RuntimeError("LLM 죽음")
    monkeypatch.setattr(llm, "outreach_opener", boom)

    row = await _run(uid, _result())
    assert row.session_id is not None

    async with AsyncSessionLocal() as db:
        s = await db.get(ChatSession, row.session_id)
    assert s.messages[0]["content"] in llm.FALLBACK_OUTREACH.values()


@pytest.mark.asyncio
async def test_앱이_선제_접촉_세션을_발견할_수_있다(client, user):
    """서버가 만들어도 앱이 못 보면 의미가 없다 — MLCM_220 6단계.

    앱의 sessionId 는 앱 안에서 대화를 시작했을 때만 채워진다. 이 경로가
    없으면 선제 접촉이 대화 기록 안에 묻힌다.
    """
    uid = await _uid(client, user)
    row = await _run(uid, _result())

    r = await client.get(f"{BASE}/chat/sessions/active", headers=user["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["session_id"] == str(row.session_id)
    assert body["origin"] == "OUTREACH"        # 사용자가 시작한 것과 구분된다
    assert body["messages"][0]["role"] == "assistant"


@pytest.mark.asyncio
async def test_열린_대화가_없으면_204(client, user):
    """본문 없는 200 을 주면 클라이언트가 빈 객체와 구분하려고 분기를 만든다."""
    r = await client.get(f"{BASE}/chat/sessions/active", headers=user["headers"])
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_사용자가_연_대화는_origin_이_USER(client, user):
    r = await client.post(
        f"{BASE}/chat/sessions", json={"persona_type": "FRIEND"},
        headers=user["headers"],
    )
    assert r.status_code == 201, r.text

    r = await client.get(f"{BASE}/chat/sessions/active", headers=user["headers"])
    assert r.status_code == 200
    assert r.json()["origin"] == "USER"


@pytest.mark.asyncio
async def test_홈에_답하지_않은_선제_접촉이_실린다(client, user):
    uid = await _uid(client, user)
    row = await _run(uid, _result())

    r = await client.get(f"{BASE}/home", headers=user["headers"])
    assert r.status_code == 200, r.text
    p = r.json()["pending_outreach"]
    assert p is not None
    assert p["session_id"] == str(row.session_id)
    assert p["opener"]


@pytest.mark.asyncio
async def test_답을_하면_홈에서_내려간다(client, user):
    """대화를 이어가는 중인데 계속 떠 있으면 안 읽은 알림처럼 보인다."""
    uid = await _uid(client, user)
    row = await _run(uid, _result())

    r = await client.post(
        f"{BASE}/chat/sessions/{row.session_id}/messages",
        json={"content": "네 요즘 좀 그랬어요"},
        headers=user["headers"],
    )
    assert r.status_code == 200, r.text

    r = await client.get(f"{BASE}/home", headers=user["headers"])
    assert r.json()["pending_outreach"] is None
