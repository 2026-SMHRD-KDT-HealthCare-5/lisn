/// FCM 토큰 등록 — `MLCM_220` 4단계 · `NFR-DV-002` · 구현 갭 1
///
/// 서버에는 토큰을 받을 창구(`PATCH /users/me/notifications`)가 8/03 부터
/// 있었는데 **앱이 토큰을 만들지 않아 넣을 것이 없었습니다.**
///
/// 여기서 확인하는 것은 「Firebase 가 동작하는가」가 아니라 **등록 로직이
/// 옳은가** 입니다. 플랫폼에 닿는 곳은 `FirebasePushTokenSource` 하나로
/// 몰아두었고, 이 테스트는 [PushTokenSource] 를 가짜로 끼웁니다 —
/// `health_reader.dart` 와 같은 구조라 **실기기 없이 돕니다.**
library;

import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:maeume_care/services/api_client.dart';
import 'package:maeume_care/services/push_messaging.dart';
import 'package:maeume_care/services/settings_service.dart';
import 'package:maeume_care/services/token_storage.dart';

/// 보낸 PATCH 본문만 모아두는 가짜 서버.
class _Server {
  final patches = <Map<String, dynamic>>[];
  int failTimes = 0;

  SettingsService get service {
    final store = MemoryTokenStore();
    store.save(
      accessToken: 'test-token',
      expiresAt: DateTime.now().add(const Duration(hours: 1)),
    );
    final client = MockClient((request) async {
      const h = {'content-type': 'application/json; charset=utf-8'};
      if (failTimes > 0) {
        failTimes--;
        return http.Response('{"detail":"boom"}', 500, headers: h);
      }
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      patches.add(body);
      return http.Response(
        jsonEncode({
          'care_alert_agreed': true,
          'content_alert_agreed': true,
          'fcm_token_registered': (body['fcm_token'] as String?)?.isNotEmpty,
        }),
        200,
        headers: h,
      );
    });
    return SettingsService(
      apiClient: ApiClient(tokenStore: store, httpClient: client),
    );
  }
}

/// 권한·토큰을 마음대로 조작할 수 있는 가짜 소스.
class _FakeSource implements PushTokenSource {
  _FakeSource({this.granted = true, this.value = 'token-a'});

  bool granted;
  String? value;
  int permissionCalls = 0;
  final _refresh = StreamController<String>.broadcast();

  @override
  Future<bool> requestPermission() async {
    permissionCalls++;
    return granted;
  }

  @override
  Future<String?> token() async => value;

  @override
  Stream<String> onTokenRefresh() => _refresh.stream;

  void emitRefresh(String t) => _refresh.add(t);
  Future<void> close() => _refresh.close();
}

void main() {
  test('권한을 허용하면 토큰이 서버에 등록된다', () async {
    final server = _Server();
    final source = _FakeSource(value: 'token-a');
    final registrar = PushRegistrar(source: source, settings: server.service);

    expect(await registrar.register(), isTrue);
    expect(server.patches, [
      {'fcm_token': 'token-a'}
    ]);
    await source.close();
  });

  test('권한을 거부하면 토큰을 보내지 않는다', () async {
    // 거부는 정상 흐름입니다. 선제 접촉 세션은 서버에 선생성돼 있어
    // 앱을 열면 보입니다(MLCM_220 6단계).
    final server = _Server();
    final source = _FakeSource(granted: false);
    final registrar = PushRegistrar(source: source, settings: server.service);

    expect(await registrar.register(), isFalse);
    expect(server.patches, isEmpty);
    await source.close();
  });

  test('토큰을 못 받으면 등록하지 않는다', () async {
    final server = _Server();
    final source = _FakeSource(value: null);
    final registrar = PushRegistrar(source: source, settings: server.service);

    expect(await registrar.register(), isFalse);
    expect(server.patches, isEmpty);
    await source.close();
  });

  test('갱신된 토큰이 서버에 다시 올라간다', () async {
    // ⚠ 이게 빠지면 **그 사용자에게만 조용히 푸시가 안 갑니다.** 재설치나
    //   장기 미사용이면 구글이 토큰을 새로 발급하는데, 실패가 눈에 보이지
    //   않는 종류라 제일 늦게 발견됩니다.
    final server = _Server();
    final source = _FakeSource(value: 'token-a');
    final registrar = PushRegistrar(source: source, settings: server.service);

    await registrar.register();
    source.emitRefresh('token-b');
    await Future<void>.delayed(Duration.zero);

    expect(server.patches, [
      {'fcm_token': 'token-a'},
      {'fcm_token': 'token-b'},
    ]);
    await source.close();
  });

  test('같은 토큰은 다시 보내지 않는다', () async {
    final server = _Server();
    final source = _FakeSource(value: 'token-a');
    final registrar = PushRegistrar(source: source, settings: server.service);

    await registrar.register();
    await registrar.register();
    source.emitRefresh('token-a');
    await Future<void>.delayed(Duration.zero);

    expect(server.patches, hasLength(1));
    await source.close();
  });

  test('로그아웃하면 빈 문자열로 토큰을 지운다', () async {
    // ⚠ null 은 서버에서 「안 바꿈」입니다(users.py). 빈 문자열이어야
    //   실제로 지워집니다. 안 지우면 다음 사용자에게 갈 알림이 앞사람
    //   폰으로 갑니다.
    final server = _Server();
    final source = _FakeSource(value: 'token-a');
    final registrar = PushRegistrar(source: source, settings: server.service);

    await registrar.register();
    await registrar.unregister();

    expect(server.patches.last, {'fcm_token': ''});
    expect(registrar.lastSent, isNull);
    await source.close();
  });

  test('로그아웃 뒤에는 갱신 토큰을 올리지 않는다', () async {
    // 구독을 안 끊으면 로그아웃했는데 앞사람 계정으로 토큰이 붙습니다.
    final server = _Server();
    final source = _FakeSource(value: 'token-a');
    final registrar = PushRegistrar(source: source, settings: server.service);

    await registrar.register();
    await registrar.unregister();
    final before = server.patches.length;
    source.emitRefresh('token-c');
    await Future<void>.delayed(Duration.zero);

    expect(server.patches, hasLength(before));
    await source.close();
  });

  test('서버가 실패해도 던지지 않는다', () async {
    // 푸시가 없다고 앱이 멈추면 안 됩니다.
    final server = _Server()..failTimes = 1;
    final source = _FakeSource(value: 'token-a');
    final registrar = PushRegistrar(source: source, settings: server.service);

    expect(await registrar.register(), isFalse);
    await source.close();
  });
}
