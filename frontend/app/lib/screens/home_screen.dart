import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/auth_models.dart' show ApiException;
import '../models/home_models.dart';
import '../services/app_services.dart';
import '../services/home_service.dart';
import '../theme/app_theme.dart';
import 'chat_screen.dart';
import 'report_screen.dart';
import '../widgets/common_widgets.dart';

/// MAIN_HOME_01
///
/// **판단은 서버가 끝냅니다.** 감정→위험도→액션 매핑을 여기서 다시 계산하지
/// 않습니다. 서버가 내려준 action 을 보고 무엇을 그릴지만 정합니다.
/// 추천 콘텐츠 카드를 눌렀을 때 링크를 여는 함수. 테스트에서 갈아끼웁니다.
typedef ContentLinkLauncher = Future<bool> Function(Uri url);

class HomeScreen extends StatefulWidget {
  const HomeScreen({
    super.key,
    this.userName,
    this.homeService,
    this.linkLauncher,
  });

  final String? userName;

  /// 테스트 주입용. 평소에는 null 이고 AppServices.home 을 씁니다.
  final HomeService? homeService;

  /// 테스트 주입용. 평소에는 null 이고 외부 브라우저로 엽니다.
  final ContentLinkLauncher? linkLauncher;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late Future<HomeSnapshot> _future;

  /// 마지막으로 성공한 홈 내용.
  ///
  /// 당겨서 새로고침할 때 화면을 로딩으로 갈아치우면 **보고 있던 내용이 통째로
  /// 사라졌다 돌아옵니다.** RefreshIndicator 가 이미 위에서 진행 표시를 하고
  /// 있으므로, 본문은 그대로 두는 편이 맞습니다.
  HomeSnapshot? _last;

  @override
  void initState() {
    super.initState();
    _future = _loadAndKeep();
  }

  /// 성공한 결과만 보관합니다.
  ///
  /// ⚠ `then(...).ignore()` 를 async/await 로 바꾸지 마세요. 조회가 즉시 실패하면
  ///   FutureBuilder 가 구독하기 전에 오류가 도착해 미처리 예외로 보고됩니다.
  ///   자세한 내용은 report_screen.dart 의 같은 함수 주석에 있습니다.
  Future<HomeSnapshot> _loadAndKeep() {
    final future = (widget.homeService ?? AppServices.home).fetch();
    future.then((snapshot) {
      if (mounted) _last = snapshot;
    }).ignore();
    return future;
  }

  Future<void> _refresh() async {
    final next = _loadAndKeep();
    setState(() => _future = next);
    await next.catchError((_) => throw Exception());
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: RefreshIndicator(
        onRefresh: () => _refresh().catchError((_) {}),
        child: FutureBuilder<HomeSnapshot>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              // 보여줄 것이 있으면 로딩으로 덮지 않습니다. RefreshIndicator 가
              // 이미 위에서 진행을 알리고 있고, 본문까지 비우면 화면이 크게 튑니다.
              if (_last != null) {
                return StaleContent(child: _content(_last!));
              }
              return _scroll([const _Loading()]);
            }
            if (snap.hasError) {
              return _scroll([
                _ErrorCard(
                  message: snap.error is ApiException
                      ? (snap.error as ApiException).message
                      : '정보를 불러오지 못했습니다.',
                  onRetry: _refresh,
                )
              ]);
            }
            return _content(snap.data!);
          },
        ),
      ),
    );
  }

  /// 오류·로딩 때도 스크롤이 살아 있어야 당겨서 새로고침이 됩니다.
  Widget _scroll(List<Widget> children) => CustomScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        slivers: [
          SliverToBoxAdapter(child: _hero(null)),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 25),
            sliver: SliverList.list(children: children),
          ),
        ],
      );

  Widget _content(HomeSnapshot data) {
    return CustomScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      slivers: [
        SliverToBoxAdapter(child: _hero(data)),
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 25),
          sliver: SliverList.list(children: [
            // ⚠ **감정 카드보다 위입니다.** 선제 접촉은 사용자가 앱을 열
            //   이유가 없는 상태에서 유일하게 닿는 경로라, 스크롤해야
            //   보이면 존재 의미가 없습니다.
            if (data.pendingOutreach != null) ...[
              _outreachCard(data.pendingOutreach!),
              const SizedBox(height: 10),
            ],
            _moodCard(data.emotionToday),
            const SizedBox(height: 10),
            _metrics(data.lifelog),
            const SizedBox(height: 10),
            if (data.aiSummary != null) ...[
              _summary(data.aiSummary!, data.emotionToday?.riskLevel),
              const SizedBox(height: 20),
            ],
            // ⚠ EMERGENCY 면 추천을 그리지 않습니다 — MLCM_510 2단계.
            //   서버도 이때는 recommendations 를 비워 보내지만, 클라이언트도
            //   한 번 더 막습니다. 위기 상황에서 콘텐츠가 뜨면 안 됩니다.
            if (data.action != HomeAction.emergency &&
                data.recommendations.isNotEmpty) ...[
              const SectionTitle('맞춤 힐링 콘텐츠',
                  trailing: Text('음악 · 운동 · 문장',
                      style: TextStyle(fontSize: 10, color: AppColors.muted))),
              const SizedBox(height: 11),
              _recommendations(data.recommendations),
            ],
          ]),
        ),
      ],
    );
  }

  Widget _hero(HomeSnapshot? data) {
    final name = widget.userName;
    // ⚠ 위기·주의일 때는 웃는 이모지를 붙이지 않습니다. 아래 마음 상태 카드가
    //   「지금 마음이 많이 힘들어 보여요」라고 말하는 화면에서 상단이 웃고 있으면
    //   공감이 아니라 무시로 읽힙니다.
    final cheerful =
        MaeumeMascot.moodFor(data?.emotionToday?.riskLevel) == MascotMood.smile;
    final face = cheerful ? ' 😊' : '';
    final greeting = name == null ? '안녕하세요$face' : '안녕하세요, $name님$face';
    return Container(
      // 높이를 줄여 「오늘의 마음 상태」가 위로 올라오게 합니다. 홈에서 가장
      // 먼저 봐야 할 것은 브랜드가 아니라 오늘 상태입니다.
      height: 214,
      padding: const EdgeInsets.fromLTRB(22, 20, 22, 0),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
            colors: [Color(0xFFF7F9FF), Color(0xFFDDE7FB)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight),
        // 아래를 둥글게 잘라 흰 카드들이 그 위에 얹힌 것처럼 보이게 합니다.
        borderRadius: BorderRadius.vertical(bottom: Radius.circular(30)),
      ),
      child: Stack(clipBehavior: Clip.none, children: [
        // 마스코트를 **글자 뒤쪽**에 깔고 오른쪽으로 흘려보냅니다.
        // 앞에 두면 인사말과 무게가 비슷해져 시선이 갈립니다.
        Positioned(
            right: -30,
            bottom: -6,
            width: 196,
            height: 196,
            child: Opacity(
                opacity: .95,
                child: Image.asset('assets/images/login_mascot.png',
                    fit: BoxFit.contain))),

        const Align(
          alignment: Alignment.topLeft,
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                '마음이',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w900,
                  color: AppColors.navy,
                ),
              ),
              SizedBox(width: 2),
              Icon(Icons.favorite_rounded, size: 15, color: AppColors.primary),
            ],
          ),
        ),

        // ⚠ **알림 종 아이콘을 되살리지 마세요.**
        //
        //   여기에 `Badge(smallSize: 7)` 로 빨간 점이 찍힌 종이 있었습니다.
        //   문제가 셋이었습니다.
        //     1. 화면설계서 `MAIN_HOME_01` ❶~❺ 에 **알림 항목이 없습니다**
        //     2. 서버에 알림 API 가 없습니다. 설정 화면은 이 점을 스위치 비활성화와
        //        「알림 기능은 준비 중이에요」로 정직하게 알리는데, 홈이 빨간 점으로
        //        **읽지 않은 알림이 있다고 주장**해 두 화면이 서로 모순됐습니다
        //     3. `IconButton` 도 아닌 정적 `Icon` 이라 **눌리지도 않았습니다**
        //
        //   FCM 을 붙이고 알림 목록 API 가 생기면 그때 넣으세요. 그 전까지는
        //   없는 편이 낫습니다 — 마이크 버튼·챗봇 검색 아이콘과 같은 판단입니다.

        Positioned(
            left: 0,
            right: 96,
            bottom: 34,
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(greeting,
                  style: const TextStyle(
                      fontSize: 29,
                      height: 1.15,
                      letterSpacing: -1,
                      fontWeight: FontWeight.w900,
                      color: AppColors.navy)),
              const SizedBox(height: 7),
              Text(_heroSub(data),
                  style: const TextStyle(
                      fontSize: 13, height: 1.5, color: Color(0xFF7E88A6)))
            ])),
      ]),
    );
  }

  /// ⚠ 느낌표를 쓰지 않습니다. 힘든 상태에서 밝은 어조는 「내 상태를 모르는
  ///   앱」으로 읽혀 신뢰를 깎습니다. 담담하게 곁에 있는 문장으로 씁니다.
  String _heroSub(HomeSnapshot? data) => switch (data?.action) {
        HomeAction.emergency => '잠시 이야기 나눌까요?',
        HomeAction.content => '오늘 하루도 애쓰셨어요.',
        HomeAction.chat => '오늘 하루는 어땠나요?',
        null => '',
      };

  Widget _moodCard(EmotionToday? emotion) {
    // 분석 기록이 없으면 수치를 지어내지 않습니다. 가입 직후가 이 상태입니다.
    if (emotion == null) {
      return AppCard(
        child: Column(children: [
          const SectionTitle('오늘의 마음 상태'),
          const SizedBox(height: 18),
          Row(children: [
            _feelingMascot(72),
            const SizedBox(width: 15),
            const Expanded(
                child: Text('아직 분석된 기록이 없어요.\n하루 이상 데이터가 모이면 알려드릴게요.',
                    style: TextStyle(
                        fontSize: 11, height: 1.6, color: AppColors.muted))),
          ]),
        ]),
      );
    }

    final score = emotion.emotionScore.clamp(0, 100).toDouble();
    return AppCard(
      child: Column(children: [
        SectionTitle('오늘의 마음 상태',
            // 정서 리포트(MAIN_REPORT_01)로 들어갑니다. 메뉴경로는
            // 라이프로그 하위지만, 오늘 상태를 본 자리에서 바로 기간별
            // 추이로 넘어가는 흐름이 자연스럽습니다.
            trailing: GestureDetector(
              onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const ReportScreen())),
              child: const Text('자세히 보기  ›',
                  style: TextStyle(fontSize: 10, color: AppColors.primary)),
            )),
        const SizedBox(height: 18),
        // 마스코트 · 문구 · 점수를 한 줄에 둡니다.
        //
        // ⚠ 문구가 카드 중앙에 오도록 폭을 벌어 놨습니다(마스코트 62 · 링 86).
        //   기본값(72 · 100)이면 문구에 143dp 밖에 안 남아 「보 / 여요」처럼
        //   단어 중간에서 잘립니다. 상태를 알리는 문장이 그렇게 보이면 안 됩니다.
        //   **크기를 되돌리려면 아래 문구 길이도 같이 확인하세요.**
        Row(children: [
          // ⚠ 위험도에 따라 표정이 갈립니다. 「많이 힘들어 보여요」 옆에서
          //   웃고 있으면 공감이 아니라 무시로 읽힙니다.
          _feelingMascot(62, riskLevel: emotion.riskLevel),
          const SizedBox(width: 12),
          // ⚠ **감정 이름(emotion_name)을 사용자에게 보여주지 않습니다.**
          //
          //   마스터 9종에 「위기」·「절망」이 들어 있습니다. 힘들어하는 사람 화면에
          //   그 단어를 헤드라인으로 박으면 관찰이 아니라 **사람에 대한 판정**으로
          //   읽힙니다. 02 요구사항의 「진단 금지」에 걸리고, 라벨이 내면화되면
          //   상태를 더 굳힙니다.
          //
          //   아래 문구가 이미 상태를 전달하므로 라벨이 정보를 더하지 않습니다.
          //   관리자 화면은 그대로 둡니다 — 담당자가 판단하는 데 필요한 용어입니다.
          Expanded(
              child: Text(_riskMessage(emotion.riskLevel),
                  style: const TextStyle(
                      fontSize: 12,
                      height: 1.75,
                      fontWeight: FontWeight.w700,
                      color: AppColors.navy))),
          const SizedBox(width: 4),
          SizedBox(
              width: 86,
              height: 86,
              child: Stack(alignment: Alignment.center, children: [
                Positioned.fill(
                    child: CircularProgressIndicator(
                        value: score / 100,
                        strokeWidth: 5,
                        backgroundColor: const Color(0xFFE2E6F2),
                        color: AppColors.primary)),
                Column(mainAxisSize: MainAxisSize.min, children: [
                  Text(score.round().toString(),
                      style: const TextStyle(
                          fontSize: 21, fontWeight: FontWeight.w900)),
                  const Text('/100',
                      style: TextStyle(fontSize: 9, color: AppColors.muted))
                ])
              ])),
        ]),
      ]),
    );
  }

  Widget _feelingMascot(double size, {String? riskLevel}) {
    // 위기 상태에서 웃는 얼굴은 사용자의 어려움을 가볍게 여기는 인상을 줄 수
    // 있으므로 기존의 비웃는 표정을 유지합니다.
    if (riskLevel == 'CRITICAL') {
      return MaeumeMascot(
        size: size,
        mood: MaeumeMascot.moodFor(riskLevel),
      );
    }
    return SizedBox(
      width: size,
      height: size,
      child: Image.asset(
        'assets/images/home_emotion.png',
        fit: BoxFit.contain,
        alignment: Alignment.center,
        semanticLabel: '오늘의 마음 상태 캐릭터',
      ),
    );
  }

  /// ⚠ 위기 상황에 경고색이나 위협적인 문구를 쓰지 않습니다.
  ///   불안을 키우면 오히려 앱을 피하게 됩니다. 담담하게 씁니다.
  ///
  /// ⚠ **한 줄이 카드 안에서 안 접히도록 길이를 맞춰 뒀습니다.** 가장 긴 줄이
  ///   「혼자 견디지 않아도 괜찮아요.」(13자)입니다. 늘리면 단어 중간에서 잘려
  ///   「보 / 여요」처럼 보입니다. **고치면 실기기에서 줄바꿈을 확인하세요.**
  String _riskMessage(String riskLevel) => switch (riskLevel) {
        'CRITICAL' => '마음이 많이 힘들어 보여요.\n혼자 견디지 않아도 괜찮아요.',
        'CAUTION' => '평소와 조금 다른 하루예요.\n무리하지 않아도 괜찮아요.',
        _ => '평소보다 안정적인 상태예요.\n잘 지내고 계세요.',
      };

  Widget _metrics(LifelogSummary log) {
    final data = <(IconData, String, String, Color)>[
      (
        Icons.dark_mode_rounded,
        '수면 시간',
        _sleep(log.totalSleepMin),
        AppColors.purple
      ),
      (
        Icons.directions_walk_rounded,
        '활동량',
        log.steps == null ? '–' : '${_comma(log.steps!)} 걸음',
        AppColors.mint
      ),
      (
        Icons.favorite_rounded,
        'HRV',
        log.hrv == null ? '–' : '${log.hrv!.toStringAsFixed(0)} ms',
        AppColors.pink
      ),
      (
        Icons.schedule_rounded,
        '마지막 수집',
        _collected(log.collectedAt),
        AppColors.blue
      ),
    ];
    Widget metricCard(int i) => SizedBox(
          height: 60,
          child: AppCard(
              key: ValueKey('lifelog-metric-$i'),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              child: Row(children: [
                CircleAvatar(
                    radius: 16,
                    backgroundColor: data[i].$4,
                    child:
                        Icon(data[i].$1, size: 16, color: AppColors.primary)),
                const SizedBox(width: 9),
                Expanded(
                    child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                      Text(data[i].$2,
                          style: const TextStyle(
                              fontSize: 10, color: AppColors.muted)),
                      const SizedBox(height: 3),
                      Text(data[i].$3,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                              fontSize: 14, fontWeight: FontWeight.w800))
                    ])),
              ])),
        );

    // 네 카드의 높이를 명시적으로 60dp로 고정해 기존 118dp의 빈 공간을 없앱니다.
    Widget metricRow(int start) => Row(children: [
          Expanded(child: metricCard(start)),
          const SizedBox(width: 10),
          Expanded(child: metricCard(start + 1)),
        ]);

    return Column(children: [
      metricRow(0),
      const SizedBox(height: 10),
      metricRow(2),
    ]);
  }

  // 값이 없으면 0 이 아니라 '–' 로 둡니다. "0걸음" 과 "모름" 은 다릅니다.
  String _sleep(int? min) => min == null ? '–' : '${min ~/ 60}시간 ${min % 60}분';

  String _comma(int n) => n
      .toString()
      .replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+$)'), (m) => '${m[1]},');

  String _collected(DateTime? at) {
    if (at == null) return '–';
    final diff = DateTime.now().difference(at);
    if (diff.inMinutes < 60) return '${diff.inMinutes}분 전';
    if (diff.inHours < 24) return '${diff.inHours}시간 전';
    return '${diff.inDays}일 전';
  }

  /// 시스템이 먼저 건 대화 — `MLCM_220` 6단계.
  ///
  /// ⚠ **「알림」이 아니라 「대화」로 보여줍니다.** 배지·빨간 점을 붙이면
  ///   처리해야 할 일이 되고, 정신건강 앱에서 그건 부담입니다. 말을 걸어둔
  ///   것이 그대로 보이는 편이 낫습니다.
  ///
  /// ⚠ **경고색을 쓰지 않습니다.** 위기 화면에 빨강·주황을 쓰면 불안을 키워
  ///   회피를 유발합니다. 주목도는 위치(맨 위)로 만듭니다.
  Widget _outreachCard(PendingOutreach o) {
    return AppCard(
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () => _openOutreach(o),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            _feelingMascot(44),
            const SizedBox(width: 12),
            const Expanded(
              child: Text('마음이가 먼저 말을 걸었어요',
                  style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: AppColors.navy)),
            ),
          ]),
          const SizedBox(height: 12),
          // 첫 문장을 그대로 보여줍니다. 「새 메시지가 있습니다」로 감추면
          // 왜 말을 걸었는지 모른 채 열어야 합니다 — 근거를 함께 보여주는
          // 것이 감시로 읽히지 않게 하는 조건입니다.
          Text(o.opener,
              style: const TextStyle(
                  fontSize: 12, height: 1.6, color: AppColors.navy)),
          const SizedBox(height: 12),
          const Align(
            alignment: Alignment.centerRight,
            child: Text('답장하기  ›',
                style: TextStyle(fontSize: 11, color: AppColors.primary)),
          ),
        ]),
      ),
    );
  }

  /// 성격 선택을 건너뛰고 **그 세션으로 바로** 들어갑니다.
  ///
  /// 돌아오면 홈을 다시 불러 카드를 걷습니다 — 답을 했는데 카드가 남아
  /// 있으면 안 읽은 것처럼 보입니다.
  Future<void> _openOutreach(PendingOutreach o) async {
    await Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => ChatScreen(resumeSessionId: o.sessionId),
    ));
    if (mounted) await _refresh().catchError((_) {});
  }

  Widget _summary(String text, String? riskLevel) {
    return AppCard(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const SectionTitle('오늘의 한 줄 요약'),
      const SizedBox(height: 14),
      Row(children: [
        _feelingMascot(52, riskLevel: riskLevel),
        const SizedBox(width: 12),
        Expanded(
            child: Text(text,
                style: const TextStyle(
                    fontSize: 11, height: 1.7, color: AppColors.muted)))
      ]),
    ]));
  }

  Widget _recommendations(List<ContentCard> cards) {
    // 홈에서는 사용자가 고르기 쉬운 세 갈래만 보여줍니다. 서버가 같은
    // 카테고리를 여러 건 내려줘도 카테고리별 첫 카드 하나만 사용합니다.
    const categories = ['MUSIC', 'EXERCISE', 'ARTICLE'];
    final selected = <ContentCard>[];
    for (final category in categories) {
      for (final card in cards) {
        if (card.category == category) {
          selected.add(card);
          break;
        }
      }
    }

    return SizedBox(
      height: 142,
      child: Row(
        children: [
          for (var i = 0; i < selected.length; i++) ...[
            if (i > 0) const SizedBox(width: 9),
            Expanded(child: _recommendationCard(selected[i])),
          ],
        ],
      ),
    );
  }

  Widget _recommendationCard(ContentCard card) => InkWell(
        key: ValueKey('content-card-${card.contentId}'),
        onTap: () => _openContent(card),
        borderRadius: BorderRadius.circular(17),
        child: Ink(
          padding: const EdgeInsets.fromLTRB(12, 12, 10, 10),
          decoration: BoxDecoration(
            color: _categoryColor(card.category),
            borderRadius: BorderRadius.circular(17),
          ),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
              width: 31,
              height: 31,
              decoration: const BoxDecoration(
                  color: Color(0xCCFFFFFF), shape: BoxShape.circle),
              child: Icon(_categoryIcon(card.category),
                  size: 17, color: AppColors.primary),
            ),
            const SizedBox(height: 8),
            Text(_categoryLabel(card.category),
                style:
                    const TextStyle(fontSize: 11, fontWeight: FontWeight.w800)),
            const SizedBox(height: 3),
            Expanded(
              child: Text(card.title,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      fontSize: 9, height: 1.4, color: AppColors.muted)),
            ),
            const Align(
              alignment: Alignment.bottomRight,
              child: Icon(Icons.arrow_forward_rounded,
                  size: 15, color: AppColors.primary),
            ),
          ]),
        ),
      );

  /// 추천 콘텐츠를 외부 브라우저로 엽니다 — MLCM_400.
  ///
  /// ⚠ 앱 안에서 열지 않습니다. 외부 기관 자료를 앱 화면 안에 띄우면 **우리가
  ///   만든 내용처럼 읽힙니다.** 긴급 상담 화면에서 브랜드를 뺀 것과 같은
  ///   이유입니다(emergency_screen.dart 주석 참고).
  Future<void> _openContent(ContentCard card) async {
    final uri = Uri.tryParse(card.externalUrl);
    var opened = false;
    if (uri != null && uri.hasScheme) {
      try {
        opened = await (widget.linkLauncher ??
            (u) => launchUrl(u, mode: LaunchMode.externalApplication))(uri);
      } catch (_) {
        opened = false;
      }
    }
    if (!mounted || opened) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('링크를 열 수 없어요. 잠시 후 다시 시도해 주세요.')),
    );
  }

  String _categoryLabel(String category) => switch (category) {
        'MUSIC' => '음악',
        'EXERCISE' => '운동',
        'ARTICLE' => '문구',
        _ => '추천',
      };

  Color _categoryColor(String category) => switch (category) {
        'MUSIC' => const Color(0xFFF0EEFF),
        'EXERCISE' => AppColors.mint,
        _ => const Color(0xFFFFF0E9),
      };

  IconData _categoryIcon(String category) => switch (category) {
        'MUSIC' => Icons.music_note_rounded,
        'EXERCISE' => Icons.directions_walk_rounded,
        _ => Icons.format_quote_rounded,
      };
}

class _Loading extends StatelessWidget {
  const _Loading();

  @override
  Widget build(BuildContext context) => const Padding(
        padding: EdgeInsets.symmetric(vertical: 60),
        child: Center(child: CircularProgressIndicator(strokeWidth: 2.5)),
      );
}

class _ErrorCard extends StatelessWidget {
  const _ErrorCard({required this.message, required this.onRetry});

  final String message;
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(children: [
        const SizedBox(height: 4),
        Text(message,
            textAlign: TextAlign.center,
            style: const TextStyle(
                fontSize: 12, height: 1.6, color: AppColors.muted)),
        const SizedBox(height: 14),
        TextButton(onPressed: () => onRetry(), child: const Text('다시 시도')),
      ]),
    );
  }
}
