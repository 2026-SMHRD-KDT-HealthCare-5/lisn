import 'package:flutter/material.dart';

import '../theme/app_theme.dart';
import '../widgets/common_widgets.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: CustomScrollView(
        slivers: [
          SliverToBoxAdapter(child: _hero()),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 25),
            sliver: SliverList.list(children: [
              _moodCard(),
              const SizedBox(height: 10),
              _metrics(),
              const SizedBox(height: 10),
              _summary(),
              const SizedBox(height: 20),
              const SectionTitle('당신을 위한 추천',
                  trailing: Text('더보기  ›',
                      style:
                          TextStyle(fontSize: 10, color: AppColors.primary))),
              const SizedBox(height: 11),
              _recommendations(),
            ]),
          ),
        ],
      ),
    );
  }

  Widget _hero() {
    return Container(
      height: 250,
      padding: const EdgeInsets.fromLTRB(23, 24, 23, 0),
      decoration: const BoxDecoration(
          gradient: LinearGradient(
              colors: [Color(0xFFF9FAFF), Color(0xFFE6EEFD)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight)),
      child: Stack(children: [
        const Align(alignment: Alignment.topLeft, child: MaeumeBrand()),
        const Align(
            alignment: Alignment.topRight,
            child: Badge(
                smallSize: 7,
                child: Icon(Icons.notifications_none_rounded,
                    color: AppColors.navy))),
        const Positioned(
            left: 0,
            top: 58,
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('안녕하세요, 지은님 😊',
                  style: TextStyle(
                      fontSize: 21,
                      fontWeight: FontWeight.w900,
                      color: AppColors.navy)),
              SizedBox(height: 5),
              Text('오늘도 수고했어요!', style: TextStyle(color: AppColors.muted))
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

  Widget _moodCard() {
    return const AppCard(
      child: Column(children: [
        SectionTitle('오늘의 마음 상태',
            trailing: Text('자세히 보기  ›',
                style: TextStyle(fontSize: 10, color: AppColors.primary))),
        SizedBox(height: 18),
        Row(children: [
          MaeumeMascot(size: 72),
          SizedBox(width: 15),
          Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                Text('안정',
                    style: TextStyle(
                        fontSize: 27,
                        fontWeight: FontWeight.w900,
                        color: AppColors.primary)),
                SizedBox(height: 5),
                Text('평소보다 안정적인 상태예요.\n잘 관리하고 있어요!',
                    style: TextStyle(
                        fontSize: 10, height: 1.6, color: AppColors.muted))
              ])),
          SizedBox(
              width: 100,
              height: 100,
              child: Stack(alignment: Alignment.center, children: [
                Positioned.fill(
                    child: CircularProgressIndicator(
                        value: .72,
                        strokeWidth: 5,
                        backgroundColor: Color(0xFFE2E6F2),
                        color: AppColors.primary)),
                Column(mainAxisSize: MainAxisSize.min, children: [
                  Text('72',
                      style:
                          TextStyle(fontSize: 22, fontWeight: FontWeight.w900)),
                  Text('/100',
                      style: TextStyle(fontSize: 9, color: AppColors.muted))
                ])
              ])),
        ]),
      ]),
    );
  }

  Widget _metrics() {
    const data = [
      (Icons.favorite_rounded, '심박수', '72 bpm', AppColors.pink),
      (Icons.dark_mode_rounded, '수면 시간', '7시간 35분', AppColors.purple),
      (Icons.directions_walk_rounded, '활동량', '8,521 걸음', AppColors.mint),
      (Icons.auto_awesome_rounded, '스트레스', '보통', AppColors.blue),
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

  Widget _summary() {
    return const AppCard(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      SectionTitle('오늘의 한 줄 요약'),
      SizedBox(height: 14),
      Row(children: [
        MaeumeMascot(size: 52),
        SizedBox(width: 12),
        Expanded(
            child: Text('오늘은 평소보다 안정적인 하루였어요.\n이런 당신을 응원해요! 💜',
                style: TextStyle(
                    fontSize: 11, height: 1.7, color: AppColors.muted)))
      ]),
    ]));
  }

  Widget _recommendations() {
    const data = [
      ('마음 정리', '5분 명상', '🌿', AppColors.mint),
      ('음악', '힐링 음악', '♫', AppColors.blue),
      ('따뜻한 글귀', '다정한 문장', '☕', Color(0xFFFFF0E9))
    ];
    return SizedBox(
      height: 132,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: data.length,
        separatorBuilder: (_, __) => const SizedBox(width: 10),
        itemBuilder: (_, i) => Container(
          width: 132,
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
              color: data[i].$4, borderRadius: BorderRadius.circular(15)),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(data[i].$1,
                style:
                    const TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
            Text(data[i].$2,
                style: const TextStyle(fontSize: 9, color: AppColors.muted)),
            const Spacer(),
            Text(data[i].$3, style: const TextStyle(fontSize: 29))
          ]),
        ),
      ),
    );
  }
}
