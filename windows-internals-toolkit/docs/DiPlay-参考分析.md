# DiPlay 参考分析（学习与可迁移点）

> 调研对象：<https://github.com/shihabal3amri/DiPlay> —— 面向比亚迪安卓车机的**独立 CarPlay 接收端**
> （有线 + 无线，公开预览版 0.2.14）。基于 xcertplay（GPL-3.0），界面/网站改编自 DiAuto（AGPL-3.0）。
> 调研方式：GitHub API 文件树（908 个 blob）+ 关键源码/构建脚本/CI/文档原文。
> 本文目的：**学它的工程方法，挑能落到本仓库的部分；协议与硬件相关部分只学不做。**

---

## 1. 它是什么：一句话与分层

一句话：在车机（Android 9+ 车机）上，用**自己的协议栈**冒充/实现 CarPlay 配件，让 iPhone 投屏到车机，
并把导航/歌曲/转向信息再投射到比亚迪的 HUD 与仪表盘。

```
iPhone ──(iAP2 over USB NCM/Ethernet·IPv6 或 蓝牙 RFCOMM)──► 车机
       ──(AirPlay over Wi-Fi Direct / 车机热点 / 同局域网)──► 车机
                          │
                   DiPlay 协议栈（Kotlin）
                          │
        ┌─────────────────┼──────────────────┐
        ▼                 ▼                  ▼
   中控 CarPlay 画面   BYD HUD / 仪表投射   车辆数据（自实现 ADB）
```

## 2. 工程结构（模块划分值得抄）

| 模块 | 角色 | 文件量 |
|---|---|---|
| `shared`（485） | **协议栈与算法**：iAP2、MFi、AirPlay、USB/NCM、蓝牙、媒体编解码、BYD HUD | 211 源文件 |
| `common`（320） | **UI 与设置**：设置架构、诊断日志、车辆后端、多语言资源 | 78 源文件 |
| `mobile` | 车机主应用（`:mobile`，包名 `com.shihab.diplay`） | 薄壳，依赖上面两个 |
| `automotive` | 继承自 xcertplay 的 Android Automotive 应用 | 独立 |
| `samples/home` | DiPlay Home 启动器（地图 +  widgets + 应用列表） | 示例 |
| `samples/maphost` | 地图托管示例应用 | 示例 |

关键观察：**协议/算法层（shared）与 UI/产品层（common）彻底分离，应用只是薄壳**。
测试占比极高：576 个代码文件里 **271 个是测试**（shared 156、common 115）——近 47%。

### 协议栈解剖（shared/src/main/java/com/shilapi/xcertplay/）

| 包 | 文件数 | 职责 | 代表类 |
|---|---|---|---|
| `transport` | 34+22 | 物理/链路：USB Host、NCM、NTB16、Ethernet-over-IPv6 编解码、CH341 I²C 桥、蓝牙 RFCOMM | `IphoneUsbHost`、`NcmUsbBridge`、`Ntb16Codec`、`Ch341I2cTransport`、`BluetoothRfcommDuplexStream` |
| `iap2` | 9 | iAP2 帧格式/会话/编解码（Apple 配件协议） | `Iap2Wire`、`Iap2Session`、`Iap2CsmFramer` |
| `mfi` | 7 | MFi 认证（本地离线身份 / 远端） | `LocalMfiAuthenticationClient`、`MfiSelfCheck` |
| `airplay` | 39 | AirPlay 会话、加密（ChaCha/AES）、HID 触摸、音频、视频布局、仪表盘画面 | `AirPlayCrypto`、`AirPlayHid`、`CarPlayMediaEngine`、`BplistCodec` |
| `network` | 42 | Wi-Fi Direct、车机热点、同局域网、Bonjour 发现、端口选择、VPN 作用域 | `CarPlayBonjour`、`HotspotJoin*`、`ExistingWifiManager` |
| `hud` | 40 | **比亚迪私有协议**：HUD 报文、仪表帧、转向码、车速、DiLink 3 适配 | `BydHudProtocol`、`BydClusterFrame`、`BydFactoryTurnCode` |
| `media` | 23 | MediaCodec 视频、音频轨道、回声消除（SpeexDSP JNI）、触摸映射、帧节奏 | `AndroidMediaSink`、`SpeexEchoCanceller`、`FramePacer` |
| `orchestration` | 9 | 连接编排、看门狗、配置、诊断计数 | `CarPlayController`、`FirstTcpWatchdog` |
| `adb` | 3 | **自己实现的 ADB 客户端**（不走 adb 二进制） | `AdbKeys`、`AdbPacket`、`LocalAdb` |

### 技术选型

- Kotlin + Jetpack Compose；**JDK 25**、`compileSdk/targetSdk 37`、`minSdk 28`、NDK 28（仅 SpeexDSP 回声消除）
- 多模块 Gradle（版本目录 `libs.*`）、配置缓存开启、模块化 lint/单测
- 7 种语言资源（英/简中/繁中/阿/俄/乌克/西），**翻译完整性由测试守护**

## 3. 最值得抄的 8 条工程实践

### ① 有界异步诊断写入器 `BoundedDiagnosticWriter`

```kotlin
// 单 daemon 写线程 + 有界队列；超载丢最旧，enqueue 永不阻塞调用方
private val pending = ArrayDeque<T>()      // maxPending = 64
fun enqueue(entry: T): Boolean = synchronized(monitor) {
    if (pending.size == maxPending) { pending.removeFirst(); dropped++ }
    pending.addLast(entry); monitor.notifyAll(); true
}
// 写入失败用 runCatching 吞掉：磁盘坏/回调抛异常都不影响后续写入
// awaitIdle(timeout) 给测试用；close() 只停止接收并排空
```

要点：**日志/诊断绝不能反向拖垮主链路**（连接、视频、UI 回调里都可能打日志）。

### ② 脱敏器 `DiagnosticRedactor`（导出即脱敏）

```kotlin
private val secret = Regex("(?i)(pass(word|phrase)?|token|private.?key|certificate|pair.?record|ssid|body=|payload=|hex=)")
fun redact(line: String): String? {
    if (secret.containsMatchIn(line) || namedDevice.containsMatchIn(line)) return null   // 整行丢弃
    return line.replace(mac, "[address]").replace(identifier, "[identifier]")
        .replace(address, "[ip]").replace(ipv6, "[ip]").take(700)
}
```

要点：**默认不信任输出**——命中凭据关键词整行丢弃；MAC/UUID/IPv4/IPv6 一律占位符；700 字符截断。
README 还明确要求用户"检查 .txt 并删除隐私信息"，并声明"报告不会自动上传"。

### ③ 构建期 + 提交期双重安全护栏

- Gradle 任务 `rejectBundledCredentials`：扫描 assets 里 `*.pk8/*.p7b/*.key/*.pem/*.p12/*.pfx/*.jks/*.keystore`，
  **只允许显式指定的两个文件**，其余一律构建失败；挂到 `preBuild`。
- CI 第一步 `python3 scripts/check_public_tree.py`：`git ls-files` 逐个查后缀黑名单 + PEM 私钥块正则。
- 签名密钥/身份全部走环境变量注入（`ANDROID_KEYSTORE_*`、`DIPLAY_AUTH_ASSETS_DIR`），**永不入 Git**。

### ④ 用测试守护"架构约定"（不是只测功能）

`AGENTS.md` 里写死规则，并用测试兜底：

| 测试 | 守护什么 |
|---|---|
| `SettingsLayoutPolicyTest` | 每个设置分区必须且只能属于一个分类 |
| `SettingsTranslationsTest` | `settings_*` 字符串必须有全语言翻译 |
| `AdaptiveSettingsUiTest` | 设置必须出现在"用户会去找"的分类里 |

外加一条产品规则：`markReconnectNeeded()` —— 改动会影响当前会话时必须提示"重连"，且**不得未经同意断开正在运行的会话**。

### ⑤ 发布可追溯 `docs/VALIDATION.md`

每版记录：源 commit/tree 哈希、**单测数量与分布**、lint 警告数、APK 字节数与 SHA-256、
签名证书 SHA-256（保证可原地升级）、native 库逐字节比对结果、**以及"哪些没验证"**。
例如 0.2.14：「1,822 单测，1,821 通过 + 1 个 macOS 预期跳过」「未做本版完整实车测试」。

> 这种"把没做的事也写清楚"的诚实度，是开源项目里少见的。

### ⑥ 文档密度与分层

39 篇 docs：`BUILD`（模块选择/环境/排查表）、`INSTALL`、`VALIDATION`、`PRIVACY`、`COMPATIBILITY`、
`TESTING`、每版 `RELEASE-NOTES-x.y.z`、`THIRD_PARTY_NOTICES`、`docs/licenses/*`（上游许可证原文）。
README 有中文/英文双份，且**明确声明**"未经 Apple 认证、身份来自公开固件提取、私钥可被提取"。

### ⑦ 环境变量驱动构建、debug 与 release 共存

```kotlin
debug { applicationIdSuffix = ".hudtest"; versionNameSuffix = "-hud-test" }
signingConfigs { create("release") { storeFile = file(env("ANDROID_KEYSTORE_PATH") ?: "missing-release-keystore.jks") } }
```
源码构建默认**无身份**（只能做源码验证），要出可连真机的包必须显式提供运行时资产——**默认安全**。

### ⑧ 给 AI/Agent 的明确规则（`AGENTS.md`，`CLAUDE.md` 只是 `@AGENTS.md`）

把"改完要跑哪条命令""新设置放哪个分类""实验性怎么标注（各语言各自的 `（实验性）`）"写成条目，
让 agent 与人类遵循同一套约定。

## 4. 与本仓库的对照：可迁移清单

| # | DiPlay 做法 | 本仓库现状 | 迁移建议 | 优先级 |
|---|---|---|---|---|
| 1 | 有界异步诊断日志 | 无（报告一次性生成） | 新增 `sysweeper/diagnostics.py`：有界队列 + 单写线程 + 超载丢最旧 + 写失败不中断 | **高** |
| 2 | 导出即脱敏 | `report.py` 原样输出（含 IP/路径/主机名） | 新增 `Redactor`：凭据关键词整行丢弃、IP/MAC/UUID/家目录占位符化、默认开启 | **高** |
| 3 | `check_public_tree.py` | 无 | 新增 `scripts/check_repo_guard.py`：私钥块 + 凭据后缀 + APK/AAB 扫描，接 CI | **高** |
| 4 | Manifest 权限白名单护栏 | `android/` 已在 README 声明零权限 | 用脚本解析 `AndroidManifest.xml` 校验权限清单，接 CI，防止日后加权限 | 中 |
| 5 | 测试守护架构约定 | 345 测试多为功能测试 | 补不变量测试：任务 id 唯一、每项必须有 standard/risk、探针只读（禁止写命令） | 中 |
| 6 | `VALIDATION.md` 发布记录 | 只有 CHANGELOG 式提交信息 | 新增 `docs/VALIDATION.md`：每版记录 commit、测试数、产物 SHA-256、未验证项 | 中 |
| 7 | 多语言翻译完整性测试 | 中文为主 | 若后续加英文资源，用测试守护 key 一致 | 低 |
| 8 | debug 与 release 共存（applicationIdSuffix） | 单一 applicationId | 可选：debug 加 `.debug` 后缀便于同机并存 | 低 |
| — | iAP2/MFi/AirPlay 协议栈 | 不涉及 | **不做**：法律风险（未认证配件身份）+ 无硬件 + 违背零依赖 | 不做 |
| — | NDK/JNI（SpeexDSP） | 无 | **不做**：我们的语言底层是 Python，Kotlin 端也应保持零 NDK | 不做 |

### 关于"自实现 ADB"的判断

DiPlay 在车机端自己实现了 ADB（RSA 2048 密钥 + AOSP `android_pubkey` 编码 +
`NONEwithRSA(SHA1 DigestInfo)` 签名），因为车机上没有 adb 二进制、且要长期记住一次授权。

**我们 PC 侧不照做**：Python 标准库无法生成/解析 RSA 密钥（那会破坏"零第三方依赖"的底线），
所以 PC 侧继续用系统 `adb` 二进制是对的。但它"一次授权长期复用""TCP 优先、USB 兜底""失败有界"
的连接策略，值得在 `sysweeper/native/android.py` 里对齐（未来增强项，本轮不做）。

## 5. 本轮实际落地

1. `system-optimizer/src/python/sysweeper/diagnostics.py` —— 有界异步诊断日志 + 默认脱敏（对应 ①②）
2. CLI 新增 `sysweeper diag` —— 生成脱敏诊断包，写盘后**只提示路径，绝不自动上传**（对应 ②）
3. `scripts/check_repo_guard.py` + CI 步骤 —— 私钥块/凭据容器/APK 扫描 + AndroidManifest 权限白名单（对应 ③④）
4. `docs/VALIDATION.md` —— 本仓库首个验证记录条目（对应 ⑤⑥）

## 6. 结论

DiPlay 给的最有价值的不是协议（那是它的领域壁垒，也伴随法律风险），而是**一套"让软件在真实设备上可诊断、
发布可追溯、凭据零入仓"的工程纪律**。这几条恰好和我们仓库已有的"只读底线、默认只分析不乱删、零依赖"
是同一种气质，移植成本极低——所以本轮只取这四条，协议栈与 NDK 一律不碰。
