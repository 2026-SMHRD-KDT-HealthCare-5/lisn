/// 앱 사용 로그 — 기업 브리프(PROJECT_02)의 「앱 사용 로그 + 웨어러블」.
///
/// 여기서 지키는 것은 **성질**입니다.
///   ① 권한이 없으면 웨어러블만으로 계속 동작한다
///   ② 못 읽은 것을 0 으로 만들지 않는다
///   ③ 하루 경계로 갈라 읽는다
library;

import 'package:flutter_test/flutter_test.dart';
import 'package:maeume_care/services/app_usage_reader.dart';
import 'package:maeume_care/services/lifelog_aggregate.dart';

/// 하루씩 다른 값을 돌려주는 가짜. 어떤 구간으로 불렸는지도 기록합니다.
class FakeUsageReader implements AppUsageReader {
  FakeUsageReader({this.granted = true, this.byDay = const {}});

  final bool granted;

  /// 날짜(로컬 자정) → 그날 집계.
  final Map<DateTime, AppUsage> byDay;

  final calls = <(DateTime, DateTime)>[];

  @override
  Future<bool> hasPermission() async => granted;

  @override
  Future<void> openSettings() async {}

  @override
  Future<AppUsage?> read({required DateTime from, required DateTime to}) async {
    calls.add((from, to));
    if (!granted) return null;
    return byDay[DateTime(from.year, from.month, from.day)];
  }
}

void main() {
  final day1 = DateTime(2026, 8, 20);
  final day2 = DateTime(2026, 8, 21);

  DailyLifelog row(DateTime d) => DailyLifelog(collectedAt: d, steps: 5000);

  group('AppUsage', () {
    test('세 값이 그대로 실린다', () {
      final r = row(day1).withUsage(
        const AppUsage(screenTimeMin: 320, nightScreenMin: 75, appSessionCount: 88),
      );
      expect(r.screenTimeMin, 320);
      expect(r.nightScreenMin, 75);
      expect(r.appSessionCount, 88);
      //  기존 필드는 건드리지 않는다
      expect(r.steps, 5000);
      expect(r.collectedAt, day1);
    });

    test('null 을 얹으면 원본 그대로 — 0 으로 만들지 않는다', () {
      final r = row(day1).withUsage(null);
      expect(r.screenTimeMin, isNull,
          reason: '「권한이 없어 모른다」를 0 으로 적재하면 기준선이 무너진다');
      expect(r.nightScreenMin, isNull);
      expect(r.appSessionCount, isNull);
    });

    test('toJson 은 값이 있을 때만 키를 넣는다', () {
      expect(row(day1).toJson().containsKey('screen_time_min'), isFalse);
      final j = row(day1)
          .withUsage(const AppUsage(
              screenTimeMin: 10, nightScreenMin: 0, appSessionCount: 3))
          .toJson();
      expect(j['screen_time_min'], 10);
      expect(j['night_screen_min'], 0);
      expect(j['app_session_count'], 3);
    });

    test('fromJson 으로 왕복해도 값이 남는다 (재시도 큐)', () {
      final src = row(day1).withUsage(
        const AppUsage(screenTimeMin: 200, nightScreenMin: 44, appSessionCount: 51),
      );
      final back = DailyLifelog.fromJson(src.toJson());
      expect(back.screenTimeMin, 200);
      expect(back.nightScreenMin, 44);
      expect(back.appSessionCount, 51);
    });

    test('앱 사용이 있으면 isEmpty 가 아니다', () {
      final r = DailyLifelog(collectedAt: day1).withUsage(
        const AppUsage(screenTimeMin: 120, nightScreenMin: 5, appSessionCount: 9),
      );
      expect(r.isEmpty, isFalse,
          reason: '웨어러블이 비어도 앱 사용만으로 보낼 값이 있다');
    });
  });

  group('NullAppUsageReader — 기본값', () {
    test('권한 없음 · 항상 null', () async {
      const r = NullAppUsageReader();
      expect(await r.hasPermission(), isFalse);
      expect(await r.read(from: day1, to: day2), isNull);
    });
  });

  group('FakeUsageReader 로 본 하루 경계', () {
    test('하루마다 따로 읽는다', () async {
      final reader = FakeUsageReader(byDay: {
        day1: const AppUsage(
            screenTimeMin: 300, nightScreenMin: 60, appSessionCount: 70),
        day2: const AppUsage(
            screenTimeMin: 150, nightScreenMin: 10, appSessionCount: 30),
      });
      final a = await reader.read(from: day1, to: day2);
      final b = await reader.read(from: day2, to: day2.add(const Duration(days: 1)));
      expect(a?.screenTimeMin, 300);
      expect(b?.screenTimeMin, 150);
      expect(reader.calls.length, 2);
    });

    test('권한이 없으면 null 이고 호출은 기록된다', () async {
      final reader = FakeUsageReader(granted: false);
      expect(await reader.read(from: day1, to: day2), isNull);
    });
  });
}
