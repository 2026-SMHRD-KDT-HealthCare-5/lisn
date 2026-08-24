# -*- coding: utf-8 -*-
r"""지금까지 얻은 것을 전부 합쳐 최대치를 낸다 — 2026.08.24

    .venv/Scripts/python.exe ai/train/eval_best.py [감정]

## 무엇을 합치나

| 출처 | 얻은 것 |
|---|---|
| 시도 12 | 시간 단위 **리듬 피처**(활동 무게중심·집중도·M10/L5) |
| 시도 13 | **시각 단위 표본**(2290 → 5029) · **같은 시간대 기준선** |
| 시도 14 | **로지스틱 회귀**가 트리보다 낫다(표본이 작을 때) |

여기에 **앙상블**(선형 + 트리 평균)까지 얹어 비교한다.

⚠ **튜닝은 여전히 안 한다.** 표본 61명에서 하이퍼파라미터를 고르면 그
  61명에 맞춰진다. 지금 재는 것은 「가진 재료를 다 쓰면 어디까지인가」다.
"""
import sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from pathlib import Path
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb

H = Path("ai/data_raw/lifesnaps/rais_anonymized/csv_rais_anonymized/hourly_fitbit_sema_df_unprocessed.csv")
TARGET = sys.argv[1] if len(sys.argv) > 1 else "HAPPY"
BASE_DAYS = 14

print("읽는 중...")
d = pd.read_csv(H, usecols=["id","date","hour","steps","bpm","calories",TARGET]).rename(columns={"id":"pid"})
d["date"] = pd.to_datetime(d["date"])
sens = d.groupby(["pid","date","hour"], as_index=False)[["steps","bpm","calories"]].mean().sort_values(["pid","date","hour"])
lab = d[d[TARGET].notna()].groupby(["pid","date","hour"], as_index=False)[TARGET].first()
by_pid = {p: g for p, g in sens.groupby("pid")}


def rhythm(day_df):
    """하루치 시간별 걸음에서 리듬 지표 (시도 12)."""
    s = day_df.groupby("hour")["steps"].mean().reindex(range(24)).fillna(0).to_numpy()
    tot = s.sum()
    if tot < 50:
        return {}
    h = np.arange(24); ang = 2*np.pi*h/24
    cx, cy = (s*np.cos(ang)).sum()/tot, (s*np.sin(ang)).sum()/tot
    hi10, lo5 = np.sort(s)[-10:].mean(), np.sort(s)[:5].mean()
    return {
        "r_center": (np.arctan2(cy, cx) % (2*np.pi)) * 24/(2*np.pi),
        "r_conc": np.hypot(cx, cy),
        "r_M10": hi10, "r_L5": lo5,
        "r_RA": (hi10-lo5)/max(1, hi10+lo5),
        "r_morning": s[6:12].sum()/tot, "r_evening": s[18:24].sum()/tot,
        "r_night": s[0:6].sum()/tot, "r_hours": (s > tot/48).sum(),
    }


rows = []
for _, s in lab.iterrows():
    g = by_pid.get(s.pid)
    if g is None: continue
    today = g[(g.date == s.date) & (g.hour <= s.hour)]
    if len(today) < 3: continue
    hist = g[(g.date < s.date) & (g.date >= s.date - pd.Timedelta(days=BASE_DAYS))]
    if len(hist) < 24: continue

    f = {}
    # ── 시도 13: 시각 기준 피처 + 같은 시간대 기준선 ──
    for c in ["steps","bpm","calories"]:
        cur = today[c].dropna()
        if len(cur) < 2: continue
        recent = today[today.hour > s.hour - 6][c].dropna()
        f[c+"_today_sum"] = cur.sum(); f[c+"_today_mean"] = cur.mean()
        f[c+"_recent"] = recent.mean() if len(recent) else 0
        f[c+"_last"] = cur.iloc[-1]
        same = hist[(hist.hour >= s.hour-1) & (hist.hour <= s.hour+1)][c].dropna()
        if len(same) >= 5 and same.std() > 0:
            f[c+"_z_samehour"] = (cur.iloc[-1]-same.median())/same.std()
            f[c+"_base_samehour"] = same.median()
        acc = hist[hist.hour <= s.hour].groupby("date")[c].sum()
        if len(acc) >= 5 and acc.std() > 0:
            f[c+"_acc_z"] = (cur.sum()-acc.median())/acc.std()

    # ── 시도 12: 리듬 피처 (오늘 + 기준선 대비) ──
    rt = rhythm(today)
    f.update(rt)
    if rt:
        hist_r = [rhythm(gg) for _, gg in hist.groupby("date")]
        hist_r = [x for x in hist_r if x]
        for k in rt:
            vals = [x[k] for x in hist_r if k in x]
            if len(vals) >= 3 and np.std(vals) > 0:
                f[k+"_z"] = (rt[k]-np.median(vals))/np.std(vals)
                f[k+"_base"] = np.mean(vals)

    if len(f) < 12: continue
    f["hour"] = s.hour
    f["_y"] = int(s[TARGET]); f["_pid"] = s.pid
    rows.append(f)

df = pd.DataFrame(rows).fillna(0)
y = df["_y"].to_numpy(); X = df.drop(columns=["_y","_pid"]); pid = df["_pid"].to_numpy()
g0 = pd.factorize(pid)[0]
print(f"표본 {len(df)} · 참가자 {df._pid.nunique()} · 피처 {X.shape[1]} · 양성률 {y.mean():.1%}\n")


def oof(kind):
    o = np.full(len(df), np.nan)
    for tr, te in GroupKFold(5).split(X, y, groups=g0):
        if len(np.unique(y[tr])) < 2: continue
        if kind == "lr":
            m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000, C=0.1))
        else:
            m = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.05, num_leaves=31,
                                   min_child_samples=20, subsample=0.8, colsample_bytree=0.8,
                                   random_state=42, verbose=-1)
        m.fit(X.iloc[tr], y[tr]); o[te] = m.predict_proba(X.iloc[te])[:,1]
    return o


def boot(o, n=2000):
    ok = ~np.isnan(o)
    rng = np.random.default_rng(42); pids = np.unique(pid); out = []
    for _ in range(n):
        smp = rng.choice(pids, len(pids), replace=True)
        idx = np.concatenate([np.where(pid == p)[0] for p in smp])
        idx = idx[ok[idx]]
        if len(np.unique(y[idx])) < 2: continue
        out.append(roc_auc_score(y[idx], o[idx]))
    a = np.array(out); return roc_auc_score(y[ok], o[ok]), a.mean(), *np.percentile(a, [2.5, 97.5])


o_lr, o_gb = oof("lr"), oof("gb")
#  순위 평균 앙상블 — 두 모델의 척도가 달라 확률을 그대로 더하면 한쪽이 먹는다
r_lr = pd.Series(o_lr).rank(pct=True).to_numpy()
r_gb = pd.Series(o_gb).rank(pct=True).to_numpy()
o_ens = (r_lr + r_gb) / 2

print(f"=== 전부 합친 결과 · {TARGET} ===\n")
print(f"  {'구성':22s} {'AUC':>7}  {'참가자 부트스트랩 95%':>22}")
print(f"  {'-'*22} {'-'*7}  {'-'*22}")
best = None
for name, o in [("LogisticRegression", o_lr), ("LightGBM", o_gb), ("앙상블(순위 평균)", o_ens)]:
    auc, m, lo, hi = boot(o)
    sig = " ✅" if lo > 0.5 else ""
    print(f"  {name:22s} {auc:7.3f}  {lo:.3f} ~ {hi:.3f}{sig}")
    if best is None or auc > best[1]: best = (name, auc)

print(f"\n  최고: {best[0]} ({best[1]:.3f})")
print(f"  (시도 13 시각 단위 단독: HAPPY 0.581 · TENSE 0.582 · TIRED 0.590)")
