# 69 导入分析学习应用：WorkBuddy 瘦身加速（workbuddy-slim）+ OpenSpeedy

> **来源**：用户指令「继续被中断；导入分析学习应用【WorkBuddy干活变慢还费token，一招教你瘦身加速】点击链接打开👉 https://m.toutiao.com/is/iLkStvDzpxY/ …… 、openspeedy；继续」。
> **落点**：两个资源均**只作只读分析**（2026-10-24 今日头条文章全文抓取 + `github.com/game1024/OpenSpeedy` 仓库页只读 WebFetch），不克隆、不安装、不构建、不下载、不复制其代码进本仓。
> **纪律红线**：只登记可核实事实；无法核实的标 `needs_verify`，不臆造；本仓无 Skill/MCP 体检 counterpart、无 Ring-3 hook / 游戏变速 counterpart（仅 API 可用性编目），按 #591 先例（docs/59）**一律只沉淀为学习笔记，不新增概念**。

## 一、资源概览与可复用点（2026-10-24 只读抓取核实）

| 资源 | 性质 | 许可证 | 规模 / 技术要点 | 可复用工程纪律（仅学习，不落地代码） |
|---|---|---|---|---|
| 头条文章《WorkBuddy干活变慢还费token，一招教你瘦身加速》 | 第三方媒体转述的工程实践文章 | —（媒体文章，非代码） | 作者**马佳彬**（公众号「马佳彬」，经「人人都是产品经理」账号发布，2026-10-24 抓取）。核心论点：WorkBuddy 变慢费 token 的根因是 **Skill / MCP / 记忆 / Agent 规则滚雪球式膨胀**，每轮任务全量塞入上下文；**长会话（几十甚至上百轮）即使有自动压缩上下文仍爆炸**；不同模型**积分倍率差异大**（同任务 DeepSeek-V4.1-Flash 约十几积分 vs MiniMax-M3 暴涨十倍）；**缓存命中率取决于前缀稳定性与任务类型**。解决方案为开源 Skill **`workbuddy-slim`**（github.com/majiabin2020/workbuddy-slim/），**只诊断不删除** | ① **上下文预算体检四维度**：规则膨胀 / 记忆超限 / 技能与连接器堆积 / 会话卫生；② **红黄绿体检报告分级**（红=严重、黄=中等、绿=健康）+ **逐项确认后非破坏性执行**；③ **工具数上限**：官方建议启用工具**不超过 80 个**；④ **记忆蒸馏压缩**：MEMORY.md 内容过多可蒸馏压缩；⑤ **前缀稳定性即成本**：缓存命中取决于前缀稳定性——多轮会话前缀漂移直接推高 token 消耗 |
| game1024 / OpenSpeedy | 开源游戏变速器（Windows 桌面应用） | **GPL v3** | 自述「The Best Open-Source Game Speed Controller」；**Ring-3 用户态 Hook 无内核侵入**，基于 **MinHook** Hook 十个 Windows 时间 API；版本 **3.3.17**（2026-10-18 bump，初版 v3.1.0 于 2026-06-21，76 commits）；平台 Windows 10+，x86/x64 | ① **Hook 面完整性矩阵**：十个时间 API 全量覆盖（见 §3.2 表）——改一个时钟面就要枚举全部读面；② **混合工具链集成**：C/C++（speedpatch DLL）+ Rust（Tauri 后端）+ TypeScript/JavaScript（Vite 前端）单仓协同；③ **防御式失败处理**：Hook 失败**不崩目标进程**（提交 `fix: remove VC++ redist dependency and stop MH hook failures crashing…`，2026-09-24）；④ **README 风险披露纪律**：五条警示前置（仅教育研究用途 / 反作弊封号风险 / 超速物理引擎崩溃 / 无数字签名杀软误报）；⑤ **分发多渠道**：winget / Releases 手装 / Steam app 5010920，且修过 **winget 同名包匹配冲突**（`docs: 修正 winget 同名包匹配冲突 (#300)`，2026-10-21） |

## 二、边界分级与诚实边界

本仓库按「是否可实做落地」分档，本仓守界如右：

- **纯技术可学习类（仅笔记，不新增概念）**：`workbuddy-slim` 文章与 `game1024/OpenSpeedy`。本仓（windows-internals-toolkit/system-optimizer）**无 Skill/MCP 体检 counterpart**（本仓非 WorkBuddy 助手本体，不管理外部 Skill / MCP 挂载）；**无 Ring-3 hook / 游戏变速 counterpart**——全仓 grep（`minhook|Ring-?3|api[- ]?hook|detours|speedpatch|GetTickCount|QueryPerformanceCounter`）仅三处命中且均为 **API 可用性版本编目**（`tools/collect_windows_api_baseline.py:39` 的 `("kernel32","GetTickCount64","6.0")`、`docs/windows-api-version-matrix.md:61` 的 Vista(6.0) 行、`research/rfc/rfc-index.xml`），**无任何 hook / 注入 / 变速实装**。按 docs/59（#591）纪律**只沉淀为学习笔记**，不新增 comp / netsys / 任何概念系统概念。
- **底层系统类（只作架构学习，不落地代码）**：OpenSpeedy 的 MinHook Ring-3 用户态 API Hook（十个时间 API 面）、speedpatch DLL 注入机制——属用户态劫持/注入技术，**本仓不复制、不构建、不安装、不移植**；仅学习其「Hook 面完整性枚举」与「失败防御」的工程思想。
- **风险行为类（只作风险登记，不落地）**：OpenSpeedy 的**游戏变速本身**——上游 README 明言仅教育研究用途、**反作弊封号风险**、超速可致物理引擎崩溃、无数字签名可遭杀软误报；本仓**不提供、不引导、不实现任何变速能力**，仅登记其风险披露纪律。

诚实边界重申：本文所有技术要点均来自 2026-10-24 的只读抓取，以页面当时呈现为准。头条文章系**第三方媒体（人人都是产品经理）转述**，`workbuddy-slim` 仓库本体未直接抓取核验（`needs_verify`：文章所述「56 个技能 40 个踩红线」样例报告数字、「官方建议工具不超过 80 个」的官方出处、DeepSeek-V4.1-Flash 与 MiniMax-M3 的积分倍率数值，均为文章单方陈述，未独立复核）；OpenSpeedy 页面**未呈现 star / fork 计数**（`needs_verify`）；文章作者公众号归属以页面呈现为准。

## 三、分主题学习笔记

### 3.1 workbuddy-slim —— 上下文预算体检：四维度诊断 + 红黄绿报告 + 非破坏性执行

- **问题根因（文章论点，2026-10-24 抓取）**：WorkBuddy 这类助手运行时，**Skill / MCP / 记忆 / Agent 规则**会随使用滚雪球式膨胀，而**每轮任务都要把全量规则塞入上下文**——即使有自动压缩，几十甚至上百轮的长会话上下文依然爆炸，表现为**干活变慢、token 变费**。
- **成本结构三因子（文章论点）**：
  - **上下文膨胀**：规则 / 技能 / 记忆 / 连接器全量常驻每轮提示；
  - **模型积分倍率**：同任务在不同模型下消耗差异巨大（文章样例：DeepSeek-V4.1-Flash 约十几积分 vs MiniMax-M3 暴涨十倍，数值为文章单方陈述 `needs_verify`）；
  - **缓存命中率**：取决于**前缀稳定性**与任务类型——前缀稳定则命中缓存省 token，长会话中前缀反复漂移则缓存失效、成本抬升。
- **解决方案形态**：开源 Skill `workbuddy-slim`（github.com/majiabin2020/workbuddy-slim/），**定位为体检而非卸载**——「只诊断不删除」。安装提示词（文章原文）：「安装这个skill：github.com/majiabin2020/workbuddy-slim/」；触发语：「给我的WorkBuddy做个体检」。
- **诊断四维度**（文章口径）：
  1. **规则膨胀**——Agent 规则 / 系统提示类条目过量堆积；
  2. **记忆超限**——MEMORY.md 等记忆文件内容过多（文章建议**蒸馏压缩**而非全量删除）；
  3. **技能与连接器堆积**——Skill / MCP 数量失控（文章样例：56 个技能中 40 个踩红线；并引「官方建议启用工具**不超过 80 个**」）；
  4. **会话卫生**——超长会话未及时清理 / 前缀漂移导致缓存失效。
- **输出与执行纪律**：输出**红黄绿体检报告**（红=严重、黄=中等、绿=健康），**用户逐项确认后才非破坏性执行**——诊断与处置分离、处置需人工逐项授权，防止自动化误删。
- **工程纪律可复用（映射到本仓，仅纪律层面）**：
  - ① **上下文预算体检**思想 ↔ 本仓已有同构实践：sysweeper 的 `audit --strict`（防误判冗余测试）、omni gaps 归零检查、工具链 catalog 新鲜度核查——都是「先体检出报告、再按门禁处置」的模式，纪律一致，无需另立工具。
  - ② **红黄绿分级 + 逐项确认后非破坏性执行** ↔ 本仓 opt-in 写入类任务一律「选择 + 确认」才执行（network 分类、openwrt_write 等先例），处置与授权分离。
  - ③ **前缀稳定性即成本** ↔ 本仓双 HTML 经生成器重生不手改、版本串二十处同步——保持构建输入前缀稳定、`--check` 防漂移，同构的「稳定前缀减少重复成本」思想。
  - ④ **记忆蒸馏压缩** ↔ 本仓 HANDOFF 分段落账、docs 学习笔记按轮次追加而非重写——历史只增不改、单点聚焦，避免单文件无限膨胀。
- **边界**：文章为第三方转述，仓库本体未直接核验；「56 技能 40 红线」「≤80 工具」等数字与出处均标 `needs_verify`；`workbuddy-slim` 是面向 WorkBuddy 运行时（Skill/MCP/记忆管理）的工具，本仓非该运行时，**不安装、不引入、不作任何助手运行时能力宣称**。

### 3.2 game1024/OpenSpeedy —— Ring-3 用户态时钟 Hook 的完整性矩阵与防御式工程

- **性质与定位**：开源游戏变速器，自述「The Best Open-Source Game Speed Controller」；**Ring-3 用户态 Hook、无内核侵入**——不碰内核驱动，全部在用户态完成，这是其与内核级变速方案的根本分野（内核级需签名驱动、兼容性与封号风险更高）。
- **Hook 面完整性矩阵（十个 Windows 时间 API，2026-10-24 抓取）**——变更时钟即需枚举全部读取面，漏一个即变速不完整：

  | 模块 | API |
  |---|---|
  | user32.dll | `Sleep`、`SetTimer` |
  | winmm.dll | `timeGetTime` |
  | kernel32.dll | `GetTickCount`、`GetTickCount64`、`QueryPerformanceCounter`、`GetSystemTimeAsFileTime`、`GetSystemTimePreciseAsFileTime`、`SetWaitableTimer`、`SetWaitableTimerEx` |

  实现基座为 **MinHook**（开源用户态 API Hook 库）。
- **技术栈与构建**：**C/C++（speedpatch DLL）+ Rust（Tauri 后端）+ TypeScript/JavaScript（Vite 前端）**混合单仓；UI 用 **MUI + Ant Design splitter**；构建命令 `npm run tauri dev`，依赖 Node.js 18+ / CMake / VS C++ 工作负载。
- **版本与分发**：版本 **3.3.17**（2026-10-18 bump；初版 v3.1.0 于 2026-06-21，共 76 commits）；平台 Windows 10+（x86 / x64）；许可 **GPL v3**；安装三途径——winget（`--id Game1024.OpenSpeedy --exact --source winget`）/ GitHub Releases 手装 / Steam app 5010920。
- **工程纪律可复用（仅纪律层面，不落地代码）**：
  - ① **Hook 面完整性枚举**：改一个语义面（时间）就要把该语义的全部 API 读取面列成矩阵——对应本仓 `tools/collect_windows_api_baseline.py` 的 **API 可用性版本编目**纪律（本仓恰好编目了 `GetTickCount64` 于 Vista(6.0) 可用，见 `docs/windows-api-version-matrix.md`）：「语义面 ↔ 全量 API 清单 ↔ 版本下限」三件套对齐，缺一不可。
  - ② **混合工具链单仓集成**：C++ 系统面 DLL + Rust 应用后端 + TS 前端分层协作，构建入口统一 `npm run tauri dev`——对应本仓多语言并存（Python / Go / Deno / Rust / Java / .NET / PowerShell）但**每层有明确职责边界与统一入口**（CLI / GUI / webapi / deno 四入口接线）的同构思想。
  - ③ **防御式失败处理**：提交 `fix: remove VC++ redist dependency and stop MH hook failures crashing…`（2026-09-24）——**Hook 失败时不崩目标进程**，把「劫持失败」当作可恢复降级路径而非致命错误；顺带移除 VC++ 运行时分发依赖。对应本仓 native 层探针「探测失败降级为 needs_verify / 未知，不抛异常炸主流程」的防御式口径。
  - ④ **README 风险披露纪律**：五条警示前置——仅教育研究用途、反作弊封号风险、超速物理引擎崩溃、无数字签名杀软误报。**能力声明与风险声明并列**，对应本仓「先划边界再讲能力」（docs/59）与「needs_verify 挂牌不臆造」纪律。
  - ⑤ **分发与包管理一致性**：修过 `docs: 修正 winget 同名包匹配冲突 (#300)`（2026-10-21）——分发渠道的**包标识唯一性**需专门对账（`--exact` 匹配防同名包误装），对应本仓 toolchain_catalog.json 对安装命令逐条核验（winget / apt / brew 标识精确匹配）的新鲜度核查纪律（#603）。
- **边界**：本仓**无 Ring-3 hook / 注入 / 变速 counterpart**，上述仅纪律学习；OpenSpeedy 的 GPL v3 代码**不复制、不链接、不移植**进本仓（许可与用途双重边界）；页面未呈现 star / fork 计数（`needs_verify`）；「Hook 失败不崩目标进程」仅据提交标题陈述，具体实现未核验（`needs_verify`）。

## 四、拓扑与验证

- **未新增概念**：本仓无 Skill/MCP 体检 counterpart、无 hook / 变速 counterpart（仅 GetTickCount64 等 API 可用性编目），守 docs/59（#591）纪律，九概念系统（comp / plang / daoxue / apilab / netsys / quantum / baigong / zhuangzi / datong）拓扑与桥接不变（`build --check` 不受影响）。
- 本文档为纯文档落点；版本号按 monorepo 里程表纪律升一版（`0000.0000.0000.0013.20261024` → `0000.0000.0000.0014.20261024`，仅升 D 段、日期后缀不变），README 加 #604 块、HANDOFF 落账 §26。
- 全量 pytest 零回归（基线 1685 passed / 5 skipped）；双 HTML 仅因版本串重生、`--check` 同步，数据语义不变。
- 附带修复：README 版本更新区 0013 块吞并 0012 块头的遗留缺陷（0011→0012 bump 与 aurora bullet 归位，块头补 `- **0000.0000.0000.0012.20261024（2026-10-24）**`），与 HEAD~1 实证结构对齐。

## 五、落点清单与下一步

- 已落账：本文档（docs/69）+ README 学习块（#604）+ 0012 块头缺陷修复 + 当前口径五处版本引用刷新 + 版本 0014 二十处落点 + HANDOFF §26（第十八轮）。
- 守界：不新增概念、不进 `repo_tools` 可装清单、不复制 GPL v3 代码、不安装任何 Skill、不实现任何 hook / 变速能力；文章转述数字（56/40、≤80、积分倍率）与 OpenSpeedy star 计数均按 `needs_verify` 登记。
- 下一步（opt-in，不主动执行）：若本仓后续真做「上下文 / 规则预算体检」类只读功能（如对本仓自身 rules / skills 清单做红黄绿体检报告），再按「真实 counterpart 存在 + `--check` 通过」纪律把 §3.1 四维度升级为工程契约；OpenSpeedy 的「Hook 面完整性矩阵」纪律已在本仓 windows-api-version-matrix 编目中同构存在，无需另立工具。

> ③ 版本号已按纪律升一版（`0000.0000.0000.0013.20261024` → `0000.0000.0000.0014.20261024`，五处源文件 + 三 taxonomy + 双 HTML 同步），本学习笔记仅增加 docs/69 文档与落账，不改 HTML / 数据语义、零回归（见 README #604 / HANDOFF §26）。
