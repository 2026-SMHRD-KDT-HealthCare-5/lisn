"""챗봇 엔드포인트 — MLCM_300 · MLCM_310 · MLCM_320

화면: MAIN_CHAT_01 · MAIN_CHAT_02
명세: docs/결정/API명세_초안.md 5절
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
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
      (→ `docs/검증/구현_갭_20260803.md` 중복 1).
    """
    return RiskInfo(level=level, action=risk_policy.RISK_ACTION[level], source=source)


# `CrisisVerdict.severity` 가 가질 수 있는 값. 프롬프트가 지시하는 집합이다.
# 여기 없는 값이 오면 **모르는 것**이지 낮은 것이 아니다.
_SEVERITY = {"NONE", "LOW", "MEDIUM", "HIGH"}


def _decide(keyword: dict, verdict) -> RiskInfo:
    """대화 발화 → 위험 단계 판정 — `MLCM_320`.

    **여기서 정하는 것은 단계까지다.** 액션은 `risk_policy` 가 붙인다.
    클라이언트에 규칙을 복제하면 반드시 어긋난다(API설계_사전결정 3절).

    LLM 판정이 없는 경우(API 장애)에는 키워드 결과만으로 판단하며,
    문맥을 볼 수 없으므로 미탐을 줄이는 보수적 임계치를 적용한다.
    HIGH 키워드가 하나라도 걸리면 문맥 판단 없이 CRITICAL 로 본다 — NFR-DV-003.

    ---
    ## `is_crisis` 만으로 CRITICAL 을 내리지 않는다 (2026.08.03)

    `is_crisis` 는 **위기 신호가 있는가**이고 `severity` 는 **얼마나
    임박했는가**다. 전에는 `is_crisis` 하나로 CRITICAL 을 확정했는데, 그러면
    「뭘 해도 의미가 없어요」에 109 긴급 상담 화면이 뜬다. 무의미감·고립을
    탐지하는 것과 전화를 걸라고 하는 것은 다른 일이다.

    `MLCM_320` 도 둘을 갈라 놓았다 — 4단계는 "경미한 부정적 감정이
    감지되었으나 위험 임계치에는 미달하는 경우 → 주의 상태", 5단계는
    "**명확한 위기 문맥** 또는 위험 임계치 초과 → 고위험"이다.

    ⚠ **탐지 성능은 그대로다.** `NFR-AI-001` 평가는 `is_crisis or HIGH` 를
      양성으로 세고 이 함수를 거치지 않는다. 재현율을 유지하면서 과잉 개입만
      줄인다.

    ⚠ **강도를 모를 때는 낮추지 않는다.** 위기라고 하면서 `severity` 가
      규격 밖이면 CRITICAL 로 올린다. 안전 기능에서 「모름」을 「약함」으로
      취급하면 안 된다.

    ⚠ **HIGH 키워드는 LLM 이 위기라고 할 때만 CRITICAL 로 올린다.**
      「죽고 싶」이 들어갔다고 무조건 긴급 화면을 띄우면 안 된다. 평가셋
      200건 실측에서 **HIGH 키워드 정밀도가 0.500**(TP 10 / FP 10)이었다.
      「예전에 죽고 싶었는데 지금은 괜찮아요」·「친구가 죽고 싶대요」가
      전부 여기 걸린다. 문맥을 볼 수 있을 때는 **LLM 의 거부권을 살린다.**

      반대로 LLM 이 위기라고 하면, 강도가 MEDIUM 이어도 HIGH 키워드가
      함께 있으면 올린다. 명시적 표현 + 위기 확인이 겹친 상태다.

      LLM 이 **없을** 때는 문맥을 볼 수단이 없으므로 종전대로 HIGH 키워드
      단독으로 CRITICAL 이다(`NFR-DV-003`). 오탐을 감수하는 것은 문맥을
      볼 수 없을 때의 정책이다.
    """
    if verdict is None:
        if keyword["level"] == "HIGH":
            return _risk("CRITICAL", "KEYWORD")
        if keyword["level"] == "MEDIUM":
            return _risk("CAUTION", "KEYWORD")
        return _risk("NORMAL", "KEYWORD")

    # ⚠ severity 는 LLM 이 채우는 자유 문자열이다. 스키마에 enum 이 걸려 있지
    #   않아 "High"·"high" 로 와도 파싱은 통과한다. 그대로 비교하면 HIGH 판정이
    #   조용히 NORMAL 로 떨어진다 — 안전 경로라 여기서 정규화한다.
    severity = (verdict.severity or "").strip().upper()

    # 강도가 HIGH 면 is_crisis 와 무관하게 올린다. 둘이 어긋나면 높은 쪽을 따른다.
    if severity == "HIGH":
        return _risk("CRITICAL", "LLM")

    if verdict.is_crisis:
        # 위기다. 얼마나 임박했는가로 개입 강도를 정한다.
        if keyword["level"] == "HIGH" or severity not in _SEVERITY:
            return _risk("CRITICAL", "LLM")
        return _risk("CAUTION", "LLM")

    # LLM 이 위기가 아니라고 보았다. 키워드 단독으로 긴급 화면을 띄우지 않는다.
    if severity == "MEDIUM" or keyword["level"] != "NONE":
        return _risk("CAUTION", "LLM")
    return _risk("NORMAL", "LLM")


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
