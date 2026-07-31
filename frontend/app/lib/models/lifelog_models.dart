/// 라이프로그 · 체성분 — MLCM_200
///
/// 서버 스키마(backend/app/schemas/lifelog.py)와 1:1로 맞춥니다.
library;

/// 한 시점의 측정치.
///
/// ⚠ `collected_at` 을 뺀 **전 필드가 null 일 수 있습니다.** Health Connect 는
///   기기·권한에 따라 주는 항목이 다릅니다. 없는 값을 0 으로 채우면
///   "0걸음"과 "측정 안 됨"이 구분되지 않습니다.
class LifelogEntry {
  const LifelogEntry({
    required this.collectedAt,
    this.steps,
    this.distance,
    this.calories,
    this.totalActiveMin,
    this.totalSleepMin,
    this.deepSleepMin,
    this.lightSleepMin,
    this.remSleepMin,
    this.awakeMin,
    this.sleepEfficiencyPct,
    this.heartRate,
    this.hrv,
  });

  final DateTime collectedAt;

  final int? steps;
  final int? distance;
  final int? calories;
  final int? totalActiveMin;

  final int? totalSleepMin;
  final int? deepSleepMin;
  final int? lightSleepMin;
  final int? remSleepMin;
  final int? awakeMin;
  final double? sleepEfficiencyPct;

  final int? heartRate;
  final double? hrv;

  static int? _int(dynamic v) => (v as num?)?.toInt();

  /// ⚠ 서버가 NUMERIC 컬럼을 **문자열로** 내려보낼 수 있습니다(Decimal 직렬화).
  ///   num 으로만 캐스팅하면 조용히 null 이 됩니다.
  static double? _num(dynamic v) => switch (v) {
        num n => n.toDouble(),
        String s => double.tryParse(s),
        _ => null,
      };

  factory LifelogEntry.fromJson(Map<String, dynamic> json) => LifelogEntry(
        collectedAt:
            DateTime.tryParse(json['collected_at'] as String? ?? '')?.toLocal() ??
                DateTime.now(),
        steps: _int(json['steps']),
        distance: _int(json['distance']),
        calories: _int(json['calories']),
        totalActiveMin: _int(json['total_active_min']),
        totalSleepMin: _int(json['total_sleep_min']),
        deepSleepMin: _int(json['deep_sleep_min']),
        lightSleepMin: _int(json['light_sleep_min']),
        remSleepMin: _int(json['rem_sleep_min']),
        awakeMin: _int(json['awake_min']),
        sleepEfficiencyPct: _num(json['sleep_efficiency_pct']),
        heartRate: _int(json['heart_rate']),
        hrv: _num(json['hrv']),
      );
}

class BodyComposition {
  const BodyComposition({
    required this.measuredAt,
    this.weightKg,
    this.bodyWaterKg,
    this.bodyFatKg,
    this.muscleMassKg,
    this.skeletalMuscleKg,
    this.bmrKcal,
  });

  final DateTime measuredAt;
  final double? weightKg;
  final double? bodyWaterKg;
  final double? bodyFatKg;
  final double? muscleMassKg;
  final double? skeletalMuscleKg;
  final int? bmrKcal;

  factory BodyComposition.fromJson(Map<String, dynamic> json) =>
      BodyComposition(
        measuredAt:
            DateTime.tryParse(json['measured_at'] as String? ?? '')?.toLocal() ??
                DateTime.now(),
        weightKg: LifelogEntry._num(json['weight_kg']),
        bodyWaterKg: LifelogEntry._num(json['body_water_kg']),
        bodyFatKg: LifelogEntry._num(json['body_fat_kg']),
        muscleMassKg: LifelogEntry._num(json['muscle_mass_kg']),
        skeletalMuscleKg: LifelogEntry._num(json['skeletal_muscle_kg']),
        bmrKcal: LifelogEntry._int(json['bmr_kcal']),
      );
}
