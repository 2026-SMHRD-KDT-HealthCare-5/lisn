"""정서 리포트 조회 — MLCM_500 · MLCM_501 공용.

본인 조회(GET /reports)와 관리자 상세 조회(GET /admin/users/{id}/report)가
같은 함수를 쓴다. MLCM_501 4단계가 "MLCM_500 과 동일한 시각화 컴포넌트 재사용,
대상 user_id 만 관리자가 지정"을 요구하므로 데이터도 같은 모양이어야 한다.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Emotion, EmotionRiskScore, LifelogMetric
from app.schemas.report import (
    LifelogPoint,
    ReportOut,
    RiskDistribution,
    RiskPoint,
)

# 리포트 한 번에 내릴 최대 점수. 차트가 읽히지 않을 만큼 촘촘해지는 것을 막는다.
MAX_POINTS = 500


def _summarize(dist: RiskDistribution, points: list[RiskPoint]) -> str:
    """종합 요약 문구 — MLCM_500 4단계.

    ⚠ 진단하지 않는다. 관찰된 분포를 서술만 한다(FR-AI-002 진단 금지).
    """
    total = dist.normal + dist.caution + dist.critical
    if total == 0:
        return "아직 분석된 기록이 없어요."

    if dist.critical:
        return (
            f"이 기간에 도움이 필요한 신호가 {dist.critical}회 관찰됐어요. "
            "혼자 견디지 않으셔도 괜찮습니다."
        )
    if dist.caution > dist.normal:
        return (
            f"주의 단계가 {dist.caution}회로 안정({dist.normal}회)보다 많았어요. "
            "쉬어가는 시간을 조금 더 가져보시면 어떨까요."
        )
    return f"전체 {total}회 중 {dist.normal}회가 안정 상태였어요. 잘 지내고 계세요."


async def build_report(
    db: AsyncSession,
    user_id: uuid.UUID,
    date_from: datetime | None,
    date_to: datetime | None,
) -> ReportOut:
    # 기간 미지정이면 최근 30일.
    if date_to is None:
        date_to = datetime.now(timezone.utc)
    if date_from is None:
        date_from = date_to - timedelta(days=30)

    rows = await db.execute(
        select(EmotionRiskScore, Emotion)
        .join(Emotion, Emotion.emotion_id == EmotionRiskScore.emotion_id)
        .where(
            EmotionRiskScore.user_id == user_id,
            EmotionRiskScore.evaluated_at >= date_from,
            EmotionRiskScore.evaluated_at <= date_to,
        )
        .order_by(EmotionRiskScore.evaluated_at.asc())
        .limit(MAX_POINTS)
    )

    dist = RiskDistribution()
    trend: list[RiskPoint] = []
    for score, emotion in rows:
        trend.append(
            RiskPoint(
                evaluated_at=score.evaluated_at,
                emotion_code=emotion.emotion_code,
                emotion_name=emotion.emotion_name,
                emotion_score=score.emotion_score,
                risk_level=score.risk_level,
                risk_score=score.risk_score,
            )
        )
        setattr(dist, score.risk_level.lower(), getattr(dist, score.risk_level.lower()) + 1)

    logs = await db.scalars(
        select(LifelogMetric)
        .where(
            LifelogMetric.user_id == user_id,
            LifelogMetric.collected_at >= date_from,
            LifelogMetric.collected_at <= date_to,
        )
        .order_by(LifelogMetric.collected_at.asc())
        .limit(MAX_POINTS)
    )

    return ReportOut(
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        distribution=dist,
        emotion_trend=trend,
        lifelog_trend=[
            LifelogPoint(
                collected_at=m.collected_at,
                steps=m.steps,
                total_sleep_min=m.total_sleep_min,
                heart_rate=m.heart_rate,
                hrv=m.hrv,
            )
            for m in logs
        ],
        summary=_summarize(dist, trend),
    )
