"""디바이스 연동 엔드포인트 — MLCM_110

화면: MAIN_JOIN_03 · MAIN_SETTING_01
명세: docs/결정/API명세_초안.md 3절
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.models import DeviceHealthConnection
from app.schemas.user import ConnectionCreate, ConnectionOut, ConnectionUpdate

router = APIRouter(prefix="/devices", tags=["devices"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/connections", response_model=ConnectionOut, status_code=status.HTTP_201_CREATED
)
async def create_connection(body: ConnectionCreate, user: CurrentUser, db: DbSession):
    """연동 등록 — MLCM_110 · MAIN_JOIN_03

    같은 플랫폼으로 다시 등록하면 새 행을 만들지 않고 기존 행을 갱신한다.
    앱이 권한을 재승인할 때마다 행이 쌓이면 last_synced_at 이 어느 행 기준인지
    알 수 없게 된다.
    """
    existing = await db.scalar(
        select(DeviceHealthConnection).where(
            DeviceHealthConnection.user_id == user.user_id,
            DeviceHealthConnection.platform_type == body.platform_type,
        )
    )

    if existing:
        existing.device_name = body.device_name
        existing.permission_granted = body.permission_granted
        existing.consent_scopes = body.consent_scopes.model_dump()
        existing.agreed_at = datetime.now(timezone.utc)
        conn = existing
    else:
        conn = DeviceHealthConnection(
            user_id=user.user_id,
            device_name=body.device_name,
            platform_type=body.platform_type,
            permission_granted=body.permission_granted,
            consent_scopes=body.consent_scopes.model_dump(),
            agreed_at=datetime.now(timezone.utc),
        )
        db.add(conn)

    await db.commit()
    await db.refresh(conn)
    return ConnectionOut.model_validate(conn)


@router.get("/connections", response_model=list[ConnectionOut])
async def list_connections(user: CurrentUser, db: DbSession):
    """연동 상태 조회 — MAIN_SETTING_01 ❶

    last_synced_at 이 함께 내려간다. 앱은 이 값을 다음 push 의 델타 기준으로,
    설정 화면은 최종 동기화 시각 표시로 쓴다.
    """
    rows = await db.scalars(
        select(DeviceHealthConnection).where(
            DeviceHealthConnection.user_id == user.user_id
        )
    )
    return [ConnectionOut.model_validate(r) for r in rows]


@router.patch("/connections/{connection_id}", response_model=ConnectionOut)
async def update_connection(
    connection_id: uuid.UUID, body: ConnectionUpdate, user: CurrentUser, db: DbSession
):
    """항목별 동의 철회·권한 갱신 — MLCM_110

    ⚠ 철회된 항목은 이후 수집 대상에서 제외되지만 **이미 수집된 데이터는
      삭제하지 않는다**(MLCM_110 종료조건). 완전 삭제는 회원 탈퇴로만 가능하다.
    """
    conn = await db.scalar(
        select(DeviceHealthConnection).where(
            DeviceHealthConnection.connection_id == connection_id,
            # 남의 연동을 건드리지 못하게 user_id 를 함께 건다.
            DeviceHealthConnection.user_id == user.user_id,
        )
    )
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="연동 정보를 찾을 수 없습니다"
        )

    data = body.model_dump(exclude_unset=True)
    if "permission_granted" in data:
        conn.permission_granted = data["permission_granted"]
    if "consent_scopes" in data and data["consent_scopes"] is not None:
        conn.consent_scopes = data["consent_scopes"]

    await db.commit()
    await db.refresh(conn)
    return ConnectionOut.model_validate(conn)
