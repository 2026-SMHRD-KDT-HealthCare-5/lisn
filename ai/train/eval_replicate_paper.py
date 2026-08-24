# -*- coding: utf-8 -*-
r"""70% 논문을 그대로 재현한다 — 지표와 분할을 바로잡아서. 2026.08.25

    .venv/Scripts/python.exe ai/train/eval_replicate_paper.py

## 무엇을 재현하나

Karim HT, Matin A, Goel M (2025) *Passive sensing with psyche: utilizing
data from wearable technology to predict emotion states*,
medRxiv 2025.02.13.25322254.

**우리와 같은 데이터셋(LifeSnaps)** 을 쓰고 **같은 문제**를 풉니다.

    38명 · 약 1200일 · 3분류
      happy 276일 · sad/tense/anxious 313일 · neither 578일
    multinomial elastic net (eNetXplorer) · 5-fold CV · 250회 순열검정
    → **약 70%, p<0.001**

표본이 정확히 재현됩니다 — **1167일 · 38명 · 276/313/578**.
논문이 지목한 피처 12종도 그대로 씁니다.

## 확인한 것 두 가지

### ① 「70%」의 지표는 전체 정확도가 아닙니다

eNetXplorer 의 multinomial 기본 품질함수는 **average accuracy**
(클래스별로 따로 채점해 평균)입니다. 이 지표는 **소수 클래스가 있으면
아무것도 학습하지 않아도 값이 높습니다.**

    happy             276/1167 → 전부 '아니다' 로 찍으면 76.3%
    sad/tense/anxious 313/1167 → 〃                    73.2%
    neither           578/1167 → 〃                    50.5%
    ─────────────────────────────────────────────────────────
    평균                                              66.7%   ← 기준선

**논문 70% − 기준선 66.7% = +3.3%p** 입니다.

### ② 방법 절에 참가자 단위 분할이 없습니다

전문(medRxiv source XML)을 받아 찾아봤습니다 —
`leave-one-subject-out` · `grouped` · `between-subject` **전부 0건**,
그냥 「5-fold cross-validation」입니다. 무작위 5겹이면 **같은 사람의 다른
날이 학습과 평가 양쪽에** 들어갑니다.

## 그래서 다른 것은 다 같게 두고 분할만 바꿉니다

    ① 무작위 5겹        논문과 같은 조건
    ② 참가자 5겹        같은 사람은 한쪽에만 — 우리 서비스 조건
    ③ 참가자 셔플 대조   참가자 안에서 라벨을 섞음.
                       「이 사람이 원래 어떤 사람인가」로 얻는 몫의 상한

> ⚠ **논문을 깎으려는 것이 아닙니다.** 논문은 스스로를
> 「proof-of-concept」라 부르고, 지표를 명시했으며, 순열검정으로 p 값도
> 냈습니다. 우리가 알고 싶은 것은 **그 숫자가 처음 보는 사용자에게도
> 나오는가**입니다. 우리 서비스는 새 사용자에게 판정을 내려야 합니다.
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold, StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

DAILY = Path("ai/data_raw/lifesnaps/rais_anonymized/csv_rais_anonymized/"
             "daily_fitbit_sema_df_unprocessed.csv")

#  논문 표 1 이 지목한 피처 그대로
FEATURES = ["steps", "distance", "moderately_active_minutes",
            "nightly_temperature", "very_active_minutes", "nremhr", "rmssd",
            "sedentary_minutes", "resting_hr", "minutesAwake",
            "lightly_active_minutes", "sleep_efficiency"]

N_REPEAT = 20
N_CLASS = 3


def load():
    d = pd.read_csv(DAILY).rename(columns={"id": "pid"})
    keep = ["pid", "date", "HAPPY", "SAD", "TENSE/ANXIOUS"] + FEATURES
    d = d[[c for c in keep if c in d.columns]].copy()

    #  ── 논문과 같은 3분류 ──
    d = d[d[["HAPPY", "SAD", "TENSE/ANXIOUS"]].notna().any(axis=1)].copy()
    happy = d.HAPPY.fillna(0) > 0
    bad = (d.SAD.fillna(0) > 0) | (d["TENSE/ANXIOUS"].fillna(0) > 0)
    d["_y"] = np.where(bad, 1, np.where(happy, 0, 2))   # 0 happy · 1 bad · 2 neither

    #  논문은 "totally complete data" 인 참가자만 썼다
    return d.dropna(subset=[c for c in FEATURES if c in d.columns])


def avg_class_acc(y_true, y_pred):
    """eNetXplorer multinomial 의 기본 지표 — 클래스별 평균 정확도.

    ⚠ **전체 정확도가 아닙니다.** 클래스마다 「그 클래스인가 아닌가」를
      따로 채점해 평균 냅니다. 소수 클래스가 있으면 **아무것도 학습하지
      않아도** 값이 높게 나옵니다.
    """
    return float(np.mean([((y_true == k) == (y_pred == k)).mean()
                          for k in range(N_CLASS)]))


def chance_level(y):
    """전부 「아니다」로만 찍었을 때의 클래스별 평균 정확도."""
    n = np.bincount(y, minlength=N_CLASS)
    return float(np.mean([1 - n[k] / len(y) for k in range(N_CLASS)]))


def main():
    d = load()
    X = d[[c for c in FEATURES if c in d.columns]].astype(float)
    y = d["_y"].to_numpy()
    g0 = pd.factorize(d.pid.astype(str))[0]
    n = np.bincount(y, minlength=N_CLASS)
    base = chance_level(y)

    print(f"표본 {len(d)}일 · 참가자 {d.pid.nunique()}명 · 피처 {X.shape[1]}")
    print(f"  happy {n[0]} · sad/tense/anxious {n[1]} · neither {n[2]}")
    print("  (논문: 38명 · 약 1200일 · 276 / 313 / 578 — 정확히 일치)")
    print(f"\n  전체 정확도로 다수 클래스만 찍으면 {n.max() / len(d):.1%}")
    print(f"  클래스별 평균 정확도(논문 지표)의 기준선 {base:.1%}\n")

    def model():
        #  논문의 최적값이 α=0(=ridge) 이라 L2 로 맞춘다
        return make_pipeline(StandardScaler(),
                             LogisticRegression(max_iter=5000, C=0.02))

    def shuffled_groups(rng):
        perm = rng.permutation(np.unique(g0))
        remap = {p: i for i, p in enumerate(perm)}
        return np.array([remap[v] for v in g0])

    def score(splits, labels):
        acc = []
        for tr, te in splits:
            if len(np.unique(labels[tr])) < 2:
                continue
            m = model().fit(X.iloc[tr], labels[tr])
            acc.append(avg_class_acc(labels[te], m.predict(X.iloc[te])))
        return float(np.mean(acc))

    def run(kind, seed):
        rng = np.random.default_rng(seed)
        if kind == "random":
            return score(StratifiedKFold(5, shuffle=True,
                                         random_state=seed).split(X, y), y)
        if kind == "group":
            gg = shuffled_groups(rng)
            return score(GroupKFold(5).split(X, y, groups=gg), y)
        #  참가자 안에서만 라벨을 섞는다 — 사람별 구성은 그대로 남는다
        ys = y.copy()
        for p in np.unique(g0):
            m = g0 == p
            v = ys[m]
            rng.shuffle(v)
            ys[m] = v
        gg = shuffled_groups(rng)
        return score(GroupKFold(5).split(X, ys, groups=gg), ys)

    print("=== 다른 것은 다 같게 두고 분할 방식만 바꿉니다 ===\n")
    print(f"  {'분할':32s} {'지표값':>8} {'95%':>16}")
    print(f"  {'-' * 32} {'-' * 8} {'-' * 16}")
    res = {}
    for kind, name in [("random", "① 무작위 5겹 (논문과 같은 조건)"),
                       ("group", "② 참가자 5겹 (새 사용자)"),
                       ("shuffle", "③ 참가자 셔플 대조")]:
        v = np.array([run(kind, s) for s in range(N_REPEAT)])
        res[kind] = v
        lo, hi = np.percentile(v, [2.5, 97.5])
        print(f"  {name:32s} {v.mean():8.1%} {lo:.1%}~{hi:.1%}")
    print(f"  {'아무것도 학습 안 함 (기준선)':32s} {base:8.1%}")
    print(f"  {'논문 보고치':32s} {0.700:8.1%}")

    print(f"\n  논문 70%  − 기준선 = {0.70 - base:+.1%}")
    print(f"  ① 무작위  − 기준선 = {res['random'].mean() - base:+.1%}")
    print(f"  ② 참가자  − 기준선 = {res['group'].mean() - base:+.1%}"
          "   <- 새 사용자에게 남는 몫")
    print(f"  ③ 셔플 대조        = {res['shuffle'].mean():.1%}"
          "   (② 가 이보다 높아야 진짜 신호)")

    print("\n  ⚠ 논문이 틀렸다는 뜻이 아닙니다. 지표를 명시했고 순열검정으로")
    print("    p<0.001 을 얻었습니다. 다만 「70% 정확도」로 읽으면 오해입니다 —")
    print("    그 지표는 아무것도 학습하지 않아도 66.7% 입니다.")
    if res["group"].mean() <= res["shuffle"].mean() + 0.005:
        print("\n  -> 참가자 분할에서는 셔플 대조와 구분되지 않습니다.")
        print("     처음 보는 사용자의 그날 기분을 라이프로그로 맞히는 것은")
        print("     이 데이터에서 되지 않습니다.")


if __name__ == "__main__":
    main()
