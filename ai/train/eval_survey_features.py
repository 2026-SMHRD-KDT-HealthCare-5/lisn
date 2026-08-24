# -*- coding: utf-8 -*-
"""논문 방식 검증 — 센서에 「설문」을 더하면 성능이 오르는가.

Applied Sciences(2025)가 같은 LifeSnaps 로 AUC 0.709 를 냈는데
「Fitbit + 자기보고 설문」결합이었다. 우리는 센서만 썼다.

⚠ 설문이라도 성격이 다르다.
   - personality(성격 5요인) : **1회 측정 · 변하지 않음** → 가입 때 한 번
     받으면 우리 서비스도 쓸 수 있다
   - PANAS/STAI            : 그때그때의 기분·불안 → 이걸 피처로 넣어
     기분을 맞히는 건 「답을 보고 답 맞히기」라 서비스에 못 쓴다
"""
import warnings, numpy as np, pandas as pd, lightgbm as lgb
warnings.filterwarnings("ignore")
from pathlib import Path
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

BASE = Path("ai/data_raw/lifesnaps/rais_anonymized")
CSV = BASE/"csv_rais_anonymized"/"daily_fitbit_sema_df_unprocessed.csv"
PERS = BASE/"scored_surveys"/"personality.csv"

FEATS = ["minutesAsleep","sleep_efficiency","minutesToFallAsleep","minutesAwake",
         "steps","distance","calories","very_active_minutes","moderately_active_minutes",
         "lightly_active_minutes","sedentary_minutes","bpm","resting_hr"]
BIG5 = ["extraversion","agreeableness","conscientiousness","stability","intellect"]

def build(target, with_personality):
    d = pd.read_csv(CSV, parse_dates=["date"]).rename(columns={"id":"pid"}).sort_values(["pid","date"])
    pers = pd.read_csv(PERS).rename(columns={"user_id":"pid"}).drop_duplicates("pid").set_index("pid")
    lab = d[d[target].notna()][["pid","date",target]]
    rows=[]
    for _, s in lab.iterrows():
        w = d[(d.pid==s.pid)&(d.date>s.date-pd.Timedelta(days=14))&(d.date<=s.date)]
        if len(w)<7: continue
        f={}
        for c in FEATS:
            if c not in w.columns: continue
            v=w[c].dropna()
            if len(v)<3: continue
            f[c+"_mean"]=v.mean(); f[c+"_std"]=v.std(); f[c+"_last"]=w[c].iloc[-1]
            h=w[c].iloc[:-1].dropna()
            if len(h)>=3 and h.std()>0: f[c+"_z"]=(w[c].iloc[-1]-h.median())/h.std()
        if len(f)<10: continue
        if with_personality:
            if s.pid not in pers.index: continue
            for b in BIG5:
                f["p_"+b]=pers.loc[s.pid, b]
        f["_y"]=int(s[target]); f["_pid"]=s.pid; rows.append(f)
    return pd.DataFrame(rows).fillna(0)

def score(df, n_rep=20):
    y=df["_y"].to_numpy(); X=df.drop(columns=["_y","_pid"]); pid=df["_pid"].to_numpy()
    rng=np.random.default_rng(42); out=[]
    for _ in range(n_rep):
        p=np.unique(pid).copy(); rng.shuffle(p)
        rm={v:i for i,v in enumerate(p)}; g=np.array([rm[v] for v in pid])
        oof=np.full(len(df),np.nan)
        for tr,te in GroupKFold(5).split(X,y,groups=g):
            if len(np.unique(y[tr]))<2: continue
            m=lgb.LGBMClassifier(n_estimators=150,learning_rate=0.05,num_leaves=15,
                min_child_samples=10,subsample=0.8,colsample_bytree=0.8,
                random_state=42,verbose=-1)
            m.fit(X.iloc[tr],y[tr]); oof[te]=m.predict_proba(X.iloc[te])[:,1]
        ok=~np.isnan(oof)
        if ok.sum()>30 and len(np.unique(y[ok]))>1: out.append(roc_auc_score(y[ok],oof[ok]))
    return np.array(out)

print("=== 센서만 vs 센서+성격 5요인 ===\n")
for t in ["HAPPY","TIRED","SAD","TENSE/ANXIOUS"]:
    a=score(build(t, False)); b=score(build(t, True))
    if not len(a) or not len(b): continue
    la,ha=np.percentile(a,[2.5,97.5]); lb,hb=np.percentile(b,[2.5,97.5])
    print(f"{t:16s} 센서만    {a.mean():.3f}  95% {la:.3f}~{ha:.3f}")
    print(f"{'':16s} +성격     {b.mean():.3f}  95% {lb:.3f}~{hb:.3f}   {b.mean()-a.mean():+.3f}")
    print()
