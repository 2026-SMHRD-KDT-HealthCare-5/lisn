/// Health Connect 표본 → 라이프로그 행 집계 — MLCM_200 3단계
///
/// **실기기 없이 검증할 수 있는 부분입니다.** 집계 로직에 플랫폼 의존이
/// 없도록 [HealthSample] 로 한 번 접어둔 이유가 이것입니다.
library;

import 'package:flutter_test/flutter_test.dart';
import 'package:maeume_care/services/lifelog_aggregate.dart';

HealthSample sample(
  HealthField field,
  num value,
  DateTime from, [
  DateTime? to,
]) =>
    HealthSample(field: field, value: value.toDouble(), from: from, to: to ?? from);

void main() {
  group('하루 한 행으로 접는다', () {
    test('15분 표본 여러 개가 한 행이 된다', () {
      // ⚠ 이게 이 파일의 핵심입니다. 15분마다 행을 만들면 ai/server 의
      //   rows[-1] 이 「마지막 15분」이 되어 「오늘」이 아니게 됩니다.
      final day = DateTime(2026, 8, 2);
      final rows = aggregateDaily([
        sample(HealthField.steps, 500, day.add(const Duration(hours: 9))),
        sample(HealthField.steps, 700, day.add(const Duration(hours: 9, minutes: 15))),
        sample(HealthField.steps, 300, day.add(const Duration(hours: 18))),
      ]);

      expect(rows, hasLength(1));
      expect(rows.single.collectedAt, day);
      expect(rows.single.steps, 1500, reason: '걸음은 하루치 합계여야 합니다');
    });

    test('여러 날은 날짜 오름차순으로 나온다', () {
      final rows = aggregateDaily([
        sample(HealthField.steps, 100, DateTime(2026, 8, 3, 10)),
        sample(HealthField.steps, 200, DateTime(2026, 8, 1, 10)),
        sample(HealthField.steps, 300, DateTime(2026, 8, 2, 10)),
      ]);

      expect(rows.map((r) => r.collectedAt.day), [1, 2, 3]);
    });

    test('collected_at 은 **로컬 자정**이다', () {
      // UTC 자정으로 자르면 한국 시간 오전 9시에 날짜가 바뀝니다.
      final rows = aggregateDaily([
        sample(HealthField.steps, 100, DateTime(2026, 8, 2, 3, 30)),
      ]);
      final at = rows.single.collectedAt;
      expect([at.hour, at.minute, at.second], [0, 0, 0]);
      expect(at.isUtc, isFalse);
    });
  });

  group('⚠ 「측정 안 됨」과 「0」은 다르다', () {
    test('표본이 없는 지표는 0 이 아니라 null 이다', () {
      // steps 는 스키마 기본값이 0 입니다. 0 을 보내면 수집이 안 된 것과
      // 하루 종일 안 움직인 것이 구분되지 않고, ai/server 는 그 0 을
      // 기준값에서 빼버립니다.
      final rows = aggregateDaily([
        sample(HealthField.heartRate, 72, DateTime(2026, 8, 2, 10)),
      ]);

      final row = rows.single;
      expect(row.heartRate, 72);
      expect(row.steps, isNull, reason: '0 이면 「0걸음」과 구분되지 않습니다');
      expect(row.distance, isNull);
      expect(row.calories, isNull);
      expect(row.totalSleepMin, isNull);
    });

    test('실제로 0 인 값은 0 으로 남는다', () {
      final rows = aggregateDaily([
        sample(HealthField.steps, 0, DateTime(2026, 8, 2, 10)),
      ]);
      expect(rows.single.steps, 0, reason: '표본이 있으면 0 도 사실입니다');
    });

    test('null 인 필드는 JSON 키 자체를 넣지 않는다', () {
      final json = aggregateDaily([
        sample(HealthField.steps, 10, DateTime(2026, 8, 2, 10)),
      ]).single.toJson();

      expect(json.containsKey('steps'), isTrue);
      expect(json.containsKey('heart_rate'), isFalse);
      expect(json.containsKey('total_sleep_min'), isFalse);
      expect(json['collected_at'], isA<String>());
    });

    test('지표가 하나도 없는 날은 행을 만들지 않는다', () {
      // 빈 행을 적재하면 ai/server 가 「행은 있는데 지표가 없다」로 422 를
      // 내는 상태를 우리가 만들게 됩니다.
      final rows = aggregateDaily([
        // 수면 세션이 아니라 단계만 있고 길이가 0 인 표본
        sample(HealthField.sleepAwake, 0, DateTime(2026, 8, 2, 3),
            DateTime(2026, 8, 2, 3)),
      ]);
      expect(rows, isEmpty);
    });
  });

  group('수면은 **깨어난 날**에 귀속된다', () {
    test('자정을 넘긴 수면은 다음 날 행에 들어간다', () {
      // 8/1 23:00 ~ 8/2 07:00 잠 → 8월 2일 수면
      final start = DateTime(2026, 8, 1, 23);
      final end = DateTime(2026, 8, 2, 7);
      final rows = aggregateDaily([
        sample(HealthField.sleepSession, 0, start, end),
      ]);

      expect(rows, hasLength(1));
      expect(rows.single.collectedAt, DateTime(2026, 8, 2),
          reason: '「8월 2일 수면」은 2일 아침에 깬 잠을 뜻합니다');
      expect(rows.single.sleepStartAt, start);
      expect(rows.single.sleepEndAt, end);
      expect(rows.single.totalSleepMin, 480);
    });

    test('걸음은 시작 시각의 날에 남는다 — 수면과 기준이 다르다', () {
      final rows = aggregateDaily([
        sample(HealthField.steps, 100, DateTime(2026, 8, 1, 23, 50)),
        sample(HealthField.sleepSession, 0, DateTime(2026, 8, 1, 23),
            DateTime(2026, 8, 2, 7)),
      ]);

      expect(rows, hasLength(2));
      expect(rows[0].collectedAt, DateTime(2026, 8, 1));
      expect(rows[0].steps, 100);
      expect(rows[1].collectedAt, DateTime(2026, 8, 2));
      expect(rows[1].totalSleepMin, 480);
    });
  });

  group('수면 계산', () {
    final start = DateTime(2026, 8, 1, 23);
    final end = DateTime(2026, 8, 2, 7); // 480분

    test('단계가 있으면 단계 합이 실제 수면 시간이다', () {
      final rows = aggregateDaily([
        sample(HealthField.sleepSession, 0, start, end),
        sample(HealthField.sleepDeep, 0, DateTime(2026, 8, 1, 23, 30),
            DateTime(2026, 8, 2, 1, 0)), // 90
        sample(HealthField.sleepLight, 0, DateTime(2026, 8, 2, 1),
            DateTime(2026, 8, 2, 5)), // 240
        sample(HealthField.sleepRem, 0, DateTime(2026, 8, 2, 5),
            DateTime(2026, 8, 2, 6, 30)), // 90
        sample(HealthField.sleepAwake, 0, DateTime(2026, 8, 2, 6, 30),
            DateTime(2026, 8, 2, 7)), // 30
      ]);

      final row = rows.single;
      expect(row.deepSleepMin, 90);
      expect(row.lightSleepMin, 240);
      expect(row.remSleepMin, 90);
      expect(row.awakeMin, 30);
      expect(row.totalSleepMin, 420, reason: '90+240+90');
      expect(row.sleepEfficiencyPct, closeTo(87.5, 0.01), reason: '420/480');
      expect(row.sleepOnsetMin, 30, reason: '23:00 에 누워 23:30 에 잠듦');
    });

    test('단계가 없으면 세션 길이에서 깬 시간을 뺀다', () {
      final rows = aggregateDaily([
        sample(HealthField.sleepSession, 0, start, end),
        sample(HealthField.sleepAwake, 0, DateTime(2026, 8, 2, 3),
            DateTime(2026, 8, 2, 3, 40)),
      ]);
      expect(rows.single.totalSleepMin, 440);
    });

    test('⚠ 단계 정보가 없으면 sleep_onset 을 추정하지 않는다', () {
      // 0 으로 채우면 「눕자마자 잠들었다」는 없는 사실이 기록됩니다.
      final rows = aggregateDaily([
        sample(HealthField.sleepSession, 0, start, end),
      ]);
      expect(rows.single.sleepOnsetMin, isNull);
      expect(rows.single.totalSleepMin, 480);
    });

    test('수면 효율은 100 을 넘지 않는다', () {
      // NUMERIC(5,2) CHECK (BETWEEN 0 AND 100) — 넘으면 서버가 거절합니다.
      final rows = aggregateDaily([
        sample(HealthField.sleepSession, 0, start, DateTime(2026, 8, 2, 0)),
        // 세션(60분)보다 긴 단계. 기기가 이런 값을 주는 경우가 있습니다.
        sample(HealthField.sleepDeep, 0, start, DateTime(2026, 8, 2, 3)),
      ]);
      expect(rows.single.sleepEfficiencyPct, lessThanOrEqualTo(100));
    });
  });

  group('심박·HRV 는 평균이다', () {
    test('심박은 정수 평균', () {
      final rows = aggregateDaily([
        sample(HealthField.heartRate, 60, DateTime(2026, 8, 2, 9)),
        sample(HealthField.heartRate, 80, DateTime(2026, 8, 2, 12)),
        sample(HealthField.heartRate, 71, DateTime(2026, 8, 2, 18)),
      ]);
      expect(rows.single.heartRate, 70);
    });

    test('HRV 는 소수 둘째 자리까지 — NUMERIC(5,2)', () {
      final rows = aggregateDaily([
        sample(HealthField.hrv, 41.234, DateTime(2026, 8, 2, 9)),
        sample(HealthField.hrv, 38.111, DateTime(2026, 8, 2, 12)),
      ]);
      final hrv = rows.single.hrv!;
      expect(hrv, 39.67);
      expect(hrv.toString().split('.')[1].length, lessThanOrEqualTo(2));
    });
  });

  group('보관·복원 — MLCM_200 6단계', () {
    test('toJson → fromJson 왕복에서 값이 유지된다', () {
      final rows = aggregateDaily([
        sample(HealthField.steps, 8000, DateTime(2026, 8, 2, 9)),
        sample(HealthField.heartRate, 68, DateTime(2026, 8, 2, 10)),
        sample(HealthField.hrv, 42.5, DateTime(2026, 8, 2, 10)),
        sample(HealthField.sleepSession, 0, DateTime(2026, 8, 1, 23),
            DateTime(2026, 8, 2, 7)),
      ]);
      // 8/1 걸음 없음 → 8/2 한 행
      final original = rows.firstWhere((r) => r.collectedAt.day == 2);
      final restored = DailyLifelog.fromJson(original.toJson());

      expect(restored.collectedAt, original.collectedAt);
      expect(restored.steps, original.steps);
      expect(restored.heartRate, original.heartRate);
      expect(restored.hrv, original.hrv);
      expect(restored.totalSleepMin, original.totalSleepMin);
      expect(restored.sleepStartAt, original.sleepStartAt);
    });

    test('null 은 왕복 후에도 null 이다', () {
      final row = DailyLifelog(collectedAt: DateTime(2026, 8, 2), steps: 100);
      final restored = DailyLifelog.fromJson(row.toJson());
      expect(restored.steps, 100);
      expect(restored.heartRate, isNull, reason: '0 으로 되살아나면 안 됩니다');
      expect(restored.totalSleepMin, isNull);
    });
  });
}
