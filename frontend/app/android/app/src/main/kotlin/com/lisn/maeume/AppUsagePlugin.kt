package com.lisn.maeume

import android.app.AppOpsManager
import android.app.usage.UsageEvents
import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Process
import android.provider.Settings
import io.flutter.plugin.common.MethodChannel
import java.util.Calendar

/**
 * 앱 사용 로그 수집 — 기업 브리프(PROJECT_02) 개발목표의
 * 「**앱 사용 로그** + 웨어러블 생체신호」 중 앞쪽.
 *
 * ⚠ **패키지명·앱 이름을 밖으로 내보내지 않습니다.**
 *   [collect] 가 돌려주는 것은 집계값 셋뿐입니다. 「무슨 앱을 썼나」가 아니라
 *   「평소와 다른가」를 재는 것이 목적이고, 판정(`ai/server/main.py`)도
 *   개인 기준선 대비 이탈만 봅니다.
 *
 * ⚠ **AccessibilityService 를 쓰지 않습니다.**
 *   그쪽은 화면 내용까지 읽을 수 있어 Play 정책상 별도 심사 대상이고,
 *   우리가 필요한 것보다 훨씬 많은 것을 볼 수 있습니다. `UsageStatsManager`
 *   는 「어떤 앱이 언제 앞으로 나왔나」만 주므로 최소 수집에 맞습니다.
 *
 * ⚠ **PACKAGE_USAGE_STATS 는 일반 권한이 아닙니다.**
 *   `requestPermission()` 으로 시스템 다이얼로그를 띄울 수 없고, 설정 화면
 *   (`ACTION_USAGE_ACCESS_SETTINGS`)으로 보내 사용자가 직접 켜야 합니다.
 *   승인하지 않아도 앱은 그대로 동작하고, 웨어러블 지표만으로 판정합니다.
 */
object AppUsagePlugin {

    /** 야간으로 셀 시간대. 22시~06시. */
    private const val NIGHT_START_HOUR = 22
    private const val NIGHT_END_HOUR = 6

    /** 이보다 짧은 포그라운드 구간은 오갈 때 스친 것으로 보고 버린다. */
    private const val MIN_SESSION_MS = 3_000L

    fun handle(context: Context, method: String, args: Any?, result: MethodChannel.Result) {
        when (method) {
            "hasPermission" -> result.success(hasPermission(context))
            "openSettings" -> {
                openSettings(context)
                result.success(null)
            }
            "collect" -> {
                @Suppress("UNCHECKED_CAST")
                val map = args as? Map<String, Any> ?: emptyMap()
                val from = (map["from"] as? Number)?.toLong()
                val to = (map["to"] as? Number)?.toLong()
                if (from == null || to == null || to <= from) {
                    result.error("BAD_RANGE", "from/to 가 없거나 순서가 뒤집혔습니다", null)
                    return
                }
                if (!hasPermission(context)) {
                    //  ⚠ 빈 값이 아니라 null 을 돌려준다. 「0분 썼다」와
                    //    「권한이 없어 모른다」는 다르고, 0 으로 적재하면
                    //    기준선이 통째로 망가진다.
                    result.success(null)
                    return
                }
                result.success(collect(context, from, to))
            }
            else -> result.notImplemented()
        }
    }

    private fun hasPermission(context: Context): Boolean {
        val ops = context.getSystemService(Context.APP_OPS_SERVICE) as AppOpsManager
        val mode = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ops.unsafeCheckOpNoThrow(
                AppOpsManager.OPSTR_GET_USAGE_STATS,
                Process.myUid(),
                context.packageName,
            )
        } else {
            @Suppress("DEPRECATION")
            ops.checkOpNoThrow(
                AppOpsManager.OPSTR_GET_USAGE_STATS,
                Process.myUid(),
                context.packageName,
            )
        }
        return mode == AppOpsManager.MODE_ALLOWED
    }

    private fun openSettings(context: Context) {
        val intent = Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS)
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(intent)
    }

    /**
     * [from]~[to] 구간의 집계값 셋.
     *
     * `queryEvents` 로 포그라운드 진입/이탈 쌍을 이어 붙여 구간을 만듭니다.
     * `queryUsageStats` 를 쓰지 않는 이유는 그쪽이 **하루 단위로 뭉친 값**만
     * 주기 때문입니다 — 야간 사용 시간을 갈라낼 수 없습니다.
     */
    private fun collect(context: Context, from: Long, to: Long): Map<String, Int> {
        val usm = context.getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
        val events = usm.queryEvents(from, to)

        //  패키지별로 마지막 진입 시각만 들고 있는다. 이름은 집계 뒤 버린다.
        val entered = HashMap<String, Long>()
        var totalMs = 0L
        var nightMs = 0L
        var sessions = 0

        val e = UsageEvents.Event()
        while (events.hasNextEvent()) {
            events.getNextEvent(e)
            when (e.eventType) {
                UsageEvents.Event.ACTIVITY_RESUMED -> entered[e.packageName] = e.timeStamp
                UsageEvents.Event.ACTIVITY_PAUSED,
                UsageEvents.Event.ACTIVITY_STOPPED -> {
                    val start = entered.remove(e.packageName) ?: continue
                    val end = e.timeStamp
                    if (end - start < MIN_SESSION_MS) continue
                    totalMs += end - start
                    nightMs += nightOverlapMs(start, end)
                    sessions++
                }
            }
        }
        //  구간 끝에서 아직 안 닫힌 것은 to 로 닫는다
        for ((_, start) in entered) {
            if (to - start < MIN_SESSION_MS) continue
            totalMs += to - start
            nightMs += nightOverlapMs(start, to)
            sessions++
        }

        return mapOf(
            "screen_time_min" to (totalMs / 60_000L).toInt(),
            "night_screen_min" to (nightMs / 60_000L).toInt(),
            "app_session_count" to sessions,
        )
    }

    /**
     * [start]~[end] 중 22시~06시에 걸친 밀리초.
     *
     * ⚠ 자정을 넘는 구간이 흔하므로 **하루씩 잘라서** 겹침을 잰다. 그냥
     *   시(hour)만 보고 판정하면 23:50~00:20 같은 구간이 통째로 빠지거나
     *   통째로 들어간다.
     */
    private fun nightOverlapMs(start: Long, end: Long): Long {
        var acc = 0L
        val cal = Calendar.getInstance()
        cal.timeInMillis = start
        cal.set(Calendar.HOUR_OF_DAY, 0)
        cal.set(Calendar.MINUTE, 0)
        cal.set(Calendar.SECOND, 0)
        cal.set(Calendar.MILLISECOND, 0)

        var day = cal.timeInMillis
        while (day < end) {
            val nextDay = day + 86_400_000L
            //  그날의 밤: [22시, 다음날 06시)
            val nightA = day + NIGHT_START_HOUR * 3_600_000L
            val nightB = nextDay + NIGHT_END_HOUR * 3_600_000L
            acc += overlap(start, end, nightA, nightB)
            //  그날 새벽(전날 밤의 꼬리)은 위 구간이 이미 덮으므로 중복하지 않는다
            day = nextDay
        }
        //  구간이 시작일 새벽에 걸린 경우 — 전날 밤 구간을 한 번 더 본다
        acc += overlap(
            start, end,
            cal.timeInMillis - 86_400_000L + NIGHT_START_HOUR * 3_600_000L,
            cal.timeInMillis + NIGHT_END_HOUR * 3_600_000L,
        )
        return acc.coerceAtMost(end - start)
    }

    private fun overlap(a1: Long, a2: Long, b1: Long, b2: Long): Long =
        (minOf(a2, b2) - maxOf(a1, b1)).coerceAtLeast(0L)
}
