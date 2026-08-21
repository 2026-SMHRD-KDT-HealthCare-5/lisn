/// 정서 리포트 조회 기간 — MAIN_REPORT_01 ❶
///
/// ```
/// ❶ 조회 기간: 주·월·직접 지정 전환. 변경 시 재조회
/// ```
///
/// 「직접 지정」이 없어 주간·월간 둘뿐이었습니다. 서버 `GET /reports` 는
/// `from`·`to` 를 받으므로 화면만 붙이면 되는 상태였습니다.
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:maeume_care/screens/report_screen.dart';
import 'package:maeume_care/services/api_client.dart';
import 'package:maeume_care/services/report_service.dart';
import 'package:maeume_care/services/token_storage.dart';
import 'package:maeume_care/theme/app_theme.dart';

class _Server {
  final queries = <Map<String, String>>[];

  ReportService build() {
    final store = MemoryTokenStore();
    store.save(
      accessToken: 'test-token',
      expiresAt: DateTime.now().add(const Duration(hours: 1)),
    );
    final client = MockClient((request) async {
      queries.add(request.url.queryParameters);
      return http.Response(
          jsonEncode({
            'from': '2026-07-26',
            'to': '2026-08-02',
            'average_score': 62,
            'points': <Object>[],
            'distribution': {'NORMAL': 5, 'CAUTION': 2, 'CRITICAL': 0},
            'summary': '요약',
          }),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'});
    });
    return ReportService(
        apiClient: ApiClient(tokenStore: store, httpClient: client));
  }
}

Future<void> _pump(WidgetTester tester, ReportService service) async {
  tester.view.physicalSize = const Size(411, 1200);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(MaterialApp(
    theme: AppTheme.light,
    // ⚠ 날짜 선택기는 MaterialLocalizations 를 요구합니다. 앱 본체와 같은
    //   델리게이트를 넣지 않으면 여는 순간 죽습니다.
    localizationsDelegates: const [
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    supportedLocales: const [Locale('ko'), Locale('en')],
    locale: const Locale('ko'),
    home: ReportScreen(reportService: service),
  ));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('❶ 세 가지 기간을 모두 제공한다', (tester) async {
    await _pump(tester, _Server().build());
    expect(find.text('주간'), findsOneWidget);
    expect(find.text('월간'), findsOneWidget);
    expect(find.text('직접 지정'), findsOneWidget);
  });

  testWidgets('기간을 바꾸면 다시 조회한다', (tester) async {
    final s = _Server();
    await _pump(tester, s.build());
    expect(s.queries, hasLength(1));

    await tester.tap(find.text('월간'));
    await tester.pumpAndSettle();
    expect(s.queries, hasLength(2), reason: '변경 시 재조회해야 합니다');
  });

  testWidgets('직접 지정을 누르면 달력이 열린다', (tester) async {
    await _pump(tester, _Server().build());
    await tester.tap(find.text('직접 지정'));
    await tester.pumpAndSettle();
    expect(find.text('조회 기간 선택'), findsOneWidget);
  });

  testWidgets('⚠ 달력을 취소하면 기간이 바뀌지 않는다', (tester) async {
    // 먼저 range 를 custom 으로 바꿔놓고 달력을 띄우면, 취소했을 때
    // 구간이 없는 custom 상태로 남아 화면이 빕니다.
    final s = _Server();
    await _pump(tester, s.build());
    await tester.tap(find.text('직접 지정'));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.close));
    await tester.pumpAndSettle();

    expect(s.queries, hasLength(1), reason: '취소했는데 다시 조회했습니다');
    expect(find.text('직접 지정'), findsOneWidget, reason: '라벨이 바뀌었습니다');
  });

  testWidgets('구간을 고르면 그 범위로 조회한다', (tester) async {
    final s = _Server();
    await _pump(tester, s.build());
    await tester.tap(find.text('직접 지정'));
    await tester.pumpAndSettle();
    // 기본 구간(최근 7일)이 이미 잡혀 있으므로 그대로 적용합니다.
    await tester.tap(find.text('적용'));
    await tester.pumpAndSettle();

    expect(s.queries, hasLength(2));
    final q = s.queries.last;
    final from = DateTime.parse(q['from']!);
    final to = DateTime.parse(q['to']!);
    expect(to.isAfter(from), isTrue);
    // ⚠ 끝나는 날을 그날 끝까지 잡아야 마지막 날이 빠지지 않습니다.
    expect(to.toLocal().hour, 23, reason: '마지막 날이 통째로 빠집니다');
  });
}
