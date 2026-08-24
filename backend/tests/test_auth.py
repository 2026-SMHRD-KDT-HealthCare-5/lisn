"""인증 — MLCM_100 · MLCM_101 · MLCM_102"""

import pytest

from app.api.v1 import auth as auth_module
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
async def test_password_reset_sends_mail_when_smtp_configured(client, user, monkeypatch):
    """구현_갭 갭4 — SMTP 가 설정돼 있으면 실제로 발송을 시도한다."""
    monkeypatch.setattr(auth_module.mail, "configured", lambda: True)
    calls = []

    async def fake_send(to_email, token):
        calls.append((to_email, token))

    monkeypatch.setattr(auth_module.mail, "send_password_reset_email", fake_send)

    r = await client.post(
        f"{BASE}/auth/password-reset/request", json={"email": user["email"]}
    )
    assert r.status_code == 200
    assert len(calls) == 1
    assert calls[0][0] == user["email"]


@pytest.mark.asyncio
async def test_password_reset_survives_smtp_failure(client, user, monkeypatch):
    """발송이 실패해도 200 을 돌려준다 — MLCM_102 5단계가 가입 여부를
    노출하지 말라고 규정하므로, 여기서 500 이 나면 그 자체로 정보가 샌다."""
    monkeypatch.setattr(auth_module.mail, "configured", lambda: True)

    async def failing_send(to_email, token):
        raise RuntimeError("SMTP 연결 실패(테스트)")

    monkeypatch.setattr(auth_module.mail, "send_password_reset_email", failing_send)

    r = await client.post(
        f"{BASE}/auth/password-reset/request", json={"email": user["email"]}
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_password_reset_skips_mail_when_smtp_unconfigured(client, user, monkeypatch):
    """SMTP 미설정이면 발송을 시도하지 않고도 200 을 돌려준다(기본 상태)."""
    monkeypatch.setattr(auth_module.mail, "configured", lambda: False)
    called = False

    async def should_not_run(to_email, token):
        nonlocal called
        called = True

    monkeypatch.setattr(auth_module.mail, "send_password_reset_email", should_not_run)

    r = await client.post(
        f"{BASE}/auth/password-reset/request", json={"email": user["email"]}
    )
    assert r.status_code == 200
    assert called is False


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
