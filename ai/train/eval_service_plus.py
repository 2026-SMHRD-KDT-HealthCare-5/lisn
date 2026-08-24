# -*- coding: utf-8 -*-
r"""테이블에 있는데 안 쓰던 컬럼을 넣는다 — 2026.08.25

    .venv/Scripts/python.exe ai/train/eval_service_plus.py [모드]
      모드: tense(기본) | narrow | happy

## 왜

현재 판정 규칙은 지표를 **7개**만 씁니다. 그런데 `LIFELOG_METRICS` 에는
**17개**가 있습니다. 앱이 이미 넣고 있고, DB 에 이미 쌓이는데, 판정이
안 보고 있던 것들입니다.

| 안 쓰던 것 | 왜 볼 만한가 |
|---|---|
| `deep_sleep_min` · `rem_sleep_min` · `light_sleep_min` | 총수면이 같아도 **구성**이 무너지는 일이 있다 |
| `heart_rate` | 각성·긴장의 대표 지표 |
| `calories` · `distance` · `total_active_min` | 걸음만으로는 활동 강도가 안 보인다 |
| `sleep_end_at` · `activity_end_at` | 기상 시각·활동 종료 — 위상 지연이 여기 찍힌다 |

`main.py` 의 `_FEATURES` 주석은 「심박·HRV 는 넣지 않았다 — 기업 제공
데이터에 없고 삼성헬스가 HRV 를 안 넘긴다」고 적고 있습니다. **HRV 는
맞지만 `heart_rate` 는 컬럼이 있고 Health Connect 도 넘깁니다.**

## 재는 방식

`eval_rule_features.py` 와 같습니다 — 지표마다 (원값 · 개인 기준선 대비
z · 기준선 중앙값), 참가자 분할 + 중첩 교차검증, 참가자 내부 AUC.

**비교 대상은 현재 배포본**(규칙 입력 7개 = 21 피처, 내부 AUC 0.609)입니다.

⚠ **없는 지표는 쓰지 않습니다.** LifeSnaps 에서 못 만드는 것은 넣지 않고,
  실기기에서 비는 것은 서버가 중앙값으로 메우고 절반 미만이면 규칙으로
  물러섭니다(`model_score.py`).
"""
import importlib.util
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
spec = importlib.util.spec_from_file_location("rf", "ai/train/eval_rule_features.py")
sys.argv = [sys.argv[0], MODE]
rf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rf)

PQ = Path("ai/data_raw/lifesnaps/parquet")
HCSV = Path("ai/data_raw/lifesnaps/rais_anonymized/csv_rais_anonymized/"
            "hourly_fitbit_sema_df_unprocessed.csv")
BASE_DAYS = 14
K_GRID = [8, 12, 21, 30, 45]

#  현재 규칙이 쓰는 7개
RULE_KEYS = ["total_sleep_min", "steps", "sleep_efficiency_pct",
             "sleep_onset_min", "awake_min", "sleep_start_min",
             "activity_start_min"]
#  테이블에 있는데 판정이 안 보던 것
EXTRA_KEYS = ["deep_sleep_min", "light_sleep_min", "rem_sleep_min",
              "heart_rate", "calories", "total_active_min",
              "sleep_end_min", "activity_end_min", "deep_ratio", "rem_ratio"]


def clock_min(dt, origin=0):
    """시각을 분으로. origin 시를 0 으로 삼아 자정을 넘어도 단조증가한다."""
    if pd.isna(dt):
        return None
    m = dt.hour * 60 + dt.minute
    cut = origin * 60
    return m - cut if m >= cut else m + (1440 - cut)


def build(lab):
    h = pd.read_csv(HCSV, usecols=["id", "date", "hour", "steps", "bpm", "calories"])
    h = h.rename(columns={"id": "pid"})
    h["pid"] = h.pid.astype(str)
    h["date"] = pd.to_datetime(h["date"])
    hs = h.groupby(["pid", "date", "hour"], as_index=False)[
        ["steps", "bpm", "calories"]].mean().sort_values(["pid", "date", "hour"])
    steps_by = {p: g for p, g in hs.groupby("pid")}

    sl = pd.read_parquet(PQ / "sleep.parquet")
    sl["date"] = pd.to_datetime(sl.dateOfSleep, errors="coerce").dt.normalize()
    sl["startTime"] = pd.to_datetime(sl.startTime, errors="coerce")
    sl["endTime"] = pd.to_datetime(sl.endTime, errors="coerce")

    #  ⚠ 수면 단계는 levels.summary 안에 들어 있다 — 우리 스키마의
    #    deep_sleep_min·light_sleep_min·rem_sleep_min 에 그대로 대응한다.
    def stage(v, name):
        try:
            return float(v["summary"][name]["minutes"])
        except (TypeError, KeyError, IndexError):
            return np.nan

    for nm in ("deep", "light", "rem"):
        sl[nm + "_sleep_min"] = sl.levels.map(lambda v, n=nm: stage(v, n))

    ds = sl.groupby(["pid", "date"], as_index=False).agg(
        total_sleep_min=("minutesAsleep", "sum"),
        awake_min=("minutesAwake", "sum"),
        sleep_onset_min=("minutesToFallAsleep", "mean"),
        sleep_efficiency_pct=("efficiency", "mean"),
        deep_sleep_min=("deep_sleep_min", "sum"),
        light_sleep_min=("light_sleep_min", "sum"),
        rem_sleep_min=("rem_sleep_min", "sum"),
        _st=("startTime", "min"), _en=("endTime", "max"))
    ds["sleep_start_min"] = ds._st.map(lambda d: clock_min(d, 18))
    ds["sleep_end_min"] = ds._en.map(lambda d: clock_min(d, 0))
    #  총수면이 같아도 구성이 무너지는 일이 있다 — 비율로도 본다
    tot = ds.total_sleep_min.replace(0, np.nan)
    ds["deep_ratio"] = ds.deep_sleep_min / tot
    ds["rem_ratio"] = ds.rem_sleep_min / tot
    sleep_by = {p: g.drop(columns=["_st", "_en"]).set_index("date")
                for p, g in ds.groupby("pid")}

    rows, rule = [], []
    for r in lab.itertuples():
        day = pd.Timestamp(r.ts).normalize()
        hcut = r.ts.hour
        g = steps_by.get(r.pid)
        if g is None:
            continue
        today = g[(g.date == day) & (g.hour <= hcut)]
        hist_days = g[(g.date < day) & (g.date >= day - pd.Timedelta(days=BASE_DAYS))]
        hist_cut = hist_days[hist_days.hour <= hcut]
        if not len(today) or not len(hist_cut):
            continue

        vals = {}
        #  ── 활동: 라벨 시각까지의 누적 ──
        vals["steps"] = (today.steps.sum(),
                         hist_cut.groupby("date").steps.sum().tolist())
        vals["calories"] = (today.calories.sum(),
                            hist_cut.groupby("date").calories.sum().tolist())
        vals["heart_rate"] = (today.bpm.mean(),
                              hist_cut.groupby("date").bpm.mean().tolist())
        act = today[today.steps > 0]
        vals["activity_start_min"] = (
            float(act.hour.min() * 60) if len(act) else None,
            (hist_days[hist_days.steps > 0].groupby("date").hour.min() * 60).tolist())
        vals["activity_end_min"] = (
            float(act.hour.max() * 60) if len(act) else None,
            (hist_cut[hist_cut.steps > 0].groupby("date").hour.max() * 60).tolist())
        #  총활동시간 = 걸음이 있던 시간 수 × 60 (우리 total_active_min 의 근사)
        vals["total_active_min"] = (
            float(len(act) * 60),
            (hist_cut[hist_cut.steps > 0].groupby("date").size() * 60).tolist())

        #  ── 수면: 전날 밤 것이라 라벨 시각 이전에 확정돼 있다 ──
        sg = sleep_by.get(r.pid)
        if sg is not None:
            hsl = sg[(sg.index < day) & (sg.index >= day - pd.Timedelta(days=BASE_DAYS))]
            cur = sg.loc[day] if day in sg.index else None
            for col in ("total_sleep_min", "awake_min", "sleep_onset_min",
                        "sleep_efficiency_pct", "sleep_start_min", "sleep_end_min",
                        "deep_sleep_min", "light_sleep_min", "rem_sleep_min",
                        "deep_ratio", "rem_ratio"):
                v = float(cur[col]) if cur is not None and pd.notna(cur[col]) else None
                vals[col] = (v, hsl[col].dropna().tolist() if len(hsl) else [])

        f, devs = {}, []
        for col in RULE_KEYS + EXTRA_KEYS:
            if col not in vals:
                continue
            v, hist = vals[col]
            z = rf.robust_z(v, hist)
            f[col] = v if v is not None else np.nan
            f[col + "_z"] = z if z is not None else np.nan
            f[col + "_base"] = float(np.median(hist)) if hist else np.nan
            #  규칙 점수는 규칙이 쓰는 7개로만 만든다 — 비교 기준이므로
            if col in RULE_KEYS and z is not None:
                down = col in ("total_sleep_min", "steps", "sleep_efficiency_pct")
                devs.append(max(0.0, -z if down else z))
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
    print(f"라벨 {len(lab)}건 · 참가자 {lab.pid.nunique()}")
    print("피처 만드는 중...")
    df, rule = build(lab)
    y = df["_y"].to_numpy()
    pid = df["_pid"].to_numpy()
    X = df.drop(columns=["_y", "_pid"])
    X = X.fillna(X.median())
    g0 = pd.factorize(pid)[0]

    rule_cols = [c for c in X.columns
                 if c.split("_z")[0].split("_base")[0] in RULE_KEYS
                 or c in RULE_KEYS or any(c == k + s for k in RULE_KEYS
                                          for s in ("", "_z", "_base"))]
    rule_cols = [c for c in X.columns
                 if any(c == k + s for k in RULE_KEYS for s in ("", "_z", "_base"))]
    print(f"표본 {len(df)} · 참가자 {df['_pid'].nunique()} "
          f"· 규칙 입력 {len(rule_cols)} · 전체 {X.shape[1]} "
          f"· 양성률 {y.mean():.1%}\n")

    def nested(Xd, tag):
        o = np.full(len(df), np.nan)
        picks = []
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
            picks.append(best_k)
            m = make_pipeline(StandardScaler(),
                              SelectKBest(f_classif, k=min(best_k, Xd.shape[1])),
                              LogisticRegression(max_iter=3000, C=0.1))
            m.fit(Xd.iloc[tr], y[tr])
            o[te] = m.predict_proba(Xd.iloc[te])[:, 1]
        print(f"  {tag}: 폴드별 K = {picks}")
        return o

    rk = lambda v: pd.Series(v).rank(pct=True).to_numpy()
    CAND = {
        "① 현재 규칙": rk(rule),
        "② 지금 배포본 (규칙 입력)": rk(nested(X[rule_cols], "배포본")),
        "③ 테이블 전체 입력": rk(nested(X, "확장")),
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

    print(f"\n=== {title} ===\n")
    print(f"  {'구성':26s} {'전체':>7} {'95%':>15}  {'내부':>7} {'95%':>15}")
    print(f"  {'-'*26} {'-'*7} {'-'*15}  {'-'*7} {'-'*15}")
    for k, o in CAND.items():
        lo, hi = np.percentile(boot[k], [2.5, 97.5])
        wl, wh = np.nanpercentile(bootw[k], [2.5, 97.5])
        print(f"  {k:26s} {roc_auc_score(y, o):7.3f} {lo:.3f}~{hi:.3f}  "
              f"{within_of(o):7.3f} {wl:.3f}~{wh:.3f}")

    print("\n  === 이득 (같은 리샘플에서의 차) ===\n")
    for basekey in ("① 현재 규칙", "② 지금 배포본 (규칙 입력)"):
        b = np.array(bootw[basekey])
        for k in CAND:
            if k == basekey or list(CAND).index(k) < list(CAND).index(basekey):
                continue
            d = np.array(bootw[k]) - b
            lo, hi = np.nanpercentile(d, [2.5, 97.5])
            sig = "✅" if lo > 0 else ("⛔" if hi < 0 else "  ")
            print(f"  {k:26s} vs {basekey:24s} "
                  f"내부 {np.nanmean(d):+.3f} [{lo:+.3f},{hi:+.3f}] {sig}")


if __name__ == "__main__":
    main()
