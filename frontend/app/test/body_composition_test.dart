/// 체성분 기록 — MAIN_LIFELOG_01 ❺
///
/// ```
/// ❺ 체성분 기록: 체중·체지방·근육량·기초대사량 측정 이력
/// ```
///
/// ## 왜 없었나
///
/// 서버 `GET /body-composition` 도 `LifelogService.fetchBodyComposition()` 도
/// 있었는데 **부르는 화면이 없었습니다.** `MAIN_JOIN_03`·`MAIN_SETTING_01` 이
/// 체성분 수집 동의를 받고 있는데 받은 데이터를 볼 곳이 없었습니다.
///
/// ## 체성분은 선택 항목입니다
///
/// 동의하지 않았거나 체성분계가 없으면 **평생 비어 있는 게 정상**입니다.
/// 비어 있음을 오류처럼 그리면 멀쩡한 앱이 고장난 것처럼 보입니다.
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:maeume_care/screens/lifelog_screen.dart';
import 'package:maeume_care/services/api_client.dart';
import 'package:maeume_care/services/lifelog_service.dart';
import 'package:maeume_care/services/token_storage.dart';
import 'package:maeume_care/theme/app_theme.dart';

/// 활동량·수면은 항상 한 건 내려주고, 체성분만 시험 대상으로 바꿉니다.
LifelogService _service({
  required Object bodyRows,
  int bodyStatus = 200,
}) {
  final store = MemoryTokenStore();
  store.save(
    accessToken: 'test-token',
    expiresAt: DateTime.now().add(const Duration(hours: 1)),
  );
  final client = MockClient((request) async {
    final json = {'content-type': 'application/json; charset=utf-8'};
    if (request.url.path.endsWith('/body-composition')) {
      return bodyStatus == 200
          ? http.Response(jsonEncode(bodyRows), 200, headers: json)
          : http.Response('{"detail":"실패"}', bodyStatus, headers: json);
    }
    return http.Response(
        jsonEncode([
          {
            'collected_at': '2026-08-02T00:00:00Z',
            'steps': 8000,
            'total_sleep_min': 420,
            'heart_rate': 68,
          }
        ]),
        200,
        headers: json);
  });
  return LifelogService(
      apiClient: ApiClient(tokenStore: store, httpClient: client));
}

Future<void> _pump(WidgetTester tester, LifelogService service) async {
  tester.view.physicalSize = const Size(411, 1600);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(MaterialApp(
    theme: AppTheme.light,
    home: Scaffold(body: LifelogScreen(lifelogService: service)),
  ));
  await tester.pumpAndSettle();
}

/// ⚠ 체성분 절은 `ListView` **맨 아래**에 있습니다. ListView 는 화면 밖 항목을
///   만들지 않으므로 그냥 찾으면 0건입니다. 스크롤해서 만들어지게 합니다.
Future<void> _scrollToBody(WidgetTester tester) async {
  await tester.scrollUntilVisible(
    find.text('체성분 기록'),
    300,
    scrollable: find.byType(Scrollable).first,
  );
  await tester.pumpAndSettle();
}

final _rows = [
  {
    'measured_at': '2026-08-02T09:00:00Z',
    'weight_kg': 63.4,
    'body_fat_kg': 15.2,
    'muscle_mass_kg': 45.1,
    'bmr_kcal': 1420,
  },
  {
    'measured_at': '2026-07-26T09:00:00Z',
    'weight_kg': 64.1,
    'body_fat_kg': 15.8,
    'muscle_mass_kg': 44.9,
    'bmr_kcal': 1415,
  },
];

void main() {
  group('❺ 체성분 기록', () {
    testWidgets('네 지표를 모두 보여준다', (tester) async {
      await _pump(tester, _service(bodyRows: _rows));
      await _scrollToBody(tester);
      expect(find.text('체성분 기록'), findsOneWidget);
      // 화면설명이 규정한 네 가지입니다.
      expect(find.text('체중'), findsOneWidget);
      expect(find.text('체지방'), findsOneWidget);
      expect(find.text('근육량'), findsOneWidget);
      expect(find.text('기초대사량'), findsOneWidget);
    });

    testWidgets('가장 최근 측정치를 쓴다', (tester) async {
      // 서버는 최신순으로 내려줍니다. 뒤엣것을 쓰면 지난주 값이 뜹니다.
      await _pump(tester, _service(bodyRows: _rows));
      await _scrollToBody(tester);
      expect(find.text('63.4 kg'), findsWidgets);
      expect(find.text('15.2 kg'), findsOneWidget);
      expect(find.text('1,420 kcal'), findsOneWidget);
    });

    testWidgets('측정 이력을 여러 건 보여준다', (tester) async {
      // 「측정 이력」이라 최신 한 건만으로는 변화를 알 수 없습니다.
      await _pump(tester, _service(bodyRows: _rows));
      await _scrollToBody(tester);
      expect(find.text('64.1 kg'), findsOneWidget, reason: '지난 측정이 없습니다');
    });

    testWidgets('값이 없으면 0 이 아니라 –', (tester) async {
      await _pump(
          tester,
          _service(bodyRows: [
            {'measured_at': '2026-08-02T09:00:00Z', 'weight_kg': 63.4}
          ]));
      await _scrollToBody(tester);
      // 「0kg」과 「측정 안 됨」은 다릅니다.
      expect(find.text('0.0 kg'), findsNothing);
      expect(find.text('–'), findsWidgets);
    });
  });

  group('⚠ 비어 있음은 오류가 아닙니다', () {
    testWidgets('기록이 없으면 안내 문구를 보여준다', (tester) async {
      // 체성분은 선택 동의라 없는 사용자가 많습니다.
      await _pump(tester, _service(bodyRows: const []));
      await _scrollToBody(tester);
      expect(find.text('아직 체성분 기록이 없어요.'), findsOneWidget);
      expect(find.textContaining('체성분계를 연동하고'), findsOneWidget);
    });

    testWidgets('체성분 조회가 실패해도 활동량·수면은 남는다', (tester) async {
      // ⚠ 선택 항목 하나 때문에 화면 전체가 비면 안 됩니다.
      await _pump(tester, _service(bodyRows: const [], bodyStatus: 500));
      expect(find.text('최근 측정치'), findsOneWidget);
      expect(find.text('8,000 걸음'), findsOneWidget);
    });

    testWidgets('실패했을 때 붉은 오류 문구를 띄우지 않는다', (tester) async {
      // 위쪽이 멀쩡한데 오류가 뜨면 전체가 고장난 것처럼 보입니다.
      await _pump(tester, _service(bodyRows: const [], bodyStatus: 500));
      expect(find.text('체성분 기록'), findsNothing);
      expect(find.textContaining('불러오지 못'), findsNothing);
    });
  });
}
