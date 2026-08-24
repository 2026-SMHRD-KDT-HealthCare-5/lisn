# -*- coding: utf-8 -*-
r"""추세 검정을 넣는다 — `main.py` 가 적어 둔 한계를 닫는다. 2026.08.25

    .venv/Scripts/python.exe ai/train/eval_trend.py [모드]
      모드: tense(기본) | narrow | happy

## `main.py` 가 스스로 적어 둔 한계

> ⚠ **아는 한계 — 서서히 나빠지는 것은 약하게 잡힌다.**
>
> z 는 「최근 분포 대비 오늘이 튀는가」를 본다. 하루아침에 무너지면 크게
> 잡히지만, **2주에 걸쳐 조금씩 나빠지면 분포 자체가 넓어져** z 가 커지지
> 않는다.
>
> 제대로 잡으려면 **추세 검정(Mann-Kendall 등)**이 따로 필요하다. 넣지
> 않은 이유는 **검증할 라벨이 없어서**다. **우울이 서서히 진행되는 경우가
> 많다는 점에서 이건 실제 한계다.**

**이제 라벨이 있습니다.** 그래서 닫아 봅니다.

## 넣는 것 — 전부 기존 컬럼만 씁니다

지표 7개마다:

| 피처 | 무엇 |
|---|---|
| `_mk` | **Mann-Kendall S 통계** — 오르는 쌍과 내리는 쌍의 차. 값의 크기가 아니라 **순서**만 보므로 이상치에 강하다 |
| `_slope` | 14일 선형 기울기를 기준선 중앙값으로 나눈 것(하루 몇 % 변하나) |
| `_shift` | 최근 3일 중앙값 − 앞 11일 중앙값. **수준이 옮겨갔나** |

**z 가 못 보는 것을 본다**는 것이 요점입니다 — z 는 「오늘이 튀는가」,
이쪽은 「계속 나빠지는 중인가」.

⚠ **방향을 맞춥니다.** 총수면·걸음·수면효율은 **줄어야** 나쁘고 나머지는
  늘어야 나쁩니다. 나쁜 쪽을 양수로 뒤집어 넣습니다.

⚠ 오늘을 포함한 최근 14일을 봅니다. 라벨 시각 이전 값만 쓰므로 미래를
  보지 않습니다.
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
spec = importlib.util.spec_from_file_location("rf", "ai/train/eval_rule_features.py")
sys.argv = [sys.argv[0], MODE]
rf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rf)

PQ = rf.PQ
HCSV = rf.HCSV
BASE_DAYS = 14
K_GRID = [8, 12, 21, 30, 42]

#  나쁜 쪽 방향 — main.py `_FEATURES` 와 같다
DIRECTION = {
    "total_sleep_min": "down", "steps": "down", "sleep_efficiency_pct": "down",
    "sleep_onset_min": "up", "awake_min": "up", "sleep_start_min": "up",
    "activity_start_min": "up",
}


def mann_kendall(v):
    """Mann-Kendall S 통계를 표본 수로 정규화한 값 (-1 ~ +1).

    ⚠ **값의 크기가 아니라 순서만 봅니다.** 워치를 하루 안 찬 날이 섞여도
      한 점에 끌려가지 않습니다 — `_robust_z` 가 중앙값을 쓰는 것과 같은
      이유입니다.
    """
    n = len(v)
    if n < 5:
        return None
    s = 0
    for i in range(n - 1):
        d = np.sign(v[i + 1:] - v[i])
        s += int(d.sum())
    return s / (n * (n - 1) / 2)


def trend_feats(hist_vals, direction):
    """추세 3종. 나쁜 쪽을 양수로 돌려준다."""
    v = np.asarray([x for x in hist_vals if x is not None and not pd.isna(x)],
                   dtype=float)
    if len(v) < 5:
        return {}
    flip = -1.0 if direction == "up" else 1.0   # up 지표는 늘면 나쁘다
    mk = mann_kendall(v)
    med = float(np.median(v))
    scale = abs(med) if abs(med) > 1e-6 else 1.0
    slope = float(np.polyfit(np.arange(len(v)), v, 1)[0]) / scale
    k = max(2, len(v) // 4)
    shift = (float(np.median(v[-k:])) - float(np.median(v[:-k]))) / scale
    #  flip 을 곱하면 「나쁜 쪽으로 가는 중」이 항상 양수가 된다
    return {"mk": -flip * mk, "slope": -flip * slope, "shift": -flip * shift}


def build(lab):
    """규칙 입력 21개 + 추세 21개."""
    h = pd.read_csv(HCSV, usecols=["id", "date", "hour", "steps"])
    h = h.rename(columns={"id": "pid"})
    h["pid"] = h.pid.astype(str)
    h["date"] = pd.to_datetime(h["date"])
    hs = h.groupby(["pid", "date", "hour"], as_index=False).steps.mean() \
          .sort_values(["pid", "date", "hour"])
    steps_by = {p: g for p, g in hs.groupby("pid")}

    sl = pd.read_parquet(PQ / "sleep.parquet")
    sl["date"] = pd.to_datetime(sl.dateOfSleep, errors="coerce").dt.normalize()
    sl["startTime"] = pd.to_datetime(sl.startTime, errors="coerce")
    ds = sl.groupby(["pid", "date"], as_index=False).agg(
        total_sleep_min=("minutesAsleep", "sum"),
        awake_min=("minutesAwake", "sum"),
        sleep_onset_min=("minutesToFallAsleep", "mean"),
        sleep_efficiency_pct=("efficiency", "mean"),
        _s=("startTime", "min"))
    ds["sleep_start_min"] = ds._s.map(rf.sleep_start_min)
    sleep_by = {p: g.drop(columns=["_s"]).set_index("date").sort_index()
                for p, g in ds.groupby("pid")}

    rows, rule = [], []
    for r in lab.itertuples():
        day = pd.Timestamp(r.ts).normalize()
        hcut = r.ts.hour
        g = steps_by.get(r.pid)
        if g is None:
            continue
        hist_days = g[(g.date < day) & (g.date >= day - pd.Timedelta(days=BASE_DAYS))]
        hist_cut = hist_days[hist_days.hour <= hcut]
        today = g[(g.date == day) & (g.hour <= hcut)]
        if not len(today) or not len(hist_cut):
            continue

        cur_steps = today.steps.sum()
        hist_steps = hist_cut.groupby("date").steps.sum()
        act = today[today.steps > 0]
        ha = hist_days[hist_days.steps > 0].groupby("date").hour.min() * 60

        vals = {
            "steps": (cur_steps, hist_steps.tolist()),
            "activity_start_min": (float(act.hour.min() * 60) if len(act) else None,
                                   ha.tolist()),
        }
        sg = sleep_by.get(r.pid)
        if sg is not None:
            hsl = sg[(sg.index < day) & (sg.index >= day - pd.Timedelta(days=BASE_DAYS))]
            cur = sg.loc[day] if day in sg.index else None
            for col in ("total_sleep_min", "awake_min", "sleep_onset_min",
                        "sleep_efficiency_pct", "sleep_start_min"):
                v = float(cur[col]) if cur is not None and pd.notna(cur[col]) else None
                vals[col] = (v, hsl[col].dropna().tolist() if len(hsl) else [])

        f, devs = {}, []
        for col, direction in DIRECTION.items():
            if col not in vals:
                continue
            v, hist = vals[col]
            z = rf.robust_z(v, hist)
            f[col] = v if v is not None else np.nan
            f[col + "_z"] = z if z is not None else np.nan
            f[col + "_base"] = float(np.median(hist)) if hist else np.nan
            #  ── 추세: 오늘까지 이어 붙여서 본다 ──
            series = list(hist) + ([v] if v is not None else [])
            for k, tv in trend_feats(series, direction).items():
                f[f"{col}_{k}"] = tv
            if z is not None:
                devs.append(max(0.0, -z if direction == "down" else z))
        if not devs:
            continue
        top = sorted(devs, reverse=True)[:3]
        rule.append(min(1.0, sum(top) / len(top) / rf.FULL_SCALE_Z))
        f["_y"] = int(r.y)
        f["_pid"] = r.pid
        rows.append(f)
    return pd.DataFrame(rows), np.array(rule)


def main():
    lab, title = rf.ef.load_labels()
    print(f"라벨 {len(lab)}건 · 대상 {title}")
    print("피처 만드는 중 (Mann-Kendall 은 조금 걸립니다)...")
    df, rule = build(lab)
    y = df["_y"].to_numpy()
    pid = df["_pid"].to_numpy()
    X = df.drop(columns=["_y", "_pid"])
    X = X.fillna(X.median())
    g0 = pd.factorize(pid)[0]

    base_cols = [c for c in X.columns
                 if any(c == k + s for k in DIRECTION for s in ("", "_z", "_base"))]
    trend_cols = [c for c in X.columns if c not in base_cols]
    print(f"표본 {len(df)} · 참가자 {df['_pid'].nunique()} "
          f"· 배포본 {len(base_cols)} · 추세 {len(trend_cols)} "
          f"· 양성률 {y.mean():.1%}\n")

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

    print(f"=== {title} ===\n")
    print(f"  {'구성':18s} {'내부 AUC':>9} {'95%':>15}")
    print(f"  {'-'*18} {'-'*9} {'-'*15}")
    for k, o in CAND.items():
        lo, hi = np.nanpercentile(bw[k], [2.5, 97.5])
        print(f"  {k:18s} {within_of(o):9.3f} {lo:.3f}~{hi:.3f}")

    print("\n  === 배포본 대비 (같은 리샘플에서의 차) ===\n")
    base = np.array(bw["② 배포본 (z 만)"])
    for k in ("③ 추세만", "④ 배포본 + 추세"):
        d = np.array(bw[k]) - base
        lo, hi = np.nanpercentile(d, [2.5, 97.5])
        sig = "✅" if lo > 0 else ("⛔" if hi < 0 else "  ")
        print(f"  {k:18s} {np.nanmean(d):+.3f} [{lo:+.3f},{hi:+.3f}] {sig}")

    #  어떤 추세 피처가 뽑혔나
    m = make_pipeline(StandardScaler(),
                      SelectKBest(f_classif, k=min(21, X.shape[1])),
                      LogisticRegression(max_iter=3000, C=0.1)).fit(X, y)
    sel = np.array(X.columns)[m.named_steps["selectkbest"].get_support()]
    print(f"\n  전체에서 고른 21개 중 추세 피처: "
          f"{sum(1 for c in sel if c in trend_cols)}개")
    print("   ", ", ".join([c for c in sel if c in trend_cols][:8]))


if __name__ == "__main__":
    main()
