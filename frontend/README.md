# frontend

사용자 앱(Flutter)과 관리자 관제 대시보드(React)가 함께 들어갑니다.

> **최종 점검** 2026.08.02

```
frontend/
├── app/        Flutter 사용자 앱      — Android 전용 (Health Connect 가 Android API)
├── admin/      React 관리자 관제 웹   — 로그인·권한 가드·관제 3개 탭 완료
└── design/     디자인 시안            — 앱 빌드에 포함되지 않음
```

**앱 14개 화면과 관리자 웹이 전부 실제 API 에 붙었습니다.** 목업 데이터는 없습니다.
남은 구현은 **Health Connect 실기기 연동** 하나입니다.

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

주요 파일은 이렇습니다.

- `config/api_config.dart` — `API_BASE_URL` 환경 분기
- `models/json.dart` — **서버 JSON 파싱은 반드시 이걸 씁니다** (아래 참조)
- `services/api_client.dart` — JSON 요청, Bearer 헤더, FastAPI 오류 처리, 타임아웃, 401 로그아웃
- `services/token_storage.dart` — access token과 만료 시각을 보안 저장소에 저장
- `services/report_pdf.dart` — 리포트 화면을 캡처해 PDF 로 조판
- `screens/auth_gate.dart` — 유효한 토큰이 있으면 홈, 없으면 로그인으로 이동

Android 에뮬레이터의 기본 API 주소는 `http://10.0.2.2:8000/api/v1`입니다. 실기기나 배포 환경에서는 실행 시 바꿉니다.

```powershell
flutter run --dart-define=API_BASE_URL=http://<개발-PC-IP>:8000/api/v1
```

> ⚠ **저장소 경로에 한글이 있으면 `flutter analyze` 가 죽습니다**(LSP 채널이 메시지를
> 잘라먹음). `C:\LISN` 에서는 정상이고, 다시 겪으면 `dart analyze` 로 우회합니다.
> 앱 쪽 함정은 [`app/README.md`](app/README.md) 에 있습니다.

남은 것은 **Health Connect 실기기 연동**입니다. `MAIN_JOIN_03` 의 권한 화면은 UI 만 있고
실제 권한 요청·주기 수집이 없습니다. 서버 `POST /lifelog/batch` 는 이미 UPSERT 로 동작합니다.

### 화면 구성

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

## admin/ — React 관리자 관제 웹

Vite + React 기반입니다. 사용자 앱과 같은 `POST /api/v1/auth/login`을 사용하며, 일반 사용자
토큰은 저장하지 않고 접근을 차단합니다. 관제 3개 탭(위험도 분포 · 대상자 목록 · 상세)이
실제 관리자 API 에 붙어 있습니다.

```powershell
cd frontend/admin
npm install
npm run dev
```

기본 API 주소는 `http://localhost:8000/api/v1`입니다. 다른 환경에서는
`VITE_API_BASE_URL`로 바꿉니다.

> ⚠ **5173 포트여야 합니다.** 백엔드 `CORS_ORIGINS` 가 그 주소만 허용합니다. 이전 vite
> 인스턴스가 5173 을 잡고 있으면 새 창이 **5174 로 뜨고 요청이 전부 CORS 로 막힙니다.**
> 400 이 계속 나면 주소창의 포트부터 보세요.
>
> **`role` 승격은 API 에 즉시 반영됩니다.** `require_admin` 이 JWT 클레임이 아니라
> **DB 의 `role`** 을 읽기 때문입니다(`tests/test_admin.py` 로 고정). 토큰에 role 이
> 들어가 있지만 아무도 읽지 않습니다.
>
> **다만 관리자 웹은 재로그인이 필요합니다.** 로그인 응답의 role 로 세션 저장 여부를
> 정하기 때문에(`admin/src/session.js`), 승격 전에 로그인해 뒀다면 세션 자체가 없습니다.

## design/ — 디자인 시안

`maeume-home.png` 등 화면 시안입니다. **앱이 실제로 쓰는 리소스가 아닙니다.**

앱 리소스는 `app/assets/` 에 두고 `pubspec.yaml` 의 `assets:` 에 등록해야 로딩됩니다. 현재 등록된 것은 `assets/images/login_mascot.png` 하나입니다. 시안을 여기 두면 빌드 크기만 커집니다.
