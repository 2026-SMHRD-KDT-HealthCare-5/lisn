/// 프로필 · 기기 연동 — MLCM_110 · MAIN_SETTING_01
library;

class UserProfile {
  const UserProfile({
    required this.userId,
    required this.email,
    required this.name,
    required this.personaType,
    required this.role,
    this.phone,
    this.heightCm,
    this.gender,
  });

  final String userId;
  final String email;
  final String name;

  /// ⚠ 서버에서 **복호화된 평문**으로 옵니다. DB 에는 AES-256-GCM 으로
  ///   암호화돼 있습니다(02-F 3항). 로그에 찍지 마세요.
  final String? phone;

  final double? heightCm;
  final String? gender;

  /// FRIEND / COUNSELOR
  final String personaType;

  /// USER / ADMIN
  final String role;

  static double? _num(dynamic v) => switch (v) {
        num n => n.toDouble(),
        String s => double.tryParse(s),
        _ => null,
      };

  factory UserProfile.fromJson(Map<String, dynamic> json) => UserProfile(
        userId: json['user_id'] as String? ?? '',
        email: json['email'] as String? ?? '',
        name: json['name'] as String? ?? '',
        phone: json['phone'] as String?,
        heightCm: _num(json['height_cm']),
        gender: json['gender'] as String?,
        personaType: json['persona_type'] as String? ?? 'FRIEND',
        role: json['role'] as String? ?? 'USER',
      );
}

/// 수집 항목 동의 범위.
///
/// `activity`·`sleep` 은 서비스 기본 동작에 필요하고, `bodyComposition` 은
/// 선택입니다. 필수를 false 로 내리는 것은 **연동 해제와 같습니다.**
class ConsentScopes {
  const ConsentScopes({
    this.activity = true,
    this.sleep = true,
    this.bodyComposition = false,
  });

  final bool activity;
  final bool sleep;
  final bool bodyComposition;

  factory ConsentScopes.fromJson(Map<String, dynamic> json) => ConsentScopes(
        activity: json['activity'] as bool? ?? true,
        sleep: json['sleep'] as bool? ?? true,
        bodyComposition: json['body_composition'] as bool? ?? false,
      );

  Map<String, dynamic> toJson() => {
        'activity': activity,
        'sleep': sleep,
        'body_composition': bodyComposition,
      };

  ConsentScopes copyWith({bool? activity, bool? sleep, bool? bodyComposition}) =>
      ConsentScopes(
        activity: activity ?? this.activity,
        sleep: sleep ?? this.sleep,
        bodyComposition: bodyComposition ?? this.bodyComposition,
      );
}

class DeviceConnection {
  const DeviceConnection({
    required this.connectionId,
    required this.platformType,
    required this.permissionGranted,
    required this.agreedAt,
    required this.consentScopes,
    this.deviceName,
    this.lastSyncedAt,
  });

  final String connectionId;
  final String? deviceName;

  /// HEALTH_CONNECT / APPLE_HEALTH.
  /// APPLE_HEALTH 는 구현 범위 밖이지만 enum 은 유지합니다(안건 2).
  final String platformType;

  /// ⚠ 기기 내 권한 승인 상태입니다. 서버가 가진 토큰이 아닙니다 —
  ///   Health Connect 는 on-device 권한 모델이라 서버에 토큰이 없습니다.
  final bool permissionGranted;

  final DateTime agreedAt;

  /// ⚠ **서버가 확정합니다.** 앱이 자기 시계로 갱신하면 단말 시간이 틀어졌을 때
  ///   그 구간이 영구 유실됩니다.
  final DateTime? lastSyncedAt;

  final ConsentScopes consentScopes;

  factory DeviceConnection.fromJson(Map<String, dynamic> json) =>
      DeviceConnection(
        connectionId: json['connection_id'] as String? ?? '',
        deviceName: json['device_name'] as String?,
        platformType: json['platform_type'] as String? ?? 'HEALTH_CONNECT',
        permissionGranted: json['permission_granted'] as bool? ?? false,
        agreedAt:
            DateTime.tryParse(json['agreed_at'] as String? ?? '')?.toLocal() ??
                DateTime.now(),
        lastSyncedAt:
            DateTime.tryParse(json['last_synced_at'] as String? ?? '')?.toLocal(),
        consentScopes: ConsentScopes.fromJson(
            (json['consent_scopes'] as Map<String, dynamic>?) ?? const {}),
      );
}
