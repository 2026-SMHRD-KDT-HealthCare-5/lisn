plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// FCM 발송 경로 — `MLCM_220` 4단계 · `MLCM_200` 7단계 · `MLCM_400` 5단계 · `NFR-DV-002`
//
// ⚠ `google-services.json` 이 `android/app/` 에 있어야 이 플러그인이 읽습니다.
//   **저장소에는 없습니다**(공개 저장소라 `.gitignore` 로 막았습니다).
//
//   전에는 이 플러그인을 위 plugins{} 블록에서 무조건 적용했는데, 그러면
//   파일이 없을 때 `processDebugGoogleServices` 단계에서 **빌드 자체가
//   실패**했습니다(2026.08.25 실측). settings.gradle.kts 주석과
//   docs/SETUP.md 는 둘 다 "없어도 앱은 뜬다, 푸시만 죽는다"고 약속하고
//   있었는데 그 약속과 실제 동작이 어긋나 있었습니다 — 파일이 있을 때만
//   적용해서 그 약속에 실제로 맞췄습니다.
//
//   새 PC 에서 FCM 을 쓰려면 Firebase 콘솔에서 받으세요 → docs/SETUP.md
if (file("google-services.json").exists()) {
    apply(plugin = "com.google.gms.google-services")
} else {
    logger.warn("⚠ google-services.json 없음 — FCM 푸시 없이 빌드합니다. docs/SETUP.md 참고")
}

android {
    namespace = "com.lisn.maeume"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        applicationId = "com.lisn.maeume"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.

        // Health Connect(androidx.health.connect:connect-client)가 API 26 을 요구한다.
        // Flutter 기본값(flutter.minSdkVersion)은 이보다 낮아 연동 패키지를 추가하는 순간
        // manifest merger 단계에서 빌드가 실패한다.
        // ※ 실제 사용할 Flutter 패키지가 더 높은 값을 요구할 수 있으므로 패키지 선정 후 재확인할 것.
        minSdk = 26
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    buildTypes {
        release {
            // TODO: Add your own signing config for the release build.
            // Signing with the debug keys for now, so `flutter run --release` works.
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}
