"""GLOBEM 공개 샘플 4개를 하나의 학습 행렬로 합칩니다.

⚠ **PhysioNet 전체 데이터가 아닙니다.** UW-EXP/GLOBEM 공개 저장소의
  `data_raw/INS-W-sample_1~4` 입니다. 자격 인증 없이 받을 수 있는 대신
  참가자 수가 적습니다. 논문 벤치마크와 비교하지 마세요.

전처리 자체는 `process_globem.py` 의 함수를 그대로 씁니다. 여기서 규칙을
다시 만들면 정본이 둘이 됩니다 — 특히 **스크린타임 제외** 결정이 그렇습니다.

실행:
    python ai/preprocess/build_matrix.py
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from process_globem import process_globem_full  # noqa: E402

RAW = Path(__file__).resolve().parent.parent / "data_raw"
OUT = Path(__file__).resolve().parent.parent / "samples" / "feature_matrix_samples1to4.csv"


def main():
    frames = []
    for i in (1, 2, 3, 4):
        base = RAW / f"INS-W-sample_{i}"
        if not base.exists():
            print(f"  sample_{i} 없음 — 건너뜁니다")
            continue
        df = process_globem_full(str(base))
        if df is None:
            continue
        # ⚠ pid 가 연차별로 겹칩니다(INS-W_004 가 sample_1 과 _2 에 모두 존재).
        #   그대로 합치면 서로 다른 사람이 한 사람으로 묶여 참가자 단위
        #   교차검증이 깨집니다. 연차를 붙여 구분합니다.
        df["pid"] = f"s{i}_" + df["pid"].astype(str)
        df["cohort"] = i
        frames.append(df)
        print(f"  sample_{i}: {len(df):>5}행  참가자 {df['pid'].nunique()}명")

    if not frames:
        raise SystemExit("data_raw 에 샘플이 없습니다.")

    merged = pd.concat(frames, ignore_index=True)
    merged = merged.dropna(subset=["dep"])

    OUT.parent.mkdir(exist_ok=True)
    merged.to_csv(OUT, index=False)

    print(f"\n합계 {len(merged):,}행  참가자 {merged['pid'].nunique()}명")
    print(f"양성 {int(merged['dep'].sum())} / {len(merged)} ({merged['dep'].mean():.1%})")
    print(f"저장 {OUT}")


if __name__ == "__main__":
    main()
