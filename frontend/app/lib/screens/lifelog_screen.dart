import 'package:flutter/material.dart';

import '../theme/app_theme.dart';
import '../widgets/common_widgets.dart';

class LifelogScreen extends StatefulWidget {
  const LifelogScreen({super.key});

  @override
  State<LifelogScreen> createState() => _LifelogScreenState();
}

class _LifelogScreenState extends State<LifelogScreen> {
  int range = 1;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Column(children: [
        SizedBox(
            height: 68,
            child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  IconButton(
                      onPressed: () {}, icon: const Icon(Icons.menu_rounded)),
                  const Text('라이프로그',
                      style:
                          TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
                  IconButton(
                      onPressed: () {}, icon: const Icon(Icons.search_rounded))
                ])),
        Expanded(
            child: ListView(
                padding: const EdgeInsets.fromLTRB(15, 8, 15, 25),
                children: [
              SegmentedButton<int>(
                  segments: const [
                    ButtonSegment(value: 0, label: Text('일간')),
                    ButtonSegment(value: 1, label: Text('주간')),
                    ButtonSegment(value: 2, label: Text('월간'))
                  ],
                  selected: {
                    range
                  },
                  onSelectionChanged: (value) =>
                      setState(() => range = value.first),
                  showSelectedIcon: false),
              const SizedBox(height: 16),
              _emotionChart(),
              const SizedBox(height: 22),
              const SectionTitle('주요 지표'),
              const SizedBox(height: 10),
              const _LogMetric(
                  icon: Icons.favorite_rounded,
                  title: '심박수',
                  value: '72 bpm',
                  color: AppColors.pink),
              const _LogMetric(
                  icon: Icons.dark_mode_rounded,
                  title: '수면 시간',
                  value: '7시간 35분',
                  color: AppColors.purple),
              const _LogMetric(
                  icon: Icons.directions_walk_rounded,
                  title: '활동량',
                  value: '8,521 걸음',
                  color: AppColors.mint),
              const _LogMetric(
                  icon: Icons.auto_awesome_rounded,
                  title: '스트레스',
                  value: '보통',
                  color: AppColors.blue),
              const SizedBox(height: 7),
              FilledButton.tonal(
                  onPressed: () {}, child: const Text('상세 라이프로그 보기  ›')),
            ])),
      ]),
    );
  }

  Widget _emotionChart() {
    return AppCard(
        child: Column(children: [
      const SectionTitle('감정 변화',
          trailing: Row(mainAxisSize: MainAxisSize.min, children: [
            Icon(Icons.calendar_today_outlined,
                size: 13, color: AppColors.muted),
            SizedBox(width: 5),
            Text('7.16 - 7.22',
                style: TextStyle(fontSize: 9, color: AppColors.muted))
          ])),
      const SizedBox(height: 18),
      SizedBox(
          height: 115,
          width: double.infinity,
          child: CustomPaint(painter: _LineChartPainter())),
      const Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
        Text('수', style: TextStyle(fontSize: 9, color: AppColors.muted)),
        Text('목', style: TextStyle(fontSize: 9, color: AppColors.muted)),
        Text('금', style: TextStyle(fontSize: 9, color: AppColors.muted)),
        Text('토', style: TextStyle(fontSize: 9, color: AppColors.muted)),
        Text('일', style: TextStyle(fontSize: 9, color: AppColors.muted)),
        Text('월', style: TextStyle(fontSize: 9, color: AppColors.muted)),
        Text('오늘', style: TextStyle(fontSize: 9, color: AppColors.muted))
      ]),
    ]));
  }
}

class _LineChartPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final values = [.72, .48, .61, .28, .51, .2, .34];
    final path = Path();
    for (var i = 0; i < values.length; i++) {
      final point =
          Offset(size.width * i / (values.length - 1), size.height * values[i]);
      i == 0
          ? path.moveTo(point.dx, point.dy)
          : path.lineTo(point.dx, point.dy);
    }
    final fill = Path.from(path)
      ..lineTo(size.width, size.height)
      ..lineTo(0, size.height)
      ..close();
    canvas.drawPath(
        fill,
        Paint()
          ..shader = const LinearGradient(
                  colors: [Color(0x4D7890EF), Color(0x007890EF)],
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter)
              .createShader(Offset.zero & size));
    canvas.drawPath(
        path,
        Paint()
          ..color = AppColors.primary
          ..strokeWidth = 3
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round);
    for (var i = 0; i < values.length; i++) {
      final point =
          Offset(size.width * i / (values.length - 1), size.height * values[i]);
      canvas.drawCircle(point, 4, Paint()..color = Colors.white);
      canvas.drawCircle(
          point,
          4,
          Paint()
            ..color = AppColors.primary
            ..strokeWidth = 2
            ..style = PaintingStyle.stroke);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _LogMetric extends StatelessWidget {
  const _LogMetric(
      {required this.icon,
      required this.title,
      required this.value,
      required this.color});
  final IconData icon;
  final String title;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: AppCard(
          child: Row(children: [
        CircleAvatar(
            backgroundColor: color,
            child: Icon(icon, color: AppColors.primary, size: 19)),
        const SizedBox(width: 13),
        Expanded(
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title,
              style: const TextStyle(fontSize: 10, color: AppColors.muted)),
          const SizedBox(height: 4),
          Text(value,
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800))
        ])),
        Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
            decoration: BoxDecoration(
                color: AppColors.soft, borderRadius: BorderRadius.circular(10)),
            child: const Text('정상',
                style: TextStyle(fontSize: 9, color: AppColors.primary))),
      ])),
    );
  }
}
