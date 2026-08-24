# -*- coding: utf-8 -*-
r"""표본을 늘린다 — 하루 1개가 아니라 「라벨이 붙은 시각」마다 1개.

    .venv/Scripts/python.exe ai/train/eval_momentary.py [감정]

## 무엇이 달라지나

지금까지는 하루를 한 표본으로 봤습니다(2290개). 그런데 SEMA 는 **하루에
1~4회, 서로 다른 시각에** 물었습니다. 오전 10시의 기분과 저녁 8시의
기분은 다른 관측입니다.

    하루 단위   2290 표본
    시각 단위   5029 표본   ← 2.2배

## 피처도 그 시각 기준으로 자릅니다

라벨이 10시에 붙었으면 **10시까지의** 데이터만 씁니다. 그 뒤를 쓰면
미래를 보고 과거를 맞히는 것이 됩니다.

    직전 6시간   그 시각 직전의 움직임
    당일 누적    자정부터 그 시각까지
    직전 14일    같은 시간대의 개인 기준선  ← 우리 서비스 방식

⚠ **같은 시간대끼리 비교합니다.** 저녁 8시 걸음을 하루 평균과 비교하면
  「저녁엔 원래 많이 걷는다」가 이탈로 잡힙니다. 직전 14일의 **같은
  시간대**와 견줘야 합니다.
"""
import sys, warnings
import numpy as np, pandas as pd, lightgbm as lgb
warnings.filterwarnings("ignore")
from pathlib import Path
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

H = Path("ai/data_raw/lifesnaps/rais_anonymized/csv_rais_anonymized/hourly_fitbit_sema_df_unprocessed.csv")
TARGET = sys.argv[1] if len(sys.argv) > 1 else "HAPPY"
BASE_DAYS = 14

print("읽는 중...")
d = pd.read_csv(H, usecols=["id","date","hour","steps","bpm","calories",TARGET])
d = d.rename(columns={"id":"pid"})
d["date"] = pd.to_datetime(d["date"])
#  같은 (참가자,날짜,시각)에 행이 여러 개다 — 먼저 하나로 모은다
sens = d.groupby(["pid","date","hour"], as_index=False)[["steps","bpm","calories"]].mean()

lab = d[d[TARGET].notna()].groupby(["pid","date","hour"], as_index=False)[TARGET].first()
print(f"라벨 {len(lab)}개 · 참가자 {lab.pid.nunique()}명\n")

#  빠른 조회를 위해 인덱싱
sens = sens.sort_values(["pid","date","hour"])
by_pid = {p: g for p, g in sens.groupby("pid")}

rows = []
for _, s in lab.iterrows():
    g = by_pid.get(s.pid)
    if g is None: continue
    # 라벨 시각까지만 — 그 뒤는 미래다
    today = g[(g.date == s.date) & (g.hour <= s.hour)]
    if len(today) < 3: continue
    hist = g[(g.date < s.date) & (g.date >= s.date - pd.Timedelta(days=BASE_DAYS))]
    if len(hist) < 24: continue

    f = {}
    for c in ["steps","bpm","calories"]:
        cur = today[c].dropna()
        if len(cur) < 2: continue
        recent = today[today.hour > s.hour - 6][c].dropna()   # 직전 6시간
        f[c+"_today_sum"]  = cur.sum()
        f[c+"_today_mean"] = cur.mean()
        f[c+"_recent"]     = recent.mean() if len(recent) else 0
        f[c+"_last"]       = cur.iloc[-1]
        # ⚠ 같은 시간대의 개인 기준선과 견준다
        same = hist[(hist.hour >= s.hour-1) & (hist.hour <= s.hour+1)][c].dropna()
        if len(same) >= 5 and same.std() > 0:
            f[c+"_z_samehour"] = (cur.iloc[-1] - same.median()) / same.std()
            f[c+"_base_samehour"] = same.median()
        # 당일 누적을 평소 같은 시각 누적과 견준다
        dayacc = hist[hist.hour <= s.hour].groupby("date")[c].sum()
        if len(dayacc) >= 5 and dayacc.std() > 0:
            f[c+"_acc_z"] = (cur.sum() - dayacc.median()) / dayacc.std()
    if len(f) < 8: continue
    f["hour"] = s.hour
    f["_y"] = int(s[TARGET]); f["_pid"] = s.pid
    rows.append(f)

df = pd.DataFrame(rows).fillna(0)
print(f"표본 {len(df)} · 참가자 {df._pid.nunique()} · 피처 {df.shape[1]-2} · 양성률 {df._y.mean():.1%}\n")

y = df["_y"].to_numpy(); X = df.drop(columns=["_y","_pid"]); pid = df["_pid"].to_numpy()
g0 = pd.factorize(pid)[0]

def oof_of(labels):
    o = np.full(len(df), np.nan)
    for tr, te in GroupKFold(5).split(X, labels, groups=g0):
        if len(np.unique(labels[tr])) < 2: continue
        m = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.05, num_leaves=31,
                               min_child_samples=20, subsample=0.8, colsample_bytree=0.8,
                               random_state=42, verbose=-1)
        m.fit(X.iloc[tr], labels[tr]); o[te] = m.predict_proba(X.iloc[te])[:,1]
    return o

oof = oof_of(y)
ok = ~np.isnan(oof)
rng = np.random.default_rng(42); pids = np.unique(pid); aucs = []
for _ in range(2000):
    smp = rng.choice(pids, len(pids), replace=True)
    idx = np.concatenate([np.where(pid == p)[0] for p in smp])
    idx = idx[ok[idx]]
    if len(np.unique(y[idx])) < 2: continue
    aucs.append(roc_auc_score(y[idx], oof[idx]))
a = np.array(aucs); lo, hi = np.percentile(a, [2.5, 97.5])

print(f"=== 시각 단위 · {TARGET} ===")
print(f"  AUC {roc_auc_score(y[ok], oof[ok]):.3f}")
print(f"  참가자 부트스트랩 {a.mean():.3f}  95% {lo:.3f}~{hi:.3f}  " + ("✅ 유의" if lo > 0.5 else "⛔"))

sh = []
for seed in range(10):
    r2 = np.random.default_rng(seed); ys = y.copy()
    for p in np.unique(pid):
        mk = pid == p; v = ys[mk]; r2.shuffle(v); ys[mk] = v
    o2 = oof_of(ys); k2 = ~np.isnan(o2)
    sh.append(roc_auc_score(ys[k2], o2[k2]))
sh = np.array(sh)
print(f"  셔플 대조: 실제 {roc_auc_score(y[ok],oof[ok]):.3f} vs 셔플 {sh.mean():.3f} (최대 {sh.max():.3f})")
print("  → 신호 있음" if roc_auc_score(y[ok],oof[ok]) > sh.max() else "  → ⚠ 구분 안 됨")

m = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.05, num_leaves=31,
                       min_child_samples=20, random_state=42, verbose=-1).fit(X, y)
imp = pd.Series(m.feature_importances_, index=X.columns).sort_values(ascending=False)
print("\n  상위 피처:")
for k, v in imp.head(8).items(): print(f"    {v:5d}  {k}")
