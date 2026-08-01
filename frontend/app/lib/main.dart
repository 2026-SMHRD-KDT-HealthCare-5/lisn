import 'package:flutter/material.dart';

import 'screens/auth_gate.dart';
import 'screens/login_screen.dart';
import 'screens/main_shell.dart';
import 'screens/password_reset_screen.dart';
import 'services/app_services.dart';
import 'theme/app_theme.dart';

final appNavigatorKey = GlobalKey<NavigatorState>();

void main() {
  AppServices.apiClient.onUnauthorized = () {
    appNavigatorKey.currentState?.pushNamedAndRemoveUntil(
      '/login',
      (_) => false,
    );
  };
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
        '/': (_) => const AuthGate(),
        '/login': (_) => const LoginScreen(),
        '/password-reset': (_) => const PasswordResetScreen(),
        '/home': (_) => const MainShell(),
      },
    );
  }
}
