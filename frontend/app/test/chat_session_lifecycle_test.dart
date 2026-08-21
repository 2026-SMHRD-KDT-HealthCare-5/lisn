/// 대화 유지·종료 — MAIN_CHAT_01 · MLCM_310
///
/// **뒤로가기(←)와 「대화 종료」는 결과가 다릅니다.** 전에는 둘 다
/// `endSession` 을 불렀습니다. 그래서 성격 카드를 눌렀다가 한 마디도 안 하고
/// 나오면 **빈 세션이 종료 처리돼 대화 기록에 쌓였습니다.** 서버는 메시지가
/// 없으면 요약을 만들지 않으므로(`llm.summarize_session`) 「요약을 만들지
/// 못했습니다」만 적힌 줄이 남습니다 — 실제로 13건 중 12건이 그랬습니다
/// (2026.08.03 실측).
///
/// 여기서 고정하는 것:
///   ← 는 서버를 부르지 않고 대화를 남긴다
///   「대화 종료」는 나눈 이야기가 있으면 PATCH /end, 없으면 DELETE
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:maeume_care/screens/chat_screen.dart';
import 'package:maeume_care/services/api_client.dart';
import 'package:maeume_care/services/chat_service.dart';
import 'package:maeume_care/services/settings_service.dart';
import 'package:maeume_care/services/token_storage.dart';
import 'package:maeume_care/theme/app_theme.dart';

const _sessionId = '019535f0-7c0a-7000-8000-0000000000aa';

Map<String, Object?> _profile(String persona) => {
      'user_id': '019535f0-7c0a-7000-8000-000000000001',
      'email': 'demo@lisn-test.example',
      'name': '데모',
      'phone': null,
      'height_cm': null,
      'gender': null,
      'persona_type': persona,
      'role': 'USER',
    };

/// 오간 요청을 `METHOD 경로` 로 적어 둡니다. 종료 방식이 갈리는지 보려면
/// 메서드까지 봐야 합니다.
class _Recorder {
  final calls = <String>[];

  http.Client client({String persona = 'FRIEND'}) =>
      MockClient((request) async {
        final path = request.url.path;
        calls.add('${request.method} $path');

        Object? body;
        if (path.endsWith('/auth/me') || path.endsWith('/users/me')) {
          body = _profile(persona);
        } else if (path.endsWith('/connections')) {
          body = const [];
        } else if (request.method == 'POST' &&
            path.endsWith('/chat/sessions')) {
          body = {
            'session_id': _sessionId,
            'persona_type': persona,
            'greeting': '안녕하세요. 오늘 하루는 어떠셨어요?',
            'started_at': DateTime.now().toUtc().toIso8601String(),
          };
        } else if (path.contains('/messages')) {
          body = {
            'reply': '그러셨군요. 조금 더 이야기해 주실래요?',
            'risk': {'level': 'NORMAL', 'action': 'CHAT', 'source': 'LLM'},
          };
        } else if (request.method == 'DELETE') {
          return http.Response('', 204);
        } else {
          body = <String, Object?>{};
        }

        return http.Response(jsonEncode(body), 200,
            headers: {'content-type': 'application/json; charset=utf-8'});
      });
}

ApiClient _api(http.Client client) {
  final store = MemoryTokenStore();
  store.save(
    accessToken: 'test-token',
    expiresAt: DateTime.now().add(const Duration(hours: 1)),
  );
  return ApiClient(tokenStore: store, httpClient: client);
}

Future<void> _pump(WidgetTester tester, _Recorder rec) async {
  tester.view.physicalSize = const Size(411, 900);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);

  final api = _api(rec.client());
  await tester.pumpWidget(MaterialApp(
    theme: AppTheme.light,
    home: Scaffold(
      body: ChatScreen(
        chatService: ChatService(apiClient: api),
        settingsService: SettingsService(apiClient: api),
      ),
    ),
  ));
  await tester.pump(const Duration(milliseconds: 300));
}

Future<void> _startTalking(WidgetTester tester) async {
  await tester.tap(find.text('이 성격으로 대화하기').first);
  await tester.pump(const Duration(milliseconds: 300));
}

Future<void> _say(WidgetTester tester, String text) async {
  await tester.enterText(find.byType(TextField), text);
  await tester.testTextInput.receiveAction(TextInputAction.done);
  await tester.pump(const Duration(milliseconds: 300));
}

void main() {
  group('뒤로가기(←)', () {
    testWidgets('대화를 끝내지 않는다 — 서버를 부르지 않는다', (tester) async {
      final rec = _Recorder();
      await _pump(tester, rec);
      await _startTalking(tester);
      await _say(tester, '오늘 좀 힘들었어요');

      rec.calls.clear();
      await tester.tap(find.byIcon(Icons.arrow_back_rounded));
      await tester.pump(const Duration(milliseconds: 300));

      expect(rec.calls, isEmpty,
          reason: '← 는 나가기일 뿐입니다. 끝내는 것은 「대화 종료」 하나뿐입니다');
    });

    testWidgets('나온 뒤 이어서 대화하면 하던 내용이 그대로 있다', (tester) async {
      final rec = _Recorder();
      await _pump(tester, rec);
      await _startTalking(tester);
      await _say(tester, '오늘 좀 힘들었어요');

      await tester.tap(find.byIcon(Icons.arrow_back_rounded));
      await tester.pump(const Duration(milliseconds: 300));

      // 선택 화면에 돌아갈 길이 남아 있어야 합니다.
      expect(find.text('나누던 이야기가 남아 있어요'), findsOneWidget);

      await tester.tap(find.text('나누던 이야기가 남아 있어요'));
      await tester.pump(const Duration(milliseconds: 300));

      expect(find.text('오늘 좀 힘들었어요'), findsOneWidget);
      expect(find.text('그러셨군요. 조금 더 이야기해 주실래요?'), findsOneWidget);
    });
  });

  group('대화 종료', () {
    testWidgets('나눈 이야기가 있으면 확인을 받고 PATCH /end 로 끝낸다', (tester) async {
      final rec = _Recorder();
      await _pump(tester, rec);
      await _startTalking(tester);
      await _say(tester, '오늘 좀 힘들었어요');

      rec.calls.clear();
      await tester.tap(find.text('대화 종료'));
      await tester.pump(const Duration(milliseconds: 300));

      // 잘못 눌렀을 때 되돌릴 수 있어야 합니다 — ← 바로 옆이라 더 그렇습니다.
      expect(find.text('대화를 끝낼까요?'), findsOneWidget);
      await tester.tap(find.text('종료하기'));
      await tester.pump(const Duration(milliseconds: 300));

      expect(
          rec.calls, contains('PATCH /api/v1/chat/sessions/$_sessionId/end'));
      expect(find.text('오늘 좀 힘들었어요'), findsNothing, reason: '종료하면 초기화됩니다');
    });

    testWidgets('한 마디도 안 했으면 묻지 않고 세션을 지운다', (tester) async {
      // ⚠ 여기가 「요약을 만들지 못했습니다」의 출처였습니다. 인사말만 있는
      //   세션을 종료하면 서버가 요약을 못 만들어 빈 기록이 남습니다.
      final rec = _Recorder();
      await _pump(tester, rec);
      await _startTalking(tester);

      rec.calls.clear();
      await tester.tap(find.text('대화 종료'));
      await tester.pump(const Duration(milliseconds: 300));

      expect(find.text('대화를 끝낼까요?'), findsNothing, reason: '잃을 것이 없으면 묻지 않습니다');
      expect(rec.calls, contains('DELETE /api/v1/chat/sessions/$_sessionId'));
      expect(rec.calls.any((c) => c.endsWith('/end')), isFalse,
          reason: '빈 세션을 종료로 남기면 요약 없는 기록이 쌓입니다');
    });
  });

  group('다른 성격 카드', () {
    testWidgets('진행 중인 대화가 있으면 확인을 받는다', (tester) async {
      final rec = _Recorder();
      await _pump(tester, rec);
      await _startTalking(tester);
      await _say(tester, '오늘 좀 힘들었어요');

      await tester.tap(find.byIcon(Icons.arrow_back_rounded));
      await tester.pump(const Duration(milliseconds: 300));

      // 두 번째 카드로 넘겨서 다른 성격을 고릅니다.
      await tester.fling(find.byType(PageView), const Offset(-400, 0), 1000);
      await tester.pumpAndSettle();
      await tester.tap(find.text('이 성격으로 대화하기').first);
      await tester.pump(const Duration(milliseconds: 300));

      expect(find.text('지금 대화를 끝낼까요?'), findsOneWidget);

      await tester.tap(find.text('계속 이야기할래요'));
      await tester.pump(const Duration(milliseconds: 300));
      expect(find.text('나누던 이야기가 남아 있어요'), findsOneWidget,
          reason: '취소했으니 하던 대화가 살아 있어야 합니다');
    });
  });
}
