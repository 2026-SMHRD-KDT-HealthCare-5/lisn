# 귀기울임(LISN) Flutter 앱

> **최종 점검** 2026.08.02

Android 전용 사용자 앱입니다. **화면 14개가 전부 실제 API 에 붙어 있습니다.** 목업 데이터는
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

### ⚠ 실기기·릴리스 빌드는 **주소를 두 곳**에 넣어야 합니다

`--dart-define` 만으로는 안 됩니다. `targetSdk 36` 은 **평문 HTTP 를 기본
차단**하므로 `android/app/src/main/res/xml/network_security_config.xml` 의
허용 목록에도 같은 IP 를 넣어야 합니다.

```xml
<domain includeSubdomains="false">여기에_개발-PC-IP</domain>
```

**안 넣으면 화면에 「서버에 연결할 수 없습니다」만 뜹니다.** 네트워크나 서버
문제로 보이지만 OS 가 요청 자체를 막은 것입니다.

> ### ⚠ 이 `--dart-define` 을 에뮬레이터에 쓰지 마세요
>
> `API_BASE_URL` 은 **컴파일 시점 상수**라 한 번 그렇게 구우면 그 설치본은 계속
> 그 주소로 나갑니다. 실기기용 IP 로 구운 앱을 에뮬레이터에서 쓰면 요청이
> 존재하지 않는 주소로 나가 10초 뒤 **「서버 응답이 지연되고 있습니다」**만
> 뜹니다. 관리자 웹은 멀쩡하니 서버 문제로 보이지 않아 원인을 찾기 어렵습니다.
> 2026.08.03 에 실제로 여기서 막혔습니다.
>
> 앱이 어디로 나가는지는 로그인 직후 호스트에서 확인합니다. `SYN_SENT` 로 남는
> 상대 주소가 앱에 박힌 주소입니다.
>
> ```powershell
> netstat -ano | Select-String ":8000"
> ```
>
> **에뮬레이터는 아무 옵션 없이 `flutter run`.** 핫 리로드로는 안 바뀌니 다시
> 빌드·설치해야 합니다.

> 에뮬레이터 **디버그** 실행은 이 설정 없이도 됩니다. Flutter 가
> `src/debug/AndroidManifest.xml` 에만 평문을 허용해 두기 때문입니다.
> **그래서 릴리스에서만 터지고, 에뮬레이터로는 아무리 확인해도 안 보입니다.**
> 2026.08.02 에 실제로 그 상태였습니다(릴리스 APK 는 빌드되는데 전 API 실패).

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

테스트 119건은 **모델 파싱 · 안전 규칙 · 재조회 시 화면 유지 · 문서와의 일치**를 고정합니다. 실패하면 주석에 적힌 요구사항 ID 부터
읽으세요.

## ⚠ 개발 편의 플래그 — 인증 우회 경로가 있습니다

화면설계서 캡처나 화면 확인 때 매번 로그인하지 않도록 **자동 로그인**과 **화면 바로
띄우기**를 넣었습니다(`lib/dev_screens.dart`, 2026.08.02).

```powershell
C:\LISN\tools\show-screen.ps1 report
```

에뮬레이터를 알아서 켜고 앱 폴더로 이동합니다. **절대 경로로 적은 것은 의도한
것입니다** — `.\tools\...` 는 저장소 루트에 있을 때만 되고, 이 폴더(`frontend/app`)
에서 치면 `CommandNotFoundException` 이 납니다. 직접 칠 때는 **`frontend/app` 에서**
실행하세요 — 저장소 루트에서는 `No pubspec.yaml file found` 가 납니다.

```bash
flutter run --dart-define=DEV_LOGIN=force --dart-define=SCREEN=report
```

| 플래그 | 하는 일 |
|---|---|
| `DEV_LOGIN=true` | 세션이 없을 때만 데모 계정으로 자동 로그인 |
| `DEV_LOGIN=force` | **기존 세션을 버리고** 데모 계정으로 다시 로그인 |
| `SCREEN=<키>` | 그 화면으로 바로 시작 |

> ⚠ **캡처를 뜰 때는 `force` 를 쓰세요.** `true` 는 이미 로그인돼 있으면 건너뛰는데,
> 손으로 다른 계정에 로그인해 뒀다면 **그 계정 데이터가 그려집니다.** 화면은 멀쩡해
> 보여서 캡처를 뜬 뒤에야 압니다. 실제로 한 번 겪었습니다.

`SCREEN` 키 — `login` `reset` `join` `home` `chat` `lifelog` `setting` `report` `emergency`

> ### 되돌리거나 지울 때 알아야 할 것
>
> - **컴파일 시점 플래그입니다.** 값을 주지 않은 평소 빌드에는 아무 영향이 없습니다
> - **릴리스 빌드에서는 무시**합니다(`kReleaseMode` 검사). 이 검사를 빼지 마세요
> - 계정은 `demo.crisis@lisn-test.example` 입니다. `.example` 은 RFC 2606 예약
>   도메인이라 실제로 존재할 수 없습니다
> - **인증 검사만 끄는 방식이 아닙니다.** 그러면 화면은 떠도 서버 호출이 전부 401 이라
>   빈 화면만 보입니다. 실제 토큰을 받아야 데이터까지 그려집니다
> - 데이터가 보이려면 백엔드가 떠 있고 `db/seed_demo_persona.sql` 이 들어가 있어야 합니다

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

## 다시 불러올 때 화면을 비우지 마세요

기간 전환·당겨서 새로고침으로 **행 수가 크게 변하는 화면이 넷**입니다(홈·라이프로그·
리포트·설정). 보여줄 것이 있는데도 로딩으로 갈아치우면 본문이 통째로 접혔다 펴집니다.
실제로 지적을 받아 고쳤습니다.

- 보여줄 것이 **없을 때만** 로딩 (최초 진입)
- 다시 불러오는 중에는 이전 내용을 두고 **흐리게만** (`Opacity 0.45`)
- 흐린 동안은 **조작을 막습니다** (`IgnorePointer`) — 곧 덮어써질 값을 바꾸게 됩니다
- **성공한 결과만 보관**합니다. 실패가 이전 결과를 지우면 다음 조회에서 다시 로딩부터

> 당겨서 새로고침은 `RefreshIndicator` 가 이미 위에서 진행을 알립니다. 본문까지
> 비우는 건 중복입니다.

> ⚠ **흐린 상태에 `RepaintBoundary` 를 달지 마세요.** 리포트 PDF 는 화면을 캡처해
> 만들기 때문에, 그 상태가 찍히면 **바뀐 기간의 머리말에 이전 기간 그림**이 들어갑니다.

> ⚠ **`_loadAndKeep()` 의 `then(...).ignore()` 를 `async`/`await` 로 바꾸지 마세요.**
> 조회가 즉시 실패하면 `FutureBuilder` 가 구독하기 전에 오류가 도착해 미처리 예외로
> 보고됩니다. 화면은 멀쩡한데 로그만 더러워지고 위젯 테스트가 실패합니다.

`test/report_reload_test.dart` 가 이 규칙을 고정합니다.

## 위기 상태에서 웃지 마세요

「지금 마음이 많이 힘들어 보여요」 옆에서 캐릭터가 웃고 있으면 **공감이 아니라 무시로
읽힙니다.** 실제로 그렇게 나가 있었습니다.

`MaeumeMascot` 은 `MascotMood` 로 표정이 갈립니다. 위험도를 아는 자리에서는 반드시
`MaeumeMascot.moodFor(riskLevel)` 을 넘기세요.

| 상태 | 표정 |
|---|---|
| `NORMAL`·미평가 | `• ᴗ •` 웃는 눈 |
| `CAUTION`·`CRITICAL` | `• · •` **담담한 표정** |

> ⚠ **슬픈 표정을 쓰지 마세요.** 캐릭터가 같이 괴로워하면 감정을 더 키우고, 사용자가
> 자기 상태를 「남까지 힘들게 하는 것」으로 받아들이게 됩니다. 위기 화면에 경고색을
> 쓰지 않는 것과 같은 이유입니다. **판단하지 않고 곁에 있는 상태**가 목표입니다.

같은 이유로 위기·주의에서는 인사말의 `😊` 를 붙이지 않고, 문구에 느낌표를 쓰지
않습니다. `test/mascot_mood_test.dart` 가 이 규칙을 고정합니다.

> **남은 것 — 상단 히어로 일러스트는 아직 웃습니다.** `assets/images/login_mascot.png`
> 하나뿐이라 코드로는 못 바꿉니다. 담담한 표정 버전이 필요합니다(디자인 작업).

## 동작하지 않는 버튼을 두지 마세요

챗봇 화면 왼쪽 위·오른쪽 위가 `onPressed: () {}` 인 **빈 버튼**이었습니다.
아이콘이 예쁘게 들어가 있어 화면만 봐서는 정상으로 보입니다. **눌러야 압니다.**

- **오른쪽** → 대화 기록. 서버 API 와 `ChatService` 는 이미 있었고 입구만
  없었습니다(`SD-12` 대화 기록 복원). **화면 동작은 오른쪽이 관례**입니다
- **왼쪽** → 비웠습니다. 여기는 탭 루트라 뒤로가기가 없고, 왼쪽 위에 동작 버튼을
  두면 뒤로가기·메뉴로 오인됩니다
- **검색** → **없앴습니다.** 화면설계서에 없는 기능이고, 만들려면 서버에 검색
  API 부터 있어야 합니다

홈 화면 오른쪽 위 **알림 종 아이콘**도 같은 이유로 없앴습니다. 셋이 겹쳐 있었습니다.

1. 화면설계서 `MAIN_HOME_01` ❶~❺ 에 **알림 항목이 없습니다**
2. 서버에 알림 API 가 없습니다. **설정 화면은 「알림 기능은 준비 중이에요」로 정직하게
   알리는데** 홈이 빨간 배지로 「읽지 않은 알림 있음」을 주장해 서로 모순됐습니다
3. `IconButton` 도 아닌 정적 `Icon` 이라 **눌리지도 않았습니다**

> FCM 을 붙이고 알림 목록 API 가 생기면 그때 넣으세요. 그 전까지는 없는 편이 낫습니다.

마이크 버튼을 지운 것과 같은 판단입니다 — 눌리는데 동작하지 않으면 시연에서
바로 드러납니다. `test/chat_history_test.dart` 와 `test/home_no_label_test.dart` 가
「눌렀을 때 실제로 열리는지」·「없어야 할 것이 없는지」를 고정합니다.

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
| `chat_history_screen.dart` | `MAIN_CHAT_02` 대화 기록 (`SD-12`) |
| `lifelog_screen.dart` | `MAIN_LIFELOG_01` |
| `report_screen.dart` | `MAIN_REPORT_01` |
| `settings_screen.dart` | `MAIN_SETTING_01` |
| `account_screen.dart` | `MAIN_SETTING_02` (설정 ❸ 에서 push) |
| `emergency_screen.dart` | `MAIN_EMERGENCY_01` |

## 라이프로그 수집 — MLCM_200

**수집 주체는 앱입니다.** Health Connect 는 Android on-device 권한 모델이라 서버가
대신 읽을 수 없습니다(안건 1-1 확정).

| 파일 | 역할 |
|---|---|
| `services/health_reader.dart` | **플랫폼에 닿는 유일한 파일.** 권한·읽기 |
| `services/lifelog_aggregate.dart` | 표본 → 하루 한 행. 순수 함수 |
| `services/lifelog_sync.dart` | 전체 흐름. 델타 구간·재시도·큐 |
| `services/sync_store.dart` | `last_synced_at` · 실패분 보관 |
| `services/sync_worker.dart` | 15분 주기 WorkManager 등록 |

플랫폼 의존을 한 곳에 몰아둔 덕에 **집계·동기화 35건을 실기기 없이 검증**합니다.

### ⚠ 행 단위는 「하루」입니다 — 15분마다 행을 만들지 마세요

`MLCM_200` 이 15분 간격 **전송**을 규정하는데, 이걸 15분마다 행 하나로 읽으면
`ai/server` 의 `rows[-1]` 이 「오늘」이 아니라 **「마지막 15분」**이 되고, 하루치
수면 컬럼(`total_sleep_min` 등)이 32행에 흩어집니다.

**전송은 15분마다, 행은 그날 것을 UPSERT 로 갱신**합니다.
하루 경계는 **로컬 자정**이고 수면은 **깨어난 날**에 귀속됩니다.

### ⚠ 두 곳을 같이 고쳐야 합니다

`health_reader.dart` 의 `_types` 에 타입을 추가하면 `AndroidManifest.xml` 의 권한도
같이 넣어야 합니다. Health Connect 는 **선언 안 된 타입을 요청하면 예외 없이 빼고
승인**하므로, 승인은 되는데 그 지표만 영원히 null 인 상태가 됩니다.
`test/health_permission_drift_test.dart` 가 둘을 대조합니다.

### 백그라운드는 다른 아이솔레이트입니다

`AppServices` 의 static 필드가 워커에서는 비어 있습니다. 워커는
`buildSyncService()` 로 따로 조립합니다. 이걸 잊고 `AppServices.lifelog` 를 쓰면
**백그라운드에서만 조용히 실패합니다.**

## ⚠ 문서와 갈리지 않게

화면설계서가 정본입니다. 앱이 문서와 어긋난 곳을 찾아 6건을 맞췄습니다
(2026.08.02 → [`문서-구현_대조_20260802.md`](../../docs/검증/문서-구현_대조_20260802.md)).

특히 **챗봇 성격 이름**은 앱만 「다정한 공감가/이성적인 분석가」를 쓰고
있었습니다. 문서·기획서·시안 세 곳이 모두 「따스한 공감형/현실적인 조언형」인데
앱 혼자 달랐습니다. 화면에 큼직하게 뜨는 글자인데도, **어느 쪽이 맞는지 알아야만
문제로 보여서** 문서와 나란히 놓기 전까지 드러나지 않았습니다.

`test/persona_label_test.dart` 가 **화면설계서 추출본을 직접 읽어** 대조합니다.
이름을 바꿔야 하면 **문서를 먼저 고치고** 테스트를 맞추세요.

## 남은 것

**Health Connect 실기기 검증** — 구현은 끝났고 에뮬레이터에서 워커 실행까지
확인했습니다(권한이 없어 `permissionDenied` 로 정상 종료). 실제 데이터 읽기는
Health Connect 가 있는 실기기에서만 확인할 수 있습니다.

## 하지 않기로 한 것

| 항목 | 이유 |
|---|---|
| **「로그인 유지」·자동 로그인** | **refresh token 이 없습니다.** access token 단일에 만료 24시간입니다. 넣으려면 인증 설계 전체가 바뀝니다 |
| **응답 스트리밍(SSE)** | 위기 판정 전에 글자를 흘리면 `CRITICAL` 일 때 회수할 수 없습니다 |
| **음성 입력** | 범위 밖. 마이크 버튼은 제거됐고 테스트로 고정돼 있습니다 |
| **iOS** | Health Connect 가 Android 전용 API 입니다 |
| **`minSdk` 26 미만** | Health Connect 요구값. 낮추면 연동 패키지 추가 시 manifest merger 에서 깨집니다 |
