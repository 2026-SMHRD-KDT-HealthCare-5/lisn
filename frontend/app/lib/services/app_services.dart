import 'api_client.dart';
import 'auth_service.dart';
import 'home_service.dart';
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
}
