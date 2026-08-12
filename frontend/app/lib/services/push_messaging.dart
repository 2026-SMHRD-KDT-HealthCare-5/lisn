/// FCM 토큰 발급·등록 — `MLCM_220` 4단계 · `MLCM_400` 5단계 · `NFR-DV-002`
///
/// **플랫폼(Firebase)에 닿는 유일한 파일입니다.** 등록 로직([PushRegistrar])은
/// [PushTokenSource] 만 보므로 실기기·Firebase 없이 테스트됩니다.
/// `health_reader.dart` 와 같은 구조입니다.
///
/// ## 왜 앱이 토큰을 보내야 하나
///
/// 서버는 사용자 폰에 직접 연결할 수 없습니다. 구글 FCM 서버를 거쳐야 하고,
/// 그때 **어느 기기로 보낼지**를 가리키는 것이 이 토큰입니다. 토큰을 만들 수
/// 있는 쪽은 앱뿐이라, 앱이 받아서 서버에 올려줘야 합니다.
///
/// 저장 창구는 이미 있습니다 — `PATCH /users/me/notifications` (`users.py`).
/// **넣을 것이 없었을 뿐입니다.**
///
/// ⚠ **알림을 거부해도 앱은 정상 동작해야 합니다.** 선제 접촉 세션은 서버에
///   선생성돼 있어 앱을 열면 보입니다(`MLCM_220` 6단계). 푸시는 「앱을 안 여는
///   사람에게 닿는 경로」를 더하는 것이지 유일한 경로가 아닙니다.
library;

import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';

import 'settings_service.dart';

/// 등록 로직이 보는 인터페이스. 테스트는 이걸 가짜로 구현합니다.
abstract class PushTokenSource {
  /// 알림 권한을 요청하고 허용됐는지 돌려줍니다.
  ///
  /// Android 13(API 33)부터 런타임 권한입니다. 그 아래는 항상 허용입니다.
  Future<bool> requestPermission();

  /// 이 기기의 FCM 토큰. 못 받으면 null.
  Future<String?> token();

  /// 토큰이 갱신될 때 새 값을 흘립니다.
  ///
  /// ⚠ **토큰은 고정값이 아닙니다.** 앱 재설치·데이터 삭제·장기 미사용이면
  ///   구글이 새로 발급합니다. 갱신을 안 올리면 **그 사용자에게는 그날부터
  ///   푸시가 조용히 안 갑니다.** 실패가 눈에 안 보이는 종류라 위험합니다.
  Stream<String> onTokenRefresh();
}

/// 실제 Firebase 구현.
class FirebasePushTokenSource implements PushTokenSource {
  FirebasePushTokenSource({FirebaseMessaging? messaging})
      : _override = messaging;

  final FirebaseMessaging? _override;

  /// ⚠ **생성자에서 만지지 않습니다.** `FirebaseMessaging.instance` 는 초기화
  ///   전에 접근하면 `[core/no-app]` 을 던집니다. 생성자에 두면
  ///   `AppServices.push` 를 **읽는 순간** 터지므로, `initializePush()` 가
  ///   초기화 실패를 삼켜도 소용이 없습니다 — 실제로 `MainShell` 진입이
  ///   통째로 깨졌습니다(위젯 테스트가 잡았습니다).
  ///
  ///   여기서 늦게 잡으면 호출은 전부 `PushRegistrar.register()` 의 try 안이라
  ///   **푸시만 죽고 앱은 뜹니다.** `google-services.json` 이 없는 팀원 PC 가
  ///   이 경우입니다.
  FirebaseMessaging get _messaging => _override ?? FirebaseMessaging.instance;

  @override
  Future<bool> requestPermission() async {
    final settings = await _messaging.requestPermission();
    return settings.authorizationStatus == AuthorizationStatus.authorized ||
        settings.authorizationStatus == AuthorizationStatus.provisional;
  }

  @override
  Future<String?> token() => _messaging.getToken();

  @override
  Stream<String> onTokenRefresh() => _messaging.onTokenRefresh;
}

/// 토큰을 받아 서버에 등록합니다.
class PushRegistrar {
  PushRegistrar({
    required PushTokenSource source,
    required SettingsService settings,
  })  : _source = source,
        _settings = settings;

  final PushTokenSource _source;
  final SettingsService _settings;

  StreamSubscription<String>? _refreshSub;
  String? _lastSent;

  /// 마지막으로 서버에 올린 토큰. 테스트·디버깅용입니다.
  @visibleForTesting
  String? get lastSent => _lastSent;

  /// 권한을 묻고 토큰을 등록합니다. **로그인 뒤에 부르세요.**
  ///
  /// 토큰은 사용자에게 매다는 값이라 인증이 없으면 저장할 곳이 없습니다.
  ///
  /// 반환값은 등록에 성공했는지입니다. **실패해도 던지지 않습니다** — 푸시가
  /// 없다고 앱이 멈추면 안 됩니다.
  Future<bool> register() async {
    try {
      if (!await _source.requestPermission()) {
        debugPrint('[푸시] 알림 권한 거부됨 — 등록을 건너뜁니다');
        return false;
      }
      final token = await _source.token();
      if (token == null || token.isEmpty) {
        debugPrint('[푸시] 토큰을 받지 못했습니다');
        return false;
      }
      await _send(token);
      _listenRefresh();
      return true;
    } catch (e) {
      // Firebase 초기화 실패(google-services.json 누락 등)도 여기로 옵니다.
      debugPrint('[푸시] 등록 실패: $e');
      return false;
    }
  }

  void _listenRefresh() {
    // 중복 구독을 막습니다. register() 를 두 번 불러도 안전해야 합니다.
    _refreshSub?.cancel();
    _refreshSub = _source.onTokenRefresh().listen(
      (t) async {
        try {
          await _send(t);
        } catch (e) {
          debugPrint('[푸시] 갱신 토큰 전송 실패: $e');
        }
      },
      onError: (Object e) => debugPrint('[푸시] 갱신 스트림 오류: $e'),
    );
  }

  Future<void> _send(String token) async {
    // 같은 값을 다시 올리지 않습니다. 앱을 켤 때마다 PATCH 가 나가면
    // 서버 로그가 의미 없는 쓰기로 찹니다.
    if (token == _lastSent) return;
    await _settings.updateNotifications(fcmToken: token);
    _lastSent = token;
  }

  /// 로그아웃 시 서버에서 토큰을 지웁니다.
  ///
  /// ⚠ **안 지우면 다음 사용자에게 갈 알림이 이전 사용자 폰으로 갑니다.**
  ///   공용 기기가 아니어도, 계정을 바꿔 로그인하면 그대로 남습니다.
  ///
  /// ⚠ 빈 문자열을 보냅니다. null 은 서버에서 「안 바꿈」입니다(`users.py`).
  Future<void> unregister() async {
    await _refreshSub?.cancel();
    _refreshSub = null;
    _lastSent = null;
    try {
      await _settings.updateNotifications(fcmToken: '');
    } catch (e) {
      debugPrint('[푸시] 토큰 해제 실패: $e');
    }
  }
}

/// Firebase 를 초기화합니다. `main()` 에서 한 번만 부릅니다.
///
/// ⚠ **실패해도 던지지 않습니다.** `google-services.json` 이 없는 PC 에서
///   앱 전체가 안 뜨면 원인을 찾기 어렵습니다. 푸시만 죽고 나머지는 돕니다.
Future<bool> initializePush() async {
  try {
    await Firebase.initializeApp();
    return true;
  } catch (e) {
    debugPrint('[푸시] Firebase 초기화 실패 — 푸시 없이 계속합니다: $e');
    return false;
  }
}
