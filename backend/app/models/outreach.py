"""OUTREACH_LOGS — 선제 접촉 이력 (MLCM_220)"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, SmallInteger, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampTZ


class OutreachLog(Base):
    """선제 접촉을 보냈거나 보내지 않은 기록.

    ⚠ **이 테이블이 없으면 쿨다운을 지킬 수 없습니다.** `MLCM_220` 은
      「쿨다운 3일 · 하루 1회」를 조건으로 규정하는데, 언제 보냈는지 기록이
      없으면 이탈이 지속되는 동안 매일 발송됩니다. 알림이 부담이 되면 앱을
      닫는데, **그 사람이 우리가 놓치면 안 되는 쪽**입니다.

    ⚠ **보내지 않은 것(`SKIPPED`)도 남깁니다.** `MLCM_220` 5단계가 「조건
      미충족 시 발송하지 않고 사유를 로그에 기록한다」를 규정합니다. 안 보낸
      것을 안 남기면 「왜 안 왔지」에 답할 수 없습니다.

    `streak_days`·`deviant_features` 를 함께 남기는 이유 — 선제 접촉은
    「관찰된 변화를 근거로 먼저 말을 거는」 기능입니다. 무엇을 보고 걸었는지가
    없으면 나중에 검증도 개선도 못 합니다.

    ⚠ 정본은 `db/schema.sql` 이다. 이 모델은 그 DDL 의 파이썬 매핑일 뿐이고
      `create_all()` 을 쓰지 않는다. 컬럼을 여기만 고치면
      `tests/test_schema_drift.py` 가 잡는다.
    """

    __tablename__ = "outreach_logs"

    outreach_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    # ⚠ SET NULL 이다. 사용자가 대화를 지워도 **접촉 사실은 남아야** 쿨다운이
    #   유지된다. CASCADE 로 두면 대화를 지우는 것으로 쿨다운이 풀린다.
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.session_id", ondelete="SET NULL"),
    )
    streak_days: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    deviant_features: Mapped[list] = mapped_column(JSONB, nullable=False)
    delivery_status: Mapped[str] = mapped_column(String(20), nullable=False)
    skip_reason: Mapped[str | None] = mapped_column(String(40))
    sent_at: Mapped[datetime] = mapped_column(TimestampTZ, nullable=False)

    __table_args__ = (
        CheckConstraint("streak_days >= 0", name="ck_outreach_streak"),
        CheckConstraint(
            "delivery_status IN ('SENT', 'FAILED', 'SKIPPED')",
            name="ck_outreach_status",
        ),
        # 쿨다운 판정이 「이 사용자에게 마지막으로 보낸 게 언제인가」라
        # 매 판정마다 탄다.
        Index("idx_outreach_user_sent", "user_id", text("sent_at DESC")),
    )
