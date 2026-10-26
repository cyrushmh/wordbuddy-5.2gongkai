# wordbuddy-github（总仓库 / Home Monorepo）

这是一个**单一 GitHub 仓库，作为所有任务的「主目录（home）」**，用来集中保存多个互不相关的项目 / 任务。**不再为每一类任务单独建仓**，从而避免反复创建 / 删除仓库、反复申请 PAT 的麻烦。

## 目录约定（核心）

- 本仓库 = 总 home。**根目录只放「总览文档 + 通用同步脚本」**。
- **整体就是整体，主系统（概念系统、组网系统）是一个整体目录；其余是组合、也是子系统、更是独立小项目**，每个自包含、互不影响：
  - `windows-internals-toolkit/` —— **主系统**：把 Windows 内核机理与优化分析工具集作为一个整体目录，内含
    - `Windows/` —— Windows Internals 工具集（PE 格式 / 磁盘优化 / Win10 整体优化 + 多语言多 GUI 的 PE Viewer）
    - `system-optimizer/` —— 万能系统优化与清理（Windows / macOS / Linux / Android / iOS，按系统+版本匹配，默认只分析不乱删）
    - `android/` —— Sysweeper Android 只读诊断 App（Kotlin/Compose，适配 Android 8–14，按 ABI 出 APK）
    - `tools/` —— 全仓库通用打包器与引导脚本（`syspkg.py` / `bootstrap.sh` / `bootstrap.ps1`）
    - `novel-website/`（未来示例）—— 小说网站构建（需要时才建）
    - `docs/`、`scripts/` 等
  - `classics-harmony-app/` —— **独立子项目**：HarmonyOS NEXT（ArkTS / Stage 模型）道家经典文库 App（含适老化与无障碍、组网无障碍）
  - 其他任务照此在根目录新建对应子目录即可
- 子目录内部保持自己的 `README`、`src/`、`docs/`、`tools/` 等结构，彼此隔离。
- **新增任务时**：在根目录新建对应子目录并把代码放进去，然后运行根目录的 `sync_to_github.py` 一键把整个仓库同步到 GitHub。

## 当前子项目

| 子目录 | 内容 | 入口说明 |
|---|---|---|
| `windows-internals-toolkit/` | **主系统**（概念系统 + 组网系统）：Windows Internals 工具集、跨平台系统优化清理、Android 诊断 App、通用打包器 | 见 [`windows-internals-toolkit/system-optimizer/README.md`](windows-internals-toolkit/system-optimizer/README.md) |
| `windows-internals-toolkit/Windows/` | Windows Internals 工具集（多语言 + 多 GUI） | 见 [`windows-internals-toolkit/Windows/README.md`](windows-internals-toolkit/Windows/README.md) |
| `windows-internals-toolkit/system-optimizer/` | 跨平台系统优化与清理（Windows/macOS/Linux/BSD/Unix/Android/iOS + uni-app 目标端 + 版本选择；语言按环境自动启用、硬件标准参考、网络/ITU 开关默认关闭需确认；`--report` 前后对比报告；`gui` 用 Python 自带 tkinter 点选；`uniapp-cleaner/` 为端上 storage 清理的真实可运行 uni-app 页面；`windows-automation/` 把 Windows 优化项固化成自包含 .bat（分析/执行/每周计划任务）） | 见 [`windows-internals-toolkit/system-optimizer/README.md`](windows-internals-toolkit/system-optimizer/README.md) |
| `windows-internals-toolkit/novel-website/` | 轻量零依赖小说网站骨架（HTML/JS + Node 内置 http 预览） | 见 [`windows-internals-toolkit/novel-website/README.md`](windows-internals-toolkit/novel-website/README.md) |
| `windows-internals-toolkit/android/` | Sysweeper Android 只读诊断 App（Kotlin/Compose，适配 Android 8–14，按 ABI 出 APK） | 见 [`windows-internals-toolkit/android/README.md`](windows-internals-toolkit/android/README.md) |
| `windows-internals-toolkit/tools/` | 统一打包器 `syspkg.py`（纯标准库）+ 引导脚本（POSIX sh / PowerShell） | 见 [`windows-internals-toolkit/tools/README.md`](windows-internals-toolkit/tools/README.md) |
| `classics-harmony-app/` | HarmonyOS NEXT 道家经典文库 App（适老化 + 无障碍 + 组网无障碍；ArkTS / Stage 模型） | 见 [`classics-harmony-app/BUILD.md`](classics-harmony-app/BUILD.md) |

## 同步到 GitHub

仓库为 **private**：`cyrushmh/wordbuddy-github`（外部不可见、无法 fork，便于个人保存与协作增删修补）。需要一个具备写权限的 PAT：

```bash
python3 sync_to_github.py <你的 GitHub PAT>
```

脚本会扫描整个仓库（跳过 `.git` / `target` / `__pycache__` 等构建产物），通过 GitHub **Git Data API** 直接重建 `main` 分支的目录树——无需 git 协议，适配沙箱网络限制。

## 语言底层（Language Layer）

整套工具有一条**最低门槛的主线**：用**多数系统默认就有的语言**跑起来，其余语言都是"有工具链才出"的加速层。

| 层 | 语言 | 为什么是它 | 产物 | 没有它怎么办 |
|---|---|---|---|---|
| **L0（底层）** | **Python 3.8+** | Linux / macOS / BSD 发行版默认自带，Windows 一条命令装；本包零第三方依赖 | 单文件 `sysweeper-<ver>.pyz`（zipapp）+ wheel + sdist | 见 `windows-internals-toolkit/tools/bootstrap.sh` 里各发行版的安装命令 |
| **L0（壳）** | **POSIX sh** | 所有 Unix 都有；Windows 有 PowerShell 5.1+ | `windows-internals-toolkit/tools/bootstrap.sh`（自动找 python3 → 跑 pyz） | `windows-internals-toolkit/tools/bootstrap.ps1` |
| **L1（加速）** | Go 1.21 / Rust | 需要额外安装工具链 | 7 个 (系统 × 架构) 静态二进制、Windows PE 原生工具 | 自动跳过，不影响 L0 |
| **L2（端上）** | Kotlin / ART | **Android 系统自带 ART 运行时**，Java/Kotlin 就是安卓的语言底层 | 按 ABI 拆分的 Android 14 APK | 免装 APK：PC 上 `python3 -m sysweeper android` 走 adb 只读审计 |

一句话：**有 python3 就能用全套；有 Go/Rust/JDK 就多拿原生二进制和 APK。**

## 低层码制（机器码 / 编译码 / 字符编码 / 通信码 / 逻辑转换码）

`sysweeper code` 是包内的「底层视图」：把要开网页计算器、翻手册、靠人肉心算的底层问题
变成**可验证的纯函数**。五层——`bits`（端序/位域/补码/格雷码/BCD/IEEE 754）、
`chars`（ASCII/Unicode/UTF-8/Base/转义/摩尔斯/字符集互转）、`comm`（CRC/校验和/成帧/线路编码/
汉明码/波特率）、`logic`（真值表/卡诺图/Quine-McCluskey/NAND/加法器）、
`machine`（Python 字节码/Java class/x86-64 指令拆解）——全部纯标准库、只读、随 `.pyz` 分发。

```bash
python -m sysweeper code                                        # 五层概览
python -m sysweeper code bits   --value -7 --width 8             # -7 的 8 位补码档案
python -m sysweeper code bits   --value 255 --action bases       # 二/三/八/十/十六进制对照（十进制可读默认）
python -m sysweeper code bits   --value 0xFF --action base --base 3  # 转三进制：100 110
python -m sysweeper code chars  --value d6d0cec4 --action mojibake   # 乱码：各编码试读
python -m sysweeper code comm   --value 010300000001 --action crc    # Modbus 帧 CRC 实测
python -m sysweeper code logic  --value 'A & B | !C' --action simplify  # 化简并验证等价性
python -m sysweeper code machine --action x86 --value 4889e5     # 拆一条 x86-64 指令
```

固定向量（CRC 8 变种 check 值、RFC 1071、Modbus、IEEE 754、COBS、汉明码穷举…）由 57 个单测
逐条断言；完整清单与**诚实边界**（x86 助记符是启发式提示、Java 反汇编是教学级、
进制限 2–36 且十进制为人类可读默认）见 [`windows-internals-toolkit/docs/低层码制.md`](windows-internals-toolkit/docs/低层码制.md)。

## 打包与分发（按系统 × 硬件）

所有产物由 CI 在打 `v*` tag 时构建并附到 GitHub Release；本地只保证工程配置正确。

| 目标系统 | 架构（ABI） | 来源 / 工程 | 产物 |
|---|---|---|---|
| **任意（有 python3.8+）** | noarch | `windows-internals-toolkit/tools/syspkg.py pyz`（Python 标准库 zipapp） | `sysweeper-<ver>.pyz` —— 一个文件，跨系统跨硬件直接跑 |
| Windows | x86_64 | `windows-internals-toolkit/Windows/`（C + Rust） | `peinfo.exe` / `peinfo32.exe` / `peview.exe` / `peinfo_rs.exe` |
| Windows | aarch64 (ARM64) | `windows-internals-toolkit/Windows/`（C + Rust，`aarch64-pc-windows-gnu`） | `peinfo-arm64.exe` / `peinfo_rs_arm64.exe` |
| Linux | x86_64 / aarch64 / riscv64 | `windows-internals-toolkit/system-optimizer/src/go`（纯标准库交叉编译） | `sysweeper-go-linux-{amd64,arm64,riscv64}` |
| macOS | x86_64 / aarch64 | `windows-internals-toolkit/system-optimizer/src/go` | `sysweeper-go-darwin-{amd64,arm64}` |
| Windows | x86_64 / aarch64 | `windows-internals-toolkit/system-optimizer/src/go` | `sysweeper-go-windows-{amd64,arm64}.exe` |
| Android | arm64-v8a / armeabi-v7a / x86_64 + 通用包 | `windows-internals-toolkit/android/`（Kotlin/Compose，compileSdk/targetSdk 34、minSdk 26） | `app-release-*.apk`（按 ABI 拆分 + universal） |
| HarmonyOS NEXT | phone / tablet / 2in1（API 12） | `classics-harmony-app/`（ArkTS / Stage 模型） | `entry-default-signed.hap`（调试签名；见 `build-harmony.yml`） |
| Python 包 | 平台无关（wheel + sdist） | `windows-internals-toolkit/system-optimizer/`（零第三方依赖） | `dist/` |

- **语言底层（.pyz）**：`python3 windows-internals-toolkit/tools/syspkg.py pyz` 一行出包；`python3 dist/sysweeper-<ver>.pyz detect` 直接跑。CI 见 `.github/workflows/build-python.yml`：只用 runner **系统自带**的 Python，并在 Linux / macOS / Windows 上验证同一个 .pyz。
- **Android APK**：见 [`windows-internals-toolkit/android/README.md`](windows-internals-toolkit/android/README.md)。真 APK 由 `.github/workflows/build-android.yml` 在 CI 上产出（本地无需 Android SDK）。
- **HarmonyOS HAP**：见 [`classics-harmony-app/BUILD.md`](classics-harmony-app/BUILD.md)。HAP 二进制需 HarmonyOS SDK + 签名（数 GB、需授权下载），沙箱无法出包；CI 见 `.github/workflows/build-harmony.yml`（需自托管 runner 装好 SDK）。
- **Go 多架构**：`.github/workflows/build.yml` 的 `build-go` 矩阵覆盖上述 7 个目标。
- **Windows PE 工具**：`windows-internals-toolkit/Windows/.github/workflows/build.yml` 交叉编译 x64 + arm64。
- **一条命令打全部**：`python3 windows-internals-toolkit/tools/syspkg.py all`（缺什么工具链就跳过什么，永不因此失败）。
- **诊断与护栏**（工程实践移植自 [DiPlay](windows-internals-toolkit/docs/DiPlay-参考分析.md)）：`python3 -m sysweeper diag`
  生成**默认脱敏**的诊断报告（只写本地，绝不自动上传）；`python3 windows-internals-toolkit/scripts/check_repo_guard.py`
  在 CI 第一道关拦截凭据容器 / 私钥块 / 白名单外的 Android 权限。
- **验证记录**：每次重要变更的测试数、产物校验和与"未验证项"记在 [`windows-internals-toolkit/docs/VALIDATION.md`](windows-internals-toolkit/docs/VALIDATION.md)。
- **CI 排错**：Actions 红了怎么读日志（先 `grep "##[error]"`、别从末尾读）、退出码速查、
  以及本仓库一次真实复盘（exit 120 = 管道断开、exit 1 = Windows 窄编码），
  见 [`windows-internals-toolkit/docs/CI-排错.md`](windows-internals-toolkit/docs/CI-排错.md)。

## 约定纪律

- **不为新类别建新仓**，统一用根目录下的子目录。
- 子项目固定在**稳定版 / LTS** 运行时，避免频繁重写（见各子目录的 `VERSIONS.md` / 工具链清单）。
- 每个优化 / 改动遵循「一次只改一项、可回退优先」。
