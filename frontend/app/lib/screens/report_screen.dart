import 'package:flutter/material.dart';

import '../models/auth_models.dart' show ApiException;
import '../models/report_models.dart';
import '../services/app_services.dart';
import '../services/report_service.dart';
import '../theme/app_theme.dart';
import '../widgets/common_widgets.dart';

/// MAIN_REPORT_01 — 정서 리포트 (MLCM_500)
///
/// 화면설계서 `SD-N2` 명세
///   ❶ 조회 기간: 주·월·직접 지정 전환. 변경 시 재조회
///   ❷ 감정 변화 곡선: 기간별 감정 스코어 추이 표시
///   ❸ 위험 단계 분포: 안정·주의·심각 단계 비율 표시
///   ❹ 결합 차트: 감정 추이와 수면·활동량 동일 시간축
///   ❺ 종합 요약 문구·PDF 내보내기 버튼 제공
///   ❼ 데이터 부족 예외 — 빈 상태
///
/// ⚠ **관리자 웹(`ADMIN_DASH_01` ❸)과 같은 시각화 규격을 씁니다**
///   (`MLCM_501` 4단계). 스택이 달라 컴포넌트를 공유할 수는 없으므로
///   차트 구성·색상·축 기준을 맞춥니다. 색을 바꾸면 그쪽도 함께 고치세요.
class ReportScreen extends StatefulWidget {
  const ReportScreen({super.key, this.reportService});

  /// 테스트 주입용. 평소에는 null 이고 AppServices.report 를 씁니다.
  final ReportService? reportService;

  @override
  State<ReportScreen> createState() => _ReportScreenState();
}

enum _Range {
  week('주간', 7),
  month('월간', 30);

  const _Range(this.label, this.days);
  final String label;
  final int days;
}

class _ReportScreenState extends State<ReportScreen> {
  ReportService get _service => widget.reportService ?? AppServices.report;

  _Range range = _Range.week;
  late Future<EmotionReport> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<EmotionReport> _load() {
    final now = DateTime.now();
    return _service.fetch(
      from: now.subtract(Duration(days: range.days)),
      to: now,
    );
  }

  void _changeRange(_Range next) {
    setState(() {
      range = next;
      _future = _load();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('정서 리포트',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
        centerTitle: true,
      ),
      body: SafeArea(
        child: FutureBuilder<EmotionReport>(
          future: _future,
          builder: (context, snap) {
            return ListView(
              padding: const EdgeInsets.fromLTRB(15, 12, 15, 30),
              children: [
                // ❶ 조회 기간
                SegmentedButton<_Range>(
                  segments: [
                    for (final r in _Range.values)
                      ButtonSegment(value: r, label: Text(r.label)),
                  ],
                  selected: {range},
                  onSelectionChanged: (v) => _changeRange(v.first),
                  showSelectedIcon: false,
                ),
                const SizedBox(height: 18),
                ...switch (snap) {
                  AsyncSnapshot(connectionState: ConnectionState.waiting) => [
                      const _Pad(
                          child:
                              CircularProgressIndicator(strokeWidth: 2.5)),
                    ],
                  // ⚠ 분석 이력이 없으면 서버가 409 를 돌려줍니다
                  //   (MLCM_500 선행조건). 오류가 아니라 빈 상태입니다.
                  AsyncSnapshot(hasError: true, :final error) => [
                      _empty(error is ApiException && error.statusCode == 409
                          ? error.message
                          : '리포트를 불러오지 못했습니다.'),
                    ],
                  _ => _body(snap.data!),
                },
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _empty(String message) {
    return AppCard(
      child: Column(children: [
        const SizedBox(height: 10),
        const MaeumeMascot(size: 64),
        const SizedBox(height: 16),
        Text(message,
            textAlign: TextAlign.center,
            style: const TextStyle(
                fontSize: 13, height: 1.7, fontWeight: FontWeight.w700)),
        const SizedBox(height: 8),
        const Text('하루 이상 기록이 쌓이면 감정 변화를 보여드릴게요.',
            textAlign: TextAlign.center,
            style:
                TextStyle(fontSize: 11, height: 1.7, color: AppColors.muted)),
        const SizedBox(height: 10),
      ]),
    );
  }

  List<Widget> _body(EmotionReport report) {
    if (report.isEmpty) {
      return [_empty('아직 분석된 기록이 없어요.')];
    }
    return [
      _trendCard(report),
      const SizedBox(height: 12),
      _distributionCard(report.distribution),
      const SizedBox(height: 12),
      _lifelogCard(report),
      const SizedBox(height: 12),
      _summaryCard(report),
    ];
  }

  /// ❷ 감정 변화 곡선
  Widget _trendCard(EmotionReport report) {
    final points = report.emotionTrend;
    return AppCard(
      child: Column(children: [
        SectionTitle('감정 변화',
            trailing: Text(_period(report),
                style: const TextStyle(fontSize: 9, color: AppColors.muted))),
        const SizedBox(height: 16),
        if (points.length < 2)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 30),
            child: Text('곡선을 그리려면 기록이 2일 이상 필요해요.',
                style: TextStyle(fontSize: 11, color: AppColors.muted)),
          )
        else ...[
          SizedBox(
            height: 130,
            width: double.infinity,
            child: CustomPaint(painter: _TrendPainter(points)),
          ),
          const SizedBox(height: 8),
          Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
            Text(_short(points.first.evaluatedAt),
                style: const TextStyle(fontSize: 9, color: AppColors.muted)),
            Text(_short(points.last.evaluatedAt),
                style: const TextStyle(fontSize: 9, color: AppColors.muted)),
          ]),
        ],
      ]),
    );
  }

  /// ❸ 위험 단계 분포
  Widget _distributionCard(RiskDistribution d) {
    // ⚠ 심각 단계에 빨강을 쓰지 않습니다. 정신건강 화면에서 경고색은
    //   불안을 키워 회피를 부릅니다. 관리자 웹과 같은 팔레트입니다.
    final rows = [
      ('안정', d.normal, AppColors.teal),
      ('주의', d.caution, AppColors.primary),
      ('심각', d.critical, const Color(0xFF987466)),
    ];
    final total = d.total;

    return AppCard(
      child: Column(children: [
        const SectionTitle('위험 단계 분포'),
        const SizedBox(height: 16),
        for (final (label, count, color) in rows) ...[
          Row(children: [
            SizedBox(
                width: 34,
                child: Text(label,
                    style: const TextStyle(
                        fontSize: 11, fontWeight: FontWeight.w700))),
            Expanded(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(5),
                child: LinearProgressIndicator(
                  value: total == 0 ? 0 : count / total,
                  minHeight: 9,
                  backgroundColor: const Color(0xFFEFF1F8),
                  color: color,
                ),
              ),
            ),
            SizedBox(
                width: 52,
                child: Text(
                    total == 0
                        ? '–'
                        : '$count일 ${(count / total * 100).round()}%',
                    textAlign: TextAlign.right,
                    style: const TextStyle(
                        fontSize: 10, color: AppColors.muted))),
          ]),
          const SizedBox(height: 10),
        ],
      ]),
    );
  }

  /// ❹ 결합 차트 — 감정 추이와 같은 시간축
  Widget _lifelogCard(EmotionReport report) {
    final sleeps = report.lifelogTrend
        .where((p) => p.totalSleepMin != null)
        .toList();
    final steps =
        report.lifelogTrend.where((p) => p.steps != null && p.steps! > 0).toList();

    return AppCard(
      child: Column(children: [
        const SectionTitle('수면·활동량'),
        const SizedBox(height: 16),
        if (sleeps.length < 2 && steps.length < 2)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 26),
            child: Text('같은 기간의 라이프로그가 아직 부족해요.',
                style: TextStyle(fontSize: 11, color: AppColors.muted)),
          )
        else ...[
          SizedBox(
            height: 110,
            width: double.infinity,
            child: CustomPaint(
              painter: _DualPainter(
                sleep: sleeps.map((p) => p.totalSleepMin!.toDouble()).toList(),
                steps: steps.map((p) => p.steps!.toDouble()).toList(),
              ),
            ),
          ),
          const SizedBox(height: 10),
          const Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            _Legend(color: AppColors.purple2, label: '수면'),
            SizedBox(width: 16),
            _Legend(color: AppColors.mint2, label: '활동량'),
          ]),
        ],
      ]),
    );
  }

  /// ❺ 종합 요약 + PDF 내보내기
  Widget _summaryCard(EmotionReport report) {
    return AppCard(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const SectionTitle('종합 요약'),
        const SizedBox(height: 14),
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const MaeumeMascot(size: 48),
          const SizedBox(width: 12),
          Expanded(
            child: Text(report.summary,
                style: const TextStyle(
                    fontSize: 11, height: 1.8, color: AppColors.muted)),
          ),
        ]),
        const SizedBox(height: 18),
        // TODO(PDF): FR-MN-001 — 상담기관·주치의 등과 공유용 내보내기.
        //   서버 엔드포인트를 두지 않기로 했으므로 앱에서 조판한다.
        //   pdf·printing 패키지와 한글 폰트 임베드가 필요하다.
        //   ⚠ 상담기관 제출 문서이므로 기간·생성일시·본인 식별 정보는
        //     기기와 무관하게 같은 위치에 있어야 한다.
        SizedBox(
          width: double.infinity,
          child: OutlinedButton.icon(
            onPressed: null,
            icon: const Icon(Icons.picture_as_pdf_outlined, size: 17),
            label: const Text('PDF로 내보내기 (준비 중)',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
            style: OutlinedButton.styleFrom(
              minimumSize: const Size.fromHeight(46),
              side: const BorderSide(color: AppColors.line),
              shape:
                  RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
          ),
        ),
      ]),
    );
  }

  String _period(EmotionReport r) {
    final from = r.dateFrom, to = r.dateTo;
    if (from == null || to == null) return '';
    return '${_short(from)} - ${_short(to)}';
  }

  String _short(DateTime d) => '${d.month}.${d.day}';
}

class _Pad extends StatelessWidget {
  const _Pad({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) => Padding(
      padding: const EdgeInsets.symmetric(vertical: 70),
      child: Center(child: child));
}

class _Legend extends StatelessWidget {
  const _Legend({required this.color, required this.label});
  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) => Row(mainAxisSize: MainAxisSize.min, children: [
        Container(
            width: 9,
            height: 9,
            decoration:
                BoxDecoration(color: color, borderRadius: BorderRadius.circular(3))),
        const SizedBox(width: 5),
        Text(label,
            style: const TextStyle(fontSize: 9, color: AppColors.muted)),
      ]);
}

/// 감정 스코어 추이. 점마다 위험 단계 색을 찍습니다.
class _TrendPainter extends CustomPainter {
  _TrendPainter(this.points);

  final List<RiskPoint> points;

  static const _levelColor = {
    'NORMAL': AppColors.teal,
    'CAUTION': AppColors.primary,
    'CRITICAL': Color(0xFF987466),
  };

  @override
  void paint(Canvas canvas, Size size) {
    if (points.length < 2) return;
    // 감정 스코어는 0~100 고정 축입니다. 데이터 범위로 정규화하면
    // 값이 조금만 흔들려도 곡선이 요동쳐 실제보다 심각해 보입니다.
    Offset at(int i) => Offset(
          size.width * i / (points.length - 1),
          size.height * (1 - points[i].emotionScore.clamp(0, 100) / 100) * .88 +
              size.height * .06,
        );

    final path = Path()..moveTo(at(0).dx, at(0).dy);
    for (var i = 1; i < points.length; i++) {
      path.lineTo(at(i).dx, at(i).dy);
    }

    canvas.drawPath(
        Path.from(path)
          ..lineTo(size.width, size.height)
          ..lineTo(0, size.height)
          ..close(),
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
          ..strokeWidth = 2.5
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round);

    if (points.length <= 14) {
      for (var i = 0; i < points.length; i++) {
        final c = _levelColor[points[i].riskLevel] ?? AppColors.primary;
        canvas.drawCircle(at(i), 4, Paint()..color = Colors.white);
        canvas.drawCircle(
            at(i),
            4,
            Paint()
              ..color = c
              ..strokeWidth = 2.2
              ..style = PaintingStyle.stroke);
      }
    }
  }

  @override
  bool shouldRepaint(covariant _TrendPainter old) => old.points != points;
}

/// 수면·활동량을 같은 시간축에 겹칩니다. 단위가 달라 각자 정규화합니다.
class _DualPainter extends CustomPainter {
  _DualPainter({required this.sleep, required this.steps});

  final List<double> sleep;
  final List<double> steps;

  void _draw(Canvas canvas, Size size, List<double> v, Color color) {
    if (v.length < 2) return;
    final lo = v.reduce((a, b) => a < b ? a : b);
    final hi = v.reduce((a, b) => a > b ? a : b);
    final span = (hi - lo).abs() < 1e-9 ? 1.0 : hi - lo;

    final path = Path();
    for (var i = 0; i < v.length; i++) {
      final p = Offset(
        size.width * i / (v.length - 1),
        size.height * (1 - (v[i] - lo) / span) * .82 + size.height * .09,
      );
      i == 0 ? path.moveTo(p.dx, p.dy) : path.lineTo(p.dx, p.dy);
    }
    canvas.drawPath(
        path,
        Paint()
          ..color = color
          ..strokeWidth = 2.5
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round);
  }

  @override
  void paint(Canvas canvas, Size size) {
    _draw(canvas, size, sleep, AppColors.purple2);
    _draw(canvas, size, steps, AppColors.mint2);
  }

  @override
  bool shouldRepaint(covariant _DualPainter old) =>
      old.sleep != sleep || old.steps != steps;
}
