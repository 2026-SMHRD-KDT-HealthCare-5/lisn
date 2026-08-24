# -*- coding: utf-8 -*-
r"""판정 서버에 넣을 모델을 학습해 저장한다. 2026.08.25

    .venv/Scripts/python.exe ai/train/train_service_model.py

출력 → `ai/server/model/anomaly_lr.joblib`

## 무엇을 학습하나

**현재 규칙이 이미 읽는 입력만** 씁니다. 새 센서도, 새 컬럼도 필요 없습니다.

    7개 지표 × (원값 · 개인 기준선 대비 z · 기준선 중앙값) = 21개

현재 규칙은 이 z 들을 **「상위 3개 평균 ÷ 4.0」** 으로 합칩니다.
`main.py` 가 스스로 「임의값이다 · 성능 근거로 쓰지 말 것」이라고 적어 둔
그 부분입니다. **그 집계만 학습된 것으로 바꿉니다.**

## 근거

`eval_rule_features.py` 실측(LifeSnaps · 참가자 62명 · 4086 표본 ·
참가자 분할 GroupKFold(5) + 중첩 교차검증):

| 구성 | 참가자 내부 AUC | 규칙 대비 이득 | 95% |
|---|---|---|---|
| 현재 규칙 | 0.491 | — | |
| **학습된 집계** | **0.609** | **+0.115** | **+0.056 ~ +0.176** ✅ |
| max(규칙, 학습) | 0.542 | +0.051 | +0.015 ~ +0.086 ✅ |

> **참가자 내부 AUC** 로 판정했습니다 — 「이 사람의 나쁜 순간을 이 사람의
> 좋은 순간보다 위로 올리는가」가 우리 서비스가 하는 일입니다. 전체 AUC 는
> 「누가 원래 부정적인가」로 부풀려집니다(→ `학습모델_활용_시도` 시도 19).

## 출력 규격

    features   학습에 쓴 컬럼 이름과 순서
    pipeline   StandardScaler → SelectKBest → LogisticRegression
    medians    결측 대체값(학습 데이터 중앙값)
    calib_p    확률 분위수 격자
    calib_r    같은 분위의 **규칙 점수** — 분포를 규칙에 맞춘다
    rule_floor 규칙이 이 값 이상이면 모델이 낮게 봐도 안 내린다
    metrics    위 표의 실측치. 서버가 로그에 찍어 근거를 남긴다

⚠ **확률을 그대로 `anomaly_score` 로 쓰지 않습니다.** 학습 데이터에서
  **규칙 점수와 같은 분포가 되도록** 분위수를 맞춰 옮깁니다(histogram
  matching). 그래서 **경보 총량이 지금과 같습니다** — 임계값 0.25·0.5 는
  정책이라 건드리지 않고, 바뀌는 것은 **누구에게 경보가 가는가**입니다.

⚠ **규칙 바닥을 남깁니다.** 규칙이 크게 튄 날은 모델이 낮게 봐도 그 아래로
  내려가지 않습니다. 모델이 어긋나도 **가장 강한 규칙 경보는 그대로 살아
  있습니다**(`NFR-DV-003` 과 같은 발상).
"""
import importlib.util
import json
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

OUT = Path("ai/server/model")
OUT.mkdir(parents=True, exist_ok=True)

sys.argv = [sys.argv[0], "tense"]     # 대상: TENSE/ANXIOUS
spec = importlib.util.spec_from_file_location("rf", "ai/train/eval_rule_features.py")
rf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rf)

K = 21             # 중첩 CV 가 폴드 5개 중 4개에서 21(전부)을 골랐다
RULE_FLOOR = 0.75  # 규칙이 이 이상이면 모델이 낮게 봐도 안 내린다

METRICS = {
    "dataset": "LifeSnaps RAIS (SEMA MOOD · TENSE/ANXIOUS)",
    "n_samples": None,
    "n_participants": None,
    "rule_within_auc": 0.491,
    "model_within_auc": 0.609,
    "gain_within": 0.115,
    "gain_within_ci95": [0.056, 0.176],
    "eval": "참가자 분할 GroupKFold(5) + 중첩 CV · 참가자 단위 부트스트랩 2000회",
    "script": "ai/train/eval_rule_features.py",
}


def main():
    lab, title = rf.ef.load_labels()
    print(f"라벨 {len(lab)}건 · 대상 {title}")
    df, rule = rf.build(lab)
    y = df["_y"].to_numpy()
    X = df.drop(columns=["_y", "_pid"])
    med = X.median()
    X = X.fillna(med)
    print(f"표본 {len(df)} · 참가자 {df['_pid'].nunique()} · 피처 {X.shape[1]} "
          f"· 양성률 {y.mean():.1%}")

    pipe = make_pipeline(StandardScaler(),
                         SelectKBest(f_classif, k=min(K, X.shape[1])),
                         LogisticRegression(max_iter=3000, C=0.1))
    pipe.fit(X, y)
    p = pipe.predict_proba(X)[:, 1]

    #  확률 분포를 규칙 점수 분포에 맞춘다(histogram matching).
    #  같은 분위끼리 이으므로 변환 뒤 분포가 규칙과 같아진다.
    q = np.arange(0, 100.5, 0.5)
    calib_p = np.percentile(p, q)
    calib_r = np.percentile(rule, q)

    METRICS["n_samples"] = int(len(df))
    METRICS["n_participants"] = int(df["_pid"].nunique())

    art = {
        "features": list(X.columns),
        "pipeline": pipe,
        "medians": {k: float(v) for k, v in med.items()},
        "calib_p": calib_p.tolist(),
        "calib_r": calib_r.tolist(),
        "rule_floor": RULE_FLOOR,
        "metrics": METRICS,
        "target": "TENSE/ANXIOUS",
        "k": int(min(K, X.shape[1])),
    }
    joblib.dump(art, OUT / "anomaly_lr.joblib")
    (OUT / "metrics.json").write_text(
        json.dumps(METRICS, ensure_ascii=False, indent=2), encoding="utf-8")

    cal = np.interp(p, calib_p, calib_r)
    comb = np.where(rule >= RULE_FLOOR, np.maximum(cal, rule), cal)

    print(f"\n저장 -> {OUT / 'anomaly_lr.joblib'}")
    print(f"  피처 {len(X.columns)} · K={art['k']} · 규칙 바닥 {RULE_FLOOR}")

    print("\n  === 경보율 (학습 데이터 기준) ===")
    print(f"  {'점수':20s} {'>=0.25':>9} {'>=0.5':>9}")
    for nm, v in [("현재 규칙", rule), ("모델(분포 맞춤)", cal),
                  ("모델+규칙 바닥 <= 채택", comb)]:
        print(f"  {nm:20s} {(v >= 0.25).mean():9.1%} {(v >= 0.5).mean():9.1%}")

    print("\n  === 규칙 바닥을 어디에 둘까 ===")
    print(f"  {'바닥':>6} {'해당 날':>8} {'>=0.25':>8} {'>=0.5':>8}")
    for fl in (0.5, 0.6, 0.75, 0.9):
        c = np.where(rule >= fl, np.maximum(cal, rule), cal)
        print(f"  {fl:6.2f} {(rule >= fl).mean():8.1%} "
              f"{(c >= 0.25).mean():8.1%} {(c >= 0.5).mean():8.1%}")
    print(f"  {'없음':>6} {0.0:8.1%} {(cal >= 0.25).mean():8.1%} "
          f"{(cal >= 0.5).mean():8.1%}")

    flip = (comb >= 0.25) != (rule >= 0.25)
    drop = ((comb < 0.25) & (rule >= 0.25)).mean()
    add = ((comb >= 0.25) & (rule < 0.25)).mean()
    print(f"\n  CAUTION 판정이 뒤집힌 날 {flip.mean():.1%} "
          f"(빠짐 {drop:.1%} · 새로 들어옴 {add:.1%})")


if __name__ == "__main__":
    main()
