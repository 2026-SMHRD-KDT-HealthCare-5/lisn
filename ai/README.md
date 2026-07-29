# AI — 라이프로그 분석 모델

> **담당** 김건영 · **최종 갱신** 2026.07.29

라이프로그 시계열에서 정서 위험도를 산출하는 2단계 모델입니다.

```
1차  LSTM Autoencoder   정상 패턴 학습 → 재구성 오차 = anomaly_score
2차  LightGBM           anomaly_score + 라이프로그 피처 → 감정 9종 · risk_score
```

위기 대화 탐지는 **별도 학습 모델이 아닙니다.** 키워드 규칙 + OpenAI 프롬프트 2단계로 구현합니다. (안건 3 확정)

---

## 학습 데이터셋

| 데이터셋 | 역할 | 핵심 피처 | 라벨 |
|---|---|---|---|
| **PMData** | 1차 이상탐지 | 수면 단계(deep/light/REM) · 깬 시간 · 평균 심박 · HRV 프록시 | 없음 |
| **GLOBEM** | 2차 위험도 분류 | 14일 히스토리 수면·걸음·스크린타임 | **BDI-II 점수 · 우울 여부** |

**GLOBEM 의 14일 집계 단위는 우연이 아니라 설계와 맞습니다.** 02 요구사항정의서 `MLCM_210` 이 전제하는 "최근 14일 개인별 정규화"와 동일한 창(window)입니다.

> **AI Hub 는 사용하지 않습니다.** 정신건강 데이터는 안심존 전용이며 기관생명윤리위원회(IRB) 심의 결과 통지서가 필요해 과제 기간 내 확보가 불가능합니다.
> **WESAD 도 사용하지 않습니다.** 실험실에서 유도한 급성 스트레스 데이터라 일상 라이프로그와 도메인이 다릅니다.

### 원본 데이터는 저장소에 없습니다

용량이 3GB 를 넘어 `.gitignore` 로 제외했습니다. 각자 내려받아 이 폴더에 두세요.

| 데이터셋 | 받는 곳 | 두는 위치 |
|---|---|---|
| PMData | OSF (`osfstorage-archive`) | `ai/data_raw/PMData/` |
| GLOBEM | GitHub `microsoft/GLOBEM` | `ai/data_raw/GLOBEM/` |

---

## 폴더 구성

```
ai/
├── preprocess/
│   ├── process_pmdata.py     PMData 수면·심박 → 일별 피처
│   └── process_globem.py     GLOBEM 수면·걸음·스크린 + BDI-II 라벨 병합
├── samples/
│   ├── pmdata_sleep_features.csv    출력 예시 (p01)
│   └── feature_matrix_sample.csv    출력 예시 (INS-W-sample_1)
└── data_raw/                 원본 — git 제외
```

## 실행

```bash
python ai/preprocess/process_pmdata.py
```

```bash
python ai/preprocess/process_globem.py
```

> 스크립트 안의 경로가 `./osfstorage-archive/...`, `./GLOBEM-main/...` 로 되어 있습니다. `data_raw/` 구조로 옮기실 때 함께 수정하세요.

---

## ⚠ 문서 작성 시 주의할 점

### 1. `hrv_sdnn` 은 진짜 SDNN 이 아닙니다

`process_pmdata.py` 는 **일별 BPM 의 표준편차**를 HRV 프록시로 씁니다.

```python
hrv_sdnn=('bpm', 'std')  # 심박수 표준편차 = HRV 프록시 지표
```

표준 SDNN 은 RR 간격(NN interval)의 표준편차인데, PMData 의 Fitbit 데이터에 RR 간격이 없어 대체한 것입니다. 합리적인 선택이지만 **산출물 문서에 그냥 "HRV"라고 쓰면 정확하지 않습니다.**

- **실서비스** — Health Connect 가 제공하는 HRV 를 그대로 수집
- **학습 데이터** — PMData 의 BPM 표준편차 프록시

두 값의 성격이 달라 **도메인 갭이 존재**합니다. 문서에 이 차이를 적어두면 "학습 데이터의 HRV 와 실제 수집하는 HRV 가 같은 건가요"라는 질문에 답할 수 있습니다.

### 2. 현재는 전체 학습이 아니라 파이프라인 검증 단계입니다

| 스크립트 | 처리 범위 |
|---|---|
| `process_pmdata.py` | **참가자 `p01` 한 명** |
| `process_globem.py` | **`INS-W-sample_1` 샘플 1개** |

"전처리 완료"가 아니라 **"파이프라인 동작 확인 완료"** 입니다. 문서에 학습 규모를 쓸 때 과장하지 마세요.

---

## 기업(라라랩스)에 확인할 것

1. 제공 데이터가 **수면·걸음 수·심박수·폰 사용량**과 비슷한 항목인지, 그리고 **초/분 단위 원본인지 하루 단위 통계인지**
   → 1분 단위면 전처리를 추가로 해야 합니다
2. **정답(라벨) 데이터가 있는지**
   → 없으면 라이프로그 수치에 가중치를 줘 자체 위험도 점수를 만들어야 합니다
3. 사용자가 **워치를 착용하지 않은 구간의 결측 처리** 방식
   → `02-H` 의 미수신 처리(`last_synced_at` 3시간 임계 · FCM 무음 푸시)와 직결됩니다

---

## 관련 문서

- [`docs/review/문서개정_체크리스트.md`](../docs/review/문서개정_체크리스트.md) — `X-1` 이 데이터셋 관련 문서 개정 항목
- [`docs/review/작업이력.md`](../docs/review/작업이력.md) — 안건 3(위기 탐지 방식) 확정 근거
