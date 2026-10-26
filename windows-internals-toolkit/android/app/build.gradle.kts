plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.sysweeper.android"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.sysweeper.android"
        minSdk = 26
        targetSdk = 34
        versionCode = 23
        versionName = "0.5.23"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    // 签名：CI 通过 -PRELEASE_* 注入 keystore；本地/缺省回落到 debug keystore，
    // 保证 assembleRelease 在没有外部密钥时也能产出可侧载的 APK。
    signingConfigs {
        create("releaseCI")
        getByName("debug")
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
            signingConfig = if (project.hasProperty("RELEASE_STORE_FILE")) {
                signingConfigs.getByName("releaseCI").apply {
                    storeFile = file(project.property("RELEASE_STORE_FILE")!!)
                    storePassword = project.property("RELEASE_STORE_PASSWORD") as String
                    keyAlias = project.property("RELEASE_KEY_ALIAS") as String
                    keyPassword = project.property("RELEASE_KEY_PASSWORD") as String
                }
            } else {
                signingConfigs.getByName("debug")
            }
        }
    }

    // 按 ABI 拆分 + 通用包：满足 Android 三 ABI（arm64-v8a / armeabi-v7a / x86_64）分发。
    splits {
        abi {
            isEnable = true
            reset()
            include("arm64-v8a", "armeabi-v7a", "x86_64")
            isUniversalApk = true
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
    }
    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.14"
    }
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.09.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.activity:activity-compose:1.9.2")
    implementation("androidx.core:core-ktx:1.13.1")
    debugImplementation("androidx.compose.ui:ui-tooling")
}
