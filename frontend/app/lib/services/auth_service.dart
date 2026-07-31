import '../models/auth_models.dart';
import 'api_client.dart';
import 'token_storage.dart';

class AuthService {
  const AuthService({
    required ApiClient apiClient,
    required TokenStore tokenStore,
  })  : _apiClient = apiClient,
        _tokenStore = tokenStore;

  final ApiClient _apiClient;
  final TokenStore _tokenStore;

  Future<AuthSession> login({
    required String email,
    required String password,
  }) async {
    final json = await _apiClient.post(
      '/auth/login',
      body: {'email': email.trim(), 'password': password},
    );
    return _saveSession(AuthSession.fromJson(json));
  }

  Future<AuthSession> signup(SignupInput input) async {
    final json = await _apiClient.post('/auth/signup', body: input.toJson());
    return _saveSession(AuthSession.fromJson(json));
  }

  Future<bool> checkEmail(String email) async {
    final json = await _apiClient.get(
      '/auth/check-email',
      queryParameters: {'email': email.trim()},
    );
    return json['available'] as bool? ?? false;
  }

  Future<String> requestPasswordReset(String email) async {
    final json = await _apiClient.post(
      '/auth/password-reset/request',
      body: {'email': email.trim()},
    );
    return json['message'] as String? ?? '재설정 안내를 보냈습니다';
  }

  Future<void> confirmPasswordReset({
    required String token,
    required String newPassword,
  }) async {
    await _apiClient.post(
      '/auth/password-reset/confirm',
      body: {'token': token.trim(), 'new_password': newPassword},
    );
  }

  Future<void> logout() async {
    try {
      await _apiClient.post('/auth/logout', authenticated: true);
    } finally {
      await _tokenStore.clear();
    }
  }

  Future<AuthSession> _saveSession(AuthSession session) async {
    await _tokenStore.save(
      accessToken: session.accessToken,
      expiresAt: session.expiresAt,
    );
    return session;
  }
}
