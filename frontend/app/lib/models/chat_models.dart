/// 챗봇 — MLCM_300 · MLCM_310 · MLCM_320
///
/// 서버 스키마(backend/app/schemas/chat.py)와 1:1로 맞춥니다.
library;

/// 서버가 확정한 액션. **클라이언트가 다시 계산하지 않습니다.**
///
/// 감정→위험도→액션 매핑을 복제하면 서버와 어긋납니다
/// (API설계_사전결정 3절).
enum ChatAction {
  chat,
  content,

  /// ⚠ MLCM_510 2단계 — 일반 응답을 버리고 긴급 상담으로 전환합니다.
  emergency;

  static ChatAction parse(String? raw) => switch (raw) {
        'CONTENT' => ChatAction.content,
        'EMERGENCY' => ChatAction.emergency,
        _ => ChatAction.chat,
      };
}

class RiskInfo {
  const RiskInfo({
    required this.level,
    required this.action,
    required this.source,
  });

  /// NORMAL / CAUTION / CRITICAL
  final String level;
  final ChatAction action;

  /// LLM / KEYWORD.
  /// KEYWORD 면 외부 API 장애로 **문맥 판단 없이** 내린 결과입니다
  /// (NFR-DV-003 fallback).
  final String source;

  factory RiskInfo.fromJson(Map<String, dynamic> json) => RiskInfo(
        level: json['level'] as String? ?? 'NORMAL',
        action: ChatAction.parse(json['action'] as String?),
        source: json['source'] as String? ?? 'KEYWORD',
      );
}

class SessionStarted {
  const SessionStarted({
    required this.sessionId,
    required this.personaType,
    required this.greeting,
    required this.startedAt,
  });

  final String sessionId;
  final String personaType;
  final String greeting;
  final DateTime startedAt;

  factory SessionStarted.fromJson(Map<String, dynamic> json) => SessionStarted(
        sessionId: json['session_id'] as String? ?? '',
        personaType: json['persona_type'] as String? ?? 'FRIEND',
        greeting: json['greeting'] as String? ?? '',
        startedAt:
            DateTime.tryParse(json['started_at'] as String? ?? '')?.toLocal() ??
                DateTime.now(),
      );
}

class MessageResult {
  const MessageResult({required this.risk, this.reply});

  /// ⚠ CRITICAL 이면 null 입니다. 서버가 병렬로 생성한 일반 응답을 버립니다.
  ///   이때 화면은 답변 대신 긴급 상담 안내를 띄워야 합니다.
  final String? reply;
  final RiskInfo risk;

  factory MessageResult.fromJson(Map<String, dynamic> json) => MessageResult(
        reply: json['reply'] as String?,
        risk: RiskInfo.fromJson(
            (json['risk'] as Map<String, dynamic>?) ?? const {}),
      );
}

class ChatSessionSummary {
  const ChatSessionSummary({
    required this.sessionId,
    required this.personaType,
    required this.startedAt,
    this.sessionSummary,
    this.endedAt,
  });

  final String sessionId;
  final String personaType;

  /// 종료 시 LLM 이 만든 요약. 생성 실패면 null 입니다.
  final String? sessionSummary;
  final DateTime startedAt;
  final DateTime? endedAt;

  bool get isEnded => endedAt != null;

  factory ChatSessionSummary.fromJson(Map<String, dynamic> json) =>
      ChatSessionSummary(
        sessionId: json['session_id'] as String? ?? '',
        personaType: json['persona_type'] as String? ?? 'FRIEND',
        sessionSummary: json['session_summary'] as String?,
        startedAt:
            DateTime.tryParse(json['started_at'] as String? ?? '')?.toLocal() ??
                DateTime.now(),
        endedAt: DateTime.tryParse(json['ended_at'] as String? ?? '')?.toLocal(),
      );
}

/// 화면에 그리는 말풍선 한 줄.
///
/// 서버는 messages 를 JSONB 배열로 보관합니다. **PII 가 [MASK] 로 치환된
/// 상태로 저장**되므로(NFR-DE-002) 지난 대화를 불러오면 마스킹된 본문이 옵니다.
class ChatBubble {
  const ChatBubble({
    required this.role,
    required this.content,
    this.at,
    this.isEmergency = false,
  });

  /// user / assistant
  final String role;
  final String content;
  final DateTime? at;

  /// 위기 판정으로 답변 대신 안내를 띄우는 말풍선인지.
  final bool isEmergency;

  bool get isUser => role == 'user';

  factory ChatBubble.fromJson(Map<String, dynamic> json) => ChatBubble(
        role: json['role'] as String? ?? 'assistant',
        content: json['content'] as String? ?? '',
        at: DateTime.tryParse(json['at'] as String? ?? '')?.toLocal(),
      );
}

class ChatSessionDetail {
  const ChatSessionDetail({required this.summary, required this.messages});

  final ChatSessionSummary summary;
  final List<ChatBubble> messages;

  factory ChatSessionDetail.fromJson(Map<String, dynamic> json) =>
      ChatSessionDetail(
        summary: ChatSessionSummary.fromJson(json),
        messages: ((json['messages'] as List<dynamic>?) ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(ChatBubble.fromJson)
            .toList(),
      );
}
