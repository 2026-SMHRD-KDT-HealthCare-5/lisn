import 'package:flutter/material.dart';

import '../models/auth_models.dart' show ApiException;
import '../models/chat_models.dart';
import '../services/app_services.dart';
import '../services/chat_service.dart';
import '../theme/app_theme.dart';
import '../widgets/common_widgets.dart';
import 'chat_history_screen.dart';
import 'emergency_screen.dart';

enum ChatPersona {
  feeling('FRIEND'),
  thinking('COUNSELOR');

  const ChatPersona(this.code);

  /// 서버 persona_type. schema.sql 의 CHECK 값과 같아야 합니다.
  final String code;
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
  const ChatScreen({super.key, this.chatService});

  /// 테스트에서 가짜 서비스를 넣기 위한 통로. 평소에는 null 이고
  /// AppServices.chat 을 씁니다.
  final ChatService? chatService;

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final pageController = PageController(viewportFraction: .9);
  final inputController = TextEditingController();
  final scrollController = ScrollController();

  ChatService get _chat => widget.chatService ?? AppServices.chat;

  ChatPersona persona = ChatPersona.feeling;
  bool conversation = false;
  List<ChatMessage> messages = [];

  String? sessionId;
  bool starting = false;
  bool sending = false;

  @override
  void dispose() {
    pageController.dispose();
    inputController.dispose();
    scrollController.dispose();
    super.dispose();
  }

  String get personaName =>
      persona == ChatPersona.feeling ? '[F] 다정한 공감가' : '[T] 이성적인 분석가';

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
                  onTap: () => startConversation(ChatPersona.feeling)),
              _PersonaCard(
                  persona: ChatPersona.thinking,
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
  const _PersonaCard({required this.persona, required this.onTap});
  final ChatPersona persona;
  final VoidCallback onTap;

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
              Text(feeling ? '다정한 공감가' : '이성적인 분석가',
                  style: const TextStyle(
                      fontSize: 24,
                      color: AppColors.navy,
                      fontWeight: FontWeight.w900)),
              const SizedBox(height: 9),
              Text(
                  feeling
                      ? '감정을 먼저 이해하고\n따뜻하게 공감해요'
                      : '상황을 정리하고\n현실적인 해결책을 찾아요',
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
          // 대화 기록 진입점 — MAIN_CHAT_02 · SD-12
          //
          // ⚠ 전에는 `onPressed: () {}` 인 **빈 버튼**이었습니다. 눌리는데 아무
          //   일도 안 나면 시연에서 바로 드러납니다(마이크 버튼을 지운 것과
          //   같은 이유). 서버 API 와 ChatService 는 이미 있었고 입구만 없었습니다.
          IconButton(
              onPressed: onHistory,
              icon: const Icon(Icons.history_rounded),
              tooltip: '대화 기록'),
          Text(title,
              style:
                  const TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
          // 오른쪽 검색 아이콘은 **없앴습니다.** 대화 내용 검색은 화면설계서에
          // 없는 기능이고, 만들면 서버에 검색 API 부터 있어야 합니다.
          // 자리를 비워 제목이 가운데 오도록 폭만 맞춥니다.
          const SizedBox(width: 48),
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
