import 'package:flutter/material.dart';

import 'screens/login_screen.dart';
import 'screens/main_shell.dart';
import 'theme/app_theme.dart';

void main() {
  runApp(const MaeumeApp());
}

class MaeumeApp extends StatelessWidget {
  const MaeumeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '마음이',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      initialRoute: '/',
      routes: {
        '/': (_) => const MainShell(),
        '/login': (_) => const LoginScreen(),
      },
    );
  }
}
