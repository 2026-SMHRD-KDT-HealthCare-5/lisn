"""긴 한글 비밀번호 — bcrypt 72바이트 한계"""

import pytest

from tests.conftest import BASE

# 한글 25자 = UTF-8 75바이트. max_length=64 는 **글자 수**라 통과한다.
LONG_KO = "귀기울임프로젝트비밀번호입니다이건꽤긴암호예요"  # 22자
LONGER_KO = "귀기울임프로젝트비밀번호입니다이건아주긴암호문장이에요정말로"  # 29자


@pytest.mark.asyncio
async def test_긴_한글_비밀번호로_가입해도_500_이_아니다(client, signup_body):
    """bcrypt 는 72바이트를 넘으면 ValueError 를 던진다(bcrypt 5.x).

    `max_length=64` 는 **글자 수**를 세므로 한글 25자(75바이트)가 그대로
    통과해 해시 단계에서 터집니다. 사용자에게는 500 으로 보입니다.
    """
    r = await client.post(f"{BASE}/auth/signup", json=signup_body(password=LONGER_KO))
    assert r.status_code != 500, r.text
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_72바이트_이내_한글_비밀번호는_가입과_로그인이_된다(client, signup_body):
    body = signup_body(password=LONG_KO)
    r = await client.post(f"{BASE}/auth/signup", json=body)
    assert r.status_code == 201, r.text

    login = await client.post(
        f"{BASE}/auth/login", json={"email": body["email"], "password": LONG_KO}
    )
    assert login.status_code == 200, login.text

    await client.request(
        "DELETE",
        f"{BASE}/users/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        json={"password": LONG_KO},
    )
