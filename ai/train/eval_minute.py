# -*- coding: utf-8 -*-
r"""분 단위 원본으로 다시 잰다 — 2026.08.25

    .venv/Scripts/python.exe ai/train/eval_minute.py [모드]
      모드: narrow(기본) | wide | happy | tense

`extract_bson.py` 를 먼저 돌려 `ai/data_raw/lifesnaps/parquet/` 을 만드세요.

## 무엇이 새로 들어가나

시간 단위 CSV 에는 걸음·심박·칼로리 **세 가지뿐**이었습니다. 원본에서
꺼낸 것을 라벨 시각 기준으로 붙입니다.

| 피처군 | 출처 | 왜 |
|---|---|---|
| **단기 심박 변동** | `hr_near`(초 단위) | 라벨 직전 15·30·60분의 표준편차·연속차 평균. **HRV 대용** |
| **심박 추세** | 〃 | 직전 60분 기울기 — 오르는 중인가 |
| **RMSSD** | `hrv`(5분 단위) | ⭐ 실제 HRV. 불안의 표준 지표 |
| 호흡률 | `resp` | 수면 중 호흡률·변동 |
| 스트레스 점수 | `stress` | Fitbit 자체 산출 |
| 손목 체온 | `temp` | 기준선 대비 편차 |
| 수면 | `sleep` | 전날 밤 수면 효율·각성 |

각 지표에 **개인 기준선 대비 z값**을 함께 넣습니다 — 우리 서비스 방식.

## ⚠ 미래를 보지 않습니다

라벨이 10:26 에 붙었으면 **10:26 이전 값만** 씁니다. 일 단위 지표
(RMSSD 요약·스트레스 점수·수면)는 **전날 것**을 씁니다 — 당일 값은
하루가 끝나야 확정되므로 예측 시점에 존재하지 않습니다.
"""
import sys
import warnings
from pathlib import Path

import bson
import lightgbm as lgb
import numpy as np
import pandas as pd
import zipfile
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

PQ = Path("ai/data_raw/lifesnaps/parquet")
ZIP = Path("ai/data_raw/lifesnaps/rais_anonymized.zip")
MODE = sys.argv[1] if len(sys.argv) > 1 else "narrow"
BASE_DAYS = 14

NEG_WIDE = {"TIRED", "TENSE/ANXIOUS", "SAD", "ANGER", "FEAR", "SADNESS"}
NEG_NARROW = {"TENSE/ANXIOUS", "SAD", "ANGER", "FEAR", "SADNESS"}
POS = {"HAPPY", "RESTED/RELAXED", "ALERT", "JOY"}


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


def zbase(cur, hist):
    """개인 기준선 대비 z. 표본이 모자라거나 편차가 0 이면 None."""
    h = np.asarray([v for v in hist if pd.notna(v)], dtype=float)
    if len(h) < 5 or pd.isna(cur):
        return None, None
    sd = h.std()
    return ((cur - np.median(h)) / sd if sd > 0 else 0.0), float(np.median(h))


def main():
    lab, title = load_labels()
    print(f"라벨 {len(lab)}건 · 참가자 {lab.pid.nunique()} · 양성률 {lab.y.mean():.1%}")

    print("parquet 읽는 중...")
    hrn = pd.read_parquet(PQ / "hr_near.parquet")
    hrn["ts"] = pd.to_datetime(hrn.ts)
    hrn = hrn.sort_values(["pid", "ts"])
    hr_by = {p: (g.ts.to_numpy("datetime64[ns]").astype("int64"),
                 g.bpm.to_numpy(dtype=float)) for p, g in hrn.groupby("pid")}

    hrv = pd.read_parquet(PQ / "hrv.parquet")
    hrv["ts"] = pd.to_datetime(hrv.timestamp, errors="coerce")
    hrv["date"] = hrv.ts.dt.normalize()
    hrv_d = hrv.groupby(["pid", "date"], as_index=False).agg(
        rmssd=("rmssd", "mean"), lf=("low_frequency", "mean"),
        hf=("high_frequency", "mean"))
    hrv_d["lfhf"] = hrv_d.lf / hrv_d.hf.replace(0, np.nan)

    stress = pd.read_parquet(PQ / "stress.parquet")
    stress["date"] = pd.to_datetime(stress.DATE, errors="coerce").dt.normalize()
    stress = stress[["pid", "date", "STRESS_SCORE", "SLEEP_POINTS",
                     "RESPONSIVENESS_POINTS", "EXERTION_POINTS"]]

    resp = pd.read_parquet(PQ / "resp.parquet")
    resp["date"] = pd.to_datetime(resp.timestamp, errors="coerce").dt.normalize()
    resp = resp.groupby(["pid", "date"], as_index=False).agg(
        br=("full_sleep_breathing_rate", "mean"),
        br_sd=("full_sleep_standard_deviation", "mean"))

    slp = pd.read_parquet(PQ / "sleep.parquet")
    slp["date"] = pd.to_datetime(slp.dateOfSleep, errors="coerce").dt.normalize()
    slp = slp.groupby(["pid", "date"], as_index=False).agg(
        asleep=("minutesAsleep", "sum"), awake=("minutesAwake", "sum"),
        tofall=("minutesToFallAsleep", "mean"), eff=("efficiency", "mean"))

    tmp = pd.read_parquet(PQ / "temp.parquet")
    tmp["date"] = pd.to_datetime(tmp.recorded_time, errors="coerce").dt.normalize()
    tmp = tmp.groupby(["pid", "date"], as_index=False).agg(temp=("temperature", "mean"))

    #  일 단위 지표를 하나로 합친다. 전부 「그날」 값이라 쓸 때 하루 당긴다.
    daily = hrv_d.merge(stress, on=["pid", "date"], how="outer") \
                 .merge(resp, on=["pid", "date"], how="outer") \
                 .merge(slp, on=["pid", "date"], how="outer") \
                 .merge(tmp, on=["pid", "date"], how="outer")
    DAILY_COLS = [c for c in daily.columns if c not in ("pid", "date", "lf", "hf")]
    #  ⚠ outer merge 는 같은 (참가자,날짜)를 여러 행으로 남길 수 있다.
    #    그대로 두면 dg.loc[yday] 가 Series 가 아니라 DataFrame 을 준다.
    daily = daily.groupby(["pid", "date"], as_index=False)[DAILY_COLS].mean()
    daily = daily.sort_values(["pid", "date"])
    daily_by = {p: g.set_index("date") for p, g in daily.groupby("pid")}
    print(f"  일 단위 지표 {len(daily)}행 · 컬럼 {len(DAILY_COLS)}\n")

    WINDOWS = [15, 30, 60, 180]
    rows = []
    for r in lab.itertuples():
        f = {}
        # ── 단기 심박: 라벨 시각 이전만 ──
        hb = hr_by.get(r.pid)
        if hb is None:
            continue
        tsv, bpm = hb
        end = np.datetime64(r.ts).astype("datetime64[ns]").astype("int64")
        hi = np.searchsorted(tsv, end, side="right")
        for w in WINDOWS:
            lo = np.searchsorted(tsv, end - w * 60_000_000_000, side="left")
            v = bpm[lo:hi]
            if len(v) < 5:
                continue
            f[f"hr{w}_mean"] = v.mean()
            f[f"hr{w}_std"] = v.std()          # ⭐ HRV 대용
            f[f"hr{w}_rng"] = v.max() - v.min()
            f[f"hr{w}_dstd"] = np.abs(np.diff(v)).mean()   # 연속차 — RMSSD 와 같은 발상
            f[f"hr{w}_n"] = len(v)
            if w >= 60:                        # 추세는 긴 창에서만 의미가 있다
                x = np.arange(len(v))
                f[f"hr{w}_slope"] = np.polyfit(x, v, 1)[0]
        if "hr30_std" not in f:
            continue

        # ── 같은 시각의 개인 기준선(직전 14일 같은 시간대) ──
        prior = []
        for d in range(1, BASE_DAYS + 1):
            e2 = end - d * 86_400_000_000_000
            a = np.searchsorted(tsv, e2 - 30 * 60_000_000_000, side="left")
            b = np.searchsorted(tsv, e2, side="right")
            if b - a >= 5:
                prior.append((bpm[a:b].mean(), bpm[a:b].std()))
        if len(prior) >= 3:
            pm = np.array([p[0] for p in prior]); ps = np.array([p[1] for p in prior])
            if pm.std() > 0:
                f["hr30_mean_z"] = (f["hr30_mean"] - np.median(pm)) / pm.std()
            if ps.std() > 0:
                f["hr30_std_z"] = (f["hr30_std"] - np.median(ps)) / ps.std()
            f["hr30_mean_base"] = float(np.median(pm))
            f["hr30_std_base"] = float(np.median(ps))

        # ── 일 단위 지표: ⚠ 전날 것만 (당일 값은 예측 시점에 없다) ──
        dg = daily_by.get(r.pid)
        if dg is not None:
            day = pd.Timestamp(r.ts).normalize()
            yday = day - pd.Timedelta(days=1)
            hist = dg[(dg.index < day) & (dg.index >= day - pd.Timedelta(days=BASE_DAYS))]
            row = dg.loc[yday] if yday in dg.index else None
            for c in DAILY_COLS:
                cur = None
                if row is not None:
                    v = row[c]
                    cur = float(v) if pd.notna(v) else None
                if cur is not None:
                    f[c] = cur
                    z, base = zbase(cur, hist[c].tolist() if len(hist) else [])
                    if z is not None:
                        f[c + "_z"] = z
                        f[c + "_base"] = base

        f["hour"] = r.ts.hour
        f["minute_of_day"] = r.ts.hour * 60 + r.ts.minute
        f["_y"] = int(r.y)
        f["_pid"] = r.pid
        rows.append(f)

    df = pd.DataFrame(rows)
    #  절반 넘게 비어 있는 피처는 뺀다 — 0 으로 메우면 없는 것이 신호가 된다
    keep = [c for c in df.columns if c.startswith("_") or df[c].notna().mean() >= 0.5]
    df = df[keep].fillna(0)
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

    print(f"=== 분 단위 원본 · {title} ===\n")
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
