# -*- coding: utf-8 -*-
r"""규칙 + 학습 모델 결합이 규칙 단독보다 나은가 — 2026.08.24

```powershell
.\.venv\Scripts\python.exe ai/train/eval_hybrid.py
```

## 왜 만들었나

슬라이드 9 가 「LightGBM 을 학습했지만 채택하지 않았다」고 말합니다.
사실이지만 **학습한 것을 서비스에서 하나도 쓰지 않는다**는 뜻이기도
합니다. PM 이 "학습한 걸 활용할 방법을 찾아라" 라고 요구했고, 그중
**(A) 가중 결합** — 규칙 기반 이탈 점수에 모델 확률을 섞는 안 — 을
검증하려고 만들었습니다.

**결합이 규칙 단독보다 나으면 (A) 를 넣을 근거가 생기고, 아니면 넣지
않을 근거가 생깁니다.** 어느 쪽이든 근거가 남는 것이 목적입니다.

## ⚠ 이 검증이 재는 것과 재지 못하는 것

**재는 것** — GLOBEM `dep`(BDI-II 기반 우울 여부) 를 정답으로 놓고,
세 방식의 판별력(ROC-AUC)을 같은 조건에서 비교합니다.

    ① 규칙 단독      개인 기준선 이탈 점수 (ai/server/main.py 와 같은 식)
    ② 모델 단독      LightGBM 확률
    ③ 가중 결합      (1-w)*규칙 + w*모델

**재지 못하는 것** — 「우리 서비스의 판정이 좋아졌는가」는 못 잽니다.
서비스가 내는 `anomaly` 에는 정답 라벨이 없습니다. 우리 평가셋 211건은
텍스트 발화라 수면·걸음 피처가 없어 모델을 먹일 수도 없습니다.
**여기서 나온 숫자를 「서비스 성능」으로 말하면 안 됩니다.**

## 조건은 기존 검증과 같게 맞춥니다

- 참가자 단위 분할(`GroupKFold`) — 무작위로 나누면 같은 사람이 학습·
  평가 양쪽에 들어가 AUC 가 부풀려집니다
- 참가자를 섞어 **20회 반복** + 95% 신뢰구간 — 0.610 이 fold 운이었던
  전례가 있습니다(작업이력 「공개 샘플 4개를 받아 학습해봤습니다」)
"""

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
import lightgbm as lgb
import warnings

warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "samples" / "feature_matrix_samples1to4.csv"
N_REPEAT = 20
N_SPLITS = 5
SEED = 42

#  ai/server/main.py 와 같은 상수. 여기서 다시 정의하는 이유는 그 파일이
#  FastAPI 앱이라 임포트하면 서버가 딸려 오기 때문입니다.
FULL_SCALE_Z = 4.0

SLEEP_COLS = [c for c in [
    "f_slp:fitbit_sleep_summary_rapids_sumdurationasleepmain:14dhist",
    "f_slp:fitbit_sleep_summary_rapids_avgdurationasleepmain:14dhist",
]]
#  이탈 방향 — 줄면 나쁜 지표(down) / 늘면 나쁜 지표(up)
RULE_FEATURES = [
    ("f_slp:fitbit_sleep_summary_rapids_sumdurationasleepmain:14dhist", "down"),
    ("f_slp:fitbit_sleep_summary_rapids_avgdurationasleepmain:14dhist", "down"),
    ("f_steps:fitbit_steps_summary_rapids_avgsumsteps:14dhist", "down"),
    ("f_steps:fitbit_steps_summary_rapids_mediansumsteps:14dhist", "down"),
    ("f_slp:fitbit_sleep_summary_rapids_sumdurationawakemain:14dhist", "up"),
    ("f_slp:fitbit_sleep_summary_rapids_sumdurationtofallasleepmain:14dhist", "up"),
]


def robust_z(value, history):
    """중앙값·MAD 기준 z. ai/server/main.py `_robust_z` 와 같은 식."""
    h = [v for v in history if pd.notna(v)]
    if len(h) < 3 or pd.isna(value):
        return None
    med = float(np.median(h))
    mad = float(np.median([abs(v - med) for v in h]))
    if mad == 0:
        #  값이 절반 이상 같으면 MAD 가 0 이 된다. 표준편차로 물러선다.
        sd = float(np.std(h))
        if sd == 0:
            return None
        return (value - med) / sd
    return (value - med) / (1.4826 * mad)


def rule_score(df):
    """개인 기준선 이탈 점수. 참가자별로 과거를 기준선 삼아 오늘을 잰다.

    ⚠ 기준선에서 **오늘을 뺀다** — main.py 와 같다. 오늘을 넣으면 오늘이
      스스로를 정상 쪽으로 끌어당겨 편차가 작아진다(미탐 방향).
    """
    out = np.zeros(len(df))
    for pid, g in df.groupby("pid", sort=False):
        g = g.sort_values("date")
        idx = g.index.to_numpy()
        for i in range(len(g)):
            hist = g.iloc[:i]           # 오늘 제외
            if len(hist) < 3:
                continue
            devs = []
            for col, direction in RULE_FEATURES:
                if col not in g.columns:
                    continue
                z = robust_z(g.iloc[i][col], hist[col].tolist())
                if z is None:
                    continue
                #  나쁜 방향으로 벗어난 것만 이탈로 센다
                signed = -z if direction == "down" else z
                devs.append(max(0.0, signed))
            if not devs:
                continue
            top = sorted(devs, reverse=True)[:3]
            out[np.where(idx == idx[i])[0][0] if False else g.index.get_loc(g.index[i])] = 0
            # 위 줄은 인덱스 혼동을 피하려 아래에서 직접 대입한다
            out[df.index.get_loc(g.index[i])] = min(1.0, sum(top) / len(top) / FULL_SCALE_Z)
    return out


def main():
    df = pd.read_csv(DATA)
    df = df.reset_index(drop=True)
    y = df["dep"].astype(int).to_numpy()
    groups = df["pid"].to_numpy()

    model_cols = [c for c in df.columns if c.startswith("f_")]
    X = df[model_cols].copy()
    if "cohort" in df.columns:
        X["cohort"] = pd.factorize(df["cohort"])[0]
    #  ⚠ LightGBM 은 피처명에 JSON 특수문자(`:`)를 허용하지 않는다.
    #    GLOBEM 원본이 `f_slp:...:14dhist` 형태라 그대로 넣으면 죽는다 —
    #    train_stage2.py 의 short_name() 이 이미 겪고 푼 문제다.
    X.columns = [c.replace(":", "_").replace("f_", "") for c in X.columns]

    print(f"데이터  {DATA.name}")
    print(f"  행 {len(df)}  참가자 {df['pid'].nunique()}  피처 {X.shape[1]}")
    print(f"  양성 {y.sum()} / {len(y)}  ({y.mean():.1%})\n")

    print("규칙 점수 계산 중...")
    rule = rule_score(df)
    usable = rule > 0          # 기준선 3일이 안 쌓인 앞부분은 뺀다
    print(f"  기준선이 쌓인 행 {usable.sum()} / {len(df)}\n")

    weights = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
    scores = {w: [] for w in weights}

    rng = np.random.default_rng(SEED)
    for rep in range(N_REPEAT):
        #  참가자를 섞는다 — fold 운을 걷어내려는 것
        pids = df["pid"].unique().copy()
        rng.shuffle(pids)
        remap = {p: i for i, p in enumerate(pids)}
        g = np.array([remap[p] for p in groups])

        gkf = GroupKFold(n_splits=N_SPLITS)
        oof = np.full(len(df), np.nan)
        for tr, te in gkf.split(X, y, groups=g):
            if len(np.unique(y[tr])) < 2:
                continue
            m = lgb.LGBMClassifier(
                n_estimators=200, learning_rate=0.05, num_leaves=15,
                min_child_samples=20, subsample=0.8, colsample_bytree=0.8,
                random_state=SEED, verbose=-1,
            )
            m.fit(X.iloc[tr], y[tr])
            oof[te] = m.predict_proba(X.iloc[te])[:, 1]

        ok = usable & ~np.isnan(oof)
        if ok.sum() < 30 or len(np.unique(y[ok])) < 2:
            continue
        for w in weights:
            combined = (1 - w) * rule[ok] + w * oof[ok]
            scores[w].append(roc_auc_score(y[ok], combined))

    print(f"참가자 단위 분할 · {N_REPEAT}회 반복 · GLOBEM dep 기준\n")
    print(f"  {'가중치':>8}  {'구성':<22} {'평균 AUC':>9}  {'95% 구간':>18}")
    print(f"  {'-'*8}  {'-'*22} {'-'*9}  {'-'*18}")
    base = None
    for w in weights:
        v = np.array(scores[w])
        if len(v) == 0:
            continue
        lo, hi = np.percentile(v, [2.5, 97.5])
        label = ("규칙 단독" if w == 0 else
                 "모델 단독" if w == 1.0 else f"규칙 {1-w:.0%} + 모델 {w:.0%}")
        if w == 0:
            base = v.mean()
        mark = ""
        if base is not None and w > 0:
            mark = "  ↑" if v.mean() > base else "  ↓"
        print(f"  {w:>8.1f}  {label:<22} {v.mean():>9.3f}  {lo:.3f} ~ {hi:.3f}{mark}")

    print()
    best_w = max((w for w in weights if len(scores[w])), key=lambda w: np.mean(scores[w]))
    best = np.mean(scores[best_w])
    print(f"최고 = 가중치 {best_w} ({best:.3f}) · 규칙 단독 {base:.3f}")
    if best_w == 0:
        print("→ 결합이 규칙 단독을 넘지 못했습니다. (A) 가중 결합을 넣을 근거가 없습니다.")
    else:
        gain = best - base
        v0, vb = np.array(scores[0]), np.array(scores[best_w])
        diff = vb - v0
        lo, hi = np.percentile(diff, [2.5, 97.5])
        print(f"→ 이득 {gain:+.3f} · 차이의 95% 구간 {lo:+.3f} ~ {hi:+.3f}")
        if lo > 0:
            print("  구간이 0 을 넘지 않습니다 — 우연이 아닙니다. (A) 를 넣을 근거가 됩니다.")
        else:
            print("  ⚠ 구간이 0 을 포함합니다 — 우연과 구분되지 않습니다. 넣을 근거가 못 됩니다.")


if __name__ == "__main__":
    main()
