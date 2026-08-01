/// 화면설계서·시연용 — 원하는 화면으로 바로 띄우고, 로그인을 건너뛰기
///
/// ═══════════════════════════════════════════════════════════════════
///  ⚠ 이 파일은 **개발 편의 도구**입니다. 인증을 우회하는 경로가 있습니다.
///     릴리스 빌드에서는 아래 플래그를 절대 주지 마세요.
/// ═══════════════════════════════════════════════════════════════════
///
/// 화면설계서에 넣을 캡처를 뜨거나 특정 화면만 확인할 때, 매번 로그인부터
/// 눌러 들어가면 오래 걸립니다. 위기 화면처럼 **조건을 만들어야만 나오는
/// 화면**은 아예 재현이 어렵습니다.
///
/// ## 쓰는 법
///
/// ```
/// flutter run --dart-define=DEV_LOGIN=true --dart-define=SCREEN=report
/// ```
///
/// | 플래그 | 하는 일 |
/// |---|---|
/// | `DEV_LOGIN=true` | 앱을 켤 때 데모 계정으로 **자동 로그인**합니다 |
/// | `SCREEN=<키>` | 그 화면으로 **바로 뜹니다** (아래 `devScreens` 참조) |
///
/// 둘은 독립입니다. `DEV_LOGIN` 만 주면 평소 흐름대로 홈까지 갑니다.
///
/// ## 왜 「인증 끄기」가 아니라 자동 로그인인가
///
/// 인증 검사만 건너뛰면 화면은 뜨는데 **서버 호출이 전부 401** 이라 빈 화면과
/// 오류 문구만 보입니다. 화면설계서 캡처에는 쓸 수가 없습니다.
/// 자동 로그인은 실제 토큰을 받으므로 데이터까지 그려집니다 — 데모 페르소나에
/// 14일치 라이프로그와 판정이 들어 있습니다(`db/seed_demo_persona.sql`).
///
/// ## 안전장치
///
/// - **컴파일 시점 플래그**입니다. 값을 주지 않은 빌드에는 코드가 있어도
///   동작하지 않습니다
/// - **릴리스 빌드에서는 무시**합니다(`kReleaseMode` 검사)
/// - 계정·비밀번호는 **테스트 전용**입니다. `.example` 은 RFC 2606 예약
///   도메인이라 실제로 존재할 수 없습니다
/// - 자동 로그인이 실패하면 **평소처럼 로그인 화면**으로 갑니다. 조용히
///   넘어가지 않고 로그로 남깁니다
library;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import 'screens/emergency_screen.dart';
import 'screens/join_screen.dart';
import 'screens/login_screen.dart';
import 'screens/main_shell.dart';
import 'screens/password_reset_screen.dart';
import 'screens/report_screen.dart';
import 'services/app_services.dart';

/// `--dart-define=SCREEN=<키>` 로 받은 값. 안 주면 빈 문자열입니다.
const String kDevScreen = String.fromEnvironment('SCREEN');

/// 키 → 화면. 키는 화면설계서 ID 를 짧게 줄인 것입니다.
final Map<String, ({String id, Widget Function() build})> devScreens = {
  'login': (id: 'MAIN_LOGIN_01', build: () => const LoginScreen()),
  'reset': (id: 'MAIN_LOGIN_02', build: () => const PasswordResetScreen()),
  'join': (id: 'MAIN_JOIN_01~03', build: () => const JoinScreen()),
  'home': (id: 'MAIN_HOME_01', build: () => const MainShell(initialTab: 0)),
  'chat': (id: 'MAIN_CHAT_01·02', build: () => const MainShell(initialTab: 1)),
  'lifelog': (
    id: 'MAIN_LIFELOG_01',
    build: () => const MainShell(initialTab: 2)
  ),
  // MAIN_SETTING_02(계정 관리·탈퇴)는 별도 화면이 아니라 설정 탭 **하단**입니다.
  // 열고 아래로 스크롤하세요.
  'setting': (
    id: 'MAIN_SETTING_01·02',
    build: () => const MainShell(initialTab: 3)
  ),
  'report': (id: 'MAIN_REPORT_01', build: () => const ReportScreen()),
  // 위기 화면은 CRITICAL 판정이 나야 뜹니다. 캡처하려고 그 상황을 만들 수는
  // 없으니 여기서 직접 띄웁니다. 전화 연결은 실제로 동작하므로 주의하세요.
  'emergency': (
    id: 'MAIN_EMERGENCY_01',
    build: () => const EmergencyScreen()
  ),
};

/// 지정된 화면. 플래그가 없거나 모르는 키면 null 입니다.
Widget? devScreenOrNull() {
  if (kDevScreen.isEmpty) return null;
  final entry = devScreens[kDevScreen];
  if (entry == null) {
    debugPrint(
      '[dev] SCREEN=$kDevScreen 은(는) 없는 키입니다. '
      '쓸 수 있는 값: ${devScreens.keys.join(", ")}',
    );
    return null;
  }
  debugPrint('[dev] ${entry.id} 로 시작합니다 (SCREEN=$kDevScreen)');
  return entry.build();
}


// ---------------------------------------------------------------------------
//  자동 로그인
// ---------------------------------------------------------------------------

/// `--dart-define=DEV_LOGIN=true` 일 때만 켜집니다.
const bool _devLoginRequested = bool.fromEnvironment('DEV_LOGIN');

/// 기본은 데모 페르소나입니다. 14일치 데이터가 들어 있어 화면이 비지 않습니다.
/// 다른 계정으로 보려면 `--dart-define=DEV_EMAIL=...` 로 바꾸세요.
const String _devEmail = String.fromEnvironment(
  'DEV_EMAIL',
  defaultValue: 'demo.crisis@lisn-test.example',
);
const String _devPassword = String.fromEnvironment(
  'DEV_PASSWORD',
  defaultValue: 'rldnfdla',
);

/// 릴리스 빌드에서는 플래그를 줘도 켜지지 않습니다.
bool get devLoginEnabled => _devLoginRequested && !kReleaseMode;

/// 유효한 세션이 없으면 데모 계정으로 로그인합니다.
///
/// 실패하면 **조용히 넘어가지 않고** 로그를 남깁니다. 백엔드가 안 떠 있거나
/// 시드를 안 넣은 상태에서 「왜 로그인 화면이 뜨지」로 헤매지 않게 하기 위해서입니다.
Future<void> devLoginIfNeeded() async {
  if (!devLoginEnabled) return;
  if (await AppServices.tokenStore.hasValidSession()) {
    debugPrint('[dev] 이미 유효한 세션이 있어 자동 로그인을 건너뜁니다.');
    return;
  }
  try {
    await AppServices.auth.login(email: _devEmail, password: _devPassword);
    debugPrint('[dev] 자동 로그인 완료: $_devEmail');
  } catch (e) {
    debugPrint(
      '[dev] 자동 로그인 실패: $e\n'
      '      백엔드가 떠 있는지, db/seed_demo_persona.sql 을 넣었는지 확인하세요.\n'
      '      로그인 화면으로 넘어갑니다.',
    );
  }
}
