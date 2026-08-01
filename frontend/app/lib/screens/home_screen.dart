import 'package:flutter/material.dart';

import '../models/auth_models.dart' show ApiException;
import '../models/home_models.dart';
import '../services/app_services.dart';
import '../services/home_service.dart';
import '../theme/app_theme.dart';
import '../widgets/common_widgets.dart';

/// MAIN_HOME_01
///
/// **판단은 서버가 끝냅니다.** 감정→위험도→액션 매핑을 여기서 다시 계산하지
/// 않습니다. 서버가 내려준 action 을 보고 무엇을 그릴지만 정합니다.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, this.userName, this.homeService});

  final String? userName;

  /// 테스트 주입용. 평소에는 null 이고 AppServices.home 을 씁니다.
  final HomeService? homeService;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late Future<HomeSnapshot> _future;

  @override
  void initState() {
    super.initState();
    _future = (widget.homeService ?? AppServices.home).fetch();
  }

  Future<void> _refresh() async {
    final next = (widget.homeService ?? AppServices.home).fetch();
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
            _moodCard(data.emotionToday),
            const SizedBox(height: 10),
            _metrics(data.lifelog),
            const SizedBox(height: 10),
            if (data.aiSummary != null) ...[
              _summary(data.aiSummary!),
              const SizedBox(height: 20),
            ],
            // ⚠ EMERGENCY 면 추천을 그리지 않습니다 — MLCM_510 2단계.
            //   서버도 이때는 recommendations 를 비워 보내지만, 클라이언트도
            //   한 번 더 막습니다. 위기 상황에서 콘텐츠가 뜨면 안 됩니다.
            if (data.action != HomeAction.emergency &&
                data.recommendations.isNotEmpty) ...[
              const SectionTitle('당신을 위한 추천',
                  trailing: Text('더보기  ›',
                      style:
                          TextStyle(fontSize: 10, color: AppColors.primary))),
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
    final greeting = name == null ? '안녕하세요 😊' : '안녕하세요, $name님 😊';
    return Container(
      height: 250,
      padding: const EdgeInsets.fromLTRB(23, 24, 23, 0),
      decoration: const BoxDecoration(
          gradient: LinearGradient(
              colors: [Color(0xFFF9FAFF), Color(0xFFE6EEFD)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight)),
      child: Stack(children: [
        const Align(alignment: Alignment.topLeft, child: LisnBrand()),
        const Align(
            alignment: Alignment.topRight,
            child: Badge(
                smallSize: 7,
                child: Icon(Icons.notifications_none_rounded,
                    color: AppColors.navy))),
        Positioned(
            left: 0,
            top: 58,
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(greeting,
                  style: const TextStyle(
                      fontSize: 21,
                      fontWeight: FontWeight.w900,
                      color: AppColors.navy)),
              const SizedBox(height: 5),
              Text(_heroSub(data),
                  style: const TextStyle(color: AppColors.muted))
            ])),
        Positioned(
            right: -18,
            bottom: 17,
            width: 205,
            height: 205,
            child: Image.asset('assets/images/login_mascot.png',
                fit: BoxFit.cover)),
      ]),
    );
  }

  String _heroSub(HomeSnapshot? data) => switch (data?.action) {
        HomeAction.emergency => '잠시 이야기 나눌까요?',
        HomeAction.content => '오늘도 수고했어요!',
        HomeAction.chat => '오늘 하루는 어땠나요?',
        null => '',
      };

  Widget _moodCard(EmotionToday? emotion) {
    // 분석 기록이 없으면 수치를 지어내지 않습니다. 가입 직후가 이 상태입니다.
    if (emotion == null) {
      return const AppCard(
        child: Column(children: [
          SectionTitle('오늘의 마음 상태'),
          SizedBox(height: 18),
          Row(children: [
            MaeumeMascot(size: 72),
            SizedBox(width: 15),
            Expanded(
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
        const SectionTitle('오늘의 마음 상태',
            trailing: Text('자세히 보기  ›',
                style: TextStyle(fontSize: 10, color: AppColors.primary))),
        const SizedBox(height: 18),
        Row(children: [
          const MaeumeMascot(size: 72),
          const SizedBox(width: 15),
          Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                Text(emotion.emotionName,
                    style: const TextStyle(
                        fontSize: 27,
                        fontWeight: FontWeight.w900,
                        color: AppColors.primary)),
                const SizedBox(height: 5),
                Text(_riskMessage(emotion.riskLevel),
                    style: const TextStyle(
                        fontSize: 10, height: 1.6, color: AppColors.muted))
              ])),
          SizedBox(
              width: 100,
              height: 100,
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
                          fontSize: 22, fontWeight: FontWeight.w900)),
                  const Text('/100',
                      style: TextStyle(fontSize: 9, color: AppColors.muted))
                ])
              ])),
        ]),
      ]),
    );
  }

  /// ⚠ 위기 상황에 경고색이나 위협적인 문구를 쓰지 않습니다.
  ///   불안을 키우면 오히려 앱을 피하게 됩니다. 담담하게 씁니다.
  String _riskMessage(String riskLevel) => switch (riskLevel) {
        'CRITICAL' => '지금 마음이 많이 힘들어 보여요.\n혼자 견디지 않아도 괜찮아요.',
        'CAUTION' => '평소와 조금 다른 하루였네요.\n무리하지 않아도 괜찮아요.',
        _ => '평소보다 안정적인 상태예요.\n잘 관리하고 있어요!',
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
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          mainAxisExtent: 118,
          crossAxisSpacing: 10,
          mainAxisSpacing: 10),
      itemCount: data.length,
      itemBuilder: (_, i) => AppCard(
          child: Row(children: [
        CircleAvatar(
            backgroundColor: data[i].$4,
            child: Icon(data[i].$1, size: 18, color: AppColors.primary)),
        const SizedBox(width: 10),
        Expanded(
            child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
              Text(data[i].$2,
                  style: const TextStyle(fontSize: 10, color: AppColors.muted)),
              const SizedBox(height: 5),
              Text(data[i].$3,
                  style: const TextStyle(
                      fontSize: 15, fontWeight: FontWeight.w800))
            ])),
      ])),
    );
  }

  // 값이 없으면 0 이 아니라 '–' 로 둡니다. "0걸음" 과 "모름" 은 다릅니다.
  String _sleep(int? min) =>
      min == null ? '–' : '${min ~/ 60}시간 ${min % 60}분';

  String _comma(int n) => n.toString().replaceAllMapped(
      RegExp(r'(\d)(?=(\d{3})+$)'), (m) => '${m[1]},');

  String _collected(DateTime? at) {
    if (at == null) return '–';
    final diff = DateTime.now().difference(at);
    if (diff.inMinutes < 60) return '${diff.inMinutes}분 전';
    if (diff.inHours < 24) return '${diff.inHours}시간 전';
    return '${diff.inDays}일 전';
  }

  Widget _summary(String text) {
    return AppCard(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const SectionTitle('오늘의 한 줄 요약'),
      const SizedBox(height: 14),
      Row(children: [
        const MaeumeMascot(size: 52),
        const SizedBox(width: 12),
        Expanded(
            child: Text(text,
                style: const TextStyle(
                    fontSize: 11, height: 1.7, color: AppColors.muted)))
      ]),
    ]));
  }

  Widget _recommendations(List<ContentCard> cards) {
    const palette = [AppColors.mint, AppColors.blue, Color(0xFFFFF0E9)];
    return SizedBox(
      height: 132,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: cards.length,
        separatorBuilder: (_, __) => const SizedBox(width: 10),
        itemBuilder: (_, i) => Container(
          width: 132,
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
              color: palette[i % palette.length],
              borderRadius: BorderRadius.circular(15)),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(_categoryLabel(cards[i].category),
                style:
                    const TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
            const SizedBox(height: 2),
            Expanded(
                child: Text(cards[i].title,
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        fontSize: 9, height: 1.5, color: AppColors.muted))),
            Text(_categoryEmoji(cards[i].category),
                style: const TextStyle(fontSize: 25))
          ]),
        ),
      ),
    );
  }

  String _categoryLabel(String category) => switch (category) {
        'MUSIC' => '음악',
        'FOOD' => '먹을거리',
        'EXERCISE' => '몸 움직이기',
        'ARTICLE' => '읽을거리',
        _ => '추천',
      };

  String _categoryEmoji(String category) => switch (category) {
        'MUSIC' => '♫',
        'FOOD' => '☕',
        'EXERCISE' => '🌿',
        _ => '📖',
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
