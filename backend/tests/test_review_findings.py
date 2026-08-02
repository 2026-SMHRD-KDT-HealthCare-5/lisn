"""2026.08.02 코드 점검에서 나온 결함들 — 회귀 방지

전부 **에러가 안 나면서 조용히 틀리던** 것들이라 테스트가 없으면 다시 들어온다.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select, text

from app.api.v1.chat import _decide
from app.core.database import AsyncSessionLocal
from app.models import Emotion, EmotionRiskScore, User
from app.services import report as report_service
from tests.conftest import BASE


async def _seed_scores(email: str, levels_at: list[tuple[str, datetime]]) -> None:
    """(risk_level, evaluated_at) 목록으로 분석 결과를 심는다."""
    async with AsyncSessionLocal() as db:
        user_id = await db.scalar(select(User.user_id).where(User.email == email))
        assert user_id is not None
        emotion_id = await db.scalar(
            select(Emotion.emotion_id).order_by(Emotion.emotion_code).limit(1)
        )
        assert emotion_id is not None, "EMOTIONS 마스터가 비어 있습니다 (db/schema.sql)"
        for level, at in levels_at:
            db.add(
                EmotionRiskScore(
                    user_id=user_id,
                    emotion_id=emotion_id,
                    emotion_score=50,
                    risk_level=level,
                    risk_score=50,
                    model_version="test",
                    evaluated_at=at,
                )
            )
        await db.commit()


@pytest_asyncio.fixture
async def scored_user(client, signup_body):
    """분석 결과를 심을 수 있는 일반 사용자."""
    body = signup_body()
    r = await client.post(f"{BASE}/auth/signup", json=body)
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    yield {
        "email": body["email"],
        "headers": {"Authorization": f"Bearer {token}"},
        "password": body["password"],
    }
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("DELETE FROM users WHERE email = :e"), {"e": body["email"]}
        )
        await db.commit()


# ──────────────────────────────────────────────────────────────────────
#  리포트가 최신이 아니라 **가장 오래된** 구간을 돌려주던 것
# ──────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_리포트는_잘릴_때_최신_쪽을_남긴다(client, scored_user, monkeypatch):
    """오름차순 + LIMIT 이면 기간 안에서 **가장 오래된** N건이 잡힌다.

    분석은 라이프로그 push 마다 1건씩 쌓이므로(앱 15분 주기) 30일 기본 구간은
    금방 상한을 넘는다. 그때 리포트가 첫 며칠에서 멈춰 있으면 **정서 변화를
    보라는 화면이 최신 상태를 못 보여준다.**
    """
    now = datetime.now(timezone.utc)
    await _seed_scores(
        scored_user["email"],
        [
            ("NORMAL", now - timedelta(days=3)),
            ("CAUTION", now - timedelta(days=2)),
            ("CRITICAL", now - timedelta(days=1)),
        ],
    )
    monkeypatch.setattr(report_service, "MAX_POINTS", 2)

    r = await client.get(f"{BASE}/reports", headers=scored_user["headers"])
    assert r.status_code == 200, r.text
    trend = r.json()["emotion_trend"]

    assert len(trend) == 2
    assert [p["risk_level"] for p in trend] == ["CAUTION", "CRITICAL"], (
        "최신 2건이 아니라 오래된 2건이 잡혔습니다"
    )
    # 차트용이므로 시간순(오름차순)이어야 한다.
    assert trend[0]["evaluated_at"] < trend[1]["evaluated_at"]


# ──────────────────────────────────────────────────────────────────────
#  CRITICAL 인데 콘텐츠 추천이 나가던 것 — MLCM_510 2단계
# ──────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_CRITICAL_이면_추천_엔드포인트도_비운다(client, scored_user):
    """`/home` 에만 가드가 있어서, 이 엔드포인트를 직접 부르면 위기 상태
    사용자에게 콘텐츠가 나갔습니다. 판정은 서버가 확정합니다."""
    await _seed_scores(
        scored_user["email"], [("CRITICAL", datetime.now(timezone.utc))]
    )

    home = await client.get(f"{BASE}/home", headers=scored_user["headers"])
    assert home.json()["action"] == "EMERGENCY"
    assert home.json()["recommendations"] == []

    recs = await client.get(
        f"{BASE}/contents/recommendations", headers=scored_user["headers"]
    )
    assert recs.status_code == 200, recs.text
    assert recs.json() == [], "CRITICAL 사용자에게 추천이 나갔습니다"


# ──────────────────────────────────────────────────────────────────────
#  LLM 이 대소문자를 다르게 줘도 위기 판정이 떨어지지 않아야 한다
# ──────────────────────────────────────────────────────────────────────
class _Verdict:
    def __init__(self, is_crisis, severity):
        self.is_crisis = is_crisis
        self.severity = severity


@pytest.mark.asyncio
async def test_severity_대소문자가_달라도_위기로_본다():
    """`CrisisVerdict.severity` 는 enum 이 아니라 자유 문자열이다.

    "High" 로 와도 파싱은 통과하므로, 그대로 비교하면 CRITICAL 이 조용히
    NORMAL 로 떨어진다.
    """
    none_kw = {"level": "NONE", "matched": []}
    for raw in ("HIGH", "high", "High", " HIGH "):
        assert _decide(none_kw, _Verdict(False, raw)).level == "CRITICAL", raw
    for raw in ("MEDIUM", "medium"):
        assert _decide(none_kw, _Verdict(False, raw)).level == "CAUTION", raw
    assert _decide(none_kw, _Verdict(False, "NONE")).level == "NORMAL"
    # severity 를 아예 못 채워도 is_crisis 는 살아 있어야 한다.
    assert _decide(none_kw, _Verdict(True, "")).level == "CRITICAL"


# ──────────────────────────────────────────────────────────────────────
#  관리자 대시보드의 「전체 N명」이 관리자 자신을 세던 것
# ──────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_대시보드_전체_인원에_관리자를_넣지_않는다(client, signup_body):
    """`/admin/users` 는 role == USER 로 거르는데 대시보드는 전체를 셌다.

    관리자 웹이 `total_users - evaluated_users` 로 미평가 수를 그리므로,
    목록에 없는 사람이 미평가자로 잡혀 숫자가 안 맞았다.
    """
    body = signup_body(email=f"adm{uuid.uuid4().hex[:12]}@lisn-test.example")
    r = await client.post(f"{BASE}/auth/signup", json=body)
    assert r.status_code == 201, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("UPDATE users SET role = 'ADMIN' WHERE email = :e"),
            {"e": body["email"]},
        )
        await db.commit()

    try:
        dash = await client.get(f"{BASE}/admin/dashboard", headers=headers)
        assert dash.status_code == 200, dash.text
        listed = await client.get(f"{BASE}/admin/users?limit=200", headers=headers)
        assert listed.status_code == 200, listed.text

        # 목록은 페이지네이션이 걸리므로 상한을 넘지 않을 때만 엄밀히 비교한다.
        rows = listed.json()
        if len(rows) < 200:
            assert dash.json()["total_users"] == len(rows), (
                "대시보드의 전체 인원과 대상자 목록 수가 다릅니다"
            )
    finally:
        await client.request(
            "DELETE", f"{BASE}/users/me", headers=headers,
            json={"password": body["password"]},
        )


# ──────────────────────────────────────────────────────────────────────
#  PATCH /users/me 의 setattr 루프 — 권한 상승 방어
# ──────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_프로필_수정으로_권한을_올릴_수_없다(client, user):
    """`update_me` 는 요청에서 받은 키를 그대로 `setattr` 로 밀어 넣는다.

    지금은 `UserUpdate` 에 role·email 이 없고 Pydantic 이 모르는 키를 버려서
    안전하다. 다만 **그 안전이 스키마 하나에 걸려 있다.** `extra="allow"` 가
    붙거나 필드가 하나 추가되는 순간 권한 상승이 된다 — 리뷰로는 놓치기 쉬운
    변경이라 여기서 못으로 박아둔다.
    """
    before = (await client.get(f"{BASE}/users/me", headers=user["headers"])).json()

    r = await client.patch(
        f"{BASE}/users/me",
        headers=user["headers"],
        json={
            "name": "바뀐이름",
            "role": "ADMIN",
            "email": "attacker@lisn-test.example",
            "password_hash": "$2b$12$0000000000000000000000000000000000000000000000000000",
            "user_id": str(uuid.uuid4()),
        },
    )
    assert r.status_code == 200, r.text
    after = r.json()

    assert after["name"] == "바뀐이름", "허용된 필드는 반영돼야 한다"
    assert after["role"] == "USER"
    assert after["email"] == before["email"]
    assert after["user_id"] == before["user_id"]

    # 관리자 API 가 실제로 막히는지까지 확인한다. 응답만 보고 판단하지 않는다.
    denied = await client.get(f"{BASE}/admin/dashboard", headers=user["headers"])
    assert denied.status_code == 403
