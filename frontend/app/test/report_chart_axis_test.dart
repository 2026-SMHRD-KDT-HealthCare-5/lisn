/// 수면·활동량 결합 차트의 시간축 — 정서 리포트 ❹
///
/// ⚠ 두 계열을 「측정된 값만」 골라 각각 배열로 만들면 **길이가 달라집니다.**
///   그러면 화면 폭을 각자 나눠 쓰게 돼 **같은 x 좌표가 서로 다른 날**을
///   가리킵니다. 「그날 수면이 줄고 활동도 줄었다」로 읽히는 그림이 실제로는
///   다른 날 둘을 겹쳐놓은 것이 됩니다.
///
///   걸음은 0 을 제외하므로(「0걸음」과 「측정 안 됨」은 다릅니다) 길이가
///   어긋나는 것이 흔합니다. 2026.08.02 점검에서 실제로 그 상태였습니다.
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:maeume_care/models/report_models.dart';
import 'package:maeume_care/screens/report_screen.dart';

/// 수면은 5일 전부, 걸음은 그중 이틀만 측정된 상황.
List<Map<String, dynamic>> _mismatchedTrend() => [
      {
        'collected_at': '2026-07-28T00:00:00Z',
        'total_sleep_min': 400,
        'steps': 0
      },
      {
        'collected_at': '2026-07-29T00:00:00Z',
        'total_sleep_min': 380,
        'steps': 0
      },
      {
        'collected_at': '2026-07-30T00:00:00Z',
        'total_sleep_min': 360,
        'steps': 5200
      },
      {
        'collected_at': '2026-07-31T00:00:00Z',
        'total_sleep_min': 200,
        'steps': 0
      },
      {
        'collected_at': '2026-08-01T00:00:00Z',
        'total_sleep_min': 180,
        'steps': 900
      },
    ];

EmotionReport _report() => EmotionReport.fromJson({
      'user_id': '019535f0-7c0a-7000-8000-000000000001',
      'date_from': '2026-07-28T00:00:00Z',
      'date_to': '2026-08-01T23:59:59Z',
      'distribution': {'normal': 2, 'caution': 2, 'critical': 1},
      'emotion_trend': const [],
      'lifelog_trend': _mismatchedTrend(),
      'summary': '테스트',
    });

void main() {
  test('두 계열은 측정 여부와 무관하게 같은 길이로 만들어진다', () {
    final report = _report();
    final sleeps = [
      for (final p in report.lifelogTrend) p.totalSleepMin?.toDouble(),
    ];
    final steps = [
      for (final p in report.lifelogTrend)
        (p.steps != null && p.steps! > 0) ? p.steps!.toDouble() : null,
    ];

    expect(sleeps.length, steps.length, reason: '길이가 다르면 같은 x 가 다른 날을 가리킵니다');
    expect(sleeps.whereType<double>().length, 5);
    expect(steps.whereType<double>().length, 2, reason: '0걸음은 측정으로 치지 않습니다');

    // 측정된 걸음이 원래 있던 자리(2일차·4일차)에 그대로 있어야 합니다.
    expect(steps[2], 5200);
    expect(steps[4], 900);
    expect(steps[0], isNull);
  });

  testWidgets('길이가 어긋나는 데이터로도 차트가 그려진다', (tester) async {
    // 길이가 다른 배열을 넘기면 _DualPainter 의 assert 가 잡습니다.
    // 여기서는 화면이 실제로 그려지는지까지 봅니다.
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: SizedBox(
          height: 110,
          width: 300,
          child: CustomPaint(
            painter: buildDualPainterForTest(
              sleep: const [400, 380, 360, 200, 180],
              steps: const [null, null, 5200, null, 900],
            ),
          ),
        ),
      ),
    ));
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}
