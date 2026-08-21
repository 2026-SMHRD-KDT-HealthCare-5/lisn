/// 체성분 수집 경로 — `MAIN_LIFELOG_01` ❺ · 구현 갭 5
///
/// **화면은 있는데 데이터가 들어갈 길이 없었습니다.** `GET /body-composition`
/// 과 조회 화면은 있었지만 `POST` 를 아무도 부르지 않았고, Health Connect
/// 읽기 목록에도 체성분이 없었습니다. 동의를 받아놓고 수집하지 않는 상태였고,
/// 화면 단위 대조(2026.08.02)에서는 「조회 화면 추가」로 닫혀 있었습니다.
library;

import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:maeume_care/services/api_client.dart';
import 'package:maeume_care/services/lifelog_aggregate.dart';
import 'package:maeume_care/services/lifelog_service.dart';
import 'package:maeume_care/services/lifelog_sync.dart';
import 'package:maeume_care/services/sync_store.dart';
import 'package:maeume_care/services/token_storage.dart';

import 'lifelog_sync_test.dart' show FakeHealthReader;

HealthSample sample(HealthField f, double v, DateTime at) =>
    HealthSample(field: f, value: v, from: at, to: at);

/// 경로별로 갈라 받는 가짜 서버. 체성분과 라이프로그가 다른 엔드포인트다.
class _Server {
  final bodyPosts = <Map<String, dynamic>>[];
  int failBodyTimes = 0;

  LifelogService get service {
    final store = MemoryTokenStore();
    store.save(
      accessToken: 'test-token',
      expiresAt: DateTime.now().add(const Duration(hours: 1)),
    );
    final client = MockClient((request) async {
      const json = {'content-type': 'application/json; charset=utf-8'};
      if (request.url.path.endsWith('/body-composition')) {
        bodyPosts.add(jsonDecode(request.body) as Map<String, dynamic>);
        if (bodyPosts.length <= failBodyTimes) {
          return http.Response('{"detail":"서버 오류"}', 500, headers: json);
        }
        return http.Response('{}', 201, headers: json);
      }
      return http.Response(
        jsonEncode({
          'accepted': 1,
          'last_synced_at': DateTime.utc(2026, 8, 3, 12).toIso8601String(),
        }),
        200,
        headers: json,
      );
    });
    return LifelogService(
      apiClient: ApiClient(tokenStore: store, httpClient: client),
    );
  }
}

void main() {
  group('집계 — 측정 건 단위', () {
    test('한 번 측정이 여러 레코드로 와도 한 건으로 묶는다', () {
      // 체성분계 한 번 측정이 체중/체지방률/체수분 레코드로 쪼개져 들어온다.
      // 초 단위가 어긋나도 같은 측정이다.
      final t = DateTime(2026, 8, 3, 7, 30, 12);
      final rows = aggregateBodyComposition([
        sample(HealthField.weight, 68.4, t),
        sample(HealthField.bodyFatPercentage, 22.5,
            t.add(const Duration(seconds: 3))),
        sample(
            HealthField.bodyWaterMass, 38.2, t.add(const Duration(seconds: 5))),
      ]);

      expect(rows, hasLength(1));
      expect(rows.single.weightKg, 68.4);
      expect(rows.single.bodyWaterKg, 38.2);
    });

    test('체지방은 %를 kg 으로 환산한다', () {
      // 스키마는 body_fat_kg 인데 Health Connect 는 퍼센트를 준다.
      final t = DateTime(2026, 8, 3, 7, 30);
      final rows = aggregateBodyComposition([
        sample(HealthField.weight, 68.0, t),
        sample(HealthField.bodyFatPercentage, 25.0, t),
      ]);
      expect(rows.single.bodyFatKg, 17.0);
    });

    test('체중이 없으면 체지방을 비운다 — 퍼센트를 kg 칸에 넣지 않는다', () {
      // 「체지방 22kg」과 「22%」가 뒤바뀌면 화면에 틀린 숫자가 뜬다.
      final rows = aggregateBodyComposition([
        sample(HealthField.bodyFatPercentage, 22.0, DateTime(2026, 8, 3, 7)),
      ]);
      expect(rows, isEmpty, reason: '환산도 못 하고 다른 값도 없으면 보낼 게 없다');
    });

    test('라이프로그 표본은 무시한다', () {
      final rows = aggregateBodyComposition([
        sample(HealthField.steps, 5000, DateTime(2026, 8, 3, 9)),
      ]);
      expect(rows, isEmpty);
    });
  });

  group('전송 — 중복을 만들지 않는다', () {
    LifelogSyncService build(
            FakeHealthReader reader, SyncStore store, LifelogService service) =>
        LifelogSyncService(
          reader: reader,
          store: store,
          lifelogService: service,
          retryDelay: Duration.zero,
        );

    test('같은 측정을 두 번 보내지 않는다', () async {
      // POST /body-composition 은 UPSERT 가 아니라 INSERT 다. 다시 보내면
      // 이력에 같은 몸무게가 두 번 뜬다.
      final t = DateTime(2026, 8, 3, 7, 30);
      final reader = FakeHealthReader(samples: [
        sample(HealthField.weight, 68.4, t),
        sample(HealthField.steps, 5000, t),
      ]);
      final server = _Server();
      final store = MemorySyncStore();
      final sync = build(reader, store, server.service);

      await sync.sync(now: DateTime(2026, 8, 3, 9));
      await sync.sync(now: DateTime(2026, 8, 3, 9, 15));

      expect(server.bodyPosts, hasLength(1));
    });

    test('새 측정만 보낸다', () async {
      final reader = FakeHealthReader(samples: [
        sample(HealthField.weight, 68.4, DateTime(2026, 8, 3, 7, 30)),
        sample(HealthField.steps, 5000, DateTime(2026, 8, 3, 7, 30)),
      ]);
      final server = _Server();
      final store = MemorySyncStore();
      final sync = build(reader, store, server.service);

      await sync.sync(now: DateTime(2026, 8, 3, 9));
      reader.samples = [
        sample(HealthField.weight, 68.4, DateTime(2026, 8, 3, 7, 30)),
        sample(HealthField.weight, 67.9, DateTime(2026, 8, 4, 7, 30)),
        sample(HealthField.steps, 6000, DateTime(2026, 8, 4, 9)),
      ];
      await sync.sync(now: DateTime(2026, 8, 4, 9, 30));

      expect(server.bodyPosts, hasLength(2));
      expect(server.bodyPosts.last['weight_kg'], 67.9);
    });

    test('체성분 전송이 실패해도 라이프로그는 올라간다', () async {
      // 체성분은 선택 동의라 없는 사용자가 많다. 여기서 막히면 활동량·수면까지
      // 못 올라간다.
      final t = DateTime(2026, 8, 3, 7, 30);
      final reader = FakeHealthReader(samples: [
        sample(HealthField.weight, 68.4, t),
        sample(HealthField.steps, 5000, t),
      ]);
      final server = _Server()..failBodyTimes = 99;
      final store = MemorySyncStore();

      final result = await build(reader, store, server.service)
          .sync(now: DateTime(2026, 8, 3, 9));

      expect(result.outcome, SyncOutcome.sent);
      expect(await store.lastBodyAt(), isNull, reason: '실패했으므로 워터마크를 옮기면 안 된다');
    });
  });
}
