"""대화 맥락 상한 — 글자수 컷이 지켜야 할 것들.

턴 수(`recent_turns[-10:]`)로 자르던 것을 글자수로 바꿨습니다(2026.08.04).
같은 10턴이라도 분량이 몇 배 차이가 나서 매 요청의 입력 크기를 예측할 수
없었고, `NFR-DV-001` 3초 예산의 여유가 101ms 뿐이라 예측 가능한 쪽이
낫습니다.
"""
from app.services import llm


def test_오래된_턴부터_버린다():
    turns = [
        {"role": "user", "content": "가" * 30},
        {"role": "assistant", "content": "나" * 30},
        {"role": "user", "content": "다" * 30},
    ]
    kept = llm.trim_turns(turns, 70)
    assert [t["content"][0] for t in kept] == ["나", "다"]


def test_예산이_넉넉하면_전부_남는다():
    turns = [{"role": "user", "content": "가" * 10} for _ in range(5)]
    assert len(llm.trim_turns(turns, 1000)) == 5


def test_턴_경계로_자른다():
    """⚠ 글자수로 딱 끊으면 안 된다.

    「친구가 죽고 싶다고 했어요」가 「죽고 싶다고 했어요」로 남으면
    위기 판정에서 제3자가 본인이 된다.
    """
    turns = [
        {"role": "user", "content": "친구가 죽고 싶다고 했어요"},
        {"role": "assistant", "content": "많이 걱정되셨겠어요"},
    ]
    kept = llm.trim_turns(turns, 15)
    assert all(t["content"] in {x["content"] for x in turns} for t in kept)


def test_긴_메시지는_뒤쪽을_남긴다():
    """최근 발화일수록 뒤가 결론인 경우가 많다."""
    turns = [{"role": "user", "content": "앞" * 700 + "결론"}]
    kept = llm.trim_turns(turns, llm.REPLY_CONTEXT_CHARS)
    assert len(kept[0]["content"]) == llm.MAX_MESSAGE_CHARS
    assert kept[0]["content"].endswith("결론")


def test_위기_맥락이_응답_맥락보다_짧다():
    """일부러 짧게 둔다.

    판정 대상은 직전 발화 하나이고 앞 문맥은 제3자·과거형을 가리는
    용도다. 길어지면 옛날 부정 감정에 끌려가 오탐이 는다.
    """
    assert llm.CRISIS_CONTEXT_CHARS < llm.REPLY_CONTEXT_CHARS


def test_평가_경로의_문자열은_바뀌지_않는다():
    """`tools/eval_crisis.py` 가 `recent_turns=[]` 로 부른다.

    상한을 조정해도 평가가 만드는 문자열과 캐시 키가 그대로여야 한다.
    바뀌면 200건을 다시 채점해야 한다.
    """
    assert llm.crisis_user_message("죽고 싶다", []) == (
        "[최근 대화]\n\n\n[판정 대상 발화]\n죽고 싶다"
    )
