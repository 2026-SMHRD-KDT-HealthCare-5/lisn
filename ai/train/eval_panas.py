# -*- coding: utf-8 -*-
r"""LifeSnaps PANAS / STAI 로 다시 검증한다 — 2026.08.24

    .venv/Scripts/python.exe ai/train/eval_panas.py

## 왜 라벨을 갈아탔나

GLOBEM `dep` 로 네 번 시도해 네 번 다 실패했습니다(eval_hybrid.py).
원인을 파보니 **라벨이 참가자 단위로 고정**돼 있었습니다 — 40명 전원이
기간 내내 `dep` 도 `BDI2` 도 안 변합니다. 2030행처럼 보여도 독립 표본은
40개고, 40개로는 무엇을 해도 신뢰구간이 0.5 를 포함합니다.

LifeSnaps 의 PANAS·STAI 는 다릅니다.

    GLOBEM dep        값이 변하는 참가자   0/40      독립 표본  40
    LifeSnaps PANAS   값이 변하는 참가자  47/51      독립 표본 268
    LifeSnaps STAI    값이 변하는 참가자  48/53      독립 표본 279

**시점마다 점수가 다릅니다.** 즉 「이 사람이 우울한가」(상태)가 아니라
「지금 기분이 어떤가」(변화)를 묻습니다 — **우리 이탈 탐지와 같은 축**이고,
막혔던 두 문제(표본 수·축 불일치)가 동시에 풀립니다.

## 재는 것

설문 응답일 기준으로 **직전 14일** 라이프로그를 모아 피처를 만들고,
그날의 PANAS/STAI 점수를 맞히는 문제입니다. 14일은 `MLCM_210` 2단계가
규정한 기준값 창과 같습니다.

    ① 규칙 단독      개인 기준선 이탈 점수
    ② 모델 단독      LightGBM
    ③ 가중 결합      (1-w)*규칙 + w*모델

⚠ **참가자 단위 분할(GroupKFold)** — 무작위로 나누면 같은 사람이 학습·
  평가 양쪽에 들어가 지표가 부풀려집니다.
⚠ **20회 반복 + 95% 신뢰구간** — 0.610 이 fold 운이었던 전례가 있습니다.
"""

import warnings
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve().parent
RAW = HERE.parent / "data_raw" / "lifesnaps" / "rais_anonymized"
DAILY = RAW / "csv_rais_anonymized" / "daily_fitbit_sema_df_unprocessed.csv"
SURVEY = RAW / "scored_surveys"

WINDOW = 14          # MLCM_210 2단계 기준값 창
N_REPEAT = 20
N_SPLITS = 5
SEED = 42
FULL_SCALE_Z = 4.0   # ai/server/main.py 와 같은 상수

#  우리 서비스가 보는 지표에 맞춘다. (방향: down=줄면 나쁨, up=늘면 나쁨)
FEATURES = [
    ("minutesAsleep", "down"),
    ("sleep_efficiency", "down"),
    ("steps", "down"),
    ("minutesToFallAsleep", "up"),
    ("sleep_wake_ratio", "up"),
    ("resting_hr", "up"),
    ("rmssd", "down"),
]


def robust_z(value, history):
    h = [v for v in history if pd.notna(v)]
    if len(h) < 3 or pd.isna(value):
        return None
    med = float(np.median(h))
    mad = float(np.median([abs(v - med) for v in h]))
    if mad == 0:
        sd = float(np.std(h))
        return None if sd == 0 else (value - med) / sd
    return (value - med) / (1.4826 * mad)


def build(target_col, survey_file):
    daily = pd.read_csv(DAILY, parse_dates=["date"])
    daily = daily.rename(columns={"id": "user_id"}).sort_values(["user_id", "date"])
    sv = pd.read_csv(SURVEY / survey_file, parse_dates=["submitdate"])
    sv = sv[["user_id", "submitdate", target_col]].dropna()

    rows = []
    for _, s in sv.iterrows():
        end = s["submitdate"]
        start = end - pd.Timedelta(days=WINDOW)
        w = daily[(daily.user_id == s.user_id) & (daily.date > start) & (daily.date <= end)]
        if len(w) < 5:                     # 창에 최소 5일은 있어야 기준선이 선다
            continue
        day = w.iloc[-1]
        hist = w.iloc[:-1]                 # ⚠ 오늘 제외 — main.py 와 같다

        feat, devs = {}, []
        for col, direction in FEATURES:
            if col not in w.columns:
                continue
            feat[f"{col}_mean"] = w[col].mean()
            feat[f"{col}_std"] = w[col].std()
            feat[f"{col}_last"] = day[col]
            z = robust_z(day[col], hist[col].tolist())
            if z is not None:
                devs.append(max(0.0, -z if direction == "down" else z))
        if not feat or not devs:
            continue
        top = sorted(devs, reverse=True)[:3]
        feat["_rule"] = min(1.0, sum(top) / len(top) / FULL_SCALE_Z)
        feat["_y"] = s[target_col]
        feat["_pid"] = s.user_id
        rows.append(feat)

    return pd.DataFrame(rows).dropna(axis=1, how="all").fillna(0)


def run(name, target_col, survey_file, high_is_bad):
    df = build(target_col, survey_file)
    if len(df) < 50:
        print(f"[{name}] 표본이 {len(df)}개뿐 — 건너뜁니다\n")
        return

    #  연속 점수를 상·하위로 갈라 이진화한다. 중앙값 기준이라 균형이 맞는다.
    med = df["_y"].median()
    y = (df["_y"] > med).astype(int) if high_is_bad else (df["_y"] < med).astype(int)
    rule = df["_rule"].to_numpy()
    X = df.drop(columns=["_y", "_pid", "_rule"])
    groups = df["_pid"].to_numpy()

    print(f"=== {name} ===")
    print(f"  표본 {len(df)} · 참가자 {df['_pid'].nunique()} · 피처 {X.shape[1]}")
    print(f"  라벨 기준 중앙값 {med:.1f} · 양성 {y.sum()}/{len(y)}\n")

    weights = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
    scores = {w: [] for w in weights}
    rng = np.random.default_rng(SEED)

    for _ in range(N_REPEAT):
        pids = df["_pid"].unique().copy()
        rng.shuffle(pids)
        remap = {p: i for i, p in enumerate(pids)}
        g = np.array([remap[p] for p in groups])

        oof = np.full(len(df), np.nan)
        for tr, te in GroupKFold(n_splits=N_SPLITS).split(X, y, groups=g):
            if len(np.unique(y.iloc[tr])) < 2:
                continue
            m = lgb.LGBMClassifier(n_estimators=150, learning_rate=0.05, num_leaves=15,
                                   min_child_samples=10, subsample=0.8,
                                   colsample_bytree=0.8, random_state=SEED, verbose=-1)
            m.fit(X.iloc[tr], y.iloc[tr])
            oof[te] = m.predict_proba(X.iloc[te])[:, 1]

        ok = ~np.isnan(oof)
        if ok.sum() < 30 or len(np.unique(y[ok])) < 2:
            continue
        for w in weights:
            scores[w].append(roc_auc_score(y[ok], (1 - w) * rule[ok] + w * oof[ok]))

    print(f"  {'가중치':>7}  {'구성':<20} {'평균 AUC':>9}  {'95% 구간':>17}")
    print(f"  {'-'*7}  {'-'*20} {'-'*9}  {'-'*17}")
    base = None
    for w in weights:
        v = np.array(scores[w])
        if not len(v):
            continue
        lo, hi = np.percentile(v, [2.5, 97.5])
        label = ("규칙 단독" if w == 0 else "모델 단독" if w == 1.0
                 else f"규칙 {1-w:.0%} + 모델 {w:.0%}")
        if w == 0:
            base = v.mean()
        sig = " ✅" if lo > 0.5 else ""
        print(f"  {w:>7.1f}  {label:<20} {v.mean():>9.3f}  {lo:.3f} ~ {hi:.3f}{sig}")

    best_w = max((w for w in weights if scores[w]), key=lambda w: np.mean(scores[w]))
    best = np.mean(scores[best_w])
    print(f"\n  최고 = 가중치 {best_w} ({best:.3f}) · 규칙 단독 {base:.3f}")
    if best_w != 0:
        diff = np.array(scores[best_w]) - np.array(scores[0])
        lo, hi = np.percentile(diff, [2.5, 97.5])
        print(f"  결합 이득 {best-base:+.3f} · 차이 95% {lo:+.3f} ~ {hi:+.3f}")
        print("  → 우연이 아닙니다. 결합을 넣을 근거가 됩니다." if lo > 0
              else "  → ⚠ 구간이 0 을 포함합니다. 근거가 못 됩니다.")
    print()


if __name__ == "__main__":
    run("PANAS 부정 정서", "negative_affect_score", "panas.csv", high_is_bad=True)
    run("PANAS 긍정 정서", "positive_affect_score", "panas.csv", high_is_bad=False)
    run("STAI 불안", "stai_stress", "stai.csv", high_is_bad=True)
