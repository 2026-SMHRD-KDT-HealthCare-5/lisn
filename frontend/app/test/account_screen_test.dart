/// 계정 관리 화면 — MAIN_SETTING_02
///
/// ```
/// ❶ 계정 정보: 이메일, 이름, 가입일 표시
/// ❷ 비밀번호 변경: 현재 비밀번호 확인 후 변경
/// ❸ 회원 탈퇴: 탈퇴 절차 시작. 비밀번호 재입력 확인
/// ❹ 삭제 범위 안내: 라이프로그·체성분·대화·분석·기기
/// ❺ 최종 확인 후 탈퇴 처리, MAIN_LOGIN_01 복귀
/// ```
///
/// ## 왜 이 화면이 새로 생겼나
///
/// 슬라이드(`MAIN_SETTING_02`)는 있는데 **화면이 없었습니다.** 탈퇴 버튼만
/// 설정 「기타」 절에 있었고, 계정 정보 표시와 비밀번호 변경은 아예 없었습니다.
/// 서버 `PATCH /users/me/password` 는 이미 있었는데 **앱이 부르지 않았습니다.**
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:maeume_care/screens/account_screen.dart';
import 'package:maeume_care/services/api_client.dart';
import 'package:maeume_care/services/settings_service.dart';
import 'package:maeume_care/services/token_storage.dart';
import 'package:maeume_care/theme/app_theme.dart';

final _profile = <String, Object?>{
  'user_id': '019535f0-7c0a-7000-8000-000000000001',
  'email': 'maeum@example.com',
  'name': '김마음',
  'phone': null,
  'height_cm': null,
  'gender': null,
  'persona_type': 'FRIEND',
  'role': 'USER',
  'terms_agreed_at': '2026-07-17T02:30:00Z',
};

class _Server {
  final requests = <http.BaseRequest>[];
  final bodies = <String>[];
  int status = 204;
  String error = '{"detail":"현재 비밀번호가 올바르지 않습니다"}';

  SettingsService build() {
    final store = MemoryTokenStore();
    store.save(
      accessToken: 'test-token',
      expiresAt: DateTime.now().add(const Duration(hours: 1)),
    );
    final client = MockClient((request) async {
      requests.add(request);
      bodies.add(request.body);
      if (request.url.path.endsWith('/users/me/password')) {
        return status == 204
            ? http.Response('', 204)
            : http.Response(error, status,
                headers: {'content-type': 'application/json; charset=utf-8'});
      }
      return http.Response(jsonEncode(_profile), 200,
          headers: {'content-type': 'application/json; charset=utf-8'});
    });
    return SettingsService(
        apiClient: ApiClient(tokenStore: store, httpClient: client));
  }
}

Future<void> _pump(WidgetTester tester, SettingsService service) async {
  tester.view.physicalSize = const Size(411, 900);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(MaterialApp(
    theme: AppTheme.light,
    home: AccountScreen(settingsService: service),
  ));
  await tester.pump(const Duration(milliseconds: 300));
}

void main() {
  group('❶ 계정 정보', () {
    testWidgets('이름·이메일·가입일을 보여준다', (tester) async {
      await _pump(tester, _Server().build());
      expect(find.text('김마음'), findsOneWidget);
      expect(find.text('maeum@example.com'), findsOneWidget);
      // ⚠ USERS 에 created_at 이 없어 약관 동의 시각을 씁니다.
      //   KST 로 바뀌므로 UTC 2026-07-17 02:30 → 07-17 11:30 (같은 날)
      expect(find.text('2026. 07. 17'), findsOneWidget);
    });

    testWidgets('가입일이 없어도 깨지지 않는다', (tester) async {
      final s = _Server();
      _profile['terms_agreed_at'] = null;
      await _pump(tester, s.build());
      expect(find.text('–'), findsOneWidget);
      _profile['terms_agreed_at'] = '2026-07-17T02:30:00Z';
    });
  });

  group('❷ 비밀번호 변경', () {
    testWidgets('현재·새·확인 세 칸을 받는다', (tester) async {
      await _pump(tester, _Server().build());
      await tester.tap(find.text('비밀번호 변경'));
      await tester.pumpAndSettle();
      expect(find.text('현재 비밀번호'), findsOneWidget);
      expect(find.text('새 비밀번호 (8자 이상)'), findsOneWidget);
      expect(find.text('새 비밀번호 확인'), findsOneWidget);
    });

    testWidgets('새 비밀번호가 서로 다르면 보내지 않는다', (tester) async {
      final s = _Server();
      await _pump(tester, s.build());
      await tester.tap(find.text('비밀번호 변경'));
      await tester.pumpAndSettle();

      await tester.enterText(find.widgetWithText(TextFormField, '현재 비밀번호'), 'old-password');
      await tester.enterText(
          find.widgetWithText(TextFormField, '새 비밀번호 (8자 이상)'), 'new-password');
      await tester.enterText(
          find.widgetWithText(TextFormField, '새 비밀번호 확인'), 'different-one');
      await tester.tap(find.text('변경하기'));
      await tester.pumpAndSettle();

      expect(find.text('새 비밀번호가 서로 다릅니다'), findsOneWidget);
      expect(s.requests.any((r) => r.url.path.endsWith('/users/me/password')),
          isFalse, reason: '검증 실패인데 서버로 나갔습니다');
    });

    testWidgets('8자 미만은 보내지 않는다', (tester) async {
      // 서버도 min_length=8 을 검증합니다. 여기서 먼저 걸러 왕복을 줄입니다.
      final s = _Server();
      await _pump(tester, s.build());
      await tester.tap(find.text('비밀번호 변경'));
      await tester.pumpAndSettle();
      await tester.enterText(find.widgetWithText(TextFormField, '현재 비밀번호'), 'old-password');
      await tester.enterText(
          find.widgetWithText(TextFormField, '새 비밀번호 (8자 이상)'), 'short');
      await tester.enterText(find.widgetWithText(TextFormField, '새 비밀번호 확인'), 'short');
      await tester.tap(find.text('변경하기'));
      await tester.pumpAndSettle();

      expect(find.text('8자 이상 입력해주세요'), findsOneWidget);
      expect(s.requests.any((r) => r.url.path.endsWith('/users/me/password')),
          isFalse);
    });

    testWidgets('제대로 채우면 현재·새 비밀번호를 함께 보낸다', (tester) async {
      final s = _Server();
      await _pump(tester, s.build());
      await tester.tap(find.text('비밀번호 변경'));
      await tester.pumpAndSettle();
      await tester.enterText(find.widgetWithText(TextFormField, '현재 비밀번호'), 'old-password');
      await tester.enterText(
          find.widgetWithText(TextFormField, '새 비밀번호 (8자 이상)'), 'new-password');
      await tester.enterText(
          find.widgetWithText(TextFormField, '새 비밀번호 확인'), 'new-password');
      await tester.tap(find.text('변경하기'));
      await tester.pumpAndSettle();

      final sent = s.bodies.last;
      // ⚠ 현재 비밀번호를 빠뜨리면 서버가 본인 확인을 못 합니다.
      expect(jsonDecode(sent), {
        'current_password': 'old-password',
        'new_password': 'new-password',
      });
    });

    testWidgets('현재 비밀번호가 틀리면 서버 문구를 그대로 보여준다', (tester) async {
      final s = _Server()..status = 400;
      await _pump(tester, s.build());
      await tester.tap(find.text('비밀번호 변경'));
      await tester.pumpAndSettle();
      await tester.enterText(find.widgetWithText(TextFormField, '현재 비밀번호'), 'wrong-password');
      await tester.enterText(
          find.widgetWithText(TextFormField, '새 비밀번호 (8자 이상)'), 'new-password');
      await tester.enterText(
          find.widgetWithText(TextFormField, '새 비밀번호 확인'), 'new-password');
      await tester.tap(find.text('변경하기'));
      await tester.pumpAndSettle();

      expect(find.text('현재 비밀번호가 올바르지 않습니다'), findsOneWidget);
    });
  });

  group('❸❹ 회원 탈퇴', () {
    testWidgets('비밀번호를 다시 받는다 — MLCM_103 2단계', (tester) async {
      await _pump(tester, _Server().build());
      await tester.tap(find.text('회원 탈퇴'));
      await tester.pumpAndSettle();
      expect(find.text('정말 탈퇴하시겠어요?'), findsOneWidget);
      expect(find.text('본인 확인을 위해 비밀번호를 입력해주세요'), findsOneWidget);
    });

    testWidgets('비밀번호를 비우면 요청하지 않는다', (tester) async {
      final s = _Server();
      await _pump(tester, s.build());
      await tester.tap(find.text('회원 탈퇴'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('탈퇴하기'));
      await tester.pumpAndSettle();

      expect(s.requests.any((r) => r.method == 'DELETE'), isFalse);
    });

    testWidgets('삭제 범위를 화면에 미리 알린다 — MLCM_103 3단계', (tester) async {
      // ⚠ 팝업을 열기 전에도 보여야 합니다. 「누르면 알려주겠다」로는
      //   무엇이 지워지는지 모른 채 버튼을 누르게 됩니다.
      await _pump(tester, _Server().build());
      expect(find.textContaining('라이프로그'), findsWidgets);
      expect(find.textContaining('체성분'), findsWidgets);
      expect(find.text('되돌릴 수 없어요.'), findsOneWidget);
    });
  });

  testWidgets('⚠ 경고색을 쓰지 않는다', (tester) async {
    // 탈퇴는 위기 화면은 아니지만 같은 계열의 판단입니다. 빨간 박스는 겁을
    // 줄 뿐이고, 필요한 건 무엇이 지워지는지 정확히 아는 것입니다.
    await _pump(tester, _Server().build());
    final texts = tester.widgetList<Text>(find.byType(Text));
    for (final t in texts) {
      final c = t.style?.color;
      if (c == null) continue;
      final isWarning = c.r > 0.7 && c.g < 0.45 && c.b < 0.4;
      expect(isWarning, isFalse, reason: '경고색 문구: "${t.data}"');
    }
  });
}
