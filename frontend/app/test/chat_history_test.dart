/// 대화 기록 — MAIN_CHAT_02 · SD-12
///
/// 서버 API 와 `ChatService` 는 진작 있었는데 **들어갈 입구가 없었습니다.**
/// 챗봇 화면 왼쪽 위가 `onPressed: () {}` 인 빈 버튼이었습니다.
///
/// 빈 버튼은 화면만 봐서는 정상으로 보입니다(아이콘이 예쁘게 들어가 있음).
/// 그래서 **눌렀을 때 실제로 열리는지**를 테스트로 고정합니다.
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:maeume_care/screens/chat_history_screen.dart';
import 'package:maeume_care/screens/chat_screen.dart';
import 'package:maeume_care/services/api_client.dart';
import 'package:maeume_care/services/chat_service.dart';
import 'package:maeume_care/services/token_storage.dart';
import 'package:maeume_care/theme/app_theme.dart';

const _sessions = [
  {
    'session_id': '019535f0-7c0a-7000-8000-000000000001',
    'persona_type': 'FRIEND',
    'session_summary': '요즘 잠이 잘 안 온다는 이야기를 나눴어요.',
    'started_at': '2026-08-01T09:00:00Z',
    'ended_at': '2026-08-01T09:20:00Z',
  },
  {
    // 진행 중인 대화 — 요약이 아직 없습니다.
    'session_id': '019535f0-7c0a-7000-8000-000000000002',
    'persona_type': 'COUNSELOR',
    'session_summary': null,
    'started_at': '2026-08-02T01:00:00Z',
    'ended_at': null,
  },
];

ChatService _service(http.Client client) {
  final store = MemoryTokenStore();
  store.save(
    accessToken: 'test-token',
    expiresAt: DateTime.now().add(const Duration(hours: 1)),
  );
  return ChatService(
    apiClient: ApiClient(tokenStore: store, httpClient: client),
  );
}

http.Response _json(Object body, [int status = 200]) => http.Response(
      jsonEncode(body),
      status,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );

Future<void> _pumpHistory(WidgetTester tester, http.Client client) async {
  tester.view.physicalSize = const Size(411, 731);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(MaterialApp(
    theme: AppTheme.light,
    home: ChatHistoryScreen(chatService: _service(client)),
  ));
  await tester.pump(const Duration(milliseconds: 300));
}

void main() {
  testWidgets('챗봇 화면의 기록 버튼이 실제로 대화 기록을 연다', (tester) async {
    tester.view.physicalSize = const Size(411, 731);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    final client = MockClient((_) async => _json(_sessions));
    await tester.pumpWidget(MaterialApp(
      theme: AppTheme.light,
      home: Scaffold(body: ChatScreen(chatService: _service(client))),
    ));
    await tester.pump(const Duration(milliseconds: 300));

    // ⚠ 빈 버튼이면 여기서 아무 일도 안 일어나고 테스트가 실패합니다.
    await tester.tap(find.byIcon(Icons.history_rounded));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));

    expect(find.text('대화 기록'), findsOneWidget);
  });

  testWidgets('대화 내용 검색 버튼은 두지 않는다', (tester) async {
    // 화면설계서에 없는 기능입니다. 만들려면 서버에 검색 API 부터 있어야 합니다.
    // 눌리는데 동작하지 않으면 시연에서 바로 드러납니다(마이크 버튼과 같은 이유).
    tester.view.physicalSize = const Size(411, 731);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    final client = MockClient((_) async => _json(_sessions));
    await tester.pumpWidget(MaterialApp(
      theme: AppTheme.light,
      home: Scaffold(body: ChatScreen(chatService: _service(client))),
    ));
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.byIcon(Icons.search_rounded), findsNothing);
  });

  testWidgets('지난 대화 목록에 요약이 보인다', (tester) async {
    await _pumpHistory(tester, MockClient((_) async => _json(_sessions)));
    expect(find.textContaining('잠이 잘 안 온다'), findsOneWidget);
  });

  testWidgets('요약이 없는 진행 중 대화는 상태를 그대로 적는다', (tester) async {
    // 「요약 없음」으로 적으면 실패한 것인지 아직 안 끝난 것인지 알 수 없습니다.
    await _pumpHistory(tester, MockClient((_) async => _json(_sessions)));
    expect(find.text('진행 중'), findsOneWidget);
    expect(find.textContaining('아직 진행 중인 대화예요'), findsOneWidget);
  });

  testWidgets('기록이 없으면 빈 상태를 안내한다', (tester) async {
    await _pumpHistory(tester, MockClient((_) async => _json(const [])));
    expect(find.textContaining('아직 나눈 대화가 없어요'), findsOneWidget);
  });

  testWidgets('삭제는 한 번 더 묻고, 취소하면 지우지 않는다', (tester) async {
    // ⚠ 대화에는 힘들었던 순간이 담겨 있고 되돌릴 수 없습니다.
    //   손이 미끄러지는 정도로 지워지면 안 됩니다.
    var deleteCalls = 0;
    final client = MockClient((request) async {
      if (request.method == 'DELETE') {
        deleteCalls += 1;
        return _json(const {});
      }
      return _json(_sessions);
    });
    await _pumpHistory(tester, client);

    await tester.tap(find.byIcon(Icons.delete_outline_rounded).first);
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('이 대화를 지울까요?'), findsOneWidget);

    await tester.tap(find.text('그대로 둘게요'));
    await tester.pump(const Duration(milliseconds: 300));
    expect(deleteCalls, 0, reason: '취소했는데 서버를 호출하면 안 됩니다');
    expect(find.textContaining('잠이 잘 안 온다'), findsOneWidget);
  });

  testWidgets('확인을 누르면 지우고 목록에서 뺀다', (tester) async {
    var deleteCalls = 0;
    final client = MockClient((request) async {
      if (request.method == 'DELETE') {
        deleteCalls += 1;
        return _json(const {});
      }
      return _json(_sessions);
    });
    await _pumpHistory(tester, client);

    await tester.tap(find.byIcon(Icons.delete_outline_rounded).first);
    await tester.pump(const Duration(milliseconds: 300));
    await tester.tap(find.text('지우기'));
    await tester.pump(const Duration(milliseconds: 400));

    expect(deleteCalls, 1);
    expect(find.textContaining('잠이 잘 안 온다'), findsNothing);
  });
}
