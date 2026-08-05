"""선제 접촉 — MLCM_220

개인 기준선 이탈이 **연속으로** 이어지면, 위험 단계와 무관하게 시스템이 먼저
말을 건다. 감지 결과가 사용자에게 도달하는 유일한 경로다 — 앱을 열지 않는
사람은 홈 화면의 콘텐츠 추천을 영영 보지 못한다.

⚠ **푸시 발송은 아직 없다.** Firebase 자격증명이 없어 FCM 경로가 비어 있다
  (구현_갭 갭 1). 그래도 **세션은 선생성한다** — `MLCM_220` 6단계가 「푸시
  발송이 실패해도 선생성된 세션은 유지되어, 다음 앱 실행 시 사용자가 확인할
  수 있다」를 규정한다. 발송 실패는 `OUTREACH_LOGS` 에 남는다.

⚠ **임계치는 임의값이다.** 연속 3일·쿨다운 3일·09~21시는 선행연구에서 가져온
  값이 아니다. 성능 근거로 쓰지 말 것.
"""

import logging
import uuid
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatSession, OutreachLog, User
from app.services import llm

logger = logging.getLogger(__name__)

STREAK_DAYS_REQUIRED = 3
COOLDOWN_DAYS = 3
ACTIVE_FROM, ACTIVE_TO = time(9, 0), time(21, 0)

# 서비스 대상이 국내라 고정한다. 사용자별 시간대를 받는 컬럼이 없다.
#
# ⚠ **`ZoneInfo("Asia/Seoul")` 을 쓰지 않는다.** 윈도우에는 IANA tz 데이터가
#   없어 `tzdata` 패키지를 따로 깔아야 하고, 안 깔린 PC 에서 임포트 시점에
#   죽는다. 한국은 서머타임이 없으므로 고정 오프셋이 정확하다.
KST = timezone(timedelta(hours=9))


async def maybe_outreach(
    db: AsyncSession, user_id: uuid.UUID, result: dict
) -> OutreachLog | None:
    """판정 직후 호출한다. 조건을 검사하고 접촉하거나 사유를 남긴다.

    보내지 않기로 한 것도 기록한다 — `MLCM_220` 5단계. 안 남기면 「왜 안
    왔지」에 답할 수 없다.

    조건을 하나라도 못 넘기면 `SKIPPED` 로 남기고 `None` 을 돌려준다.
    """
    streak = int(result.get("streak_days") or 0)
    features = list(result.get("deviant_features") or [])

    # ── 1. 이탈이 지속되고 있는가
    if streak < STREAK_DAYS_REQUIRED:
        return None  # 접촉 대상이 아니다. 로그를 남기면 매 판정마다 쌓인다.

    reason = await _blocking_reason(db, user_id, result)
    if reason:
        return await _log(db, user_id, None, streak, features, "SKIPPED", reason)

    # ── 2. 첫 발화를 만들고 세션을 선생성한다
    user = await db.get(User, user_id)
    persona = user.persona_type if user else "FRIEND"
    try:
        opener = await llm.outreach_opener(persona, features, streak)
    except Exception as e:
        # 말을 걸기로 판정된 사람에게 아무 말도 안 하는 것보다 낫다.
        logger.info("선제 접촉 발화 생성 실패 (user=%s): %s", user_id, e)
        opener = llm.FALLBACK_OUTREACH.get(persona, llm.FALLBACK_OUTREACH["FRIEND"])
    if not opener:
        opener = llm.FALLBACK_OUTREACH.get(persona, llm.FALLBACK_OUTREACH["FRIEND"])

    now = datetime.now(timezone.utc)
    session = ChatSession(
        user_id=user_id,
        persona_type=persona,
        # 사용자가 열면 이미 첫 마디가 있는 상태로 들어온다.
        messages=[{"role": "assistant", "content": opener, "at": now.isoformat()}],
        started_at=now,
    )
    db.add(session)
    await db.flush()

    # ── 3. FCM 이 없으므로 발송은 실패로 남긴다. 세션은 유지된다.
    return await _log(
        db, user_id, session.session_id, streak, features,
        "FAILED", "fcm_미구현",
    )


async def _blocking_reason(
    db: AsyncSession, user_id: uuid.UUID, result: dict
) -> str | None:
    """보내면 안 되는 사유. 없으면 None."""
    # CRITICAL 은 긴급 상담 연결(MLCM_510)이 이미 개입한다. 안부 인사를
    # 겹쳐 보내면 그쪽 흐름을 흐린다.
    if result.get("risk_level") == "CRITICAL":
        return "risk_critical"

    user = await db.get(User, user_id)
    if user is None:
        return "user_없음"
    if not user.care_alert_agreed:
        return "케어알림_미동의"

    now_kst = datetime.now(KST)
    if not (ACTIVE_FROM <= now_kst.time() <= ACTIVE_TO):
        return "발송시간_아님"

    last = await db.scalar(
        select(OutreachLog.sent_at)
        .where(OutreachLog.user_id == user_id)
        .order_by(OutreachLog.sent_at.desc())
        .limit(1)
    )
    if last is not None:
        elapsed = datetime.now(timezone.utc) - last
        if elapsed < timedelta(days=COOLDOWN_DAYS):
            # 하루 1회 제한은 쿨다운 3일에 포함된다 — 3일보다 짧은 간격은
            # 전부 여기서 걸린다.
            return "쿨다운_중"

    return None


async def _log(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID | None,
    streak: int,
    features: list[str],
    status: str,
    reason: str | None,
) -> OutreachLog:
    row = OutreachLog(
        user_id=user_id,
        session_id=session_id,
        streak_days=streak,
        deviant_features=features,
        delivery_status=status,
        skip_reason=reason,
        sent_at=datetime.now(timezone.utc),
    )
    db.add(row)
    await db.flush()
    logger.info(
        "선제 접촉 user=%s status=%s reason=%s streak=%d",
        user_id, status, reason, streak,
    )
    return row
