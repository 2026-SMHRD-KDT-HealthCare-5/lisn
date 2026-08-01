import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:maeume_care/services/api_client.dart';
import 'package:maeume_care/services/chat_service.dart';
import 'package:maeume_care/services/token_storage.dart';

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
    // pumpAndSettle 을 쓰지 않습니다. 홈이 서버 응답을 기다리는 동안
    // 로딩 인디케이터가 계속 돌아 settle 이 끝나지 않습니다.
    await tester.pump(const Duration(milliseconds: 300));

    // 인사말은 하드코딩이 아니라 로그인한 사용자 이름을 씁니다.
    // MainShell 은 이름을 넘기지 않으므로 이름 없는 형태가 나옵니다.
    expect(find.text('안녕하세요 😊'), findsOneWidget);
    expect(find.text('홈'), findsOneWidget);
    expect(find.text('AI 챗봇'), findsOneWidget);
    expect(find.text('라이프로그'), findsOneWidget);
    expect(find.text('설정'), findsOneWidget);

    await tester.tap(find.text('AI 챗봇'));
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('오늘은 어떤 방식으로\n이야기 나눌까요?'), findsOneWidget);
  });

  testWidgets('로그인은 마스코트 화면에서 시작하고 입력란은 단계적으로 나타난다', (tester) async {
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

    // 0단계 — 입력란이 아직 없고 회원가입만 함께 보인다.
    expect(find.text('다시 만나 반가워요'), findsOneWidget);
    expect(find.byType(TextFormField), findsNothing);
    // 회원가입은 테두리 없이 글자만 둡니다. Text.rich 라 조각으로 찾습니다.
    expect(find.textContaining('회원가입'), findsOneWidget);
    expect(find.text('비밀번호를 잊으셨나요?'), findsNothing);

    // 1단계 — 이메일만.
    await tester.tap(find.text('로그인'));
    await tester.pumpAndSettle();
    expect(find.byType(TextFormField), findsOneWidget);
    expect(find.text('비밀번호를 잊으셨나요?'), findsNothing);
    // 로그인을 시작하면 회원가입은 감춘다.
    expect(find.textContaining('회원가입'), findsNothing);

    // 2단계 — 이메일이 형태를 갖추면 비밀번호와 재설정 링크가 함께 나타난다.
    await tester.enterText(find.byType(TextFormField), 'user@example.com');
    await tester.pumpAndSettle();
    expect(find.byType(TextFormField), findsNWidgets(2));
    expect(find.text('비밀번호를 잊으셨나요?'), findsOneWidget);
  });

  testWidgets('로그인 단계에서 비밀번호 검증이 동작한다', (tester) async {
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

    await tester.tap(find.text('로그인'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextFormField), 'user@example.com');
    await tester.pumpAndSettle();

    // 비밀번호를 비운 채 제출하면 그 칸만 걸린다.
    await tester.tap(find.text('로그인'));
    await tester.pumpAndSettle();
    expect(find.text('비밀번호는 8자 이상 입력해주세요'), findsOneWidget);
    expect(find.text('올바른 이메일을 입력해주세요'), findsNothing);
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

    // 재설정 링크는 비밀번호 단계에서만 나오므로 거기까지 진행한다.
    await tester.tap(find.text('로그인'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextFormField), 'user@example.com');
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

    // MLCM_510 2단계 — CRITICAL 이면 서버가 reply 를 null 로 내려보내고,
    // 앱은 답변을 그리지 않고 긴급 화면으로 넘어가야 한다.
    var messageCalls = 0;
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/chat/sessions')) {
        return http.Response(
          jsonEncode({
            'session_id': '019535f0-7c0a-7000-8000-000000000010',
            'persona_type': 'FRIEND',
            'greeting': '오늘 하루는 어떠셨나요?',
            'started_at': '2026-08-01T09:00:00Z',
          }),
          201,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      }
      if (request.url.path.endsWith('/messages')) {
        messageCalls += 1;
        return http.Response(
          jsonEncode({
            'reply': null,
            'risk': {
              'level': 'CRITICAL',
              'action': 'EMERGENCY',
              'source': 'KEYWORD',
            },
          }),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      }
      return http.Response('{}', 200);
    });

    final tokenStore = MemoryTokenStore();
    await tokenStore.save(
      accessToken: 'test-token',
      expiresAt: DateTime.now().add(const Duration(hours: 1)),
    );
    final chatService = ChatService(
      apiClient: ApiClient(tokenStore: tokenStore, httpClient: client),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light,
        home: Scaffold(body: ChatScreen(chatService: chatService)),
      ),
    );

    await tester.tap(find.text('다정한 공감가'));
    await tester.pumpAndSettle();
    expect(find.text('오늘 하루는 어떠셨나요?'), findsOneWidget);

    await tester.enterText(find.byType(TextField), '도움이 필요해요');
    await tester.tap(find.byIcon(Icons.send_rounded));
    await tester.pumpAndSettle();

    expect(messageCalls, 1);
    expect(find.text('지금 많이 힘드신 것 같아요'), findsOneWidget);
    expect(find.text('109'), findsOneWidget);
  });

  testWidgets('음성 입력은 범위에서 제외돼 마이크 버튼이 없다', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    final client = MockClient((request) async => http.Response(
          jsonEncode({
            'session_id': '019535f0-7c0a-7000-8000-000000000011',
            'persona_type': 'FRIEND',
            'greeting': '안녕하세요',
            'started_at': '2026-08-01T09:00:00Z',
          }),
          201,
          headers: {'content-type': 'application/json; charset=utf-8'},
        ));
    final tokenStore = MemoryTokenStore();
    await tokenStore.save(
      accessToken: 'test-token',
      expiresAt: DateTime.now().add(const Duration(hours: 1)),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light,
        home: Scaffold(
          body: ChatScreen(
            chatService: ChatService(
              apiClient: ApiClient(tokenStore: tokenStore, httpClient: client),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('다정한 공감가'));
    await tester.pumpAndSettle();

    expect(find.byIcon(Icons.mic_none_rounded), findsNothing);
  });
}
