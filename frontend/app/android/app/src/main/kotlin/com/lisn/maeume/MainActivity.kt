package com.lisn.maeume

import io.flutter.embedding.android.FlutterFragmentActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

/**
 * ⚠ FlutterActivity 가 아니라 **FlutterFragmentActivity** 입니다.
 *
 * Health Connect 권한 요청은 AndroidX Activity Result API 를 쓰는데, health
 * 플러그인이 이를 Fragment 기반으로 띄웁니다. FlutterActivity 로 두면 권한
 * 다이얼로그가 뜨지 않고 요청이 조용히 거부됩니다.
 * (health 패키지 README "Android: Health Connect 설정" 참조)
 */
class MainActivity : FlutterFragmentActivity() {

    /** 앱 사용 로그 채널 — [AppUsagePlugin] 참조. */
    private val usageChannel = "com.lisn.maeume/app_usage"

    override fun configureFlutterEngine(engine: FlutterEngine) {
        super.configureFlutterEngine(engine)
        MethodChannel(engine.dartExecutor.binaryMessenger, usageChannel)
            .setMethodCallHandler { call, result ->
                AppUsagePlugin.handle(applicationContext, call.method, call.arguments, result)
            }
    }
}
