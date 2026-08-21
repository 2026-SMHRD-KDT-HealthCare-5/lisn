/// 라이프로그 동기화 — MLCM_200 전체 흐름 · NFR-DV-002
///
/// ```
/// 1. 권한 확인          권한 없으면 중단하고 재승인 안내 (2단계)
/// 2. 읽을 구간 계산      last_synced_at 이 든 날의 자정부터 지금까지 (3단계)
/// 3. 하루 한 행으로 집계  lifelog_aggregate.dart
/// 4. 실패분 합치기       지난 주기에 못 보낸 행 (6단계)
/// 5. push + 재시도       30초 간격 3회 (6단계 · NFR-DV-002)
/// 6. 결과 저장          서버가 준 last_synced_at, 또는 실패분 보관
/// ```
///
/// **플랫폼 의존이 없습니다.** [HealthReader]·[SyncStore]·[LifelogService] 를
/// 주입받으므로 실기기 없이 전체 흐름을 테스트할 수 있습니다.
library;

import 'dart:async';

import 'package:flutter/foundation.dart';

import 'health_reader.dart';
import 'lifelog_aggregate.dart';
import 'lifelog_service.dart';
import 'sync_store.dart';

/// 한 번의 동기화 결과.
enum SyncOutcome {
  /// 보낼 게 있어서 보냈습니다.
  sent,

  /// 읽었지만 보낼 행이 없었습니다. 정상입니다.
  nothingToSend,

  /// 권한이 없습니다. **재승인 안내가 필요합니다**(MLCM_200 2단계).
  permissionDenied,

  /// Health Connect 앱이 없습니다. 설치 안내가 필요합니다.
  unavailable,

  /// 3회까지 실패했습니다. 행은 단말에 보관됐고 다음 주기에 다시 보냅니다.
  failedAndQueued,
}

class SyncResult {
  const SyncResult(this.outcome, {this.rowsSent = 0, this.rowsQueued = 0});

  final SyncOutcome outcome;
  final int rowsSent;
  final int rowsQueued;

  bool get isSuccess =>
      outcome == SyncOutcome.sent || outcome == SyncOutcome.nothingToSend;

  @override
  String toString() =>
      'SyncResult($outcome, sent=$rowsSent, queued=$rowsQueued)';
}

class LifelogSyncService {
  LifelogSyncService({
    required HealthReader reader,
    required SyncStore store,
    required LifelogService lifelogService,
    this.retryDelay = const Duration(seconds: 30),
    this.maxAttempts = 3,
    this.maxLookback = const Duration(days: 14),
  })  : _reader = reader,
        _store = store,
        _lifelog = lifelogService;

  final HealthReader _reader;
  final SyncStore _store;
  final LifelogService _lifelog;

  /// 재시도 간격. `MLCM_200` 6단계와 `NFR-DV-002` 가 30초를 규정합니다.
  final Duration retryDelay;

  /// 총 시도 횟수(첫 시도 포함). 규정은 「최대 3회」입니다.
  final int maxAttempts;

  /// 처음 연동했을 때 거슬러 올라갈 최대 기간.
  ///
  /// `MLCM_210` 이 기준값을 14일로 규정하므로 그만큼만 있으면 됩니다.
  /// 더 읽어봐야 분석에 안 쓰이고 첫 동기화만 느려집니다.
  final Duration maxLookback;

  /// 동기화 1회. 백그라운드 워커와 화면 양쪽에서 호출합니다.
  Future<SyncResult> sync({DateTime? now}) async {
    final at = now ?? DateTime.now();

    final permission = await _reader.permissionStatus();
    if (permission == HealthPermission.unavailable) {
      return const SyncResult(SyncOutcome.unavailable);
    }
    if (permission != HealthPermission.granted) {
      // ⚠ 권한이 없으면 **여기서 끝냅니다.** 큐를 비우지 않습니다.
      //   권한을 다시 켜면 보관된 행이 그대로 올라갑니다.
      return const SyncResult(SyncOutcome.permissionDenied);
    }

    final from = await _readWindowStart(at);
    List<HealthSample> samples;
    try {
      samples = await _reader.read(from: from, to: at);
    } catch (e) {
      debugPrint('Health Connect 읽기 실패: $e');
      samples = const [];
    }

    // ⚠ 체성분을 **먼저, 따로** 보냅니다. 라이프로그 전송이 실패해도 이건
    //   이미 올라가 있어야 합니다 — 둘은 다른 테이블이고 실패 원인도 다릅니다.
    //   여기서 던지면 라이프로그까지 못 가므로 예외를 삼킵니다.
    await _syncBodyComposition(samples);

    final fresh = aggregateDaily(samples);
    final rows = _merge(await _store.pendingRows(), fresh);

    if (rows.isEmpty) {
      // ⚠ 보낼 게 없어도 **last_synced_at 을 갱신하지 않습니다.** 갱신하면
      //   기기가 잠깐 데이터를 안 준 구간을 영영 다시 안 읽습니다.
      return const SyncResult(SyncOutcome.nothingToSend);
    }

    return _push(rows);
  }

  /// 체성분 전송 — `MAIN_LIFELOG_01` ❺.
  ///
  /// ## 왜 워터마크로 거르나
  ///
  /// `POST /body-composition` 은 **UPSERT 가 아니라 INSERT** 입니다. 같은
  /// 측정을 다시 보내면 이력에 중복 행이 남고, 사용자 화면에 같은 몸무게가
  /// 두 번 뜹니다. 라이프로그는 `uq_lifelog_user_collected` 가 막아주지만
  /// 체성분 테이블에는 그런 제약이 없습니다
  /// (→ `docs/검증/구현_갭_20260803.md`).
  ///
  /// ⚠ **한 건 보낼 때마다 워터마크를 옮깁니다.** 마지막에 한 번만 저장하면
  ///   중간에 실패했을 때 성공한 것까지 다시 보냅니다.
  ///
  /// ⚠ 실패해도 **던지지 않습니다.** 체성분은 선택 동의 항목이라 없는
  ///   사용자가 많고, 여기서 막히면 활동량·수면까지 못 올라갑니다.
  Future<void> _syncBodyComposition(List<HealthSample> samples) async {
    final all = aggregateBodyComposition(samples);
    if (all.isEmpty) return;

    final mark = await _store.lastBodyAt();
    final fresh = mark == null
        ? all
        : all.where((r) => r.measuredAt.isAfter(mark)).toList();

    for (final row in fresh) {
      try {
        await _lifelog.pushBodyComposition(row);
        await _store.saveLastBodyAt(row.measuredAt);
      } catch (e) {
        debugPrint('체성분 전송 실패(다음 주기에 다시 시도): $e');
        return;
      }
    }
  }

  /// 어디부터 읽을지.
  ///
  /// 마지막 동기화 시각이 든 **날의 자정**부터 읽습니다. 시각 그대로가 아닌
  /// 이유는 오늘 행이 하루 종일 갱신되기 때문입니다. 09:00 에 보낸 뒤
  /// 09:15 에 09:00 부터만 읽으면 **오늘 걸음이 15분치로 덮어써집니다.**
  Future<DateTime> _readWindowStart(DateTime now) async {
    final last = await _store.lastSyncedAt();
    final earliest = now.subtract(maxLookback);
    if (last == null) return dayStart(earliest);
    final start = dayStart(last);
    return start.isBefore(earliest) ? dayStart(earliest) : start;
  }

  /// 보관분과 새로 읽은 행을 합칩니다. 같은 날짜면 **새로 읽은 쪽**이 이깁니다.
  ///
  /// 새로 읽은 값이 Health Connect 의 현재 상태이고, 보관분은 그때의 스냅숏일
  /// 뿐입니다. 오래된 값으로 덮어쓰면 그날 데이터가 뒤로 갑니다.
  static List<DailyLifelog> _merge(
    List<DailyLifelog> pending,
    List<DailyLifelog> fresh,
  ) {
    final byDay = <DateTime, DailyLifelog>{};
    for (final r in pending) {
      byDay[dayStart(r.collectedAt)] = r;
    }
    for (final r in fresh) {
      byDay[dayStart(r.collectedAt)] = r;
    }
    final days = byDay.keys.toList()..sort();
    return [for (final d in days) byDay[d]!];
  }

  Future<SyncResult> _push(List<DailyLifelog> rows) async {
    Object? lastError;
    for (var attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        final syncedAt = await _lifelog.push(rows);
        // 서버가 확정한 시각을 씁니다. 앱 시계를 쓰면 단말 시간이 틀어졌을 때
        // 그 구간이 영구 유실됩니다(LifelogBatchResult 주석 참조).
        await _store.saveLastSyncedAt(syncedAt);
        await _store.clearPending();
        return SyncResult(SyncOutcome.sent, rowsSent: rows.length);
      } catch (e) {
        lastError = e;
        debugPrint('라이프로그 전송 실패 ($attempt/$maxAttempts): $e');
        if (attempt < maxAttempts) await Future<void>.delayed(retryDelay);
      }
    }

    // 최종 실패분은 단말에 보관했다가 다음 수집 주기에 함께 전송합니다.
    debugPrint('라이프로그 ${rows.length}건 보관 — 마지막 오류: $lastError');
    await _store.savePending(rows);
    return SyncResult(SyncOutcome.failedAndQueued, rowsQueued: rows.length);
  }
}
