# -*- coding: utf-8 -*-
r"""과거 정서 이력을 넣는다 + 참가자 내부로 잰다 — 2026.08.25

    .venv/Scripts/python.exe ai/train/eval_context.py [모드]
      모드: narrow(기본) | wide | happy | tense

## ① 아직 한 번도 안 넣은 것 — 과거 정서 이력

지금까지 **센서만** 넣었습니다. 그런데 우리 서비스는 **대화 이력과 과거
감정 분석 결과를 실제로 갖고 있습니다.** 안 쓸 이유가 없습니다.

    prev_neg        직전 응답이 부정이었나
    prev2_neg       그 앞은
    hours_since     직전 응답으로부터 몇 시간 지났나
    run_neg_rate    지금까지의 부정 비율 (이 사람 기준)
    run_n           지금까지 응답 수

> ⚠ **전부 「그 시점 이전」만 씁니다.** 미래 응답은 쓰지 않습니다.
> 시계열 예측에서 과거 정답을 입력으로 쓰는 것은 정상이지만,
> **센서만으로 얼마나 되는지를 따로 보고**해야 합니다 — 안 그러면
> 「센서가 잡았다」와 「기분은 원래 이어진다」를 구분할 수 없습니다.

## ② 재는 방식도 바꿉니다 — 참가자 내부 AUC

전체 AUC 는 **사람 사이 차이**에 좌우됩니다. 늘 우울한 사람과 늘 밝은
사람을 가르기만 해도 점수가 오릅니다. 그런데 우리 서비스가 하는 일은
그게 아닙니다.

> **「이 사람의 나쁜 순간을 이 사람의 좋은 순간보다 위로 올리는가」**

참가자별로 AUC 를 따로 내고 평균합니다(두 라벨이 다 있는 사람만).
이것이 개인 기준선 이탈 탐지의 목표와 정확히 같은 질문입니다.
"""
import sys
import warnings
import importlib.util

import numpy as np
import pandas as pd
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb

warnings.filterwarnings("ignore")

MODE = sys.argv[1] if len(sys.argv) > 1 else "narrow"
spec = importlib.util.spec_from_file_location("ef", "ai/train/eval_final.py")
ef = importlib.util.module_from_spec(spec)
sys.argv = [sys.argv[0], MODE]
spec.loader.exec_module(ef)

K = 30
HIST = ["prev_neg", "prev2_neg", "hours_since", "run_neg_rate", "run_n"]


def main():
    lab, title = ef.load_labels()
    print(f"라벨 {len(lab)}건 · 참가자 {lab.pid.nunique()} · 양성률 {lab.y.mean():.1%}")
    print("피처 만드는 중...")

    #  build 는 lab 행 순서대로 채택된 것만 돌려준다. 어떤 라벨이 살아남았는지
    #  알아야 이력을 붙일 수 있어, ts 를 같이 실어 보낸다.
    df = ef.build(lab)
    #  build 안에서 걸러진 행을 되찾기 위해 같은 조건을 다시 계산하지 않고,
    #  (pid, y, hour, minute_of_day) 조합으로 lab 과 맞춘다.
    lab2 = lab.copy()
    lab2["hour"] = lab2.ts.dt.hour
    lab2["minute_of_day"] = lab2.ts.dt.hour * 60 + lab2.ts.dt.minute
    lab2 = lab2.rename(columns={"pid": "_pid", "y": "_y"})
    merged = df.merge(lab2[["_pid", "_y", "hour", "minute_of_day", "ts", "mood"]],
                      on=["_pid", "_y", "hour", "minute_of_day"], how="left")
    merged = merged.drop_duplicates(subset=[c for c in df.columns], keep="first")
    if len(merged) != len(df) or merged.ts.isna().any():
        #  드물게 같은 분에 같은 라벨이 겹치면 못 맞춘다 — 그런 행만 버린다
        merged = merged[merged.ts.notna()].reset_index(drop=True)
    print(f"  표본 {len(merged)} (ts 매칭 후)")

    #  ── 과거 정서 이력: 참가자별 시간순, 그 시점 이전만 ──
    merged = merged.sort_values(["_pid", "ts"]).reset_index(drop=True)
    tsv_all = merged["ts"].to_numpy()
    pid_all = merged["_pid"].to_numpy()

    def history(labels):
        """주어진 라벨로 이력 피처를 만든다.

        ⚠ **셔플 대조에서도 반드시 다시 계산해야 합니다.** 참 라벨로 만든
          이력을 그대로 두고 목표만 섞으면, 대조군이 여전히 참 라벨의
          구조를 들고 있어 비교가 성립하지 않습니다.
        """
        h = {c: np.full(len(labels), np.nan) for c in HIST}
        for p in np.unique(pid_all):
            idx = np.where(pid_all == p)[0]
            ys, ts = labels[idx], tsv_all[idx]
            run = 0
            for i in range(len(idx)):
                j = idx[i]
                h["run_n"][j] = i
                if i > 0:
                    h["prev_neg"][j] = ys[i - 1]
                    h["hours_since"][j] = (ts[i] - ts[i - 1]) / np.timedelta64(1, "h")
                    h["run_neg_rate"][j] = run / i
                if i > 1:
                    h["prev2_neg"][j] = ys[i - 2]
                run += ys[i]
        return pd.DataFrame(h, index=merged.index)

    y = merged["_y"].to_numpy()
    pid = merged["_pid"].to_numpy()
    g0 = pd.factorize(pid)[0]
    sensor_cols = [c for c in df.columns if not c.startswith("_")]
    X_sensor = merged[sensor_cols].fillna(0)
    X_full = pd.concat([merged[sensor_cols], history(y)], axis=1).fillna(0)
    print(f"  센서 {len(sensor_cols)}개 · 이력 {len(HIST)}개 · 양성률 {y.mean():.1%}\n")

    def oof(X, kind, labels=None):
        yy = y if labels is None else labels
        o = np.full(len(X), np.nan)
        for tr, te in GroupKFold(5).split(X, yy, groups=g0):
            if len(np.unique(yy[tr])) < 2:
                continue
            k = min(K, X.shape[1])
            m = (make_pipeline(StandardScaler(), SelectKBest(f_classif, k=k),
                               LogisticRegression(max_iter=3000, C=0.1))
                 if kind == "lr" else
                 make_pipeline(SelectKBest(f_classif, k=k),
                               lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05,
                                                  num_leaves=31, min_child_samples=20,
                                                  subsample=0.8, colsample_bytree=0.8,
                                                  random_state=42, verbose=-1)))
            m.fit(X.iloc[tr], yy[tr])
            o[te] = m.predict_proba(X.iloc[te])[:, 1]
        return o

    def rank(o):
        return pd.Series(o).rank(pct=True).to_numpy()

    def boot(o, n=2000):
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

    def within(o, n=2000):
        """참가자 내부 AUC — 이 사람의 나쁜 순간이 좋은 순간보다 위인가."""
        ok = ~np.isnan(o)
        per = {}
        for p in np.unique(pid):
            m = (pid == p) & ok
            if m.sum() < 8 or len(np.unique(y[m])) < 2:
                continue
            per[p] = roc_auc_score(y[m], o[m])
        v = np.array(list(per.values()))
        rng = np.random.default_rng(42)
        bs = [rng.choice(v, len(v), replace=True).mean() for _ in range(n)]
        return v.mean(), *np.percentile(bs, [2.5, 97.5]), len(v)

    print(f"=== {title} ===\n")
    print(f"  {'입력':16s} {'전체 AUC':>9} {'95%':>16}   "
          f"{'참가자 내부':>10} {'95%':>16}")
    print(f"  {'-'*16} {'-'*9} {'-'*16}   {'-'*10} {'-'*16}")
    res = {}
    for name, X in [("센서만", X_sensor), ("센서+정서이력", X_full)]:
        o = (rank(oof(X, "lr")) + rank(oof(X, "gb"))) / 2
        res[name] = o
        a, lo, hi = boot(o)
        w, wlo, whi, npart = within(o)
        print(f"  {name:16s} {a:9.3f} {lo:.3f}~{hi:.3f}{'✅' if lo > .5 else '  '}   "
              f"{w:10.3f} {wlo:.3f}~{whi:.3f}{'✅' if wlo > .5 else '  '}")
    print(f"\n  (참가자 내부는 두 라벨이 다 있고 8건 이상인 {npart}명 평균)")

    #  ── 셔플 대조 ──
    for name, use_hist in [("센서만", False), ("센서+정서이력", True)]:
        sh, shw = [], []
        for seed in range(10):
            rng = np.random.default_rng(seed)
            ys = y.copy()
            for p in np.unique(pid):
                mk = pid == p
                v = ys[mk]
                rng.shuffle(v)
                ys[mk] = v
            #  ⚠ 이력도 섞인 라벨로 다시 만든다
            Xs = (pd.concat([merged[sensor_cols], history(ys)], axis=1).fillna(0)
                  if use_hist else X_sensor)
            e = (rank(oof(Xs, "lr", ys)) + rank(oof(Xs, "gb", ys))) / 2
            k = ~np.isnan(e)
            sh.append(roc_auc_score(ys[k], e[k]))
            per = []
            for p in np.unique(pid):
                m = (pid == p) & k
                if m.sum() >= 8 and len(np.unique(ys[m])) > 1:
                    per.append(roc_auc_score(ys[m], e[m]))
            shw.append(np.mean(per))
        sh, shw = np.array(sh), np.array(shw)
        o = res[name]
        ok2 = ~np.isnan(o)
        real = roc_auc_score(y[ok2], o[ok2])
        rw = within(o)[0]
        print(f"  셔플 {name:12s} 전체 {real:.3f} vs {sh.mean():.3f}(최대 {sh.max():.3f})"
              f" {'✅' if real > sh.max() else '⛔'}"
              f"   내부 {rw:.3f} vs {shw.mean():.3f}(최대 {shw.max():.3f})"
              f" {'✅' if rw > shw.max() else '⛔'}")

    #  ── 운영 지점: 상위 N% 만 알림한다면 ──
    o = res["센서만"]      # 서비스가 실제로 쓸 조건
    ok = ~np.isnan(o)
    print(f"\n  === 상위 N% 만 알림했을 때 (기본 양성률 {y[ok].mean():.1%}) ===")
    print(f"  {'상위':>6} {'건수':>6} {'정밀도':>7} {'재현율':>7} {'향상':>6}")
    base = y[ok].mean()
    ov, yv = o[ok], y[ok]
    order = np.argsort(-ov)
    for pct in (5, 10, 20, 30):
        n = max(1, int(len(ov) * pct / 100))
        sel = order[:n]
        prec = yv[sel].mean()
        rec = yv[sel].sum() / yv.sum()
        print(f"  {pct:5d}% {n:6d} {prec:7.1%} {rec:7.1%} {prec/base:5.2f}배")


if __name__ == "__main__":
    main()
