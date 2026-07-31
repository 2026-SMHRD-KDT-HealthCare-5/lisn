"""사용자·연동 — MLCM_103 · MLCM_110 · MLCM_300"""

import pytest

from app.core.crypto import decrypt
from tests.conftest import BASE


@pytest.mark.asyncio
async def test_phone_is_encrypted_at_rest(client, signup_body, auth):
    """02-F (3) — 연락처는 AES-256-GCM 으로 저장하고 응답에서 복호화한다."""
    body = signup_body(phone="010-1234-5678")
    r = await client.post(f"{BASE}/auth/signup", json=body)
    token = r.json()["access_token"]

    me = await client.get(f"{BASE}/users/me", headers=auth(token))
    assert me.json()["phone"] == "010-1234-5678"

    # DB 원문을 직접 확인
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models import User

    async with AsyncSessionLocal() as db:
        stored = await db.scalar(select(User.phone).where(User.email == body["email"]))

    assert stored != "010-1234-5678", "평문으로 저장되면 안 된다"
    assert decrypt(stored) == "010-1234-5678"

    await client.request(
        "DELETE", f"{BASE}/users/me", headers=auth(token),
        json={"password": body["password"]},
    )


@pytest.mark.asyncio
async def test_partial_update_keeps_untouched_fields(client, signup_body, auth):
    """exclude_unset 이 없으면 안 보낸 phone 이 None 으로 덮여 날아간다."""
    body = signup_body(phone="010-9999-8888")
    token = (await client.post(f"{BASE}/auth/signup", json=body)).json()["access_token"]

    r = await client.patch(
        f"{BASE}/users/me", headers=auth(token), json={"persona_type": "COUNSELOR"}
    )
    assert r.status_code == 200
    assert r.json()["persona_type"] == "COUNSELOR"
    assert r.json()["phone"] == "010-9999-8888"

    await client.request(
        "DELETE", f"{BASE}/users/me", headers=auth(token),
        json={"password": body["password"]},
    )


@pytest.mark.asyncio
async def test_password_change_requires_current(client, user):
    r = await client.patch(
        f"{BASE}/users/me/password",
        headers=user["headers"],
        json={"current_password": "WRONG", "new_password": "newpass1234"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_reconnecting_same_platform_updates_row(client, user):
    """앱이 권한을 재승인할 때마다 행이 쌓이면 last_synced_at 기준이 모호해진다."""
    first = await client.post(
        f"{BASE}/devices/connections",
        headers=user["headers"],
        json={"platform_type": "HEALTH_CONNECT", "device_name": "Watch 6"},
    )
    second = await client.post(
        f"{BASE}/devices/connections",
        headers=user["headers"],
        json={"platform_type": "HEALTH_CONNECT", "device_name": "Watch 7"},
    )
    assert first.json()["connection_id"] == second.json()["connection_id"]
    assert second.json()["device_name"] == "Watch 7"

    rows = await client.get(f"{BASE}/devices/connections", headers=user["headers"])
    assert len(rows.json()) == 1


@pytest.mark.asyncio
async def test_cannot_touch_others_connection(client, user):
    r = await client.patch(
        f"{BASE}/devices/connections/00000000-0000-0000-0000-000000000000",
        headers=user["headers"],
        json={"permission_granted": False},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_consent_withdrawal_is_recorded(client, user):
    """MLCM_110 — 철회는 반영하되 기존 데이터는 지우지 않는다."""
    created = await client.post(
        f"{BASE}/devices/connections",
        headers=user["headers"],
        json={"platform_type": "HEALTH_CONNECT"},
    )
    cid = created.json()["connection_id"]

    r = await client.patch(
        f"{BASE}/devices/connections/{cid}",
        headers=user["headers"],
        json={"consent_scopes": {"activity": True, "sleep": False, "body_composition": False}},
    )
    assert r.json()["consent_scopes"]["sleep"] is False
