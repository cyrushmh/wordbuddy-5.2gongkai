# 35 · 三个标准知识库同日落地 + APK 工程补全（v0.6.67）

> 指令原文：「继续被中断；完善补全apk，邮件提示失败，检查国内标准以及gms标准，整两个；继续」。
> 本档案记录 v0.6.67 的执行闭环：先修 CI 失败的 Android APK 与卡死的 Harmony HAP，再按「整两个」建两个标准知识库，随后按用户追加指令「如果不能gms可以试试fdroid标准，github有，国内只要能下载就能安装」补上第三个（F-Droid 免 GMS 分发标准）。

## 一、APK 与 CI（先修被中断的）

- **Android APK CI 失败根因**：`android-actions/setup-android@v3` 内部调用镜像内 sdkmanager 安装已被 Google 移除的 `tools` 包 → `Failed to find package 'tools'` → exit 1 → 后续步骤跳过 → 失败通知邮件。修复：弃用该 action，手动下载官方 `commandlinetools-linux-11076708_latest.zip`，解压至 `$ANDROID_HOME/cmdline-tools/latest`（sdkmanager 自洽性要求该路径，错误信息可证），`yes | sdkmanager --licenses` 后装 platform-tools / platforms;android-34 / build-tools;34.0.0。已实测：URL 206 可达、zip 内部结构匹配、`sdkmanager --version` = 12.0、licenses 链路可拉远端仓库。
- **HarmonyOS HAP 三连空排队根因**：`build-harmony.yml` 绑定 `runs-on: [self-hosted, harmonyos]`，仓库从未注册该 runner → push 触发永久 queued。已取消 3 个运行（HTTP 202），触发收敛为仅 `workflow_dispatch`。
- **ProbeEngine.kt 探针补全**：从 9 项扩至约 20 项（font.weight / a11y.high_text_contrast / a11y.magnification / a11y.services / anim.window / anim.transition / anim.animator / haptic.feedback / sound.effects / screen.brightness / screen.timeout / eyecare.night），全部 API 门控 + try/catch 降级，describeSdk 扩至 26-36（含 Android 15/16）；版本号 22/0.5.22 → 23/0.5.23。无 Android SDK 环境，用 Kotlin 1.9.24 语法级自检（kotlinc 报错集合仅为 android.* 预期符号）。

## 二、三个标准知识库（「整两个」+「试试 fdroid」）

三库共用同一范式：`data/<key>_*.json`（按语义 key 组织，8 字段）+ native 只读层（零参可调报告 + 检查清单逐条回链 key）+ tasks（5 个指引类，category=privacy）+ 四入口接线（CLI / GUI / subsystems / registry）+ linkage 轴接入。红线一致：**只读知识库 + 出检查项，不扫描、不联网、不代执法/审/分发**。

| 子系统 | 条目数 | 实检口径 |
|---|---|---|
| `androidstd` 国内标准·App 隐私合规 | 13 | PIPL + 4 国标 + 4 部门文件 + TC260 2 规程，**全部官方源实检**（openstd.samr.gov.cn / cac.gov.cn / miit.gov.cn / gov.cn / tc260.org.cn，2026-10 检索日） |
| `gmsstd` GMS 兼容与 Play 标准 | 10 | CDD/CTS/VTS（source.android.google.cn 实检）+ Play Integrity / App Signing / targetSdk / Data safety（developer.android.google.cn / play.google.com 实检）；**STS 官方单页未实检到 → 社区整理源逐条标 `needs_verify`**，诚实边界不臆造 |
| `fdroidstd` F-Droid 免 GMS 分发标准 | 10 | f-droid.org 直连不可达（.org 域被墙），取官方中文/韩文文档检索快照 + **GitHub/GitLab API 仓库层实检**（f-droid/fdroidclient GPL-3.0 3222★、f-droid/fdroiddata 358★、顶层 metadata/templates/srclibs/repo/tools/schemas）+ Wikipedia（2010 年创建 / F-Droid Limited 非营利运营 / 免账号） |

关键事实（均经实检）：

- **Play targetSdk 门槛**：2026-08-31 起新 App 与更新须 target Android 16（API level 36）或更高；Wear OS 与 Android Automotive OS 例外，须 target Android 15（API 35）。此前 2025-08-31 节点为 API 34。
- **Play App Signing**：上传密钥（.jks，RSA≥2048）开发者自管可重置；应用签名密钥（Google 生成 4096 位 RSA / 自定义 ≥2048）托管 Google 不可取回；条款 2021-08-01 生效；AAB 强制接入；符合条件应用自动走 v4 签名。
- **Play Integrity API**：三类核心 verdict（appLicensingVerdict=LICENSED / appRecognitionVerdict=PLAY_RECOGNIZED / deviceIntegrity 分层）+ 四类可选风险信号；默认每应用每日 10,000 次请求；官方建议分层执法而非二元封禁。
- **CTS**：免费商业级测试套件，Trade Federation（自动化）+ CTS Verifier（手工），八大测试域（签名/平台 API/Dalvik/数据模型/Intent/权限/资源/CTS-V）。
- **GMS 与 CTS 关系**（官方原话）：SafetyNet Attestation 是「用于确定设备是否与 CTS 兼容」的 API；GMS「安装到兼容的 Android 设备上」、非 AOSP 一部分。
- **F-Droid 反特征官方列表**：Ads / Disabled Algorithm / Known Vulnerability / Non-Free Addons / Non-Free Network Services / Non-Free Dependencies / Tracking / UpstreamNonFree / NoSourceSince——不阻断收录但必须透明标注。
- **F-Droid 与国内**：免 GMS、免账号、**能下载即可安装**——正是国内拿不到 GMS 授权时分发的标准答案；零依赖 App 是主收录最友好形态。

## 三、连带修正（提交前门禁全绿的连带账）

- linkage 三轴接入主干（androidstd→android 门控 / gmsstd↔fdroidstd 印证 / fdroidstd→android 供给）：孤岛 3→0、悬空 0，统一清单 81 项、轴 143 条全覆盖。
- 四处 taxonomy 实测面同步：`cli_subcommands` 107→110、`gui_windows` 91→94（apilab / baigong / datong / zhuangzi）。
- ergonomics 入口地图：三命令归入「概念与知识」场景（12 场景不变）。
- concepts tagline：apilab 「107 CLI」→「110 CLI」。
- 任务分类并入 CATEGORY_ORDER：gmsstd/fdroidstd 的 compat/security 统一归 privacy（与 androidstd 一致）。
- 版本三处同步：pyproject / `sysweeper.__version__` / `src/go/main.go` = 0.6.67。
- 测试：新增 `tests/test_gmsstd.py`（13 断言组）+ `tests/test_fdroidstd.py`（13 断言组）；修正 `test_androidstd.py` 两处旧断言（Action 字段名 kind/command、报告 title 断言）。全量 **1329 passed / 3 skipped / 0 failed**（基线 1290）；`tools/audit_concepts.py --strict` 零不一致；九个 research build 脚本 `--check` 全过；omni real_gaps = 0。

## 四、诚实边界（needs_verify 挂牌）

1. STS 官方单页在本仓检索环境未实检到（source.android.google.cn 镜像 404、.com 域不可达）——其运行细节、与 GMS 认证的量化关系均为社区整理，逐条标注，以 Google 官方文档为准。
2. f-droid.org 域名直连不可达，F-Droid 官方文档内容取搜索快照（官方中文 Inclusion_Policy / 韩文 Anti-Features 页摘要），仓库层数据以 GitHub/GitLab API 实检为准。
3. GB/T 43696-2024 初判为权限标准，实检确认实为《零信任参考体系架构》，已从国内库剔除（不落错）。
4. Play App Signing 的 2048/4096 RSA 事实来自 support.google.com 帮助页（百度索引快照）+ developer.android.google.cn《为应用签名》页双源互证。

## 五、遗留

- PAT（github_pat_ 开头）已在历史命令中出现过，需在 GitHub 设置里吊销并轮换（已告知用户）；后续推送走 Git Data API，token 只从 origin URL 内存提取、不回显。
- build-android.yml 已修复，待下个 push/tag 触发 CI 观察转绿。
- 网络恢复后可选 `git fetch origin` 同步远端（当前 HEAD 与 origin/main 一致）。
