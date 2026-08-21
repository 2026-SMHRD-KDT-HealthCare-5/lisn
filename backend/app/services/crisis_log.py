"""채팅 위기 판정을 DB 에 남긴다 — `MLCM_320` 7단계

## 왜 필요한가

`chat.py` 는 `EMERGENCY` 판정이 나오면 생성된 일반 응답을 버리고 사용자를
긴급 상담 화면으로 보낸다. **거기서 끝났다.** 판정 결과가 어디에도 남지
않아서, 관리자 관제의 「위기 사건 이력」에 **아무 일도 일어나지 않았다.**

관제가 읽는 것은 `EMOTION_RISK_SCORES` 의 `CRITICAL` 행뿐이고, 그건
라이프로그 기반 일일 판정(`MLCM_210`)이다. 즉 —

    수면·걸음이 무너진 사람은 보이는데, **직접 「죽고 싶다」고 말한
    사람은 안 보였다.**

요구사항정의서 `MLCM_320` 7단계가 이것을 요구한다:

> 자살/자해 암시 등 명확한 위기 문맥 … 이 탐지된 경우, 시스템은 즉시
> 해당 대화 세션을 고위험 상태로 전환하고, **위험 탐지 로그를 최우선
> 순위로 DB에 기록한다.**

→ `docs/진행/구현_갭.md` 갭 9 (A안 채택, 2026.08.22)

## 왜 새 테이블을 만들지 않는가

`EMOTION_RISK_SCORES` 에 적재한다. 새 테이블이나 새 컬럼을 만들면
데이터베이스요구사항분석서·테이블명세서와 어긋나는데 **둘 다 제출이 끝났다.**
더 중요하게는, 관제 화면이 이 테이블을 읽으므로 **조회 코드를 한 줄도
고치지 않고** 위기가 관제에 닿는다.

`model_version` 이 원래 「이 판정을 무엇이 만들었는가」를 적는 칸이라
출처가 섞이지 않는다 — 일일 판정은 `rule-`/모델 버전, 이쪽은
`chat-crisis-*` 다.

## 판정 근거를 버전에 적는 이유

**키워드 단독 판정은 정밀도가 0.500 이다**(평가셋 200건 · TP 10 / FP 10 —
`risk_policy.level_for()` 주석). 외부 API 장애 때 문맥 판단 없이 내린
결과라 절반이 오탐이다.

관리자가 목록에서 이걸 구분하지 못하면 **오탐에 개입하느라 진짜를 놓친다.**
그래서 같은 `CRITICAL` 이라도 근거를 나눠 적는다. 화면의 「모델」 칸에
그대로 보인다.

⚠ **그렇다고 키워드 단독 건을 안 남기면 안 된다.** `NFR-DV-003` 은 외부 API
  장애 중에도 키워드 필터가 단독 동작하도록 요구한다. 그때 관제까지 조용해지면
  **시스템이 가장 약할 때 감시도 함께 꺼진다.**
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Emotion, EmotionRiskScore

logger = logging.getLogger(__name__)

# EMOTIONS 마스터 9종 중 category='CRITICAL' 인 「위기」.
# ⚠ 마스터는 `db/schema.sql` 이 정본이다. 코드를 바꾸면 여기도 바꾼다.
CRISIS_EMOTION_CODE = "CRISIS"

# 판정 근거(`RiskInfo.source`) → model_version.
# ⚠ 관리자 화면의 「모델」 칸에 이 값이 그대로 나온다. 사람이 읽고 판단하는
#   값이므로 줄이거나 암호처럼 만들지 말 것.
MODEL_VERSION = {
    "LLM": "chat-crisis-llm-v1",
    "KEYWORD": "chat-crisis-kw-v1",
}
CHAT_CRISIS_VERSIONS = tuple(MODEL_VERSION.values())

# ⚠ **측정값이 아니라 정책 상수다.**
#
#   일일 판정(`MLCM_210`)의 점수는 개인 기준선 이탈을 환산한 값이지만,
#   대화 위기 탐지에는 그런 척도가 없다. 있는 척 중간값을 넣으면 리포트
#   차트에서 **측정된 값처럼 보인다.**
#
#   「확정된 위기는 최고 위험도」라는 **정의**로 100 을 쓴다. 근거는
#   `model_version` 이 말해 준다 — 그 값을 보면 어떻게 나온 점수인지 안다.
CRISIS_SCORE = Decimal("100.00")


async def record(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_started_at: datetime,
    source: str,
    now: datetime,
) -> bool:
    """위기 판정을 적재한다. 실제로 넣었으면 True.

    ⚠ **커밋하지 않는다.** 호출자(`chat.py`)의 트랜잭션에 얹는다.
      대화 저장과 같은 커밋에 묶여야 「메시지는 저장됐는데 위기 기록은
      없는」 상태가 생기지 않는다. 커밋이 실패하면 요청 자체가 실패하고
      사용자는 긴급 화면을 보지 못하므로, 그때 로그만 남는 것도 무의미하다.

    ⚠ **여기서 예외를 밖으로 던지지 않는다.** 기록에 실패해도 사용자는
      긴급 상담 화면으로 가야 한다. 안전장치가 로그 때문에 막히면 안 된다.
    """
    try:
        if await _already_logged(db, user_id, session_started_at):
            return False

        emotion_id = await db.scalar(
            select(Emotion.emotion_id).where(
                Emotion.emotion_code == CRISIS_EMOTION_CODE
            )
        )
        if emotion_id is None:
            # EMOTIONS 는 9종 고정 마스터다. 없으면 시드가 안 들어간 DB다.
            logger.warning(
                "감정 마스터에 %s 가 없어 위기 기록을 남기지 못했습니다 "
                "(db/schema.sql 의 EMOTIONS 시드 확인)",
                CRISIS_EMOTION_CODE,
            )
            return False

        db.add(
            EmotionRiskScore(
                user_id=user_id,
                emotion_id=emotion_id,
                emotion_score=CRISIS_SCORE,
                risk_level="CRITICAL",
                risk_score=CRISIS_SCORE,
                model_version=MODEL_VERSION.get(source, MODEL_VERSION["KEYWORD"]),
                evaluated_at=now,
            )
        )
        logger.info("대화 위기 기록 적재 user=%s source=%s", user_id, source)
        return True

    except Exception as e:  # noqa: BLE001
        logger.warning("대화 위기 기록 실패 (user=%s): %s", user_id, e)
        return False


async def _already_logged(
    db: AsyncSession, user_id: uuid.UUID, session_started_at: datetime
) -> bool:
    """이 세션에서 이미 위기를 기록했는가.

    ⚠ **한 세션에 한 번만 남긴다.** 위기 상태의 사람은 연달아 여러 마디를
      한다. 그때마다 행을 넣으면 관제의 「위기 사건 이력」 첫 페이지를
      **그 사람 혼자 채운다.** 목록은 최신순이라, 그 뒤로 밀려난 다른
      위험군이 화면에서 사라진다 — 감시하려고 만든 화면이 감시를 방해한다.

      발화 하나하나는 `CHAT_SESSIONS.messages` 에 그대로 남는다. 관리자가
      상세로 들어가면 전부 볼 수 있으므로 **잃는 정보가 없다.**

    ⚠ 세션 경계로 자르는 이유는 요구사항 문구가 「해당 대화 **세션**을
      고위험 상태로 전환」이기 때문이다. 시간 창(예: 30분)으로 자르면
      기준이 문서 어디에도 없는 임의값이 된다.
    """
    hit = await db.scalar(
        select(EmotionRiskScore.score_id)
        .where(
            EmotionRiskScore.user_id == user_id,
            EmotionRiskScore.evaluated_at >= session_started_at,
            EmotionRiskScore.model_version.in_(CHAT_CRISIS_VERSIONS),
        )
        .limit(1)
    )
    return hit is not None
