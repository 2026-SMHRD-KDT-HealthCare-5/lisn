import 'package:flutter/material.dart';

import '../theme/app_theme.dart';
import '../widgets/common_widgets.dart';

enum ChatPersona { feeling, thinking }

class ChatMessage {
  const ChatMessage(this.text, {required this.fromUser});
  final String text;
  final bool fromUser;
}

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final pageController = PageController(viewportFraction: .9);
  final inputController = TextEditingController();
  ChatPersona persona = ChatPersona.feeling;
  bool conversation = false;
  List<ChatMessage> messages = [];

  @override
  void dispose() {
    pageController.dispose();
    inputController.dispose();
    super.dispose();
  }

  String get personaName =>
      persona == ChatPersona.feeling ? '[F] 다정한 공감가' : '[T] 이성적인 분석가';

  void startConversation(ChatPersona selected) {
    setState(() {
      persona = selected;
      conversation = true;
      messages = [
        ChatMessage(
          selected == ChatPersona.feeling
              ? '지은님, 오늘 하루는 어떠셨나요? 어떤 마음이든 편하게 이야기해 주세요.'
              : '지은님, 오늘 있었던 일을 함께 정리해볼까요? 가장 신경 쓰였던 일부터 알려주세요.',
          fromUser: false,
        ),
      ];
    });
  }

  void send() {
    final text = inputController.text.trim();
    if (text.isEmpty) return;
    setState(() {
      messages.add(ChatMessage(text, fromUser: true));
      messages.add(ChatMessage(
        persona == ChatPersona.feeling
            ? '많이 힘드셨겠어요. 그런 마음이 드는 건 너무 자연스러워요. 오늘의 지은님에게 가장 필요한 건 무엇일까요?'
            : '상황을 하나씩 정리해볼게요. 가장 스트레스가 컸던 순간과 바꿀 수 있는 부분을 나눠서 살펴볼까요?',
        fromUser: false,
      ));
      inputController.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
        child: conversation ? _conversationView() : _selectionView());
  }

  Widget _selectionView() {
    return Column(
      children: [
        const _ChatHeader(title: 'AI 챗봇'),
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
              onPressed: () => setState(() => conversation = false),
              icon: const Icon(Icons.arrow_back_rounded)),
          MaeumeMascot(size: 45, thinking: persona == ChatPersona.thinking),
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
              onPressed: () => setState(() => conversation = false),
              child: const Text('대화 종료',
                  style: TextStyle(fontSize: 10, color: AppColors.muted))),
        ]),
      ),
      const Divider(height: 1, color: AppColors.line),
      Expanded(
        child: ListView.builder(
          padding: const EdgeInsets.symmetric(horizontal: 17, vertical: 22),
          itemCount: messages.length,
          itemBuilder: (_, index) => _MessageBubble(
            messages[index],
            thinking: persona == ChatPersona.thinking,
          ),
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
        child: TextField(
          controller: inputController,
          onSubmitted: (_) => send(),
          decoration: InputDecoration(
            hintText: '메시지를 입력해주세요...',
            prefixIcon: const Icon(Icons.mic_none_rounded),
            suffixIcon: IconButton(
                onPressed: send,
                icon: const CircleAvatar(
                    backgroundColor: AppColors.primary,
                    child: Icon(Icons.send_rounded,
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
      padding: const EdgeInsets.fromLTRB(8, 8, 8, 18),
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
            Center(
                child: Column(mainAxisSize: MainAxisSize.min, children: [
              MaeumeMascot(size: 132, thinking: !feeling),
              const SizedBox(height: 24),
              Text(feeling ? 'FEELING' : 'THINKING',
                  style: TextStyle(
                      fontSize: 9,
                      letterSpacing: 1.8,
                      fontWeight: FontWeight.w900,
                      color: feeling ? AppColors.primary : AppColors.teal)),
              const SizedBox(height: 7),
              Text(feeling ? '다정한 공감가' : '이성적인 분석가',
                  style: const TextStyle(
                      fontSize: 24,
                      color: AppColors.navy,
                      fontWeight: FontWeight.w900)),
              const SizedBox(height: 10),
              Text(
                  feeling
                      ? '감정을 먼저 이해하고\n따뜻하게 공감해요'
                      : '상황을 정리하고\n현실적인 해결책을 찾아요',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                      fontSize: 12, height: 1.6, color: AppColors.muted)),
              const SizedBox(height: 14),
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
              const SizedBox(height: 23),
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
            ])),
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
              MaeumeMascot(size: 42, thinking: thinking),
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
  const _ChatHeader({required this.title});
  final String title;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
        height: 68,
        child:
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          IconButton(onPressed: () {}, icon: const Icon(Icons.menu_rounded)),
          Text(title,
              style:
                  const TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
          IconButton(onPressed: () {}, icon: const Icon(Icons.search_rounded))
        ]));
  }
}
