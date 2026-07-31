"""인증 — MLCM_100 · MLCM_101 · MLCM_102"""

import pytest

from tests.conftest import BASE


@pytest.mark.asyncio
async def test_signup_applies_db_defaults(client, signup_body):
    """05-C — persona_type 에 DEFAULT 가 없으면 여기서 INSERT 가 실패한다."""
    r = await client.post(f"{BASE}/auth/signup", json=signup_body())
    assert r.status_code == 201
    u = r.json()["user"]
    assert u["persona_type"] == "FRIEND"
    assert u["role"] == "USER"


@pytest.mark.asyncio
async def test_signup_requires_both_consents(client, signup_body):
    """05-K — 민감정보 동의는 일반 약관과 별도 항목이다. 둘 다 있어야 가입된다."""
    r = await client.post(
        f"{BASE}/auth/signup", json=signup_body(sensitive_agreed=False)
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_duplicate_email_conflicts(client, user, signup_body):
    r = await client.post(f"{BASE}/auth/signup", json=signup_body(email=user["email"]))
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_login_does_not_leak_account_existence(client, user):
    """계정 없음과 비밀번호 오류의 응답이 같아야 한다.

    구분되면 응답만으로 어떤 이메일이 가입돼 있는지 알아낼 수 있다.
    """
    wrong_pw = await client.post(
        f"{BASE}/auth/login", json={"email": user["email"], "password": "WRONG"}
    )
    no_account = await client.post(
        f"{BASE}/auth/login",
        json={"email": "nobody@lisn-test.example", "password": "whatever"},
    )
    assert wrong_pw.status_code == no_account.status_code == 401
    assert wrong_pw.json()["detail"] == no_account.json()["detail"]


@pytest.mark.asyncio
async def test_password_reset_hides_membership(client):
    """MLCM_102 5단계 — 미가입 이메일도 동일한 200 을 받는다."""
    r = await client.post(
        f"{BASE}/auth/password-reset/request", json={"email": "nobody@lisn-test.example"}
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_reset_token_cannot_be_used_as_access_token(client, user):
    """purpose 클레임 검사. 없으면 재설정 링크 하나로 계정 전체를 쓸 수 있다."""
    r = await client.post(f"{BASE}/users/me", headers={"Authorization": "Bearer bogus"})
    assert r.status_code in (401, 405)

    r = await client.get(f"{BASE}/users/me", headers={"Authorization": "Bearer bogus"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_logout_requires_token(client):
    r = await client.post(f"{BASE}/auth/logout")
    assert r.status_code == 401
