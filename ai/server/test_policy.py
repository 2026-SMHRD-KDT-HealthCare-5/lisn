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
#  risk_level_of — 데이터베이스요구사항분석서 6항
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

    # ⚠ **여섯이 다 있는지**를 본다. 같은지가 아니다 — MLCM_220 용 부가
    #   필드(streak_days·deviant_features)를 덧붙일 수 있어야 한다.
    #   비즈니스 서버의 _persist 는 필요한 키만 골라 쓴다.
    assert {
        "emotion_code",
        "emotion_score",
        "anomaly_score",
        "risk_level",
        "risk_score",
        "model_version",
    } <= set(result)
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


def test_규칙_판정임이_model_version_에_드러난다():
    """이 값이 남아 있는 한 성능 근거로 쓸 수 없다는 표시가 된다.

    실제 모델을 넣으면 MODEL_VERSION 을 바꾸게 되고, 이 테스트가 실패하면서
    「이제 진짜 모델」이라는 사실을 문서·발표자료에 반영하도록 강제한다.

    ⚠ 전에는 `rule-placeholder` 였다. 빅데이터분석정의서가 지도학습을 실측으로 닫고 규칙
      기반을 **정식 방법으로 채택**했으므로 「자리 표시」가 아니다. 다만
      모델은 아니라서 `rule-` 은 유지한다.
    """
    assert MODEL_VERSION.startswith("rule-")

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

    오늘을 기준선에 넣으면 오늘이 스스로를 정상 쪽으로 끌어당겨 편차가
    작아진다. 안전 기능이라 그 방향이 **미탐**이다.

    ⚠ **수치를 고정하지 않는다.** 임계값이 임의값이라 박아두면 조정을
      방해한다. 대신 **성질**을 본다 — 평소와 다른 날이 같은 날보다 커야 한다.
    """
    deviated = [row(sleep=400) for _ in range(5)] + [row(sleep=200)]
    steady = [row(sleep=400) for _ in range(5)] + [row(sleep=400)]

    assert _predict(deviated)["anomaly_score"] > _predict(steady)["anomaly_score"]
    assert _predict(steady)["anomaly_score"] == 0.0


def test_기준선이_완전히_일정해도_이탈을_잡는다():
    """MAD 가 0 이라고 넘기면 **가장 규칙적인 사람을 통째로 놓친다.**

    매일 400분 자던 사람이 200분 잔 날이 정확히 그 경우다. 절반 이상이
    같은 값이면 MAD 가 0 이 되는데, 실제 데이터에서도 드물지 않다.
    """
    rows = [row(sleep=400) for _ in range(5)] + [row(sleep=200)]
    assert _predict(rows)["anomaly_score"] > 0.0


def test_히스토리가_없으면_나눗셈을_하지_않는다():
    """행이 하나뿐이면 뺄 것을 빼고 나면 기준값이 없다. 죽지 않아야 한다."""
    result = _predict([row(sleep=400, steps=3000)])
    assert result["anomaly_score"] == 0.0


# ==========================================================================
#  개인 기준선 이탈 — 2026.08.03 신설
# ==========================================================================


def day(**kw):
    """시각 컬럼까지 넣을 수 있는 행. `row()` 보다 넓다."""
    base = {
        "collected_at": None,
        "steps": None,
        "total_sleep_min": None,
        "sleep_efficiency_pct": None,
        "sleep_start_at": None,
        "sleep_onset_min": None,
        "awake_min": None,
        "activity_start_at": None,
        "heart_rate": None,
        "hrv": None,
    }
    base.update(kw)
    return base


def test_좋은_쪽_이탈은_이상이_아니다():
    """평소보다 **더 잘 잔** 날에 「이상」이 뜨면 안 된다.

    양방향으로 재면 컨디션 좋은 날마다 경보가 울린다. 사용자가 신뢰를
    잃으면 정작 필요할 때 무시한다.
    """
    better = [day(total_sleep_min=v) for v in (380, 400, 390, 410, 395)]
    better.append(day(total_sleep_min=600))          # 평소보다 3시간 더 잠
    assert _predict(better)["anomaly_score"] == 0.0


def test_입면_시각이_자정을_넘어도_늦어진_것으로_센다():
    """23:30 -> 01:00 은 **늦어진** 것이다.

    자정 기준 분으로 재면 1410 -> 60 이라 「빨라졌다」로 뒤집힌다. 새벽까지
    못 자는 것이 정확히 우리가 잡아야 하는 신호인데 부호가 반대가 된다.
    """
    from datetime import datetime

    def at(h, m):
        return datetime(2026, 8, 1, h, m)

    rows = [day(sleep_start_at=at(23, 30), total_sleep_min=400) for _ in range(5)]
    rows.append(day(sleep_start_at=at(2, 30), total_sleep_min=400))

    result = _predict(rows)
    assert "입면시각" in result["deviant_features"], result


def test_연속_이탈일수를_센다():
    """MLCM_220 은 이 값으로 발동한다. 하루 튄 것과 사흘 이어진 것은 다르다."""
    steady = [day(total_sleep_min=400, steps=6000) for _ in range(6)]
    assert _predict(steady)["streak_days"] == 0

    drifting = steady[:4] + [
        day(total_sleep_min=200, steps=1000),
        day(total_sleep_min=180, steps=800),
    ]
    assert _predict(drifting)["streak_days"] >= 2


def test_지표_하나만_튀면_이탈로_세지_않는다():
    """측정 오차일 수 있다. 하루 워치를 늦게 찬 것만으로 접촉하면 안 된다."""
    rows = [day(total_sleep_min=400, steps=6000) for _ in range(5)]
    rows.append(day(total_sleep_min=200, steps=6000))     # 수면만 이탈
    assert _predict(rows)["streak_days"] == 0


def test_이탈한_지표_이름을_돌려준다():
    """선제 접촉 문구가 "무엇이 달라졌는지" 말하려면 필요하다.

    근거 없는 접촉은 감시로 읽힌다.
    """
    rows = [day(total_sleep_min=400, steps=6000) for _ in range(5)]
    rows.append(day(total_sleep_min=180, steps=500))
    feats = _predict(rows)["deviant_features"]
    assert "총수면" in feats and "걸음수" in feats, feats


def test_NUMERIC_컬럼이_Decimal_로_와도_죽지_않는다():
    """asyncpg 는 NUMERIC 을 `Decimal` 로 준다.

    float 와 섞어 곱하면 TypeError 로 판정이 통째로 죽는다. 데모 시드에서
    실제로 500 이 났다 — `sleep_efficiency_pct` 가 NUMERIC(5,2) 이다.
    """
    from decimal import Decimal

    rows = [day(sleep_efficiency_pct=Decimal(str(v)), total_sleep_min=400)
            for v in (93.5, 92.8, 94.1, 93.0, 91.9)]
    rows.append(day(sleep_efficiency_pct=Decimal("70.4"), total_sleep_min=200))

    result = _predict(rows)
    assert 0.0 <= result["anomaly_score"] <= 1.0
