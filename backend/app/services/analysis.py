"""AI 추론 서버 연동 — MLCM_210

라이프로그 적재가 끝나면 분석을 트리거하고 결과를 EMOTION_RISK_SCORES 에 적재한다.

내부 API 라 인증이 없다. 두 서버가 같은 네트워크 안에 있고 AI 서버 포트를
외부에 열지 않는 것을 전제로 한다 — API설계_사전결정 7절.

⚠ AI 추론 서버는 아직 구현되지 않았다. 여기서는 **계약과 적재 경로만** 갖춰두고,
  서버가 없거나 실패하면 조용히 넘어간다. 라이프로그 수신 자체는 이미 성공했으므로
  분석 실패로 push 를 되돌리면 안 된다.
"""

import logging
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models import Emotion, EmotionRiskScore

logger = logging.getLogger(__name__)

# AI 서버가 죽어 있을 때 push 응답이 늘어지지 않도록 짧게 끊는다.
# 백그라운드 태스크라 사용자 응답에는 영향이 없지만, 워커를 오래 점유하면
# 15분 주기로 들어오는 다음 배치가 밀린다.
TIMEOUT_SECONDS = 10.0


async def trigger_lifelog_analysis(user_id: uuid.UUID) -> None:
    """MLCM_210 — 적재 완료 신호를 받은 AI 서버가 분석을 수행한다.

    비즈니스 서버는 user_id 와 시각만 보낸다. AI 서버가 DB 에서 최근 14일
    기준값과 최신 시퀀스를 직접 읽는다. 페이로드로 실어 보내면 요청이 비대해지고,
    전처리 규격이 바뀔 때마다 양쪽을 함께 고쳐야 한다.
    """
    payload = {
        "user_id": str(user_id),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as http:
            resp = await http.post(
                f"{settings.ai_server_url}/internal/analyze/lifelog", json=payload
            )
            resp.raise_for_status()
            result = resp.json()
    except Exception as e:
        # AI 서버 미구현·미기동·타임아웃 전부 여기로 온다.
        # 라이프로그는 이미 적재됐으므로 다음 주기에 다시 분석되면 된다.
        logger.info("분석 트리거 실패 (user=%s): %s", user_id, e)
        return

    await _persist(user_id, result)


async def _persist(user_id: uuid.UUID, result: dict) -> None:
    """AI 서버 판정 결과를 적재한다.

    risk_level 매핑은 **AI 서버가 확정한다**(04 문서 6항). 비즈니스 서버가
    다시 계산하면 규칙이 두 곳에 존재하게 되어 반드시 어긋난다.
    여기서는 값이 규격에 맞는지만 확인한다.
    """
    required = {"emotion_code", "emotion_score", "risk_level", "risk_score", "model_version"}
    missing = required - result.keys()
    if missing:
        logger.warning("분석 결과 필드 누락: %s", missing)
        return

    if result["risk_level"] not in ("NORMAL", "CAUTION", "CRITICAL"):
        logger.warning("알 수 없는 risk_level: %s", result["risk_level"])
        return

    async with AsyncSessionLocal() as db:
        emotion_id = await db.scalar(
            select(Emotion.emotion_id).where(
                Emotion.emotion_code == result["emotion_code"]
            )
        )
        if emotion_id is None:
            # EMOTIONS 는 9종 고정 마스터다. 없는 코드가 오면 AI 서버 쪽 오류다.
            logger.warning("등록되지 않은 감정 코드: %s", result["emotion_code"])
            return

        db.add(
            EmotionRiskScore(
                user_id=user_id,
                emotion_id=emotion_id,
                emotion_score=result["emotion_score"],
                risk_level=result["risk_level"],
                risk_score=result["risk_score"],
                model_version=result["model_version"],
                evaluated_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

    logger.info(
        "분석 적재 완료 user=%s level=%s emotion=%s",
        user_id,
        result["risk_level"],
        result["emotion_code"],
    )
