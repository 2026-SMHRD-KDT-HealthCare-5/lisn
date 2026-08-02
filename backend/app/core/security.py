"""비밀번호 해시 · JWT 발급/검증 · 인증 의존성.

설계 근거는 docs/결정/API설계_사전결정.md 1절.

- access token 단일. refresh token 을 두지 않는다.
- 로그아웃은 클라이언트가 토큰을 폐기하는 것으로 처리하고
  서버측 블랙리스트를 만들지 않는다. 블랙리스트를 만들면 그게 곧 세션
  테이블이라 stateless JWT 로 간 의미가 사라진다.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models import User

# 비밀번호 재설정 토큰이 access token 으로 쓰이는 것을 막기 위한 구분자
PURPOSE_ACCESS = "access"
PURPOSE_PASSWORD_RESET = "pwd_reset"

bearer_scheme = HTTPBearer(auto_error=False)


def _secret() -> str:
    """JWT 서명 키. 플레이스홀더면 **동작을 거부한다.**

    ⚠ `.env.example` 이 `JWT_SECRET=CHANGE_ME` 로 배포되고 **이 저장소는
      공개**다. 새 PC 에서 예제를 복사만 하고 값을 안 바꾸면 서명 키가
      공개된 상태로 서버가 뜬다. 그러면 누구나

          {"sub": <아무 uuid>, "role": "ADMIN", "purpose": "access"}

      를 직접 서명해 `/admin/*` 을 열 수 있다 — 전 사용자의 정서 리포트가
      그 뒤에 있다.

      조용히 도는 것보다 **못 뜨는 편이 낫다.** ENCRYPTION_KEY 도 같은 이유로
      `crypto._key()` 에서 막고 있다.
    """
    raw = settings.jwt_secret
    if not raw or raw == "CHANGE_ME":
        raise RuntimeError(
            "JWT_SECRET 이 설정되지 않았습니다. backend/.env 에 임의의 긴 문자열을 넣으세요. "
            'python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )
    return raw


# --------------------------------------------------------------------------
# 비밀번호
# --------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    """Bcrypt 단방향 해시. 평문은 어디에도 저장하지 않는다(04 문서 3항)."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        # 해시 형식이 깨진 경우. 인증 실패로 처리하고 예외를 밖으로 던지지 않는다.
        return False


# --------------------------------------------------------------------------
# 토큰
# --------------------------------------------------------------------------

def create_access_token(user_id: uuid.UUID, role: str) -> tuple[str, datetime]:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload = {
        "sub": str(user_id),
        "role": role,
        "purpose": PURPOSE_ACCESS,
        "exp": expires_at,
    }
    token = jwt.encode(payload, _secret(), algorithm=settings.jwt_algorithm)
    return token, expires_at


def create_password_reset_token(user_id: uuid.UUID) -> str:
    """비밀번호 재설정용 단기 토큰.

    별도 테이블을 두지 않는다. 수명이 30분이고 1회성 용도라
    저장할 가치보다 관리 비용이 크다.
    """
    payload = {
        "sub": str(user_id),
        "purpose": PURPOSE_PASSWORD_RESET,
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=settings.password_reset_expire_minutes),
    }
    return jwt.encode(payload, _secret(), algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_purpose: str) -> dict:
    try:
        payload = jwt.decode(
            token, _secret(), algorithms=[settings.jwt_algorithm]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="토큰이 만료되었습니다"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 토큰입니다"
        )

    if payload.get("purpose") != expected_purpose:
        # 재설정 토큰으로 일반 API 를 호출하는 것을 막는다.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="용도가 다른 토큰입니다"
        )
    return payload


# --------------------------------------------------------------------------
# 의존성
# --------------------------------------------------------------------------

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="인증이 필요합니다"
        )

    payload = decode_token(credentials.credentials, PURPOSE_ACCESS)
    user = await db.scalar(select(User).where(User.user_id == uuid.UUID(payload["sub"])))

    if user is None:
        # 토큰은 유효하나 계정이 삭제된 경우(회원 탈퇴 후 만료 전 토큰)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="존재하지 않는 계정입니다"
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> User:
    """관리자 전용 API 가드.

    별도 인증 체계를 만들지 않고 role 만 검사한다(SD-E1).
    토큰이 유효한데 권한이 없는 것이므로 401 이 아니라 403 이다.
    """
    if user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="관리자 권한이 필요합니다"
        )
    return user


AdminUser = Annotated[User, Depends(require_admin)]
