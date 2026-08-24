# -*- coding: utf-8 -*-
r"""피처를 늘리면 왜 나빠지는가 — 절제(ablation)와 폴드 안 피처 선택. 2026.08.25

    .venv/Scripts/python.exe ai/train/eval_ablation.py [모드]

## 왜 만들었나

같은 라벨·같은 분할인데 피처를 늘릴수록 성능이 내려갔습니다.

    시간 CSV 만 (50개)                0.569  ✅
    + 분 단위 심박·생체 (95개)         0.551
    분 단위만 (59개, 리듬 제외)        0.519  ⛔

**「좋은 재료를 다 넣으면 다 좋아진다」가 아닙니다.** 참가자가 60명뿐이라
피처가 늘면 얻는 신호보다 늘어나는 분산이 큽니다. 추측하지 않고 재봅니다.

## 두 가지를 잽니다

**① 절제** — 피처군을 하나씩 넣어 어디서 꺾이는지 봅니다.

**② 폴드 안 피처 선택** — 학습 폴드에서만 상위 K개를 골라 평가 폴드에
적용합니다.

> ⚠ **선택을 폴드 밖에서 하면 안 됩니다.** 전체 데이터로 고른 피처는 평가
> 폴드의 정답을 이미 본 것이라, AUC 가 실제보다 크게 부풀려집니다.
> 흔한 실수이고, 여기서는 `SelectKBest` 를 `Pipeline` 안에 넣어 막습니다.
"""
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

sys.path.insert(0, "ai/train")
import importlib.util

spec = importlib.util.spec_from_file_location("ef", "ai/train/eval_final.py")
ef = importlib.util.module_from_spec(spec)
sys.argv = [sys.argv[0], sys.argv[1] if len(sys.argv) > 1 else "narrow"]
spec.loader.exec_module(ef)

#  피처군 — 이름 앞머리로 가른다
GROUPS = {
    "리듬(r_*)": lambda c: c.startswith("r_"),
    "같은시간대(steps/bpm/calories)": lambda c: c.split("_")[0] in
        ("steps", "bpm", "calories"),
    "분단위 심박(hr*)": lambda c: c.startswith("hr"),
    "일단위 생체": lambda c: c.split("_")[0] in
        ("rmssd", "lfhf", "STRESS", "SLEEP", "RESPONSIVENESS", "EXERTION",
         "br", "asleep", "awake", "tofall", "eff", "temp"),
    "시각": lambda c: c in ("hour", "minute_of_day"),
}


def main():
    lab, title = ef.load_labels()
    print(f"라벨 {len(lab)}건 · 참가자 {lab.pid.nunique()}")
    print("피처 만드는 중...")
    df = ef.build(lab)
    y = df["_y"].to_numpy()
    Xall = df.drop(columns=["_y", "_pid"])
    pid = df["_pid"].to_numpy()
    g0 = pd.factorize(pid)[0]
    print(f"표본 {len(df)} · 참가자 {df._pid.nunique()} · 피처 {Xall.shape[1]}\n")

    cols = list(Xall.columns)
    assigned = set()
    gcols = {}
    for name, pred in GROUPS.items():
        gcols[name] = [c for c in cols if pred(c) and c not in assigned]
        assigned |= set(gcols[name])
    rest = [c for c in cols if c not in assigned]
    if rest:
        gcols["기타"] = rest
    for name, cs in gcols.items():
        print(f"  {name:32s} {len(cs):3d}개")
    print()

    def run(X, k=None, n=1000):
        steps = [StandardScaler()]
        if k is not None and k < X.shape[1]:
            steps.append(SelectKBest(f_classif, k=k))
        steps.append(LogisticRegression(max_iter=3000, C=0.1))
        o = np.full(len(df), np.nan)
        for tr, te in GroupKFold(5).split(X, y, groups=g0):
            if len(np.unique(y[tr])) < 2:
                continue
            #  ⚠ 선택기가 파이프라인 안에 있어야 학습 폴드만 보고 고른다
            m = make_pipeline(*steps)
            m.fit(X.iloc[tr], y[tr])
            o[te] = m.predict_proba(X.iloc[te])[:, 1]
        ok = ~np.isnan(o)
        rng = np.random.default_rng(42)
        pids = np.unique(pid)
        out = []
        for _ in range(n):
            smp = rng.choice(pids, len(pids), replace=True)
            idx = np.concatenate([np.where(pid == p)[0] for p in smp])
            idx = idx[ok[idx]]
            if len(np.unique(y[idx])) < 2:
                continue
            out.append(roc_auc_score(y[idx], o[idx]))
        a = np.array(out)
        return roc_auc_score(y[ok], o[ok]), *np.percentile(a, [2.5, 97.5])

    print(f"=== ① 절제 · {title} ===\n")
    print(f"  {'구성':38s} {'개수':>4} {'AUC':>7}  {'95%':>16}")
    print(f"  {'-'*38} {'-'*4} {'-'*7}  {'-'*16}")
    order = ["리듬(r_*)", "같은시간대(steps/bpm/calories)", "시각",
             "분단위 심박(hr*)", "일단위 생체"]
    acc = []
    for name in order:
        cs = gcols.get(name, [])
        if not cs:
            continue
        acc += cs
        auc, lo, hi = run(Xall[acc])
        mark = " ✅" if lo > 0.5 else ""
        print(f"  +{name:37s} {len(acc):4d} {auc:7.3f}  {lo:.3f}~{hi:.3f}{mark}")

    print(f"\n=== ② 폴드 안 상위 K개만 (전체 {Xall.shape[1]}개에서) ===\n")
    print(f"  {'K':>5} {'AUC':>7}  {'95%':>16}")
    print(f"  {'-'*5} {'-'*7}  {'-'*16}")
    best = None
    for k in [5, 10, 15, 20, 30, 50, Xall.shape[1]]:
        auc, lo, hi = run(Xall, k=k)
        mark = " ✅" if lo > 0.5 else ""
        print(f"  {k:5d} {auc:7.3f}  {lo:.3f}~{hi:.3f}{mark}")
        if best is None or auc > best[1]:
            best = (k, auc, lo, hi)
    print(f"\n  최고 K={best[0]} · AUC {best[1]:.3f} · 95% {best[2]:.3f}~{best[3]:.3f}")


if __name__ == "__main__":
    main()
