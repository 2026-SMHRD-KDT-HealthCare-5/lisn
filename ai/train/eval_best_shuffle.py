# -*- coding: utf-8 -*-
import sys, warnings, numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb

TARGET = sys.argv[1] if len(sys.argv) > 1 else "TENSE/ANXIOUS"
src = open("ai/train/eval_best.py", encoding="utf-8").read()
head = src.split("def oof(kind):")[0]
head = head.replace('TARGET = sys.argv[1] if len(sys.argv) > 1 else "HAPPY"', f'TARGET = {TARGET!r}')
exec(head)

def run(labels):
    outs=[]
    for kind in ["lr","gb"]:
        o=np.full(len(df),np.nan)
        for tr,te in GroupKFold(5).split(X,labels,groups=g0):
            if len(np.unique(labels[tr]))<2: continue
            m=(make_pipeline(StandardScaler(),LogisticRegression(max_iter=3000,C=0.1))
               if kind=="lr" else
               lgb.LGBMClassifier(n_estimators=200,learning_rate=0.05,num_leaves=31,
                   min_child_samples=20,subsample=0.8,colsample_bytree=0.8,
                   random_state=42,verbose=-1))
            m.fit(X.iloc[tr],labels[tr]); o[te]=m.predict_proba(X.iloc[te])[:,1]
        outs.append(pd.Series(o).rank(pct=True).to_numpy())
    e=(outs[0]+outs[1])/2; ok=~np.isnan(e)
    return roc_auc_score(labels[ok],e[ok])

real = run(y)
sh=[]
for seed in range(10):
    r=np.random.default_rng(seed); ys=y.copy()
    for p in np.unique(pid):
        mk=pid==p; v=ys[mk]; r.shuffle(v); ys[mk]=v
    sh.append(run(ys))
sh=np.array(sh)
print(f"=== 앙상블 셔플 대조 · {TARGET} ===")
print(f"  실제 {real:.3f}  vs  셔플 {sh.mean():.3f} (최대 {sh.max():.3f})")
print("  → 신호 있음" if real > sh.max() else "  → ⚠ 셔플과 구분 안 됨")
