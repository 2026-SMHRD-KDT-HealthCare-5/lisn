# 프론트엔드 인수인계 — Codex 용

> 이 문서만 읽고도 작업을 시작할 수 있게 썼습니다. 대화 맥락 없이 단독으로 성립합니다.
> **최종 갱신** 2026.08.01

---

## 0. 한 문단 요약

귀기울임(LISN)은 스마트워치 라이프로그를 AI로 분석해 1인가구의 정서 위험을 조기 감지하고
페르소나 LLM 챗봇으로 케어하는 Android 앱입니다. 화면설계서가 UI 범위의 정본입니다.
**앱 화면 13개와 관리자 웹 2개가 모두 실제 API 에 붙었습니다.** 목업 데이터는 남아 있지
않습니다. 남은 것은 Health Connect 실기기 연동과 화면설계서 PPTX 의 디자인 작업입니다.

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

`함은선` 브랜치에서 프론트엔드 작업을 이어갑니다. 2026.08.01 기준 main 최신 커밋을
fast-forward로 반영한 상태입니다.

```
frontend/
├── app/                    Flutter 사용자 앱
│   ├── lib/
│   │   ├── main.dart
│   │   ├── config/         API base URL, 환경 분기
│   │   ├── models/         DTO 6종 + json.dart (공용 파싱 헬퍼)
│   │   ├── services/       HTTP 클라이언트·토큰 저장·업무 API 6종·PDF 조판
│   │   ├── screens/        11개 파일 — 전부 실제 API 연동
│   │   ├── theme/app_theme.dart
│   │   └── widgets/common_widgets.dart
│   ├── test/               17건 (모델 파싱·세션 규칙)
│   └── android/            패키지 com.lisn.maeume · minSdk 26
├── admin/                  Vite + React 관리자 웹 — 로그인 + 관제 3개 탭
└── design/                 디자인 시안
```

### 무엇이 없나

- **Health Connect 연동 패키지 없음.** `MAIN_JOIN_03` 의 권한 화면은 UI 만 있고 실제
  권한 요청·수집이 없습니다. **남은 것 중 가장 큽니다**
- 상태관리 패키지 없음 (`setState` 만). MVP 범위에서는 의도한 선택입니다
- 자동 로그인 없음 — refresh token 이 없어서입니다(4절 참조)

### 연동 완료

- `http` 공통 클라이언트와 `flutter_secure_storage` 토큰 저장
- access token 만료 확인을 포함한 인증 게이트, 401 자동 로그아웃
- **앱 화면 전부** — 인증 6개 · 홈 · 챗봇 · 라이프로그 · 설정/기기 · 리포트
- **관리자 웹 전부** — 로그인·`ADMIN` 역할 가드 · 위험도 분포 · 대상자 목록 · 상세
- 기본 Base URL은 Android 에뮬레이터용 `http://10.0.2.2:8000/api/v1`
- `flutter analyze`·`flutter test`(17건)·Android debug APK 빌드 통과

### 서버 JSON 을 직접 캐스팅하지 마세요

`lib/models/json.dart` 의 헬퍼(`jsonInt`·`jsonNum`·`jsonAt`·`jsonObj`·`jsonList` …)를 쓰세요.
두 가지가 실제로 터진 적이 있습니다.

- **PostgreSQL `NUMERIC` 은 문자열로 옵니다.** `hrv`·`sleep_efficiency_pct`·`emotion_score`
  가 `'36.50'` 으로 와서 `as num?` 이 조용히 null 이 됐습니다
- **중첩 객체는 `Map<String, dynamic>` 이 아닙니다.** `json['distribution'] as Map<String,
  dynamic>?` 이 `_Map<dynamic, dynamic>` 캐스트 실패로 예외를 던졌습니다

`test/report_models_test.dart` 가 이 두 가지를 고정하고 있습니다.

### 화면 시안

`docs/design/`의 신규 화면 시안 6장과 원본 HTML은 모두 완성됐습니다. Flutter·React 구현 시 동일한 팔레트와 차트 규격을 기준으로 사용하세요.

### 화면 대응

| 화면 ID | 현재 파일 | 상태 |
|---|---|---|
| `MAIN_LOGIN_01` | `login_screen.dart` | 완료 — 3단계 점진 노출. **「로그인 유지」 없음** |
| `MAIN_LOGIN_02` | `password_reset_screen.dart` | 완료 — 재설정 요청·확정 API |
| `MAIN_JOIN_01` | `join_screen.dart` STEP01 | 완료 — 약관 동의 |
| `MAIN_JOIN_02` | `join_screen.dart` STEP02 | 완료 — 기본/선택 입력 분리 · `?` 설명 |
| `MAIN_JOIN_03` | `join_screen.dart` STEP03 | UI 완료 — **Health Connect 권한 연동만 남음** |
| `MAIN_HOME_01` | `home_screen.dart` | 완료 — 요약·콘텐츠 추천·`action` 분기 |
| `MAIN_CHAT_01` | `chat_screen.dart` 성격 선택부 | 완료 |
| `MAIN_CHAT_02` | `chat_screen.dart` 대화부 | 완료 — 기록 조회·상세·삭제 |
| `MAIN_LIFELOG_01` | `lifelog_screen.dart` | 완료 — 재작성 후 API 연동 |
| `MAIN_REPORT_01` | `report_screen.dart` | 완료 — 분포·추이·PDF 내보내기 |
| `MAIN_SETTING_01` | `settings_screen.dart` | 완료 — 프로필·페르소나·기기 동의 범위 |
| `MAIN_SETTING_02` | `settings_screen.dart` 하단 | 완료 — 비밀번호 변경·탈퇴(`MLCM_103` 2단계 확인) |
| `MAIN_EMERGENCY_01` | `emergency_screen.dart` | 완료 — `EMERGENCY` 액션 즉시 전환·`tel:109` 호출 |
| `ADMIN_LOGIN_01` | `admin/src/App.jsx` | 완료 — React, 실제 인증 API·역할 가드 |
| `ADMIN_DASH_01` | `admin/src/App.jsx` | 완료 — 분포·대상자·상세 3개 탭 |

`join_screen.dart` 는 약관 동의와 정보 입력이 한 파일에 STEP 으로 들어가 있습니다. 문서는 3개 화면으로 정의하지만, 세 단계가 **하나의 가입 흐름을 공유**(입력값 이월·뒤로가기)하므로 파일은 합쳐 둡니다. 화면 ID 는 STEP 주석으로 표시돼 있습니다.

### 리포트 PDF 는 서버가 만들지 않습니다

`GET /reports/export` 는 **없습니다.** `GET /reports` 응답을 받아 앱이 조판합니다
(`services/report_pdf.dart`).

- 한글 폰트를 PDF 에 심으면 4~8MB 가 붙습니다. 그래서 **화면을 캡처해 이미지로 넣고**,
  헤더만 실제 PDF 텍스트로 그립니다. 기본 Helvetica 에 한글 글리프가 없어 **헤더는 영문**입니다
- `RenderRepaintBoundary.toImage` 는 `debugNeedsPaint` 상태에서 assert 로 죽습니다.
  캡처 직전 `setState` 로 프레임을 더럽히면 반드시 터지니 `endOfFrame` 을 기다리세요

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

## 5. 남은 작업

1. **Health Connect 실기기 연동** ⭐ — `MAIN_JOIN_03` 의 권한 요청과 주기적 수집·push.
   지금은 UI 만 있습니다. 서버 `POST /lifelog/batch` 는 이미 UPSERT 로 동작합니다
2. **화면설계서 PPTX 디자인** — 완성 시안 6장 배치와 기존 와이어프레임 ❶❷❸ 마커 (함은선 님)
3. **실기기 QA** — 지금까지 검증은 Android 에뮬레이터 기준입니다

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
| 앱 상단 `마음이 ♥` | **철회.** 「마음이」는 챗봇 캐릭터 이름이라 브랜드 자리에 쓰면 앱 이름으로 오인됩니다. 브랜드는 `귀기울임 LISN`(`LisnBrand`) 이고, **앱 상단에는 표시하지 않습니다** — 로그인·가입 등 앱을 처음 식별해야 하는 화면에만 둡니다 |
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
