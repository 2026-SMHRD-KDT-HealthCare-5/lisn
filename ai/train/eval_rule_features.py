# -*- coding: utf-8 -*-
r"""규칙과 **같은 입력**으로, 집계 방식만 학습된 것으로 바꾼다. 2026.08.25

    .venv/Scripts/python.exe ai/train/eval_rule_features.py [모드]
      모드: tense(기본) | narrow | happy

## 왜 이 형태인가

`eval_rule_vs_model.py` 가 보여준 것 — 모델이 현재 규칙을 크게 이깁니다
(내부 AUC 0.628 vs 0.503). 그런데 그 모델은 리듬·심박 등 **60개 피처**를
씁니다. 판정 서버에 넣으려면 그 입력을 다 만들어야 하고, 실기기에서
빠지는 것이 하나라도 있으면 통째로 못 돕니다.

**더 작고 확실한 변경이 있습니다.**

현재 규칙이 하는 일은 두 단계입니다.

    ① 지표 7개의 개인 기준선 이탈(z)을 잰다      ← 근거 있음
    ② 상위 3개를 평균 내고 4.0 으로 나눈다        ← **임의값** (main.py 자인)

**①은 그대로 두고 ②만 학습된 집계로 바꿉니다.** 입력이 늘지 않으므로
지금 서버가 이미 읽는 것만으로 돌아갑니다.

    입력 = 7개 지표 × (원값 · 개인 기준선 대비 z · 기준선 중앙값)

## 비교 대상

    ① 현재 규칙           상위 3개 평균 / 4.0
    ② 학습된 집계         같은 입력, 로지스틱 회귀
    ③ max(규칙, 학습)     ⭐ 규칙이 올린 경보는 하나도 안 내려간다

⚠ **참가자 분할 + 중첩 교차검증**입니다. K 선택에 평가 부분을 쓰지 않습니다.
⚠ **참가자 내부 AUC** 로 판정합니다 — 「이 사람의 나쁜 순간을 이 사람의
  좋은 순간보다 위로 올리는가」가 우리 서비스가 하는 일입니다.
"""
import importlib.util
import statistics
import sys
import warnings
from pathlib import Path

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
spec = importlib.util.spec_from_file_location("ef", "ai/train/eval_final.py")
ef = importlib.util.module_from_spec(spec)
sys.argv = [sys.argv[0], MODE]
spec.loader.exec_module(ef)

rvm_spec = importlib.util.spec_from_file_location("rvm", "ai/train/eval_rule_vs_model.py")

PQ = Path("ai/data_raw/lifesnaps/parquet")
HCSV = Path("ai/data_raw/lifesnaps/rais_anonymized/csv_rais_anonymized/"
            "hourly_fitbit_sema_df_unprocessed.csv")

MIN_DAYS_FOR_BASELINE = 3
FULL_SCALE_Z = 4.0
BASE_DAYS = 14
K_GRID = [5, 8, 12, 21]

#  main.py `_FEATURES` 와 같은 지표·방향
RULE_FEATURES = [
    ("total_sleep_min", "down"),
    ("steps", "down"),
    ("sleep_efficiency_pct", "down"),
    ("sleep_onset_min", "up"),
    ("awake_min", "up"),
    ("sleep_start_min", "up"),
    ("activity_start_min", "up"),
]


def robust_z(value, history):
    """main.py `_robust_z` 를 그대로 옮긴 것."""
    vals = [v for v in history if v is not None and not pd.isna(v)]
    if value is None or pd.isna(value) or len(vals) < MIN_DAYS_FOR_BASELINE:
        return None
    med = statistics.median(vals)
    diff = value - med
    mad = statistics.median([abs(v - med) for v in vals])
    if mad:
        return 0.6745 * diff / mad
    mean_ad = sum(abs(v - med) for v in vals) / len(vals)
    if mean_ad:
        return diff / (1.253314 * mean_ad)
    return 0.0 if diff == 0 else (FULL_SCALE_Z if diff > 0 else -FULL_SCALE_Z)


def sleep_start_min(dt):
    if pd.isna(dt):
        return None
    m = dt.hour * 60 + dt.minute
    return m - 1080 if m >= 1080 else m + 360


def build(lab):
    """라벨마다 규칙 입력 7종의 (원값 · z · 기준선) 과 규칙 점수를 함께 낸다."""
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
    ds["sleep_start_min"] = ds._s.map(sleep_start_min)
    sleep_by = {p: g.drop(columns=["_s"]).set_index("date")
                for p, g in ds.groupby("pid")}

    rows, rule = [], []
    for r in lab.itertuples():
        day = pd.Timestamp(r.ts).normalize()
        hcut = r.ts.hour
        g = steps_by.get(r.pid)
        if g is None:
            continue
        hist_days = g[(g.date < day) & (g.date >= day - pd.Timedelta(days=BASE_DAYS))]

        #  ⚠ 걸음·활동개시는 라벨 시각까지만 — 미래를 보지 않는다
        vals = {
            "steps": (g[(g.date == day) & (g.hour <= hcut)].steps.sum(),
                      hist_days[hist_days.hour <= hcut].groupby("date").steps.sum().tolist()),
        }
        td = g[(g.date == day) & (g.hour <= hcut) & (g.steps > 0)]
        vals["activity_start_min"] = (
            float(td.hour.min() * 60) if len(td) else None,
            (hist_days[hist_days.steps > 0].groupby("date").hour.min() * 60).tolist())

        sg = sleep_by.get(r.pid)
        if sg is not None:
            hsl = sg[(sg.index < day) & (sg.index >= day - pd.Timedelta(days=BASE_DAYS))]
            cur = sg.loc[day] if day in sg.index else None
            for col, _ in RULE_FEATURES:
                if col in vals:
                    continue
                v = float(cur[col]) if cur is not None and pd.notna(cur[col]) else None
                vals[col] = (v, hsl[col].dropna().tolist() if len(hsl) else [])

        f, devs = {}, []
        for col, direction in RULE_FEATURES:
            if col not in vals:
                continue
            v, hist = vals[col]
            z = robust_z(v, hist)
            f[col] = v if v is not None else np.nan
            f[col + "_z"] = z if z is not None else np.nan
            f[col + "_base"] = float(np.median(hist)) if hist else np.nan
            if z is not None:
                devs.append(max(0.0, -z if direction == "down" else z))
        if not devs:
            continue
        top = sorted(devs, reverse=True)[:3]
        rule.append(min(1.0, sum(top) / len(top) / FULL_SCALE_Z))
        f["_y"] = int(r.y)
        f["_pid"] = r.pid
        rows.append(f)

    return pd.DataFrame(rows), np.array(rule)


def main():
    lab, title = ef.load_labels()
    print(f"라벨 {len(lab)}건 · 참가자 {lab.pid.nunique()}")
    print("규칙 입력 만드는 중...")
    df, rule = build(lab)
    #  ⚠ 결측을 0 으로 메우면 「없음」이 신호가 된다. 중앙값으로 메운다.
    y = df["_y"].to_numpy()
    pid = df["_pid"].to_numpy()
    X = df.drop(columns=["_y", "_pid"])
    X = X.fillna(X.median())
    g0 = pd.factorize(pid)[0]
    print(f"표본 {len(df)} · 참가자 {df._pid.nunique()} · 피처 {X.shape[1]} "
          f"· 양성률 {y.mean():.1%}\n")

    def nested():
        o = np.full(len(df), np.nan)
        picks = []
        for tr, te in GroupKFold(5).split(X, y, groups=g0):
            if len(np.unique(y[tr])) < 2:
                continue
            gin = g0[tr]
            best_k, best_s = K_GRID[0], -1
            for k in K_GRID:
                if k > X.shape[1]:
                    continue
                oin = np.full(len(tr), np.nan)
                for a, b in GroupKFold(4).split(X.iloc[tr], y[tr], groups=gin):
                    if len(np.unique(y[tr][a])) < 2:
                        continue
                    m = make_pipeline(StandardScaler(), SelectKBest(f_classif, k=k),
                                      LogisticRegression(max_iter=3000, C=0.1))
                    m.fit(X.iloc[tr].iloc[a], y[tr][a])
                    oin[b] = m.predict_proba(X.iloc[tr].iloc[b])[:, 1]
                kk = ~np.isnan(oin)
                if kk.sum() < 30 or len(np.unique(y[tr][kk])) < 2:
                    continue
                s = roc_auc_score(y[tr][kk], oin[kk])
                if s > best_s:
                    best_k, best_s = k, s
            picks.append(best_k)
            m = make_pipeline(StandardScaler(), SelectKBest(f_classif, k=best_k),
                              LogisticRegression(max_iter=3000, C=0.1))
            m.fit(X.iloc[tr], y[tr])
            o[te] = m.predict_proba(X.iloc[te])[:, 1]
        print(f"  폴드별로 고른 K = {picks}")
        return o

    model = nested()
    rk = lambda v: pd.Series(v).rank(pct=True).to_numpy()
    r_rule, r_model = rk(rule), rk(model)
    CAND = {
        "① 현재 규칙": r_rule,
        "② 학습된 집계": r_model,
        "③ max(규칙, 학습)": np.maximum(r_rule, r_model),
        "④ 규칙 50% + 학습 50%": 0.5 * r_rule + 0.5 * r_model,
    }

    def within_of(o, idx=None):
        v = []
        pp = pid if idx is None else pid[idx]
        oo = o if idx is None else o[idx]
        yy = y if idx is None else y[idx]
        for p in np.unique(pp):
            k = pp == p
            if k.sum() >= 8 and len(np.unique(yy[k])) > 1:
                v.append(roc_auc_score(yy[k], oo[k]))
        return np.mean(v) if v else np.nan

    rng = np.random.default_rng(42)
    pids = np.unique(pid)
    boot = {k: [] for k in CAND}
    bootw = {k: [] for k in CAND}
    for _ in range(2000):
        smp = rng.choice(pids, len(pids), replace=True)
        idx = np.concatenate([np.where(pid == p)[0] for p in smp])
        if len(np.unique(y[idx])) < 2:
            continue
        for k, o in CAND.items():
            boot[k].append(roc_auc_score(y[idx], o[idx]))
            bootw[k].append(within_of(o, idx))

    print(f"\n=== {title} · 같은 입력, 집계만 바꿈 ===\n")
    print(f"  {'구성':22s} {'전체':>7} {'95%':>15}  {'내부':>7} {'95%':>15}")
    print(f"  {'-'*22} {'-'*7} {'-'*15}  {'-'*7} {'-'*15}")
    for k, o in CAND.items():
        lo, hi = np.percentile(boot[k], [2.5, 97.5])
        wl, wh = np.nanpercentile(bootw[k], [2.5, 97.5])
        print(f"  {k:22s} {roc_auc_score(y, o):7.3f} {lo:.3f}~{hi:.3f}  "
              f"{within_of(o):7.3f} {wl:.3f}~{wh:.3f}")

    print(f"\n  === 현재 규칙 대비 이득 (같은 리샘플에서의 차) ===\n")
    base, basew = np.array(boot["① 현재 규칙"]), np.array(bootw["① 현재 규칙"])
    ok = []
    for k in CAND:
        if k.startswith("①"):
            continue
        d, dw = np.array(boot[k]) - base, np.array(bootw[k]) - basew
        lo, hi = np.percentile(d, [2.5, 97.5])
        wl, wh = np.nanpercentile(dw, [2.5, 97.5])
        sig = "✅" if wl > 0 else ("⛔" if wh < 0 else "  ")
        print(f"  {k:22s} 전체 {d.mean():+.3f} [{lo:+.3f},{hi:+.3f}]  "
              f"내부 {np.nanmean(dw):+.3f} [{wl:+.3f},{wh:+.3f}] {sig}")
        if wl > 0:
            ok.append((k, np.nanmean(dw), wl))
    print()
    if ok:
        b = max(ok, key=lambda t: t[1])
        print(f"  ⭐ **{b[0]}** — 내부 이득 {b[1]:+.3f}, 95% 하한 {b[2]:+.3f} > 0")
        print("     **입력을 하나도 안 늘리고** 현재 규칙을 이깁니다.")
    else:
        print("  ⛔ 같은 입력만으로는 현재 규칙을 유의하게 넘지 못했습니다.")


if __name__ == "__main__":
    main()
