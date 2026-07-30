"""EMOTIONS · EMOTION_RISK_SCORES · HEALING_CONTENTS"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Emotion(Base):
    """감정 마스터 9종.

    category 가 곧 기본 위험도다(04 문서 6항).
    단, ANGER 만 emotion_score 70 을 기준으로 런타임에 동적 재분류되고
    CRISIS 는 점수와 무관하게 즉시 CRITICAL 로 확정된다.
    이 규칙은 AI 추론 서버가 적용하며 클라이언트에 복제하지 않는다.
    """

    __tablename__ = "emotions"

    emotion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    emotion_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    emotion_name: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "category IN ('NORMAL', 'CAUTION', 'CRITICAL')", name="ck_emotions_category"
        ),
    )


class EmotionRiskScore(Base):
    """AI 분석 결과.

    관리자 관제의 '위기 사건 이력'도 이 테이블에서 risk_level='CRITICAL' 로
    조회한다. MLCM_510 5단계가 요구하는 판정 이력이 여기 이미 있으므로
    별도 테이블을 만들지 않는다.
    """

    __tablename__ = "emotion_risk_scores"

    score_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    # EMOTIONS 는 RESTRICT — 참조가 남아 있으면 삭제를 막는다.
    emotion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emotions.emotion_id", ondelete="RESTRICT"),
        nullable=False,
    )

    emotion_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        CheckConstraint(
            "risk_level IN ('NORMAL', 'CAUTION', 'CRITICAL')", name="ck_risk_level"
        ),
        CheckConstraint("emotion_score BETWEEN 0 AND 100", name="ck_emotion_score"),
        CheckConstraint("risk_score BETWEEN 0 AND 100", name="ck_risk_score"),
        Index("idx_risk_user_evaluated", "user_id", text("evaluated_at DESC")),
    )


class HealingContent(Base):
    """CAUTION 단계 추천 콘텐츠.

    사전 안전 검수를 거친 중립적 콘텐츠만 등록한다. 감정 매칭이 틀려도
    사용자에게 해가 되지 않도록 하는 것이 원칙이다(04 문서 7항).
    """

    __tablename__ = "healing_contents"

    content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    emotion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emotions.emotion_id", ondelete="RESTRICT"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    external_url: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "category IN ('MUSIC', 'FOOD', 'EXERCISE', 'ARTICLE')",
            name="ck_content_category",
        ),
        Index("idx_healing_emotion", "emotion_id"),
    )
