# -*- coding: utf-8 -*-
r"""추가 지표를 그룹별로 갈라 넣어본다 — 어디까지가 값어치를 하나. 2026.08.25

    .venv/Scripts/python.exe ai/train/eval_plus_ablation.py [모드]

## 왜

`eval_service_plus.py` 에서 테이블 전체(51 피처)를 넣었더니 엇갈렸습니다.

    narrow  +0.047 [+0.020,+0.080] ✅
    tense   +0.020 [-0.005,+0.043]
    happy   -0.008 [-0.046,+0.030]

**컬럼 30개를 더 붙이는 비용**(실기기에서 하나라도 비면 대체값으로
메워야 함)에 비해 근거가 일정하지 않습니다. 그래서 **어느 그룹이 실제로
기여하는지** 갈라 봅니다.

| 그룹 | 컬럼 | 실기기에서 얼마나 확실한가 |
|---|---|---|
| `심박` | `heart_rate` | ⭐ Health Connect 가 확실히 넘긴다. 컬럼 하나 |
| `수면단계` | `deep`·`light`·`rem` + 비율 | 삼성헬스가 넘긴다. 스키마에도 있다 |
| `활동확장` | `calories`·`total_active_min`·`activity_end` | 있지만 출처마다 빈다 |
| `기상시각` | `sleep_end_min` | `sleep_end_at` 에서 바로 나온다 |

**싼 것부터 넣어 보고, 값어치를 하는 지점에서 멈춥니다.**
"""
import importlib.util
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

MODE = sys.argv[1] if len(sys.argv) > 1 else "tense"
spec = importlib.util.spec_from_file_location("sp", "ai/train/eval_service_plus.py")
sys.argv = [sys.argv[0], MODE]
sp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sp)

K_GRID = [8, 12, 21, 30]

GROUPS = [
    ("심박", ["heart_rate"]),
    ("수면단계", ["deep_sleep_min", "light_sleep_min", "rem_sleep_min",
                  "deep_ratio", "rem_ratio"]),
    ("기상시각", ["sleep_end_min"]),
    ("활동확장", ["calories", "total_active_min", "activity_end_min"]),
]


def main():
    lab, title = sp.rf.ef.load_labels()
    print(f"라벨 {len(lab)}건 · 대상 {title}")
    print("피처 만드는 중...")
    df, rule = sp.build(lab)
    y = df["_y"].to_numpy()
    pid = df["_pid"].to_numpy()
    X = df.drop(columns=["_y", "_pid"])
    X = X.fillna(X.median())
    g0 = pd.factorize(pid)[0]

    def cols_of(keys):
        return [c for c in X.columns
                for k in keys if c in (k, k + "_z", k + "_base")]

    base_cols = cols_of(sp.RULE_KEYS)
    print(f"표본 {len(df)} · 참가자 {df['_pid'].nunique()} "
          f"· 배포본 {len(base_cols)} · 전체 {X.shape[1]} · 양성률 {y.mean():.1%}\n")

    def nested(cols):
        Xd = X[cols]
        o = np.full(len(df), np.nan)
        for tr, te in GroupKFold(5).split(Xd, y, groups=g0):
            if len(np.unique(y[tr])) < 2:
                continue
            gin = g0[tr]
            best_k, best_s = K_GRID[0], -1
            for k in K_GRID:
                if k > Xd.shape[1]:
                    continue
                oin = np.full(len(tr), np.nan)
                for a, b in GroupKFold(4).split(Xd.iloc[tr], y[tr], groups=gin):
                    if len(np.unique(y[tr][a])) < 2:
                        continue
                    m = make_pipeline(StandardScaler(), SelectKBest(f_classif, k=k),
                                      LogisticRegression(max_iter=3000, C=0.1))
                    m.fit(Xd.iloc[tr].iloc[a], y[tr][a])
                    oin[b] = m.predict_proba(Xd.iloc[tr].iloc[b])[:, 1]
                kk = ~np.isnan(oin)
                if kk.sum() < 30 or len(np.unique(y[tr][kk])) < 2:
                    continue
                s = roc_auc_score(y[tr][kk], oin[kk])
                if s > best_s:
                    best_k, best_s = k, s
            m = make_pipeline(StandardScaler(),
                              SelectKBest(f_classif, k=min(best_k, Xd.shape[1])),
                              LogisticRegression(max_iter=3000, C=0.1))
            m.fit(Xd.iloc[tr], y[tr])
            o[te] = m.predict_proba(Xd.iloc[te])[:, 1]
        return pd.Series(o).rank(pct=True).to_numpy()

    CAND = {"배포본 (규칙 7지표)": nested(base_cols)}
    acc = list(base_cols)
    for name, keys in GROUPS:
        add = [c for c in cols_of(keys) if c not in acc]
        if not add:
            continue
        acc += add
        print(f"  +{name} ({len(add)}개) 도는 중...", flush=True)
        CAND[f"+{name}"] = nested(list(acc))
    #  각 그룹 하나씩만 더한 것도 따로 본다
    for name, keys in GROUPS:
        add = [c for c in cols_of(keys) if c not in base_cols]
        if not add:
            continue
        print(f"  배포본+{name} 만 도는 중...", flush=True)
        CAND[f"배포본+{name}만"] = nested(base_cols + add)

    def within_of(o, idx=None):
        pp = pid if idx is None else pid[idx]
        oo = o if idx is None else o[idx]
        yy = y if idx is None else y[idx]
        v = [roc_auc_score(yy[pp == p], oo[pp == p]) for p in np.unique(pp)
             if (pp == p).sum() >= 8 and len(np.unique(yy[pp == p])) > 1]
        return np.mean(v) if v else np.nan

    rng = np.random.default_rng(42)
    pids = np.unique(pid)
    bw = {k: [] for k in CAND}
    for _ in range(2000):
        smp = rng.choice(pids, len(pids), replace=True)
        idx = np.concatenate([np.where(pid == p)[0] for p in smp])
        if len(np.unique(y[idx])) < 2:
            continue
        for k, o in CAND.items():
            bw[k].append(within_of(o, idx))

    base = np.array(bw["배포본 (규칙 7지표)"])
    print(f"\n=== {title} · 배포본 대비 ===\n")
    print(f"  {'구성':22s} {'내부 AUC':>9} {'배포본 대비':>10} {'95%':>17}")
    print(f"  {'-'*22} {'-'*9} {'-'*10} {'-'*17}")
    for k, o in CAND.items():
        line = f"  {k:22s} {within_of(o):9.3f}"
        if k != "배포본 (규칙 7지표)":
            d = np.array(bw[k]) - base
            lo, hi = np.nanpercentile(d, [2.5, 97.5])
            sig = "✅" if lo > 0 else ("⛔" if hi < 0 else "  ")
            line += f" {np.nanmean(d):+10.3f} [{lo:+.3f},{hi:+.3f}] {sig}"
        print(line)


if __name__ == "__main__":
    main()
