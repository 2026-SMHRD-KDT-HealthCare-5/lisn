import 'api_client.dart';
import 'auth_service.dart';
import 'chat_service.dart';
import 'home_service.dart';
import 'lifelog_service.dart';
import 'report_service.dart';
import 'settings_service.dart';
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
}
