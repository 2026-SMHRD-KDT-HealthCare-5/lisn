# -*- coding: utf-8 -*-
r"""판정에 넣을 근거를 만든다 — 현재 규칙 vs 모델 vs 결합. 2026.08.25

    .venv/Scripts/python.exe ai/train/eval_rule_vs_model.py [모드]
      모드: tense(기본) | narrow | happy

## 질문을 바로 세웁니다

지금까지 「모델이 0.9 를 넘는가」를 물었고 답은 계속 아니오였습니다.
그런데 **판정에 들어갈지 말지를 정하는 질문은 그게 아닙니다.**

> **지금 쓰는 규칙보다 나은가?**

`ai/server/main.py` 는 스스로 이렇게 적고 있습니다 —
「임계값도 선행연구값이 아닌 임의값이다」·「성능 근거로 쓰지 마세요」.
**현재 규칙은 한 번도 검증된 적이 없습니다.** 그러면 기준선은 0.9 가
아니라 **그 규칙의 실측치**입니다.

## 규칙을 그대로 옮겼습니다

`main.py` 의 `_robust_z`(중앙값·MAD, MeanAD 폴백, 평평하면 최대) 와
`_predict`(방향 있는 이탈만 셈 → 상위 3개 평균 / `FULL_SCALE_Z`) 를
같은 식으로 구현했습니다. 지표도 맞췄습니다.

    총수면 · 걸음 · 수면효율 · 입면지연 · 야간각성 · 입면시각 · 활동개시

> ⚠ **한 곳만 다릅니다.** 서비스는 하루가 끝난 뒤 판정하지만 라벨은 하루
> 중간에 붙습니다. 그래서 걸음은 **그 시각까지의 누적**을 같은 시각의
> 기준선과 견줍니다. 미래를 보지 않기 위한 것이고, 나머지(수면·활동개시)는
> 라벨 시각 이전에 이미 확정된 값이라 그대로 씁니다.

## 결합은 「올릴 수만 있게」 합니다

```
결합 = max(규칙, 모델)          ← 순위 공간에서
```

**규칙이 올린 경보는 하나도 안 내려갑니다.** 모델이 고장 나도 현재
안전 수준 아래로 못 내려갑니다. `NFR-DV-003`(외부 장애 시 규칙 단독
동작)과 같은 발상입니다.

가중 결합 `(1-w)·규칙 + w·모델` 도 함께 재서, 어느 쪽이 나은지 봅니다.

## 판정 기준

**차이의 95% 신뢰구간이 0 을 넘어야** 넣습니다. 참가자 단위 부트스트랩
으로 규칙과 결합의 **같은 리샘플에서의 차이**를 잽니다 — 각각의 구간이
겹치는지 보는 것보다 정확합니다.
"""
import importlib.util
import statistics
import sys
import warnings
from pathlib import Path

import lightgbm as lgb
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
#  두 번째 인자가 `feasible` 이면 **우리 서비스가 실제로 가진 입력만** 씁니다.
FEASIBLE = len(sys.argv) > 2 and sys.argv[2] == "feasible"

#  ⚠ LIFELOG_METRICS 에 없는 것 — Fitbit 전용 지표라 우리 앱이 못 받습니다.
#    RMSSD·LF/HF   : 삼성헬스가 Health Connect 에 HRV 를 안 넘깁니다
#    STRESS_*      : Fitbit 자체 산출 점수
#    br·br_sd      : 수면 중 호흡률
#    temp          : 손목 체온 센서
#    hr15~hr180    : 초 단위 심박. 우리는 15분 간격 한 값씩만 받습니다
_INFEASIBLE_HEADS = ("rmssd", "lfhf", "STRESS_SCORE", "SLEEP_POINTS",
                     "RESPONSIVENESS_POINTS", "EXERTION_POINTS", "br", "br_sd",
                     "temp", "hr15", "hr30", "hr60", "hr180")


def feasible_cols(cols):
    """우리 서비스가 채울 수 있는 컬럼만 남긴다."""
    out = []
    for c in cols:
        head = c.split("_z")[0].split("_base")[0]
        if any(head == h or c.startswith(h + "_") or c == h
               for h in _INFEASIBLE_HEADS):
            continue
        out.append(c)
    return out
spec = importlib.util.spec_from_file_location("ef", "ai/train/eval_final.py")
ef = importlib.util.module_from_spec(spec)
sys.argv = [sys.argv[0], MODE]
spec.loader.exec_module(ef)

PQ = Path("ai/data_raw/lifesnaps/parquet")
HCSV = Path("ai/data_raw/lifesnaps/rais_anonymized/csv_rais_anonymized/"
            "hourly_fitbit_sema_df_unprocessed.csv")

#  ── main.py 와 같은 상수 ──
MIN_DAYS_FOR_BASELINE = 3
FULL_SCALE_Z = 4.0
BASE_DAYS = 14
K_GRID = [10, 15, 20, 30, 50]

#  ── main.py `_FEATURES` 와 같은 지표·방향 ──
RULE_FEATURES = [
    ("총수면", "total_sleep_min", "down"),
    ("걸음수", "steps", "down"),
    ("수면효율", "sleep_efficiency_pct", "down"),
    ("입면지연", "sleep_onset_min", "up"),
    ("야간각성", "awake_min", "up"),
    ("입면시각", "sleep_start_min", "up"),
    ("활동개시", "activity_start_min", "up"),
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
    if diff == 0:
        return 0.0
    return FULL_SCALE_Z if diff > 0 else -FULL_SCALE_Z


def sleep_start_min(dt):
    """입면 시각을 18시 기준 분으로 — main.py `_sleep_start_min` 과 같다."""
    if pd.isna(dt):
        return None
    m = dt.hour * 60 + dt.minute
    return m - 1080 if m >= 1080 else m + 360


def build_rule(lab):
    """라벨마다 현재 규칙의 anomaly_score 를 계산한다."""
    h = pd.read_csv(HCSV, usecols=["id", "date", "hour", "steps"])
    h = h.rename(columns={"id": "pid"})
    h["pid"] = h.pid.astype(str)
    h["date"] = pd.to_datetime(h["date"])
    hs = h.groupby(["pid", "date", "hour"], as_index=False).steps.mean()

    #  ── 하루 지표: 그 시각까지의 누적 걸음 · 활동개시 ──
    hs = hs.sort_values(["pid", "date", "hour"])

    sl = pd.read_parquet(PQ / "sleep.parquet")
    sl["date"] = pd.to_datetime(sl.dateOfSleep, errors="coerce").dt.normalize()
    sl["startTime"] = pd.to_datetime(sl.startTime, errors="coerce")
    day_sleep = sl.groupby(["pid", "date"], as_index=False).agg(
        total_sleep_min=("minutesAsleep", "sum"),
        awake_min=("minutesAwake", "sum"),
        sleep_onset_min=("minutesToFallAsleep", "mean"),
        sleep_efficiency_pct=("efficiency", "mean"),
        _start=("startTime", "min"))
    day_sleep["sleep_start_min"] = day_sleep._start.map(sleep_start_min)
    day_sleep = day_sleep.drop(columns=["_start"])
    sleep_by = {p: g.set_index("date") for p, g in day_sleep.groupby("pid")}

    steps_by = {p: g for p, g in hs.groupby("pid")}

    out = []
    for r in lab.itertuples():
        day = pd.Timestamp(r.ts).normalize()
        hcut = r.ts.hour
        g = steps_by.get(r.pid)
        sg = sleep_by.get(r.pid)
        if g is None:
            out.append(np.nan)
            continue

        #  걸음: 그 시각까지의 누적 (미래를 보지 않기 위해)
        cur_steps = g[(g.date == day) & (g.hour <= hcut)].steps.sum()
        hist_days = g[(g.date < day) & (g.date >= day - pd.Timedelta(days=BASE_DAYS))]
        hist_steps = hist_days[hist_days.hour <= hcut].groupby("date").steps.sum()

        #  활동개시: 오늘 처음 걸은 시각(분). 라벨 시각 이전만 본다.
        td = g[(g.date == day) & (g.hour <= hcut) & (g.steps > 0)]
        cur_act = float(td.hour.min() * 60) if len(td) else None
        ha = hist_days[hist_days.steps > 0].groupby("date").hour.min() * 60

        vals = {"steps": (cur_steps, hist_steps.tolist()),
                "activity_start_min": (cur_act, ha.tolist())}

        #  수면: 전날 밤 것이라 라벨 시각 이전에 확정돼 있다
        if sg is not None:
            hist_sleep = sg[(sg.index < day)
                            & (sg.index >= day - pd.Timedelta(days=BASE_DAYS))]
            row = sg.loc[day] if day in sg.index else None
            for _, col, _ in RULE_FEATURES:
                if col in ("steps", "activity_start_min"):
                    continue
                cur = float(row[col]) if row is not None and pd.notna(row[col]) else None
                vals[col] = (cur, hist_sleep[col].dropna().tolist()
                             if len(hist_sleep) else [])

        devs = []
        for _, col, direction in RULE_FEATURES:
            if col not in vals:
                continue
            cur, hist = vals[col]
            z = robust_z(cur, hist)
            if z is None:
                continue
            signed = -z if direction == "down" else z
            devs.append(max(0.0, signed))     # 나쁜 쪽으로 벗어난 것만
        if not devs:
            out.append(np.nan)
            continue
        top = sorted(devs, reverse=True)[:3]   # main.py 와 같이 상위 3개
        out.append(min(1.0, sum(top) / len(top) / FULL_SCALE_Z))
    return np.array(out, dtype=float)


def make(kind, k):
    if kind == "lr":
        return make_pipeline(StandardScaler(), SelectKBest(f_classif, k=k),
                             LogisticRegression(max_iter=3000, C=0.1))
    return make_pipeline(SelectKBest(f_classif, k=k),
                         lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05,
                                            num_leaves=31, min_child_samples=20,
                                            subsample=0.8, colsample_bytree=0.8,
                                            random_state=42, verbose=-1))


def main():
    lab, title = ef.load_labels()
    print(f"라벨 {len(lab)}건 · 참가자 {lab.pid.nunique()}")
    print("피처 만드는 중...")
    df = ef.build(lab)

    #  build 가 채택한 행만 lab 과 되맞춘다
    lab2 = lab.copy()
    lab2["hour"] = lab2.ts.dt.hour
    lab2["minute_of_day"] = lab2.ts.dt.hour * 60 + lab2.ts.dt.minute
    lab2 = lab2.rename(columns={"pid": "_pid", "y": "_y"})
    m = df.merge(lab2[["_pid", "_y", "hour", "minute_of_day", "ts"]],
                 on=["_pid", "_y", "hour", "minute_of_day"], how="left")
    m = m.drop_duplicates(subset=list(df.columns), keep="first")
    m = m[m.ts.notna()].reset_index(drop=True)

    print("현재 규칙 계산 중...")
    lab_m = m[["_pid", "ts"]].rename(columns={"_pid": "pid"})
    lab_m = lab_m.assign(y=m["_y"].to_numpy())
    rule = build_rule(lab_m)

    ok = ~np.isnan(rule)
    m, rule = m[ok].reset_index(drop=True), rule[ok]
    y = m["_y"].to_numpy()
    pid = m["_pid"].to_numpy()
    X = m.drop(columns=["_y", "_pid", "ts"])
    if FEASIBLE:
        keep = feasible_cols(list(X.columns))
        print(f"⚙ 서비스 가용 입력만: {X.shape[1]} → {len(keep)}개")
        X = X[keep]
    g0 = pd.factorize(pid)[0]
    print(f"표본 {len(m)} · 참가자 {m._pid.nunique()} · 양성률 {y.mean():.1%}")
    print(f"규칙 점수 분포: 평균 {rule.mean():.3f} · 0 인 비율 "
          f"{(rule == 0).mean():.1%} · 고유값 {len(np.unique(rule))}\n")

    #  ── 모델: 중첩 교차검증 (K 선택에 평가 부분을 쓰지 않는다) ──
    def nested(kind, labels=None):
        yy = y if labels is None else labels
        o = np.full(len(m), np.nan)
        for tr, te in GroupKFold(5).split(X, yy, groups=g0):
            if len(np.unique(yy[tr])) < 2:
                continue
            gin = g0[tr]
            best_k, best_s = K_GRID[0], -1
            for k in K_GRID:
                if k > X.shape[1]:
                    continue
                oin = np.full(len(tr), np.nan)
                for a, b in GroupKFold(4).split(X.iloc[tr], yy[tr], groups=gin):
                    if len(np.unique(yy[tr][a])) < 2:
                        continue
                    mm = make(kind, k)
                    mm.fit(X.iloc[tr].iloc[a], yy[tr][a])
                    oin[b] = mm.predict_proba(X.iloc[tr].iloc[b])[:, 1]
                kk = ~np.isnan(oin)
                if kk.sum() < 30 or len(np.unique(yy[tr][kk])) < 2:
                    continue
                s = roc_auc_score(yy[tr][kk], oin[kk])
                if s > best_s:
                    best_k, best_s = k, s
            mm = make(kind, min(best_k, X.shape[1]))
            mm.fit(X.iloc[tr], yy[tr])
            o[te] = mm.predict_proba(X.iloc[te])[:, 1]
        return o

    rk = lambda v: pd.Series(v).rank(pct=True).to_numpy()
    model = (rk(nested("lr")) + rk(nested("gb"))) / 2
    r_rule, r_model = rk(rule), rk(model)

    CAND = {
        "① 현재 규칙 단독": r_rule,
        "② 모델 단독": r_model,
        "③ max(규칙, 모델)": np.maximum(r_rule, r_model),
        "④ 규칙 70% + 모델 30%": 0.7 * r_rule + 0.3 * r_model,
        "⑤ 규칙 50% + 모델 50%": 0.5 * r_rule + 0.5 * r_model,
        "⑥ 규칙 30% + 모델 70%": 0.3 * r_rule + 0.7 * r_model,
    }

    def within_of(o, labels, idx=None):
        """참가자 내부 AUC 평균."""
        v = []
        pids = np.unique(pid if idx is None else pid[idx])
        for p in pids:
            k = (pid == p) if idx is None else (pid[idx] == p)
            oo = o if idx is None else o[idx]
            yy = labels if idx is None else labels[idx]
            if k.sum() >= 8 and len(np.unique(yy[k])) > 1:
                v.append(roc_auc_score(yy[k], oo[k]))
        return np.mean(v) if v else np.nan

    #  ── 참가자 단위 부트스트랩: 같은 리샘플에서 모든 후보를 함께 잰다 ──
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
            bootw[k].append(within_of(o, y, idx))

    print(f"=== {title} · 현재 규칙과 견주기 ===\n")
    print(f"  {'구성':22s} {'전체':>7} {'95%':>15}  {'내부':>7} {'95%':>15}")
    print(f"  {'-'*22} {'-'*7} {'-'*15}  {'-'*7} {'-'*15}")
    for k, o in CAND.items():
        a = roc_auc_score(y, o)
        lo, hi = np.percentile(boot[k], [2.5, 97.5])
        w = within_of(o, y)
        wl, wh = np.nanpercentile(bootw[k], [2.5, 97.5])
        print(f"  {k:22s} {a:7.3f} {lo:.3f}~{hi:.3f}  {w:7.3f} {wl:.3f}~{wh:.3f}")

    #  ── 규칙 대비 차이: 같은 리샘플에서의 차 ──
    print(f"\n  === 현재 규칙 대비 이득 (같은 리샘플에서의 차) ===\n")
    print(f"  {'구성':22s} {'전체 이득':>9} {'95%':>17}  {'내부 이득':>9} {'95%':>17}")
    print(f"  {'-'*22} {'-'*9} {'-'*17}  {'-'*9} {'-'*17}")
    base, basew = np.array(boot["① 현재 규칙 단독"]), np.array(bootw["① 현재 규칙 단독"])
    verdict = []
    for k in CAND:
        if k.startswith("①"):
            continue
        d = np.array(boot[k]) - base
        dw = np.array(bootw[k]) - basew
        lo, hi = np.percentile(d, [2.5, 97.5])
        wl, wh = np.nanpercentile(dw, [2.5, 97.5])
        sig = "✅" if wl > 0 else ("⛔" if wh < 0 else "  ")
        print(f"  {k:22s} {d.mean():+9.3f} {lo:+.3f}~{hi:+.3f}  "
              f"{np.nanmean(dw):+9.3f} {wl:+.3f}~{wh:+.3f} {sig}")
        if wl > 0:
            verdict.append((k, np.nanmean(dw), wl))

    print()
    if verdict:
        best = max(verdict, key=lambda t: t[1])
        print(f"  ⭐ **{best[0]}** — 내부 AUC 이득 {best[1]:+.3f}, "
              f"95% 하한 {best[2]:+.3f} > 0")
        print("     현재 규칙보다 낫다는 근거가 있습니다. 판정에 넣을 수 있습니다.")
    else:
        print("  ⛔ 어느 구성도 현재 규칙을 유의하게 넘지 못했습니다.")


if __name__ == "__main__":
    main()
