"""AI 추론 서버 — MLCM_210

비즈니스 서버가 라이프로그 적재 후 호출한다. 내부 API 라 인증이 없고,
두 서버가 같은 네트워크 안에 있으며 이 포트를 외부에 열지 않는 것을 전제로 한다
(docs/review/API설계_사전결정.md 7절).

실행:
    cd ai/server
    uvicorn main:app --reload --port 8001

⚠ 지금은 **규칙 기반 임시 판정**입니다. LSTM Autoencoder · LightGBM 이 아직
  없어서, 그때까지 전체 파이프라인이 끊기지 않도록 자리를 채워둔 것입니다.
  model_version 에 rule-placeholder 를 명시해 실제 모델 결과와 구분됩니다.
  모델이 준비되면 _predict() 하나만 교체하면 됩니다.
"""

import logging
import os
from datetime import datetime, timedelta, timezone

import asyncpg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="귀기울임 AI 추론 서버", version="0.1.0")

# 비즈니스 서버와 같은 DB 를 본다. 페이로드로 시퀀스를 실어 보내면 요청이
# 비대해지고, 전처리 규격이 바뀔 때마다 양쪽을 함께 고쳐야 한다.
DATABASE_URL = os.getenv(
    "AI_DATABASE_URL",
    os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lisn"),
).replace("postgresql+asyncpg://", "postgresql://")

# MLCM_210 2단계가 "최근 14일 평소 활동/생체 데이터(개인별 Min-Max 정규화 기준값)"
# 를 규정한다. GLOBEM 의 14일 집계 단위와도 일치한다.
BASELINE_DAYS = 14

MODEL_VERSION = "rule-placeholder-v0"


class AnalyzeRequest(BaseModel):
    user_id: str
    evaluated_at: datetime | None = None


class AnalyzeResponse(BaseModel):
    emotion_code: str
    emotion_score: float
    anomaly_score: float
    risk_level: str
    risk_score: float
    model_version: str


@app.get("/health")
async def health():
    return {"status": "ok", "model_version": MODEL_VERSION}


@app.post("/internal/analyze/lifelog", response_model=AnalyzeResponse)
async def analyze_lifelog(body: AnalyzeRequest):
    """라이프로그 기반 정서 위험도 산출 — MLCM_210

    비즈니스 서버는 user_id 만 보낸다. 필요한 시퀀스는 여기서 직접 읽는다.
    """
    try:
        conn = await asyncpg.connect(DATABASE_URL)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DB 연결 실패: {e}")

    try:
        since = datetime.now(timezone.utc) - timedelta(days=BASELINE_DAYS)
        rows = await conn.fetch(
            """
            SELECT collected_at, steps, total_sleep_min, sleep_efficiency_pct,
                   heart_rate, hrv
              FROM lifelog_metrics
             WHERE user_id = $1 AND collected_at >= $2
             ORDER BY collected_at ASC
            """,
            body.user_id,
            since,
        )
    finally:
        await conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="분석할 라이프로그가 없습니다")

    # ⚠ 행은 있는데 지표가 전부 비어 있는 경우가 있다(권한만 승인하고 실제 수집이
    #   안 된 상태). 이때 판정을 강행하면 편차가 0 이라 NORMAL 이 나오는데,
    #   그건 "정상"이 아니라 "모름"이다. 거짓 정상 기록이 남으면 사용자 대시보드와
    #   관리자 관제(MLCM_501) 양쪽에서 위험을 놓친다. 적재하지 않고 끊는다.
    if not _has_signal(rows):
        raise HTTPException(
            status_code=422, detail="지표가 비어 있어 판정할 수 없습니다"
        )

    result = _predict(rows)
    logger.info(
        "analyze user=%s n=%d -> %s/%s",
        body.user_id,
        len(rows),
        result["emotion_code"],
        result["risk_level"],
    )
    return AnalyzeResponse(**result)


# 최소 며칠은 있어야 "평소"를 정의할 수 있다. MLCM_210 은 14일을 규정하지만
# 연동 직후에는 그만큼 쌓이지 않으므로, 판정을 시작할 최소선만 둔다.
MIN_DAYS_FOR_BASELINE = 3


def _has_signal(rows: list) -> bool:
    """기준값을 만들 수 있을 만큼 실측치가 있는지."""
    # 0 도 제외한다. steps 는 스키마 기본값이 0 이라 수집이 안 돼도 0 이 채워지고,
    # 기준값이 0 이면 상대 편차 자체를 계산할 수 없다.
    sleeps = [r["total_sleep_min"] for r in rows if r["total_sleep_min"]]
    steps = [r["steps"] for r in rows if r["steps"]]
    return max(len(sleeps), len(steps)) >= MIN_DAYS_FOR_BASELINE


# ==========================================================================
#  모델 자리
# ==========================================================================

def _predict(rows: list) -> dict:
    """⚠ 임시 규칙 판정. 여기를 실제 모델로 교체한다.

    교체 시 구조:
        1차  LSTM Autoencoder — 정상 패턴 재구성 오차 -> anomaly_score
        2차  LightGBM         — anomaly_score + 피처 -> emotion_code, risk_score

    반환 계약은 바꾸지 말 것. 비즈니스 서버가 이 여섯 필드를 그대로 적재한다
    (backend/app/services/analysis.py).

    ---
    현재 규칙은 **모델의 근사가 아니라 자리 표시**다. 수면 부족과 활동량 급감이
    정서 저하와 상관이 있다는 것은 선행연구에서 반복 보고된 바지만, 아래 임계값은
    그 연구에서 가져온 값이 아니라 데모가 돌아가도록 임의로 정한 것이다.
    이 값으로 성능을 주장하면 안 된다.
    """
    recent = rows[-1]
    sleeps = [r["total_sleep_min"] for r in rows if r["total_sleep_min"]]
    steps = [r["steps"] for r in rows if r["steps"]]

    baseline_sleep = sum(sleeps) / len(sleeps) if sleeps else None
    baseline_steps = sum(steps) / len(steps) if steps else None

    # 개인별 기준 대비 편차. MLCM_210 이 규정한 "개인별 정규화" 의 자리다.
    anomaly = 0.0
    if baseline_sleep and recent["total_sleep_min"]:
        deficit = (baseline_sleep - recent["total_sleep_min"]) / baseline_sleep
        anomaly += max(0.0, deficit)
    if baseline_steps and recent["steps"] is not None:
        drop = (baseline_steps - recent["steps"]) / baseline_steps
        anomaly += max(0.0, drop) * 0.5

    anomaly = min(anomaly, 1.0)

    # 모델이 내놓아야 하는 것은 여기까지 — 감정 코드와 두 점수뿐이다.
    if anomaly >= 0.5:
        emotion_code = "SADNESS"
    elif anomaly >= 0.25:
        emotion_code = "ANXIETY"
    else:
        emotion_code = "HAPPINESS"

    emotion_score = round(min(anomaly * 120, 100), 2)

    return {
        "emotion_code": emotion_code,
        "emotion_score": emotion_score,
        "anomaly_score": round(anomaly, 4),
        "risk_level": risk_level_of(emotion_code, emotion_score),
        "risk_score": round(anomaly * 100, 2),
        "model_version": MODEL_VERSION,
    }


# ==========================================================================
#  위험 단계 매핑 — 04 문서 6항
# ==========================================================================

# EMOTIONS.category 가 기본값이다. schema.sql 의 마스터 9종과 같은 값이어야 한다.
# 여기에 복제해 둔 이유: 매 요청마다 EMOTIONS 를 조회하지 않기 위해서다.
# schema.sql 을 고치면 여기도 같이 고쳐야 한다.
EMOTION_CATEGORY = {
    "JOY": "NORMAL",
    "DELIGHT": "NORMAL",
    "HAPPINESS": "NORMAL",
    "SADNESS": "CAUTION",
    "ANXIETY": "CAUTION",
    "LONELINESS": "CAUTION",
    "ANGER": "CAUTION",
    "DESPAIR": "CRITICAL",
    "CRISIS": "CRITICAL",
}

ANGER_CRITICAL_THRESHOLD = 70.0


def risk_level_of(emotion_code: str, emotion_score: float) -> str:
    """감정 코드 + 강도 -> NORMAL / CAUTION / CRITICAL

    ⚠ 이 매핑은 **AI 서버만 수행한다**(04 문서 6항). 비즈니스 서버나 클라이언트가
      같은 계산을 다시 하면 규칙이 여러 곳에 생겨 반드시 어긋난다.
      비즈니스 서버는 값이 규격에 맞는지만 검사한다
      (backend/app/services/analysis.py 의 _persist).

    모델을 교체해도 이 함수는 그대로 둔다. 여기는 모델이 아니라 정책이다.
    """
    # CRISIS 는 점수와 무관하게 즉시 CRITICAL 이다.
    if emotion_code == "CRISIS":
        return "CRITICAL"

    # ANGER 만 동적 재분류한다. 분노는 강도에 따라 의미가 갈려서,
    # 낮으면 일상적 짜증이고 높으면 개입이 필요한 상태다.
    if emotion_code == "ANGER" and emotion_score >= ANGER_CRITICAL_THRESHOLD:
        return "CRITICAL"

    return EMOTION_CATEGORY.get(emotion_code, "CAUTION")


# ==========================================================================
#  위기 문맥 탐지는 여기에 없습니다
# ==========================================================================
#
# API 명세 초안은 POST /internal/analyze/crisis 를 이 서버에 두었으나,
# 구현은 비즈니스 서버(backend/app/services/) 에 있습니다. 이유는 두 가지입니다.
#
# 1. NFR-DV-003 이 "1차 키워드 필터는 외부 API 장애 시에도 단독 동작" 을
#    요구합니다. 위기 탐지를 AI 서버로 옮기면 **AI 서버가 죽는 순간 위기 탐지가
#    통째로 멈춥니다.** 키워드 필터를 비즈니스 서버에 중복으로 두면 그 자체가
#    규칙이 두 곳에 존재하는 문제가 됩니다.
# 2. 위기 탐지에는 학습 모델이 없습니다(안건 3 — 키워드 + OpenAI 프롬프트).
#    ML 서버로 보낼 이유가 없고 왕복만 한 번 늘어 NFR-DV-001 3초 요건에 불리합니다.
#
# → docs/API명세_초안.md 의 내부 API 절을 이 구조에 맞게 고쳐야 합니다.
