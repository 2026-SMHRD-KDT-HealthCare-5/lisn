"""AI 추론 서버 — MLCM_210

비즈니스 서버가 라이프로그 적재 후 호출한다. 내부 API 라 인증이 없고,
두 서버가 같은 네트워크 안에 있으며 이 포트를 외부에 열지 않는 것을 전제로 한다
(docs/결정/API설계_사전결정.md 7절).

실행:
    cd ai/server
    uvicorn main:app --reload --port 8001

판정 방식은 **개인 기준선 이탈 탐지**입니다. 그 사람의 최근 14일을 기준선으로
삼아 오늘이 얼마나 벗어났는지를 잽니다.

⚠ **감정을 분류하지 않습니다.** 라이프로그로 감정을 맞히는 것은
  빅데이터분석정의서가 실측으로 닫은 방향입니다(GLOBEM ROC-AUC 0.528 ·
  LifeSnaps 0.479~0.540, 참가자 단위 분할). 여기서 하는 일은 **평소와 오늘의
  대조**이고, 이탈 정도를 재는 것이지 감정을 맞히는 것이 아닙니다.

## 두 단계로 나뉩니다 (2026.08.25 개정)

    ① 지표 7개의 개인 기준선 이탈(z)을 잰다      ← 그대로
    ② 그 z 들을 하나의 이상치 점수로 합친다        ← **학습된 집계로 교체**

②는 원래 「상위 3개 평균 ÷ 4.0」이었고, 여기 주석에 **「임의값이다 · 성능
근거로 쓰지 말 것」**이라고 적혀 있었습니다. 실제로 재보니 그랬습니다.

    LifeSnaps · 참가자 62명 · 4086 표본 · 참가자 분할 + 중첩 교차검증
    참가자 내부 AUC   규칙 0.491  →  학습된 집계 0.609
    이득 +0.115 (참가자 단위 부트스트랩 95% +0.056 ~ +0.176)

**입력은 하나도 안 늘었습니다.** 이 서버가 이미 읽던 컬럼뿐입니다.
근거와 재현 방법은 `ai/train/eval_rule_features.py` ·
`docs/검증/학습모델_활용_시도_20260824.md`.

⚠ **경보 총량은 그대로입니다.** 모델 확률을 규칙 점수와 **같은 분포**로
  옮기기 때문입니다(`model_score.py`). 임계값 0.25·0.5 는 정책이라
  건드리지 않았고, 바뀐 것은 **누구에게 경보가 가는가**입니다.

⚠ **`model_version` 이 `rule-` 로 시작하면 학습된 집계가 관여하지 않은
  것입니다.** 모델 파일이 없거나 지표가 모자라면 기존 규칙으로 돕니다.
  그때는 임계값이 여전히 임의값이니 성능 근거로 쓰지 마세요.
"""

import logging
import os
import statistics
from datetime import datetime, timedelta, timezone

import asyncpg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pathlib import Path
from pydantic import BaseModel

import model_score

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="귀기울임 AI 추론 서버", version="0.1.0")

# ⚠ backend/.env 를 직접 읽는다.
#
#   전에는 os.getenv 만 썼다. 그런데 `cd ai\server; uvicorn main:app` 으로
#   띄우면 환경변수가 비어 있어 아래 기본값으로 붙고, PostgreSQL 이
#   "사용자 postgres 의 password 인증을 실패했습니다" 로 끊는다.
#
#   증상이 고약하다 — asyncpg 는 원인을 감추고
#   "connection was closed in the middle of operation" 만 던진다. 503 만 보고
#   전처리나 쿼리를 의심하게 된다(2026.08.02 실측에서 실제로 겪었다).
#
#   DB 는 비즈니스 서버와 같은 것을 보므로 설정도 그쪽 .env 를 그대로 쓴다.
#   AI 서버용으로 갈라야 하면 AI_DATABASE_URL 을 환경변수로 준다.
#
# ⚠ 컨테이너 안에서는 이 파일이 /app/main.py 하나뿐이라 parents[2] 가 없다.
#   인덱싱을 그대로 하면 IndexError 로 죽어 서버가 통째로 못 뜬다(2026.08.24,
#   infra/ 배포 첫 기동 때 실제로 겪었다 — crash loop). 로컬(repo 안에 있을
#   때)만 조상 경로가 3단 이상이므로, 그만큼 깊이가 있을 때만 계산한다.
_SELF = Path(__file__).resolve()
_BACKEND_ENV = _SELF.parents[2] / "backend" / ".env" if len(_SELF.parents) > 2 else None
if _BACKEND_ENV and _BACKEND_ENV.exists():
    load_dotenv(_BACKEND_ENV, override=False)

# 비즈니스 서버와 같은 DB 를 본다. 페이로드로 시퀀스를 실어 보내면 요청이
# 비대해지고, 전처리 규격이 바뀔 때마다 양쪽을 함께 고쳐야 한다.
DATABASE_URL = os.getenv(
    "AI_DATABASE_URL",
    os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lisn"),
).replace("postgresql+asyncpg://", "postgresql://")

# MLCM_210 2단계가 "최근 14일 평소 활동/생체 데이터(개인별 Min-Max 정규화 기준값)"
# 를 규정한다. GLOBEM 의 14일 집계 단위와도 일치한다.
BASELINE_DAYS = 14

# ⚠ **모델이 아니다.** 규칙 기반 판정임이 적재된 행마다 남도록 이름에 박아둔다.
#
#   전에는 rule-placeholder-v0 이었다. 「모델이 준비될 때까지의 자리」라는
#   뜻이었는데, 빅데이터분석정의서가 지도학습을 실측으로 닫고 **규칙 기반을 정식 방법으로
#   채택**했으므로 placeholder 가 아니다. 다만 여전히 모델은 아니라서
#   rule- 접두사는 유지한다 — 이 값이 보이면 성능 근거로 쓰지 말 것.
MODEL_VERSION = "rule-baseline-v1"


class AnalyzeRequest(BaseModel):
    user_id: str
    evaluated_at: datetime | None = None


class AnalyzeResponse(BaseModel):
    """⚠ 위 6필드가 비즈니스 서버와의 계약이다. 순서·이름을 바꾸지 말 것.

    아래 둘은 `MLCM_220`(선제 접촉)용으로 **덧붙인** 것이다. 비즈니스 서버의
    `_persist` 는 필요한 키만 골라 쓰므로 추가 필드가 있어도 깨지지 않는다.
    """

    emotion_code: str
    emotion_score: float
    anomaly_score: float
    risk_level: str
    risk_score: float
    model_version: str

    # 마지막 날부터 연속으로 이탈한 일수. MLCM_220 이 이 값으로 발동한다.
    streak_days: int = 0
    # 이탈이 큰 지표 이름. 선제 접촉 문구가 "무엇이 달라졌는지" 말할 때 쓴다.
    deviant_features: list[str] = []
    # 학습된 집계를 쓰기 전의 규칙 점수. 관제에서 둘을 나란히 볼 수 있게 남긴다.
    # 모델을 못 쓴 경우에는 anomaly_score 와 같은 값이 온다.
    rule_anomaly_score: float = 0.0


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
                   sleep_start_at, sleep_onset_min, awake_min, activity_start_at,
                   heart_rate, hrv,
                   screen_time_min, night_screen_min, app_session_count
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
#  개인 기준선 이탈 탐지 — MLCM_210
# ==========================================================================
#
# ⚠ **이건 감정을 맞히는 것이 아니다.** 라이프로그로 감정을 분류하는 것은
#   빅데이터분석정의서가 실측으로 닫은 방향이다(GLOBEM ROC-AUC 0.528 ·
#   LifeSnaps 0.479~0.540). 여기서 하는 일은 **그 사람의 평소와 오늘을
#   비교하는 것**이고, 그건 분류가 아니라 기술통계라 라벨이 필요 없다.
#
#   그래서 정확도를 주장하지 않는다. 「평소와 다르다」는 맞고 틀림을 가릴
#   대상이 아니라 측정값이다.
#
# ⚠ **2026.08.25 개정 — 아래 z 계산은 그대로다. 바뀐 것은 합치는 방식뿐이다.**
#   `_predict` 가 이 z 들을 `model_score` 에 넘겨 학습된 집계를 쓴다.
#   여전히 감정을 분류하지 않는다. 「평소와 얼마나 다른가」를 더 잘 합치는
#   방법을 데이터로 고른 것이고, 대상 라벨은 그 합침이 쓸 만한지 검증하는
#   데만 썼다.

# 판정에 쓰는 지표와 **나쁜 쪽 방향**.
#
# ⚠ 방향이 중요하다. 평소보다 **더 잘 잔** 날은 이탈이 아니다. 양방향으로
#   세면 컨디션 좋은 날에 「이상」이 뜬다.
#
# ⚠ 심박·HRV 는 넣지 않았다. 기업 제공 데이터에 없고, 삼성헬스가 Health
#   Connect 에 HRV 를 쓰지 않아 실기기에서도 안 들어온다
#   (→ docs/진행/구현_갭.md).
_FEATURES = [
    ("총수면",     "total_sleep_min",      "down"),
    ("걸음수",     "steps",                "down"),
    ("수면효율",   "sleep_efficiency_pct", "down"),
    ("입면지연",   "sleep_onset_min",      "up"),
    ("야간각성",   "awake_min",            "up"),
    ("입면시각",   "_sleep_start_min",     "up"),
    ("활동개시",   "_activity_start_min",  "up"),
    # [05-U] 앱 사용 로그 — 기업 브리프 개발목표의 「앱 사용 로그 + 웨어러블」.
    #
    # ⚠ **무슨 앱을 썼는지는 보지 않는다.** 패키지명·앱 이름은 애초에 수집하지
    #   않고, 여기서도 「평소와 다른가」만 잰다. 나머지 지표와 완전히 같은
    #   방식(개인 14일 기준선 대비 robust z)이라 특별 취급이 없다.
    #
    # ⚠ 방향이 전부 up 이다 — 화면을 평소보다 **더** 오래 보거나, **밤에** 더
    #   보거나, **더 자주** 집어들면 이탈로 센다. 줄어드는 쪽은 이탈이 아니다.
    #
    # ⚠ 값이 없으면(특별권한 미승인) `_robust_z` 가 None 을 돌려주고 그냥
    #   빠진다. 웨어러블 지표만으로 판정이 계속된다.
    ("화면사용",   "screen_time_min",      "up"),
    ("야간사용",   "night_screen_min",     "up"),
    ("앱전환",     "app_session_count",    "up"),
]

# 이탈로 셀 z 값과, 그런 지표가 몇 개여야 「이탈한 날」로 볼지.
#
# ⚠ **임의값이다.** 선행연구에서 가져온 값이 아니다. 성능 근거로 쓰지 말 것.
DEVIATION_Z = 2.0
MIN_DEVIANT_FEATURES = 2

# anomaly_score 를 1.0 으로 채우는 z. 이것도 임의값이다.
FULL_SCALE_Z = 4.0

MODEL_VERSION_NOTE = "규칙 기반 판정 — 모델이 아니다"


def _get(r, key):
    """asyncpg.Record 와 dict 를 함께 받는다. 없는 키는 None."""
    try:
        return r[key]
    except (KeyError, IndexError, TypeError):
        return None


def _sleep_start_min(r):
    """입면 시각을 **18시 기준 분**으로. 자정을 넘어도 단조증가한다.

    23:30 -> 330 · 01:00 -> 420. 그냥 자정 기준으로 재면 23:30(1410)과
    01:00(60)이 하루를 사이에 두고 뒤집혀, **더 늦게 잔 것이 더 이른 것**으로
    계산된다.
    """
    dt = _get(r, "sleep_start_at")
    if dt is None:
        return None
    m = dt.hour * 60 + dt.minute
    return m - 1080 if m >= 1080 else m + 360


def _activity_start_min(r):
    """활동 개시 시각을 자정 기준 분으로. 늦어질수록 크다."""
    dt = _get(r, "activity_start_at")
    if dt is None:
        return None
    return dt.hour * 60 + dt.minute


_DERIVED = {
    "_sleep_start_min": _sleep_start_min,
    "_activity_start_min": _activity_start_min,
}


def _value(r, key):
    """지표 하나를 float 로.

    ⚠ **NUMERIC 컬럼은 asyncpg 가 `Decimal` 로 준다.** `sleep_efficiency_pct`
      가 그렇고, float 와 섞어 곱하면 `TypeError` 로 판정이 통째로 죽는다.
      실제로 데모 시드에서 500 이 났다. 들어오는 자리에서 한 번에 맞춘다.
    """
    fn = _DERIVED.get(key)
    v = fn(r) if fn else _get(r, key)
    return None if v is None else float(v)


def _robust_z(value, history_values):
    """중앙값·MAD 기준 z. 잴 수 없으면 None.

    ⚠ **평균·표준편차를 쓰지 않는다.** 워치를 하루 안 찬 날 하나가 평균을
      끌어내리면, 그 다음 날이 멀쩡한데도 이탈로 잡힌다. 중앙값은 그런
      한 점에 흔들리지 않는다.

    ⚠ **MAD 가 0 이어도 포기하지 않는다.** 값이 절반 이상 같으면 MAD 가 0 이
      되는데, 그때 「못 잰다」로 넘기면 **가장 규칙적인 사람의 이탈을 통째로
      놓친다.** 매일 400분 자던 사람이 200분 잔 날이 정확히 그 경우다.

      평균절대편차(MeanAD)로 넘어가고, 그것도 0 이면 기준선이 완전히 평평한
      것이므로 **다르기만 하면 최대 이탈**로 본다. Iglewicz-Hoaglin 이
      권하는 폴백이다.
    """
    vals = [v for v in history_values if v is not None]
    if value is None or len(vals) < MIN_DAYS_FOR_BASELINE:
        return None

    med = statistics.median(vals)
    diff = value - med

    mad = statistics.median([abs(v - med) for v in vals])
    if mad:
        return 0.6745 * diff / mad

    mean_ad = sum(abs(v - med) for v in vals) / len(vals)
    if mean_ad:
        return diff / (1.253314 * mean_ad)

    # 기준선이 완전히 평평하다. 같으면 0, 다르면 최대.
    if diff == 0:
        return 0.0
    return FULL_SCALE_Z if diff > 0 else -FULL_SCALE_Z


def _deviations(day, history):
    """지표별 **나쁜 쪽 이탈 정도**. 좋은 쪽으로 벗어난 것은 0 이다."""
    out = {}
    for label, key, direction in _FEATURES:
        z = _robust_z(_value(day, key), [_value(h, key) for h in history])
        if z is None:
            continue
        dev = z if direction == "up" else -z
        if dev > 0:
            out[label] = dev
    return out


def _measures(day, history):
    """학습된 집계에 넘길 재료 — 지표마다 (오늘 값, z, 기준선 중앙값).

    ⚠ `_deviations` 와 달리 **좋은 쪽 이탈도 그대로** 넘긴다. 규칙은 나쁜
      쪽만 세지만, 학습된 집계는 방향까지 스스로 배우기 때문이다.
    """
    out = {}
    for _, key, _ in _FEATURES:
        v = _value(day, key)
        hist = [_value(h, key) for h in history]
        z = _robust_z(v, hist)
        vals = [x for x in hist if x is not None]
        base = statistics.median(vals) if vals else None
        out[key] = (v, z, base)
    return out


def _is_deviant(devs):
    """이탈한 날인가 — 지표 하나만 튀는 것은 측정 오차일 수 있다."""
    return sum(1 for d in devs.values() if d >= DEVIATION_Z) >= MIN_DEVIANT_FEATURES


# ⚠ **아는 한계 — 서서히 나빠지는 것은 약하게 잡힌다.**
#
#   z 는 「최근 분포 대비 오늘이 튀는가」를 본다. 그래서 하루아침에 무너지면
#   크게 잡히지만, **2주에 걸쳐 조금씩 나빠지면 분포 자체가 넓어져** z 가
#   커지지 않는다.
#
#   데모 시드에서 실제로 그렇다. 총수면이 421분 -> 171분으로 반토막인데
#   `deviant_features` 에는 수면효율·입면지연만 뜬다. 중간값들이 고르게
#   퍼져 MAD 가 커졌기 때문이다.
#
#   `streak_days` 가 이걸 부분적으로 보완한다 — 각 날을 **그 날 이전** 기록만
#   으로 보므로 초반에는 분포가 좁아 잡힌다. 데모에서 8일이 나오는 이유다.
#
#   제대로 잡으려면 **추세 검정**(Mann-Kendall 등)이 따로 필요하다. 넣지
#   않은 이유는 검증할 라벨이 없어서다 — 빅데이터분석정의서가 닫은 그 문제와 같다.
#   우울이 서서히 진행되는 경우가 많다는 점에서 **이건 실제 한계**다.


def _streak(rows):
    """마지막 날부터 **연속으로** 이탈한 일수 — `MLCM_220` 트리거.

    각 날을 그 날 **이전** 기록만으로 판정한다. 뒤에서부터 세다가 이탈이
    아닌 날을 만나면 멈춘다.
    """
    n = 0
    for i in range(len(rows) - 1, 0, -1):
        if not _is_deviant(_deviations(rows[i], rows[:i])):
            break
        n += 1
    return n


def _predict(rows: list) -> dict:
    """개인 기준선 대비 이탈을 정량화한다 — `MLCM_210`.

    반환 6필드는 비즈니스 서버와의 계약이다(`backend/app/services/analysis.py`).
    `streak_days`·`deviant_features` 는 `MLCM_220`(선제 접촉)용으로 **덧붙인**
    것이라 기존 6필드를 건드리지 않는다.

    ⚠ `risk_level` 은 여기서 만들지 않고 `risk_level_of()` 를 부른다.
      데이터베이스요구사항분석서 6항이 정한 정책이고, 여기서 다시 계산하면 규칙이 두 곳에 생긴다.
    """
    day = rows[-1]

    # ⚠ 기준선에서 **오늘을 뺀다.** MLCM_210 2단계의 "평소"는 판정 대상일
    #   이전의 패턴이다. 오늘을 넣으면 오늘이 스스로를 정상 쪽으로 끌어당겨
    #   편차가 작게 나온다 — 안전 기능에서 그 방향은 **미탐**이다.
    history = rows[:-1]
    devs = _deviations(day, history)

    # 위에서 셋만 본다. 일곱 개 평균을 내면 두 지표가 크게 벗어나도 나머지
    # 다섯에 희석돼 신호가 사라진다.
    top = sorted(devs.values(), reverse=True)[:3]
    rule_anomaly = min(1.0, (sum(top) / len(top) / FULL_SCALE_Z)) if top else 0.0

    # ⚠ **여기가 유일하게 바뀐 곳이다.** 위의 z 계산(①단계)은 그대로 두고,
    #   「상위 3개 평균 / 4.0」이라는 **임의 집계만** 학습된 것으로 바꾼다.
    #   입력이 늘지 않으므로 지금 읽는 컬럼만으로 돈다.
    #
    #   근거 — LifeSnaps 참가자 62명 · 4086 표본 · 참가자 분할 + 중첩 CV
    #   참가자 내부 AUC 0.491(규칙) -> 0.609(학습), 이득 +0.115
    #   (참가자 단위 부트스트랩 95% +0.056~+0.176)
    #   → ai/train/eval_rule_features.py
    #
    #   ⚠ 모델을 못 쓰면 version 이 None 으로 와서 **기존 규칙 그대로** 돈다.
    anomaly, model_ver = model_score.score(_measures(day, history), rule_anomaly)

    # ⚠ **감정을 식별하는 것이 아니다.** 이탈 정도를 9종 코드로 옮기는
    #   규칙일 뿐이고, 빅데이터분석정의서가 "감정 코드는 라벨이 없어 규칙 기반으로 산출한다"
    #   고 기록한 그 부분이다. 발표에서 "감정을 분류한다"고 말하지 말 것.
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
        # 규칙 점수도 남긴다 — 관제에서 둘을 나란히 볼 수 있어야 한다
        "rule_anomaly_score": round(rule_anomaly, 4),
        # ⚠ 규칙으로 돈 경우에는 `rule-` 접두사가 유지된다. 응답만 보고도
        #   모델이 관여했는지 구분할 수 있어야 하기 때문이다.
        "model_version": model_ver or MODEL_VERSION,
        # --- MLCM_220 용 부가 정보 (기존 6필드와 별개) ---
        "streak_days": _streak(rows),
        # 이탈이 큰 순서. 선제 접촉 문구가 "무엇이 달라졌는지" 말할 때 쓴다.
        "deviant_features": [
            k for k, _ in sorted(devs.items(), key=lambda kv: -kv[1])
            if devs[k] >= DEVIATION_Z
        ],
    }


# ==========================================================================
#  위험 단계 매핑 — 데이터베이스요구사항분석서 6항
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

    ⚠ 이 매핑은 **AI 서버만 수행한다**(데이터베이스요구사항분석서 6항). 비즈니스 서버나 클라이언트가
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
# docs/결정/API명세_초안.md 의 내부 API 절도 이 구조로 고쳤습니다(2026.08.01 철회 표기).
