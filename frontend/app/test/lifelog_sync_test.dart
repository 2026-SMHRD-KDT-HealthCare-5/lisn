/// 라이프로그 동기화 흐름 — MLCM_200 · NFR-DV-002
///
/// **실기기 없이 전체 흐름을 검증합니다.** [HealthReader]·[SyncStore]·
/// [LifelogService] 를 전부 주입받게 만든 이유가 이것입니다.
library;

import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:maeume_care/services/api_client.dart';
import 'package:maeume_care/services/health_reader.dart';
import 'package:maeume_care/services/lifelog_aggregate.dart';
import 'package:maeume_care/services/lifelog_service.dart';
import 'package:maeume_care/services/lifelog_sync.dart';
import 'package:maeume_care/services/sync_store.dart';
import 'package:maeume_care/services/token_storage.dart';

class FakeHealthReader implements HealthReader {
  FakeHealthReader({
    this.permission = HealthPermission.granted,
    this.samples = const [],
    this.throwOnRead = false,
  });

  HealthPermission permission;
  List<HealthSample> samples;
  bool throwOnRead;

  int readCount = 0;
  DateTime? lastFrom;
  DateTime? lastTo;

  @override
  Future<HealthPermission> permissionStatus() async => permission;

  @override
  Future<HealthPermission> requestPermission() async => permission;

  @override
  Future<void> openInstall() async {}

  @override
  Future<List<HealthSample>> read({
    required DateTime from,
    required DateTime to,
  }) async {
    readCount++;
    lastFrom = from;
    lastTo = to;
    if (throwOnRead) throw Exception('Health Connect 오류');
    return samples;
  }
}

/// 서버 응답을 흉내내는 LifelogService. 요청 본문도 기록합니다.
class _Server {
  _Server({this.failTimes = 0, DateTime? syncedAt})
      : syncedAt = syncedAt ?? DateTime.utc(2026, 8, 2, 12);

  int failTimes;
  DateTime syncedAt;

  final bodies = <Map<String, dynamic>>[];
  int calls = 0;

  LifelogService get service {
    final store = MemoryTokenStore();
    store.save(
      accessToken: 'test-token',
      expiresAt: DateTime.now().add(const Duration(hours: 1)),
    );
    final client = MockClient((request) async {
      calls++;
      bodies.add(jsonDecode(request.body) as Map<String, dynamic>);
      if (calls <= failTimes) {
        return http.Response('{"detail":"서버 오류"}', 500,
            headers: {'content-type': 'application/json; charset=utf-8'});
      }
      final items = (bodies.last['items'] as List).length;
      return http.Response(
        jsonEncode({
          'accepted': items,
          'last_synced_at': syncedAt.toIso8601String(),
        }),
        200,
        headers: {'content-type': 'application/json; charset=utf-8'},
      );
    });
    return LifelogService(
      apiClient: ApiClient(tokenStore: store, httpClient: client),
    );
  }
}

HealthSample steps(int value, DateTime at) => HealthSample(
    field: HealthField.steps, value: value.toDouble(), from: at, to: at);

LifelogSyncService build({
  required FakeHealthReader reader,
  required SyncStore store,
  required LifelogService service,
}) =>
    LifelogSyncService(
      reader: reader,
      store: store,
      lifelogService: service,
      // 테스트에서 30초를 실제로 기다릴 이유는 없습니다. 규정된 기본값이
      // 30초인지는 아래 '기본값' 테스트가 따로 봅니다.
      retryDelay: Duration.zero,
    );

void main() {
  group('권한 — MLCM_200 2단계', () {
    test('권한이 없으면 읽지 않고 끝낸다', () async {
      final reader = FakeHealthReader(permission: HealthPermission.denied);
      final store = MemorySyncStore();
      final sync = build(
          reader: reader, store: store, service: _Server().service);

      final result = await sync.sync();

      expect(result.outcome, SyncOutcome.permissionDenied);
      expect(reader.readCount, 0, reason: '권한 없이 읽으러 가면 예외가 납니다');
    });

    test('⚠ 권한이 없어도 보관분을 버리지 않는다', () async {
      // 권한을 다시 켜면 그대로 올라가야 합니다. 여기서 비우면 사용자가
      // 권한을 껐다 켠 구간이 영구 유실됩니다.
      final store = MemorySyncStore();
      await store.savePending([
        DailyLifelog(collectedAt: DateTime(2026, 8, 1), steps: 100),
      ]);
      final sync = build(
        reader: FakeHealthReader(permission: HealthPermission.denied),
        store: store,
        service: _Server().service,
      );

      await sync.sync();

      expect(await store.pendingRows(), hasLength(1));
    });

    test('Health Connect 미설치는 권한 거부와 구분된다', () async {
      // 화면이 안내할 내용이 다릅니다(설치 vs 권한 켜기).
      final sync = build(
        reader: FakeHealthReader(permission: HealthPermission.unavailable),
        store: MemorySyncStore(),
        service: _Server().service,
      );
      expect((await sync.sync()).outcome, SyncOutcome.unavailable);
    });
  });

  group('⚠ 읽기 구간 — 오늘 행이 덮어써지면 안 된다', () {
    test('마지막 동기화 **시각**이 아니라 그 **날의 자정**부터 읽는다', () async {
      // 09:00 에 보낸 뒤 09:15 에 09:00 부터만 읽으면, 오늘 걸음이
      // 15분치로 계산돼 UPSERT 로 **덮어써집니다.**
      final store = MemorySyncStore();
      await store.saveLastSyncedAt(DateTime(2026, 8, 2, 9));
      final reader = FakeHealthReader(
          samples: [steps(500, DateTime(2026, 8, 2, 9, 10))]);
      final sync =
          build(reader: reader, store: store, service: _Server().service);

      await sync.sync(now: DateTime(2026, 8, 2, 9, 15));

      expect(reader.lastFrom, DateTime(2026, 8, 2),
          reason: '그날 자정부터 다시 읽어야 하루 합계가 유지됩니다');
    });

    test('첫 동기화는 14일 전부터 읽는다 — MLCM_210 기준값', () async {
      final reader = FakeHealthReader();
      final sync = build(
          reader: reader,
          store: MemorySyncStore(),
          service: _Server().service);

      await sync.sync(now: DateTime(2026, 8, 2, 10));

      expect(reader.lastFrom, DateTime(2026, 7, 19));
    });

    test('오래 밀려도 14일 넘게 거슬러 올라가지 않는다', () async {
      final store = MemorySyncStore();
      await store.saveLastSyncedAt(DateTime(2026, 1, 1));
      final reader = FakeHealthReader();
      final sync =
          build(reader: reader, store: store, service: _Server().service);

      await sync.sync(now: DateTime(2026, 8, 2, 10));

      expect(reader.lastFrom, DateTime(2026, 7, 19),
          reason: '더 읽어봐야 분석에 안 쓰이고 첫 동기화만 느려집니다');
    });
  });

  group('전송 — MLCM_200 4·5단계', () {
    test('집계 행을 items 로 보낸다', () async {
      final server = _Server();
      final sync = build(
        reader: FakeHealthReader(samples: [
          steps(3000, DateTime(2026, 8, 1, 10)),
          steps(5000, DateTime(2026, 8, 2, 10)),
        ]),
        store: MemorySyncStore(),
        service: server.service,
      );

      final result = await sync.sync(now: DateTime(2026, 8, 2, 12));

      expect(result.outcome, SyncOutcome.sent);
      expect(result.rowsSent, 2);
      final items = server.bodies.single['items'] as List;
      expect(items, hasLength(2));
      expect((items[0] as Map)['steps'], 3000);
      expect((items[1] as Map)['steps'], 5000);
    });

    test('⚠ last_synced_at 은 **서버가 준 값**을 쓴다', () async {
      // 앱 시계를 쓰면 단말 시간이 틀어졌을 때 그 구간이 영구 유실됩니다.
      final serverTime = DateTime.utc(2026, 8, 2, 3, 45);
      final store = MemorySyncStore();
      final sync = build(
        reader: FakeHealthReader(samples: [steps(10, DateTime(2026, 8, 2, 9))]),
        store: store,
        service: _Server(syncedAt: serverTime).service,
      );

      await sync.sync(now: DateTime(2030, 1, 1)); // 단말 시계가 크게 틀어진 상황

      expect((await store.lastSyncedAt())!.toUtc(), serverTime);
    });

    test('보낼 게 없으면 last_synced_at 을 갱신하지 않는다', () async {
      // 갱신하면 기기가 잠깐 데이터를 안 준 구간을 영영 다시 안 읽습니다.
      final store = MemorySyncStore();
      final sync = build(
          reader: FakeHealthReader(samples: const []),
          store: store,
          service: _Server().service);

      final result = await sync.sync();

      expect(result.outcome, SyncOutcome.nothingToSend);
      expect(await store.lastSyncedAt(), isNull);
    });

    test('Health Connect 읽기가 실패해도 크래시하지 않는다', () async {
      final sync = build(
        reader: FakeHealthReader(throwOnRead: true),
        store: MemorySyncStore(),
        service: _Server().service,
      );
      expect((await sync.sync()).outcome, SyncOutcome.nothingToSend);
    });
  });

  group('재시도와 보관 — MLCM_200 6단계 · NFR-DV-002', () {
    test('최대 3회까지 시도한다', () async {
      final server = _Server(failTimes: 99);
      final sync = build(
        reader: FakeHealthReader(samples: [steps(10, DateTime(2026, 8, 2, 9))]),
        store: MemorySyncStore(),
        service: server.service,
      );

      final result = await sync.sync();

      expect(server.calls, 3, reason: '규정은 「최대 3회」입니다');
      expect(result.outcome, SyncOutcome.failedAndQueued);
    });

    test('중간에 성공하면 더 시도하지 않는다', () async {
      final server = _Server(failTimes: 2);
      final sync = build(
        reader: FakeHealthReader(samples: [steps(10, DateTime(2026, 8, 2, 9))]),
        store: MemorySyncStore(),
        service: server.service,
      );

      expect((await sync.sync()).outcome, SyncOutcome.sent);
      expect(server.calls, 3);
    });

    test('최종 실패분은 단말에 보관한다', () async {
      final store = MemorySyncStore();
      final sync = build(
        reader: FakeHealthReader(samples: [steps(77, DateTime(2026, 8, 2, 9))]),
        store: store,
        service: _Server(failTimes: 99).service,
      );

      await sync.sync();

      final pending = await store.pendingRows();
      expect(pending, hasLength(1));
      expect(pending.single.steps, 77);
    });

    test('성공하면 보관분을 비운다', () async {
      final store = MemorySyncStore();
      await store.savePending([
        DailyLifelog(collectedAt: DateTime(2026, 8, 1), steps: 100),
      ]);
      final sync = build(
        reader: FakeHealthReader(samples: [steps(10, DateTime(2026, 8, 2, 9))]),
        store: store,
        service: _Server().service,
      );

      await sync.sync();

      expect(await store.pendingRows(), isEmpty);
    });

    test('보관분은 다음 주기에 **함께** 전송된다', () async {
      final store = MemorySyncStore();
      await store.savePending([
        DailyLifelog(collectedAt: DateTime(2026, 7, 30), steps: 111),
      ]);
      final server = _Server();
      final sync = build(
        reader: FakeHealthReader(samples: [steps(222, DateTime(2026, 8, 2, 9))]),
        store: store,
        service: server.service,
      );

      final result = await sync.sync();

      expect(result.rowsSent, 2);
      final items = server.bodies.single['items'] as List;
      expect((items[0] as Map)['steps'], 111, reason: '오래된 날이 먼저');
      expect((items[1] as Map)['steps'], 222);
    });

    test('⚠ 같은 날짜는 **새로 읽은 값**이 이긴다', () async {
      // 보관분은 그때의 스냅숏일 뿐입니다. 오래된 값으로 덮어쓰면 그날
      // 데이터가 뒤로 갑니다(걸음 8000 → 3000).
      final store = MemorySyncStore();
      await store.savePending([
        DailyLifelog(collectedAt: DateTime(2026, 8, 2), steps: 3000),
      ]);
      final server = _Server();
      final sync = build(
        reader: FakeHealthReader(samples: [steps(8000, DateTime(2026, 8, 2, 9))]),
        store: store,
        service: server.service,
      );

      final result = await sync.sync();

      expect(result.rowsSent, 1, reason: '같은 날이므로 한 행');
      final items = server.bodies.single['items'] as List;
      expect((items.single as Map)['steps'], 8000);
    });

    test('권한이 없으면 보관분만으로 전송하지 않는다', () async {
      // 큐가 있어도 권한 확인이 먼저입니다.
      final store = MemorySyncStore();
      await store.savePending([
        DailyLifelog(collectedAt: DateTime(2026, 8, 1), steps: 100),
      ]);
      final server = _Server();
      final sync = build(
        reader: FakeHealthReader(permission: HealthPermission.denied),
        store: store,
        service: server.service,
      );

      await sync.sync();

      expect(server.calls, 0);
    });
  });

  group('규정된 기본값', () {
    test('재시도 간격 30초 · 최대 3회 — NFR-DV-002', () {
      // ⚠ 이 값을 바꾸면 요구사항 문서와 어긋납니다.
      final sync = LifelogSyncService(
        reader: FakeHealthReader(),
        store: MemorySyncStore(),
        lifelogService: _Server().service,
      );
      expect(sync.retryDelay, const Duration(seconds: 30));
      expect(sync.maxAttempts, 3);
    });
  });
}
