import 'api_client.dart';
import 'auth_service.dart';
import 'chat_service.dart';
import 'health_reader.dart';
import 'home_service.dart';
import 'lifelog_service.dart';
import 'lifelog_sync.dart';
import 'push_messaging.dart';
import 'report_service.dart';
import 'settings_service.dart';
import 'sync_store.dart';
import 'token_storage.dart';

class AppServices {
  AppServices._();

  static final TokenStore tokenStore = SecureTokenStore();
  static final ApiClient apiClient = ApiClient(tokenStore: tokenStore);
  static final AuthService auth = AuthService(
    apiClient: apiClient,
    tokenStore: tokenStore,
  );
  static final HomeService home = HomeService(apiClient: apiClient);
  static final ChatService chat = ChatService(apiClient: apiClient);
  static final LifelogService lifelog =
      LifelogService(apiClient: apiClient);
  static final ReportService report = ReportService(apiClient: apiClient);
  static final SettingsService settings =
      SettingsService(apiClient: apiClient);

  /// Health Connect 읽기 — MLCM_200
  static final HealthReader healthReader = HealthConnectReader();

  /// FCM 토큰 등록 — MLCM_220 4단계.
  ///
  /// ⚠ **로그인 뒤에 `register()` 를 부릅니다.** 토큰은 사용자에게 매다는
  ///   값이라 인증이 없으면 저장할 곳이 없습니다. 호출 지점은 `MainShell`
  ///   입니다 — 새로 로그인하든 자동 로그인이든 거기를 지나갑니다.
  static final PushRegistrar push = PushRegistrar(
    source: FirebasePushTokenSource(),
    settings: settings,
  );

  /// 라이프로그 동기화. 화면에서 즉시 당길 때 씁니다.
  ///
  /// ⚠ **백그라운드 워커는 이걸 쓰지 않습니다.** 다른 아이솔레이트라 이
  ///   static 필드가 비어 있습니다. 워커는 `buildSyncService()` 로 따로
  ///   조립합니다(sync_worker.dart).
  static final LifelogSyncService lifelogSync = LifelogSyncService(
    reader: healthReader,
    store: PrefsSyncStore(),
    lifelogService: lifelog,
  );
}
