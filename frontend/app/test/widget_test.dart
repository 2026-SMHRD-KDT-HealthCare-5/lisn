import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:maeume_care/screens/chat_screen.dart';
import 'package:maeume_care/screens/emergency_screen.dart';
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

  testWidgets('긴급 상담 화면은 109 전화 연결만 실행한다', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    var callRequested = false;
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light,
        home: EmergencyScreen(
          callLauncher: () async {
            callRequested = true;
            return true;
          },
        ),
      ),
    );

    expect(find.text('지금 많이 힘드신 것 같아요'), findsOneWidget);
    expect(find.text('109'), findsOneWidget);
    expect(find.byType(Checkbox), findsNothing);
    expect(find.textContaining('정서 분석 데이터는 상담기관으로 전송되지 않아요'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('emergency-call-button')));
    await tester.pumpAndSettle();
    expect(callRequested, isTrue);
  });

  testWidgets('챗봇 EMERGENCY 응답은 추가 조회 없이 긴급 화면으로 전환한다', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    var replyCalls = 0;
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light,
        home: Scaffold(
          body: ChatScreen(
            replyBuilder: (message, persona) {
              replyCalls += 1;
              return const ChatReply(
                '',
                action: ChatResponseAction.emergency,
              );
            },
          ),
        ),
      ),
    );

    await tester.tap(find.text('다정한 공감가'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byType(TextField),
      '도움이 필요해요',
    );
    await tester.tap(find.byIcon(Icons.send_rounded));
    await tester.pumpAndSettle();

    expect(replyCalls, 1);
    expect(find.text('지금 많이 힘드신 것 같아요'), findsOneWidget);
    expect(find.text('109'), findsOneWidget);
  });
}
