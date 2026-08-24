# -*- coding: utf-8 -*-
"""학습된 집계 — `_predict` 의 「상위 3개 평균 ÷ 4.0」을 대신한다.

## 무엇이 바뀌나

`main.py` 의 판정은 두 단계입니다.

    ① 지표 7개의 개인 기준선 이탈(z)을 잰다      ← 근거 있음. 그대로 둔다
    ② 상위 3개를 평균 내고 4.0 으로 나눈다        ← 임의값. 여기만 바꾼다

**입력이 늘지 않습니다.** 서버가 이미 읽는 컬럼만 씁니다.

## 왜 바꾸나 — 현재 규칙이 검증되지 않았기 때문입니다

`main.py` 는 스스로 「임계값도 선행연구값이 아닌 임의값이다 · 성능 근거로
쓰지 마세요」라고 적어 두었습니다. 실제로 재보니 그랬습니다.

    LifeSnaps · 참가자 62명 · 4086 표본 · 참가자 분할 + 중첩 교차검증
    참가자 내부 AUC     현재 규칙 0.491  →  학습된 집계 0.609
    이득 +0.115 (참가자 단위 부트스트랩 95% +0.056 ~ +0.176)

근거·재현 방법은 `ai/train/eval_rule_features.py` 와
`docs/검증/학습모델_활용_시도_20260824.md` 에 있습니다.

## 안전장치 세 가지

**① 경보 총량이 같습니다.** 모델 확률을 학습 데이터에서 **규칙 점수와 같은
분포**가 되도록 옮깁니다(histogram matching). `risk_level_of` 의 임계값
0.25·0.5 는 정책이라 건드리지 않습니다. 바뀌는 것은 **누구에게 경보가
가는가**입니다.

**② 규칙 바닥.** 규칙이 `rule_floor`(0.75) 이상을 낸 날은 모델이 낮게 봐도
그 아래로 내려가지 않습니다. **가장 강한 규칙 경보는 그대로 살아 있습니다.**

**③ 없으면 규칙으로 돕니다.** 모델 파일이 없거나, 지표가 모자라거나,
예측이 실패하면 `None` 을 돌려주고 `main.py` 는 기존 규칙 점수를 씁니다.
그때 `model_version` 은 `rule-` 접두사를 그대로 유지하므로, **응답만 보고도
모델이 관여했는지 구분됩니다.**

⚠ **`risk_level_of()` 는 건드리지 않습니다.** 거기는 모델이 아니라 정책이고,
  데이터베이스요구사항분석서 6항이 정한 것입니다.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ARTIFACT = Path(__file__).resolve().parent / "model" / "anomaly_lr.joblib"
MODEL_VERSION = "hybrid-lr-v1-20260825"

#  main.py `_FEATURES` 의 키 → 학습 때 쓴 컬럼 이름.
#  파생 지표는 main.py 에서 밑줄로 시작하지만 학습 쪽은 밑줄이 없다.
KEY_MAP = {
    "total_sleep_min": "total_sleep_min",
    "steps": "steps",
    "sleep_efficiency_pct": "sleep_efficiency_pct",
    "sleep_onset_min": "sleep_onset_min",
    "awake_min": "awake_min",
    "_sleep_start_min": "sleep_start_min",
    "_activity_start_min": "activity_start_min",
}

_art = None
_load_failed = False


def _load():
    """한 번만 읽는다. 실패하면 다시 시도하지 않고 규칙으로 돈다."""
    global _art, _load_failed
    if _art is not None or _load_failed:
        return _art
    try:
        import joblib

        _art = joblib.load(ARTIFACT)
        m = _art["metrics"]
        logger.info(
            "학습된 집계 적재: %s · 피처 %d · 참가자 내부 AUC %.3f "
            "(규칙 %.3f · 이득 %+.3f, 95%% %+.3f~%+.3f)",
            MODEL_VERSION, len(_art["features"]), m["model_within_auc"],
            m["rule_within_auc"], m["gain_within"], *m["gain_within_ci95"])
    except Exception as e:                      # 파일 없음·버전 불일치 등
        _load_failed = True
        logger.warning("학습된 집계를 쓸 수 없습니다 — 규칙으로 돕니다: %s", e)
    return _art


def available() -> bool:
    return _load() is not None


def score(measures: dict, rule_anomaly: float) -> tuple[float, str]:
    """이상치 점수를 낸다.

    Args:
        measures: `{main.py 의 지표 키: (오늘 값, 기준선 z, 기준선 중앙값)}`.
            값이 없으면 `None` 을 넣는다.
        rule_anomaly: 기존 규칙이 낸 점수. 바닥으로 쓴다.

    Returns:
        `(anomaly_score, model_version)`. 모델을 못 쓰면 규칙 점수와
        `None` 을 돌려주므로, 부르는 쪽이 그대로 기존 동작을 유지한다.
    """
    art = _load()
    if art is None:
        return rule_anomaly, None

    try:
        import numpy as np
        import pandas as pd

        med = art["medians"]
        row = {}
        filled = 0
        for src, dst in KEY_MAP.items():
            v, z, base = measures.get(src, (None, None, None))
            for name, val in ((dst, v), (dst + "_z", z), (dst + "_base", base)):
                if name not in med:
                    continue
                if val is None:
                    row[name] = med[name]        # 학습 데이터 중앙값으로 대체
                else:
                    row[name] = float(val)
                    filled += 1

        #  ⚠ 절반도 못 채우면 중앙값 덩어리를 예측하는 셈이라 의미가 없다.
        #    규칙으로 물러선다.
        if filled < len(art["features"]) // 2:
            logger.info("지표가 모자라 규칙으로 돕니다 (%d/%d)",
                        filled, len(art["features"]))
            return rule_anomaly, None

        X = pd.DataFrame([[row.get(c, med[c]) for c in art["features"]]],
                         columns=art["features"])
        p = float(art["pipeline"].predict_proba(X)[0, 1])
        #  학습 데이터에서 규칙과 같은 분포가 되도록 옮긴다
        cal = float(np.interp(p, art["calib_p"], art["calib_r"]))

        #  규칙 바닥 — 규칙이 크게 튄 날은 모델이 낮게 봐도 안 내린다
        if rule_anomaly >= art["rule_floor"]:
            cal = max(cal, rule_anomaly)
        return round(min(1.0, max(0.0, cal)), 4), MODEL_VERSION
    except Exception as e:
        logger.warning("학습된 집계 예측 실패 — 규칙으로 돕니다: %s", e)
        return rule_anomaly, None
