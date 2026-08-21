"""관리자 비밀번호를 팀 공용 테스트값으로 되돌립니다 — 개발 DB 전용

왜 필요한가
    관리자 계정은 앱과 같은 로그인 API 를 쓰지만 **시드 SQL 로 만들지
    않습니다.** bcrypt 해시를 SQL 로 만들 수 없어서 API/스크립트로 만들고,
    그 비밀번호는 어디에도 기록되지 않습니다. 2026.08.22 에 실제로
    잃어버려 시연 준비 중 관제 웹에 못 들어갔습니다.

    ⚠ 발표 당일에 이걸 겪으면 관제 시연을 통째로 못 합니다.

사용:
    cd backend
    python ../tools/reset_admin_password.py
    python ../tools/reset_admin_password.py --email admin@lisn-test.example

⚠ **개발 DB 전용입니다.** 운영·공용 DB 를 가리키는 .env 로 실행하지 마세요.
  대상 이메일이 `.example`(RFC 2606 예약) 이 아니면 물어봅니다.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import select  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models import User  # noqa: E402

# db/seed_demo_persona.sql 주석과 같은 값을 씁니다. 계정마다 다르면
# 시연 중에 어느 것이었는지 헷갈립니다.
TEAM_TEST_PASSWORD = "rldnfdla"
DEFAULT_EMAIL = "admin@lisn-test.example"


async def main(email: str, yes: bool) -> int:
    if not email.endswith(".example") and not yes:
        print(f"[!] {email} 은 예약 도메인(.example)이 아닙니다.")
        print("    실제 계정일 수 있습니다. 확실하면 --yes 를 붙이세요.")
        return 2

    async with AsyncSessionLocal() as db:
        u = await db.scalar(select(User).where(User.email == email))
        if u is None:
            print(f"[!] 계정이 없습니다: {email}")
            return 1
        u.password_hash = hash_password(TEAM_TEST_PASSWORD)
        await db.commit()
        print(f"[ok] {u.email} (role={u.role}, name={u.name})")
        print(f"     비밀번호를 팀 공용값으로 맞췄습니다: {TEAM_TEST_PASSWORD}")
        return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--email", default=DEFAULT_EMAIL)
    p.add_argument("--yes", action="store_true", help=".example 이 아닌 계정도 강행")
    a = p.parse_args()
    raise SystemExit(asyncio.run(main(a.email, a.yes)))
