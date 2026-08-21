import 'package:flutter_test/flutter_test.dart';
import 'package:maeume_care/models/lifelog_models.dart';

void main() {
  test('NUMERIC 컬럼이 문자열로 와도 파싱한다', () {
    // 서버가 Decimal 을 문자열로 직렬화한다. 실측 확인:
    //   hrv: '36.50', sleep_efficiency_pct: '88.50'
    // num 으로만 캐스팅하면 조용히 null 이 되어 화면에 '–' 만 뜬다.
    final entry = LifelogEntry.fromJson({
      'collected_at': '2026-08-01T09:00:00Z',
      'steps': 9200,
      'total_sleep_min': 292,
      'heart_rate': 74,
      'hrv': '36.50',
      'sleep_efficiency_pct': '88.50',
    });

    expect(entry.hrv, 36.5);
    expect(entry.sleepEfficiencyPct, 88.5);
    expect(entry.steps, 9200);
    expect(entry.heartRate, 74);
  });

  test('측정되지 않은 항목은 0 이 아니라 null 로 남는다', () {
    // "0걸음"과 "측정 안 됨"은 다르다. 0 으로 채우면 구분이 사라진다.
    final entry = LifelogEntry.fromJson({
      'collected_at': '2026-08-01T09:00:00Z',
    });

    expect(entry.steps, isNull);
    expect(entry.totalSleepMin, isNull);
    expect(entry.heartRate, isNull);
    expect(entry.hrv, isNull);
  });

  test('체성분도 문자열 숫자를 받는다', () {
    final body = BodyComposition.fromJson({
      'measured_at': '2026-08-01T09:00:00Z',
      'weight_kg': '67.30',
      'skeletal_muscle_kg': '28.10',
      'bmr_kcal': 1520,
    });

    expect(body.weightKg, 67.3);
    expect(body.skeletalMuscleKg, 28.1);
    expect(body.bmrKcal, 1520);
    expect(body.bodyFatKg, isNull);
  });
}
