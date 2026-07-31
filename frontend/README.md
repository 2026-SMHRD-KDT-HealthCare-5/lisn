# frontend

사용자 앱(Flutter)과 관리자 관제 대시보드(React)가 함께 들어갑니다.

```
frontend/
├── app/        Flutter 사용자 앱      — Android 전용 (Health Connect 가 Android API)
├── admin/      React 관리자 관제 웹   — 로그인·권한 가드 완료
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

인증 영역은 실제 FastAPI와 연동됐습니다.

- `config/api_config.dart` — `API_BASE_URL` 환경 분기
- `models/auth_models.dart` — 로그인·회원가입 DTO
- `services/api_client.dart` — JSON 요청, Bearer 헤더, FastAPI 오류 처리, 타임아웃
- `services/token_storage.dart` — access token과 만료 시각을 보안 저장소에 저장
- `services/auth_service.dart` — 인증 API 6개 호출
- `screens/auth_gate.dart` — 유효한 토큰이 있으면 홈, 없으면 로그인으로 이동

Android 에뮬레이터의 기본 API 주소는 `http://10.0.2.2:8000/api/v1`입니다. 실기기나 배포 환경에서는 실행 시 바꿉니다.

```powershell
flutter run --dart-define=API_BASE_URL=http://<개발-PC-IP>:8000/api/v1
```

로그인·회원가입·비밀번호 재설정은 API 연동이 끝났고, 홈·챗봇·라이프로그·설정의 데이터는 아직 하드코딩 목업입니다.

남은 연동 순서는 이렇습니다.

1. 백엔드 `users`·`devices` 라우터가 완성되면 설정·웨어러블 연동
2. `POST /lifelog/batch`와 조회 API가 완성되면 홈·라이프로그
3. 챗봇 API가 완성되면 대화·위기 화면 전환
4. 관리자 API가 완성되면 React 관제 대시보드 데이터 연동

### 화면 구성

| 파일 | 화면설계서 ID |
|---|---|
| `login_screen.dart` | `MAIN_LOGIN_01` |
| `password_reset_screen.dart` | `MAIN_LOGIN_02` |
| `join_screen.dart` | `MAIN_JOIN_01` · `MAIN_JOIN_02` |
| `main_shell.dart` | 하단 네비게이션 4탭 |
| `home_screen.dart` | `MAIN_HOME_01` |
| `chat_screen.dart` | `MAIN_CHAT_01` · `MAIN_CHAT_02` |
| `lifelog_screen.dart` | 라이프로그 |
| `settings_screen.dart` | 설정 |

## admin/ — React 관리자 관제 웹

Vite + React 기반 관리자 로그인 화면과 `ADMIN` 역할 가드를 구현했습니다. 사용자 앱과 같은
`POST /api/v1/auth/login`을 사용하며, 일반 사용자 토큰은 저장하지 않고 접근을 차단합니다.
관리자 세션이 확인되면 대시보드 셸로 진입합니다.

```powershell
cd frontend/admin
npm install
npm run dev
```

기본 API 주소는 `http://localhost:8000/api/v1`입니다. 다른 환경에서는
`VITE_API_BASE_URL`로 바꿉니다. 위험도 분포·고위험 사용자 목록 등 실제 대시보드 데이터는
관리자 조회 API가 구현된 뒤 연결합니다.

## design/ — 디자인 시안

`maeume-home.png` 등 화면 시안입니다. **앱이 실제로 쓰는 리소스가 아닙니다.**

앱 리소스는 `app/assets/` 에 두고 `pubspec.yaml` 의 `assets:` 에 등록해야 로딩됩니다. 현재 등록된 것은 `assets/images/login_mascot.png` 하나입니다. 시안을 여기 두면 빌드 크기만 커집니다.
