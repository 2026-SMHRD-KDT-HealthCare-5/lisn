"""인증 관련 요청·응답 스키마.

필드명은 snake_case 그대로 쓴다. 변환 계층을 두면 DB·API·문서 사이에
이름이 세 벌이 된다(docs/결정/API설계_사전결정.md 5절).
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import NewPassword


class SignupRequest(BaseModel):
    email: EmailStr
    password: NewPassword
    name: str = Field(min_length=1, max_length=100)
    birth_date: date | None = None
    gender: Literal["MALE", "FEMALE", "OTHER"] | None = None
    height_cm: Decimal | None = Field(default=None, gt=0, le=300)

    # 선택 입력. 저장 시 AES-256-GCM 으로 암호화한다(05-B).
    phone: str | None = Field(default=None, max_length=20)

    # 05-K — 민감정보 동의는 일반 약관과 별도 항목으로 받는다.
    # 둘 다 필수이므로 False 면 400 으로 막는다.
    terms_agreed: bool
    sensitive_agreed: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    user_id: uuid.UUID
    email: EmailStr
    name: str
    role: Literal["USER", "ADMIN"]
    persona_type: Literal["FRIEND", "COUNSELOR"]

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    expires_at: datetime
    user: UserPublic


class EmailAvailability(BaseModel):
    available: bool


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: NewPassword


class MessageResponse(BaseModel):
    message: str
