# 67 导入分析学习应用：cleanyourtv / Gathin23 / tv-detox / sony-a7iv-feature-research（v0.6.86）

> **来源**：用户指令「继续被中断；导入分析学习应用 github.com/Gathin23/cleanyourtv、github.com/Gathin23、github.com/Ansub/tv-detox、github.com/leogenot/sony-a7iv-feature-research；继续」。
> **落点**：四仓库均**只作只读 WebFetch 分析**（2026-10-24 抓取核实），不克隆、不安装、不构建、不下载、不复制其代码进本仓；本仓无对应工程落点（无 Android TV / Google TV debloat 子系统、无相机固件研究面），按 #591 先例（docs/59）**一律只沉淀为学习笔记，不新增概念**。
> **纪律红线**：只登记可核实事实；无法核实的标 `needs_verify`，不臆造；TV debloat 类工具的 ADB 明文端口 / 恢复出厂风险如实登记，本仓**不采纳**任何 ADB 设备管理流程；相机固件研究仓「仓内不含固件 / 解密二进制 / 密钥 / 备份」的干净分发纪律值得学习，本仓**不复现**任何固件改动、不作任何厂商相关能力宣称。

## 一、资源概览与可复用点（2026-10-24 只读 WebFetch 核实）

| 资源 | 性质 | 许可证 | 规模 / 技术要点 | 可复用工程纪律（仅学习，不落地代码） |
|---|---|---|---|---|
| Gathin23 / cleanyourtv | Android / Google TV 无线 debloat + Apple TV 风格启动器 | MIT（launcher 字体 Outfit 为 SIL OFL） | 29.6k★ / 3.4k fork / 380+ 贡献者 / 840+ merged PR（2026-10-17 上线以来）；260 TV 型号 · 77 品牌 · 25 语言 · 497 KB launcher；Wi-Fi ADB `pm disable-user` 不 root 不卸载一行还原；纯 Java launcher 面向 1GB RAM、无网络权限无后台服务；Python 工具链（tv.py 纯 Python ADB 客户端 / b64push.py / relay.py / check.py / privacy.py 等）+ .sh/.ps1 双生脚本 | ① **可逆优先**：先写恢复记录再改动，一行还原，且不依赖本工具（电视自身设置也能重启用）；② **最小权限**：不 root、不卸载、只 disable-user，launcher 零网络权限；③ **顺序纪律**：新 Home 装好运行后才禁用原厂 Home；④ **安全诚实**：明示 ADB 5555 明文风险 + `adb-closed.py` 验证端口关闭 + 建议 Tailscale 私网而非路由器开端口；⑤ **风险分级披露**：setupwraith crash-loop / Private DNS 权衡 / 固件更新覆盖清理成果 |
| Gathin23（用户主页） | CleanYourTV 作者主页（背景信息） | —（GitHub 个人主页，非代码仓） | Gathin，Sr. DevRel Lead @0gfoundation（onchain AI），India；2026-10 单月 6 仓 1,195 commits（cleanyourtv 1,039）；置顶 cleanyourtv（Java 29.6k/3.4k）、cleanyourtv-website（TS 59/11）、NiceNode/nice-node（TS 203/30，已归档）、TalentLayer-Labs/starter-kit（TS 8/20） | ① **真实需求驱动**：父母电视开屏广告 → 给 Claude Code 电视型号 → 一周 29.6k★；② **文档与社区一等交付**：press 页（187 篇 31 国报道）、25 语言、社区实测 260 型号 |
| Ansub / tv-detox | AI 驱动（Claude Code / Codex）的 Android TV debloat + 极简主屏 | MIT | 126 commits；star / fork 页面未呈现（`needs_verify`）；纯 Java 单屏 launcher（无第三方库、无 Gradle，javac + d8 构建，Java 17 + Android SDK 34）；README 称约 30 MB RAM（初始提交曾称约 12 MB，两说并存如实登记）；Shell 脚本族 install / undo / check / candidates / build + GitHub Actions + ShellCheck + 模拟器 smoke test | ① **先分类后动作**：`candidates.sh` 只读分 never / keep / safe / review 四档，「不确定就保留」；② **保守默认演进**：v1.4.1 起默认保留 Google TV 主屏幕（`GOOGLE_TV=1` 才 opt-in）——从 crash-loop 报告学到的 fail-safe 默认并版本化记录；③ **撤销完整性审计**：诚实声明 undo.sh 不撤销 TCL 远程服务改动；④ **恢复路径文档化**：卡 logo 时 `adb wait-for-device` + `pm enable` 逐个恢复手册 |
| leogenot / sony-a7iv-feature-research | Sony A7 IV（ILCE-7M4）固件 6.02 service-mode / shutter-angle / LUT 研究 | 页面未呈现许可证（`needs_verify`） | 最近提交 2026-09-21；纯文档 + 只读脚本（appfw_elf.py / bk4.py / bkid_inventory.py / feature_manager_matrix.py）；**仓内明确不含 Sony 固件、解密二进制、相机备份、序列号、密钥**；上游依赖 ma1co/Sony-PMCA-RE、DavidBuchathan314/fwtool.py a7iv 分支、ILCE-7M4-RE；1,064 个更新包文件独立哈希匹配 | ① **证据分级**：每条结论带状态戳（Verified / display verified / gate unresolved / product-excluded / untested），不把「实现在固件中」转述为「可用」；② **备份先行**：实验前保存 checksum 有效设置备份，原备份与哈希留在仓外；③ **单属性隔离**：一次只改一个 persisted backup property + 冷启动验证，可复现；④ **上游归因**：显式列出全部上游项目 |

## 二、边界分级与诚实边界

四个仓库按「是否可实做落地」分两档，本仓守界如右：

- **纯技术可学习类（仅笔记，不新增概念）**：`cleanyourtv` / `tv-detox` / `sony-a7iv-feature-research` 及作者主页。四者均无可直接编目为「本仓自研工具」的工程落点——本仓无 Android TV / Google TV 设备管理子系统、无相机固件研究面，故按 docs/59（#591）纪律**只沉淀为学习笔记**，不新增 comp / netsys 概念。若未来本仓出现对应工程面，再按「真实 counterpart 存在 + `--check` 通过」纪律补概念。
- **风险行为类（只作风险登记，不落地）**：TV debloat 工具依赖的 ADB 5555 明文端口、`pm disable-user` 改系统状态、Google TV 关原生 launcher 的 crash-loop / 恢复出厂风险——本仓工具链不涉及 Android 设备管理，这些机制**只登记不采纳**，更不提供任何操作步骤。

诚实边界重申：本文所有技术要点均来自 2026-10-24 的只读 WebFetch 抓取，star / fork / 贡献者数、协议细节以仓库页面当时呈现为准；`tv-detox` 与 `sony-a7iv-feature-research` 页面未呈现 star / fork 计数，标 `needs_verify` 不补数；`cleanyourtv` 的 29.6k★ / 3.4k fork / 380+ 贡献者 / 840+ merged PR 为作者主页 pinned 徽章与 README 自述口径（"since the repo went up on 17 October 2026"）；`tv-detox` RAM 占用 ~12 MB（初始提交）与 ~30 MB（README）两说并存，均按原文登记；`sony-a7iv-feature-research` 全部功能状态以其 Research status 表分级为准，不转述为「已实现 / 可用」。

## 三、分仓学习笔记

### 3.1 Gathin23/cleanyourtv —— 可逆优先的无线 debloat + 极简启动器

- **起源与规模**：2026-10-17 作者把父母电视型号交给 Claude Code——电视开屏先播赞助广告才能进 Netflix；代理在 Wi-Fi 上找到电视、移除 25 个小米包、写出新 launcher；发 X 后一周内 29.6k★ / 3.4k fork / 380+ 贡献者 / 840+ merged PR；187 篇来自 31 国的报道（TechCrunch / Mashable / TechRadar / Tom's Guide / Android Authority / XDA）；社区实测 260 TV 型号 · 77 品牌；25 种语言（含希伯来语完整 RTL 镜像）。
- **核心机制**：Wi-Fi ADB `pm disable-user`（不 root、不卸载、一行还原）；三步流程 Back up → Disable → Install launcher；**顺序纪律**——新 launcher 安装并运行后才禁用原厂 Home，否则 Home 可能落到工厂测试应用；497 KB 纯 Java launcher 面向 1GB RAM 电视，无模糊、无视频、无网络权限、无后台服务；主题经 `config.json` 经 Wi-Fi 推送无需重构建；第三方应用可以模块卡片提供磁贴（需用户逐次授权）。
- **工程纪律可复用**：
  - ① **可逆优先**：`disable.sh` 先写恢复记录再修改；`restore.sh` 一行还原；即使工具不在，电视自身 Settings → Apps 也能重新启用被禁包。
  - ② **最小权限**：不 root、不卸载、只 disable-user；launcher 零网络权限、零后台服务——资源与权限双最小化。
  - ③ **工具链同构**：每个脚本 .sh / .ps1 双生；`tools/tv.py` 纯 Python ADB 客户端（绕 macOS Local Network privacy 屏蔽）、`b64push.py` base64 分块上传 + checksum、`relay.py` 仅监听本机、`check.py` 固件更新后比对重放、`privacy.py` 对语音 / ACR / 遥测候选包取证审计并生成可禁用列表。
  - ④ **安全诚实**：README 明示 network ADB 端口 5555 明文传输、`ro.adb.secure=0` 固件上局域网任意设备可得 shell；用后必须关调试并撤销授权，`adb-closed.py` 验证端口关闭；远程帮他人清理建议走 Tailscale 私网而非路由器开端口。
  - ⑤ **风险分级披露**：`com.google.android.tungsten.setupwraith` 可能接管 Home 致系统 crash-loop（Chromecast / Google TV Streamer 上还会失去投屏）；Private DNS 权衡（解析器可见电视全部 DNS 查询、不能去除与视频同源的 YouTube 广告）；固件更新会覆盖清理成果需跑 `check.py`。
- **对照本仓**：可逆优先 / 最小权限 / 工具双生 / 风险分级披露，与 docs/57 工具链纪律、needs_verify 挂牌、docs/59「先划边界再讲能力」同构；但本仓无 Android 设备管理工程面，仅作纪律学习，**不把任何 debloat 清单或 ADB 流程编入本仓工具目录**。

### 3.2 Gathin23（用户主页）—— 作者背景与项目起源

- Gathin，Senior DevRel Lead @ 0G（onchain AI），驻 India；2026 年 10 月单月在 6 个仓库产出 1,195 commits（cleanyourtv 1,039 / cleanyourtv-website 129 / maintainer-bot 17 / 0g-ui 4 / zerobot 4 / 个人 profile 2）。
- 可学点：**真实需求驱动 + AI 编码代理快速原型 + 社区化运营**三段链——从「父母电视的开屏广告」这一具体痛点出发，用 Claude Code 一周内做出 29.6k★ 项目；文档（press 页 / 25 语言 / 260 型号社区实测表）与社区运营被当作一等交付物而非附属品。对照本仓「只读登记、不臆造」的文档纪律：该项目 README 的能力陈述与风险提示分区行文，同样是「先划边界再讲能力」的范式。

### 3.3 Ansub/tv-detox —— AI 驱动 debloat + 保守默认 + 模拟器 CI

- **核心机制**：Claude Code 或 Codex 执行清理，每步改动前询问用户确认；`candidates.sh` **只读**列出全部应用的判定结果（never / keep / safe / review）；所有「卸载」实为 `pm disable-user --user 0` 关闭，从不真删；`install.sh` 在电视 `/data/local/tmp/` 保留关闭列表供 `check.sh` / `undo.sh` 使用；极简主屏 = 应用 + HDMI 输入 + 时钟，16 种语言、14 种渐变壁纸、网络状态图标；系统优化（关动画、5 分钟休眠）；README 称约 30 MB RAM。
- **工程纪律可复用**：
  - ① **先分类后动作**：never（电视需要它）/ keep（承载可能用的功能）/ safe（常见垃圾）/ review（未知需人工判断）四档 + `docs/debloat.md` 记录判定规则与陷阱（Android 无论如何都会重启的应用、承载 casting 功能的应用、包名掩盖真实用途）；「不确定就保留」。
  - ② **保守默认演进**：v1.4.1 起 `install.sh` 默认保留 Google TV 主屏幕，除非 `GOOGLE_TV=1` 选择加入——这是从 Google TV / Chromecast 用户 crash-loop 报告中学到的 fail-safe 默认，并以版本号记录演进。
  - ③ **CI 纪律**：GitHub Actions 跑构建 + ShellCheck + 模拟器 smoke test（`ci/smoke-test.sh`）——Shell 脚本也过静态分析与自动化测试。
  - ④ **撤销完整性审计**：诚实声明关闭 Google TV 手机远程服务（TCL 场景）后 `undo.sh` **不会**撤销该改动，需手动恢复——不夸大「一键还原」。
  - ⑤ **恢复路径文档化**：卡 logo / 无限重启时的恢复手册（每次启动几秒窗口内 `adb connect` / `adb wait-for-device` / `pm list packages -d` 后逐个 `pm enable`；连不上则 recovery 或恢复出厂）。
- **风险登记（只登记不采纳）**：Google TV / Chromecast 关原生主屏可能无限重启、唯一修复=恢复出厂；OLED 电视务必保留屏保防烧屏；调试期间同网其他设备可请求控制电视，用完应关；无线调试端口在电视重启后变化。

### 3.4 leogenot/sony-a7iv-feature-research —— 证据分级的固件特性研究

- **研究范围**：Sony ILCE-7M4（A7 IV）固件 6.02，经官方更新文件 + Sony USB service mode 研究；纯文档 + 只读脚本，仓内**明确不含** Sony 固件、解密二进制、相机备份、序列号、解密密钥、提取的专有文件——「官方更新自行获取，生成数据本地保留」。
- **研究状态表（证据分级原样）**：
  - Service mode：**Verified**——PMCA 把 A7 IV 从 Mass Storage 切换到 service mode 并认证。
  - Settings backup：**Verified**——实验前可保存 checksum 有效的完整本地备份。
  - 解密文件系统读取：**Verified，read-only**——Jiritsu `GET_FILE2` 接受遍历路径返回运行中相机文件；1,064 个更新包文件独立哈希匹配。
  - Shutter angle：**display verified；adjustment still gated**——`0x02cf1702`（`00` speed / `01` angle）；已有 `0x02cf1704=10` 显示 180°，但 6.02 仍把触摸 / 拨盘控制路由离开 angle setter。
  - Custom LUT：**implementation verified；runtime gate unresolved**——`0x02cf1443=01` 被接受、存活同步与冷启动，但不暴露 Flexible ISO；User1–User16 存储、CUBE 解析、选择与显示路径存在，另有一处 runtime / UI 条件未明。
  - Open Gate：**generic imager path found；recording path unproven**——共享固件有 5016×3344 3:2 扫描模式名，但无匹配编码器 profile、无 live PTP 分辨率、无验证过的 A7 IV product route。
  - Product class：**Resolved offline**——A7 IV 以 `PRODUCT_MODEL_LS`（非 LAX）运行共享应用，每个 product class 自选菜单目录。
  - Log Shooting / Flexible ISO：**Product-excluded**——生成的 model-difference 规则列 14 个 product class，不含 `LS`。
  - De-Squeeze：**display strong candidate，untested**——`0x02cf1bf2`（`00` Off / `01` 1.3x / `02` 2.0x）到达显示缩放序列且无 product 检查。
  - XAVC S-I DCI 4K：**Shared implementation，route unknown**——不被 HAITA 排除，但无 A7 IV 菜单或验证过的编码器路径，不提议实验。
- **工程纪律可复用**：
  - ① **证据分级**：每条结论带状态戳，把「实现在固件中」与「菜单可用」严格分开——同构本仓 needs_verify 纪律与 docs/65「参考层不冒充」。
  - ② **备份先行**：任何实验前保存 checksum 有效设置备份；原备份与哈希放在仓库外。
  - ③ **单属性隔离**：一次只改一个 persisted backup property 再冷启动验证，全程可复现；明确「所有改动操作 persisted backup properties，不是重打包固件更新」。
  - ④ **干净分发**：仓内零固件 / 零密钥 / 零备份 / 零序列号，把法律与安全边界做进仓库结构而非只写进 README。
  - ⑤ **上游归因**：显式列出上游项目（ma1co/Sony-PMCA-RE、DavidBuchathan314/fwtool.py `a7iv` 分支、ma1co/fwtool.py PR #52、DavidBuchathan314/ILCE-7M4-RE）并评估其可帮助解决的下层特性支持问题。
- **边界**：该研究是作者在自有设备上的只读研究，首页明示 "Use this at your own risk"；本仓**不复现**任何固件改动、不下载任何固件、不作任何索尼相机相关能力宣称，仅学习其证据分级与干净分发纪律。

## 四、拓扑与验证

- **未新增概念**：四仓均无真实 counterpart（本仓无 Android TV debloat 子系统 / 无固件研究面），守 docs/59（#591）纪律，comp 概念系统拓扑与桥接不变（`build --check` 不受影响）。
- 本文档为纯文档落点；版本号按 monorepo 里程表纪律升一版（`0000.0000.0000.0008.20261024` → `0000.0000.0000.0009.20261024`，仅升 D 段、日期后缀不变），README 加 #599 块、HANDOFF 落账 §21。
- 全量 pytest 零回归（基线 1683 passed / 5 skipped）；双 HTML 仅因版本串重生、`--check` 同步，数据语义不变。

## 五、落点清单与下一步

- 已落账：本文档（docs/67）+ README 学习块（#599）+ 版本 0009 十三处落点 + HANDOFF §21（第十三轮）。
- 守界：四仓均不新增概念、不进 `repo_tools` 可装清单、不复制代码、不提供任何 ADB / 固件操作步骤；TV debloat 的 ADB 明文端口与恢复出厂风险只登记不采纳。
- 下一步（opt-in，不主动执行）：若本仓后续真做 Android / TV 设备管理子系统或硬件只读研究面，再按「真实 counterpart 存在 + `--check` 通过」纪律把 §三 的学习点升级为工程契约或概念桥接。

> ③ 版本号已按纪律升一版（`0000.0000.0000.0008.20261024` → `0000.0000.0000.0009.20261024`，五处源文件 + 三 taxonomy + 双 HTML 同步），本学习笔记仅增加 docs/67 文档与落账，不改 HTML / 数据语义、零回归（见 README #599 / HANDOFF §21）。
