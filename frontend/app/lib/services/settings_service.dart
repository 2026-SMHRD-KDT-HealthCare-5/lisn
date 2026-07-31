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
  Future<void> deleteAccount(String password) => _apiClient.delete(
        '/users/me',
        body: {'password': password},
        authenticated: true,
      );
}
