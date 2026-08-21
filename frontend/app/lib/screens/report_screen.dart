import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';

import '../models/auth_models.dart' show ApiException;
import '../models/report_models.dart';
import '../services/app_services.dart';
import '../services/report_pdf.dart';
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
  month('월간', 30),
  // ❶ 「직접 지정」 — 화면설계서 MAIN_REPORT_01 이 규정합니다.
  // days 는 쓰지 않고 _customFrom·_customTo 를 씁니다.
  custom('직접 지정', 0);

  const _Range(this.label, this.days);
  final String label;
  final int days;
}

class _ReportScreenState extends State<ReportScreen> {
  ReportService get _service => widget.reportService ?? AppServices.report;

  _Range range = _Range.week;
  late Future<EmotionReport> _future;

  /// 「직접 지정」으로 고른 구간. 고르기 전에는 null 입니다.
  DateTimeRange? _custom;

  /// 마지막으로 성공한 리포트.
  ///
  /// 기간을 바꿀 때 화면을 스피너로 갈아치우면 **본문이 통째로 접혔다 펴집니다.**
  /// 분포·곡선·라이프로그·요약이 한 번에 사라지니 움직임이 큽니다.
  /// 이전 내용을 두고 흐리게만 처리합니다.
  EmotionReport? _last;

  /// PDF 로 찍을 영역. 화면에 그려진 뒤에만 캡처가 됩니다.
  final _captureKey = GlobalKey();
  bool exporting = false;

  @override
  void initState() {
    super.initState();
    _future = _loadAndKeep();
  }

  Future<EmotionReport> _load() {
    final now = DateTime.now();
    final picked = _custom;
    if (range == _Range.custom && picked != null) {
      // ⚠ 끝나는 날을 **그날 끝까지** 잡습니다. 그대로 보내면 자정 기준이라
      //   고른 마지막 날이 통째로 빠집니다.
      return _service.fetch(
        from: picked.start,
        to: DateTime(picked.end.year, picked.end.month, picked.end.day,
            23, 59, 59),
      );
    }
    return _service.fetch(
      from: now.subtract(Duration(days: range.days)),
      to: now,
    );
  }

  /// 성공한 결과만 보관합니다. 실패는 이전 내용을 지우지 않습니다 —
  /// 통신이 한 번 끊겼다고 보고 있던 리포트가 사라질 이유가 없습니다.
  ///
  /// ⚠ `then(...).ignore()` 를 async/await 로 바꾸지 마세요. 조회가 즉시 실패하면
  ///   FutureBuilder 가 구독하기 전에 오류가 도착해 **미처리 예외로 보고**됩니다
  ///   (화면은 정상 처리되는데 로그만 더러워지고, 위젯 테스트는 실패합니다).
  ///   여기서 곧바로 리스너를 달아 그 경합을 없앱니다. 화면 처리는 아래
  ///   FutureBuilder 가 하므로 파생 future 의 오류만 흘려보냅니다.
  Future<EmotionReport> _loadAndKeep() {
    final future = _load();
    future.then((report) {
      if (mounted) _last = report;
    }).ignore();
    return future;
  }

  void _changeRange(_Range next) {
    if (next == _Range.custom) {
      _pickRange();
      return;
    }
    setState(() {
      range = next;
      _future = _loadAndKeep();
    });
  }

  /// 「직접 지정」 — 날짜 두 개를 고릅니다.
  ///
  /// ⚠ **고르기를 취소하면 기간을 바꾸지 않습니다.** 먼저 range 를 custom 으로
  ///   바꿔놓고 달력을 띄우면, 취소했을 때 구간이 없는 custom 상태로 남아
  ///   화면이 빕니다.
  Future<void> _pickRange() async {
    final now = DateTime.now();
    final picked = await showDateRangePicker(
      context: context,
      // 수집 시작 이전은 고를 이유가 없고, 미래는 데이터가 없습니다.
      firstDate: DateTime(now.year - 1),
      lastDate: now,
      initialDateRange: _custom ??
          DateTimeRange(start: now.subtract(const Duration(days: 7)), end: now),
      locale: const Locale('ko'),
      helpText: '조회 기간 선택',
      saveText: '적용',
    );
    if (picked == null || !mounted) return;
    setState(() {
      _custom = picked;
      range = _Range.custom;
      _future = _loadAndKeep();
    });
  }

  /// 고른 구간을 사람이 읽는 형태로.
  String get _customLabel {
    final c = _custom;
    if (c == null) return _Range.custom.label;
    String f(DateTime d) =>
        '${d.month}.${d.day.toString().padLeft(2, '0')}';
    return '${f(c.start)} ~ ${f(c.end)}';
  }

  /// ❺ PDF 내보내기 — FR-MN-001
  ///
  /// 화면을 이미지로 찍어 A4 문서에 넣고 공유 시트를 띄웁니다.
  /// 이름·기간·생성일시는 캡처가 아니라 PDF 머리말로 그려집니다 —
  /// 상담기관 제출 문서라 기기가 달라도 같은 자리에 있어야 합니다.
  Future<void> _exportPdf(EmotionReport report) async {
    if (exporting) return;
    setState(() => exporting = true);
    try {
      final boundary = _captureKey.currentContext?.findRenderObject()
          as RenderRepaintBoundary?;
      if (boundary == null) {
        throw StateError('캡처할 영역을 찾지 못했습니다');
      }
      final image = await ReportPdf.capture(boundary);
      if (image == null) {
        throw StateError('화면을 이미지로 만들지 못했습니다');
      }

      // 이름은 프로필에서 가져옵니다. 실패해도 PDF 는 만듭니다 —
      // 이름 하나 때문에 내보내기 전체가 막히면 안 됩니다.
      String name = '';
      try {
        name = (await AppServices.settings.profile()).name;
      } catch (_) {}

      await ReportPdf.share(
        capture: image,
        report: report,
        userName: name,
        generatedAt: DateTime.now(),
      );
    } catch (e, stack) {
      // 원인을 삼키지 않습니다. 사용자에게는 짧은 문구만 보여주고
      // 실제 오류는 로그로 남겨야 다음에 원인을 찾을 수 있습니다.
      debugPrint('[report-pdf] 내보내기 실패: $e\n$stack');
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('PDF를 만들지 못했습니다. 잠시 후 다시 시도해주세요.')));
    } finally {
      if (mounted) setState(() => exporting = false);
    }
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
                      ButtonSegment(
                          value: r,
                          label: Text(r == _Range.custom && range == r
                              ? _customLabel
                              : r.label)),
                  ],
                  selected: {range},
                  onSelectionChanged: (v) => _changeRange(v.first),
                  showSelectedIcon: false,
                ),
                const SizedBox(height: 18),
                ...switch (snap) {
                  // 기간을 바꾸는 중. 이전 리포트가 있으면 그대로 두고 흐리게만
                  // 처리합니다. 스피너로 갈아치우면 본문이 통째로 접혔다 펴져
                  // 화면이 크게 튑니다.
                  AsyncSnapshot(connectionState: ConnectionState.waiting)
                      when _last != null =>
                    [
                      // ⚠ RepaintBoundary 를 달지 않습니다. 이 상태에서 PDF 를
                      //   찍으면 바뀐 기간의 머리말에 이전 기간의 그림이 들어갑니다.
                      StaleContent(child: Column(children: _body(_last!))),
                    ],
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
                  _ => [
                      // PDF 로 찍을 영역. 기간 선택 버튼은 문서에 들어갈
                      // 내용이 아니므로 바깥에 둡니다.
                      RepaintBoundary(
                        key: _captureKey,
                        child: Column(children: _body(snap.data!)),
                      ),
                    ],
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
  ///
  /// ⚠ 두 계열의 **길이가 같아야 합니다.** 측정된 값만 골라 각각 배열로 만들면
  ///   길이가 달라지고, 그러면 화면 폭을 각자 나눠 쓰게 돼 **같은 x 좌표가 서로
  ///   다른 날**을 가리킵니다. 「그날 수면이 줄고 활동도 줄었다」로 읽히는 그림이
  ///   실제로는 다른 날 둘을 겹쳐놓은 것이 됩니다.
  ///   걸음은 0 을 제외하므로(「0걸음」과 「측정 안 됨」은 다릅니다) 길이가
  ///   어긋나는 것이 흔합니다.
  ///
  ///   그래서 전 구간 길이를 유지하고 **빈 날은 null 로 비워** 넘깁니다.
  Widget _lifelogCard(EmotionReport report) {
    final trend = report.lifelogTrend;
    final sleeps = [
      for (final p in trend) p.totalSleepMin?.toDouble(),
    ];
    final steps = [
      for (final p in trend)
        (p.steps != null && p.steps! > 0) ? p.steps!.toDouble() : null,
    ];
    final sleepCount = sleeps.whereType<double>().length;
    final stepCount = steps.whereType<double>().length;

    return AppCard(
      child: Column(children: [
        const SectionTitle('수면·활동량'),
        const SizedBox(height: 16),
        if (sleepCount < 2 && stepCount < 2)
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
              painter: _DualPainter(sleep: sleeps, steps: steps),
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
          // 요약이 「도움이 필요한 신호가 N회 관찰됐어요」인데 옆에서 웃고 있으면
          // 안 됩니다. 심각이 한 번이라도 있으면 담담한 표정입니다.
          MaeumeMascot(
              size: 48,
              mood: report.distribution.critical > 0
                  ? MascotMood.calm
                  : MascotMood.smile),
          const SizedBox(width: 12),
          Expanded(
            child: Text(report.summary,
                style: const TextStyle(
                    fontSize: 11, height: 1.8, color: AppColors.muted)),
          ),
        ]),
        const SizedBox(height: 18),
        // ❺ PDF 내보내기 — FR-MN-001
        // 서버 엔드포인트를 두지 않고 앱에서 조판합니다.
        // 방식과 규격은 services/report_pdf.dart 주석 참고.
        SizedBox(
          width: double.infinity,
          child: OutlinedButton.icon(
            onPressed: exporting ? null : () => _exportPdf(report),
            icon: exporting
                ? const SizedBox(
                    width: 15,
                    height: 15,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.picture_as_pdf_outlined, size: 17),
            label: Text(exporting ? '만드는 중...' : 'PDF로 내보내기',
                style: const TextStyle(
                    fontSize: 12, fontWeight: FontWeight.w700)),
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

/// 테스트에서 결합 차트 페인터를 직접 만들기 위한 통로입니다.
///
/// 페인터를 공개하지 않는 대신 이 함수만 엽니다. 시간축이 어긋나는 회귀를
/// 잡으려면 그리기 자체를 태워봐야 합니다.
@visibleForTesting
CustomPainter buildDualPainterForTest({
  required List<double?> sleep,
  required List<double?> steps,
}) =>
    _DualPainter(sleep: sleep, steps: steps);

/// 수면·활동량을 같은 시간축에 겹칩니다. 단위가 달라 **세로만** 각자 정규화하고,
/// **가로는 두 계열이 공유**합니다.
///
/// ⚠ 두 배열은 **같은 길이**여야 하며 측정이 없는 날은 null 입니다. 길이가
///   다르면 같은 x 가 서로 다른 날을 가리켜 그래프가 거짓말을 합니다.
class _DualPainter extends CustomPainter {
  _DualPainter({required this.sleep, required this.steps})
      : assert(sleep.length == steps.length, '두 계열의 길이가 달라 시간축이 어긋납니다');

  final List<double?> sleep;
  final List<double?> steps;

  void _draw(Canvas canvas, Size size, List<double?> v, Color color) {
    final measured = v.whereType<double>().toList();
    if (measured.length < 2 || v.length < 2) return;
    final lo = measured.reduce((a, b) => a < b ? a : b);
    final hi = measured.reduce((a, b) => a > b ? a : b);
    final span = (hi - lo).abs() < 1e-9 ? 1.0 : hi - lo;

    final path = Path();
    var started = false;
    for (var i = 0; i < v.length; i++) {
      final value = v[i];
      // 측정이 없는 날은 건너뜁니다. x 는 **전 구간 기준**이라 건너뛰어도
      // 나머지 점의 위치가 밀리지 않습니다.
      if (value == null) continue;
      final p = Offset(
        size.width * i / (v.length - 1),
        size.height * (1 - (value - lo) / span) * .82 + size.height * .09,
      );
      started ? path.lineTo(p.dx, p.dy) : path.moveTo(p.dx, p.dy);
      started = true;
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
