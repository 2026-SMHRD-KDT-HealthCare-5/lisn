import 'package:flutter/material.dart';

import '../models/auth_models.dart' show ApiException;
import '../models/lifelog_models.dart';
import '../services/app_services.dart';
import '../services/lifelog_service.dart';
import '../theme/app_theme.dart';
import 'report_screen.dart';
import '../widgets/common_widgets.dart';

/// MAIN_LIFELOG_01
///
/// ⚠ **수집은 이 화면이 하지 않습니다.** Health Connect 는 Android on-device
///   권한 모델이라 앱이 읽어서 서버로 push 하는 구조입니다(안건 1-1).
///   여기서는 적재된 것을 조회해 그리기만 합니다.
class LifelogScreen extends StatefulWidget {
  const LifelogScreen({super.key, this.lifelogService});

  /// 테스트 주입용. 평소에는 null 이고 AppServices.lifelog 를 씁니다.
  final LifelogService? lifelogService;

  @override
  State<LifelogScreen> createState() => _LifelogScreenState();
}

class _LifelogScreenState extends State<LifelogScreen> {
  /// 0 일간 · 1 주간 · 2 월간
  int range = 1;
  late Future<List<LifelogEntry>> _future;

  LifelogService get _service => widget.lifelogService ?? AppServices.lifelog;

  static const _days = [1, 7, 30];

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<LifelogEntry>> _load() {
    final now = DateTime.now();
    return _service.fetch(
      from: now.subtract(Duration(days: _days[range])),
      to: now,
      limit: 500,
    );
  }

  void _changeRange(int next) {
    setState(() {
      range = next;
      _future = _load();
    });
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Column(children: [
        SizedBox(
          height: 68,
          child: Row(children: [
            const SizedBox(width: 15),
            const Expanded(
                child: Text('라이프로그',
                    style:
                        TextStyle(fontSize: 18, fontWeight: FontWeight.w900))),
            // 화면설계서 메뉴경로: 라이프로그 / 정서 리포트
            TextButton(
              onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const ReportScreen())),
              child: const Text('정서 리포트  ›',
                  style: TextStyle(fontSize: 11, color: AppColors.primary)),
            ),
          ]),
        ),
        Expanded(
          child: FutureBuilder<List<LifelogEntry>>(
            future: _future,
            builder: (context, snap) {
              final body = switch (snap) {
                AsyncSnapshot(connectionState: ConnectionState.waiting) =>
                  [const _Centered(child: CircularProgressIndicator(strokeWidth: 2.5))],
                AsyncSnapshot(hasError: true, :final error) => [
                    _Centered(
                      child: Column(children: [
                        Text(
                            error is ApiException
                                ? error.message
                                : '기록을 불러오지 못했습니다.',
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                                fontSize: 12, color: AppColors.muted)),
                        const SizedBox(height: 12),
                        TextButton(
                            onPressed: () =>
                                setState(() => _future = _load()),
                            child: const Text('다시 시도')),
                      ]),
                    )
                  ],
                _ => _body(snap.data ?? const []),
              };

              return RefreshIndicator(
                onRefresh: () async => setState(() => _future = _load()),
                child: ListView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.fromLTRB(15, 8, 15, 25),
                  children: [
                    SegmentedButton<int>(
                        segments: const [
                          ButtonSegment(value: 0, label: Text('일간')),
                          ButtonSegment(value: 1, label: Text('주간')),
                          ButtonSegment(value: 2, label: Text('월간'))
                        ],
                        selected: {range},
                        onSelectionChanged: (v) => _changeRange(v.first),
                        showSelectedIcon: false),
                    const SizedBox(height: 16),
                    ...body,
                  ],
                ),
              );
            },
          ),
        ),
      ]),
    );
  }

  List<Widget> _body(List<LifelogEntry> entries) {
    if (entries.isEmpty) {
      return [
        const AppCard(
          child: Column(children: [
            SizedBox(height: 8),
            Text('아직 수집된 기록이 없어요.',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800)),
            SizedBox(height: 8),
            Text('설정에서 건강 데이터 연동을 켜면\n걸음·수면·심박수가 자동으로 쌓입니다.',
                textAlign: TextAlign.center,
                style: TextStyle(
                    fontSize: 11, height: 1.7, color: AppColors.muted)),
            SizedBox(height: 8),
          ]),
        ),
      ];
    }

    // 서버는 최신순으로 내려줍니다. 그래프는 시간순이어야 하므로 뒤집습니다.
    final ordered = entries.reversed.toList();
    final latest = entries.first;

    return [
      _sleepChart(ordered),
      const SizedBox(height: 22),
      const SectionTitle('최근 측정치'),
      const SizedBox(height: 10),
      _LogMetric(
          icon: Icons.favorite_rounded,
          title: '심박수',
          value: latest.heartRate == null ? '–' : '${latest.heartRate} bpm',
          color: AppColors.pink),
      _LogMetric(
          icon: Icons.dark_mode_rounded,
          title: '수면 시간',
          value: _sleepText(latest.totalSleepMin),
          color: AppColors.purple),
      _LogMetric(
          icon: Icons.directions_walk_rounded,
          title: '활동량',
          value: latest.steps == null ? '–' : '${_comma(latest.steps!)} 걸음',
          color: AppColors.mint),
      _LogMetric(
          icon: Icons.monitor_heart_rounded,
          title: 'HRV',
          value: latest.hrv == null ? '–' : '${latest.hrv!.toStringAsFixed(0)} ms',
          color: AppColors.blue),
      const SizedBox(height: 4),
      Text('마지막 수집  ${_stamp(latest.collectedAt)}',
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 9, color: AppColors.muted)),
    ];
  }

  Widget _sleepChart(List<LifelogEntry> ordered) {
    // 수면 값이 있는 것만 그립니다. 없는 날을 0 으로 이으면
    // 실제로 안 잔 것처럼 보입니다.
    final points = ordered
        .where((e) => e.totalSleepMin != null)
        .map((e) => (e.collectedAt, e.totalSleepMin!.toDouble()))
        .toList();

    return AppCard(
        child: Column(children: [
      SectionTitle('수면 변화',
          trailing: Text(_rangeLabel(ordered),
              style: const TextStyle(fontSize: 9, color: AppColors.muted))),
      const SizedBox(height: 18),
      if (points.length < 2)
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 34),
          child: Text('그래프를 그리려면 수면 기록이 2일 이상 필요해요.',
              style: TextStyle(fontSize: 11, color: AppColors.muted)),
        )
      else ...[
        SizedBox(
            height: 115,
            width: double.infinity,
            child: CustomPaint(
                painter: _LineChartPainter(
                    points.map((p) => p.$2).toList()))),
        const SizedBox(height: 6),
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Text(_short(points.first.$1),
              style: const TextStyle(fontSize: 9, color: AppColors.muted)),
          Text(_short(points.last.$1),
              style: const TextStyle(fontSize: 9, color: AppColors.muted)),
        ]),
      ],
    ]));
  }

  String _rangeLabel(List<LifelogEntry> ordered) => ordered.isEmpty
      ? ''
      : '${_short(ordered.first.collectedAt)} - ${_short(ordered.last.collectedAt)}';

  String _short(DateTime d) => '${d.month}.${d.day}';

  String _sleepText(int? min) =>
      min == null ? '–' : '${min ~/ 60}시간 ${min % 60}분';

  String _comma(int n) => n.toString().replaceAllMapped(
      RegExp(r'(\d)(?=(\d{3})+$)'), (m) => '${m[1]},');

  String _stamp(DateTime at) {
    final diff = DateTime.now().difference(at);
    if (diff.inMinutes < 60) return '${diff.inMinutes}분 전';
    if (diff.inHours < 24) return '${diff.inHours}시간 전';
    return '${diff.inDays}일 전';
  }
}

class _Centered extends StatelessWidget {
  const _Centered({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) => Padding(
      padding: const EdgeInsets.symmetric(vertical: 70),
      child: Center(child: child));
}

class _LineChartPainter extends CustomPainter {
  _LineChartPainter(this.values);

  final List<double> values;

  @override
  void paint(Canvas canvas, Size size) {
    if (values.length < 2) return;

    // 실측값을 0~1 로 정규화합니다. 화면 좌표는 위가 0 이라 뒤집습니다.
    final lo = values.reduce((a, b) => a < b ? a : b);
    final hi = values.reduce((a, b) => a > b ? a : b);
    final span = (hi - lo).abs() < 1e-9 ? 1.0 : hi - lo;

    Offset at(int i) => Offset(
          size.width * i / (values.length - 1),
          size.height * (1 - (values[i] - lo) / span) * 0.9 + size.height * 0.05,
        );

    final path = Path()..moveTo(at(0).dx, at(0).dy);
    for (var i = 1; i < values.length; i++) {
      path.lineTo(at(i).dx, at(i).dy);
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

    // 점이 많으면 원을 다 찍지 않습니다. 월간이면 30개라 뭉개집니다.
    if (values.length <= 10) {
      for (var i = 0; i < values.length; i++) {
        canvas.drawCircle(at(i), 4, Paint()..color = Colors.white);
        canvas.drawCircle(
            at(i),
            4,
            Paint()
              ..color = AppColors.primary
              ..strokeWidth = 2
              ..style = PaintingStyle.stroke);
      }
    }
  }

  @override
  bool shouldRepaint(covariant _LineChartPainter old) => old.values != values;
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
      ])),
    );
  }
}
