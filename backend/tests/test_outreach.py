"""선제 접촉 조건 — MLCM_220.

`maybe_outreach` 는 **보내지 않기로 한 것도 기록**한다. 조건을 하나씩
고정해두지 않으면 나중에 한 줄 고칠 때 조용히 사라진다.

LLM 은 호출하지 않는다. 발화 생성은 `llm.outreach_opener` 를 갈아끼워
막는다 — 조건 판정을 재는 테스트이지 문장 품질을 재는 테스트가 아니다.
"""

import uuid
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import ChatSession, Emotion, EmotionRiskScore, OutreachLog, User
from app.services import llm, outreach, push

BASE = "http://test/api/v1"


def _result(**over) -> dict:
    """판정 결과. **기본값은 `NORMAL` 이다.**

    ⚠ `CAUTION` 을 기본으로 두면 안 된다. 그날은 힐링 콘텐츠 알림
      (`MLCM_400`)이 나가므로 **선제 접촉이 겹침으로 전부 막힌다.**
      다른 조건을 재려는 테스트가 죄다 `콘텐츠알림_겹침` 으로 떨어진다.

      선제 접촉의 트리거는 위험 단계가 아니라 **기준선 이탈**이다. 이탈이
      3일 이어졌지만 위험 단계는 `NORMAL` 인 상태가 이 기능의 본래 자리다.
    """
    r = {
        "emotion_code": "SADNESS",
        "emotion_score": 60.0,
        "risk_level": "NORMAL",
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


@pytest.fixture(autouse=True)
def _always_sendable(monkeypatch):
    """발송 시간대를 하루 종일로 연다.

    ⚠ **이게 없으면 테스트가 벽시계에 묶인다.** `ACTIVE_FROM`~`ACTIVE_TO`
      밖에서 돌리면 조건 판정이 전부 `발송시간_아님` 으로 떨어져, 세션
      선생성·쿨다운·발견 경로까지 **8건이 한꺼번에 실패**한다. 실제로
      2026.08.05 저녁에 만들 때는 통과했다가 이튿날 08:43 에 깨졌다.

      실패 메시지는 `assert 'SKIPPED' == 'FAILED'` 라 시각과 무관해 보이고,
      **아홉 시가 지나면 저절로 낫는다.** 원인을 찾기 가장 나쁜 형태다.

    시각 조건 자체는 아래 `test_발송_시간대가_아니면_보내지_않는다` 가
    창을 닫아놓고 따로 잰다.
    """
    monkeypatch.setattr(outreach, "ACTIVE_FROM", time(0, 0))
    monkeypatch.setattr(outreach, "ACTIVE_TO", time(23, 59, 59))


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
async def test_FCM_토큰이_없으면_발송은_실패로_남는다(client, user):
    """`SENT` 로 적으면 보내지도 않고 보냈다고 기록하는 것이다.

    회원가입만으로는 `fcm_token` 이 채워지지 않는다 — 앱이 로그인 후
    `PATCH /users/me/notifications` 로 등록해야 생긴다.
    """
    uid = await _uid(client, user)
    row = await _run(uid, _result())
    assert row.delivery_status == "FAILED"
    assert row.skip_reason == "fcm_토큰_없음"


@pytest.mark.asyncio
async def test_FCM_토큰이_있으면_실제로_발송한다(client, user, monkeypatch):
    """`push.send` 가 호출되고, 성공하면 `SENT` 로 남는다.

    실제 Firebase 로 나가면 테스트가 자격증명·네트워크에 묶인다 —
    `push.send` 자체를 갈아끼워 「호출했는가」만 잰다.
    """
    uid = await _uid(client, user)
    async with AsyncSessionLocal() as db:
        u = await db.get(User, uid)
        u.fcm_token = "fake-token-for-test"
        await db.commit()

    sent: list[tuple[str, str, str]] = []

    async def fake_send(token, title, body, data=None):
        sent.append((token, title, body))
        return "fake-message-id"

    monkeypatch.setattr(push, "send", fake_send)

    row = await _run(uid, _result())
    assert row.delivery_status == "SENT"
    assert row.skip_reason is None
    assert len(sent) == 1
    token, title, body = sent[0]
    assert token == "fake-token-for-test"
    assert title and body
    # ⚠ 알림 본문에 opener 원문(예: "요즘 어떠셨어요")을 넣지 않는다 —
    #   잠금화면 노출 위험(services/push.py 참고).
    assert "요즘 어떠셨어요" not in body


@pytest.mark.asyncio
async def test_FCM_발송이_실패해도_세션은_유지된다(client, user, monkeypatch):
    """`MLCM_220` 6단계 — 발송 실패가 선생성된 세션을 되돌리지 않는다."""
    uid = await _uid(client, user)
    async with AsyncSessionLocal() as db:
        u = await db.get(User, uid)
        u.fcm_token = "fake-token-for-test"
        await db.commit()

    async def boom(token, title, body, data=None):
        raise RuntimeError("네트워크 장애 흉내")

    monkeypatch.setattr(push, "send", boom)

    row = await _run(uid, _result())
    assert row.delivery_status == "FAILED"
    assert row.skip_reason == "fcm_발송_실패"
    assert row.session_id is not None

    async with AsyncSessionLocal() as db:
        s = await db.get(ChatSession, row.session_id)
        assert s is not None


@pytest.mark.asyncio
async def test_CRITICAL_이면_보내지_않는다(client, user):
    """긴급 상담 연결(MLCM_510)이 이미 개입한 상태다."""
    uid = await _uid(client, user)
    row = await _run(uid, _result(risk_level="CRITICAL"))
    assert row.delivery_status == "SKIPPED"
    assert row.skip_reason == "risk_critical"
    assert row.session_id is None


@pytest.mark.asyncio
async def test_발송_시간대가_아니면_보내지_않는다(client, user, monkeypatch):
    """새벽에 말을 걸면 그 자체가 해가 된다.

    `_always_sendable` 이 열어둔 창을 여기서만 닫는다. 벽시계를 그대로 쓰면
    「아홉 시에 돌리면 통과하는 테스트」가 되어 아무것도 보장하지 못한다.
    """
    monkeypatch.setattr(outreach, "ACTIVE_FROM", time(3, 0))
    monkeypatch.setattr(outreach, "ACTIVE_TO", time(3, 1))

    uid = await _uid(client, user)
    row = await _run(uid, _result())
    assert row.delivery_status == "SKIPPED"
    assert row.skip_reason == "발송시간_아님"
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
async def test_콘텐츠_알림과_같은_날이면_보내지_않는다(client, user):
    """`MLCM_220` ※ — 「같은 날 두 알림이 겹치면 보내지 않는다」.

    `CAUTION` 판정은 힐링 콘텐츠 알림(`MLCM_400`)을 유발한다. 거기에 선제
    접촉까지 가면 **하루에 두 번 울린다.**
    """
    uid = await _uid(client, user)
    row = await _run(uid, _result(risk_level="CAUTION"))
    assert row.delivery_status == "SKIPPED"
    assert row.skip_reason == "콘텐츠알림_겹침"
    assert row.session_id is None


@pytest.mark.asyncio
async def test_콘텐츠_알림을_꺼두면_겹치지_않는다(client, user):
    """끈 것은 콘텐츠 쪽인데 안부 인사까지 막히면 안 된다.

    푸시가 애초에 안 나가므로 **겹칠 것이 없다.** 이 검사가 빠지면 알림을
    줄이려던 사람이 선제 접촉까지 잃는다 — 알림을 끄는 사람일수록 앱을
    안 여는 사람이라 손실이 크다.
    """
    uid = await _uid(client, user)
    async with AsyncSessionLocal() as db:
        u = await db.get(User, uid)
        u.content_alert_agreed = False
        await db.commit()

    row = await _run(uid, _result(risk_level="CAUTION"))
    assert row.delivery_status == "FAILED"      # 접촉이 나갔다
    assert row.session_id is not None


@pytest.mark.asyncio
async def test_오늘_앞서_CAUTION_판정이_있었으면_보내지_않는다(client, user):
    """지금 판정이 NORMAL 이어도 **오늘 이미 콘텐츠 알림이 나갔다.**

    하루에 판정이 여러 번 적재될 수 있다. 지금 들고 있는 것만 보면
    오전에 나간 콘텐츠 알림을 놓친다.
    """
    uid = await _uid(client, user)
    async with AsyncSessionLocal() as db:
        emotion_id = await db.scalar(
            select(Emotion.emotion_id).where(Emotion.emotion_code == "SADNESS")
        )
        assert emotion_id is not None, "EMOTIONS 시드가 없습니다"
        db.add(EmotionRiskScore(
            user_id=uid,
            emotion_id=emotion_id,
            emotion_score=Decimal("60.00"),
            risk_level="CAUTION",
            risk_score=Decimal("55.00"),
            model_version="test",
            # 오늘(KST) 안이되 지금보다 앞선 시각.
            evaluated_at=datetime.now(outreach.KST).replace(
                hour=9, minute=0, second=0, microsecond=0
            ),
        ))
        await db.commit()

    row = await _run(uid, _result(risk_level="NORMAL"))
    assert row.delivery_status == "SKIPPED"
    assert row.skip_reason == "콘텐츠알림_겹침"


@pytest.mark.asyncio
async def test_어제_CAUTION_은_오늘을_막지_않는다(client, user):
    """겹침 판정은 **하루 단위**다. 어제 것까지 막으면 쿨다운과 구분이 없다."""
    uid = await _uid(client, user)
    async with AsyncSessionLocal() as db:
        emotion_id = await db.scalar(
            select(Emotion.emotion_id).where(Emotion.emotion_code == "SADNESS")
        )
        db.add(EmotionRiskScore(
            user_id=uid,
            emotion_id=emotion_id,
            emotion_score=Decimal("60.00"),
            risk_level="CAUTION",
            risk_score=Decimal("55.00"),
            model_version="test",
            evaluated_at=datetime.now(outreach.KST) - timedelta(days=1),
        ))
        await db.commit()

    row = await _run(uid, _result())
    assert row.delivery_status == "FAILED"
    assert row.session_id is not None


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
