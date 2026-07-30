"""CHAT_SESSIONS"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ChatSession(Base):
    """챗봇 대화 세션.

    messages 는 PII 를 [MASK] 로 치환한 뒤 저장한다. 마스킹은 저장 시점에
    서버가 수행하며 클라이언트는 원문을 그대로 보낸다(NFR-DE-002).

    session_summary 는 세션 종료 시 LLM 이 자동 생성한다(MLCM_310 종료조건).
    """

    __tablename__ = "chat_sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    persona_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'FRIEND'")
    )
    messages: Mapped[list] = mapped_column(JSONB, nullable=False)
    session_summary: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column()

    __table_args__ = (
        CheckConstraint(
            "persona_type IN ('FRIEND', 'COUNSELOR')", name="ck_chat_persona"
        ),
        Index("idx_chat_user_started", "user_id", text("started_at DESC")),
    )
