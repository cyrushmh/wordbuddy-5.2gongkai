# 76 导入分析学习应用：今日头条 batch-5 十三篇（IPv6 全链路 / 星闪3.0 / Jev 智能体 / novel-plus / 网络共享 / Graphify / shuohao-skills / MOSS-Image / ICMPv6 / Docker Compose / switch2 / Filee / Huashu-Report）

> **来源**：用户指令「导入分析学习应用」batch-5（2026-10-25），今日头条技术文章 13 篇，已全部只读核实（12 篇 WebFetch 抓取正文 + 星闪3.0 一文经 WebSearch 补抓权威报道）。
> **落点**：全部资源**只作只读分析**，不克隆、不安装、不构建、不下载、不复制其代码进本仓。
> **纪律红线**：只登记可核实事实；无法核实或报道单方陈述的标 `needs_verify`，不臆造；本仓守「无真实 counterpart 不加概念」纪律（#591 先例 docs/59、docs/70、docs/71）——IPv6/ICMPv6/星闪三篇有真实 counterpart（protec 产品保护概念系统 + netsys 组网系统），本轮**同步建模回填**；其余十篇无 counterpart，**只沉淀为学习笔记**。

## 一、资源概览表（2026-10-25 只读核实）

| # | 文章 | 性质 | 技术要点（页面/报道口径） | 边界分级 |
|---|---|---|---|---|
| 1 | IPv6：部署链｜运维链｜安全链｜卡脖子｜赛道｜难度点 | 网络协议工程实践综述 | 部署链七环、运维链、FMEA 18 行失效分析、卡脖子五类、赛道六类、难度点；指出 SEND（安全邻居发现，RFC 3971/3972 CGA）生态失效、风险优先数 RPN 392 | **可回填**：protec 新增轴8「ipv6」域（10 概念）+ 10 条 netsys 桥接 |
| 2 | 星闪 3.0 协议标准 | 近距离无线通信标准发布报道 | CEIC2026 峰会（2026-10-22~24，深圳）发布星闪 3.0 标准成果 + **15 项推荐性国家标准**（编号 `needs_verify`）；3.0 面向全场景智能物联，新增 SLZ 无源零功耗（第四空口模式，对标 RFID）、毫米波、PQC、量子安全；空口模式 SLB（同步宽带）/SLE（同步窄带）/SLP（同步高精定位）；《星闪 SLE 3.0 技术标准演进蓝皮书》60 余家单位参编；已发布无损音频等三项标准 | **可回填**：protec access 域补 `sparklink`（星闪）概念；国标编号 `needs_verify` |
| 3 | Jev 在智能体中的 10 大应用 | 智能体运行时框架介绍 | TypeSafe System One；Choice / Score / Noul 三原语；70–500ms 级响应；置信度门控 | 纯技术可学习（本仓无智能体运行时 counterpart） |
| 4 | novel-plus v6.2.0 | 开源小说 CMS 版本发布 | RBAC 权限、上下架流程、增量 SQL、密码重置流程安全警示 | 纯技术可学习（无 counterpart） |
| 5 | 网络共享手册 | SMB 共享运维科普 | SMB 四链路；`0x80070035`（找不到网络路径）/`0x0000011b`（SMB1 被禁后回退失败）等排障；SMB1 协议风险（永恒之蓝面） | 纯技术可学习（netsys 无 SMB/NFS counterpart，按 #591 不加概念） |
| 6 | Graphify 实测 | 图结构 RAG 工具实测 | 95 节点 229 边「0 token」建图；中文问句 0 结果；单次 2581 token 超预算反例；社区聚类弱 | 纯技术可学习（无 counterpart）；「token 预算」纪律可学 |
| 7 | shuohao-skills | 短视频创作技能管线 | 五段管线；52 道质量门；分镜只做输出格式 | 纯技术可学习（无 counterpart） |
| 8 | 国产 5B 生图模型（MOSS-Image） | 国产图像生成模型发布 | 5B 参数 DiT；4 天 130 万下载；LLTB 96.3%；JSON Layout 结构化生成；国产 PPU 训练 | 纯技术可学习（无 counterpart） |
| 9 | ICMPv6 | 协议科普 | 差错报文 / 信息报文两类；PMTUD 机制（RFC 8201）；Echo Request/Reply 128/129；NDP 133–136（RS/RA/NS/NA）；MLD（RFC 2710/3810） | **可回填**：并入 protec ipv6 域（`icmpv6` 概念） |
| 10 | Docker Compose 部署 WeKnora | RAG 框架容器化部署实践 | 六步部署；三个「想当然」误区；失败三档分类；诚实边界 | 纯技术可学习（container 子系统为构建/打包 counterpart，非 RAG 部署）；「诚实边界」纪律可学 |
| 11 | switch2 ounce-core | 任天堂 Switch 2 自研核心 | Rust 清洁室实现；Tegra T239 芯片；早期验证阶段 | 纯技术可学习（无 counterpart，仅编目参考） |
| 12 | Filee 200+ 格式转换 | 文件格式转换工具 | 200+ 格式；Ctrl 拖拽圆环交互；离线免费 | 纯技术可学习（无 counterpart） |
| 13 | Huashu-Report | 报告生成工具工程实践 | 数据表 `.json` 数字锁源 + 编译反查；规则函数化三层；渲染自检 | 纯技术可学习（无 counterpart）；「数字锁源 + 反查」纪律与本仓构建期实测（`live_user_face`）同构，可学 |

## 二、边界分级与诚实边界

本仓库按「是否可实做落地」分档：

- **可回填概念系统档（本轮同步建模）**：
  - **IPv6 / ICMPv6**：本仓 netsys 已有 IPv6 相邻 counterpart——`network`（IPv6 RFC 8200）、`osi`（控制面）、`netauth`（SEND/CGA 安全邻居发现）、`dhcp`（DHCPv6 RFC 8415）、`nat`（NAT64 RFC 6146/6147 + DNS64 RFC 6052）、`edge`（6LoWPAN RFC 4944/6282/6775）——按 protec 既有「轴」组织范式新增**轴8「ipv6：IPv6 与 ICMPv6 控制面」**（10 概念），并建 10 条 netsys 桥接；netsys 侧只加桥接目标引用，不改其模块。
  - **星闪 3.0**：protec access（接入与链路）域补 `sparklink` 概念（SLB/SLE/SLP/SLZ 四空口模式、PQC/量子安全、毫米波）；15 项推荐性国家标准的**精确编号未在报道中列出，`needs_verify`**。
- **纯技术可学习档（仅笔记，不新增概念）**：Jev（智能体运行时）、novel-plus（小说 CMS）、网络共享（SMB，netsys 无 counterpart）、Graphify（图 RAG）、shuohao-skills（创作管线）、MOSS-Image（图像生成）、switch2 ounce-core（主机核心）、Filee（格式转换）、Huashu-Report（报告生成）、Docker Compose WeKnora（RAG 部署）。本仓对上述能力均无 counterpart，按 docs/71 先例**一律只沉淀为学习笔记**。
- **第三方口径档（needs_verify 挂牌）**：IPv6 综述的「FMEA 18 行 / RPN 392 / 卡脖子五类 / 赛道六类」细目、星闪 15 项国标编号、Jev 的 70–500ms 与十大应用清单、novel-plus 版本特性清单、SMB 错误码精确含义、Graphify 的 95 节点 229 边与 2581 token 数字、MOSS-Image 的 130 万下载与 LLTB 96.3%、switch2 的芯片型号与验证阶段、Huashu-Report 的规则分层细节——均为文章单方陈述，未独立复核。

诚实边界重申：本文技术要点均来自 2026-10-25 只读抓取的页面/报道，以当时呈现为准；文章标题与用户所给链接短码存在错位（如「星闪3.0」标题后所跟短码实为 Jev 文），本文按**实际抓取内容**归类，不依赖用户配对。IPv6/ICMPv6 两篇的标准编号（RFC 8200/4443/4861/4862/8981/8415/8201/6146/6147/6052/4944/6282/6775/3971/3972/2710/3810）已另行核实。

## 三、分主题学习笔记

### 3.1 IPv6 全链路（部署链 / 运维链 / 安全链 / 卡脖子 / 赛道 / 难度点）

- **问题定位**：IPv6 不是「打开开关」就完事——文章按工程生命周期拆成**部署链七环**（地址规划 → 前缀委派 → 路由宣告 → DNS → 过渡隧道 → 安全 → 验收），配**运维链**（监控/计费/排障）与**安全链**（RA  Guard、SEND、 ACL、日志），并用 **FMEA 18 行**逐失效模式列严重度/发生率/可检测度。
- **卡脖子五类**（文章口径，细目 `needs_verify`）：地址规划失当、过渡机制（NAT64/DNS64）联动断裂、安全链缺位、运维可见性不足、生态（家用路由器/老旧固件）不支持。
- **难度点**：SEND（RFC 3971/3972，基于 CGA 地址的邻居发现安全）文章判定为「生态失效、风险优先数 RPN 392」——即协议设计完备但**现实部署近乎为零**，风险仍由 RA-Guard（RFC 7113 实施建议）+ 首跳安全兜底。
- **本仓落点**：protec 新增轴8「ipv6」域 10 概念（见下），netsys 既有模块做桥接目标（network/osi/netauth/dhcp/nat/edge），SEND 与 RA-Guard 的「设计完备 vs 生态失效」张力如实沉淀为 needs_verify 项。

### 3.2 ICMPv6（IPv6 控制面消息）

- **两类消息**：差错报文（目的不可达、包过大、超时、参数问题）与信息报文（Echo Request 128 / Echo Reply 129；组播侦听发现 MLD；邻居发现 NDP 133–136）。
- **与 IPv4 ICMP 的关键差异**：ICMPv6 在 IPv6 协议族中位置等同于 ICMPv4 但**承担更多控制面职能**——NDP（RS 133 / RA 134 / NS 135 / NA 136）取代了 IPv4 的 ARP，PMTUD 依赖 ICMPv6 Packet Too Big，MLDv2 取代 IGMP。
- **安全含义**：控制面消息即攻击面（RA 欺骗、伪造 NA、PMTUD 黑洞攻击）↔ 本仓安全链概念同域。
- **本仓落点**：`icmpv6` 概念并入 ipv6 域，桥接 netsys `osi`（协议分层）与 `network`。

### 3.3 星闪 3.0（SparkLink / NearLink 3.0）

- **发布事实**：CEIC2026 峰会（2026-10-22~24，深圳）发布星闪 3.0 标准成果 + 15 项推荐性国家标准（编号 `needs_verify`）；《星闪 SLE 3.0 技术标准演进蓝皮书》60 余家单位参编；此前已发布无损音频等三项标准。
- **技术演进**：星闪（SparkLink）面向全场景智能物联；3.0 新增 **SLZ 无源零功耗**空口模式（第四模式，对标 RFID 类无源场景）+ 毫米波 + PQC 后量子密码 + 量子安全；既有三模式 SLB（同步宽带，高吞吐）/ SLE（同步窄带，低功耗广连接）/ SLP（同步高精定位）。
- **工程纪律可学点**：① **一套协议多空口模式分层覆盖**（宽带/窄带/定位/无源）↔ 本仓协议标准库「按场景分层选型」同构；② **PQC/量子安全前置进标准** ↔ 本仓 quantum 概念系统「量子安全」条目呼应；③ 标准演进以蓝皮书形式固化（参编单位公开）。
- **本仓落点**：protec access 域补 `sparklink` 概念；本仓无星闪 counterpart，仅概念编目 + needs_verify 挂牌（国标编号）。

### 3.4 Jev 在智能体中的 10 大应用

- **定位**：TypeSafe System One——Choice / Score / Noul 三原语构成的智能体运行时；宣称 70–500ms 级决策响应；十大应用场景（细目 `needs_verify`）。
- **可学纪律**：① **置信度门控**——智能体输出须过置信阈值才执行 ↔ 本仓 needs_verify/红线纪律（不确证不落地）同构；② 类型安全（TypeSafe）优先 ↔ 本仓跨语言 parity 校验纪律同构。
- 本仓无智能体运行时 counterpart，仅笔记。

### 3.5 novel-plus v6.2.0

- **定位**：开源小说 CMS；v6.2.0 宣称含 RBAC 权限体系、作品上下架流程、增量 SQL、密码重置流程安全加固（警示重置链路为常见攻击面）。
- **可学纪律**：① **重置/认证链路是攻击面**须显式加固 ↔ 本仓 netauth 隐私验证「不存原始 PII」同构；② **增量变更（incremental SQL）而非全量** ↔ 本仓快照 diff 子系统同构。
- 无 counterpart，仅笔记。

### 3.6 网络共享手册（SMB）

- **要点**：SMB 共享四链路（发现 → 协商 → 认证 → 传输）；错误码排障 `0x80070035`（找不到网络路径，多为发现/防火墙档）、`0x0000011b`（SMB1 被禁后客户端回退失败）；SMB1 风险（永恒之蓝 EternalBlue 攻击面，应禁 SMB1、强制 SMB 签名）。
- **可学纪律**：① **协议版本降级即安全退步**（SMB1 回退）↔ 本仓「最小兼容面」须设下限纪律；② 错误码即运维语言 ↔ 本仓只读报告结构化输出同构。
- netsys 无 SMB/NFS counterpart，按 #591 不加概念，仅笔记。

### 3.7 Graphify 实测（图 RAG）

- **实测要点**：95 节点 229 边「0 token」建图（建图阶段不耗 token）；**中文问句检索 0 结果**（中文支持缺陷）；单次查询 2581 token 超预算反例；社区聚类效果弱。
- **可学纪律**：① **建图/查询分账计 token**的思路 ↔ 本仓「只读编目 vs 查询」分层同构；② **中文场景失效**是只读抓取的现实边界（本仓资料库中文为主，须防「英文优先」工具偏见）；③ 超预算是典型失败模式，工具化须设**预算上限硬闸** ↔ 本仓有界日志/阈值注册表同构。
- 无 counterpart，仅笔记。

### 3.8 shuohao-skills（短视频创作管线）

- **要点**：五段管线（选题 → 脚本 → 分镜 → 生成 → 质检）；52 道质量门；分镜阶段只做输出格式规范化。
- **可学纪律**：① **管线分段 + 段内质量门** ↔ 本仓「分层 + `--check` 幂等重放」门禁同构；② 职责单一（分镜只管格式）↔ 本仓子系统「单一职责」拆分纪律（如 tasks/jvm.py 拆 jdk.py+kmod.py 先例）。
- 无 counterpart，仅笔记。

### 3.9 国产 5B 生图模型（MOSS-Image）

- **要点**：5B 参数 DiT（Diffusion Transformer）；发布 4 天下载 130 万；LLTB（榜单口径 `needs_verify`）96.3%；JSON Layout 结构化布局生成；**国产 PPU 训练**（国产并行处理单元）。
- **可学纪律**：① **结构化中间表示（JSON Layout）驱动生成** ↔ 本仓「数据层 JSON 驱动渲染」同构；② **国产算力底座可用性**信号 ↔ 本仓 qarch/量子架构 + 国产架构（龙芯/RISC-V）编目同域。
- 无 counterpart，仅笔记。

### 3.10 switch2 ounce-core（任天堂 Switch 2 自研核心）

- **要点**：Rust 清洁室实现；面向 Tegra T239 芯片；早期验证阶段（成熟度 `needs_verify`）。
- **可学纪律**：① **Rust 清洁室**（rewrite-from-spec，规避 GPL 污染）↔ 本仓 licenses/ 引用纪律同构；② 早期验证须显式标注成熟度 ↔ 本仓 needs_verify 挂牌纪律同构。
- 无 counterpart，仅笔记。

### 3.11 Filee（200+ 格式转换）

- **要点**：200+ 格式互转；Ctrl 拖拽圆环交互；离线免费。
- **可学纪律**：① **离线优先**（数据不出本机）↔ 本仓 androidstd 隐私本地优先同构；② 格式矩阵按「源 × 目标」全量编目 ↔ 本仓 toolchain_catalog.json 编目范式同构。
- 无 counterpart，仅笔记。

### 3.12 Huashu-Report（报告生成工程实践）

- **要点**：数据表 `.json` 数字锁源（报告数字只能来自锁源数据表）+ 编译反查（从成品反查数字出处）；规则函数化三层；渲染自检。
- **可学纪律**：① **数字锁源 + 编译反查** ↔ 本仓构建期实测（`live_user_face()` 实测 CLI/GUI/webapi/deno 版本防漂移）**高度同构**——都是「成品数字必须可反查到实测源」，是本仓最可直接内化的一条；② 规则函数化三层（规则 → 函数 → 渲染）↔ 本仓 data → native → tasks → cli/gui 分层同构；③ 渲染自检 ↔ 本仓 `--check` 门禁同构。
- 无 counterpart，仅笔记（但其纪律已在本仓既有机制中存在，无需新增）。

### 3.13 Docker Compose 部署 WeKnora（RAG 框架容器化实践）

- **要点**：六步部署 compose 栈；三个「想当然」误区（镜像拉取/端口冲突/卷权限）；失败三档分类（启动失败 / 运行期失败 / 静默降级）；诚实边界（哪些没验证）。
- **可学纪律**：① **失败分档**（启动/运行期/静默降级）↔ 本仓 emergency/预警子系统「失效分级」同构；② **诚实边界自陈**（明示未验证项）↔ 本仓 needs_verify 纪律同构；③ compose 六步 ↔ 本仓 Dockerfile/compose 已有（Task #450），本仓 counterpart 是**构建/打包**而非 RAG 部署，不新增概念。
- 无 counterpart，仅笔记。

## 四、落实动作（本轮）

- **protec 概念系统**（本轮同步建模，回填第 1/2/9 篇）：
  - 新增**轴8「ipv6：IPv6 与 ICMPv6 控制面」** 10 概念：`ipv6-base`（IPv6 基址与报头 RFC 8200）、`icmpv6`（ICMPv6 两类消息 RFC 4443）、`ndp`（邻居发现 RFC 4861）、`slaac`（无状态自动配置 RFC 4862）、`dhcpv6`（有状态配置 RFC 8415）、`pmtud`（路径 MTU 发现 RFC 8201）、`nat64-dns64`（NAT64/DNS64 RFC 6146/6147/6052）、`6lowpan`（物联网 6LoWPAN RFC 4944/6282/6775）、`send-cga`（SEND 与 CGA RFC 3971/3972）、`mld`（组播侦听 RFC 2710/3810）；各概念建 netsys 桥接（network/osi/netauth/dhcp/nat/edge）。
  - access 域补 `sparklink`（星闪 SLB/SLE/SLP/SLZ + PQC/量子安全）；15 项国标编号 `needs_verify`。
  - needs_verify 增补：星闪国标编号、SEND 生态失效现状（RPN 392 报道口径）。
- **daoxue 概念系统**（Task #670，另篇 docs/50 承接）：新增「zhen 阵」域 4 条目（周天星斗 / 十二都天神煞 / 分合 / 河图洛书），桥接 protec consistent-hash/redundancy 与 netsys net-arch/distcompute/meshnet。
- **其余十篇**（Jev / novel-plus / 网络共享 / Graphify / shuohao-skills / MOSS-Image / switch2 / Filee / Huashu-Report / Docker Compose）：仅本文笔记，不新增概念、不引入依赖。
- 本文标准编号（RFC 8200/4443/4861/4862/8981/8415/8201/6146/6147/6052/4944/6282/6775/3971/3972/2710/3810/7113）已另行核实；星闪 15 项国标编号 `needs_verify`。
