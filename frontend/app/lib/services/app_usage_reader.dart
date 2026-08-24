/// 앱 사용 로그 읽기 — 기업 브리프(PROJECT_02) 개발목표의
/// 「**앱 사용 로그** + 웨어러블 생체신호」 중 앞쪽.
///
/// **플랫폼에 닿는 두 번째 파일입니다**(첫 번째는 [health_reader.dart]).
/// 집계·동기화는 이 파일에 의존하지 않고 [AppUsageReader] 인터페이스만
/// 보므로, 실기기 없이 테스트할 수 있습니다.
///
/// ⚠ **패키지명·앱 이름을 받지 않습니다.** 네이티브 쪽에서 이미 집계값
///   셋으로 접어서 넘어옵니다(`AppUsagePlugin.kt`). 「무슨 앱을 썼나」가
///   아니라 「평소와 다른가」를 재는 것이 목적이고, 판정도 개인 기준선
///   대비 이탈만 봅니다.
///
/// ⚠ **권한이 없으면 `null` 입니다. 0 이 아닙니다.**
///   「0분 썼다」와 「권한이 없어 모른다」는 다릅니다. 0 으로 적재하면
///   개인 기준선이 통째로 내려앉아, 실제로 많이 쓴 날이 이탈로 안 잡힙니다.
library;

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

import 'lifelog_aggregate.dart' show AppUsageLike;

/// 한 구간의 앱 사용 집계.
@immutable
class AppUsage implements AppUsageLike {
  const AppUsage({
    required this.screenTimeMin,
    required this.nightScreenMin,
    required this.appSessionCount,
  });

  /// 구간 내 화면 사용 시간(분).
  @override
  final int screenTimeMin;

  /// 그중 22시~06시 사용 시간(분). 수면 방해·야간 반추의 지표입니다.
  @override
  final int nightScreenMin;

  /// 앱 전환(포그라운드 진입) 횟수. 짧고 잦은 확인의 지표입니다.
  @override
  final int appSessionCount;

  Map<String, Object?> toJson() => {
        'screen_time_min': screenTimeMin,
        'night_screen_min': nightScreenMin,
        'app_session_count': appSessionCount,
      };

  @override
  bool operator ==(Object other) =>
      other is AppUsage &&
      other.screenTimeMin == screenTimeMin &&
      other.nightScreenMin == nightScreenMin &&
      other.appSessionCount == appSessionCount;

  @override
  int get hashCode => Object.hash(screenTimeMin, nightScreenMin, appSessionCount);

  @override
  String toString() =>
      'AppUsage($screenTimeMin분 · 야간 $nightScreenMin분 · $appSessionCount회)';
}

/// 동기화 로직이 보는 인터페이스. 테스트는 이걸 가짜로 구현합니다.
abstract class AppUsageReader {
  /// 사용 정보 접근이 켜져 있는가.
  Future<bool> hasPermission();

  /// 설정 화면으로 보냅니다.
  ///
  /// ⚠ **시스템 다이얼로그가 없습니다.** `PACKAGE_USAGE_STATS` 는 일반
  ///   권한이 아니라 사용자가 설정에서 직접 켜야 합니다. 그래서 「요청」이
  ///   아니라 「안내」입니다 — 돌아온 뒤 [hasPermission] 을 다시 보세요.
  Future<void> openSettings();

  /// [from]~[to] 구간의 집계. 권한이 없으면 `null`.
  Future<AppUsage?> read({required DateTime from, required DateTime to});
}

/// 실제 Android 구현. 다른 플랫폼에서는 항상 `null` 을 돌려줍니다.
class PlatformAppUsageReader implements AppUsageReader {
  const PlatformAppUsageReader();

  static const _channel = MethodChannel('com.lisn.maeume/app_usage');

  bool get _supported => defaultTargetPlatform == TargetPlatform.android;

  @override
  Future<bool> hasPermission() async {
    if (!_supported) return false;
    try {
      return await _channel.invokeMethod<bool>('hasPermission') ?? false;
    } on PlatformException {
      return false;
    }
  }

  @override
  Future<void> openSettings() async {
    if (!_supported) return;
    try {
      await _channel.invokeMethod<void>('openSettings');
    } on PlatformException {
      //  설정 화면이 없는 기기가 있을 수 있다. 안내만 실패하고 앱은 계속 돈다.
    }
  }

  @override
  Future<AppUsage?> read({required DateTime from, required DateTime to}) async {
    if (!_supported) return null;
    try {
      final r = await _channel.invokeMapMethod<String, int>('collect', {
        'from': from.millisecondsSinceEpoch,
        'to': to.millisecondsSinceEpoch,
      });
      if (r == null) return null; // 권한 없음
      return AppUsage(
        screenTimeMin: r['screen_time_min'] ?? 0,
        nightScreenMin: r['night_screen_min'] ?? 0,
        appSessionCount: r['app_session_count'] ?? 0,
      );
    } on PlatformException {
      //  ⚠ 여기서 0 을 만들지 마세요. 못 읽은 것과 안 쓴 것은 다릅니다.
      return null;
    }
  }
}

/// 항상 `null` 을 돌려주는 구현. 테스트와 iOS 용입니다.
class NullAppUsageReader implements AppUsageReader {
  const NullAppUsageReader();

  @override
  Future<bool> hasPermission() async => false;

  @override
  Future<void> openSettings() async {}

  @override
  Future<AppUsage?> read({required DateTime from, required DateTime to}) async =>
      null;
}
