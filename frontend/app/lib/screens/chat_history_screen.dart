/// 대화 기록 — MAIN_CHAT_02 · MLCM_310
///
/// 화면설계서 개정안 `SD-12` 「대화 기록 복원」이 요구하는 화면입니다.
/// 서버 API(`GET /chat/sessions`·`GET /chat/sessions/{id}`·`DELETE`)와
/// `ChatService` 는 이미 있었는데 **들어갈 입구가 없었습니다.** 챗봇 화면 왼쪽
/// 위 버튼이 `onPressed: () {}` 인 빈 버튼이었습니다.
library;

import 'package:flutter/material.dart';

import '../models/auth_models.dart' show ApiException;
import '../models/chat_models.dart';
import '../services/app_services.dart';
import '../services/chat_service.dart';
import '../theme/app_theme.dart';
import '../widgets/common_widgets.dart';

class ChatHistoryScreen extends StatefulWidget {
  const ChatHistoryScreen({super.key, this.chatService});

  /// 테스트 주입용. 평소에는 null 이고 AppServices.chat 을 씁니다.
  final ChatService? chatService;

  @override
  State<ChatHistoryScreen> createState() => _ChatHistoryScreenState();
}

class _ChatHistoryScreenState extends State<ChatHistoryScreen> {
  ChatService get _chat => widget.chatService ?? AppServices.chat;

  /// 마지막으로 성공한 목록.
  ///
  /// 지우고 다시 불러올 때 목록을 비우면 화면이 통째로 접혔다 펴집니다.
  /// 앱 다른 화면과 같은 규칙입니다(`frontend/app/README.md`).
  List<ChatSessionSummary>? sessions;
  bool pending = true;
  String? error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      pending = true;
      error = null;
    });
    try {
      final rows = await _chat.listSessions();
      if (!mounted) return;
      setState(() {
        sessions = rows;
        pending = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        error = e is ApiException ? e.message : '대화 기록을 불러오지 못했습니다.';
        pending = false;
      });
    }
  }

  /// 삭제는 되돌릴 수 없으므로 한 번 더 묻습니다.
  ///
  /// ⚠ 대화에는 힘들었던 순간이 담겨 있습니다. 실수로 지웠을 때 복구할 방법이
  ///   없으므로, 손이 미끄러지는 정도로는 지워지지 않게 합니다.
  Future<void> _confirmDelete(ChatSessionSummary s) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('이 대화를 지울까요?',
            style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800)),
        content: const Text('지운 대화는 되돌릴 수 없어요.',
            style: TextStyle(fontSize: 12, height: 1.6)),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('그대로 둘게요')),
          TextButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('지우기',
                  style: TextStyle(color: Color(0xFF987466)))),
        ],
      ),
    );
    if (ok != true) return;

    try {
      await _chat.deleteSession(s.sessionId);
      if (!mounted) return;
      // 서버가 지웠으니 목록에서도 뺍니다. 다시 조회하지 않는 이유는
      // 목록 전체가 깜빡이는 것을 피하기 위해서입니다.
      setState(() => sessions =
          sessions?.where((x) => x.sessionId != s.sessionId).toList());
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(e is ApiException ? e.message : '지우지 못했습니다.')));
    }
  }

  Future<void> _openDetail(ChatSessionSummary s) async {
    Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => _SessionDetailScreen(summary: s, chatService: _chat)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('대화 기록',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
        centerTitle: true,
      ),
      body: SafeArea(child: _body()),
    );
  }

  Widget _body() {
    if (error != null && sessions == null) {
      return _notice(error!, onRetry: _load);
    }
    if (sessions == null) {
      return const Center(child: CircularProgressIndicator(strokeWidth: 2.5));
    }
    if (sessions!.isEmpty) {
      return _notice('아직 나눈 대화가 없어요.\n챗봇에서 이야기를 시작해보세요.');
    }

    final list = RefreshIndicator(
      onRefresh: _load,
      child: ListView.separated(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(15, 14, 15, 25),
        itemCount: sessions!.length,
        separatorBuilder: (_, __) => const SizedBox(height: 10),
        itemBuilder: (_, i) => _card(sessions![i]),
      ),
    );
    // 다시 불러오는 중에는 목록을 두고 흐리게만 처리합니다.
    return pending ? StaleContent(child: list) : list;
  }

  Widget _card(ChatSessionSummary s) {
    final friend = s.personaType == 'FRIEND';
    return AppCard(
      child: InkWell(
        onTap: () => _openDetail(s),
        borderRadius: BorderRadius.circular(12),
        child: Row(children: [
          // 성격은 이름이 아니라 배지로 보여줍니다. 목록에서 이름까지 쓰면
          // 요약을 읽을 자리가 없어집니다.
          CircleAvatar(
            radius: 17,
            backgroundColor:
                friend ? const Color(0xFFE8ECFF) : const Color(0xFFDDF1F4),
            child: Text(friend ? 'F' : 'T',
                style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w900,
                    color: friend ? AppColors.primary : AppColors.teal)),
          ),
          const SizedBox(width: 12),
          Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                Row(children: [
                  Text(_stamp(s.startedAt),
                      style: const TextStyle(
                          fontSize: 11, fontWeight: FontWeight.w800)),
                  const SizedBox(width: 7),
                  // 진행 중인 대화는 구분해 줍니다. 요약이 없는 이유이기도 합니다.
                  if (!s.isEnded)
                    const Text('진행 중',
                        style: TextStyle(
                            fontSize: 9,
                            fontWeight: FontWeight.w800,
                            color: Color(0xFF61C799))),
                ]),
                const SizedBox(height: 4),
                Text(
                    // 요약은 종료 시 LLM 이 만듭니다. 실패하면 null 이라
                    // 「요약 없음」이 아니라 상황을 그대로 적습니다.
                    s.sessionSummary ??
                        (s.isEnded ? '요약을 만들지 못했어요.' : '아직 진행 중인 대화예요.'),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        fontSize: 11, height: 1.5, color: AppColors.muted)),
              ])),
          IconButton(
            onPressed: () => _confirmDelete(s),
            icon: const Icon(Icons.delete_outline_rounded,
                size: 19, color: AppColors.muted),
            tooltip: '이 대화 지우기',
          ),
        ]),
      ),
    );
  }

  Widget _notice(String text, {VoidCallback? onRetry}) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(30),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const MaeumeMascot(size: 64),
          const SizedBox(height: 16),
          Text(text,
              textAlign: TextAlign.center,
              style: const TextStyle(
                  fontSize: 12, height: 1.7, color: AppColors.muted)),
          if (onRetry != null) ...[
            const SizedBox(height: 12),
            TextButton(onPressed: onRetry, child: const Text('다시 시도')),
          ],
        ]),
      ),
    );
  }

  String _stamp(DateTime at) {
    final d = at.toLocal();
    return '${d.year}.${d.month}.${d.day} '
        '${d.hour.toString().padLeft(2, '0')}:'
        '${d.minute.toString().padLeft(2, '0')}';
  }
}

/// 지난 대화 한 건 상세.
///
/// 읽기 전용입니다. 종료된 대화에 이어 쓰면 그 시점의 감정 맥락과 섞입니다.
class _SessionDetailScreen extends StatefulWidget {
  const _SessionDetailScreen(
      {required this.summary, required this.chatService});

  final ChatSessionSummary summary;
  final ChatService chatService;

  @override
  State<_SessionDetailScreen> createState() => _SessionDetailScreenState();
}

class _SessionDetailScreenState extends State<_SessionDetailScreen> {
  ChatSessionDetail? detail;
  String? error;

  @override
  void initState() {
    super.initState();
    widget.chatService.getSession(widget.summary.sessionId).then((d) {
      if (mounted) setState(() => detail = d);
    }).catchError((Object e) {
      if (mounted) {
        setState(
            () => error = e is ApiException ? e.message : '대화를 불러오지 못했습니다.');
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('지난 대화',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
        centerTitle: true,
      ),
      body: SafeArea(child: _body()),
    );
  }

  Widget _body() {
    if (error != null) {
      return Center(
          child: Text(error!,
              style: const TextStyle(fontSize: 12, color: AppColors.muted)));
    }
    if (detail == null) {
      return const Center(child: CircularProgressIndicator(strokeWidth: 2.5));
    }

    return ListView(
      padding: const EdgeInsets.fromLTRB(17, 18, 17, 26),
      children: [
        // ⚠ 상세에는 요약을 넣지 않습니다 — 목록에서 이미 보여줍니다(2026.08.04).
        //   목록은 「어느 대화였는지 고르는」 자리라 요약이 맞고, 상세는
        //   「그때 무슨 말이 오갔는지 다시 읽는」 자리라 실제 대화가 맞습니다.
        //   둘 다 넣으면 같은 내용을 두 번 읽게 됩니다.
        //   요약 자체는 목록·관리자 쪽에서 계속 쓰므로 서버에 그대로 둡니다.
        for (final m in detail!.messages) _bubble(m),
      ],
    );
  }

  Widget _bubble(ChatBubble m) {
    // ⚠ 위기 안내 말풍선은 일반 답변과 구분합니다. 그때 답변이 없었던 이유가
    //   기록에 남아야 나중에 읽을 때 「앱이 무시했다」로 오해하지 않습니다.
    if (m.isEmergency) {
      return Container(
        margin: const EdgeInsets.symmetric(vertical: 6),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
            color: const Color(0xFFF4F6FC),
            borderRadius: BorderRadius.circular(14)),
        child: Text(m.content,
            style: const TextStyle(
                fontSize: 11, height: 1.7, color: AppColors.muted)),
      );
    }

    return Align(
      alignment: m.isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 5),
        padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 11),
        constraints: const BoxConstraints(maxWidth: 260),
        decoration: BoxDecoration(
          color: m.isUser ? AppColors.primary : Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: m.isUser ? null : Border.all(color: AppColors.line),
        ),
        child: Text(m.content,
            style: TextStyle(
                fontSize: 12,
                height: 1.6,
                color: m.isUser ? Colors.white : AppColors.navy)),
      ),
    );
  }
}
