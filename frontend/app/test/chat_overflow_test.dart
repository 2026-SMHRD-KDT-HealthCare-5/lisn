/// 페르소나 카드가 화면을 넘치지 않아야 한다 — MAIN_CHAT_01
///
/// 카드 안에 마스코트·라벨·제목·설명 2줄·태그·버튼이 세로로 쌓여 있는데
/// **카드 높이는 화면에서 남는 만큼**입니다. 하나만 키워도 바로 넘칩니다.
/// 실제로 `BOTTOM OVERFLOWED BY 31 PIXELS` 가 떠 있었습니다.
///
/// 넘침은 디버그 빌드에서만 노란 줄무늬로 보이고 **릴리스에서는 그냥 잘립니다.**
/// 그래서 눈으로 확인하는 것에 기대지 않고 테스트로 잡습니다.
///
/// 위젯 테스트는 오버플로가 나면 예외를 던지므로, 화면 크기만 바꿔가며
/// 그려보면 됩니다.
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:maeume_care/screens/chat_screen.dart';
import 'package:maeume_care/theme/app_theme.dart';

/// 실제 기기와 같은 조건으로 그립니다.
///
/// ⚠ **`MainShell` 의 하단 네비게이션(약 80dp)을 빼먹으면 재현되지 않습니다.**
///   처음에 `Scaffold(body: ChatScreen())` 로만 그렸다가 카드에 578dp 가 주어져
///   테스트가 통과했습니다. 실기기에서는 약 344dp 였고 31px 넘쳤습니다.
///
/// ⚠ 크기도 실기기 기준입니다. 에뮬레이터(1080x1920 @420dpi)의 논리 크기가
///   **411x731** 입니다. 844 로 잡으면 세로가 100dp 넘게 남아 안 걸립니다.
Future<void> _pumpAt(WidgetTester tester, Size size,
    {double textScale = 1.0}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  // ⚠ 상태바·제스처바 여백까지 넣어야 재현됩니다. 이걸 빼면 세로가 48dp 더
  //   생겨 411x731 에서도 안 걸립니다(실제로 처음에 그래서 못 잡았습니다).
  //   ChatScreen 이 SafeArea 를 쓰므로 이 여백만큼 본문이 줄어듭니다.
  tester.view.padding = const FakeViewPadding(top: 24, bottom: 24);
  tester.view.viewPadding = const FakeViewPadding(top: 24, bottom: 24);
  addTearDown(tester.view.reset);

  await tester.pumpWidget(MaterialApp(
    theme: AppTheme.light,
    home: MediaQuery(
      data: MediaQueryData(textScaler: TextScaler.linear(textScale)),
      child: Scaffold(
        body: const ChatScreen(),
        // MainShell 과 같은 높이를 차지하게 둡니다.
        bottomNavigationBar: NavigationBar(
          selectedIndex: 1,
          onDestinationSelected: (_) {},
          destinations: const [
            NavigationDestination(icon: Icon(Icons.home_outlined), label: '홈'),
            NavigationDestination(
                icon: Icon(Icons.chat_bubble_outline_rounded), label: 'AI 챗봇'),
            NavigationDestination(
                icon: Icon(Icons.monitor_heart_outlined), label: '라이프로그'),
            NavigationDestination(
                icon: Icon(Icons.settings_outlined), label: '설정'),
          ],
        ),
      ),
    ),
  ));
  // pumpAndSettle 을 쓰지 않습니다 — 서버 응답을 기다리는 인디케이터가
  // 계속 돌면 settle 이 끝나지 않습니다.
  await tester.pump(const Duration(milliseconds: 300));
}

void main() {
  testWidgets('에뮬레이터 크기(411x731)에서 넘치지 않는다', (tester) async {
    // ⚠ 이 케이스는 **재현 테스트가 아닙니다.** 실기기에서는 이 크기에서
    //   31px 넘쳤지만, 위젯 테스트로는 하단 네비게이션·여백을 맞춰도 몇 dp 가
    //   남아 걸리지 않습니다. 실제 방어선은 아래 두 개(짧은 기기·글꼴 확대)이고,
    //   고치기 전 코드로 돌리면 그 둘이 실패합니다.
    await _pumpAt(tester, const Size(411, 731));
    expect(tester.takeException(), isNull);
    expect(find.text('따스한 공감형'), findsOneWidget);
  });

  testWidgets('세로가 더 짧은 기기에서도 넘치지 않는다', (tester) async {
    await _pumpAt(tester, const Size(360, 640));
    expect(tester.takeException(), isNull);
  });

  testWidgets('글꼴 확대 설정에서도 넘치지 않는다', (tester) async {
    // 접근성 설정으로 글꼴을 키우면 같은 카드가 더 커집니다. 시스템 설정이라
    // 앱이 막을 수 없고, 이때 잘려 보이면 버튼을 못 찾습니다.
    await _pumpAt(tester, const Size(411, 731), textScale: 1.3);
    expect(tester.takeException(), isNull);
  });

  testWidgets('설계 기준 390x844 에서도 넘치지 않는다', (tester) async {
    await _pumpAt(tester, const Size(390, 844));
    expect(tester.takeException(), isNull);
  });

  testWidgets('두 성격 카드를 스와이프로 넘길 수 있다', (tester) async {
    await _pumpAt(tester, const Size(411, 731));
    expect(find.text('따스한 공감형'), findsOneWidget);
    await tester.drag(find.byType(PageView), const Offset(-400, 0));
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.text('현실적인 조언형'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
