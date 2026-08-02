/// Health Connect 읽기 — MLCM_200 2·3단계
///
/// **플랫폼에 닿는 유일한 파일입니다.** 나머지 동기화 로직은
/// [lifelog_aggregate.dart] 와 [lifelog_sync.dart] 에 있고, 둘 다 이 파일에
/// 의존하지 않습니다. 그래서 실기기 없이 테스트할 수 있습니다.
///
/// ⚠ **수집 주체는 앱입니다.** 서버 스케줄러가 아닙니다. Health Connect 는
///   Android on-device 권한 모델이라 서버가 들고 있을 OAuth 토큰이 아예
///   없습니다(안건 1-1 확정).
library;

import 'package:flutter/foundation.dart';
import 'package:health/health.dart';

import 'lifelog_aggregate.dart';

/// 권한 상태. 화면이 무엇을 안내해야 하는지가 갈립니다.
enum HealthPermission {
  /// 읽을 수 있습니다.
  granted,

  /// 사용자가 거부했거나 아직 승인하지 않았습니다. 재승인 안내가 필요합니다.
  denied,

  /// Health Connect 앱 자체가 없습니다. 설치 안내가 필요합니다.
  unavailable,
}

/// 동기화 로직이 보는 인터페이스. 테스트는 이걸 가짜로 구현합니다.
abstract class HealthReader {
  Future<HealthPermission> permissionStatus();

  /// 권한 요청. 시스템 다이얼로그가 뜹니다.
  Future<HealthPermission> requestPermission();

  /// [from] ~ [to] 구간의 표본을 읽습니다.
  Future<List<HealthSample>> read({
    required DateTime from,
    required DateTime to,
  });

  /// Health Connect 설치 화면으로 보냅니다.
  Future<void> openInstall();
}

/// 실제 Health Connect 구현.
class HealthConnectReader implements HealthReader {
  HealthConnectReader({Health? health}) : _health = health ?? Health();

  final Health _health;
  bool _configured = false;

  /// 읽을 타입. **쓰기 권한은 요청하지 않습니다.**
  ///
  /// 이 앱은 건강 데이터를 만들지 않습니다. 쓰기 권한을 같이 요청하면
  /// 사용자가 승인 화면에서 「내 데이터를 고치려 한다」고 보게 됩니다.
  static const _types = <HealthDataType>[
    HealthDataType.STEPS,
    HealthDataType.DISTANCE_DELTA,
    HealthDataType.ACTIVE_ENERGY_BURNED,
    HealthDataType.HEART_RATE,
    HealthDataType.HEART_RATE_VARIABILITY_RMSSD,
    HealthDataType.SLEEP_SESSION,
    HealthDataType.SLEEP_DEEP,
    HealthDataType.SLEEP_LIGHT,
    HealthDataType.SLEEP_REM,
    HealthDataType.SLEEP_AWAKE,
  ];

  static final _permissions =
      List<HealthDataAccess>.filled(_types.length, HealthDataAccess.READ);

  Future<void> _ensureConfigured() async {
    if (_configured) return;
    await _health.configure();
    _configured = true;
  }

  @override
  Future<HealthPermission> permissionStatus() async {
    await _ensureConfigured();
    if (!await _health.isHealthConnectAvailable()) {
      return HealthPermission.unavailable;
    }
    // ⚠ hasPermissions 는 **null 을 돌려줄 수 있습니다**(판정 불가).
    //   null 을 granted 로 처리하면 권한이 없는데 읽으러 가서 예외가 납니다.
    final ok = await _health.hasPermissions(_types, permissions: _permissions);
    return ok == true ? HealthPermission.granted : HealthPermission.denied;
  }

  @override
  Future<HealthPermission> requestPermission() async {
    await _ensureConfigured();
    if (!await _health.isHealthConnectAvailable()) {
      return HealthPermission.unavailable;
    }
    final granted =
        await _health.requestAuthorization(_types, permissions: _permissions);
    if (!granted) return HealthPermission.denied;

    // 백그라운드 읽기 권한은 **별도**입니다. 이게 없으면 워커가 돌기는 하는데
    // 아무것도 못 읽어서 「앱을 열었을 때만 수집되는」 상태가 됩니다.
    //
    // ⚠ 실패해도 denied 로 만들지 않습니다. 기기가 이 기능을 지원하지 않을 수
    //   있고, 그래도 **앱이 떠 있는 동안의 수집은 정상 동작**합니다.
    try {
      if (await _health.isHealthDataInBackgroundAvailable() &&
          !await _health.isHealthDataInBackgroundAuthorized()) {
        await _health.requestHealthDataInBackgroundAuthorization();
      }
    } catch (e) {
      debugPrint('백그라운드 읽기 권한 요청 실패(수집은 계속됩니다): $e');
    }
    return HealthPermission.granted;
  }

  @override
  Future<void> openInstall() => _health.installHealthConnect();

  @override
  Future<List<HealthSample>> read({
    required DateTime from,
    required DateTime to,
  }) async {
    await _ensureConfigured();
    final points = await _health.getHealthDataFromTypes(
      types: _types,
      startTime: from,
      endTime: to,
    );

    final samples = <HealthSample>[];
    for (final p in points) {
      final field = _fieldOf(p.type);
      if (field == null) continue;
      final value = _valueOf(p);
      if (value == null) continue;
      samples.add(HealthSample(
        field: field,
        value: value,
        // ⚠ 반드시 로컬로 변환합니다. 하루 경계를 로컬 자정으로 자르는데
        //   UTC 시각을 그대로 넣으면 한국 기준 9시간이 밀립니다.
        from: p.dateFrom.toLocal(),
        to: p.dateTo.toLocal(),
      ));
    }
    return samples;
  }

  static HealthField? _fieldOf(HealthDataType type) => switch (type) {
        HealthDataType.STEPS => HealthField.steps,
        HealthDataType.DISTANCE_DELTA => HealthField.distance,
        HealthDataType.ACTIVE_ENERGY_BURNED => HealthField.calories,
        HealthDataType.HEART_RATE => HealthField.heartRate,
        HealthDataType.HEART_RATE_VARIABILITY_RMSSD => HealthField.hrv,
        HealthDataType.SLEEP_SESSION => HealthField.sleepSession,
        HealthDataType.SLEEP_DEEP => HealthField.sleepDeep,
        HealthDataType.SLEEP_LIGHT => HealthField.sleepLight,
        HealthDataType.SLEEP_REM => HealthField.sleepRem,
        HealthDataType.SLEEP_AWAKE => HealthField.sleepAwake,
        _ => null,
      };

  static double? _valueOf(HealthDataPoint p) {
    final v = p.value;
    if (v is NumericHealthValue) return v.numericValue.toDouble();
    // 수면 단계는 값이 아니라 **구간 길이**가 의미를 가집니다. 값이 숫자가
    // 아니어도 from~to 는 쓸 수 있으므로 0 을 넣고 통과시킵니다.
    if (p.type == HealthDataType.SLEEP_SESSION ||
        p.type == HealthDataType.SLEEP_DEEP ||
        p.type == HealthDataType.SLEEP_LIGHT ||
        p.type == HealthDataType.SLEEP_REM ||
        p.type == HealthDataType.SLEEP_AWAKE) {
      return 0;
    }
    debugPrint('알 수 없는 Health 값 형식: ${p.type} ${v.runtimeType}');
    return null;
  }
}
