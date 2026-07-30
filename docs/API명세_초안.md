# API 명세 초안

> **작성일** 2026.07.30 · 설계 근거는 [`review/API설계_사전결정.md`](review/API설계_사전결정.md)
>
> **이 문서는 착수용 초안입니다.** 구현이 시작되면 FastAPI 가 생성하는 OpenAPI(`/docs`)가 정본이 되고
> 이 문서는 역할이 끝납니다. 갱신하지 마세요. 산출물 제출 대상이 아닙니다.
>
> 도출 근거 — `db/schema.sql`(정본) · 02 유스케이스 14건 · 화면 15개([`review/화면설계서_개정안.md`](review/화면설계서_개정안.md))

---

## 공통 규약

| 항목 | 값 |
|---|---|
| Base URL | `/api/v1` |
| 인증 | `Authorization: Bearer <JWT>` · access token 단일 · 만료 24시간 |
| JWT 페이로드 | `sub`(user_id) · `role`(USER/ADMIN) · `exp` |
| 시각 | ISO 8601 **UTC** 문자열 (`2026-07-30T12:34:56Z`) |
| 네이밍 | `snake_case` |
| 페이징 | `?limit=20&offset=0` · 시계열은 항상 최신순 고정 |
| 에러 | FastAPI 기본 `{ "detail": "..." }` + HTTP 상태코드 |

### 상태코드 사용

| 코드 | 쓰임 |
|---|---|
| `400` | 요청 형식·유효성 오류 |
| `401` | 토큰 없음·만료·위조 |
| `403` | 토큰은 유효하나 권한 부족 (`role != ADMIN` 인데 관리자 API 호출) |
| `404` | 대상 없음 |
| `409` | 중복 (이메일 등) |
| `413` | 배치 크기 초과 |
| `503` | 외부 API(OpenAI·Health Connect) 장애 |

### 원칙

- **판단은 서버가 끝낸다.** 감정→위험도 매핑(`ANGER` 70 기준 분기 등)을 클라이언트에 복제하지 않는다. 서버가 `action` 까지 확정해 내려주고 클라이언트는 렌더만 한다
- **PII 마스킹은 저장 시점에 서버가 한다.** 클라이언트는 원문을 그대로 보낸다

---

# 외부 API

앱(Flutter) · 관리자 웹(React) → 비즈니스 서버

## 1. 인증

### `POST /auth/signup`
`MLCM_100` · `MAIN_JOIN_01` `MAIN_JOIN_02`

```json
{
  "email": "user@example.com",
  "password": "...",
  "name": "홍길동",
  "birth_date": "1994-05-16",
  "gender": "MALE",
  "height_cm": 173.5,
  "phone": "010-0000-0000",
  "terms_agreed": true,
  "sensitive_agreed": true
}
```

`phone` · `height_cm` 은 선택. `terms_agreed` · `sensitive_agreed` 는 **각각 별도 항목**으로 받는다(`05-K`). 서버가 동의 일시를 기록한다.

```json
201 → { "user_id": "...", "access_token": "...", "expires_at": "..." }
409 → 이메일 중복
```

### `GET /auth/check-email?email=...`
`MAIN_JOIN_02` ❸ 중복 확인 → `{ "available": true }`

### `POST /auth/login`
`MLCM_100` · `MAIN_LOGIN_01` · `ADMIN_LOGIN_01`

```json
{ "email": "...", "password": "..." }

200 → {
  "access_token": "...",
  "expires_at": "2026-07-31T12:00:00Z",
  "user": { "user_id": "...", "name": "...", "role": "USER", "persona_type": "FRIEND" }
}
```

관리자 웹도 **같은 엔드포인트**를 쓴다. 응답의 `role` 이 `ADMIN` 이 아니면 웹이 대시보드로 보내지 않는다.

### `POST /auth/logout`
`MLCM_101` — 서버는 `204` 만 반환하고 클라이언트가 토큰을 폐기한다. 블랙리스트를 두지 않는다(사전결정 1절).

### `POST /auth/password-reset/request`
`MLCM_102` · `MAIN_LOGIN_02`

```json
{ "email": "..." }
200 → { "message": "발송 완료" }
```

**미가입 이메일이어도 동일한 200 을 반환하고 실제 메일은 보내지 않는다.** 가입 여부가 노출되지 않도록 하는 `MLCM_102` 5단계 요건이다.

### `POST /auth/password-reset/confirm`
`{ "token": "...", "new_password": "..." }` → `204`

---

## 2. 사용자 · 설정

### `GET /users/me` → 프로필 + `role` + `persona_type`

### `PATCH /users/me`
`MLCM_300` 페르소나 변경 · `MAIN_SETTING_01`

```json
{ "persona_type": "COUNSELOR", "fcm_token": "..." }
```

### `PATCH /users/me/password`
`MAIN_SETTING_02` ❷ — `{ "current_password": "...", "new_password": "..." }`

### `DELETE /users/me`
`MLCM_103` · `MAIN_SETTING_02`

```json
{ "password": "..." }
204
```

본인 확인용 비밀번호를 요구한다. `USERS` 행 삭제로 `LIFELOG_METRICS` · `BODY_COMPOSITION_METRICS` · `CHAT_SESSIONS` · `EMOTION_RISK_SCORES` · `DEVICE_HEALTH_CONNECTIONS` 가 CASCADE 삭제된다.

---

## 3. 디바이스 연동

### `POST /devices/connections`
`MLCM_110` · `MAIN_JOIN_03`

```json
{
  "device_name": "Galaxy Watch 6",
  "platform_type": "HEALTH_CONNECT",
  "permission_granted": true,
  "consent_scopes": { "activity": true, "sleep": true, "body_composition": false }
}
201 → { "connection_id": "...", "agreed_at": "..." }
```

### `GET /devices/connections`
`MAIN_SETTING_01` ❶ — 연동 상태와 `last_synced_at` 반환

### `PATCH /devices/connections/{connection_id}`
항목별 동의 철회. `consent_scopes` 만 보낸다.

```json
{ "consent_scopes": { "activity": true, "sleep": true, "body_composition": false } }
```

**철회된 항목은 즉시 수집 대상에서 제외되지만 기존 데이터는 삭제하지 않는다**(`MLCM_110` 종료조건). 완전 삭제는 회원 탈퇴로만 가능하다.

---

## 4. 라이프로그

### `POST /lifelog/batch` ⭐
`MLCM_200` — 앱 push 의 핵심 엔드포인트

```json
{
  "items": [
    {
      "collected_at": "2026-07-30T09:00:00Z",
      "steps": 3200, "distance": 2100, "calories": 180,
      "activity_start_at": "...", "activity_end_at": "...", "total_active_min": 42,
      "sleep_start_at": "...", "sleep_end_at": "...",
      "total_sleep_min": 280, "deep_sleep_min": 65, "light_sleep_min": 180,
      "rem_sleep_min": 35, "awake_min": 20, "sleep_onset_min": 15,
      "sleep_efficiency_pct": 71.0,
      "heart_rate": 72, "hrv": 45.2
    }
  ]
}

200 → { "accepted": 12, "last_synced_at": "2026-07-30T09:15:00Z" }
413 → 배치 200건 초과
```

- `(user_id, collected_at)` **UNIQUE 기준 UPSERT**. 재전송해도 중복되지 않는다
- **`last_synced_at` 은 서버가 확정해 돌려준다.** 앱이 자기 시계로 갱신하면 단말 시간이 틀어졌을 때 데이터가 영구 유실된다
- 적재 완료 후 서버가 내부 API 로 분석을 트리거한다(`MLCM_210`)

### `POST /body-composition`
체성분은 측정 시점에만 발생하므로 라이프로그와 분리한다.

```json
{ "measured_at": "...", "weight_kg": 68.4, "body_fat_kg": 14.2,
  "muscle_mass_kg": 30.1, "skeletal_muscle_kg": 27.8, "bmr_kcal": 1520 }
```

### `GET /lifelog?from=&to=&granularity=day`
`MAIN_LIFELOG_01` — 기간별 조회. `granularity` 는 `day` `week` `month`

### `GET /body-composition?from=&to=`

---

## 5. 챗봇

### `POST /chat/sessions`
`MLCM_300` · `MAIN_CHAT_01`

```json
{ "persona_type": "FRIEND" }
201 → { "session_id": "...", "greeting": "...", "started_at": "..." }
```

인사말을 서버가 생성해 함께 내린다. 클라이언트가 하드코딩하면 페르소나별 톤이 어긋난다.

### `POST /chat/sessions/{session_id}/messages` ⭐⭐
`MLCM_310` `MLCM_320` · `MAIN_CHAT_02`

```json
{ "content": "요즘 너무 힘들고 다 내려놓고 싶어" }

200 → {
  "message_id": "...",
  "reply": "많이 힘드셨겠어요. ...",
  "risk": { "level": "NORMAL|CAUTION|CRITICAL", "action": "CHAT|CONTENT|EMERGENCY" }
}
```

- 서버는 **위기 문맥 탐지와 응답 생성을 병렬 호출**한다(`NFR-DV-001` 3초 요건)
- `CRITICAL` 이면 `reply` 를 `null` 로 두고 `action: "EMERGENCY"` 만 내린다. 병렬로 생성된 일반 응답은 **서버가 버린다**
- **스트리밍을 쓰지 않는다.** 위기 판정 전에 글자를 흘리면 `CRITICAL` 일 때 이미 나간 글자를 회수할 수 없다
- OpenAI 장애 시 `NFR-DV-003` 에 따라 정형 대체 응답을 내리되, **1차 키워드 필터는 백엔드 내부에서 독립 동작**하므로 `risk` 는 계속 채워진다

### `POST /chat/sessions/{session_id}/voice`
음성 입력. `multipart/form-data` 로 오디오 업로드 → Whisper STT → 위와 동일 응답.
**STT 완료 즉시 원본 음성 파일을 삭제한다**(`NFR-DE-002`).

### `PATCH /chat/sessions/{session_id}/end`
`MLCM_310` 종료조건 — `ended_at` 기록 + LLM 요약 생성 → `session_summary` 저장

### `GET /chat/sessions?limit=&offset=`
`MAIN_CHAT_02` ❹ 대화 기록 목록. `session_summary` 와 `started_at` 만 반환(본문 제외).

### `GET /chat/sessions/{session_id}`
❺ 상세 — `messages`(마스킹된 상태) 전체

### `DELETE /chat/sessions/{session_id}`
❻ 삭제 → `204`

---

## 6. 홈 · 리포트 · 콘텐츠

### `GET /home`
`MAIN_HOME_01` — 화면 하나가 여러 리소스를 쓰므로 **합성 엔드포인트**로 둔다. 개별 호출 4번이면 첫 화면 지연이 커진다.

```json
{
  "emotion_today": { "emotion_code": "ANXIETY", "emotion_name": "불안",
                     "emotion_score": 82.0, "risk_level": "CAUTION" },
  "lifelog_summary": { "total_sleep_min": 455, "steps": 8521, "hrv": 45.2 },
  "ai_summary": "오늘은 평소보다 수면이 짧았어요. ...",
  "recommendations": [ { "content_id": "...", "category": "MUSIC", "title": "...", "external_url": "..." } ],
  "action": "CONTENT"
}
```

`action` 이 `EMERGENCY` 면 클라이언트는 추천을 렌더하지 않고 `MAIN_EMERGENCY_01` 로 전환한다(`MLCM_510` 2단계 — 콘텐츠 추천 즉시 중단).

### `GET /reports?from=&to=`
`MLCM_500` · `MAIN_REPORT_01` — 감정 스코어 추이 + 위험 단계 분포 + 라이프로그 결합 시계열 + 요약 문구.
분석 이력이 1일 미만이면 `409` 와 안내 메시지.

### `GET /reports/export?from=&to=`
PDF 생성 → `application/pdf`

### `GET /contents/recommendations`
`MLCM_400` — `CAUTION` 판정 시 감정별 큐레이션. 홈에 포함되지만 새로고침용으로 분리.

---

## 7. 관리자

전부 `role == ADMIN` 필요. 아니면 `403`.

### `GET /admin/dashboard`
`MLCM_501` ❶ — `{ "normal": 128, "caution": 34, "critical": 5, "evaluated_at": "..." }`

### `GET /admin/users?risk_level=&limit=&offset=`
❷ 대상자 목록. 기본 정렬은 **위험도 높은 순 → 최근 평가순**.

### `GET /admin/users/{user_id}/report?from=&to=`
❸ — `GET /reports` 와 동일 스키마. 대상 `user_id` 만 관리자가 지정한다.

### `GET /admin/emergency-events?limit=&offset=`
❹ 위기 사건 이력. `EMOTION_RISK_SCORES` 에서 `risk_level = 'CRITICAL'` 인 행을 조회한다. **별도 테이블을 만들지 않는다** — `MLCM_510` 5단계가 요구하는 "판정 이력"이 이미 그 테이블에 있다.

---

# 내부 API

비즈니스 서버 ↔ AI 추론 서버. **인증 없음** — 같은 네트워크 안에 두고 AI 서버 포트를 외부에 열지 않는 것으로 갈음한다(사전결정 7절).

### `POST /internal/analyze/lifelog`
`MLCM_210` — 라이프로그 적재 후 트리거

```json
{ "user_id": "...", "evaluated_at": "..." }

200 → {
  "emotion_code": "ANXIETY",
  "emotion_score": 82.0,
  "anomaly_score": 0.73,
  "risk_level": "CAUTION",
  "risk_score": 68.5,
  "model_version": "v1.0"
}
```

AI 서버가 DB 에서 최근 14일 기준값과 최신 시퀀스를 직접 읽는다. 비즈니스 서버가 페이로드로 실어 보내면 요청이 비대해진다.

**`risk_level` 매핑은 AI 서버가 확정한다.** `EMOTIONS.category` 를 기본값으로 하고 `ANGER` 만 `emotion_score` 70 기준으로 재분류, `CRISIS` 는 무조건 `CRITICAL`(04 문서 6항).

### `POST /internal/analyze/crisis`
`MLCM_320` — 대화 위기 문맥 탐지

```json
{ "user_id": "...", "session_id": "...", "utterance": "...", "recent_turns": [ ... ] }

200 → { "is_crisis": true, "severity": "HIGH", "matched_context": "...", "source": "LLM|KEYWORD" }
```

- 1차 키워드 규칙 필터 → 2차 OpenAI 프롬프트. **JSON 스키마로만 반환하도록 프롬프트에서 제약**한다
- OpenAI 장애 시 키워드 결과만으로 판정하고 `source: "KEYWORD"` 로 표기한다. 이때는 문맥 판단이 불가능하므로 **미탐을 줄이는 보수적 임계치**를 적용한다(`NFR-DV-003`)
- 호출 전에 비즈니스 서버가 PII 를 `[MASK]` 로 치환한다

---

## 엔드포인트 요약

| # | 메서드 · 경로 | 유스케이스 | 화면 |
|---|---|---|---|
| 1 | `POST /auth/signup` | `MLCM_100` | `MAIN_JOIN_01` `_02` |
| 2 | `GET /auth/check-email` | `MLCM_100` | `MAIN_JOIN_02` |
| 3 | `POST /auth/login` | `MLCM_100` | `MAIN_LOGIN_01` `ADMIN_LOGIN_01` |
| 4 | `POST /auth/logout` | `MLCM_101` | `MAIN_SETTING_01` |
| 5 | `POST /auth/password-reset/request` | `MLCM_102` | `MAIN_LOGIN_02` |
| 6 | `POST /auth/password-reset/confirm` | `MLCM_102` | `MAIN_LOGIN_02` |
| 7 | `GET /users/me` | — | 공통 |
| 8 | `PATCH /users/me` | `MLCM_300` | `MAIN_SETTING_01` |
| 9 | `PATCH /users/me/password` | — | `MAIN_SETTING_02` |
| 10 | `DELETE /users/me` | `MLCM_103` | `MAIN_SETTING_02` |
| 11 | `POST /devices/connections` | `MLCM_110` | `MAIN_JOIN_03` |
| 12 | `GET /devices/connections` | `MLCM_110` | `MAIN_SETTING_01` |
| 13 | `PATCH /devices/connections/{id}` | `MLCM_110` | `MAIN_SETTING_01` |
| 14 | `POST /lifelog/batch` | `MLCM_200` | (백그라운드) |
| 15 | `POST /body-composition` | `MLCM_200` | (백그라운드) |
| 16 | `GET /lifelog` | `MLCM_200` | `MAIN_LIFELOG_01` |
| 17 | `GET /body-composition` | `MLCM_200` | `MAIN_LIFELOG_01` |
| 18 | `POST /chat/sessions` | `MLCM_300` | `MAIN_CHAT_01` |
| 19 | `POST /chat/sessions/{id}/messages` | `MLCM_310` `MLCM_320` | `MAIN_CHAT_02` |
| 20 | `POST /chat/sessions/{id}/voice` | `MLCM_310` | `MAIN_CHAT_02` |
| 21 | `PATCH /chat/sessions/{id}/end` | `MLCM_310` | `MAIN_CHAT_02` |
| 22 | `GET /chat/sessions` | `MLCM_310` | `MAIN_CHAT_02` |
| 23 | `GET /chat/sessions/{id}` | `MLCM_310` | `MAIN_CHAT_02` |
| 24 | `DELETE /chat/sessions/{id}` | `MLCM_310` | `MAIN_CHAT_02` |
| 25 | `GET /home` | `MLCM_400` | `MAIN_HOME_01` |
| 26 | `GET /reports` | `MLCM_500` | `MAIN_REPORT_01` |
| 27 | `GET /reports/export` | `MLCM_500` | `MAIN_REPORT_01` |
| 28 | `GET /contents/recommendations` | `MLCM_400` | `MAIN_HOME_01` |
| 29 | `GET /admin/dashboard` | `MLCM_501` | `ADMIN_DASH_01` |
| 30 | `GET /admin/users` | `MLCM_501` | `ADMIN_DASH_01` |
| 31 | `GET /admin/users/{id}/report` | `MLCM_501` | `ADMIN_DASH_01` |
| 32 | `GET /admin/emergency-events` | `MLCM_510` | `ADMIN_DASH_01` |
| I1 | `POST /internal/analyze/lifelog` | `MLCM_210` | — |
| I2 | `POST /internal/analyze/crisis` | `MLCM_320` | — |

**외부 32개 · 내부 2개.**

---

## 유스케이스 커버리지 확인

| 유스케이스 | 대응 |
|---|---|
| `MLCM_100` 회원가입·로그인 | 1·2·3 |
| `MLCM_101` 로그아웃 | 4 |
| `MLCM_102` 비밀번호 재설정 | 5·6 |
| `MLCM_103` 회원 탈퇴 | 10 |
| `MLCM_110` 연동 동의·설정 | 11·12·13 |
| `MLCM_200` 라이프로그 자동 수집 | 14·15 |
| `MLCM_210` AI 정서 분석 | I1 |
| `MLCM_300` 페르소나 선택 | 8·18 |
| `MLCM_310` 공감 대화 | 19~24 |
| `MLCM_320` 위기 문맥 탐지 | I2 |
| `MLCM_400` 콘텐츠 추천 | 25·28 |
| `MLCM_500` 정서 리포트 | 26·27 |
| `MLCM_501` 관리자 관제 | 29~31 |
| `MLCM_510` 긴급 상담 연결 | 19·25 의 `action: EMERGENCY` · 32 |

**14건 전부 커버됩니다.**

`MLCM_510` 은 전용 엔드포인트를 두지 않습니다. 긴급 UI 는 **분석·대화 응답의 `action` 필드로 트리거**되고, 화면 자체는 클라이언트에 이미 있습니다. `NFR-TS-001`(3초 이내 노출)을 지키려면 별도 조회를 한 번 더 도는 구조가 오히려 불리합니다.
