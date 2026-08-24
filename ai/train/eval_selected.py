# -*- coding: utf-8 -*-
r"""폴드 안 피처 선택 + 앙상블 — 최종 구성. 2026.08.25

    .venv/Scripts/python.exe ai/train/eval_selected.py [모드]
      모드: narrow(기본) | wide | happy | tense

`extract_bson.py` 를 먼저 돌리세요.

## 왜 이 구성인가

`eval_ablation.py` 가 보여준 것 — 피처 95개를 다 넣으면 0.551 인데,
**폴드 안에서 상위 30개만 고르면 0.592** 로 오릅니다. 참가자가 60명뿐이라
피처가 늘면 얻는 신호보다 늘어나는 분산이 큽니다.

> ⚠ **선택은 반드시 파이프라인 안에서** 합니다. 전체 데이터로 고르면 평가
> 폴드의 정답을 이미 본 것이라 AUC 가 부풀려집니다.

> ⚠ **K=30 은 같은 데이터를 보고 골랐습니다.** 다만 K 10~30 이 전부
> 0.576~0.592 라 칼날 위의 값은 아닙니다(`eval_ablation.py` 참조).
> **엄밀히는 K 도 중첩 교차검증으로 골라야** 합니다.

## 결과 (2026.08.25 실측)

| 대상 | 표본 | 양성률 | 앙상블 AUC | 95% | 셔플 |
|---|---|---|---|---|---|
| **TENSE/ANXIOUS** | 3801 | 14.7% | **0.608** | 0.565~0.649 | 0.466 (최대 0.486) |
| 부정 정서(narrow) | 2786 | 25.0% | 0.598 | 0.558~0.638 | 0.497 (최대 0.515) |
| HAPPY | 3801 | 18.1% | 0.596 | 0.542~0.652 | 0.504 (최대 0.520) |
| 부정 정서(wide) | 3801 | 45.0% | 0.568 | 0.525~0.612 | 0.520 (최대 0.562) |

**`wide` 만 셔플과의 거리가 좁습니다** — `TIRED` 를 섞은 정의입니다.
"""
import sys, warnings, importlib.util
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb

MODE = sys.argv[1] if len(sys.argv) > 1 else "narrow"
spec = importlib.util.spec_from_file_location("ef", "ai/train/eval_final.py")
ef = importlib.util.module_from_spec(spec)
sys.argv = [sys.argv[0], MODE]
spec.loader.exec_module(ef)

lab, title = ef.load_labels()
df = ef.build(lab)
y = df["_y"].to_numpy(); X = df.drop(columns=["_y","_pid"]); pid = df["_pid"].to_numpy()
g0 = pd.factorize(pid)[0]
K = 30
print(f"{title} · 표본 {len(df)} · 참가자 {df._pid.nunique()} · 피처 {X.shape[1]} · 양성률 {y.mean():.1%}")

def oof(kind, labels=None):
    yy = y if labels is None else labels
    o = np.full(len(df), np.nan)
    for tr, te in GroupKFold(5).split(X, yy, groups=g0):
        if len(np.unique(yy[tr])) < 2: continue
        if kind == "lr":
            m = make_pipeline(StandardScaler(), SelectKBest(f_classif, k=K),
                              LogisticRegression(max_iter=3000, C=0.1))
        else:
            m = make_pipeline(SelectKBest(f_classif, k=K),
                              lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05,
                                  num_leaves=31, min_child_samples=20, subsample=0.8,
                                  colsample_bytree=0.8, random_state=42, verbose=-1))
        m.fit(X.iloc[tr], yy[tr]); o[te] = m.predict_proba(X.iloc[te])[:,1]
    return o

rank = lambda o: pd.Series(o).rank(pct=True).to_numpy()
def boot(o, n=2000):
    ok = ~np.isnan(o); rng = np.random.default_rng(42); pids = np.unique(pid); out=[]
    for _ in range(n):
        smp = rng.choice(pids, len(pids), replace=True)
        idx = np.concatenate([np.where(pid==p)[0] for p in smp]); idx = idx[ok[idx]]
        if len(np.unique(y[idx])) < 2: continue
        out.append(roc_auc_score(y[idx], o[idx]))
    a = np.array(out); return roc_auc_score(y[ok], o[ok]), *np.percentile(a,[2.5,97.5])

o_lr, o_gb = oof("lr"), oof("gb")
o_en = (rank(o_lr)+rank(o_gb))/2
print(f"\n  {'구성':22s} {'AUC':>7}  {'95%':>16}")
for nm, o in [("LogisticRegression",o_lr),("LightGBM",o_gb),("앙상블",o_en)]:
    a,lo,hi = boot(o)
    print(f"  {nm:22s} {a:7.3f}  {lo:.3f}~{hi:.3f}" + (" ✅" if lo>0.5 else ""))

for nm, fn in [("LogReg", lambda ys: oof("lr", ys)),
               ("앙상블", lambda ys: (rank(oof("lr",ys))+rank(oof("gb",ys)))/2)]:
    sh=[]
    for seed in range(10):
        rng=np.random.default_rng(seed); ys=y.copy()
        for p in np.unique(pid):
            mk=pid==p; v=ys[mk]; rng.shuffle(v); ys[mk]=v
        o2=fn(ys); k2=~np.isnan(o2); sh.append(roc_auc_score(ys[k2],o2[k2]))
    sh=np.array(sh)
    real = roc_auc_score(y[~np.isnan(o_lr)], o_lr[~np.isnan(o_lr)]) if nm=="LogReg" \
           else roc_auc_score(y[~np.isnan(o_en)], o_en[~np.isnan(o_en)])
    ok = "신호 있음" if real > sh.max() else "⚠ 구분 안 됨"
    print(f"  셔플 대조({nm}): 실제 {real:.3f} vs 셔플 {sh.mean():.3f} (최대 {sh.max():.3f}) → {ok}")
