import '../models/chat_models.dart';
import 'api_client.dart';

/// 챗봇 — MLCM_300 · MLCM_310 · MLCM_320
class ChatService {
  const ChatService({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  /// 세션 시작. personaType 을 생략하면 서버가 USERS.persona_type 을 씁니다.
  Future<SessionStarted> startSession({String? personaType}) async {
    final json = await _apiClient.post(
      '/chat/sessions',
      body: personaType == null ? null : {'persona_type': personaType},
      authenticated: true,
    );
    return SessionStarted.fromJson(json);
  }

  /// 발화 전송.
  ///
  /// ⚠ **스트리밍이 아닙니다.** 서버가 위기 판정과 응답 생성을 병렬로 돌린 뒤
  ///   CRITICAL 이면 생성된 응답을 버리기 때문입니다. 판정 전에 글자를 흘리면
  ///   회수할 수 없습니다. 응답이 한 번에 오는 것은 의도된 설계입니다.
  Future<MessageResult> send(String sessionId, String content) async {
    final json = await _apiClient.post(
      '/chat/sessions/$sessionId/messages',
      body: {'content': content},
      authenticated: true,
    );
    return MessageResult.fromJson(json);
  }

  /// 세션 종료. 서버가 LLM 요약을 만들어 session_summary 에 넣습니다.
  Future<ChatSessionDetail> endSession(String sessionId) async {
    final json = await _apiClient.patch(
      '/chat/sessions/$sessionId/end',
      authenticated: true,
    );
    return ChatSessionDetail.fromJson(json);
  }

  /// 대화 기록 목록 — MAIN_CHAT_02 ❹. 본문은 오지 않습니다.
  Future<List<ChatSessionSummary>> listSessions({
    int limit = 20,
    int offset = 0,
  }) async {
    final rows = await _apiClient.getList(
      '/chat/sessions',
      queryParameters: {'limit': '$limit', 'offset': '$offset'},
      authenticated: true,
    );
    return rows.map(ChatSessionSummary.fromJson).toList();
  }

  /// 상세 — ❺. messages 는 PII 가 마스킹된 상태입니다.
  /// 열려 있는 대화 하나 — `MLCM_220` 6단계.
  ///
  /// **선제 접촉이 만든 세션을 앱이 발견하는 경로입니다.** 앱은 자기가
  /// 시작한 대화만 알고 있어서, 서버가 먼저 만든 세션은 물어보지 않으면
  /// 못 찾습니다.
  ///
  /// ⚠ 없으면 서버가 **204** 를 줍니다. `ApiClient` 는 본문 없는 응답을
  ///   빈 맵으로 돌려주므로 그걸로 판별합니다.
  Future<ActiveSession?> activeSession() async {
    final json =
        await _apiClient.get('/chat/sessions/active', authenticated: true);
    if (json.isEmpty) return null;
    return ActiveSession.fromJson(json);
  }

  Future<ChatSessionDetail> getSession(String sessionId) async {
    final json = await _apiClient.get(
      '/chat/sessions/$sessionId',
      authenticated: true,
    );
    return ChatSessionDetail.fromJson(json);
  }

  Future<void> deleteSession(String sessionId) =>
      _apiClient.delete('/chat/sessions/$sessionId', authenticated: true);
}
