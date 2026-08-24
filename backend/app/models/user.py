"""USERS · DEVICE_HEALTH_CONNECTIONS"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampTZ


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # [05-B] AES-256-GCM 암호문(Base64)을 담으므로 TEXT.
    # 암호화 컬럼이라 phone 기준 검색·정렬·중복확인은 불가능하다.
    phone: Mapped[str | None] = mapped_column(Text)

    birth_date: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(10))
    fcm_token: Mapped[str | None] = mapped_column(Text)

    # 알림 수신 동의 — [05-N]. 안전 알림과 콘텐츠 알림을 나눈다.
    #
    # ⚠ 하나로 묶으면 콘텐츠 알림이 귀찮아 끈 사람이 선제 접촉(MLCM_220)까지
    #   끈다. 알림을 끄는 사람일수록 앱을 안 여는 사람이다.
    care_alert_agreed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("TRUE")
    )
    content_alert_agreed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("TRUE")
    )
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    # [05-C] DEFAULT 가 없으면 회원가입 INSERT 가 실패한다.
    # 페르소나 선택은 로그인 이후 MLCM_300 에서 이루어지기 때문.
    persona_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'FRIEND'")
    )

    # [05-K] 민감정보 동의는 일반 약관 동의와 별도 항목으로 받는다.
    terms_agreed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    terms_agreed_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    sensitive_agreed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    sensitive_agreed_at: Mapped[datetime | None] = mapped_column(TimestampTZ)

    # [SD-E1] 관리자 판별 수단. MLCM_501 · FR-MN-003 이 관리자를 전제한다.
    # 관리자는 일반 가입 후 UPDATE 로 승격한다.
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'USER'")
    )

    __table_args__ = (
        CheckConstraint("gender IN ('MALE', 'FEMALE', 'OTHER')", name="ck_users_gender"),
        CheckConstraint("height_cm > 0", name="ck_users_height"),
        CheckConstraint(
            "persona_type IN ('FRIEND', 'COUNSELOR')", name="ck_users_persona"
        ),
        CheckConstraint("role IN ('USER', 'ADMIN')", name="ck_users_role"),
    )

    connections: Mapped[list["DeviceHealthConnection"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class DeviceHealthConnection(Base):
    __tablename__ = "device_health_connections"

    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    device_name: Mapped[str | None] = mapped_column(String(100))

    # APPLE_HEALTH 는 구현 범위 제외(안건 2)이나 enum 값은 유지한다.
    # 빼면 값이 하나뿐이라 컬럼의 존재 이유가 사라진다.
    platform_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # [05-A] Health Connect 는 Android on-device 권한 모델이라 서버가 보유할
    # OAuth 토큰이 없다. access_token 대신 권한 승인 상태를 기록한다.
    permission_granted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    agreed_at: Mapped[datetime] = mapped_column(TimestampTZ, nullable=False)

    # 앱이 이 시각 이후 신규분만 조회해 push 한다. 서버가 갱신해 응답으로 돌려준다.
    # 3시간 이상 미갱신이면 미수신으로 보고 FCM 무음 푸시를 발송한다(NFR-DV-002).
    last_synced_at: Mapped[datetime | None] = mapped_column(TimestampTZ)

    consent_scopes: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # [05-P] 미수신 감지 상태 — NFR-DV-002 (2026.08.24)
    #   OK           정상. 3시간 안에 들어오고 있다
    #   NUDGED       미수신을 감지해 FCM 무음 푸시를 보냈다
    #   RETRY_FAILED 푸시를 보냈는데도 안 들어왔다 → 관리자 알림 대상
    sync_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'OK'")
    )
    # NUDGED 로 바꾼 시각. 「푸시 후 얼마나 기다렸나」를 재는 기준이다.
    nudged_at: Mapped[datetime | None] = mapped_column(TimestampTZ)

    __table_args__ = (
        CheckConstraint(
            "platform_type IN ('HEALTH_CONNECT', 'APPLE_HEALTH')",
            name="ck_device_platform",
        ),
        CheckConstraint(
            "sync_status IN ('OK', 'NUDGED', 'RETRY_FAILED')",
            name="ck_device_sync_status",
        ),
    )

    user: Mapped["User"] = relationship(back_populates="connections")
