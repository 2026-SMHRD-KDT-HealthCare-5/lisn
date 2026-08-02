# backend

FastAPI 비즈니스 서버. 앱(Flutter)과 관리자 웹(React)이 여기로 붙습니다.

---

## 실행

```powershell
Copy-Item .env.example .env
```

`.env` 에서 최소 두 개를 채웁니다.

| 키 | 값 |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:<비밀번호>@localhost:5432/lisn` |
| `JWT_SECRET` | 아무 긴 문자열. **`CHANGE_ME` 면 서버가 토큰 발급을 거부합니다** |

> ⚠ `JWT_SECRET` 을 예제값 그대로 두면 안 됩니다. **이 저장소는 공개**라 예제값이
> 곧 공개된 서명 키이고, 누구나 `role=ADMIN` 토큰을 만들어 `/admin/*` 으로 전
> 사용자 리포트를 볼 수 있습니다. 그래서 `security._secret()` 이 아예 막습니다.
>
> ```powershell
> python -c "import secrets; print(secrets.token_urlsafe(48))"
> ```

> 비밀번호에 `@` `:` `/` `#` 이 있으면 URL 인코딩이 필요합니다. `@` → `%40`

DB 가 없으면 먼저 만듭니다.

```powershell
psql -U postgres -c "CREATE DATABASE lisn;"
```

```powershell
psql -U postgres -d lisn -f ..\db\schema.sql
```

```powershell
pip install -r requirements.txt
```

```powershell
uvicorn app.main:app --reload
```

http://127.0.0.1:8000/docs 에서 바로 테스트할 수 있습니다.

---

## 구조

```
app/
├── main.py           앱 · 라우터 등록 · /health
├── core/
│   ├── config.py     환경 설정 (.env)
│   ├── database.py   async 엔진 · 세션
│   ├── security.py   bcrypt · JWT · 인증 의존성
│   └── crypto.py     AES-256-GCM 컬럼 암호화
├── models/           db/schema.sql 의 파이썬 매핑
├── schemas/          Pydantic 요청·응답 DTO
├── services/
│   ├── safety.py     PII 마스킹 · 키워드 위기 필터
│   ├── llm.py        LLM 호출 (Gemini | OpenAI 전환)
│   ├── analysis.py   AI 추론 서버 연동
│   └── report.py     리포트 조회 (본인·관리자 공용)
├── api/v1/           엔드포인트
└── data/             키워드 사전 등 설정 데이터
```

---

## 반드시 알아야 할 규칙

### `db/schema.sql` 이 스키마 정본입니다

모델은 그 DDL 의 파이썬 매핑일 뿐입니다.

- **`Base.metadata.create_all()` 을 쓰지 않습니다**
- **alembic 을 쓰지 않습니다.** 정본이 둘이 되면 04·05 문서와 대조할 기준이 파이썬 코드로 옮겨갑니다
- 스키마를 바꿀 때는 `schema.sql` 을 고치고 **DB 를 다시 만듭니다**

> 그 대가로 **둘이 어긋나도 아무것도 알려주지 않습니다.** 한쪽에만 컬럼을 추가하면
> 운영 중에 `UndefinedColumnError` 로 처음 드러납니다. `tests/test_schema_drift.py`
> 가 컬럼 이름 집합을 대조해 이걸 막습니다 — **DB 없이 0.03초에 돕니다.**

### 시각 컬럼에는 `TimestampTZ` 를 명시하세요

`Mapped[datetime]` 만 쓰면 SQLAlchemy 가 `timezone=False` 로 추론해 `TIMESTAMP WITHOUT TIME ZONE` 을 만듭니다. 그 상태로 tz-aware 값을 넣으면 asyncpg 가 죽습니다. 04 문서는 전 컬럼 `TIMESTAMPTZ` 를 규정합니다.

### 판단은 서버가 끝냅니다

감정→위험도→액션 매핑을 클라이언트에 복제하지 않습니다. `action` 필드까지 확정해서 내려보내고 클라이언트는 렌더만 합니다.

### `role` 은 DB 를 봅니다 — JWT 가 아닙니다

`require_admin` 은 토큰의 role 클레임이 아니라 **DB 의 `USERS.role`** 을 읽습니다.
토큰에도 role 이 들어가지만 **아무도 읽지 않습니다.**

- `UPDATE users SET role='ADMIN'` 하면 **기존 토큰 그대로 즉시** 관리자 API 가 열립니다
- 강등도 마찬가지로 즉시입니다. 토큰 만료(24시간)를 기다리지 않습니다

> **관리자 웹은 재로그인해야 합니다.** 로그인 응답의 role 로 세션 저장 여부를 정해서
> (`admin/src/session.js`), 승격 전에 로그인했다면 저장된 세션이 아예 없습니다.
> **403 이 계속 나면 토큰이 아니라 DB 의 role 을 보세요.**

---

## 테스트

```powershell
python -m pytest -q
```

**45건.** 개발 DB 를 그대로 씁니다. 테스트마다 고유 계정을 만들고 끝나면 지우므로 기존 데이터에 영향이 없습니다.

DB 없이 스키마 정합만 보려면 이것만 돌려도 됩니다.

```powershell
python -m pytest tests/test_schema_drift.py -q
```

주석에 **어느 요구사항을 지키는 테스트인지** 적혀 있습니다. 실패하면 그 주석부터 읽으세요.

> `pytest.ini` 의 `asyncio_default_*_loop_scope = session` 을 지우지 마세요. asyncpg 커넥션 풀이 이벤트 루프에 묶여 있어, 테스트마다 루프를 새로 만들면 두 번째 테스트부터 `Event loop is closed` 로 죽습니다.

---

## 외부 의존

| 대상 | 없을 때 동작 |
|---|---|
| **PostgreSQL** | 필수. 없으면 기동은 되지만 `/health/db` 가 503 |
| **LLM** (Gemini \| OpenAI) | 없어도 동작. 챗봇은 정형 대체 응답, **위기 탐지는 키워드 필터로 계속 동작** (`NFR-DV-003`) |
| **AI 추론 서버** | 없어도 동작. 라이프로그 push 는 성공하고 분석만 건너뜀 |
| **SMTP** | **미설정 (범위 밖).** 재설정 메일이 실제로 나가지 않습니다 |

> **비밀번호 재설정은 기능 자체가 문서 요구사항**입니다(`MLCM_102` · `FR-AD-004` 우선순위 상,
> 예외 흐름까지 명세). 빠진 것은 메일 발송 수단뿐이라 기능을 지우지 않았습니다.
>
> 토큰은 **기본적으로 로그에 남지 않습니다.** 개발 중 흐름을 확인하려면
> `PASSWORD_RESET_LOG_TOKEN=true` 로 켜세요. **운영에서는 절대 켜지 마세요** — 로그를 볼 수
> 있는 사람이 누구 계정이든 비밀번호를 바꿀 수 있게 됩니다.

DB 연결이 안 되면 **PostgreSQL 로그를 먼저 보세요.** asyncpg 는 원인을 감추는 메시지를 던집니다.

```
C:\Program Files\PostgreSQL\17\data\log\
```

---

## 미구현

| 항목 | 비고 |
|---|---|
| `HEALING_CONTENTS` 의 `MUSIC`·`FOOD` | `EXERCISE`·`ARTICLE` 은 채워져 있습니다. 나머지 두 카테고리는 팀이 직접 큐레이션합니다 → [기준](../docs/review/힐링콘텐츠_큐레이션.md) |

> **AI 추론 서버의 모델**은 이 저장소 범위가 아닙니다. 데이터 제약으로 이번 과제에서는
> 규칙 기반 판정을 유지합니다 → [`ai/README.md`](../ai/README.md)

### 서버에 만들지 않기로 한 것 (2026.08.01)

| 항목 | 결정 |
|---|---|
| `GET /reports/export` | **클라이언트가 PDF 를 만듭니다.** 서버 엔드포인트를 두지 않습니다. `GET /reports` 응답이 데이터 원본입니다 |
| `POST /chat/sessions/{id}/voice` | 음성 입력은 **이번 범위 제외**. 확장 항목 |
| `POST /internal/analyze/crisis` | 위기 탐지는 **비즈니스 서버에 유지**. `NFR-DV-003` 때문 |

---

## 관련 문서

- [API 명세 초안](../docs/API명세_초안.md) — 구현 후에는 `/docs`(OpenAPI)가 정본
- [API 설계 사전 결정](../docs/review/API설계_사전결정.md) — **바꾸기 전에 반드시 확인**
- [LLM 작업 규칙](../docs/llm/PROMPT_REFERENCE.md) · [사용 이력](../docs/llm/USAGE_LOG.md)
