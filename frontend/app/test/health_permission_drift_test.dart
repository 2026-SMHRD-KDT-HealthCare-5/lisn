/// 코드가 요청하는 타입 ↔ 매니페스트 권한이 갈리지 않게 — MLCM_200
///
/// ## 왜 이 테스트가 필요한가
///
/// Health Connect 는 **매니페스트에 선언되지 않은 타입을 요청하면 예외 없이
/// 그냥 빼고 승인**합니다. 그래서 `health_reader.dart` 에 타입을 추가하고
/// `AndroidManifest.xml` 을 안 고치면 이렇게 됩니다.
///
/// * 권한 다이얼로그가 **정상적으로 뜹니다**
/// * 사용자가 **「허용」을 누릅니다**
/// * `hasPermissions` 가 **true 를 돌려줍니다**
/// * 그런데 그 타입만 **항상 빈 배열**입니다
///
/// 화면 어디에도 오류가 없고, 그 지표만 영원히 null 입니다. 실기기에서
/// 며칠 데이터를 모아본 뒤에야 알아챌 수 있습니다.
///
/// ⚠ 이건 `backend/tests/test_schema_drift.py` 와 같은 종류의 테스트입니다.
///   정본이 둘인 곳(코드·매니페스트)을 기계가 대조합니다.
library;

import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// Health Connect 데이터 타입 → 필요한 매니페스트 권한.
///
/// 여러 타입이 한 권한을 공유합니다(수면 5종 → READ_SLEEP).
const _requiredPermission = <String, String>{
  'STEPS': 'READ_STEPS',
  'DISTANCE_DELTA': 'READ_DISTANCE',
  'ACTIVE_ENERGY_BURNED': 'READ_ACTIVE_CALORIES_BURNED',
  'HEART_RATE': 'READ_HEART_RATE',
  'HEART_RATE_VARIABILITY_RMSSD': 'READ_HEART_RATE_VARIABILITY',
  'SLEEP_SESSION': 'READ_SLEEP',
  'SLEEP_DEEP': 'READ_SLEEP',
  'SLEEP_LIGHT': 'READ_SLEEP',
  'SLEEP_REM': 'READ_SLEEP',
  'SLEEP_AWAKE': 'READ_SLEEP',
};

/// `health_reader.dart` 의 `_types` 목록에 적힌 타입 이름.
Set<String> readerTypes() {
  final source = File('lib/services/health_reader.dart').readAsStringSync();
  final start = source.indexOf('static const _types');
  expect(start, greaterThan(-1), reason: '_types 선언을 찾지 못했습니다');
  final end = source.indexOf('];', start);
  expect(end, greaterThan(start));

  final block = source.substring(start, end);
  return RegExp(r'HealthDataType\.([A-Z_]+)')
      .allMatches(block)
      .map((m) => m.group(1)!)
      .toSet();
}

/// 매니페스트에 선언된 `android.permission.health.*` 권한.
Set<String> manifestPermissions() {
  final manifest =
      File('android/app/src/main/AndroidManifest.xml').readAsStringSync();
  return RegExp(r'android\.permission\.health\.([A-Z_]+)')
      .allMatches(manifest)
      .map((m) => m.group(1)!)
      .toSet();
}

void main() {
  test('테스트가 실제로 뭔가를 읽었는지 먼저 확인한다', () {
    // ⚠ 파싱이 조용히 0건이면 아래 검사가 전부 통과해버립니다.
    expect(readerTypes(), isNotEmpty);
    expect(manifestPermissions(), isNotEmpty);
  });

  test('요청하는 모든 타입의 권한이 매니페스트에 있다', () {
    final declared = manifestPermissions();
    final missing = <String, String>{};

    for (final type in readerTypes()) {
      final needed = _requiredPermission[type];
      expect(needed, isNotNull,
          reason: '$type 에 필요한 권한을 이 테스트가 모릅니다. '
              '_requiredPermission 에 추가하세요');
      if (!declared.contains(needed)) missing[type] = needed!;
    }

    expect(missing, isEmpty,
        reason: 'AndroidManifest.xml 에 권한이 없습니다. '
            '요청은 성공하는데 데이터만 안 옵니다 → $missing');
  });

  test('매니페스트에 쓰지 않는 권한을 선언하지 않는다', () {
    // 안 쓰는 민감 권한이 남아 있으면 승인 화면에 그대로 뜨고, Google
    // 심사에서도 「왜 필요한가」를 설명해야 합니다.
    final needed = {
      for (final t in readerTypes()) _requiredPermission[t]!,
      // 백그라운드 읽기는 타입이 아니라 별도 권한입니다.
      'READ_HEALTH_DATA_IN_BACKGROUND',
    };
    expect(manifestPermissions().difference(needed), isEmpty);
  });

  test('⚠ 백그라운드 읽기 권한이 선언돼 있다', () {
    // 이게 없으면 워커가 **돌기는 하는데 아무것도 못 읽습니다.**
    // 앱을 열었을 때만 수집돼서 「가끔 되는」 것처럼 보입니다.
    expect(manifestPermissions(), contains('READ_HEALTH_DATA_IN_BACKGROUND'));
  });

  test('걸음 수에 필요한 ACTIVITY_RECOGNITION 이 있다', () {
    final manifest =
        File('android/app/src/main/AndroidManifest.xml').readAsStringSync();
    expect(manifest, contains('android.permission.ACTIVITY_RECOGNITION'));
  });

  test('⚠ MainActivity 는 FlutterFragmentActivity 를 상속한다', () {
    // FlutterActivity 로 두면 권한 다이얼로그가 **뜨지 않고** 요청이 조용히
    // 거부됩니다. health 플러그인이 Fragment 기반으로 띄우기 때문입니다.
    final main = File(
      'android/app/src/main/kotlin/com/lisn/maeume/MainActivity.kt',
    ).readAsStringSync();
    expect(main, contains('FlutterFragmentActivity'));
    expect(main.contains(': FlutterActivity()'), isFalse);
  });
}
