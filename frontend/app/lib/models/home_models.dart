/// GET /home 응답 — MAIN_HOME_01
///
/// 서버 스키마(backend/app/api/v1/home.py HomeOut)와 1:1로 맞춥니다.
/// 필드를 추가할 때는 서버부터 고치세요.
library;

import 'json.dart';

/// 홈이 무엇을 보여줘야 하는지. **판단은 서버가 끝냅니다.**
///
/// 감정→위험도→액션 매핑을 클라이언트에 복제하지 않습니다. 규칙이 두 곳에
/// 생기면 반드시 어긋납니다. 앱은 이 값을 보고 렌더만 합니다.
enum HomeAction {
  /// 대화를 권함
  chat,

  /// 힐링 콘텐츠 추천
  content,

  /// ⚠ MLCM_510 2단계 — 콘텐츠 추천을 즉시 중단하고 긴급 상담으로 전환.
  /// 서버도 이때는 recommendations 를 비워서 보냅니다.
  emergency;

  static HomeAction parse(String? raw) => switch (raw) {
        'CONTENT' => HomeAction.content,
        'EMERGENCY' => HomeAction.emergency,
        _ => HomeAction.chat,
      };
}

class EmotionToday {
  const EmotionToday({
    required this.emotionCode,
    required this.emotionName,
    required this.emotionScore,
    required this.riskLevel,
    required this.evaluatedAt,
  });

  final String emotionCode;
  final String emotionName;
  final double emotionScore;

  /// NORMAL / CAUTION / CRITICAL. 서버가 확정한 값입니다(데이터베이스요구사항분석서 6항).
  final String riskLevel;
  final DateTime evaluatedAt;

  factory EmotionToday.fromJson(Map<String, dynamic> json) => EmotionToday(
        emotionCode: jsonStr(json['emotion_code']),
        emotionName: jsonStr(json['emotion_name']),
        emotionScore: jsonNum(json['emotion_score']) ?? 0,
        riskLevel: jsonStr(json['risk_level'], 'NORMAL'),
        evaluatedAt: jsonAt(json['evaluated_at']) ?? DateTime.now(),
      );
}

class LifelogSummary {
  const LifelogSummary({
    this.totalSleepMin,
    this.steps,
    this.hrv,
    this.collectedAt,
  });

  /// ⚠ 전부 null 이 될 수 있습니다. 워치를 연동하지 않았거나 수집 전이면
  ///   값이 없습니다. 0 으로 대체하지 마세요 — "0걸음" 과 "모름" 은 다릅니다.
  final int? totalSleepMin;
  final int? steps;
  final double? hrv;
  final DateTime? collectedAt;

  factory LifelogSummary.fromJson(Map<String, dynamic> json) => LifelogSummary(
        totalSleepMin: jsonInt(json['total_sleep_min']),
        steps: jsonInt(json['steps']),
        hrv: jsonNum(json['hrv']),
        collectedAt: jsonAt(json['collected_at']),
      );
}

class ContentCard {
  const ContentCard({
    required this.contentId,
    required this.category,
    required this.title,
    required this.externalUrl,
    this.description,
  });

  final String contentId;

  /// MUSIC / FOOD / EXERCISE / ARTICLE
  final String category;
  final String title;
  final String? description;
  final String externalUrl;

  factory ContentCard.fromJson(Map<String, dynamic> json) => ContentCard(
        contentId: jsonStr(json['content_id']),
        category: jsonStr(json['category']),
        title: jsonStr(json['title']),
        description: json['description'] as String?,
        externalUrl: jsonStr(json['external_url']),
      );
}

/// 시스템이 먼저 건 대화 중 **아직 답하지 않은 것** — `MLCM_220` 6단계.
///
/// ⚠ **이게 없으면 선제 접촉이 대화 기록 안에 묻힙니다.** 앱은 자기가
///   시작한 대화만 알고 있어서, 서버가 세션을 만들어도 사용자는 목록을
///   뒤지지 않는 한 못 봅니다. FCM 이 없어도 이 경로만 있으면 도달합니다.
class PendingOutreach {
  const PendingOutreach({
    required this.sessionId,
    required this.personaType,
    required this.opener,
    required this.startedAt,
  });

  final String sessionId;
  final String personaType;

  /// 챗봇이 먼저 건넨 첫 문장. 홈 카드에 그대로 보여줍니다.
  final String opener;
  final DateTime startedAt;

  factory PendingOutreach.fromJson(Map<String, dynamic> json) =>
      PendingOutreach(
        sessionId: jsonStr(json['session_id']),
        personaType: jsonStr(json['persona_type']),
        opener: jsonStr(json['opener']),
        startedAt: jsonAt(json['started_at']) ?? DateTime.now(),
      );
}

class HomeSnapshot {
  const HomeSnapshot({
    required this.action,
    required this.lifelog,
    required this.recommendations,
    this.emotionToday,
    this.aiSummary,
    this.pendingOutreach,
  });

  final HomeAction action;

  /// null 이면 아직 분석된 기록이 없습니다. 가입 직후가 이 상태입니다.
  final EmotionToday? emotionToday;
  final LifelogSummary lifelog;

  /// null 이면 요약 생성에 실패한 것입니다. 그 칸만 비우고 나머지는 그립니다 —
  /// 요약 하나 때문에 화면 전체가 실패하면 안 됩니다.
  final String? aiSummary;
  final List<ContentCard> recommendations;

  /// null 이면 답하지 않은 선제 접촉이 없습니다.
  final PendingOutreach? pendingOutreach;

  factory HomeSnapshot.fromJson(Map<String, dynamic> json) => HomeSnapshot(
        action: HomeAction.parse(json['action'] as String?),
        emotionToday: json['emotion_today'] == null
            ? null
            : EmotionToday.fromJson(jsonObj(json['emotion_today'])),
        lifelog: LifelogSummary.fromJson(jsonObj(json['lifelog_summary'])),
        aiSummary: json['ai_summary'] as String?,
        recommendations: jsonList(json['recommendations'])
            .map(ContentCard.fromJson)
            .toList(),
        pendingOutreach: json['pending_outreach'] == null
            ? null
            : PendingOutreach.fromJson(jsonObj(json['pending_outreach'])),
      );
}
