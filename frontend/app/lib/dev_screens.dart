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
/// | `DEV_LOGIN=true` | 세션이 없으면 데모 계정으로 **자동 로그인** |
/// | `DEV_LOGIN=force` | 기존 세션을 **버리고** 데모 계정으로 다시 로그인 |
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

import 'screens/account_screen.dart';
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
  'setting': (
    id: 'MAIN_SETTING_01',
    build: () => const MainShell(initialTab: 3)
  ),
  // 설정 ❸ 에서 push 로 열리는 화면입니다. 최상위로 띄우면 뒤로가기가
  // 사라져 실제와 달라지므로 설정 탭 위에 얹습니다.
  'account': (
    id: 'MAIN_SETTING_02',
    build: () => const _PushOver(
          under: MainShell(initialTab: 3),
          child: AccountScreen(),
        ),
  ),
  // ⚠ 아래 둘은 평소에 **push 로 열리는 화면**입니다. 최상위 라우트로 그냥 띄우면
  //   뒤로가기·닫기가 사라져 실제 화면과 달라집니다(캡처가 틀어집니다).
  //   그래서 원래 부모 위에 얹어 띄웁니다.
  'report': (
    id: 'MAIN_REPORT_01',
    // 메뉴경로가 「라이프로그 / 정서 리포트」라 라이프로그 탭 위에 얹습니다.
    build: () => const _PushOver(
          under: MainShell(initialTab: 2),
          child: ReportScreen(),
        ),
  ),
  // 위기 화면은 CRITICAL 판정이 나야 뜹니다. 캡처하려고 그 상황을 만들 수는
  // 없으니 여기서 직접 띄웁니다. 전화 연결은 실제로 동작하므로 주의하세요.
  'emergency': (
    id: 'MAIN_EMERGENCY_01',
    build: () => const _PushOver(
          under: MainShell(initialTab: 0),
          child: EmergencyScreen(),
        ),
  ),
};

/// `under` 를 깔고 그 위에 `child` 를 push 합니다.
///
/// 평소에 push 로 열리는 화면을 최상위로 띄우면 **뒤로가기 버튼이 안 생기고**
/// 「나중에 볼게요」 같은 닫기도 동작하지 않습니다. 화면설계서 캡처가 실제와
/// 달라지므로 원래 진입 경로를 흉내 냅니다.
class _PushOver extends StatefulWidget {
  const _PushOver({required this.under, required this.child});

  final Widget under;
  final Widget child;

  @override
  State<_PushOver> createState() => _PushOverState();
}

class _PushOverState extends State<_PushOver> {
  @override
  void initState() {
    super.initState();
    // 첫 프레임 뒤에 얹습니다. build 중에 push 하면 죽습니다.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      Navigator.of(context).push(
        MaterialPageRoute<void>(builder: (_) => widget.child),
      );
    });
  }

  @override
  Widget build(BuildContext context) => widget.under;
}

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

/// `--dart-define=DEV_LOGIN=true` 또는 `=force` 일 때 켜집니다.
///
/// - `true`  — 유효한 세션이 없을 때만 로그인
/// - `force` — **기존 세션을 버리고** 데모 계정으로 다시 로그인
///
/// `force` 가 필요한 이유: 앞서 손으로 다른 계정에 로그인해 뒀으면 토큰이 남아 있어
/// 그 계정 데이터가 그려집니다. 화면설계서 캡처를 뜰 때 **엉뚱한 데이터가 찍히는데
/// 화면은 정상으로 보여** 알아채기 어렵습니다.

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

const String _devLoginMode = String.fromEnvironment('DEV_LOGIN');

/// 릴리스 빌드에서는 플래그를 줘도 켜지지 않습니다.
bool get devLoginEnabled =>
    (_devLoginMode == 'true' || _devLoginMode == 'force') && !kReleaseMode;

/// 유효한 세션이 없으면 데모 계정으로 로그인합니다.
///
/// 실패하면 **조용히 넘어가지 않고** 로그를 남깁니다. 백엔드가 안 떠 있거나
/// 시드를 안 넣은 상태에서 「왜 로그인 화면이 뜨지」로 헤매지 않게 하기 위해서입니다.
Future<void> devLoginIfNeeded() async {
  if (!devLoginEnabled) return;

  if (_devLoginMode == 'force') {
    await AppServices.tokenStore.clear();
    debugPrint('[dev] 기존 세션을 버리고 다시 로그인합니다 (DEV_LOGIN=force).');
  } else if (await AppServices.tokenStore.hasValidSession()) {
    // ⚠ 어느 계정인지 반드시 알립니다. 손으로 다른 계정에 로그인해 뒀다면 그
    //   계정 데이터가 그려지는데, 화면은 멀쩡해 보여 캡처를 뜬 뒤에야 압니다.
    String who = '(확인 실패)';
    try {
      who = (await AppServices.settings.profile()).email;
    } catch (_) {}
    debugPrint(
      '[dev] 이미 로그인돼 있어 건너뜁니다 — 현재 계정: $who\n'
      '      데모 계정으로 바꾸려면 --dart-define=DEV_LOGIN=force',
    );
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
