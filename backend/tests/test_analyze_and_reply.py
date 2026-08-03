"""`analyze_and_reply` 병렬 호출 — `NFR-DV-001` · `NFR-TS-001`

위기가 확정되면 응답 생성을 기다리지 않는다. 실제 API 를 부르지 않고
`generate_reply`·`detect_crisis` 를 가짜로 갈아끼워 **기다림 여부**만 본다.

    cd backend
    python -m pytest tests/test_analyze_and_reply.py -q
"""

import asyncio

import pytest

from app.services import llm


class _Verdict:
    def __init__(self, is_crisis, severity):
        self.is_crisis = is_crisis
        self.severity = severity


def _patch(monkeypatch, *, reply_delay, verdict, verdict_delay=0.0, reply="응답"):
    """느린 응답 생성 / 빠른 위기 판정을 흉내낸다."""
    state = {"reply_finished": False}

    async def fake_reply(persona_type, utterance, recent_turns):
        await asyncio.sleep(reply_delay)
        state["reply_finished"] = True
        return reply

    async def fake_crisis(utterance, recent_turns):
        await asyncio.sleep(verdict_delay)
        if isinstance(verdict, BaseException):
            raise verdict
        return verdict

    monkeypatch.setattr(llm, "generate_reply", fake_reply)
    monkeypatch.setattr(llm, "detect_crisis", fake_crisis)
    return state


@pytest.mark.asyncio
async def test_HIGH_이면_응답_생성을_기다리지_않는다(monkeypatch):
    """위기 발화가 일반 발화보다 느렸던 원인 — 버릴 것을 기다렸다."""
    state = _patch(monkeypatch, reply_delay=5.0, verdict=_Verdict(True, "HIGH"))

    loop = asyncio.get_running_loop()
    t0 = loop.time()
    reply, verdict = await llm.analyze_and_reply("FRIEND", "발화", [])
    elapsed = loop.time() - t0

    assert reply is None, "버릴 응답을 들고 오면 안 됩니다"
    assert verdict.severity == "HIGH"
    assert elapsed < 1.0, f"응답 생성을 기다렸습니다({elapsed:.2f}s)"
    assert not state["reply_finished"], "취소되지 않았습니다"


@pytest.mark.asyncio
async def test_HIGH_키워드_MEDIUM_판정도_취소된다(monkeypatch):
    """실제로 가장 흔한 경우인데 처음 구현에서 빠졌던 조건.

    「요즘 정말 죽고 싶다는 생각이 들어요」에 LLM 이 MEDIUM 을 주는 일이
    잦다(프롬프트가 "실행 의도가 드러나지 않으면 MEDIUM"). 최종 CRITICAL 은
    **HIGH 키워드가 함께 있어서** 나온다.

    severity 만 보고 취소하면 이 경우에 안 걸려 개선이 통째로 무효가 된다.
    실제로 그렇게 만들었다가 실측에서 잡았다.
    """
    state = _patch(monkeypatch, reply_delay=5.0, verdict=_Verdict(True, "MEDIUM"))

    loop = asyncio.get_running_loop()
    t0 = loop.time()
    reply, _ = await llm.analyze_and_reply(
        "FRIEND", "발화", [], keyword_level="HIGH"
    )
    elapsed = loop.time() - t0

    assert reply is None
    assert elapsed < 1.0, f"응답 생성을 기다렸습니다({elapsed:.2f}s)"
    assert not state["reply_finished"]


@pytest.mark.asyncio
async def test_LLM_이_위기가_아니라면_HIGH_키워드여도_기다린다(monkeypatch):
    """CAUTION 이면 응답을 그대로 쓴다. 취소하면 폴백 문구가 나간다.

    HIGH 키워드 정밀도가 0.500 이라 「예전에 죽고 싶었는데 지금은 괜찮아요」가
    여기 해당한다. 이 사용자는 정상 응답을 받아야 한다.
    """
    _patch(monkeypatch, reply_delay=0.05, verdict=_Verdict(False, "LOW"))

    reply, _ = await llm.analyze_and_reply(
        "FRIEND", "발화", [], keyword_level="HIGH"
    )

    assert reply == "응답", "쓸 응답을 취소했습니다"


@pytest.mark.asyncio
async def test_MEDIUM_이면_응답을_그대로_기다린다(monkeypatch):
    """`is_crisis` 만으로 끊으면 안 된다.

    MEDIUM 은 `_decide()` 에서 CAUTION 이 되어 **응답을 그대로 쓴다.**
    여기서 취소해 버리면 사용자가 폴백 문구를 받는다.
    """
    _patch(monkeypatch, reply_delay=0.05, verdict=_Verdict(True, "MEDIUM"))

    reply, verdict = await llm.analyze_and_reply("FRIEND", "발화", [])

    assert reply == "응답"
    assert verdict.severity == "MEDIUM"


@pytest.mark.asyncio
async def test_응답이_먼저_끝나면_그대로_둘_다_받는다(monkeypatch):
    """순서를 강제하지 않는다. 빠른 쪽이 먼저 끝나도 결과가 달라지지 않는다."""
    _patch(
        monkeypatch,
        reply_delay=0.0,
        verdict=_Verdict(True, "HIGH"),
        verdict_delay=0.05,
    )

    reply, verdict = await llm.analyze_and_reply("FRIEND", "발화", [])

    # 이미 끝난 응답을 버리지는 않는다. 버리는 판단은 chat.py 가 한다.
    assert reply == "응답"
    assert verdict.severity == "HIGH"


@pytest.mark.asyncio
async def test_위기_판정이_실패해도_응답은_살린다(monkeypatch):
    """한쪽 실패가 다른 쪽을 죽이지 않는다 — `NFR-DV-003`."""
    _patch(
        monkeypatch,
        reply_delay=0.0,
        verdict=RuntimeError("API 장애"),
        verdict_delay=0.02,
    )

    reply, verdict = await llm.analyze_and_reply("FRIEND", "발화", [])

    assert reply == "응답"
    assert verdict is None, "실패는 None 으로 내려 키워드 fallback 이 돌게 한다"
