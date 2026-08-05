"""챗봇 스키마 — MLCM_300 · MLCM_310 · MLCM_320"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    # 생략하면 USERS.persona_type 을 쓴다.
    persona_type: Literal["FRIEND", "COUNSELOR"] | None = None


class SessionStarted(BaseModel):
    session_id: uuid.UUID
    persona_type: str
    greeting: str
    started_at: datetime


class MessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class RiskInfo(BaseModel):
    """서버가 확정한 위험도와 액션.

    클라이언트는 action 을 그대로 따르기만 한다. 매핑 규칙을 복제하면
    서버와 어긋난다(API설계_사전결정 3절).
    """

    level: Literal["NORMAL", "CAUTION", "CRITICAL"]
    action: Literal["CHAT", "CONTENT", "EMERGENCY"]
    # 판정 근거. KEYWORD 면 OpenAI 장애로 문맥 판단 없이 내린 결과다.
    source: Literal["LLM", "KEYWORD"]


class MessageOut(BaseModel):
    # CRITICAL 이면 null. 병렬로 생성된 일반 응답을 서버가 버린다.
    reply: str | None
    risk: RiskInfo


class SessionOut(BaseModel):
    """목록용. 본문(messages)은 제외한다."""

    session_id: uuid.UUID
    persona_type: str
    session_summary: str | None
    started_at: datetime
    ended_at: datetime | None

    model_config = {"from_attributes": True}


class SessionDetail(SessionOut):
    messages: list

    model_config = {"from_attributes": True}


class ActiveSession(SessionDetail):
    """열려 있는 대화 하나 — `MLCM_220` 6단계.

    `origin` 이 `OUTREACH` 면 **시스템이 먼저 건 대화**다. 사용자가 시작한
    것과 화면에서 구분해야 한다 — 안 그러면 「내가 언제 이런 말을 했지」가
    된다.
    """

    origin: Literal["USER", "OUTREACH"]

    model_config = {"from_attributes": True}
