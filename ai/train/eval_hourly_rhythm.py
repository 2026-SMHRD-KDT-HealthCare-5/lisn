# -*- coding: utf-8 -*-
"""시간 단위 리듬 피처로 넘어간다 — 표본을 못 늘리면 해상도를 올린다.

일별 요약(steps 합계)에서는 「언제 움직였나」가 사라진다. 같은 8000보라도
아침에 몰린 날과 밤에 몰린 날은 다르다. 우울·무기력의 알려진 신호가
**활동 위상 지연**(늦게 일어나고 늦게 활동)인데, 일별 합계로는 안 보인다.
"""
import warnings, numpy as np, pandas as pd, lightgbm as lgb
warnings.filterwarnings("ignore")
from pathlib import Path
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

H = Path("ai/data_raw/lifesnaps/rais_anonymized/csv_rais_anonymized/hourly_fitbit_sema_df_unprocessed.csv")
import sys
TARGET = sys.argv[1] if len(sys.argv)>1 else "HAPPY"

def circadian(g):
    """하루치 시간별 걸음에서 리듬 지표를 뽑는다."""
    # 같은 시간에 행이 여러 개 있다(라벨 중복 기록). 먼저 집계한다.
    s = g.groupby("hour")["steps"].mean().reindex(range(24)).fillna(0).to_numpy()
    tot = s.sum()
    if tot < 100:
        return None
    h = np.arange(24)
    # 활동 무게중심 — 하루 중 언제 움직였나 (원형 평균)
    ang = 2*np.pi*h/24
    cx, cy = (s*np.cos(ang)).sum()/tot, (s*np.sin(ang)).sum()/tot
    center = (np.arctan2(cy, cx) % (2*np.pi)) * 24/(2*np.pi)
    conc = np.hypot(cx, cy)                       # 활동 집중도 (1=한 시간에 몰림)
    bpm = g.groupby("hour")["bpm"].mean().reindex(range(24))
    return {
        "act_center": center,                      # 활동 위상 — 늦으면 지연
        "act_conc": conc,                          # 집중도
        "act_M10": np.sort(s)[-10:].mean(),        # 가장 활동적인 10시간 평균
        "act_L5": np.sort(s)[:5].mean(),           # 가장 조용한 5시간 평균
        "act_RA": (np.sort(s)[-10:].mean()-np.sort(s)[:5].mean())
                  /max(1,np.sort(s)[-10:].mean()+np.sort(s)[:5].mean()),  # 상대 진폭
        "act_morning": s[6:12].sum()/tot,          # 오전 비중
        "act_evening": s[18:24].sum()/tot,         # 저녁 비중
        "act_night": (s[0:6].sum())/tot,           # 심야 비중
        "act_hours": (s > tot/48).sum(),           # 활동한 시간 수
        "bpm_mean": bpm.mean(), "bpm_std": bpm.std(),
        "bpm_min": bpm.min(), "bpm_range": bpm.max()-bpm.min(),
        "steps_total": tot,
    }

print("시간 단위 데이터 읽는 중...")
d = pd.read_csv(H, usecols=["id","date","hour","steps","bpm","calories",TARGET])
d = d.rename(columns={"id":"pid"})
d["date"] = pd.to_datetime(d["date"])

# 하루 단위 리듬 피처
daily = {}
for (pid, dt), g in d.groupby(["pid","date"]):
    f = circadian(g)
    if f: daily[(pid, dt)] = f
print(f"리듬 피처 생성: {len(daily)}일\n")

lab = d[d[TARGET].notna()].groupby(["pid","date"])[TARGET].first().reset_index()

rows = []
for _, s in lab.iterrows():
    hist_keys = [(s.pid, s.date - pd.Timedelta(days=k)) for k in range(1, 15)]
    hist = [daily[k] for k in hist_keys if k in daily]
    today = daily.get((s.pid, s.date))
    if today is None or len(hist) < 5:
        continue
    f = dict(today)
    for k in today:
        vals = [h[k] for h in hist if h.get(k) is not None and not pd.isna(h[k])]
        if len(vals) >= 3 and np.std(vals) > 0:
            f[k+"_z"] = (today[k]-np.median(vals))/np.std(vals)     # 개인 기준선 대비
        f[k+"_base"] = np.mean(vals) if vals else 0
    f["_y"] = int(s[TARGET]); f["_pid"] = s.pid
    rows.append(f)

df = pd.DataFrame(rows).fillna(0)
print(f"표본 {len(df)} · 참가자 {df['_pid'].nunique()} · 피처 {df.shape[1]-2} · 양성률 {df['_y'].mean():.1%}\n")

y = df["_y"].to_numpy(); X = df.drop(columns=["_y","_pid"]); pid = df["_pid"].to_numpy()
g0 = pd.factorize(pid)[0]
oof = np.full(len(df), np.nan)
for tr, te in GroupKFold(5).split(X, y, groups=g0):
    m = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.05, num_leaves=15,
                           min_child_samples=10, subsample=0.8, colsample_bytree=0.8,
                           random_state=42, verbose=-1)
    m.fit(X.iloc[tr], y[tr]); oof[te] = m.predict_proba(X.iloc[te])[:,1]

rng = np.random.default_rng(42); pids = np.unique(pid); aucs = []
for _ in range(2000):
    smp = rng.choice(pids, len(pids), replace=True)
    idx = np.concatenate([np.where(pid==p)[0] for p in smp])
    if len(np.unique(y[idx])) < 2: continue
    aucs.append(roc_auc_score(y[idx], oof[idx]))
a = np.array(aucs); lo, hi = np.percentile(a, [2.5, 97.5])
print(f"=== 시간 단위 리듬 피처 · {TARGET} ===")
print(f"  AUC {a.mean():.3f}  참가자 부트스트랩 95% {lo:.3f}~{hi:.3f}  " + ("✅ 유의" if lo>0.5 else "⛔"))
print(f"  (일별 요약 피처는 0.549 · 95% 0.501~0.600)\n")

# 라벨 셔플 대조 — 참가자 안에서 섞어 날짜-라벨 관계만 끊는다
sh=[]
for seed in range(10):
    r2=np.random.default_rng(seed); ys=y.copy()
    for p in np.unique(pid):
        mk=pid==p; v=ys[mk]; r2.shuffle(v); ys[mk]=v
    o2=np.full(len(df),np.nan)
    for tr,te in GroupKFold(5).split(X,ys,groups=g0):
        if len(np.unique(ys[tr]))<2: continue
        mm=lgb.LGBMClassifier(n_estimators=200,learning_rate=0.05,num_leaves=15,
            min_child_samples=10,subsample=0.8,colsample_bytree=0.8,random_state=42,verbose=-1)
        mm.fit(X.iloc[tr],ys[tr]); o2[te]=mm.predict_proba(X.iloc[te])[:,1]
    ok2=~np.isnan(o2)
    sh.append(roc_auc_score(ys[ok2],o2[ok2]))
sh=np.array(sh)
real=roc_auc_score(y[~np.isnan(oof)],oof[~np.isnan(oof)])
print(f"  셔플 대조: 실제 {real:.3f} vs 셔플 {sh.mean():.3f} (최대 {sh.max():.3f})")
print("  → 신호 있음" if real>sh.max() else "  → ⚠ 셔플과 구분 안 됨")
print()

m = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.05, num_leaves=15,
                       min_child_samples=10, random_state=42, verbose=-1).fit(X, y)
imp = pd.Series(m.feature_importances_, index=X.columns).sort_values(ascending=False)
print("  상위 피처:")
for k, v in imp.head(8).items(): print(f"    {v:5d}  {k}")
