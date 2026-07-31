# 프론트엔드 인수인계 — Codex 용

> 이 문서만 읽고도 작업을 시작할 수 있게 썼습니다. 대화 맥락 없이 단독으로 성립합니다.
> **최종 갱신** 2026.07.31

---

## 0. 한 문단 요약

귀기울임(LISN)은 스마트워치 라이프로그를 AI로 분석해 1인가구의 정서 위험을 조기 감지하고
페르소나 LLM 챗봇으로 케어하는 Android 앱입니다. 화면설계서가 UI 범위의 정본입니다.
Flutter 인증 흐름과 React 관리자 로그인은 구현됐고, 나머지 업무 화면은 문서의 13개 앱
화면·관리자 웹 2개 기준으로 계속 재구축합니다.

---

## 1. 먼저 읽을 것

| 파일 | 왜 |
|---|---|
| `docs/review/화면설계서_개정안.md` | **화면 15개의 명세.** Part D 에 현재 앱 파일과의 대응표 |
| `docs/API명세_초안.md` | 엔드포인트 34개. 요청·응답 스키마 |
| `docs/review/API설계_사전결정.md` | 왜 그렇게 설계했는지. 바꾸기 전에 반드시 확인 |
| `db/schema.sql` | 스키마 정본. 모델 필드는 여기서 맞춤 |
| `docs/design/README.md` | 시안 만드는 방법 · 팔레트 |

---

## 2. 현재 상태

### 코드 위치

`함은선` 브랜치에서 프론트엔드 작업을 이어갑니다. 2026.07.31 기준 main 최신 커밋을
fast-forward로 반영한 상태입니다.

```
frontend/
├── app/                    Flutter 사용자 앱
│   ├── lib/
│   │   ├── main.dart
│   │   ├── config/         API base URL, 환경 분기
│   │   ├── models/         인증 DTO
│   │   ├── services/       HTTP 클라이언트·토큰 저장·인증 API
│   │   ├── screens/        9개 파일 (인증은 API 연동, 업무 데이터는 목업)
│   │   ├── theme/app_theme.dart
│   │   └── widgets/common_widgets.dart
│   └── android/            패키지 com.lisn.maeume · minSdk 26
├── admin/                  Vite + React 관리자 웹
└── design/                 디자인 시안
```

### 무엇이 없나

- 인증 외 화면의 서버 통신은 아직 없습니다. 로그인·회원가입·비밀번호 재설정 API 6개는 연동 완료됐습니다
- 상태관리 패키지 없음 (`setState` 만)
- Health Connect 연동 패키지 없음
- 관리자 웹은 로그인·`ADMIN` 역할 가드·대시보드 셸까지 구현됐고, 실제 관제 데이터 API 연동이 남았습니다

### 인증 연동 완료

- `http` 공통 클라이언트와 `flutter_secure_storage` 토큰 저장
- access token 만료 확인을 포함한 인증 게이트
- FastAPI 오류 `detail` 표시와 인증 요청의 401 로그아웃 처리
- 로그인·회원가입·이메일 중복 확인·로그아웃·비밀번호 재설정 요청/확정
- 기본 Base URL은 Android 에뮬레이터용 `http://10.0.2.2:8000/api/v1`
- `flutter analyze`·`flutter test`·Android debug APK 빌드 통과

### 화면 시안

`docs/design/`의 신규 화면 시안 6장과 원본 HTML은 모두 완성됐습니다. Flutter·React 구현 시 동일한 팔레트와 차트 규격을 기준으로 사용하세요.

### 화면 대응

| 화면 ID | 현재 파일 | 할 일 |
|---|---|---|
| `MAIN_LOGIN_01` | `login_screen.dart` | 완료 — 실제 로그인 API·비밀번호 찾기. **「로그인 유지」 없음** |
| `MAIN_LOGIN_02` | `password_reset_screen.dart` | 완료 — 재설정 요청·확정 API |
| `MAIN_JOIN_01` | `join_screen.dart` STEP01 | 유지 |
| `MAIN_JOIN_02` | `join_screen.dart` STEP02 | 완료 — 키(`height_cm`) 선택 입력·회원가입 API |
| `MAIN_JOIN_03` | `join_screen.dart` STEP03 | UI 일부 완료 — Health Connect 권한 연동 필요 |
| `MAIN_HOME_01` | `home_screen.dart` | 유지 |
| `MAIN_CHAT_01` | `chat_screen.dart` 성격 선택부 | 유지 |
| `MAIN_CHAT_02` | `chat_screen.dart` 대화부 | 수정 — 대화 기록 조회·상세·삭제 추가 |
| `MAIN_LIFELOG_01` | `lifelog_screen.dart` | **전면 재작성** |
| `MAIN_REPORT_01` | 없음 | 신규 — 정서 리포트 |
| `MAIN_SETTING_01` | `settings_screen.dart` | 실제 로그아웃 완료 — 설정·기기 API 연동 필요 |
| `MAIN_SETTING_02` | 없음 | 신규 — 계정 관리·탈퇴 |
| `MAIN_EMERGENCY_01` | 없음 | **신규 · 최우선** |
| `ADMIN_LOGIN_01` | `admin/src/App.jsx` | 완료 — React, 실제 인증 API·역할 가드 |
| `ADMIN_DASH_01` | `admin/src/App.jsx` | 셸 완료 — 관리자 조회 API 구현 후 데이터 연동 |

`join_screen.dart` 는 약관 동의와 정보 입력이 한 파일에 STEP 으로 들어가 있습니다. 문서는 3개 화면으로 정의하므로 **분리를 권합니다.**

---

## 3. 반드시 지켜야 할 설계 원칙

### ⭐ 판단 로직을 클라이언트에 두지 마세요

감정→위험도 매핑(`ANGER` 는 점수 70 이상이면 CRITICAL 등)은 **서버가 확정**해서 내려줍니다. 응답의 `action` 필드를 그대로 따르세요.

```json
{ "reply": "...", "risk": { "level": "CRITICAL", "action": "EMERGENCY" } }
```

- `CHAT` → 일반 대화 렌더
- `CONTENT` → 힐링 콘텐츠 추천 표시
- `EMERGENCY` → **콘텐츠 추천을 즉시 중단하고** `MAIN_EMERGENCY_01` 로 전환

규칙을 클라이언트에 복제하면 서버와 반드시 어긋납니다.

### ⭐ `MAIN_EMERGENCY_01` 은 3초 이내에 떠야 합니다

`NFR-TS-001` 요건입니다. 별도 API 를 호출하지 말고 **이미 받은 응답의 `action` 으로 즉시 전환**하세요. 조회를 한 번 더 돌면 요건을 못 지킵니다.

### ⭐ 위기 화면에 경고색을 쓰지 마세요

정신건강 위기 UI 에서 빨강·주황은 불안을 키워 회피를 유발합니다. 브랜드 블루를 유지하고 주목도는 **구조**로 만드세요 — 하단 네비게이션 제거, 요소 최소화, 주행동 버튼에만 그림자.

문구도 진단·단정이 아닌 권유조로 씁니다(`FR-AI-002` 진단 금지).

### PII 는 그대로 보내세요

대화 내용의 마스킹은 **서버가 저장 시점에** 합니다. 클라이언트에서 미리 가리지 마세요.

### 시각은 UTC

API 는 전부 ISO 8601 UTC 입니다. 로컬 변환은 표시 직전에만 하세요.

---

## 4. 하지 말아야 할 것

| 항목 | 이유 |
|---|---|
| **「로그인 유지」 체크박스** | 이 프로젝트는 **refresh token 이 없습니다.** access token 단일에 만료 24시간입니다. 자동 로그인을 넣으려면 인증 설계 전체가 바뀝니다 |
| **응답 스트리밍(SSE)** | 위기 판정 전에 글자를 흘리면 CRITICAL 일 때 회수할 수 없습니다. 단발 응답으로 갑니다 |
| **iOS 대응** | Health Connect 가 Android 전용 API 라 범위에서 제외됐습니다. `platform_type` enum 에 `APPLE_HEALTH` 가 남아 있지만 구현하지 않습니다 |
| **`minSdk` 를 26 미만으로** | Health Connect 가 API 26 을 요구합니다. 낮추면 연동 패키지 추가 시 manifest merger 에서 빌드가 깨집니다 |
| **감정·위험도 상수 하드코딩** | 서버 응답을 그대로 쓰세요 |

---

## 5. 착수 순서 제안

1. **신규 앱 화면** — `MAIN_EMERGENCY_01` 최우선, 이후 웨어러블·리포트·계정 관리
2. **백엔드 API 순서에 맞춘 연동** — `users`·`devices` → `lifelog` → `chat`
3. **기존 목업 데이터 제거** — 각 API가 완성되는 즉시 화면 DTO와 상태 처리 추가
4. **관리자 대시보드 데이터 연동** — 관리자 조회 API가 나온 뒤 위험도 분포·고위험군 연결

---

## 6. 화면 시안이 필요하면

`docs/design/` 에 만드는 방법이 정리돼 있습니다. 요약하면:

- 기존 시안 PNG 에서 **픽셀로 팔레트를 추출**합니다 (눈대중은 어긋납니다)
- HTML/CSS 로 그리고 **Edge 헤드리스**로 PNG 를 굽습니다 (Node·Python 불필요)
- 캔버스는 앱 **390×844**, 관리자 웹 **1280×800**
- **아이콘은 이모지 대신 인라인 SVG** — 이모지는 OS 가 자기 색으로 렌더해 팔레트 밖으로 튑니다
- 폰트는 Pretendard 를 CDN 으로 부릅니다. 설치 불필요

완성 예시가 `docs/design/MAIN_EMERGENCY_01.png` 이고 원본 HTML 이 `src/` 에 있습니다. **그 파일을 복사해서 고치는 게 가장 빠릅니다.**

### 팔레트

| 용도 | 값 |
|---|---|
| 배경 | `#EDF2FF` |
| 카드 | `#FFFFFF` |
| 제목 텍스트 | `#24325F` |
| 보조 텍스트 | `#A8ACBA` |
| 포인트 | `#8A9CF0` |
| 주행동 버튼 | `#5A6BE0` |
| 파스텔 민트 / 블루 / 피치 | `#EAF8F4` / `#EAF5FF` / `#FFF0E9` |

> 피치는 **작은 액센트로만** 쓰세요. 카드 하나를 통째로 칠하면 브랜드 톤에서 튑니다.

---

## 7. 남은 UI 결정·확인

| 항목 | 상태 |
|---|---|
| 긴급 상담 번호 표기 | 확인 완료 — 위기 화면은 `109` 단일 노출 |
| 앱 상단 `마음이 ♥` 하트 | 현재 코드는 텍스트 + 포인트 색. 최종 자산 표기는 팀 확인 필요, SVG 권장 |
| `height_cm` 입력 위치 | `MAIN_JOIN_02` 선택 입력으로 구현 완료 |
| 화면설계서 PPTX 배치 | 완성 시안 6장 배치와 기존 화면의 ❶❷❸ 마커 작업 남음 |

---

## 8. 빌드 관련

```bash
cd frontend/app
flutter clean      # 폴더 구조가 바뀐 뒤에는 필수
flutter pub get
flutter run
```

패키지명이 `com.example.maeume_care` → `com.lisn.maeume` 로 바뀌었습니다. 캐시가 남아 있으면 빌드가 깨집니다.

빌드가 안 되면 `frontend/restructure` 계열 커밋 중 패키지명(`f35568c`)이나 `minSdk`(`533605d`) 커밋만 되돌리면 구조 변경은 유지됩니다.
