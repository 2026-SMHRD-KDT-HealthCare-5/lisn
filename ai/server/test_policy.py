"""AI 추론 서버 정책 테스트 — DB 없이 돕니다.

여기서 고정하는 것은 **모델이 아니라 정책**입니다. `_predict()` 를 LSTM AE +
LightGBM 으로 교체해도 이 테스트는 그대로 통과해야 합니다.

**통과하지 않으면 모델을 넣으면서 정책을 같이 들어낸 것입니다.**

    python -m pytest ai/server -q
"""

import re
from pathlib import Path

import pytest

from main import (
    EMOTION_CATEGORY,
    MIN_DAYS_FOR_BASELINE,
    MODEL_VERSION,
    _has_signal,
    _predict,
    risk_level_of,
)


def row(steps=None, sleep=None):
    """lifelog_metrics 한 행 흉내. asyncpg.Record 는 dict 처럼 첨자 접근한다."""
    return {
        "collected_at": None,
        "steps": steps,
        "total_sleep_min": sleep,
        "sleep_efficiency_pct": None,
        "heart_rate": None,
        "hrv": None,
    }


# ==========================================================================
#  risk_level_of — 04 문서 6항
# ==========================================================================


SCHEMA_SQL = Path(__file__).resolve().parents[2] / "db" / "schema.sql"


def emotions_from_schema() -> dict[str, str]:
    """schema.sql 의 EMOTIONS 시드에서 코드 -> 카테고리를 읽는다.

    상수를 여기 또 적으면 정본이 세 곳이 된다. 파일을 직접 읽는다.
    """
    text = SCHEMA_SQL.read_text(encoding="utf-8")
    block = re.search(
        r"INSERT\s+INTO\s+EMOTIONS[^;]*?VALUES(.*?);", text, re.DOTALL | re.IGNORECASE
    )
    assert block, "schema.sql 에서 EMOTIONS 시드를 찾지 못했습니다"

    return {
        code: category
        for code, category in re.findall(
            r"\(\s*'(\w+)'\s*,\s*'[^']*'\s*,\s*'(\w+)'\s*\)", block.group(1)
        )
    }


def test_감정_마스터가_schema_sql_과_같다():
    """EMOTION_CATEGORY 는 schema.sql 감정 마스터의 복제본이다.

    요청마다 EMOTIONS 를 조회하지 않으려고 복제해 뒀다. 한쪽만 고치면 AI 서버가
    내려준 emotion_code 를 비즈니스 서버가 적재하지 **못하고 조용히 건너뛴다.**
    로그에 경고만 남아서 「분석이 가끔 안 된다」로 보인다.
    """
    master = emotions_from_schema()
    assert len(master) == 9, f"파싱된 감정: {sorted(master)}"
    assert EMOTION_CATEGORY == master, (
        "schema.sql 을 고쳤으면 ai/server/main.py 의 EMOTION_CATEGORY 도 고쳐야 합니다.\n"
        f"  schema.sql: {sorted(master.items())}\n"
        f"  main.py   : {sorted(EMOTION_CATEGORY.items())}"
    )


def test_CRISIS_는_점수와_무관하게_항상_CRITICAL():
    """위기는 강도로 깎지 않는다. 0점이어도 CRITICAL 이다."""
    assert risk_level_of("CRISIS", 0.0) == "CRITICAL"
    assert risk_level_of("CRISIS", 100.0) == "CRITICAL"


def test_ANGER_만_강도로_재분류된다():
    """분노는 낮으면 일상적 짜증, 높으면 개입이 필요한 상태다."""
    assert risk_level_of("ANGER", 69.9) == "CAUTION"
    assert risk_level_of("ANGER", 70.0) == "CRITICAL"

    # 다른 감정은 점수가 높아도 카테고리가 바뀌지 않는다.
    assert risk_level_of("SADNESS", 100.0) == "CAUTION"
    assert risk_level_of("HAPPINESS", 100.0) == "NORMAL"


def test_모르는_감정코드는_NORMAL_로_떨어지지_않는다():
    """오타·미등록 코드가 「안전함」으로 읽히면 위험을 놓친다.

    모르면 CAUTION 이다. 관제 대시보드에 남아 사람이 보게 된다.
    """
    assert risk_level_of("UNKNOWN_CODE", 0.0) == "CAUTION"
    assert risk_level_of("", 0.0) == "CAUTION"


# ==========================================================================
#  _has_signal — 데이터가 없을 때 NORMAL 을 만들지 않는다
# ==========================================================================


def test_실측치가_모자라면_판정하지_않는다():
    rows = [row(sleep=400) for _ in range(MIN_DAYS_FOR_BASELINE - 1)]
    assert _has_signal(rows) is False

    rows.append(row(sleep=400))
    assert _has_signal(rows) is True


def test_steps_0_은_실측치로_치지_않는다():
    """steps 는 스키마 기본값이 0 이라 수집이 안 돼도 0 이 채워진다.

    이걸 실측치로 세면 「권한만 승인하고 수집은 안 된」 사용자가 편차 0 →
    NORMAL 로 기록된다. 그건 정상이 아니라 모름이다.
    """
    rows = [row(steps=0) for _ in range(10)]
    assert _has_signal(rows) is False


def test_행은_있는데_전부_비어_있으면_거부한다():
    rows = [row() for _ in range(14)]
    assert _has_signal(rows) is False


def test_수면이나_활동_중_하나만_있어도_판정한다():
    """Health Connect 는 기기·권한에 따라 주는 항목이 다르다.

    둘 다 있어야 판정한다고 하면 활동만 주는 기기가 영영 분석되지 않는다.
    """
    only_steps = [row(steps=3000) for _ in range(MIN_DAYS_FOR_BASELINE)]
    only_sleep = [row(sleep=380) for _ in range(MIN_DAYS_FOR_BASELINE)]
    assert _has_signal(only_steps) is True
    assert _has_signal(only_sleep) is True


# ==========================================================================
#  _predict — 계약만 검사한다 (수치는 임의값이라 고정하지 않는다)
# ==========================================================================


def test_반환_계약_6필드를_지킨다():
    """비즈니스 서버가 이 여섯 필드를 그대로 EMOTION_RISK_SCORES 에 적재한다.

    ⚠ 값이 아니라 **계약**을 검사한다. 지금 임계값은 선행연구값이 아니라
      데모용 임의값이라 고정하면 모델 교체를 방해한다.
    """
    rows = [row(steps=5000, sleep=420) for _ in range(14)]
    result = _predict(rows)

    assert set(result) == {
        "emotion_code",
        "emotion_score",
        "anomaly_score",
        "risk_level",
        "risk_score",
        "model_version",
    }
    assert result["emotion_code"] in EMOTION_CATEGORY
    assert 0.0 <= result["emotion_score"] <= 100.0
    assert 0.0 <= result["anomaly_score"] <= 1.0
    assert result["risk_level"] in {"NORMAL", "CAUTION", "CRITICAL"}


def test_risk_level_은_risk_level_of_가_정한_값과_같다():
    """_predict 가 자체 매핑을 만들면 정책이 두 곳에 생긴다."""
    rows = [row(steps=5000, sleep=420) for _ in range(13)] + [row(steps=200, sleep=120)]
    result = _predict(rows)
    assert result["risk_level"] == risk_level_of(
        result["emotion_code"], result["emotion_score"]
    )


def test_임시_판정임이_model_version_에_드러난다():
    """이 값이 남아 있는 한 성능 근거로 쓸 수 없다는 표시가 된다.

    실제 모델을 넣으면 MODEL_VERSION 을 바꾸게 되고, 이 테스트가 실패하면서
    「이제 진짜 모델」이라는 사실을 문서·발표자료에 반영하도록 강제한다.
    """
    assert MODEL_VERSION.startswith("rule-placeholder")

    rows = [row(steps=5000, sleep=420) for _ in range(14)]
    assert _predict(rows)["model_version"] == MODEL_VERSION


@pytest.mark.parametrize("sleep", [None, 0])
def test_기준값이_0_이거나_없으면_나눗셈을_하지_않는다(sleep):
    """0 으로 나누면 ZeroDivisionError 로 분석이 통째로 죽는다."""
    rows = [row(steps=5000, sleep=sleep) for _ in range(14)]
    result = _predict(rows)
    assert 0.0 <= result["anomaly_score"] <= 1.0


# ==========================================================================
#  기준값에 오늘이 섞이던 것 — 2026.08.02 점검
# ==========================================================================


def test_기준값에_오늘을_넣지_않는다():
    """"평소"는 판정 대상일 **이전**의 패턴이다(MLCM_210 2단계).

    오늘을 평균에 넣으면 오늘이 스스로를 정상 쪽으로 끌어당겨 편차가 실제보다
    작아진다. 안전 기능이라 그 방향이 **미탐**이다.

    아래는 평소 400분 자던 사람이 오늘 200분만 잔 경우다.
      오늘 제외  기준 400 -> 편차 (400-200)/400 = 0.5
      오늘 포함  기준 366.7 -> 편차 0.4545      ← 과소평가
    """
    rows = [row(sleep=400) for _ in range(5)] + [row(sleep=200)]
    assert _predict(rows)["anomaly_score"] == 0.5


def test_히스토리가_없으면_나눗셈을_하지_않는다():
    """행이 하나뿐이면 뺄 것을 빼고 나면 기준값이 없다. 죽지 않아야 한다."""
    result = _predict([row(sleep=400, steps=3000)])
    assert result["anomaly_score"] == 0.0
