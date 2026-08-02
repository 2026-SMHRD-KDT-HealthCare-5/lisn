# -*- coding: utf-8 -*-
"""LifeSnaps 로 감정 분류가 되는지 **검증만** 한다 — 2026.08.02

```powershell
python ai/train/eval_lifesnaps.py
```

## 왜 학습이 아니라 검증인가

지금 결론(「데이터가 부족해서 모델을 안 넣었다」)의 약한 고리는
**「40명이 적어서 그런 것 아니냐」** 입니다. 참가자를 늘린 다른 데이터로
같은 결과가 나오면 그 반문이 사라집니다.

**모델을 채택하려고 돌리는 게 아니라, 결론을 검증하려고 돌립니다.**

## 데이터

- LifeSnaps (Zenodo 7229547, CC-BY 4.0) — 71명 4개월, Fitbit Sense
- 감정 라벨은 EMA 로 받은 **7종 이진 체크**
  (HAPPY / SAD / TENSE·ANXIOUS / RESTED·RELAXED / TIRED / ALERT / NEUTRAL)
- 라벨이 있는 행은 63명 · 2290일

## 우리 파이프라인과 같은 조건으로 맞춘다

- **14일 히스토리 집계** — `MLCM_210` 2단계가 규정한 기준값 창
- **참가자 단위 분할**(`GroupKFold`) — 무작위로 나누면 같은 사람이 학습·평가
  양쪽에 들어가 AUC 가 부풀려진다
- 피처는 수면·걸음 중심. LifeSnaps 에만 있는 HRV·호흡수도 함께 본다
"""
import warnings
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

warnings.filterwarnings('ignore')

CSV = (Path(__file__).resolve().parents[1] / 'data_raw' / 'lifesnaps'
       / 'rais_anonymized' / 'csv_rais_anonymized'
       / 'daily_fitbit_sema_df_unprocessed.csv')

EMOTIONS = ['HAPPY', 'SAD', 'TENSE/ANXIOUS', 'RESTED/RELAXED',
            'TIRED', 'ALERT', 'NEUTRAL']

# 우리 수집 항목과 겹치는 것 위주. HRV·호흡수는 LifeSnaps 에만 있다.
BASE = ['steps', 'minutesAsleep', 'sleep_efficiency', 'sleep_duration',
        'minutesToFallAsleep', 'resting_hr', 'nremhr',
        'full_sleep_breathing_rate', 'sleep_deep_ratio', 'calories',
        'distance', 'lightly_active_minutes', 'very_active_minutes']

HIST = 14  # MLCM_210 이 규정한 기준값 창


def build():
    df = pd.read_csv(CSV)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['id', 'date'])

    cols = [c for c in BASE if c in df.columns]
    out = []
    for pid, g in df.groupby('id'):
        g = g.set_index('date').asfreq('D')  # 빠진 날을 NaN 으로 채운다
        feat = {}
        for c in cols:
            s = pd.to_numeric(g[c], errors='coerce')
            r = s.rolling(HIST, min_periods=7)
            feat[f'{c}_mean'] = r.mean()
            feat[f'{c}_std'] = r.std()
            feat[f'{c}_min'] = r.min()
            feat[f'{c}_max'] = r.max()
            # ⚠ 「평소 대비 오늘」이 우리 판정 축이다. 절대값만 쓰면
            #   사람마다 기준이 달라 비교가 안 된다.
            feat[f'{c}_dev'] = (s - r.mean()) / (r.std() + 1e-6)
        f = pd.DataFrame(feat, index=g.index)
        for e in EMOTIONS:
            if e in g.columns:
                f[e] = pd.to_numeric(g[e], errors='coerce')
        f['pid'] = pid
        out.append(f.reset_index())
    return pd.concat(out, ignore_index=True)


def evaluate(X, y, groups, repeats=20, seed=0):
    """참가자를 섞어 fold 를 재구성하며 반복한다. 한 번만 재면 fold 운을 본다."""
    rng = np.random.default_rng(seed)
    uniq = pd.unique(groups)
    scores = []
    for _ in range(repeats):
        perm = {p: i for i, p in enumerate(rng.permutation(uniq))}
        gg = np.array([perm[p] for p in groups])
        fold = []
        for tr, te in GroupKFold(n_splits=5).split(X, y, gg):
            if len(set(y[te])) < 2 or len(set(y[tr])) < 2:
                continue
            m = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.05,
                                   num_leaves=15, min_child_samples=20,
                                   subsample=0.8, colsample_bytree=0.8,
                                   random_state=42, verbose=-1)
            m.fit(X.iloc[tr], y[tr])
            fold.append(roc_auc_score(y[te], m.predict_proba(X.iloc[te])[:, 1]))
        if fold:
            scores.append(float(np.mean(fold)))
    return np.array(scores)


def main():
    if not CSV.exists():
        raise SystemExit(f'데이터가 없습니다: {CSV}')
    df = build()
    feats = [c for c in df.columns if c not in EMOTIONS + ['pid', 'date']]

    print(f'LifeSnaps — 전체 {len(df)}행 · 참가자 {df["pid"].nunique()}명 '
          f'· 피처 {len(feats)}개\n')
    print(f'{"감정":16s} {"일수":>5s} {"참가자":>5s} {"양성률":>7s} '
          f'{"평균AUC":>8s} {"95%구간":>16s} {"0.5이하":>8s}')
    print('-' * 78)

    rows = []
    for e in EMOTIONS:
        sub = df[df[e].notna()].copy()
        y = sub[e].astype(int).values
        if len(sub) < 200 or y.mean() in (0, 1):
            print(f'{e:16s} 표본 부족 — 건너뜀')
            continue
        X = sub[feats].astype(float)
        s = evaluate(X, y, sub['pid'].values)
        if len(s) == 0:
            print(f'{e:16s} 유효 fold 없음')
            continue
        lo, hi = np.percentile(s, [2.5, 97.5])
        rows.append((e, s.mean(), lo, hi))
        print(f'{e:16s} {len(sub):5d} {sub["pid"].nunique():5d} '
              f'{y.mean():6.1%} {s.mean():8.3f} '
              f'{lo:7.3f}~{hi:.3f} {int((s <= 0.5).sum()):5d}/{len(s)}')

    print('\n' + '=' * 78)
    beats = [r for r in rows if r[2] > 0.5]
    if beats:
        print('95% 구간이 0.5 위인 감정 (무작위보다 낫다고 말할 수 있는 것)')
        for e, m, lo, hi in beats:
            print(f'  {e:16s} {m:.3f}  [{lo:.3f}, {hi:.3f}]')
    else:
        print('⚠ **모든 감정에서 95% 구간이 0.5 를 포함합니다.**')
        print('   참가자를 63명으로 늘려도 무작위와 구분되지 않습니다.')


if __name__ == '__main__':
    main()
