"""사용자 · 디바이스 연동 스키마"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class UserProfile(BaseModel):
    """GET /users/me — phone 은 복호화해서 내린다."""

    user_id: uuid.UUID
    email: EmailStr
    name: str
    phone: str | None = None
    birth_date: date | None = None
    gender: Literal["MALE", "FEMALE", "OTHER"] | None = None
    height_cm: Decimal | None = None
    persona_type: Literal["FRIEND", "COUNSELOR"]
    role: Literal["USER", "ADMIN"]
    terms_agreed_at: datetime | None = None
    sensitive_agreed_at: datetime | None = None


class UserUpdate(BaseModel):
    """PATCH /users/me — 보낸 필드만 반영한다."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    height_cm: Decimal | None = Field(default=None, gt=0, le=300)
    persona_type: Literal["FRIEND", "COUNSELOR"] | None = None
    fcm_token: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=64)


class AccountDelete(BaseModel):
    """회원 탈퇴 — MLCM_103 2단계 본인 확인"""

    password: str


# --------------------------------------------------------------------------
# 디바이스 연동
# --------------------------------------------------------------------------

class ConsentScopes(BaseModel):
    """MLCM_110 항목별 동의.

    activity·sleep 은 필수, body_composition 은 선택이다.
    필수를 false 로 내리는 것은 연동 해제와 같으므로 허용한다.
    """

    activity: bool = True
    sleep: bool = True
    body_composition: bool = False


class ConnectionCreate(BaseModel):
    device_name: str | None = Field(default=None, max_length=100)
    # APPLE_HEALTH 는 구현 범위 제외지만 enum 은 유지한다(안건 2).
    platform_type: Literal["HEALTH_CONNECT", "APPLE_HEALTH"] = "HEALTH_CONNECT"
    permission_granted: bool = False
    consent_scopes: ConsentScopes = ConsentScopes()


class ConnectionUpdate(BaseModel):
    """동의 철회·권한 상태 갱신. 기존 데이터는 삭제하지 않는다(MLCM_110 종료조건)."""

    permission_granted: bool | None = None
    consent_scopes: ConsentScopes | None = None


class ConnectionOut(BaseModel):
    connection_id: uuid.UUID
    device_name: str | None
    platform_type: str
    permission_granted: bool
    agreed_at: datetime
    last_synced_at: datetime | None
    consent_scopes: dict

    model_config = {"from_attributes": True}
