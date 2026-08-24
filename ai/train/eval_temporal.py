# -*- coding: utf-8 -*-
r"""이미 쓰던 사용자를 예측한다 — 시간 분할. 2026.08.25

    .venv/Scripts/python.exe ai/train/eval_temporal.py [모드]

## 지금까지 잰 것은 다른 질문이었습니다

`GroupKFold(참가자)` 는 **「한 번도 본 적 없는 사람」**을 예측하는 문제를
잽니다. 그런데 우리 서비스는 그렇게 동작하지 않습니다.

    가입 → 14일 기준선 수집 → 그 다음부터 판정

**판정 시점에 우리는 그 사용자의 과거를 갖고 있습니다.** 그러면 평가도
그 조건이어야 합니다.

| 분할 | 재는 질문 | 우리 서비스 |
|---|---|---|
| 참가자 분할 | 처음 보는 사람을 맞히나 | 가입 직후에만 해당 |
| **시간 분할** | **쓰던 사람의 앞날을 맞히나** | **평소 동작** |

## 어떻게 나누나

참가자마다 시간순으로 정렬해 **앞 70% 로 배우고 뒤 30% 를 맞힙니다.**
전원의 앞부분을 모아 한 모델을 학습합니다.

    ⚠ 미래로 과거를 맞히지 않습니다. 각 사람의 학습 구간은 평가 구간보다
      전부 앞섭니다.

    ⚠ **참가자 분할 결과와 나란히 두면 안 됩니다.** 더 쉬운 문제입니다.
      쉬운 문제를 푼 것이 아니라, **우리가 실제로 푸는 문제**입니다.

## 대조군

같은 분할에서 **참가자 안 라벨 셔플**을 돌립니다. 사람마다의 기저율은
그대로 두고 시각-라벨 관계만 끊으므로, 「이 사람이 원래 부정적인가」로
얻는 점수는 대조군도 똑같이 얻습니다. **그 위로 올라가야 진짜입니다.**
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
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

MODE = sys.argv[1] if len(sys.argv) > 1 else "narrow"
spec = importlib.util.spec_from_file_location("ef", "ai/train/eval_final.py")
ef = importlib.util.module_from_spec(spec)
sys.argv = [sys.argv[0], MODE]
spec.loader.exec_module(ef)

K = 30
TRAIN_FRAC = 0.7


def main():
    lab, title = ef.load_labels()
    print(f"라벨 {len(lab)}건 · 참가자 {lab.pid.nunique()}")
    print("피처 만드는 중...")
    df = ef.build(lab)

    #  build 가 lab 순서대로 채택한 행만 돌려주므로 (참가자, 시각)으로 되맞춘다
    lab2 = lab.copy()
    lab2["hour"] = lab2.ts.dt.hour
    lab2["minute_of_day"] = lab2.ts.dt.hour * 60 + lab2.ts.dt.minute
    lab2 = lab2.rename(columns={"pid": "_pid", "y": "_y"})
    m = df.merge(lab2[["_pid", "_y", "hour", "minute_of_day", "ts"]],
                 on=["_pid", "_y", "hour", "minute_of_day"], how="left")
    m = m.drop_duplicates(subset=list(df.columns), keep="first")
    m = m[m.ts.notna()].sort_values(["_pid", "ts"]).reset_index(drop=True)

    y = m["_y"].to_numpy()
    pid = m["_pid"].to_numpy()
    X = m.drop(columns=["_y", "_pid", "ts"])
    print(f"표본 {len(m)} · 참가자 {m._pid.nunique()} · 피처 {X.shape[1]} "
          f"· 양성률 {y.mean():.1%}\n")

    #  ── 사람마다 앞 70% / 뒤 30% ──
    tr_mask = np.zeros(len(m), dtype=bool)
    for p in np.unique(pid):
        idx = np.where(pid == p)[0]          # 이미 시간순
        cut = max(1, int(len(idx) * TRAIN_FRAC))
        tr_mask[idx[:cut]] = True
    te_mask = ~tr_mask
    print(f"학습 {tr_mask.sum()} · 평가 {te_mask.sum()} "
          f"(평가 양성률 {y[te_mask].mean():.1%})\n")

    def fit_predict(labels):
        out = {}
        for kind in ("lr", "gb"):
            mdl = (make_pipeline(StandardScaler(), SelectKBest(f_classif, k=K),
                                 LogisticRegression(max_iter=3000, C=0.1))
                   if kind == "lr" else
                   make_pipeline(SelectKBest(f_classif, k=K),
                                 lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05,
                                                    num_leaves=31, min_child_samples=20,
                                                    subsample=0.8, colsample_bytree=0.8,
                                                    random_state=42, verbose=-1)))
            mdl.fit(X[tr_mask], labels[tr_mask])
            out[kind] = mdl.predict_proba(X[te_mask])[:, 1]
        r = (pd.Series(out["lr"]).rank(pct=True).to_numpy()
             + pd.Series(out["gb"]).rank(pct=True).to_numpy()) / 2
        return out["lr"], out["gb"], r

    yte, pte = y[te_mask], pid[te_mask]

    def within(o, labels):
        v = []
        for p in np.unique(pte):
            k = pte == p
            if k.sum() >= 6 and len(np.unique(labels[k])) > 1:
                v.append(roc_auc_score(labels[k], o[k]))
        return (np.mean(v) if v else np.nan), len(v)

    def boot_overall(o, n=2000):
        rng = np.random.default_rng(42)
        pids = np.unique(pte)
        out = []
        for _ in range(n):
            smp = rng.choice(pids, len(pids), replace=True)
            idx = np.concatenate([np.where(pte == p)[0] for p in smp])
            if len(np.unique(yte[idx])) < 2:
                continue
            out.append(roc_auc_score(yte[idx], o[idx]))
        return np.percentile(np.array(out), [2.5, 97.5])

    o_lr, o_gb, o_en = fit_predict(y)
    print(f"=== 시간 분할 (앞 70% 로 배우고 뒤 30% 예측) · {title} ===\n")
    print(f"  {'구성':22s} {'전체 AUC':>9} {'95%':>16}  {'참가자 내부':>10}")
    print(f"  {'-'*22} {'-'*9} {'-'*16}  {'-'*10}")
    for name, o in [("LogisticRegression", o_lr), ("LightGBM", o_gb),
                    ("앙상블(순위 평균)", o_en)]:
        a = roc_auc_score(yte, o)
        lo, hi = boot_overall(o)
        w, npart = within(o, yte)
        print(f"  {name:22s} {a:9.3f} {lo:.3f}~{hi:.3f}{'✅' if lo > .5 else '  '}  "
              f"{w:10.3f}")
    print(f"\n  (참가자 내부는 두 라벨이 다 있고 6건 이상인 {npart}명 평균)\n")

    #  ── 셔플 대조: 참가자 안에서만 섞는다 ──
    sh, shw = [], []
    for seed in range(10):
        rng = np.random.default_rng(seed)
        ys = y.copy()
        for p in np.unique(pid):
            k = pid == p
            v = ys[k]
            rng.shuffle(v)
            ys[k] = v
        _, _, e = fit_predict(ys)
        sh.append(roc_auc_score(ys[te_mask], e))
        shw.append(within(e, ys[te_mask])[0])
    sh, shw = np.array(sh), np.array(shw)
    real = roc_auc_score(yte, o_en)
    rw = within(o_en, yte)[0]
    print(f"  셔플 대조  전체 {real:.3f} vs {sh.mean():.3f}(최대 {sh.max():.3f}) "
          f"{'✅' if real > sh.max() else '⛔'}")
    print(f"            내부 {rw:.3f} vs {shw.mean():.3f}(최대 {shw.max():.3f}) "
          f"{'✅' if rw > shw.max() else '⛔'}")

    #  ── 운영 지점 ──
    base = yte.mean()
    order = np.argsort(-o_en)
    print(f"\n  === 상위 N% 만 알림 (기본 양성률 {base:.1%}) ===")
    print(f"  {'상위':>6} {'건수':>6} {'정밀도':>7} {'재현율':>7} {'향상':>6}")
    for pct in (5, 10, 20, 30):
        n = max(1, int(len(o_en) * pct / 100))
        sel = order[:n]
        prec = yte[sel].mean()
        print(f"  {pct:5d}% {n:6d} {prec:7.1%} {yte[sel].sum()/yte.sum():7.1%} "
              f"{prec/base:5.2f}배")


if __name__ == "__main__":
    main()
