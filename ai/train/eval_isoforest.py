# -*- coding: utf-8 -*-
r"""기업 브리프가 명시한 Isolation Forest 를 실제로 재본다. 2026.08.25

    .venv/Scripts/python.exe ai/train/eval_isoforest.py [모드]

## 왜 재는가

기업 과제 브리프(PROJECT_02 · 디지털 라이프로그 기반 정서 케어 서비스)의
「필요 기술 — AI 모델링」에 이렇게 적혀 있습니다.

> **이상탐지(Isolation Forest)**, 복합 위험 스코어링(LightGBM Ensemble),
> 시계열 특징 추출, (선택) 우울·정서 상태 분류 모델

우리는 이상탐지를 **중앙값·MAD 기반 robust z** 로 구현했습니다. 브리프가
「Isolation Forest **등**」이라 범위 안이지만, **이름이 박힌 방법을 안 재보고
「다른 걸 썼다」고만 말하면 방어가 안 됩니다.**

그래서 같은 조건에서 나란히 잽니다.

| 후보 | 무엇 |
|---|---|
| ① 현재 규칙 | 개인 기준선 이탈 z 의 상위 3개 평균 |
| ② **Isolation Forest (전역)** | 전체 참가자 데이터로 한 번 학습 |
| ③ **Isolation Forest (개인별)** | 참가자마다 그 사람의 과거로 학습 ← 브리프의 「개인 기저선」에 더 맞음 |
| ④ 배포본 (학습된 집계) | 지금 판정에 들어간 것 |

⚠ **Isolation Forest 는 비지도입니다.** 라벨을 안 보고 「드문 날」을 찾습니다.
  그래서 라벨 대비 성능이 낮아도 그 자체로 결함은 아닙니다 — 다만 **정서
  위험 스코어로 쓸 수 있느냐**가 질문이므로 같은 잣대로 잽니다.

⚠ 방향이 없습니다. 평소보다 **더 잘 잔** 날도 「드문 날」로 잡습니다.
  규칙이 방향을 보는 것과 다른 점이고, 결과를 읽을 때 감안해야 합니다.
"""
import importlib.util
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

MODE = sys.argv[1] if len(sys.argv) > 1 else "tense"
spec = importlib.util.spec_from_file_location("rf", "ai/train/eval_rule_features.py")
sys.argv = [sys.argv[0], MODE]
rf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rf)

K = 21
RAW_COLS = list(rf.RULE_FEATURES)          # (컬럼, 방향) 목록


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

    #  ── ② 전역 Isolation Forest ──
    #  ⚠ 라벨을 안 쓰므로 폴드 분할이 필요 없다. 다만 공정하게 하려고
    #    평가 참가자를 뺀 데이터로 학습한다(참가자 분할과 같은 조건).
    iso_global = np.full(len(df), np.nan)
    for tr, te in GroupKFold(5).split(X, y, groups=g0):
        m = IsolationForest(n_estimators=300, contamination=0.1, random_state=42)
        m.fit(X.iloc[tr])
        #  score_samples 는 정상일수록 높다 — 이상일수록 높게 뒤집는다
        iso_global[te] = -m.score_samples(X.iloc[te])

    #  ── ③ 개인별 Isolation Forest ──
    #  브리프의 「개인별 기저선」에 더 맞는 형태. 그 사람의 데이터만으로
    #  「이 사람에게 드문 날」을 찾는다.
    iso_person = np.full(len(df), np.nan)
    for p in np.unique(pid):
        m = pid == p
        if m.sum() < 20:
            continue
        mdl = IsolationForest(n_estimators=200, contamination=0.1, random_state=42)
        sub = X[m]
        mdl.fit(sub)
        iso_person[m] = -mdl.score_samples(sub)

    #  ── ④ 배포본 ──
    dep = np.full(len(df), np.nan)
    for tr, te in GroupKFold(5).split(X, y, groups=g0):
        if len(np.unique(y[tr])) < 2:
            continue
        mdl = make_pipeline(StandardScaler(), SelectKBest(f_classif, k=min(K, X.shape[1])),
                            LogisticRegression(max_iter=3000, C=0.1))
        mdl.fit(X.iloc[tr], y[tr])
        dep[te] = mdl.predict_proba(X.iloc[te])[:, 1]

    rk = lambda v: pd.Series(v).rank(pct=True).to_numpy()
    CAND = {
        "① 현재 규칙 (robust z)": rk(rule),
        "② Isolation Forest (전역)": rk(iso_global),
        "③ Isolation Forest (개인별)": rk(np.nan_to_num(iso_person, nan=0.5)),
        "④ 배포본 (학습된 집계)": rk(dep),
    }

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

    print(f"=== {title} · 기업 브리프가 명시한 방법과 나란히 ===\n")
    print(f"  {'구성':28s} {'참가자 내부 AUC':>14} {'95%':>15}")
    print(f"  {'-'*28} {'-'*14} {'-'*15}")
    for k, o in CAND.items():
        lo, hi = np.nanpercentile(bw[k], [2.5, 97.5])
        print(f"  {k:28s} {within_of(o):14.3f} {lo:.3f}~{hi:.3f}")

    print("\n  === 현재 규칙 대비 (같은 리샘플에서의 차) ===\n")
    base = np.array(bw["① 현재 규칙 (robust z)"])
    for k in CAND:
        if k.startswith("①"):
            continue
        d = np.array(bw[k]) - base
        lo, hi = np.nanpercentile(d, [2.5, 97.5])
        sig = "✅" if lo > 0 else ("⛔" if hi < 0 else "  ")
        print(f"  {k:28s} {np.nanmean(d):+.3f} [{lo:+.3f},{hi:+.3f}] {sig}")


if __name__ == "__main__":
    main()
