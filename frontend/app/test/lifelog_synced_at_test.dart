/// 최종 동기화 시각 — MAIN_LIFELOG_01 ❶
///
/// ```
/// ❶ 조회 기간 선택: 일·주·월 단위 전환 및 최종 동기화 시각 표시
/// ```
///
/// ## 왜 없었나
///
/// 기간 전환(일·주·월)만 있고 **「최종 동기화 시각 표시」가 빠져 있었습니다.**
/// 2026.08.06 화면 전수 대조에서 나왔습니다. `GET /devices/connections` 가
/// `last_synced_at` 을 이미 내려주고 모델(`DeviceConnection.lastSyncedAt`)도
/// 있었는데 **그리는 곳만 없었습니다.**
///
/// ## 왜 필요한가
///
/// 라이프로그가 비어 있을 때 **「데이터가 없는 것」인지 「동기화가 멈춘
/// 것」인지 사용자가 구분할 수 없습니다.** `NFR-DV-002` 는 3시간 미갱신을
/// 미수신으로 보는데, 그 사실이 사용자에게 닿는 화면이 여기밖에 없습니다.
///
/// ⚠ **경고색을 쓰지 않습니다.** 오래됐다고 빨강·주황을 쓰면 불안을
/// 키웁니다(정신건강 UI 규칙). 시간만 담담히 적습니다.
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:maeume_care/screens/lifelog_screen.dart';
import 'package:maeume_care/services/api_client.dart';
import 'package:maeume_care/services/lifelog_service.dart';
import 'package:maeume_care/services/settings_service.dart';
import 'package:maeume_care/services/token_storage.dart';
import 'package:maeume_care/theme/app_theme.dart';

ApiClient _client(Object connections, {int status = 200}) {
  final store = MemoryTokenStore();
  store.save(
    accessToken: 'test-token',
    expiresAt: DateTime.now().add(const Duration(hours: 1)),
  );
  final client = MockClient((request) async {
    final json = {'content-type': 'application/json; charset=utf-8'};
    if (request.url.path.endsWith('/devices/connections')) {
      return status == 200
          ? http.Response(jsonEncode(connections), 200, headers: json)
          : http.Response('{"detail":"실패"}', status, headers: json);
    }
    // 라이프로그 목록은 늘 한 건.
    // ⚠ 절대 날짜를 쓰지 않습니다 — 실행 시점에 따라 "N일 전"의 N이 바뀌고,
    // 우연히 다른 테스트의 검사 문자열(예: "3일 전")을 부분 문자열로 포함할
    // 수 있습니다(CLAUDE.md "시각 의존 테스트" 사례). 항상 "1일 전"으로
    // 고정되는 상대 날짜를 씁니다.
    return http.Response(
        jsonEncode([
          {
            'collected_at': DateTime.now()
                .subtract(const Duration(days: 1))
                .toUtc()
                .toIso8601String(),
            'steps': 8000,
            'total_sleep_min': 420,
          }
        ]),
        200,
        headers: json);
  });
  return ApiClient(tokenStore: store, httpClient: client);
}

Future<void> _pump(WidgetTester tester, ApiClient api) async {
  tester.view.physicalSize = const Size(411, 1600);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(MaterialApp(
    theme: AppTheme.light,
    home: Scaffold(
      body: LifelogScreen(
        lifelogService: LifelogService(apiClient: api),
        settingsService: SettingsService(apiClient: api),
      ),
    ),
  ));
  await tester.pumpAndSettle();
}

Map<String, dynamic> _conn(DateTime? at) => {
      'connection_id': '11111111-1111-1111-1111-111111111111',
      'platform_type': 'HEALTH_CONNECT',
      'permission_granted': true,
      'last_synced_at': at?.toUtc().toIso8601String(),
    };

void main() {
  group('❶ 최종 동기화 시각', () {
    testWidgets('방금 동기화했으면 분 단위로 보여준다', (tester) async {
      final at = DateTime.now().subtract(const Duration(minutes: 12));
      await _pump(tester, _client([_conn(at)]));
      expect(find.textContaining('최종 동기화'), findsOneWidget);
      expect(find.textContaining('12분 전'), findsOneWidget);
    });

    testWidgets('오래됐으면 시간 단위로 보여준다', (tester) async {
      // NFR-DV-002 가 미수신으로 보는 3시간을 넘긴 상태입니다.
      final at = DateTime.now().subtract(const Duration(hours: 5));
      await _pump(tester, _client([_conn(at)]));
      expect(find.textContaining('5시간 전'), findsOneWidget);
    });

    testWidgets('기기가 여러 대면 가장 최근 것을 쓴다', (tester) async {
      // 권한을 재승인하면 행이 쌓입니다. 옛 행을 쓰면 「멈춘 것」처럼 보입니다.
      final old = DateTime.now().subtract(const Duration(days: 3));
      final recent = DateTime.now().subtract(const Duration(minutes: 5));
      await _pump(tester, _client([_conn(old), _conn(recent)]));
      expect(find.textContaining('5분 전'), findsOneWidget);
      // 부분 문자열 매칭(textContaining)은 "23일 전" 같은 값에 우연히
      // 걸릴 수 있으므로 정확히 일치하는 경우만 검사합니다.
      expect(find.text('3일 전'), findsNothing);
    });

    testWidgets('한 번도 동기화한 적 없으면 줄을 그리지 않는다', (tester) async {
      // 「최종 동기화 —」 같은 빈 줄은 고장으로 읽힙니다.
      await _pump(tester, _client([_conn(null)]));
      expect(find.textContaining('최종 동기화'), findsNothing);
    });

    testWidgets('연동 조회가 실패해도 라이프로그는 그린다', (tester) async {
      // ⚠ 이 줄 하나 때문에 활동량·수면이 같이 사라지면 안 됩니다.
      await _pump(tester, _client([], status: 500));
      expect(find.textContaining('최종 동기화'), findsNothing);
      expect(find.text('일간'), findsOneWidget);
    });
  });
}
