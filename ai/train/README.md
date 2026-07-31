# ai/train — 모델 학습

## ⚠ 먼저 읽으세요 — 지금 나온 모델은 쓸 수 없습니다

`train_stage2.py` 는 **동작합니다.** 하지만 샘플 데이터로 학습한 결과는 **예측력이 없습니다.**

| 지표 | 값 | 해석 |
|---|---|---|
| ROC-AUC | **0.485** (±0.131) | **0.5 미만 = 무작위보다 못함** |
| PR-AUC | 0.504 | 기준선 0.393 대비 소폭 위 |
| 유효 fold | **2개** | 참가자가 10명뿐이라 나눌 수가 없음 |

**원인은 모델이 아니라 데이터입니다.** `samples/feature_matrix_sample.csv` 는 GLOBEM 전체가 아니라 **참가자 10명 · 481행** 짜리 맛보기입니다. 이 크기로는 어떤 알고리즘을 써도 의미 있는 결과가 나오지 않습니다.

> ### 그래서 이 모델을 `ai/server` 에 붙이지 않았습니다
>
> 붙이면 **규칙 기반 placeholder 보다 더 나쁩니다.** placeholder 는 `model_version` 이
> `rule-placeholder-v0` 이라 누가 봐도 임시인 걸 알지만, 학습된 모델은 이름만 보면
> 진짜처럼 보입니다. **성능이 무작위 수준인 채로 "모델 적용 완료" 로 읽히는 게
> 가장 위험합니다.**
>
> 발표 자료에 이 숫자를 성능으로 쓰지 마세요.

---

## 그럼 이건 왜 있나

**전체 데이터가 들어왔을 때 바로 돌릴 수 있는 상태**를 만들어 둔 것입니다. 데이터가 준비되면 경로만 바꿔서 다시 돌리면 됩니다.

```powershell
python train_stage2.py --data ..\..\data\globem_full.csv
```

같은 스크립트가 지표를 다시 뽑고 `ai/models/` 에 새 모델과 `stage2_meta.json` 을 씁니다. **그때 ROC-AUC 가 유의미하게 올라오면** 그 시점에 `ai/server/main.py` 의 `_predict()` 를 교체하세요.

---

## 실행

```powershell
cd ai\train
python train_stage2.py
```

필요 패키지: `lightgbm` `scikit-learn` `pandas` `numpy` `joblib`

---

## 설계에서 짚어둔 것

### 참가자 단위로 나눕니다 (`GroupKFold`)

무작위로 행을 나누면 **같은 사람의 다른 날짜가 학습·평가 양쪽에 들어갑니다.** 14일 히스토리 피처라 연속된 날짜끼리 값이 거의 같고, 그러면 **성능이 크게 부풀려집니다.**

> 이걸 안 하면 지금 샘플에서도 AUC 가 0.9 넘게 나옵니다. 그 숫자를 믿고 진행하면 전체 데이터에서 무너집니다.

### 피처명을 줄입니다

GLOBEM 원본은 `f_slp:fitbit_sleep_summary_rapids_sumdurationasleepmain:14dhist` 처럼 길고 `:` 가 들어 있습니다. **LightGBM 은 피처명에 JSON 특수문자를 허용하지 않아** 그대로 넣으면 `LightGBMError` 로 죽습니다.

이름을 바꾸므로 **저장된 모델의 `features` 순서가 곧 계약**입니다. 추론할 때 같은 순서로 넣어야 합니다.

### 라벨

- `dep` — 이진(우울 여부). 지금 학습에 쓰는 것
- `BDI2` — BDI-II 원점수. 회귀로 갈 때를 위해 남겨둠

---

## 1차 LSTM Autoencoder 는 아직 없습니다

`samples/pmdata_sleep_features.csv` 는 **155행**입니다. PMData `p01` 한 명 분량이라 시계열 오토인코더를 학습할 수 없습니다. 1차는 **PMData 원본을 받은 뒤에** 시작해야 합니다.

전처리 스크립트는 [`../preprocess/process_pmdata.py`](../preprocess/process_pmdata.py) 에 있습니다.
