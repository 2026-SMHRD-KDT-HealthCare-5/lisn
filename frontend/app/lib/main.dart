import 'package:flutter/material.dart';

import 'dev_screens.dart';
import 'screens/auth_gate.dart';
import 'screens/login_screen.dart';
import 'screens/main_shell.dart';
import 'screens/password_reset_screen.dart';
import 'services/app_services.dart';
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
