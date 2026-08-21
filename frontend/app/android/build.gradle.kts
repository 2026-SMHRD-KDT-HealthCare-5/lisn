allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}
subprojects {
    project.evaluationDependsOn(":app")
}

// ⚠ workmanager_android 0.9.1+1 은 AGP 9 에서 Kotlin 이 컴파일되지 않습니다.
//
// 이 플러그인은 build.gradle 에서 `if (agpMajor < 9) apply plugin: 'kotlin-android'`
// 로 KGP 적용을 건너뛰고 AGP 9 의 Built-in Kotlin 에 맡깁니다. 그런데 소스는
// `main.java.srcDirs += 'src/main/kotlin'` 로 **java** 소스셋에 넣기 때문에,
// KGP 가 없으면 .kt 파일을 아무도 컴파일하지 않습니다.
//
// 증상이 고약합니다 — **모듈 빌드는 에러 없이 성공**하고, 클래스만 안 만들어져서
// 앱 컴파일 단계에서 이렇게 납니다.
//     GeneratedPluginRegistrant.java:59: error: cannot find symbol
//       new dev.fluttercommunity.workmanager.WorkmanagerPlugin()
//
// 여기서 KGP 를 대신 적용해 우회합니다. 같은 방식으로 소스를 넣는 health 는
// KGP 를 항상 적용하기 때문에 정상 동작합니다.
//
// 플러그인이 AGP 9 를 지원하면 이 블록을 지우세요. 확인 방법:
//     find build/workmanager_android -name "WorkmanagerPlugin*"
//   이 블록 없이도 결과가 나오면 지워도 됩니다.
subprojects {
    if (name == "workmanager_android") {
        apply(plugin = "org.jetbrains.kotlin.android")

        // 이 모듈은 Java 를 1.8 로 컴파일합니다. Kotlin 쪽 jvmTarget 설정도
        // `if (agpMajor < 9)` 안에 있어서 같이 건너뛰어지므로, 여기서 맞춰
        // 줍니다. 안 맞추면 Kotlin 이 21 로 잡혀 이렇게 납니다.
        //     Inconsistent JVM-target compatibility detected for tasks
        //     'compileDebugJavaWithJavac' (1.8) and 'compileDebugKotlin' (21)
        tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>()
            .configureEach {
                compilerOptions.jvmTarget.set(
                    org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_1_8,
                )
            }
    }
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
