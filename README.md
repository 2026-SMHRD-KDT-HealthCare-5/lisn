# 귀기울임 (LISN)

**멀티모달 라이프로그 감정 분석 기반 맞춤형 LLM 케어 및 모니터링 시스템**

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
| Frontend | Flutter (사용자 앱) · React + Chart.js (관리자 관제 대시보드) |
| Backend | FastAPI — 비동기 REST API, 15분 주기 배치 스케줄러, JWT 인증 |
| Database | PostgreSQL — UUID v4 / TIMESTAMPTZ / JSONB |
| AI / ML | PyTorch · LSTM Autoencoder · LightGBM · Pandas / Scikit-learn |
| LLM | OpenAI API (페르소나 대화 · 위기 문맥 탐지 · 세션 요약) / Whisper (STT) |
| 데이터 연동 | Health Connect (Android) |

**플랫폼 범위** — Android 전용입니다. Health Connect 가 Android 전용 API이며, iOS 는 HealthKit 기반 별도 연동 계층이 필요해 본 과제 기간 내 구현 대상에서 제외했습니다.

---

## 아키텍처

```
[수집 계층]   Flutter App · Health Connect (Android)
              활동량 · 수면단계 · 심박 · HRV · 체성분   |   15분 주기
                       |  HTTPS / REST
                       v
[비즈니스 서버]  FastAPI  <->  PostgreSQL
                 JWT 인증 · UPSERT 적재 · 배치 스케줄러
                       |  내부 API
                       v
[AI 추론 서버]   1차  LSTM Autoencoder  ->  anomaly_score (재구성 오차)
                 2차  LightGBM          ->  감정 9종 · risk_score
                      OpenAI            ->  페르소나 대화 · 위기 문맥 탐지
                       |
                       v
[시스템 액션]   NORMAL -> CHAT   |   CAUTION -> CONTENT   |   CRITICAL -> EMERGENCY
```

대용량 시계열 수집과 LLM 추론 부하가 서로 간섭하지 않도록 비즈니스 로직 서버와 AI 추론 서버를 분리했습니다.

---

## 저장소 구조

```
lisn/
├── backend/     FastAPI 비즈니스 서버          (윤일준)
├── ai/          AI 추론 서버 · 모델링          (김건영)
├── frontend/    Flutter 앱 · React 관리자 웹   (함은선)
├── db/
│   └── schema.sql            8개 테이블 DDL + EMOTIONS 마스터 시드
├── docs/
│   ├── extracted/            산출물 HWP·PPTX 본문 추출본 (버전 diff 비교용)
│   └── review/               문서 검수·개정 관리
├── tools/
│   └── hwp2txt.ps1           HWP 본문 추출 스크립트
└── Documents/                산출물 원본 (HWP · PPTX)
```

---

## 시작하기

```bash
git clone https://github.com/2026-SMHRD-KDT-HealthCare-5/lisn.git
```

### DB 구축

PostgreSQL 13 이상이 필요합니다. (12 이하면 `db/schema.sql` 상단 주석의 `pgcrypto` 확장 참고)

```bash
psql -U postgres -c "CREATE DATABASE lisn;"
```

```bash
psql -U postgres -d lisn -f db/schema.sql
```

`schema.sql` 은 05 테이블명세서 원문을 그대로 옮긴 baseline 입니다. **개정 대기 항목이 `[05-A]` `[05-B]` `[05-C]` 주석으로 표시되어 있으니 실행 전에 확인하세요.** 특히 `[05-C]` 는 현재 정의대로면 회원가입 INSERT 가 실패하는 실제 결함입니다.

### 문서 작업

산출물은 모두 HWP 라 git 이 바이너리로 취급해 변경 내용을 볼 수 없습니다. `tools/hwp2txt.ps1` 로 본문을 텍스트로 뽑아 `docs/extracted/` 에 두면 버전 간 diff 비교가 가능합니다. 한컴오피스 설치 없이 동작합니다.

```powershell
.\tools\hwp2txt.ps1 -Path ".\Documents\02_요구사항정의서_귀기울임.hwp"
```

문서를 수정한 뒤에는 추출본도 함께 갱신해 커밋해주세요.

---

## 협업 규칙

- 작업은 개인 브랜치에서 진행하고 `main` 으로 병합합니다. (`feat/`, `docs/`, `fix/` 접두사)
- `.env` 는 절대 커밋하지 않습니다. **OpenAI API 키가 공개 저장소에 올라가면 즉시 폐기해야 합니다.**
- 산출물 문서를 수정하면 `docs/review/문서개정_체크리스트.md` 의 해당 항목에 체크하세요.

---

## 관련 링크

- [Notion 프로젝트 페이지](https://app.notion.com/p/3ab02025254781d18e1ac402a0f59d77) — 자료실 · 진행 현황
- [Google Drive 공유 폴더](https://drive.google.com/drive/folders/1myjO0y6uNJW75gCbehvgbTvioo-Te2EW)

---

## 라이선스

[MIT](LICENSE)
