/// 한글 응답 인코딩 — 실제 서버 응답 모양으로 고정합니다 (2026.08.02 점검)
///
/// **지금은 정상입니다.** 다만 그 이유가 우연에 가까워 테스트로 묶어둡니다.
///
/// - 실제 FastAPI(Starlette)는 `content-type: application/json` 만 보내고
///   **charset 을 붙이지 않습니다.**
/// - Dart `http` 의 `Response.body` 는 charset 이 없으면 보통 **latin-1** 로
///   폴백하는데, `application/json` 일 때만 예외적으로 UTF-8 을 씁니다
///   (http 1.6 `response.dart` `_encodingForHeaders`). 여기에 기대고 있습니다.
///
/// ⚠ 다른 테스트들은 목 응답에 `charset=utf-8` 을 **직접 붙여** 두어서, 이
///   의존이 깨져도 알 수 없습니다. 여기서는 **charset 없이** 보냅니다.
library;

import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:maeume_care/models/auth_models.dart';
import 'package:maeume_care/services/api_client.dart';
import 'package:maeume_care/services/token_storage.dart';

/// 실제 FastAPI 응답 그대로. **charset 파라미터가 없습니다.**
///
/// Starlette 의 JSONResponse 는 `content-type: application/json` 만 붙이고
/// charset 을 명시하지 않습니다. 그런데 Dart `http` 의 `Response.body` 는
/// charset 이 없으면 **latin-1 로 폴백**합니다 — 한글이 그대로 깨집니다.
http.Response _fastApiError(int status, String detail) => http.Response.bytes(
      utf8.encode(jsonEncode({'detail': detail})),
      status,
      headers: {'content-type': 'application/json'},
    );

void main() {
  test('한글 오류 문구가 깨지지 않는다', () async {
    const message = '이메일 또는 비밀번호를 확인하세요';
    final client = MockClient((_) async => _fastApiError(401, message));
    final api = ApiClient(
      tokenStore: MemoryTokenStore(),
      httpClient: client,
      baseUrl: 'http://localhost:8000/api/v1',
    );

    await expectLater(
      api.post('/auth/login', body: const {'email': 'a@b.c', 'password': 'x'}),
      throwsA(
        isA<ApiException>()
            .having((e) => e.message, 'message', message)
            .having((e) => e.statusCode, 'statusCode', 401),
      ),
    );
  });

  test('정상 응답의 한글도 깨지지 않는다', () async {
    final client = MockClient(
      (_) async => http.Response.bytes(
        utf8.encode(jsonEncode({'greeting': '오늘 하루는 어떠셨어요?'})),
        200,
        headers: {'content-type': 'application/json'},
      ),
    );
    final api = ApiClient(
      tokenStore: MemoryTokenStore(),
      httpClient: client,
      baseUrl: 'http://localhost:8000/api/v1',
    );

    final body = await api.post('/chat/sessions');
    expect(body['greeting'], '오늘 하루는 어떠셨어요?');
  });

  test('JSON 이 아닌 오류 본문은 공통 문구로 떨어진다', () async {
    final client = MockClient(
      (_) async => http.Response.bytes(
        utf8.encode('<html>502 Bad Gateway</html>'),
        502,
        headers: {'content-type': 'text/html'},
      ),
    );
    final api = ApiClient(
      tokenStore: MemoryTokenStore(),
      httpClient: client,
      baseUrl: 'http://localhost:8000/api/v1',
    );

    await expectLater(
      api.get('/home'),
      throwsA(
          isA<ApiException>().having((e) => e.statusCode, 'statusCode', 502)),
    );
  });
}
