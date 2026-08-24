/// Health Connect 표본 → 라이프로그 행 집계 — MLCM_200 3단계
///
/// **이 파일에는 플랫폼 의존이 없습니다.** Health Connect 를 읽는 쪽은
/// [HealthReader] 이고, 여기는 읽어온 표본을 접기만 합니다. 그래서 실기기
/// 없이 테스트할 수 있습니다.
///
/// ---
/// ## ⚠ 왜 「하루 한 행」인가 — 15분마다 행을 만들면 안 됩니다
///
/// `MLCM_200` 은 **최소 15분 간격 전송**을 규정합니다. 그래서 15분마다 행을
/// 하나씩 넣는 것으로 읽기 쉬운데, 그러면 아래가 전부 깨집니다.
///
/// * `ai/server` 는 `rows[-1]` 을 **「오늘」** 로 보고, 행들의 평균을 14일
///   기준값으로 씁니다. 15분 행이면 `rows[-1]` 이 **「마지막 15분」** 이 되고
///   기준값은 15분 버킷 평균이 되어 의미가 사라집니다.
/// * `sleep_start_at`·`sleep_end_at`·`total_sleep_min` 은 **하루치 수면**을
///   담는 컬럼입니다. 15분으로 쪼개면 한 수면이 32행에 흩어집니다.
/// * `MLCM_200` 5단계의 「동일 시각 재전송해도 중복 적재되지 않는다」는
///   **같은 행을 다시 보낸다**는 뜻입니다. 지나간 15분 버킷은 다시 보낼 이유가
///   없으므로, 이 문장은 갱신되는 집계 행을 전제합니다.
///
/// 그래서 **전송은 15분마다 하되, 행은 그날 것을 UPSERT 로 갱신**합니다.
/// `uq_lifelog_user_collected (user_id, collected_at)` 이 정확히 이걸 위한
/// 제약입니다.
///
/// ## 하루의 경계는 **로컬 자정**입니다
///
/// UTC 자정으로 자르면 한국 시간 오전 9시에 날짜가 바뀌어, 사용자가 체감하는
/// 하루와 어긋납니다. 수면이 자정을 넘기므로 경계 선택이 특히 중요합니다.
library;

/// 집계 대상 지표. Health Connect 타입을 그대로 쓰지 않고 한 번 접습니다.
///
/// 플러그인 타입(`HealthDataType`)을 여기까지 끌고 오면 이 파일이 플랫폼에
/// 묶여 테스트가 어려워집니다.
enum HealthField {
  steps,
  distance,
  calories,
  heartRate,
  hrv,
  activeSession,
  sleepSession,
  sleepDeep,
  sleepLight,
  sleepRem,
  sleepAwake,

  // --- 체성분 (MAIN_LIFELOG_01 ❺) ---
  //
  // ⚠ **하루 집계에 섞지 않습니다.** 체성분은 측정한 순간에만 생기고
  //   측정 빈도가 불규칙합니다. 15분 배치에 섞으면 빈 값이 대부분인 행이
  //   쌓입니다 — 서버도 같은 이유로 테이블·엔드포인트를 분리했습니다.
  weight,
  bodyFatPercentage,
  bodyWaterMass,
  basalEnergy,
}

/// Health Connect 표본 한 건. 구간([from], [to])과 값을 가집니다.
///
/// 순간 측정(심박·HRV)은 [from] 과 [to] 가 같습니다.
class HealthSample {
  const HealthSample({
    required this.field,
    required this.value,
    required this.from,
    required this.to,
  });

  final HealthField field;
  final double value;

  /// ⚠ **로컬 시각**입니다. 하루 경계를 로컬 자정으로 자르기 때문입니다.
  final DateTime from;
  final DateTime to;

  Duration get duration => to.difference(from);
}

/// 하루치 라이프로그 한 행. 서버 `LifelogItem` 과 필드가 1:1 대응합니다.
///
/// ⚠ **모든 필드가 nullable 입니다.** 「0」과 「측정 안 됨」은 다릅니다.
///   자세한 이유는 [toJson] 주석을 보세요.
class DailyLifelog {
  const DailyLifelog({
    required this.collectedAt,
    this.steps,
    this.distance,
    this.calories,
    this.activityStartAt,
    this.activityEndAt,
    this.totalActiveMin,
    this.sleepStartAt,
    this.sleepEndAt,
    this.totalSleepMin,
    this.deepSleepMin,
    this.lightSleepMin,
    this.remSleepMin,
    this.awakeMin,
    this.sleepOnsetMin,
    this.sleepEfficiencyPct,
    this.heartRate,
    this.hrv,
    this.screenTimeMin,
    this.nightScreenMin,
    this.appSessionCount,
  });

  /// 그날의 **로컬 자정**. 서버로는 UTC 로 보냅니다.
  final DateTime collectedAt;

  final int? steps;
  final int? distance;
  final int? calories;

  final DateTime? activityStartAt;
  final DateTime? activityEndAt;
  final int? totalActiveMin;

  final DateTime? sleepStartAt;
  final DateTime? sleepEndAt;
  final int? totalSleepMin;
  final int? deepSleepMin;
  final int? lightSleepMin;
  final int? remSleepMin;
  final int? awakeMin;
  final int? sleepOnsetMin;
  final double? sleepEfficiencyPct;

  final int? heartRate;
  final double? hrv;

  //  [05-U] 앱 사용 로그. 사용 정보 접근을 승인하지 않은 단말은 셋 다 null.
  //  ⚠ **0 이 아니라 null 입니다.** 「0분 썼다」와 「권한이 없어 모른다」는
  //    다르고, 0 으로 적재하면 개인 기준선이 통째로 내려앉습니다.
  final int? screenTimeMin;
  final int? nightScreenMin;
  final int? appSessionCount;

  /// 측정된 지표가 하나도 없으면 참. 보낼 이유가 없는 행입니다.
  bool get isEmpty =>
      steps == null &&
      distance == null &&
      calories == null &&
      totalActiveMin == null &&
      totalSleepMin == null &&
      heartRate == null &&
      hrv == null &&
      screenTimeMin == null;

  /// 서버 `POST /lifelog/batch` 의 item 규격.
  ///
  /// ⚠ **null 인 필드는 키 자체를 넣지 않습니다.** 서버 스키마가 전부
  ///   `| None = None` 이라 빠진 키는 null 로 들어갑니다.
  ///
  /// ⚠ **없는 값을 0 으로 채우지 마세요.** `steps` 는 스키마 기본값이 0 이라
  ///   0 을 보내면 「측정 안 됨」과 「0걸음」이 구분되지 않습니다.
  ///   `ai/server` 의 `_has_signal()` 은 이걸 알고 0 을 기준값에서 빼지만,
  ///   그 결과 **하루 종일 안 움직인 사람의 실제 0 도 같이 버려집니다.**
  ///   구분이 되도록 애초에 null 로 보내는 게 맞습니다.
  Map<String, dynamic> toJson() {
    final json = <String, dynamic>{
      'collected_at': collectedAt.toUtc().toIso8601String(),
    };
    void put(String key, Object? value) {
      if (value != null) json[key] = value;
    }

    put('steps', steps);
    put('distance', distance);
    put('calories', calories);
    put('activity_start_at', activityStartAt?.toUtc().toIso8601String());
    put('activity_end_at', activityEndAt?.toUtc().toIso8601String());
    put('total_active_min', totalActiveMin);
    put('sleep_start_at', sleepStartAt?.toUtc().toIso8601String());
    put('sleep_end_at', sleepEndAt?.toUtc().toIso8601String());
    put('total_sleep_min', totalSleepMin);
    put('deep_sleep_min', deepSleepMin);
    put('light_sleep_min', lightSleepMin);
    put('rem_sleep_min', remSleepMin);
    put('awake_min', awakeMin);
    put('sleep_onset_min', sleepOnsetMin);
    put('sleep_efficiency_pct', sleepEfficiencyPct);
    put('heart_rate', heartRate);
    put('hrv', hrv);
    put('screen_time_min', screenTimeMin);
    put('night_screen_min', nightScreenMin);
    put('app_session_count', appSessionCount);
    return json;
  }

  /// 앱 사용 집계를 얹은 사본.
  ///
  /// ⚠ **집계(`aggregateDaily`)에서 만들지 않고 여기서 붙입니다.** 앱 사용은
  ///   Health Connect 가 아니라 `UsageStatsManager` 에서 오고, 권한도 따로
  ///   입니다. 출처가 다른 것을 한 함수에 섞으면 한쪽 권한이 없을 때 다른
  ///   쪽까지 못 만들게 됩니다.
  DailyLifelog withUsage(AppUsageLike? usage) {
    if (usage == null) return this;
    return DailyLifelog(
      collectedAt: collectedAt,
      steps: steps,
      distance: distance,
      calories: calories,
      activityStartAt: activityStartAt,
      activityEndAt: activityEndAt,
      totalActiveMin: totalActiveMin,
      sleepStartAt: sleepStartAt,
      sleepEndAt: sleepEndAt,
      totalSleepMin: totalSleepMin,
      deepSleepMin: deepSleepMin,
      lightSleepMin: lightSleepMin,
      remSleepMin: remSleepMin,
      awakeMin: awakeMin,
      sleepOnsetMin: sleepOnsetMin,
      sleepEfficiencyPct: sleepEfficiencyPct,
      heartRate: heartRate,
      hrv: hrv,
      screenTimeMin: usage.screenTimeMin,
      nightScreenMin: usage.nightScreenMin,
      appSessionCount: usage.appSessionCount,
    );
  }

  /// 재시도 큐를 단말에 보관했다가 복원할 때 씁니다(`MLCM_200` 6단계).
  static DailyLifelog fromJson(Map<String, dynamic> json) {
    DateTime? at(String key) {
      final raw = json[key];
      return raw is String ? DateTime.parse(raw).toLocal() : null;
    }

    int? i(String key) => (json[key] as num?)?.round();
    double? d(String key) => (json[key] as num?)?.toDouble();

    return DailyLifelog(
      collectedAt: DateTime.parse(json['collected_at'] as String).toLocal(),
      steps: i('steps'),
      distance: i('distance'),
      calories: i('calories'),
      activityStartAt: at('activity_start_at'),
      activityEndAt: at('activity_end_at'),
      totalActiveMin: i('total_active_min'),
      sleepStartAt: at('sleep_start_at'),
      sleepEndAt: at('sleep_end_at'),
      totalSleepMin: i('total_sleep_min'),
      deepSleepMin: i('deep_sleep_min'),
      lightSleepMin: i('light_sleep_min'),
      remSleepMin: i('rem_sleep_min'),
      awakeMin: i('awake_min'),
      sleepOnsetMin: i('sleep_onset_min'),
      sleepEfficiencyPct: d('sleep_efficiency_pct'),
      heartRate: i('heart_rate'),
      hrv: d('hrv'),
      screenTimeMin: i('screen_time_min'),
      nightScreenMin: i('night_screen_min'),
      appSessionCount: i('app_session_count'),
    );
  }
}

/// [DailyLifelog.withUsage] 가 요구하는 최소 모양.
///
/// ⚠ `app_usage_reader.dart` 의 `AppUsage` 를 직접 import 하지 않습니다.
///   집계 파일이 플랫폼 채널 파일에 의존하면 「실기기 없이 테스트 가능」이
///   깨집니다. 필드 셋만 요구합니다.
abstract class AppUsageLike {
  int get screenTimeMin;
  int get nightScreenMin;
  int get appSessionCount;
}

/// 그날의 로컬 자정.
DateTime dayStart(DateTime t) => DateTime(t.year, t.month, t.day);

/// 표본들을 하루 한 행으로 접습니다. 결과는 `collected_at` 오름차순.
///
/// 귀속 규칙:
/// * 활동량(걸음·거리·칼로리)·심박·HRV → 표본 **시작** 시각의 날
/// * 수면 → 그 수면에서 **깨어난** 날
///
/// 수면을 깨어난 날에 붙이는 이유: 「7월 3일 수면」이라고 하면 보통 3일 밤에
/// 잠들어 4일 아침에 깬 것이 아니라, **4일 아침에 일어나기까지의 잠**을
/// 뜻합니다. 사용자가 4일 낮에 앱을 열었을 때 보고 싶은 값이기도 합니다.
List<DailyLifelog> aggregateDaily(List<HealthSample> samples) {
  final byDay = <DateTime, List<HealthSample>>{};
  for (final s in samples) {
    // 수면만 종료 시각 기준. 나머지는 시작 시각 기준.
    final anchor = _isSleep(s.field) ? s.to : s.from;
    byDay.putIfAbsent(dayStart(anchor), () => []).add(s);
  }

  final days = byDay.keys.toList()..sort();
  final out = <DailyLifelog>[];
  for (final day in days) {
    final row = _foldDay(day, byDay[day]!);
    // 지표가 하나도 없는 행은 보내지 않습니다. 빈 행을 적재하면 ai/server 가
    // 「행은 있는데 지표가 없다」로 422 를 내는 상태를 우리가 만들게 됩니다.
    if (!row.isEmpty) out.add(row);
  }
  return out;
}

bool _isSleep(HealthField f) =>
    f == HealthField.sleepSession ||
    f == HealthField.sleepDeep ||
    f == HealthField.sleepLight ||
    f == HealthField.sleepRem ||
    f == HealthField.sleepAwake;

DailyLifelog _foldDay(DateTime day, List<HealthSample> samples) {
  List<HealthSample> of(HealthField f) =>
      samples.where((s) => s.field == f).toList();

  int? sumOf(HealthField f) {
    final rows = of(f);
    if (rows.isEmpty) return null; // ⚠ 0 이 아니라 null
    return rows.fold<double>(0, (a, s) => a + s.value).round();
  }

  int? meanOf(HealthField f) {
    final rows = of(f);
    if (rows.isEmpty) return null;
    return (rows.fold<double>(0, (a, s) => a + s.value) / rows.length).round();
  }

  double? meanDoubleOf(HealthField f) {
    final rows = of(f);
    if (rows.isEmpty) return null;
    final mean = rows.fold<double>(0, (a, s) => a + s.value) / rows.length;
    return double.parse(mean.toStringAsFixed(2)); // NUMERIC(5,2)
  }

  int? minutesOf(HealthField f) {
    final rows = of(f);
    if (rows.isEmpty) return null;
    return rows.fold<int>(0, (a, s) => a + s.duration.inMinutes);
  }

  // --- 활동 구간 -----------------------------------------------------
  final active = of(HealthField.activeSession);
  DateTime? activityStart;
  DateTime? activityEnd;
  int? activeMin;
  if (active.isNotEmpty) {
    active.sort((a, b) => a.from.compareTo(b.from));
    activityStart = active.first.from;
    activityEnd =
        active.map((s) => s.to).reduce((a, b) => a.isAfter(b) ? a : b);
    activeMin = active.fold<int>(0, (a, s) => a + s.duration.inMinutes);
  }

  // --- 수면 ----------------------------------------------------------
  final sessions = of(HealthField.sleepSession);
  final deep = minutesOf(HealthField.sleepDeep);
  final light = minutesOf(HealthField.sleepLight);
  final rem = minutesOf(HealthField.sleepRem);
  final awake = minutesOf(HealthField.sleepAwake);

  DateTime? sleepStart;
  DateTime? sleepEnd;
  int? totalSleep;
  int? onset;
  double? efficiency;

  if (sessions.isNotEmpty) {
    sessions.sort((a, b) => a.from.compareTo(b.from));
    sleepStart = sessions.first.from;
    sleepEnd = sessions.map((s) => s.to).reduce((a, b) => a.isAfter(b) ? a : b);
    final inBed = sessions.fold<int>(0, (a, s) => a + s.duration.inMinutes);

    final staged = [deep, light, rem].whereType<int>();
    if (staged.isNotEmpty) {
      // 단계가 있으면 단계 합이 실제 수면 시간입니다.
      totalSleep = staged.fold<int>(0, (a, b) => a + b);
    } else if (awake != null) {
      totalSleep = inBed - awake;
    } else {
      // 단계 정보가 없는 기기. 세션 길이를 그대로 씁니다.
      totalSleep = inBed;
    }
    if (totalSleep < 0) totalSleep = 0;

    if (inBed > 0) {
      final pct = totalSleep / inBed * 100;
      efficiency = double.parse(pct.clamp(0, 100).toStringAsFixed(2));
    }

    // 잠들기까지 걸린 시간 — 세션 시작부터 첫 수면 단계까지.
    // ⚠ 단계 정보가 없으면 **추정하지 않고 null** 로 둡니다. 0 으로 채우면
    //   「눕자마자 잠들었다」는 없는 사실이 기록됩니다.
    final stages = samples
        .where((s) =>
            s.field == HealthField.sleepDeep ||
            s.field == HealthField.sleepLight ||
            s.field == HealthField.sleepRem)
        .toList();
    if (stages.isNotEmpty) {
      stages.sort((a, b) => a.from.compareTo(b.from));
      final gap = stages.first.from.difference(sleepStart).inMinutes;
      onset = gap < 0 ? 0 : gap;
    }
  }

  return DailyLifelog(
    collectedAt: day,
    steps: sumOf(HealthField.steps),
    distance: sumOf(HealthField.distance),
    calories: sumOf(HealthField.calories),
    activityStartAt: activityStart,
    activityEndAt: activityEnd,
    totalActiveMin: activeMin,
    sleepStartAt: sleepStart,
    sleepEndAt: sleepEnd,
    totalSleepMin: totalSleep,
    deepSleepMin: deep,
    lightSleepMin: light,
    remSleepMin: rem,
    awakeMin: awake,
    sleepOnsetMin: onset,
    sleepEfficiencyPct: efficiency,
    heartRate: meanOf(HealthField.heartRate),
    hrv: meanDoubleOf(HealthField.hrv),
  );
}

/// 체성분 측정 한 건. 서버 `POST /body-composition` 규격과 1:1 대응합니다.
///
/// ⚠ **8개 컬럼 중 4개만 채웁니다.** Health Connect 에 근육량·골격근량
///   레코드가 없습니다(2026.08.03 확인, A안 확정 → 개정안 `PL-26`).
///   기업 제공 데이터에는 8개가 다 있어 테이블은 그대로 둡니다 — 실서비스
///   수집 경로와 학습 데이터 출처의 항목이 다른 것입니다.
///
/// ⚠ **`LEAN_BODY_MASS`(제지방량)를 근육량에 넣지 마세요.** 제지방량은
///   근육 + 뼈 + 수분 + 장기라서 다른 값입니다. 이름이 비슷하다고 넣으면
///   틀린 숫자가 화면에 뜹니다.
class BodyCompositionSample {
  const BodyCompositionSample({
    required this.measuredAt,
    this.weightKg,
    this.bodyFatKg,
    this.bodyWaterKg,
    this.bmrKcal,
  });

  final DateTime measuredAt;
  final double? weightKg;
  final double? bodyFatKg;
  final double? bodyWaterKg;
  final int? bmrKcal;

  bool get isEmpty =>
      weightKg == null &&
      bodyFatKg == null &&
      bodyWaterKg == null &&
      bmrKcal == null;

  /// null 인 필드는 키 자체를 넣지 않습니다(`DailyLifelog.toJson` 과 같은 이유).
  Map<String, dynamic> toJson() {
    final json = <String, dynamic>{
      'measured_at': measuredAt.toUtc().toIso8601String(),
    };
    void put(String k, Object? v) {
      if (v != null) json[k] = v;
    }

    put('weight_kg', weightKg);
    put('body_fat_kg', bodyFatKg);
    put('body_water_kg', bodyWaterKg);
    put('bmr_kcal', bmrKcal);
    return json;
  }
}

/// 체성분 표본을 **측정 건 단위**로 묶습니다. 결과는 `measuredAt` 오름차순.
///
/// ## 왜 분 단위로 묶나
///
/// 체성분계 한 번 측정이 Health Connect 에 **레코드 여러 개**로 들어옵니다
/// (체중 / 체지방률 / 체수분이 각각). 같은 측정인데 타임스탬프가 초 단위로
/// 어긋날 수 있어, 그대로 두면 한 번 잰 것이 세 건으로 쪼개집니다.
///
/// ## 체지방은 %로 오므로 체중이 있어야 kg 이 됩니다
///
/// 스키마는 `body_fat_kg` 인데 Health Connect 는 `BODY_FAT_PERCENTAGE` 를
/// 줍니다. **체중이 같이 없으면 환산할 수 없어 비웁니다.** 퍼센트를 kg
/// 칸에 그대로 넣으면 「체지방 22kg」이 「22%」로 뒤바뀝니다.
List<BodyCompositionSample> aggregateBodyComposition(
  List<HealthSample> samples,
) {
  const fields = {
    HealthField.weight,
    HealthField.bodyFatPercentage,
    HealthField.bodyWaterMass,
    HealthField.basalEnergy,
  };

  final byMinute = <DateTime, Map<HealthField, double>>{};
  for (final s in samples) {
    if (!fields.contains(s.field)) continue;
    final key = DateTime(
        s.from.year, s.from.month, s.from.day, s.from.hour, s.from.minute);
    // 같은 분에 같은 지표가 여럿이면 마지막 것을 씁니다.
    (byMinute[key] ??= {})[s.field] = s.value;
  }

  final keys = byMinute.keys.toList()..sort();
  final out = <BodyCompositionSample>[];
  for (final at in keys) {
    final v = byMinute[at]!;
    final weight = v[HealthField.weight];
    final fatPct = v[HealthField.bodyFatPercentage];

    final row = BodyCompositionSample(
      measuredAt: at,
      weightKg: _round2(weight),
      bodyFatKg: (weight != null && fatPct != null)
          ? _round2(weight * fatPct / 100)
          : null,
      bodyWaterKg: _round2(v[HealthField.bodyWaterMass]),
      bmrKcal: v[HealthField.basalEnergy]?.round(),
    );
    if (!row.isEmpty) out.add(row);
  }
  return out;
}

/// NUMERIC(5,2) 에 맞춥니다.
double? _round2(double? v) =>
    v == null ? null : double.parse(v.toStringAsFixed(2));
