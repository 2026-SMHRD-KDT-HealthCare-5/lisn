# 귀기울임 (LISN)

**멀티모달 라이프로그 감정 분석 기반 맞춤형 LLM 케어 및 모니터링 시스템**

> **최종 점검** 2026.08.01 · API 30개 · 앱 화면 13개 · 관리자 웹 2개가 전부 연동돼
> **수집 → 분석 → 케어 → 관제 전 구간이 관통합니다.** 남은 구현은 Health Connect
> 실기기 연동이고, 정서 판정은 **규칙 기반 임시값**입니다(아래 「현재 구현 상태」).

Multi-modal Lifelog Emotion Care & Monitoring System — wearable lifelog anomaly detection (LSTM AE + LightGBM) with persona-based LLM care | Flutter · FastAPI · PostgreSQL

스마트워치·체성분계에서 자동 수집되는 라이프로그 시계열을 AI로 분석해 1인가구의 정서적 위험 징후를 조기에 탐지하고, 페르소나 기반 LLM 챗봇으로 정서 케어를 제공하는 모니터링 서비스입니다.

> 본 서비스는 정신건강 상태를 진단하거나 의학적으로 확정하지 않습니다.
> 행동·생체 패턴의 변화를 관찰해 정서적 위험 징후의 가능성을 조기에 포착하고,
> 적절한 케어·상담 연계를 지원하는 **모니터링 보조 도구**입니다.

- **팀** 귀기울임 (스마트인재개발원 KDT 헬스케어 5팀) · 기업주제(라라랩스)
- **기간** 2026.07.17 ~ 2026.08.28 · **최종 발표** 2026.08.28

---

## 팀 구성

| 역할 | 이름 | 담당 |
|---|---|---|
| PM | 이응균 | 일정·산출물 총괄, 기획서 및 DB 명세, 최종 발표 |
| DATA / AI | 김건영 | LSTM Autoencoder · LightGBM 2단계 모델, 위기 대화 탐지 |
| BACKEND / DB | 윤일준 | API 서버, PostgreSQL 설계, Health Connect 연동 |
| FRONTEND | 함은선 | 앱 UI/UX 설계·디자인, 감정 추이 대시보드 |

---

## 기술 스택

| 영역 | 기술 |
|---|---|
| Frontend | Flutter (사용자 앱) · React + Vite (관리자 관제 웹) |
| Backend | FastAPI — 비동기 REST API, JWT 인증, 앱 push UPSERT 수신 |
| Database | PostgreSQL 17 — UUID v4 / TIMESTAMPTZ / JSONB |
| AI / ML | PyTorch · LSTM Autoencoder · LightGBM · Pandas / Scikit-learn |
| LLM | OpenAI API (페르소나 대화 · 위기 문맥 탐지 · 세션 요약) |
| 데이터 연동 | Health Connect (Android) |

> 음성 입력(Whisper STT)은 **이번 범위에서 제외**했습니다. 위기 판정 전에 응답을 흘릴 수
> 없는 구조라 스트리밍도 쓰지 않습니다 — `CRITICAL` 일 때 이미 나간 글자를 회수할 수
> 없기 때문입니다.

**플랫폼 범위** — Android 전용입니다. Health Connect 가 Android 전용 API이며, iOS 는 HealthKit 기반 별도 연동 계층이 필요해 본 과제 기간 내 구현 대상에서 제외했습니다.

---

## 아키텍처

```
[수집 계층]   Flutter App · Health Connect (Android)
              활동량 · 수면단계 · 심박 · HRV · 체성분   |   최소 15분 간격
                       |  HTTPS / REST
                       v
[비즈니스 서버]  FastAPI  <->  PostgreSQL
                 JWT 인증 · 앱 push 수신/UPSERT 적재 · 키워드 위기 필터
                       |  내부 API
                       v
[AI 추론 서버]   1차  LSTM Autoencoder  ->  anomaly_score (재구성 오차)
                 2차  LightGBM          ->  감정 9종 · risk_score
                       |
                       v
[시스템 액션]   NORMAL -> CHAT   |   CAUTION -> CONTENT   |   CRITICAL -> EMERGENCY
```

대용량 시계열 수집과 LLM 추론 부하가 서로 간섭하지 않도록 비즈니스 로직 서버와 AI 추론 서버를 분리했습니다.

**위기 문맥 탐지는 비즈니스 서버에 둡니다.** `NFR-DV-003` 이 외부 API 장애 시에도 키워드
필터 단독 동작을 요구하므로, AI 추론 서버에 두면 그 서버가 죽을 때 같이 죽습니다.

---

## 현재 구현 상태 (2026.08.01)

| 영역 | 상태 |
|---|---|
| 백엔드 API | 30개 **구현·검증 완료**. 회귀 테스트 45건 |
| Flutter 앱 | 화면 13개 **전부 실제 API 연동**. 목업 없음. 테스트 17건 |
| 관리자 관제 웹 | 로그인·역할 가드 + 분포·대상자·상세 3개 탭 완료 |
| AI 추론 서버 | 구동 완료. **판정은 규칙 기반 임시값** ⚠ |
| Health Connect | **미구현.** 권한 화면 UI 만 있음 |

> ### ⚠ 정서 판정 수치를 성능 근거로 쓰지 마세요
>
> `model_version` 이 `rule-placeholder-v0` 이면 모델 결과가 아니라 임의 임계값입니다.
>
> **이번 과제에서는 모델을 학습하지 않습니다.** GLOBEM 공개 샘플 4개를 다 합쳐도
> 참가자 40명이라 ROC-AUC **0.528**(95% 구간이 0.5 를 포함) — 무작위와 구분되지
> 않습니다. 전체 데이터(497명)는 PhysioNet 자격 심사가 **최대 45일**이라 8/28 발표까지
> 남은 27일로는 승인돼도 쓸 시간이 없습니다. 실측 근거는 [`ai/README.md`](ai/README.md).
>
> 학습 대신 **전처리 → 추론 → 적재 → 액션 전환 파이프라인의 완성도**로 갑니다.
> `_predict()` 하나만 바꾸면 모델이 들어가도록 계약을 고정해 뒀습니다.

> ### LLM 은 현재 Gemini 로 돕니다 — 임시입니다
>
> `.env` 의 `LLM_PROVIDER` 로 전환합니다. 평소 개발은 Gemini(무료 한도), 정확도 검사·
> 시연은 OpenAI. **산출 문서의 "외부 OpenAI API" 가 정본**이고, OpenAI 경로는 살아
> 있습니다. Gemini 는 OpenAI 호환 엔드포인트라 SDK 는 `openai` 를 그대로 씁니다.

---

## 저장소 구조

```
lisn/
├── backend/     FastAPI 비즈니스 서버          (윤일준)
├── ai/
│   ├── server/              FastAPI 추론 서버 (포트 8001)   (김건영)
│   ├── preprocess/          라이프로그 전처리
│   └── train/               2단계 모델 학습 스크립트
├── frontend/
│   ├── app/                 Flutter 사용자 앱               (함은선)
│   ├── admin/               React + Vite 관리자 관제 웹
│   └── design/              화면 시안 (앱 빌드 제외)
├── db/
│   ├── schema.sql           8개 테이블 DDL + EMOTIONS 마스터 시드
│   └── seed_healing_contents.sql   힐링 콘텐츠 시드
├── docs/
│   ├── extracted/           산출물 HWP·PPTX 본문 추출본 (버전 diff 비교용)
│   ├── llm/                 LLM 작업 규칙 · 사용 이력
│   └── review/              문서 검수·개정 관리
├── tools/
│   ├── start-dev.ps1         백엔드 · AI 서버 · 관리자 웹 · Flutter 통합 실행
│   ├── doc2txt.py            PDF·PPTX 기준 본문 추출 스크립트
│   └── hwp2txt.ps1           HWP 직접 파싱 보조 스크립트
├── .vscode/tasks.json        VS Code 공용 실행 작업
├── lisn.code-workspace       팀 공용 VS Code 워크스페이스
└── Documents/                산출물 원본 (HWP · PPTX)
```

---

## 시작하기

```bash
git clone https://github.com/2026-SMHRD-KDT-HealthCare-5/lisn.git
```

### DB 구축

**PostgreSQL 17 로 고정합니다.** 팀 재현성을 위해 버전을 통일합니다.
(13 미만이면 `db/schema.sql` 상단 주석의 `pgcrypto` 확장 참고)

```bash
psql -U postgres -c "CREATE DATABASE lisn;"
```

```bash
psql -U postgres -d lisn -f db/schema.sql
```

`schema.sql` 은 05 테이블명세서와 정합을 맞춘 현재 스키마 정본입니다. 8개 테이블과
`EMOTIONS` 9종 시드를 생성합니다. 기존 DB가 구버전이면 개발 단계에서는 스키마를 다시
적용합니다.

콘텐츠 추천(`CAUTION` 액션)을 쓰려면 힐링 콘텐츠도 넣습니다.

```bash
psql -U postgres -d lisn -f db/seed_healing_contents.sql
```

관리자 관제 화면(위험도 분포 · 위기 사건 이력)은 판정 이력이 있어야 그려집니다.
실제 라이프로그를 14일 쌓지 않고 확인하려면 데모 페르소나를 넣습니다.

```bash
psql -U postgres -d lisn -f db/seed_demo_persona.sql
```

> ⚠ **만들어낸 데이터입니다.** `model_version` 이 `seed-demo-v0` 로 박혀 있어 실제
> 판정과 구분됩니다. 성능 근거로 쓰지 말고 운영 DB 에 넣지 마세요.

### 애플리케이션 실행

최초 1회 의존성과 `backend/.env`를 준비한 뒤에는 저장소 루트에서 한 명령으로
백엔드·AI 추론 서버·관리자 웹·Flutter를 각각 새 터미널에 실행할 수 있습니다.

```powershell
.\tools\start-dev.ps1
```

실행하지 않고 준비 상태만 확인하려면 `.\tools\start-dev.ps1 -Check`를 사용합니다.
VS Code에서는 `lisn.code-workspace`를 열고 `Ctrl+Shift+B`를 누르면 같은 통합 실행 작업이
동작합니다. Flutter 창에는 실행 중인 Android 에뮬레이터 또는 연결된 기기가 필요합니다.

개별 실행이 필요하면 다음 기존 명령을 사용합니다.

```powershell
Copy-Item backend\.env.example backend\.env
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd backend
uvicorn app.main:app --reload
```

```powershell
cd frontend\app
flutter pub get
flutter run
```

```powershell
cd frontend\admin
npm install
npm run dev
```

```powershell
cd ai\server
uvicorn main:app --reload --port 8001
```

환경별 DB 접속 정보와 비밀값은 `backend/.env`에만 넣고 커밋하지 않습니다.

> **AI 추론 서버는 `.env` 를 스스로 읽지 않습니다.** 개별 실행할 때는 `AI_DATABASE_URL`
> 이나 `DATABASE_URL` 을 직접 넘기세요. `start-dev.ps1` 은 `backend\.env` 에서 읽어
> 넘겨줍니다.

> **관리자 웹은 5173 포트여야 합니다.** 백엔드 `CORS_ORIGINS` 가 그 주소만 허용합니다.
> 이전 vite 인스턴스가 5173 을 잡고 있으면 새 창이 5174 로 뜨고 요청이 전부 CORS 로
> 막힙니다. 먼저 남은 프로세스를 정리하세요.
>
> **`role` 승격은 API 에 즉시 반영됩니다.** `require_admin` 이 JWT 클레임이 아니라
> **DB 의 `role`** 을 읽기 때문입니다(`tests/test_admin.py` 로 고정). 토큰에 role 이
> 들어가 있지만 아무도 읽지 않습니다.
>
> **다만 관리자 웹은 재로그인이 필요합니다.** 로그인 응답의 role 로 세션 저장 여부를
> 정하기 때문에(`admin/src/session.js`), 승격 전에 로그인해 뒀다면 세션 자체가 없습니다.

### 문서 작업

산출물 원본은 바이너리라 Git diff로 본문을 비교할 수 없습니다. HWP를 PDF로 내보낸 뒤
`tools/doc2txt.py`를 실행해 `docs/extracted/`를 갱신하는 방식이 가장 정확합니다.
HWP 직접 확인이 필요할 때만 `tools/hwp2txt.ps1`을 보조로 사용합니다.

```powershell
python tools\doc2txt.py
```

문서를 수정한 뒤에는 추출본도 함께 갱신해 커밋해주세요.

---

## 협업 규칙

- 작업은 개인 브랜치에서 진행하고 `main` 으로 병합합니다. (`feat/`, `docs/`, `fix/` 접두사)
- `.env` 는 절대 커밋하지 않습니다. **API 키(OpenAI·Gemini)가 공개 저장소에 올라가면 즉시 폐기해야 합니다.**
- 산출물 문서를 수정하면 추출본도 갱신하고, 완료 근거는 `docs/review/작업이력.md`에 기록합니다.

---

## 관련 링크

- [Notion 프로젝트 페이지](https://app.notion.com/p/3ab02025254781d18e1ac402a0f59d77) — 자료실 · 진행 현황
- [Google Drive 공유 폴더](https://drive.google.com/drive/folders/1myjO0y6uNJW75gCbehvgbTvioo-Te2EW)

---

## 라이선스

별도 라이선스 파일은 아직 확정·추가되지 않았습니다.
