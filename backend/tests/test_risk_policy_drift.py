"""위험 단계 정책이 한 곳에만 있는지 — DB 없이 돕니다.

이 프로젝트에는 「규칙을 두 곳에 두지 않는다」는 원칙이 여러 문서에 적혀
있습니다(데이터베이스요구사항분석서 6항 · API설계_사전결정 3절). 그런데 **지키는 장치는 없어서**
실제로 두 곳에 복제된 상태가 한동안 유지됐습니다
(→ `docs/진행/구현_갭.md` 중복 1·2).

원칙을 주석으로 적는 것으로는 안 지켜집니다. 여기서 기계로 고정합니다.

    cd backend
    python -m pytest tests/test_risk_policy_drift.py -q
"""

import re
from pathlib import Path

from app.api.v1 import chat, home
from app.services import risk_policy

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_SQL = ROOT / "db" / "schema.sql"
AI_SERVER = ROOT / "ai" / "server" / "main.py"


# ---------------------------------------------------------------------------
#  1. risk_level -> action 매핑
# ---------------------------------------------------------------------------

def test_액션_매핑이_문서와_같다():
    """요구사항정의서 `MLCM_210` 6단계가 규정한 매핑 그대로여야 한다."""
    assert risk_policy.RISK_ACTION == {
        "NORMAL": "CHAT",
        "CAUTION": "CONTENT",
        "CRITICAL": "EMERGENCY",
    }


def test_모르는_단계를_CHAT_으로_떨어뜨리지_않는다():
    """판정이 없는 것과 안정인 것은 다르다.

    없음을 NORMAL 로 취급하면 「위험을 못 본 것」이 「정상」으로 기록된다.
    `ai/server` 가 지표 부족 시 NORMAL 대신 422 를 내는 것과 같은 이유다.
    """
    assert risk_policy.action_for(None) is None
    assert risk_policy.action_for("UNKNOWN") is None
    assert risk_policy.action_for("") is None
    assert not risk_policy.is_emergency(None)


def test_액션_문자열을_다른_모듈이_직접_적지_않는다():
    """`home.py`·`chat.py` 가 매핑을 다시 갖지 않는지.

    전에는 `home.py` 에 `_ACTION` 딕셔너리가, `chat.py` `_decide()` 에
    인라인 분기가 각각 있었다. 값이 같아서 드러나지 않았을 뿐 규칙은 셋이었다.
    """
    for module in (home, chat):
        source = Path(module.__file__).read_text(encoding="utf-8")
        # 주석·docstring 을 걷어낸 실행 코드에서만 찾는다. 설명에는 등장해도 된다.
        code = "\n".join(
            line.split("#")[0] for line in source.splitlines()
        )
        for level, action in risk_policy.RISK_ACTION.items():
            pair = re.search(
                rf'["\']{level}["\']\s*:\s*["\']{action}["\']', code
            )
            assert pair is None, (
                f"{module.__name__} 에 {level}->{action} 매핑이 다시 적혀 있습니다. "
                "services/risk_policy.py 를 쓰세요."
            )


def test_대화_판정_세_갈래가_모두_정책을_거친다():
    """`_decide()` 가 돌려주는 액션이 정책표와 일치하는지."""

    class _Verdict:
        def __init__(self, is_crisis, severity):
            self.is_crisis = is_crisis
            self.severity = severity

    cases = [
        ({"level": "HIGH"}, None, "CRITICAL"),
        ({"level": "MEDIUM"}, None, "CAUTION"),
        ({"level": "NONE"}, None, "NORMAL"),
        ({"level": "NONE"}, _Verdict(True, "HIGH"), "CRITICAL"),
        ({"level": "NONE"}, _Verdict(False, "MEDIUM"), "CAUTION"),
        ({"level": "NONE"}, _Verdict(False, "NONE"), "NORMAL"),
    ]
    for keyword, verdict, expected_level in cases:
        info = chat._decide(keyword, verdict)
        assert info.level == expected_level
        assert info.action == risk_policy.RISK_ACTION[expected_level], (
            f"{keyword}/{verdict} 에서 액션이 정책표와 다릅니다"
        )


def test_위기_신호와_임박도를_가른다():
    """`is_crisis` 만으로 109 화면을 띄우지 않는다 — 2026.08.03.

    무의미감·사회적 고립을 위기로 **탐지**하되(`is_crisis=true`), 의도가
    드러나지 않았으면 긴급 개입까지 가지 않는다. `MLCM_320` 4·5단계가
    나눠 놓은 것과 같은 구분이다.
    """

    class _Verdict:
        def __init__(self, is_crisis, severity):
            self.is_crisis = is_crisis
            self.severity = severity

    none_kw = {"level": "NONE"}

    # 의도가 드러난 경우 — 109 로 간다
    assert chat._decide(none_kw, _Verdict(True, "HIGH")).action == "EMERGENCY"

    # 위기 신호는 있으나 의도가 불명확 — 공감 대화 + 콘텐츠까지만
    for severity in ("MEDIUM", "LOW", "NONE"):
        info = chat._decide(none_kw, _Verdict(True, severity))
        assert info.level == "CAUTION", severity
        assert info.action == "CONTENT", severity


def test_HIGH_키워드는_LLM_이_위기라고_할_때_올린다():
    """명시적 표현 + 위기 확인이 겹치면 강도가 MEDIUM 이어도 CRITICAL.

    `bench_nfr.py` 에서 「요즘 정말 죽고 싶다는 생각이 들어요」가 CONTENT 와
    EMERGENCY 사이를 오갔다(2026.08.03). LLM 이 MEDIUM 을 주면 내려갔기 때문이다.
    """

    class _Verdict:
        def __init__(self, is_crisis, severity):
            self.is_crisis = is_crisis
            self.severity = severity

    high_kw = {"level": "HIGH"}
    for verdict in (_Verdict(True, "MEDIUM"), _Verdict(True, "LOW")):
        info = chat._decide(high_kw, verdict)
        assert info.level == "CRITICAL", f"{verdict.severity} 에서 내려갔습니다"
        assert info.action == "EMERGENCY"

    # LLM 장애 — 문맥을 볼 수단이 없으므로 키워드 단독으로 올린다(NFR-DV-003)
    assert chat._decide(high_kw, None).level == "CRITICAL"


def test_LLM_이_위기가_아니라면_키워드만으로_109_를_띄우지_않는다():
    """HIGH 키워드 정밀도가 0.500 이다 — 절반이 오탐이다.

    평가셋 200건 실측(2026.08.03): TP 10 / FP 10. 아래가 전부 HIGH 키워드에
    걸리지만 위기가 아니다.

        "예전에 죽고 싶었는데 지금은 괜찮아요"
        "친구가 죽고 싶대요. 제가 어떻게 해줘야 할까요?"
        "죽고 싶은 건 아니에요. 그냥 좀 쉬고 싶어요"

    문맥을 볼 수 있을 때는 LLM 의 거부권을 살린다. 오탐을 감수하는 것은
    **문맥을 볼 수 없을 때의 정책**이지 상시 규칙이 아니다.
    """

    class _Verdict:
        def __init__(self, is_crisis, severity):
            self.is_crisis = is_crisis
            self.severity = severity

    high_kw = {"level": "HIGH"}
    for severity in ("NONE", "LOW", "MEDIUM"):
        info = chat._decide(high_kw, _Verdict(False, severity))
        assert info.level == "CAUTION", severity
        assert info.action != "EMERGENCY", severity


def test_강도를_모르면_낮추지_않는다():
    """`severity` 가 규격 밖인데 위기라고 하면 CRITICAL 로 올린다.

    안전 기능에서 「모름」을 「약함」으로 취급하면 안 된다. `severity` 는
    스키마에 enum 이 걸려 있지 않은 자유 문자열이라 실제로 올 수 있다.
    """

    class _Verdict:
        def __init__(self, is_crisis, severity):
            self.is_crisis = is_crisis
            self.severity = severity

    none_kw = {"level": "NONE"}
    for junk in ("", "  ", "위험", "SEVERE", "critical", None):
        info = chat._decide(none_kw, _Verdict(True, junk))
        assert info.level == "CRITICAL", f"severity={junk!r} 에서 낮아졌습니다"


# ---------------------------------------------------------------------------
#  2. 감정 마스터 9종 ↔ AI 서버 복제본
# ---------------------------------------------------------------------------
#
# `ai/server/main.py` 의 `EMOTION_CATEGORY` 는 **의도된 복제**다. 매 요청마다
# EMOTIONS 를 조회하지 않기 위한 것이고 주석에도 그렇게 적혀 있다.
# 없애지 않는다. 다만 어긋나면 알려주는 장치가 없어서 여기서 막는다.
#
# 챗봇 성격 이름은 `frontend/app/test/persona_label_test.dart` 가 화면설계서
# 추출본을 직접 읽어 같은 일을 한다. 그 패턴을 감정 9종에도 적용한 것이다.


def parse_emotions_seed() -> dict[str, str]:
    """`schema.sql` 의 EMOTIONS INSERT 에서 코드→카테고리를 뽑는다."""
    text = SCHEMA_SQL.read_text(encoding="utf-8")
    block = re.search(
        r"INSERT\s+INTO\s+EMOTIONS\s*\([^)]*\)\s*VALUES(.*?);",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    assert block, "schema.sql 에서 EMOTIONS INSERT 를 찾지 못했습니다"

    rows = re.findall(
        r"\(\s*'(\w+)'\s*,\s*'[^']*'\s*,\s*'(\w+)'\s*\)", block.group(1)
    )
    return {code: category for code, category in rows}


def parse_ai_server_category() -> dict[str, str]:
    """`ai/server/main.py` 의 `EMOTION_CATEGORY` 리터럴을 읽는다.

    import 하지 않는 이유: `ai/server` 는 별도 서비스라 backend 의존성 안에
    들어 있지 않다. 파일을 텍스트로 읽으면 그 경계를 넘지 않는다.
    """
    text = AI_SERVER.read_text(encoding="utf-8")
    block = re.search(r"EMOTION_CATEGORY\s*=\s*\{(.*?)\}", text, re.DOTALL)
    assert block, "ai/server/main.py 에서 EMOTION_CATEGORY 를 찾지 못했습니다"

    rows = re.findall(r'"(\w+)"\s*:\s*"(\w+)"', block.group(1))
    return {code: category for code, category in rows}


SEED = parse_emotions_seed()
AI_COPY = parse_ai_server_category()


def test_감정_마스터를_읽었다():
    """정규식이 헛돌면 아래 대조가 조용히 통과한다."""
    assert len(SEED) == 9, f"파싱된 감정: {sorted(SEED)}"
    assert len(AI_COPY) == 9, f"파싱된 복제본: {sorted(AI_COPY)}"


def test_AI서버_복제본이_정본과_같다():
    """`schema.sql` 을 고치고 `ai/server` 를 안 고치면 여기서 걸린다."""
    assert AI_COPY == SEED, (
        "감정 코드→카테고리가 어긋났습니다.\n"
        f"  schema.sql   : {SEED}\n"
        f"  ai/server    : {AI_COPY}\n"
        "db/schema.sql 이 정본입니다."
    )


def test_카테고리_값이_세_단계뿐이다():
    """`EMOTION_RISK_SCORES.risk_level` CHECK 제약과 같은 집합이어야 한다."""
    assert set(SEED.values()) <= set(risk_policy.RISK_ACTION), (
        f"알 수 없는 카테고리: {set(SEED.values()) - set(risk_policy.RISK_ACTION)}"
    )
