# -*- coding: utf-8 -*-
r"""모델을 바꾸면 나아지는가 — 같은 피처·같은 분할로 6종 비교.

    .venv/Scripts/python.exe ai/train/eval_models.py [감정]

## 왜 재보는가

논문(Applied Sciences 2025)이 CatBoost 로 0.709 를 냈습니다. 우리는
LightGBM 만 썼습니다. **모델 탓인지 데이터 탓인지 가려야** 다음 판단이
섭니다.

⚠ **하이퍼파라미터 튜닝은 하지 않습니다.** 표본이 61명이라 튜닝하면
  그 61명에 맞춰질 뿐입니다. 각 모델의 기본값 근처로만 비교합니다 —
  「모델 종류를 바꾸는 것만으로 달라지는가」가 질문이기 때문입니다.

⚠ **선형 모델과 더미를 함께 넣습니다.** 트리 계열끼리만 비교하면
  「트리가 이 문제에 안 맞는 것 아닌가」를 못 가려냅니다.
"""
import sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from pathlib import Path
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.dummy import DummyClassifier
import lightgbm as lgb, xgboost as xgb
from catboost import CatBoostClassifier

sys.argv = sys.argv if len(sys.argv) > 1 else sys.argv + ["HAPPY"]
TARGET = sys.argv[1]

#  eval_momentary.py 와 같은 방식으로 표본을 만든다(시각 단위).
exec(open("ai/train/eval_momentary.py", encoding="utf-8").read().split("y = df[")[0]
     .replace('TARGET = sys.argv[1] if len(sys.argv) > 1 else "HAPPY"', f'TARGET = {TARGET!r}'))

y = df["_y"].to_numpy(); X = df.drop(columns=["_y","_pid"]); pid = df["_pid"].to_numpy()
g0 = pd.factorize(pid)[0]

MODELS = {
    "Dummy(기준선)":  lambda: DummyClassifier(strategy="stratified", random_state=42),
    "LogisticReg":    lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=0.1)),
    "RandomForest":   lambda: RandomForestClassifier(n_estimators=300, min_samples_leaf=5,
                                                     random_state=42, n_jobs=-1),
    "LightGBM":       lambda: lgb.LGBMClassifier(n_estimators=200, learning_rate=0.05, num_leaves=31,
                                                 min_child_samples=20, subsample=0.8,
                                                 colsample_bytree=0.8, random_state=42, verbose=-1),
    "XGBoost":        lambda: xgb.XGBClassifier(n_estimators=200, learning_rate=0.05, max_depth=5,
                                                subsample=0.8, colsample_bytree=0.8,
                                                random_state=42, eval_metric="logloss", verbosity=0),
    "CatBoost":       lambda: CatBoostClassifier(iterations=200, learning_rate=0.05, depth=5,
                                                 random_seed=42, verbose=0),
}

def oof_auc(make):
    o = np.full(len(df), np.nan)
    for tr, te in GroupKFold(5).split(X, y, groups=g0):
        if len(np.unique(y[tr])) < 2: continue
        m = make(); m.fit(X.iloc[tr], y[tr])
        o[te] = m.predict_proba(X.iloc[te])[:, 1]
    ok = ~np.isnan(o)
    return roc_auc_score(y[ok], o[ok]), o, ok

def boot(o, ok, n=1000):
    rng = np.random.default_rng(42); pids = np.unique(pid); out = []
    for _ in range(n):
        smp = rng.choice(pids, len(pids), replace=True)
        idx = np.concatenate([np.where(pid == p)[0] for p in smp])
        idx = idx[ok[idx]]
        if len(np.unique(y[idx])) < 2: continue
        out.append(roc_auc_score(y[idx], o[idx]))
    a = np.array(out); return a.mean(), *np.percentile(a, [2.5, 97.5])

print(f"=== 모델 비교 · {TARGET} · 표본 {len(df)} · 참가자 {df._pid.nunique()} ===\n")
print(f"  {'모델':16s} {'AUC':>7}  {'참가자 부트스트랩 95%':>24}")
print(f"  {'-'*16} {'-'*7}  {'-'*24}")
res = {}
for name, make in MODELS.items():
    try:
        auc, o, ok = oof_auc(make)
        m, lo, hi = boot(o, ok)
        sig = " ✅" if lo > 0.5 else ""
        print(f"  {name:16s} {auc:7.3f}  {lo:.3f} ~ {hi:.3f}{sig}")
        res[name] = auc
    except Exception as e:
        print(f"  {name:16s}  실패: {str(e)[:40]}")

best = max(res, key=res.get)
lgbm = res.get("LightGBM", 0)
print(f"\n  최고: {best} ({res[best]:.3f}) · LightGBM ({lgbm:.3f}) 대비 {res[best]-lgbm:+.3f}")
if abs(res[best] - lgbm) < 0.02:
    print("  → 모델 종류로 갈리는 폭이 작습니다. 병목은 모델이 아닙니다.")
else:
    print("  → 모델 종류가 유의미하게 갈립니다.")
