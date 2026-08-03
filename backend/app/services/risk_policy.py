"""위험 단계 → 시스템 액션 매핑 — 01 기획서 · 02 `MLCM_210` 6단계

    NORMAL   -> CHAT       일상 공감 대화
    CAUTION  -> CONTENT    힐링 콘텐츠 추천 (MLCM_400)
    CRITICAL -> EMERGENCY  콘텐츠 중단 + 109 연결 UI (MLCM_510)

**이 매핑은 여기 한 곳에만 둡니다.**

전에는 `home.py` 의 `_ACTION` 딕셔너리와 `chat.py` 의 `_decide()` 인라인
분기가 같은 규칙을 각각 갖고 있었습니다. 둘 다 주석에는 "클라이언트에 규칙을
복제하면 반드시 어긋난다"고 적어두고, 정작 서버 안에서 자기들끼리 복제한
상태였습니다. 값이 같아서 드러나지 않았을 뿐입니다
(→ `docs/검증/구현_갭_20260803.md` 중복 1).

⚠ **`risk_level` 자체를 계산하지 않습니다.** 라이프로그 경로의 위험 단계는
  AI 서버의 `risk_level_of()` 가 확정하고(04 문서 6항), 대화 경로는
  `chat.py` 의 `_decide()` 가 키워드·LLM 판정으로 정합니다. 여기는 **이미
  정해진 단계를 액션으로 옮기기만** 합니다.

⚠ **클라이언트는 이 표를 복제하지 않습니다.** 서버가 `action` 을 내려주고
  앱·웹은 그대로 따릅니다(API설계_사전결정 3절).
"""

from typing import Literal

RiskLevel = Literal["NORMAL", "CAUTION", "CRITICAL"]
Action = Literal["CHAT", "CONTENT", "EMERGENCY"]

# 02 `MLCM_210` 6단계가 규정한 매핑 그대로입니다.
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
