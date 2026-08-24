# -*- coding: utf-8 -*-
"""LifeSnaps 를 확장 피처로 다시 — 활동 강도·수면 단계까지 넣는다."""
import warnings, numpy as np, pandas as pd, lightgbm as lgb
warnings.filterwarnings("ignore")
from pathlib import Path
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

CSV = Path("ai/data_raw/lifesnaps/rais_anonymized/csv_rais_anonymized/daily_fitbit_sema_df_unprocessed.csv")
WINDOW, N_REP, N_SPLIT, SEED = 14, 20, 5, 42

# 이전 검증(eval_lifesnaps)은 수면·걸음 중심이었다. 여기서는 활동 강도·
# 수면 단계·심박까지 넣는다 — 결측 50% 미만인 것만.
FEATS = ["minutesAsleep","sleep_efficiency","minutesToFallAsleep","minutesAwake",
         "steps","distance","calories",
         "very_active_minutes","moderately_active_minutes",
         "lightly_active_minutes","sedentary_minutes",
         "bpm","resting_hr"]

def run(target):
    d = pd.read_csv(CSV, parse_dates=["date"]).rename(columns={"id":"pid"})
    d = d.sort_values(["pid","date"])
    lab = d[d[target].notna()][["pid","date",target]]
    rows=[]
    for _, s in lab.iterrows():
        w = d[(d.pid==s.pid)&(d.date>s.date-pd.Timedelta(days=WINDOW))&(d.date<=s.date)]
        if len(w) < 7: continue
        f={}
        for c in FEATS:
            if c not in w.columns: continue
            v=w[c].dropna()
            if len(v)<3: continue
            f[c+"_mean"]=v.mean(); f[c+"_std"]=v.std()
            f[c+"_last"]=w[c].iloc[-1]
            # 개인 기준선 대비 오늘의 위치 (우리 서비스가 보는 것)
            hist=w[c].iloc[:-1].dropna()
            if len(hist)>=3 and hist.std()>0:
                f[c+"_z"]=(w[c].iloc[-1]-hist.median())/hist.std()
        if len(f)<10: continue
        f["_y"]=int(s[target]); f["_pid"]=s.pid
        rows.append(f)
    df=pd.DataFrame(rows).fillna(0)
    if len(df)<80: print(f"[{target}] 표본 {len(df)} — 건너뜀"); return
    y=df["_y"].to_numpy(); X=df.drop(columns=["_y","_pid"]); g0=df["_pid"].to_numpy()
    print(f"=== {target} ===")
    print(f"  표본 {len(df)} · 참가자 {df['_pid'].nunique()} · 피처 {X.shape[1]} · 양성률 {y.mean():.1%}")
    rng=np.random.default_rng(SEED); aucs=[]
    for _ in range(N_REP):
        p=df["_pid"].unique().copy(); rng.shuffle(p)
        rm={v:i for i,v in enumerate(p)}; g=np.array([rm[v] for v in g0])
        oof=np.full(len(df),np.nan)
        for tr,te in GroupKFold(N_SPLIT).split(X,y,groups=g):
            if len(np.unique(y[tr]))<2: continue
            m=lgb.LGBMClassifier(n_estimators=150,learning_rate=0.05,num_leaves=15,
                min_child_samples=10,subsample=0.8,colsample_bytree=0.8,
                random_state=SEED,verbose=-1)
            m.fit(X.iloc[tr],y[tr]); oof[te]=m.predict_proba(X.iloc[te])[:,1]
        ok=~np.isnan(oof)
        if ok.sum()>30 and len(np.unique(y[ok]))>1: aucs.append(roc_auc_score(y[ok],oof[ok]))
    a=np.array(aucs); lo,hi=np.percentile(a,[2.5,97.5])
    flag=" ✅ 유의" if lo>0.5 else "  ⛔ 0.5 포함"
    print(f"  AUC {a.mean():.3f}  95% {lo:.3f}~{hi:.3f}{flag}\n")

for t in ["SAD","TENSE/ANXIOUS","TIRED","HAPPY"]:
    run(t)
