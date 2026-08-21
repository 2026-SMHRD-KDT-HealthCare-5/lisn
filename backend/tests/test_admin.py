"""관리자 관제 — MLCM_501 · MLCM_510

`require_admin` 은 JWT 가 아니라 **DB 의 role** 을 본다. 그래서 승격은 DB 를 직접
고치고, 토큰은 그대로 쓴다(아래 test_승격은_재로그인_없이_즉시_적용된다 참조).
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text

from app.core.database import AsyncSessionLocal

BASE = "http://test/api/v1"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _promote(email: str, role: str) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("UPDATE users SET role = :role WHERE email = :email"),
            {"role": role, "email": email},
        )
        await db.commit()


@pytest_asyncio.fixture
async def target(client):
    """검색 대상 일반 사용자. 이름에 검색어를 심어둔다."""
    tag = uuid.uuid4().hex[:10]
    body = {
        "email": f"srch{tag}@lisn-test.example",
        "password": "test1234!",
        "name": f"검색대상{tag}",
        "terms_agreed": True,
        "sensitive_agreed": True,
    }
    r = await client.post(f"{BASE}/auth/signup", json=body)
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]

    yield {"tag": tag, "name": body["name"], "email": body["email"]}

    await client.request(
        "DELETE", f"{BASE}/users/me", headers=_auth(token),
        json={"password": body["password"]},
    )


# --------------------------------------------------------------------------
#  권한
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_일반_사용자는_403_이다(client, user):
    """토큰은 유효한데 권한이 없는 것이므로 401 이 아니라 403 이다(SD-E1).

    401 로 내리면 클라이언트가 재로그인을 시도하는데, 다시 로그인해도 해결되지
    않는 상황이라 무한 루프가 된다.
    """
    r = await client.get(f"{BASE}/admin/users", headers=user["headers"])
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_승격은_재로그인_없이_즉시_적용된다(client, admin):
    """`require_admin` 이 DB 의 role 을 읽기 때문이다.

    JWT 에도 role 클레임이 들어가지만 **아무도 읽지 않는다.** 이 테스트가
    실패한다면 누군가 검증을 JWT 클레임으로 옮긴 것이고, 그 순간 승격·강등이
    토큰 만료(24시간)까지 반영되지 않는다.

    ⚠ 다만 **관리자 웹은 재로그인이 필요하다.** 로그인 응답의 role 로 세션 저장
      여부를 결정하기 때문이다(admin/src/session.js). API 와 화면의 동작이
      다르므로 안내할 때 구분해야 한다.
    """
    r = await client.get(f"{BASE}/admin/users", headers=admin["headers"])
    assert r.status_code == 200


# --------------------------------------------------------------------------
#  검색 — MLCM_501 ❷
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_이름으로_검색된다(client, admin, target):
    r = await client.get(
        f"{BASE}/admin/users", headers=admin["headers"], params={"q": target["tag"]}
    )
    assert r.status_code == 200
    assert [u["email"] for u in r.json()] == [target["email"]]


@pytest.mark.asyncio
async def test_이메일로도_검색된다(client, admin, target):
    r = await client.get(
        f"{BASE}/admin/users", headers=admin["headers"], params={"q": f"srch{target['tag']}"}
    )
    assert [u["email"] for u in r.json()] == [target["email"]]


@pytest.mark.asyncio
async def test_대소문자를_구분하지_않는다(client, admin, target):
    """관리자가 이메일을 대문자로 칠 수 있다. 못 찾으면 없는 사람으로 오인한다."""
    r = await client.get(
        f"{BASE}/admin/users",
        headers=admin["headers"],
        params={"q": target["tag"].upper()},
    )
    assert [u["email"] for u in r.json()] == [target["email"]]


@pytest.mark.asyncio
async def test_관리자_계정은_검색에_안_잡힌다(client, admin):
    """대상자 목록은 role='USER' 만 본다. 관제 대상이 아닌 사람이 섞이면 안 된다."""
    r = await client.get(
        f"{BASE}/admin/users", headers=admin["headers"], params={"q": "관제담당"}
    )
    assert r.json() == []


@pytest.mark.asyncio
async def test_퍼센트_기호가_전체조회로_새지_않는다(client, admin, target):
    """LIKE 메타문자를 이스케이프하지 않으면 '%' 한 글자가 전 사용자 조회가 된다.

    관리자가 의도적으로 넣지 않아도, 검색창에 실수로 들어간 한 글자가
    전체 명단을 띄우는 것은 개인정보 관점에서 사고다.
    """
    r = await client.get(f"{BASE}/admin/users", headers=admin["headers"], params={"q": "%"})
    assert r.json() == []


@pytest.mark.asyncio
async def test_언더바가_임의의_한_글자로_동작하지_않는다(client, admin, target):
    """'_' 는 LIKE 에서 임의의 한 글자다. 이스케이프를 빼면 검색 결과가

    조용히 틀어진다 — 틀린 사람이 나오는데 오류는 안 난다.
    """
    # target 이름은 '검색대상<tag>' 이므로 '검색_상' 은 리터럴로는 매칭되지 않아야 한다.
    r = await client.get(
        f"{BASE}/admin/users", headers=admin["headers"], params={"q": "검색_상"}
    )
    assert r.json() == []


@pytest.mark.asyncio
async def test_공백만_있으면_검색하지_않은_것과_같다(client, admin, target):
    """검색창을 지우다 공백이 남는 일이 흔하다. 빈 결과가 뜨면 없는 줄 안다."""
    plain = await client.get(f"{BASE}/admin/users", headers=admin["headers"])
    spaced = await client.get(
        f"{BASE}/admin/users", headers=admin["headers"], params={"q": "   "}
    )
    assert len(spaced.json()) == len(plain.json())
    assert len(plain.json()) > 0


@pytest.mark.asyncio
async def test_없는_사람을_찾으면_빈_목록이다(client, admin):
    """404 가 아니다. 검색은 조회이고, 결과가 없는 것은 오류가 아니다."""
    r = await client.get(
        f"{BASE}/admin/users", headers=admin["headers"], params={"q": "존재하지않는이름xyzzy"}
    )
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_위험도_필터와_AND_로_걸린다(client, admin, target):
    """"심각한 사람 중에서 김씨" 가 관제에서 실제로 필요한 동작이다.

    target 은 방금 가입해 평가 이력이 없으므로(risk_level=null) 어떤 위험도로
    걸러도 나오지 않아야 한다.
    """
    r = await client.get(
        f"{BASE}/admin/users",
        headers=admin["headers"],
        params={"q": target["tag"], "risk_level": "CRITICAL"},
    )
    assert r.json() == []


@pytest.mark.asyncio
async def test_검색어가_너무_길면_422(client, admin):
    """길이 제한이 없으면 임의 길이 문자열이 그대로 SQL 패턴이 된다."""
    r = await client.get(
        f"{BASE}/admin/users", headers=admin["headers"], params={"q": "가" * 101}
    )
    assert r.status_code == 422
