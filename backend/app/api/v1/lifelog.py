"""라이프로그 엔드포인트 — MLCM_200

화면: MAIN_LIFELOG_01 (조회) · 수집은 앱 백그라운드
명세: docs/API명세_초안.md 4절

수집 구조는 **앱 push** 다(안건 1-1). Health Connect 는 Android on-device
권한 모델이라 서버가 보유할 OAuth 토큰이 없고, 서버가 단말 데이터를 당겨올
수 없다. 앱이 last_synced_at 이후 신규분만 조회해 여기로 보낸다.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.models import BodyCompositionMetric, DeviceHealthConnection, LifelogMetric
from app.services.analysis import trigger_lifelog_analysis
from app.schemas.lifelog import (
    MAX_BATCH,
    BodyCompositionIn,
    BodyCompositionOut,
    LifelogBatch,
    LifelogBatchResult,
    LifelogOut,
)

router = APIRouter(tags=["lifelog"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/lifelog/batch", response_model=LifelogBatchResult)
async def push_lifelog(
    body: LifelogBatch, background: BackgroundTasks, user: CurrentUser, db: DbSession
):
    """앱 push 수신 — MLCM_200 4·5단계

    (user_id, collected_at) UNIQUE 기준 UPSERT 로 적재한다. 전송 실패 후
    재시도로 같은 시각이 다시 와도 중복 행이 생기지 않는다.
    """
    if len(body.items) > MAX_BATCH:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"한 번에 최대 {MAX_BATCH}건까지 전송할 수 있습니다 (요청 {len(body.items)}건)",
        )

    rows = [{"user_id": user.user_id, **item.model_dump()} for item in body.items]

    stmt = pg_insert(LifelogMetric).values(rows)
    # 갱신 대상에서 키 컬럼은 제외한다.
    updatable = {
        c.name: stmt.excluded[c.name]
        for c in LifelogMetric.__table__.columns
        if c.name not in ("metric_id", "user_id", "collected_at")
    }
    stmt = stmt.on_conflict_do_update(
        constraint="uq_lifelog_user_collected", set_=updatable
    )
    await db.execute(stmt)

    # 수신 시각을 서버가 확정한다. 앱 시계를 신뢰하지 않는다.
    now = datetime.now(timezone.utc)
    conn = await db.scalar(
        select(DeviceHealthConnection).where(
            DeviceHealthConnection.user_id == user.user_id
        )
    )
    if conn is not None:
        conn.last_synced_at = now

    await db.commit()

    # MLCM_210 — 적재 완료 후 분석을 트리거한다.
    # 백그라운드로 돌린다. 동기로 하면 AI 추론이 끝날 때까지 앱이 대기하는데,
    # 앱은 결과가 아니라 "수신됐다"만 알면 된다.
    background.add_task(trigger_lifelog_analysis, user.user_id)

    return LifelogBatchResult(accepted=len(rows), last_synced_at=now)


@router.get("/lifelog", response_model=list[LifelogOut])
async def list_lifelog(
    user: CurrentUser,
    db: DbSession,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """기간별 조회 — MAIN_LIFELOG_01

    시계열은 항상 최신순 고정이다. 정렬 파라미터를 열면
    (user_id, collected_at DESC) 복합 인덱스와 어긋난다.
    """
    q = select(LifelogMetric).where(LifelogMetric.user_id == user.user_id)
    if date_from:
        q = q.where(LifelogMetric.collected_at >= date_from)
    if date_to:
        q = q.where(LifelogMetric.collected_at <= date_to)

    q = q.order_by(LifelogMetric.collected_at.desc()).limit(limit).offset(offset)
    rows = await db.scalars(q)
    return [LifelogOut.model_validate(r) for r in rows]


@router.post(
    "/body-composition",
    response_model=BodyCompositionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_body_composition(
    body: BodyCompositionIn, user: CurrentUser, db: DbSession
):
    """체성분 기록.

    측정 시점에만 발생해 라이프로그와 주기가 다르므로 별도 테이블·엔드포인트다.
    15분 주기 배치에 섞으면 빈 값이 대부분인 행이 쌓인다.
    """
    row = BodyCompositionMetric(user_id=user.user_id, **body.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return BodyCompositionOut.model_validate(row)


@router.get("/body-composition", response_model=list[BodyCompositionOut])
async def list_body_composition(
    user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    q = (
        select(BodyCompositionMetric)
        .where(BodyCompositionMetric.user_id == user.user_id)
        .order_by(BodyCompositionMetric.measured_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = await db.scalars(q)
    return [BodyCompositionOut.model_validate(r) for r in rows]
