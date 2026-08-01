import 'package:flutter/material.dart';

import '../theme/app_theme.dart';
import 'chat_screen.dart';
import 'home_screen.dart';
import 'lifelog_screen.dart';
import 'settings_screen.dart';

class MainShell extends StatefulWidget {
  const MainShell({super.key, this.initialTab = 0});

  /// 처음 열 탭. 0 홈 · 1 챗봇 · 2 라이프로그 · 3 설정.
  ///
  /// 평소에는 0 입니다. 화면설계서용으로 특정 화면을 바로 띄울 때만 씁니다
  /// (`--dart-define=SCREEN=...`, `main.dart` 참조).
  final int initialTab;

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  late int currentIndex = widget.initialTab;

  @override
  Widget build(BuildContext context) {
    final screens = [
      const HomeScreen(),
      const ChatScreen(),
      const LifelogScreen(),
      const SettingsScreen()
    ];
    return Scaffold(
      body: IndexedStack(index: currentIndex, children: screens),
      bottomNavigationBar: NavigationBar(
        selectedIndex: currentIndex,
        onDestinationSelected: (index) => setState(() => currentIndex = index),
        indicatorColor: const Color(0xFFE8ECFF),
        backgroundColor: Colors.white,
        destinations: const [
          NavigationDestination(
              icon: Icon(Icons.home_outlined),
              selectedIcon: Icon(Icons.home_rounded, color: AppColors.primary),
              label: '홈'),
          NavigationDestination(
              icon: Icon(Icons.chat_bubble_outline_rounded),
              selectedIcon:
                  Icon(Icons.chat_bubble_rounded, color: AppColors.primary),
              label: 'AI 챗봇'),
          NavigationDestination(
              icon: Icon(Icons.monitor_heart_outlined),
              selectedIcon:
                  Icon(Icons.monitor_heart_rounded, color: AppColors.primary),
              label: '라이프로그'),
          NavigationDestination(
              icon: Icon(Icons.settings_outlined),
              selectedIcon:
                  Icon(Icons.settings_rounded, color: AppColors.primary),
              label: '설정'),
        ],
      ),
    );
  }
}
