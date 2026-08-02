import '../models/lifelog_models.dart';
import 'api_client.dart';
import 'lifelog_aggregate.dart';

/// 라이프로그 조회·전송 — MLCM_200 · MAIN_LIFELOG_01
///
/// ⚠ **수집 주체는 앱입니다.** Health Connect 는 Android on-device 권한
///   모델이라 서버가 대신 읽을 수 없고, 앱이 읽어서 push 합니다
///   (안건 1-1 확정). 읽기는 [HealthReader], 전체 흐름은
///   [LifelogSyncService] 가 맡고, 이 서비스는 **HTTP 만** 담당합니다.
class LifelogService {
  const LifelogService({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  /// 수집분 전송 — `MLCM_200` 4단계.
  ///
  /// 서버가 확정한 `last_synced_at` 을 돌려줍니다. **앱 시계로 대신 채우지
  /// 마세요.** 단말 시간이 틀어졌을 때 그 구간이 영구 유실됩니다.
  ///
  /// 재시도는 여기서 하지 않습니다([LifelogSyncService] 담당). 이 메서드는
  /// 실패하면 그대로 던집니다.
  Future<DateTime> push(List<DailyLifelog> rows) async {
    final json = await _apiClient.post(
      '/lifelog/batch',
      body: {'items': rows.map((r) => r.toJson()).toList()},
      authenticated: true,
    );
    final raw = json['last_synced_at'];
    if (raw is! String) {
      throw const FormatException('last_synced_at 이 응답에 없습니다');
    }
    return DateTime.parse(raw).toLocal();
  }

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
