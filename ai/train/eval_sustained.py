# -*- coding: utf-8 -*-
r"""추세가 잡아야 할 것은 「순간」이 아니라 「지속」이다 — 2026.08.25

    .venv/Scripts/python.exe ai/train/eval_sustained.py

## 왜 대상을 바꾸나

`eval_trend.py` 에서 추세 피처(Mann-Kendall·기울기·수준 이동)가 순간
불안 예측에는 도움이 안 됐습니다(-0.001). 그런데 **`main.py` 가 적은
한계는 순간에 대한 것이 아니었습니다.**

> 「**2주에 걸쳐 조금씩 나빠지면**」·「우울이 **서서히 진행되는** 경우가
> 많다」

**서서히 나빠지는 것은 서서히 나빠지는 것을 예측해야 맞습니다.** 그리고
그게 우리 서비스에서 실제로 쓰이는 자리입니다 — 선제 접촉(`MLCM_220`)은
`streak_days`(연속 이탈 일수)로 발동하지, 하루의 튐으로 발동하지 않습니다.

## 새 대상 — 「앞으로 사흘이 나쁠 것인가」

```
그 시점 이후 3일 안의 응답 중 부정이 절반을 넘으면 양성
```

⚠ **미래를 봅니다 — 그게 목적입니다.** 예측 대상이 미래이고, 입력은
  전부 그 시점 이전입니다. 「지금 상태를 맞히기」가 아니라 **「곧 나빠질
  사람을 먼저 찾기」**라 우리 선제 접촉과 같은 문제입니다.

⚠ 응답이 3일 안에 2건 미만인 시점은 뺍니다 — 한 건으로 「지속」을 말할
  수 없습니다.
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

sys.argv = [sys.argv[0], "narrow"]     # 부정 정서 기준으로 「지속」을 정의한다
spec = importlib.util.spec_from_file_location("tr", "ai/train/eval_trend.py")
tr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tr)

HORIZON_DAYS = 3
MIN_FUTURE = 2
K_GRID = [8, 12, 21, 30, 42]


def main():
    lab, _ = tr.rf.ef.load_labels()
    print(f"라벨 {len(lab)}건 · 참가자 {lab.pid.nunique()}")

    #  ── 앞으로 3일이 나쁠 것인가 ──
    lab = lab.sort_values(["pid", "ts"]).reset_index(drop=True)
    fut = np.full(len(lab), np.nan)
    for p, g in lab.groupby("pid"):
        idx = g.index.to_numpy()
        ts = g.ts.to_numpy()
        ys = g.y.to_numpy()
        for i in range(len(idx)):
            hi = np.searchsorted(ts, ts[i] + np.timedelta64(HORIZON_DAYS, "D"),
                                 side="right")
            nxt = ys[i + 1:hi]
            if len(nxt) >= MIN_FUTURE:
                fut[idx[i]] = float(nxt.mean() > 0.5)
    lab["y_now"] = lab.y
    lab["y"] = fut
    keep = lab.y.notna()
    print(f"  앞으로 {HORIZON_DAYS}일 안에 응답 {MIN_FUTURE}건 이상인 시점: "
          f"{keep.sum()} · 양성률 {lab.y[keep].mean():.1%}\n")

    print("피처 만드는 중 (Mann-Kendall 은 조금 걸립니다)...")
    df, rule = tr.build(lab[keep].assign(y=lab.y[keep].astype(int)))
    y = df["_y"].to_numpy()
    pid = df["_pid"].to_numpy()
    X = df.drop(columns=["_y", "_pid"]).fillna(
        df.drop(columns=["_y", "_pid"]).median())
    g0 = pd.factorize(pid)[0]

    base_cols = [c for c in X.columns
                 if any(c == k + s for k in tr.DIRECTION for s in ("", "_z", "_base"))]
    trend_cols = [c for c in X.columns if c not in base_cols]
    print(f"표본 {len(df)} · 참가자 {df['_pid'].nunique()} "
          f"· 배포본 {len(base_cols)} · 추세 {len(trend_cols)} "
          f"· 양성률 {y.mean():.1%}\n")

    def nested(cols):
        Xd = X[cols]
        o = np.full(len(df), np.nan)
        for a_tr, a_te in GroupKFold(5).split(Xd, y, groups=g0):
            if len(np.unique(y[a_tr])) < 2:
                continue
            gin = g0[a_tr]
            best_k, best_s = K_GRID[0], -1
            for k in K_GRID:
                if k > Xd.shape[1]:
                    continue
                oin = np.full(len(a_tr), np.nan)
                for a, b in GroupKFold(4).split(Xd.iloc[a_tr], y[a_tr], groups=gin):
                    if len(np.unique(y[a_tr][a])) < 2:
                        continue
                    m = make_pipeline(StandardScaler(), SelectKBest(f_classif, k=k),
                                      LogisticRegression(max_iter=3000, C=0.1))
                    m.fit(Xd.iloc[a_tr].iloc[a], y[a_tr][a])
                    oin[b] = m.predict_proba(Xd.iloc[a_tr].iloc[b])[:, 1]
                kk = ~np.isnan(oin)
                if kk.sum() < 30 or len(np.unique(y[a_tr][kk])) < 2:
                    continue
                s = roc_auc_score(y[a_tr][kk], oin[kk])
                if s > best_s:
                    best_k, best_s = k, s
            m = make_pipeline(StandardScaler(),
                              SelectKBest(f_classif, k=min(best_k, Xd.shape[1])),
                              LogisticRegression(max_iter=3000, C=0.1))
            m.fit(Xd.iloc[a_tr], y[a_tr])
            o[a_te] = m.predict_proba(Xd.iloc[a_te])[:, 1]
        return pd.Series(o).rank(pct=True).to_numpy()

    rk = lambda v: pd.Series(v).rank(pct=True).to_numpy()
    CAND = {
        "① 현재 규칙": rk(rule),
        "② 배포본 (z 만)": nested(base_cols),
        "③ 추세만": nested(trend_cols),
        "④ 배포본 + 추세": nested(base_cols + trend_cols),
    }

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

    print(f"=== 앞으로 {HORIZON_DAYS}일이 나쁠 것인가 (선제 접촉의 문제) ===\n")
    print(f"  {'구성':18s} {'내부 AUC':>9} {'95%':>15}")
    print(f"  {'-'*18} {'-'*9} {'-'*15}")
    for k, o in CAND.items():
        lo, hi = np.nanpercentile(bw[k], [2.5, 97.5])
        print(f"  {k:18s} {within_of(o):9.3f} {lo:.3f}~{hi:.3f}")

    print("\n  === 대비 (같은 리샘플에서의 차) ===\n")
    for basekey in ("① 현재 규칙", "② 배포본 (z 만)"):
        b = np.array(bw[basekey])
        for k in CAND:
            if list(CAND).index(k) <= list(CAND).index(basekey):
                continue
            d = np.array(bw[k]) - b
            lo, hi = np.nanpercentile(d, [2.5, 97.5])
            sig = "✅" if lo > 0 else ("⛔" if hi < 0 else "  ")
            print(f"  {k:18s} vs {basekey:16s} "
                  f"{np.nanmean(d):+.3f} [{lo:+.3f},{hi:+.3f}] {sig}")


if __name__ == "__main__":
    main()
