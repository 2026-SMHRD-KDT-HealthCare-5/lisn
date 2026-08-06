"""홈 대시보드 · 콘텐츠 추천 — MLCM_400 · MLCM_510

화면: MAIN_HOME_01
명세: docs/결정/API명세_초안.md 6절

화면 하나가 네 가지 리소스를 쓰므로 **합성 엔드포인트**로 둔다.
개별 호출 4번이면 첫 화면 지연이 그만큼 쌓인다.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import CurrentUser
from app.models import ChatSession, Emotion, EmotionRiskScore, HealingContent, LifelogMetric, OutreachLog
from app.services import llm, risk_policy

router = APIRouter(tags=["home"])

DbSession = Annotated[AsyncSession, Depends(get_db)]

# 위험 단계 -> 시스템 액션 매핑은 services/risk_policy.py 한 곳에 있다.
# 여기에 다시 적으면 chat.py 와 셋이 되어 반드시 어긋난다.

# score_id -> 생성된 요약. 분석이 갱신되면 키가 바뀌어 자연히 무효화된다.
#
# ⚠ 프로세스 내 캐시라 워커를 여러 개 띄우면 워커마다 한 번씩 생성된다.
#   데모 규모에서는 문제가 없지만, 확장한다면 요약을 EMOTION_RISK_SCORES 의
#   컬럼으로 저장하는 편이 맞다. 그때는 데이터베이스요구사항분석서·테이블명세서 개정이 함께 필요하다.
_SUMMARY_CACHE: dict[uuid.UUID, str | None] = {}
_SUMMARY_CACHE_MAX = 500


async def _cached_daily_summary(
    score_id: uuid.UUID,
    emotion_name: str,
    risk_level: str,
    sleep_min: int | None,
    steps: int | None,
) -> str | None:
    if score_id in _SUMMARY_CACHE:
        return _SUMMARY_CACHE[score_id]

    text = await llm.daily_summary(emotion_name, risk_level, sleep_min, steps)

    # 무한히 자라지 않게 오래된 것부터 버린다(dict 는 삽입 순서를 유지한다).
    if len(_SUMMARY_CACHE) >= _SUMMARY_CACHE_MAX:
        for key in list(_SUMMARY_CACHE)[: _SUMMARY_CACHE_MAX // 2]:
            del _SUMMARY_CACHE[key]

    _SUMMARY_CACHE[score_id] = text
    return text


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


class PendingOutreach(BaseModel):
    """시스템이 먼저 건 대화 중 **아직 답하지 않은 것** — MLCM_220 6단계.

    앱은 자기가 시작한 대화만 알고 있어서, 이 필드가 없으면 선제 접촉이
    대화 기록 안에 묻힌다. 홈은 앱을 열 때마다 부르므로 호출이 늘지 않는다.
    """

    session_id: uuid.UUID
    persona_type: str
    opener: str
    started_at: datetime


class HomeOut(BaseModel):
    emotion_today: EmotionToday | None
    lifelog_summary: LifelogSummary
    ai_summary: str | None
    recommendations: list[ContentCard]
    action: Literal["CHAT", "CONTENT", "EMERGENCY"]
    pending_outreach: PendingOutreach | None = None


async def _pick_healing_contents(
    db: AsyncSession, emotion_id: uuid.UUID, limit: int
) -> list[HealingContent]:
    """감정 코드로 필터링한 힐링 콘텐츠 중 무작위로 limit 개 선정.

    ⚠ ORDER BY 없이 LIMIT 만 쓰면 매번 같은 콘텐츠만 나온다. 감정 하나당
    콘텐츠가 5개보다 많으면(지금 6개) 나머지는 영원히 노출되지 않는다 —
    빅데이터분석정의서 "데이터 분석 시나리오"가 규정한 "무작위/순환 방식"이 이 자리다.
    """
    return list(
        await db.scalars(
            select(HealingContent)
            .where(HealingContent.emotion_id == emotion_id)
            .order_by(func.random())
            .limit(limit)
        )
    )


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

    action = risk_policy.action_for(risk_level)

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
    if action == "CONTENT" and emotion_today and row:
        # MLCM_400 — CAUTION 단계에서만 추천한다.
        # 등록되는 콘텐츠는 사전 안전 검수를 거친 중립적인 것만이므로
        # 감정 매칭이 빗나가도 사용자에게 해가 되지 않는다(데이터베이스요구사항분석서 7항).
        cards = await _pick_healing_contents(db, row[1].emotion_id, 5)
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

    # MAIN_HOME_01 ❸ — LLM 기반 일일 감정 종합 리포트.
    #
    # 홈은 앱을 열 때마다 호출된다. 매번 OpenAI 를 부르면 비용과 지연이 그대로
    # 쌓이므로, 같은 분석 결과에 대해서는 한 번만 생성하고 재사용한다.
    # 분석이 갱신되면(score_id 가 바뀌면) 자동으로 다시 생성된다.
    ai_summary = None
    if emotion_today and row:
        ai_summary = await _cached_daily_summary(
            row[0].score_id,
            emotion_today.emotion_name,
            emotion_today.risk_level,
            summary.total_sleep_min,
            summary.steps,
        )

    # MLCM_220 6단계 — 선제 접촉 세션 중 사용자가 아직 답하지 않은 것.
    #
    # ⚠ **사용자가 한 마디라도 했으면 빼야 한다.** 대화를 이어가는 중인데
    #   홈에 「먼저 말을 걸었어요」가 계속 떠 있으면 안 읽은 알림처럼 보인다.
    pending = None
    pending_row = (
        await db.execute(
            select(ChatSession)
            .join(OutreachLog, OutreachLog.session_id == ChatSession.session_id)
            .where(
                ChatSession.user_id == user.user_id,
                ChatSession.ended_at.is_(None),
            )
            .order_by(ChatSession.started_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if pending_row is not None:
        msgs = list(pending_row.messages or [])
        if msgs and not any(m.get("role") == "user" for m in msgs):
            pending = PendingOutreach(
                session_id=pending_row.session_id,
                persona_type=pending_row.persona_type,
                opener=msgs[0].get("content", ""),
                started_at=pending_row.started_at,
            )

    return HomeOut(
        emotion_today=emotion_today,
        lifelog_summary=summary,
        ai_summary=ai_summary,
        recommendations=recommendations,
        action=action,
        pending_outreach=pending,
    )


@router.get("/contents/recommendations", response_model=list[ContentCard])
async def recommendations(
    user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
):
    """콘텐츠 추천 새로고침 — MLCM_400

    홈 응답에 이미 포함되므로 **평소 화면 진입에는 쓰이지 않는다.** 다시
    뽑아보는 동작을 위해 분리해 두었다.

    ⚠ **2026.08.03 현재 이 엔드포인트를 호출하는 클라이언트가 없다.**
      앱에 새로고침 UI 가 아직 없기 때문이다(→ `docs/진행/구현_갭.md`
      갭 7). 없앨 것이 아니라 UI 를 붙일 자리이므로 남겨두되, **여기 있다는
      이유로 「구현됐다」고 세지 말 것.**

    ⚠ **CRITICAL 이면 빈 목록을 돌려준다** — MLCM_510 2단계(콘텐츠 추천 즉시
      중단). `/home` 에만 이 가드를 두면, 이 엔드포인트를 직접 부르는 것만으로
      위기 상태 사용자에게 추천이 나간다. **판정은 서버가 확정한다**는 원칙이
      여기에도 걸린다(API설계_사전결정 3절).
    """
    row = (
        await db.execute(
            select(EmotionRiskScore.emotion_id, EmotionRiskScore.risk_level)
            .where(EmotionRiskScore.user_id == user.user_id)
            .order_by(EmotionRiskScore.evaluated_at.desc())
            .limit(1)
        )
    ).first()
    if row is None:
        return []

    emotion_id, risk_level = row
    if risk_policy.is_emergency(risk_level):
        return []

    cards = await _pick_healing_contents(db, emotion_id, limit)
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
