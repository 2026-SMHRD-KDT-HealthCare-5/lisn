/// 프로필 · 기기 연동 — MLCM_110 · MAIN_SETTING_01
library;

import 'json.dart';

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
    this.joinedAt,
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

  /// 가입 시각 — `MAIN_SETTING_02` ❶ 「가입일」.
  ///
  /// ⚠ **`USERS` 에 `created_at` 컬럼이 없습니다.** 대신 필수 약관 동의 시각을
  ///   씁니다. 약관 동의 없이는 가입이 성립하지 않고(`chk_terms_logic`),
  ///   가입 처리에서 같은 `now` 로 함께 기록됩니다.
  ///
  ///   컬럼을 새로 만들지 않은 이유는 `db/schema.sql` 이 정본이라 04·05 문서까지
  ///   같이 고쳐야 하기 때문입니다. 표시용 한 칸 때문에 치를 값이 아닙니다.
  final DateTime? joinedAt;

  factory UserProfile.fromJson(Map<String, dynamic> json) => UserProfile(
        userId: jsonStr(json['user_id']),
        email: jsonStr(json['email']),
        name: jsonStr(json['name']),
        phone: json['phone'] as String?,
        heightCm: jsonNum(json['height_cm']),
        gender: json['gender'] as String?,
        personaType: jsonStr(json['persona_type'], 'FRIEND'),
        role: jsonStr(json['role'], 'USER'),
        joinedAt: json['terms_agreed_at'] is String
            ? DateTime.tryParse(json['terms_agreed_at'] as String)?.toLocal()
            : null,
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
        activity: jsonBool(json['activity'], true),
        sleep: jsonBool(json['sleep'], true),
        bodyComposition: jsonBool(json['body_composition']),
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
        connectionId: jsonStr(json['connection_id']),
        deviceName: json['device_name'] as String?,
        platformType: jsonStr(json['platform_type'], 'HEALTH_CONNECT'),
        permissionGranted: jsonBool(json['permission_granted']),
        agreedAt:
            jsonAt(json['agreed_at']) ??
                DateTime.now(),
        lastSyncedAt:
            jsonAt(json['last_synced_at']),
        consentScopes: ConsentScopes.fromJson(
            jsonObj(json['consent_scopes'])),
      );
}
