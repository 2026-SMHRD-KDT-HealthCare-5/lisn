"""인증 엔드포인트 — MLCM_100 · MLCM_101 · MLCM_102

화면: MAIN_LOGIN_01 · MAIN_LOGIN_02 · MAIN_JOIN_01 · MAIN_JOIN_02 · ADMIN_LOGIN_01
명세: docs/API명세_초안.md 1절
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import encrypt
from app.core.database import get_db
from app.core.security import (
    PURPOSE_PASSWORD_RESET,
    CurrentUser,
    create_access_token,
    create_password_reset_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import User
from app.schemas.auth import (
    EmailAvailability,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    SignupRequest,
    TokenResponse,
    UserPublic,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, db: DbSession):
    """회원가입 — MLCM_100 · MAIN_JOIN_01 · MAIN_JOIN_02"""

    # 필수 동의 2건. 05-K 로 민감정보 동의를 별도 항목으로 분리했다.
    if not body.terms_agreed or not body.sensitive_agreed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="서비스 이용약관과 민감정보 처리에 모두 동의해야 가입할 수 있습니다",
        )

    exists = await db.scalar(select(User.user_id).where(User.email == body.email))
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="이미 가입된 이메일입니다"
        )

    now = datetime.now(timezone.utc)
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        name=body.name,
        birth_date=body.birth_date,
        gender=body.gender,
        height_cm=body.height_cm,
        # 02-F (3) — 연락처는 AES-256-GCM 으로 암호화해 저장한다.
        phone=encrypt(body.phone),
        terms_agreed=True,
        terms_agreed_at=now,
        sensitive_agreed=True,
        sensitive_agreed_at=now,
        # persona_type · role 은 DB DEFAULT 에 맡긴다(FRIEND / USER).
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token, expires_at = create_access_token(user.user_id, user.role)
    return TokenResponse(
        access_token=token,
        expires_at=expires_at,
        user=UserPublic.model_validate(user),
    )


@router.get("/check-email", response_model=EmailAvailability)
async def check_email(email: str, db: DbSession):
    """이메일 중복 확인 — MAIN_JOIN_02 ❸"""
    exists = await db.scalar(select(User.user_id).where(User.email == email))
    return EmailAvailability(available=exists is None)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DbSession):
    """로그인 — MLCM_100 · MAIN_LOGIN_01 · ADMIN_LOGIN_01

    관리자 웹도 같은 엔드포인트를 쓴다. 응답의 role 이 ADMIN 이 아니면
    웹이 대시보드로 보내지 않는다. 인증 체계를 복제하지 않는다(SD-E1).
    """
    user = await db.scalar(select(User).where(User.email == body.email))

    # 계정 존재 여부와 비밀번호 오류를 구분하지 않는다.
    # 구분하면 이메일 존재 여부가 노출된다.
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호를 확인하세요",
        )

    token, expires_at = create_access_token(user.user_id, user.role)
    return TokenResponse(
        access_token=token,
        expires_at=expires_at,
        user=UserPublic.model_validate(user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(user: CurrentUser):
    """로그아웃 — MLCM_101

    서버는 아무것도 하지 않는다. 클라이언트가 토큰을 폐기한다.
    블랙리스트를 두지 않는 근거는 API설계_사전결정.md 1절 참고.
    토큰 유효성만 확인해 잘못된 호출을 걸러낸다.
    """
    return None


@router.post("/password-reset/request", response_model=MessageResponse)
async def request_password_reset(body: PasswordResetRequest, db: DbSession):
    """비밀번호 재설정 요청 — MLCM_102 · MAIN_LOGIN_02

    미가입 이메일이어도 동일한 200 을 반환하고 메일을 보내지 않는다.
    가입 여부가 노출되지 않도록 하는 MLCM_102 5단계 요건이다.
    """
    user = await db.scalar(select(User).where(User.email == body.email))

    if user is not None:
        token = create_password_reset_token(user.user_id)
        # TODO(메일): SMTP 미설정. 붙일 때까지 로그로 대체한다.
        #   운영에서는 이 로그를 반드시 제거할 것 — 토큰이 그대로 남는다.
        logger.info("[password-reset] %s token=%s", body.email, token)

    return MessageResponse(message="입력하신 주소로 재설정 안내를 보냈습니다")


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_password_reset(body: PasswordResetConfirm, db: DbSession):
    """새 비밀번호 확정 — MLCM_102"""
    payload = decode_token(body.token, PURPOSE_PASSWORD_RESET)

    user = await db.scalar(select(User).where(User.user_id == uuid.UUID(payload["sub"])))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="계정을 찾을 수 없습니다"
        )

    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return None
