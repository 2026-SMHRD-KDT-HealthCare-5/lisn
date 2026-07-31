import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:maeume_care/models/auth_models.dart';
import 'package:maeume_care/services/api_client.dart';
import 'package:maeume_care/services/auth_service.dart';
import 'package:maeume_care/services/token_storage.dart';

void main() {
  test('로그인 응답을 파싱하고 토큰을 저장한다', () async {
    final tokenStore = MemoryTokenStore();
    final client = MockClient((request) async {
      expect(request.url.path, '/api/v1/auth/login');
      expect(
        jsonDecode(request.body),
        {'email': 'user@example.com', 'password': 'password123'},
      );
      return http.Response(
        jsonEncode({
          'access_token': 'test-token',
          'expires_at': '2099-01-01T00:00:00Z',
          'user': {
            'user_id': '019535f0-7c0a-7000-8000-000000000001',
            'email': 'user@example.com',
            'name': '테스트',
            'role': 'USER',
            'persona_type': 'FRIEND',
          },
        }),
        200,
        headers: {'content-type': 'application/json; charset=utf-8'},
      );
    });
    final apiClient = ApiClient(
      tokenStore: tokenStore,
      httpClient: client,
      baseUrl: 'http://localhost:8000/api/v1',
    );
    final service = AuthService(
      apiClient: apiClient,
      tokenStore: tokenStore,
    );

    final session = await service.login(
      email: 'user@example.com',
      password: 'password123',
    );

    expect(session.user.name, '테스트');
    expect(await tokenStore.readAccessToken(), 'test-token');
    expect(await tokenStore.hasValidSession(), isTrue);
  });

  test('FastAPI detail 오류를 사용자 메시지로 전달한다', () async {
    final tokenStore = MemoryTokenStore();
    final client = MockClient(
      (_) async => http.Response(
        jsonEncode({'detail': '이메일 또는 비밀번호를 확인하세요'}),
        401,
        headers: {'content-type': 'application/json; charset=utf-8'},
      ),
    );
    final service = AuthService(
      apiClient: ApiClient(
        tokenStore: tokenStore,
        httpClient: client,
        baseUrl: 'http://localhost:8000/api/v1',
      ),
      tokenStore: tokenStore,
    );

    expect(
      () => service.login(
        email: 'user@example.com',
        password: 'incorrect',
      ),
      throwsA(
        isA<ApiException>().having(
          (error) => error.message,
          'message',
          '이메일 또는 비밀번호를 확인하세요',
        ),
      ),
    );
  });
}
