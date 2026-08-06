"""위험 단계 → 시스템 액션 매핑 — 기획서 · 요구사항정의서 `MLCM_210` 6단계

    NORMAL   -> CHAT       일상 공감 대화
    CAUTION  -> CONTENT    힐링 콘텐츠 추천 (MLCM_400)
    CRITICAL -> EMERGENCY  콘텐츠 중단 + 109 연결 UI (MLCM_510)

**이 매핑은 여기 한 곳에만 둡니다.**

전에는 `home.py` 의 `_ACTION` 딕셔너리와 `chat.py` 의 `_decide()` 인라인
분기가 같은 규칙을 각각 갖고 있었습니다. 둘 다 주석에는 "클라이언트에 규칙을
복제하면 반드시 어긋난다"고 적어두고, 정작 서버 안에서 자기들끼리 복제한
상태였습니다. 값이 같아서 드러나지 않았을 뿐입니다
(→ `docs/진행/구현_갭.md` 중복 1).

⚠ **`risk_level` 자체를 계산하지 않습니다.** 라이프로그 경로의 위험 단계는
  AI 서버의 `risk_level_of()` 가 확정하고(데이터베이스요구사항분석서 6항), 대화 경로는
  `chat.py` 의 `_decide()` 가 키워드·LLM 판정으로 정합니다. 여기는 **이미
  정해진 단계를 액션으로 옮기기만** 합니다.

⚠ **클라이언트는 이 표를 복제하지 않습니다.** 서버가 `action` 을 내려주고
  앱·웹은 그대로 따릅니다(API설계_사전결정 3절).
"""

from typing import Literal

RiskLevel = Literal["NORMAL", "CAUTION", "CRITICAL"]
Action = Literal["CHAT", "CONTENT", "EMERGENCY"]

# 요구사항정의서 `MLCM_210` 6단계가 규정한 매핑 그대로입니다.
RISK_ACTION: dict[str, str] = {
    "NORMAL": "CHAT",
    "CAUTION": "CONTENT",
    "CRITICAL": "EMERGENCY",
}


def action_for(risk_level: str | None) -> str | None:
    """위험 단계에 대응하는 시스템 액션. 모르는 값이면 None.

    ⚠ **모르는 값을 CHAT 으로 떨어뜨리지 않습니다.** 판정이 없거나 규격 밖의
      값이 들어왔을 때 「안정」으로 취급하면, 그건 안전한 기본값이 아니라
      **위험을 못 본 것을 정상으로 기록하는 것**입니다. 호출자가 없음을
      명시적으로 처리하게 둡니다 — `ai/server` 가 지표 부족 시 NORMAL 대신
      422 를 내는 것과 같은 이유입니다.
    """
    if risk_level is None:
        return None
    return RISK_ACTION.get(risk_level)


def is_emergency(risk_level: str | None) -> bool:
    """콘텐츠 추천을 끊어야 하는 상태인지 — `MLCM_510` 2단계."""
    return action_for(risk_level) == "EMERGENCY"


# ---------------------------------------------------------------------------
#  대화 발화의 위험 단계 — MLCM_320
# ---------------------------------------------------------------------------
#
# ⚠ **이 규칙도 한 곳에만 둡니다.** `chat.py` 의 `_decide()` 가 최종 판정에
#   쓰고, `llm.analyze_and_reply()` 가 「생성한 응답을 버리게 될지」를 미리
#   알기 위해 씁니다. 두 곳이 각자 조건을 적으면 **응답을 버릴 상황인데
#   기다리거나, 쓸 응답을 취소하는** 사고가 납니다. 실제로 한 번 냈습니다
#   (→ `docs/검증/성능실측_20260803_openai.md`).

# `severity` 가 가질 수 있는 값. 여기 없으면 **모르는 것**이지 낮은 것이 아니다.
SEVERITY = {"NONE", "LOW", "MEDIUM", "HIGH"}


def level_for(
    keyword_level: str,
    is_crisis: bool | None,
    severity: str | None,
) -> str:
    """키워드 + LLM 판정 -> 위험 단계.

    `is_crisis` 가 None 이면 **LLM 판정이 없다**(외부 API 장애). 이때는 문맥을
    볼 수단이 없으므로 미탐을 줄이는 보수적 임계치를 적용한다 — `NFR-DV-003`.

    LLM 판정이 있으면 **거부권을 살린다.** HIGH 키워드 정밀도가 0.500 이라
    (평가셋 200건 · TP 10 / FP 10) 키워드 단독으로 긴급 화면을 띄우면 절반이
    오탐이다. 「예전에 죽고 싶었는데 지금은 괜찮아요」가 여기 걸린다.

    ⚠ `severity` 는 LLM 이 채우는 자유 문자열이다. 스키마에 enum 이 걸려
      있지 않아 "High"·"위험" 같은 값이 올 수 있으므로 호출자가 아니라
      **여기서 정규화**한다.
    """
    kw = (keyword_level or "NONE").strip().upper()

    if is_crisis is None:
        # LLM 없음 — 키워드 단독
        if kw == "HIGH":
            return "CRITICAL"
        if kw == "MEDIUM":
            return "CAUTION"
        return "NORMAL"

    sev = (severity or "").strip().upper()

    # 강도가 HIGH 면 is_crisis 와 무관하게 올린다. 둘이 어긋나면 높은 쪽.
    if sev == "HIGH":
        return "CRITICAL"

    if is_crisis:
        # 위기다. 얼마나 임박했는가로 개입 강도를 정한다.
        #   HIGH 키워드가 함께 있으면 명시적 표현 + 위기 확인이 겹친 상태다.
        #   강도를 모르면 낮추지 않는다 — 「모름」은 「약함」이 아니다.
        if kw == "HIGH" or sev not in SEVERITY:
            return "CRITICAL"
        return "CAUTION"

    # LLM 이 위기가 아니라고 보았다. 키워드 단독으로 긴급 화면을 띄우지 않는다.
    if sev == "MEDIUM" or kw != "NONE":
        return "CAUTION"
    return "NORMAL"


def will_discard_reply(
    keyword_level: str,
    is_crisis: bool | None,
    severity: str | None,
) -> bool:
    """생성한 일반 응답을 버리게 될 판정인지 — `MLCM_510` 2단계.

    `llm.analyze_and_reply()` 가 이걸 보고 **응답 생성을 기다릴지** 정한다.
    버릴 것을 기다리면 위기 경로가 그만큼 느려진다. 실측에서 응답 생성이
    위기 판정보다 2.7배 길었다(5151ms vs 1920ms).
    """
    return level_for(keyword_level, is_crisis, severity) == "CRITICAL"
