# 68 导入分析学习应用：aurora-silicon/mesa（v0.6.87）

> **来源**：用户指令「看看有什么推进的继续；导入分析学习应用 https://github.com/aurora-silicon/mesa 、 继续」。
> **落点**：本仓库**只作只读 WebFetch 分析**（2026-10-24 抓取核实），不克隆、不安装、不构建、不下载、不复制其代码进本仓；本仓无图形栈 / GPU 驱动 counterpart，按 #591 先例（docs/59）**一律只沉淀为学习笔记，不新增概念**。
> **纪律红线**：只登记可核实事实；无法核实的标 `needs_verify`，不臆造；本 mirror 自述为 freedesktop 上游的 **stock mirror（非原创、非权威源）**，其底层 GPU 驱动代码（C / 内核态交互）**本仓不可复用、不构建、不宣称任何图形能力**。

## 一、资源概览与可复用点（2026-10-24 只读 WebFetch 核实）

| 资源 | 性质 | 许可证 | 规模 / 技术要点 | 可复用工程纪律（仅学习，不落地代码） |
|---|---|---|---|---|
| aurora-silicon / mesa | freedesktop Mesa 3D 图形库的 **stock mirror** + Apple Silicon 移植工作分支 | 页面未呈现（上游 Mesa 为 MIT；本 mirror 许可 `needs_verify`） | 描述原文「Mesa 3D graphics library (stock mirror of https://gitlab.freedesktop.org/mesa/mesa)」；默认分支 `aurora-wip`；**231,027 commits**；star / fork 页面未呈现（`needs_verify`，此前组织页抓取见 2★/4 forks 与 2★/10 forks 两个不一致值）；技术栈 **C + Meson + Ninja + Vulkan + 多 GPU 后端**（radv/AMD、Intel、hk/Apple AGX、amd/virtio、ethosu/ARM、gfxstream）；README.rst 构建原文 `meson setup build && ninja -C build/ && sudo ninja -C build/ install` | ① **上游归因署名链**：镜像提交带 `Part-of: <gitlab.freedesktop.org/mesa/mesa/-/merge_requests/XXXX>` 上游 MR 归因标签；② **权威源声明**：README 明言「This repository lives at https://gitlab.freedesktop.org/mesa/mesa. Other repositories are likely forks, and code found there is not supported.」；③ **stock mirror + wip 分支工作流**：不自立门户宣称原创，以上游为准跟踪衍生；④ **LLM 辅助署名透明**：提交带 `Assisted-by: LLM` 与 `Co-Authored-By: Claude Opus 5.5`；⑤ **可复现构建即文档**：Meson/Ninja 三段标准命令 + docs/install.rst / meson.rst 上游文档索引 |
| aurora-silicon（组织页，背景信息） | Apple Silicon Linux 移植组织 | —（组织主页，非代码仓） | 自述「**New light for Apple Silicon**」——为 Apple Silicon 交付完整 Linux 体验（内核 / 图形驱动 / 工具），并正将 Windows 移植到 Apple Silicon；43 个公开仓库（linux 47★、aurora-installer、aura EL2 monitor、nixos-aurora、m1n1 364 forks、speakerguardd、fedora-aurora、asahi-audio、aura-silicon.github.io、alsa-ucm-conf-asahi 等，计数以页面当时呈现为准 `needs_verify`） | ① **平台使能分层**：bootloader（m1n1）→ 内核 → 驱动 → 发行版集成（nixos-aurora / fedora-aurora）分层交付；② **AI 代理指令入库**：mirror 仓内含 AGENTS.md / CLAUDE.md / GEMINI.md 等 AI 代理协作配置文件（2026-10-20 `gfya` 提交更新） |

## 二、边界分级与诚实边界

本仓库按「是否可实做落地」分档，本仓守界如右：

- **纯技术可学习类（仅笔记，不新增概念）**：`aurora-silicon/mesa` 及组织页。本仓（windows-internals-toolkit/system-optimizer）**无图形栈 / GPU 驱动 counterpart**——native 层只读探针面向 Windows / Linux / macOS / BSD / Unix / 移动端的系统优化，不涉及用户态图形驱动、GPU 固件交互或 Vulkan 后端实现，故按 docs/59（#591）纪律**只沉淀为学习笔记**，不新增 comp / netsys / 任何概念系统概念。若未来本仓出现对应工程面，再按「真实 counterpart 存在 + `--check` 通过」纪律补概念。
- **底层系统类（只作架构学习，不落地代码）**：Mesa 的 C 语言 GPU 驱动后端（radv / Intel / hk / virtio / ethosu / gfxstream）、内核态交互、Honeykrisp G17P 芯片相关使能——属操作系统图形栈底层，**本仓不复制、不构建、不安装、不移植**，仅学习其「驱动与硬件平台解耦」的架构分层思想（与本仓 native/ 多平台只读层同构，仅理念层面）。
- **风险行为类（只作风险登记，不落地）**：mirror 的 `aurora-wip` 工作分支是 Apple Silicon 移植的 WIP 分支（提交如 `hk: gate the bounded AS-build hint to G17P and kernel capability` 属未稳定实验性改动）——本仓**不跟踪、不合并、不采纳**任何 WIP 分支代码；上游 README 明言其他仓库的代码「not supported」，引用任何事实一律以上游 gitlab 为准。

诚实边界重申：本文所有技术要点均来自 2026-10-24 的只读 WebFetch 抓取，以仓库页面当时呈现为准。`aurora-silicon/mesa` 页面**未呈现 star / fork 计数**（此前组织页抓取曾显示 2★/4 forks 与 2★/10 forks 两个不一致值，均标 `needs_verify` 不取单一值）；**LICENSE 未在页面呈现**（上游 Mesa 为 MIT 许可，但本 mirror 的 LICENSE 文件未在抓取内容中出现，标 `needs_verify`，不据上游许可推定本 mirror 许可）；GitHub fork 链字段（forked from omacom/mesa）本次抓取未呈现，仓库自述为 gitlab 上游 stock mirror，以自述为准；提交列表为页面 History / 目录最后提交快照（PR #64、三条 hk 驱动提交、一条 `gfya`），非全量历史。

## 三、分仓学习笔记

### 3.1 aurora-silicon/mesa —— 上游归因署名链 + stock mirror 纪律

- **性质**：Mesa 3D 图形库的 GitHub stock mirror（上游 https://gitlab.freedesktop.org/mesa/mesa），默认分支 `aurora-wip`，231,027 commits；仓内提交带 `Part-of: <gitlab.freedesktop.org/mesa/mesa/-/merge_requests/XXXX>` 标签，把每个衍生改动归回上游 MR——**衍生仓库不吞没上游贡献**。
- **README.rst 原文关键段**（2026-10-24 抓取）：
  - 权威源声明：「This repository lives at https://gitlab.freedesktop.org/mesa/mesa. Other repositories are likely forks, and code found there is not supported.」
  - 构建（Meson 推荐路径）：`meson setup build` / `ninja -C build/` / `sudo ninja -C build/ install`；详细文档指向 docs/install.rst 与 docs/meson.rst。
  - 贡献流程：「Mesa uses gitlab for patches submission, review and discussions.」——补丁、评审、讨论统一回上游 GitLab，GitHub mirror 不收 PR。
- **工程纪律可复用**：
  - ① **上游归因署名链**：`Part-of:` 标签 + 提交署名（Ryan Murray <ryan@aurorasilicon.org>）双层归因——对应本仓 research/ 镜像纪律、docs/67（sony-a7iv 研究）「显式列出全部上游项目」的同构做法；本仓 HANDOFF 落账同样要求来源可溯。
  - ② **权威源声明**：README 首段即声明上游地址并声明其他仓库「not supported」——**先声明权威源再谈衍生**，对应本仓 docs/59「先划边界再讲能力」与 needs_verify 挂牌纪律（无法以上游核验的一律挂牌）。
  - ③ **stock mirror + wip 分支工作流**：以 mirror 跟踪上游、以 `aurora-wip` 承载自有衍生分支，分支名自含「wip」性质——衍生与实验分层命名，不自立门户宣称原创。
  - ④ **LLM 辅助署名透明**：提交带 `Assisted-by: LLM`、`Co-Authored-By: Claude Opus 5.5`——AI 辅助产出在版本历史中署名可见，对应本仓「AI 辅助开发如实落账」的 HANDOFF 纪律。
  - ⑤ **可复现构建即文档**：README 三段标准命令 + 上游 install/meson 文档索引——构建路径单一且文档化，对应本仓 tools/ 构建脚本 `--check` 防漂移、双 HTML 经生成器重生不手改的纪律。
- **边界**：本 mirror 非权威源、许可未呈现、WIP 分支为实验性改动；本仓**不跟踪其分支、不合并代码、不据上游 MIT 许可推定本 mirror 许可**，仅学习上述纪律。

### 3.2 aurora-silicon（组织页）—— Apple Silicon 平台使能分层

- **组织自述**：「New light for Apple Silicon」——为 Apple Silicon 交付完整 Linux 体验（内核 / 图形驱动 / 工具），并正在把 Windows 移植到 Apple Silicon；公开仓库 43 个，覆盖 bootloader（m1n1）、内核（linux）、驱动与音频（asahi-audio、alsa-ucm-conf-asahi、speakerguardd）、安装器（aurora-installer）、monitor（aura EL2 monitor）、发行版集成（nixos-aurora、fedora-aurora）、站点（aura-silicon.github.io）。star / fork 计数以页面当时呈现为准（`needs_verify`）。
- **mesa 仓内提交样本**（2026-10-24 页面快照）：PR #64（2026-10-24，RyanTheTide，`hk: three CTS fixes` 系列之 exact index range）；`hk: make G17P sparse image capabilities match the slice layout`（2026-10-23）；`hk: gate the bounded AS-build hint to G17P and kernel capability`（2026-10-22）；`gfya`（2026-10-20，`Co-Authored-By: Claude Opus 5.5`，触及 .github / AGENTS.md / CLAUDE.md / GEMINI.md）。`hk` = Apple AGX/Honeykrisp GPU 驱动后端（G17P 芯片）。
- **工程纪律可复用**：
  - ① **平台使能分层**：bootloader → 内核 → 驱动 → 发行版集成分层交付，每层独立仓库、独立演进——对应本仓子系统分层（native 只读层 / tasks 任务层 / data 知识层 / CLI-GUI-webapi-deno 四入口）的同构思想。
  - ② **AI 代理指令入库**：AGENTS.md / CLAUDE.md / GEMINI.md 等 AI 代理协作配置随仓库版本化管理——人机协作约定可见、可评审、可演进。
- **边界**：组织仓库多为底层平台使能（内核 / 驱动 / bootloader），本仓无任何 counterpart；仅作分层架构与协作纪律学习，**不克隆、不构建、不作任何 Apple Silicon 相关能力宣称**。

## 四、拓扑与验证

- **未新增概念**：本仓无图形栈 counterpart，守 docs/59（#591）纪律，九概念系统（comp / plang / daoxue / apilab / netsys / quantum / baigong / zhuangzi / datong）拓扑与桥接不变（`build --check` 不受影响）。
- 本文档为纯文档落点；版本号按 monorepo 里程表纪律升一版（`0000.0000.0000.0011.20261024` → `0000.0000.0000.0012.20261024`，仅升 D 段、日期后缀不变），README 加 #602 块、HANDOFF 落账 §24。
- 全量 pytest 零回归（基线 1683 passed / 5 skipped）；双 HTML 仅因版本串重生、`--check` 同步，数据语义不变。

## 五、落点清单与下一步

- 已落账：本文档（docs/68）+ README 学习块（#602）+ 版本 0012 十四处落点 + HANDOFF §24（第十六轮）。
- 守界：不新增概念、不进 `repo_tools` 可装清单、不复制代码、不跟踪 WIP 分支、不据上游许可推定本 mirror 许可；star/fork 不一、LICENSE 未呈现、fork 链未呈现均按 `needs_verify` 登记。
- 下一步（opt-in，不主动执行）：若本仓后续真做图形 / GPU 只读观测面（如 GPU 传感器只读探针），再按「真实 counterpart 存在 + `--check` 通过」纪律把 §三 的学习点升级为工程契约或概念桥接；Mesa 上游 GitLab MR 归因（`Part-of:` 标签）与 LLM 署名链纪律，已在本仓 HANDOFF 来源可溯要求中同构落地，无需另立工具。

> ③ 版本号已按纪律升一版（`0000.0000.0000.0011.20261024` → `0000.0000.0000.0012.20261024`，五处源文件 + 三 taxonomy + 双 HTML 同步），本学习笔记仅增加 docs/68 文档与落账，不改 HTML / 数据语义、零回归（见 README #602 / HANDOFF §24）。
