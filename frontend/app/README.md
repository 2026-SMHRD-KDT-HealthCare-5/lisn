# 마음이 Flutter 앱

> **최종 점검** 2026.07.31

Android 전용 Flutter 사용자 앱입니다. 인증 API 6개, 보안 토큰 저장, 인증 게이트,
로그인·회원가입·비밀번호 재설정·로그아웃 흐름과 긴급 상담 화면이 구현돼 있습니다.

## 실행 준비

1. Flutter SDK를 설치합니다.
2. 저장소 루트에서 이 폴더로 이동합니다.
3. 의존성을 받고 실행합니다.

```bash
flutter pub get
flutter run
```

Health Connect 때문에 Android만 지원하며 `minSdk`는 26입니다. 플랫폼 파일은 이미 있으므로
`flutter create`를 다시 실행하지 않습니다.

Android 에뮬레이터의 기본 API 주소는 `http://10.0.2.2:8000/api/v1`입니다.

```powershell
flutter run --dart-define=API_BASE_URL=http://<개발-PC-IP>:8000/api/v1
```

검증 명령:

```bash
flutter analyze
flutter test
```

긴급 상담은 서버 응답의 `EMERGENCY` 액션에서 추가 조회 없이 전체 화면으로 전환하고,
`url_launcher`로 `tel:109`를 호출합니다. 홈·챗봇·라이프로그·설정의 업무 데이터와
Health Connect 연동은 아직 목업입니다.
