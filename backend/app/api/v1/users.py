"""사용자 엔드포인트 — MLCM_103 · MLCM_300

화면: MAIN_SETTING_01 · MAIN_SETTING_02
명세: docs/결정/API명세_초안.md 2절
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt, encrypt
from app.core.database import get_db
from app.core.security import CurrentUser, hash_password, verify_password
from app.schemas.user import (
    AccountDelete,
    NotificationSettings,
    NotificationSettingsOut,
    PasswordChange,
    UserProfile,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["users"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


def _to_profile(user) -> UserProfile:
    """phone 은 저장 시 암호화돼 있으므로 응답에서 복호화한다."""
    return UserProfile(
        user_id=user.user_id,
        email=user.email,
        name=user.name,
        phone=decrypt(user.phone),
        birth_date=user.birth_date,
        gender=user.gender,
        height_cm=user.height_cm,
        persona_type=user.persona_type,
        role=user.role,
        terms_agreed_at=user.terms_agreed_at,
        sensitive_agreed_at=user.sensitive_agreed_at,
    )


@router.get("/me", response_model=UserProfile)
async def get_me(user: CurrentUser):
    return _to_profile(user)


@router.patch("/me", response_model=UserProfile)
async def update_me(body: UserUpdate, user: CurrentUser, db: DbSession):
    """프로필 수정 — 페르소나 변경(MLCM_300)과 FCM 토큰 갱신을 겸한다.

    보낸 필드만 반영한다. exclude_unset 을 쓰지 않으면 None 으로 덮어써서
    "안 보낸 것"과 "비우려는 것"을 구분할 수 없다.
    """
    data = body.model_dump(exclude_unset=True)

    if "phone" in data:
        data["phone"] = encrypt(data["phone"])

    for field, value in data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return _to_profile(user)


@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(body: PasswordChange, user: CurrentUser, db: DbSession):
    """비밀번호 변경 — MAIN_SETTING_02 ❷"""
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 일치하지 않습니다",
        )
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return None


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(body: AccountDelete, user: CurrentUser, db: DbSession):
    """회원 탈퇴 — MLCM_103 · MAIN_SETTING_02

    USERS 행을 지우면 CASCADE 로 LIFELOG_METRICS · BODY_COMPOSITION_METRICS ·
    CHAT_SESSIONS · EMOTION_RISK_SCORES · DEVICE_HEALTH_CONNECTIONS 가 함께
    삭제된다. 삭제 범위 안내는 클라이언트가 화면에서 보여준다(MLCM_103 3단계).
    """
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비밀번호가 일치하지 않습니다",
        )
    await db.delete(user)
    await db.commit()
    return None


@router.get("/me/notifications", response_model=NotificationSettingsOut)
async def get_notifications(user: CurrentUser):
    """알림 설정 조회 — `MAIN_SETTING_01` ❷"""
    return NotificationSettingsOut(
        care_alert_agreed=user.care_alert_agreed,
        content_alert_agreed=user.content_alert_agreed,
        fcm_token_registered=bool(user.fcm_token),
    )


@router.patch("/me/notifications", response_model=NotificationSettingsOut)
async def update_notifications(
    body: NotificationSettings, user: CurrentUser, db: DbSession
):
    """알림 설정 저장 — `MAIN_SETTING_01` ❷ · `MLCM_400` 5단계

    보낸 필드만 반영한다. 토글 하나를 껐다고 다른 하나까지 건드리면 안 된다.

    ⚠ **`MLCM_400` 5단계가 "알림 수신 동의 상태인 경우"를 전제**하는데
      그 상태를 담을 곳이 없었다. 화면은 토글을 그려놓고 「알림 기능은
      준비 중이에요」를 띄우고 있었다(구현 갭 2).

    ⚠ **토큰을 지우려면 빈 문자열을 보낸다.** null 은 「안 바꿈」이라
      로그아웃 시 토큰을 비울 방법이 없어진다.
    """
    if body.care_alert_agreed is not None:
        user.care_alert_agreed = body.care_alert_agreed
    if body.content_alert_agreed is not None:
        user.content_alert_agreed = body.content_alert_agreed
    if body.fcm_token is not None:
        user.fcm_token = body.fcm_token or None

    await db.commit()
    await db.refresh(user)
    return NotificationSettingsOut(
        care_alert_agreed=user.care_alert_agreed,
        content_alert_agreed=user.content_alert_agreed,
        fcm_token_registered=bool(user.fcm_token),
    )
