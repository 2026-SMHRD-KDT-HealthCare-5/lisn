plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
    // FCM 발송 경로 — `MLCM_220` 4단계 · `MLCM_200` 7단계 · `MLCM_400` 5단계 · `NFR-DV-002`
    //
    // ⚠ `google-services.json` 이 `android/app/` 에 있어야 합니다. **저장소에는
    //   없습니다**(공개 저장소라 `.gitignore` 로 막았습니다). 새 PC 에서는
    //   Firebase 콘솔에서 내려받으세요 → `docs/SETUP.md`
    id("com.google.gms.google-services")
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
