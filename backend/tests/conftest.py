"""테스트 공통 픽스처.

개발 DB 를 그대로 쓴다. 테스트마다 고유 이메일로 계정을 만들고 끝나면 지우므로
기존 데이터에 영향을 주지 않는다. 별도 테스트 DB 를 두면 schema.sql 을 두 번
적용해야 하고, 그 순간 "정본이 하나" 원칙이 흐려진다.

⚠ **다만 「개발 DB」는 로컬을 뜻한다.** 2026.08.05 에 `.env` 기본값이 캠퍼스
  공용 DB 로 바뀌었다. 그대로 pytest 를 돌리면 **팀 공용 DB 에 계정을 만들고
  지운다** — 고유 이메일이라 남의 데이터를 덮지는 않지만, 남의 개발 중에
  행이 생겼다 사라지고 실패 시 찌꺼기가 남는다.

  그래서 아래 `pytest_configure` 가 **로컬이 아니면 실행 자체를 막는다.**
"""

import os
import uuid
from urllib.parse import urlsplit

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app

BASE = "http://test/api/v1"

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
_ALLOW_ENV = "LISN_ALLOW_REMOTE_TEST_DB"


def pytest_configure(config):
    """공용 DB 를 향한 채로 테스트가 돌지 않게 막는다.

    막기만 하고 대신 골라주지는 않는다. 어느 DB 로 돌릴지는 사람이 정해야
    하는 것이고, 여기서 조용히 로컬로 바꿔치면 **정본이 어디인지가 다시
    흐려진다.**
    """
    host = urlsplit(settings.database_url.replace("+asyncpg", "")).hostname or ""
    if host in _LOCAL_HOSTS or os.getenv(_ALLOW_ENV):
        return
    pytest.exit(
        f"\n테스트가 로컬이 아닌 DB 를 향하고 있습니다 — host={host}\n"
        "\n"
        "테스트는 계정을 만들고 지웁니다. 공용 DB 에서 돌리면 팀 데이터에\n"
        "섞입니다. 아래 중 하나로 돌리세요.\n"
        "\n"
        "  DATABASE_URL=<로컬주소> python -m pytest -q\n"
        f"  {_ALLOW_ENV}=1 python -m pytest -q      # 정말 그래야 할 때만\n",
        returncode=2,
    )


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _signup_body(**overrides) -> dict:
    body = {
        "email": f"t{uuid.uuid4().hex[:12]}@lisn-test.example",
        "password": "test1234!",
        "name": "테스터",
        "terms_agreed": True,
        "sensitive_agreed": True,
    }
    body.update(overrides)
    return body


@pytest_asyncio.fixture
async def user(client):
    """가입된 일반 사용자. (token, body) 를 돌려준다."""
    body = _signup_body()
    r = await client.post(f"{BASE}/auth/signup", json=body)
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]

    yield {"token": token, "email": body["email"], "headers": _auth(token)}

    await client.request(
        "DELETE",
        f"{BASE}/users/me",
        headers=_auth(token),
        json={"password": body["password"]},
    )


@pytest.fixture
def signup_body():
    return _signup_body


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth():
    return _auth
