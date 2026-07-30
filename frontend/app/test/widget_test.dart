import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:maeume_care/main.dart';

void main() {
  testWidgets('메인 화면과 하단 탭을 표시한다', (tester) async {
    tester.view.physicalSize = const Size(360, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(const MaeumeApp());
    await tester.pumpAndSettle();

    expect(find.text('안녕하세요, 지은님 😊'), findsOneWidget);
    expect(find.text('홈'), findsOneWidget);
    expect(find.text('AI 챗봇'), findsOneWidget);
    expect(find.text('라이프로그'), findsOneWidget);
    expect(find.text('설정'), findsOneWidget);

    await tester.tap(find.text('AI 챗봇'));
    await tester.pumpAndSettle();
    expect(find.text('오늘은 어떤 방식으로\n이야기 나눌까요?'), findsOneWidget);
  });

  testWidgets('로그인 경로에서 로그인할 수 있다', (tester) async {
    tester.view.physicalSize = const Size(360, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(const MaeumeApp());
    await tester.pumpAndSettle();

    tester.state<NavigatorState>(find.byType(Navigator)).pushNamed('/login');
    await tester.pumpAndSettle();

    expect(find.text('다시 만나 반가워요'), findsOneWidget);
    await tester.tap(find.text('로그인'));
    await tester.pumpAndSettle();
    expect(find.text('안녕하세요, 지은님 😊'), findsOneWidget);
  });
}
