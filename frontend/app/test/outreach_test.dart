/// 선제 접촉이 사용자에게 도달하는가 — `MLCM_220` 6단계
///
/// **서버는 세션을 만들었는데 앱이 안 보여주면 아무 일도 일어나지
/// 않습니다.** 선제 접촉은 「감지 결과가 사용자에게 도달하는 유일한
/// 경로」라, 이 연결이 비면 차별점이 성립하지 않습니다.
///
/// FCM 이 없어도 이 두 경로만 있으면 도달합니다.
///   홈 카드          `pending_outreach`
///   성격 선택 배너    `/chat/sessions/active`
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:maeume_care/models/home_models.dart';
import 'package:maeume_care/screens/chat_screen.dart';
import 'package:maeume_care/screens/home_screen.dart';
import 'package:maeume_care/services/api_client.dart';
import 'package:maeume_care/services/chat_service.dart';
import 'package:maeume_care/services/home_service.dart';
import 'package:maeume_care/services/settings_service.dart';
import 'package:maeume_care/services/token_storage.dart';
import 'package:maeume_care/theme/app_theme.dart';

const _opener = '요즘 잠드는 시각이 평소보다 1시간 20분 늦어졌어요. 별일 없으셨어요?';
const _sid = '11111111-1111-1111-1111-111111111111';

Map<String, dynamic> _home({bool withOutreach = true}) => {
      'action': 'CHAT',
      'emotion_today': null,
      'lifelog_summary': {},
      'ai_summary': null,
      'recommendations': [],
      if (withOutreach)
        'pending_outreach': {
          'session_id': _sid,
          'persona_type': 'FRIEND',
          'opener': _opener,
          'started_at': '2026-08-05T09:00:00Z',
        },
    };

ApiClient _client(MockClient c) {
  final store = MemoryTokenStore();
  store.save(
    accessToken: 'test-token',
    expiresAt: DateTime.now().add(const Duration(hours: 1)),
  );
  return ApiClient(tokenStore: store, httpClient: c);
}

const _h = {'content-type': 'application/json; charset=utf-8'};

void main() {
  group('모델', () {
    test('pending_outreach 를 읽는다', () {
      final s = HomeSnapshot.fromJson(_home());
      expect(s.pendingOutreach, isNotNull);
      expect(s.pendingOutreach!.opener, _opener);
      expect(s.pendingOutreach!.sessionId, _sid);
    });

    test('없으면 null 이다', () {
      expect(HomeSnapshot.fromJson(_home(withOutreach: false)).pendingOutreach,
          isNull);
    });
  });

  group('홈 카드 — 주 경로', () {
    testWidgets('첫 문장을 그대로 보여준다', (tester) async {
      // 「새 메시지가 있습니다」로 감추면 **왜 말을 걸었는지 모른 채**
      // 열어야 한다. 근거를 함께 보여주는 것이 감시로 읽히지 않게 하는
      // 조건이다.
      final service = HomeService(
        apiClient: _client(MockClient(
            (_) async => http.Response(jsonEncode(_home()), 200, headers: _h))),
      );

      await tester
          .pumpWidget(MaterialApp(home: HomeScreen(homeService: service)));
      await tester.pumpAndSettle();

      expect(find.text('마음이가 먼저 말을 걸었어요'), findsOneWidget);
      expect(find.text(_opener), findsOneWidget);
    });

    testWidgets('선제 접촉이 없으면 카드도 없다', (tester) async {
      final service = HomeService(
        apiClient: _client(MockClient((_) async => http.Response(
            jsonEncode(_home(withOutreach: false)), 200,
            headers: _h))),
      );

      await tester
          .pumpWidget(MaterialApp(home: HomeScreen(homeService: service)));
      await tester.pumpAndSettle();

      expect(find.text('마음이가 먼저 말을 걸었어요'), findsNothing);
    });
  });

  group('성격 선택 배너 — 챗봇 탭으로 바로 들어온 경우', () {
    /// `/chat/sessions/active` 와 프로필만 답하는 가짜 서버.
    ({ChatService chat, SettingsService settings, List<String> paths}) build({
      required bool outreach,
    }) {
      final paths = <String>[];
      final client = MockClient((req) async {
        paths.add(req.url.path);
        if (req.url.path.endsWith('/chat/sessions/active')) {
          if (!outreach) return http.Response('', 204);
          return http.Response(
            jsonEncode({
              'session_id': _sid,
              'persona_type': 'FRIEND',
              'origin': 'OUTREACH',
              'messages': [
                {'role': 'assistant', 'content': _opener},
              ],
              'started_at': '2026-08-05T09:00:00Z',
            }),
            200,
            headers: _h,
          );
        }
        if (req.url.path.endsWith('/users/me')) {
          return http.Response(
            jsonEncode({
              'user_id': '00000000-0000-0000-0000-000000000001',
              'email': 'a@b.c',
              'name': '테스터',
              'persona_type': 'FRIEND',
              'role': 'USER',
            }),
            200,
            headers: _h,
          );
        }
        return http.Response('[]', 200, headers: _h);
      });
      final api = _client(client);
      return (
        chat: ChatService(apiClient: api),
        settings: SettingsService(apiClient: api),
        paths: paths,
      );
    }

    testWidgets('열려 있으면 배너가 뜬다', (tester) async {
      final s = build(outreach: true);
      await tester.pumpWidget(MaterialApp(
        theme: AppTheme.light,
        home: Scaffold(
          body: ChatScreen(chatService: s.chat, settingsService: s.settings),
        ),
      ));
      await tester.pumpAndSettle();

      expect(find.text('마음이가 먼저 말을 걸었어요'), findsOneWidget);
    });

    testWidgets('204 면 배너가 없다', (tester) async {
      // 없을 때 빈 객체를 주면 클라이언트가 분기를 하나 더 만들게 된다.
      final s = build(outreach: false);
      await tester.pumpWidget(MaterialApp(
        theme: AppTheme.light,
        home: Scaffold(
          body: ChatScreen(chatService: s.chat, settingsService: s.settings),
        ),
      ));
      await tester.pumpAndSettle();

      expect(find.text('마음이가 먼저 말을 걸었어요'), findsNothing);
    });
  });

  group('세션 이어받기', () {
    testWidgets('새 세션을 만들지 않는다', (tester) async {
      // 서버가 첫 발화까지 넣어 만들어둔 세션이다. 여기서 startSession 을
      // 부르면 **그 대화가 버려지고 빈 세션이 하나 더 생긴다.**
      final posted = <String>[];
      final client = MockClient((req) async {
        if (req.method == 'POST') posted.add(req.url.path);
        if (req.url.path.endsWith('/chat/sessions/$_sid')) {
          return http.Response(
            jsonEncode({
              'session_id': _sid,
              'persona_type': 'FRIEND',
              'started_at': '2026-08-05T09:00:00Z',
              'messages': [
                {'role': 'assistant', 'content': _opener},
              ],
            }),
            200,
            headers: _h,
          );
        }
        return http.Response('{}', 200, headers: _h);
      });
      final api = _client(client);

      await tester.pumpWidget(MaterialApp(
        theme: AppTheme.light,
        home: Scaffold(
          body: ChatScreen(
            chatService: ChatService(apiClient: api),
            settingsService: SettingsService(apiClient: api),
            resumeSessionId: _sid,
          ),
        ),
      ));
      await tester.pumpAndSettle();

      expect(posted.where((p) => p.endsWith('/chat/sessions')), isEmpty,
          reason: '이미 있는 세션인데 새로 만들었습니다');
      expect(find.text(_opener), findsOneWidget,
          reason: '첫 발화가 대화 화면에 그대로 있어야 합니다');
    });
  });
}
