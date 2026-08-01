/// 라이프로그 · 체성분 — MLCM_200
///
/// 서버 스키마(backend/app/schemas/lifelog.py)와 1:1로 맞춥니다.
library;

import 'json.dart';

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

  factory LifelogEntry.fromJson(Map<String, dynamic> json) => LifelogEntry(
        collectedAt:
            jsonAt(json['collected_at']) ??
                DateTime.now(),
        steps: jsonInt(json['steps']),
        distance: jsonInt(json['distance']),
        calories: jsonInt(json['calories']),
        totalActiveMin: jsonInt(json['total_active_min']),
        totalSleepMin: jsonInt(json['total_sleep_min']),
        deepSleepMin: jsonInt(json['deep_sleep_min']),
        lightSleepMin: jsonInt(json['light_sleep_min']),
        remSleepMin: jsonInt(json['rem_sleep_min']),
        awakeMin: jsonInt(json['awake_min']),
        sleepEfficiencyPct: jsonNum(json['sleep_efficiency_pct']),
        heartRate: jsonInt(json['heart_rate']),
        hrv: jsonNum(json['hrv']),
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
            jsonAt(json['measured_at']) ??
                DateTime.now(),
        weightKg: jsonNum(json['weight_kg']),
        bodyWaterKg: jsonNum(json['body_water_kg']),
        bodyFatKg: jsonNum(json['body_fat_kg']),
        muscleMassKg: jsonNum(json['muscle_mass_kg']),
        skeletalMuscleKg: jsonNum(json['skeletal_muscle_kg']),
        bmrKcal: jsonInt(json['bmr_kcal']),
      );
}
