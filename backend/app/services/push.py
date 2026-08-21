"""FCM 푸시 발송 — MLCM_220 4단계 · MLCM_400 5단계 · NFR-DV-002

Firebase Admin SDK 로 서버에서 직접 발송한다(구현_갭 갭 1 해소, 2026.08.21).

⚠ **자격증명이 없어도 서버는 뜬다.** 초기화는 첫 발송 시도 때 지연 수행하고,
  실패하면 예외를 던진다. 호출부(`outreach.py`)가 잡아서 `OUTREACH_LOGS` 에
  `FAILED` 로 남긴다 — `MLCM_220` 6단계가 「발송이 실패해도 선생성된 세션은
  유지된다」를 규정하므로, 여기서 예외가 나도 세션 자체는 이미 커밋됐다.

⚠ **알림 본문에 원문을 넣지 않는다.** 첫 발화(`opener`)는 위기 맥락을 담을
  수 있어, 잠금화면에 그대로 뜨면 타인에게 노출된다. 실제 내용은 앱을 열어야
  보이는 홈 카드·배너(`_outreachCard`)에서 보여준다 — 알림은 「왔다」는 것만
  알린다.
"""

import asyncio
import logging

import firebase_admin
from firebase_admin import credentials, messaging

from app.core.config import settings

logger = logging.getLogger(__name__)

_app: firebase_admin.App | None = None
_init_failed = False


def _get_app() -> firebase_admin.App:
    """지연 초기화. 앱 시작 시점에 자격증명 파일이 없어도 서버가 죽지 않는다."""
    global _app, _init_failed
    if _app is not None:
        return _app
    if _init_failed:
        raise RuntimeError("Firebase Admin 초기화가 이전에 실패했습니다")
    try:
        cred = credentials.Certificate(settings.firebase_credentials_path)
        _app = firebase_admin.initialize_app(cred)
    except Exception:
        _init_failed = True
        raise
    return _app


async def send(
    token: str,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> str:
    """단일 기기로 알림을 보낸다. 성공하면 FCM 메시지 ID 를 돌려준다.

    실패하면 예외를 그대로 던진다 — 재시도하지 않는다. 호출부가 상태를
    기록할 책임을 진다(로그를 두 곳에서 남기지 않기 위해).
    """
    app = _get_app()
    message = messaging.Message(
        token=token,
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
    )
    # firebase-admin 은 동기 SDK다 — 이벤트 루프를 막지 않도록 스레드로 뺀다.
    return await asyncio.to_thread(messaging.send, message, app=app)
