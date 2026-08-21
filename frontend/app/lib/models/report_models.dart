/// 정서 리포트 — MLCM_500 · MAIN_REPORT_01
///
/// 서버 스키마(backend/app/schemas/report.py ReportOut)와 1:1로 맞춥니다.
/// 관리자 상세 조회(MLCM_501 ❸)도 같은 스키마를 쓰므로, 필드를 바꾸면
/// 관리자 웹 시각화도 함께 확인해야 합니다.
library;

import 'json.dart';

/// ❸ 위험 단계 분포 — 안정·주의·심각 비율
class RiskDistribution {
  const RiskDistribution(
      {this.normal = 0, this.caution = 0, this.critical = 0});

  final int normal;
  final int caution;
  final int critical;

  int get total => normal + caution + critical;

  factory RiskDistribution.fromJson(Map<String, dynamic> json) =>
      RiskDistribution(
        normal: jsonInt(json['normal']) ?? 0,
        caution: jsonInt(json['caution']) ?? 0,
        critical: jsonInt(json['critical']) ?? 0,
      );
}

/// ❷ 감정 변화 곡선의 한 점
class RiskPoint {
  const RiskPoint({
    required this.evaluatedAt,
    required this.emotionCode,
    required this.emotionName,
    required this.emotionScore,
    required this.riskLevel,
    required this.riskScore,
  });

  final DateTime evaluatedAt;
  final String emotionCode;
  final String emotionName;
  final double emotionScore;

  /// NORMAL / CAUTION / CRITICAL — 서버가 확정한 값입니다(데이터베이스요구사항분석서 6항).
  final String riskLevel;
  final double riskScore;

  factory RiskPoint.fromJson(Map<String, dynamic> json) => RiskPoint(
        evaluatedAt: jsonAt(json['evaluated_at']) ?? DateTime.now(),
        emotionCode: jsonStr(json['emotion_code']),
        emotionName: jsonStr(json['emotion_name']),
        emotionScore: jsonNum(json['emotion_score']) ?? 0,
        riskLevel: jsonStr(json['risk_level'], 'NORMAL'),
        riskScore: jsonNum(json['risk_score']) ?? 0,
      );
}

/// ❹ 결합 차트용 — 감정 추이와 **같은 시간축**에 겹칩니다
class LifelogPoint {
  const LifelogPoint({
    required this.collectedAt,
    this.steps,
    this.totalSleepMin,
    this.heartRate,
    this.hrv,
  });

  final DateTime collectedAt;
  final int? steps;
  final int? totalSleepMin;
  final int? heartRate;
  final double? hrv;

  factory LifelogPoint.fromJson(Map<String, dynamic> json) => LifelogPoint(
        collectedAt: jsonAt(json['collected_at']) ?? DateTime.now(),
        steps: jsonInt(json['steps']),
        totalSleepMin: jsonInt(json['total_sleep_min']),
        heartRate: jsonInt(json['heart_rate']),
        hrv: jsonNum(json['hrv']),
      );
}

class EmotionReport {
  const EmotionReport({
    required this.distribution,
    required this.emotionTrend,
    required this.lifelogTrend,
    required this.summary,
    this.dateFrom,
    this.dateTo,
  });

  final DateTime? dateFrom;
  final DateTime? dateTo;
  final RiskDistribution distribution;
  final List<RiskPoint> emotionTrend;
  final List<LifelogPoint> lifelogTrend;

  /// ❺ 종합 요약 문구
  final String summary;

  /// ⚠ 서버는 분석 이력이 없으면 **409** 를 돌려줍니다(MLCM_500 선행조건).
  ///   그 경우 이 객체가 만들어지지 않으므로, 빈 상태는 화면에서 처리합니다.
  bool get isEmpty => emotionTrend.isEmpty;

  factory EmotionReport.fromJson(Map<String, dynamic> json) => EmotionReport(
        dateFrom: jsonAt(json['date_from']),
        dateTo: jsonAt(json['date_to']),
        distribution: RiskDistribution.fromJson(jsonObj(json['distribution'])),
        emotionTrend:
            jsonList(json['emotion_trend']).map(RiskPoint.fromJson).toList(),
        lifelogTrend:
            jsonList(json['lifelog_trend']).map(LifelogPoint.fromJson).toList(),
        summary: jsonStr(json['summary']),
      );
}
