import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'dev_screens.dart';
import 'screens/auth_gate.dart';
import 'screens/login_screen.dart';
import 'screens/main_shell.dart';
import 'screens/password_reset_screen.dart';
import 'services/app_services.dart';
import 'services/sync_worker.dart';
import 'theme/app_theme.dart';

final appNavigatorKey = GlobalKey<NavigatorState>();

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  AppServices.apiClient.onUnauthorized = () {
    appNavigatorKey.currentState?.pushNamedAndRemoveUntil(
      '/login',
      (_) => false,
    );
  };

  // ⚠ 개발 편의 기능입니다. `--dart-define=DEV_LOGIN=true` 를 준 빌드에서만
  //   동작하고, 릴리스 빌드에서는 무시합니다 → dev_screens.dart
  await devLoginIfNeeded();

  // 라이프로그 수집 워커 등록 — MLCM_200 1단계.
  //
  // ⚠ 여기서 **await 하지 않습니다.** WorkManager 초기화가 플랫폼 채널을
  //   타는데, 등록이 늦어지면 그만큼 첫 화면이 늦게 뜹니다. 수집은 15분
  //   주기라 몇 초 늦게 등록돼도 아무 차이가 없습니다.
  //
  // ⚠ 실패해도 앱은 떠야 합니다. 에뮬레이터나 WorkManager 를 못 쓰는 환경에서
  //   앱 전체가 안 뜨면 원인을 찾기 어렵습니다.
  unawaited(registerLifelogSync().catchError((Object e) {
    debugPrint('라이프로그 워커 등록 실패: $e');
  }));

  runApp(const MaeumeApp());
}

class MaeumeApp extends StatelessWidget {
  const MaeumeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      navigatorKey: appNavigatorKey,
      title: '귀기울임',
      debugShowCheckedModeBanner: false,
      // ⚠ 날짜 선택기(정서 리포트 「직접 지정」)가 MaterialLocalizations 를
      //   요구합니다. 없으면 **화면을 여는 순간 죽습니다.**
      //   기본 제공은 영어뿐이라 한국어 델리게이트를 함께 넣습니다.
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: const [Locale('ko'), Locale('en')],
      locale: const Locale('ko'),
      theme: AppTheme.light,
      initialRoute: '/',
      routes: {
        // 평소에는 AuthGate 입니다. `--dart-define=SCREEN=<키>` 를 준 빌드에서만
        // 그 화면으로 바로 뜹니다 — 화면설계서 캡처·시연용(dev_screens.dart).
        '/': (_) => devScreenOrNull() ?? const AuthGate(),
        '/login': (_) => const LoginScreen(),
        '/password-reset': (_) => const PasswordResetScreen(),
        '/home': (_) => const MainShell(),
      },
    );
  }
}
