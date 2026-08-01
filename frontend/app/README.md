# 귀기울임(LISN) Flutter 앱

> **최종 점검** 2026.08.01

Android 전용 사용자 앱입니다. **화면 13개가 전부 실제 API 에 붙어 있습니다.** 목업 데이터는
남아 있지 않습니다.

## 실행

```bash
flutter pub get
flutter run
```

Health Connect 때문에 Android만 지원하며 `minSdk`는 26입니다. 플랫폼 파일은 이미 있으므로
`flutter create`를 다시 실행하지 않습니다.

Android 에뮬레이터의 기본 API 주소는 `http://10.0.2.2:8000/api/v1`입니다. 실기기에서는
개발 PC 의 IP 를 넘깁니다.

```powershell
flutter run --dart-define=API_BASE_URL=http://<개발-PC-IP>:8000/api/v1
```

## 검증

```bash
flutter analyze
```

```bash
flutter test
```

> ⚠ **저장소 경로에 한글이 있으면 `flutter analyze` 가 죽습니다.** LSP 채널이 메시지를
> 잘라 먹고 `FormatException: Unterminated string` 으로 분석 서버가 종료됩니다(exit 255).
> `바탕 화면` 아래에 뒀을 때 실제로 겪었고, `C:\LISN` 으로 옮겨 해소됐습니다.
> 다시 겪으면 **`dart analyze`** 로 우회하세요 — 같은 규칙으로 같은 결과가 나옵니다.

테스트 17건은 **모델 파싱과 안전 규칙**을 고정합니다. 실패하면 주석에 적힌 요구사항 ID 부터
읽으세요.

## 서버 JSON 을 직접 캐스팅하지 마세요

`lib/models/json.dart` 의 헬퍼(`jsonInt`·`jsonNum`·`jsonAt`·`jsonStr`·`jsonBool`·`jsonObj`·
`jsonList`)를 씁니다. 두 가지가 실제로 터진 적이 있습니다.

- **PostgreSQL `NUMERIC` 은 문자열로 옵니다.** `hrv`·`sleep_efficiency_pct`·`emotion_score`
  가 `'36.50'` 으로 와서 `as num?` 이 **조용히 null** 이 됐습니다. 화면에는 「측정 안 됨」으로
  보여 원인을 찾기 어렵습니다
- **중첩 객체는 `Map<String, dynamic>` 이 아닙니다.** `json['distribution'] as Map<String,
  dynamic>?` 이 `_Map<dynamic, dynamic>` 캐스트 실패로 예외를 던졌습니다

`test/report_models_test.dart` 가 이 둘을 고정합니다.

## 값이 없으면 null 입니다 — 0 으로 채우지 마세요

Health Connect 는 기기·권한에 따라 주는 항목이 다릅니다. `LifelogEntry` 는 `collected_at`
을 뺀 전 필드가 nullable 입니다. 없는 값을 0 으로 채우면 **「0걸음」과 「측정 안 됨」이
구분되지 않습니다.**

## 판단 로직을 앱에 복제하지 마세요

감정→위험도→액션 매핑은 **서버가 확정**합니다(04 문서 6항). 응답의 `action` 을 그대로
따르세요.

- `CHAT` → 일반 대화 렌더
- `CONTENT` → 힐링 콘텐츠 추천 표시
- `EMERGENCY` → **콘텐츠 추천을 즉시 중단하고** `MAIN_EMERGENCY_01` 로 전환

긴급 전환은 **이미 받은 응답으로 즉시** 합니다. 조회를 한 번 더 돌면 `NFR-TS-001`(3초)을
못 지킵니다. `url_launcher` 로 `tel:109` 를 호출합니다.

> 위기 화면에 **경고색(빨강·주황)을 쓰지 마세요.** 불안을 키워 회피를 유발합니다.
> 주목도는 구조로 만듭니다 — 하단 네비게이션 제거, 요소 최소화.

## 리포트 PDF 는 앱이 조판합니다

`GET /reports/export` 는 없습니다. `GET /reports` 응답으로 `services/report_pdf.dart` 가
만듭니다.

- 한글 TTF 를 심으면 4~8MB 가 붙어서, 본문은 **화면을 캡처해 이미지로** 넣고 헤더만 실제
  PDF 텍스트로 그립니다. 기본 Helvetica 에 한글 글리프가 없어 **헤더는 영문**입니다
- `RenderRepaintBoundary.toImage` 는 `debugNeedsPaint` 상태에서 assert 로 죽습니다.
  캡처 직전 `setState` 로 프레임을 더럽히지 말고 `endOfFrame` 을 기다리세요

## 화면 구성

| 파일 | 화면설계서 ID |
|---|---|
| `login_screen.dart` | `MAIN_LOGIN_01` |
| `password_reset_screen.dart` | `MAIN_LOGIN_02` |
| `join_screen.dart` | `MAIN_JOIN_01` · `MAIN_JOIN_02` · `MAIN_JOIN_03` |
| `main_shell.dart` | 하단 네비게이션 4탭 |
| `home_screen.dart` | `MAIN_HOME_01` |
| `chat_screen.dart` | `MAIN_CHAT_01` · `MAIN_CHAT_02` |
| `lifelog_screen.dart` | `MAIN_LIFELOG_01` |
| `report_screen.dart` | `MAIN_REPORT_01` |
| `settings_screen.dart` | `MAIN_SETTING_01` · `MAIN_SETTING_02` |
| `emergency_screen.dart` | `MAIN_EMERGENCY_01` |

## 남은 것

**Health Connect 실기기 연동** — `MAIN_JOIN_03` 의 권한 요청과 주기적 수집·push 가
없습니다. 서버 `POST /lifelog/batch` 는 이미 UPSERT 로 동작합니다.

## 하지 않기로 한 것

| 항목 | 이유 |
|---|---|
| **「로그인 유지」·자동 로그인** | **refresh token 이 없습니다.** access token 단일에 만료 24시간입니다. 넣으려면 인증 설계 전체가 바뀝니다 |
| **응답 스트리밍(SSE)** | 위기 판정 전에 글자를 흘리면 `CRITICAL` 일 때 회수할 수 없습니다 |
| **음성 입력** | 범위 밖. 마이크 버튼은 제거됐고 테스트로 고정돼 있습니다 |
| **iOS** | Health Connect 가 Android 전용 API 입니다 |
| **`minSdk` 26 미만** | Health Connect 요구값. 낮추면 연동 패키지 추가 시 manifest merger 에서 깨집니다 |
