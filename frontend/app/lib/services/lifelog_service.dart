import '../models/lifelog_models.dart';
import 'api_client.dart';

/// 라이프로그 조회 — MLCM_200 · MAIN_LIFELOG_01
///
/// ⚠ **수집·전송은 여기 없습니다.** Health Connect 는 Android on-device 권한
///   모델이라 서버가 대신 읽을 수 없고, 앱이 읽어서 push 하는 구조입니다
///   (안건 1-1 확정). 그 push 는 백그라운드 워커가 담당하고,
///   이 서비스는 **화면에 그릴 데이터를 조회**하기만 합니다.
class LifelogService {
  const LifelogService({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  Future<List<LifelogEntry>> fetch({
    DateTime? from,
    DateTime? to,
    int limit = 100,
  }) async {
    final rows = await _apiClient.getList(
      '/lifelog',
      queryParameters: {
        'limit': '$limit',
        if (from != null) 'from': from.toUtc().toIso8601String(),
        if (to != null) 'to': to.toUtc().toIso8601String(),
      },
      authenticated: true,
    );
    return rows.map(LifelogEntry.fromJson).toList();
  }

  Future<List<BodyComposition>> fetchBodyComposition({int limit = 30}) async {
    final rows = await _apiClient.getList(
      '/body-composition',
      queryParameters: {'limit': '$limit'},
      authenticated: true,
    );
    return rows.map(BodyComposition.fromJson).toList();
  }
}
