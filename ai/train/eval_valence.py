# -*- coding: utf-8 -*-
r"""정서가(valence) 이진 분류 — 원본 BSON 라벨로 다시 짠다. 2026.08.25

    .venv/Scripts/python.exe ai/train/eval_valence.py [모드]
      모드: wide(기본) | narrow | happy

## 왜 문제 정의를 바꾸나

CSV 의 `HAPPY`·`SAD`·`TIRED`·`TENSE/ANXIOUS` 네 컬럼은 **원본의 단일
`MOOD` 필드에서 파생**된 것이었습니다. 원본(`sema.bson`)을 열어 확인했습니다.

    MOOD 분포   RESTED/RELAXED 1179 · TIRED 1126 · NEUTRAL 822 · HAPPY 789
                TENSE/ANXIOUS 620 · ALERT 345 · SAD 147 · (그 외 8)

**즉 다중분류 한 문제**를 네 개의 이진 문제로 쪼개 풀고 있었습니다. 그래서
`SAD` 양성률이 3.0% 까지 떨어졌고(147/4500), 어떤 모델도 임계점을 못
찾았습니다.

**정서가로 묶으면 균형이 맞습니다.**

    wide     부정(TIRED·TENSE·SAD·ANGER·FEAR·SADNESS) vs 긍정(HAPPY·RESTED·ALERT·JOY)
    narrow   TIRED 를 뺀 좁은 정의 — 피로는 정서라기보다 상태에 가깝다
    happy    비교용. 시도 15 와 같은 대상

⚠ **NEUTRAL 은 뺍니다.** 「좋지도 나쁘지도 않다」를 어느 쪽에 넣어도
  라벨이 흐려집니다.

## 원본을 쓰는 두 번째 이유 — 시각이 분 단위입니다

CSV 는 시각을 **시간으로 뭉갰습니다**. 원본 `COMPLETED_TS` 는 분까지
있습니다. 지금은 센서가 시간 단위라 자르는 정밀도까지는 못 올리지만,
**하루 중 몇 분인지**(`minute_of_day`)는 피처로 넣을 수 있습니다.
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

ZIP = Path("ai/data_raw/lifesnaps/rais_anonymized.zip")
H = Path("ai/data_raw/lifesnaps/rais_anonymized/csv_rais_anonymized/"
         "hourly_fitbit_sema_df_unprocessed.csv")
MODE = sys.argv[1] if len(sys.argv) > 1 else "wide"
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
        title = "HAPPY (비교용)"
    else:
        neg = NEG_WIDE if MODE == "wide" else NEG_NARROW
        lab = lab[lab.mood.isin(neg | POS)].copy()
        lab["y"] = lab.mood.isin(neg).astype(int)
        title = f"부정 정서 ({MODE})"

    lab["date"] = lab.ts.dt.normalize()
    lab["hour"] = lab.ts.dt.hour
    lab["minute"] = lab.ts.dt.minute
    #  같은 참가자·같은 시각에 두 건이면 앞의 것만 — 중복 응답이다
    lab = lab.drop_duplicates(subset=["pid", "ts"]).sort_values(["pid", "ts"])
    return lab, title


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


def build(lab):
    d = pd.read_csv(H, usecols=["id", "date", "hour", "steps", "bpm", "calories"])
    d = d.rename(columns={"id": "pid"})
    d["pid"] = d.pid.astype(str)
    d["date"] = pd.to_datetime(d["date"])
    sens = d.groupby(["pid", "date", "hour"], as_index=False)[
        ["steps", "bpm", "calories"]].mean().sort_values(["pid", "date", "hour"])
    by_pid = {p: g for p, g in sens.groupby("pid")}

    rows = []
    for _, s in lab.iterrows():
        g = by_pid.get(s.pid)
        if g is None:
            continue
        today = g[(g.date == s.date) & (g.hour <= s.hour)]
        if len(today) < 3:
            continue
        hist = g[(g.date < s.date) & (g.date >= s.date - pd.Timedelta(days=BASE_DAYS))]
        if len(hist) < 24:
            continue

        f = {}
        for c in ["steps", "bpm", "calories"]:
            cur = today[c].dropna()
            if len(cur) < 2:
                continue
            recent = today[today.hour > s.hour - 6][c].dropna()
            f[c + "_today_sum"] = cur.sum()
            f[c + "_today_mean"] = cur.mean()
            f[c + "_recent"] = recent.mean() if len(recent) else 0
            f[c + "_last"] = cur.iloc[-1]
            #  ⚠ 같은 시간대끼리 비교한다 — 저녁 걸음을 하루 평균과 견주면
            #    「저녁엔 원래 많이 걷는다」가 이탈로 잡힌다
            same = hist[(hist.hour >= s.hour - 1) & (hist.hour <= s.hour + 1)][c].dropna()
            if len(same) >= 5 and same.std() > 0:
                f[c + "_z_samehour"] = (cur.iloc[-1] - same.median()) / same.std()
                f[c + "_base_samehour"] = same.median()
            acc = hist[hist.hour <= s.hour].groupby("date")[c].sum()
            if len(acc) >= 5 and acc.std() > 0:
                f[c + "_acc_z"] = (cur.sum() - acc.median()) / acc.std()

        rt = rhythm(today)
        f.update(rt)
        if rt:
            hr = [x for x in (rhythm(gg) for _, gg in hist.groupby("date")) if x]
            for k in rt:
                v = [x[k] for x in hr if k in x]
                if len(v) >= 3 and np.std(v) > 0:
                    f[k + "_z"] = (rt[k] - np.median(v)) / np.std(v)
                    f[k + "_base"] = np.mean(v)

        if len(f) < 12:
            continue
        f["hour"] = s.hour
        f["minute_of_day"] = s.hour * 60 + s.minute   # 원본에만 있는 정보
        f["_y"] = int(s.y)
        f["_pid"] = s.pid
        rows.append(f)
    return pd.DataFrame(rows).fillna(0)


def main():
    print("SEMA 원본 라벨 읽는 중...")
    lab, title = load_labels()
    print(f"라벨 {len(lab)}건 · 참가자 {lab.pid.nunique()} · 양성률 {lab.y.mean():.1%}\n")

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
                 lgb.LGBMClassifier(n_estimators=200, learning_rate=0.05, num_leaves=31,
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
    #  ⚠ 순위 평균 — 두 모델의 확률 척도가 달라 그대로 더하면 한쪽이 먹는다
    o_en = (rank(o_lr) + rank(o_gb)) / 2

    print(f"=== {title} ===\n")
    print(f"  {'구성':22s} {'AUC':>7}  {'참가자 부트스트랩 95%':>22}")
    print(f"  {'-' * 22} {'-' * 7}  {'-' * 22}")
    best = None
    for name, o in [("LogisticRegression", o_lr), ("LightGBM", o_gb),
                    ("앙상블(순위 평균)", o_en)]:
        auc, lo, hi = boot(o)
        print(f"  {name:22s} {auc:7.3f}  {lo:.3f} ~ {hi:.3f}" + (" ✅" if lo > 0.5 else ""))
        if best is None or auc > best[1]:
            best = (name, auc)

    #  셔플 대조 — 참가자 안에서 라벨을 섞어 시각-라벨 관계만 끊는다
    sh = []
    for seed in range(10):
        r = np.random.default_rng(seed)
        ys = y.copy()
        for p in np.unique(pid):
            mk = pid == p
            v = ys[mk]
            r.shuffle(v)
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
    print(f"\n  최고: {best[0]} ({best[1]:.3f})")


if __name__ == "__main__":
    main()
