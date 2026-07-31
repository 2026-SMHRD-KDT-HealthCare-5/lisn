import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:maeume_care/screens/login_screen.dart';
import 'package:maeume_care/screens/main_shell.dart';
import 'package:maeume_care/screens/password_reset_screen.dart';
import 'package:maeume_care/theme/app_theme.dart';

void main() {
  testWidgets('메인 화면과 하단 탭을 표시한다', (tester) async {
    tester.view.physicalSize = const Size(360, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      MaterialApp(theme: AppTheme.light, home: const MainShell()),
    );
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

  testWidgets('미로그인 사용자는 로그인 화면과 입력 검증을 본다', (tester) async {
    tester.view.physicalSize = const Size(360, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light,
        home: const LoginScreen(),
        routes: {
          '/password-reset': (_) => const PasswordResetScreen(),
        },
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('다시 만나 반가워요'), findsOneWidget);
    await tester.tap(find.text('로그인'));
    await tester.pumpAndSettle();
    expect(find.text('올바른 이메일을 입력해주세요'), findsOneWidget);
    expect(find.text('비밀번호는 8자 이상 입력해주세요'), findsOneWidget);
  });

  testWidgets('비밀번호 재설정 화면으로 이동한다', (tester) async {
    tester.view.physicalSize = const Size(360, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light,
        home: const LoginScreen(),
        routes: {
          '/password-reset': (_) => const PasswordResetScreen(),
        },
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('비밀번호를 잊으셨나요?'));
    await tester.pumpAndSettle();
    expect(find.text('비밀번호를\n다시 설정해요'), findsOneWidget);
    expect(find.text('인증 메일 보내기'), findsOneWidget);
  });
}
