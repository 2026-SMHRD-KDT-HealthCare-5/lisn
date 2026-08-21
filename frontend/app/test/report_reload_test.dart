/// 기간을 바꿀 때 화면이 접혔다 펴지지 않아야 한다 — MAIN_REPORT_01 ❶
///
/// 관리자 웹 대상자 조회에서 같은 문제로 「화면 움직임이 너무 많다」는 지적을
/// 받았다. 앱의 리포트·라이프로그도 같은 구조였다.
///
/// 스피너로 갈아치우면 분포·곡선·라이프로그·요약이 한 번에 사라졌다 돌아온다.
/// 이전 내용을 두고 흐리게만 처리해야 한다.
library;

import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:maeume_care/screens/report_screen.dart';
import 'package:maeume_care/services/api_client.dart';
import 'package:maeume_care/services/report_service.dart';
import 'package:maeume_care/services/token_storage.dart';
import 'package:maeume_care/theme/app_theme.dart';

/// 감정 추이 2점 이상이어야 곡선을 그린다(1점이면 안내 문구로 빠진다).
String _reportJson({required String summary}) => jsonEncode({
      'user_id': '019535f0-7c0a-7000-8000-000000000001',
      'date_from': '2026-07-26T00:00:00Z',
      'date_to': '2026-08-02T00:00:00Z',
      'distribution': {'normal': 3, 'caution': 1, 'critical': 0},
      'emotion_trend': [
        {
          'evaluated_at': '2026-07-30T10:00:00Z',
          'emotion_code': 'HAPPINESS',
          'emotion_name': '행복',
          'emotion_score': '71.20',
          'risk_level': 'NORMAL',
          'risk_score': '12.40',
        },
        {
          'evaluated_at': '2026-08-01T10:00:00Z',
          'emotion_code': 'ANXIETY',
          'emotion_name': '불안',
          'emotion_score': '48.60',
          'risk_level': 'CAUTION',
          'risk_score': '41.20',
        },
      ],
      'lifelog_trend': const [],
      'summary': summary,
    });

ReportService _service(http.Client client) {
  final store = MemoryTokenStore();
  store.save(
    accessToken: 'test-token',
    expiresAt: DateTime.now().add(const Duration(hours: 1)),
  );
  return ReportService(
    apiClient: ApiClient(tokenStore: store, httpClient: client),
  );
}

void main() {
  testWidgets('기간을 바꾸는 동안 이전 리포트가 화면에 남는다', (tester) async {
    tester.view.physicalSize = const Size(360, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    // 두 번째 호출은 우리가 풀어줄 때까지 응답하지 않는다.
    // 그 사이 화면이 어떤 상태인지가 이 테스트의 관심사다.
    var calls = 0;
    Completer<void>? gate;
    final client = MockClient((request) async {
      calls += 1;
      if (calls >= 2) {
        gate = Completer<void>();
        await gate!.future;
      }
      return http.Response(
        _reportJson(summary: calls == 1 ? '첫 조회 요약입니다.' : '두 번째 조회 요약입니다.'),
        200,
        headers: {'content-type': 'application/json; charset=utf-8'},
      );
    });

    await tester.pumpWidget(MaterialApp(
      theme: AppTheme.light,
      home: ReportScreen(reportService: _service(client)),
    ));
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('첫 조회 요약입니다.'), findsOneWidget,
        reason: '첫 조회가 그려져야 이후 비교가 성립한다');

    // 월간으로 전환 — 응답은 아직 오지 않는다.
    await tester.tap(find.text('월간'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 120));

    // ⚠ 핵심. 스피너로 갈아치우면 여기서 이전 내용이 사라진다.
    expect(find.text('첫 조회 요약입니다.'), findsOneWidget,
        reason: '다시 불러오는 동안 이전 리포트가 남아 있어야 화면이 튀지 않는다');
    expect(find.byType(CircularProgressIndicator), findsNothing,
        reason: '이미 보여줄 내용이 있으면 스피너로 덮지 않는다');

    // 흐리게 처리되고 조작은 막혀 있어야 한다.
    final opacity = tester.widget<Opacity>(find
        .ancestor(of: find.text('첫 조회 요약입니다.'), matching: find.byType(Opacity))
        .first);
    expect(opacity.opacity, lessThan(1.0), reason: '갱신 중임이 보여야 한다');
    expect(
      find.ancestor(
          of: find.text('첫 조회 요약입니다.'), matching: find.byType(IgnorePointer)),
      findsWidgets,
      reason: '흐린 상태에서 PDF 내보내기가 눌리면 이전 기간 그림이 새 머리말로 나간다',
    );

    gate!.complete();
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('두 번째 조회 요약입니다.'), findsOneWidget);
    expect(find.text('첫 조회 요약입니다.'), findsNothing);
  });

  testWidgets('처음 열 때는 보여줄 것이 없으므로 스피너가 뜬다', (tester) async {
    tester.view.physicalSize = const Size(360, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    final gate = Completer<void>();
    final client = MockClient((request) async {
      await gate.future;
      return http.Response(_reportJson(summary: '요약'), 200,
          headers: {'content-type': 'application/json; charset=utf-8'});
    });

    await tester.pumpWidget(MaterialApp(
      theme: AppTheme.light,
      home: ReportScreen(reportService: _service(client)),
    ));
    await tester.pump(const Duration(milliseconds: 120));

    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    gate.complete();
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.byType(CircularProgressIndicator), findsNothing);
  });

  testWidgets('조회에 실패해도 이전 리포트를 버리지 않는다', (tester) async {
    tester.view.physicalSize = const Size(360, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    // 통신이 한 번 끊겼다고 보고 있던 내용을 버리면, 다음 조회에서 다시
    // 스피너부터 시작한다. 사용자 눈에는 기록이 사라졌다 돌아오는 것으로 보인다.
    var calls = 0;
    final gate = Completer<void>();
    final client = MockClient((request) async {
      calls += 1;
      if (calls == 2) {
        // ⚠ charset 을 안 주면 http.Response 가 Latin-1 로 인코딩하려다 죽는다.
        return http.Response('{"detail":"일시적 오류"}', 500,
            headers: {'content-type': 'application/json; charset=utf-8'});
      }
      if (calls == 3) await gate.future;
      return http.Response(
        _reportJson(summary: calls == 1 ? '첫 조회 요약입니다.' : '세 번째 조회 요약입니다.'),
        200,
        headers: {'content-type': 'application/json; charset=utf-8'},
      );
    });

    await tester.pumpWidget(MaterialApp(
      theme: AppTheme.light,
      home: ReportScreen(reportService: _service(client)),
    ));
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('첫 조회 요약입니다.'), findsOneWidget);

    // ① 실패 — 화면에는 안내가 뜬다.
    await tester.tap(find.text('월간'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    // FutureBuilder 가 hasError 로 받아 화면은 처리됐지만, Future 자체가 오류로
    // 끝나 테스트 프레임워크가 따로 잡아둔다. 화면 처리와 별개라 비워준다.
    tester.takeException();
    expect(find.textContaining('불러오지 못했습니다'), findsOneWidget);

    // ② 다시 조회 — 응답 전인데도 이전 리포트가 나와야 한다.
    //    실패가 _last 를 지웠다면 여기서 스피너가 뜬다.
    await tester.tap(find.text('주간'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 120));
    expect(find.text('첫 조회 요약입니다.'), findsOneWidget,
        reason: '실패가 이전 결과를 지웠다면 스피너부터 다시 시작한다');
    expect(find.byType(CircularProgressIndicator), findsNothing);

    gate.complete();
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('세 번째 조회 요약입니다.'), findsOneWidget);
  });
}
