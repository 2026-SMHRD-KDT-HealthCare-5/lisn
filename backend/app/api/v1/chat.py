"""챗봇 엔드포인트 — MLCM_300 · MLCM_310 · MLCM_320

화면: MAIN_CHAT_01 · MAIN_CHAT_02
명세: docs/결정/API명세_초안.md 5절
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.models import ChatSession, OutreachLog
from app.schemas.chat import (
    ActiveSession,
    MessageIn,
    MessageOut,
    RiskInfo,
    SessionCreate,
    SessionDetail,
    SessionOut,
    SessionStarted,
)
from app.services import llm, risk_policy, safety

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


def _risk(level: str, source: str) -> RiskInfo:
    """위험 단계와 판정 근거로 `RiskInfo` 를 만든다.

    ⚠ **액션을 손으로 적지 않는다.** 단계→액션 매핑은
      `services/risk_policy.py` 한 곳에 있다. 전에는 여기서 `action=` 을
      직접 채웠는데, `home.py` 에도 같은 표가 있어 규칙이 두 곳에 존재했다
      (→ `docs/진행/구현_갭.md` 중복 1).
    """
    return RiskInfo(level=level, action=risk_policy.RISK_ACTION[level], source=source)


def _decide(keyword: dict, verdict) -> RiskInfo:
    """대화 발화 → 위험 단계 판정 — `MLCM_320`.

    **판정 규칙 자체는 `risk_policy.level_for()` 에 있다.** 여기서는 그것을
    호출하고 판정 근거(`source`)를 붙일 뿐이다.

    규칙을 여기 두면 `llm.analyze_and_reply()` 가 「생성한 응답을 버리게
    될지」를 알 수 없어 조건을 따로 적게 된다. 실제로 그렇게 했다가
    **취소가 안 걸려 성능 개선이 통째로 무효**가 됐다
    (→ `docs/검증/성능실측_20260803_openai.md`).

    `source` 는 근거다. `KEYWORD` 면 외부 API 장애로 문맥 판단 없이 내린
    결과다 — 클라이언트가 이걸 보고 안내 문구를 달리할 수 있다.

    판정 근거와 임계치의 이유는 `risk_policy.level_for()` 주석에 있다.
    """
    if verdict is None:
        level = risk_policy.level_for(keyword["level"], None, None)
        return _risk(level, "KEYWORD")

    level = risk_policy.level_for(
        keyword["level"], verdict.is_crisis, verdict.severity
    )
    return _risk(level, "LLM")


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
        # ⚠ 키워드 결과를 함께 넘긴다. 응답을 버리게 될지가 LLM 판정만으로
        #   정해지지 않기 때문이다 — analyze_and_reply 주석 참조.
        reply, verdict = await llm.analyze_and_reply(
            s.persona_type, masked, history, keyword_level=keyword["level"]
        )
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
    """대화 기록 목록 — MAIN_CHAT_02 ❹. 본문은 제외하고 요약만 내린다.

    ⚠ **한 마디도 오가지 않은 세션은 빼고 내린다.**
      성격 카드를 눌렀다가 아무 말 없이 나오면 세션 행만 남는다. 요약할 내용이
      없어 `session_summary` 가 NULL 이라, 목록에 그대로 실으면 「요약을 만들지
      못했습니다」만 적힌 빈 줄이 쌓인다. 실제로 13건 중 12건이 그랬다
      (2026.08.03). 앱은 이제 그런 세션을 종료 대신 삭제하지만, 앱이 죽거나
      네트워크가 끊겨 삭제가 못 나간 경우가 남으므로 여기서도 막는다.
    """
    rows = await db.scalars(
        select(ChatSession)
        .where(
            ChatSession.user_id == user.user_id,
            func.jsonb_array_length(ChatSession.messages) > 0,
        )
        .order_by(ChatSession.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [SessionOut.model_validate(r) for r in rows]


@router.get("/sessions/active", response_model=ActiveSession | None)
async def active_session(user: CurrentUser, db: DbSession, response: Response):
    """열려 있는 대화 하나 — `MLCM_220` 6단계.

    **선제 접촉이 만든 세션을 앱이 발견하는 경로다.** 앱은 자기가 시작한
    대화만 알고 있어서, 서버가 먼저 만든 세션은 물어보지 않으면 못 찾는다.
    실제로 대화 기록을 뒤져야 발견되는 상태였다.

    ⚠ **`/sessions/{session_id}` 보다 먼저 선언해야 한다.** 뒤에 두면
      `active` 가 UUID 로 파싱되어 422 가 난다.

    없으면 204 다. 본문 없는 200 을 주면 클라이언트가 빈 객체와 구분하려고
    분기를 하나 더 만들게 된다.
    """
    s = await db.scalar(
        select(ChatSession)
        .where(ChatSession.user_id == user.user_id, ChatSession.ended_at.is_(None))
        .order_by(ChatSession.started_at.desc())
        .limit(1)
    )
    if s is None:
        response.status_code = status.HTTP_204_NO_CONTENT
        return None

    origin = await db.scalar(
        select(OutreachLog.outreach_id).where(OutreachLog.session_id == s.session_id)
    )
    return ActiveSession.model_validate(
        {**s.__dict__, "origin": "OUTREACH" if origin else "USER"}
    )


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
