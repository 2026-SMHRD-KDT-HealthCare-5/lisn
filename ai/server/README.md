# ai/server — AI 추론 서버

`MLCM_210` 정서 위험도 분석을 수행합니다. 비즈니스 서버(`backend/`)가 라이프로그를
적재한 직후 백그라운드로 호출합니다.

> ⚠ **지금은 규칙 기반 임시 판정입니다.** 모델이 아직 없어서, 그때까지 파이프라인이
> 끊기지 않도록 자리를 채워둔 것입니다. 응답의 `model_version` 이
> `rule-placeholder-v0` 이면 **모델 결과가 아닙니다.** 이 값으로 성능을 주장하지 마세요.

---

## 실행

```powershell
pip install -r requirements.txt
```

```powershell
uvicorn main:app --reload --port 8001
```

DB 는 비즈니스 서버와 **같은 것**을 봅니다. `AI_DATABASE_URL` 이 없으면 `DATABASE_URL`
을 쓰고, 그것도 없으면 `localhost:5432/lisn` 로 붙습니다. `postgresql+asyncpg://`
접두사는 자동으로 벗겨내므로 backend 의 `.env` 값을 그대로 넣어도 됩니다.

포트 8001 은 backend 의 `AI_SERVER_URL` 기본값과 맞춘 것입니다. 바꾸려면 양쪽을 함께
고치세요.

---

## 왜 DB 를 직접 읽나

비즈니스 서버는 `user_id` 와 시각만 보냅니다. 시퀀스를 페이로드로 실어 보내면
요청이 비대해지고, **전처리 규격이 바뀔 때마다 양쪽 서버를 함께 고쳐야 합니다.**
전처리는 모델 담당 영역이므로 이쪽에 두는 편이 맞습니다.

---

## 엔드포인트

### `POST /internal/analyze/lifelog`

```json
{ "user_id": "uuid", "evaluated_at": "2026-08-01T09:00:00Z" }
```

```json
{ "emotion_code": "ANXIETY", "emotion_score": 82.0, "anomaly_score": 0.73,
  "risk_level": "CAUTION", "risk_score": 68.5, "model_version": "v1.0" }
```

| 코드 | 상황 |
|---|---|
| 404 | 최근 14일 라이프로그가 없음 |
| 503 | DB 연결 실패 |

비즈니스 서버는 실패를 조용히 넘깁니다. 라이프로그 push 자체는 이미 성공했으므로
분석 실패로 되돌리지 않습니다. 다음 주기(15분)에 다시 분석됩니다.

### `GET /health`

기동 확인용.

---

## 인증이 없습니다

내부 API 라 인증을 두지 않았습니다. **두 서버가 같은 네트워크 안에 있고 이 포트를
외부에 열지 않는 것이 전제입니다**(`docs/review/API설계_사전결정.md` 7절).
외부에 노출하면 `user_id` 만 알면 아무나 타인의 라이프로그 분석을 돌릴 수 있습니다.

---

## 모델 교체 방법

`main.py` 의 **`_predict()` 하나만** 바꾸면 됩니다.

```
1차  LSTM Autoencoder — 정상 패턴 재구성 오차        -> anomaly_score
2차  LightGBM         — anomaly_score + 피처        -> emotion_code, risk_score
```

반환하는 여섯 필드의 이름과 타입은 바꾸지 마세요. 비즈니스 서버가 그대로
`EMOTION_RISK_SCORES` 에 적재합니다(`backend/app/services/analysis.py`).

`emotion_code` 는 `schema.sql` 의 **감정 마스터 9종** 중 하나여야 합니다. 다른 값을
보내면 비즈니스 서버가 적재를 건너뛰고 경고만 남깁니다.

### 건드리지 말 것 — `risk_level_of()`

위험 단계 매핑은 **모델이 아니라 정책**입니다(04 문서 6항). `_predict()` 를 교체할 때
이 함수까지 같이 들어내지 마세요.

- `EMOTIONS.category` 가 기본값
- `ANGER` 는 `emotion_score >= 70` 이면 `CRITICAL` 로 재분류
- `CRISIS` 는 점수와 무관하게 항상 `CRITICAL`

`EMOTION_CATEGORY` 는 `schema.sql` 의 마스터를 복제한 것입니다(요청마다 조회하지
않으려고). **`schema.sql` 을 고치면 여기도 고쳐야 합니다.**

---

## 위기 문맥 탐지는 여기 없습니다

API 명세 초안은 `POST /internal/analyze/crisis` 를 이 서버에 두었지만, 구현은
비즈니스 서버에 있습니다.

1. `NFR-DV-003` 이 "1차 키워드 필터는 외부 API 장애 시에도 단독 동작"을 요구합니다.
   위기 탐지를 이 서버로 옮기면 **이 서버가 죽는 순간 위기 탐지가 통째로 멈춥니다.**
2. 위기 탐지에는 학습 모델이 없습니다(안건 3 — 키워드 + OpenAI 프롬프트).
   ML 서버로 보낼 이유가 없고 왕복만 늘어 `NFR-DV-001` 3초 요건에 불리합니다.

→ **`docs/API명세_초안.md` 의 내부 API 절을 이 구조에 맞게 고쳐야 합니다.**

---

## 관련

- [모델 설계·데이터셋](../README.md) — PMData / GLOBEM, 2단계 모델 구조
- [API 명세 초안](../../docs/API명세_초안.md)
- [스키마 정본](../../db/schema.sql)
