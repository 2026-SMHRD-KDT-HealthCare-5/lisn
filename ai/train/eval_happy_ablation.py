# -*- coding: utf-8 -*-
"""마지막 확인 — _z 피처가 정말 기여하는가 + 라벨 셔플 대조."""
import warnings, numpy as np, pandas as pd, lightgbm as lgb
warnings.filterwarnings("ignore")
from pathlib import Path
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

CSV = Path("ai/data_raw/lifesnaps/rais_anonymized/csv_rais_anonymized/daily_fitbit_sema_df_unprocessed.csv")
FEATS = ["minutesAsleep","sleep_efficiency","minutesToFallAsleep","minutesAwake",
         "steps","distance","calories","very_active_minutes","moderately_active_minutes",
         "lightly_active_minutes","sedentary_minutes","bpm","resting_hr"]

def build():
    d = pd.read_csv(CSV, parse_dates=["date"]).rename(columns={"id":"pid"}).sort_values(["pid","date"])
    lab = d[d["HAPPY"].notna()][["pid","date","HAPPY"]]
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
        f["_y"]=int(s["HAPPY"]); f["_pid"]=s.pid; rows.append(f)
    return pd.DataFrame(rows).fillna(0)

def evaluate(df, cols, shuffle=False, seed=42):
    y=df["_y"].to_numpy().copy(); X=df[cols]; pid=df["_pid"].to_numpy()
    if shuffle:
        rng=np.random.default_rng(seed)
        # 참가자 안에서 섞는다 — 참가자 효과는 남기고 날짜-라벨 관계만 끊는다
        for p in np.unique(pid):
            m=pid==p; v=y[m]; rng.shuffle(v); y[m]=v
    g=pd.factorize(pid)[0]; oof=np.full(len(df),np.nan)
    for tr,te in GroupKFold(5).split(X,y,groups=g):
        if len(np.unique(y[tr]))<2: continue
        m=lgb.LGBMClassifier(n_estimators=150,learning_rate=0.05,num_leaves=15,
            min_child_samples=10,subsample=0.8,colsample_bytree=0.8,random_state=42,verbose=-1)
        m.fit(X.iloc[tr],y[tr]); oof[te]=m.predict_proba(X.iloc[te])[:,1]
    ok=~np.isnan(oof)
    return roc_auc_score(y[ok],oof[ok])

df=build()
allc=[c for c in df.columns if not c.startswith("_")]
zc=[c for c in allc if c.endswith("_z")]
nz=[c for c in allc if not c.endswith("_z")]

print("=== ① 어떤 피처군이 기여하는가 ===")
print(f"  전체({len(allc)}개)        AUC {evaluate(df,allc):.3f}")
print(f"  _z 만({len(zc)}개)          AUC {evaluate(df,zc):.3f}   ← 개인 기준선 대비 편차")
print(f"  _z 제외({len(nz)}개)        AUC {evaluate(df,nz):.3f}   ← 절대값·변동성만")
print()
print("=== ② 라벨 셔플 대조 (참가자 내에서 섞음) ===")
print("   진짜 신호라면 셔플하면 0.5 로 떨어져야 한다")
real=evaluate(df,allc)
sh=[evaluate(df,allc,shuffle=True,seed=s) for s in range(10)]
sh=np.array(sh)
print(f"  실제       {real:.3f}")
print(f"  셔플 10회   {sh.mean():.3f}  (범위 {sh.min():.3f}~{sh.max():.3f})")
print(f"  차이       {real-sh.mean():+.3f}")
print("  → 신호가 있습니다" if real > sh.max() else "  → ⚠ 셔플과 구분되지 않습니다")
