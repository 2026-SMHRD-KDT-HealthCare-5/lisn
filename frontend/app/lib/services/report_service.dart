import '../models/report_models.dart';
import 'api_client.dart';

/// 정서 리포트 — MLCM_500 · MAIN_REPORT_01
///
/// ⚠ **PDF 는 서버가 만들지 않습니다.** `GET /reports/export` 를 두지 않기로
///   했습니다(2026.08.01). 이 응답이 **PDF 의 데이터 원본**이므로, 리포트에
///   넣을 항목이 늘면 서버의 `GET /reports` 부터 넓혀야 합니다.
class ReportService {
  const ReportService({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  /// 기간별 리포트.
  ///
  /// ⚠ 분석 이력이 하루도 없으면 서버가 **409** 를 돌려줍니다
  ///   (MLCM_500 선행조건). 호출자가 빈 상태로 처리해야 합니다.
  Future<EmotionReport> fetch({DateTime? from, DateTime? to}) async {
    final json = await _apiClient.get(
      '/reports',
      queryParameters: {
        if (from != null) 'from': from.toUtc().toIso8601String(),
        if (to != null) 'to': to.toUtc().toIso8601String(),
      },
      authenticated: true,
    );
    return EmotionReport.fromJson(json);
  }
}
