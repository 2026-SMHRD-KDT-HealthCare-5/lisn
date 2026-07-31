import '../models/home_models.dart';
import 'api_client.dart';

/// MAIN_HOME_01 데이터.
///
/// 홈은 한 번의 호출로 끝납니다. 감정·라이프로그·요약·추천을 각각 부르면
/// 왕복이 4회가 되고, 그 사이에 분석이 갱신되면 화면 안에서 값이 어긋납니다.
class HomeService {
  const HomeService({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  Future<HomeSnapshot> fetch() async {
    final json = await _apiClient.get('/home', authenticated: true);
    return HomeSnapshot.fromJson(json);
  }
}
