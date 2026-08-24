# -*- coding: utf-8 -*-
r"""참가자별 표준화 — 사람 사이 차이를 걷어내고 개인 내 변화만 본다. 2026.08.25

    .venv/Scripts/python.exe ai/train/eval_person.py [모드]

## 왜

`eval_context.py` 가 보여준 것 — 전체 AUC 0.728 중 상당 부분이 **「이
사람이 원래 부정적인가」**였습니다(셔플 대조도 0.666). 우리 서비스가
하는 일은 그게 아닙니다.

> **「이 사람의 나쁜 순간을 이 사람의 좋은 순간보다 위로 올리는가」**

그렇다면 **입력에서도 사람 사이 차이를 빼면** 됩니다. 참가자별로 각
피처를 그 사람의 평균·표준편차로 표준화합니다.

    x'  =  (x - mean_user(x)) / std_user(x)

⚠ **라벨 누수가 아닙니다.** 그 사람의 **피처**만 쓰고 정답은 보지
  않습니다. 배포 시에도 사용자의 센서 이력은 갖고 있으므로 같은 조건입니다.
  (참가자가 폴드 사이에 겹치지 않으므로 학습 폴드 오염도 없습니다.)

## 세 가지를 나란히 잽니다

    원본            지금까지 쓰던 것
    참가자 표준화     위 식
    둘 다           원본 + 표준화본을 함께
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

MODE = sys.argv[1] if len(sys.argv) > 1 else "narrow"
spec = importlib.util.spec_from_file_location("ef", "ai/train/eval_final.py")
ef = importlib.util.module_from_spec(spec)
sys.argv = [sys.argv[0], MODE]
spec.loader.exec_module(ef)

K = 30


def person_z(X, pid):
    """참가자별 표준화. 편차가 0 인 피처는 0 으로 둔다."""
    #  ⚠ 정수 컬럼에 실수를 넣으면 pandas 가 거부한다 — 먼저 실수로 바꾼다
    out = X.astype(float).copy()
    for p in np.unique(pid):
        m = pid == p
        sub = X.loc[m]
        sd = sub.std().replace(0, np.nan)
        out.loc[m] = ((sub - sub.mean()) / sd).fillna(0.0).to_numpy()
    return out


def main():
    lab, title = ef.load_labels()
    print(f"라벨 {len(lab)}건 · 참가자 {lab.pid.nunique()}")
    print("피처 만드는 중...")
    df = ef.build(lab)
    y = df["_y"].to_numpy()
    pid = df["_pid"].to_numpy()
    g0 = pd.factorize(pid)[0]
    X = df.drop(columns=["_y", "_pid"])
    Xz = person_z(X, pid)
    Xz.columns = [c + "_pz" for c in Xz.columns]
    print(f"표본 {len(df)} · 참가자 {df._pid.nunique()} · 피처 {X.shape[1]} "
          f"· 양성률 {y.mean():.1%}\n")

    SETS = {
        "원본": X,
        "참가자 표준화": Xz,
        "둘 다": pd.concat([X, Xz], axis=1),
    }

    def oof(Xd, kind, labels=None):
        yy = y if labels is None else labels
        o = np.full(len(Xd), np.nan)
        for tr, te in GroupKFold(5).split(Xd, yy, groups=g0):
            if len(np.unique(yy[tr])) < 2:
                continue
            k = min(K, Xd.shape[1])
            m = (make_pipeline(StandardScaler(), SelectKBest(f_classif, k=k),
                               LogisticRegression(max_iter=3000, C=0.1))
                 if kind == "lr" else
                 make_pipeline(SelectKBest(f_classif, k=k),
                               lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05,
                                                  num_leaves=31, min_child_samples=20,
                                                  subsample=0.8, colsample_bytree=0.8,
                                                  random_state=42, verbose=-1)))
            m.fit(Xd.iloc[tr], yy[tr])
            o[te] = m.predict_proba(Xd.iloc[te])[:, 1]
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

    def within(o, labels=None, n=2000):
        yy = y if labels is None else labels
        ok = ~np.isnan(o)
        v = []
        for p in np.unique(pid):
            m = (pid == p) & ok
            if m.sum() >= 8 and len(np.unique(yy[m])) > 1:
                v.append(roc_auc_score(yy[m], o[m]))
        v = np.array(v)
        rng = np.random.default_rng(42)
        bs = [rng.choice(v, len(v), replace=True).mean() for _ in range(n)]
        return v.mean(), *np.percentile(bs, [2.5, 97.5]), len(v)

    print(f"=== {title} ===\n")
    print(f"  {'입력':14s} {'전체':>7} {'95%':>15}   {'참가자 내부':>10} {'95%':>15}")
    print(f"  {'-'*14} {'-'*7} {'-'*15}   {'-'*10} {'-'*15}")
    res = {}
    for name, Xd in SETS.items():
        o = (rank(oof(Xd, "lr")) + rank(oof(Xd, "gb"))) / 2
        res[name] = o
        a, lo, hi = overall(o)
        w, wlo, whi, npart = within(o)
        print(f"  {name:14s} {a:7.3f} {lo:.3f}~{hi:.3f}{'✅' if lo > .5 else '  '}   "
              f"{w:10.3f} {wlo:.3f}~{whi:.3f}{'✅' if wlo > .5 else '  '}")
    print(f"\n  (참가자 내부는 두 라벨이 다 있고 8건 이상인 {npart}명 평균)\n")

    for name, Xd in SETS.items():
        sh, shw = [], []
        for seed in range(10):
            rng = np.random.default_rng(seed)
            ys = y.copy()
            for p in np.unique(pid):
                mk = pid == p
                v = ys[mk]
                rng.shuffle(v)
                ys[mk] = v
            e = (rank(oof(Xd, "lr", ys)) + rank(oof(Xd, "gb", ys))) / 2
            sh.append(overall(e, ys, n=1)[0])
            shw.append(within(e, ys, n=1)[0])
        sh, shw = np.array(sh), np.array(shw)
        o = res[name]
        ok = ~np.isnan(o)
        print(f"  셔플 {name:12s} 전체 {roc_auc_score(y[ok], o[ok]):.3f} vs "
              f"{sh.mean():.3f}(최대 {sh.max():.3f})"
              f" {'✅' if roc_auc_score(y[ok], o[ok]) > sh.max() else '⛔'}"
              f"   내부 {within(o)[0]:.3f} vs {shw.mean():.3f}(최대 {shw.max():.3f})"
              f" {'✅' if within(o)[0] > shw.max() else '⛔'}")

    #  ── 운영 지점: 사용자마다 자기 상위 N% 를 알림한다면 ──
    best = max(res, key=lambda k: within(res[k])[0])
    o = res[best]
    print(f"\n  === 사용자별 상위 N% 만 알림 ({best} 기준 · 기본 양성률 "
          f"{y.mean():.1%}) ===")
    print(f"  {'상위':>6} {'건수':>6} {'정밀도':>7} {'재현율':>7} {'향상':>6}")
    for pct in (5, 10, 20, 30):
        sel = np.zeros(len(o), dtype=bool)
        for p in np.unique(pid):
            m = np.where((pid == p) & ~np.isnan(o))[0]
            if len(m) < 5:
                continue
            k = max(1, int(len(m) * pct / 100))
            sel[m[np.argsort(-o[m])[:k]]] = True
        if not sel.any():
            continue
        prec, rec = y[sel].mean(), y[sel].sum() / y.sum()
        print(f"  {pct:5d}% {sel.sum():6d} {prec:7.1%} {rec:7.1%} "
              f"{prec/y.mean():5.2f}배")


if __name__ == "__main__":
    main()
