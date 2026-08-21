/// 백그라운드 수집 워커 — MLCM_200 1단계
///
/// `MLCM_200` 은 「최소 15분 간격」을 규정하고, 「단말의 전력 최적화
/// 정책(Doze 모드, 앱 대기 버킷)에 따라 실제 실행 시점은 지연될 수 있다」고
/// 함께 적고 있습니다. **15분은 하한이지 보장이 아닙니다.** WorkManager 도
/// 주기 작업의 최소 간격이 15분이고 정확한 시각은 보장하지 않습니다.
///
/// 밀린 구간은 다음 실행이 따라잡습니다. 읽기 구간이 `last_synced_at` 이 든
/// 날의 자정부터라서, 몇 시간 밀려도 그날 행이 통째로 다시 계산됩니다.
///
/// ---
/// ## ⚠ 백그라운드는 **다른 아이솔레이트**입니다
///
/// [callbackDispatcher] 는 앱 UI 와 메모리를 공유하지 않습니다.
/// `AppServices` 의 static 필드도 여기서는 비어 있습니다. 그래서 필요한 것을
/// **전부 다시 만듭니다.** 이걸 잊고 `AppServices.lifelog` 를 쓰면
/// 백그라운드에서만 조용히 실패합니다.
///
/// `@pragma('vm:entry-point')` 도 필수입니다. 릴리스 빌드의 트리 셰이킹이
/// 진입점을 지워서, **디버그에서만 되고 릴리스에서 안 되는** 상태가 됩니다.
library;

import 'package:flutter/foundation.dart';
import 'package:workmanager/workmanager.dart';

import 'api_client.dart';
import 'health_reader.dart';
import 'lifelog_service.dart';
import 'lifelog_sync.dart';
import 'sync_store.dart';
import 'token_storage.dart';

/// 주기 작업 식별자. 재등록해도 중복되지 않게 고정합니다.
const _kUniqueName = 'lisn.lifelog.sync';
const _kTaskName = 'lifelogSync';

/// `MLCM_200` 이 규정한 하한.
const kSyncInterval = Duration(minutes: 15);

/// 백그라운드에서도 쓸 수 있는 동기화 서비스 한 벌을 만듭니다.
///
/// UI 쪽에서도 같은 함수를 씁니다. 두 곳이 다른 방식으로 조립되면 한쪽에서만
/// 나는 버그가 생깁니다.
LifelogSyncService buildSyncService() {
  final tokenStore = SecureTokenStore();
  final apiClient = ApiClient(tokenStore: tokenStore);
  return LifelogSyncService(
    reader: HealthConnectReader(),
    store: PrefsSyncStore(),
    lifelogService: LifelogService(apiClient: apiClient),
  );
}

@pragma('vm:entry-point')
void callbackDispatcher() {
  Workmanager().executeTask((task, inputData) async {
    if (task != _kTaskName) return true;
    try {
      final result = await buildSyncService().sync();
      debugPrint('[동기화] $result');

      // ⚠ **실패해도 true 를 돌려줍니다.** false 면 WorkManager 가 자체
      //   백오프로 재시도하는데, 우리는 이미 30초·3회 재시도를 했고
      //   실패분은 큐에 있습니다. 여기서 또 재시도하면 규정(NFR-DV-002)
      //   보다 많이 때리게 됩니다. 다음 주기가 큐를 가져갑니다.
      return true;
    } catch (e, st) {
      debugPrint('[동기화] 예외: $e\n$st');
      return true;
    }
  });
}

/// 앱 시작 시 1회 호출. 이미 등록돼 있으면 갱신됩니다.
///
/// ⚠ 권한이 없어도 등록합니다. 워커가 매번 권한을 확인하고 없으면 바로
///   빠져나오므로 비용이 거의 없고, 사용자가 나중에 권한을 켰을 때 **앱을
///   다시 열지 않아도** 수집이 시작됩니다.
Future<void> registerLifelogSync() async {
  await Workmanager().initialize(callbackDispatcher);
  await Workmanager().registerPeriodicTask(
    _kUniqueName,
    _kTaskName,
    frequency: kSyncInterval,
    existingWorkPolicy: ExistingPeriodicWorkPolicy.update,
    constraints: Constraints(networkType: NetworkType.connected),
    backoffPolicy: BackoffPolicy.linear,
    backoffPolicyDelay: const Duration(seconds: 30),
  );
}

/// 로그아웃·회원탈퇴 시 호출.
///
/// ⚠ 이걸 빼면 **로그아웃한 뒤에도 워커가 계속 돕니다.** 토큰이 없어 전송은
///   실패하고, 실패분이 큐에 쌓입니다. 다음 사람이 같은 기기로 로그인하면
///   **앞사람 데이터가 그 계정으로 올라갑니다.**
Future<void> cancelLifelogSync() async {
  await Workmanager().cancelByUniqueName(_kUniqueName);
  await PrefsSyncStore().clearPending();
}
