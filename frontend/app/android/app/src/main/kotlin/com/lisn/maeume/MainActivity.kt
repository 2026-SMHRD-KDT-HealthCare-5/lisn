package com.lisn.maeume

import io.flutter.embedding.android.FlutterFragmentActivity

/**
 * ⚠ FlutterActivity 가 아니라 **FlutterFragmentActivity** 입니다.
 *
 * Health Connect 권한 요청은 AndroidX Activity Result API 를 쓰는데, health
 * 플러그인이 이를 Fragment 기반으로 띄웁니다. FlutterActivity 로 두면 권한
 * 다이얼로그가 뜨지 않고 요청이 조용히 거부됩니다.
 * (health 패키지 README "Android: Health Connect 설정" 참조)
 */
class MainActivity : FlutterFragmentActivity()
