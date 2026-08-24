# -*- coding: utf-8 -*-
r"""무엇으로 학습해야 하나 — 배포본의 학습 대상을 고른다. 2026.08.25

    .venv/Scripts/python.exe ai/train/eval_target_choice.py

## 아직 안 물어본 질문

판정에 넣은 모델은 **`TENSE/ANXIOUS` 로 학습**했습니다. 그런데 우리 판정이
찾아야 하는 것은 불안 하나가 아니라 **부정 상태 전반**입니다.

**대상이 다른 모델끼리는 AUC 를 나란히 못 놓습니다.** 그래서 이렇게 잽니다.

> **평가는 하나로 고정하고**(부정 정서 = 불안·슬픔·분노·공포),
> **학습 대상만 바꿔** 어느 쪽이 그 평가에서 더 잘 줄 세우는지 본다.

| 후보 | 학습 대상 |
|---|---|
| ① 지금 배포본 | `TENSE/ANXIOUS` |
| ② 부정 정서 | 불안·슬픔·분노·공포 (평가와 같은 라벨) |
| ③ 둘 다 (순위 평균) | 두 모델을 합침 |

⚠ **②가 유리해 보이는 것이 당연해 보이지만 그렇지 않습니다.** 부정 정서는
  양성률 25% 로 표본이 넉넉한 대신 **서로 다른 감정이 섞여** 신호가 흐려질
  수 있습니다. 실제로 시도 16 에서 `TIRED` 를 섞자 신호가 죽었습니다.

⚠ 평가 라벨(부정 정서)로 **학습 대상을 고르는 것 자체**가 그 라벨을 보는
  일입니다. 그래서 판정은 **참가자 분할 + 중첩 교차검증**으로 하고,
  차이의 95% 하한이 0 을 넘을 때만 바꿉니다.
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
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

sys.argv = [sys.argv[0], "narrow"]      # 피처 빌더는 라벨과 무관하다
spec = importlib.util.spec_from_file_location("rf", "ai/train/eval_rule_features.py")
rf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rf)

K_GRID = [8, 12, 21]
NEG_NARROW = rf.ef.NEG_NARROW
POS = rf.ef.POS
NEG_WIDE = rf.ef.NEG_WIDE


def main():
    #  ── 평가 라벨(부정 정서)과 학습 후보 라벨을 같은 표본 위에 올린다 ──
    docs_lab, _ = rf.ef.load_labels()          # narrow 로 이미 걸러진 것
    #  원본 mood 가 필요하므로 다시 읽는다
    import bson
    import zipfile
    docs = bson.decode_all(zipfile.ZipFile(rf.ef.ZIP).read(
        "rais_anonymized/mongo_rais_anonymized/sema.bson"))
    lab = pd.DataFrame([{"pid": str(d["user_id"]),
                         "ts": d["data"].get("COMPLETED_TS"),
                         "mood": d["data"].get("MOOD")} for d in docs])
    lab["ts"] = pd.to_datetime(lab["ts"], errors="coerce")
    lab = lab.dropna(subset=["ts"])
    lab = lab[lab.mood.isin(NEG_NARROW | POS)].copy()
    lab["y"] = lab.mood.isin(NEG_NARROW).astype(int)          # 평가 라벨
    lab["y_tense"] = (lab.mood == "TENSE/ANXIOUS").astype(int)  # 학습 후보
    lab = lab.drop_duplicates(subset=["pid", "ts"]).sort_values(["pid", "ts"])
    print(f"표본 후보 {len(lab)} · 참가자 {lab.pid.nunique()} "
          f"· 부정 {lab.y.mean():.1%} · 불안 {lab.y_tense.mean():.1%}")

    print("피처 만드는 중...")
    df, _ = rf.build(lab)
    #  build 가 채택한 행에 학습 후보 라벨을 되붙인다
    lab2 = lab.rename(columns={"pid": "_pid", "y": "_y"})
    lab2["hour"] = lab2.ts.dt.hour
    m = df.merge(lab2[["_pid", "_y", "y_tense", "ts"]].assign(
        _k=lab2.ts.dt.hour * 60 + lab2.ts.dt.minute), how="left",
        left_on=["_pid", "_y"], right_on=["_pid", "_y"])
    #  위 merge 는 중복이 생긴다 — 순서가 보존되므로 위치로 붙이는 편이 안전하다
    y_eval = df["_y"].to_numpy()
    #  build 는 lab 행 순서대로 채택하므로, 채택된 순서대로 y_tense 를 맞춘다
    kept = []
    it = iter(lab.itertuples())
    #  ⚠ build 와 같은 조건으로 다시 걸러야 순서가 맞는다. 대신 (pid, y) 쌍이
    #    같은 순서로 나온다는 성질을 이용해 앞에서부터 대응시킨다.
    tense_seq = []
    pos = 0
    rows_pid = df["_pid"].to_numpy()
    for r in lab.itertuples():
        if pos >= len(df):
            break
        if r.pid == rows_pid[pos] and int(r.y) == int(y_eval[pos]):
            tense_seq.append(int(r.y_tense))
            pos += 1
    if len(tense_seq) != len(df):
        raise SystemExit(f"라벨 대응 실패 {len(tense_seq)} != {len(df)}")

    y_tense = np.array(tense_seq)
    pid = df["_pid"].to_numpy()
    X = df.drop(columns=["_y", "_pid"])
    X = X.fillna(X.median())
    g0 = pd.factorize(pid)[0]
    print(f"표본 {len(df)} · 참가자 {df['_pid'].nunique()} · 피처 {X.shape[1]} "
          f"· 평가 양성률 {y_eval.mean():.1%} · 불안 양성률 {y_tense.mean():.1%}\n")

    def nested(train_y):
        o = np.full(len(df), np.nan)
        for tr, te in GroupKFold(5).split(X, train_y, groups=g0):
            if len(np.unique(train_y[tr])) < 2:
                continue
            gin = g0[tr]
            best_k, best_s = K_GRID[0], -1
            for k in K_GRID:
                oin = np.full(len(tr), np.nan)
                for a, b in GroupKFold(4).split(X.iloc[tr], train_y[tr], groups=gin):
                    if len(np.unique(train_y[tr][a])) < 2:
                        continue
                    mm = make_pipeline(StandardScaler(), SelectKBest(f_classif, k=k),
                                       LogisticRegression(max_iter=3000, C=0.1))
                    mm.fit(X.iloc[tr].iloc[a], train_y[tr][a])
                    oin[b] = mm.predict_proba(X.iloc[tr].iloc[b])[:, 1]
                kk = ~np.isnan(oin)
                if kk.sum() < 30 or len(np.unique(train_y[tr][kk])) < 2:
                    continue
                s = roc_auc_score(train_y[tr][kk], oin[kk])
                if s > best_s:
                    best_k, best_s = k, s
            mm = make_pipeline(StandardScaler(), SelectKBest(f_classif, k=best_k),
                               LogisticRegression(max_iter=3000, C=0.1))
            mm.fit(X.iloc[tr], train_y[tr])
            o[te] = mm.predict_proba(X.iloc[te])[:, 1]
        return pd.Series(o).rank(pct=True).to_numpy()

    o_tense = nested(y_tense)
    o_neg = nested(y_eval)
    CAND = {
        "① 배포본 (불안으로 학습)": o_tense,
        "② 부정 정서로 학습": o_neg,
        "③ 둘 다 (순위 평균)": (o_tense + o_neg) / 2,
    }

    def within_of(o, idx=None):
        pp = pid if idx is None else pid[idx]
        oo = o if idx is None else o[idx]
        yy = y_eval if idx is None else y_eval[idx]
        v = [roc_auc_score(yy[pp == p], oo[pp == p]) for p in np.unique(pp)
             if (pp == p).sum() >= 8 and len(np.unique(yy[pp == p])) > 1]
        return np.mean(v) if v else np.nan

    rng = np.random.default_rng(42)
    pids = np.unique(pid)
    bw = {k: [] for k in CAND}
    for _ in range(2000):
        smp = rng.choice(pids, len(pids), replace=True)
        idx = np.concatenate([np.where(pid == p)[0] for p in smp])
        if len(np.unique(y_eval[idx])) < 2:
            continue
        for k, o in CAND.items():
            bw[k].append(within_of(o, idx))

    print("=== 평가는 「부정 정서」로 고정 · 학습 대상만 바꿈 ===\n")
    print(f"  {'구성':22s} {'내부 AUC':>9} {'95%':>15}")
    print(f"  {'-'*22} {'-'*9} {'-'*15}")
    for k, o in CAND.items():
        lo, hi = np.nanpercentile(bw[k], [2.5, 97.5])
        print(f"  {k:22s} {within_of(o):9.3f} {lo:.3f}~{hi:.3f}")

    print("\n  === 배포본 대비 (같은 리샘플에서의 차) ===\n")
    base = np.array(bw["① 배포본 (불안으로 학습)"])
    for k in ("② 부정 정서로 학습", "③ 둘 다 (순위 평균)"):
        d = np.array(bw[k]) - base
        lo, hi = np.nanpercentile(d, [2.5, 97.5])
        sig = "✅" if lo > 0 else ("⛔" if hi < 0 else "  ")
        print(f"  {k:22s} {np.nanmean(d):+.3f} [{lo:+.3f},{hi:+.3f}] {sig}")


if __name__ == "__main__":
    main()
