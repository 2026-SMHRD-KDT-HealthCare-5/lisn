import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config/api_config.dart';
import '../models/auth_models.dart';
import 'token_storage.dart';

typedef UnauthorizedHandler = FutureOr<void> Function();

class ApiClient {
  ApiClient({
    required TokenStore tokenStore,
    http.Client? httpClient,
    String? baseUrl,
  })  : _tokenStore = tokenStore,
        _httpClient = httpClient ?? http.Client(),
        _baseUri = Uri.parse(baseUrl ?? ApiConfig.baseUrl);

  final TokenStore _tokenStore;
  final http.Client _httpClient;
  final Uri _baseUri;

  UnauthorizedHandler? onUnauthorized;

  Future<Map<String, dynamic>> get(
    String path, {
    Map<String, String>? queryParameters,
    bool authenticated = false,
  }) async {
    return _send(
      'GET',
      path,
      queryParameters: queryParameters,
      authenticated: authenticated,
    );
  }

  Future<Map<String, dynamic>> post(
    String path, {
    Map<String, dynamic>? body,
    bool authenticated = false,
  }) async {
    return _send(
      'POST',
      path,
      body: body,
      authenticated: authenticated,
    );
  }

  Future<Map<String, dynamic>> _send(
    String method,
    String path, {
    Map<String, String>? queryParameters,
    Map<String, dynamic>? body,
    required bool authenticated,
  }) async {
    final normalizedPath = path.startsWith('/') ? path : '/$path';
    final uri = _baseUri.replace(
      path: '${_baseUri.path}$normalizedPath',
      queryParameters: queryParameters,
    );
    final headers = <String, String>{'Accept': 'application/json'};

    if (body != null) {
      headers['Content-Type'] = 'application/json';
    }

    if (authenticated) {
      final token = await _tokenStore.readAccessToken();
      if (token == null) {
        throw const ApiException('로그인이 필요합니다', statusCode: 401);
      }
      headers['Authorization'] = 'Bearer $token';
    }

    try {
      final request = http.Request(method, uri)
        ..headers.addAll(headers)
        ..body = body == null ? '' : jsonEncode(body);
      final streamed =
          await _httpClient.send(request).timeout(ApiConfig.requestTimeout);
      final response = await http.Response.fromStream(streamed);

      if (response.statusCode == 401 && authenticated) {
        await _tokenStore.clear();
        await onUnauthorized?.call();
      }

      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw ApiException(
          _readError(response.body),
          statusCode: response.statusCode,
        );
      }

      if (response.body.isEmpty) {
        return const {};
      }
      final decoded = jsonDecode(utf8.decode(response.bodyBytes));
      return decoded is Map<String, dynamic> ? decoded : const {};
    } on TimeoutException {
      throw const ApiException('서버 응답이 지연되고 있습니다. 잠시 후 다시 시도해주세요.');
    } on http.ClientException {
      throw const ApiException('서버에 연결할 수 없습니다. 네트워크 상태를 확인해주세요.');
    }
  }

  String _readError(String responseBody) {
    try {
      final decoded = jsonDecode(responseBody);
      if (decoded is Map<String, dynamic>) {
        final detail = decoded['detail'];
        if (detail is String) {
          return detail;
        }
        if (detail is List && detail.isNotEmpty) {
          final first = detail.first;
          if (first is Map<String, dynamic> && first['msg'] is String) {
            return first['msg'] as String;
          }
        }
      }
    } catch (_) {
      // JSON이 아닌 오류 응답은 공통 문구로 처리한다.
    }
    return '요청을 처리하지 못했습니다. 잠시 후 다시 시도해주세요.';
  }

  void close() => _httpClient.close();
}
