"""라이프로그·챗봇 — MLCM_200 · MLCM_310 · MLCM_320"""

import pytest

from app.services import safety
from tests.conftest import BASE


@pytest.mark.asyncio
async def test_resend_upserts_instead_of_duplicating(client, user):
    """MLCM_200 5단계 — 재시도로 같은 시각이 다시 와도 중복 행이 생기면 안 된다."""
    at = "2026-07-31T09:00:00Z"
    await client.post(
        f"{BASE}/lifelog/batch",
        headers=user["headers"],
        json={"items": [{"collected_at": at, "steps": 3200}]},
    )
    await client.post(
        f"{BASE}/lifelog/batch",
        headers=user["headers"],
        json={"items": [{"collected_at": at, "steps": 9999}]},
    )

    rows = (await client.get(f"{BASE}/lifelog", headers=user["headers"])).json()
    same_time = [r for r in rows if r["collected_at"].startswith("2026-07-31T09:00")]
    assert len(same_time) == 1, "행이 늘어나면 UPSERT 가 아니다"
    assert same_time[0]["steps"] == 9999, "값이 갱신돼야 한다"


@pytest.mark.asyncio
async def test_oversized_batch_is_rejected_not_truncated(client, user):
    """서버가 잘라내면 유실이 조용히 생긴다. 거절해야 앱이 나눠 보낸다."""
    items = [
        {"collected_at": f"2026-06-{(i % 28) + 1:02d}T{i % 24:02d}:{i % 60:02d}:00Z"}
        for i in range(201)
    ]
    r = await client.post(
        f"{BASE}/lifelog/batch", headers=user["headers"], json={"items": items}
    )
    assert r.status_code == 413


@pytest.mark.asyncio
async def test_server_owns_last_synced_at(client, user):
    """앱 시계를 신뢰하지 않는다. 서버가 확정해 돌려준다."""
    await client.post(
        f"{BASE}/devices/connections",
        headers=user["headers"],
        json={"platform_type": "HEALTH_CONNECT"},
    )
    r = await client.post(
        f"{BASE}/lifelog/batch",
        headers=user["headers"],
        json={"items": [{"collected_at": "2026-07-31T10:00:00Z", "steps": 100}]},
    )
    assert r.json()["last_synced_at"]

    conns = (await client.get(f"{BASE}/devices/connections", headers=user["headers"])).json()
    assert conns[0]["last_synced_at"]


@pytest.mark.asyncio
async def test_report_409_when_no_analysis(client, user):
    """빈 차트를 내리면 '분석 실패'인지 '데이터 없음'인지 구분이 안 된다."""
    r = await client.get(f"{BASE}/reports", headers=user["headers"])
    assert r.status_code == 409


# --------------------------------------------------------------------------
# 위기 탐지 — 외부 API 없이 동작해야 한다 (NFR-DV-003)
# --------------------------------------------------------------------------

def test_keyword_filter_runs_without_openai():
    """1차 필터는 백엔드 내부 로직이라 OpenAI 장애와 무관하게 동작한다."""
    assert safety.keyword_scan("오늘 산책했어요")["level"] == "NONE"
    assert safety.keyword_scan("요즘 너무 지쳤어")["level"] == "MEDIUM"
    assert safety.keyword_scan("죽고 싶다는 생각이 들어")["level"] == "HIGH"


def test_idiom_is_not_flagged():
    """'배고파 죽겠다' 같은 관용 표현은 사전에서 제외했다."""
    assert safety.keyword_scan("배고파 죽겠다")["level"] == "NONE"


def test_pii_is_masked():
    """NFR-DE-002 — 저장 시점에 서버가 마스킹한다."""
    masked = safety.mask_pii("제 번호는 010-1234-5678이고 a@b.com 입니다")
    assert "010-1234-5678" not in masked
    assert "a@b.com" not in masked
    assert "[MASK:전화]" in masked


@pytest.mark.asyncio
async def test_critical_utterance_suppresses_reply(client, user):
    """CRITICAL 이면 병렬로 생성된 일반 응답을 서버가 버린다.

    OPENAI_API_KEY 가 없으면 키워드 단독 판정(source=KEYWORD)으로 떨어진다.
    """
    s = await client.post(
        f"{BASE}/chat/sessions", headers=user["headers"], json={"persona_type": "FRIEND"}
    )
    sid = s.json()["session_id"]

    r = await client.post(
        f"{BASE}/chat/sessions/{sid}/messages",
        headers=user["headers"],
        json={"content": "그냥 다 사라지고 싶어. 죽고 싶다는 생각이 계속 들어"},
    )
    body = r.json()
    assert body["risk"]["level"] == "CRITICAL"
    assert body["risk"]["action"] == "EMERGENCY"
    assert body["reply"] is None


@pytest.mark.asyncio
async def test_chat_stores_masked_text(client, user):
    s = await client.post(f"{BASE}/chat/sessions", headers=user["headers"], json={})
    sid = s.json()["session_id"]

    await client.post(
        f"{BASE}/chat/sessions/{sid}/messages",
        headers=user["headers"],
        json={"content": "제 번호는 010-1234-5678이에요"},
    )
    detail = (await client.get(f"{BASE}/chat/sessions/{sid}", headers=user["headers"])).json()
    joined = " ".join(m["content"] for m in detail["messages"])
    assert "010-1234-5678" not in joined


@pytest.mark.asyncio
async def test_cannot_read_others_session(client, user):
    r = await client.get(
        f"{BASE}/chat/sessions/00000000-0000-0000-0000-000000000000",
        headers=user["headers"],
    )
    assert r.status_code == 404
