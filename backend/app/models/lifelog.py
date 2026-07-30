"""LIFELOG_METRICS · BODY_COMPOSITION_METRICS"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LifelogMetric(Base):
    """앱이 push 한 시계열 라이프로그.

    (user_id, collected_at) UNIQUE 로 재전송 시 중복 적재를 막는다.
    적재는 항상 UPSERT 로 한다 — MLCM_200 5단계.
    """

    __tablename__ = "lifelog_metrics"

    metric_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )

    steps: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    distance: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    calories: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))

    # [05-E] 활동 시각 3컬럼
    activity_start_at: Mapped[datetime | None] = mapped_column()
    activity_end_at: Mapped[datetime | None] = mapped_column()
    total_active_min: Mapped[int | None] = mapped_column(Integer)

    sleep_start_at: Mapped[datetime | None] = mapped_column()
    sleep_end_at: Mapped[datetime | None] = mapped_column()
    total_sleep_min: Mapped[int | None] = mapped_column(Integer)
    deep_sleep_min: Mapped[int | None] = mapped_column(Integer)
    light_sleep_min: Mapped[int | None] = mapped_column(Integer)
    rem_sleep_min: Mapped[int | None] = mapped_column(Integer)
    awake_min: Mapped[int | None] = mapped_column(Integer)
    sleep_onset_min: Mapped[int | None] = mapped_column(Integer)
    sleep_efficiency_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    heart_rate: Mapped[int | None] = mapped_column(Integer)
    hrv: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    collected_at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "collected_at", name="uq_lifelog_user_collected"),
        # 04 문서 5항이 요구하는 복합 인덱스. 컬럼 암호화를 포기한 근거이기도 하다.
        Index("idx_lifelog_user_collected", "user_id", text("collected_at DESC")),
        CheckConstraint("steps >= 0", name="ck_lifelog_steps"),
        CheckConstraint(
            "sleep_efficiency_pct BETWEEN 0 AND 100", name="ck_lifelog_sleep_eff"
        ),
    )


class BodyCompositionMetric(Base):
    """체성분. 측정 시점에만 발생하므로 라이프로그와 주기가 다르다."""

    __tablename__ = "body_composition_metrics"

    body_metric_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )

    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    body_water_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    body_fat_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    muscle_mass_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    muscle_mass_min_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    muscle_mass_max_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    skeletal_muscle_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    bmr_kcal: Mapped[int | None] = mapped_column(Integer)

    measured_at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        Index("idx_body_user_measured", "user_id", text("measured_at DESC")),
    )
