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
#
# ⚠ 자를 때는 **최신 쪽을 남긴다.** 오름차순에 LIMIT 을 걸면 기간 안에서 가장
#   **오래된** 500건이 잡혀 최근 데이터가 통째로 사라진다. 분석은 라이프로그
#   push 마다 1건씩 쌓이므로(앱 15분 주기 → 하루 최대 96건) 30일 기본 구간은
#   금방 500건을 넘는다 — 며칠만 써도 리포트가 첫 며칠에서 멈춘다.
#   그래서 내림차순으로 뽑고 파이썬에서 뒤집는다.
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
        .order_by(EmotionRiskScore.evaluated_at.desc())
        .limit(MAX_POINTS)
    )

    dist = RiskDistribution()
    trend: list[RiskPoint] = []
    # 최신순으로 받아 왔으므로 차트용으로 다시 시간순으로 되돌린다.
    for score, emotion in reversed(list(rows)):
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
        .order_by(LifelogMetric.collected_at.desc())
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
            for m in reversed(list(logs))
        ],
        summary=_summarize(dist, trend),
    )
