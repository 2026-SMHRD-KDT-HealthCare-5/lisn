# -*- coding: utf-8 -*-
"""학습된 집계가 판정에 들어간 뒤에도 지켜야 하는 것들.

    cd ai/server
    python -m pytest test_model_score.py -q

여기서 지키는 것은 **성능이 아니라 안전 성질**입니다. 성능 근거는
`ai/train/eval_rule_features.py` 가 냅니다.
"""
from datetime import datetime, timedelta, timezone

import pytest

import main
import model_score


def make_day(d, sleep=420, steps=8000, eff=92, onset=10, awake=40,
             sleep_hour=23, act_hour=8):
    base = datetime(2026, 8, 1, tzinfo=timezone.utc) + timedelta(days=d)
    return {
        "collected_at": base,
        "steps": steps,
        "total_sleep_min": sleep,
        "sleep_efficiency_pct": eff,
        "sleep_onset_min": onset,
        "awake_min": awake,
        "sleep_start_at": base.replace(hour=sleep_hour % 24),
        "activity_start_at": base.replace(hour=act_hour),
        "heart_rate": 70,
        "hrv": None,
    }


NORMAL = [make_day(i) for i in range(14)]
COLLAPSED = [make_day(i) for i in range(13)] + [
    make_day(13, sleep=180, steps=900, eff=61, onset=75, awake=160,
             sleep_hour=3, act_hour=13)
]


@pytest.fixture
def no_model(monkeypatch):
    """모델을 못 쓰는 상태로 만든다."""
    monkeypatch.setattr(model_score, "_art", None)
    monkeypatch.setattr(model_score, "_load_failed", True)


def test_계약_6필드가_그대로다():
    r = main._predict(NORMAL)
    for k in ("emotion_code", "emotion_score", "anomaly_score",
              "risk_level", "risk_score", "model_version"):
        assert k in r, f"{k} 가 빠지면 비즈니스 서버가 깨진다"


def test_모델이_없으면_규칙으로_돈다(no_model):
    """⚠ 이 성질을 없애지 마세요 — 모델 파일이 빠져도 판정은 계속돼야 합니다."""
    r = main._predict(COLLAPSED)
    assert r["model_version"].startswith("rule-"), (
        "폴백일 때는 rule- 접두사가 유지돼야 응답만 보고 구분할 수 있다")
    assert r["anomaly_score"] == r["rule_anomaly_score"]


def test_모델이_있으면_버전이_바뀐다():
    if not model_score.available():
        pytest.skip("모델 파일이 없습니다 — train_service_model.py 를 먼저 돌리세요")
    r = main._predict(COLLAPSED)
    assert not r["model_version"].startswith("rule-")
    assert r["model_version"] == model_score.MODEL_VERSION


def test_규칙_바닥이_지켜진다():
    """규칙이 크게 튄 날은 모델이 낮게 봐도 그 아래로 내려가지 않는다."""
    if not model_score.available():
        pytest.skip("모델 파일이 없습니다")
    r = main._predict(COLLAPSED)
    floor = model_score._load()["rule_floor"]
    if r["rule_anomaly_score"] >= floor:
        assert r["anomaly_score"] >= r["rule_anomaly_score"], (
            "규칙 바닥 위에서는 점수가 규칙 아래로 내려가면 안 된다")


def test_점수는_0과_1_사이다():
    for rows in (NORMAL, COLLAPSED):
        r = main._predict(rows)
        assert 0.0 <= r["anomaly_score"] <= 1.0
        assert 0.0 <= r["rule_anomaly_score"] <= 1.0


def test_risk_level_은_정책_그대로다():
    """`risk_level_of` 는 모델이 아니라 정책이다 — 모델 도입과 무관하다."""
    assert main.risk_level_of("CRISIS", 0.0) == "CRITICAL"
    assert main.risk_level_of("ANGER", 80.0) == "CRITICAL"
    assert main.risk_level_of("ANGER", 10.0) == main.EMOTION_CATEGORY["ANGER"]


def test_이탈_지표와_streak_는_규칙이_계속_만든다():
    """MLCM_220 선제 접촉 문구가 쓰는 값이라 모델과 무관해야 한다."""
    r = main._predict(COLLAPSED)
    assert r["deviant_features"], "무너진 날인데 이탈 지표가 비어 있다"
    assert r["streak_days"] >= 1


def test_지표가_모자라면_규칙으로_돈다():
    """절반도 못 채우면 중앙값 덩어리를 예측하는 셈이라 의미가 없다."""
    if not model_score.available():
        pytest.skip("모델 파일이 없습니다")
    empty = {k: (None, None, None) for k in model_score.KEY_MAP}
    score, ver = model_score.score(empty, rule_anomaly=0.42)
    assert ver is None
    assert score == 0.42
