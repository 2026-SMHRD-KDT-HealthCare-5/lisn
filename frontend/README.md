# frontend

사용자 앱(Flutter)과 관리자 관제 대시보드(React)가 함께 들어갑니다.

```
frontend/
├── app/        Flutter 사용자 앱      — Android 전용 (Health Connect 가 Android API)
├── admin/      React 관리자 관제 웹   — 미착수
└── design/     디자인 시안            — 앱 빌드에 포함되지 않음
```

## app/ — Flutter 사용자 앱

```
app/lib/
├── main.dart
├── config/     API base URL, 환경 분기 등 설정값
├── models/     서버 응답 ↔ Dart 객체 변환 (DTO)
├── services/   HTTP 클라이언트 · API 호출
├── screens/    화면 단위 위젯
├── theme/      색상 · 타이포그래피
└── widgets/    화면 간 공유 위젯
```

**`config` · `models` · `services` 는 아직 비어 있습니다.** 현재 화면은 전부 하드코딩된 목업이고 서버 통신 코드가 없습니다. `pubspec.yaml` 의존성도 `flutter` 와 `cupertino_icons` 뿐입니다.

붙이는 순서는 이렇습니다.

1. **API 명세 확정** — 이게 선행조건입니다. 엔드포인트와 응답 형태가 정해져야 아래를 만들 수 있습니다
2. `models/` — `db/schema.sql` 이 정본이므로 거기서 필드를 맞춥니다
3. `services/` — `http` 또는 `dio` 패키지를 `pubspec.yaml` 에 추가하고 클라이언트 작성
4. `screens/` 의 하드코딩 값을 `services/` 호출로 교체

### 화면 구성

| 파일 | 화면설계서 ID |
|---|---|
| `login_screen.dart` | `MAIN_LOGIN_01` |
| `join_screen.dart` | `MAIN_JOIN_01` · `MAIN_JOIN_02` |
| `main_shell.dart` | 하단 네비게이션 4탭 |
| `home_screen.dart` | `MAIN_HOME_01` |
| `chat_screen.dart` | `MAIN_CHAT_01` · `MAIN_CHAT_02` |
| `lifelog_screen.dart` | 라이프로그 |
| `settings_screen.dart` | 설정 |

## admin/ — React 관리자 관제 웹

아직 폴더만 있습니다. 기획서상 관리자가 전체 사용자의 위험도 분포를 조회하고 고위험군을 우선 식별하는 화면(`MLCM_501`)이며, Chart.js 로 시각화합니다. `MLCM_500`(개인 정서 리포트)과 시각화 컴포넌트를 공유합니다.

## design/ — 디자인 시안

`maeume-home.png` 등 화면 시안입니다. **앱이 실제로 쓰는 리소스가 아닙니다.**

앱 리소스는 `app/assets/` 에 두고 `pubspec.yaml` 의 `assets:` 에 등록해야 로딩됩니다. 현재 등록된 것은 `assets/images/login_mascot.png` 하나입니다. 시안을 여기 두면 빌드 크기만 커집니다.
