"""시연 촬영용 — 실재하는 선제 접촉 건의 알림을 다시 띄운다.

왜 필요한가
    영상의 첫 장면은 「앱이 꺼져 있는데 마음이가 먼저 말을 건다」이다.
    그런데 실제 발송은 **라이프로그 분석 파이프라인 끝**에서만 일어나고
    (services/analysis.py → outreach.maybe_outreach), 쿨다운이 3일이라
    촬영하고 싶을 때 다시 부를 수가 없다.

⚠ **이 스크립트가 하는 일과 하지 않는 일을 정확히 알고 쓰세요.**

    하는 일   : DB 에 **이미 있는** 선제 접촉 건을 찾아, 그 건에 대한
                FCM 알림을 `services/push.py` 의 **운영과 같은 경로로**
                다시 보낸다. 제목·본문·data 페이로드가 outreach.py 와
                한 글자도 다르지 않다(아래 상수는 그쪽에서 그대로 가져온다).
    안 하는 일 : 판정을 새로 하지 않는다. 세션을 만들지 않는다.
                OUTREACH_LOGS 에 행을 추가하지 않는다. 쿨다운을 건드리지
                않는다. **없는 접촉을 지어내지 않는다.**

    그러니 화면에 뜨는 알림도, 눌러서 들어간 홈 카드도, 그 안의 첫 마디도
    전부 실제 데이터다. 사람이 정하는 것은 **발송 시각 하나뿐**이다.

    반대로 「푸시가 도착하는 순간까지 시스템이 자동으로 판단했다」고
    말하면 안 된다. 그 판단은 이미 과거에 일어났고, 지금 누르는 건
    재발송이다.

사용:
    cd backend
    python ../tools/demo_notify.py                      # 기본 데모 계정
    python ../tools/demo_notify.py --email cohort.03@lisn-test.example
    python ../tools/demo_notify.py --dry-run            # 보내지 않고 확인만

전제: backend/.env 의 DB 설정과 firebase-service-account.json 이 있어야 한다.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# backend 패키지를 import 경로에 올린다. 어디서 실행하든 동작하게.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import select  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.models import ChatSession, OutreachLog, User  # noqa: E402
from app.services import push  # noqa: E402

# ⚠ outreach.py 와 **같은 문구**여야 한다. 여기만 고치면 시연과 운영이
#   달라진다. 바꿀 일이 생기면 outreach.py 를 고치고 여기로 복사하세요.
TITLE = "마음이가 먼저 말을 걸었어요"
BODY = "지금 어떻게 지내고 계신지 궁금해요. 눌러서 확인해보세요."

DEFAULT_EMAIL = "demo.crisis@lisn-test.example"


async def main(email: str, dry_run: bool) -> int:
    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == email))
        if user is None:
            print(f"[!] 계정이 없습니다: {email}")
            return 1

        # 홈 카드가 읽는 것과 **같은 조건**으로 찾는다 (api/v1/home.py).
        #   · 선제 접촉으로 만들어진 세션이고
        #   · 아직 끝나지 않았고
        #   · 사용자가 아직 한 마디도 하지 않았다
        rows = (
            await db.execute(
                select(ChatSession)
                .join(OutreachLog, OutreachLog.session_id == ChatSession.session_id)
                .where(
                    ChatSession.user_id == user.user_id,
                    ChatSession.ended_at.is_(None),
                )
                .order_by(ChatSession.started_at.desc())
                .limit(1)
            )
        ).scalars().all()

        session = None
        for r in rows:
            msgs = list(r.messages or [])
            if msgs and not any(m.get("role") == "user" for m in msgs):
                session = r
                break

        if session is None:
            print(f"[!] {email} 에 **답장을 기다리는 선제 접촉이 없습니다.**")
            print("    홈 카드도 지금 안 떠 있을 겁니다. 둘은 같은 조건을 봅니다.")
            print("    이미 답장했거나 세션이 종료된 상태입니다.")
            return 2

        opener = (list(session.messages or [])[0] or {}).get("content", "")
        print(f"  대상   : {user.name} <{email}>")
        print(f"  세션   : {session.session_id}")
        print(f"  만든 때: {session.started_at}")
        print(f"  첫 마디: {opener[:70]}{'…' if len(opener) > 70 else ''}")
        print(f"  토큰   : {'있음' if user.fcm_token else '**없음**'}")

        if not user.fcm_token:
            print("\n[!] FCM 토큰이 없습니다. 앱을 한 번 실행해 알림 권한을 허용하면")
            print("    토큰이 서버에 등록됩니다.")
            return 3

        if dry_run:
            print("\n[dry-run] 보내지 않았습니다.")
            return 0

        msg_id = await push.send(
            user.fcm_token,
            title=TITLE,
            body=BODY,
            data={"type": "outreach", "session_id": str(session.session_id)},
        )
        print(f"\n[ok] 발송했습니다. message_id={msg_id}")
        print("     기기에서 알림을 눌러 홈 카드까지 이어지는지 확인하세요.")
        return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--email", default=DEFAULT_EMAIL)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    raise SystemExit(asyncio.run(main(a.email, a.dry_run)))
