import 'package:flutter_test/flutter_test.dart';
import 'package:maeume_care/models/report_models.dart';

void main() {
  group('EmotionReport', () {
    test('NUMERIC 컬럼이 문자열로 와도 파싱한다', () {
      // 서버가 Decimal 을 문자열로 직렬화한다. 실측 확인:
      //   emotion_score: '30.00', risk_score: '27.00', hrv: '40.00'
      // num 으로만 캐스팅하면 조용히 0 이 되어 곡선이 바닥에 붙는다.
      final report = EmotionReport.fromJson({
        'distribution': {'normal': 3, 'caution': 4, 'critical': 0},
        'emotion_trend': [
          {
            'evaluated_at': '2026-08-01T09:00:00Z',
            'emotion_code': 'ANXIETY',
            'emotion_name': '불안',
            'emotion_score': '62.00',
            'risk_level': 'CAUTION',
            'risk_score': '55.80',
          }
        ],
        'lifelog_trend': [
          {
            'collected_at': '2026-08-01T09:00:00Z',
            'steps': 8400,
            'total_sleep_min': 300,
            'heart_rate': 76,
            'hrv': '36.50',
          }
        ],
        'summary': '주의 단계가 많았어요.',
      });

      expect(report.emotionTrend.single.emotionScore, 62.0);
      expect(report.emotionTrend.single.riskScore, 55.8);
      expect(report.lifelogTrend.single.hrv, 36.5);
      expect(report.distribution.total, 7);
      expect(report.isEmpty, isFalse);
    });

    test('추이가 비면 isEmpty 로 빈 상태를 알린다', () {
      // 서버는 분석 이력이 없으면 409 를 주지만, 200 에 빈 배열이 올
      // 가능성도 막아둔다. 빈 배열로 차트를 그리면 0으로 나눈다.
      final report = EmotionReport.fromJson({
        'distribution': {},
        'emotion_trend': [],
        'lifelog_trend': [],
        'summary': '',
      });

      expect(report.isEmpty, isTrue);
      expect(report.distribution.total, 0);
    });

    test('없는 필드가 있어도 터지지 않는다', () {
      // 서버 스키마가 늘거나 줄어도 화면이 죽지 않아야 한다.
      final report = EmotionReport.fromJson(const {});

      expect(report.emotionTrend, isEmpty);
      expect(report.summary, '');
      expect(report.dateFrom, isNull);
    });

    test('측정되지 않은 라이프로그 항목은 0 이 아니라 null 이다', () {
      // "0걸음"과 "측정 안 됨"은 다르다. 0 으로 채우면 결합 차트가
      // 실제로 안 움직인 것처럼 그려진다.
      final report = EmotionReport.fromJson({
        'emotion_trend': const [],
        'lifelog_trend': [
          {'collected_at': '2026-08-01T09:00:00Z'}
        ],
        'summary': '',
      });

      final point = report.lifelogTrend.single;
      expect(point.steps, isNull);
      expect(point.totalSleepMin, isNull);
      expect(point.heartRate, isNull);
      expect(point.hrv, isNull);
    });
  });
}
