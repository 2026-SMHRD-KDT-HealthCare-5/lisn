/// 선제 접촉 대화 화면이 **라우트로 열릴 때** 제대로 그려지는가
///
/// 왜 이 테스트가 있는가
///   `ChatScreen` 은 평소 `MainShell` 의 `Scaffold` 안에서 그려집니다. 그런데
///   선제 접촉 카드(`MLCM_220`)는 홈에서 **라우트로 push** 합니다. 그 경로에
///   `Scaffold` 를 안 씌웠더니 `Material` 조상이 없어서, 빠른 답장 칩
///   (`ActionChip`)·입력창(`TextField`)·전송 버튼이 전부
///   「No Material widget found」를 던지고 **화면 전체가 빨간 에러**가 됐습니다.
///
///   MainShell 경로에서는 멀쩡해서 개발 중에 한 번도 안 보였습니다.
///   2026.08.22 시연영상을 찍다 답장하기를 눌렀더니 에러 화면이 녹화되어
///   처음 드러났습니다.
///
/// ⚠ **ChatScreen 안에서 칩만 `Material` 로 감싸는 것으로는 안 됩니다.**
///   실제로 해봤는데 입력창과 전송 버튼이 똑같이 터졌습니다. Material 을
///   요구하는 위젯이 한둘이 아니라, **화면을 여는 쪽이 Scaffold 를 주는 것**이
///   맞습니다 — 이 저장소의 다른 push 대상 화면들(리포트·긴급·대화기록·계정)도
///   전부 자기 Scaffold 를 갖고 있습니다.
///
/// ⚠ **이 테스트를 지우지 마세요.** 「한 화면이 두 가지 방식으로 마운트될 때」
///   같은 형태의 결함이 언제든 다시 납니다.
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

const _sid = '11111111-1111-1111-1111-111111111111';
const _opener = '요즘 잠드는 데 걸리는 시간이 조금 길어지고 있네요.';
const _h = {'content-type': 'application/json; charset=utf-8'};

ApiClient _client(MockClient c) {
  final store = MemoryTokenStore();
  store.save(
    accessToken: 'test-token',
    expiresAt: DateTime.now().add(const Duration(hours: 1)),
  );
  return ApiClient(tokenStore: store, httpClient: c);
}

/// 선제 접촉으로 만들어진 세션을 돌려주는 가짜 서버.
MockClient _server() => MockClient((req) async {
      if (req.url.path.contains('/chat/sessions/$_sid')) {
        return http.Response(
          jsonEncode({
            'session_id': _sid,
            'persona_type': 'FRIEND',
            'messages': [
              {
                'role': 'assistant',
                'content': _opener,
                'at': '2026-08-22T00:00:00Z'
              }
            ],
            'session_summary': null,
            'started_at': '2026-08-22T00:00:00Z',
            'ended_at': null,
          }),
          200,
          headers: _h,
        );
      }
      return http.Response('{}', 200, headers: _h);
    });

/// `home_screen.dart` 의 `_openOutreach()` 와 **같은 모양**으로 엽니다.
/// 여기가 어긋나면 이 테스트는 아무것도 지켜주지 못합니다.
Widget _outreachRoute(ChatService chat, SettingsService settings) => MaterialApp(
      home: Builder(
        builder: (context) => ElevatedButton(
          onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(
            builder: (_) => Scaffold(
              body: ChatScreen(
                chatService: chat,
                settingsService: settings,
                resumeSessionId: _sid,
              ),
            ),
          )),
          child: const Text('답장하기'),
        ),
      ),
    );

void main() {
  testWidgets('답장하기로 열면 첫 마디와 빠른 답장 칩이 그려진다', (tester) async {
    final api = _client(_server());
    await tester.pumpWidget(_outreachRoute(
      ChatService(apiClient: api),
      SettingsService(apiClient: api),
    ));

    await tester.tap(find.text('답장하기'));
    await tester.pumpAndSettle();

    // 예외만 안 나고 화면이 비면 시연에서는 똑같이 실패다. 내용까지 본다.
    expect(tester.takeException(), isNull);
    expect(find.text(_opener), findsOneWidget);
    expect(find.byType(ActionChip), findsNWidgets(2));
    expect(find.byType(TextField), findsOneWidget);
  });

  testWidgets('빠른 답장 칩을 누르면 입력창에 채워진다', (tester) async {
    final api = _client(_server());
    await tester.pumpWidget(_outreachRoute(
      ChatService(apiClient: api),
      SettingsService(apiClient: api),
    ));
    await tester.tap(find.text('답장하기'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('마음이 답답해요'));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.widgetWithText(TextField, '마음이 답답해요'), findsOneWidget);
  });
}
