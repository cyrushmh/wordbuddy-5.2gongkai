# Sysweeper · Android 诊断 App

纯 Kotlin + Jetpack Compose 的**只读**系统诊断工具，把 `system-optimizer` 的 Android 只读探针口径移植到端上：
设备/API 信息、字体缩放与字重（适老化）、色彩校正/高对比度文本/放大镜（低视力）、深色模式、动画缩放、触感与提示音、
亮度/息屏/护眼夜览、TalkBack 与无障碍服务清单（视障）、开发者选项等。
**只读取系统设置，绝不修改、不 root、不写系统属性。**

## 语言底层：为什么是 Kotlin / ART

Android 系统自带 **ART 运行时**（Java / Kotlin 的执行引擎），所以 **Kotlin 就是安卓的语言底层**——
本工程因此坚持"纯 Kotlin + Compose、零 NDK、零第三方 SDK"：不引入需要额外工具链的依赖，
任何装了 Android SDK 的机器 `./gradlew assembleRelease` 就能出包。

对应到 PC 侧，语言底层换成 **Python 3**（多数系统默认自带），于是有两条并行的审计路径：

| 路径 | 语言底层 | 需要什么 | 适合场景 |
|---|---|---|---|
| **端上 APK**（本目录） | Kotlin / ART（安卓自带） | Android SDK + JDK 17（CI 出包） | 在手机上直接看诊断结果 |
| **免装审计**（推荐先试） | Python 3.8+（PC 自带） | `python3` + `adb` | PC 上只读审计真机，**手机不用装任何东西** |

```bash
# 免装路径：手机开 USB 调试连上电脑即可，全程只读（settings get / dumpsys）
python3 -m sysweeper android
# 或单文件版，无需 pip 安装
python3 dist/sysweeper-0000.0000.0000.0004.20261024.pyz android
```

## 适配范围

| 项目 | 取值 |
|---|---|
| `compileSdk` | 34（Android 14） |
| `targetSdk` | 34（Android 14） |
| `minSdk` | 26（Android 8，下探下限，与 `system-optimizer` 的 Android 8 适配一致） |
| 构建方式 | AAB/APK，按 ABI 拆分 + 通用包 |
| 权限 | 无（全部读取经公开 `Settings` Provider，包在 try/catch 中降级） |

## 工程结构

```
android/
  build.gradle.kts            # 根：声明 AGP / Kotlin 插件版本
  settings.gradle.kts
  gradle.properties
  gradle/wrapper/             # gradlew + gradle-wrapper.jar（bootstrap Gradle 8.9）
  app/
    build.gradle.kts          # namespace=com.sysweeper.android，splits.abi 按硬件分发
    src/main/
      AndroidManifest.xml     # 无危险权限
      java/com/sysweeper/android/
        MainActivity.kt       # Compose 入口 + 诊断列表
        probe/ProbeEngine.kt  # 只读探针（移植自 system-optimizer native/android.py）
        probe/model.kt        # ProbeResult / Severity
        ui/Theme.kt           # 深色主题
      res/values/{strings,themes}.xml
```

## 本地构建（需要 Android SDK）

> 沙箱环境无 Android SDK，以下命令在装有 Android SDK + JDK 17 的机器上执行。

```bash
# 首次：生成 wrapper（需联网拉取 Gradle 8.9；之后用 ./gradlew）
gradle wrapper --gradle-version 8.9

# 构建发布 APK（按 ABI 拆分 + 通用包）
./gradlew assembleRelease

# 产物：
#   app/build/outputs/apk/release/app-arm64-v8a-release.apk
#   app/build/outputs/apk/release/app-armeabi-v7a-release.apk
#   app/build/outputs/apk/release/app-x86_64-release.apk
#   app/build/outputs/apk/release/app-universal-release.apk
```

带签名（侧载分发）：

```bash
./gradlew assembleRelease \
  -PRELEASE_STORE_FILE=my.keystore \
  -PRELEASE_STORE_PASSWORD=*** \
  -PRELEASE_KEY_ALIAS=sysweeper \
  -PRELEASE_KEY_PASSWORD=***
```

若不注入 `-PRELEASE_*`，`assembleRelease` 回落到 debug keystore，仍可产出可安装 APK（适合自测）。

## CI 自动构建（推荐）

打 `v*` tag 时，[`../../.github/workflows/build-android.yml`](../../.github/workflows/build-android.yml) 会：

1. `actions/setup-java@v4`（JDK 17）+ 手动安装官方 Android cmdline-tools（`sdkmanager --licenses` + `platform-34` / `build-tools;34.0.0`）；
2. `keytool` 生成调试用 keystore；
3. `./gradlew assembleRelease` 产出 4 个 APK；
4. 上传 artifact，并把 APK 附到对应 GitHub Release。

无需本地 Android SDK——真包在 GitHub 托管机器上产出。

> 2026-10 起 CI 弃用 `android-actions/setup-android@v3`：该 action 在镜像内调用
> `sdkmanager` 安装已被 Google 移除的旧 `tools` 包（`Failed to find package 'tools'`
> → exit 1），导致整流程跳过并发出失败通知。现改为手动下载官方 cmdline-tools
> （`commandlinetools-linux-*.zip`，版本固定、可升级），规避镜像预装 SDK 的版本漂移。

## 探针口径（与 PC 侧 native/android.py 对齐）

| 门控 | 探针 |
|---|---|
| 全版本（API 26 起点） | 设备型号 / API / 版本 / ABI、字体缩放、色彩校正+模式、TalkBack、无障碍服务清单、三项动画缩放、触感反馈、提示音、亮度、息屏超时、开发者选项 |
| API 28+（Android 9） | 可调字重、护眼/夜览 |
| API 29+（Android 10） | 高对比度文本、设置侧深色模式（ui_night_mode） |

低于所需 API 时明说「此版本无此开关」，绝不伪装成已开启；每项读取都包 try/catch，读不到即降级为手动核对提示。

## 一条命令打全部（含 APK）

仓库根 `tools/syspkg.py` 会先探测工具链，检测到 JDK 17+ 才构建 APK，否则跳过（不失败）：

```bash
python3 tools/syspkg.py probe        # 看这台机器能产出什么
python3 tools/syspkg.py android      # 只打 APK，并复制到 dist/
python3 tools/syspkg.py all          # pyz + wheel + sdist + Go + Rust + APK
```

## 接入更多探针

在 `probe/ProbeEngine.kt` 的 `scan()` 中追加 `ProbeResult(...)`，保持「只读 + try/catch 降级」底线即可；
`MainActivity` 的 `LazyColumn` 会自动渲染新增条目。
