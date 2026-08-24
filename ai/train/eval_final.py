# -*- coding: utf-8 -*-
r"""전부 합친 최종 검증 — 2026.08.25

    .venv/Scripts/python.exe ai/train/eval_final.py [모드]
      모드: narrow(기본) | wide | happy | tense

`extract_bson.py` 를 먼저 돌리세요.

## 여기까지 얻은 것을 한 번에 씁니다

| 출처 | 합친 것 |
|---|---|
| 시도 12 | 시간 단위 **활동 리듬**(무게중심·집중도·M10/L5·상대진폭) |
| 시도 13 | **같은 시간대 기준선**(`_samehour`) |
| 시도 14 | 로지스틱 회귀 + 트리 **순위 평균 앙상블** |
| 시도 16 | **정서가 라벨**(원본 `MOOD`, 피로 제외) · 분 단위 시각 |
| 시도 17 | 원본 BSON — **단기 심박 변동**(HRV 대용) · RMSSD · 스트레스 점수 · 호흡률 · 손목 체온 |

## ⚠ 분 단위 피처만으로는 오히려 나빴습니다

`eval_minute.py` 는 심박·일 단위 지표만 넣어 **0.519**(셔플과 구분 안 됨)
였습니다. 리듬 피처를 빼버린 것이 원인입니다 — **가장 잘 듣던 것을
새 재료로 갈아치우면 안 됩니다.** 그래서 여기서는 둘 다 넣습니다.

## ⚠ 미래를 보지 않습니다

라벨 시각 이전 값만 씁니다. 일 단위 지표(RMSSD·스트레스·수면·체온)는
**전날 것**만 씁니다 — 당일 값은 하루가 끝나야 확정되므로 예측 시점에
존재하지 않습니다.
"""
import sys
import warnings
import zipfile
from pathlib import Path

import bson
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

PQ = Path("ai/data_raw/lifesnaps/parquet")
ZIP = Path("ai/data_raw/lifesnaps/rais_anonymized.zip")
HCSV = Path("ai/data_raw/lifesnaps/rais_anonymized/csv_rais_anonymized/"
            "hourly_fitbit_sema_df_unprocessed.csv")
MODE = sys.argv[1] if len(sys.argv) > 1 else "narrow"
BASE_DAYS = 14

NEG_WIDE = {"TIRED", "TENSE/ANXIOUS", "SAD", "ANGER", "FEAR", "SADNESS"}
NEG_NARROW = {"TENSE/ANXIOUS", "SAD", "ANGER", "FEAR", "SADNESS"}
POS = {"HAPPY", "RESTED/RELAXED", "ALERT", "JOY"}
MIN = 60_000_000_000          # 1분(나노초)
DAY = 86_400_000_000_000


def load_labels():
    docs = bson.decode_all(
        zipfile.ZipFile(ZIP).read("rais_anonymized/mongo_rais_anonymized/sema.bson"))
    lab = pd.DataFrame([{"pid": str(d["user_id"]),
                         "ts": d["data"].get("COMPLETED_TS"),
                         "mood": d["data"].get("MOOD")} for d in docs])
    lab["ts"] = pd.to_datetime(lab["ts"], errors="coerce")
    lab = lab.dropna(subset=["ts"])
    if MODE == "happy":
        lab = lab[lab.mood.isin(POS | NEG_WIDE)].copy()
        lab["y"] = (lab.mood == "HAPPY").astype(int)
        title = "HAPPY"
    elif MODE == "tense":
        lab = lab[lab.mood.isin(POS | NEG_WIDE)].copy()
        lab["y"] = (lab.mood == "TENSE/ANXIOUS").astype(int)
        title = "TENSE/ANXIOUS"
    else:
        neg = NEG_WIDE if MODE == "wide" else NEG_NARROW
        lab = lab[lab.mood.isin(neg | POS)].copy()
        lab["y"] = lab.mood.isin(neg).astype(int)
        title = f"부정 정서 ({MODE})"
    lab = lab.drop_duplicates(subset=["pid", "ts"]).sort_values(["pid", "ts"])
    return lab.reset_index(drop=True), title


def rhythm(day_df):
    """하루치 시간별 걸음에서 리듬 지표 (시도 12)."""
    s = day_df.groupby("hour")["steps"].mean().reindex(range(24)).fillna(0).to_numpy()
    tot = s.sum()
    if tot < 50:
        return {}
    ang = 2 * np.pi * np.arange(24) / 24
    cx, cy = (s * np.cos(ang)).sum() / tot, (s * np.sin(ang)).sum() / tot
    hi10, lo5 = np.sort(s)[-10:].mean(), np.sort(s)[:5].mean()
    return {
        "r_center": (np.arctan2(cy, cx) % (2 * np.pi)) * 24 / (2 * np.pi),
        "r_conc": np.hypot(cx, cy), "r_M10": hi10, "r_L5": lo5,
        "r_RA": (hi10 - lo5) / max(1, hi10 + lo5),
        "r_morning": s[6:12].sum() / tot, "r_evening": s[18:24].sum() / tot,
        "r_night": s[0:6].sum() / tot, "r_hours": int((s > tot / 48).sum()),
    }


def load_daily():
    """일 단위 생체 지표를 하나로 합친다. 전부 「그날」 값이다."""
    hrv = pd.read_parquet(PQ / "hrv.parquet")
    hrv["date"] = pd.to_datetime(hrv.timestamp, errors="coerce").dt.normalize()
    hv = hrv.groupby(["pid", "date"], as_index=False).agg(
        rmssd=("rmssd", "mean"), lf=("low_frequency", "mean"),
        hf=("high_frequency", "mean"))
    hv["lfhf"] = hv.lf / hv.hf.replace(0, np.nan)
    hv = hv.drop(columns=["lf", "hf"])

    st = pd.read_parquet(PQ / "stress.parquet")
    st["date"] = pd.to_datetime(st.DATE, errors="coerce").dt.normalize()
    st = st[["pid", "date", "STRESS_SCORE", "SLEEP_POINTS",
             "RESPONSIVENESS_POINTS", "EXERTION_POINTS"]]

    rs = pd.read_parquet(PQ / "resp.parquet")
    rs["date"] = pd.to_datetime(rs.timestamp, errors="coerce").dt.normalize()
    rs = rs.groupby(["pid", "date"], as_index=False).agg(
        br=("full_sleep_breathing_rate", "mean"),
        br_sd=("full_sleep_standard_deviation", "mean"))

    sl = pd.read_parquet(PQ / "sleep.parquet")
    sl["date"] = pd.to_datetime(sl.dateOfSleep, errors="coerce").dt.normalize()
    sl = sl.groupby(["pid", "date"], as_index=False).agg(
        asleep=("minutesAsleep", "sum"), awake=("minutesAwake", "sum"),
        tofall=("minutesToFallAsleep", "mean"), eff=("efficiency", "mean"))

    tp = pd.read_parquet(PQ / "temp.parquet")
    tp["date"] = pd.to_datetime(tp.recorded_time, errors="coerce").dt.normalize()
    tp = tp.groupby(["pid", "date"], as_index=False).agg(temp=("temperature", "mean"))

    d = hv.merge(st, on=["pid", "date"], how="outer") \
          .merge(rs, on=["pid", "date"], how="outer") \
          .merge(sl, on=["pid", "date"], how="outer") \
          .merge(tp, on=["pid", "date"], how="outer")
    cols = [c for c in d.columns if c not in ("pid", "date")]
    #  ⚠ outer merge 는 같은 (참가자,날짜)를 여러 행으로 남긴다
    d = d.groupby(["pid", "date"], as_index=False)[cols].mean().sort_values(["pid", "date"])
    return d, cols


def build(lab):
    #  ── 시간 단위 CSV: 걸음·심박·칼로리 + 리듬 ──
    h = pd.read_csv(HCSV, usecols=["id", "date", "hour", "steps", "bpm", "calories"])
    h = h.rename(columns={"id": "pid"})
    h["pid"] = h.pid.astype(str)
    h["date"] = pd.to_datetime(h["date"])
    sens = h.groupby(["pid", "date", "hour"], as_index=False)[
        ["steps", "bpm", "calories"]].mean().sort_values(["pid", "date", "hour"])
    sens_by = {p: g for p, g in sens.groupby("pid")}

    #  ── 원본: 라벨 앞 6시간의 초 단위 심박 ──
    hrn = pd.read_parquet(PQ / "hr_near.parquet")
    hrn["ts"] = pd.to_datetime(hrn.ts)
    hrn = hrn.sort_values(["pid", "ts"])
    hr_by = {p: (g.ts.to_numpy("datetime64[ns]").astype("int64"),
                 g.bpm.to_numpy(dtype=float)) for p, g in hrn.groupby("pid")}

    daily, DCOLS = load_daily()
    daily_by = {p: g.set_index("date") for p, g in daily.groupby("pid")}

    rows = []
    for r in lab.itertuples():
        g = sens_by.get(r.pid)
        if g is None:
            continue
        day = pd.Timestamp(r.ts).normalize()
        today = g[(g.date == day) & (g.hour <= r.ts.hour)]
        if len(today) < 3:
            continue
        hist = g[(g.date < day) & (g.date >= day - pd.Timedelta(days=BASE_DAYS))]
        if len(hist) < 24:
            continue

        f = {}
        # ── 같은 시간대 기준선 (시도 13) ──
        for c in ["steps", "bpm", "calories"]:
            cur = today[c].dropna()
            if len(cur) < 2:
                continue
            recent = today[today.hour > r.ts.hour - 6][c].dropna()
            f[c + "_today_sum"] = cur.sum()
            f[c + "_today_mean"] = cur.mean()
            f[c + "_recent"] = recent.mean() if len(recent) else 0
            f[c + "_last"] = cur.iloc[-1]
            same = hist[(hist.hour >= r.ts.hour - 1) & (hist.hour <= r.ts.hour + 1)][c].dropna()
            if len(same) >= 5 and same.std() > 0:
                f[c + "_z_samehour"] = (cur.iloc[-1] - same.median()) / same.std()
                f[c + "_base_samehour"] = same.median()
            acc = hist[hist.hour <= r.ts.hour].groupby("date")[c].sum()
            if len(acc) >= 5 and acc.std() > 0:
                f[c + "_acc_z"] = (cur.sum() - acc.median()) / acc.std()

        # ── 활동 리듬 (시도 12) ──
        rt = rhythm(today)
        f.update(rt)
        if rt:
            hr = [x for x in (rhythm(gg) for _, gg in hist.groupby("date")) if x]
            for k in rt:
                v = [x[k] for x in hr if k in x]
                if len(v) >= 3 and np.std(v) > 0:
                    f[k + "_z"] = (rt[k] - np.median(v)) / np.std(v)
                    f[k + "_base"] = np.mean(v)

        # ── 단기 심박 변동 (원본) ──
        hb = hr_by.get(r.pid)
        if hb is not None:
            tsv, bpm = hb
            end = np.datetime64(r.ts).astype("datetime64[ns]").astype("int64")
            hi = np.searchsorted(tsv, end, side="right")
            for w in (15, 30, 60, 180):
                lo = np.searchsorted(tsv, end - w * MIN, side="left")
                v = bpm[lo:hi]
                if len(v) < 5:
                    continue
                f[f"hr{w}_mean"] = v.mean()
                f[f"hr{w}_std"] = v.std()                    # HRV 대용
                f[f"hr{w}_dstd"] = np.abs(np.diff(v)).mean()  # 연속차 — RMSSD 와 같은 발상
                if w >= 60:
                    f[f"hr{w}_slope"] = np.polyfit(np.arange(len(v)), v, 1)[0]
            #  같은 시각의 개인 기준선
            prior = []
            for dd in range(1, BASE_DAYS + 1):
                e2 = end - dd * DAY
                a = np.searchsorted(tsv, e2 - 30 * MIN, side="left")
                b = np.searchsorted(tsv, e2, side="right")
                if b - a >= 5:
                    prior.append((bpm[a:b].mean(), bpm[a:b].std()))
            if len(prior) >= 3 and "hr30_mean" in f:
                pm = np.array([p[0] for p in prior])
                ps = np.array([p[1] for p in prior])
                if pm.std() > 0:
                    f["hr30_mean_z"] = (f["hr30_mean"] - np.median(pm)) / pm.std()
                if ps.std() > 0:
                    f["hr30_std_z"] = (f["hr30_std"] - np.median(ps)) / ps.std()

        # ── 일 단위 생체 지표: ⚠ 전날 것만 ──
        dg = daily_by.get(r.pid)
        if dg is not None:
            yday = day - pd.Timedelta(days=1)
            dh = dg[(dg.index < day) & (dg.index >= day - pd.Timedelta(days=BASE_DAYS))]
            row = dg.loc[yday] if yday in dg.index else None
            for c in DCOLS:
                if row is None or pd.isna(row[c]):
                    continue
                cur = float(row[c])
                f[c] = cur
                hv = dh[c].dropna().to_numpy(dtype=float) if len(dh) else np.array([])
                if len(hv) >= 5 and hv.std() > 0:
                    f[c + "_z"] = (cur - np.median(hv)) / hv.std()
                    f[c + "_base"] = float(np.median(hv))

        if len(f) < 15:
            continue
        f["hour"] = r.ts.hour
        f["minute_of_day"] = r.ts.hour * 60 + r.ts.minute
        f["_y"] = int(r.y)
        f["_pid"] = r.pid
        rows.append(f)

    df = pd.DataFrame(rows)
    #  절반 넘게 비어 있는 피처는 뺀다 — 0 으로 메우면 「없음」이 신호가 된다
    keep = [c for c in df.columns if c.startswith("_") or df[c].notna().mean() >= 0.5]
    return df[keep].fillna(0)


def main():
    lab, title = load_labels()
    print(f"라벨 {len(lab)}건 · 참가자 {lab.pid.nunique()} · 양성률 {lab.y.mean():.1%}")
    print("피처 만드는 중...")
    df = build(lab)
    y = df["_y"].to_numpy()
    X = df.drop(columns=["_y", "_pid"])
    pid = df["_pid"].to_numpy()
    g0 = pd.factorize(pid)[0]
    print(f"표본 {len(df)} · 참가자 {df._pid.nunique()} · 피처 {X.shape[1]} "
          f"· 양성률 {y.mean():.1%}\n")

    def oof(kind, labels=None):
        yy = y if labels is None else labels
        o = np.full(len(df), np.nan)
        for tr, te in GroupKFold(5).split(X, yy, groups=g0):
            if len(np.unique(yy[tr])) < 2:
                continue
            m = (make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000, C=0.1))
                 if kind == "lr" else
                 lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=31,
                                    min_child_samples=20, subsample=0.8,
                                    colsample_bytree=0.8, random_state=42, verbose=-1))
            m.fit(X.iloc[tr], yy[tr])
            o[te] = m.predict_proba(X.iloc[te])[:, 1]
        return o

    def rank(o):
        return pd.Series(o).rank(pct=True).to_numpy()

    def boot(o, n=2000):
        ok = ~np.isnan(o)
        rng = np.random.default_rng(42)
        pids = np.unique(pid)
        out = []
        for _ in range(n):
            smp = rng.choice(pids, len(pids), replace=True)
            idx = np.concatenate([np.where(pid == p)[0] for p in smp])
            idx = idx[ok[idx]]
            if len(np.unique(y[idx])) < 2:
                continue
            out.append(roc_auc_score(y[idx], o[idx]))
        a = np.array(out)
        return roc_auc_score(y[ok], o[ok]), *np.percentile(a, [2.5, 97.5])

    o_lr, o_gb = oof("lr"), oof("gb")
    o_en = (rank(o_lr) + rank(o_gb)) / 2

    print(f"=== 전부 합침 · {title} ===\n")
    print(f"  {'구성':22s} {'AUC':>7}  {'참가자 부트스트랩 95%':>22}")
    print(f"  {'-' * 22} {'-' * 7}  {'-' * 22}")
    best = None
    for name, o in [("LogisticRegression", o_lr), ("LightGBM", o_gb),
                    ("앙상블(순위 평균)", o_en)]:
        auc, lo, hi = boot(o)
        print(f"  {name:22s} {auc:7.3f}  {lo:.3f} ~ {hi:.3f}" + (" ✅" if lo > 0.5 else ""))
        if best is None or auc > best[1]:
            best = (name, auc)

    sh = []
    for seed in range(10):
        rng = np.random.default_rng(seed)
        ys = y.copy()
        for p in np.unique(pid):
            mk = pid == p
            v = ys[mk]
            rng.shuffle(v)
            ys[mk] = v
        e = (rank(oof("lr", ys)) + rank(oof("gb", ys))) / 2
        k = ~np.isnan(e)
        sh.append(roc_auc_score(ys[k], e[k]))
    sh = np.array(sh)
    ke = ~np.isnan(o_en)
    real = roc_auc_score(y[ke], o_en[ke])
    print(f"\n  셔플 대조(앙상블): 실제 {real:.3f} vs 셔플 {sh.mean():.3f} "
          f"(최대 {sh.max():.3f})")
    print("  → 신호 있음" if real > sh.max() else "  → ⚠ 셔플과 구분 안 됨")

    m = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=31,
                           min_child_samples=20, random_state=42, verbose=-1).fit(X, y)
    imp = pd.Series(m.feature_importances_, index=X.columns).sort_values(ascending=False)
    print("\n  상위 피처:")
    for k, v in imp.head(10).items():
        print(f"    {v:5d}  {k}")
    print(f"\n  최고: {best[0]} ({best[1]:.3f})")


if __name__ == "__main__":
    main()
