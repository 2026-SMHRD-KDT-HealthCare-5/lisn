import 'package:flutter_secure_storage/flutter_secure_storage.dart';

abstract interface class TokenStore {
  Future<void> save({
    required String accessToken,
    required DateTime expiresAt,
  });

  Future<String?> readAccessToken();

  Future<bool> hasValidSession();

  Future<void> clear();
}

class SecureTokenStore implements TokenStore {
  SecureTokenStore({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  static const _accessTokenKey = 'access_token';
  static const _expiresAtKey = 'access_token_expires_at';

  final FlutterSecureStorage _storage;

  @override
  Future<void> save({
    required String accessToken,
    required DateTime expiresAt,
  }) async {
    await Future.wait([
      _storage.write(key: _accessTokenKey, value: accessToken),
      _storage.write(
        key: _expiresAtKey,
        value: expiresAt.toUtc().toIso8601String(),
      ),
    ]);
  }

  @override
  Future<String?> readAccessToken() => _storage.read(key: _accessTokenKey);

  @override
  Future<bool> hasValidSession() async {
    try {
      final values = await Future.wait([
        _storage.read(key: _accessTokenKey),
        _storage.read(key: _expiresAtKey),
      ]);
      final expiresAt = DateTime.tryParse(values[1] ?? '');
      if (values[0] == null || expiresAt == null) {
        return false;
      }
      if (!expiresAt.toUtc().isAfter(DateTime.now().toUtc())) {
        await clear();
        return false;
      }
      return true;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<void> clear() async {
    await Future.wait([
      _storage.delete(key: _accessTokenKey),
      _storage.delete(key: _expiresAtKey),
    ]);
  }
}

class MemoryTokenStore implements TokenStore {
  String? _accessToken;
  DateTime? _expiresAt;

  @override
  Future<void> save({
    required String accessToken,
    required DateTime expiresAt,
  }) async {
    _accessToken = accessToken;
    _expiresAt = expiresAt.toUtc();
  }

  @override
  Future<String?> readAccessToken() async => _accessToken;

  @override
  Future<bool> hasValidSession() async {
    return _accessToken != null &&
        _expiresAt != null &&
        _expiresAt!.isAfter(DateTime.now().toUtc());
  }

  @override
  Future<void> clear() async {
    _accessToken = null;
    _expiresAt = null;
  }
}
