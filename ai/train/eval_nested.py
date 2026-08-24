# -*- coding: utf-8 -*-
r"""K 를 중첩 교차검증으로 고른다 — 마지막 방법론 구멍을 막는다. 2026.08.25

    .venv/Scripts/python.exe ai/train/eval_nested.py [모드]

## 무엇을 고치나

`eval_selected.py` 의 0.608 에는 한 가지 한계가 남아 있었습니다 —
**`K=30` 을 전체 결과를 보고 골랐습니다.** 「K 를 5~95 까지 다 돌려보고
제일 좋은 것을 골랐다」면, 그 K 는 평가 데이터를 이미 본 것입니다.

여기서는 **바깥 폴드의 학습 부분만으로 K 를 고릅니다.**

    바깥 5겹 (참가자 분할)
      └ 학습 부분에서 안쪽 4겹을 다시 돌려 K 를 고른다
      └ 고른 K 로 학습 부분 전체를 다시 학습
      └ 바깥 평가 부분을 예측          ← 이 예측은 K 선택을 본 적이 없다

**바깥 평가 부분은 K 선택 과정에 한 번도 쓰이지 않습니다.** 그래서 나온
숫자에는 「같은 데이터로 골랐다」는 단서가 붙지 않습니다.

⚠ 안쪽에서 고른 K 는 폴드마다 다를 수 있습니다. 그게 정상이고, 어떤
  값들이 뽑혔는지 함께 출력합니다.
"""
import importlib.util
import sys
import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

MODE = sys.argv[1] if len(sys.argv) > 1 else "tense"
spec = importlib.util.spec_from_file_location("ef", "ai/train/eval_final.py")
ef = importlib.util.module_from_spec(spec)
sys.argv = [sys.argv[0], MODE]
spec.loader.exec_module(ef)

K_GRID = [10, 15, 20, 30, 50]


def make(kind, k):
    if kind == "lr":
        return make_pipeline(StandardScaler(), SelectKBest(f_classif, k=k),
                             LogisticRegression(max_iter=3000, C=0.1))
    return make_pipeline(SelectKBest(f_classif, k=k),
                         lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05,
                                            num_leaves=31, min_child_samples=20,
                                            subsample=0.8, colsample_bytree=0.8,
                                            random_state=42, verbose=-1))


def main():
    lab, title = ef.load_labels()
    print(f"라벨 {len(lab)}건 · 참가자 {lab.pid.nunique()}")
    print("피처 만드는 중...")
    df = ef.build(lab)
    y = df["_y"].to_numpy()
    X = df.drop(columns=["_y", "_pid"])
    pid = df["_pid"].to_numpy()
    g0 = pd.factorize(pid)[0]
    print(f"표본 {len(df)} · 참가자 {df._pid.nunique()} · 피처 {X.shape[1]} "
          f"· 양성률 {y.mean():.1%}\n")

    def nested(kind, labels=None, log=False):
        yy = y if labels is None else labels
        o = np.full(len(df), np.nan)
        picks = []
        for tr, te in GroupKFold(5).split(X, yy, groups=g0):
            if len(np.unique(yy[tr])) < 2:
                continue
            # ── 안쪽: 학습 부분만으로 K 를 고른다 ──
            gin = g0[tr]
            best_k, best_s = K_GRID[0], -1
            for k in K_GRID:
                if k > X.shape[1]:
                    continue
                oin = np.full(len(tr), np.nan)
                for itr, ite in GroupKFold(4).split(X.iloc[tr], yy[tr], groups=gin):
                    if len(np.unique(yy[tr][itr])) < 2:
                        continue
                    m = make(kind, k)
                    m.fit(X.iloc[tr].iloc[itr], yy[tr][itr])
                    oin[ite] = m.predict_proba(X.iloc[tr].iloc[ite])[:, 1]
                ok = ~np.isnan(oin)
                if ok.sum() < 30 or len(np.unique(yy[tr][ok])) < 2:
                    continue
                s = roc_auc_score(yy[tr][ok], oin[ok])
                if s > best_s:
                    best_k, best_s = k, s
            picks.append(best_k)
            # ── 바깥: 고른 K 로 다시 학습해 평가 부분을 예측 ──
            m = make(kind, min(best_k, X.shape[1]))
            m.fit(X.iloc[tr], yy[tr])
            o[te] = m.predict_proba(X.iloc[te])[:, 1]
        if log:
            print(f"  {kind}: 폴드별로 고른 K = {picks}")
        return o

    def rank(o):
        return pd.Series(o).rank(pct=True).to_numpy()

    def overall(o, labels=None, n=2000):
        yy = y if labels is None else labels
        ok = ~np.isnan(o)
        rng = np.random.default_rng(42)
        pids = np.unique(pid)
        out = []
        for _ in range(n):
            smp = rng.choice(pids, len(pids), replace=True)
            idx = np.concatenate([np.where(pid == p)[0] for p in smp])
            idx = idx[ok[idx]]
            if len(np.unique(yy[idx])) < 2:
                continue
            out.append(roc_auc_score(yy[idx], o[idx]))
        a = np.array(out)
        return roc_auc_score(yy[ok], o[ok]), *np.percentile(a, [2.5, 97.5])

    def within(o, labels=None):
        yy = y if labels is None else labels
        ok = ~np.isnan(o)
        v = []
        for p in np.unique(pid):
            m = (pid == p) & ok
            if m.sum() >= 8 and len(np.unique(yy[m])) > 1:
                v.append(roc_auc_score(yy[m], o[m]))
        return (np.mean(v) if v else np.nan), len(v)

    print(f"=== 중첩 교차검증 · {title} ===\n")
    o_lr = nested("lr", log=True)
    o_gb = nested("gb", log=True)
    o_en = (rank(o_lr) + rank(o_gb)) / 2
    print()
    print(f"  {'구성':22s} {'전체 AUC':>9} {'95%':>16}  {'참가자 내부':>10}")
    print(f"  {'-'*22} {'-'*9} {'-'*16}  {'-'*10}")
    for name, o in [("LogisticRegression", o_lr), ("LightGBM", o_gb),
                    ("앙상블(순위 평균)", o_en)]:
        a, lo, hi = overall(o)
        w, npart = within(o)
        print(f"  {name:22s} {a:9.3f} {lo:.3f}~{hi:.3f}{'✅' if lo > .5 else '  '}  "
              f"{w:10.3f}")
    print(f"\n  (참가자 내부는 {npart}명 평균)")

    sh, shw = [], []
    for seed in range(5):        # 중첩이라 무거워 5회
        rng = np.random.default_rng(seed)
        ys = y.copy()
        for p in np.unique(pid):
            k = pid == p
            v = ys[k]
            rng.shuffle(v)
            ys[k] = v
        e = (rank(nested("lr", ys)) + rank(nested("gb", ys))) / 2
        ok = ~np.isnan(e)
        sh.append(roc_auc_score(ys[ok], e[ok]))
        shw.append(within(e, ys)[0])
    sh, shw = np.array(sh), np.array(shw)
    ok = ~np.isnan(o_en)
    real, rw = roc_auc_score(y[ok], o_en[ok]), within(o_en)[0]
    print(f"\n  셔플 대조  전체 {real:.3f} vs {sh.mean():.3f}(최대 {sh.max():.3f}) "
          f"{'✅' if real > sh.max() else '⛔'}")
    print(f"            내부 {rw:.3f} vs {shw.mean():.3f}(최대 {shw.max():.3f}) "
          f"{'✅' if rw > shw.max() else '⛔'}")


if __name__ == "__main__":
    main()
