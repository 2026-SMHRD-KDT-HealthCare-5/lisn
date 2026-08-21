"""대화 위기 판정이 DB 에 남는가 — MLCM_320 7단계 · 구현_갭 갭 9

여기서 지키려는 것은 하나다.

    **사용자가 「죽고 싶다」고 말하면 관리자 관제에 보여야 한다.**

전에는 안 보였다. `chat.py` 가 응답만 버리고 판정을 어디에도 남기지 않아서,
관제의 위기 사건 이력(EMOTION_RISK_SCORES 의 CRITICAL 행)에 아무 일도
일어나지 않았다. 수면·걸음이 무너진 사람은 보이는데 **직접 말한 사람은
안 보이는** 상태였다.
"""

import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import Emotion, EmotionRiskScore, User
from app.services import crisis_log, llm
from tests.conftest import BASE

CRISIS_UTTERANCE = "그냥 다 사라지고 싶어. 죽고 싶다는 생각이 계속 들어"
CALM_UTTERANCE = "오늘은 산책도 하고 기분이 괜찮았어요"


def _fake_llm(reply, is_crisis, severity):
    """`analyze_and_reply` 를 대신한다.

    ⚠ **실제 LLM 을 부르지 않는다.** `.env` 에 키가 있으면 테스트가 매번 외부
      API 를 치는데, 느린 것보다 나쁜 것은 **판정이 그날그날 달라져 테스트가
      흔들리는 것**이다. 여기서 보려는 것은 판정 품질이 아니라 「판정이 나온
      뒤 DB 에 남는가」다. 판정 품질은 `docs/평가셋/` 이 따로 잰다.

    `is_crisis=None` 이면 외부 API 장애를 흉내낸다 — 키워드 단독 경로.
    """

    async def _call(persona_type, utterance, recent_turns, keyword_level="NONE"):
        if is_crisis is None:
            return None, None
        return reply, llm.CrisisVerdict(
            is_crisis=is_crisis, severity=severity, matched_context="테스트"
        )

    return _call


async def _scores(email: str) -> list[EmotionRiskScore]:
    async with AsyncSessionLocal() as db:
        uid = await db.scalar(select(User.user_id).where(User.email == email))
        rows = await db.scalars(
            select(EmotionRiskScore)
            .where(EmotionRiskScore.user_id == uid)
            .order_by(EmotionRiskScore.evaluated_at)
        )
        return list(rows)


async def _say(client, user, text, session_id=None):
    """한 마디 한다. 세션을 안 주면 새로 연다."""
    if session_id is None:
        r = await client.post(
            f"{BASE}/chat/sessions",
            headers=user["headers"],
            json={"persona_type": "FRIEND"},
        )
        session_id = r.json()["session_id"]
    resp = await client.post(
        f"{BASE}/chat/sessions/{session_id}/messages",
        headers=user["headers"],
        json={"content": text},
    )
    return session_id, resp


# ---------------------------------------------------------------------------
#  1. 위기 발화가 판정 이력에 남는가 — 이 갭의 본체
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_위기_발화가_판정_이력에_남는다(client, user, monkeypatch):
    monkeypatch.setattr(llm, "analyze_and_reply", _fake_llm("버려질 응답", True, "HIGH"))

    _, resp = await _say(client, user, CRISIS_UTTERANCE)
    assert resp.json()["risk"]["action"] == "EMERGENCY"

    rows = await _scores(user["email"])
    assert len(rows) == 1, "위기 발화인데 판정 이력이 남지 않았습니다"

    row = rows[0]
    assert row.risk_level == "CRITICAL"
    assert row.model_version == "chat-crisis-llm-v1"
    # 측정값이 아니라 정책 상수다 — crisis_log.CRISIS_SCORE 주석 참고.
    assert float(row.emotion_score) == 100.0
    assert float(row.risk_score) == 100.0

    async with AsyncSessionLocal() as db:
        code = await db.scalar(
            select(Emotion.emotion_code).where(Emotion.emotion_id == row.emotion_id)
        )
    assert code == "CRISIS"


@pytest.mark.asyncio
async def test_외부_API_장애면_키워드_단독임이_모델_버전에_남는다(client, user, monkeypatch):
    """`NFR-DV-003` — 장애 중에도 키워드 필터는 돌고, 관제도 계속 봐야 한다.

    ⚠ 다만 키워드 단독은 **정밀도 0.500** 이다(평가셋 200건 · TP 10 / FP 10).
      같은 CRITICAL 이라도 근거가 다르다는 것이 관리자 화면에 보여야,
      오탐에 개입하느라 진짜를 놓치지 않는다.
    """
    monkeypatch.setattr(llm, "analyze_and_reply", _fake_llm(None, None, None))

    _, resp = await _say(client, user, CRISIS_UTTERANCE)
    body = resp.json()
    assert body["risk"]["source"] == "KEYWORD"
    assert body["risk"]["action"] == "EMERGENCY"

    rows = await _scores(user["email"])
    assert len(rows) == 1
    assert rows[0].model_version == "chat-crisis-kw-v1"


# ---------------------------------------------------------------------------
#  2. 한 사람이 관제 목록을 통째로 덮지 않는가
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_같은_세션에서_여러_번_말해도_한_행만_남는다(client, user, monkeypatch):
    """위기 상태의 사람은 연달아 말한다. 그때마다 행을 넣으면 관제의
    「위기 사건 이력」 첫 페이지를 그 사람 혼자 채우고, **다른 위험군이
    화면에서 밀려난다.** 감시하려고 만든 화면이 감시를 방해한다.

    발화 자체는 CHAT_SESSIONS.messages 에 전부 남으므로 잃는 정보가 없다.
    """
    monkeypatch.setattr(llm, "analyze_and_reply", _fake_llm(None, True, "HIGH"))

    sid, _ = await _say(client, user, CRISIS_UTTERANCE)
    await _say(client, user, "정말 그만두고 싶어요", sid)
    await _say(client, user, CRISIS_UTTERANCE, sid)

    rows = await _scores(user["email"])
    assert len(rows) == 1, f"한 세션에 {len(rows)}행이 쌓였습니다"

    detail = (
        await client.get(f"{BASE}/chat/sessions/{sid}", headers=user["headers"])
    ).json()
    said = [m for m in detail["messages"] if m["role"] == "user"]
    assert len(said) == 3, "발화 자체는 전부 남아 있어야 합니다"


@pytest.mark.asyncio
async def test_세션이_다르면_따로_남는다(client, user, monkeypatch):
    """다른 때 다시 위기가 오면 그건 별개의 사건이다. 묶어버리면 재발을
    못 본다."""
    monkeypatch.setattr(llm, "analyze_and_reply", _fake_llm(None, True, "HIGH"))

    await _say(client, user, CRISIS_UTTERANCE)
    await _say(client, user, CRISIS_UTTERANCE)  # 새 세션

    rows = await _scores(user["email"])
    assert len(rows) == 2


# ---------------------------------------------------------------------------
#  3. 남기지 말아야 할 때 안 남기는가
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_평범한_대화는_아무것도_남기지_않는다(client, user, monkeypatch):
    monkeypatch.setattr(llm, "analyze_and_reply", _fake_llm("좋으셨겠어요", False, "NONE"))

    _, resp = await _say(client, user, CALM_UTTERANCE)
    assert resp.json()["risk"]["action"] != "EMERGENCY"
    assert await _scores(user["email"]) == []


@pytest.mark.asyncio
async def test_주의_단계는_남기지_않는다(client, user, monkeypatch):
    """CAUTION 은 콘텐츠 추천으로 대응한다(MLCM_400). 위기 사건이 아니다.

    여기까지 적재하면 관제의 「심각」이 실제 위기가 아닌 것으로 채워진다.
    """
    monkeypatch.setattr(llm, "analyze_and_reply", _fake_llm("힘드셨겠어요", True, "MEDIUM"))

    _, resp = await _say(client, user, "요즘 좀 답답하네요")
    assert resp.json()["risk"]["level"] == "CAUTION"
    assert await _scores(user["email"]) == []


# ---------------------------------------------------------------------------
#  4. 기록이 실패해도 안전장치가 막히지 않는가
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_감정_마스터가_없어도_긴급_전환은_된다(client, user, monkeypatch):
    """기록은 부가 기능이고 **긴급 상담 연결이 본체다.**

    시드가 안 들어간 DB 에서 감정 코드를 못 찾았다고 대화 요청이 500 이 되면,
    위기에 처한 사용자가 긴급 화면을 못 본다. 그건 훨씬 나쁘다.
    """
    monkeypatch.setattr(llm, "analyze_and_reply", _fake_llm(None, True, "HIGH"))
    monkeypatch.setattr(crisis_log, "CRISIS_EMOTION_CODE", "존재하지-않는-코드")

    _, resp = await _say(client, user, CRISIS_UTTERANCE)
    assert resp.status_code == 200
    body = resp.json()
    assert body["risk"]["action"] == "EMERGENCY"
    assert body["reply"] is None
    assert await _scores(user["email"]) == []


@pytest.mark.asyncio
async def test_기록_중_예외가_나도_대화는_저장된다(client, user, monkeypatch):
    monkeypatch.setattr(llm, "analyze_and_reply", _fake_llm(None, True, "HIGH"))

    async def _boom(*a, **kw):
        raise RuntimeError("DB 가 잠깐 흔들렸다고 치자")

    monkeypatch.setattr(crisis_log, "_already_logged", _boom)

    sid, resp = await _say(client, user, CRISIS_UTTERANCE)
    assert resp.status_code == 200
    assert resp.json()["risk"]["action"] == "EMERGENCY"

    detail = (
        await client.get(f"{BASE}/chat/sessions/{sid}", headers=user["headers"])
    ).json()
    assert len(detail["messages"]) == 1, "위기 기록이 실패했다고 발화까지 잃으면 안 됩니다"


# ---------------------------------------------------------------------------
#  5. 실제로 관제 화면까지 닿는가 — 이 갭을 연 이유
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_관리자_위기_사건_이력에_보인다(client, user, admin, monkeypatch):
    monkeypatch.setattr(llm, "analyze_and_reply", _fake_llm(None, True, "HIGH"))
    await _say(client, user, CRISIS_UTTERANCE)

    r = await client.get(f"{BASE}/admin/emergency-events", headers=admin["headers"])
    assert r.status_code == 200, r.text

    mine = [
        i
        for i in r.json()
        if str(i.get("model_version", "")).startswith("chat-crisis")
    ]
    assert mine, "채팅 위기가 관제 위기 사건 이력에 나타나지 않았습니다"
    assert mine[0]["emotion_code"] == "CRISIS"
