"""테스트 공통 픽스처.

개발 DB 를 그대로 쓴다. 테스트마다 고유 이메일로 계정을 만들고 끝나면 지우므로
기존 데이터에 영향을 주지 않는다. 별도 테스트 DB 를 두면 schema.sql 을 두 번
적용해야 하고, 그 순간 "정본이 하나" 원칙이 흐려진다.
"""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "http://test/api/v1"


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
