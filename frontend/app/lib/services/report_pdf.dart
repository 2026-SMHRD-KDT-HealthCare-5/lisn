import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/rendering.dart';
import 'package:flutter/widgets.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';

import '../models/report_models.dart';

/// 정서 리포트 PDF — FR-MN-001
///
/// 「PDF 로 내보내 상담기관·주치의 등과 공유」를 앱에서 충족합니다.
/// 서버에 `GET /reports/export` 를 두지 않기로 했습니다(2026.08.01).
///
/// ## 왜 화면을 이미지로 찍나
///
/// PDF 에 한글을 **글자로** 넣으려면 한글 TTF 를 에셋에 임베드해야 합니다
/// (4~8MB). 화면을 그대로 찍으면 Flutter 가 이미 쓰는 폰트로 렌더되므로
/// 폰트를 따로 넣을 필요가 없고, **화면과 PDF 가 정확히 같아집니다.**
///
/// 대신 문서가 이미지라 글자 선택·검색이 안 됩니다. 상담기관에 보여주는
/// 용도라 읽을 수만 있으면 되므로 그 비용을 받아들입니다.
///
/// ## 기기가 달라도 같아야 하는 것
///
/// 상담기관에 제출되는 문서입니다. **기간·생성일시·본인 식별 정보는 어느
/// 기기에서 뽑아도 같은 자리에 있어야** 합니다. 그래서 이 세 가지는 화면
/// 캡처가 아니라 **PDF 머리말로 직접 그립니다.** 화면은 기기 폭에 따라
/// 여백이 달라지지만 머리말은 A4 기준으로 고정됩니다.
class ReportPdf {
  const ReportPdf._();

  /// 위젯을 이미지로 찍습니다.
  ///
  /// ⚠ **다시 그려질 것이 남아 있으면 `toImage` 가 실패합니다**
  ///   (`!debugNeedsPaint` assertion). 버튼을 누르면 로딩 상태 때문에
  ///   `setState` 가 먼저 돌아 화면이 dirty 해지는데, 그 프레임이 그려지기
  ///   전에 캡처하면 여기서 터집니다. 실제로 그렇게 만들었다가 잡았습니다.
  ///
  ///   그래서 `debugNeedsPaint` 가 풀릴 때까지 프레임을 기다립니다.
  ///   무한정 기다리지 않도록 횟수를 제한합니다 — 계속 dirty 하면
  ///   레이아웃 쪽에 다른 문제가 있는 것이고, 그때는 실패로 알리는 편이 낫습니다.
  static Future<Uint8List?> capture(RenderRepaintBoundary boundary) async {
    for (var i = 0; boundary.debugNeedsPaint && i < 10; i++) {
      await WidgetsBinding.instance.endOfFrame;
    }
    if (boundary.debugNeedsPaint) return null;

    // 3배로 찍습니다. 1배면 A4 로 늘렸을 때 글자가 뭉갭니다.
    final image = await boundary.toImage(pixelRatio: 3.0);
    final data = await image.toByteData(format: ui.ImageByteFormat.png);
    return data?.buffer.asUint8List();
  }

  /// 캡처 이미지를 A4 문서로 묶어 공유 시트를 띄웁니다.
  static Future<void> share({
    required Uint8List capture,
    required EmotionReport report,
    required String userName,
    required DateTime generatedAt,
  }) async {
    final doc = pw.Document();
    final image = pw.MemoryImage(capture);

    doc.addPage(
      pw.Page(
        pageFormat: PdfPageFormat.a4,
        margin: const pw.EdgeInsets.fromLTRB(28, 28, 28, 24),
        build: (context) => pw.Column(
          crossAxisAlignment: pw.CrossAxisAlignment.start,
          children: [
            _header(report, userName, generatedAt),
            pw.SizedBox(height: 14),
            pw.Expanded(
              child: pw.Center(
                child: pw.Image(image, fit: pw.BoxFit.contain),
              ),
            ),
            pw.SizedBox(height: 10),
            _footer(),
          ],
        ),
      ),
    );

    await Printing.sharePdf(
      bytes: await doc.save(),
      filename: 'lisn-report-${_ymd(generatedAt)}.pdf',
    );
  }

  /// 머리말 — 기기와 무관하게 고정된 자리입니다.
  ///
  /// ⚠ 한글을 쓰지 않습니다. 기본 폰트(Helvetica)에 한글 글리프가 없어
  ///   깨집니다. 라벨은 영문·숫자로 두고, 한글 내용은 아래 캡처 이미지가
  ///   담습니다. 한글 라벨이 필요해지면 TTF 를 에셋에 넣어야 합니다.
  static pw.Widget _header(
      EmotionReport report, String userName, DateTime generatedAt) {
    final from = report.dateFrom, to = report.dateTo;
    final period = (from == null || to == null)
        ? '-'
        : '${_ymd(from)} ~ ${_ymd(to)}';

    return pw.Container(
      padding: const pw.EdgeInsets.only(bottom: 10),
      decoration: const pw.BoxDecoration(
        border: pw.Border(
            bottom: pw.BorderSide(color: PdfColor.fromInt(0xFFDDE2F0))),
      ),
      child: pw.Column(
        crossAxisAlignment: pw.CrossAxisAlignment.start,
        children: [
          pw.Text('LISN  Emotional Report',
              style: const pw.TextStyle(
                  fontSize: 15,
                  fontWeight: pw.FontWeight.bold,
                  color: PdfColor.fromInt(0xFF172147))),
          pw.SizedBox(height: 6),
          _row('Name', userName.isEmpty ? '-' : userName),
          _row('Period', period),
          _row('Generated', _ymdhm(generatedAt)),
        ],
      ),
    );
  }

  static pw.Widget _row(String label, String value) => pw.Padding(
        padding: const pw.EdgeInsets.only(top: 2),
        child: pw.Row(children: [
          pw.SizedBox(
            width: 62,
            child: pw.Text(label,
                style: const pw.TextStyle(
                    fontSize: 9, color: PdfColor.fromInt(0xFF7C86A5))),
          ),
          pw.Text(value, style: const pw.TextStyle(fontSize: 9)),
        ]),
      );

  /// ⚠ 진단서가 아니라는 것을 문서에 남깁니다. 상담기관·주치의에게
  ///   전달되는 문서라, 이 문장이 없으면 분석 결과가 임상 판단으로
  ///   읽힐 수 있습니다. FR-AI-002 의 진단 금지와 같은 선입니다.
  static pw.Widget _footer() => pw.Text(
        'This report is generated from self-tracked lifelog data '
        'and is not a medical diagnosis.',
        style: const pw.TextStyle(
            fontSize: 7, color: PdfColor.fromInt(0xFF97A0B5)),
      );

  static String _ymd(DateTime d) =>
      '${d.year}-${_two(d.month)}-${_two(d.day)}';

  static String _ymdhm(DateTime d) =>
      '${_ymd(d)} ${_two(d.hour)}:${_two(d.minute)}';

  static String _two(int n) => n.toString().padLeft(2, '0');
}
