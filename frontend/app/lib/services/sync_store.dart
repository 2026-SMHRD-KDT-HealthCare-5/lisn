/// 동기화 상태 보관 — MLCM_200 3·6단계
///
/// 담는 것은 둘입니다.
/// * **마지막 동기화 시각** — 다음에 어디부터 읽을지
/// * **실패분 큐** — 3회 재시도까지 실패한 행. 다음 주기에 같이 보냅니다
///
/// ⚠ **`flutter_secure_storage` 를 쓰지 않습니다.** 여기 담기는 건 측정치가
///   아니라 「언제 보냈나」와 재전송 대기열입니다. 토큰과 달리 유출돼도
///   계정을 못 씁니다. 백그라운드 워커에서도 열어야 하는데 보안 저장소는
///   기기 잠금 상태에서 못 여는 경우가 있어 동기화가 조용히 멈춥니다.
library;

import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import 'lifelog_aggregate.dart';

abstract class SyncStore {
  Future<DateTime?> lastSyncedAt();
  Future<void> saveLastSyncedAt(DateTime value);

  Future<List<DailyLifelog>> pendingRows();
  Future<void> savePending(List<DailyLifelog> rows);
  Future<void> clearPending();
}

class PrefsSyncStore implements SyncStore {
  PrefsSyncStore({SharedPreferences? prefs}) : _injected = prefs;

  static const _kLastSynced = 'lifelog.last_synced_at';
  static const _kPending = 'lifelog.pending';

  /// 단말에 쌓아둘 최대 행 수.
  ///
  /// ⚠ 한도가 없으면 서버가 오래 죽어 있을 때 큐가 무한히 자랍니다. 행은
  ///   하루 하나이므로 60이면 두 달치입니다. 그보다 오래 밀린 데이터는
  ///   Health Connect 에서 다시 읽는 편이 낫습니다.
  static const maxPending = 60;

  final SharedPreferences? _injected;
  SharedPreferences? _cached;

  Future<SharedPreferences> get _prefs async =>
      _injected ?? (_cached ??= await SharedPreferences.getInstance());

  @override
  Future<DateTime?> lastSyncedAt() async {
    final raw = (await _prefs).getString(_kLastSynced);
    if (raw == null) return null;
    return DateTime.tryParse(raw)?.toLocal();
  }

  @override
  Future<void> saveLastSyncedAt(DateTime value) async {
    await (await _prefs).setString(_kLastSynced, value.toUtc().toIso8601String());
  }

  @override
  Future<List<DailyLifelog>> pendingRows() async {
    final raw = (await _prefs).getString(_kPending);
    if (raw == null || raw.isEmpty) return const [];
    try {
      final decoded = jsonDecode(raw);
      if (decoded is! List) return const [];
      return decoded
          .whereType<Map<String, dynamic>>()
          .map(DailyLifelog.fromJson)
          .toList();
    } catch (_) {
      // ⚠ 깨진 큐 때문에 동기화가 영구히 멈추면 안 됩니다. 버리고 갑니다.
      //   행은 Health Connect 에서 다시 읽을 수 있습니다.
      await (await _prefs).remove(_kPending);
      return const [];
    }
  }

  @override
  Future<void> savePending(List<DailyLifelog> rows) async {
    if (rows.isEmpty) return clearPending();
    // 최신 것부터 남깁니다. 오래된 행일수록 다시 읽어 채울 여지가 큽니다.
    final trimmed = rows.length <= maxPending
        ? rows
        : (rows.toList()..sort((a, b) => a.collectedAt.compareTo(b.collectedAt)))
            .sublist(rows.length - maxPending);
    await (await _prefs)
        .setString(_kPending, jsonEncode(trimmed.map((r) => r.toJson()).toList()));
  }

  @override
  Future<void> clearPending() async {
    await (await _prefs).remove(_kPending);
  }
}

/// 테스트용 메모리 구현.
class MemorySyncStore implements SyncStore {
  DateTime? _last;
  List<DailyLifelog> _pending = const [];

  @override
  Future<DateTime?> lastSyncedAt() async => _last;

  @override
  Future<void> saveLastSyncedAt(DateTime value) async => _last = value;

  @override
  Future<List<DailyLifelog>> pendingRows() async => _pending;

  @override
  Future<void> savePending(List<DailyLifelog> rows) async => _pending = rows;

  @override
  Future<void> clearPending() async => _pending = const [];
}
