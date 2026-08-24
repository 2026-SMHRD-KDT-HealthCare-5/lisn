"""라이프로그 미수신 감지 — NFR-DV-002 (구현_갭 갭3, 2026.08.24 해소)

요구사항 원문이 네 단계를 규정한다.

  ① `last_synced_at` 이 **3시간 이상** 갱신되지 않은 사용자를 미수신으로 감지
  ② **FCM 무음 푸시**로 동기화를 유도
  ③ 이후에도 수신되지 않으면 연동 상태를 **'재시도 실패'**로 표시
  ④ **관리자 알림**을 발송

`DEVICE_HEALTH_CONNECTIONS.sync_status` 가 이 흐름의 상태 기계다.

    OK ──(3시간 미갱신)──> NUDGED ──(푸시 후에도 계속 미갱신)──> RETRY_FAILED
     ^                        │                                      │
     └────────────(데이터가 들어오면 어느 상태에서든 OK)───────────────┘

⚠ **앱이 재시도하는 것과 다른 층이다.** `NFR-DV-002` 앞부분은 앱이 전송
  실패 시 3회·30초 간격으로 재시도하라고 규정한다(앱 책임). 여기는 그
  재시도까지 전부 실패했거나 앱이 아예 안 돌고 있는 경우를 **서버가**
  뒤늦게 알아채는 층이다. 둘을 헷갈리면 "이미 재시도하는데 왜 또?" 가
  된다.

⚠ **판정 결과를 만들지 않는다.** 미수신은 「데이터가 없다」는 뜻이지
  「위험하다」는 뜻이 아니다. `EMOTION_RISK_SCORES` 에 NORMAL 을 쓰면
  관제 대시보드가 안전한 것으로 착각한다 — `ai/server` 가 3일치 미만일 때
  422 로 끊는 것과 같은 이유다.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DeviceHealthConnection, User
from app.services import push

logger = logging.getLogger(__name__)

#  NFR-DV-002 가 명시한 값이다. 임의값이 아니다.
MISSED_AFTER_HOURS = 3
#  무음 푸시를 보낸 뒤 이만큼 더 기다려도 안 들어오면 재시도 실패로 본다.
#  ⚠ 요구사항이 "이후에도 수신되지 않으면" 이라고만 하고 대기 시간을 정하지
#    않았다. 앱 수집 주기가 15분이므로 그 4배를 뒀다 — 한두 주기 걸러도
#    실패로 몰지 않으면서, 한 시간 안에는 관리자가 알게 된다.
RETRY_GRACE_HOURS = 1


async def scan(db: AsyncSession, now: datetime | None = None) -> dict[str, int]:
    """미수신을 한 번 훑는다. 스케줄러가 주기적으로 부른다.

    `now` 를 주입받는 이유 — 테스트가 벽시계에 의존하면 특정 시간대에만
    깨진다. 선제 접촉 테스트가 실제로 그렇게 깨진 적이 있다(학습자료 사례 20).

    돌려주는 값은 이번 스캔에서 무엇을 했는지 센 것이다:
      nudged        무음 푸시를 보낸 수 (①②)
      retry_failed  재시도 실패로 표시한 수 (③④)
      recovered     데이터가 들어와 OK 로 되돌린 수
    """
    now = now or datetime.now(timezone.utc)
    missed_before = now - timedelta(hours=MISSED_AFTER_HOURS)
    grace_before = now - timedelta(hours=RETRY_GRACE_HOURS)

    counts = {"nudged": 0, "retry_failed": 0, "recovered": 0}

    rows = await db.execute(
        select(DeviceHealthConnection, User)
        .join(User, User.user_id == DeviceHealthConnection.user_id)
        .where(DeviceHealthConnection.permission_granted.is_(True))
    )

    for conn, user in rows:
        synced = conn.last_synced_at
        healthy = synced is not None and synced > missed_before

        #  들어오고 있으면 어느 상태에서든 OK 로 되돌린다.
        if healthy:
            if conn.sync_status != "OK":
                conn.sync_status = "OK"
                conn.nudged_at = None
                counts["recovered"] += 1
            continue

        if conn.sync_status == "OK":
            #  ① 감지 → ② 무음 푸시
            #  ⚠ 푸시가 실패해도 NUDGED 로 넘긴다. 토큰이 없거나 죽었다는
            #    것 자체가 「앱이 안 돌고 있다」는 신호라, 여기서 OK 로
            #    남겨두면 영영 재시도 실패까지 못 간다.
            if user.fcm_token:
                try:
                    await push.send_silent(
                        user.fcm_token,
                        {"type": "sync_nudge", "reason": "missed_sync"},
                    )
                except Exception:
                    logger.exception("[sync-watch] 무음 푸시 실패: user=%s", user.user_id)
            else:
                logger.info("[sync-watch] FCM 토큰 없음: user=%s", user.user_id)
            conn.sync_status = "NUDGED"
            conn.nudged_at = now
            counts["nudged"] += 1

        elif conn.sync_status == "NUDGED":
            #  ③ 푸시를 보냈는데도 유예 시간이 지나도록 안 들어옴
            if conn.nudged_at is not None and conn.nudged_at <= grace_before:
                conn.sync_status = "RETRY_FAILED"
                counts["retry_failed"] += 1
                #  ④ 관리자 알림 — 관제 화면의 「미수신」 목록으로 노출된다
                #    (`GET /admin/sync-failures`). 별도 알림 테이블을 만들지
                #    않는 이유는 이 컬럼 자체가 곧 알림 대상 목록이기 때문이다.
                logger.warning(
                    "[sync-watch] 재시도 실패 — 관리자 확인 필요: user=%s 마지막=%s",
                    user.user_id,
                    synced,
                )

    await db.commit()
    if any(counts.values()):
        logger.info("[sync-watch] %s", counts)
    return counts
