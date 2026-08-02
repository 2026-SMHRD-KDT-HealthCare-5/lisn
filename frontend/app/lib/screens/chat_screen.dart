import 'package:flutter/material.dart';

import '../models/auth_models.dart' show ApiException;
import '../models/chat_models.dart';
import '../services/app_services.dart';
import '../services/chat_service.dart';
import '../services/settings_service.dart';
import '../theme/app_theme.dart';
import '../widgets/common_widgets.dart';
import 'chat_history_screen.dart';
import 'emergency_screen.dart';

enum ChatPersona {
  feeling(
    code: 'FRIEND',
    tag: 'F',
    label: '따스한 공감형',
    description: '감정을 먼저 들어주고\n따뜻하게 위로해요.',
  ),
  thinking(
    code: 'COUNSELOR',
    tag: 'T',
    label: '현실적인 조언형',
    description: '상황을 객관적으로 살피고\n해결책을 함께 찾아요.',
  );

  const ChatPersona({
    required this.code,
    required this.tag,
    required this.label,
    required this.description,
  });

  /// 서버 persona_type. schema.sql 의 CHECK 값과 같아야 합니다.
  final String code;

  /// 카드 위 표식. 화면설명의 `[F]`·`[T]` 와 같습니다.
  final String tag;

  /// 화면에 보이는 이름.
  ///
  /// ⚠ **화면설계서 `MAIN_CHAT_01` 과 01 프로젝트 기획서가 정본입니다.**
  ///   전에는 앱만 「다정한 공감가/이성적인 분석가」를 쓰고 있었습니다. 문서
  ///   3종(화면설계서·기획서·시안)이 모두 지금 이름을 쓰는데 앱 혼자
  ///   달랐습니다 — 임의로 바꾸지 마세요.
  ///
  /// ⚠ 이름을 여기 모아둔 이유도 같습니다. 전에는 `personaName` 과 카드에
  ///   각각 적혀 있어서 한쪽만 고치면 조용히 갈렸습니다.
  final String label;

  /// 카드 설명. 시안(`docs/design/MAIN_CHAT_01.png`)과 같은 문구입니다.
  final String description;

  /// 대화 화면 머리말에 쓰는 표기.
  String get titled => '[$tag] $label';
}

class ChatMessage {
  const ChatMessage(this.text, {required this.fromUser});
  final String text;
  final bool fromUser;
}

/// MAIN_CHAT_01 · MAIN_CHAT_02
///
/// ⚠ **스트리밍을 쓰지 않습니다.** 서버가 위기 판정과 응답 생성을 병렬로
///   돌린 뒤 CRITICAL 이면 생성된 응답을 버리기 때문입니다. 판정 전에 흘린
///   글자는 회수할 수 없습니다. 응답이 한 번에 오는 건 의도된 설계입니다.
class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key, this.chatService, this.settingsService});

  /// 테스트에서 가짜 서비스를 넣기 위한 통로. 평소에는 null 이고
  /// AppServices.chat 을 씁니다.
  final ChatService? chatService;

  /// 최근에 고른 성격(`USERS.persona_type`)을 읽고 쓰는 데 씁니다.
  ///
  /// ⚠ 주입 통로를 지우지 마세요. 없을 때 `AppServices.settings` 를 직접 쓰다가
  ///   테스트에서 진짜 네트워크로 나가 「최근 대화」 표시가 안 뜬 적이 있습니다.
  final SettingsService? settingsService;

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final pageController = PageController(viewportFraction: .9);
  final inputController = TextEditingController();
  final scrollController = ScrollController();

  ChatService get _chat => widget.chatService ?? AppServices.chat;
  SettingsService get _settings =>
      widget.settingsService ?? AppServices.settings;

  ChatPersona persona = ChatPersona.feeling;

  /// 서버에 저장된 성격(`USERS.persona_type`). 마지막으로 대화한 성격입니다.
  ///
  /// 카드에 「최근 대화」 표시를 붙이는 데 씁니다. **기본으로 떠 있는 것만으로는
  /// 그게 저장된 값인지 그냥 첫 카드인지 알 수 없습니다.**
  ChatPersona? lastUsed;
  bool conversation = false;
  List<ChatMessage> messages = [];

  String? sessionId;
  bool starting = false;
  bool sending = false;

  @override
  void initState() {
    super.initState();
    _applySavedPersona();
  }

  /// 설정에 저장된 성격(`USERS.persona_type`)을 첫 선택으로 맞춥니다.
  ///
  /// 설정 화면 ❸ 이 「현재 챗봇 성격」을 보여주는데, 챗봇을 열 때마다 항상
  /// 첫 카드로 돌아가면 그 표시가 거짓이 됩니다.
  ///
  /// ⚠ 실패해도 조용히 넘어갑니다. 기본 선택이 어긋나는 것뿐이고, 사용자는
  ///   어차피 카드를 넘겨 고를 수 있습니다. 여기서 오류를 띄우면 대화를
  ///   시작하기도 전에 실패 문구부터 보게 됩니다.
  Future<void> _applySavedPersona() async {
    try {
      final saved = (await _settings.profile()).personaType;
      final match = ChatPersona.values.where((p) => p.code == saved);
      if (!mounted || match.isEmpty) return;
      final found = match.first;
      setState(() {
        lastUsed = found;
        persona = found;
      });
      if (pageController.hasClients) {
        pageController.jumpToPage(ChatPersona.values.indexOf(found));
      }
    } catch (_) {
      // 기본 선택만 못 맞춘 것이라 그대로 진행합니다.
    }
  }

  @override
  void dispose() {
    pageController.dispose();
    inputController.dispose();
    scrollController.dispose();
    super.dispose();
  }

  String get personaName => persona.titled;

  void _toast(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));
  }

  String _errorText(Object e) =>
      e is ApiException ? e.message : '요청을 처리하지 못했습니다.';

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!scrollController.hasClients) return;
      scrollController.jumpTo(scrollController.position.maxScrollExtent);
    });
  }

  Future<void> startConversation(ChatPersona selected) async {
    if (starting) return;
    setState(() {
      persona = selected;
      starting = true;
    });
    try {
      final session =
          await _chat.startSession(personaType: selected.code);
      if (!mounted) return;

      // 고른 성격을 **기본값으로도 저장**합니다(`USERS.persona_type`).
      // 안 하면 설정 화면 ❸ 의 「현재 챗봇 성격」이 실제와 어긋납니다.
      //
      // ⚠ 대화 시작을 막지 않습니다. 실패해도 이번 대화는 고른 성격으로
      //   진행되고, 기본값만 예전 값으로 남습니다.
      setState(() => lastUsed = selected);
      _settings
          .updateProfile(personaType: selected.code)
          .then((_) {}, onError: (Object e) {
        debugPrint('[chat] 최근 성격 저장 실패: $e');
      });
      setState(() {
        sessionId = session.sessionId;
        conversation = true;
        // 첫 인사도 서버가 만듭니다. 페르소나 문구가 두 곳에 있으면 어긋납니다.
        messages = [ChatMessage(session.greeting, fromUser: false)];
      });
    } catch (e) {
      _toast(_errorText(e));
    } finally {
      if (mounted) setState(() => starting = false);
    }
  }

  Future<void> send() async {
    final text = inputController.text.trim();
    if (text.isEmpty || sending) return;
    final id = sessionId;
    if (id == null) return;

    setState(() {
      messages.add(ChatMessage(text, fromUser: true));
      inputController.clear();
      sending = true;
    });
    _scrollToEnd();

    try {
      final result = await _chat.send(id, text);
      if (!mounted) return;

      // ⚠ EMERGENCY 면 답변을 그리지 않고 긴급 상담으로 전환합니다.
      //   MLCM_510 2단계. 서버도 이때 reply 를 null 로 내려보냅니다.
      if (result.risk.action == ChatAction.emergency) {
        setState(() => sending = false);
        await Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => const EmergencyScreen(),
            fullscreenDialog: true,
          ),
        );
        return;
      }

      setState(() {
        if (result.reply != null) {
          messages.add(ChatMessage(result.reply!, fromUser: false));
        }
        sending = false;
      });
      _scrollToEnd();
    } catch (e) {
      if (!mounted) return;
      setState(() => sending = false);
      _toast(_errorText(e));
    }
  }

  /// 세션 종료. 서버가 요약을 만들고 ended_at 을 기록합니다.
  ///
  /// 종료에 실패해도 화면은 닫습니다. 세션이 열린 채로 남아도
  /// 비활성 상태가 되면 서버가 정리하고, 여기서 사용자를 붙잡아둘 이유가 없습니다.
  Future<void> endConversation() async {
    final id = sessionId;
    setState(() {
      conversation = false;
      sessionId = null;
      messages = [];
    });
    if (id == null) return;
    try {
      await _chat.endSession(id);
    } catch (_) {
      // 조용히 넘어간다.
    }
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
        child: conversation ? _conversationView() : _selectionView());
  }

  Widget _selectionView() {
    return Column(
      children: [
        _ChatHeader(
            title: 'AI 챗봇',
            onHistory: () => Navigator.of(context).push(MaterialPageRoute(
                builder: (_) => ChatHistoryScreen(chatService: _chat)))),
        const Padding(
          padding: EdgeInsets.fromLTRB(22, 20, 22, 12),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('대화 성격 선택',
                style: TextStyle(
                    fontSize: 10,
                    color: AppColors.primary,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.2)),
            SizedBox(height: 10),
            Text('오늘은 어떤 방식으로\n이야기 나눌까요?',
                style: TextStyle(
                    fontSize: 27,
                    height: 1.3,
                    color: AppColors.navy,
                    fontWeight: FontWeight.w900)),
            SizedBox(height: 7),
            Text('좌우로 넘겨 성격을 고른 후 카드를 눌러주세요.',
                style: TextStyle(fontSize: 11, color: AppColors.muted)),
          ]),
        ),
        Expanded(
          child: PageView(
            controller: pageController,
            onPageChanged: (index) =>
                setState(() => persona = ChatPersona.values[index]),
            children: [
              _PersonaCard(
                  persona: ChatPersona.feeling,
                  lastUsed: lastUsed == ChatPersona.feeling,
                  onTap: () => startConversation(ChatPersona.feeling)),
              _PersonaCard(
                  persona: ChatPersona.thinking,
                  lastUsed: lastUsed == ChatPersona.thinking,
                  onTap: () => startConversation(ChatPersona.thinking)),
            ],
          ),
        ),
        Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(2, (index) {
              final active = ChatPersona.values[index] == persona;
              return AnimatedContainer(
                  duration: const Duration(milliseconds: 250),
                  width: active ? 24 : 7,
                  height: 7,
                  margin: const EdgeInsets.symmetric(horizontal: 4),
                  decoration: BoxDecoration(
                      color:
                          active ? AppColors.primary : const Color(0xFFD6DBEA),
                      borderRadius: BorderRadius.circular(5)));
            })),
        const SizedBox(height: 11),
        const Text('‹   좌우로 스와이프하여 변경   ›',
            style: TextStyle(fontSize: 9, color: AppColors.muted)),
        const SizedBox(height: 18),
      ],
    );
  }

  Widget _conversationView() {
    return Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(15, 8, 15, 12),
        child: Row(children: [
          IconButton(
              onPressed: endConversation,
              icon: const Icon(Icons.arrow_back_rounded)),
          MaeumeMascot(
              size: 45,
              mood: persona == ChatPersona.thinking
                  ? MascotMood.thinking
                  : MascotMood.smile),
          const SizedBox(width: 10),
          Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                Text(personaName,
                    style: const TextStyle(
                        fontSize: 12, fontWeight: FontWeight.w800)),
                const Text('●  지금 대화할 수 있어요',
                    style: TextStyle(fontSize: 9, color: Color(0xFF61C799)))
              ])),
          TextButton(
              onPressed: endConversation,
              child: const Text('대화 종료',
                  style: TextStyle(fontSize: 10, color: AppColors.muted))),
        ]),
      ),
      const Divider(height: 1, color: AppColors.line),
      Expanded(
        child: ListView.builder(
          controller: scrollController,
          padding: const EdgeInsets.symmetric(horizontal: 17, vertical: 22),
          // 응답을 기다리는 동안 말풍선 한 칸을 더 그립니다.
          itemCount: messages.length + (sending ? 1 : 0),
          itemBuilder: (_, index) {
            if (index >= messages.length) return const _TypingBubble();
            return _MessageBubble(
              messages[index],
              thinking: persona == ChatPersona.thinking,
            );
          },
        ),
      ),
      SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: Row(
            children: ['마음이 답답해요', '스트레스가 많았어요']
                .map((text) => Padding(
                    padding: const EdgeInsets.only(right: 7),
                    child: ActionChip(
                        label: Text(text, style: const TextStyle(fontSize: 10)),
                        onPressed: () => inputController.text = text)))
                .toList()),
      ),
      Padding(
        padding: const EdgeInsets.fromLTRB(15, 8, 15, 14),
        // 마이크 버튼을 두지 않습니다 — 음성 입력(STT)은 이번 범위에서
        // 제외됐습니다(2026.08.01). 눌리는데 동작하지 않으면 시연에서 드러납니다.
        child: TextField(
          controller: inputController,
          enabled: !sending,
          onSubmitted: (_) => send(),
          maxLength: 2000, // 서버 MessageIn 제약과 동일
          decoration: InputDecoration(
            counterText: '',
            hintText: sending ? '답변을 기다리는 중이에요...' : '메시지를 입력해주세요...',
            suffixIcon: IconButton(
                onPressed: sending ? null : send,
                icon: CircleAvatar(
                    backgroundColor:
                        sending ? AppColors.muted : AppColors.primary,
                    child: const Icon(Icons.send_rounded,
                        size: 17, color: Colors.white))),
            border: OutlineInputBorder(
                borderSide: BorderSide.none,
                borderRadius: BorderRadius.circular(16)),
          ),
        ),
      ),
    ]);
  }
}

class _PersonaCard extends StatelessWidget {
  const _PersonaCard(
      {required this.persona, required this.onTap, this.lastUsed = false});
  final ChatPersona persona;
  final VoidCallback onTap;

  /// 마지막으로 대화한 성격인지. 앱을 껐다 켜도 유지됩니다.
  final bool lastUsed;

  @override
  Widget build(BuildContext context) {
    final feeling = persona == ChatPersona.feeling;
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 6, 8, 12),
      child: InkWell(
        borderRadius: BorderRadius.circular(25),
        onTap: onTap,
        child: Ink(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(25),
            gradient: LinearGradient(
                colors: feeling
                    ? const [Colors.white, Color(0xFFE5EBFF)]
                    : const [Colors.white, Color(0xFFDDF1F4)],
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter),
            border: Border.all(
                color: feeling
                    ? const Color(0xFFDCE4FB)
                    : const Color(0xFFD4E9EE)),
          ),
          child: Stack(children: [
            // ⚠ 「최근 대화」 표시를 빼지 마세요. 저장된 성격 카드가 먼저 뜨긴
            //   하지만, 표시가 없으면 **그게 내가 고른 값인지 그냥 첫 카드인지
            //   알 수 없습니다.** 설정에서 페르소나 항목을 뺀 것도 이 표시가
            //   그 역할을 대신하기 때문입니다.
            if (lastUsed)
              Positioned(
                  top: 20,
                  left: 20,
                  child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 5),
                      decoration: BoxDecoration(
                          color: Colors.white.withAlpha(210),
                          borderRadius: BorderRadius.circular(12)),
                      child: Text('최근 대화',
                          style: TextStyle(
                              fontSize: 9,
                              fontWeight: FontWeight.w800,
                              color: feeling
                                  ? const Color(0xFF6678CE)
                                  : const Color(0xFF38889A))))),
            Positioned(
                top: 18,
                right: 20,
                child: CircleAvatar(
                    radius: 18,
                    backgroundColor: Colors.white,
                    child: Text(feeling ? 'F' : 'T',
                        style: TextStyle(
                            fontWeight: FontWeight.w900,
                            color: feeling
                                ? AppColors.primary
                                : AppColors.teal)))),
            // ⚠ 카드 안 내용이 카드보다 커지면 바로 넘칩니다(실제로 31px 넘쳤습니다).
            //   화면 높이는 기기마다 다른데 여기 값은 고정이라, 크기만 줄이면
            //   더 작은 기기에서 또 터집니다.
            //   자리가 있으면 가운데, 모자라면 스크롤되도록 둡니다.
            //   세로 스크롤이라 좌우 페이지 넘김과 부딪히지 않습니다.
            // ⚠ Positioned.fill 을 빼지 마세요. Stack 의 배치 안 된 자식은 느슨한
            //   제약을 받아 **내용 폭만큼 줄고 좌상단에 붙습니다.** 예전 Center 가
            //   하던 일을 여기서 대신합니다.
            Positioned.fill(child: LayoutBuilder(builder: (context, box) {
              return SingleChildScrollView(
                // ⚠ 카드 위아래로 숨 쉴 자리입니다. 빼면 마스코트가 카드
                //   테두리에 붙고 「이 성격으로 대화하기」가 바닥에 닿습니다.
                padding: const EdgeInsets.symmetric(vertical: 18),
                child: ConstrainedBox(
                  constraints:
                      BoxConstraints(minHeight: box.maxHeight - 36),
                  child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
              MaeumeMascot(
                  size: 84,
                  mood: feeling ? MascotMood.smile : MascotMood.thinking),
              const SizedBox(height: 14),
              Text(feeling ? 'FEELING' : 'THINKING',
                  style: TextStyle(
                      fontSize: 9,
                      letterSpacing: 1.8,
                      fontWeight: FontWeight.w900,
                      color: feeling ? AppColors.primary : AppColors.teal)),
              const SizedBox(height: 6),
              Text(persona.label,
                  style: const TextStyle(
                      fontSize: 24,
                      color: AppColors.navy,
                      fontWeight: FontWeight.w900)),
              const SizedBox(height: 9),
              Text(persona.description,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                      fontSize: 12, height: 1.6, color: AppColors.muted)),
              const SizedBox(height: 12),
              Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 13, vertical: 7),
                  decoration: BoxDecoration(
                      color: Colors.white.withAlpha(179),
                      borderRadius: BorderRadius.circular(14)),
                  child: Text(
                      feeling ? '감정 지지 · 경청 · 위로' : '상황 분석 · 문제 해결 · 실행 제안',
                      style: TextStyle(
                          fontSize: 10,
                          color: feeling
                              ? const Color(0xFF6678CE)
                              : const Color(0xFF38889A)))),
              const SizedBox(height: 16),
              Row(mainAxisSize: MainAxisSize.min, children: [
                Text('이 성격으로 대화하기',
                    style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                        color: feeling
                            ? const Color(0xFF5F73DA)
                            : const Color(0xFF38889A))),
                const Icon(Icons.chevron_right_rounded, size: 17)
              ]),
                  ]),
                ),
              );
            })),
          ]),
        ),
      ),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble(this.message, {required this.thinking});
  final ChatMessage message;
  final bool thinking;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment:
          message.fromUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Padding(
        padding: const EdgeInsets.only(bottom: 16),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (!message.fromUser) ...[
              MaeumeMascot(
                  size: 42,
                  mood: thinking ? MascotMood.thinking : MascotMood.smile),
              const SizedBox(width: 9),
            ],
            Flexible(
              child: Container(
                constraints: const BoxConstraints(maxWidth: 280),
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                decoration: BoxDecoration(
                    color: message.fromUser
                        ? const Color(0xFF7889E9)
                        : const Color(0xFFF1F3FA),
                    borderRadius: BorderRadius.circular(15)),
                child: Text(message.text,
                    style: TextStyle(
                        fontSize: 12,
                        height: 1.6,
                        color:
                            message.fromUser ? Colors.white : AppColors.navy)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ChatHeader extends StatelessWidget {
  const _ChatHeader({required this.title, required this.onHistory});
  final String title;
  final VoidCallback onHistory;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
        height: 68,
        child:
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          // 왼쪽은 비워 둡니다. 여기는 탭 루트라 뒤로가기가 없고, 왼쪽 위는
          // 관례상 뒤로가기·메뉴 자리라 동작 버튼을 두면 오인됩니다.
          // 제목이 가운데 오도록 오른쪽 버튼과 같은 폭만 맞춥니다.
          const SizedBox(width: 48),
          Text(title,
              style:
                  const TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
          // 대화 기록 진입점 — MAIN_CHAT_02 · SD-12
          //
          // ⚠ 전에는 `onPressed: () {}` 인 **빈 버튼**이 양쪽에 있었습니다.
          //   눌리는데 아무 일도 안 나면 시연에서 바로 드러납니다(마이크 버튼을
          //   지운 것과 같은 이유). 서버 API 와 ChatService 는 이미 있었고
          //   입구만 없었습니다.
          //
          // 오른쪽에 두는 이유: 화면 동작(action)은 오른쪽이 관례입니다.
          // 검색 아이콘은 없앴습니다 — 화면설계서에 없는 기능이고, 만들려면
          // 서버에 검색 API 부터 있어야 합니다.
          IconButton(
              onPressed: onHistory,
              icon: const Icon(Icons.history_rounded),
              tooltip: '대화 기록'),
        ]));
  }
}

/// 응답을 기다리는 동안 띄우는 말풍선.
///
/// 스트리밍을 쓸 수 없어(위기 판정 전에 글자를 흘릴 수 없음) 응답이 한 번에
/// 옵니다. 그동안 화면이 멈춘 것처럼 보이지 않게 자리를 채웁니다.
class _TypingBubble extends StatelessWidget {
  const _TypingBubble();

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 14),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(15),
          border: Border.all(color: AppColors.line),
        ),
        child: const Row(mainAxisSize: MainAxisSize.min, children: [
          SizedBox(
              width: 13,
              height: 13,
              child: CircularProgressIndicator(
                  strokeWidth: 2, color: AppColors.muted)),
          SizedBox(width: 10),
          Text('마음이가 생각하고 있어요',
              style: TextStyle(fontSize: 10, color: AppColors.muted)),
        ]),
      ),
    );
  }
}
