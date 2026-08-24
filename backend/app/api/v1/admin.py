"""관리자 관제 엔드포인트 — MLCM_501 · MLCM_510

화면: ADMIN_DASH_01
명세: docs/결정/API명세_초안.md 7절

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
from app.models import DeviceHealthConnection, Emotion, EmotionRiskScore, User
from app.schemas.report import (
    AdminDashboard,
    AdminUserRow,
    EmergencyEvent,
    ReportOut,
    RiskDistribution,
    SyncFailure,
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

    # ⚠ 관리자 계정은 대상자가 아니다. 여기서 빼지 않으면 `/admin/users` 목록
    #   (role == "USER" 로 거른다)과 숫자가 안 맞아, 관리자 웹의
    #   「전체 N명 중 M명 평가 완료」가 자기 자신을 미평가자로 세게 된다.
    total = await db.scalar(
        select(func.count()).select_from(User).where(User.role == "USER")
    )

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
    q: Annotated[
        str | None,
        Query(
            max_length=100,
            description="이름·이메일 부분 일치 검색 (대소문자 무시)",
        ),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """대상자 목록 — MLCM_501 ❷

    아직 평가 이력이 없는 사용자도 포함한다(risk_level=null). 관리자 입장에서
    "분석된 적 없는 사람"도 관리 대상이다.

    `q` 는 이름·이메일 검색이다. 위험도 필터와 **AND** 로 걸린다 —
    "심각한 사람 중에서 김씨" 를 찾는 것이 관제에서 실제로 필요한 동작이다.

    ⚠ **연락처(phone)로는 검색할 수 없다.** AES-256-GCM 으로 컬럼 암호화돼 있어
      (02-F 3항) 같은 값이라도 암호문이 매번 달라 LIKE 가 성립하지 않는다.
      복호화해서 비교하려면 전 사용자를 메모리로 올려야 하므로 하지 않는다.
      검색 편의보다 저장 시점의 보호를 택한 결과다(안건 4).
    """
    sub = _latest_score_subq()
    stmt = (
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

    # 검색은 SQL 로 넘긴다. 아래 위험도 필터처럼 파이썬에서 거르면 전 사용자를
    # 메모리로 올린 뒤 버리게 된다.
    keyword = (q or "").strip()
    if keyword:
        # LIKE 메타문자를 이스케이프한다. 안 하면 '%' 한 글자가 전체 조회가 되고,
        # '_' 가 임의의 한 글자로 동작해 검색 결과가 조용히 틀어진다.
        escaped = (
            keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        pattern = f"%{escaped}%"
        stmt = stmt.where(
            User.name.ilike(pattern, escape="\\")
            | User.email.ilike(pattern, escape="\\")
        )

    rows = await db.execute(stmt)

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


@router.get("/sync-failures", response_model=list[SyncFailure])
async def sync_failures(
    admin: AdminUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """미수신 재시도 실패 목록 — NFR-DV-002 ④ 관리자 알림

    DEVICE_HEALTH_CONNECTIONS 에서 sync_status='RETRY_FAILED' 인 행을
    조회한다. 별도 알림 테이블을 만들지 않는 이유는 그 컬럼 자체가 곧
    알림 대상 목록이기 때문이다 — /emergency-events 가 EMOTION_RISK_SCORES
    를 그대로 쓰는 것과 같다.

    ⚠ **위기 판정과 섞지 않는다.** 미수신은 「데이터가 없다」이지
      「위험하다」가 아니다. 관제 대시보드의 위험도 분포에 이 사람들을
      넣으면 안 된다 — 미평가로 남아 있어야 관리자가 따로 확인한다.
    """
    rows = await db.execute(
        select(DeviceHealthConnection, User)
        .join(User, User.user_id == DeviceHealthConnection.user_id)
        .where(DeviceHealthConnection.sync_status == "RETRY_FAILED")
        .order_by(DeviceHealthConnection.nudged_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [
        SyncFailure(
            connection_id=c.connection_id,
            user_id=c.user_id,
            name=u.name,
            device_name=c.device_name,
            last_synced_at=c.last_synced_at,
            nudged_at=c.nudged_at,
        )
        for c, u in rows
    ]
