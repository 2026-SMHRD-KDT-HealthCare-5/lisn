/// 감정 이름을 사용자에게 보여주지 않는다 — MAIN_HOME_01 ❶
///
/// 감정 마스터 9종에 **「위기」·「절망」**이 들어 있습니다. 힘들어하는 사람 화면에
/// 그 단어를 헤드라인으로 박으면 데이터 관찰이 아니라 **사람에 대한 판정**으로
/// 읽힙니다. 요구사항정의서 요구사항의 「진단 금지」에 걸립니다.
///
/// 라벨을 되살리는 변경은 화면만 봐서는 정상으로 보입니다(글자가 크고 예쁘게
/// 들어갑니다). 그래서 테스트로 고정합니다.
///
/// ⚠ **관리자 화면은 대상이 아닙니다.** 거기서 「위기」는 담당자가 판단하는 데
///   필요한 정확한 용어입니다. 본인이 보는 화면과 전문가가 보는 화면은 기준이
///   다릅니다.
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:maeume_care/screens/home_screen.dart';
import 'package:maeume_care/services/api_client.dart';
import 'package:maeume_care/services/home_service.dart';
import 'package:maeume_care/services/token_storage.dart';
import 'package:maeume_care/theme/app_theme.dart';
import 'package:maeume_care/widgets/common_widgets.dart';

String _homeJson({
  required String code,
  required String name,
  required String risk,
  required String action,
}) =>
    jsonEncode({
      'action': action,
      'emotion_today': {
        'emotion_code': code,
        'emotion_name': name,
        'emotion_score': '93.80',
        'risk_level': risk,
        'evaluated_at': '2026-08-02T01:00:00Z',
      },
      'lifelog': {
        'total_sleep_min': 171,
        'steps': 390,
        'heart_rate': 89,
        'hrv': '22.80',
        'collected_at': '2026-08-02T00:00:00Z',
      },
      'ai_summary': null,
      'recommendations': const [],
    });

HomeService _service(String body) {
  final store = MemoryTokenStore();
  store.save(
    accessToken: 'test-token',
    expiresAt: DateTime.now().add(const Duration(hours: 1)),
  );
  final client = MockClient((_) async => http.Response(
        body,
        200,
        headers: {'content-type': 'application/json; charset=utf-8'},
      ));
  return HomeService(
    apiClient: ApiClient(tokenStore: store, httpClient: client),
  );
}

Future<void> _pump(WidgetTester tester, String body) async {
  tester.view.physicalSize = const Size(390, 900);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(MaterialApp(
    theme: AppTheme.light,
    home: Scaffold(body: HomeScreen(homeService: _service(body))),
  ));
  await tester.pump(const Duration(milliseconds: 300));
}

void main() {
  testWidgets('위기 상태여도 「위기」라는 단어가 화면에 없다', (tester) async {
    await _pump(
      tester,
      _homeJson(
          code: 'CRISIS', name: '위기', risk: 'CRITICAL', action: 'EMERGENCY'),
    );

    expect(find.text('위기'), findsNothing,
        reason: '감정 이름을 헤드라인으로 쓰면 진단으로 읽힙니다');
    // 대신 상태를 서술하는 문구가 나와야 합니다. 라벨만 지우고 아무것도
    // 안 남기면 사용자가 자기 상태를 알 수 없습니다.
    expect(find.textContaining('힘들어 보여요'), findsOneWidget);
  });

  testWidgets('「절망」도 노출되지 않는다', (tester) async {
    // 마스터 9종 중 가장 강한 단어입니다. CRISIS 만 막고 넘어가지 않게 함께 봅니다.
    await _pump(
      tester,
      _homeJson(
          code: 'DESPAIR', name: '절망', risk: 'CRITICAL', action: 'EMERGENCY'),
    );
    expect(find.text('절망'), findsNothing);
  });

  testWidgets('주의 단계의 감정 이름도 노출되지 않는다', (tester) async {
    await _pump(
      tester,
      _homeJson(
          code: 'LONELINESS', name: '외로움', risk: 'CAUTION', action: 'CONTENT'),
    );
    expect(find.text('외로움'), findsNothing);
    expect(find.textContaining('평소와 조금 다른'), findsOneWidget);
  });

  testWidgets('안정 상태에서도 라벨 대신 문구를 쓴다', (tester) async {
    // 안정일 때만 라벨을 남기면 「이름이 사라지면 나쁜 상태」라는 신호가 됩니다.
    await _pump(
      tester,
      _homeJson(code: 'JOY', name: '기쁨', risk: 'NORMAL', action: 'CHAT'),
    );
    expect(find.text('기쁨'), findsNothing);
    expect(find.textContaining('안정적인 상태'), findsOneWidget);
  });

  testWidgets('위기 상태에서 마음이가 웃지 않는다', (tester) async {
    await _pump(
      tester,
      _homeJson(
          code: 'CRISIS', name: '위기', risk: 'CRITICAL', action: 'EMERGENCY'),
    );

    final mascots = tester.widgetList<MaeumeMascot>(find.byType(MaeumeMascot));
    expect(mascots, isNotEmpty);
    for (final m in mascots) {
      expect(m.mood, isNot(MascotMood.smile),
          reason: '「많이 힘들어 보여요」 옆에서 웃으면 무시로 읽힙니다');
    }
  });

  testWidgets('구현되지 않은 알림 종 아이콘을 두지 않는다', (tester) async {
    // ⚠ 빨간 배지가 찍힌 종이 있었습니다. 화면설계서 ❶~❺ 에 알림 항목이 없고,
    //   서버에 알림 API 도 없습니다. 설정 화면은 「준비 중」이라고 정직하게
    //   알리는데 홈이 빨간 점으로 「읽지 않은 알림 있음」을 주장해 모순됐습니다.
    //   눌리지도 않는 정적 Icon 이었습니다.
    await _pump(
      tester,
      _homeJson(code: 'JOY', name: '기쁨', risk: 'NORMAL', action: 'CHAT'),
    );
    expect(find.byIcon(Icons.notifications_none_rounded), findsNothing);
    expect(find.byType(Badge), findsNothing);
  });

  testWidgets('위기 상태에서는 인사말에 웃는 이모지를 붙이지 않는다', (tester) async {
    await _pump(
      tester,
      _homeJson(
          code: 'CRISIS', name: '위기', risk: 'CRITICAL', action: 'EMERGENCY'),
    );
    expect(find.textContaining('😊'), findsNothing);
  });
}
