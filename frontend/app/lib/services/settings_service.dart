import '../models/settings_models.dart';
import 'api_client.dart';

/// 프로필 · 기기 연동 — MAIN_SETTING_01 · MLCM_110
class SettingsService {
  const SettingsService({required ApiClient apiClient})
      : _apiClient = apiClient;

  final ApiClient _apiClient;

  Future<UserProfile> profile() async {
    final json = await _apiClient.get('/users/me', authenticated: true);
    return UserProfile.fromJson(json);
  }

  /// 프로필 수정. 보낸 필드만 바뀝니다.
  Future<UserProfile> updateProfile({
    String? name,
    String? phone,
    double? heightCm,
    String? personaType,
  }) async {
    final json = await _apiClient.patch(
      '/users/me',
      body: {
        if (name != null) 'name': name,
        if (phone != null) 'phone': phone,
        if (heightCm != null) 'height_cm': heightCm,
        if (personaType != null) 'persona_type': personaType,
      },
      authenticated: true,
    );
    return UserProfile.fromJson(json);
  }

  /// 기기 연동 등록 — MLCM_110
  ///
  /// ⚠ `permissionGranted` 는 **기기 내 권한 승인 상태**입니다. 서버가 가진
  ///   토큰이 아닙니다. Health Connect 는 on-device 권한 모델이라 앱이
  ///   사용자에게 권한을 받아야 하고, 그 전까지는 false 로 등록합니다.
  Future<DeviceConnection> createConnection({
    String? deviceName,
    bool permissionGranted = false,
  }) async {
    final json = await _apiClient.post(
      '/devices/connections',
      body: {
        if (deviceName != null) 'device_name': deviceName,
        'platform_type': 'HEALTH_CONNECT',
        'permission_granted': permissionGranted,
      },
      authenticated: true,
    );
    return DeviceConnection.fromJson(json);
  }

  Future<List<DeviceConnection>> connections() async {
    final rows =
        await _apiClient.getList('/devices/connections', authenticated: true);
    return rows.map(DeviceConnection.fromJson).toList();
  }

  /// 동의 철회·권한 상태 갱신.
  ///
  /// ⚠ **기존에 수집된 데이터는 지워지지 않습니다**(MLCM_110 종료조건).
  ///   화면에서 "연동을 끄면 지금까지 기록이 사라진다"고 오해하게 두면 안 됩니다.
  Future<DeviceConnection> updateConnection(
    String connectionId, {
    bool? permissionGranted,
    ConsentScopes? consentScopes,
  }) async {
    final json = await _apiClient.patch(
      '/devices/connections/$connectionId',
      body: {
        if (permissionGranted != null) 'permission_granted': permissionGranted,
        if (consentScopes != null) 'consent_scopes': consentScopes.toJson(),
      },
      authenticated: true,
    );
    return DeviceConnection.fromJson(json);
  }

  /// 회원 탈퇴 — MLCM_103.
  ///
  /// USERS row 삭제 → CASCADE 로 연관 데이터가 전부 지워집니다. 되돌릴 수 없습니다.
  ///
  /// ⚠ **비밀번호 재확인이 필수입니다**(MLCM_103 2단계 본인 확인).
  ///   서버가 본문 없이 오는 요청을 422 로 거절합니다.
  /// 비밀번호 변경 — `MAIN_SETTING_02` ❷ · `MLCM_101`
  ///
  /// 서버가 현재 비밀번호를 검증합니다. 틀리면 `ApiException` 이 납니다.
  /// 알림 수신 동의 조회 — `MAIN_SETTING_01` ❷
  Future<NotificationSettings> notifications() async {
    final json =
        await _apiClient.get('/users/me/notifications', authenticated: true);
    return NotificationSettings.fromJson(json);
  }

  /// 알림 수신 동의 저장. **보낸 것만 바뀝니다.**
  ///
  /// ⚠ 토큰을 지우려면 빈 문자열을 넘기세요. null 은 「안 바꿈」입니다.
  Future<NotificationSettings> updateNotifications({
    bool? careAlert,
    bool? contentAlert,
    String? fcmToken,
  }) async {
    final json = await _apiClient.patch(
      '/users/me/notifications',
      body: {
        if (careAlert != null) 'care_alert_agreed': careAlert,
        if (contentAlert != null) 'content_alert_agreed': contentAlert,
        if (fcmToken != null) 'fcm_token': fcmToken,
      },
      authenticated: true,
    );
    return NotificationSettings.fromJson(json);
  }

  Future<void> changePassword({
    required String currentPassword,
    required String newPassword,
  }) =>
      _apiClient.patch(
        '/users/me/password',
        body: {
          'current_password': currentPassword,
          'new_password': newPassword,
        },
        authenticated: true,
      );

  Future<void> deleteAccount(String password) => _apiClient.delete(
        '/users/me',
        body: {'password': password},
        authenticated: true,
      );
}
