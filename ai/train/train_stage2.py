"""2차 위험도 분류기 학습 — LightGBM

GLOBEM 14일 집계 피처(수면·걸음) → 우울 여부(`dep`) / BDI-II 점수(`BDI2`)

⚠ **지금은 샘플 481행으로 학습합니다.** GLOBEM 전체가 아닙니다.
  전체 데이터가 들어오면 --data 로 경로만 바꿔 그대로 다시 돌리면 됩니다.
  산출물의 model_version 에 표본 크기가 박히므로 어떤 데이터로 만든
  모델인지 나중에도 구분됩니다.

실행:
    cd ai/train
    python train_stage2.py
    python train_stage2.py --data ../../data/globem_full.csv   # 전체 데이터가 생기면
"""

import argparse
import json
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupKFold

HERE = Path(__file__).resolve().parent
DEFAULT_DATA = HERE.parent / "samples" / "feature_matrix_sample.csv"
OUT_DIR = HERE.parent / "models"

LABEL = "dep"          # 이진 라벨. BDI2 는 원점수라 회귀용으로 남겨둔다.
GROUP = "pid"          # ⚠ 참가자 단위로 나눠야 한다. 아래 설명 참조.
DROP = ["pid", "date", "BDI2", "dep"]


def short_name(col: str) -> str:
    """GLOBEM 원본 피처명을 짧게 줄인다.

    원본은 `f_slp:fitbit_sleep_summary_rapids_sumdurationasleepmain:14dhist` 처럼
    길고 `:` 가 들어 있다. **LightGBM 은 피처명에 JSON 특수문자를 허용하지 않아**
    그대로 넣으면 LightGBMError 로 죽는다.

    이름을 바꾸므로 **저장된 모델의 features 순서가 곧 계약**이 된다.
    추론할 때 같은 순서로 넣어야 한다.
    """
    if ":" not in col:
        return col
    parts = col.split(":")
    body = parts[1]
    for prefix in ("fitbit_sleep_summary_rapids_", "fitbit_steps_summary_rapids_"):
        body = body.replace(prefix, "")
    return f"{parts[0].replace('f_', '')}_{body}"


def load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in (LABEL, GROUP) if c not in df.columns]
    if missing:
        raise SystemExit(f"필요한 열이 없습니다: {missing}")
    df = df.rename(columns={c: short_name(c) for c in df.columns})
    return df.dropna(subset=[LABEL])


def evaluate(df: pd.DataFrame) -> dict:
    """참가자 단위 교차검증.

    ⚠ 무작위로 행을 나누면 **같은 사람의 다른 날짜가 학습·평가 양쪽에 들어간다.**
      14일 히스토리 피처라 연속된 날짜끼리 거의 같은 값이고, 그러면 성능이
      크게 부풀려진다. 참가자로 묶어서 나눈다(GroupKFold).
    """
    X = df.drop(columns=[c for c in DROP if c in df.columns])
    y = df[LABEL].astype(int)
    groups = df[GROUP]

    n_splits = min(5, groups.nunique())
    aucs, aps = [], []
    for tr, te in GroupKFold(n_splits=n_splits).split(X, y, groups):
        if y.iloc[tr].nunique() < 2 or y.iloc[te].nunique() < 2:
            continue  # 한쪽 클래스만 있는 fold 는 평가 불가
        m = lgb.LGBMClassifier(
            n_estimators=200, learning_rate=0.05, num_leaves=15,
            min_child_samples=20, subsample=0.8, colsample_bytree=0.8,
            random_state=42, verbose=-1,
        )
        m.fit(X.iloc[tr], y.iloc[tr])
        p = m.predict_proba(X.iloc[te])[:, 1]
        aucs.append(roc_auc_score(y.iloc[te], p))
        aps.append(average_precision_score(y.iloc[te], p))

    return {
        "n_folds": len(aucs),
        "roc_auc": float(np.mean(aucs)) if aucs else None,
        "roc_auc_std": float(np.std(aucs)) if aucs else None,
        "pr_auc": float(np.mean(aps)) if aps else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    args = ap.parse_args()

    df = load(args.data)
    X = df.drop(columns=[c for c in DROP if c in df.columns])
    y = df[LABEL].astype(int)

    print(f"데이터  {args.data.name}")
    print(f"  행 {len(df)}  참가자 {df[GROUP].nunique()}  피처 {X.shape[1]}")
    print(f"  양성 {int(y.sum())} / {len(y)}  ({y.mean():.1%})\n")

    metrics = evaluate(df)
    print("참가자 단위 교차검증")
    if metrics["roc_auc"] is None:
        print("  평가 불가 — 유효한 fold 가 없습니다\n")
    else:
        print(f"  ROC-AUC  {metrics['roc_auc']:.3f} (±{metrics['roc_auc_std']:.3f}, {metrics['n_folds']} folds)")
        print(f"  PR-AUC   {metrics['pr_auc']:.3f}   (기준선 {y.mean():.3f})\n")

    # 최종 모델은 전체로 학습한다. 위 지표는 이 모델의 일반화 추정치다.
    model = lgb.LGBMClassifier(
        n_estimators=200, learning_rate=0.05, num_leaves=15,
        min_child_samples=20, subsample=0.8, colsample_bytree=0.8,
        random_state=42, verbose=-1,
    )
    model.fit(X, y)

    OUT_DIR.mkdir(exist_ok=True)
    version = f"lgbm-sample-n{len(df)}-v0"
    joblib.dump({"model": model, "features": list(X.columns), "version": version},
                OUT_DIR / "stage2_lgbm.joblib")

    meta = {"version": version, "n_rows": len(df),
            "n_participants": int(df[GROUP].nunique()),
            "features": list(X.columns), "metrics": metrics,
            "positive_rate": float(y.mean())}
    (OUT_DIR / "stage2_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    imp = sorted(zip(X.columns, model.feature_importances_),
                 key=lambda t: -t[1])
    print("피처 중요도")
    for name, v in imp:
        short = name.split(":")[1][:40] if ":" in name else name
        print(f"  {v:5d}  {short}")

    print(f"\n저장  {OUT_DIR / 'stage2_lgbm.joblib'}")
    print(f"버전  {version}")


if __name__ == "__main__":
    main()
