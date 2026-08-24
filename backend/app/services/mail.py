"""비밀번호 재설정 메일 발송 — MLCM_102 5단계 · MAIN_LOGIN_02

구현_갭 갭4 해소(2026.08.24). SMTP 가 없어 토큰을 사용자에게 전달할 경로가
없었다. 표준 라이브러리 `smtplib` 로 붙였다 — 발송량이 적어(재설정 요청뿐)
전용 SDK 를 새로 들일 이유가 없다.

⚠ **자격증명이 없어도 서버는 뜬다.** `push.py` 의 지연 초기화와 같은
  이유다 — SMTP 설정이 비면 발송을 시도할 때만 실패하고, `.env` 에
  `PASSWORD_RESET_LOG_TOKEN=true` 를 켜서 개발 흐름을 계속 탈 수 있다.

⚠ **smtplib 는 동기다.** `push.py` 가 firebase-admin(동기 SDK)을 스레드로
  빼는 것과 같은 이유로, 여기서도 이벤트 루프를 막지 않도록 스레드로 뺀다.
"""

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def configured() -> bool:
    """SMTP 자격증명이 채워져 있는지. 호출부가 발송 시도 전에 분기할 때 쓴다."""
    return bool(settings.smtp_host and settings.smtp_username and settings.smtp_password)


def _send_sync(to_email: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_username
    msg["To"] = to_email
    msg.set_content(body)

    # ⚠ smtp_use_tls 는 STARTTLS(587)용이다. 465(implicit TLS)를 쓰려면
    #   SMTP_SSL 로 갈아타야 한다 — Gmail 은 587+STARTTLS 가 표준이라 이 조합을 쓴다.
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(msg)


async def send_password_reset_email(to_email: str, token: str) -> None:
    """재설정 토큰을 담아 보낸다. 실패하면 예외를 그대로 던진다 — 재시도하지
    않는다. 호출부(`auth.py`)가 잡아서 로그로 남길 책임을 진다.

    ⚠ **웹 링크가 아니라 토큰 원문을 담는다.** 재설정 화면은 앱 안에
      있고(`MAIN_LOGIN_02`, `password_reset_screen.dart`), 이미 사용자가
      토큰을 직접 붙여넣는 입력창("메일로 받은 토큰과 새 비밀번호를
      입력해주세요")을 갖고 있다. 딥링크가 없으니 여기서 웹 URL 을
      만들어 봤자 열 곳이 없다.
    """
    import asyncio

    body = (
        "귀기울임 비밀번호 재설정을 요청하셨습니다.\n\n"
        f"앱의 비밀번호 재설정 화면에서 아래 토큰을 입력해주세요"
        f" ({settings.password_reset_expire_minutes}분 안에 만료됩니다):\n\n"
        f"{token}\n\n"
        "본인이 요청하지 않았다면 이 메일을 무시하셔도 됩니다."
    )
    await asyncio.to_thread(_send_sync, to_email, "[귀기울임] 비밀번호 재설정", body)
