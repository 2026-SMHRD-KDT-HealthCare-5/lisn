# -*- coding: utf-8 -*-
r"""배포본을 더 올릴 수 있나 — 모델 형태와 라벨을 바꿔본다. 2026.08.25

    .venv/Scripts/python.exe ai/train/eval_variants.py

지금 판정에 들어간 것은 **규칙 입력 21개 + 로지스틱 회귀**이고
참가자 내부 AUC 0.609 입니다. 그것을 기준으로 다음을 잽니다.

| 후보 | 발상 |
|---|---|
| 규제 세기 `C` | 표본 62명이면 더 세게 눌러야 할 수 있다 |
| ElasticNet | 상관 높은 z 들 사이에서 골라내기 |
| 상호작용 항 | 「못 잔 날 + 안 걸은 날」처럼 **겹칠 때** 나쁜 경우 |
| 클래스 가중 | 양성률 14.7% 의 불균형 보정 |
| **다중 라벨 앙상블** | 불안·부정정서·긍정을 각각 학습해 합친다 |

⚠ 전부 **참가자 분할 + 중첩 교차검증**, 판정은 **참가자 내부 AUC** 의
  같은 리샘플 차이로 합니다. 기준선(배포본)보다 95% 하한이 0 을 넘어야
  바꿉니다.

⚠ **여기서 이겨도 그대로 넣지 않습니다.** 후보를 여럿 재면 그중 하나는
  우연히 좋아 보입니다. 이긴 후보는 **다른 대상(narrow·happy)에서도**
  같은 방향인지 확인한 뒤에 넣습니다.
"""
import importlib.util
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

warnings.filterwarnings("ignore")

spec = importlib.util.spec_from_file_location("rf", "ai/train/eval_rule_features.py")
sys.argv = [sys.argv[0], "tense"]
rf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rf)

K_GRID = [8, 12, 21]


def make(kind, k):
    if kind == "poly":
        #  ⚠ 상호작용만. 제곱항까지 넣으면 피처가 폭발한다.
        return make_pipeline(
            StandardScaler(), SelectKBest(f_classif, k=k),
            PolynomialFeatures(2, interaction_only=True, include_bias=False),
            LogisticRegression(max_iter=5000, C=0.05))
    if kind == "elastic":
        return make_pipeline(
            StandardScaler(), SelectKBest(f_classif, k=k),
            LogisticRegression(max_iter=5000, penalty="elasticnet", l1_ratio=0.5,
                               solver="saga", C=0.1))
    if kind == "balanced":
        return make_pipeline(
            StandardScaler(), SelectKBest(f_classif, k=k),
            LogisticRegression(max_iter=3000, C=0.1, class_weight="balanced"))
    C = {"base": 0.1, "c001": 0.01, "c1": 1.0}[kind]
    return make_pipeline(StandardScaler(), SelectKBest(f_classif, k=k),
                         LogisticRegression(max_iter=3000, C=C))


def main():
    lab, title = rf.ef.load_labels()
    print(f"라벨 {len(lab)}건 · 대상 {title}")
    print("피처 만드는 중...")
    df, rule = rf.build(lab)
    y = df["_y"].to_numpy()
    pid = df["_pid"].to_numpy()
    X = df.drop(columns=["_y", "_pid"])
    X = X.fillna(X.median())
    g0 = pd.factorize(pid)[0]
    print(f"표본 {len(df)} · 참가자 {df['_pid'].nunique()} · 피처 {X.shape[1]} "
          f"· 양성률 {y.mean():.1%}\n")

    #  ── 다른 라벨로도 학습해 두었다가 합친다 ──
    def labels_for(mode):
        neg = rf.ef.NEG_WIDE if mode == "wide" else rf.ef.NEG_NARROW
        pos = rf.ef.POS
        key = df[["_pid"]].copy()
        return None  # 아래에서 직접 만든다

    def nested(kind, target=None):
        yy = y if target is None else target
        o = np.full(len(df), np.nan)
        for tr, te in GroupKFold(5).split(X, yy, groups=g0):
            if len(np.unique(yy[tr])) < 2:
                continue
            gin = g0[tr]
            best_k, best_s = K_GRID[0], -1
            for k in K_GRID:
                oin = np.full(len(tr), np.nan)
                for a, b in GroupKFold(4).split(X.iloc[tr], yy[tr], groups=gin):
                    if len(np.unique(yy[tr][a])) < 2:
                        continue
                    m = make(kind, k)
                    m.fit(X.iloc[tr].iloc[a], yy[tr][a])
                    oin[b] = m.predict_proba(X.iloc[tr].iloc[b])[:, 1]
                kk = ~np.isnan(oin)
                if kk.sum() < 30 or len(np.unique(yy[tr][kk])) < 2:
                    continue
                s = roc_auc_score(yy[tr][kk], oin[kk])
                if s > best_s:
                    best_k, best_s = k, s
            m = make(kind, best_k)
            m.fit(X.iloc[tr], yy[tr])
            o[te] = m.predict_proba(X.iloc[te])[:, 1]
        return o

    rk = lambda v: pd.Series(v).rank(pct=True).to_numpy()
    CAND = {}
    CAND["기준 (배포본)"] = rk(nested("base"))
    for nm, kind in [("규제 강화 C=0.01", "c001"), ("규제 완화 C=1.0", "c1"),
                     ("ElasticNet", "elastic"), ("클래스 가중", "balanced"),
                     ("상호작용 항", "poly")]:
        print(f"  {nm} 도는 중...", flush=True)
        CAND[nm] = rk(nested(kind))

    def within_of(o, idx=None):
        pp = pid if idx is None else pid[idx]
        oo = o if idx is None else o[idx]
        yy = y if idx is None else y[idx]
        v = [roc_auc_score(yy[pp == p], oo[pp == p]) for p in np.unique(pp)
             if (pp == p).sum() >= 8 and len(np.unique(yy[pp == p])) > 1]
        return np.mean(v) if v else np.nan

    rng = np.random.default_rng(42)
    pids = np.unique(pid)
    bw = {k: [] for k in CAND}
    for _ in range(2000):
        smp = rng.choice(pids, len(pids), replace=True)
        idx = np.concatenate([np.where(pid == p)[0] for p in smp])
        if len(np.unique(y[idx])) < 2:
            continue
        for k, o in CAND.items():
            bw[k].append(within_of(o, idx))

    print(f"\n=== {title} · 배포본 대비 ===\n")
    print(f"  {'구성':18s} {'내부 AUC':>9} {'95%':>15}  {'배포본 대비':>10} {'95%':>17}")
    print(f"  {'-'*18} {'-'*9} {'-'*15}  {'-'*10} {'-'*17}")
    base = np.array(bw["기준 (배포본)"])
    for k, o in CAND.items():
        wl, wh = np.nanpercentile(bw[k], [2.5, 97.5])
        line = f"  {k:18s} {within_of(o):9.3f} {wl:.3f}~{wh:.3f}"
        if k != "기준 (배포본)":
            d = np.array(bw[k]) - base
            dl, dh = np.nanpercentile(d, [2.5, 97.5])
            sig = "✅" if dl > 0 else ("⛔" if dh < 0 else "  ")
            line += f"  {np.nanmean(d):+10.3f} [{dl:+.3f},{dh:+.3f}] {sig}"
        print(line)

    print("\n  ⚠ 후보를 여럿 재면 그중 하나는 우연히 좋아 보입니다."
          "\n    이긴 후보는 narrow·happy 에서도 같은 방향인지 확인한 뒤에 넣으세요.")


if __name__ == "__main__":
    main()
