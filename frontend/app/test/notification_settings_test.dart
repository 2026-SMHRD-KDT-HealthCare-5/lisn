/// 알림 수신 동의 — `MAIN_SETTING_01` ❷ · 구현 갭 2
///
/// 화면에 토글을 그려놓고 「알림 기능은 준비 중이에요」를 띄우고 있었습니다.
/// `MLCM_400` 5단계가 "사용자가 알림 수신 동의 상태인 경우" 를 전제하는데
/// 그 상태를 저장할 곳이 없었습니다.
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:maeume_care/screens/settings_screen.dart';
import 'package:maeume_care/services/api_client.dart';
import 'package:maeume_care/services/settings_service.dart';
import 'package:maeume_care/services/token_storage.dart';

/// 알림 PATCH 만 갈라 받고 나머지는 최소 응답을 돌려주는 가짜 서버.
class _Server {
  final patches = <Map<String, dynamic>>[];
  bool care = true;
  bool content = true;

  SettingsService get service {
    final store = MemoryTokenStore();
    store.save(
      accessToken: 'test-token',
      expiresAt: DateTime.now().add(const Duration(hours: 1)),
    );
    final client = MockClient((request) async {
      const h = {'content-type': 'application/json; charset=utf-8'};
      final path = request.url.path;

      if (path.endsWith('/users/me/notifications')) {
        if (request.method == 'PATCH') {
          final body = jsonDecode(request.body) as Map<String, dynamic>;
          patches.add(body);
          if (body.containsKey('care_alert_agreed')) {
            care = body['care_alert_agreed'] as bool;
          }
          if (body.containsKey('content_alert_agreed')) {
            content = body['content_alert_agreed'] as bool;
          }
        }
        return http.Response(
          jsonEncode({
            'care_alert_agreed': care,
            'content_alert_agreed': content,
            'fcm_token_registered': false,
          }),
          200,
          headers: h,
        );
      }
      if (path.endsWith('/users/me')) {
        return http.Response(
          jsonEncode({
            'user_id': '00000000-0000-0000-0000-000000000001',
            'email': 'a@b.c',
            'name': '테스터',
            'persona_type': 'FRIEND',
            'role': 'USER',
          }),
          200,
          headers: h,
        );
      }
      return http.Response('[]', 200, headers: h);
    });
    return SettingsService(
      apiClient: ApiClient(tokenStore: store, httpClient: client),
    );
  }
}

Future<void> pump(WidgetTester tester, SettingsService service) async {
  await tester.pumpWidget(
    MaterialApp(home: SettingsScreen(settingsService: service)),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('토글이 둘이고 「준비 중」 문구가 없다', (tester) async {
    final server = _Server();
    await pump(tester, server.service);

    expect(find.text('케어 알림'), findsOneWidget);
    expect(find.text('콘텐츠·리포트 알림'), findsOneWidget);
    expect(find.textContaining('준비 중'), findsNothing);
  });

  testWidgets('콘텐츠 알림을 꺼도 케어 알림은 켜진 채로 남는다', (tester) async {
    // **이게 토글을 둘로 나눈 이유다.** 하나로 묶으면 광고성 알림이 귀찮아
    // 끈 사람이 선제 접촉(MLCM_220)까지 끈다.
    final server = _Server();
    await pump(tester, server.service);

    await tester.tap(find.byType(SwitchListTile).last);
    await tester.pumpAndSettle();

    expect(server.patches, hasLength(1));
    expect(server.patches.single, {'content_alert_agreed': false},
        reason: '보낸 것만 바뀌어야 한다 — 둘을 함께 보내면 옛 값이 덮어쓴다');

    final care =
        tester.widget<SwitchListTile>(find.byType(SwitchListTile).first);
    expect(care.value, isTrue);
  });

  testWidgets('서버 값을 그대로 그린다', (tester) async {
    final server = _Server()
      ..care = false
      ..content = true;
    await pump(tester, server.service);

    final tiles =
        tester.widgetList<SwitchListTile>(find.byType(SwitchListTile)).toList();
    expect(tiles.first.value, isFalse);
    expect(tiles.last.value, isTrue);
  });
}
