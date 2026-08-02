"""챗봇 엔드포인트 — MLCM_300 · MLCM_310 · MLCM_320

화면: MAIN_CHAT_01 · MAIN_CHAT_02
명세: docs/결정/API명세_초안.md 5절
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.models import ChatSession
from app.schemas.chat import (
    MessageIn,
    MessageOut,
    RiskInfo,
    SessionCreate,
    SessionDetail,
    SessionOut,
    SessionStarted,
)
from app.services import llm, safety

router = APIRouter(prefix="/chat", tags=["chat"])

DbSession = Annotated[AsyncSession, Depends(get_db)]

GREETING = {
    "FRIEND": "안녕하세요. 오늘 하루는 어떠셨어요? 어떤 마음이든 편하게 이야기해 주세요.",
    "COUNSELOR": "안녕하세요. 요즘 어떤 일로 마음이 무거우신지 편하게 말씀해 주세요.",
}


async def _load_session(session_id: uuid.UUID, user, db) -> ChatSession:
    """세션 조회. user_id 를 함께 걸어 타인 세션 접근을 막는다."""
    s = await db.scalar(
        select(ChatSession).where(
            ChatSession.session_id == session_id,
            ChatSession.user_id == user.user_id,
        )
    )
    if s is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다"
        )
    return s


def _decide(keyword: dict, verdict) -> RiskInfo:
    """감정→위험도→액션 매핑. **서버가 확정한다.**

    클라이언트에 규칙을 복제하면 반드시 어긋난다(API설계_사전결정 3절).

    LLM 판정이 없는 경우(API 장애)에는 키워드 결과만으로 판단하며,
    문맥을 볼 수 없으므로 미탐을 줄이는 보수적 임계치를 적용한다.
    HIGH 키워드가 하나라도 걸리면 문맥 판단 없이 CRITICAL 로 본다 — NFR-DV-003.
    """
    if verdict is None:
        if keyword["level"] == "HIGH":
            return RiskInfo(level="CRITICAL", action="EMERGENCY", source="KEYWORD")
        if keyword["level"] == "MEDIUM":
            return RiskInfo(level="CAUTION", action="CONTENT", source="KEYWORD")
        return RiskInfo(level="NORMAL", action="CHAT", source="KEYWORD")

    # ⚠ severity 는 LLM 이 채우는 자유 문자열이다. 스키마에 enum 이 걸려 있지
    #   않아 "High"·"high" 로 와도 파싱은 통과한다. 그대로 비교하면 HIGH 판정이
    #   조용히 NORMAL 로 떨어진다 — 안전 경로라 여기서 정규화한다.
    severity = (verdict.severity or "").strip().upper()

    if verdict.is_crisis or severity == "HIGH":
        return RiskInfo(level="CRITICAL", action="EMERGENCY", source="LLM")
    if severity == "MEDIUM" or keyword["level"] != "NONE":
        return RiskInfo(level="CAUTION", action="CONTENT", source="LLM")
    return RiskInfo(level="NORMAL", action="CHAT", source="LLM")


@router.post("/sessions", response_model=SessionStarted, status_code=status.HTTP_201_CREATED)
async def start_session(body: SessionCreate, user: CurrentUser, db: DbSession):
    """세션 시작 — MLCM_300 · MAIN_CHAT_01

    인사말을 서버가 내려준다. 클라이언트가 하드코딩하면 페르소나별 톤이 어긋난다.
    """
    persona = body.persona_type or user.persona_type
    s = ChatSession(
        user_id=user.user_id,
        persona_type=persona,
        messages=[],
        started_at=datetime.now(timezone.utc),
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return SessionStarted(
        session_id=s.session_id,
        persona_type=persona,
        greeting=GREETING[persona],
        started_at=s.started_at,
    )


@router.post("/sessions/{session_id}/messages", response_model=MessageOut)
async def send_message(
    session_id: uuid.UUID, body: MessageIn, user: CurrentUser, db: DbSession
):
    """대화 — MLCM_310 · MLCM_320

    1차 키워드 필터를 로컬에서 먼저 돌리고, 2차 LLM 문맥 분석과 응답 생성을
    **병렬로** 호출한다(NFR-DV-001 3초 요건).

    CRITICAL 이면 생성된 일반 응답을 버리고 EMERGENCY 만 내린다. 스트리밍을
    쓰지 않는 이유가 이것이다 — 판정 전에 흘린 글자는 회수할 수 없다.
    """
    s = await _load_session(session_id, user, db)
    if s.ended_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="이미 종료된 세션입니다"
        )

    # 저장·LLM 전송 모두 마스킹된 텍스트를 쓴다(NFR-DE-002).
    masked = safety.mask_pii(body.content)
    keyword = safety.keyword_scan(masked)
    history = list(s.messages or [])

    try:
        reply, verdict = await llm.analyze_and_reply(s.persona_type, masked, history)
    except RuntimeError:
        # OPENAI_API_KEY 미설정 등 호출 자체가 불가능한 경우.
        # 키워드 필터는 백엔드 내부 로직이라 계속 동작한다.
        reply, verdict = None, None

    risk = _decide(keyword, verdict)

    if risk.action == "EMERGENCY":
        # MLCM_510 2단계 — 콘텐츠 추천과 일반 응답을 중단한다.
        reply = None
    elif reply is None:
        reply = llm.FALLBACK_REPLY.get(s.persona_type, llm.FALLBACK_REPLY["FRIEND"])

    now = datetime.now(timezone.utc)
    history.append({"role": "user", "content": masked, "at": now.isoformat()})
    if reply:
        history.append({"role": "assistant", "content": reply, "at": now.isoformat()})
    # JSONB 는 재할당해야 변경이 감지된다.
    s.messages = history
    await db.commit()

    return MessageOut(reply=reply, risk=risk)


@router.patch("/sessions/{session_id}/end", response_model=SessionDetail)
async def end_session(session_id: uuid.UUID, user: CurrentUser, db: DbSession):
    """세션 종료 — MLCM_310 종료조건. 요약을 자동 생성한다."""
    s = await _load_session(session_id, user, db)
    if s.ended_at is None:
        s.ended_at = datetime.now(timezone.utc)
        s.session_summary = await llm.summarize_session(list(s.messages or []))
        await db.commit()
        await db.refresh(s)
    return SessionDetail.model_validate(s)


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(
    user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """대화 기록 목록 — MAIN_CHAT_02 ❹. 본문은 제외하고 요약만 내린다."""
    rows = await db.scalars(
        select(ChatSession)
        .where(ChatSession.user_id == user.user_id)
        .order_by(ChatSession.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [SessionOut.model_validate(r) for r in rows]


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(session_id: uuid.UUID, user: CurrentUser, db: DbSession):
    """상세 — MAIN_CHAT_02 ❺. messages 는 마스킹된 상태로 저장돼 있다."""
    return SessionDetail.model_validate(await _load_session(session_id, user, db))


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: uuid.UUID, user: CurrentUser, db: DbSession):
    """삭제 — MAIN_CHAT_02 ❻"""
    s = await _load_session(session_id, user, db)
    await db.delete(s)
    await db.commit()
    return None
