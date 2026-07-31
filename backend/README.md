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
| `JWT_SECRET` | 아무 긴 문자열 |

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
│   ├── llm.py        OpenAI 호출
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

### 시각 컬럼에는 `TimestampTZ` 를 명시하세요

`Mapped[datetime]` 만 쓰면 SQLAlchemy 가 `timezone=False` 로 추론해 `TIMESTAMP WITHOUT TIME ZONE` 을 만듭니다. 그 상태로 tz-aware 값을 넣으면 asyncpg 가 죽습니다. 04 문서는 전 컬럼 `TIMESTAMPTZ` 를 규정합니다.

### 판단은 서버가 끝냅니다

감정→위험도→액션 매핑을 클라이언트에 복제하지 않습니다. `action` 필드까지 확정해서 내려보내고 클라이언트는 렌더만 합니다.

### `role` 은 JWT 에 박힙니다

`UPDATE users SET role='ADMIN'` 만 하고 기존 토큰을 쓰면 계속 403 입니다. **승격 후 재로그인**해야 합니다.

---

## 테스트

```powershell
python -m pytest -q
```

개발 DB 를 그대로 씁니다. 테스트마다 고유 계정을 만들고 끝나면 지우므로 기존 데이터에 영향이 없습니다.

주석에 **어느 요구사항을 지키는 테스트인지** 적혀 있습니다. 실패하면 그 주석부터 읽으세요.

> `pytest.ini` 의 `asyncio_default_*_loop_scope = session` 을 지우지 마세요. asyncpg 커넥션 풀이 이벤트 루프에 묶여 있어, 테스트마다 루프를 새로 만들면 두 번째 테스트부터 `Event loop is closed` 로 죽습니다.

---

## 외부 의존

| 대상 | 없을 때 동작 |
|---|---|
| **PostgreSQL** | 필수. 없으면 기동은 되지만 `/health/db` 가 503 |
| **OpenAI** | 없어도 동작. 챗봇은 정형 대체 응답, **위기 탐지는 키워드 필터로 계속 동작** (`NFR-DV-003`) |
| **AI 추론 서버** | 없어도 동작. 라이프로그 push 는 성공하고 분석만 건너뜀 |
| **SMTP** | 미설정. 비밀번호 재설정 토큰이 **로그로 출력**됨 |

> ⚠ **운영 전에 반드시** — 재설정 토큰 로그 출력을 제거하세요(`api/v1/auth.py`). 로그에 토큰이 그대로 남습니다.

DB 연결이 안 되면 **PostgreSQL 로그를 먼저 보세요.** asyncpg 는 원인을 감추는 메시지를 던집니다.

```
C:\Program Files\PostgreSQL\17\data\log\
```

---

## 미구현

| 항목 | 비고 |
|---|---|
| `GET /reports/export` (PDF) | 서버 생성이냐 클라이언트 생성이냐 결정 필요. `reports.py` 에 `TODO(PDF)` |
| `POST /chat/sessions/{id}/voice` | Whisper STT. 명세만 있음 |
| `HEALING_CONTENTS` 데이터 | 비어 있어 추천이 0건. [큐레이션 기준](../docs/review/힐링콘텐츠_큐레이션.md) 참조 |
| LLM 2차 문맥 판정 검증 | API 키 설정 후 재평가 필요. `docs/llm/USAGE_LOG.md` LLM-002 |

---

## 관련 문서

- [API 명세 초안](../docs/API명세_초안.md) — 구현 후에는 `/docs`(OpenAPI)가 정본
- [API 설계 사전 결정](../docs/review/API설계_사전결정.md) — **바꾸기 전에 반드시 확인**
- [LLM 작업 규칙](../docs/llm/PROMPT_REFERENCE.md) · [사용 이력](../docs/llm/USAGE_LOG.md)
