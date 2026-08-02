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


# ──────────────────────────────────────────────────────────────────────
#  키워드 등급 — 2026.08.02 성능 실측에서 드러난 빈틈
# ──────────────────────────────────────────────────────────────────────
def test_그만두고_싶다는_표현이_걸린다():
    """실측에서 「다 그만두고 싶어요」가 **아무 단계에도 안 걸렸습니다.**

    「다 끝내고 싶」·「다 내려놓고 싶」은 있는데 같은 뜻의 이 표현만
    빠져 있었습니다.
    """
    assert safety.keyword_scan("요즘 사는 게 힘들고 다 그만두고 싶어요")["level"] == "MEDIUM"


def test_그만두고_싶다는_HIGH_가_아니다():
    """⚠ **이 등급을 HIGH 로 올리지 마세요.**

    `chat.py` `_decide()` 는 LLM 판정이 없을 때(외부 API 장애) HIGH 키워드를
    **문맥 판단 없이 CRITICAL 로 확정**합니다. 「회사를 그만두고 싶어요」는
    아주 흔한 말이라, HIGH 로 올리면 그 상황에서 멀쩡한 사용자에게 긴급
    상담 화면이 뜹니다.

    미탐을 줄이려고 오탐을 감수하는 것은 **문맥을 볼 수 없을 때**의 정책이지,
    일상 표현을 고위험으로 분류하라는 뜻이 아닙니다.
    """
    assert safety.keyword_scan("회사를 그만두고 싶어요")["level"] == "MEDIUM"


def test_일상_표현은_여전히_걸리지_않는다():
    """추가한 단어가 기존 오탐 방어를 무너뜨리지 않았는지."""
    for text in ["배고파 죽겠다", "오늘 산책했어요", "이 회의는 의미가 없어요"]:
        assert safety.keyword_scan(text)["level"] == "NONE", text


# ──────────────────────────────────────────────────────────────────────
#  띄어쓰기 — 평가셋 200건에서 드러난 결함
# ──────────────────────────────────────────────────────────────────────
def test_붙여쓴_표현도_걸린다():
    """사전은 「죽고 싶」인데 사용자는 「죽고싶다」로 씁니다.

    원문 그대로 비교하면 **공백 하나에 필터가 통째로 뚫립니다.** 평가셋
    200건을 돌렸을 때 「아 진짜 죽고싶다」가 HIGH 에도 MEDIUM 에도 안
    걸렸습니다.
    """
    for text in ["아 진짜 죽고싶다", "죽고싶어", "다그만두고싶어요", "살기싫다"]:
        assert safety.keyword_scan(text)["level"] != "NONE", text


def test_보이지_않는_문자로도_못_피한다():
    """제로폭 문자를 끼워 넣어도 우회되지 않아야 합니다."""
    assert safety.keyword_scan("죽고\u200b싶다")["level"] == "HIGH"


def test_구두점은_지우지_않는다():
    """공백만 지웁니다. 구두점까지 지우면 문장 경계를 넘어 매칭됩니다.

    「일을 그만두고. 싶은 건 따로 있어요」처럼 두 문장이 붙으면 안 됩니다.
    """
    assert safety.keyword_scan("일을 그만두고. 싶은 건 따로 있어요")["level"] == "NONE"


def test_matched_는_사전_원본_형태로_돌려준다():
    """비교는 공백을 지운 쪽에서 하지만, 보고는 사전에 적힌 형태여야
    관리자가 어떤 규칙에 걸렸는지 알 수 있습니다."""
    assert safety.keyword_scan("죽고싶다")["matched"] == ["죽고 싶"]
