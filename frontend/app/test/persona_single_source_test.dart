/// 대화 성격을 고르는 곳은 하나여야 한다 — MAIN_CHAT_01
///
/// 전에는 **설정에도 라디오 버튼이 있어 두 곳에서 바꿀 수 있었습니다.** 게다가
/// 챗봇은 세션을 시작할 때 고른 값을 **항상 명시로 넘겨서** 서버의
/// `user.persona_type` 폴백을 타지 않았습니다. 즉 **설정에서 바꿔도 챗봇 동작이
/// 바뀌지 않았습니다.** 코드 주석은 「여기서 바꾸면 기본값이 됩니다」라고 적혀
/// 있었지만 사실이 아니었습니다.
///
/// 이 앱은 **성격 선택과 대화 시작이 한 동작**입니다(카드 버튼이 「이 성격으로
/// 대화하기」). 그래서 설정에서 「바꾸기」를 누르면 결국 대화가 시작돼,
/// 설정 변경치고는 이상한 흐름이 됩니다.
///
/// **챗봇 탭이 확인 화면 역할을 합니다.** 열면 최근에 고른 성격이 먼저 뜨고
/// 「최근 대화」 표시가 붙습니다. 그래서 설정에서는 항목 자체를 뺐습니다.
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:maeume_care/screens/chat_screen.dart';
import 'package:maeume_care/screens/settings_screen.dart';
import 'package:maeume_care/services/api_client.dart';
import 'package:maeume_care/services/chat_service.dart';
import 'package:maeume_care/services/settings_service.dart';
import 'package:maeume_care/services/token_storage.dart';
import 'package:maeume_care/theme/app_theme.dart';

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

ApiClient _api(http.Client client) {
  final store = MemoryTokenStore();
  store.save(
    accessToken: 'test-token',
    expiresAt: DateTime.now().add(const Duration(hours: 1)),
  );
  return ApiClient(tokenStore: store, httpClient: client);
}

http.Client _client(String persona, {void Function(http.BaseRequest)? spy}) =>
    MockClient((request) async {
      spy?.call(request);
      final body = request.url.path.endsWith('/connections')
          ? jsonEncode(const [])
          : jsonEncode(_profile(persona));
      return http.Response(body, 200,
          headers: {'content-type': 'application/json; charset=utf-8'});
    });

void main() {
  group('설정 — MAIN_SETTING_01', () {
    Future<void> pump(WidgetTester tester, String persona) async {
      tester.view.physicalSize = const Size(411, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.reset);

      await tester.pumpWidget(MaterialApp(
        theme: AppTheme.light,
        home: SettingsScreen(
            settingsService:
                SettingsService(apiClient: _api(_client(persona)))),
      ));
      await tester.pump(const Duration(milliseconds: 300));
    }

    testWidgets('페르소나 항목을 두지 않는다', (tester) async {
      // ⚠ 되살리면 설정 지점이 둘로 갈립니다. 챗봇 탭이 확인 화면입니다.
      await pump(tester, 'FRIEND');

      expect(find.byType(RadioListTile<String>), findsNothing);
      expect(find.byType(RadioGroup<String>), findsNothing);
      expect(find.text('따스한 공감형'), findsNothing);
      expect(find.text('현실적인 조언형'), findsNothing);
      // ⚠ 절 제목도 함께 봅니다. 카드만 지우고 제목을 남기면 **아무것도 없는
      //   「대화 성격」 절**이 화면에 뜹니다. 실제로 그렇게 남아 있었습니다.
      expect(find.text('대화 성격'), findsNothing);
    });

    testWidgets('설정 화면은 성격을 저장하려 들지 않는다', (tester) async {
      final methods = <String>[];
      tester.view.physicalSize = const Size(411, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.reset);

      await tester.pumpWidget(MaterialApp(
        theme: AppTheme.light,
        home: SettingsScreen(
            settingsService: SettingsService(
                apiClient: _api(
                    _client('FRIEND', spy: (r) => methods.add(r.method))))),
      ));
      await tester.pump(const Duration(milliseconds: 300));

      expect(methods.contains('PATCH'), isFalse,
          reason: '성격 저장은 대화를 시작하는 쪽(MAIN_CHAT_01)이 합니다');
    });
  });

  group('챗봇 성격 선택 — MAIN_CHAT_01', () {
    Future<void> pump(WidgetTester tester, String saved,
        {void Function(http.BaseRequest)? spy}) async {
      tester.view.physicalSize = const Size(411, 731);
      tester.view.devicePixelRatio = 1;
      tester.view.padding = const FakeViewPadding(top: 24, bottom: 24);
      addTearDown(tester.view.reset);

      final api = _api(_client(saved, spy: spy));
      await tester.pumpWidget(MaterialApp(
        theme: AppTheme.light,
        home: Scaffold(
            body: ChatScreen(
                chatService: ChatService(apiClient: api),
                // ⚠ 이걸 빼면 진짜 네트워크로 나가 조용히 실패합니다.
                settingsService: SettingsService(apiClient: api))),
      ));
      await tester.pump(const Duration(milliseconds: 400));
    }

    testWidgets('앱을 다시 켜도 최근에 고른 성격이 먼저 보인다', (tester) async {
      // ⚠ 텍스트 존재로 판정하면 안 됩니다. PageView 는 옆 페이지도 만들어 두므로
      //   기본 선택이 틀려도 「현실적인 조언형」가 트리에 있습니다.
      //   **실제로 어느 페이지에 있는지**를 봅니다.
      await pump(tester, 'COUNSELOR');
      final view = tester.widget<PageView>(find.byType(PageView));
      expect(view.controller?.page?.round(),
          ChatPersona.values.indexOf(ChatPersona.thinking),
          reason: '저장된 성격이 첫 화면으로 와야 합니다');
    });

    testWidgets('최근에 고른 성격에 「최근 대화」 표시가 붙는다', (tester) async {
      // ⚠ 기본으로 떠 있는 것만으로는 **그게 내가 고른 값인지 그냥 첫 카드인지
      //   알 수 없습니다.** 설정에서 페르소나 항목을 뺀 것도 이 표시가 그 역할을
      //   대신하기 때문입니다.
      await pump(tester, 'COUNSELOR');
      expect(find.text('최근 대화'), findsOneWidget);
    });

    testWidgets('표시는 한 카드에만 붙는다', (tester) async {
      // 두 장 다 붙으면 어느 쪽이 최근인지 알 수 없습니다.
      await pump(tester, 'FRIEND');
      expect(find.text('최근 대화'), findsOneWidget);
    });
  });
}
