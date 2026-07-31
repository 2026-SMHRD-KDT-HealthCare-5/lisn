"""관리자 관제 엔드포인트 — MLCM_501 · MLCM_510

화면: ADMIN_DASH_01
명세: docs/API명세_초안.md 7절

전부 role == ADMIN 이 필요하다. 별도 인증 체계를 만들지 않고 JWT 의 role
클레임만 검사한다(SD-E1). 토큰은 유효한데 권한이 없으면 401 이 아니라 403 이다.
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import AdminUser
from app.models import Emotion, EmotionRiskScore, User
from app.schemas.report import (
    AdminDashboard,
    AdminUserRow,
    EmergencyEvent,
    ReportOut,
    RiskDistribution,
)
from app.services.report import build_report

router = APIRouter(prefix="/admin", tags=["admin"])

DbSession = Annotated[AsyncSession, Depends(get_db)]

# 위험도 정렬 우선순위. 심각 -> 주의 -> 안정 순으로 보여야 한다(MLCM_501 3단계).
_RISK_ORDER = {"CRITICAL": 0, "CAUTION": 1, "NORMAL": 2}


def _latest_score_subq():
    """사용자별 최신 평가 1건만 남기는 서브쿼리.

    전체 행을 집계하면 자주 측정한 사용자가 분포를 왜곡한다.
    MLCM_501 2단계의 "전체 대상자의 risk_level 분포"는 사람 수 기준이다.
    """
    return (
        select(
            EmotionRiskScore.user_id,
            func.max(EmotionRiskScore.evaluated_at).label("latest"),
        )
        .group_by(EmotionRiskScore.user_id)
        .subquery()
    )


@router.get("/dashboard", response_model=AdminDashboard)
async def dashboard(admin: AdminUser, db: DbSession):
    """위험도 분포 요약 — MLCM_501 ❶"""
    sub = _latest_score_subq()
    rows = await db.execute(
        select(EmotionRiskScore.risk_level, func.count())
        .join(
            sub,
            (EmotionRiskScore.user_id == sub.c.user_id)
            & (EmotionRiskScore.evaluated_at == sub.c.latest),
        )
        .group_by(EmotionRiskScore.risk_level)
    )

    dist = RiskDistribution()
    evaluated = 0
    for level, count in rows:
        setattr(dist, level.lower(), count)
        evaluated += count

    total = await db.scalar(select(func.count()).select_from(User))

    return AdminDashboard(
        distribution=dist,
        total_users=total or 0,
        evaluated_users=evaluated,
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/users", response_model=list[AdminUserRow])
async def list_users(
    admin: AdminUser,
    db: DbSession,
    risk_level: Annotated[
        Literal["NORMAL", "CAUTION", "CRITICAL"] | None, Query()
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """대상자 목록 — MLCM_501 ❷

    아직 평가 이력이 없는 사용자도 포함한다(risk_level=null). 관리자 입장에서
    "분석된 적 없는 사람"도 관리 대상이다.
    """
    sub = _latest_score_subq()
    rows = await db.execute(
        select(User, EmotionRiskScore, Emotion)
        .outerjoin(
            sub, sub.c.user_id == User.user_id
        )
        .outerjoin(
            EmotionRiskScore,
            (EmotionRiskScore.user_id == sub.c.user_id)
            & (EmotionRiskScore.evaluated_at == sub.c.latest),
        )
        .outerjoin(Emotion, Emotion.emotion_id == EmotionRiskScore.emotion_id)
        .where(User.role == "USER")
    )

    out: list[AdminUserRow] = []
    for user, score, emotion in rows:
        if risk_level and (score is None or score.risk_level != risk_level):
            continue
        out.append(
            AdminUserRow(
                user_id=user.user_id,
                name=user.name,
                email=user.email,
                risk_level=score.risk_level if score else None,
                risk_score=score.risk_score if score else None,
                emotion_code=emotion.emotion_code if emotion else None,
                evaluated_at=score.evaluated_at if score else None,
            )
        )

    # 심각 -> 주의 -> 안정 -> 미평가, 같은 등급이면 최근 평가순.
    out.sort(
        key=lambda r: (
            _RISK_ORDER.get(r.risk_level, 3),
            -(r.evaluated_at.timestamp() if r.evaluated_at else 0),
        )
    )
    return out[offset : offset + limit]


@router.get("/users/{user_id}/report", response_model=ReportOut)
async def user_report(
    user_id: uuid.UUID,
    admin: AdminUser,
    db: DbSession,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
):
    """대상자 상세 — MLCM_501 ❸

    GET /reports 와 **같은 스키마**를 돌려준다. 대상 user_id 만 관리자가 지정한다.
    """
    exists = await db.scalar(select(User.user_id).where(User.user_id == user_id))
    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다"
        )
    return await build_report(db, user_id, date_from, date_to)


@router.get("/emergency-events", response_model=list[EmergencyEvent])
async def emergency_events(
    admin: AdminUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """위기 사건 이력 — MLCM_501 ❹ · MLCM_510 5단계

    EMOTION_RISK_SCORES 에서 risk_level='CRITICAL' 인 행을 조회한다.
    별도 테이블을 만들지 않는 이유는 그 행이 곧 판정 이력이기 때문이다.
    """
    rows = await db.execute(
        select(EmotionRiskScore, User, Emotion)
        .join(User, User.user_id == EmotionRiskScore.user_id)
        .join(Emotion, Emotion.emotion_id == EmotionRiskScore.emotion_id)
        .where(EmotionRiskScore.risk_level == "CRITICAL")
        .order_by(EmotionRiskScore.evaluated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [
        EmergencyEvent(
            score_id=s.score_id,
            user_id=s.user_id,
            name=u.name,
            emotion_code=e.emotion_code,
            emotion_score=s.emotion_score,
            risk_score=s.risk_score,
            model_version=s.model_version,
            evaluated_at=s.evaluated_at,
        )
        for s, u, e in rows
    ]
