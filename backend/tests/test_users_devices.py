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


# ==========================================================================
#  알림 수신 동의 — MAIN_SETTING_01 ❷ · MLCM_400 5단계 (구현 갭 2)
# ==========================================================================


async def test_알림_설정_기본값은_둘_다_켜짐(client, user):
    """`MLCM_400` 5단계가 "알림 수신 동의 상태인 경우" 를 전제한다.

    기본이 꺼져 있으면 그 유스케이스가 기본 상태에서 동작하지 않는다.
    """
    r = await client.get(f"{BASE}/users/me/notifications", headers=user["headers"])
    assert r.status_code == 200
    assert r.json() == {
        "care_alert_agreed": True,
        "content_alert_agreed": True,
        "fcm_token_registered": False,
    }


async def test_콘텐츠_알림만_꺼도_케어_알림은_남는다(client, user):
    """**이 테스트가 토글을 둘로 나눈 이유다.**

    하나로 묶으면 광고성 알림이 귀찮아 끈 사람이 선제 접촉(`MLCM_220`)까지
    끈다. 알림을 끄는 사람일수록 앱을 안 여는 사람, 즉 놓치면 안 되는 쪽이다.
    """
    r = await client.patch(
        f"{BASE}/users/me/notifications",
        headers=user["headers"],
        json={"content_alert_agreed": False},
    )
    assert r.status_code == 200
    assert r.json()["content_alert_agreed"] is False
    assert r.json()["care_alert_agreed"] is True


async def test_토큰은_등록_여부만_돌려준다(client, user):
    """토큰 자체를 응답에 실으면 저장된 값이 그대로 노출된다."""
    r = await client.patch(
        f"{BASE}/users/me/notifications",
        headers=user["headers"],
        json={"fcm_token": "fake-device-token"},
    )
    assert r.status_code == 200
    assert r.json()["fcm_token_registered"] is True
    assert "fcm_token" not in r.json()


async def test_빈_문자열로_토큰을_지운다(client, user):
    """로그아웃 시 토큰을 비워야 한다.

    null 은 「안 바꿈」이라 그것만으로는 지울 방법이 없다.
    """
    await client.patch(
        f"{BASE}/users/me/notifications",
        headers=user["headers"],
        json={"fcm_token": "t"},
    )
    r = await client.patch(
        f"{BASE}/users/me/notifications",
        headers=user["headers"],
        json={"fcm_token": ""},
    )
    assert r.json()["fcm_token_registered"] is False


async def test_보내지_않은_필드는_건드리지_않는다(client, user):
    """토글 하나를 껐다고 다른 하나까지 바뀌면 안 된다."""
    await client.patch(
        f"{BASE}/users/me/notifications",
        headers=user["headers"],
        json={"care_alert_agreed": False, "content_alert_agreed": False},
    )
    r = await client.patch(
        f"{BASE}/users/me/notifications",
        headers=user["headers"],
        json={"care_alert_agreed": True},
    )
    assert r.json()["care_alert_agreed"] is True
    assert r.json()["content_alert_agreed"] is False
