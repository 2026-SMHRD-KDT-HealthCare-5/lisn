/// 정서 리포트 — MLCM_500 · MAIN_REPORT_01
///
/// 서버 스키마(backend/app/schemas/report.py ReportOut)와 1:1로 맞춥니다.
/// 관리자 상세 조회(MLCM_501 ❸)도 같은 스키마를 쓰므로, 필드를 바꾸면
/// 관리자 웹 시각화도 함께 확인해야 합니다.
library;

/// ⚠ 서버가 NUMERIC 을 **문자열로** 내려보낼 수 있습니다(Decimal 직렬화).
///   num 으로만 캐스팅하면 조용히 null 이 됩니다 — 라이프로그에서 실제로 겪었습니다.
double? _num(dynamic v) => switch (v) {
      num n => n.toDouble(),
      String s => double.tryParse(s),
      _ => null,
    };

DateTime? _at(dynamic v) =>
    DateTime.tryParse(v as String? ?? '')?.toLocal();

/// ❸ 위험 단계 분포 — 안정·주의·심각 비율
class RiskDistribution {
  const RiskDistribution({this.normal = 0, this.caution = 0, this.critical = 0});

  final int normal;
  final int caution;
  final int critical;

  int get total => normal + caution + critical;

  factory RiskDistribution.fromJson(Map<String, dynamic> json) =>
      RiskDistribution(
        normal: (json['normal'] as num?)?.toInt() ?? 0,
        caution: (json['caution'] as num?)?.toInt() ?? 0,
        critical: (json['critical'] as num?)?.toInt() ?? 0,
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

  /// NORMAL / CAUTION / CRITICAL — 서버가 확정한 값입니다(04 문서 6항).
  final String riskLevel;
  final double riskScore;

  factory RiskPoint.fromJson(Map<String, dynamic> json) => RiskPoint(
        evaluatedAt: _at(json['evaluated_at']) ?? DateTime.now(),
        emotionCode: json['emotion_code'] as String? ?? '',
        emotionName: json['emotion_name'] as String? ?? '',
        emotionScore: _num(json['emotion_score']) ?? 0,
        riskLevel: json['risk_level'] as String? ?? 'NORMAL',
        riskScore: _num(json['risk_score']) ?? 0,
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
        collectedAt: _at(json['collected_at']) ?? DateTime.now(),
        steps: (json['steps'] as num?)?.toInt(),
        totalSleepMin: (json['total_sleep_min'] as num?)?.toInt(),
        heartRate: (json['heart_rate'] as num?)?.toInt(),
        hrv: _num(json['hrv']),
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
        dateFrom: _at(json['date_from']),
        dateTo: _at(json['date_to']),
        distribution: RiskDistribution.fromJson(
            (json['distribution'] as Map<String, dynamic>?) ?? const {}),
        emotionTrend: ((json['emotion_trend'] as List<dynamic>?) ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(RiskPoint.fromJson)
            .toList(),
        lifelogTrend: ((json['lifelog_trend'] as List<dynamic>?) ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(LifelogPoint.fromJson)
            .toList(),
        summary: json['summary'] as String? ?? '',
      );
}
