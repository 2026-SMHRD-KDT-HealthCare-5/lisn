import 'dart:async';

import 'package:flutter/material.dart';

import '../services/app_services.dart';
import '../services/lifelog_sync.dart';
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

class _MainShellState extends State<MainShell> with WidgetsBindingObserver {
  late int currentIndex = widget.initialTab;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _pullLifelog();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _pullLifelog();
  }

  /// 앱을 열거나 되돌아왔을 때 라이프로그를 한 번 당깁니다 — MLCM_200.
  ///
  /// ⚠ 백그라운드 워커가 있는데도 필요합니다. 워커는 15분 주기이고 Doze 로
  ///   더 밀릴 수 있어서, 방금 걸은 사용자가 앱을 열면 **어제 값이 그대로**
  ///   보입니다. 여기서 당겨야 「열면 최신」이 됩니다.
  ///
  /// ⚠ 결과를 기다리지 않고 실패도 삼킵니다. 권한이 없거나 서버가 죽어도
  ///   홈 화면은 떠야 합니다. 실패분은 큐에 남아 다음 주기가 가져갑니다.
  void _pullLifelog() {
    unawaited(AppServices.lifelogSync.sync().catchError(
      (Object e) => const SyncResult(SyncOutcome.failedAndQueued),
    ));
  }

  @override
  Widget build(BuildContext context) {
    final screens = [
      const HomeScreen(),
      const ChatScreen(),
      const LifelogScreen(),
      const SettingsScreen(),
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
