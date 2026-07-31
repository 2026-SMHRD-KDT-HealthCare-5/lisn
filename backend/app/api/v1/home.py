"""홈 대시보드 · 콘텐츠 추천 — MLCM_400 · MLCM_510

화면: MAIN_HOME_01
명세: docs/API명세_초안.md 6절

화면 하나가 네 가지 리소스를 쓰므로 **합성 엔드포인트**로 둔다.
개별 호출 4번이면 첫 화면 지연이 그만큼 쌓인다.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import CurrentUser
from app.models import Emotion, EmotionRiskScore, HealingContent, LifelogMetric

router = APIRouter(tags=["home"])

DbSession = Annotated[AsyncSession, Depends(get_db)]

# 위험 단계 -> 시스템 액션. 서버가 확정해 내려준다.
# 클라이언트에 규칙을 복제하면 반드시 어긋난다(API설계_사전결정 3절).
_ACTION = {"NORMAL": "CHAT", "CAUTION": "CONTENT", "CRITICAL": "EMERGENCY"}


class EmotionToday(BaseModel):
    emotion_code: str
    emotion_name: str
    emotion_score: float
    risk_level: str
    evaluated_at: datetime


class LifelogSummary(BaseModel):
    total_sleep_min: int | None = None
    steps: int | None = None
    hrv: float | None = None
    collected_at: datetime | None = None


class ContentCard(BaseModel):
    content_id: str
    category: str
    title: str
    description: str | None
    external_url: str


class HomeOut(BaseModel):
    emotion_today: EmotionToday | None
    lifelog_summary: LifelogSummary
    ai_summary: str | None
    recommendations: list[ContentCard]
    action: Literal["CHAT", "CONTENT", "EMERGENCY"]


@router.get("/home", response_model=HomeOut)
async def home(user: CurrentUser, db: DbSession):
    """MAIN_HOME_01

    action 이 EMERGENCY 면 클라이언트는 추천을 렌더하지 않고
    MAIN_EMERGENCY_01 로 전환한다 — MLCM_510 2단계(콘텐츠 추천 즉시 중단).
    그래서 서버도 그때는 recommendations 를 아예 비워 보낸다.
    """
    row = (
        await db.execute(
            select(EmotionRiskScore, Emotion)
            .join(Emotion, Emotion.emotion_id == EmotionRiskScore.emotion_id)
            .where(EmotionRiskScore.user_id == user.user_id)
            .order_by(EmotionRiskScore.evaluated_at.desc())
            .limit(1)
        )
    ).first()

    emotion_today = None
    risk_level = "NORMAL"
    if row:
        score, emotion = row
        risk_level = score.risk_level
        emotion_today = EmotionToday(
            emotion_code=emotion.emotion_code,
            emotion_name=emotion.emotion_name,
            emotion_score=float(score.emotion_score),
            risk_level=score.risk_level,
            evaluated_at=score.evaluated_at,
        )

    action = _ACTION[risk_level]

    # 최근 24시간 라이프로그 요약. 수면은 합계가 아니라 최근값을 쓴다 —
    # 15분 주기로 같은 수면 구간이 반복 적재되므로 합치면 부풀려진다.
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    agg = (
        await db.execute(
            select(
                func.max(LifelogMetric.total_sleep_min),
                func.sum(LifelogMetric.steps),
                func.avg(LifelogMetric.hrv),
                func.max(LifelogMetric.collected_at),
            ).where(
                LifelogMetric.user_id == user.user_id,
                LifelogMetric.collected_at >= since,
            )
        )
    ).first()

    summary = LifelogSummary(
        total_sleep_min=agg[0],
        steps=int(agg[1]) if agg[1] is not None else None,
        hrv=float(agg[2]) if agg[2] is not None else None,
        collected_at=agg[3],
    )

    recommendations: list[ContentCard] = []
    if action == "CONTENT" and emotion_today:
        # MLCM_400 — CAUTION 단계에서만 추천한다.
        # 등록되는 콘텐츠는 사전 안전 검수를 거친 중립적인 것만이므로
        # 감정 매칭이 빗나가도 사용자에게 해가 되지 않는다(04 문서 7항).
        cards = await db.scalars(
            select(HealingContent)
            .join(Emotion, Emotion.emotion_id == HealingContent.emotion_id)
            .where(Emotion.emotion_code == emotion_today.emotion_code)
            .limit(5)
        )
        recommendations = [
            ContentCard(
                content_id=str(c.content_id),
                category=c.category,
                title=c.title,
                description=c.description,
                external_url=c.external_url,
            )
            for c in cards
        ]

    # TODO(AI 한줄 요약): MAIN_HOME_01 ❸ 은 LLM 기반 일일 감정 종합 리포트다.
    #   EMOTION_RISK_SCORES 가 채워진 뒤에 붙인다. 지금은 분석 트리거가 없어
    #   원본 데이터 자체가 없다.
    ai_summary = None

    return HomeOut(
        emotion_today=emotion_today,
        lifelog_summary=summary,
        ai_summary=ai_summary,
        recommendations=recommendations,
        action=action,
    )


@router.get("/contents/recommendations", response_model=list[ContentCard])
async def recommendations(
    user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
):
    """콘텐츠 추천 새로고침 — MLCM_400

    홈에 포함되지만 사용자가 다시 뽑아보고 싶을 때를 위해 분리한다.
    """
    row = (
        await db.execute(
            select(EmotionRiskScore.emotion_id)
            .where(EmotionRiskScore.user_id == user.user_id)
            .order_by(EmotionRiskScore.evaluated_at.desc())
            .limit(1)
        )
    ).first()
    if row is None:
        return []

    cards = await db.scalars(
        select(HealingContent)
        .where(HealingContent.emotion_id == row[0])
        .limit(limit)
    )
    return [
        ContentCard(
            content_id=str(c.content_id),
            category=c.category,
            title=c.title,
            description=c.description,
            external_url=c.external_url,
        )
        for c in cards
    ]
