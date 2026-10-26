| 子命令 | 说明（最新登记） |
|---|---|
| `datong` | **「大同」人类文明一体概念系统**（v0.6.62，只读不联网）：用户立意「人类命运是一个的，古今中外的宗教哲学都融合进来」「还是要宣扬天罡元阳、地煞元阴的正道，类似科学的，把固液气、电磁波，这六样是正道」「古来唯道独成尊」——按**文明传统(15) → 核心命题(21，唯道独尊为宗) → 正道六象(6) → 实践形态(12) → 人间落法(9)** 五轴登记 **63 个概念**；用户点名的**一体两面 / 三位一体 / 神恩如狱 / 萨满巫觋 / 唯道独尊**全部落册；**正道六象**（固/液/气/电/磁/波）按「天罡元阳（气·电·波·外发）/ 地煞元阴（固·液·磁·内聚）」分属，每象带科学口径 + 跨传统通名 + 工程落法；**51 条桥接**到八个既有概念系统（comp 8 / apilab 7 / baigong 7 / daoxue 7 / netsys 7 / zhuangzi 6 / quantum 6 / plang 3），构建期逐条校验目标真实存在（无悬空）；**用户端面 + 语言面为构建期实测**（CLI 123 / GUI 108 / webapi 29 / deno 双文件 0000.0000.0000.0034.20261026；plang 161 条 / probe 实测 15 种 / comp 语言编译需要 16 条 / 概念系统 9）。**红线：只读登记，不宣扬任何宗教为真理**；跨传统同构非等同（三位一体/三身/三相只作结构同构）、元阳元阴分属为正名约定非物理学分类、引文未核对与年代/词源分歧统一标 needs_verify（7 项）。子动作：`overview` / `traditions` / `theses` / `six` / `practices` / `ethics` / `concept <id>` / `principles [id]` / `bridge [系统]` / `userface` / `verify` / `stats` / `search <词>`。数据 `data/concepts/datong_taxonomy.json`（由 `research/datong/build_datong.py` 构建，`--check` 防漂移） |
| `baigong` | **「百工」匠作概念系统**（v0.6.61，只读不联网）：以**墨子、公输般、公孙策、鲁班**（可扩大为三教九流）为「具体无解 / 暂时不允许 / 构建程序具体结构」三类工程场景的理念指导——核心理念五偶（墨子·守御明辩 / 公输般·九设九距 / 鲁班·绳墨规矩 / 公孙策·锦囊 / 三教九流总纲）、**七条可审计的匠作工程原则**（非攻守御/精慎明辩/九设九距/绳墨规矩/锦囊策略/器用明示/事实三表）、**三教九流 12 条**（三教 3 + 九流 9，一流一工程域映射）、**三场景**（无解→悬置降级 / 暂不允许→守御 opt-in / 具体结构→绳墨与九设九距）；**50 条桥接**到八个概念系统（comp 14 / plang 8 / daoxue 7 / apilab 7 / netsys 7 / quantum 4 / zhuangzi 2 / datong 1），构建期校验无悬空；**用户端面 + 语言面实测**（构建时读出 CLI 子命令 123 / GUI 窗口 108 / webapi ACTIONS 29 / deno 双文件 0000.0000.0000.0034.20261026；plang 161 条 / probe 实测 15 种 / comp 语言编译需要 16 条）。**诚实边界**：不复制经典全文，引文按通行本登记并统一标 needs_verify（公输般即鲁班一名两译、公孙策系文学形象）。子动作：`overview` / `core` / `craft` / `schools` / `scenes` / `principles [id]` / `concept <id>` / `bridge [系统]` / `userface` / `verify` / `stats` / `search <词>`。数据 `data/concepts/baigong_taxonomy.json`（由 `research/baigong/build_baigong.py` 构建，`--check` 防漂移） |
| `zhuangzi` | **「南华」用户端概念系统**（v0.6.60，只读不联网）：以《南华真经》（《庄子》33 篇，内篇 7/外篇 15/杂篇 11）为**用户端设计**的中心指导理念——核心理念三篇**《逍遥游》（无待一步）/《应帝王》（顺性不抢，浑沌之诫）/《大宗师》（以使用者意图为宗师）**，内篇辅篇四篇（齐物论·双模平权 / 养生主·养生不伤 / 人间世·人间安命 / 德充符·德充于内），外杂 26 篇选登 5 条（秋水/天道/达生/胠箧/概览）；落成**八条可审计的用户端人体工程学原则**；**18 条桥接**到 daoxue(9)/apilab(6)/datong(2)/netsys(1)；**用户端面实测**（构建时读出 CLI 子命令 123 / GUI 窗口 108 / webapi ACTIONS 29 / deno 控制台 0000.0000.0000.0034.20261026）。**诚实边界**：不复制经典全文；原典未逐字核对（needs_verify 挂牌）；原则系理念的工程翻译。子动作：`overview` / `core` / `inner` / `outer` / `ergonomics` / `concept <id>` / `principles [id]` / `bridge [系统]` / `userface` / `verify` / `stats` / `search`。数据 `data/concepts/zhuangzi_taxonomy.json`（由 `research/zhuangzi/build_zhuangzi.py` 构建） |
| `protec` | **「产品保护」概念系统**（v0.6.69，只读不联网）：以设备设施**长期可靠运行与基本保护**为中心——按**材料耐久(durability) / 电气安全(electrical) / 环境标准(environment) / 应急保护(emergency) / 基本保护(protection) / 传输与可用性(transfer) / 接入与链路(access) / IPv6 与 ICMPv6 控制面(ipv6)** 八轴登记 **53 个概念**；统于**七条基本保护原则**（冗余/降额/隔离/监控/接地/防护/可维护）；**34 条桥接**到 netsys(20)/datong(3)/apilab(4)/baigong(2)/comp(2)/zhuangzi(2)/quantum(1)；**用户端面实测**（CLI 128 / GUI 112 / webapi 29 / deno 双文件 0000.0000.0000.0034.20261026）。红线：只读登记，标准编号与机构按通行口径、不臆造实测数字；桥接只作结构同构、未核对处统一标 needs_verify（8 项）。子动作：`overview` / `durability` / `electrical` / `environment` / `emergency` / `protection` / `concept <id>` / `principles [id]` / `bridge [系统]` / `userface` / `verify` / `stats` / `search <词>`。数据 `data/concepts/protec_taxonomy.json`（由 `research/protec/build_protec.py` 构建，`--check` 防漂移） |
| `sciences` | **「自然科学」概念系统**（v0.6.69，只读不联网）：材料学/热力学/气候学/环境学/物理/化学/生物及方法论——按**材料学(materials) / 热力学(thermodynamics) / 气候学(climatology) / 环境学(environmental) / 物理(physics) / 化学(chemistry) / 生物(biology) / 方法论(methodology)** 八轴登记 **32 个概念**；统于**七条科学原则**（可证伪/可复现/量纲一致/能守恒/熵增/还原-整体/不确定性）；**18 条桥接**到 protec(10)/baigong(2)/comp(2)/apilab(1)/datong(1)/netsys(1)/quantum(1)；**用户端面实测**（CLI 127 / GUI 112 / webapi 29 / deno 双文件 0000.0000.0000.0034.20261026）。红线：只读登记，通说口径、不臆造；跨域同构非等同、未核对处统一标 needs_verify（3 项）。子动作：`overview` / `materials` / `thermodynamics` / `climatology` / `environmental` / `physics` / `chemistry` / `biology` / `methodology` / `concept <id>` / `principles [id]` / `bridge [系统]` / `userface` / `verify` / `stats` / `search <词>`。数据 `data/concepts/sciences_taxonomy.json`（由 `research/sciences/build_sciences.py` 构建，`--check` 防漂移） |
| `androidstd` | **国内标准·App 隐私合规知识库**（v0.6.67，只读不联网）：PIPL 上位法 → 四项国标 → 四部门规定（39 类必要个人信息范围/认定方法/备案）→ TC260 实践指南，**13 条全部官方源实检**；用户视角 App 合规检查清单（11 项，逐条回链标准）与知识库总报告零参可调。红线：只读知识库 + 出检查项，不扫描任何 App、不代执法、不代申诉（判定权在用户与监管部门）。四入口：CLI `androidstd` / GUI「国内标准·App隐私合规」/ `tasks/androidstd.py`（5 任务）/ subsystems 登记 |
| `gmsstd` | **GMS 标准·GMS 兼容与 Play 上架知识库**（v0.6.67，只读不联网）：CDD/CTS/VTS/STS 兼容体系 → GMS 兼容与许可 → Play 三件套（Integrity verdict 分层 / App Signing 密钥托管 / 2026-08-31 起 targetSdk API 36）→ Data safety 披露 → 安全公告补丁，**10 条除 STS 细节外官方源实检**（STS 社区整理逐条标 `needs_verify`）；上架自查清单 11 项逐条回链。红线：只读知识库，不扫描、不联网、不代审、不代申诉 |
| `fdroidstd` | **F-Droid 标准·免 GMS 自由软件分发知识库**（v0.6.67，只读不联网）：存储库模型（免账号）→ 收录政策（FLOSS）→ 反特征（Ads/Tracking/非自由依赖）→ fdroiddata 配方 → 可复现构建 → 仓库协议（索引签名/指纹信任）→ F-Droid vs Play 对照，**10 条经 GitHub/GitLab API 与官方文档检索快照实检**（fdroidclient GPL-3.0 3222★ / fdroiddata 358★）；收录/分发自查清单 8 项逐条回链。国内拿不到 GMS 时的标准答案：**能下载即可安装** |
| `guide` | **一屏操作入口地图**（v0.6.60，南华·逍遥游「无待一步」）：把全部子命令按 12 个场景分组一屏全览（巡检/报告/清理/设置/硬件/平台/网络/语言/概念/移动/门户/其他），入口唯一、任意深度可一步回顶；`--principles` 附八条人体工程学原则。地图双向校验：漏分组/幻影命令由 `tests/test_ergonomics.py` 断言，子命令增减即时暴露。三端同源：GUI 破坏性确认三段式（后果+回退）、deno 控制台启动横幅动作目录 + `GET /manifest`、错误统一指路 |
# system-optimizer · 万能系统优化与清理

一个**纯 Python 标准库**实现的跨平台系统优化 / 清理工具，覆盖：

| 平台 | 版本选择（2026-10 口径） | 清理方式 | 说明 |
|---|---|---|---|
| **Windows** | 10 / 11 | 本地 PowerShell 真正执行 | Win10 已终止支持 → 强提醒升级 |
| **macOS** | 13 / 14 / 15 / 26 (Tahoe) | 本地 shell（部分需 sudo） | 受 SIP 保护，仅清用户/可写目录 |
| **Linux** | 按发行版（Ubuntu/Debian/Fedora/Arch…） | 本地 shell（apt/dnf/pacman 自适应） | 深度清理需 root |
| **BSD** | FreeBSD 14/15 · OpenBSD 7 · NetBSD 10 | 本地 shell（pkg/pkg_add/pkgin 自适应） | sysctlbyname 原生接口读内核态 |
| **Unix** | Solaris 11 · illumos | 本地 shell（IPS pkg / svcadm / zfs / logadm / ipadm） | /etc/release 识别，SMF（v0.5.14 补全文档层与官方写接口） |
| **Android** | **8（下探下限）** / 8.1 / 9 / 10 / 11 / 12 / 12L / 13 / 14 / 15 / 16 / 17 | **adb** 推送到设备执行（文档层 `data/android_docs.json` + `and_tune_*` 官方写接口深度调优，v0.5.15；**逐项 API 门控 + 适老化只读巡检，v0.5.22**） | 需 USB 调试；未连接则优雅降级为文档指引。Android 8.0 = API 26 为支持下限，不支持的开关**明说「此版本无此开关」而非伪装成已开启** |
| **iOS** | 16 / 17 / 18 / 26 | **libimobiledevice**（文档层 `data/ios_docs.json` + `ios_tune_*` 官方写接口深度调优，v0.5.16） | 需已配对且信任；未连接则优雅降级为文档指引 |
| **uni-app** | 3.x / 4.x（跨端目标） | 工程侧自动 + 端上手动 | 一套代码到 App/H5/小程序；见「uni-app」章节 |
| **OpenWrt** | 23.05 / 24.10（路由器/嵌入式 Linux） | 原生只读接口（UCI/opkg-apk/netifd/ubus/procd/防火墙/无线/DHCP/存储，v0.5.20/21）+ 高危写操作 opt-in 指引 | 仅只读探测与文档引用；写操作（uci set/opkg install/sysupgrade/服务启停）只给命令文本、绝不自动执行 |
| **OpenJDK / JVM** | 8 ~ 25+（任何装了 JDK 的平台） | 纯 JVM 标准工具链只读（`java -version` / `--list-modules` / `-XX:+PrintFlagsFinal` / `jps` / `jcmd`，v0.5.22） | 只读体检；不改 `JAVA_HOME`、不设 GC 参数、不录 JFR、不 attach 进程；系统属性**只输出白名单键**，敏感值一律隐藏 |
| **Linux 内核** | 3.8+（module/firmware）/ 4.9+（BTF·eBPF） | 内核只读层（`/proc/modules`、`/sys/module`、`modinfo`、`/lib/firmware`、BTF/bpffs，v0.5.22） | 「可插拔」三层：module(s) / firmware / plugin(s)=eBPF；**绝不 insmod/rmmod、不写模块参数、不替换固件、不 load/attach eBPF** |

> **跨平台（platform="any"）能力**：语言自动启用（lang，含 Go/Rust/Java/.NET/PHP/Ruby…）、硬件标准（hardware）、字体/字符标准（fonts）、网络/ITU 开关（network）、**跨平台清点（cross：用户缓存/临时目录/大目录/DNS 刷新）**、**无障碍（a11y：ORCA / AT-SPI2 报告与标准对照）**、**架构/开源硬件（arch：龙芯 LoongArch / MIPS / RISC-V / OSHWA）**——见下文。另有 Go 组件 `src/go/` 提供同口径的单文件二进制查询（CI 交叉编译）。
> **v0.5.22 新增两条跨平台只读能力**：**OpenJDK/JVM 体检（jdk）** 与 **Linux 内核 module/firmware/plugin(s) 只读层（kmod）**，均不写任何东西；同时新增**任务档位（`profiles`）**与**数学量化评分（`score`）**两条元能力，用来回答「大而全 vs 小而全怎么选、选得对不对」。
> 注意：跨平台任务只作用于**操作系统**平台，不会混入 uni-app 这类「跨端目标」。BSD/Unix 原先与 Linux 重复的缓存/临时清理已统一收敛到 `cross`，避免重复。

核心理念：**默认只分析、不乱删**。所有删除类动作都带风险等级，需显式 `--apply` 才会落地，中/高风险还要 `--yes` 确认。

## 理论与只读红线（v0.6.40 起的统一框架）

本工具把「系统优化/清理」放进一套**只读观测理论框架**里：用理论当透镜，把系统拆成
可观测的维度，每个维度只观察、不改动、不代执行。任何写操作一律只给官方/规范指引。

| 理论层 | 作用 | 入口 |
|---|---|---|
| **量子理论及计算机原理** | 观测透镜：叠加态（并行非破坏观测各维）/ 纠缠（时间维与空间维相互关联）/ 测量（只读探针即测量，观测不改态）/ 后量子密码（FIPS 203/204/205 是未来兼容硬约束） | `chrono`（量子透镜） |
| **时间理论** | 时钟同步（NTP/PTP）、时区、生命周期阶段（provisioning→steady→aging→EOL）；只观测不改正 | `chrono`（时间维） |
| **空间理论** | 存储层次金字塔、虚拟地址空间、挂载点、NUMA 拓扑；只盘点不整理 | `chrono`（空间维） |
| **施时空组合理论** | 把带时间戳事件与当时空间资源态配对成因果链，识别时间维与空间维的纠缠（如某时刻负载高峰 ↔ 该时刻电气温度升高）；只读关联不阻断 | `chrono`（施时空组合维） |
| **未来兼容** | 标准 EOL 追踪、后量子迁移、前向兼容原则；只评估给迁移方向不自动升级 | `chrono`（未来兼容维） |
| **全时空全维度循环往复管理器** | 以上各维（及既有子系统维度）登记进统一维度注册表，`cycle_dimensions()` 以 round-robin **周而复始**遍历全部维度，每维一视同仁只读（亦复如是） | `chrono` → `cycle_dimensions` |

> **只读红线（贯穿全工具）**：绝不刷固件/装私有驱动/挂钩输入流/改写 PD 协商、绝不改系统
> 时钟时区/分区格式化/升级替换组件/执行量子写操作、绝不读解密口令/改 sshd_config/替你停服务、
> 绝不碰配电箱/测接触电阻、**绝不播放声音/调音量/采集麦克风内容/发射射频信号**。读操作只给官方指引，是否施工始终由用户在图形界面或厂商工具确认。

## 版本更新

- **0000.0000.0000.0034.20261026（2026-10-26）**
  - **补全批次：降维升维位元转化（docs/95）**：在 `native/qudit.py` 新增**降维升维位元转化**算法——把 W 位经典整数（每符号 2 维）**升维**成 N 个 d 级 qudit（每符号 d 维）、再**降维**回位元。**精确离散升维**＝base-d 按位展开（digit 升维）↔ 测量解码，严格同构 `R∘E=I`（γ=0 无损）；**量化升维**＝每符号 |dig> 纯态经同位能级散逸（T1 γ / T2 λ）+ 测量塌缩，诚实量化符号损失（与 `register_roundtrip` 同口径）。新增 `dimension_profile`（维数画像：升维比 `bits_per_carrier=log2(d)`、降维比 `reduction_factor=W/N`、联合态维数 `joint_dimension=d**N` **仅声明不物化**）/ `elevate_bits` / `reduce_bits` / `bit_convert` / `bit_convert_table`；`capabilities` 增 `bit_conversion`；`qudit_probe` 增 `dim_reduce_elevate_invertible`（全值域 R∘E=I）与 `dim_profile_invariant`（降维比≤升维比、总容量≥名义位宽、联合态维数一致）自检，纳入 `all_pass`。**CLI** 增 `quantum bitconv [width] [value] [gamma] [d]`（打印升维/降维维数画像 + 往返，γ=0 无损；`--table` 展示 8/16/64/128 全宽维数比）；`tests/test_qudit.py` 增 8 项断言。**整合**：包版本 0033→0034 全 11 处同步 + `concept_gui.html` 重生；quantum `_meta.version` 0068→0069（`build_quantum.py` 重烘焙 82 概念 / 56 桥接，`qudit-register` 概念 detail 与落法补记 0034 降维升维扩展）；docs/94 候选回填收尾。**验证**：`gen_concept_gui --check` OK、`audit_concepts --strict` 归零、`deno check` 通过、全量 pytest 见提交。

- **0000.0000.0000.0033.20261026（2026-10-26）**
  - **补全批次：量子架构多位元寄存器级往返与可复现耗散数值实验（docs/93）**：接 0032 轮「qudit 寄存器（结合 PiLink 内存交换参数覆盖 8/16/64/128 位元）」。**补齐寄存器级多位元往返**——新增 `register_roundtrip(width_bits, value, d, gamma, lam, seed)`：整数值按 d 进制拆成 N 个 digit，逐 qudit 经 `encode_log_amplitudes` 编码（digit=0 走真空态）、经 PiLink 逐交换（encode+measure 各一次，`link_writes==2·n_qudits`），可选 `apply_dissipation(γ,λ)` + 投影测量后解码回整数；诚实结果 **γ=0 无损全等**（`ber==0 && decoded==value`）、**γ>0 下漂**（`decoded≤value`，BER 随 γ 单调非减）。**可复现耗散数值实验**——`register_experiment` 固定位宽、固定 seed（`random.Random(seed)`）扫 γ 统计平均/最大符号误码率 BER；`register_experiment_plot` 改**纯标准库 SVG**（不引 matplotlib，守住核心 `pure_stdlib` 红线）。`QuditRegister.measure(qidx, rng)` 投影测量接 PiLink；`qudit_probe` 增 `register_roundtrip_lossless` 自检、`capabilities` 增 `register_roundtrip`/`register_experiment`/`register_plot`/`measure`。**CLI** 增 `quantum qudexp [width] [gamma] [seed] [samples]`（打印 BER-γ 扫描表，`--plot PATH` 生成纯标准库 SVG，width 越界诚实拒绝）。**整合**：包版本 0032→0033 全 11 处同步 + `concept_gui.html` 重生；quantum `_meta.version` 0067→0068（`build_quantum.py` 重烘焙 82 概念 / 56 桥接，`qudit-register` 概念 detail 与落法登记补记 0033 扩展）；`tests/test_qudit.py` 增 6 项断言；概念计数不变（仅给既有 `qudit-register` 补函数）。**验证**：`gen_concept_gui --check` OK、`audit_concepts --strict` 归零、`deno check` 通过、全量 pytest 见提交。

- **0000.0000.0000.0032.20261026（2026-10-26）**
  - **补全批次：量子架构多位元寄存器——结合 PiLink 内存交换参数覆盖 8/16/64/128 位元（docs/92）**：接 0031 轮「qudit 单 d 级系统」与更早的「量子架构基座（CPU↔闪存 π 链路不间断交换 / PiLink 内存交换参数）」，用户指令「结合之前的内存交换参数，就能支持 8_16_64_128 位元支持了」。**新增 `QuditRegister` + `register_report`（native/qudit.py）**：N 个 d 级 qudit 并联成寄存器，总容量 N·log₂(d) 比特；取 d=8（3 bit/qudit）、N=⌈位宽/3⌉，8/16/64/128 位元分别拆成 3/6/22/43 个 qudit（128 位 → 8⁴³≈2¹²⁹ 维联合态）。**为什么必须结合「内存交换参数」**：8^N 联合态绝不可物化为单一密度矩阵——每个 qudit 仅维持自身 d×d 局部态，CPU↔量子核的每一次交换（encode/gate/dissipation/measure）都经 `native/quantum.py` 的 **PiLink** π 链路环形缓冲记录（即基座的「内存交换参数」落点），状态以分块方式经链路交换而非一次性铺满内存。**诚实数值（register_report 演示 qudit[0]，v=6，γ=0.3）**：编码 6.0 → 理想解码 6.1459 → 散逸后 4.9920（下漂 1.1539）；链路统计如实记录交换次数（size=7 的 FIFO 节流）。**诚实边界（四条）**：①多位元=log₂(d) 比特容量非 d 比特；②经典数值模拟、不接硬件、不宣称量子优势；③**不物化 8^N 联合态**——仅逐 qudit 局部态，容量为分解后总容量；④耗散为单步均匀衰减模型。`qudit_probe` 增寄存器自检（分解覆盖名义位宽 + 内存交换记录交换），`capabilities` 增 `register_widths=[8,16,64,128]` 与 `register_memory_exchange`。**整合**：quantum taxonomy **81→82 概念**（state 域增 `qudit-register`）、**桥接 55→56**（qudit-register→plang:lang:python）；quantum `_meta.version` 0066→0067；CLI 增 `quantum qudreg [width] [d] [gamma]` 动作（width 越界诚实拒绝）；新增 `tests/test_qudit.py` 寄存器断言（分解覆盖、PiLink 记录、解码漂移）；TAGLINES 与 test_concepts_center/test_quantum/test_quantum_vm/test_gui_quantum 五处计数同步（81→82、55→56、state 域 7→8）。**验证**：`build_quantum --check` 通过、`audit_concepts --strict` 归零、全量 pytest 见提交。

- **0000.0000.0000.0031.20261026（2026-10-26）**
  - **补全批次：量子架构多位元（qudit）支持——同位能级散逸 + log 值交换（docs/91）**：用户指令「量子架构的多位元支持也要进行，用量子同位能级散逸，进行 log 值交换」。**新增 `src/python/sysweeper/native/qudit.py`（纯标准库密度矩阵，零依赖）**：d 级系统态 |ψ⟩=Σα_k|k⟩、广义门集 DFT_d（U_jk=ω^{jk}/√d）/ X_d（循环移位）/ Z_d（相位）均酉、**同位能级散逸双通道**——振幅阻尼（T1，γ：|k⟩→|k−1⟩，Kraus K0=|0⟩⟨0|+√(1−γ)Σ_{k≥1}|k⟩⟨k| 与 A_k=√γ|k−1⟩⟨k|）+ 相位阻尼（T2，λ：ρ'=(1−λ)ρ+λ Z_d ρ Z_d†），严格 CPTP 迹保持；**log 值交换**：encode_log_amplitudes（α_k∝exp(−(k−μ)²/2σ²)，μ=log₂v）→ 耗散信道 → decode_log_value（v̂=2^{Σk·p_k}）；exchange_integer 以 n 个 d 级 qudit 承载 n·log₂(d) 比特。**诚实数值（d=5, v=6）**：γ=0 解码 6.1459、γ=0.05→5.9366、γ=0.1→5.7343、γ=0.2→5.3503、γ=0.35→4.8220、γ=0.5→4.3458、γ=0.75→3.6544、γ=1.0→3.0730——**信息随能级向低泄漏单调损失**；纯度随耗散单调衰减（1.0→0.52）；exchange_integer 在 γ=0 无损全对。**诚实边界（三条）**：①多位元的「元」是**能级数 d**、容量是 **log₂(d) 比特/符号**而非 d 比特——不把 d 级混同经典 d 位宽（comp 位宽阶梯到 128 位 SIMD 为止，qudit 无经典位宽轴）；②经典数值模拟，**不宣称量子优势**、不接硬件；③耗散为单步均匀衰减模型，不建模真实器件 T1/T2 频变、串扰与门误差谱。**整合**：quantum taxonomy **78→81 概念**（state 域增 `qudit-multi-level`、error 域增 `level-dissipation`、qsim 域增 `log-value-exchange`）、**桥接 51→55**（qudit-multi-level→plang:lang:python + daoxue:fan-zhe 类比「二生三三生万物」的层级推广链、level-dissipation→daoxue:fan-zhe 同构「能级只能向低跃迁的不可逆」、log-value-exchange→plang:lang:python）；quantum `_meta.version` 0065→0066；native dispatch 注册（`qudit` 模块）+ `quantum qudit [d] [value]` CLI 动作（越界值按 μ=log₂(v)∈[0,d−1] 诚实拒绝而非静默截断）；新增 `tests/test_qudit.py`（**16 passed**：酉性逐 d 断言、CPTP 迹保持、耗散单调性、log 值交换往返、边界拒绝）；TAGLINES 与 test_concepts_center/test_quantum/test_quantum_vm/test_gui_quantum 六处计数同步（78→81、51→55、state 域 6→7）。**验证**：`build_quantum --check` 通过、`audit_concepts --strict` 归零、11 系统 `build --check` 全过、定向测试 101 passed、全量 pytest 见提交。**纪律**：CLI 参数越界**拒绝而不截断**（截断会静默失真，违反诚实口径）——这条从 qudit 编码函数越界行为学来，已成本轮可复用纪律。

- **0000.0000.0000.0030.20261026（2026-10-26）**
  - **补全批次：#690 32 位 DOS 的 C 编译路径缺口闭合——DJGPP GCC 预构建工具链实跑 + dosbox DPMI 双面证据（docs/90）**：接 0028 轮挂号的诚实缺口「DJGPP 的 GCC/libc/stub 包不在 apt（仅 binutils 侧 as/ld），watcom 不可得——32 位 DOS 侧只有汇编链没有 C 编译器」。**路线**：apt 确认仅 binutils-djgpp；自上游 `andrewwutw/build-djgpp` release v3.4（2023-06-12，NetHack 3.7 官方交叉编译指引引用源）取 Linux64 预构建 `djgpp-linux64-gcc1220.tar.bz2`（GCC 12.2.0 + DJGPP libc + go32 stub，**80,596,981B，sha256 `8464f170…`**）。**下载工程（本轮血泪）**：wget 单连接被中断时尾部半块未完 + aria2 `-c` 从该不对齐断点续传拼接 → **bzip2 CRC 坏（大小对但内容腐）**；安装 aria2（1.37.0）多连接 `-x16 -s16` 从头干净重下才通过 `bzip2 -t`——「续传必须断点对齐，否则宁删重下」。**编译**：`i586-pc-msdosdjgpp-gcc -O2 -Wall -Wextra hello32c.c`（ANSI C，零警告）→ `hello32c.exe` **197852B**（`MS-DOS executable, MZ for MS-DOS, COFF for MS-DOS, DJGPP go32 DOS extender`），objdump 反汇编见 `__exit`/`_exit` 调用链（24212 指令行）。**实跑闭环**：dosbox 0.74-3 无头 + `dpmi=true` + **自带 CWSDPMI(csdpmi7b)** + `[autoexec] mount c / c: / cd \`（cwd 落 C:）——`OUT.TXT`（stdout 重定向，DOS 文本模式 `\r\n` 计 18B）与 `Z32C.TXT`（fopen/fprintf/fclose 二进制 16B）**双面证据均为 `Z32C-RT-OK55\nFB\n`**，累加值 **0xFB = 0x55+0x29C(10 字符和)+0x0A 独立复算一致**，dosbox rc=0——32 位 DOS 取得与 8 位 OUT 流、16 位 R7.TXT 同级的宿主机可观测 C 闭环。**工程坑入账（5 条）**：①wget 中断尾部半块 + aria2 续传拼接致 bzip2 CRC 坏须从头干净重下；②dosbox 0.74-3 的 `dpmi=true` 不被 DJGPP 12.2 go32 桩接受（仍报 "no DPMI - Get csdpmi*b.zip"），须自带 CWSDPMI.EXE；③DOS 批处理 + CWSDPMI 下 `%ERRORLEVEL%` 不 propagate 且 dosbox 退出挂起（rc=124），进程完成证据取直跑 rc=0 + fclose 写全，**退出码面不伪证**；④`-c "C:"` 换驱对后续 `-c` 不生效须 `C:\` 全路径（重申上批），批处理内部 `cd \` 生效；⑤程序相对路径 `fopen` 在 Z: 只读虚拟盘失败（FILE-FAIL），须先 `cd` 到 C:。**整合**：`protected-32` concept detail+engineering 换「三路径实测」（as/ld 手写链 + gcc-m32 宿主 + DJGPP GCC C 闭环）口径、缺口改为已闭合；新增 `tests/test_djgpp32c.py`（设计值 0xFB 独立复算 + 宿主 gcc 三面 roundtrip + DOS 侧 MZ/证据归档口径，**3 passed**）；**数字**：87 概念 / 15 语言实测 / 100 桥接无悬空（概念数不变——本轮是缺口闭合非新增概念）；comp taxonomy 版本 0071→0072；包版本 D 段 0029→0030 全 11 处同步（cnstd 数据 + version.py + pyproject + console.ts + report_viewer.ts + go + 5 taxonomy 经重建） + concept_gui.html 重生（data-sha256 `cd5bc5ee…`→`a529aa57…`，11 系统/66 边/2 外部拓扑不变）。**验证**：定向 `test_djgpp32c`+`test_comp`+`test_cnstd`+`test_concept_gui`+`test_z80core` 37 passed、全量 pytest 见提交、`audit_concepts --strict` 归零、11 系统 `build --check` 全过。**仓外交付**：`/workspace/dos-toolchain-20261026/`（hello32c.c/exe、hello32c_evidence.txt、collect_32c_evidence.sh、dosbox-dpmi.conf、CWSDPMI.EXE、djgpp-cross/）。

- **0000.0000.0000.0029.20261026（2026-10-26）**
  - **补全批次：8 位运行层缺口闭合——自含 Z80 执行内核 + dz80 独立交叉核对（docs/89）**：接 0028 轮「8 位只到编译产物级」的诚实缺口，本轮按「闭环-缺口分类与按需补齐」纪律真正闭合。**装**：pyz80 探测后证实 PyPI 上是汇编器非模拟器（诚实排除）、apt 无 Z80 模拟器候选（fuse/openmsx/tilem 均无法无头加载裸二进制）——改走**自含内核路线**：`research/comp/z80core.py`（全基础集 256 槽 + CB 全块 + ED 常用块 + DD/FD 前缀 + DDCB，已知答案自测 22/22 覆盖 ADD/SUB/INC/DJNZ/LD 双字节寻址/OUT/RLCA/BIT/CALL-RET/DAA/LDIR/SBC/PUSH-POP 的标志位语义）+ `research/comp/z80_runner.py`（Intel HEX 解析校验和、OUT 端口捕获、.map 符号回读、HALT 停机、dz80 交叉核对）。**实跑闭环**：`hello8run.c`（sdcc -mz80，ANSI C）→ 618B ihx → 内核执行 196 指令 ~1710 T 态（标称）后 HALT 停机 PC=0264；**OUT(01) 端口流 `Z80-RT-OK68\n`**（宿主机侧逐字节捕获）、**_counter@8000 回读 0x68**（= 0x55+9 字符+0x0A，与手算一致）——8 位档取得与 16 位 R7.TXT 同级的宿主机可观测闭环。**独立交叉核对**：dz80（d52 包 3.4.1，与内核无共享代码）对「已执行指令拼接流」线性反汇编，助记符序列 **197/197 一致**——长度解码分叉会被立即发现。**内核调试入账的工程坑**：x=0/z=2 行寄存器对索引须用 p=y>>1（0x0A=LD A,(BC) 曾误读 DE）；JR 行 y=4→JR NZ、y=5→JR Z（条件曾写反）；LD rp,nn 与 ADD HL,rp 曾被误加 _imm16()（多吞 2 字节）；asz80 绝对寻址须括号 `ld a,(_sym)`（裸写 error a）、OUT 立即数十进制 `out (1),a`（`1h` 后缀不可）；dz80 只接受 cwd 相对文件名（绝对路径回落 '.hex' 失败）。**诚实边界**：内核非参考级实现——不建模中断接受/精确 T 态/内存竞争，覆盖范围 docstring 文档化；qemu/MAME/FCEU 维持存在性只读探测不启动。**整合**：bit8-era detail+engineering 换「编译+运行双实测」口径；新增 `tests/test_z80core.py`（自测回归锁 + ihx 端到端，2 passed）；**数字**：87 概念/15 语言实测/100 桥接无悬空（概念数不变——本轮是口径升级非新增概念）；comp taxonomy 版本 0070→0071；包版本 D 段 0028→0029 全 11 处同步 + concept_gui.html 重生（data-sha256 `a65ad71b…`→`cd5bc5ee…`）。**验证**：定向 `test_z80core`+`test_comp`+`test_concepts_center` 全过、全量 pytest 见提交、`audit_concepts --strict` 归零、`build_comp --check` 通过。**仓外交交付**：`/workspace/dos-toolchain-20261026/`（z80core.py/z80_runner.py/hello8run.*/Z80RUN.TXT 更新）。

- **0000.0000.0000.0028.20261026（2026-10-26）**
  - **构建批次：8/16/32/64/128 位元 DOS 工具链环境生成 + 概念系统 DOS 子系统整合（docs/88）**：用户指令「生成8、16、32 位元dos工具链环境，并且整合到概念系统的dos子系统」，续轮扩展「8_16_32_64_128 位元……稳态且交互往返……闪存设备……继续到收尾」。**装（用户显式请求的构建车道，先例 #8 mingw-w64/#9 PE viewer，与只读分析批次两车道不混用）**：bcc 0.16.17（dev86，16 位 8086 K&R C，含 as86/ld86）、sdcc 4.2.0（8 位 Z80）、binutils-djgpp 2.35.1（32 位 DOS go32 DPMI 交叉 as/ld）、dosbox 0.74-3（运行层）、gcc-multilib（宿主 i386）。**位宽阶梯全档实测**：8 位 `sdcc -mz80` → 358B Intel HEX（hex 内 jp 0x0100/RST 08h/jr 循环指纹）；16 位 `bcc -Md -0` → 228B 无头 COM（mov ax,42 + int 21h/20h 指纹，dosbox 无头 exit 0）；16 位手写链 `as86 -0`+`ld86 -d` → 64B 裸 COM，**int 21h 3Ch/40h/3Eh 建写关 C:\R7.TXT、宿主机回读 18B『ROUNDTRIP-OK-16BIT』——实模式↔宿主文件往返闭环**；32 位 DOS djgpp as+ld → 7628B MZ+COFF go32（内嵌 DJ Delorie stub 1993-1995/2022 重建），dosbox 实跑 exit 0（int 21h 4Ch 经 DPMI 反射）；32 位宿主 `gcc -m32`、64 位 `gcc -m64` 均实跑 exit 0；128 位 `__int128`（sizeof=16、hi/lo 算术往返）+ SSE2 movdqa XMM 内存往返 1 2 3 4。**稳态交互往返实证**：loop.com 死循环 dosbox 挂起被 timeout 杀（exit 124）证执行链。**工程坑入账**：ld86 -d 以 origin 0 产 COM 而 DOS 装在 PSP:0x100，as86 `#label` 立即数汇编期解析不带重定位——手写汇编须自加 `$100`（nasm org 0x100 等价物；bcc 传 -T100、C 代码走可重定位引用故无恙）；dosbox `-c "C:"` 换驱对后续命令不生效须写 `C:\` 全路径；sdcc 4.2 须 ANSI C 且 z80 裸 `__at` 被拒须 `__sfr __at`；bcc 是 K&R C。**诚实缺口**：DJGPP GCC/libc/stub 不在 apt（watcom 亦不可得）——32 位 DOS 侧只到 as/ld，needs_verify 未从上游下载；8 位无 Z80 运行层（qemu 不可得）只到编译产物级；**「量子架构位宽」不成立**（qubit 无经典位宽、OpenQASM/QIR 无寄存器宽度档；qiskit/cirq 不可导入、apt 无候选）——不臆造量子位阶梯；**「能量衍射」非存储工程概念**——不臆造映射，真实对应项（电荷保持/易散性、跨设备 I/O 分布、磨损均衡/调度）实测登记（vda/vdb/vdc + 1000 NBD；rotational=1/scheduler=none/discard=0；无 smartctl）。**整合（comp bitwidth 域 = 概念系统的 DOS 子系统；datong 为哲学类无 DOS）**：bit8-era/real-mode-16/protected-32/long-mode-64 四条 detail+engineering 换实测口径；**新增 simd-128 概念**（128 位 SIMD 世代，桥接 quantum:qubit 标明范式边界）；retro-dos-stack 两车道纪律成文。**数字**：87 概念（86→87）/ 15 语言实测 / 100 桥接无悬空；comp taxonomy 版本 0069→0070；包版本 D 段 0027→0028 全 11 处同步 + concept_gui.html 重生（data-sha256 `d5c0cfe1…`→`a65ad71b…`）。**验证**：定向 `test_concepts_center` 9 passed、全量 pytest 见提交、`audit_concepts --strict` 归零。**仓外交付**：`/workspace/dos-toolchain-20261026/`（data.json + report.md + 全部构建产物）。

- **0000.0000.0000.0027.20261026（2026-10-26）**
  - **导入分析学习应用 batch-11：010 Editor 二进制模板分析（SweetScape 商业专有，docs/87）**：用户指令「010 editer学习」。只读核实官网 7 个 URL 全部实测 200——双定位（"World's Best Hex Editor" + Tree-sitter 实时解析 45+ 语法的文本编辑，50GB+ 大文件/列模式/无限撤销）、**Binary Templates**（类 C/C++ struct 领域语言，可含 if/for/while 与函数，300+ 格式，打开自动运行，在线 Template Repository 分享）、脚本引擎（类 C 语法 350+ 函数、与模板集成「给模板变量赋值即改文件」、CLI 无界面批处理、断点/监视调试器）、分析工具（CRC-16/CRC-32/Adler32/MD2/MD4/MD5/RIPEMD160/SHA-1/SHA-256/TIGER 校验和/哈希；X86/ARM/MIPS/PowerPC/SPARC/SystemZ/XCore 七架构反汇编；直方图；二进制逐字节比较）、驱动器级编辑（NTFS/FAT16/FAT32/exFAT/HFS + MBR/EFI 分区 + slack space，取证/恢复路径）、稳定版 **16.0.4**（Beta v17 在测）、三平台（Windows 11/10 32/64 位+便携、macOS 10.14–15 Intel+ARM、Ubuntu 18.04–25.04 32/64 位）逐产物附 SHA256、许可 **商业专有买断 $149.95 商用 / $59.95 家用学术、30 天全功能试用无免费档**（EULA kb1038）。**边界分级（守 #591/docs/59）**：`reverse_docs.json`（黑箱逆向与调试工具链知识库，UPX 壳特征/熵判据/PE 解剖/MinGW/GDB 等 9 条）是 **真实 counterpart**（同一二进制格式分析工作流的商业级形态，其 `_position` 明示服务「学习二进制格式与调试方法」）→ **走回填路径**：新增 `hexeditor_010_templates` 条目（8 protocols/5 interfaces/5 docs，全官方口径）+ `REVERSE_CHECKS` 增 `template_structural_reading` 检查项 + `reverse_report()` 管线插入「010 Editor 模板结构细读」步；`imagefmt`/`compress`/`firmware`/`legacy` 均为 gen-stub 空占位桩（items:0）按纪律**不填空桩**；**不新增概念域**（概念系统零改动）。**可复用纪律**（仅纪律层面）：模板=机器可读的格式说明书（↔ 本仓格式路由三段式）、模板即断言须防漂移（↔ 沙箱实测口径固化）、`binary_scan` 粗判→模板细读两步走、商业专有不进运行时依赖（↔ 零依赖红线）、只读边界同源（↔ `readonly_reverse_ethics`）。**诚实边界**：60 天退款保证/一年免费支持仅第三方评测站转述（needs_verify，不纳入条目）、Beta v17 未展开、公司成立年份取版权线 2002–2026 互证；专有软件**不安装不试用不复制不链接**。**落点**：`reverse_docs.json` +1 条目、`native/reverse.py` +1 检查项、`test_reverse.py` 三处计数同步（条目 9→10、检查项 8→9）、docs/87、README 本块（含 0025/0026 补账）、版本号 D 段 0026→0027 全 11 处同步 + `concept_gui.html` 重生（data-sha256 `1ff79e4a…`→`d5c0cfe1…`）。**验证**：定向 `test_reverse` **16 passed**、全量 pytest **1755 passed / 6 skipped 零回归**、`audit_concepts --strict` 归零。
  - **版本台账补账（0025/0026，据 git 历史 50f73d1/ba81ca0/cd0091a）**：batch-10 两轮 bump 当时未落 README 台账（仅 protec 表行刷新），现补齐——**0026.20261026**：batch-10 续推，CLFS 版本化 book/view 路径穷尽探测全 404（sitemap 404、cross-lfs.org 无渲染书）以 trac.clfs.org 指针+精确 needs_verify 落地未臆造；`distro.items` 填 4 条 Slackware 系统构成条目（包集 A–Y 地图/引导 initrd/升级安全序/原生包管理，全 official_verified）；版本 D 段 0025→0026 全 11 处同步 + concept_gui.html 重生；docs/86 记 §六。**0025.20261026**：batch-10 首轮，Slackware+LFS 全系列文档归集，25 个候选 URL 实测 24×200，命中 `distro`（18 条 references）与 `linux`（7 条）真实 counterpart 回填 + `sysbase_docs.system_layout` 补 Slackbook 系统构成视角；守 #591 不新增概念域；docs/86。

- **0000.0000.0000.0024.20261025（2026-10-25）**
  - **S4 整体收尾（#667）：概念系统十一成形 + search_all 纳入新系统 + 版本升 D 段**：用户对「完善 concepts/__init__.py OVERALL_GUIDANCE、确认 search_all 纳入新系统、版本号升 D 段、全量 pytest 0 failed、audit 零不一致、各阶段独立提交并推送 origin/main」收尾。核实 `REGISTRY` 已登记 **十一个概念系统**（plang/netsys/daoxue/quantum/comp/apilab/zhuangzi/baigong/datong/protec/sciences）——`overview`/`search_all`/`topo` 均遍历 `systems()`（=REGISTRY 键），新增的 `protec`/`sciences` 已自动纳入；逐方法核实 `protec.py`/`sciences.py` 均实现 `search`/`info`/`stats`/`bridges`，`search_all` 跨系统检索对二者生效；`OVERALL_GUIDANCE` 为八源元理念（因果记录·全息·感应），与系统计数无关、口径自洽。`#666` 缺口清单（docs/82）确认三大面无代码层明显缺陷。**版本号升一版（monorepo 里程表纪律）**：整体包 `0000.0000.0000.0023.20261025` → `0000.0000.0000.0024.20261025`，五处核心同步（`version.py`/`pyproject.toml`/`main.go`/`console.ts`/`report_viewer.ts`）+ `cnstd_domestic_standards.json` 版本串 + 五 taxonomy JSON（baigong/datong/protec/sciences/zhuangzi）的 `deno_console_version`/`deno_report_viewer_version` + `tests/test_cnstd.py` 前缀断言 + README protec 表行 deno 口径 0023→0024；概念系统拓扑与桥接不变（protec 53 概念/34 桥接、sciences 32 概念/18 桥接未动）。**落点**：docs/82 + 版本五处 0023→0024 + 5 taxonomy deno 版本 + test_cnstd 前缀 + concept_gui.html 重生 + README 本块与 protec 表行 deno 口径。**验证**：`audit_concepts --strict` 归零、定向 `test_version`/`test_cnstd`/`test_concept_gui` 通过、双 HTML `--check` 同步、全量 pytest **1755 passed / 6 skipped 零回归**（基线）。

  - **导入分析学习应用 batch-7：Authentik（自建身份 IdP）+ herdr（AI Agent 终端复用器）（docs/83）**：今日头条两篇只读核实（Authentik：OAuth2/OIDC/SAML/LDAP/SCIM/ForwardAuth 全协议 IdP，Docker Compose 部署，Provider/Application/Flow/Stage 四概念，Grafana OIDC 接入示例，对比 Keycloak/Authelia/Okta；herdr：Rust 单二进制 AI Agent 终端复用器，ctrl+b 对齐 tmux，blocked/working/done/idle 四态感知，CLI+Socket API 支持 Agent 调度 Agent，AGPL-3.0-or-later，macOS/Linux/Windows 预览）。**边界分级（守 #591/docs/59）**：Authentik 候选 `netauth` 但该文件为「网络隐私验证」空占位桩（items:0、明确不自动填充正文）、全仓无 sso/ldap/oidc/idp 关键词命中 → **无真实 counterpart**；herdr 全仓 `data/` 无终端复用器/Agent 运行时归宿（rfc/toolchain 中 tmux/agent 命中为协议/工具链上下文误碰）→ **无真实 counterpart**。两者一律**只沉淀学习笔记、不新增概念、不填充空 stub**；候选映射仅标注（Authentik→netauth、herdr→reverse_docs/toolchain_catalog，均 needs_action 候选，不创建不实现）。**诚实边界**：两篇均第三方头条转述非一手文档，Authentik LICENSE/herdr star 数/对比数字均 needs_verify；只读红线恪守（不克隆不安装不构建不复制代码，AGPL 代码不复制不链接不移植）。**落点**：docs/83 + README 本块（版本沿用 `0000.0000.0000.0024`，无功能/数据层改动、不升版）。**验证**：全量 pytest **1755 passed / 6 skipped 零回归**（`audit_concepts --strict` 归零，概念系统未动）。

  - **导入分析学习应用 batch-8：Arch Linux ARM PKGBUILDs（docs/84）**：GitHub `archlinuxarm/PKGBUILDs` 只读核实——ALARM 官方构建脚本仓（从上游 Arch Linux 改写以在 ARM 架构构建，未改动纯上游包不入仓），布局 `core`/`extra`/`aur`/`alarm`，构建系统私有变量 `buildarch` 位掩码（1=全 / 4=armv7h / 8=armv8 AArch64）、`noautobuild`、`highmem`；近期提交活跃（2026-10）。**边界分级（守 #591/docs/59）**：本仓 `packages_docs.json` 的 `pacman` 段（"pacman（Arch Linux / 衍生）"、`url` 即 PKGBUILD wiki）是 **Arch/pacman/PKGBUILD 域真实 counterpart**，且全仓 `data/` 多文件命中 `pkgbuild`/`makepkg`/`pacman`/`archlinux`/`aur` → **有 counterpart，走回填路径**（区别于 batch-7 纯笔记）。**回填**：`packages_docs.pacman.references` 新增 1 条权威指针（对齐 `busybox.json` 等仓内 `{name,org,url}` 极简 schema；`test_packages.py::test_knowledge_base_loads` 仅断言 4 操作键存在、允许额外键，`native/packages.py` 按固定键 `.get()` 取操作不遍历全部键，无破环）；详细事实（布局/位掩码/私有变量）沉淀于本 docs。**诚实边界**：本仓为源码构建脚本非二进制包（ALARM 二进制由 archlinuxarm.org 镜像分发），仓库 LICENSE/star 未呈现（needs_verify），只读红线恪守（不克隆不安装不构建不复制代码）。**落点**：`packages_docs.json` 回填 + docs/84 + README 本块（版本沿用 `0000.0000.0000.0024`，`packages_docs.json` 不在版本同步面内、不升版）。**验证**：JSON 合法、全量 pytest **1755 passed / 6 skipped 零回归**（概念系统未动）。

  - **导入分析学习应用 batch-9：Slackware 在 LVM 逻辑卷上安装（README_LVM.TXT）（docs/85）**：用户贴出在 `The resulting initrd image will be written to th` 处截断的官方安装指南，已据上游 `mirrors.slackware.com/.../slackware-15.0/README_LVM.TXT`（作者 Eric Hameleers，2013-10-13）补全尾部并重写为结构化中文 + 增「关键步骤速览 / 常见陷阱 / 优化注解」。**边界分级（守 #591/docs/59）**：本仓 `storage_docs.json` 的 `lvm` 条目（LVM 域权威归宿，url 指 `lvm(8)`）是 **真实 counterpart**，且现有 `lvm.advice` 偏运行期（lvreduce/pvmove/thin pool）、缺安装期 initrd 强制要点 → **有 counterpart，走回填路径**。**回填**：`storage_docs.lvm` 加 `references` 权威指针（已核实 URL，对齐仓内 `{name,org,url}` 惯例；`test_storage_docs_load` 仅断言 8 键含 name/org/url/protocols/interfaces/docs/advice、允许额外键，无破环）+ `advice` 补安装期要点（根在 LVM 必须 initrd、须 chroot 后 mkinitrd -L、huge 须换 generic 内核、引导器显式 initrd= + root=）。**事实要点**：PV/VG/LV（`pvcreate`/`vgcreate`/`lvcreate -L/-l`）、分区类型 `8e`、setup TARGET 选 `/dev/<vg>/<lv>`、ext4/btrfs/jfs/xfs、SWAP-on-LVM 须先 `mkswap` 再 ADDSWAP。**诚实边界**：属发行版安装规程（操作指引非规范）；许可证随 Slackware、README 自由文档已署名；只读红线恪守（不克隆/不安装/不构建/不复制代码）；粘贴截断处内核 `5.15.19` 已据上游补全为 `5.15.19-smp`；UEFI/elilo 差异标 needs_verify。**落点**：`storage_docs.json` 回填 + docs/85 + README 本块（版本沿用 `0000.0000.0000.0024`，`storage_docs.json` 不在版本同步面内、不升版）。**验证**：JSON 合法、`test_storage_docs_load` 通过、全量 pytest **零回归**（概念系统未动）。

- **0000.0000.0000.0023.20261025（2026-10-25）**
  - **release 架构包完善（#662，docs/80）：本地全矩阵构建 + CI pyz 缺口补齐 + 资产矩阵登记**：排查现有 release 打包脚本/CI 与实际资产的三方对账（CI 矩阵 × syspkg targets × 宿主工具链）。**本地全矩阵实跑**——`syspkg all` 12 产物（pyz/wheel/sdist noarch + go×7 含 darwin arm64/amd64 + rust-native×2，file 逐行校验 + smoke ok=true）；`classics-rs/build-rs.sh` **10/10**（Linux 七架构 + Windows×2 + WASM，含 MSB s390x 与 32 位 ARM EABI5）；`Windows/build.sh` 序贯产出 4 个 PE 后于 arm64 步如实中断。**CI 缺口**：docs/37 各系统安装方式 A 首推的**单文件 .pyz 历来未进 CI**（两份 build.yml 的 build-python 只构建 sdist/wheel，Release 资产里从来没有 .pyz）——外层与内层 build.yml 各补 `pyz` 构建 + `smoke` 两步（上传/发布路径 dist/* 天然覆盖；两份 YAML 过语法校验）。**登记**：`toolchain_catalog.json` 新增 `release-matrix` 条目（12+10+PE 家族资产矩阵、SHA256 前 16 位、CI 覆盖与缺口清单）、`ci-workflows`/`syspkg` 两条目口径刷新、`target_matrix` 新增 19 行（go×7 / classics-rs×10 / noarch / Windows ARM64 缺口标注行）。**诚实缺口（needs_action，docs/80 §五）**：Windows ARM64 的 C 工具链（Ubuntu apt 无 mingw aarch64 包——`gcc-mingw-w64*` 仅 i686/x86_64 两族，65 个 mingw 包无一 aarch64）与 Rust 工具链（rustc target-list 无 `aarch64-pc-windows-gnu`；变体 `aarch64-pc-windows-gnullvm` 在列但 rust-std 组件下载在本环境停滞于 12.9MB——static.rust-lang.org 大文件传输被断、HEAD 小请求正常）；该架构由 **go:windows-arm64 覆盖**（CI 矩阵 + 本地构建）；classics-rs 的 `*-apple-darwin`（无 macOS SDK）与 `aarch64-pc-windows-gnu`（上游 rustc 不提供）属上游不可能长期缺席；Android APK 未上 CI（需网络 SDK）、adb 缺席致设备端审计如实 SKIP。
  - **落点**：docs/80 + 两份 `.github/workflows/build.yml`（pyz+smoke）+ `toolchain_catalog.json`（release-matrix 条目 / 两条目刷新 / target_matrix +19 行）+ README 本块与 protec 表行口径刷新 + 版本五处 0022→0023 + 5 个 taxonomy JSON 重建（deno 双版本字段）+ concept_gui.html 重生（data-sha256 ec63f54274bd）+ tests/test_cnstd.py 版本戳。**验证**：YAML 语法校验 ×2、catalog 定向测试、全量 pytest **1755 passed / 6 skipped 零回归**。

  - **国内标准资源导入分析学习应用（#663，docs/81）：14 链接只读核实 + 数据层增量（不单独升版）**：只读核实 14 个国内标准相关链接（openstd/std.samr 国标全文与总门户、hbba 行业 76 行业 88751 项、htsfwb 合同示范文本近 500 种、ccsa 通信标准化、spc 标准在线服务、biaozhuns 标准网免费聚合、modbus.cn 工业总线、mqtt.org.cn + techphant TPUNB 物联网、腾讯云/华为云科普文章、gitcode RFC 中文版 ~300 份）。全部吸收进 `cnstd_domestic_standards.json` 的 11 个条目（`openstd_platform`/`std_samr_platform`/`hbba_platform`/`ccsa_platform`/`spc_platform`/`biaozhuns_platform`/`htsfwb_platform`/`modbus_specs`/`mqtt_protocol`/`open_standards_articles`/`rfc_cn_translations`），`_meta` 固化 `sources_total=14 / sources_imported=14 / layering` 分层与红线条目。**严守 #591 纪律**：科普文章（链接 4/12）与 RFC 中文翻译（链接 13）明确标记「非规范源 / 学习用途」，不污染权威标准数据；第三方「免费分享」仅登记存在性与风险，不提供代查/代下/破解；不臆造实测数字。版本号沿用 `0000.0000.0000.0023`（数据层随 #662 已升 0023，本轮仅增 docs + README，避免无功能收益的 20 文件面改动）。**落点**：docs/81 + `cnstd_domestic_standards.json` 14 源全吸收（11 条目）+ README 本块 + HANDOFF 第二十二轮。**验证**：定向 `test_cnstd` 通过、全量 pytest **1755 passed / 6 skipped 零回归**（`audit_concepts --strict` 归零，`cnstd` 为数据层不进概念审计）。

  - **S3 源码补全完善缺口清单（#666，docs/82）：classics 多架构 + sysweeper 12 语言 + 硬件域 只读审查**：逐脚本核实 classics 五兄弟——`classics-rs/build-rs.sh` 10/10 目标（Linux 7 架构 + Windows×2 + WASM，#662 已实跑）、`classics-linux` Arch 3 架构 + deb/mobile 矩阵、`classics-ios-mac` 与 `classics-harmony-app` 需宿主 SDK（Xcode/DevEco，交叉不可建、脚本如实标注）、`classics-swift-linux` 仅 Package.swift（SwiftPM 宿主架构非交叉职责，非缺口）；sysweeper `src/` 14 个语言单文件组件（12 种同口径只读范式 + 宿主 python + uni-app）已由 `langdetect.LANGUAGES` 注册、Windows PE 查看器多语言接入 `parity_test.py`；硬件域 `hardware`/`hardware_kernel`/`edge`/`durability`/`electrical`/`peripheral`/`jdk`/`kmod`/`kernel`/`arch`/`asm` 全部在 `registry.py` + `native/__init__.py` 双注册、零悬空。**审查结论**：三大面代码层与注册层均已落地；现存缺口**全部为交叉 SDK / 上游工具链约束**（`aarch64-pc-windows-gnu` 上游不提供、`*-apple-darwin` 无 macOS SDK、iOS/macOS/HarmonyOS 需自托管 runner），属 `needs_action` 环境项、**无代码层明显缺陷可安全修复**——与 #662 `docs/80` §五 口径一致，不虚构修复。**落点**：docs/82 + README 本块（版本沿用 0023，#666 为审查清单无功能改动，升版留待 #667）。

- **0000.0000.0000.0022.20261025（2026-10-25）**
  - **量子构建测试床收尾（#661，docs/79）**：`research/quantum/quantum-testbed.sh` 落地三阶段轻量验收路径——stage1 debootstrap minbase bookworm + chroot 装 python3（默认 aliyun 镜像：实测清华源 CDN 偶发 403 约一成失败，aliyun/ustc/tencent 三源 debootstrap --download-only 全对全 0 失败；外层 3 次有限重试 + apt `Acquire::Retries=3` 兜底）；stage2 chroot 内 `build_quantum.py --check`（78 概念 / 51 桥接无悬空 / 11 标准，不拷 `sysweeper/__init__.py`、经 namespace package 引入 concepts 只读层）；stage3 chroot 内 mkinitramfs 生成 initrd 演示（26M，仅生成不启动不引导；宿主缺 mkinitramfs 如实挂 needs_action exit 4）。ROOTFS 硬护栏拒 `/workspace` 与非 `/tmp` 路径；诚实边界写明「chroot 是验收环境非量子硬件」。lint-gate 白名单两处同步（外层 `scripts/check_shell_lint.sh` + `tests/test_lint_gate.py`），shellcheck 零告警。全链路实跑验证（stage1 python3.11.2 / stage2 通过 / stage3 26M initrd）。
  - **导入分析学习应用 batch-6：今日头条二十六篇全量只读核实（docs/77）**：按 docs/71/76 范本逐篇抓取分析。**有 counterpart 回填 7 条**——UltraVNC（remote_clients_docs：VNC/RFB 协议、Server/Viewer 双组件、GPL、AES/SecureVNC/MSRC4 加密分级、弱网自适应、安全模式远程）；aardio+DsoFramer（winternals_refs：references + items 各一条，COM/OLE 嵌入式 Office 控件机制，「快数十倍/96KB」报道口径挂 needs_verify）；B 码/PTP 变电站授时（chrono_theory_docs `power_grid_time_sync`：IRIG-B DC<1μs、IEEE 1588-2008 四步双向、C37.238-2017/61850-9-3:2016、BMCA、DL/T 1100.1-2018、BD 520002-2019、PTP 转 B 码混合架构——network_docs 已有 ntp/ptp 条目，本仓 chrono 侧补的是电力轮廓特有内容）；ipset+MQTT（network_docs：hash:net O(1)/restore 批量/timeout 自动解封/ipset-persistent/nftables 演进/200·2000 自查线；LWT/WillDelay<SessionExpiry/KeepAlive 1.5×/双向 Retain/单调序号/7200s vs NAT 5-10min）；REA（reverse_docs：MCP+Ghidra/Hopper/IDA+编码体重写、VLC 复刻实测口径、版权边界「功能复刻≠搬运源码」）。**无 counterpart 仅学习笔记**（守 #591 纪律）：HatchZip（→needs_action 候选 protec durability）、Ansible/数学软件（→toolchain_catalog 候选）、gpu-unlock（→hardware_kernel 候选）、DeepInfer（distcompute 无数据层）、GNSS 导航大模型（→#665 S2 候选）；其余纯技术篇（TabClustPFN/DigUp/LangGraph/Code Video Model/Harness²/ioDraw/agent.md/VBA 类模块/Snow Shot/Prometheus+nVisual/CAD 插件/Jev/Cua/涨星榜）入 docs/77 笔记。**落点**：docs/77 + 5 数据层 7 条回填 + `tests/test_winternals.py` 计数同步 12→13（items/REFS/doc_list/回链消息）+ aardio 官网入 OFFICIAL_DOMAINS 白名单 + README 本块 + 版本 0021→0022。**验证**：定向 test_winternals 19 passed、全量 pytest **1755 passed / 6 skipped 零回归**。

- **0000.0000.0000.0021.20261025（2026-10-25）**
  - **protec 新增轴8「ipv6：IPv6 与 ICMPv6 控制面」（42→53 概念、24→34 桥接）+ access 域补星闪 sparklink**：源自 docs/76 batch-5 只读导入中三篇有 counterpart 的文章（IPv6 全链路 / ICMPv6 / 星闪 3.0）。ipv6 域 10 概念——ipv6-base(RFC 8200)、icmpv6(RFC 4443)、ndp(RFC 4861)、slaac(RFC 4862+8981)、dhcpv6(RFC 8415)、pmtud(RFC 8201+4821)、nat64-dns64(RFC 6146/6147/6052)、6lowpan(RFC 4944/6282/6775)、send-cga(RFC 3971/3972)、mld(RFC 2710/3810)——各桥接 netsys 既有模块（network/osi/netauth/dhcp/nat/edge，netsys 侧零改动，netsys 桥接 10→20）；access 域补 sparklink（SLB/SLE/SLP/SLZ 四空口模式 + PQC/量子安全，无 netsys counterpart 故不设桥接）。needs_verify 6→8：星闪 15 项推荐性国家标准编号未在报道中列出、SEND 生态失效（RPN 392）为文章单方口径。RFC 编号已逐条独立核实（含 RFC 8981 废 RFC 4941、RFC 7113 RA-Guard 实施建议）。
  - **daoxue 方术层新增「zhen 阵」域（55→59 条目、方术桥接 13→18、总桥接 57→62）+ 桥接机制扩展支持 protec**：周天星斗大阵（365 星位环布/太阳太阴为枢 ↔ 一致性哈希环 + 多枢互备 + 虚拟节点均衡，桥 protec:consistent-hash 与 netsys:module:net-arch）、十二都天神煞大阵（十二祖巫各守一宫、缺一不可合则重构 ↔ M-of-N 门限 + 纠删重构 + 失效隔离，桥 protec:redundancy 与 netsys:module:distcompute）、分合转化（桥 netsys:module:meshnet）、河图洛书数理布局（图书学争议挂 needs_verify）；两阵为小说演绎非史实，各挂 needs_verify（方术 needs_verify 25→28）。子系统承接见 docs/50（数字矩阵冗余数据 + fail2ban 模式，均只读）——本轮只在其上做理念层翻译，不新增子系统。bridge_pools()/bridge_ok() 扩展 protec 概念池（concept: 前缀），构建期逐条校验无悬空。
  - **导入分析学习应用 batch-5：今日头条十三篇全量只读核实（docs/76）**：IPv6 全链路（部署链七环/运维链/安全链/FMEA 18 行/卡脖子五类/赛道六类/SEND 生态失效 RPN 392）、星闪 3.0（CEIC2026 峰会 2026-10-22~24 深圳发布 15 项推荐性国标 + SLZ 无源零功耗第四空口 + 毫米波/PQC/量子安全 + 60 余家单位参编蓝皮书）、ICMPv6（差错/信息两类、PMTUD、Echo 128/129、NDP 133-136、MLD）三篇有 counterpart 已回填 protec 概念；其余十篇——Jev（TypeSafe System One、Choice/Score/Noul 三原语、70-500ms、置信度门控）、novel-plus v6.2.0（RBAC/上下架/增量 SQL/密码重置警示）、网络共享（SMB 四链路、0x80070035/0x0000011b 排障、SMB1 风险）、Graphify（95 节点 229 边 0 token 建图、中文问句 0 结果、2581 token 超预算反例、社区聚类弱）、shuohao-skills（五段管线、52 道质量门）、MOSS-Image（5B DiT、4 天 130 万下载、LLTB 96.3%、JSON Layout、国产 PPU）、switch2 ounce-core（Rust 清洁室、Tegra T239、早期验证）、Filee（200+ 格式、Ctrl 拖拽圆环、离线免费）、Huashu-Report（数据表.json 数字锁源 + 编译反查 ↔ 本仓 live_user_face 构建期实测同构、规则函数化三层、渲染自检）、Docker Compose WeKnora（六步、三个想当然、失败三档、诚实边界）——本仓均无 counterpart，按 #591/docs/59 纪律**仅沉淀学习笔记、不新增概念**（netsys 无 SMB/NFS counterpart，SMB 篇不加概念）。
  - **落点**：docs/76 + research/protec + research/daoxue + concepts/protec.py/daoxue.py docstring 刷新 + gui.py show_protec docstring + 2 个 taxonomy JSON 重建 + 5 个内嵌 deno 版本 JSON 重建（protec/baigong/datong/sciences/zhuangzi）+ cnstd 数据层版本戳 + concept_gui.html 重烘焙（11 系统 / 66 边）+ README 本块与顶部 protec 表行刷新为真实口径 + 版本五处 0020→0021 + test_cnstd/test_protec/test_gui_protec/test_daoxue/test_gui_daoxue 计数断言同步（含新增 test_protec_ipv6_axis 门禁）。**验证**：全量 pytest **1755 passed / 6 skipped 零回归**（期间 2 个 GUI wiring 测试因前序测试污染 sys.modules 偶发失败，单独与文件级复跑均过、重跑全量全绿，属既有 flaky 非本轮引入）；protec/daoxue 构建 `--check` 全过（53 概念 / 34 桥接 / 59 方术条目 / 62 桥接无悬空）；`audit_concepts --strict` 归零；`gen_concept_gui.py --check` 同步；cli 128 / gui 112 实测。

- **0000.0000.0000.0019.20261025（2026-10-25）**
  - **概念系统补全收尾（protec + sciences 接入，十一系统成形）**：用户指令「材料学/热力学/气候学/环境学/物理/化学/生物等以及相关对产品长期运行和基本保护的协议和标准查看，并且尝试补全完善概念系统与整体」。把 S1/S2 两个概念系统完整接入——`protec`「产品保护」（28 概念 / 5 域 durability·electrical·environment·emergency·protection / 14 桥 / 7 原则 / 4 待核实）与 `sciences`「自然科学」（32 概念 / 8 域 materials·thermodynamics·climatology·environmental·physics·chemistry·biology·methodology / 18 桥 / 7 原则 / 3 待核实）：`cli.py` 加 `cmd_protec`/`cmd_sciences` 两子命令、`gui.py` 加「产品保护」「自然科学」两窗口与按钮、`concepts/__init__.py` 注册为第十/十一个系统（与 `ergonomics` 入口地图「概念与知识」场景同步）；四份新测试（test_protec/test_sciences/test_gui_protec/test_gui_sciences）含 `build_* --check` 断言；六个计数型 taxonomy JSON 重生成（cli 125→127 / gui 110→112 / datong `concept_systems` 9→11 改动态 `len(C.systems())`）；概念 id 全部统一 kebab-case（protec 13 个下划线 id、sciences 7 个引用同步改）消除 `audit_concepts --strict` 漂移；`concept_gui.html` 重烘焙（11 系统 / 65 边）。**导入分析学习应用**：LinkSwift（网盘直链下载助手，只读分析，docs/73）+ openKylin 软件包管理 SIG（gitee，docs/72）；均按 #591 纪律只沉淀学习笔记、不新增概念（本仓组网能力仅 IPMsg 文件通知、无字节下载引擎，LinkSwift 直链加速无 counterpart）。**落点**：research/protec + research/sciences + concepts/protec.py/sciences.py + 4 测试 + cli/gui/__init__/ergonomics + 6 taxonomy JSON + concept_gui.html + docs/72/73 + README 本块与顶部十一系统表 + 当前口径刷新 + 版本 0019 + HANDOFF。**验证**：全量 pytest **1738 passed / 6 skipped 零回归**；六构建 `--check` 全过；`audit_concepts --strict` 归零；cli 127 / gui 112 实测。
  - **版本号升一版（monorepo 里程表纪律，用户不看）**：整体包 `0000.0000.0000.0018.20261025` → `0000.0000.0000.0019.20261025`，同步 `version.py` / `pyproject.toml` / `console.ts` / `report_viewer.ts` + 五 taxonomy JSON（datong/baigong/zhuangzi/protec/sciences）的 deno 版本字段 + `comp_taxonomy.json` 与 `cnstd_domestic_standards.json` 版本串 + `tests/test_cnstd.py` 版本戳；0018 代码/数据层零残留（README 历史块不动）；六构建脚本重跑 + 双 HTML 生成器重生。

- **0000.0000.0000.0018.20261025（2026-10-25）**
  - **导入分析学习应用：Hermes 多项目只读分析（#607，五个同名项目全部核实）**：用户指令「导入分析学习应用 github/google-research2 、github/google-research，其实忘记仓库了，主要是Hermes或类似的英文；继续」。先联网核实：**`google-research2` 组织不存在（404）、`google-research` 组织内无任何 hermes 仓库**（monorepo 树亦无 hermes 路径）——用户仓库记忆有混淆；按「同名 Hermes」全网核实出**五个真实项目**（用户批复「都有，以防未来需要用，还要重新来过」），全部只读分析、**一律只沉淀学习笔记不新增概念**（本仓无网络观测 / RAG / Agent 运行时 / Lean 形式化 / 视频理解 counterpart，守 docs/59 #591 纪律）。**① `m-lab/hermes`**（ACM SIGCOMM 2026，DOI 10.1145/3789240.3829129；Columbia/LIX/Northeastern + Google 合作）：把 M-Lab NDT 公开测速聚合为「用户组」（源 AS × 都会区 × 站点）做统计退化检测（延迟显著性+效应量双门槛、吞吐 Wasserstein+Mann-Whitney），以**时间层析 + 相关层析**双法 + 双向路径定位网络实体，事件三级分类 **localized/ambiguous/unresolved**（报关联不报因果）；2024-08 起运行，公开 BigQuery 数据集（`events_enriched` 六类记录、列名即契约）+ 仪表盘 hermes-dashboard.org；Docker 一体化管道默认跑最近 2 天（每日 cron 设计）；评测：5 个月 40 亿次测试、166 国 65,000 事件、仅 5.2% 被其他公共观测台捕获、11× 于对比观测台的公开讨论事件、Blame-IT 重实现检出 91.4%/片段一致 94.5%。**② `S4AI-CornellTech/Hermes`**（ISCA 2025，MIT）：RAG 算法-系统协同设计——层次化搜索簇跨机 + 两阶段检索（sample-nprobe 8 → deep-nprobe 128）+ DVFS 延迟-能耗平衡；栈 faiss-gpu 1.8.0/vLLM/PyTorch CUDA 11 + Intel RAPL/perf stat 能耗实测；数据 SPHERE_899M/100M/100K + TriviaQA，模型 GEMMA-2 9B/BGE-Large。**③ `nousresearch/hermes-agent`**（257k stars，MIT）：开源 AI Agent「The agent that grows with you」——official/labs/example 三层插件生态 + 六个记忆提供器独立插件 + DSPy+GEPA 自我进化 + toolperf 工具 A/B 评估 + compression-eval 上下文压缩离线评估。**④ `aziksh-ospanov/HERMES`**（arXiv 2511.18760，MIT）：Lean 4 单步形式化验证器——对 LangGraph agent 暴露唯一工具 `verify_one_mathematical_step`，证明步骤自动形式化后返回 **CORRECT/INCORRECT/VERIFICATION FAILURE** 三值，幻觉在传播前拦截；prover 改编自 Goedel-Prover-V2。**⑤ `haowei-freesky/HERMES`**（ACL 2026，arXiv 2601.14724）：KV Cache 即层次化记忆的流式视频理解（LLaVA-OneVision/Qwen2.5-VL，kv_size 6000 预算硬参数化，基于 ReKV）。**可复用纪律**（仅纪律层面）：公开可复现的测量（每步输入输出落公开数据）、三值诚实分级、限额显式配置、评估框架先于能力宣称、列名即契约。**落点**：docs/70 + README 本块 + 当前口径五处刷新 + 版本 0017 + HANDOFF §29（第二十一轮）。**验证**：全量 pytest 零回归（基线 1704 passed / 5 skipped）；needs_verify 挂牌：各项目 star 数（257k vs 报道 14 万翻倍）、venue（arXiv vs ICML 2026 页称）、许可条款、论文指标均未独立复核。
  - **版本号升一版（monorepo 里程表纪律，用户不看）**：整体包 `0000.0000.0000.0016.20261025` → `0000.0000.0000.0018.20261025`，同步 `version.py` / `pyproject.toml` / `main.go` / `console.ts` / `report_viewer.ts` + 三 taxonomy JSON 的 deno 版本字段 + `comp_taxonomy.json` 与 `research/comp/build_comp.py` odometer 串 + `toolchain_catalog.json` 三处 + 三测试 docstring 戳；0016 代码/数据层零残留（README 历史块不动）；四构建脚本重跑 + 双 HTML 生成器重生。

- **0000.0000.0000.0016.20261025（2026-10-25）**
  - **可持续方向收尾②——lint-gate 落地（shellcheck 一环，#652/#653）**：把 #598 轮以来挂账的「lint 宿主可用、CI 未落地」推进到收尾。① **`scripts/check_shell_lint.sh` 白名单门禁**（外层仓根）：lint 本仓自有 **11 个 .sh**（classics 六构建脚本 + 内层 `tools/bootstrap.sh`/`tools/disposable-env.sh`/`Windows/build.sh`/`Windows/push-to-github.sh` + 门禁脚本自身），显式排除 **quantum-kernel 上游 Linux 6.18.57 内核源码树**与 **plang 语法样例**；附**防漏网全仓扫描**——新增 .sh 不入册即红；默认严重级别（含 note/style）零告警才算过；宿主 shellcheck 缺席时如实 SKIP 并明示。② **`.github/workflows/lint-shell.yml` 接入 CI**：先 apt 安装 shellcheck 再跑门禁脚本（本地 SKIP 语义不适用于 CI，由安装步兜底），paths 触发 `**/*.sh` + 门禁脚本自身。③ **`system-optimizer/tests/test_lint_gate.py` 7 项守卫**：脚本存在可执行 / 白名单与 EXPECTED 一致 / 双向契约（无漏网且无失效条目，rogue 文件冒烟实测拦截）/ 排除口径非空转（内核树与样例真实存在）/ workflow 引用脚本且含安装步 / hadolint·actionlint 未接入防伪断言 / 实跑 PASS-or-SKIP。④ **修复既有 5 处 shellcheck 告警**（`classics-linux/build-arch.sh` SC2015+SC2012、`classics-linux/build-mobile.sh` SC2015+SC2086、`Windows/push-to-github.sh` SC2164）——本仓自有 .sh 现全零告警。⑤ **文档销项**：comp `lint-gate` 概念「未落地」→**「部分落地」**（shellcheck 一环落地，hadolint/actionlint 宿主缺席如实挂 needs_action——`build_comp.py` detail/落法/桥接三处改 + `comp_taxonomy.json` 重建）；`toolchain_catalog.json` ci-workflows 实数刷新 **2→9**（外层 7 + 内层 1 + Windows 1，find 实证）；`docs/57` §2.13 同口径刷新（旧「全仓仅 2 个 workflow」为 #652 前状态，HANDOFF 当轮如实更正、历史原文不动）。**落点**：scripts/ 门禁 + workflow + 7 项守卫测试 + 三脚本修复 + comp 概念 + catalog + docs/57 + README 本块 + 当前口径五处刷新 + 版本 0016 + HANDOFF §28（第二十轮）。**验证**：shellcheck 全零告警、门禁脚本 `[PASS]`、守卫 7/7（含 rogue 冒烟）、四构建 `--check` 全过、全量 pytest **1704 passed / 5 skipped 零回归**（基线 1697 +7 新守卫）。
  - **版本号升一版（monorepo 里程表纪律，用户不看）**：整体包 `0000.0000.0000.0015.20261025` → `0000.0000.0000.0016.20261025`，同步 `version.py` / `pyproject.toml` / `main.go` / `console.ts` / `report_viewer.ts`（含头注释与 DEMO schema 串）+ 三 taxonomy JSON 的 `deno_console_version`/`deno_report_viewer_version` + `comp_taxonomy.json` 与 `research/comp/build_comp.py` 的 odometer-versioning 版本串 + `toolchain_catalog.json` 三处 + `tests/test_toolchain.py` / `tests/test_a11y_operable.py` docstring 版本戳（上轮 a11y 测试 docstring 日期笔误 0015.20261024 一并校正）；0015 代码/数据层零残留（README 历史块不动）；四构建脚本重跑 + 双 HTML 生成器重生。

- **0000.0000.0000.0015.20261025（2026-10-25）**
  - **前端运动/肢体无障碍差距补齐收尾（#605，docs/66 §六清单全部销项）**：把 #598 轮登记的 WCAG 2.2 Operable 差距清单**推进到收尾**——① `concept_gui.html`：全局 `:focus-visible{outline:2px solid var(--acc)}` 兜底（含 `g[tabindex]:focus-visible` 与 `.mx td.cell:focus-visible`，2.4.7）；`.btn` 显式 `min-width:24px;min-height:24px`（2.5.8）；SVG 中心圆 + 9 系统节点经 el() 置 `tabindex="0"`/`role="button"`/`aria-label` 并挂 Enter/Space 键控（2.1.1）；矩阵有数格 `tabindex='0' role='button'` + aria-label + 键控（0 值格保持纯展示）；`<header>` + `<main id="main">` landmark + 屏外 skip link（2.4.1）。② `report_viewer.html`：全局 `:focus-visible` 兜底、`.btn` 24px、header/main landmark + skip link；指针取消经 `click` 事件模型天然满足（2.5.2）。③ **修复一处既有源码 bug**：`report_viewer.ts` page() 反引号模板中 base64url 替换行写 `\/`/`\+`，按模板字符串语义产出 `/`/`+`（无效正则 + 行注释），导致**整块内联 script 语法错误、页面全部 JS 功能瘫痪**（自诞生起存在，历轮字节模式测试未覆盖）；改双重转义 `\\/`/`\\+` 后重生。④ 固化门禁 `tests/test_a11y_operable.py`（12 项）：契约模式静态断言（focus-visible/24px/tabindex/role/aria-label/skip link/landmark/keydown）+ 生成器源码防回退 + `node --check` 内联 JS 语法门禁（node 缺席跳过）。⑤ docs/66 §六 差距清单**全部销项**（2.5.7 无拖拽操作自然满足、2.5.2 click 模型天然满足如实登记）、§九 验证方法补 JS 语法门禁、基线计数刷新。**落点**：docs/66 销项 + 双生成器改造 + 双 HTML 重生 + 新测试 + README 本块 + 当前口径五处刷新 + 版本 0015 + HANDOFF §27（第十九轮）。**验证**：`node --check` 双页通过、`test_a11y_operable` 12 passed、定向 `test_concept_gui` 7 passed、双 HTML `--check` 同步（concept_gui data-sha256 2bd250ca0916 因版本串入 payload 而变、数据语义不变）、四构建 `--check` 全过、全量 pytest 1697 passed / 5 skipped 零回归（基线 1685 +12 新门禁）。
  - **版本号升一版（monorepo 里程表纪律，用户不看）**：整体包 `0000.0000.0000.0014.20261024` → `0000.0000.0000.0015.20261025`，二十处同步（`version.py` / `pyproject.toml` / `main.go` / `console.ts` / `report_viewer.ts` 含头注释与 DEMO schema 串 + 三 taxonomy JSON 的 `deno_console_version`/`deno_report_viewer_version` + `comp_taxonomy.json` 与 `research/comp/build_comp.py` 的 odometer-versioning 版本串 + `toolchain_catalog.json` 三处 + `tests/test_toolchain.py` docstring 版本戳）+ 新测试 docstring 戳；0014 代码/数据层零残留（README 历史块不动）；四构建脚本重跑 + 双 HTML 生成器重生。

- **0000.0000.0000.0014.20261024（2026-10-24）**
  - **导入分析学习应用：WorkBuddy 瘦身加速（workbuddy-slim）+ OpenSpeedy（#604，两个资源均只读分析）**：用户指令「导入分析学习应用【WorkBuddy干活变慢还费token，一招教你瘦身加速】点击链接打开👉 https://m.toutiao.com/is/iLkStvDzpxY/ …… 、openspeedy」。**① 头条文章**（作者马佳彬，公众号「马佳彬」经「人人都是产品经理」账号发布）：WorkBuddy 变慢费 token 的根因是 **Skill / MCP / 记忆 / Agent 规则滚雪球式膨胀**，每轮任务全量塞入上下文；**长会话（几十甚至上百轮）即使有自动压缩上下文仍爆炸**；**模型积分倍率差异大**（同任务 DeepSeek-V4.1-Flash 约十几积分 vs MiniMax-M3 暴涨十倍，文章单方陈述 needs_verify）；**缓存命中率取决于前缀稳定性与任务类型**。解法为开源 Skill **`workbuddy-slim`**（github.com/majiabin2020/workbuddy-slim/），**只诊断不删除**——诊断四维度（**规则膨胀 / 记忆超限 / 技能与连接器堆积 / 会话卫生**）、输出**红黄绿体检报告**（红=严重、黄=中等、绿=健康）、**用户逐项确认后非破坏性执行**；安装提示词「安装这个skill：github.com/majiabin2020/workbuddy-slim/」，触发语「给我的WorkBuddy做个体检」；样例报告 56 个技能 40 个踩红线、官方建议启用工具**不超过 80 个**、MEMORY.md 内容过多可**蒸馏压缩**（均为文章口径 needs_verify）。**② OpenSpeedy**（`github.com/game1024/OpenSpeedy`，GPL v3，v3.3.17）：开源游戏变速器「The Best Open-Source Game Speed Controller」，**Ring-3 用户态 Hook 无内核侵入**，基于 **MinHook** Hook 十个 Windows 时间 API（Sleep/SetTimer→user32.dll；timeGetTime→winmm.dll；GetTickCount/GetTickCount64/QueryPerformanceCounter/GetSystemTimeAsFileTime/GetSystemTimePreciseAsFileTime/SetWaitableTimer/SetWaitableTimerEx→kernel32.dll）；技术栈 **C/C++（speedpatch DLL）+ Rust（Tauri 后端）+ TypeScript/JavaScript（Vite 前端）**，UI 用 MUI + Ant Design splitter，构建 `npm run tauri dev`（依赖 Node.js 18+/CMake/VS C++ 工作负载）；平台 Windows 10+（x86/x64）；安装三途径（winget `--id Game1024.OpenSpeedy --exact --source winget` / Releases 手装 / Steam app 5010920）；工程亮点为**防御式失败处理**（提交 `fix: remove VC++ redist dependency and stop MH hook failures crashing…`，2026-09-24——Hook 失败不崩目标进程）与 **winget 同名包匹配冲突修复**（`docs: 修正 winget 同名包匹配冲突 (#300)`，2026-10-21）；README 五条风险警示前置（仅教育研究用途 / 反作弊封号风险 / 超速物理引擎崩溃 / 无数字签名杀软误报）。**边界分级**：本仓无 Skill/MCP 体检 counterpart、无 Ring-3 hook / 游戏变速 counterpart（全仓 grep 仅 GetTickCount64 等三处 API 可用性版本编目命中，无任何 hook/注入/变速实装），按 #591/docs/59 先例**一律只沉淀学习笔记、不新增概念**；可复用纪律（仅纪律层面）：上下文预算体检四维度 ↔ 本仓 audit --strict / omni gaps 归零；红黄绿分级 + 逐项确认后非破坏性执行 ↔ 本仓 opt-in 写入类「选择+确认」先例；前缀稳定性即成本 ↔ 双 HTML 生成器重生 `--check` 防漂移；Hook 面完整性矩阵 ↔ 本仓 windows-api-version-matrix「语义面↔全量 API 清单↔版本下限」编目；混合工具链单仓集成 ↔ 本仓多语言四入口分层接线；防御式失败处理 ↔ native 探针失败降级不炸主流程；README 风险披露 ↔ 「先划边界再讲能力」；包标识唯一性对账 ↔ toolchain_catalog 安装命令逐条核验（#603）。**诚实边界**：文章系第三方转述、workbuddy-slim 仓库本体未直接抓取（56/40、≤80、积分倍率均 needs_verify）；OpenSpeedy 页面未呈现 star/fork 计数（needs_verify）；GPL v3 代码不复制不链接不移植。**落点**：新增 `docs/69_导入分析学习应用-workbuddy瘦身加速与openspeedy.md` 学习笔记 + README 本块 + **0012 块头缺陷修复**（上一轮 0013 块吞并 0012 块内容的遗留，0011→0012 bump 与 aurora bullet 归位）+ 当前口径版本引用五处刷新为 0014 + HANDOFF §26（第十八轮）落账。**验证**：定向 `test_toolchain` / `test_comp` / `test_concept_gui` / `test_concepts_center` / `test_version` 校验通过、双 HTML `--check` 同步、`build_comp.py --check` 无漂移、全量 pytest 零回归（基线 1685 passed / 5 skipped）；未改任何概念数据语义，不影响九概念系统拓扑与桥接。
  - **版本号升一版（monorepo 里程表纪律，用户不看）**：整体包 `0000.0000.0000.0013.20261024` → `0000.0000.0000.0014.20261024`，二十处同步（`version.py` / `pyproject.toml` / `main.go` / `console.ts` / `report_viewer.ts` 含头注释与 DEMO schema 串 + 三 taxonomy JSON 的 `deno_console_version`/`deno_report_viewer_version` + `comp_taxonomy.json` 与 `research/comp/build_comp.py` 的 odometer-versioning 版本串 + `toolchain_catalog.json` 三处 + `tests/test_toolchain.py` docstring 版本戳）；仅升 D 段、日期后缀不变。**验证**：全量 pytest 零回归（1685 passed / 5 skipped）、双 HTML `--check` 同步、`build_comp.py --check` 无漂移。

- **0000.0000.0000.0013.20261024（2026-10-24）**
  - **toolchain 子系统完善补全优化（#603，用户指令「各工具链完善补全优化」）**：宿主实装而未编目的工具链全部入册——**catalog 类别 7→10**（新增 vcs-network 版本控制与网络 / container 容器 / media 媒体）、**宿主工具链 23→42 条**（+19：git/http-clients/rsync/openssl/ssh/compression-suite/docker/ffmpeg/chrome/editor-suite/terminal-mux/binary-inspect/autotools-suite/debug-trace/lint-format/build-extra/text-data-utils/perl/tcl）、**仓库工具软件 11→14 条**（+3：docker-support——Dockerfile+compose 真实 counterpart；ci-workflows——全仓 workflow 实数 2 个；repo-guard——check_repo_guard.py+测试）、修 sysweeper/syspkg 陈旧版本串 0004→0013。
  - **上游新鲜度 16 项逐项联网核实**（needs_action 11→27，全部带上游版本/发布日期/处置）：安全相关优先——OpenSSL 3.0.13（3.0 系 2026-09-07 EOL，迁 LTS 3.5.9）、curl 8.5.0（上游 8.23.0，8.22.0 一轮 10 CVE）、Chrome 144（落后 8 大版本多轮 High CVE）、Docker 27.5.1（上游 29.9.1）、git 2.43.0、Perl 5.38.2（安全补丁 2026-07-02 止）、jq 1.7（1.8.2 修 17 CVE）；次轮 vim/nvim/emacs/meson/ninja/scons/tmux/tcl/ffmpeg 逐一取上游版本；tmux 发布日期两源不一如实标 needs_verify。
  - **探针层优化**（`native/toolchain.py`）：HOST_PROBES 19→39 项 + 3 项绝对路径回退，对 catalog 宿主条目 **42/42 全覆盖**；版本旗标按上游口径特例化（openssl/go 用 `version`、ssh/tmux 用 `-V`、perl 用 `-v`、ffmpeg 用 `-version`、tclsh 走 stdin 读 `$tcl_version`）；小结行加在位/缺席/覆盖率统计；新增两条回归守卫测试（探针覆盖 catalog、旗标对齐探针）。本机实录：在位 41 项 / 缺席 1 项（osxcross 未安装，与 catalog 口径一致）。
  - **comp 概念系统构建域补三概念**（83→86、桥接 96→98）：`scons`（Python 驱动构建，宿主 4.5.2 vs 上游 4.11.1 记 needs_action）、`container-toolchain`（Dockerfile 多阶段 + compose 最小权限，桥 datong 一体两面）、`lint-gate`（clang-format/clang-tidy/shellcheck 宿主可用但 **CI 未接入——如实登记未落地**，桥 daoxue 知止知足）；连带修订 `artifact-container` 陈旧「未落地」记述与 `odometer-versioning` 的陈旧版本串；docs/57 全文计数刷新（42/14/10 类别、27+4 新鲜度两栏、新增 §1.5–1.10 与 §2.12–2.14）。
  - **红线守住**：toolchain 源码零写路径（禁 `curl `/`wget ` 等执行路径字样，测试断言通过）；catalog 只读编目不构建不拉取；lint-gate 不把宿主可用写成 CI 已接入。
  - **版本号升一版（monorepo 里程表纪律，用户不看）**：整体包 `0000.0000.0000.0012.20261024` → `0000.0000.0000.0013.20261024`，五处同步（`version.py` / `pyproject.toml` / `main.go` / `console.ts` / `report_viewer.ts`）+ 三 taxonomy JSON + catalog 两处版本串；仅升 D 段、日期后缀不变。**验证**：全量 pytest 零回归（1685 passed / 5 skipped）、双 HTML `--check` 同步、`build_comp.py --check` 无漂移。

- **0000.0000.0000.0012.20261024（2026-10-24）**
  - **版本号升一版（monorepo 里程表纪律，用户不看）**：整体包 `0000.0000.0000.0011.20261024` → `0000.0000.0000.0012.20261024`，五处同步（`version.py` / `pyproject.toml` / `main.go` / `console.ts` / `report_viewer.ts`，含头注释与 DEMO schema 串）+ 三 taxonomy JSON（`baigong`/`datong`/`zhuangzi` 的 `deno_console_version`/`deno_report_viewer_version`）；仅升计数段 D（0011→0012）、日期后缀 `20261024` 不变（同一天定版）。
  - **第五仓库只读导入分析：aurora-silicon/mesa（#602）**：用户指令「导入分析学习应用 https://github.com/aurora-silicon/mesa」。该仓为 freedesktop Mesa 3D 图形库的 **stock mirror**（默认分支 `aurora-wip`，231,027 commits，技术栈 C + Meson + Ninja + Vulkan + 多 GPU 后端），组织 aurora-silicon 自述「New light for Apple Silicon」。**只读 WebFetch 分析，不克隆不安装不构建不复制代码**；本仓无图形栈 / GPU 驱动 counterpart，守 #591/docs/59 先例**只沉淀学习笔记、不新增概念**。可复用工程纪律：① **上游归因署名链**（提交带 `Part-of: <gitlab.freedesktop.org/mesa/mesa/-/merge_requests/XXXX>` 上游 MR 归因标签，衍生仓库不吞没上游贡献）；② **权威源声明**（README 明言上游在 gitlab、其他仓库「not supported」——先声明权威源再谈衍生，同构本仓「先划边界再讲能力」）；③ **stock mirror + wip 分支工作流**（分支名自含 wip 性质，衍生与实验分层命名）；④ **LLM 辅助署名透明**（`Assisted-by: LLM` / `Co-Authored-By: Claude Opus 5.5`，AI 辅助产出在版本历史中署名可见）；⑤ **可复现构建即文档**（Meson/Ninja 三段标准命令 + 上游 install/meson 文档索引，同构本仓构建脚本 `--check` 防漂移）；⑥ **平台使能分层**（bootloader m1n1 → 内核 linux → 驱动 → 发行版集成 nixos-aurora/fedora-aurora，同构本仓 native/tasks/data/四入口分层）。**诚实边界**：star/fork 页面未呈现（组织页曾显示 2★/4 forks 与 2★/10 forks 两个不一致值，均标 `needs_verify` 不取单一值）；LICENSE 未在页面呈现（上游 Mesa 为 MIT，本 mirror 许可不据上游推定，`needs_verify`）；底层 GPU 驱动代码（C/内核态交互）不可复用；`aurora-wip` 为实验性 WIP 分支不跟踪不合并。**落点**：docs/68 学习笔记 + README 本块 + 当前口径版本引用刷新为 0012 + HANDOFF §24（第十六轮）落账。**验证**：定向 `test_concept_gui` / `test_version` 校验通过、双 HTML `--check` 同步、全量 pytest 零回归（基线 1683 passed / 5 skipped）；未改任何概念数据语义，不影响九概念系统拓扑与桥接。

- **0000.0000.0000.0011.20261024（2026-10-24）**
  - **版本号升一版（monorepo 里程表纪律，用户不看）**：整体包 `0000.0000.0000.0010.20261024` → `0000.0000.0000.0011.20261024`，五处同步（`version.py` / `pyproject.toml` / `main.go` / `console.ts` / `report_viewer.ts`，含头注释与 DEMO schema 串）+ 三 taxonomy JSON（`baigong`/`datong`/`zhuangzi` 的 `deno_console_version`/`deno_report_viewer_version`）；仅升计数段 D（0010→0011）、日期后缀 `20261024` 不变（同一天定版）。
  - **「育」义补全轮（#601，全仓「都改动」）**：用户对「德育体知（智）美劳」中的**「育」**给出完整释义并要求全仓框架表述据此补全——「育」具体所指为**北京师范大学**（中国师范教育最高学府，校训「学为人师，行为世范」），即**教书育人**的制度化载体；教学法为**言传身教**（以言行示范为教，不只以知识传授为教）；内容为**诗书礼易**（《诗经》《尚书》《礼记》《周易》——诗言志、书载道、礼立范、易明变）；立场代表**国家民族**（「师者，所以传道受业解惑也」，道统与民族文化之传承），**不是社会组织、不是企业**（绝不以商业组织逻辑办教育、绝不以营利 / KPI 逻辑办育人）。**落点**：HANDOFF §12 框架释义块补全（六字逐一释义，「育」为教育之体、全套框架的承载）+ 十个映射表（§12.5–§21.6）标题下统一补 compact「育」义注 + §23（第十五轮）落账；README 加本块 + 当前口径版本引用刷新为 0011；memory 补「育」义。**验证**：定向 `test_concept_gui` / `test_version` 校验通过、双 HTML `--check` 同步、全量 pytest 零回归（基线 1683 passed / 5 skipped）；未改任何概念数据语义，不影响九概念系统拓扑与桥接。

- **0000.0000.0000.0010.20261024（2026-10-24）**
  - **版本号升一版（monorepo 里程表纪律，用户不看）**：整体包 `0000.0000.0000.0009.20261024` → `0000.0000.0000.0010.20261024`，五处同步（`version.py` / `pyproject.toml` / `main.go` / `console.ts` / `report_viewer.ts`，含头注释与 DEMO schema 串）+ 三 taxonomy JSON（`baigong`/`datong`/`zhuangzi` 的 `deno_console_version`/`deno_report_viewer_version`）；仅升计数段 D（0009→0010）、日期后缀 `20261024` 不变（同一天定版）。
  - **用户原话纠正轮：「德育体知（智）美劳」写法改回（#600）**：用户指出 HANDOFF §12 起的「德智体美劳全面发展（先天道体）」维度映射框架是我对用户原始命题的**转写**，而用户原话（HANDOFF §12 引用块所录）为「**德育体知（智）美劳**全面发展，做素质新人（先天道体）」——该写法源自用户所读民办学校，「必须改回来」。本轮把全仓 12 处转写版（HANDOFF 11 处：§12 转述句 + §12.5/§13.5/§14.5/§15.5/§16.4/§17.5/§18.5/§19.5/§20.6/§21.6 十个映射表标题；README 版本更新区 1 处历史引用）全部改回用户原话「德育体知（智）美劳全面发展（先天道体）」，改后全仓「德智体美劳」零残留；用户命题引用块（原话）保持不动。**落点**：HANDOFF + README 文字纠正；README 加本块 + 当前口径版本引用刷新为 0010；HANDOFF §22（第十四轮）落账。**验证**：定向 `test_concept_gui` / `test_version` 校验通过、双 HTML `--check` 同步、全量 pytest 零回归（基线 1683 passed / 5 skipped）；未改任何概念数据语义，不影响九概念系统拓扑与桥接。

- **0000.0000.0000.0009.20261024（2026-10-24）**
  - **版本号升一版（monorepo 里程表纪律，用户不看）**：整体包 `0000.0000.0000.0008.20261024` → `0000.0000.0000.0009.20261024`，五处同步（`version.py` / `pyproject.toml` / `main.go` / `console.ts` / `report_viewer.ts`，含头注释与 DEMO schema 串）+ 三 taxonomy JSON（`baigong`/`datong`/`zhuangzi` 的 `deno_console_version`/`deno_report_viewer_version`）；仅升计数段 D（0008→0009）、日期后缀 `20261024` 不变（同一天定版）。
  - **导入分析学习应用四仓库：cleanyourtv / Gathin23 / tv-detox / sony-a7iv-feature-research（#599，只读 + 边界分级）**：用户指令导入分析四个外部 GitHub 仓库——① `Gathin23/cleanyourtv`（MIT，Android/Google TV 无线 debloat + Apple TV 风格启动器：Wi-Fi ADB `pm disable-user` 不 root 不卸载一行还原、497 KB 纯 Java launcher 无网络权限无后台服务、29.6k★/3.4k fork/380+ 贡献者/840+ merged PR、社区实测 260 TV 型号·77 品牌·25 语言、Python 工具链 tv.py/b64push.py/relay.py/check.py/privacy.py）；② `Gathin23` 用户主页（Gathin，Sr. DevRel Lead @0G onchain AI，India；起源故事：父母电视开屏广告 → Claude Code 一周做出 29.6k★ 项目，2026-10 单月 6 仓 1,195 commits）；③ `Ansub/tv-detox`（MIT，AI 驱动 debloat：`candidates.sh` 只读分 never/keep/safe/review 四档、v1.4.1 起默认保留 Google TV 主屏幕的 fail-safe 演进、GitHub Actions + ShellCheck + 模拟器 smoke test、诚实登记 undo.sh 不撤销项）；④ `leogenot/sony-a7iv-feature-research`（A7 IV 固件 6.02 研究：证据分级状态表 Verified/gated/unresolved/product-excluded/untested、仓内零固件零密钥零备份零序列号的干净分发、单属性隔离实验法、1,064 更新包文件独立哈希匹配、上游归因 PMCA-RE/fwtool.py a7iv 分支）。**边界分级**：四仓均无可直接编目为「本仓自研工具」的工程落点（本仓无 Android TV debloat 子系统 / 无相机固件研究面），按 #591 先例（docs/59）**一律只沉淀为学习笔记、不新增概念**；TV debloat 的 ADB 5555 明文端口与恢复出厂风险**只登记不采纳**，相机固件纪律只学习不复现。**落点**：新增 `docs/67_导入分析学习应用-cleanyourtv-tv-detox-sony-a7iv四仓库.md`（四仓概览与可复用点表 + 边界分级与诚实边界 + 分仓学习笔记 + 落点清单）；README 加本块 + 子系统 deno 版本引用刷新为 0009；HANDOFF §21（第十三轮）落账。**验证**：定向 `test_concept_gui` / `test_version` 校验通过、双 HTML `--check` 同步、全量 pytest 零回归（基线 1683 passed / 5 skipped）；未改任何概念数据语义，不影响九概念系统拓扑与桥接。

- **0000.0000.0000.0008.20261024（2026-10-24）**
  - **版本号升一版（monorepo 里程表纪律，用户不看）**：整体包 `0000.0000.0000.0008.20261024` → `0000.0000.0000.0008.20261024`，五处同步（`version.py` / `pyproject.toml` / `main.go` / `console.ts` / `report_viewer.ts`，含头注释与 DEMO schema 串）+ 三 taxonomy JSON（`baigong`/`datong`/`zhuangzi` 的 `deno_console_version`/`deno_report_viewer_version`）；仅升计数段 D（0007→0008）、日期后缀 `20261024` 不变（同一天定版）。
  - **肢体残疾 / 辅助设备设施 / 外部设备设施 / 义肢 / 器官脏腑 协议标准查据（#598，只读 + WCAG Operable 契约）**：在 #597（docs/60–64 Web 视觉健康与无障碍查据全集收口）基础上，继续查据**肢体残疾辅助设备 · 外部辅助设备 · 义肢（假肢）· 器官脏腑相关器械**一脉标准——① 辅助产品总纲：ISO 9999:2022（Ed.7，三层三级编码、ICF 全对齐、约 948 条目、删 Class 05 剩 10 大类；**明确排除植入设备**，即「外部/辅助设备」与「植入/器官脏腑器械」的标准原文分界）；② 轮椅/移动：ISO 7176 系列（-2/-5/-8/-11/-16/-19/-28）、ISO 10542（WTORS 车辆约束）、ISO 10865-1/-2、ISO 16840（-4 界面压力峰值 ≤40 kPa/平均 ≤15 kPa 防褥疮）、ISO 11199（助行器）；③ 建筑无障碍：ISO 21542:2021（轮椅足迹 800×1300 mm、坡道 max 1:12 推荐 1:20、路径宽 ≥1800/1200 mm、回转直径 ≥1500 mm、Michelson 对比 ≥30%/60%、照度 20–500 lx 分级）、ISO 23599:2019（TWSI 触觉地面）、EN 17210、GB 50763-2012、GB 55019-2021（全文强制，2022-04-01 施行）、《无障碍环境建设法》（2023-09-01 施行）；④ 义肢/矫形：ISO 8549-1（词汇）、ISO 10328:2016（下肢假肢结构测试，静力+循环，evidence/ultimate/fatigue 三级强度）、ISO 22523、ISO 22675、ISO 15032、ISO 13405-1/-2/-3（2024 新版）、ISO 8551:2020；⑤ 器官脏腑/植入与器官支持器械：ISO 14708 七部分（-1 通用/-2 起搏器/-3 神经刺激/-4 输液泵/-5 循环支持/-6 除颤/-7 人工耳蜗）、ISO 5840 三部分（心脏瓣膜）、ISO 22442-1/-2/-3、ISO 7198:2016（血管移植物）、ISO 7197（脑积水分流）、ISO 14607（乳房植入）、ISO 14630（非有源外科植入通用）、IEC 60601 系列、ISO 13485:2016（QMS）、ISO 14971:2019（风险管理）、IEC 62366-1:2015+A1:2020（人因/可用性，docs/63 已同引）、IEC 62304:2015（医疗软件 A/B/C 三级）、ISO 10993 系列（生物评价）。**层归属判定**：以上全部判为**物理/硬件/医学/工程参考层**，不冒充为本仓 Web 前端职责或任何器械/建筑/临床能力；该脉**唯一 Web 落点 = WCAG 2.2 Operable 原则（2.1 键盘可达/无陷阱、2.2 时间可调/可暂停、2.4 焦点可见/不被遮挡、2.5 输入模态含 2.5.7 拖拽替代与 2.5.8 目标尺寸 ≥24×24 CSS px）**，服务肢体残疾与精细运动障碍用户的替代输入与可达操作。**落点**：新增 `docs/65_肢体残疾辅助设备义肢器官脏腑协议标准查据.md`（五标准族查据 + 层归属判定 + 诚实边界）、新增 `docs/66_前端运动肢体无障碍规范（WCAG_Operable_落地）.md`（Operable 全套前端契约 + 两 HTML 现状差距清单实测登记 + PR 前自检 14 项）、docs/64 索引扩为七份文档（新增 §三 16 行 Operable 条目、§四诚实边界第 11–12 条、§五点五 #598 opt-in 对账）；双 HTML 因版本串重生、`--check` 同步。**验证**：`test_version.py` 动态读 `PACKAGE_VERSION`、定向 `test_concept_gui` / `test_version` 校验通过（18 passed）、双 HTML `--check` 通过、全量 pytest 零回归（基线 1683 passed / 5 skipped）；未改任何概念数据语义，不影响九概念系统拓扑与桥接。

- **0000.0000.0000.0008.20261024（2026-10-24）**
  - **版本号升一版（monorepo 里程表纪律，用户不看）**：整体包 `0000.0000.0000.0006.20261024` → `0000.0000.0000.0008.20261024`，五处同步（`version.py` / `pyproject.toml` / `main.go` / `console.ts` / `report_viewer.ts`，含头注释与 DEMO schema 串）+ 三 taxonomy JSON（`baigong`/`datong`/`zhuangzi` 的 `deno_console_version`/`deno_report_viewer_version`）；仅升计数段 D（0006→0007）、日期后缀 `20261024` 不变（同一天定版）。
  - **Web 视觉健康与无障碍查据收尾轮（#597，干净收口 docs/63 §六 opt-in 1–4）**：在 #596（docs/63 离子态/听力/五感/幻觉查据）基础上，把 docs/63 §六列出的 4 项 opt-in 待办全部执行——① docs/61 减动效节**扩写** WCAG 2.3.1 光敏癫痫硬约束（≤3 闪/秒、一般闪光阈值 20.0 cd/m² / 红色闪光阈值 6.0 cd/m²、PEAT/G19、2.3.2 红线），纳入 PR 前自检清单；② concept_gui.html「标准依据」卡补一列「听觉/多感官/光敏（生理·Web 参考层）」科普（呼应圆光术多感官与光主题，不冒充 Web 职责）；③ 评估本仓前端：当前无音视频/自动音频，故 WCAG 1.2.x / 1.4.2 / 1.4.7 **暂不适用**，留作契约基线（docs/61 §八第 6 条 + PR 前自检新增项）；④ 新建 `docs/64_Web视觉健康与无障碍查据全集索引.md` 串联 docs/60/61/62/63，统一层归属口径、穷举 Web 可落地项与诚实边界。**落点**：docs/61 扩写、gen_concept_gui.py TEMPLATE 改卡并重生 concept_gui.html（data-sha256 同步）、新增 docs/64；双 HTML 因版本串重生、`--check` 同步。**验证**：`test_version.py` 动态读 `PACKAGE_VERSION`、定向 `test_concept_gui` / `test_repo_guard` 校验通过、全量 pytest 零回归（基线 1683 passed / 5 skipped）；未改任何概念数据语义，不影响九概念系统拓扑与桥接。

- **0000.0000.0000.0006.20261024（2026-10-24）**
  - **版本号升一版（monorepo 里程表纪律，用户不看）**：整体包 `0000.0000.0000.0005.20261024` → `0000.0000.0000.0006.20261024`，五处同步（`version.py` / `pyproject.toml` / `main.go` / `console.ts` / `report_viewer.ts`，含头注释与 DEMO schema 串）；仅升计数段 D（0005→0006）、日期后缀 `20261024` 不变（同一天定版）。
  - **离子态 / 听力 / 五感差异 / 幻听 / 幻视 / 幻触 协议标准查据（#596，只读）**：在 #592/#593/#594（Web 内容层视觉健康与无障碍已落地为 `concept_gui.html` + `docs/60` + `docs/61` 前端契约）与 #595（docs/62 光学/环境光/屈光/光的本质）基础上，继续查据**离子态 · 听力 · 五感差异 · 幻听 · 幻视 · 幻触**一脉标准——① 离子态：等离子态（物质第四态）与离子通道（感觉转导物理/生理基底）+ IEC 62366-1（医疗器械人因可用性，仅作通用人因纪律范本）；② 听力：ISO 8253-1/2/3（测听）、ISO 226（等响曲线）、ISO 389（测听零基准）、ISO 1999（噪声性听损）、ISO 7029（年龄听阈）、IEC 60118（助听器）、IEC 60645（听力计），及其 Web 落点 WCAG 1.2.x（字幕/文本替代/音频描述）、1.4.2（自动音频 >3s 可控）、1.4.7（背景声低于语音 20 dB）；③ 五感差异/多感官整合（McGurk 效应、跨模态耦合）+ ISO 9241，及其已落地 Web 落点 1.3.3 / 1.4.1（非颜色非单通道编码，见 docs/61）；④ 幻听/幻视/幻触：ICD-11 / DSM-5 精神病性症状分类；⑤ 幻视 ↔ 光敏癫痫：WCAG 2.3.1（≤3 闪/秒、一般闪光阈值 20 cd/m²、红闪 6 cd/m²、PEAT）。层归属判定：离子态/听力测听/幻觉分类一律判为**物理/生理/医学/心理参考层**，不冒充为本仓 Web 前端职责；唯一可呼应的 Web 落点 = 听力媒体无障碍（1.2.x/1.4.2/1.4.7）与幻视↔光敏癫痫（2.3.1），已单列。**落点**：新增 `docs/63_离子态听力五感幻觉协议标准查据.md`。**验证**：仅文档新增 + 版本号升版，未改数据逻辑（双 HTML 因版本串重生、data-sha256 / source-sha256 同步），`test_version.py` 动态读 `PACKAGE_VERSION`、全量 pytest 不受影响（零回归）。

- **0000.0000.0000.0005.20261024（2026-10-24）**
  - **版本号升一版（monorepo 里程表纪律，用户不看）**：整体包 `0000.0000.0000.0004.20261024` → `0000.0000.0000.0005.20261024`，五处同步（`version.py` / `pyproject.toml` / `main.go` / `console.ts` / `report_viewer.ts`，含头注释与 DEMO schema 串）；仅升计数段 D（0004→0005）、日期后缀 `20261024` 不变（同一天定版）。
  - **光学 / 环境光 / 屈光 / 光的本质 协议标准查据（#595，只读）**：在 #592/#593/#594（Web 内容层视觉健康与无障碍已落地为 `concept_gui.html` + `docs/60` + `docs/61` 前端契约）基础上，继续查据**光学 · 环境光 · 屈光 · 光的本质**一脉标准——① 屈光眼科与器械：ISO 10342（验光仪）/ ISO 8598（焦度计）/ ISO 11979（人工晶状体功率允差 ±0.3~±1.0 D）/ ANSI Z80.1（处方镜片）；② 环境光照度：EN 12464-1:2021（办公室 500 lx、Uo≥0.60、UGR≤19、Ra≥80）/ ISO 8995-1:2025 / CIE S 026（人因照明 M-EDI）；③ 光学元件与镀膜：ISO 10110（光学制图，ISO 10110-5:2026 以 nm 为首选单位）/ ISO 9211（光学镀膜 τ/ρ/α）；④ CIE 光度学：V(λ) 明视觉（峰值 555 nm）、Km=683 lm/W、辐射↔光度成对量换算（BIPM candela mise en pratique）；⑤ 光的波粒二象性：Planck→Einstein 光电效应→Compton 散射→de Broglie 物质波，E=hν、p=h/λ。层归属判定：屈光/光学/光度学/波粒二象性一律判为**医学/硬件/物理参考层**，不冒充为本仓 Web 前端职责；唯一可呼应的 Web 落点 = 环境光 ↔ 暗亮主题（`concept_gui.html` 主题开关已随系统偏好切换）。**落点**：新增 `docs/62_光学环境光屈光与光的本质协议标准查据.md`。**验证**：仅文档新增 + 版本号升版，未改 HTML 与数据，`test_version.py` 动态读 `PACKAGE_VERSION`、`test_concept_gui.py` 与全量 pytest 不受影响（零回归）。

- **0000.0000.0000.0004.20261024（2026-10-24）**
  - **版本号体系 monorepo 统一（全线换新，不沿用旧号）**：整体包里程表 `0000.0000.0000.0003.20261023` → `0000.0000.0000.0004.20261024`，五处同步（`version.py` / `pyproject.toml` / `main.go` / `console.ts` / `report_viewer.ts`，含头注释与 DEMO schema 串）；**semver 强制场景改 CalVer**——Cargo.toml ×3（classics-rs / peinfo / peview-egui，含各自 Cargo.lock，`cargo metadata` 离线验证一致）与 novel-website package.json 由旧 semver（1.0.0 / 0.1.0）迁到 `2026.10.24`（年份打头显长青，与 odometer 日期后缀同源；`version.py` 新增 `to_semver()` 映射与自检断言）；**deb 迁 odometer**——classics-linux 与 xfce4-quantum 的 `debian/changelog` 各追加 `0001.0000.0000.0000.20261024` 条目（迁移首版 A 段置 1 保证 dpkg 版本序不降级，`dpkg --compare-versions` 两条 gt 断言实测通过）；三个概念系统 taxonomy 重跑 build 脚本刷新 deno 版本引用（`--check` 无漂移）。
  - **新建 toolchain 工具链全景子系统（分类别 × 目标架构 × 仓库目录，只读不写）**：数据层 `data/toolchain_catalog.json`（23 条宿主工具链 + 7 条仓库工具软件 + 10 条目标架构矩阵 + 上游新鲜度两栏，全部版本为 2026-10-24 本机 `--version` 实采）+ `native/toolchain.py`（编目全景 / 本机实采 which+版本 / 仓库工具软件含配置逻辑顺序与命令序列 / 目标矩阵 / 新鲜度五个只读报告，NDK 与 OHOS 按 catalog 绝对路径回退探测）+ `tasks/toolchain.py`（4 任务）+ 四入口接线（subsystems 第 95 项 layer「语言/编译」/ CLI `toolchain` 子命令 / GUI「工具链全景」面板 / registry）+ `tests/test_toolchain.py`（14 项：schema/category 引用/关键条目/新鲜度两栏/实采/逻辑顺序/端到端/红线无写路径）；linkage 新增 7 条轴（llvm 供给/arch 门控/pkgmgr 供给/compat 供给/reverse 供给/sysdev 供给/winternals 关联，无孤岛无悬空）；ergonomics「语言与编译」组收入 toolchain。**红线：只探测与编目，绝不安装/卸载/构建/下载；catalog 的 setup_steps 与 commands 是 README 性质的逻辑顺序，不是自动执行队列。配套文档 `docs/57_工具链全景.md`（类别 × 目标架构 × 仓库目录三维组织 + 每个工具配置逻辑顺序与命令序列 + 交叉实境诚实边界 + 上游新鲜度两栏）。**
  - **comp 概念系统新增第九轴「交叉工具链实境」（cross-reality，72→81 概念、76→94 桥接）**：九个概念全部源自本仓 2026-10-24 实证——`bionic-no-iconv`（NDK r15 起 bionic 移除 iconv，libiconv 1.17 双架构静态链入）、`musl-gb18030`（OHOS musl iconv 原生 GB18030，classics 直编 + qemu 静态实跑）、`qemu-user-bionic-limits`（TLS 段对齐 8<64 / personality 被沙箱拒 / 动态 linker init SIGSEGV 三连坎，运行级验证不可行如实记录）、`mingw-thread-variants`（win32/posix 线程模型与异常模型变体，PE 产物 wine 9.0 验收）、`wine-emulation`（仿真≠真机的口径边界）、`ohos-sdk-layout`（2.4GB 外层包 + 内层多 zip 两层结构，native/llvm/bin clang 15.0.4 + sysroot 软链）、`ndk-api-levels`（API 21 旧版打底 / API 26 项目口径双轨门控）、`dpkg-version-migration`（semver 迁 odometer 的 A 段置 1 迁移税，版本序 gt 断言）、`odometer-versioning`（四段里程表进位循环 + to_semver() CalVer 映射）；每条带 engineering 工程落法与桥接（plang 6/daoxue 4/llvm 2/quantum 3），构建期 `--check` 校验无悬空。
  - **计数同步与门禁**：CLI 子命令 123→124、GUI 窗口 108→109（apilab/baigong/datong/zhuangzi 四个 taxonomy 的 user_face_facts 重跑刷新 + TAGLINES 同步 + test_gui_quantum 两处断言更新）；concept_gui.html 重新生成（data-sha256 同步）；audit_concepts --strict 与 check_concept_mesh --strict 零欠账；全量 pytest **1683 passed / 5 skipped**。
  - **工具链全景文档与上游新鲜度联网核实（docs/57 + catalog `version_freshness`）**：新增 `docs/57_工具链全景.md`（类别 × 目标架构 × 仓库目录三维组织 + 每个工具配置逻辑顺序与命令序列 + 交叉实境诚实边界 + 上游新鲜度两栏）；catalog `version_freshness` 由 3→**11 条 needs_action**（OpenJDK 20→LTS 21/25、Node 22.13.1→22.23.4、binutils 2.42→2.48、GCC 13.3.0→16.2、Clang 18.1.3→23.1.3、Rust 1.93.0→1.99.0、NDK r26d→r29/r27d LTS、OHOS SDK 6.0.0.47→7.0 Release、Qt 5.15.13→6.12 LTS、.NET 10.0.401→10.0.13、Python 3.11.17→3.15.1）与 4 条 fresh（Firefox 158.0.1 == 稳定、Go 1.27.3 == 最新补丁、Deno 2.9.8、Ruby 3.2.3），全部 2026-10-24 联网核实（developer.android.com / developer.huawei.com / gcc.gnu.org / llvm.org / blog.rust-lang.org / python.org / dotnet.microsoft.com / doc.qt.io / openjdk.org / blog.qt.io），宿主多随 Ubuntu 24.04 钉住，落后上游主干但随发行版滚动。
  - **工具链全景 repo_tools 补全与仓库目录校准（#586）**：catalog `repo_tools` 由 7→**8 条**——新增 `quantum-kernel`（量子架构内核 · Linux 6.18.57 LTS + arch/quantum，6 分支 LTS 补丁，C/Python/Shell，打包 deb `quantum-core_0.6.80` + `xfce4-quantum_0.6.80`，native-build · verified，含目录/配置逻辑顺序/命令序列/验收四维）；修正 pe-viewer-family 9 条 `paths` 漏写 `windows-internals-toolkit/` 前缀（统一真实仓库目录，呼应「仓库目录适配存放」）；docs/57 §2 表头 7→8 条并新增 §2.8 quantum-kernel（同四维格式）。
  - **工具链全景「全面发展」三方向（承接 #586，仅编目/评估，不装不卸不升级）**：
    - **仓库条目细化拆分（#587）**：catalog `repo_tools` 由 8→**11 条**——把伞条目 `harmony-ios-mac-swift`（4 个真实仓库塞 1 条 `paths`）拆为 4 个独立条目：`classics-swift-linux`（native-build · Swift 典籍工具 Linux 原生编译）/ `classics-harmony-app`（cross-compile · HarmonyOS ArkUI）/ `classics-ios-mac`（cross-compile · iOS/macOS SwiftUI，受 Apple EULA 限制）/ `android-app`（cross-compile · Android Compose，`windows-internals-toolkit/android/`）；各自精确 `repo_path` 与合法类别；测试 `must` 守卫同步（删 `harmony-ios-mac-swift`、加 4 新 id）；docs/57 §2 表头 8→11 条并把 §2.7 伞块拆为 §2.7–§2.10 四块、quantum-kernel 顺延 §2.11。
    - **工具链升级评估文档（#588）**：新增 `docs/58_工具链升级评估.md`——对 catalog `version_freshness.needs_action` 的 11 项逐条给「风险/CVE、升级路径逻辑顺序、优先级（应升/可选/无动作/宿主持有者责任）、是否随发行版滚动、验收口径」；明确仅评估不执行（守红线）；结论：仅 Node（#2 本仓 novel-website 构建前必升）、OpenJDK（#1 持有者责任）为明确动作项，其余 9 项为「观察 + 随滚」。
    - **comp 概念系统对接 quantum-kernel 补丁分发（#589）**：`comp_taxonomy.json` 81→**82 概念**、94→**95 桥接**——cross-reality 域新增 `qkern-patch-distribution`（工具链侧镜像概念，含 gist/detail/engineering），桥接 `quantum:concept:qkern-patch-distribution`（工具链是量子内核补丁分发的工程实现面）；by_domain 追加、_meta version 0066→0067；审计 0 不一致 / mesh 0 欠账 / 单连通分量。
    - **全量回归 + 概念同步三检查 + 提交推送 + HANDOFF §12（#590）**：全量 pytest 回归通过；audit_concepts --strict / check_concept_mesh --strict / repo guard 三检查零欠账；concept_gui.html 重生（data-sha256 同步）；git 提交并推送 origin/main；HANDOFF-arm-deb.md 追加 §12 记录本轮落账与「德育体知（智）美劳全面发展（先天道体）」维度映射。
    - **导入分析学习应用 4 外部仓库（#591，只读 WebFetch，边界分级）**：对 `massgravel`（Microsoft-Activation-Scripts）/ `ToiCF/CF-Workers-TGProxy` / `mokurin000/is-rust-gui-ready` / `Ebony-Vinyl/dsh-our-free-model` 四个外部 GitHub 仓做只读 WebFetch 分析（不克隆/不安装/不构建/不下载/不复制代码进本仓）。**边界分级**：massgravel 为「许可规避」类工具，钉为合规分析对象——仅分析激活服务的协议与机制，绝不编目为可装可跑、不提供任何绕过手段（落在新增 `license-compliance-boundary` 概念）；另三仓（边缘多 lane 代理 / Rust GUI 成熟度清单 / 插件化协议适配省 Token）纯技术可学习，但本仓无对应工程落点，**仅作 docs/59 学习笔记，不新增概念**（守「无真实 counterpart 不加概念」纪律）。**comp 概念系统 82→83 概念 / 95→96 桥接**：reverse 域新增 `license-compliance-boundary`（桥 daoxue `zhi-bu-zhi` 知边界而不过界）；并补回 #589 遗漏同步进 `build_comp.py` 的 `qkern-patch-distribution`（cross-reality 域，桥 quantum）——消除「误跑 build 无 --check 覆盖 JSON 回 81」的静默漂移地雷，使脚本与 JSON 重新同源。新增 `docs/59_导入分析学习应用四仓库边界分级.md`。**验证**：`build_comp.py --check` 通过（83 概念/96 桥接无悬空）；`concept_gui.html` 重生（data-sha256 同步）；test_comp.py/test_concept_gui.py 计数断言同步、17 passed；test_build_check_no_drift 与 test_committed_page_is_in_sync 全绿。
    - **圆光术可视化色彩/视觉/开关完善 · 依协议标准（#592）**：`concept_gui.html`（由 `tools/gen_concept_gui.py` 重生）新增**明暗双主题 + 可访问主题开关**，并补全色彩/视觉相关协议标准落地——① 查据 **WCAG 2.2 SC 1.4.3**（正文 ≥ 4.5:1、大字/UI ≥ 3:1，实测 dark 13.9:1 / light 14.8:1；dim 5.8/5.5:1；accent 6.3/4.9:1）、**SC 1.4.11**（功能性图形对象边框 ≥ 3:1，用 `--line-strong`：dark 3.5:1 / light 3.3:1）；② **CSS color-scheme** + **@media prefers-color-scheme**（声明 `dark light`、随系统偏好初值、配 `<meta name="color-scheme">` 与早期脚本防首屏闪烁）；③ **WAI-ARIA APG switch**（`role="switch"` + `aria-checked`、标签恒定不随状态变、Space/Enter 切换、localStorage 持久化）；④ **prefers-reduced-motion**（流光动画与切换过渡在「减少动态」偏好下停用，前庭安全）；⑤ **CSS Color L4 oklch()/light-dark()** 作为感知均匀着色演进方向（本页核心调色板用 hex 实测达标）。新增页面内「标准依据」卡列出上述标准与实测对比度。**验证**：`gen_concept_gui.py --check` 通过（data-sha256 不变，数据完整）；test_concept_gui.py 7 passed（含 test_committed_page_is_in_sync / test_page_is_offline_and_yuanguang 离线合规）；全量 pytest 复验通过。
    - **视觉健康与无障碍协议标准查据（#593）**：在 #592 双主题 + 可访问开关基础上，继续查据**视觉健康**一脉标准——① Web 内容层：WCAG 2.2 SC 1.4.1 用色（信息不单靠颜色，红绿色盲患病率北欧裔男 ≈8%/女 ≈0.4%）、SC 1.4.4 缩放(200%)、SC 1.4.6 增强对比度(AAA 正文 ≥7:1、大字 ≥4.5:1，本页双主题 13.9/14.8 已超)、SC 1.4.10 回流(320px/256px)、SC 1.4.12 文字间距(行高≥1.5/字距≥0.12/词距≥0.16)；② 硬件/人因层（仅设计原则参考，不冒充职责）：ISO 9241-303:2011 电子视觉显示人因（亮度/对比/眩光控制/减少闪烁/字符高度）、IEC 62471 / IEC-TR 62778 蓝光危害风险组（RG0–RG3，评 400–500nm 视网膜蓝光，**明确非 Web 内容标准**，软件暗色模式仅降整体亮度间接减蓝光、不是「护眼」保证）。诚实边界：散光是「深色模式护眼」反例（暗底亮字更模糊）→ 本页保留浅色主题等效选项、不主张暗色更护眼；青光眼/白内障→对比敏感度下降→高对比需求，其医学管理不属前端职责；弱视/低视力靠放大+高对比、色盲靠非颜色编码，分别有落地与标注。**落点**：扩展 concept_gui.html「标准依据」卡（gen_concept_gui.py 重生，data-sha256 不变）+ 新增 `docs/60_视觉健康与无障碍协议标准查据.md`。**验证**：test_concept_gui.py 7 passed（含同步/离线合规）；data-sha256 不变；全量 pytest 复验通过。
    - **前端无障碍规范（视觉健康落地，#594）**：把 #592/#593 已查据、已实测、已落地的视觉健康与无障碍做法沉淀为**本仓前端工程契约**——新建 `docs/61_前端无障碍规范（视觉健康落地）.md`。契约含：① 双主题 CSS 变量（禁止硬编码，暗色默认 + 浅色等效，散光反例下不主张暗色更护眼）；② 主题开关组件规范（`role="switch"` + `aria-checked`、标签恒定、Space/Enter、localStorage 持久化、`<head>` 早期脚本防首屏闪烁）；③ 减动效规范（`prefers-reduced-motion: reduce` 下动效/过渡归零）；④ 非颜色编码规范（SC 1.4.1，字形+形状+文本三重区分）；⑤ 对比度验收阈值表（正文 13.9/14.8:1 超 AAA、dim 5.8/5.5、acc 6.3/4.9、line-strong 3.5/3.5，经 sRGB 相对亮度公式独立复算与 docs/60 一致）；⑥ 缩放/回流/文字间距诚实标注（拓扑图属 graphics 例外）；⑦ 诚实边界（散光反例、青光眼/白内障医学层、IEC 62471 蓝光硬件层不冒充）。并给出其它前端产物（report_viewer / GUI 面板）接入清单与 PR 前自检清单。**落点**：`docs/61`（新建）+ `docs/60`「可继续方向①」标记落地。**验证**：对比度数字经 sRGB 公式复算通过；docs 仅新增/标注、未改 HTML 与数据，test_concept_gui.py 与全量 pytest 不受影响（零回归）。

- **v0.6.89（2026-10）**
  - **网络/存储/线缆/内外环境标准补全（逐条联网核实后写入，两处编号纠错）**：① **L4S 低时延族**——RFC 9330（架构，Informational）/ RFC 9331（ECN 协议，Experimental，ECT(1) 码点标识 L4S 流）/ RFC 9332（双队列耦合 AQM，Experimental，p_C=(p_CL/k)²，k=2）+ **RFC 8033**（PIE 抗 bufferbloat，Experimental，2017-02）；② **Wi-Fi 6/7**——IEEE 802.11ax-2021（2021-05-19 发布）与 IEEE 802.11be-2024（2024-09-26 批准、2025-07-22 正式发布，MLO/320MHz/4096-QAM）；③ **异位同步/高延时异位同步**——NTP RFC 5905（**纠正：RFC 5909 不是 NTP**，是 Neighbor Discovery Proxy 安全）、PTP IEEE 1588-2019、gPTP IEEE 802.1AS-2020、SyncE ITU-T G.8261/G.8262/G.8264、分组网时间/相位 G.8271·Y.1366 + G.8275.1 + G.8273.2、White Rabbit（CERN 亚纳秒光纤扩展）；④ **存储/文件系统**——NVMe Base 2.1（2024-08-05）/ SATA（SATA-IO）/ SAS（INCITS T10）/ UFS 4.1（JEDEC JESD220G）/ eMMC 5.1（JESD84-B51）/ POSIX IEEE 1003.1-2024（兼 ISO/IEC/IEEE 9945）/ ISO 9660 / UDF（ECMA-167）/ exFAT（ECMA-382）/ NTFS；⑤ **线缆/连接器**——ISO/IEC 11801:2017 布线 / ANSI TIA-568-D / ITU-T G.652 单模光纤 / IEC 60793 / HDMI 2.1 / DP 2.1 / Thunderbolt 4·5 / IEC 60320 器具耦合器；⑥ **内外环境运行**——IEC 60529（IP 代码）/ IEC 62368-1:2018（安规第三版，GB 4943.1-2022 等同）/ IEC 60721（环境分类）/ IEC 61000（EMC）/ IEC 62321（RoHS 测定，GB/T 39560 对应）。落点：`data/network_standards.json`（26 键）+ `data/storage_docs.json` + `data/peripheral_standards_docs.json` + 新建 `data/env_standards.json`（经 `native/electrical.py` 的 `env_reference()` 只读消费）。
  - **应用到概念系统与各系统/设备自动适应优化**：netsys network 模块 standards 扩为 16 项（**RFC 4941→8981 纠错**随行）；`network_docs.json` 增 l4s / wifi_ax_be / ntp / ptp 四条自动适应调优（dualpi2 先 fq_codel/cake 验证再升级、WPA3/SAE 基线、`chronyc tracking` 三上游 + NTS、`ethtool -T` 探 PHC 无 PHC 不上 PTP）；`storage.py`/`peripheral.py`/`electrical.py` docstring 立「存储协议标准族」「线缆/连接器与内外环境运行标准」段。
  - **导入分析学习应用 Linux 内核源码（torvalds/linux master 2026-10-23 拉取，逐文件核对）**：netsys 新增 3 个**源码实证**模块——`kernel-l4s`（`net/sched/sch_dualpi2.c` 头部明示 RFC 9332 coupled dual-queue PI2 与 L4S ECN 标识；`include/net/inet_ecn.h` 定义 `INET_ECN_ECT_1=1`/`INET_ECN_MASK=3`）、`kernel-ptp`（`include/linux/ptp_clock_kernel.h` 的 `ptp_clock_info` adjfine/adjphase + `drivers/ptp` PHC 基础设施）、`kernel-wifi-he-eht`（`include/linux/ieee80211.h` 的 HE 能力元素 35 / EHT 能力元素 108，`net/mac80211/he.c` 与 `eht.c` 分治）；另实证 `net/sched/sch_pie.c` 引用 RFC 8033、`drivers/nvme/host/core.c`「NVMe host core framework」、`fs/ext4/super.c` 的 metadata_csum 特性。netsys 61→64 模块、35→41 关系，test_netsys 计数断言同步。
  - **导入分析学习应用 pepsipu（Sammy Hajhamid）GitHub 项目群 → 新建 sysdev 子系统**（7 仓库浅克隆逐文件分析，学习不等于打包）：**warpalloc**（110 行 NASM 分配器：prewalloc 预分配 + 单空闲链首次适应 + 荒野 bump + 8 字节内嵌头；README 自述 25 次分配约快 ptmalloc 300 倍、churn 场景劣化——「别用 warpalloc 做游戏」）、**aski**（约 1077 行 Rust 最小编译器：IStream→Tokenizer→Parser→Program 四段管线 + NASM 分节输出 + 寄存器显式暴露 + while/for 未实现如实标注）、**xinOS-old/OSpaint**（玩具 OS：bootloader→保护模式→remap_pic+init_idt→VESA→应用；rule 1 硬件尺寸减一；QEMU/Bochs 可启动镜像验收）、**ramenbox**（6502 幻想主机：gen_ops.py 从 oplist 文本生成 opcodes.json、CPU 按字节反射分发、GPIO 位掩码 + ST7789 SPI 外设）、**cx**（约 40 行 zsh：符号链接农场 + CODEX_HOME 选家的多账户隔离）、**torus**（pnpm workspace + Cloudflare Worker 聚合校园服务）。**许可证边界**：warpalloc MIT / xinOS-old BSD 风格可学模式；其余五仓库无许可证默认保留所有权利，只学思想。落点：`data/sysdev_docs.json`（8 主题）+ `native/sysdev.py`（只读：工具链盘点/glibc malloc 环境只读展示/内存足迹）+ `tasks/sysdev.py`（4 任务）+ 四入口接线（omni 四件套齐全）+ `tests/test_sysdev.py`（23 项）。
  - **comp 概念系统新增 `aski-pipeline`**（71→72 概念、73→76 桥接）：aski 四段管线实例落 pipeline 域，桥接 daoxue 道法自然与 plang 的 rust/assembly，附工程落法（先建表再驱动、分节输出进数据结构）。
  - **版本号（全线换新，不沿用旧号）**：整体包里程表 `0000.0000.0000.0001.20261023` → `0000.0000.0000.0003.20261023`（0002 为批次中途快照，回归修复与计数同步后进位到 0003）；**五处同步**——`version.py` / `pyproject.toml` / `main.go` / `console.ts` / `report_viewer.ts`（含头注释与 DEMO schema 串）全部落到 `0000.0000.0000.0003.20261023`，deno 两文件自此脱离旧的 0.6.x 编号、与主线同口径；`version.py` 的 `_CONCEPTS` 映射同步（netsys 0066 / comp 0065）；netsys `...0065` → `...0066`、comp `...0064` → `...0065`、sysdev 子系统 `...0001` 各自独立；`concept_gui.html` 重新生成（data-sha256 同步）。

- **v0.6.87（2026-10）**
  - **声学与音律子系统（acoustics）：声音 / 频率 / 振动 / 音调 / 声率 / 黄钟大吕的学习分析应用**。用户命题「最可能应用在无线技术、电磁波，还有喇叭或耳机」落成四轴知识库 `data/acoustics_docs.json`：① **声学基础**——频率/波长/声速（c=f·λ，空气 331.3+0.606·T）/共振（ωn=√(k/m)）/分贝（SPL=20·log10(prms/p0)，参考 20 µPa）/ A·C·Z 计权与 F·S·I 时间计权（IEC 61672-1:2013 标称值全表入数据层）；② **中国音律**——黄钟大吕·十二律·三分损益（管长基数 81，损一 ×2/3、益一 ×4/3；《吕氏春秋·古乐》《淮南子·天文训》典籍口径 + 朱载堉新法密率），**三分损益生成器按典籍数值逐律对账**（含「蕤宾→大吕连续两次益一」的易错点与「清黄钟不能还原」comma 证明）；③ **无线电磁**——ITU 无线电规则 ISM 频段全表（RR 5.138/5.150/5.280，含 433.92/2450/5800 MHz 中心频率与频段属性）+ 中国微功率设备口径（工信部 2019 年第 52 号公告三豁免与红线）+ 频率↔波长↔λ/4 天线尺寸换算；④ **音频硬件**——喇叭/耳机电声标准（IEC 60268 系列、EN 50332-1 整机 ≤100 dB、EN 50332-2 播放器 ≤150 mV / 耳机 WBCV ≥75 mV、GB/T 14471）。
  - **知识层含可机算表格**：A/C/Z 计权值表、空气波长表、各介质声速表、十二律管长/频率比/音分偏差表（机算值，自林钟起每律 ≈ +1.96 音分 = comma÷12，纠正了转载源里与公式自相矛盾的旧值）、ISM 频段 12 条（每条带 ITU 脚注出处）、EN 50332 限值结构化字段。
  - **native/acoustics.py 只读探针 + 纯函数引擎**：`wavelength` / `frequency_from_wavelength` / `speed_of_sound` / `em_wavelength` / `antenna_length` / `db_sum` / `weighting_correction`（对数轴就近取标称频点）/ `sanfen_sunyi`（三分损益生成器）/ `probe_alsa`（/proc/asound + aplay/arecord -l）/ `probe_pulseaudio`（pactl info）/ `probe_audio_tools`（工具面存在性）。**红线：绝不播放任何声音、绝不调音量、绝不采集麦克风内容、无任何射频发射路径**（测试用 AST 核查唯一执行收口 `_run` 的实参常量全在只读白名单）。
  - **四入口接线齐全**：`tasks/acoustics.py`（4 任务：总报告 / 音频设备盘点 / 三分损益十二律 / ISM 频段与波长天线参照）+ `subsystems` 登记（设备/声学层）+ CLI `acoustics` 子命令 + GUI「声学与音律」面板（基准频率可调）；`linkage` 加 4 轴（acoustics↔radio 波动几何互印证、↔peripheral 音频设备能力面、↔chrono 十二律配十二月的古典算例，radio→acoustics 反向边）；omni 四件套齐全无欠账；测试 `tests/test_acoustics.py` 19 项（知识库四轴字段完整、换算精度、算律对账经典数值表、探针不变量、AST 写路径核查）。
  - **补丁四件套实测收官 + CI 钉版**：Python 3.11.17（pyenv global）、Node 22.23.4、Deno 2.9.8、Go 1.27.3 七平台重编 + `go vet` 全过；`.github/workflows/build.yml` 的 `go-version` 由 1.21（已无上游补丁）升至 1.27 随工具链同步；3.11.17 下全量 pytest 1577 passed / 5 skipped。
  - **版本号五处同步 0.6.87**（`__init__` / pyproject / `main.go` / `console.ts` / `report_viewer.ts` 含头注释与 DEMO schema 串）+ 两个 HTML 重新生成。

- **v0.6.86（2026-10）**
  - **编程语言 / 编译语言 / 汇编语言安全新闻与补丁评估**（docs/52）：头条 eMudhra 中间 CA 事件（密钥仪式缺陷致 P-384 私钥仅 3–8 bit 熵、8 张中间 CA、Mozilla 三小时 OneCRL 拦截）及其跨语言响应——Go 1.27.3/1.26.10（CVE-2026-111943，**必须重编译部署才生效**）、OpenJDK 周期外 CVE-2026-91403（CVSS 9.1）、Python 3.15.1/3.14.9/3.13.17 加急 + certifi 2026.10.19、Node.js 三线 ca-cert、Rust webpki-roots 1.0.10；Python 10-01 五连发 8 个 CVE 明细（3.10.22 终版 EOL）；Node.js 10-21 十项 CVE（Brotli 越界写 RCE 等）；OpenJDK 10-20 CPU 约 27 CVE；.NET 10 月补丁日 46 CVE（NuGet 运行时外补丁形态）；工具链本体 LLVM 23.1.4 + CVE-2026-27144、binutils/GAS 4 CVE（修于 2.48，本机 2.42 不在面）、GCC libstdc++ PBDS UAF、Rust rustc 11 年老漏洞（needs_verify）；供应链事件（tensorlake 投毒 / axios 劫持 / AI agent 记忆投毒 / TrapDoor）与 FIRST「无 CVE 补丁路径」口径。**本仓九项补丁评估表**：pyenv Python 3.11.1→3.11.17（source-only 正好匹配）、Node 22.13.1→22.23.4、Deno 可选、**Go 1.21.4 无补丁可打只能升级重编译七平台产物**、OpenJDK 20 宿主持有者责任、binutils/gcc 无需动作、.NET 缺位仅登记、零第三方依赖维持纪律。
  - **comp 概念系统 bringup 域增 `toolchain-security-response`**（70→71 概念、71→73 桥接）：解释型换运行时即生效 vs 编译型必须重编译部署——两种补丁响应时钟；工程落法写到本仓 Go 七平台产物 CI 每次全量重编 + 宿主解释器版本是一等字段（langdetect / tasks/jdk.py）+ docs/52 九项评估表按时钟逐项定性；桥接 `plang:lang:go` 与 `quantum:concept:qkern-patch-distribution` 均在册无悬空。同步修正 `_meta.axes` 漏登记 bringup 的 0.6.85 遗留漂移（八轴与 DOMAINS 对齐，文档字符串七轴→八轴）。
  - **llvm_docs.json changelog 增 v0.6.86**（LLVM 23.1.4 / CVE-2026-27144 / binutils 4 CVE / comp 新概念对账）。
  - **质量门禁**：comp build --check 通过（71 概念/73 桥接无悬空）；test_comp/test_concepts_center/test_gui_quantum 计数断言同步（70→71、71→73）；全量 pytest、audit_concepts --strict、check_concept_mesh --strict、repo guard 全绿。
  - **版本号五处同步 0.6.86**（`__init__` / pyproject / `main.go` / `console.ts` / `report_viewer.ts` 含头注释与 DEMO schema 串）+ 两个 HTML 重新生成。

- **v0.6.85（2026-10）**
  - **导入分析学习应用两仓库**（docs/51）：`haxi0/ios-instantnoodle`（XNU iOS 16 引导 shim：arm64 Linux Image 头 + 自管 MMU + live-FDT 探查 + UFS，三板 169 文件）与 `terminallywell/center-widget-popups`（KDE Plasma 6 KWin 脚本，main.js 约 40 行，MIT）——**只作只读分析，零代码复制、零产物打包**。
  - **comp 概念系统新增第八轴「引导与实测纪律」**（66→70 概念，67→71 桥接）：`diagnostic-first-boot`（无载荷先出 live-FDT 诊断报告，对照本仓 quantum-core 缺接口记 available=false + 面板「host(模拟)」）、`live-fdt-probe`（*(verify)* 标注纪律 ↔ 本仓 needs_verify + audit --strict）、`abs-reloc-gate`（构建期 readelf ABS64=0 门禁 ↔ 本仓 guard/--check/sha256 同步校验）、`host-test-harness`（-DHOST_TEST=1 宿主验证 ↔ 本仓宿主模拟架构 + pytest + make check）；每条带 engineering 工程落法与桥接——**comp 首批 3 条 quantum 边**（qsim-asset / qkern-patch-distribution / qsim-engine）+ 1 条 daoxue 边（zhi-bu-zhi 知不知上）。
  - **zhuangzi 新增第 8 条人体工程学原则「幂等护栏」**（19→20 概念）：源模式为 center-widget-popups 的 `|geo.x-x|<1` 重入护栏（frameGeometryChanged 回调不自我触发）+ 范围纪律（区间外不顺动、只改水平位置）；对应本仓 GUI「生成/关闭」不重入、genmon 定时刷新只读不写、破坏性操作前置确认。同步修正 wudai-yizhi 落法中陈旧的子命令计数（103→119 实测）。
  - **质量门禁**：comp/zhuangzi build --check 通过（70 概念/71 桥接、20 概念/18 桥接无悬空）；concept_gui.html 边数 50→51 重新生成且 data-sha256 同步；test_comp/test_zhuangzi/test_ergonomics 计数断言同步更新（八轴 70/桥接 71/原则 8）；全量 pytest、audit_concepts --strict、check_concept_mesh --strict、repo guard 全绿。
  - **版本号五处同步 0.6.85**（`__init__` / pyproject / `main.go` / `console.ts` / `report_viewer.ts` 含头注释与 DEMO schema 串）+ 两个 HTML 重新生成。

- **v0.6.84（2026-10）**
  - **数字量子无法实体，那就成为两大阵法的基石**——用户命题「如果我们的数字量子无法实体，那么，就成为周天星斗大阵和十二都天神煞大阵的基石，也就是利用数字矩阵冗余数据（非个人数据和关键资产）和 fail2ban 源代码的引入分析学习应用，进行原路返回」全链路落地（docs/50）：
    - **周天星斗大阵（数字矩阵冗余数据）**：`native/matrix.py` + `data/matrix_refs.json`——冗余数据如漫天星斗，只观其位、不取其光。allowlist 5 类（user-cache / tmp / pkg-cache / trash / log-rotate，11 条路径）逐一实测体积（不跟随 symlink、只取 st_size、深度/条数/总量三重预算截断），denylist 20 条关键资产路径（~/.ssh、~/.gnupg、~/.password-store、~/.config/keyrings、~/.netrc、~/.gitconfig、~/.aws、~/.kube、~/.docker、个人目录、浏览器 profile、/etc/ssl/private 等）**红线校验**：展开后与 allowlist 有交集即拒绝执行；清理建议只以文本交还用户（**原路返回**——道法自然在操作语义上的体现：只读观测、不代行写操作）。
    - **十二都天神煞大阵（fail2ban 源代码引入分析学习应用）**：`native/f2b.py` + `data/f2b_refs.json`——引入 fail2ban 官方源码作**只读学习分析**（license=GPL-2.0 如实述明、不 vendored、不入包），拆解其六层模式（jail / filter / action / threshold / daemon / client，「十二」取周遍环绕之义）；`fail2ban-client` 只放行 `status` / `version` / `get` 三个只读子命令，本地 `jail.local` / `jail.d/*.local` 只读解析（INI 含 `#`/`;` 注释、`\` 续行、`[DEFAULT]` 浅合并）；fail2ban 不在场时如实降级「未能获取」，绝不虚构战果。
    - **两大阵法指导理念总纲**（道法自然、活在当下、只有生存才能发展、在发展中能更好的生存、发展生存如此循环亦复如是）：写入两份 refs JSON 的 philosophy 段，并贯穿 native / tasks / CLI / GUI / 文档每一层。
    - **接线四入口**：`tasks/matrix.py`（matrix_report / matrix_reclaim_guidance）+ `tasks/f2b.py`（f2b_report / f2b_jail_guidance）→ registry 注册（任务总数 508）→ CLI `sysweeper matrix` / `sysweeper f2b` 子命令（--env）→ GUI「周天星斗大阵」「十二都天神煞大阵」两个面板（LabelFrame 维度输入 + ScrolledText 报告 + 生成/关闭，940x740）→ 测试 31 项（test_matrix 16 + test_f2b 15，含红线交集报警 / symlink 不跟随 / chmod 000 不崩 / 无写调用 token 强制 / 四入口接线断言）。
  - **quantum-core 桌面守护进程接入 `/proc/quantum-net`（组网维度）**：`quantum-kernel/desktop/quantum-core` 新增 `parse_net()`（memsets 清零语义与 parse_energy 一致）与 `GetNetStats` DBus 方法，`state.json` 增加 net 段（available/nics/mode/gaia_level/swarm_units/links/peers/exchanges/entanglements/topology_changes/nic_rows）；新增 Genmon 面板小程序 `quantum-net-genmon.sh`（jq/python3/grep 三级回退，host 缺接口显示「host(模拟)」优雅降级）；`quantum-settings.sh` 升级为能量 / QPU / 组网三维面板；`xfce4-quantum` 打包至 v0.6.84（net genmon 入包，dpkg-deb -c 实测校验）。`make check`（C 单测）全过。
  - **文档补全**：docs/49《netsys 架构与硬件维度》（架构 6 模块 net-arch/ctrl-plane/data-plane/qnic-arch/qkd-arch/qrelay-arch + 硬件 5 模块 + 神性层 + sysmesh/sysfed 只读登记口径、quantum 桥接 4 条、`--check` 61 模块实测）；docs/50《周天星斗与十二都天神煞-数字矩阵与 fail2ban 学习应用》（理念总纲 / 两阵落点 / 协同 / 诚实边界五节）。
  - **版本号五处同步 0.6.84**（`__init__` / pyproject / `main.go` / `console.ts` / `report_viewer.ts` 含头注释与 DEMO schema 串）+ `report_viewer.html` / `concept_gui.html` 重新生成（source-sha256 / data-sha256 双校验通过）；实测计数 CLI 子命令 / GUI 窗口同步递增。

- **v0.6.69（2026-10）**
  - **量子程序与虚拟机（native/quantum.py）**——纯标准库态矢量模拟器 + 程序 IR + 量子架构基座，CLI 新入口 `sysweeper quantum vm <bell|ghz|teleport|grover2q|bv2|arch>`：
    - **态矢量模拟器**：19 个量子门 + 4 个参数门（P/Rx/Ry/Rz，支持 `pi`/`pi/2`/`2*pi` 等安全数字解析，绝不用 eval）、测量真实坍缩、reset_qubit、通用 k 比特门；
    - **程序 IR**：量子指令集（gate/measure/reset/barrier/enc/halt/if-cond/xd/zd），`parse_program` ↔ `to_text_ir` round-trip，显式 qubits 头簿记越界校验；
    - **内置算法**：bell/ghz/teleport（含 xd/zd 经典修复，传态右位恒 1）/grover2q（100% 命中）/bv2；固定种子确定性；
    - **量子架构基座**（应用量子的意义在量子架构）：**量子矩阵数字转换门**（enc/dec 整数⟷量子态置换矩阵）、**CPU↔闪存不间断交换**（PiLink 链路，每条指令入链直至 halt，max_steps 护栏）、**tan/ctan 返回交互**（phase_wrap=atan(tan(x)) π 周期折叠）、**圆周率数据链路缓冲**（size=ceil(ratio·π)，2π→7 槽）、**虚拟其他硬件针脚**（define_pin/set_pin/read_pin）；
    - 接线：native 导入 + subsystems 开关（82 项）+ GUI「量子虚拟机」面板；测试 90 项（test_quantum_vm 57 + test_gui_quantum 29 等）。诚实边界：经典模拟器，不含量子硬件探针、不接入量子设备。
  - **Docker 容器化**：`Dockerfile`（多阶段构建、非 root、`--no-index` 可复现）+ `docker-compose.yml`（read_only + cap_drop ALL + no-new-privileges 最小权限）+ `.dockerignore` + `docs/36`；`docs/37` 给出 Windows/Linux/macOS/BSD/Unix/Android/iOS 全系统安装路径与产物矩阵。容器实测：detect / quantum vm / 只读根 / 零 capabilities / uid=999 全部通过。
  - **版本号五处同步**：`__init__` / pyproject / `main.go` / `console.ts` / `report_viewer.ts` 统一 0.6.69（连带修正 deno 两处自 0.6.62 起的滞后），`report_viewer.html` 重新生成；userface 实测面同步（GUI 窗口 95 / CLI 子命令 110 / deno 0.6.69）。

- **v0.6.77（2026-10）**
  - **新建「量子存储交换」只读诊断子系统（qstore）**：把「保持量子架构 + ext4 默认 4K 对齐 + GPU/NPU/TPU/CAN 异构端点缓冲交互 + 按程序要求做储存读取扫描索引 + 量子数字逻辑矩阵做进制转换」落成 **v0.6.69 量子架构基座之上的第一个存储域消费者**——不重写量子层，只复用：端点握手用经典针脚（每端点 2 位 req/ack，4 端点恰好占满 8 位寄存器）、缓冲水位用 PiLink 环形缓冲（ceil(2π)=7 槽）、进制转换用 `enc k` 置换矩阵 Π_k 编码门。「硬盘可接受的数列」= 字节流经 12 位重组为 4096 进制（4K 粒度）数列，每项 0..4095 与 4K 块对齐。
  - **两条已核实的技术契约**（测试锁住）：①**enc 是翻转语义**——从 |0…0> 编码 k 得 |k>，紧接着编码 j 会得到 |k⊕j>（实测 202→77 不复位得 135），逐数字编码前必须 `load()` 复位；②`decode_number()` 真实坍缩态矢量、`snapshot()` 只回最近 7 条——全量链路历史由模块自累积 step 级记录。**诚实边界**：量子部分是可逆编码与管线仿真，不是真的把 GPU 变成磁盘加速器。
  - **落地**：`data/qstore_refs.json` 10 条 + 11 官方源（kernel.org ext4·块层·SocketCAN / UEFI GPT / PCI-SIG / ISO 11898 / 昇腾 CANN / Coral Edge TPU / Mesa / e2fsprogs，3 条挂 needs_verify；含本仓量子基座内部锚点）+ `native/qstore.py` 六段只读报告（端点存在性 / ext4·4K 对齐三级降级 sysfs→lsblk→statvfs / Π_k 保真往返 / 管线仿真 / 聚合 / 能力自检）+ `tasks/qstore.py` 4 任务 + CLI `qstore` 子命令（overview/endpoints/align/radix/pipeline/capabilities）+ GUI「量子存储」面板。
  - **红线**：绝不执行写盘/格式化/分区命令（mkfs.ext4/dd/wipefs/sgdisk/parted 只作文本建议）；绝不加载驱动或提交计算任务；CAN 绝不开套接字不发帧；不改 `quantum.py` 任何语义（其 import 白名单与 quantum_* 任务数有既有断言守着）。
  - **组网接入**：subsystems 第 88 项（layer「存储/量子」，omni 自动归存储域）；`linkage.py` 三条联动轴（qstore→quantum 供给·基座消费 / storage→qstore 供给·对齐落点 / qstore→virtgpu 关联·GPU 端点两极），孤岛 0、悬空 0，`check_concept_mesh --strict` 与 `audit_concepts --strict` 零欠账。
  - **版本号五处同步 0.6.77** + `report_viewer.html` 重新生成；实测计数 CLI 115→116、GUI 100→101 四库同步；测试 23 项（schema/官方源域名/needs_verify/回链/针脚预算/保真往返/越界/XOR 陷阱/对齐纯函数/缺失降级/管线一致性/4096 打包整除/12 位重组可逆/红线 token/四入口接线）；文档见 docs/43《量子存储交换子系统》。

- **v0.6.83（2026-10）**
  - **GUI「圆光术」指导理念与基本设计原则落地**（docs/GUI圆光术指导理念与基本设计原则.md）：把概念系统整体论（道通为一 / 盖亚意识 / 集智体 / 层次分道 / 通过组网而来）翻译成 GUI 视觉与交互范式——**圆**（中心辐射 / 环抱聚合 / 整体全息）、**光**（光晕聚焦 / 明暗层次 / 全息照亮）、**术**（交互即组网），落为**圆光术八则**（中心为一 / 辐射呈现 / 环抱聚合 / 光晕聚焦 / 整体全息 / 层次分道 / 诚实边界 / 协议无关）与四反模式（不做树菜单 / 中心不做首页按钮 / 不加一键修复 / 不依赖单一平台）。
  - **A · 诊断报告查看器注入圆光术视觉范式**（`src/deno/report_viewer.ts` + `report_viewer.html`）：品牌位改为发光同心圆 logo（radial-gradient 光晕），新增可折叠「圆光术理念」banner（以圆为体、以光为用），`halo` 径向光晕聚焦样式供异常 / 变化高亮；渲染逻辑保持纯展示、只读、数据不出浏览器。
  - **B · 新建圆光术概念系统拓扑 GUI**（`tools/gen_concept_gui.py` → `concept_gui.html`）：单文件静态页把 `concepts.topo()/overview()` **实测数据**烘焙成「圆」——中心盖亚意识 · 集智体光晕（三道性/神性/人性光环），9 系统环抱成环（节点大小 = stats 体量），桥接为辐射光线（粗细 / 透明度 = `topo()["edge"]` 边权，箭头示向），下附 **9×9 桥接矩阵**（整体全息，可点击格子聚焦桥接）与 external 外部靶（llvm ×13 / langref ×2，如实呈现不并入环内）；交互即组网：点节点辐射聚焦、点中心回归整体。与 `gen_report_viewer.py` 同一同步纪律——页面嵌「数据摘要 SHA256」，`--check` 复算比对，`tests/test_concept_gui.py` 7 项守护（生成 / 同步 / 防篡改 / 摘要稳定 / 数据与 topo() 逐项一致 / 离线无外链）。
  - **浏览器实测**：Chromium 实开 `concept_gui.html`——50 条桥接连线、72 格矩阵（50 格有数）、聚焦 netsys 得 15 条热边（8 出 + 7 入）与 8 节点淡出、重置回归全貌，均正确；`report_viewer.html` 视觉同步确认。
  - **版本号五处同步 0.6.83**（`__init__` / pyproject / `main.go` / `console.ts` / `report_viewer.ts` 含 DEMO schema 串）+ `report_viewer.html` / `concept_gui.html` 重新生成；`audit_concepts --strict` 与 `check_concept_mesh --strict` 零欠账；全量 pytest 1548 passed / 3 skipped。

- **v0.6.82（2026-10）**
  - **概念系统整体组网能力（全面）**：netsys 新增协议无关的「系统互联组网协调」基底模块 `sysmesh`（系统互联协调）与 `sysfed`（跨系统组网联邦协调），61 模块 / 37 桥接；让组网作为「各种系统·各种硬件·各种架构」的基底连通**全部 9 概念系统**——各系统（plang / daoxue / quantum / comp / apilab / zhuangzi / baigong / datong）均显式锚定 `netsys:sysmesh`，呼应「就算协议不再支持、基底不灭」。9×9 桥接矩阵全双向连通（netsys 出边覆盖全部 8 个对端系统，zhuangzi 亦获首个 netsys 锚点）。
  - **道枢治理层补齐 comp / apilab 治理桥**：daoxue 此前仅 JSON 漂移携带、脚本从未生成的 comp / apilab 治理桥，以正确口径恢复（`zhi-bu-zhi → comp:pipeline-overview` 同构、`wu-zhi-you-yong → apilab:openapi` 类比），道枢真正治理全部 9 系统。
  - **质量门禁归零**：`check_concept_mesh --strict` 与 `audit_concepts --strict` 零欠账（修正检查器识别 `guidance:zhengti_zhida` 整体指导伪段，消除历史误报）；9 系统连通为单一整体（连通分量 = 1）。
  - **版本号五处同步 0.6.82**（`__init__` / pyproject / `main.go` / `console.ts` / `report_viewer.ts`）+ `report_viewer.html` 重新生成；全量 pytest 1541 passed / 3 skipped。

- **v0.6.80（2026-10）**
  - **概念系统完善补全 + 组网能力增强**：netsys 新增 5 个组网模块（batman-adv / mesh-routing / sdn-openflow / lldp-topo / wireguard-mesh），46 模块；quantum network 域深化至 13 概念（量子互联网栈 / 纠缠交换 / 隐形传态 / 量子网络拓扑 / QKD 密钥管理），78 概念、45 桥接；跨系统桥接贯通量子↔组网（quantum→netsys 18 条、netsys↔quantum 安全桥），`check_concept_mesh --strict` 与 `audit_concepts --strict` 零欠账。
  - **XFCE「改成量子架构」（doc 48）**：把 XFCE 会话/守护进程/面板小程序/主题做成真正接线量子架构内核诚实接口（`/proc/quantum-energy`、`/dev/qpu0`）的桌面基座——`quantum-core` 守护进程（读接口、写 state.json、可选 DBus 暴露 org.quantum.Core，host 缺接口优雅降级）、两个 Genmon 小程序（能级 / QPU 链路）、量子色系 GTK 主题与壁纸、`quantum.desktop` 会话。`xfce4-quantum` Debian 源包（双二进制包 quantum-core + xfce4-quantum，Provides: quantum-desktop-base）经 debhelper 与 build_deb.sh 两条路径实测可构建（arch=amd64，v0.6.80），证明桌面基座可为目标架构构建/安装。**诚实边界**：量子是宿主模拟架构，不声称 XFCE 在已引导的量子处理器上运行；测试床 `scripts/quantum-testbed.sh --with-xfce` 把该目标升级为端到端演示（默认仍只产内核+initrd 轻量核心）。
  - **版本号五处同步 0.6.80**（`__init__` / pyproject / `main.go` / `console.ts` / `report_viewer.ts`）+ `report_viewer.html` 重新生成；文档见 docs/48《XFCE 量子架构适配》。

- **v0.6.79（2026-10）**
  - **量子架构内核「六分支 LTS 适配」完成（各版本打补丁）**：单一 6.18.57 基线补丁之外，`scripts/gen_version_patch.py` 在基线之上对 5 个在维护 LTS 分支做「版本面适配」——`drivers/Kconfig`·`drivers/Makefile`·`Documentation/index.rst`·`arch/quantum/include/asm/Kbuild` 按目标版本原文重建，`arch/quantum` 内 8 个头文件按各版本内核 API 契约做差异修法（atomic/pgtable/cache/cmpxchg/bitsperlong/signal 等）。产出 `patches/0001-quantum-architecture-v1-<ver>.patch`（6.12=3486 / 6.6=3484 / 6.1=3493 / 5.15=3523 / 5.10=3736 行）。
  - **三层验收如实报告（run_builds.sh 汇总）**：① defconfig 全解析；② 真实全量链接 vmlinux（宿主机器码）——6.18.57=4,608,952 字节、6.12.113=4,339,272、6.6.159=4,163,528、6.1.190=4,119,064，四版各 15 个 `quantum_*` 符号在 nm 清单内在位；③ 其他架构零破坏（x86_64 defconfig 对照 1704/1635/1588/1476/1453 项）。**5.15.223 / 5.10.272 为已 EOL 长尾分支**，其通用代码（trap_init / pm_power_off / screen_info 强引用、head.o 双入链、asm-generic uaccess 内联冲突）与量子架构移植强纠缠——补丁 + defconfig 全解析 + arch/quantum 注册均就绪，但整树链接 vmlinux 失败，按用户「有些无法完善才是正确的」**有意记为已知限制、不强行修复**（见 doc 44 §8.3 与 doc 47）。受支持目标：6.18.57 + 6.12 / 6.6 / 6.1。
  - **概念系统 qkern 域补全至 7 条 + needs_verify 清零**：补 `qkern-page-discipline`（4KiB 页纪律）、`qkern-patch-distribution`（补丁分发与增量镜像）、`qkern-lts`（LTS 基线）三条，九域 70→73 概念、桥接 35→38、全部 needs_verify 清零；`check_concept_mesh --strict` 与 `audit_concepts --strict` 零欠账。
  - **最近新闻报道（doc 45）**：汇总量子计算 / 内核 LTS / 开源发行版方向的可信进展，作为架构定位与诚实边界的旁证。
  - **测试床与 initrd（doc 47 + `scripts/quantum-testbed.sh`）**：响应用户「在目录里测试内核」——一键 `debootstrap --components=main` 拉「几乎完全开源自由」的 Debian（默认 bookworm，可换 Devuan daedalus / PureOS），挂载 `/proc /sys /dev` 后 chroot 内执行 `build.sh` 编译 `ARCH=quantum`，并用 `mkinitramfs` 产出 initrd 参考配方。**诚实边界**：量子无引导协议，initrd 仅作参考配方，不是可实际引导的量子镜像。
  - **研究架构定位（doc 44 §8）**：明确「量子是**架构**本身，不是借量子之名去修当前架构」——纯新增、零改 21 个既有架构；列出有意留桩表（gcc 后端 / FPU dump_fpu / 能量模型 / screen_info / 真实 QPU）；记录 EOL 分支的已知链接限制。
  - **版本号五处同步 0.6.79**（`__init__` / pyproject / `main.go` / `console.ts` / `report_viewer.ts`）+ `report_viewer.html` 重新生成；文档见 docs/46《各 LTS 版本补丁矩阵》、docs/45《最近新闻报道》、docs/47《测试床与 initrd》。

- **v0.6.78（2026-10）**
  - **新建「量子架构内核」只读诊断子系统（qarch）**：把「考虑量子物理特性和量子效应以及能量的激发态」落成 **Linux 6.18.57 LTS 基线上真实可编译的 `arch/quantum` 纯新增架构**——`ARCH=quantum` 零修改注册（`arch/Kconfig` 动态 source + `SRCARCH` 默认映射，新目录本身即注册），`diff -rq` 实证仅 3 个既有文件变更（drivers 两处纯追加注册 + 文档索引一行），21 个既有架构目录零改动，x86_64 defconfig 回归正常（4395 项配置）。
  - **构建验收三层如实报告**（scripts/build.sh）：①defconfig 全解析（已过）；②整树编译并链接出真实 vmlinux（已过——EXIT=0 零警告，4608728 字节，15 个 quantum_* 符号在 nm 清单内在位）；③真实量子硬件上运行（不可达——没有量子处理器与其编译器后端，这是硬事实，不虚报）。补丁 `patches/0001` 60 文件段 125KB，对原始 tarball 树 round-trip 洁净回放；git 侧只传补丁+增量镜像，完整树 1.7GiB 凭 fetch_kernel.sh 一键重建。
  - **量子物理语义层**（arch/quantum/kernel/quantum-energy.c，随 vmlinux 一并编译）：离散能级 E_n=n×ΔE、叠加布居（16.16 定点）、相位演化 φ_n=E_n·t、干涉 2·w_a·w_b·cos(Δφ)（256 项定点 sin 表）、测量/坍缩（中断到达即测量，Bell 对关联记账）、T1/T2 退相干、电偶极型选择定则 |Δn|=1、弛豫虚拟光子入 PiLink——`/proc/quantum-energy` 只读自报。
  - **idle= 启动参数**（GRUB/LILO 双样本 arch/quantum/boot/）：`idle=mwait`（默认，基态等待）/ `idle=poll` / `idle=halt`；x86 官方已废弃 idle=mwait 但 6.18.57 仍然可用，quantum 架构显式保留该语义。
  - **落地**：`data/qarch_refs.json` 6 条 + 4 个 kernel.org 官方源（LTS 状态经 kernel.org releases.json 实测核实：6 个长期分支并存）+ `native/qarch.py` 六段只读报告（树/架构/QPU/分发/聚合/能力自检，含镜像一致性与构建产物盘点）+ `tasks/qarch.py` 2 任务 + CLI `qarch` 子命令（overview/tree/arch/qpu/dist/capabilities）+ GUI「量子内核」面板。
  - **组网接入**：subsystems 第 87 项（layer「系统/内核」）；`linkage.py` 两轴（qarch→qstore 印证·4K 页纪律两层互证 / qarch→quantum 闭环·QPU 设备语义成环），孤岛 0、悬空 0；quantum taxonomy 增 qkern 域 4 概念（九域 70 概念），`check_concept_mesh --strict` 与 `audit_concepts --strict` 零欠账。
  - **红线**：qarch 纯只读——绝不执行内核构建、绝不写内核树、绝不加载内核模块；内核内新增代码全部 GPL-2.0（内核树纪律），与本仓 MIT 是分发关系互不传染；vmlinux 已链接与「非量子处理器指令」两条事实都被测试锁住，不退不回。
  - **版本号五处同步 0.6.78** + `report_viewer.html` 重新生成；实测计数 CLI 116→117、GUI 101→102 四库同步；测试 23 项（schema/官方源/回链/树在位与降级双路径/纯新增 diff 实证/镜像一致性/能量模型符号与 idle=mwait 固化/补丁 round-trip/vmlinux 诚实边界锁定/四入口接线/红线 token）；全量回归 1541 passed / 3 skipped / 0 failed；文档见 docs/44《量子架构内核》。

- **v0.6.76（2026-10）**
  - **新建「开源 Windows 分析学习应用」只读诊断子系统**（承接 docs《导入分析学习应用-开源Windows分析学习应用》参考篇，用户拍板「都有」= 三条路径全做）：`data/winternals_refs.json` 12 条 + 16 官方源（*ReactOS* GPL-2.0-or-later / *Wine* LGPL-2.1 / *Ghidra* Apache-2.0 / *x64dbg* GPL-3.0 / *radare2·Cutter* LGPL·GPL / *dnSpyEx* GPL 系 / *Volatility3* GPL-2.0 / *MemProcFS* AGPL-3.0 / *Windows Driver Samples* MIT / *Vergilius*·*Geoff Chappell* 结构参考，8 条挂 needs_verify）+ `native/winternals.py` 五段只读报告（目标环境判定 / 文件系统与目录约定核验 / 运行语言环境 / 分析工具链存在性盘点 / 内核锚点与许可纯度）+ `tasks/winternals.py` 4 任务 + CLI `winternals` 子命令（overview/env/fs/runtime/toolchain/anchors/capabilities）+ GUI「Win分析/逆向」面板。
  - **跨系统先认系统与硬件**（本轮追加的硬约束，落为模块第一原则）：面向其他系统与硬件时，**先判定目标所属环境**（Windows 原生 / WSL / Linux / macOS / Android），再**只按那一套的规矩**去看它的文件系统、目录约定、路径分隔与保留名限制——判为 Windows 摆盘符与 System32/SysWOW64 之分（32 位映像在 SysWOW64，目录名会骗人）、判为 Linux 走 FHS 单根树，两者绝不混用；SystemRoot 只按环境变量或 `GetSystemDirectory` 语义取，绝不硬编码 `C:\Windows`。**运行语言环境两头看**：目标是 PE/PE32+ 还是 ELF 还是 Mach-O、绑哪个 CRT、有没有 CLR；工具链自己则要 JVM（Ghidra）/ Python 3（Volatility3）/ CLR（dnSpyEx）/ 交叉编译器（生成 PE）——两头缺一结论不成立。
  - **红线与许可纯度**：工具链**只问在不在、绝不启动**（只 `shutil.which`，不下载不 attach 不反汇编）；**PCILeech** 一类具备 PCIe DMA 读写物理内存能力的工具（存在即等同内核级控制权）**仅登记存在性与法律边界**，不给任何操作入口；Sysinternals / WinDbg 微软非开源，仅作能力对照不吸收；本仓取向 MIT / Apache-2.0 优先，GPL 与 AGPL 系只登记不引入代码。
  - **组网接入（不欠账且不过度）**：winternals 不是概念中心，故**不**走 radio 那套概念系统四桥手术式同步，改走 `native/linkage.py` 四条联动轴（winternals→reverse 供给工具链生态坐标 / windows→winternals 关联本机面与分析面 / proton→winternals 印证 Wine 兼容层 / compat→winternals 关联兼容层串联），subsystems 第 87 项；孤岛 0、悬空 0，`check_concept_mesh --strict` 与 `audit_concepts --strict` 均零欠账。
  - **版本号五处同步 0.6.76**（`__init__` / pyproject / main.go / console.ts / report_viewer.ts）+ `report_viewer.html` 重新生成；实测计数 CLI 114→115、GUI 99→100（gui.py 实测 100 个窗口方法）四库同步；测试 19 项（schema/官方源域名/needs_verify/六维度回链/**Windows 目标不混 Linux 目录**/五段报告红线/禁执行禁网络/四入口接线）；文档见 docs《导入分析学习应用-开源Windows分析学习应用》第五节。

- **v0.6.75（2026-10）**
  - **新建「无线电技术与标准」只读诊断子系统**：`data/radio_docs.json` 12 条（法规与 SDR 事实均经官方源实检——gov.cn/国务院·中央军委令第672号《无线电管理条例》、工信部令第62号《频率划分规定》、第67号《业余无线电台管理办法》、2019年第52号公告微功率目录、2024无线充电暂行规定、GNU Radio/rtl-sdr/SoapySDR/Hamlib 开源口径）+ `native/radio.py` 六段只读报告（射频开关 rfkill / Wi-Fi 物理能力与 regdom / 蓝牙控制器 / 总线射频器件 / SDR 工具链存在性盘点 / 法规频段口径）+ `tasks/radio.py` 3 任务 + CLI `radio` 子命令（overview/rf/wifi/bluetooth/rf_devices/sdr/regulation/capabilities）+ GUI「无线电/射频」面板。
  - **红线比全项目更严**：只读诊断，**绝不驱动任何真实发射**——不改 regdom/信道/发射功率、不开 monitor 注入、不扫描不配对、不解码他人通信内容、不抓包破解未授权网络、不连校外网做写；法规结论只引官方源（gov.cn/miit.gov.cn）给合规路径，不代办频率许可/台站执照/型号核准；attack 类工具（aircrack-ng 等）仅登记存在性、不提供操作入口。
  - **组网接入（不欠账）**：netsys 加 `radio` 模块（L1 物理面，depends osi，互补 meshnet/netlink/openwrt，RFC 4944/6282/7668/8376/8724 经 rfc_catalog 验证）+ 四桥（→comp:bit8-era 算力底座对照 / →plang:lang:c SDR 实现语言 / →apilab:stdio IQ 样本管道纪律 / →apilab:websocket 频谱实时推送）；comp 反向桥 `bit8-era→netsys:module:radio`（保留 daoxue guidance 根环补丁，走手术式同步不整机重建），40→41 模块 / 66→67 桥接，概念网 `check_concept_mesh --strict` 零欠账。
  - **版本号五处同步 0.6.75**（`__init__` / pyproject / main.go / console.ts / report_viewer.ts）+ `report_viewer.html` 重新生成；测试 17 项（schema/官方源域名/needs_verify/六维度回链/禁执行禁网络/四入口接线）；文档 docs/42 归档。

- **v0.6.74（2026-10）**
  - **完善 DOS/BusyBox/开源 DOS 知识层并整合进概念系统**：v0.6.36 gen-stub 空壳 dos/busybox/dosbox 三个 data 库正式填充（FreeDOS 1.4 官方源实检 + MS-DOS 3.1 历史坐标 + DOSEMU2 + 启动盘前提 + DOS 中断面；busybox 1.37.0/1.38.0 官方版本线；dosbox core/衍生/边界共 12 条知识条目），由 `native/legacy.py` `_load_refs` 真正消费（LEGACY_CHECKS 五维度全部回链真实 key）；schema 齐备化（url/docs/evidence_status）+ needs_verify 诚实挂牌。
  - **新建位宽世代能力矩阵（8/16/32/64 位元）**：`bitwidth_report()` 按世代分档——8 位（MAME/FCEU）/16 位实模式（dosbox/DOSEMU2）/32 位保护模式（qemu-system-i386/wine）/64 位长模式（cpuinfo lm 标志）；本机能力由 cpuinfo flags + 内核位宽 + 模拟层存在性三件事决定；只探测存在性，绝不启动任何模拟器。
  - **PAE 物理地址扩展只读检测 + 开启指引（含 32 位 XP）**：`pae_report()` 读 cpuinfo pae 标志/内核位宽/MemTotal，按官方口径给命令文本——XP/Server 2003 `boot.ini /PAE`（DEP 启用即自动开）、Vista/Win7 `bcdedit /set pae ForceEnable`、Linux `HIGHMEM64G`（选中后 select X86_PAE）；微软官方诚实边界：**XP 全版本物理地址空间上限即 4GB，开 PAE 的意义是硬件 DEP/NX 与热插拔，不是突破 4GB**；红线：只检测 + 给命令文本，不代改 boot.ini/bcdedit/内核命令行。
  - **概念系统整合：comp 扩为第七轴「位宽与寻址世代」**：CONCEPTS 加 6 条（8 位世代/16 位实模式/32 位保护模式/PAE/64 位长模式/遗留 DOS·BusyBox 栈落地，bridges 全部指向 plang arch:x86-64、llvm target:i686-linux-gnu、daoxue principle:zhi-bu-zhi、datong 三概念等合法靶），60→66 概念、磁盘桥接 58→66（guidance 根环补丁按历史模式回注）；按上轮踩坑教训走「重建 + 回注」，组网零欠账。
  - **版本号五处同步 0.6.74** + `report_viewer.html` 重新生成；legacy 任务扩为 5 个（dos/busybox/dosbox/bitwidth/pae）；测试 19 项（schema/官方源域名/needs_verify/回链/禁执行禁网络）。
  - **全量回归 1459 passed / 3 skipped / 0 failed**（legacy 14 项新测试），`check_concept_mesh` 与 `audit_concepts --strict` 零欠账，docs/41 归档。

- **v0.6.73（2026-10）**
  - **黑箱实战：UPX / MinGW / GDB 全链实测**（沙箱只读）：mingw GCC 13 自造 PE32/PE32+ 双样本（237482B/17 节、249562B/19 节）→ UPX 4.2.2 `--best --lzma` 加壳（win64→121050B/48.50%、win32→126378B/53.22%）→ 自写只读扫描器（熵 5.898→7.035、UPX! marker@0x205、节表解析 MZ→PE→COFF→节表）→ GDB 四连（info functions/disassemble/info proc mappings/break）→ strip 前后对照（16000→14472B、熵 1.522→1.235）；wine 启动 PE 失败的事实如实登记，动态侧以 ELF+GDB 为主路径。
  - **新建 `reverse` 黑箱逆向与调试工具链子系统**：`data/reverse_docs.json` 8 条 + `native/reverse.py`（`binary_scan()` 只读扫描器 + `REVERSE_CHECKS` 8 项回链）+ `tasks/reverse.py` 3 任务 + CLI `reverse` 子命令 + GUI「黑箱逆向·UPX/GDB/熵」面板 + 测试 16 项（实测常量冻结 / 禁执行禁网络不变量）。红线：只读诊断不碰未授权目标，GDB 观察不写内存。
  - **概念系统整合：comp 扩为第六轴「黑箱逆向」**：CONCEPTS 加 6 条（UPX 壳识别/熵判据/格式解剖/GDB 四连/符号可见性/自造样本，engineering 全部真落地），54→60 概念、桥接 49→58（含 guidance 根环补丁回注）；四库计数据实测同步（CLI 112→113 / GUI 97→98 / deno 0.6.72→0.6.73）；踩坑归档——带组网补丁的 taxonomy 不整机重建、只手术式同步计数。
  - **版本号五处同步 0.6.73** + `report_viewer.html` 重新生成；联动轴 4 条（llvm→reverse→asm→cert→gmsstd）接入，孤岛清零。
  - **全量回归 1445 passed / 3 skipped / 0 failed**（reverse 16 项新测试），`check_concept_mesh` 与 `audit_concepts --strict` 零欠账，docs/40 归档。

- **v0.6.72（2026-10）**
  - **新建 `hmosstd` 鸿蒙标准与合规知识库**（第四生态标准库，与 androidstd 国内 / gmsstd GMS / fdroidstd 免 GMS 并列）：`data/hmosstd_standards.json` 11 条 + `native/hmosstd.py` 只读层 + `tasks/hmosstd.py` 3 任务 + CLI `hmosstd` 子命令 + GUI「鸿蒙标准」面板 + 测试 13 项。覆盖 PIPL 上位法（告知-同意/敏感信息单独同意/跨境/个人权利）→ AppGallery 上架要件（软著/备案/隐私政策/首启同意时序）→ 工信部 App 备案（171 号文）→ 权限 APL 分级与敏感权限 → NEXT 隐私指示器 → HUKS 密钥库（密钥不出 TEE + Attestation）→ 加解密框架/证书链/TEE → API 版本兼容（@ohos→@kit、canIUse 降级）→ 未成年人保护（14 岁分界）→ 后台任务与网络规范 → XTS/Acts 兼容性测试。
  - **鸿蒙侧知识体系合龙**：hmosstd（对齐什么标准）+ hmos_ecosystem（生态怎么干活）+ harmony/harmony_hdc/harmony_device/kaihong（设备与工程只读探测）三层分工闭合；联动轴 4 条接入，孤岛清零，omni 真缺口 0 项。
  - **版本号五处同步 0.6.72**：`__init__` / pyproject / `main.go` / `console.ts` / `report_viewer.ts` + concepts 四库三字段（`deno_report_viewer_version` / `cli_subcommands` 111→112 / `gui_windows` 96→97）；`report_viewer.html` 重新生成。
  - **全量回归 1429 passed / 3 skipped / 0 failed**（hmosstd 13 项新测试），docs/39 归档。

- **v0.6.71（2026-10）**
  - **导入分析学习四个 HarmonyOS 仓库并回灌**（承接 #312/#313 模式的又一轮四仓导入）：
    - **鸿蒙生态知识库 `hmos_ecosystem` 子系统**（`data/hmos_ecosystem_docs.json` 8 条 + `native/hmos_ecosystem.py` 只读层 + `tasks/hmos_ecosystem.py` 3 任务 + CLI `hmoseco` 子命令 + GUI「鸿蒙生态」面板 + 测试 16 项）：HAP 工程与 deviceTypes 判定 → NEXT 侧载工具链（Auto-Installer/HoKit/HapInstaller/HapStore）→ 第三方生态版图（2026-10 快照 110 款）→ HarmonyOS/OpenHarmony 版本线（NEXT 分水岭）→ 开发工具链（Deveco/方舟/ArkTS/仓颉/ArkUI）→ HiSpark 开发板与 HDF → 官方 Codelabs 构建块图谱（53 demo，git tree 实测）→ FA→Stage 范式演进对照。
    - **gmsstd 知识库 10→15 条**：补 GMS 设备侧部署实施层——三件套包名地图（gsf/gms/vending）、HarmonyOS 4.x 原生三件套部署路径（MicroG 跳板 + 50% 进度禁 gsf 保 FCM）、MicroG 能力边界、FCM 推送保活、ADB 多用户包管理；检查项 11→15；社区源逐条 needs_verify。
    - 弱网实况如实记录：fenwii/OpenHarmony（765MB 文档站）与 codelabs（124MB，29M 处断流）git/tarball 直连均不可达——以 GitHub tree API 全量文件树（codelabs 1.5MB JSON）+ raw 抽样（fenwii README 634 行全文 + DistributeNewsETS config.json 实证）达成同等结构分析深度。
    - 接入联动轴 4 条（hmos_ecosystem → harmony_hdc/gmsstd/distro + kaihong → hmos_ecosystem），孤岛清零；omni 真缺口 0 项。
    - **CLI 假计数修复**：回灌后 CLI 字面量漏改两处（hmoseco 打印「6 条」实为 8、gmsstd 打印「10 条」实为 15），改动态引用 `len(ENTRY_KEYS)`/`len(REFS)` 并加回归测试守死字面量复活。
    - 全量回归 **1416 passed / 3 skipped**；全过程归档 `docs/38`。
  - **版本号五处同步 0.6.71**（`__init__` / pyproject / `main.go` / `console.ts` / `report_viewer.ts`）+ concepts 三库 `deno_report_viewer_version` 字符串键同步；`report_viewer.html` 重新生成。

- **v0.6.70（2026-10）**
  - **量子子系统 omni 四件套收口**：`tasks/quantum.py`（只读任务 `quantum_vm_report`：就绪自检 + 环境报告 + 架构基座演示 + 命令行入口指引）+ `data/quantum.json`（标准知识库 17 条：OpenQASM 3 / QIR / ISO·IEC 4879 / IEEE 7130 / ITU-T Y.3800 / ETSI GS QKD 014 / FIPS 203·204·205 / Nielsen & Chuang + bell·GHZ·teleport·Grover·BV·Shor 六份原始文献），registry 归位——**omni 真缺口自此归零**（`sysweeper omni gaps` 复核：真缺口 0 项，13 项设计如此）；任务动作经 runner 真实调用全通过。
  - **版本号五处同步 0.6.70**（含 `report_viewer.html` 重新生成）；修复 datong/baigong 两库 `deno_report_viewer_version` 停留 0.6.62 的字符串漂移（三库六字段统一 0.6.70——`--check` 的 int 键比对盖不住字符串键，本次人工核出并修正）。
  - **i18n 补册**：`extract_task_strings` + `gen_zh_tw` + `make_mo` 全链重跑（70 条历史遗留 + 本次新串，zh_TW 2519 条全量 OpenCC）；测试 **1399 passed / 3 skipped**（+7 项：量子接线 5 + omni zipapp 一致性 2）。
  - **修复 zipapp 内 omni 自检误报**：`wiring()` 原用 pathlib 直读包内源码文本，`.pyz` 里 `sysweeper.__file__` 指向 zip 内部路径致读不到——82 项被全量误报成「缺 cli/gui/task/data」（实测谎报 69 项真缺口，源码树实为 0）。改为走 `importlib.resources`（与知识库加载同一条路径，复用 `_zipres` shim），zip 与磁盘同结论；pyz 端到端测试新增「真缺口 0 项」断言。

- **v0.6.67（2026-10）**
  - **三个标准知识库子系统同日落地（androidstd / gmsstd / fdroidstd）**——把「检查国内标准以及 GMS 标准」的指令落成只读知识库，并用 F-Droid 补上「拿不到 GMS 也能分发」那条通道：
    - **国内标准·App 隐私合规（androidstd）**：PIPL 上位法 → 四项国标（GB/T 35273-2020 / 41391-2022 / 42574-2023 / 34975-2017）→ 四部门规定（认定方法 / 39 类必要个人信息范围 / 信息服务管理规定 / App 备案）→ TC260 实践指南（自评估 / 系统权限），**13 条全部经官方源实检**（openstd/cac/miit/gov/tc260）。
    - **GMS 兼容与 Play 标准（gmsstd）**：CDD/CTS/VTS/STS 兼容体系 → GMS 兼容与许可 → Play 三件套（Integrity API verdict 分层 / App Signing 2048·4096 密钥 / 2026-08-31 起 targetSdk API 36）→ Data safety 披露 → 安全公告补丁体系，**10 条除 STS 细节外全部官方源实检**（STS 官方单页未实检到，社区整理逐条标 `needs_verify`）。
    - **F-Droid 免 GMS 分发标准（fdroidstd）**：存储库模型（免账号、能下载即可安装）→ 收录政策（FLOSS）→ 反特征体系（Ads/Tracking/NonFreeNet/NonFreeDep/KnownVuln 等）→ fdroiddata 配方 → 可复现构建 → 仓库协议（索引签名/指纹信任）→ F-Droid vs Play 对照，**10 条经 GitHub/GitLab API 与官方文档检索快照实检**（f-droid.org 直连不可达，取官方中文/韩文文档检索快照 + 仓库层 API 数据：fdroidclient GPL-3.0 3222 stars / fdroiddata 358 stars）。
  - **三库同一范式**：data JSON（按语义 key 组织 8 字段）+ native 只读层（零参可调报告 + 检查清单逐条回链 key）+ tasks（5 个指引类任务）+ 四入口接线（CLI 子命令 / GUI 面板 / subsystems 登记 / registry 归位）+ linkage 三轴接入主干（androidstd→android 门控、gmsstd↔fdroidstd 印证、fdroidstd→android 供给）——孤岛/悬空保持 0/0，omni 真缺口保持 0。
  - **Android APK 工程补全**：ProbeEngine 探针 9 项补至约 20 项（字体粗细/高对比度/放大镜/无障碍服务清单/三项动画缩放/触感反馈/音效/亮度/锁屏超时/夜间显示，全部 API 门控 + try/catch 降级），版本号 0.5.23；CI 修复 `setup-android@v3` 的 Google 已移除 `tools` 包导致 APK 构建失败的问题（改手动装官方 commandline-tools），HarmonyOS HAP 三连空排队收敛为仅 workflow_dispatch。
  - **版本号统一**：三处同步至 `0.6.67`（pyproject / `sysweeper.__version__` / `src/go/main.go`）。

- **v0.6.40（2026-10）**
  - **时空与全维度管理器子系统（chrono）：量子/计算机原理 + 时间/空间/施时空组合/未来兼容只读透镜 + 全时空全维度循环往复管理器**。以量子理论及计算机原理为只读观测透镜，观察时间维（时钟/时区/生命周期）、空间维（存储/地址空间/NUMA）、施时空组合维（事件-资源因果链）、未来兼容维（标准 EOL/后量子）；`cycle_dimensions()` 以 round-robin 周而复始遍历全部维度（时间/空间/施时空组合/未来兼容/量子透镜 + 既有子系统维度共 11 维），每维一视同仁只读——「循环往复，周而复始，亦复如是」。四入口接线齐全：`native/chrono.py` + `tasks/chrono.py`（4 个只读+指引任务）+ `subsystems` 登记 + CLI `chrono` 子命令（含 `--env`）+ GUI「时空与全维度」面板；linkage 加 3 轴、sysmap 加 3 关系消除孤岛。
  - **docker-easyconnect 学习回灌（全选 4 项）**：① 新增标准库版本巡检 CI（`scripts/audit_standards_eol.py` + `.github/workflows/audit-standards-eol.yml`，只读不写、每周巡检 57 个标准知识库、绝不自动改库）；② `remote` 新增「连接保活与重连」只读任务（借鉴其自动保活/重连，绝不改连接配置、绝不注入重连进程）；③ 安全基线注记（对外服务默认拒绝入站、端口只绑 localhost，见「安全基线」章）；④ 学习报告入库存档（`learn-docker-easyconnect.md`）。
  - **版本号统一**：七处同步至 `0.6.40`（修正 `report_viewer.ts` 残留 `0.6.38`）；`report_viewer.html` 重新生成（source-sha 已记录）。

- **v0.6.41（2026-10）**
  - **导入 trae/agent-z8YrX1 分支并分析学习应用（源代码允许的整体都纳入）**：经 GitHub API 定位并下载该分支 tarball 比对，确认其为 v0.6.35 基线、净新增 10 种语言单文件只读组件（bun/c/elixir/erlang/java/kotlin/ruby/rust/swift/zig，其中 java/ruby/rust 既有、其余 7 种为净新增）；已复制进 `src/<lang>/` 并统一版本号至 `0.6.40`、扩展 `langdetect.LANGUAGES` 注册表（有则自动启用、无则隐藏）。提炼可复用纪律：跨语言「同口径只读组件」范式（纯标准库、零依赖、只降级不 panic、版本号同步、统一 `version`/`sysinfo`/`help` 子命令）、语言注册表集中化、文档与代码同源。学习报告存档 `learn-trae-branch.md`。
  - **虚拟机子系统（virt）：让整体在不同虚拟机都能正常运行**。只读识别本工具自身运行在裸金属/KVM/VMware/VirtualBox/Hyper-V/Xen/WSL/容器哪一层，给出各只读探针的「可用/退化」结论（受限 VM 退化为概念观测、裸金属全开），确保整体在任意虚拟化环境只降级不崩溃。四入口接线齐全：`native/virt.py` + `tasks/virt.py`（2 任务）+ `subsystems` 登记 + CLI `virt` 子命令 + GUI「虚拟机环境」面板；linkage 加 3 轴、sysmap 加 3 关系消除孤岛。绝不装增强工具/改 QEMU-crosvm 配置/加载内核模块。
  - **软件包子系统（packages）：按系统/硬件/相关软件包检测包管理器 + 包规范合规审计**。按系统/硬件检测包管理器（apt/dnf/pacman/brew/winget/choco/apk/scoop/zypper），只读审计「安装/卸载/配置/设置优化」四类操作的包规范符合性，并给出相应层级应对。与 pkgmgr（缓存清理）互补：pkgmgr 清缓存、packages 审计包规范合规。四入口接线齐全：`native/packages.py` + `tasks/packages.py`（5 任务）+ `subsystems` 登记 + CLI `packages` 子命令 + GUI「软件包规范审计」面板；linkage 加 3 轴、sysmap 加 3 关系消除孤岛。任何 install/uninstall/configure/optimize 一律只给层级应对指引，不代执行。
  - **版本号统一**：七处同步至 `0.6.41`；`report_viewer.html` 重新生成（source-sha 已记录）。

- **v0.6.39（2026-10）**
  - **外部设备连接与兼容子系统（peripheral）：整体引入星闪标准 + 触控技术支持 + 外部设备支持与兼容**。与 electrical/durability 并列，形成「外部设备连接 → 供电环境 → 设备自身」三维度长期保障运行框架。四件事均**只读识别 + 只给规范指引，绝不刷固件/装私有驱动/挂钩输入流/改写 PD 协商**。
    - **整体引入星闪标准（NearLink / SparkLink）**：`introduce_nearlink` 给出空口（SLB 高速率/高精 对标 Wi-Fi、SLE 低功耗 对标 BLE）、特性（μs 时延/一拖上千/Polar 码抗干扰/μs 精同步）、接入须配对与身份校验、与 BLE/Wi-Fi 2.4G 共存调度；无线外设优先按星闪选型。
    - **触控技术支持与兼容**：`read_touch_devices` 只读解析 `/proc/bus/input/devices` 判多点触控协议（MT-A/MT-B、精确触控板），缺驱动给官方指引；绝不采集按键/触控内容。
    - **外部设备支持与兼容**：`read_usb_devices` 只读盘点 USB/USB4/USB-C PD 与 HID 即插即用，出 e-Marker 线缆/PD 3.1 EPR 240W/USB4 Alt Mode/IEC 62680 强制 USB-C/HID 即插即用选型指引。
    - **四入口接线齐全**：新增 `native/peripheral.py` + `tasks/peripheral.py`（4 个只读+指引任务，category=maintenance）+ `subsystems` 登记 + CLI `peripheral` 子命令（含 `--env`）+ GUI「外部设备连接与兼容」面板；linkage 加 3 轴、sysmap 加 3 关系消除孤岛，omni 接线完整度 45/65 → 46/66。
  - **深化 electrical：环境温度接入外部温湿度计 + 回路级动态负载门控**。`read_external_env_sensor` 复用 peripheral 识别结果（绝不挂钩数据流、绝不伪造读数）；`adapt_by_env` 消费 ambient_temp_c（>35°C 降载错峰）/ humidity（>80% 防蚀）；新增纯函数 `dynamic_load_gating`——对 overload_risk 回路结合断路器额定与实测连续负载，按「80% 木桶短板」阈值门控（超阈即门控掉高发热连续负载、错峰、限容），把自适应从定性建议推进到按读数闭环（只给指引不代执行）。
  - **版本号统一**：六处同步至 `0.6.39`；`report_viewer.html` 重新生成（source-sha 已记录）。

- **v0.6.38（2026-10）**
  - **供电与环境安全子系统（electrical）：把电气火灾科普落成「设备长期保障运行」的供电环境维度自适应**。与「设备长期使用保护（durability）」并列——durability 看设备自身（电池/温度/SMART/uptime），electrical 看设备**外部与内部供电环境**（回路质量/接地/负载），二者共同支撑「依据设备外部和内部环境自适应、保持长期保障运行」。
  - **知识库驱动的风险识别**：把电气火灾科普提炼的 **8 类隐患**（局部高阻发热 P=I²R、铜铝原电池腐蚀、金属蠕变松脱、串联电弧/AFDD、木桶短板过载、接地+RCD、接点老化、可燃底座）落成 `data/electrical_safety_docs.json`，引用 GB/T 16895（等同 IEC 60364）/ GB/T 2099.1 / GB 13955 / IEC 61008·61009（RCD）/ GB/T 31143（AFDD）等标准。据用户声明的供电环境标签（old_wiring/copper_aluminum/no_ground/wood_base/loose_outlet/overload_risk/high_dust）识别「事故前兆链条」与风险级，每条回链知识库 key。
  - **自适应运行指引（纯函数引擎）**：铜铝/无接地/旧线/松动/木座 → 严禁在该回路接高发热连续负载并指引重拉全程阻燃铜线；木座/松动 → 立即断开上级回路；温度偏高 → 联动 durability 热管理降载。所有写操作（换线/装 RCD/AFDD/换插座）一律**只给规范指引，不代执行**——严守只读红线，也契合「用户 GUI 控制」：电气改造由持证电工按规范施工，是否施工始终由用户确认。
  - **四入口接线齐全**：新增 `native/electrical.py` + `tasks/electrical.py`（4 个只读+指引任务，category=maintenance）+ 模块开关 `subsystems` 登记 + CLI `electrical` 子命令（含 `--env`）+ GUI「供电与环境安全」面板；omni 接线完整度 44/64 → 45/65。
  - **版本号统一**：六处同步至 `0.6.38`（修正 `report_viewer.ts` 残留 `0.6.35`）；`report_viewer.html` 重新生成。

- **v0.6.35（2026-10）**
  - **全能全知自检（新增 `omni`）：让工具自述自己的边界**。全知不是宣称什么都知道——那叫吹牛；真正的全知是三层边界：**① 我知道什么**（登记能力 + 接线完整度）／**② 我知道我不知道什么**（本机探不到的，需 `--deep` 实跑）／**③ 我不知道我不知道什么**（本工具压根没有探针的域）。第三层最容易被忽略也最要命：一个只会报「已处理 N 项」的工具永远不会告诉你「生物识别、GNSS 定位、摄像头内容、文件正文、通信内容这些维度我一行都没探」。本轮把它写成**显式边界声明**（12 个域，每条带理由与替代路径），把沉默的盲区变成声明过的边界。
  - **顺带暴露「半截能力」**：登记进统一清单 ≠ 真的接全了。自检按 **CLI 子命令 / GUI 面板 / 任务定义 / 知识库** 四处入口盘点，实测 61 项里四件套齐全的只有 22 项——其余是「总览看得见、入口没接全」的半截能力。判定按 **key → module → 入口别名** 三级回退，避免把共用入口（`netlink` 覆盖 netauth/reshare、`mesh` 覆盖 meshchat/distcompute、`kaihong` 覆盖 harmony、`import` 覆盖 importio）误报成欠账——**自检不能自己报错**。
  - **向全能补真欠账**：补齐此前「登记了却没入口」的五项——CLI `linux` / `compress` / `emergency`（GUI 此前已有 `show_emergency`）、GUI「Linux 发行面」「压缩空间分析」「单板机(SBC)」面板；新增 `tasks/compat.py`（3 个任务）与 `data/compat_docs.json`（Wine / Proton / DOSBox / WSL / Vulkan / busybox 权威出处）。半截能力 16 → 12 项。
  - **元能力入图**：把 `subsystems`（统一清单）与 `linkage`（联动连轴）也登记为子系统，加上 `omni` 共三项元能力彼此联动（清单供给自检、自检与联动互相印证两种欠账视角）。统一清单 61 → **64 项**，联动轴 96 → **99 条**，孤岛与悬空仍为 **0 / 0**。
  - **接线**：CLI `omni`（`coverage` 默认 / `all` 三层总览 / `blind N` 半截能力清单，均可加 `--deep`）；GUI「全能全知自检」面板（一键自检 + 实跑已知未知）；`models.py` 的 `KEYWORD_STANDARDS` 补 compat 与 omni 两组标准出处。
  - **测试**：新增 `tests/test_omni_v0635.py`（20 项：接线覆盖全部登记项、共用入口不误报、边界声明含敏感维度、三层报告分段、本轮补齐的入口确实已接、新增后仍无孤岛悬空）。
  - **版本号统一**：五处同步至 `0.6.35`；`report_viewer.html` 重新生成。

- **v0.6.36（2026-10）**
  - **闭环：让「全知」长出可执行性**。v0.6.35 让工具能精确说出自己哪儿不知道，本轮更进一步——把缺口分成**「设计如此」与「真缺口」**两类，真缺口给**具体补法**（补哪个文件、加哪个入口），让「全知」从「能说出缺什么」前进到「能说出怎么补」。
  - **设计如此 ≠ 半截能力**：`subsystems` / `linkage` / `omni` / `settings` / `importio` / `snapshot` / `distjob` 这 7 项是元能力/机制类，四件套里的 task/data 本就不适用——把它们单列说明，不再污染「四件套齐全」比例（此前 35% 里混着它们）。其余 14 项「缺 task+data」也据此归类，真缺口清单只列诊断类能力。
  - **补掉那 1 个真 GUI 缺口**：omni 自检暴露 `fonts`（字体与文本规范化）只差 GUI 面板——CLI 命令、任务、知识库都在。本轮补 `gui.show_fonts` 面板并登记底部按钮，**CLI / GUI 入口现已 64/64 接全**。
  - **按需脚手架 `omni gen-stub KEY`**：为真缺口的 data 项生成**知识库占位 JSON**（纯数据，不碰代码）。默认 dry-run 只回显内容不落盘；`--write` 才创建；**已存在则跳过不覆盖**；未知 key / 完整项 / 设计如此项都安全拒做，绝不自动填充任何正文或引用未核实来源。
  - **接线**：CLI `omni` 新增 `gaps`（补齐清单）与 `gen-stub KEY [--write]` 两种模式；GUI「全能全知自检」面板补「补齐清单」视角、「字体与文本规范化」面板入列。`models` / `subsystems` / `linkage` / `compat` 不变。
  - **测试**：新增 `tests/test_remediation_v0636.py`（9 项：7 项 by-design 正确归类、真缺口不含 by-design、fonts 已接全不再出现在缺口、gen-stub 对未知 key / 完整项 / by-design 安全拒做、dry-run 不落盘、write 后幂等不覆盖、CLI `gaps` 与 `gen-stub` 模式可跑）。
  - **版本号统一**：五处同步至 `0.6.36`；`report_viewer.html` 重新生成。

- **v0.6.37（2026-10）**
  - **修掉「全知自检」自身的失真（调试）**。v0.6.36 的 `omni gaps` 跑出 33 项「真缺口」，但其中混了两类误报：① data 检查用 `<key>*.json` 前缀，漏掉**语义命名**的知识库——`netlink`→`link_protocols.json`、`thirdparty`→`net_interop_refs.json` 被错判成「缺 data」；② 借 module 名「继承」——harmony 三子项（kaihong/harmony_hdc/harmony_device）误借 `harmony_docs.json` 判成「有 data」。修法：新增 `DATA_FILE_ALIASES` 显式映射 native 模块**实际加载**的 data 文件，`has_data(key)` 改为「先查别名 → 回退 key 前缀 → 不再借 module 继承」。
  - **运行期数据不再算缺口（分类优化）**。把 `webnews` / `plugins` / `plugins_allowlist` / `distcompute` / `reshare` / `meshchat` 这 6 项运行期数据 / 机制类加入 `BY_DESIGN_KEYS`（data 是运行期生成、或本身即知识源、或代码侧白名单，非包内静态知识库），不再污染「真缺口」比例。
  - **用脚手架批量补全真诊断缺口（补全）**。修正后真缺口收敛为 26 项。其中 **24 项**属「诊断维度应有知识库但缺 data」，用 v0.6.36 造的 `omni gen-stub KEY --write` 一键补全占位知识库（`osi` / `dnshealth` / `tor` / `zerotier` / `netauth` / `wsl` / `proton` / `virtgpu` / `browser` / `jdk` / `kmod` / `firmware` / `modules` / `distro` / `edge` / `imagefmt` / `dos` / `legacy` / `busybox` / `dosbox` / `livemedia` / `emergency` / `linux` / `compress`），**data 知识库 30 → 54**。
  - **接线完整度跃升**：四处齐全 **44/64（68%，原 ≈36%）**，CLI / GUI 入口 64/64，知识库(data) 51/64。剩余真缺口只剩 **7 项缺 task**（netlink / netauth / jdk / kernel / kmod / firmware / modules，有原生报告但没注册进 TASKS，进不了扫描/执行流程）——属逻辑承载变更，留作 v0.6.38 明确范围，不在本版赶工。
  - **测试**：`tests/test_remediation_v0636.py` 扩 `BY_DESIGN` 集合（+6）并新增别名准确性 / 真缺口纯净度两组断言；全量 pytest 通过。
  - **版本号统一**：五处同步至 `0.6.37`；`report_viewer.html` 重新生成。

- **v0.6.34（2026-10）**
  - **兼容层串联（新增 `compat` 子系统）**：proton / dosbox / wsl / virtgpu / legacy 此前是四份各说各话的报告，用户真正想知道的只有一件事——**「我这台机器能不能跑那个平台的软件、缺哪一层」**。本轮把它们串成**一条四层依赖链**：宿主底座（arch/kmod/distro）→ 设备与图形（virtgpu）→ 兼容运行时（proton/dosbox/wsl/legacy）→ 供给（pkgmgr），按**场景**给结论（跑 Windows 程序 / 跑 DOS 程序 / 在 Windows 上跑 Linux / 跑遗留嵌入式）。**缺任一层即判「缺层」而非「已装」**——上层能不能用，取决于下层给不给得了。
  - **踩住一个真陷阱：不适用 ≠ 已就绪**。本机是 Linux 时 `wsl_report` 返回 `ok=True`，但正文写的是「未识别为 WSL 环境，其余维度不适用」——直接把 ok 当就绪，结论就**反了**。compat 因此把三态分开：`ready` / `missing`（真缺层）/ `na`（本机不适用），并配了专门的回归用例钉死这条判据。
  - **串联：从「有边」升级到「能沿边走」**。联动轴此前只是关系图，现在能沿轴走通：`linkage.path(A, B)` 给 A→B 的最短串联链（含每跳性质与说明）、`reachable(A)` 给影响范围、`longest_chain()` 给全图最深串联（当前 **10 跳**：iOS→安卓→Linux→发行版→兼容层→WSL→网络→DNS→Tor→ZeroTier）、`chains_report()` 给串联体检与串联深度 Top。新增**「串联」性质**（同一条依赖链的上下游），兼容层四层即它的首个实例：arch →(门控) compat →(串联) pkgmgr。
  - **图形：联动图看得见、也带得走**。新增 `linkage.graph()`（结构化图数据）/ `layout()`（分层布局，纯函数可单测）/ `svg()`（**纯标准库生成**的 SVG，零依赖、可离线看、可直接贴网页）/ `ascii_graph()`（命令行分层邻接图）。GUI 新增「联动图」窗口：分层布局、边按性质着色（供给绿 / 门控红 / 印证蓝 / 闭环紫 / 串联橙 / 关联灰）、点越大联通度越高、**点节点看它的入边与出边**、一键导出 SVG。CLI `linkage --graph / --svg PATH / --path A B / --chains`。
  - **接线**：CLI `compat` 子命令；GUI「联动图」「兼容层串联」两个面板；统一清单 60 → **61 项**，联动轴 87 → **96 条**，孤岛与悬空仍为 **0**。
  - **测试**：新增 `tests/test_compat_v0634.py`（22 项：四层模型形状、场景三态、**不适用≠已就绪**用例、串联链首尾相接、未知 key 返回空、图数据/布局/SVG/ASCII 形态、新增后无孤岛悬空）。
  - **版本号统一**：五处同步至 `0.6.34`；`report_viewer.html` 重新生成。

- **v0.6.33（2026-10）**
  - **整合统合合并：补齐六项「有模块、无登记」的假嵌入**。上一轮把 `durability/remote/cert` 收进统一清单后，逐模块比对发现 native 层仍有六个模块一直在干活、却没登记进 `native/subsystems.py`——进不了统一开关、也进不了 `sysmap` 总览。本轮全部收编：**Linux 本机发行面**（新增 `linux_report()` 零参聚合：发行版 / 包管理器 / journal 体积 / 根分区用量）、**系统快照/对比**（新增 `snapshot_report()` 零参摘要，只采基线指标不重复跑全量探针）、**压缩空间分析**、**字体与文本规范化**、**鸿蒙 HDC 设备桥**、**鸿蒙设备信息**。统一清单 54 → **60 项**，`sysmap` 实测「已登记 60 · 已开启 60 · 异常 0」。
  - **联动连轴：新增 `native/linkage.py`**。此前 sysmap 的关系图只回答「谁和谁有关系」，不回答三件更要命的事：这条边**是什么性质**、有没有**接不上的**、边有没有**写错**。本模块一次补齐——每条联动轴标 **供给 / 门控 / 印证 / 闭环**（既有关系表归并为「关联」），并做两项体检：**孤岛检测**（登记了却一条边都没有 = 假嵌入）与**悬空轴自检**（端点 key 写错会静默失效）。全部 87 条轴、纯计算只读、不跑任何诊断函数、不写任何状态。
  - **首跑即抓出真实欠账并清零**：孤岛检测第一次跑就报出 **8 个孤岛**，其中**跨平台 OS 五面（Windows / macOS / BSD / Unix / iOS）一条联动边都没有**——登记了五年、却从来没接上主干。本轮按「供给/门控/印证」逐条补轴（安卓↔Linux 内核、iOS↔macOS↔Unix↔BSD 同源链、Windows↔桌面/存储/跨平台对照、第三方互联↔网络、资讯↔设备保护、遗留总览↔DOS/busybox…），**孤岛与悬空轴双双归零**（联通覆盖率 60/60）。
  - **接线**：CLI `linkage`（`--stats` 打印结构化统计）、GUI「联动连轴」面板（一键体检 + 能力自检）。sysmap 关系表同步补 24 条边，总览图与新联动轴保持一致。
  - **测试**：新增 `tests/test_linkage_v0633.py`（19 项：六项登记与函数可调用、轴端点合法、性质白名单、无孤岛、无悬空、联通度自洽、关闭开关后生效轴减少、关系表 label 可映射、新项进入 sysmap 探测项）；开关用例一律隔离配置落点到 `tmp_path`，不污染真实用户配置。
  - **版本号统一**：`__init__.py` / `pyproject.toml` / `src/go/main.go` / `src/deno/console.ts` / `src/deno/report_viewer.ts` 同步至 `0.6.33`；`report_viewer.html` 重新生成。

- **v0.6.32（2026-10）**
  - **新子系统「嵌入整体」**：把 v0.6.30-31 新增的 `durability`（设备长期使用保护）、`remote`（远程接入审计）、`cert`（证书与加密）登记进 `native/subsystems.py` 的**统一子系统清单**（单一事实源）。登记即自动生效于 CLI `--enable/--disable/--list-subsystems`、`subsystems` 子命令、GUI「模块开关」面板与 `sysmap` 系统总览——三者从此与既有 40+ 子系统一样可独立开/关、可被总览串起来。
  - **sysmap 关系边补齐**：新增 5 条耦合——证书↔远程接入（SSH/SFTP 强度即证书链与加密库）、证书↔设备保护（资产保护段吸收证书/TPM 状态）、设备保护↔硬件本征（传感器读数来源）、设备保护↔网络接口（链路 down 即入保护清单）、远程接入↔网络接口（明文风险只在不可信网成立）。
  - **测试**：新增 `tests/test_subsystems_v0631.py`（登记字段 + 报告函数零参可调用 + sysmap 探测项包含 + 关系边端点存在 + 总览报告含新节点）。
  - **版本号统一**：同步至 `0.6.32` 并重生成 `report_viewer.html`。

- **v0.6.31（2026-10）**
  - **证书与加密开源整合子系统（cert）**：整合**类似 OpenSSL 的开源项目**（OpenSSL / LibreSSL / BoringSSL / GnuTLS，允许接入作加密底座）与**最低内置硬件证书**——TPM 2.0 硬件信任根、IEEE 802.1AR IDevID 设备身份证书（私钥锁硬件、不可导出）、平台密钥库（Keychain/Secure Enclave/CNG/Android Keystore），以及**各种证书**（X.509 RFC 5280 / ACME 自动续期 / PKCS#12 / FIDO2-WebAuthn）。只读审计：EOL 加密库、未启用 TPM、临近过期证书、密钥库不可达。**绝不读私钥、绝不解密、绝不改配置**；输出无障碍纯文本（`a11y_cert_summary`，屏幕阅读器可直接朗读），与既有无障碍子系统统一口径。CLI `cert`、GUI「证书与加密」面板、任务 `cert_*`、知识库 `data/cert_docs.json`。
  - **整体感知环境天气气候 + 保护关键资产/个人数据/通信能力（durability 扩展）**：新增 `read_weather_climate()`（主板 hwmon / lm-sensors 只读感知天气气候，缺即降级外部接入）与 `read_comms()`（网卡 operstate 只读感知链路，绝不外发）两项传感器；`auto_climate_tags()` 自动推导环境标签并入保养包络；新增纯函数 `protect_assets()`，融合**证书状态**（`cert.cert_status_summary()`）与**通信状态**，生成「关键资产 / 个人数据 / 通信能力」保护清单——备份优先、无 TPM 即建议启用硬件信任根、EOL 加密库即建议升级、临近过期证书即建议 ACME 续期、链路 down 即排查。`durability` 报告新增资产保护段，实现「传感器感知 → 优化 → 保护」闭环。
  - **版本号统一**：`__init__.py` / `pyproject.toml` / `src/go/main.go` / `src/deno/report_viewer.ts`（含 VERSION 常量 + schema version + 头部注释）同步至 `0.6.31`；`report_viewer.html` 重新生成（含源模板 SHA 标记）。
  - **测试**：新增 `tests/test_cert.py` / `tests/test_durability_protect.py`（文档完整 + 跨平台安全降级 + 引擎纯函数 + 资产保护断言）；仓库护栏测试通过。

- **v0.6.30（2026-10）**
  - **设备长期使用保护子系统（durability）**：只读采集电池/温度/存储 SMART/运行时长/环境传感器（读不到即标「本机未提供」，绝不伪造），按「使用量 + 期望使用年限 + 环境标签」由知识库（IEC 60529 / ASHRAE / 厂商电池指南 / NVMe SMART）推导充电上限·温湿预算·清灰与备份周期，并给分项健康评分、保养清单与优化建议，每条回链知识库。写操作（充电阈值/清灰/拆机）一律只给 OEM 官方工具指引，不代执行。CLI `durability`（含 `--usage/--years/--env`）、GUI「设备长期使用保护」面板、任务 `durability_*`。知识库 `data/durability_docs.json`（天气/气候/材料/耐久/保养/水汽异物）。
  - **远程接入与传输客户端只读审计（remote）**：覆盖 telnet / ssh（OpenSSH）/ filezilla / putty，各自按**自身协议与接口**核对（SSH=RFC 425x 加密；Telnet=RFC 854 明文；FileZilla=FTP/RFC959 明文 vs SFTP vs FTPS/RFC4217；PuTTY=Windows SSH）。只读探针 + 安全审计（telnet 明文 / ssh 口令登录与 root 直登 / filezilla 明文 FTP + 弱口令存储），**绝不读解密口令、绝不改 sshd_config、不替你停 telnetd**；加固（停用 telnet / sshd 改公钥 / filezilla 用 SFTP + 主密码）只给官方指引。CLI `remote`、GUI「远程接入审计」面板、任务 `remote_*`。知识库 `data/remote_clients_docs.json`。
  - **版本通道（channels）：stable 常态稳定版 / lts 长期支持版 / fresh 尝鲜版**：用户可在 CLI 与 GUI「版本通道」面板里选择，并据「使用量 / 期望年限 / 环境」给个性化推荐；选定仅写入 `settings.json` 作更新检查标记，**工具绝不自动切换或升级你的环境**——是否更新始终由用户确认。GUI 全模块面板新增「设备长期使用保护」「远程接入审计」入口。
  - **版本号统一**：`__init__.py` / `pyproject.toml` / `src/go/main.go` / `src/deno/report_viewer.ts`（含 VERSION 常量 + schema version + 头部注释）同步至 `0.6.30`；`report_viewer.html` 重新生成（含源模板 SHA 标记）。
  - **测试**：新增 `tests/test_durability.py` / `tests/test_remote.py`（文档完整 + 跨平台安全降级 + 引擎纯函数 + CLI 可跑）；仓库护栏测试通过。

- **v0.6.15（2026-10）**
  - **导入分析学习应用（第二批，5 仓库 + 1 份 AI 系统卡）**：microsoft/wsl2-linux-kernel、mdn/browser-compat-data、ZoranWong/MINUX3、arehnman/yttrium-virtio-gpu、python-dnspython（Arch 打包）、Claude Haiku 5.5 System Card。红线不变——只读、不执行、不引入 LLM 运行时。
  - **WSL 环境只读诊断（wsl）**：基于 wsl2-linux-kernel 视角，核验是否 WSL、版本 1/2、内核对照主线、根文件系统驱动(virtiofs/9p)、systemd 与 interop。CLI `wsl`、GUI「WSL 诊断」、任务 `wsl_report`。
  - **虚拟化与 GPU 虚拟化只读诊断（virtgpu）**：基于 yttrium-virtio-gpu，核验 hypervisor 标志、virtio 设备、virtio-gpu（Venus 协议免直通加速）、DRM 显示卡后端。CLI `virtgpu`、GUI「虚拟化/GPU」、任务 `virtgpu_report`。
  - **浏览器与引擎检测 + Web 兼容知识参考（browser）**：基于 mdn/browser-compat-data，探测已装浏览器/引擎(Blink/Gecko)版本，并给「特性→支持等级」结构性子集。CLI `browser`、GUI「浏览器/引擎」、任务 `browser_report`。
  - **DNS 解析健康度（dnshealth）**：基于 python-dnspython 打包视角，聚焦解析链路（nameserver 来源 / systemd-resolved stub / 一次良性解析延迟），与 `network.nm_resolved` 互补。CLI `dnshealth`（默认带探测，`--no-query` 关闭）、GUI「DNS 健康」、任务 `dnshealth_report`。
  - **MINIX3 微内核架构对照 + System Card 范式吸收**：docs 沉淀微内核 vs 宏内核对照，并产出 `docs/Sysweeper系统能力卡.md`（把本工具自身做成「能力/局限/护栏/用途/评估」可审计一页纸）。
  - **文档**：`docs/导入分析学习应用-多仓库2.md`、`docs/Sysweeper系统能力卡.md`。

- **v0.6.14（2026-10）**
  - **导入分析学习应用多仓库（Proton 已落地）**：按用户指令整体分析 7 个仓库——ValveSoftware/Proton、microsoft/litebox、elie222/rakazo、milind-soni/OpenMausBot、CopilotKit/openmuse、CopilotKit/OpenDots、Anil-matcha/open-dots。全项目红线约束下分两类「应用」：① 直接落地为代码模块（最贴切的 Proton）；② 吸收架构原则（litebox 的「接口面削减/隔离」+ 5 个 AI 项目的「隔离/审计/可接管/本地优先」）沉淀为诊断隔离理念，不引入 LLM 运行时。
  - **游戏/应用兼容层只读诊断（proton）**：吸收 Proton（Steam Play 兼容层 = Wine+DXVK+VKD3D-Proton+wine-mono+Steam Runtime）原理，只读核验「机器能否跑 Windows 游戏/程序」的前提——Vulkan 支撑栈(loader+ICD)、32 位 i386 运行时、NT 同步原语(esync/fsync/NTSync，含 /dev/ntsync 与内核版本比较)、Steam Runtime 与 Proton/Wine 安装，逐项给结论与修复提示。CLI `proton`(report/caps)、GUI「兼容层诊断」按钮、任务 `proton_report` 全部接入。
  - **文档**：新增 `docs/导入分析学习应用-多仓库.md`（7 仓库整体分析 + 融合结论）。

- **v0.6.13（2026-10）**
  - **以 OSI 七层模型为骨架的整体网络诊断（osi）**：检索 ISO/IEC 7498-1 / ITU-T X.200、各层 RFC（1122/1123、791/2460/792、9293/768、8446/7858/8484、1035），把本机网络栈按 L1 物理→L7 应用**只读、结构化**摸一遍——接口/载波/速率、MAC/MTU/卸载、IP/路由/防火墙、监听/拥塞/连接跟踪、会话保活/隧道、TLS/DoT·DoH、DNS/可达性。复用 `network` 只读报告，红线同 webnews/edge：不写地址/路由/防火墙，不连校外网做写操作；要探外网用 `osi probe --url <http(s)>`（显式、可审计）。
  - **发行版文档与发行注记（distro）**：复用 `linux.detect_distro`（LSB /etc/os-release），并把「识别」推进到「可读」——只读本机 `/usr/share/doc` 的 NEWS.Debian / changelog.Debian.gz（含 .gz 自动解压），列出可用注记来源；`distro notes --pkg <包名>` 读某包本地变更日志。红线：不 `apt-get changelog`（联网）、不改源、不写文件。
  - **接口/总线枚举（hardware.bus_report）**：读 `/sys/bus/*` 列出已注册总线（PCIe/USB/platform/i2c/spi/acpi…）与设备驱动绑定，把「接口文档」落到可读设备树；PCI/USB 设备驱动抽样。
  - **接入无头 CLI 与 GUI**：新增 `osi`（动作 `report`/`layer`/`probe`/`caps`）与 `distro`（动作 `report`/`notes`/`caps`）子命令；GUI 顶部新增「OSI 网络诊断」「发行版与注记」按钮。
  - **任务注册**：`tasks/osi.py`（`osi_report`）、`tasks/distro.py`（`distro_notes`）接入 registry；全只读、risk=low。
  - **文档**：新增 `docs/OSI七层网络诊断与发行版注记.md`。

- **v0.6.12（2026-10）**
  - **新能力接入无头 CLI**：v0.6.11 的 webnews / edge / mesh 节点发现此前只在图形界面里，现补齐命令行子命令，无 GUI 环境也能用——
    - `webnews`（动作：`report`/`fetch`/`knowledge`/`sources`/`caps`）：查看能力、配置来源、抓资讯、读缓存知识点；`fetch --source <url>` 可临时追加 http(s) 来源（带 8s 超时与 2 MiB 上限，失败如实报「未能获取」）。
    - `edge`（动作：`report`/`caps`）：单板机只读探测（板型/温度/降频欠压/启动盘）+ 能力自检；非 SBC 降级为「未识别为单板机」。
    - `mesh`（动作：`nodes`/`announce`/`protocol`）：查看网内在线节点、广播本机能力通告（SW-OFFER1）、协议与安全命令白名单说明。
  - **修复版本一致性门**：`pyproject.toml` 版本号此前停留在 `0.6.10`，与 `__version__` 不一致；现已统一为 `0.6.12`（测试 `test_version_consistent_with_pyproject` 通过）。

- **v0.6.11（2026-10）**
  - **新闻/网站优化资讯系统（webnews）**：只读聚合你配置的 http(s) RSS/网页 → 解析条目 → 按平台/分类（Windows/macOS/Linux/Android/网络/安全/隐私/硬件/存储/电池）抽取优化知识点 → XDG 缓存。抓来的只是文本，**无执行路径**，优化建议由你决定做不做；GUI 新增「新闻与优化资讯」窗口。
  - **新硬件：单板机/ARM SBC（edge）**：只读探测设备树板型、thermal 温度、Broadcom 降频/欠压位、启动盘类型（SD/eMMC/NVMe），给出带因果的建议；非 SBC 优雅降级为「未识别为单板机」。
  - **节点发现注册表（meshchat）**：补齐「谁能接活」——能力通告（SW-OFFER1）自动登记 + TTL（10 分钟）过期剔除，配套 `mesh_offer` 任务（广播自己 + 看网内在线节点）。
  - **新语言框架（i18n）**：登记 ko_KR / es_ES / pt_BR / it_IT / vi_VN / id_ID 共 6 种 UI 语言（脚手架就绪、随构建生成 .mo；ko_KR 已填分类标签与新任务标题样例），`i18n.list_ui_languages()` 给出可用语言清单。加一种 UI 语言是「数据 + 翻译」，不是代码改动。

## 以系统原生接口解决问题（设计核心）

为「不麻烦、靠系统本身」，工具把各平台**官方/系统级接口**封装成 `sysweeper/native/`
一层，探测与执行都优先走接口，而非堆shell 字符串：

| 平台 | 原生接口（native/ 下） | 用途 |
|---|---|---|
| **Windows** | `ctypes` → `SHGetKnownFolderPath` / `GetTempPathW` / `GetDiskFreeSpaceEx` / `SHEmptyRecycleBinW`；`winreg` 读注册表；`powercfg` / `DISM` / `netsh` / `fsutil` / `sfc` / `Get-CimInstance`（v0.5.13 文档层 `data/windows_docs.json`） | 真实路径解析、磁盘用量、清空回收站、版本探测、电源/组件/网络/文件系统官方接口 |
| **Linux** | LSB 规范文件 `/etc/os-release`（与 `lsb_release` 同源）+ `shutil.disk_usage` + `journalctl` | 发行版识别、磁盘、日志清理 |
| **macOS** | `libc.sysctlbyname`（ctypes 调 libSystem）+ `sw_vers` / `launchctl` / `defaults` | 内核状态、版本、系统服务 |
| **BSD** | `libc.sysctlbyname` + `/etc/os-release` + 各 BSD 包管理（pkg/pkg_add/pkgin） | 内核态读取、发行版识别、包清理 |
| **Unix** | System V：`/etc/release`（Solaris/illumos）+ IPS `pkg` + `svcs`/`zpool`/`kstat`/`logadm`/`fmadm`/`dladm`+`ipadm` 只读探测（v0.5.14 文档层 `data/unix_docs.json`） | 发行版识别、IPS 历史清理、服务/池/内核统计/日志/故障/网络官方接口 |
| **Android** | `adb`（Android Debug Bridge）：settings/pm/am/dumpsys/svc/wm/logcat 只读探测（v0.5.15 文档层 `data/android_docs.json`）+ `and_tune_*` 官方写接口深度调优 | 设备级缓存/trim/设置/统计/日志/显示官方接口，只往安全方向写 |
| **iOS** | `libimobiledevice`（ideviceinfo/ideviceinstaller/idevicesyslog/idevicecrashreport/idevicediagnostics/idevicebackup2/idevicepair/idevicename/idevicedate/idevicesetlocation/ideviceimagemounter）：只读探测（v0.5.16 文档层 `data/ios_docs.json`）+ `ios_tune_*` 官方写接口深度调优 | 备份/归档/清日志/同步时间/清定位/归一化设备名/优雅重启/挂开发者镜像，只往安全方向写，绝不 remount |
| **OpenWrt** | UCI（`/etc/config/*` 解析 + `uci show`）、opkg/apk 状态文件、netifd/`ubus call`、procd `/etc/init.d`、防火墙 `/etc/config/firewall`、无线 `/etc/config/wireless`、DHCP `/etc/config/dhcp`、存储 `/etc/config/fstab`、LuCI/rpcd ACL、`/etc/openwrt_release`+`/tmp/sysinfo`（v0.5.20/21 文档层 `data/openwrt_docs.json`） | 路由器/嵌入式 Linux 的只读接口：固件/板型、配置审计、包盘点、网络、服务、防火墙、无线、DHCP、存储、构建系统参考；高危写操作（sysupgrade/包管理/uci set/服务启停）为 opt-in 指引，只给命令文本绝不执行 |
| **硬件** | `smartctl`(S.M.A.R.T.)/`lspci`/`lsusb`/`fstrim`+`/sys/power/state`（ACPI） | 按 T13/ATA、UEFI Forum、PCI-SIG、USB-IF 标准读取 |
| **跨平台** | `native/common`：`~/.cache`/`/tmp` 体积、`os.walk` 大目录、`resolvectl`/`nscd`/`mDNSResponder` DNS 刷新提示 | 跨 OS 通用的缓存/临时/目录清点与优化指引（XDG Base Directory / POSIX） |
| **网络/ITU** | `sysctl`/`iw`（Linux）；其余为指引 | 按 RFC / IEEE / ITU-T 标准施加网络调优（默认关闭） |
| **字体/字符** | `fc-list`/`fc-cache`（fontconfig）；其余为指引 | 按 Unicode 18.0.0 / ISO-IEC 10646、OpenType(ISO 14496-22)、W3C WOFF 标准读取 |
| **OpenJDK/JVM** | `java -version` / `-XshowSettings:properties` / `--list-modules` / `-XX:+PrintFlagsFinal` / `jps -l` / `jcmd -l`（v0.5.22） | JVM 版本与发行版、JPMS 模块系统、GC/JIT 标志实际取值、诊断工具可用性、JFR 状态；**系统属性只挑白名单键输出**，含 password/token/secret 的键一律显示「<存在敏感值，已隐藏>」 |
| **内核 module/firmware/plugin(s)** | `/proc/modules`、`/sys/module/*`（含 `parameters/`）、`modinfo`、`/lib/firmware`、`/sys/class/firmware`、`/sys/kernel/btf/vmlinux`、`/sys/fs/bpf`、`/proc/cmdline` 的 `module.blacklist`（v0.5.22） | 已加载模块盘点、模块参数读取（只读）、固件库与已加载固件、**eBPF 能力面**（BTF/vmlinux 是否存在 = 能否用 BPF CO、bpffs pin 数、kprobe 可挂载面）、模块黑名单、电源状态与唤醒计数 |
| **设备长期使用保护（durability）** | 只读传感器：`/sys/class/power_supply/BAT*/uevent`（电量/温度/循环/健康）、`/sys/class/thermal/*/temp`、`smartctl`/`nvme` 工具名、`/proc/uptime`、`lm_sensors`（环境温湿度，缺则降级外部接入）；知识库 `data/durability_docs.json`（IEC 60529 / ASHRAE / 厂商电池指南 / NVMe SMART / 材料与保养）（v0.6.30） | 跨平台只读采集 + 知识库驱动保养目标包络与健康评分；写操作（充电阈值/清灰/拆机）只给 OEM 官方工具指引，不代执行 |
| **远程接入与传输客户端（remote）** | `ssh`/`telnet`/`filezilla`/`putty` 可用性探测、`/etc/ssh/sshd_config` 与 `~/.ssh/config` 关键项（只读）、`~/.ssh/*.pub` 公钥、`sitemanager.xml` 协议取值（只读，绝不读解密口令）、23 端口监听探测；知识库 `data/remote_clients_docs.json`（RFC 425x / RFC 854 / RFC 959 / RFC 4217）（v0.6.30） | 远程 Shell 与传输客户端只读安全审计（telnet 明文 / ssh 口令登录 / filezilla 明文 FTP + 弱口令存储）；加固（停用 telnet / sshd 改公钥 / filezilla 用 SFTP + 主密码）只给官方指引，绝不改配置 |
| **证书与加密（cert）** | `openssl version` 只读查询、`certtool`/`gnutls-cli` 探测、`/sys/class/tpm*`（TPM 2.0 硬件信任根，只读）、平台密钥库可达性（Keychain/CNG/NSS/Keystore，不读口令）、设备身份证书探测（IEEE 802.1AR IDevID）、证书到期只读扫描（`openssl x509 -enddate`）；知识库 `data/cert_docs.json`（RFC 5280 / RFC 8555 / RFC 7292 / TPM 2.0 / IEEE 802.1AR / FIDO2）（v0.6.31） | 整合 OpenSSL/LibreSSL/BoringSSL/GnuTLS 开源加密栈 + 硬件信任根 + 各种证书的**只读审计**（EOL 加密库 / 未启用 TPM / 临近过期 / 密钥库不可达）；**绝不读私钥、绝不解密、绝不改配置**，升级加密库·启用 TPM·ACME 续期只给官方指引；输出无障碍纯文本 |
| **联动连轴（linkage）** | 纯计算：只读 `subsystems` 统一清单与 `sysmap` 关系表，**不调用任何诊断函数、不写任何状态**（v0.6.33，v0.6.34 加串联与图形） | 每条联动轴标注**供给 / 门控 / 印证 / 闭环 / 串联**（既有关系表归并为「关联」），并做**孤岛检测**（登记了却没接上主干）与**悬空轴自检**（端点写错会静默失效）；**串联**（`path`/`reachable`/`longest_chain`）让关系图能沿边走通；**图形**（`graph`/`layout`/`svg`/`ascii_graph`）出分层布局与纯标准库 SVG。CLI `linkage --stats/--chains/--path/--graph/--svg`、GUI「联动连轴」与「联动图」面板 |
| **兼容层串联（compat）** | 只调既有零参只读报告（proton / dosbox / wsl / virtgpu / legacy / arch / kmod / distro / pkgmgr），**不安装、不启用、不改配置**（v0.6.34） | 四层依赖模型 + 场景结论（跑 Windows 程序 / 跑 DOS 程序 / 在 Windows 上跑 Linux / 跑遗留嵌入式）；**缺任一层判缺层、不适用不判就绪**；缺什么只给官方路径。CLI `compat`、GUI「兼容层串联」面板、任务 `compat_*`、知识库 `data/compat_docs.json` |
| **全能全知自检（omni）** | 纯计算：只读统一清单与本仓库源码文本盘点接线，**不调用外部命令、不采集任何信息**（v0.6.35，v0.6.36 加补齐清单与按需脚手架） | 三层边界自述：覆盖面与接线完整度（四处入口盘点，key→module→别名三级回退避免误报）/ 本机探不到的已知未知（`--deep`）/ **无探针域的边界声明**（生物识别、GNSS 定位、音视频内容、文件正文、通信内容等 12 个域）。**补齐清单**（`gaps`：缺口分「设计如此 / 真缺口」两类，真缺口给具体补法）/ **按需脚手架**（`gen-stub KEY`：为真缺口 data 项生成知识库占位 JSON，dry-run 不落盘、`--write` 才创建、已存在跳过不覆盖）。CLI `omni`、GUI「全能全知自检」面板 |

- 全程**纯标准库**，零第三方依赖；在任意平台 import 不崩溃（平台专属调用都做惰性守卫，拿不到就优雅降级）。
- 动作新增 `native` 通道：`command` 写成 `"module.func"`（如 `windows.empty_recycle_bin`），由 `runner` 直接调起对应系统接口。

## 设计原则

- **按「系统 + 版本」匹配**：每个任务声明 `platform` 与 `min_ver`/`max_ver`，只对该范围生效。例如「Win10 终止支持提醒」只在 Windows 10 出现。
- **风险分级**：`low` / `medium` / `high`。`clean` 可用 `--risk` 限制上限（如 `--risk low` 只跑低风险）。
- **动作通道**：`shell`（桌面端真执行）、`adb`（安卓设备）、`manual`（iOS / 需图形点选项，只给指引）、`native`（调系统原生接口）、`python`（预留）。
- **注意事项与提醒**：每个任务可附 `caveats`（风险）与 `notes`（注意事项），`notes` 子命令单独查看。
- **零依赖**：仅用 Python 标准库，七平台都可直接跑，无需 `pip install`。

### 语言运行时自动启用（不强求安装）

某些清理/优化功能用特定语言实现（Ruby 去重、Go 模块缓存、Node 缓存、Perl 日志…）。
工具在运行时用 `shutil.which` 探测这些语言运行时，**有则自动启用、没有就自动隐藏**，
绝不要求用户事先安装。用 `langs` 命令可查看当前环境装了哪些语言、哪些功能被自动启用：

```bash
python -m sysweeper langs
```

任务上用 `requires_lang` 字段标记依赖；`registry.applicable` 默认只保留「已装该语言」的任务。

### 硬件标准参考（按标准文档行事）

清理/维护项对照权威硬件标准文档（见 `data/hardware.json`），用系统原生接口读取，
工具缺失时自动降级为指引、不强求安装：

- **S.M.A.R.T.**（INCITS T13 / ATA8-ACS）—— `smartctl` 读磁盘健康
- **ACPI**（UEFI Forum）—— 读 `/sys/power/state` 核对睡眠态
- **PCI / PCIe**（PCI-SIG）/ **USB**（USB-IF）—— `lspci -nn` / `lsusb` 读类代码
- **SSD TRIM**（T13 DATA SET MANAGEMENT）—— `fstrim` 维护

```bash
python -m sysweeper hardware      # 原生读取 + 标准引用，不改系统
```

### 网络协议 / ITU 标准开关（默认关闭，需选择 + 确认）

网络调优项对照 RFC / IEEE / ITU-T 标准（见 `data/network_standards.json`），
统一 `opt_in=True`：**默认不出现、不执行**；必须用 `toggles` 查看，并在 `clean` 时
加 `--opt-in` 选择具体项、加 `--yes` 确认后才会执行——符合「默认关闭、需选择和确认」。

```bash
python -m sysweeper toggles                              # 列出全部开关 + 标准引用
python -m sysweeper clean --category network --opt-in --yes --apply   # 确认后全开
python -m sysweeper clean --only net_ipv6_privacy --opt-in --yes --apply  # 只开一项
```

另有 **网络栈深度调优**文档跟踪（v0.5.9）：`network` 子命令只读探测 iproute2 / ethtool /
eBPF(bpftool) / tc / conntrack / NetworkManager-resolved / RPS-XPS 缩放，并列出 `net_*` 深度
调优任务（ethtool 卸载/中断聚合、RPS/XPS、fq_codel 抗缓冲膨胀、conntrack 上限、NAPI backlog、
XDP/eBPF、IRQ 亲和、RFS），每一项都走该工具**自身的官方接口**（ethtool -K / sysfs / tc qdisc /
sysctl / bpftool），绝不套用协议层的 sysctl 写法，也不做 rm/dd 类破坏性操作。

```bash
python -m sysweeper network     # 网络栈深度调优：文档跟踪 + 只读探测 + net_* 任务
python -m sysweeper clean --only net_tc_fq --opt-in --yes --apply   # 仅对出口挂 fq_codel（需确认）
```

另有 **基线快照与差异对比**（v0.5.10）：把跨子系统的只读探测聚合成可序列化的 JSON 快照，
并在两次扫描间做可追溯对比，让「前后对比」从屏幕上的一闪而过变成可归档、可复核的产物。
全程只读——只读取文件（`/proc/meminfo`）+ 复用各子系统的 `*_report` 只读探测，绝不写系统、
绝不跑清理/调优命令。磁盘/内存给出可比对数值，各子系统探测给出「可用/不适用」与详情，
`diff` 时既能看数值增减，也能看「某探测从可用变不可用」。

```bash
python -m sysweeper snapshot capture --out before.json   # 生成基线快照（聚合磁盘/内存 + 各子系统只读探测）
# ... 跑一次优化/清理 ...
python -m sysweeper snapshot capture --out after.json    # 生成对比快照
python -m sysweeper snapshot diff --a before.json --b after.json   # 输出前后差异（磁盘/内存/探测）
python -m sysweeper snapshot show before.json           # 查看某份快照原文
```

GUI 中「快照/对比」面板提供同样的：生成快照（选保存路径）、或选两份快照做差异对比。

**v0.5.17 横切深化：扫描流程内嵌基线快照。** 点「扫描分析」/「执行选中项」时，主流程会**每次自动采集一份只读基线快照**（聚合磁盘/内存指标 + 各子系统只读探测），并**与上次扫描自动对比**（展示探针状态变化 + 磁盘/内存数值增减），日志框内即时可见；底部新增「扫描快照对比」按钮可弹出本会话内最近两次扫描的差异详情。无需再到独立「快照/对比」窗口手动选文件即可追溯「前后变化」。

**v0.5.18：链接协议导入 + 多设备自组网/人机交互 + 按网络隐私验证 + 同人资源共享 + 无障碍多系统适配。**

**v0.5.19：导入第三方网络互联互通/硬件优化/开源下载 并合并到共享资源 + 许可证单独归档。**

1. **导入第三方网络互联互通方案并合并到共享资源**（`thirdparty` 子命令 + `tasks/thirdparty.py`，文档层 `data/net_interop_refs.json`）：把
   [p2wlan](https://github.com/yhan-sun/p2wlan)（P2P 虚拟局域网，MIT）、
   [dae](https://github.com/daeuniverse/dae)（eBPF 透明代理，AGPL-3.0）、
   [gfw-pac](https://github.com/zhiyi7/gfw-pac)（PAC 生成器，Apache-2.0）、
   [v2rayN](https://github.com/2dust/v2rayN)（Xray/sing-box 客户端，GPL-3.0）
   作为「同人设备网络互联互通」的可选方案**只读登记**——汇入 `net_reshare` 同人资源共享模型，
   只用于本人**授权**网络，**绝不盗用他人网络互联互通能力**。
2. **硬件优化（由用户选择）**：导入 [DLSS5-Swapper](https://github.com/rakanki911/DLSS5-Swapper)
   （DLSS5 一键安装/调优/还原，MIT），作为 GPU 硬件优化的可选工具登记；会改写游戏内超分 DLL，
   需用户逐游戏确认且自动备份原文件，**仅在本人设备、本人拥有的游戏上操作**。
3. **引入开源下载软件 + CDN/P2P 开关**：导入 [aria2](https://github.com/aria2/aria2)
   （多协议多源下载器，GPL-2.0），提供两套开关语义 —— CDN 开关（走 HTTP/FTP 镜像源多连接分片）、
   P2P 开关（走 BitTorrent/Metalink 多源），仅用于本人有权获取/分享的资源的。
4. **许可证单独归档**（`licenses/` 文件夹）：将文档提及的 MIT / Apache-2.0 / GPL-2.0 / GPL-3.0 /
   AGPL-3.0 各放一个文件（含官方全文链接与核心义务），并写 `licenses/README.md` 引用来源——
   逐条列出每个导入仓库的名称、仓库链接、许可证 SPDX、许可证全文链接与用途。
5. **安全护栏默认开启**（`any_interop_policy`）：同人登录的多设备可共享硬件资源
   （CPU/GPU/NPU/TPU/内存/网络），个人数据与关键资产数据（凭据/密钥/钱包/通讯录/文档）一律不共享；
   任何以「共享」之名索取密码/密钥/证件原件的均为盗用风险，应拒绝。

1. **多种网络链接协议**（`netlink`，文档层 `data/link_protocols.json`）：按各协议**自身的规范**登记
   TCP（RFC 9293）、UDP（RFC 768）、蓝牙 RFCOMM（Bluetooth SIG / ETSI TS 07.10）、串口（RS-232）、
   BLE（GATT/ATT）、802.15.4（IEEE 低速率无线个域网），并只读探测本机是否具备对应能力。
2. **多设备自通信 + 人机交互**（`netlink serve/discover/msg`）：启用网络后，多于 1 台设备可自己
   通信 —— UDP 广播发现邻居 + TCP 可靠命令通道；命令通道只有 **info/ping/probe/msg 四个只读安全
   命令**，**绝不执行对端发来的任意命令**（越权命令一律降级为 msg 错误回显）。
3. **按网络维度的隐私验证**（`netauth`）：不同网络用**个人输入的两个以上信息**作验证（如姓名+
   身份证号，或邮箱+手机号）；**原始信息不作保存**，只落盘 `salt + PBKDF2 派生令牌 + 字段标签`；
   下次启动重新输入同样信息即可**重新连接**。不同网络用不同 salt，防跨网关联。
4. **同人登录的多设备资源共享**（`reshare`）：同一人登录的多台设备共享 **CPU / 内存 / GPU /
   NPU / TPU / 网络**；**个人数据与关键资产数据（凭据、密钥、钱包、通讯录、文档）一律不共享**，
   以防他人盗用你的网络互联互通能力。认定同一人用 `netauth` 的跨设备身份指纹（相同验证信息 +
   相同共享口令 + 同一网络维度 ⇒ 同一指纹），他人指纹一律拒绝并记审计；只落盘指纹与授权种类。
5. **无障碍多系统适配**（`a11y --platform`，文档层 `data/a11y_docs.json`）：Windows 讲述人
   （UI Automation / MSAA）、macOS VoiceOver（NSAccessibility AX）、Linux ORCA（AT-SPI2）、
   Android TalkBack（AccessibilityService / adb settings secure）、iOS VoiceOver、
   鸿蒙屏幕朗读（AccessibilityExtensionAbility）—— 各自按自己的接口只读探测，非当前系统降级为指引。

```bash
python -m sysweeper netlink                 # 链接协议注册表 + 本机能力 + 自组网就绪态
python -m sysweeper netlink serve           # 启用本地自组网（>1 台设备自己通信）
python -m sysweeper netlink discover        # 发现本网段内的其他设备（只读）
python -m sysweeper netlink msg --text hi  # 设备间人机交互消息（仅回显）
python -m sysweeper netlink auth           # 按网络隐私验证（原始信息不保存，可重连）
python -m sysweeper netlink reshare        # 同人资源共享（算力共享，数据不共享）
python -m sysweeper a11y --platform windows   # 指定系统的无障碍探测（多系统适配）
```

另有 **Windows 原生接口**文档跟踪（v0.5.13）：此前唯独 Windows 缺文档层，本轮补齐——
`windows` 子命令只读探测 Win32 API（`GetDiskFreeSpaceExW`）、注册表（winreg 读
HKLM/HKCU）、WMI/CIM（`Get-CimInstance`）、powercfg、DISM、存储感知策略、传递优化缓存、
Windows 更新检测时间，并给出 9 个接口的**协议 + 接口**文档引用；同样另有一组官方写接口
深度调优（`win_tune_*`，8 项全 opt_in）：`fsutil behavior set`（NTFS 少写元数据 / 关 8.3
短名）、`netsh int tcp set global`（RFC 7323 窗口自动调优 / RSS / RFC 3168 ECN）、
`netsh advfirewall`（防火墙**只开不关**）、`powercfg /change`、`/h /type reduced`
（缩减休眠文件但**保留快速启动**，比 `/hibernate off` 温和）。

```bash
python -m sysweeper windows    # Windows：文档引用 + 只读探测 + 官方写接口清单 + win_* / win_tune_* 任务
python -m sysweeper clean --only win_tune_tcp_autotuning --opt-in --yes --apply   # 只开一项
```

另有 **Unix（System V）原生接口**文档跟踪（v0.5.14）：Windows / macOS / BSD 之后，
把同一模式补到 Solaris / illumos——同样**只按它自己的协议与接口**，一条都不套 Linux 的
`/proc/sys`、sysctl 或 systemd 写法。9 个接口的文档引用（IPS `pkg` / SMF / ZFS /
`/etc/release` / `logadm` / `kstat` / Zones / FMA / `dladm`+`ipadm`），9 个只读探测，
外加 9 个官方写接口（`unix_tune_*` 任务 8 项，全 opt_in）：

- **IPS**：`pkg refresh`（只刷 publisher 目录与本地元数据，不装不卸）、`pkg fix`
  （按官方 manifest 还原被改动的文件，不动用户数据）。
- **SMF**：`svcadm enable svc:/system/fmd:default`（开 FMA 自愈守护，**只开不关**）、
  `svcadm clear <fmri>`（清 maintenance，FMRI 由 `svcs -a` 自动探测——只清状态、不做启停）。
- **ZFS**：`zfs set atime=off`（读文件不再回写访问时间戳，减写放大）、
  `zfs set compression=lz4`（低 CPU 换空间，只压缩新写入块）、`zpool scrub`（官方校验，
  有冗余时自愈；池名自动探测）。
- **日志 / 网络**：`logadm -r`（按 `/etc/logadm.conf` 官方轮转，只归档不删正在写的日志）、
  `ipadm set-prop -p ecn=active tcp`（RFC 3168 ECN；Solaris 11 起 TCP 可调项由 `ipadm`
  管，**取代 ndd**，属性随接口配置持久化）。

```bash
python -m sysweeper unix      # Unix：文档引用 + 只读探测 + 官方写接口清单 + unix_* / unix_tune_* 任务
python -m sysweeper clean --only unix_tune_zfs_atime --opt-in --yes --apply   # 只开一项
```

另有 **Android 原生接口**文档跟踪（v0.5.15）：Windows / macOS / BSD / Unix 之后，
把同一模式补到 **Android 自身系统接口**。Android 是 managed OS，PC 端只能经官方
**ADB** 向设备发指令，每个接口都与桌面完全不同，逐个**只按自身协议与接口**核对，
绝不套注册表/plist/sysctl、也**绝不 `adb remount` 后改系统分区**（越权，本工具不做）。
9 个接口的文档引用（`adb` / `settings_provider` / `pm` / `am` / `dumpsys` / `getprop` /
`svc` / `wm` / `logcat`），9 个只读探测（需设备已连且授权），外加 8 个官方写接口
（`and_tune_*`，全 opt_in，**只往安全方向写**）：

- **settings**：`settings put global window/transition/animator_animation_scale 0`
  （关窗口动画，界面更跟手，可随时改回 1）。
- **pm**：`pm trim-caches 2147483647`（释放全部应用可丢弃缓存，**只清缓存不删数据**）。
- **svc**：`svc wifi enable`（开 Wi-Fi，**只开不关**，绝不替用户切断网络）。
- **dumpsys**：`batterystats --reset` / `netstats --reset`（清零电量/流量统计，**只清计数**）。
- **logcat**：`logcat -c`（清空 logd 环形日志缓冲，**只清日志不碰文件**）。
- **am**：`am kill-all`（杀全部后台进程，**只后台、前台不受影响**）。
- **wm**：`wm size reset` / `wm density reset`（显示恢复设备默认，修复误设导致的
  界面不可点——**只 reset 不自定义设具体分辨率**）。

```bash
python -m sysweeper android    # Android：文档引用 + 只读探测 + 官方写接口清单 + and_* / and_tune_* 任务
python -m sysweeper clean --only and_tune_trim_cache --opt-in --yes --apply   # 只开一项（需设备已连且授权）
```

另有 **iOS 原生接口**文档跟踪（v0.5.16）：Windows / macOS / BSD / Unix / Android 之后，
把同一模式补到 **iOS 自身系统接口**。iOS 沙盒严格，PC 端只能经 **libimobiledevice**
向**已配对且已信任**的设备发指令，每个接口都与其它平台完全不同，逐个**只按自身协议与
接口**核对，绝不套注册表/plist/sysctl、也**绝不 `remount` 改系统分区**（越权，本工具不做）。
10 个接口的文档引用（`libimobiledevice` / `lockdown` / `usbmuxd` / `installation_proxy` /
`afc` / `crashreport` / `syslog_relay` / `diagnostics` / `mobilebackup2` /
`mobile_image_mounter`），9 个只读探测（需设备已连且信任，未连则优雅降级），外加 8 个
官方写接口（`ios_tune_*`，全 opt_in，**只往安全方向写**）：

- **mobilebackup2**：`idevicebackup2 backup`（整机备份到本地，**单向、只进不出**，绝不 restore）。
- **installation_proxy**：`ideviceinstaller -a`（归档用户 App，**保留数据、可逆**，绝不 `-U` 卸载）。
- **crashreport**：`idevicecrashreport -e`（拷贝+删除崩溃报告，**仅诊断日志、可逆**）。
- **idevicedate**：`idevicedate -s`（设备时间同步为主机时间，可逆）。
- **idevicesetlocation**：`idevicesetlocation clear`（清除模拟定位，恢复真实 GPS）。
- **idevicename**：`idevicename`（归一化设备名，设置中可随时改回）。
- **idevicediagnostics**：`idevicediagnostics restart`（优雅重启释放内存，无数据丢失，标 medium）。
- **mobile_image_mounter**：`ideviceimagemounter`（挂开发者磁盘镜像启用开发者服务，可逆）。

```bash
python -m sysweeper ios        # iOS：文档引用 + 只读探测 + 官方写接口清单 + ios_* / ios_tune_* 任务
python -m sysweeper clean --only ios_tune_backup --opt-in --yes --apply        # 只开一项（需设备已连且信任）
```
```

另有 **macOS / BSD 官方接口深度调优**（v0.5.12）：继 v0.5.11 补全两个平台的只读探测后，
再补上它们**自己的官方写接口**（同样绝不套用 Linux 的 `/proc/sys` 或 systemd 写法）：

- **macOS**（`macos_tune_*`，9 项）：`pmset -a hibernatemode`（按 `sysctl hw.model`
  自动判别笔记本/台式机）、`pmset -a standbydelayhigh/low`、`sysctl -w kern.maxfiles`、
  `networksetup -setdnsservers <服务> empty`（官方取值，DNS 交回 DHCP）、
  `tmutil thinlocalsnapshots / 1g`（APFS 官方瘦身，不碰备份磁盘历史）、
  `defaults write com.apple.dock` + `killall Dock`、`softwareupdate --schedule on`、
  `spctl --master-enable`（Gatekeeper **只开不关**）、`diskutil verifyVolume`（只校验不修复）。
- **BSD**（`bsd_tune_*`，8 项）：`sysctl -w net.inet.tcp.rfc1323`（RFC 7323）、
  `net.inet.tcp.recvspace/sendspace`（**只上调不降低**，不覆盖内核自动调优）、
  `kern.maxfiles/maxfilesperproc`、`zpool set autotrim=on`、`zpool scrub`、
  `vfs.zfs.arc_max`（按 `hw.physmem` 自动算比例）、`pfctl -e -f /etc/pf.conf`
  （**只启用不停用**）、`periodic daily`。

全部默认关闭（`opt_in`），须显式选择 + 确认才执行；原生写接口一律零参数可调用
（机型/网络服务/池名/内存均自动探测），非目标平台优雅降级为文档指引。

```bash
python -m sysweeper macos     # macOS：文档跟踪 + 只读探测 + 官方写接口清单 + mac_* / macos_tune_* 任务
python -m sysweeper bsd       # BSD：同上（bsd_* / bsd_tune_*）
python -m sysweeper clean --platform macos --opt-in --yes --apply            # 全开（需确认）
python -m sysweeper clean --only bsd_tune_zfs_autotrim --opt-in --yes --apply  # 只开一项
```

参考标准涵盖：RFC 4941（IPv6 隐私）/ RFC 8200（IPv6）/ RFC 3168（ECN）/
RFC 9002（BBR）/ RFC 1191（PMTUD）/ RFC 7858（DoT）/ RFC 8484（DoH）/
IEEE 802.11（Wi-Fi 节能）/ ITU-T Y.1541（QoS/DSCP）/ ITU-T G.992（ADSL）/ ITU-T G.711（语音）。

### 字体/字符标准参考（Unicode 最新稳定版或 LTS 版本）

字体/字符处理对照权威字符与字体标准文档（见 `data/fonts_standards.json`），用系统原生接口读取，
工具缺失时自动降级为指引、不强求安装：

- **Unicode 18.0.0**（最新稳定版，2026-09 发布）/ **ISO/IEC 10646** —— 字符编码基线；UTF-8（RFC 3629）为推荐编码
- **OpenType**（ISO/IEC 14496-22）/ **TrueType**（Apple）—— 轮廓字体格式，现代字体引擎事实标准
- **WOFF 1.0 / 2.0**（W3C Recommendation）—— Web 字体封装（WOFF 2.0 用 Brotli 压缩，体积更小）
- **Unicode Emoji**（UTS #51）/ **CLDR** / **UAX #9**（双向算法）—— emoji 字体、区域数据、RTL 排版
- **Unicode 规范化（UAX #15）** —— NFC/NFD/NFKC/NFKD；系统文本建议统一为 NFC，便于等价比较与去重，与 UTF-8 / UTF-128 编码策略配套保证跨平台文本一致

> **版本策略**：字符编码以 Unicode **最新稳定版（18.0.0）** 为基线，长期支持（LTS）以各平台/语言运行时锁定的 Unicode 版本为准（如系统内置 ICU、.NET Globalization、Python `unicodedata` 钉版），不强制追新；新增字符与 emoji 需对应版本才渲染。

> **编码模式（UTF-128 向下兼容 UTF-8）**：除推荐 UTF-8 外，可声明前瞻的 **UTF-128** 宽编码模式（UTF-8 的严格超集——ASCII 0–127 同字节、UTF-8 多字节续字节方案作子集保留）。声明 UTF-128 时，实际落盘表示**规范化为 UTF-8**（UTF-8 是便携且超集安全的形态），从而保证对既有 UTF-8 文件与工具的完全向下兼容。UTF-128 为前瞻提案（非现行 ISO/Unicode 标准），不强制追新，仅在确需超宽字符集时声明。

> **网络字体（需先开启网络协议）**：开启网络协议开关（`toggles` / `--opt-in`）后，字体分类下的 **启用网络字体（@font-face 拉取 WOFF2）** 同步可用；其经 W3C WOFF 2.0 封装、按 RFC 9110 缓存语义拉取，文本编码保持 UTF-8 兼容（UTF-128 模式下亦向下兼容）。

```bash
python -m sysweeper fonts               # 原生读取 + 字符/字体标准引用，不改系统
python -m sysweeper fonts --encoding utf-128   # 查看 UTF-128 模式的 UTF-8 向下兼容判定
python -m sysweeper list --category fonts
python -m sysweeper scan --category fonts     # 分析模式：UTF-8 检查 / 冗余字体 / 缓存重建 / 文本 NFC 规范化（不改）
python -m sysweeper list --category fonts --opt-in   # 含网络字体（需先开网络协议开关）
```

## 目录结构

```
system-optimizer/
├── README.md
├── .gitignore
├── licenses/                # 第三方许可证与引用来源（v0.5.19）：MIT / Apache-2.0 / GPL-2.0 / GPL-3.0 / AGPL-3.0 各一文件 + README.md 索引
├── src/python/sysweeper/
│   ├── __init__.py
│   ├── __main__.py          # python -m sysweeper 入口
│   ├── cli.py               # argparse 命令与参数
│   ├── models.py            # Task / Action 数据模型 + 版本比较
│   ├── registry.py          # 任务注册与过滤
│   ├── detect.py            # 平台/版本自动探测（走 native 接口）
│   ├── runner.py            # 分析/执行/风险评估（含 native 派发）
│   ├── native/              # 各平台原生接口层（不麻烦的核心）
│   │   ├── common.py        # 跨平台共享：run / disk_usage / human / 目录体积 / 用户缓存·临时·大目录·DNS 报告
│   │   ├── windows.py       # Win32 API (ctypes) + winreg
│   │   ├── linux.py         # LSB /etc/os-release + journalctl
│   │   ├── macos.py         # sysctlbyname (libc) + sw_vers
│   │   ├── bsd.py           # sysctlbyname (libc) + 各 BSD 包管理
│   │   ├── unix.py          # System V: /etc/release + IPS pkg
│   │   ├── android.py       # adb 封装
│   │   ├── ios.py           # libimobiledevice 封装
│   │   ├── hardware.py      # S.M.A.R.T./ACPI/PCI/USB/TRIM 原生读取
│   │   ├── arch.py          # 架构/指令集：龙芯 LoongArch / MIPS / RISC-V / 开源硬件（uname/cpuinfo/sysctl 探测）
│   │   ├── fonts.py         # 字体/字符标准：fc-list/fc-cache 原生读取（Unicode 18.0.0/OpenType/WOFF）
│   │   ├── network.py       # 网络栈：协议/ITU 开关（sysctl/iw）+ 深度调优只读探测与调优接口（iproute2/ethtool/eBPF/tc/conntrack/RPS-XPS，默认关闭）
│   │   ├── netlink.py       # 链接协议注册表（TCP/UDP/RFCOMM/串口/BLE/802.15.4）+ 本地自组网 PeerMesh（UDP 发现 + TCP 可靠通道 + 只读安全命令白名单）
│   │   ├── netauth.py       # 按网络维度隐私验证：两项以上个人信息派生令牌，只存 salt+令牌+标签，原始值不保存、可重连；跨设备身份指纹
│   │   ├── reshare.py       # 同人设备资源共享：只共享算力/网络（CPU/内存/GPU/NPU/TPU/网络），个人数据与关键资产数据永不共享
│   │   ├── openwrt.py       # OpenWrt 路由器系统只读接口（UCI/opkg-apk/netifd/ubus/procd/防火墙/无线/DHCP/存储/固件板型/构建系统参考，v0.5.20/21）
│   │   ├── openwrt_write.py # OpenWrt 高危写操作「安全指引」层（只读预检+命令文本，绝不执行；sysupgrade/包管理/uci set/服务启停，v0.5.21）
│   │   ├── plugins.py       # 安全插件框架：内置+用户只读插件注册表，native 入口仅限白名单只读函数，register_native 可安全扩展，plugin_validate 防命令注入（v0.5.20/21）
│   │   ├── jdk.py           # OpenJDK/JVM 只读层：java -version/系统属性白名单/--list-modules/PrintFlagsFinal GC+JIT/jps/jcmd/JFR 状态；敏感值只报存在性，绝不写 JAVA_HOME、不设 GC 参数、不录 JFR、不 attach（v0.5.22）
│   │   ├── kmod.py          # Linux 内核 module/firmware/plugin(s) 只读层：/proc/modules、/sys/module 参数（只读）、modinfo、/lib/firmware、BTF/bpffs/eBPF 能力面、黑名单、电源状态；绝不 insmod/rmmod、不写 parameters、不替换固件、不 load/attach eBPF（v0.5.22）
│   │   ├── metrics.py       # 数学量化引擎（纯标准库）：归一化、Shannon 熵、Gini、CV、Jaccard、cosine、任务深度饱和曲线、WSM 多准则决策评分 S=Σwᵢx̂ᵢ；所有除法零分母保护（v0.5.22）
│   │   ├── syssoftware.py   # 其余系统软件：systemd/D-Bus/NetworkManager/PipeWire/BlueZ/udev/polkit/Wayland
│   │   ├── harmony.py       # 鸿蒙：hdc 设备侧 + HiLog/Stage/SysCap/HAP 工程侧只读探测
│   │   ├── miniapp.py       # 各小程序端：微信/支付宝/百度/抖音/QQ/快手 + 跨端条件编译静态检查
│   │   ├── pkgmgr.py        # 包管理器：APT/RPM/apk/pacman/Homebrew/winget/pip/npm/Snap-Flatpak
│   │   ├── container.py     # 容器运行时：Docker/Podman/containerd/BuildKit/OCI/LXC-LXD/CRI 只读探测
│   │   └── storage.py       # 存储与文件系统：ext4/Btrfs/XFS/ZFS/LVM/fstrim/SMART/swap 只读探测
│   ├── a11y.py              # 无障碍：ORCA/AT-SPI2(org.a11y.Bus) 协议常量·探测·朗读降级·友好文本 + **多系统适配**（Windows 讲述人 UIA / macOS VoiceOver AX / Android TalkBack / iOS VoiceOver / 鸿蒙屏幕朗读，data/a11y_docs.json）
│   ├── arch.py              # 架构/指令集：ISA 探测 + 三层标准 + 开源硬件 + GOARCH 构建映射
│   ├── gui.py               # 图形界面（Python 自带 tkinter，零依赖 + 无图形环境优雅降级）
│   ├── windows_bat.py       # 把 Windows 适用任务展开成自包含 .bat（分析/执行/注册计划任务）
│   ├── report.py            # --report 前后对比报告（Markdown / JSON 渲染）
│   ├── tasks/               # 各平台任务定义
│   │   ├── windows.py  macos.py  linux.py  bsd.py  unix.py  android.py  ios.py
│   │   ├── lang.py          # 按语言自动启用的功能（python/ruby/go/node/perl/lua/rust/java/dotnet + trae 分支导入的 bun/c/elixir/erlang/kotlin/swift/zig，见 `src/<lang>/` 单文件只读组件）
│   │   ├── hardware.py      # 硬件标准相关维护项
│   │   ├── fonts.py          # 字体/字符标准相关检查与维护项
│   │   ├── network.py       # 网络栈：协议/ITU 标准开关 + 深度调优任务（net_*，opt_in，默认关闭；mesh/netauth 任务 v0.6.66 归位至 netlink.py/netauth.py，net_reshare 留此）
│   │   ├── androidstd.py    # 国内标准·App 隐私合规知识库任务（5 个指引类，v0.6.67；PIPL/GB-T/四部门规定/TC260 全部官方源实检）
│   │   ├── gmsstd.py        # GMS 标准·GMS 兼容与 Play 上架知识库任务（5 个指引类，v0.6.67；CDD/CTS/VTS/STS→GMS 许可→Play 三件套→Data safety）
│   │   ├── fdroidstd.py     # F-Droid 标准·免 GMS 分发知识库任务（5 个指引类，v0.6.67；收录政策/反特征/可复现构建/仓库协议，GitHub/GitLab API 实检）
│   │   ├── cross.py         # 跨平台清点：用户缓存/临时目录/大目录/DNS 刷新（收敛 BSD/Unix 重复项）
│   │   ├── a11y.py          # 无障碍：ORCA/AT-SPI2 自检与开关 + **多系统适配**（Windows 讲述人 / macOS VoiceOver / Android TalkBack / iOS VoiceOver / 鸿蒙屏幕朗读）
│   │   ├── arch.py          # 架构/指令集：龙芯/MIPS/RISC-V/开源硬件/工具链 + 龙芯与 MIPS 平台专属项
│   │   ├── syssoftware.py   # 其余系统软件：按各自协议与接口的核对/清理（journalctl --vacuum 等）
│   │   ├── harmony.py       # 鸿蒙工程侧缓存清理 + HiLog 只读报告 + hdc 设备侧核对
│   │   ├── miniapp.py       # 各小程序端清理/核对 + 跨端静态检查（mp_cross_lint）
│   │   ├── pkgmgr.py        # 包管理器清理/核对：各走自身官方接口（paccache/brew cleanup/pip cache purge…）
│   │   ├── container.py     # 容器运行时清理/核对：各走自身官方接口（docker/podman prune/nerdctl/ctr/CRI）
│   │   ├── storage.py       # 存储/文件系统清理核对：各走自身官方接口（e4defrag/xfs_fsr/btrfs balance/scrub/zpool trim/fstrim/smartctl）
│   │   ├── thirdparty.py    # 导入第三方网络互联/硬件优化/开源下载（只读引用，v0.5.19）
│   │   ├── openwrt.py       # OpenWrt 只读任务（探测/UCI/包/网络/防火墙/无线/DHCP/存储/构建，risk=low）+ 高危写指引任务（sysupgrade/包管理/uci set/服务启停，risk=high+opt-in，platform=openwrt，v0.5.20/21）
│   │   ├── plugins.py       # 插件框架任务（platform=any，只读展示已注册插件，v0.5.20）
│   │   ├── jdk.py           # OpenJDK 只读体检任务（jdk_*，platform=any/requires_lang=java），全部 risk=low、无 shell 写动作（v0.5.22；v0.6.66 自 jvm.py 拆出归位）
│   │   ├── kmod.py          # Linux 内核 module/firmware/eBPF 只读任务（kmod_*，platform=linux），全部 risk=low、无 shell 写动作（v0.5.22；v0.6.66 自 jvm.py 拆出归位，经 module 回退同时满足 firmware/modules 子系统接线）
│   │   ├── netlink.py       # 链接协议注册表 + mesh 自组网/人机交互只读任务（net_link_* / net_mesh_*，v0.6.66 自 network.py 归位 + 新增 net_link_env 双栈连通体检）
│   │   ├── netauth.py       # 按网络隐私验证任务（net_auth_*，原始个人信息不落盘；v0.6.66 自 network.py 归位 + 新增 net_auth_fingerprint 跨设备身份指纹指引）
│   │   ├── kernel.py        # 内核调优只读总览（kernel_sysctl_overview，串联调度/OOM/PSI/THP/vm/TCP/拥塞/net.core/RPS 十项报告，v0.6.66 新增）
│   │   └── uniapp.py        # uni-app 目标端：工程侧自动清理 + 端上清理任务 + 分包懒加载指引
├── plugins/                 # 用户插件 drop-in 清单（*.json，经 plugin_validate 校验后自动发现；v0.5.20）
│   └── openwrt.example.json # 示例：OpenWrt 只读插件（与内置 openwrt 插件同构）
├── profiles.py              # 任务档位「大而全 / 小而全」：4 档（minimal/lite/standard/full）+ 4 场景档（readonly-audit/daily-clean/deep-opt/elderly-friendly），声明式五维度筛选（v0.5.22）
├── src/go/                  # Go 组件（纯标准库、零依赖）：同口径查询 + 交叉编译二进制
│   ├── go.mod  main.go  standards.go  a11y.go  platform.go
│   └── windows-automation/  # 生成的 Windows 自包含 .bat 样例 + 说明（见其 README）
│   ├── langdetect.py        # 语言运行时探测（shutil.which）
│   └── uniapp-cleaner/      # 一个真实可运行的 uni-app 工程：端上 storage 清理页（含 showModal 确认）
│   └── data/
│       ├── versions.json        # 可选版本与版本级注意事项（含 uni-app 3.x/4.x）
│       ├── hardware.json        # 硬件标准参考（T13/ACPI/PCI-SIG/USB-IF…）
│       ├── fonts_standards.json # 字体/字符标准参考（Unicode 18.0.0 / ISO-IEC 10646 / OpenType / WOFF / UTF-128 向下兼容 / 网络字体）
│       ├── network_standards.json  # 网络/ITU 标准参考（RFC/IEEE/ITU-T…）
│       ├── rfc_standards.json      # RFC 全量目录（10,036 条，官方 RFC INDEX 解析）
│       ├── xiuzhen_map.json        # 修真图谱（75 节点/77 边，典籍/道藏部类/主题/旁参/语料，全带 source）
│       ├── ca_audit_standards.json  # WebTrust for CAs 审计图谱（GoDaddy/Starfield 2026：35 CA/12 地点/4 事项/标准条款映射，全带 source 页码）
│       ├── mongo_docs.json          # MongoDB 权威指南（第2版）知识索引（6 部分/23 章/43 概念/16 条系统层调优；原件按版权不入库，只留 SHA256）
│       ├── arch.json           # 架构/指令集标准参考（龙芯 LoongArch / MIPS / RISC-V / OpenPOWER / OpenRISC / x86 / ARM / 开源硬件）
│       ├── syssoftware_docs.json  # 其余系统软件文档参考（systemd/D-Bus/… ：各自的协议 + 接口）
│       ├── harmony_docs.json   # 鸿蒙文档参考（Stage 模型/ArkUI/SysCap/HiLog/hdc/HAP/分布式 + uni-app 鸿蒙端）
│       ├── miniapp_docs.json   # 各小程序端文档参考（wx.*/my.*/swan.*/tt.*/qq.*/ks.* + 条件编译映射）
│       ├── pkgmgr_docs.json    # 包管理器文档参考（deb/RPM/APKINDEX/pkg.tar.zst/Formula/清单/PEP/Registry/OSTree）
│       ├── container_docs.json # 容器运行时文档参考（OCI/Docker/Podman/containerd/BuildKit/LXC/CRI：各自的协议 + 接口）
│       ├── storage_docs.json   # 存储/文件系统文档参考（ext4/Btrfs/XFS/ZFS/LVM/fstrim/SMART/swap：各自的协议 + 接口）
│       ├── network_docs.json    # 网络栈运维文档参考（iproute2/ethtool/eBPF/tc/conntrack/NM-resolved/scaling：各自的协议 + 接口）
│       ├── windows_docs.json  # Windows 原生接口文档参考（Win32/注册表/WMI-CIM/powercfg/DISM/SFC/存储感知/传递优化/Windows Update：各自的协议 + 接口）
│       ├── unix_docs.json     # Unix（System V）原生接口文档参考（IPS pkg/SMF/ZFS//etc/release/logadm/kstat/Zones/FMA/dladm-ipadm：各自的协议 + 接口）
│       ├── android_docs.json  # Android 原生接口文档参考（adb/settings_provider/pm/am/dumpsys/getprop/svc/wm/logcat：各自的协议 + 接口）
│       ├── ios_docs.json      # iOS 原生接口文档参考（libimobiledevice/lockdown/usbmuxd/installation_proxy/afc/crashreport/syslog_relay/diagnostics/mobilebackup2/mobile_image_mounter：各自的协议 + 接口）
│       ├── macos_docs.json    # macOS 原生接口文档参考（launchd/sysctl/defaults/softwareupdate/diskutil/pmset/tmutil/spctl/networksetup：各自的协议 + 接口）
│       ├── bsd_docs.json      # BSD 原生接口文档参考（pkg/rc.conf/sysctl/pf/zfs/periodic/bsdconfig/ports：各自的协议 + 接口）
│       ├── link_protocols.json # 链接层/传输层协议注册表（TCP/UDP/RFCOMM/串口/BLE/802.15.4：各自协议 + 接口 + 文档）
│       ├── net_interop_refs.json # 第三方网络互联互通/硬件优化/开源下载 引用注册表（p2wlan/dae/gfw-pac/v2rayN/DLSS5-Swapper/aria2：含 license/repo/role）
│       └── uniapp_api.json      # uni-app 需要的 API 清单（分组 + 各端支持 + 标准出处）
└── tests/test_sysweeper.py
```

## 安装与运行

```bash
# 任选一种方式设置 PYTHONPATH
export PYTHONPATH=$PWD/src/python
cd system-optimizer

python -m sysweeper detect                              # 自动探测当前平台/版本
python -m sysweeper info --platform linux               # 用原生接口报告磁盘/版本/发行版
python -m sysweeper langs                               # 语言运行时探测 + 自动启用状态
python -m sysweeper hardware                            # 硬件标准参考（原生读取，不改系统）
python -m sysweeper fonts                               # 字体/字符标准参考（Unicode 18.0.0 + OpenType/WOFF 原生读取）
python -m sysweeper toggles                             # 网络/ITU 开关（默认关闭，需选择+确认）
python -m sysweeper standards                           # 分类规范整体：分类→标准出处(国家/国际/地区三层)→覆盖→逐类任务 id
python -m sysweeper standards --audience intl            # 面向外国用户：优先列国际标准(IEEE/RFC/ISO/ITU)
python -m sysweeper a11y                                 # 无障碍：ORCA / AT-SPI2 环境自检 + 适用任务
python -m sysweeper a11y --speak                         # 有语音后端时朗读报告摘要（无则纯文本）
python -m sysweeper versions --platform windows         # 列出某平台可选版本
python -m sysweeper scan                                # 分析模式扫描（不改系统）
python -m sysweeper list --platform bsd --version 14
python -m sysweeper notes --platform ios --version 26   # 仅看注意事项/风险提示
python -m sysweeper clean --apply --risk low            # 仅执行低风险清理
python -m sysweeper clean --platform windows --version 11 --apply --yes --risk medium

python -m sysweeper jdk                                  # OpenJDK/JVM 只读体检（无 JDK 则给官方文档指引）
python -m sysweeper kmod                                 # Linux 内核 module/firmware/eBPF 只读体检（非 Linux 优雅降级）
python -m sysweeper profiles list                        # 任务档位总览（minimal/lite/standard/full + 4 场景档）
python -m sysweeper score overview                       # 任务库数学量化评分（WSM 加权 + 分类覆盖 + 风险画像）
python -m sysweeper list --profile minimal               # 小而全：极简档（零 opt-in、零非 low 风险）
python -m sysweeper list --profile elderly-friendly      # 场景档：适老化巡检（只留无障碍相关）
python -m sysweeper scan --profile lite                  # 大而全一点的日常档（仍只分析不执行）
```

> 没指定 `--platform/--version` 时会自动探测（走 native 接口）；探测不到（如容器环境）会提示手动指定。
> `--profile` 是**通用参数**：`list` / `scan` / `clean` / `notes` 都认，可写档位名（`minimal`/`lite`/`standard`/`full`）或场景档名（`readonly-audit`/`daily-clean`/`deep-opt`/`elderly-friendly`）。它只是**筛选范围**，不等于授权执行——`clean` 仍需 `--apply`（+ 中高风险 `--yes`）。

## 命令说明

| 命令 | 作用 |
|---|---|
| `detect` | 打印自动探测到的平台、版本、发行版 |
| `info` | 用各平台**原生接口**报告系统环境（磁盘/版本/发行版/设备），不修改任何东西 |
| `langs` | 语言运行时探测 + 「按语言自动启用」的功能开关状态（不强求安装） |
| `hardware` | 硬件标准参考：S.M.A.R.T./ACPI/PCI/USB 原生读取 + 标准文档引用 |
| `fonts` | 字体/字符标准参考：系统文本编码 UTF-8 检查 + 已安装字体/冗余 + 标准文档引用（Unicode 18.0.0 / OpenType / WOFF）；`--encoding utf-128` 看 UTF-8 向下兼容判定 |
| `toggles` | 网络协议 / ITU 标准开关（默认关闭，需选择 + 确认）；开启后同步解锁字体分类的「网络字体（@font-face 拉取 WOFF2）」 |
| `standards` | **分类规范整体**：每个分类 → 标准出处（**按受众分层**：国家标准/国家平台 → 国际 → 地区）→ 任务计数与平台覆盖矩阵 → 逐类列出全部任务 id（平台/风险）；**opt-in 开关逐条标注其标准归属**（带层级标记，按 `--audience` 排序）。`--audience cn/intl/regional` 切换引用优先级 |
| `rfc` | **RFC 全量标准目录**（v0.6.52，IETF 官方 RFC INDEX 本地解析、只读不联网）：`rfc` 裸命令看目录速览（10,036 条，含 188 个编号保留未发布）；`list [--status X] [--limit N]` 按状态/最新列出；`search <词>` 按标题/作者检索；`show <编号>` 单条详情（标题/作者/日期/状态/废弃-被废弃-更新关系/DOI/格式/主题域归属/引用任务）；`citing <编号>` **反向列出哪些 sysweeper 任务引用了该 RFC**；`relations <编号>` 关系视图（指向编号尽力解析，目录外引用如实标注未解析）；`current <编号>` 沿 obsoleted-by 链找现行版本（含 CYCLE/DANGLING/TOO_DEEP 诚实状态）；`series [名]` STD/BCP/FYI 系列索引与成员；`topics`/`topic <域名>` **主题域索引**（heuristic 标题规则匹配，13 域 / 89 条规则，命中 rule_id 留痕，未分类如实保留，非 IETF 官方分类）；`refs` 任务侧引用全量核验（悬空/真过期引用/说明性提及三分）；`wgs` **官方 WG/RG 索引速览**（rfc-index.xml + datatracker 名录第二索引源：area 分布 + Top WG，与 heuristic 层模态一致率 81.8%）；`wg <名>` 某 WG/RG 或 area（datatracker 代码 sec/rtg/int/app…）的成员列表。官方 WG 索引由 `../../research/rfc/build_rfc_wg_index.py` 生成（`data/rfc_wg_index.json`，`--check` 模式对账）。数据由 `../../research/harvest/rfc_index_harvest.py` 从 rfc-editor.org 解析生成（`data/rfc_standards.json`，含 obs/oby/upd/udy 关系字段）。**GUI「RFC 知识库」面板**（`gui.py` `show_rfc`，v0.6.52 新增）：三页只读浏览——主题域（13 域点选列成员）/ 工作组(WG)（area + Top WG 点选列成员）/ 单号查询（并陈 heuristic 主题域与官方 WG 两层归属），与 CLI 同数据层、口径一致 |
| `xiuzhen` | **修真图谱**（v0.6.46，典籍/道藏部类/研修主题/旁参典籍/语料 五层关系图谱，只读不联网）：`xiuzhen` 裸命令看图谱速览（75 节点 / 77 关系，节点/边一律带 source）；`layers` 分层清单（含每层节点数）；`list [--layer X]` 列出节点；`search <词>` 按名称检索；`show <节点>` 单节点详情（说明/道藏编号/出处/关联数）；`edges <节点>` 该节点全部关联关系的中文句（如「道德经（老子） 属于 道德真经」「…… 主题 脏腑辨证（命中 135 次）」）。数据由 `../../research/xiuzhen/build_xiuzhen_map.py` 从 ClassicsData.ts + analysis.json + suwen 索引三源可复现 join 生成（`data/xiuzhen_map.json`），App 侧同源渲染为「修真图谱」页（邻域探索/分层全景/文本等价视图） |
| `caudit` | **WebTrust for CAs 审计图谱**（v0.6.47，GoDaddy/Starfield 2026 审计报告导入，只读不联网）：`caudit` 裸命令看速览（35 个 CA=12 根+8 交叉签名+15 签发，Schellman 无保留意见）；`list [--kind root\|cross\|issuing]` 按种类列 CA（SHA-256 指纹/出处页码）；`search <词>` 按名称/指纹前缀检索；`show <名称>` 单 CA 详情；`children <根>` 某根下的交叉/签发 CA；`matters [--bug 编号]` 4 项 Mozilla Bugzilla 事项（条款映射 RFC 5280 §4.2.2.1 / BR §7.1.2.10.3/§7.2.2.1 / CCADB §6.2、整改与审计师核查结论，#2007216 报告期末仍开放）；`locations` 12 个地点；`std [rfc <编号>]` 标准引用清单（可经 `rfc` 目录跨库反查 RFC 5280 元数据）；`cpcps` CP/CPS 六版谱系；`domains` WebTrust v2.2.2 控制域清单。数据由 `../../research/caaudit/build_ca_audit_standards.py` 从用户投递的《GoDaddy - 2026 WebTrust for CAs - Report.pdf》事实底稿可复现生成（`data/ca_audit_standards.json`） |
| `mongo` | **MongoDB 权威指南（第2版）知识索引**（v0.6.48，O'Reilly/图灵授权中文版，只读不联网）：`mongo` 裸命令看书目与规模（6 部分 / 23 章 / 43 概念 / 16 条系统调优）；`chapters [--part p1..p6]` 章节清单；`show <章号>` 某章全部小节 + 本章相关概念；`concepts [--cat model\|crud\|query\|index\|aggregate\|design\|replica\|sharding\|admin]` 概念条目（文档模型/修改器/查询操作符/索引类型/聚合管道/范式化/副本集/片键/备份与持久性，均标所属章节）；`search <词>` 检索；`deploy` 第 23 章「部署 MongoDB」的 16 条系统层调优（存储介质/RAID/swap/文件系统/NUMA/readahead/THP/IO 调度/noatime/ulimit/时钟同步/OOM）；`cross` 只列与 sysweeper 对得上的项（如 THP→`linux_thp_compaction`、IO 调度→`linux_io_scheduler`、swappiness→`linux_swappiness`，运行期二次核验存在）；`book` 书目与版权边界。**原书为商业出版物（版权页声明仅供个人使用），PDF 原件与提取全文均不入库，仅留 SHA256 备核验**。数据由 `../../research/mongodb/build_mongo_docs.py` 从事实底稿生成（`data/mongo_docs.json`） |
| `recert` | **WCET 续证 PDU 计分方案**（v0.6.51，IEEE 无线通信工程技术认证，已于 2019 年停办，只读不联网）：`recert` 裸命令看方案速览；`cycles` 两周期下限与跨度（三年 ≥60 / 五年 ≥100 PDU，均须覆盖 ≥3 年、≥3 个技术知识领域）；`areas` 七大技术知识领域（第 7 类标注待核实，不臆造）；`categories` 10 个活动分类的计分规则与双周期封顶（专业工作/志愿/WCET贡献/授课/论文/培训/自学/其他认证/会议/会员升级）；`show <类>` 单类规则；`rules` 续证合规校验清单；`caps` 各分类理论封顶合计（仅合规提示，非刷分建议）。**数据由 `../../research/recert/build_recert_docs.py` 从用户投递的两个 .xls 续证跟踪表解析生成（`data/recert_docs.json`）；表内个人隐私字段不入库，仅留规则知识** |
| `langref` | **编程语言与编译器知识库**（v0.6.55，只读不联网）：**161 条**结构化元数据（首现年/范式/类型系统/实现/设计者/来源/状态/标准/分类），**不复制教材**。以 2008–2026 新发语言为主体（**72** 条：Rust/Go/Kotlin/Swift/Zig/Mojo/Carbon/ArkTS/Futhark/Pony/Verse/Unison…），补**古今锚点**（89 条：Fortran/Lisp/C/Java/Python/Simula/Ada/APL/Erlang/OCaml…）与**国内外代表**（国内 10：易语言/文言/仓颉/凹语言/Go+/木兰/习语言/周蟒/汉语编程/ArkTS）；**esolang** 10 条（Brainfuck/Befunge/INTERCAL/Malbolge/Piet/Whitespace/LOLCODE/Unlambda/Shakespeare/Chef）；**其他计算机类**（查询/标记/数据/配置/Shell/IR/**硬件描述 Verilog·VHDL**/排版/记号/验证）。存疑项标 `needs_verify`（12 条）。子命令：`overview`/`stats`/`window`/`search <词>`/`show <id>`/`category <分类>`/`origin <来源>`/`paradigms`/`verify`。**GUI「编程语言库」面板**（`show_langref`，v0.6.54 新增）：三页只读浏览——窗口内 / 分类·来源筛选 / 检索·待核实，与 CLI 同数据层口径；存疑项以「⚠ 待核实」原样标出。**注：`langs` 已用于语言运行时探测子系统**。数据 `data/langs_docs.json`，校验 `../../research/langs/validate_langs.py --check`（防 entry_count/in_window 漂移） |
| `plang` | **编程语言「概念系统」分层分类**（v0.6.56，只读不联网）：以仓库 wordbuddy-github 为主目录，按**执行模型(8 类) → 硬件架构子分类(13 类: x86-64·arm64·riscv / wasm / jvm·clr·beam·evm·js / gpu-simt / fpga / host / n-a) → 能力域(7) → 底层标准依据(RFC 等)** 组织 161 条语言；**「各语言各自尝试编程整体」实测 15/15**（Python/JS/TS/Go/Rust/C/C++/Java/Ruby/Perl/Bash/AWK/Tcl/F#/Makefile 各跑通 8 面能力契约：字面量/运算/控制流/函数/数据结构/IO/错误/并发），无工具链的一律标「未实测」不臆造；**不足处以 RFC 等底层标准补充**（TCP 9293 / HTTP 9110·9112 / TLS 8446 / DNS 1035 / JSON 8259 / UTF-8 3629 / URI 3986 / 时间 3339 / X.509 5280 等），且**每个 RFC 编号均经本仓库 rfc_catalog 交叉验证存在**并回填标题。**v0.6.61 全量补全**：161/161 条语言齐备**六字段**（范式 / 类型系统 / 内存管理 / 首次出现年 / 一句话定位 / 工程落法），`plang of <id>` 输出概念卡片；工程落法按诚实口径分级——15 种 probe 实测语言标「probe 实测通过」并给具体落法（rust 落 cargo build/test+clippy 等），其余仅登记工具链名称不宣称可编译；非执行类（HTML 等宿主工具解释）与 esolang（brainfuck 等玩具/实验）如实标注；构建 `--check` 三类新校验（陈旧补全键 / 六字段非空 / probe 口径一致）。子命令：`overview` / `archs` / `arch <架构>` / `models` / `model <模型>` / `of <id>` / `rfc [id]` / `probe` / `domains`。数据 `data/concepts/plang_taxonomy.json`（由 `research/plang/build_plang.py` 合并 `lang_enrich.py` 构建，`--check` 防漂移） |
| `netsys` | **网络与组网「概念系统」**（v0.6.57，只读不联网）：以仓库 wordbuddy-github 为主目录，把散落的 **20+ 个网络/组网子系统**重组为 **64 个模块**，按**网络层次(8: L1→L7 + overlay 覆盖 + mesh 组网) → 组网形态(8: standalone/lan/mesh/overlay/sdwan/distributed/anonymous/wan) → 能力性质(7: 只读诊断/调优/通信/共享/审计/发现/引用) → 标准依据(RFC·ISO·ITU)** 四轴重组；**显式登记 41 条关系边**（依赖 10：`osi→network`、`meshchat→netlink`、`distjob→distcompute·meshchat`、`emergency→network`、`radio→osi`、`kernel-l4s/kernel-ptp/kernel-wifi-he-eht→network`、`sysfed→sysmesh`；互补 31：meshnet↔zerotier、dnshealth↔network、vdns↔dnshealth、tls13↔cert、reshare↔distcompute、apctrl↔openwrt、nat↔meshnet、dhcp↔dnshealth、mdns↔ipp、quic↔tls13、vxlan↔meshnet·zerotier、kernel 三模块↔network、batman-adv↔meshnet、`radio` 互补 meshnet·netlink·openwrt 等），`--check` 校验**无悬空轴**；**每模块带红线**（如「只跑内置可验证算子绝不执行外部代码」「结果必须复算校验」「收到的文件不自动落盘」「不读私钥」「抓来的永远是文本无执行路径」），`redlines` 可一次列出；标准依据 RFC 8981/8200/3168/9002/9293/768/1035/8484/7858/4253/4251/854/959/4217/9846/8996/5280/8010/8011/9110/4944/6282/7668/8376/8724/9330/9331/9332/8033 **均经本仓库 rfc_catalog 交叉验证**（4944/6282=6LoWPAN、7668=BLE IPv6、8376=LPWAN 综述、8724=SCHC，补无线电/物联网链路）。子命令：`overview` / `layers` / `layer <层次>` / `forms` / `form <形态>` / `natures` / `nature <性质>` / `of <id>` / `relations` / `rfc` / `redlines`。**注意：本层只做重组视图，不代调用各网络模块、不改任何配置**。数据 `data/netsys_taxonomy.json`（由 `research/netsys/build_netsys.py` 构建） |
| `quantum` | **量子理念「概念系统」**（v0.6.65，只读不联网）：以仓库 wordbuddy-github 为主目录，按**量子态表示(8) → 量子门与线路(6) → 量子算法(10) → 硬件平台(8) → 纠错与噪声(8) → 量子网络(13) → 标准·语言·工具链(9) → 经典模拟与语义(13) → 量子架构内核(7)** 九域登记 **82 个概念**；**7 条标准逐条核实**（ISO/IEC 4879:2024、OpenQASM 3.0、QIR、ITU-T Y.3800、ETSI GS QKD 014、FIPS 203/204/205 均 official_verified；IEEE P7130 经核查仍为 IEEE-SA 在研项目（PAR）、尚未发布为正式标准，改标 `draft_project`，仅作草案基准）；**56 条桥接**到 netsys(24：如 Grover 使对称密钥等效安全位束约减半→tls13 套件强度按抗量子口径折算等)/datong(13：六象位序同构/一体两面/中道/净化禁忌)/daoxue(8)/plang(9)/baigong(2)，构建期校验无悬空。**qsim 域（v0.6.65）登记本仓库自建的经典模拟器**（`research/quantum/simulator/`：六态造化/正负零电压/六个相变矩阵/数制双读出/Born 观测，extract_engine.py + verify3/4/5.mjs 同源断言），在 O(2ⁿ) 墙内执行 ≤6 比特——**是「可跑的教具」而非量子硬件**。**多位元 qudit（0031 轮，native/qudit.py）**：d 级系统容量 log₂(d) 比特/符号（非 d 比特），同位能级散逸（振幅阻尼 T1 + 相位阻尼 T2，Kraus CPTP 迹保持）+ log 值交换（d=5/v=6：γ=0 解码 6.15、γ=1.0→3.07 单调下漂）——经典数值模拟，不宣称量子优势。**多位元 qudit 寄存器（0032 轮）**：N 个 d=8 qudit 经 native/quantum.py 的 PiLink 内存交换参数逐 qudit 交换（不物化 8^N 联合态），覆盖经典位宽 8/16/64/128 位元。**诚实边界：不含量子硬件探针、不接入量子设备、不在真实量子硬件上执行量子线路**；算法结论（如 QAOA 优势）按文献现状登记不夸大为定论；概念登记不构成威胁评估或采购建议。子命令：`overview` / `domains` / `domain <域>` / `of <id>` / `standards` / `bridge [系统]` / `search <词>` / `verify` / `stats` / `vm <bell\|ghz\|teleport\|grover2q\|bv2\|arch> [--shots N] [--seed N]` / `qudit [d] [value]` / `qudreg [width] [d] [gamma]`。**`vm` 为量子虚拟机入口**（v0.6.69，native/quantum.py 态矢量模拟）：内置程序实跑（bell 00/11≈50/50 相关、teleport 传态右位恒 1、grover2q 100% 命中 11、bv2 隐串 10），`arch` 为量子架构基座演示（数字转换门 enc/dec、CPU↔闪存 π 链路不间断交换、tan/ctan 返回交互）。**`qudit` 为多位元 qudit 入口**（0031 轮）：d 级 log₂(d) 比特容量表 + 同位能级散逸解码漂移表，参数越界按 μ=log₂(v)∈[0,d−1] 诚实拒绝。经典模拟器，不含量子硬件探针。数据 `data/concepts/quantum_taxonomy.json`（由 `research/quantum/build_quantum.py` 构建，`--check` 防漂移） |
| `comp` | **编译与工具链「概念系统」**（v0.6.59，只读不联网）：以仓库 wordbuddy-github 为主目录，按**编译流水线(10) → 工具链家族(12) → 构建系统(12) → 目标产物(8) → 语言编译需要(16) → 黑箱逆向(7) → 位宽与寻址世代(6) → 引导与实测纪律(5) → 交叉工具链实境(10)** 九轴登记 **86 个概念**；语言编译需要**仅对 plang probe 实测通过的 15 种语言**（python/js/ts/go/rust/c/c++/java/ruby/perl/bash/awk/tcl/f#/makefile）逐条登记明细（证据取自 `probe_results`），其余 146 种**汇总为一条 needs_verify 不逐条臆造**；**98 条桥接**到 plang(49)/llvm(15：`tool:clang` 等与数据层 `llvm_docs.json` 的工具/目标三元组核对，含 `target:x86_64-w64-mingw32`)/daoxue(14)/datong(8)/netsys(3：含 `bit8-era→module:radio` 算力底座对照)/quantum(9：v0.6.85 首批 comp→quantum 边，诊断优先/可复现门禁/宿主验证 + v0.6.86 工具链安全响应时钟 ↔ qsim 与 qkern 域 + v0004 交叉实境的页纪律/LTS 同构边 + v0.6.68 qkern-patch-distribution 工具链侧镜像边），构建期校验无悬空。**第九轴「交叉工具链实境」九概念全部源自本仓 2026-10-24 实证**（bionic 无 iconv 补 libiconv / musl 原生 GB18030 / qemu-user 三连坎 / MinGW 线程变体 / Wine 仿真验收 / OHOS SDK 布局 / NDK API 门控 / deb 迁移税 / 里程表版本号）。**#603 构建域补三概念（83→86 概念、96→98 桥接）**：`scons`（Python 驱动构建，宿主 4.5.2 vs 上游 4.11.1 记 needs_action）、`container-toolchain`（Dockerfile 多阶段 + compose 最小权限，本仓 counterpart 真实在位）、`lint-gate`（clang-format/clang-tidy/shellcheck 宿主可用但 CI 未接入——如实登记「未落地」）。**红线：只读登记，不驱动任何真实编译**（编译动作属各工具链自身）。子命令：`overview` / `domains` / `domain <轴>` / `of <id>` / `need <语言>` / `needs` / `bridge [系统]` / `search <词>` / `verify` / `stats`。数据 `data/concepts/comp_taxonomy.json`（由 `research/comp/build_comp.py` 构建，`--check` 防漂移） |
| `toolchain` | **工具链全景「子系统」**（v0.6.70，只读不写）：把本仓全部「概念系统 × 子系统」的**工具链**与**自研工具软件**按**类别(交叉编译 / 原生构建 / 语言运行时 / 仿真 / 编辑器浏览器 / 打包 / 质量 / 安全检测) × 目标架构 × 仓库目录**三维编目，含每个工具的**配置逻辑顺序与命令序列**。数据层 `data/toolchain_catalog.json`（23 条宿主工具链 + 7 条仓库工具软件 + 10 条目标架构矩阵 + 上游新鲜度两栏，全部版本为 2026-10-24 本机 `--version` 实采）；`native/toolchain.py` 五个只读报告（**catalog 编目全景** / **本机实采 which+版本**（NDK 与 OHOS 按 catalog 绝对路径回退探测）/ **仓库工具软件**（含配置逻辑顺序与命令序列）/ **目标矩阵** / **新鲜度**（上游 vs 本机两栏差异）/ **按类别过滤**）；`tasks/toolchain.py` 4 任务（toolchain-catalog-review / toolchain-host-audit / toolchain-target-matrix / toolchain-freshness）；四入口接线（subsystems 第 95 项 layer「语言/编译」/ CLI `toolchain [--category X]` 子命令 / GUI「工具链全景」面板 / registry）；`linkage` 7 条轴（llvm 供给 / arch 门控 / pkgmgr 供给 / compat 供给 / reverse 供给 / sysdev 供给 / winternals 关联，无孤岛无悬空）；ergonomics「语言与编译」组收入。**红线：只探测与编目，绝不安装/卸载/构建/下载**；catalog 的 `setup_steps` 与 `commands` 是 README 性质的逻辑顺序，不是自动执行队列。配套文档 `docs/57_工具链全景.md` |
| `apilab` | **接口 API「概念系统」**（v0.6.59，只读不联网）：以仓库 wordbuddy-github 为主目录，按**接口风格(9) → 规约标准(6) → 传输绑定(6) → 认证授权(6) → 本仓库接口面(5)** 五轴登记 **36 个概念**；**12 条 RFC**（9110/9112/9113/9114/9000/9293/6455/7617/7519/6750/6749/5280）编号**均经本仓库 rfc_catalog 交叉验证存在并回填标题**；**repo-face 轴以当前仓库实测事实登记**（构建时从 argparse 与 webapi.py 读出 **107 个 CLI 子命令 / 29 个 webapi ACTIONS**，JSONL 白名单协议、插件 API 白名单制、report schema、report_viewer sha256 守护），`--check` 把磁盘登记值与源码实测值逐键比对防漂移；**19 条桥接**到 daoxue(8)/netsys(7)/plang(2)/datong(2)。**红线：令牌禁入 URL/localStorage、私钥不明文、访问令牌短时效 + 服务端刷新**。子命令：`overview` / `domains` / `domain <轴>` / `of <id>` / `repo` / `rfc` / `bridge [系统]` / `search <词>` / `verify` / `stats`。数据 `data/concepts/apilab_taxonomy.json`（由 `research/apilab/build_apilab.py` 构建） |
| `baigong` | **「百工」匠作概念系统**（v0.6.61，只读不联网）：以**墨子、公输般、公孙策、鲁班**（可扩大为三教九流）为工程理念，落实「具体无解 / 暂时不允许 / 构建程序具体结构」三个场景——按**核心理念(5) → 匠作原则(7) → 三教九流(12) → 工程场景(3)** 四轴登记 **27 个概念**；五偶各带工程落法（墨子·守御红线先立 / 公输般·九设九距兵推法 / 鲁班·绳墨定检 / 公孙策·锦囊预案分级）；**50 条桥接**到八个概念系统（comp 14 / plang 8 / daoxue 7 / apilab 7 / netsys 7 / quantum 4 / zhuangzi 2 / datong 1），构建期逐条校验目标真实存在（无悬空）；**用户端面 + 语言面为构建期实测**（CLI 123 / GUI 108 / webapi 29 / deno 双文件 0000.0000.0000.0034.20261026 / plang 161·probe 15 / comp 16），`--check` 逐键比对防漂移。**红线：只读登记，不驱动任何真实施工**；引文按通行本登记并标 needs_verify（一名两译/文学形象/工程翻译）。子命令：`overview` / `core` / `craft` / `schools` / `scenes` / `principles [id]` / `concept <id>` / `bridge [系统]` / `userface` / `verify` / `stats` / `search <词>`。数据 `data/concepts/baigong_taxonomy.json`（由 `research/baigong/build_baigong.py` 构建，`--check` 防漂移） |
| `datong` | **「大同」人类文明一体概念系统**（v0.6.62，只读不联网）：以「人类命运是一个的，古今中外的宗教哲学都融合进来」为立意，按**文明传统(15：儒/道/佛/基督/伊斯兰/犹太/印度/耆那/锡克/琐罗亚斯德/希腊/神道/萨满巫觋/古埃及两河/巴哈伊) → 核心命题(21：人类一体·一体两面·三位一体·神恩如狱·……·**唯道独尊**) → 正道六象(6：固/液/气/电/磁/波) → 实践形态(12) → 人间落法(9)** 五轴登记 **63 个概念**；六象按「天罡元阳（气·电·波·外发）/ 地煞元阴（固·液·磁·内聚）」分属，每象登记科学口径 + 跨传统通名 + 工程落法（固→不可变发布物 / 液→流式管道 / 磁→约束吸附寻的 / 气→事件总线 / 电→信号触发 / 波→一处发布处处到达）；**51 条桥接**到八个既有概念系统（comp 8 / apilab 7 / baigong 7 / daoxue 7 / netsys 7 / zhuangzi 6 / quantum 6 / plang 3），构建期逐条校验目标真实存在（无悬空）；**用户端面 + 语言面为构建期实测**（CLI 123 / GUI 108 / webapi 29 / deno 双文件 0000.0000.0000.0034.20261026；plang 161 条 / probe 实测 15 种 / comp 语言编译需要 16 条），`--check` 逐键比对防漂移。**红线：只读登记，不宣扬任何宗教为真理、不复制经典全文**；跨传统同构非等同、**神恩如狱**按奥古斯丁恩典论/加尔文预定论/伊斯兰前定/佛教业力观的学术口径作喻解，原典未核对与年代/词源分歧统一标 needs_verify（7 项）。子命令：`overview` / `traditions` / `theses` / `six` / `practices` / `ethics` / `concept <id>` / `principles [id]` / `bridge [系统]` / `userface` / `verify` / `stats` / `search <词>`。数据 `data/concepts/datong_taxonomy.json`（由 `research/datong/build_datong.py` 构建，`--check` 防漂移） |
| `concepts` | **概念系统中心**（v0.6.62，只读不联网）：九个概念系统（plang/netsys/daoxue/quantum/comp/apilab/zhuangzi/baigong/datong）的统一注册表入口——`concepts` 裸命令看九系统总览（tagline + 版本 + 规模，datong 为 63 概念 / 50 桥接 / 9 原则）；`search <词>` 跨系统检索（命中带 `system` 字段标明来源）；`show <系统>` 单系统摘要；新系统按「数据层 `data/concepts/<name>_taxonomy.json` + 只读层 `concepts/<name>.py` + `REGISTRY` 一行」三处追加即被中心收口，CLI/GUI 复用共享派发无需逐系统复制。**GUI「概念系统中心」窗口**：九系统总览 + 跨系统检索 + 双击惰性展开各系统面板（底部按钮另有「量子理念」「编译工具链」「接口 API」「南华理念」「百工理念」「大同理念」直达；`guide` 一屏入口地图） |
| `a11y` | **无障碍环境报告（多系统适配）**：Linux ORCA / AT-SPI2（D-Bus `org.a11y.Bus`）、Windows 讲述人（UI Automation / MSAA）、macOS VoiceOver（NSAccessibility）、Android TalkBack（AccessibilityService）、iOS VoiceOver、鸿蒙屏幕朗读（AccessibilityExtensionAbility）—— 各自按自身接口只读探测。用 `--platform windows\|macos\|linux\|android\|ios\|harmony\|any` 指定系统（默认 any 概览）；`--speak` 用系统语音朗读摘要（无后端时降级为纯文本） |
| `netlink` | **多种网络链接协议 + 多设备自组网 + 隐私验证 + 同人资源共享**（v0.5.18）：`list` 链接协议注册表（TCP/UDP/RFCOMM/串口/BLE/802.15.4）与本机能力；`serve` 启用本地自组网（>1 台设备自己通信，命令通道只有 info/ping/probe/msg，**绝不执行任意命令**）；`discover` 发现本网段设备；`msg --text` 人机交互消息；`auth` 按网络隐私验证（两项以上个人信息，原始值不保存、可重连）；`reshare` 同人资源共享（算力/网络共享，个人数据与关键资产数据永不共享） |
| `thirdparty` | **导入的第三方网络互联互通/硬件优化/开源下载 引用**（v0.5.19，只读登记、不打包二进制）：`list` 全部引用清单；`interop` 网络互联互通（p2wlan/dae/gfw-pac/v2rayN）；`hw` 硬件优化（DLSS5-Swapper，由用户选择）；`download` 开源下载（aria2）；`cdn-p2p` CDN/P2P 开关说明；`licenses` 第三方许可证引用来源汇总（详见仓库 `licenses/` 文件夹） |
| `openwrt` | **OpenWrt 路由器系统只读接口**（v0.5.20/21）：`list` 能力总览（探测+UCI+包+网络+服务+防火墙+无线+DHCP+存储+构建参考）；`detect` 板型/固件识别；`uci` UCI 配置只读审计（不打印 secret 明文）；`pkgs` 已装软件包盘点（opkg/apk 自适应）；`network` 网络接口只读报告；`firewall` 防火墙只读报告；`wireless` 无线只读报告（不回显密码）；`dhcp` DHCP/DNS 只读报告；`storage` 存储只读报告；`build` 构建系统参考（仅文档）；`write` 高危写操作指引（sysupgrade/包管理/uci set/服务启停；只预检+命令文本，绝不执行）。非 OpenWrt 环境优雅降级为指引 |
| `plugins` | **插件支持**（v0.5.20/21，安全只读插件注册表）：`list` 全部已注册插件（内置 openwrt/interop + 用户 drop-in）；`show --id X` 查看某插件清单（能力/原生入口/任务）；`run --id X` 只读运行某插件声明的全部白名单原生函数；`allowlist` 查看当前只读白名单（静态审读 + `register_native` 运行时登记）。插件 native 入口仅限只读白名单，绝不执行任意代码 |
| `jdk` | **OpenJDK/JVM 只读体检**（v0.5.22）：版本与发行版、系统属性（**仅白名单键**，敏感值只报存在性）、JPMS 模块清单、GC 标志实际取值、JIT 编译参数、`jps`/`jcmd` 诊断工具、JFR 状态、JIT 编译缓存与环境全景。**只读**——不改 `JAVA_HOME`、不设 GC 参数、不录 JFR、不 attach 进程；无 JDK 时优雅降级为 OpenJDK 官方文档指引 |
| `kmod` | **Linux 内核 module / firmware / plugin(s) 只读体检**（v0.5.22）：已加载模块、`/sys/module` 面、模块参数（只读）、`modinfo`、固件库与已加载固件、**eBPF 能力面**（BTF/vmlinux、bpffs pin 数、kprobe 可挂载面、`unprivileged_bpf_disabled`）、`module.blacklist`、电源状态与唤醒计数。**只读**——绝不 insmod/rmmod/modprobe、不写模块参数、不替换固件、不 load/attach eBPF；非 Linux 环境优雅降级 |
| `profiles` | **任务档位「大而全 / 小而全」**（v0.5.22）：`list` 列出 4 档与 4 场景档；`show --profile X` 看某档收录规则与风险画像；`tasks --profile X` 看该档实际收录的任务；`compare --profile X --against Y` 看两档差集（Jaccard）。不带 `--profile` 时默认按 `minimal` 处理。**选档位 ≠ 授权执行**，仍需 `--apply --yes` 才落地 |
| `score` | **数学量化评分**（v0.5.22）：`overview` 任务库总评分（WSM 加权）+ 风险画像 + 分类覆盖；`global` Shannon 熵/Gini 分布诊断；`platform` 平台覆盖均衡（Gini/CV）；`profile --profile X` 各档位量化对比；`balance` 覆盖缺口诊断（哪些分类/平台偏少） |
| `arch` | **架构/指令集报告**：龙芯 LoongArch / MIPS / RISC-V / 开源硬件（OSHWA·CERN OHL·DIN SPEC 3105）+ 交叉工具链与 Go GOARCH 映射。`--audience cn/intl/regional/us/jp/eu/de` 切换标准优先级 |
| `versions` | 列出某平台所有可选版本及版本级注意事项 |
| `list` | 列出某平台/版本适用的任务（可按 `--category` 过滤；`--opt-in` 含网络/ITU） |
| `notes` | 仅汇总该平台/版本的风险提示与注意事项 |
| `scan` | 分析模式：展示任务、预估可回收空间、列出命令，**不修改系统**（加 `--opt-in` 含网络开关） |
| `clean` | 执行清理；默认仅展示，加 `--apply` 才真正执行；`--yes` 确认中高风险；`--opt-in` 纳入网络/ITU，`--only` 精确选择 |
| `syssoftware` | **其余系统软件**文档跟踪：systemd / D-Bus / NetworkManager / PipeWire / BlueZ / udev / polkit / Wayland，各自按自身协议与接口只读核对 |
| `harmony` | **鸿蒙**文档跟踪：Stage 模型 / ArkUI / SysCap / HiLog / hdc / HAP / 分布式 + uni-app 鸿蒙端；hdc 已连接时识别为平台 `harmony` |
| `miniapp` | **各小程序端**文档跟踪：微信 / 支付宝 / 百度 / 抖音 / QQ / 快手，按各端自身 API 规范 + 跨端条件编译静态检查 |
| `pkgmgr` | **包管理器**文档跟踪：APT / RPM-DNF / apk / pacman / Homebrew / winget / pip / npm / Snap-Flatpak，各自按自身协议与接口，只读统计缓存与可清理项 |
| `container` | **容器运行时**文档跟踪：Docker / Podman / containerd / BuildKit / OCI / LXC-LXD / CRI，各自按自身协议与接口，只读统计磁盘占用与可清理项 |
| `storage` | **存储与文件系统**文档跟踪：ext4 / Btrfs / XFS / ZFS / LVM / fstrim / SMART / swap，各自按自身协议与接口，只读统计占用/碎片率/健康与可清理项 |
| `network` | **网络栈深度调优**文档跟踪：iproute2 / ethtool / eBPF / tc / conntrack / NM-resolved / RPS-XPS，各自按自身协议与接口，只读探测 + net_* 深度调优任务（全 opt_in） |
| `windows` | **Windows 原生接口**文档跟踪（v0.5.13）：Win32 API / 注册表 / WMI-CIM / powercfg / DISM / SFC / 存储感知 / 传递优化 / Windows Update，各自按自身协议与接口，只读探测 + win_* 清理/优化任务 + **win_tune_\* 官方写接口深度调优**（全 opt_in：fsutil behavior set、netsh int tcp set global、netsh advfirewall 只开不关、powercfg /change 与 /h /type reduced） |
| `macos` | **macOS 原生接口**文档跟踪：launchd / sysctl / defaults / softwareupdate / diskutil / pmset / tmutil / spctl / networksetup，各自按自身协议与接口，只读探测 + mac_* 清理/优化任务（执行需 --apply）+ **macos_tune_\* 官方写接口深度调优**（v0.5.12，全 opt_in：pmset -a / sysctl -w / networksetup -setdnsservers empty / tmutil thinlocalsnapshots / defaults write / softwareupdate --schedule / spctl --master-enable / diskutil verifyVolume） |
| `bsd` | **BSD 原生接口**文档跟踪：pkg / rc.conf / sysctl / pf / zfs / periodic / bsdconfig / ports，各自按自身协议与接口，只读探测 + bsd_* 清理/优化任务 + **bsd_tune_\* 官方写接口深度调优**（v0.5.12，全 opt_in：sysctl -w rfc1323/缓冲/maxfiles/arc_max、zpool autotrim、zpool scrub、pfctl -e -f、periodic） |
| `unix` | **Unix（System V）原生接口**文档跟踪（v0.5.14）：IPS pkg / SMF / ZFS / \/etc\/release / logadm / kstat / Zones / FMA / dladm-ipadm，各自按自身协议与接口，只读探测 + unix_* 清理/优化任务 + **unix_tune_\* 官方写接口深度调优**（全 opt_in：pkg refresh/fix、svcadm enable/clear、zfs set atime\|compression、zpool scrub、logadm -r、ipadm set-prop ecn） |
| `android` | **Android 原生接口**文档跟踪（v0.5.15）：adb / settings_provider / pm / am / dumpsys / getprop / svc / wm / logcat，各自按自身协议与接口（经官方 ADB），只读探测 + and_* 清理/优化任务 + **and_tune_\* 官方写接口深度调优**（全 opt_in：settings put 关动画、pm trim-caches、svc wifi enable、dumpsys \* --reset、logcat -c、am kill-all、wm size\|density reset，只往安全方向写） |
| `ios` | **iOS 原生接口**文档跟踪（v0.5.16）：libimobiledevice（ideviceinfo / ideviceinstaller / idevicesyslog / idevicecrashreport / idevicediagnostics / idevicebackup2 / idevicepair / idevicename / idevicedate / idevicesetlocation / ideviceimagemounter），各自按自身协议与接口（经已配对设备），只读探测 + ios_* 指引/清理任务 + **ios_tune_\* 官方写接口深度调优**（全 opt_in：idevicebackup2 backup、ideviceinstaller -a、idevicecrashreport -e、idevicedate -s、idevicesetlocation clear、idevicename、idevicediagnostics restart、ideviceimagemounter，只往安全方向写，绝不 remount） |
| `snapshot` | **基线快照与差异对比**（纯只读）：`capture` 聚合各子系统只读探测 + 磁盘/内存指标落盘为 JSON；`diff` 对比两份快照输出可追溯差异；`show` 查看快照。把「前后对比」做成可归档产物 |
| `uniapp` | uni-app 需要的**原生能力与 API 清单**（按能力分组 + 各端支持 + 标准出处）+ 该目标端的清理任务 |
| `gui` | **图形界面点选**：选平台/版本 → 勾选任务 → 扫描/执行/生成报告 / **可视化对比** / **扫描快照对比**（扫描流程自动留只读基线并与上次对比）。用 Python 自带 tkinter，零依赖 |
| `genbat` | 生成 **Windows 自包含 .bat**：分析 / 执行（中高风险逐一确认）/ `schedule` 注册每周计划任务。默认 UTF-8(BOM)（允许 UTF-8 以上），可 `--encoding gbk` |
| `chart` | 读取一个 JSON 报告（`--report xxx.json` 生成），打印 **ASCII 条形图** 可视化对比（磁盘前/后 + 各任务可回收），适合无图形环境 |
| `diag` | **脱敏诊断报告**（工程实践移植自 DiPlay）：收集平台/版本/Python 与外部只读工具可用性，**默认脱敏**——IP / MAC / 长标识 / 家目录占位符化，命中凭据关键词的行整行丢弃，单行截断 700 字符。`--out` 指定落点（默认 `~/Downloads/sysweeper-diagnostics-<时间>.txt`），`--note` 追加说明。**只写本地，绝不自动上传** |
| `channels` | **版本通道**：stable 常态稳定版 / lts 长期支持版 / fresh 尝鲜版。CLI `channels`（动作 `list/show/recommend/select`，含 `--usage/--years/--env`）据使用量/期望年限/环境推荐；`select` 仅写入 `settings.json` 作更新检查标记，**绝不自动升级** |
| `durability` | **设备长期使用保护**（v0.6.30）：只读采集电池/温度/SMART/uptime/环境传感器，按使用量+期望年限+环境标签由知识库推导保养目标包络与健康评分，给保养清单与优化建议（每条回链 IEC 60529 / ASHRAE / 电池指南 / NVMe SMART）。写操作只给 OEM 指引，不代执行。含 `--usage/--years/--env` |
| `remote` | **远程接入与传输客户端只读审计**（v0.6.30）：telnet/ssh/filezilla/putty 各自按自身协议核对；只读审计 telnet 明文 / ssh 口令登录 / filezilla 明文 FTP 与弱口令存储，**绝不读解密口令、不改 sshd_config、不替你停 telnetd**；加固只给官方指引 |
| `cert` | **证书与加密开源整合**（v0.6.31）：整合 OpenSSL/LibreSSL/BoringSSL/GnuTLS 等开源加密栈 + 硬件信任根（TPM 2.0 / IDevID 设备身份证书）+ 平台密钥库 + 各种证书（X.509/ACME/PKCS#12/FIDO2）；只读审计 EOL 加密库 / 未启用 TPM / 临近过期 / 密钥库不可达，**绝不读私钥、绝不解密、绝不改配置**，输出无障碍纯文本 |
| `linkage` | **联动连轴体检**（v0.6.33）：每条联动轴标注**供给 / 门控 / 印证 / 闭环 / 串联**，并给出**孤岛**（登记了却没接上主干）与**悬空轴**（端点写错会静默失效）两份待修清单。`--stats` 打印结构化统计，`--chains` 看最长串联链与串联深度，`--path A B` 沿轴走一遍看两者怎么串起来，`--graph` 打 ASCII 分层邻接图，`--svg PATH` 导出纯标准库生成的 SVG。纯计算只读：不跑任何诊断、不改任何状态 |
| `compat` | **兼容层串联**（v0.6.34）：把 proton/dosbox/wsl/virtgpu/legacy 串成**四层依赖链**（底座 → 设备与图形 → 兼容运行时 → 供给），按场景回答「能不能跑那个平台的软件、缺哪一层」。**不适用 ≠ 已就绪**；只调既有只读报告，**不安装、不启用、不改配置**，缺什么只给官方指引 |
| `omni` | **全能全知自检**（v0.6.35，v0.6.36 闭环）：自述三层边界——我知道什么（`coverage`，能力覆盖面 + 接线完整度）／我知道我不知道什么（`--deep` 实跑本机探不到的）／**我不知道我不知道什么**（`all`，本工具没有探针的 12 个域，带理由与替代路径）。`blind N` 列缺 N 处入口以上的半截能力；`gaps` 出**补齐清单**（缺口分「设计如此 / 真缺口」两类，真缺口给具体补法）；`gen-stub KEY [--write]` 为真缺口 data 项生成知识库占位 JSON（dry-run 不落盘、已存在不覆盖）。纯计算只读，不采集任何信息 |
| `linux` | **Linux 本机发行面**（v0.6.35 补入口）：发行版 / 包管理器 / systemd 日志体积 / 根分区用量，只读聚合；**只报告不清日志** |
| `compress` | **压缩空间分析**（v0.6.35 补入口）：`caps` 看本机可读哪些压缩格式，`report` 估算还能压出多少空间并标出「别白压」的已压格式；**不压缩、不解压、不删除** |
| `emergency` | **预警应急定位**（v0.6.35 补入口）：`report`/`position`/`alert` 只读探测；不发预警、不上传位置 |

> **标准引用策略（分类规范整体）**：每一项优化/清理都映射到参考标准，按三层引用——
> **国家标准 / 国家平台**（国内优先，如 GB 18030、个人信息保护法 PIPL、中国能效标识、通信行业标准 YD/T，国家平台：全国标准信息公共服务平台 `std.samr.gov.cn`）
> → **国际标准**（面向外国用户 / 跨国场景，如 IEEE、IETF RFC、ISO/IEC、ITU-T、W3C、Unicode）
> → **地区标准**（必要时按国家/地区执行，如欧盟 GDPR、美国 NIST SP 800、日本 JIS / APPI、ENERGY STAR / ErP）。
> 用 `standards --audience cn|intl|regional` 或 GUI「标准与分类」查看对应优先级；非中国场景默认以国际标准为准。
> **地区子标签**：需要按具体国家/地区执行时用 `--audience us|jp|eu|de`，该地区条目会排到最前
> （如 EU → GDPR / EN 301 549 / ErP，JP → JIS / APPI，US → NIST / Section 508 / ENERGY STAR，DE → DIN SPEC 3105）。
> **逐条标注**：每个任务在 `standards` 列表与 GUI 中显示各自依据的标准条目（带 `[国标]/[国际]/[地区]` 层级标记），
> 按受众排序并标 `①` 当前优先层。任务自带的 `standards` 优先；其余按「关键词细化 → 分类默认」派生，
> 保证**每一项普通任务也能追溯到标准出处**（如含 trim/ssd 的任务 → ATA TRIM，含 power/sleep 的 → ACPI）。

## 打包与分发（GitHub 构建）

Python 侧用 PEP 621 的 `pyproject.toml` 声明（纯标准库、零运行时依赖）。分发包由仓库自带
`tools/syspkg.py` 生成（手写 PEP 427 wheel / sdist，纯标准库、**不经由 setuptools**，
因此对去中心化版本号格式零依赖、不触发 PEP 440 校验）；仓库根
`.github/workflows/build.yml` 在打 `v*` tag 时自动构建并附到 GitHub Release：

```bash
# 本地构建（等价配置，验证过可产出 sdist + wheel；版本串原样写入，零依赖）
python3 ../tools/syspkg.py wheel --out dist
python3 ../tools/syspkg.py sdist --out dist

# 安装产物（wheel 文件名含去中心化版本号，如 sysweeper-0000.0000.0000.0004.20261024-py3-none-any.whl）
pip install dist/sysweeper-*.whl
sysweeper --help                    # 安装后即可用 sysweeper 命令
```

# 如需把去中心化版本映射为 PEP 440 串（仅 PyPI 等强制 PEP 440 的外部系统才需要，
# 不改三处活版本）：
#   python3 -c "from sysweeper import version as v; print(v.to_pep440(v.PACKAGE_VERSION))"
#   # -> 0.0.0.3+20261023

### 语言底层：单文件 .pyz（推荐）

**Python 3 是本项目的语言底层**——多数 Linux / macOS / BSD 发行版默认自带，本包又零第三方依赖，
于是可以把整个包压成一个 zipapp 单文件，**任何有 python3 的机器直接跑**，不需要 pip、不需要编译：

```bash
# 构建（纯标准库，不需要 setuptools / build / wheel）
python3 ../tools/syspkg.py pyz --out dist

# 运行（三种等价方式）
python3 dist/sysweeper-0000.0000.0000.0004.20261024.pyz detect
./dist/sysweeper-0000.0000.0000.0004.20261024.pyz detect        # 已带 shebang + 可执行位
sh ../tools/bootstrap.sh detect        # 自动找 python3 → 自动找 pyz
```

包内 `sysweeper/data/*.json` 知识库在 zip 中同样读得到（Python 3.11+ 由 zipimport 原生支持，
3.9 / 3.10 由 `sysweeper/_zipres.py` 补一层 `zipfile.Path` shim），不会出现"能跑但知识库为空"。
验证命令：`python3 ../tools/syspkg.py smoke --out dist`。

打包器 `tools/syspkg.py` 只依赖标准库，`all` 子命令会先探测工具链，有 Go / Rust / JDK 就多产出
对应的原生二进制与 APK，没有就跳过，**永不因此失败**：

```bash
python3 ../tools/syspkg.py probe     # 我这套机器能产出什么
python3 ../tools/syspkg.py targets   # 支持的（系统 × 硬件）矩阵
python3 ../tools/syspkg.py all       # 能打的都打
```

CI 触发方式与产物：

| 触发 | 产物 |
|---|---|
| 推送 `v*` tag（如 `git tag v0.2.0 && git push origin v0.2.0`） | 自动构建并把 **sdist / wheel / Go 二进制**附到对应 GitHub Release |
| Actions 页 `workflow_dispatch` 手动触发 | 产物作为 artifact 留存（`dist-python`、`dist-go-<os>-<arch>`） |
| CI 内 `build-python` job | 先跑 `pytest`，测试通过才打包（保证产物质量） |
| 推送 / PR（`build-python.yml`） | 用 runner **系统自带** Python 构建 .pyz + wheel + sdist，并在 Linux / macOS / Windows 上跑同一个 .pyz |

wheel 内含 `sysweeper/data/*.json`（标准参考数据）与 `sysweeper` 命令入口，为纯 Python
的 `py3-none-any`，可直接跨平台安装。

### 容器：Docker 镜像（v0000.0000.0000.0004.20261024）

```bash
docker build -t sysweeper:0000.0000.0000.0003.20261023 -f system-optimizer/Dockerfile ..   # 构建上下文 = 仓库根
docker run --rm sysweeper:0000.0000.0000.0003.20261023 detect                 # 单次只读诊断
docker run --rm sysweeper:0000.0000.0000.0003.20261023 quantum vm bell        # 量子虚拟机演示
docker compose up --build                                # 在 system-optimizer/ 下运行：声明式最小权限
```

多阶段构建（构建工具不进最终镜像）、非 root 运行、`--no-index` 只装本构建产出的 wheel；
容器镜像的 wheel 同样由 `tools/syspkg.py` 产出（不经由 setuptools，对去中心化版本号零依赖）；
compose 把「只读根 / 全能力丢弃 / 阻断提权」固化为配置。详见
[`docs/36_Docker容器化与镜像构建.md`](docs/36_Docker容器化与镜像构建.md)；
各系统（Windows / Linux / macOS / BSD / Unix / Android / iOS）的安装路径与产物矩阵见
[`docs/37_各系统打包安装教程.md`](docs/37_各系统打包安装教程.md)。

## 图形界面（`gui`）

有些语言**默认就带 GUI**，所以界面优先用「自带」的那套，不强求安装任何东西：

| 后端 | 是否需要额外安装 | 状态 |
|---|---|---|
| **Python tkinter** | 否（标准库自带，本项目默认使用） | 首选 |
| Java Swing / AWT | 否（装了 JDK 就有） | 备选 |
| .NET WinForms / WPF | 否（装了 .NET SDK 就有） | 备选（桌面 Windows） |
| Qt 6 / PySide6 | 是（需 `pip install PySide6`） | 不强求，缺了就用 tkinter |

```bash
python -m sysweeper gui                       # 自动探测平台后打开界面
python -m sysweeper gui --platform windows --version 11
```

界面能力：平台/版本/分类/风险选择 → 任务勾选（全选/全不选）→ **扫描分析**（不改系统）/ **执行选中项**（弹窗二次确认）/ **生成报告** / **可视化对比** / 查看 GUI 后端状态 / **标准与分类**（弹出窗口展示分类→标准出处→覆盖→逐类任务 id，opt-in 开关单列）/ **无障碍**（ORCA / AT-SPI2 环境报告 + 适用任务 + 「朗读结果」按钮）/ **无障碍(多系统)**（下拉切换 Windows/macOS/Linux/Android/iOS/鸿蒙，各自按自身接口只读探测 + 权威文档）/ **架构/开源硬件**（ISA 探测 + 龙芯/MIPS/RISC-V + 开源硬件认证与许可 + GOARCH）/ **系统软件** / **包管理器** / **容器运行时** / **存储/文件系统** / **网络栈调优** / **网络链接/Mesh**（链接协议注册表 + 启动自组网 + 发现设备 + 隐私验证 + 同人资源共享）/ **Windows** / **Unix(SysV)** / **macOS** / **BSD** / **鸿蒙** / **小程序端** / **Android**（面板末尾含**适老化专块**：总报告 + 纯文字建议 + Android 8~17 兼容口径表）/ **iOS** / **OpenJDK/JVM** / **内核模块/固件** / **档位(大而全/小而全)** / **数学评分** / **扫描快照对比** / **版本通道**（stable/lts/fresh，GUI 选择并据使用量/年限/环境推荐，选定仅写偏好绝不自动升级）/ **设备长期使用保护**（只读采集传感器 + 知识库驱动保养，写操作只给 OEM 指引）/ **远程接入审计**（telnet/ssh/filezilla/putty 只读安全审计与加固指引，绝不读解密口令、不改配置）/ **证书与加密**（OpenSSL 类开源加密栈 + 硬件信任根 TPM/IDevID + 各种证书只读审计，绝不读私钥、绝不解密，无障碍纯文本）/ **联动连轴**（每条轴标注供给/门控/印证/闭环/串联 + 孤岛与悬空轴两份待修清单，一键重新体检，纯计算不改状态）/ **联动图**（分层布局 Canvas 图，边按性质着色、点越大联通度越高、**点节点看它的入边与出边**、一键导出 SVG）/ **兼容层串联**（四层依赖 + 场景结论，缺层判缺层、不适用不判就绪，只读不代装）/ **全能全知自检**（三层边界自述：我知道什么 / 我不知道什么 / 我不做什么，含半截能力清单与**补齐清单**：缺口分「设计如此 / 真缺口」两类）/ **字体与文本规范化**（v0.6.36 补 GUI 入口：本机字体清单 / 重复项 / 文本规范化状态，只读不改字体与文件）/ **Linux 发行面** / **压缩空间分析** / **单板机(SBC)**（上述文档跟踪层 + v0.5.22 三条新能力的图形入口，内容与同名 CLI 子命令一致）。执行前对中高风险与默认关闭的开关会强制弹窗确认。

**可视化对比**：扫描/执行或生成报告后，点「可视化对比」会弹出窗口，用 tkinter Canvas 画出两段条形图——「处理前 → 处理后」主盘已用占比，以及各任务「预计可回收空间」纵向条；无图形环境可用 `chart` 命令看等效的 ASCII 版。

**扫描快照对比**：每次「扫描分析」/「执行选中项」都会自动留下只读基线快照，下次扫描自动输出与上次的可追溯差异（探针状态 + 磁盘/内存数值）；点此按钮弹出本会话最近两次扫描的对比详情。

### 图形模式的四件事（v0.6.7）

| 能力 | 怎么用 | 落地方式 |
|---|---|---|
| **开启 / 关闭** | 任务列表每项勾选框；插件窗口里每个插件的启停勾选 | 勾选即生效：关掉的项不进执行清单，**停用后的插件点了也不运行** |
| **更新** | 顶部「更新/检查」 | **默认只检查不动手**：只读体检（版本 / git 状态 / 远端新提交 / 插件与任务库规模）；「本地刷新」只重新扫描本地；真更新**只给命令不代劳** |
| **插件选择** | 「插件」窗口 | 白名单只读清单 + 启停开关，停用即拒绝运行（不是装饰） |
| **优化项目选择** | 平台/版本/分类/风险下拉 + 任务勾选 + 档位窗口 | 与命令行同一套 `applicable()` 过滤口径，界面只是它的显示层 |

**适配当前系统**：顶部按钮，一键探测本机平台/版本并套用（不用手填），随后刷新任务列表。
探测失败会把原因写进日志，不静默吞掉。

**开关会记住**：勾了什么、关了什么写进 `~/.config/sysweeper/gui.json`
（XDG 规范；家目录不可写则降级为本次会话有效）。只存**任务 id / 插件 id 这类标识符**，
不存任何命令、不存代码、不执行——与插件白名单同一套安全模型。
配置损坏或版本不认识 → 整体回退默认，界面绝不因配置问题打不开。

验证方式（`tools/smoke_gui.py`，真的把窗口建起来点一遍再关）：

```bash
xvfb-run -a python3.11 tools/smoke_gui.py    # 无显示器也能跑；退出码 0 = 全通过
```

无图形环境（SSH / 容器 / CI）时不会报错，而是打印各后端状态并退回命令行：

```
无法启动图形界面：couldn't connect to display ":0"
各 GUI 后端状态（优先「语言自带」的）：
  [✓ 可用] Python tkinter（标准库自带） — 零依赖，本项目 GUI 默认用它
  ...
替代方案（命令行，功能完全一致）： python -m sysweeper scan ...
```

## 无障碍（ORCA / AT-SPI2）

Linux 上 ORCA 屏幕阅读器通过 **AT-SPI2** 访问应用无障碍树；AT-SPI2 构建在 D-Bus 之上，
即「辅助技术总线」`org.a11y.Bus`。本项目把这套协议/接口做成可自检、可开关的能力：

| 协议要点 | 值 |
|---|---|
| 辅助技术总线 | `org.a11y.Bus`（由 `at-spi-bus-launcher` 拉起） |
| 注册表对象 | `/org/a11y/atspi/registry`（`org.a11y.atspi.Registry`） |
| 常用接口 | `Accessible` / `Action` / `Component` / `Text` / `Selection` / `Value` / `Table` … |
| 启用开关 | `gsettings set org.gnome.desktop.a11y.applications screen-reader-enabled true` |
| 接口暴露开关 | `gsettings set org.gnome.desktop.interface toolkit-accessibility true` |
| 读屏器 | `orca --replace`（重启）/ `orca --setup`（设置），配置在 `~/.local/share/orca` |
| 各平台对应 | Windows 讲述人（UIA/MSAA，`Win+Ctrl+Enter`）、macOS VoiceOver（AX API，`Cmd+F5`） |

```bash
python -m sysweeper a11y              # ORCA 安装 / AT-SPI2 总线 / 自启动开关 / 语音后端
python -m sysweeper a11y --speak      # 朗读摘要（spd-say / espeak / say；无则纯文本）
```

无障碍任务（`--category accessibility`）：`any_a11y_report`（跨平台报告）、`linux_atspi_bus`
（总线自检）、`linux_orca_status`、`linux_orca_enable`、`linux_atspi_toolkit`、`win_narrator_hint`、
`mac_voiceover_hint`、`any_a11y_standards`。

### 无障碍多系统适配（v0.5.18）

无障碍设置与配置**适配多个系统**，每个系统按**它自己的**协议与接口只读探测（`--platform` 指定，
不指定则给全部概览）。权威文档在 `data/a11y_docs.json`：

| 系统 | 屏幕阅读器 | 原生接口 / 探测方式 | 启用入口 |
|---|---|---|---|
| **Windows** | 讲述人（Narrator） | UI Automation（UIA）/ MSAA；只读读 `HKCU\Software\Microsoft\Narrator` | `Win+Ctrl+Enter`；设置 → 辅助功能 → 讲述人 |
| **macOS** | VoiceOver | NSAccessibility（AX API）；`defaults read com.apple.universalaccess voiceOverOnOffKey` | `Cmd+F5`；系统设置 → 辅助功能 → VoiceOver |
| **Linux** | ORCA | AT-SPI2（D-Bus `org.a11y.Bus`）；`gsettings screen-reader-enabled` | `orca --replace`；设置 → 辅助功能 |
| **Android** | TalkBack | AccessibilityService；`adb shell settings get secure accessibility_enabled` | 设置 → 无障碍 → TalkBack |
| **iOS** | VoiceOver | UIAccessibility（设备端）；主机侧只能给指引 | 设置 → 辅助功能 → VoiceOver（设备端操作） |
| **鸿蒙** | 屏幕朗读 | AccessibilityExtensionAbility；`hdc shell` 只读查询 | 设置 → 辅助功能 → 无障碍 → 屏幕朗读 |

```bash
python -m sysweeper a11y --platform windows   # 只看 Windows 讲述人（非 Windows 上时给指引）
python -m sysweeper a11y --platform android   # 只看 Android TalkBack
python -m sysweeper a11y --platform harmony   # 只看鸿蒙屏幕朗读
python -m sysweeper a11y --platform any       # 多系统概览 + 权威文档
```

> iOS 与鸿蒙**不允许主机直接开启读屏器**，工具只给设备端指引，绝不尝试改写设备状态；
> Android 用 `adb settings put secure` 属变更操作，默认关闭（opt_in）。

标准引用同样三层：**国标** GB/T 37668 / GB/T 38652 → **国际** AT-SPI2、W3C WCAG 2.2 / WAI-ARIA 1.2、
ITU-T F.790 → **地区** EN 301 549（欧盟）/ Section 508（美国）/ JIS X 8341（日本）。
GUI「无障碍」窗口与 `a11y` 命令的输出已去除框线等装饰字符，便于读屏器连续朗读。

## 第三方引用、许可证与安全护栏（v0.5.19）

把用户要求「导入」的开源仓库作为**只读引用与可选方案**登记到对应能力，**本工具不打包、不运行其二进制**；
用户需自行按各自许可证与平台安装使用。

### 导入清单（合并到网络互联互通共享资源 / 硬件优化 / 开源下载）

| 仓库 | 用途归类 | 许可证 | 仓库链接 |
|---|---|---|---|
| yhan-sun/p2wlan | 网络互联互通：P2P 虚拟局域网（自组网补充） | MIT | https://github.com/yhan-sun/p2wlan |
| daeuniverse/dae | 网络互联互通：eBPF 高性能透明代理 | AGPL-3.0 | https://github.com/daeuniverse/dae |
| zhiyi7/gfw-pac | 网络互联互通：PAC 文件生成器（直连/代理分流） | Apache-2.0 | https://github.com/zhiyi7/gfw-pac |
| 2dust/v2rayN | 网络互联互通：Xray/sing-box GUI 客户端 | GPL-3.0 | https://github.com/2dust/v2rayN |
| rakanki911/DLSS5-Swapper | 硬件优化：DLSS5 一键安装/调优/还原（用户选择） | MIT | https://github.com/rakanki911/DLSS5-Swapper |
| aria2/aria2 | 开源下载软件：多协议多源下载（CDN/P2P 开关） | GPL-2.0 | https://github.com/aria2/aria2 |

> 说明：gfw-pac 仓库根 `LICENSE.txt` 经解码确认为 **Apache License 2.0**（GitHub API 自动判定为
> `NOASSERTION`，以仓库内实际 LICENSE 文件为准）。

### 许可证单独归档

仓库 `licenses/` 文件夹集中存放文档提及的许可证与引用来源：

- `MIT.txt` / `Apache-2.0.txt` / `GPL-2.0.txt` / `GPL-3.0.txt` / `AGPL-3.0.txt`
  —— 各含 SPDX 标识、官方全文链接、核心义务摘要；
- `README.md` —— 索引：逐条列出每个导入仓库的名称、仓库链接、许可证 SPDX、许可证全文链接与用途。

### 安全护栏（必读，呼应 `any_interop_policy`）

- **同人共享只限本人授权网络与算力**：同一人登录的多台设备共享 CPU/GPU/NPU/TPU/内存/网络出口；
- **个人数据与关键资产数据（凭据/密钥/钱包/通讯录/文档）一律不共享**；
- **绝不盗用他人网络互联互通能力**：不蹭他人房间/代理出口、不转发他人流量；
- 任何以「共享」之名索取密码/密钥/证件原件的，均为盗用风险，应拒绝。

```bash
python -m sysweeper thirdparty            # 全部第三方引用清单
python -m sysweeper thirdparty interop    # 网络互联互通方案
python -m sysweeper thirdparty hw         # 硬件优化（由用户选择）
python -m sysweeper thirdparty download   # 开源下载软件
python -m sysweeper thirdparty cdn-p2p    # CDN / P2P 开关说明
python -m sysweeper thirdparty licenses   # 许可证引用来源汇总
```

GUI 新增「第三方网络/硬件」面板（底部按钮），内容与 CLI 子命令一致。

## 安全基线（借鉴 docker-easyconnect，v0.6.40）

分析 docker-easyconnect（把深信服 EasyConnect 跑进 Docker、端口默认绑 localhost、tun 侧入站
默认拒绝）后，把其工程纪律沉淀为本工具的**安全基线**（纯文档注记 + 只读指引，不自动改配置）：

- **D5 对外服务端口默认只绑 `127.0.0.1`**：本工具本机 Web 控制台（`src/deno/console.ts`）默认
  `host:"127.0.0.1"`、文档明写「只本机可访问」；任何对外暴露须用户显式开启并自担风险。
- **D6 tun/对外侧入站默认拒绝**：远程接入（`remote`）与网络（`network`）任务把「对外暴露面」
  当作风险前提——明文风险只在不可信网上成立；隧道/长连接只管本端保活韧性（见
  `remote_keepalive_guidance`），不扩大对外暴露面。
- **D1 只封装不重分发闭源/第三方二进制**：本工具只读探针 + 指引，绝不重分发第三方二进制、
  绝不读 dmidecode 硬件指纹等可能触及凭据/隐私的探测（见 repo guard 与 `netauth` 不存原始 PII）。
- **D7 凭据只走环境变量不落盘**：远程接入审计只读配置取值，绝不读取或解密任何口令/私钥。

> 这些纪律与「只读红线」同源同向：工具出方案，用户在图形界面或厂商工具里确认施工。



## OpenWrt 路由器系统只读接口与插件支持（v0.5.20）

把 **OpenWrt**（面向路由器/嵌入式设备的 Linux 发行版）作为一类系统能力接入，并提供一套
**安全优先的插件框架**，使既有能力与用户自定义能力都能以「只读插件」形式统一登记与调用。

### OpenWrt 原生只读接口（`native/openwrt.py` + `data/openwrt_docs.json`）

各子系统仅做**只读探测与文档引用**，绝不自动执行写操作：

| 子系统 | 只读接口 | 说明 |
|---|---|---|
| 固件/板型 | `/etc/openwrt_release`（DISTRIB_*）、`/etc/os-release`（ID=openwrt）、`/tmp/sysinfo/{board_name,model}` | 识别型号、版本、目标、架构 |
| UCI 配置 | `/etc/config/*` 解析 + `uci show` | 审计配置节/接口/桥接；**只展示敏感项「存在性」，绝不回显 secret 明文** |
| 包管理 | opkg（`/usr/lib/opkg/status`）/ apk（`/usr/lib/apk/db/installed`），23.05 用 opkg、24.10 起默认 apk | 只读盘点已装包 |
| 网络 | `/etc/config/network` 解析 + `ubus call network.interface dump` | 接口/桥接/VLAN + 运行时状态 |
| 服务/procd | `/etc/init.d/*`、`ubus call service list` | 服务状态只读 |
| 构建系统 | ImageBuilder / SDK / feeds / 完整 menuconfig | **仅文档引用**，绝不调用 make / 不刷机 |

任务（`tasks/openwrt.py`）`platform="openwrt"`，因此只在 OpenWrt 平台出现；非 OpenWrt 环境
用 `--platform openwrt` 可预览，运行时优雅降级为指引。探测逻辑（`detect.py`）在
`/etc/os-release` 的 `ID=openwrt` 时把平台识别为 `openwrt`。

### 插件框架（`native/plugins.py`，安全优先）

插件把一项能力登记为一份**清单（manifest）**：声明它依赖哪些**已审读**的只读原生函数
（`native` 字段）、暴露哪些能力、对应哪些任务。**插件不能执行任意代码**——其唯一可调用
的「执行入口」必须是 `NATIVE_ALLOWLIST` 白名单里的零参只读函数（返回 `(ok, msg)`）。

- **内置插件**（随工具发布）：`openwrt`（路由器系统只读接口）、`interop`（把 v0.5.19 导入的
  第三方网络互联引用聚合为一个插件，演示插件系统可统一承载既有能力）。
- **用户插件**：把一枚 `*.json` 清单放到 `$SYSWEEPER_PLUGINS_DIR` 或仓库 `plugins/` 目录即被
  自动发现；随包附带示例 `plugins/openwrt.example.json`（与内置 openwrt 插件同构）。
- **安全护栏（最关键）**：`plugin_validate` 校验每一份清单——`id` 仅允许安全字符、`native`
  入口必须全部落在只读白名单内；含任意命令、路径、shell 元字符或非白名单函数的清单**直接拒绝
  注册**（防命令注入、防任意代码执行）。插件不持有可写入口，所有调用最终回到 `runner._run_native`
  的只读函数。

```bash
python -m sysweeper openwrt              # OpenWrt 能力总览（非 OpenWrt 降级为指引）
python -m sysweeper openwrt uci          # UCI 配置只读审计
python -m sysweeper openwrt pkgs         # 已装软件包盘点（opkg/apk）
python -m sysweeper plugins              # 已注册插件清单
python -m sysweeper plugins show --id openwrt   # 查看 openwrt 插件清单
python -m sysweeper plugins run  --id openwrt   # 只读运行 openwrt 插件
```

GUI 新增「OpenWrt」与「插件」两个面板（底部按钮），内容与 CLI 子命令一致。


## OpenWrt 子系统补全、高危写操作指引与可扩展插件白名单（v0.5.21）

在 v0.5.20 的只读底座上继续做三件事：**补齐路由器核心子系统**、**把危险写操作变成
「只预检 + 给命令」的 opt-in 指引**、**让插件白名单可安全扩展**。全部保持「只读优先、
绝不自动执行写操作」的底线。

### 1. OpenWrt 只读子系统补全（防火墙 / 无线 / DHCP / 存储）

新增 4 个只读报告与对应任务（`risk=low`、非 opt-in）：

| 子系统 | 只读接口 | 说明 |
|---|---|---|
| 防火墙 | `/etc/config/firewall` 解析 + `fw4 print` | zone / forwarding / rule / redirect、区域网络归属、NAT(masq)、input/output 策略 |
| 无线 | `/etc/config/wireless` 解析 | radio（频段/信道/禁用）与 wifi-iface（模式/加密）；**密码仅提示「含密码」，绝不回显明文** |
| DHCP/DNS | `/etc/config/dhcp` 解析 | dnsmasq 实例、地址池(start/limit)、静态租约条目数 |
| 存储 | `/etc/config/fstab` 解析 + `df -h` | 挂载点(fstype/enabled)、overlay 叠加根；**不 resize/格式化** |

### 2. 高危写操作「安全指引」层（`native/openwrt_write.py`，opt-in，绝不执行）

把 sysupgrade / 包管理 / UCI 写配置 / 服务启停这四类**危险写操作**做成
**`risk=high` + `opt_in=True`（默认关闭）**的指引任务：只做**只读预检**（读固件/板型、
识别包管理器、列配置包与服务名），然后**把确切命令作为文本打印出来**；**从不调用任何写命令**
（该模块源码零 `subprocess` 调用，有测试守护这条不变量）。

| 任务 | 覆盖 | 指引要点 |
|---|---|---|
| `openwrt_sysupgrade_guide` | 固件刷写 | 强调「同型号匹配 + 先 `sysupgrade -b` 备份」；只给命令文本，绝不刷机 |
| `openwrt_pkg_write_guide` | opkg/apk 安装·升级·卸载 | 先只读确认依赖，再手动执行；opkg(≤23.05)/apk(≥24.10) 自适应 |
| `openwrt_uci_write_guide` | `uci set/commit` | 先 `uci export` 备份、`uci changes` 预览、`uci revert` 可回滚 |
| `openwrt_svc_write_guide` | 服务启停·重载 | 提醒重启网络/防火墙会断网，远程需带外通道 |

默认不出现（`opt_in`），须 `--opt-in` 且确认才可见；即使可见也**只是打印命令**。
写指引层**刻意不进入插件白名单**——写操作只能由用户显式选择的 opt-in 任务触发，
不允许被插件间接驱动。

### 3. 插件白名单可安全扩展（`register_native`）

白名单不再硬编码：`register_native(*names)` 可把**本包内已存在**的零参只读函数登记进白名单。
这是**「可扩展」而非「可注入」**——安全底线不变：

- 入口名必须是严格 `module.func` 标识符（杜绝路径/命令/shell 元字符）；
- 模块必须真实存在于 `sysweeper.native` 内、函数必须可调用（无法引入任意外部代码）；
- 写指引层 `openwrt_write` 显式**拒绝**进入白名单；
- 登记后的入口与静态条目同等对待（`runner` 零参 `fn()` 调用）。

新增 CLI 动作 `plugins allowlist` 展示当前生效白名单（静态 + 运行时登记），便于检视。

```bash
python -m sysweeper openwrt firewall      # 防火墙只读报告
python -m sysweeper openwrt wireless      # 无线只读报告（不回显密码）
python -m sysweeper openwrt dhcp          # DHCP/DNS 只读报告
python -m sysweeper openwrt storage       # 存储只读报告
python -m sysweeper openwrt write         # 高危写操作指引（只预检+命令文本，绝不执行）
python -m sysweeper plugins allowlist     # 查看只读白名单（静态+运行时登记）
# 高危写指引任务默认关闭，需显式开启：
python -m sysweeper --platform openwrt --opt-in list   # 预览含 opt-in 的写指引任务
```

GUI 的「OpenWrt」面板新增防火墙/无线/DHCP/存储按钮与「⚠ 写操作指引」按钮；「插件」面板新增
「只读白名单」按钮。


## 无障碍适老化（面向老年人）+ Android 8 向下适配（v0.5.22）

把 Android 支持面**下探到 Android 8.0（API 26）**，并新增一整条**面向老年人 / 高龄用户**
的无障碍只读体检线。

### 1. 为什么必须按 API 逐项门控

Android 的适老化开关散落在 `settings` 的三张表里，而且**相当一部分是按 API 级别才引入的**：

| 开关 | settings 键 | 最低 API | 低版本时的正确说法 |
|---|---|---|---|
| 字体缩放 | `system/font_scale` | 1 | 全版本可用 |
| 读屏服务 | `secure/enabled_accessibility_services` | 14 | 全版本可用 |
| 放大镜 | `secure/accessibility_display_magnification_enabled` | 17 | 全版本可用 |
| 减弱动画 | `global/*_animation_scale` | 17 | 全版本可用 |
| **色彩校正** | `secure/accessibility_display_daltonizer` | **26** | 「API 26 起才引入，此版本无此开关」 |
| 字重微调 | `system/font_weight_adjustment` | 28 | 同上 |
| 护眼夜览 | `secure/night_display_activated` | 28 | 同上 |
| **高对比度文本 / 深色模式** | `secure/accessibility_high_text_contrast` / `ui_night_mode` | **29** | 同上（Android 8/9 给等效替代建议） |

老设备上盲写这些 key 会静默失败或抛 `SecurityException`，用户「我都开了为什么没变化」往往就来自
这里。所以 `native/android.py` 新增 `MIN_API` / `API_NAMES` / `supports()` / `_sdk_gate()`，
**每个探针声明自己的最低 API；不支持就明说「此版本无此开关」，绝不伪装成已开启**。

同时修掉一个既有缺陷：`and_app_hibernate`（`cmd package set-app-hibernate`）其实是 **Android 11
（API 30）** 才有的官方子命令，此前没写 `min_ver`，会在 Android 8/9/10 上被列出来却必然失败。
现已补上 `min_ver="11"`，低版本**直接不出现**（不是失败，是不适用）。

### 2. 适老化只读探针（只体检，不代改）

```bash
python -m sysweeper android          # 完整适老化区块
```

| 探针 | 读什么 | 适老化视角的判断 |
|---|---|---|
| `font_scale_report` | 字体缩放系数 | `<1.0` 偏小 / `1.15–1.3` 已放大 / `≥1.3` 大字体档 |
| `font_weight_report` | 字重微调（API 28+） | 对低视力老人比无限放大字号更省版式 |
| `a11y_display_report` | 放大镜 / 色彩校正 / 高对比 / 深色（**逐项判版本**） | 老设备最实用的是放大镜；8/9 无高对比度则给等效替代 |
| `a11y_speech_report` | TalkBack / 无障碍服务清单 | 读屏是视力障碍核心依赖 |
| `a11y_motion_haptics_report` | 三项动画缩放 + 触感 + 提示音 | 动画降 0 防眩晕；触感/提示音是非视觉反馈确认 |
| `a11y_eyecare_report` | 亮度 / 息屏 / 夜览 | 老花与白内障需更高亮度；自动亮度反而更累 |
| `android_compat_report` | 各接口最低 API × 本机 API | 回答「这台老安卓还能不能被管」 |

**安全设计：只读，且刻意不代改。** 全部只 `settings get`，一个 `put` 都不写（有测试用 AST 守护）。
理由很硬——替长辈打开 TalkBack / 放大镜 / 移除动画属于**改变其使用习惯**，开了没当面教反而更糟
（TalkBack 一开，触控手势全变：单指点=朗读、双指点=返回）。所以本工具只做「体检 + 建议」。

新增 8 个任务（`risk=low`、非 opt-in，`min_ver="8"`）：

| 任务 | 内容 |
|---|---|
| `and_a11y_report` | 适老化体检总报告（五类开关一次性读取） |
| `and_a11y_font` | 字体缩放与字重核对 |
| `and_a11y_display` | 放大镜 / 色彩校正 / 高对比度（按版本门控） |
| `and_a11y_talkback` | 读屏服务状态核对 |
| `and_a11y_motion` | 移除动画 + 触感反馈核对 |
| `and_a11y_eyecare` | 亮度 / 息屏 / 护眼夜览核对 |
| `and_a11y_guide` | **纯文字**适老化八条清单（无需 adb，可直接念给长辈） |
| `and_compat_audit` | Android 8 向下兼容口径总览 |

标准依据：WCAG 2.1/2.2（1.4.3 对比度、1.4.4 文字可放大、2.3.3 动画可关闭）、
GB/T 37668-2019《信息技术 互联网内容无障碍可访问性技术要求与测试方法》、AOSP Accessibility 官方文档。

`data/android_docs.json` 新增 `accessibility`（无障碍框架）与 `eyecare`（护眼与显示偏好）两条文档；
`data/versions.json` 补齐 Android 8 / 8.1 / 9 / 10 / 11 / 12 / 12L 的版本条目与 API 口径。


## OpenJDK / JVM 只读体检（v0.5.22）

「推进 openJDK」的含义是**把 OpenJDK 当成被体检的对象**，而不是在工具里装 JDK。
与 Linux/Windows/macOS 那一层同构：按它自己的规范与接口逐项只读核对。

```bash
python -m sysweeper jdk
```

| 探针 | 只读命令 | 说明 |
|---|---|---|
| `java_runtime_report` | `java -version` / `javac -version` | JAVA_HOME、是否 JRE-only、运行架构 |
| `java_properties_report` | `java -XshowSettings:properties` | **只输出 30 余个白名单键**；口令/令牌类只报「存在」不回显值 |
| `modules_report` | `java --list-modules` | JPMS 模块清单与顶层分类（JDK 8 明确降级） |
| `module_describe_report` | `java --describe-module java.se` | 核心模块的导出面与依赖面 |
| `gc_report` | `java -XX:+PrintFlagsFinal` | 报告当前生效的 GC（G1/Parallel/Z/Shenandoah/Epsilon） |
| `jit_report` | 同上（只筛 JIT 标志） | TieredCompilation、CompileThreshold、内联上限 |
| `diag_tools_report` | **只查 PATH** | jcmd/jps/jstack/jmap/jstat/jfr 是否可用，不执行子命令 |
| `jvm_processes_report` | `jps -l` / `jcmd -l` | 只列进程，**不 attach、不 dump** |
| `jfr_capability_report` | 查工具与版本 | **不 start、不 dump**（录制属写操作） |
| `build_tool_cache_report` | 遍历目录统计 | Gradle / Maven 缓存体积，**不删任何文件** |

### 为什么不整段 dump 系统属性

`-XshowSettings:properties` 会把所有系统属性打出来，其中混着 `http.proxyPassword`、令牌、
带凭据的 URL 拼接串。本模块只挑白名单键输出，且对疑似含口令的键（`password`/`token`/`secret`/
`credential`/`auth`…）**只报存在性、绝不回显值**——与 OpenWrt 层的敏感键处理同一条底线。
有测试专门守护这条不变量（`test_properties_report_never_echoes_secrets`）。

`FORBIDDEN_SUBCOMMANDS` 明确列出**不执行**的高副作用子命令，防止后续误加：
`jcmd GC.run`（触发 full GC）、`jcmd heap_dump`（GB 级写盘）、`jmap -histo:live`（强制 full GC）、
`jfr start`/`JFR.start`（持续写盘）、`VM.set_flag`（运行期改标志）。

新增 9 个任务（`requires_lang="java"`，**没装 JDK 时自动隐藏，不强求安装**）：
`jdk_runtime` / `jdk_properties` / `jdk_modules` / `jdk_gc` / `jdk_jit` / `jdk_diag` /
`jdk_jfr` / `jdk_build_cache` / `jdk_nohard_guide`（高危动作清单，纯文字指引）。

标准依据：OpenJDK 官网、JEP 261（JPMS）、JEP 439（JEP Generational ZGC）、JEP 379（Shenandoah）、
Oracle GC Tuning Guide、Java SE 规范第 7 章（Code Generation）、JFR API 文档。


## Linux 内核 module / firmware / plugin(s) 只读层（v0.5.22）

「引入、参考、模仿、进阶、超越 linux kernel 源码的 module(s)、firmware、plugin(s)」
在这里落地为**按内核源码自己的组织方式做只读体检**——不把内核源码搬进来。

Linux 世界里对应「可插拔」的恰好是三层，各给一个只读视图：

| 层 | 只读接口 | 对应 Documentation |
|---|---|---|
| **module(s)** 可加载内核模块 | `/proc/modules`、`/sys/module`（builtin vs live）、`/sys/module/*/parameters`、modinfo | `admin-guide/modules.rst`、`admin-guide/quick-kparams.rst` |
| **firmware** 固件 | `/lib/firmware` 统计、`/sys/class/firmware` 已加载固件、modinfo 声明的固件需求 | `driver-api/firmware/`（request_firmware 框架） |
| **plugin(s)** 内核级可编程插件 | eBPF：BTF、`/sys/fs/bpf`（bpffs）、`unprivileged_bpf_disabled`、可挂 kprobe 函数数、tracefs | `bpf/`、`trace/` |

eBPF 是现代 Linux 事实上的「内核级可编程插件」：Cilium、bpftrace、systemd 的 BPF 单元、
多数可观测性 agent 都建在它上面；`/sys/kernel/btf/vmlinux` 存在则意味着可用
**BPF CO（Compile Once, Run Everywhere）**——同一份 `.o` 跨内核版本加载。

```bash
python -m sysweeper kmod
```

11 个只读探针：`loaded_modules_report`（含 refcnt 非 0 = 卸载不掉的模块）、
`sys_module_report`、`module_params_report`、`modinfo_report`、`firmware_report`、
`firmware_class_report`、`bpf_capability_report`、`module_sysctl_report`（taint / modules_disabled）、
`blacklist_report`、`power_state_report`、`thermal_report`。

### 安全边界：这些操作本工具一律不做

模块装卸是 **root 权限的全系统最高危动作之一**，用错一个可致网络/存储不可用甚至不可开机。
`FORBIDDEN_COMMANDS` 明确列出禁令（并有 AST 测试守护源码里没有真正的装卸调用）：

- `insmod` / `rmmod` / `modprobe -r` / `depmod -a` —— 不执行
- `echo … > /sys/module/*/parameters/*` —— 写 sysfs = 运行期改内核行为，不执行
- 改 `/etc/modprobe.d` 黑名单 —— root 级改动，不执行
- 替换 `/lib/firmware` 下任何文件 —— 固件错配 = 硬件直接不可用，不执行
- `bpftool prog load` / `map create` —— 需 CAP_BPF，挂错程序可能拖垮内核路径，不执行
- `echo deep > /sys/power/mem_sleep` —— 让机器进休眠，有数据风险，不执行

新增 11 个任务（`platform="linux"`，`risk="low"`，**全部无 shell 动作**，有测试守护）：
`kmod_loaded` / `kmod_sysfs` / `kmod_params` / `kmod_modinfo` / `kmod_firmware` /
`kmod_firmware_class` / `kmod_bpf` / `kmod_sysctl` / `kmod_blacklist` / `kmod_power` /
`kmod_unload_guide`（卸载/换固件的前置检查清单，纯文字）。

`kmod_unload_guide` 讲清卸载前必查的四件事：refcnt 是否为 0、`lsmod` 确认无人使用、
`modinfo -F firmware` 确认固件需求、确认有可回滚手段（Live USB 或另一终端）。


## 任务档位（大而全 / 小而全）与数学量化评分（v0.5.22）

### 1. 四个命名档位：让「大而全」与「小而全」不再冲突

300+ 项任务全开等于没人敢用，砍到十几项又等于「不全」。解法是把「选哪些任务」从
**「手工挑 300 个 checkbox」变成「选一个档位名」**：

| 档位 | 定位 | Linux 命中数 |
|---|---|---|
| `minimal` | **小而全**：零风险只读体检 + 纯文字指引，**保证零风险** | ~92 |
| `lite` | 保守档：加回低危可逆执行项，排除卸载/删除 | ~137 |
| `standard` | 默认档：低/中危全覆盖，不含 opt-in | ~165 |
| `full` | **大而全**：含高危项与 opt-in 高影响项 | ~197 |

另有 4 个**场景档**（由基础档派生，不重复定义规则）：`readonly-audit`（只读审计）、
`daily-clean`（日常清理）、`deep-opt`（深度优化）、`elderly-friendly`（适老化：只读 + 文字指引）。

```bash
python -m sysweeper profiles list                      # 档位清单
python -m sysweeper profiles show --profile minimal    # 某档位详情（含数学评分）
python -m sysweeper profiles tasks --profile standard  # 列出命中的任务
python -m sysweeper profiles compare --profile minimal --against full

# 档位接入主流程（--profile 是所有子命令的通用参数）
python -m sysweeper clean --profile lite --apply --yes
python -m sysweeper scan  --profile minimal           # 零风险体检
python -m sysweeper list  --profile standard
```

**档位是声明式的**：只用「最大风险 / 是否含 opt_in / 分类白名单 / 关键词排除 / 语言依赖」
这几个正交维度描述，**不写死任何具体任务 id**。这样新增任务时**无需改档位定义**——
只要符合语义，档位自动跟着扩展。这是它能长期维护的关键（与「硬编码一个 minimal 列表」的本质区别）。

**安全不变量**（有测试守护）：选档位**不等于授权执行**。`full` 虽含 opt-in 与高危项，
执行仍需 `--opt-in` + `--yes` + `--apply` 三重确认；档位只影响「默认列入哪些」，
不改变底层执行路径的确认逻辑。另有单调性断言：`minimal ⊆ lite ⊆ standard ⊆ full`，
且 `minimal` 在全部 7 个平台上都**零 opt_in、零非 low 风险、零语言依赖**。

### 2. 数学量化评估：借鉴 openai/math 的理念，但不 vendor LaTeX

先说清一件事，避免误解与浪费：[`openai/math`](https://github.com/openai/math) 是
**LaTeX 数学宏的集合**（`\frac`、`\sum`…），服务于 KaTeX / MathJax 这类公式渲染库，
本身不含任何与「系统优化」相关的内容。所以「引入 math.git」有两条路：

- **不采用**：vendor 上千个 LaTeX 宏。那会让本工具从「零第三方依赖的系统优化器」
  变成「带字体/宏解析的排版工具」，**与功能零增益**，且违背仓库第一原则。
- **采用（本模块）**：把 openai/math 背后的真正理念——**「用数学把话说精确」**——落到工程上。
  公式的价值在于把模糊判断变成可计算、可比较、可复现的量。

`native/metrics.py`（纯标准库，`math` 即可）提供：

| 指标 | 公式 | 回答什么问题 |
|---|---|---|
| min-max 归一化 | x' = (x−min)/(max−min) | 不同量纲怎么放进同一个加权和 |
| **WSM 加权评分** | S = Σ wᵢ·x̂ᵢ，Σwᵢ = 1 | 一个任务集覆盖得够不够全 |
| **Shannon 熵 / 归一化熵** | H = −Σ pᵢ log₂pᵢ，除以 log₂n | 分类分布均不均衡（会不会偏科） |
| Jaccard 相似度 | J = \|A∩B\|/\|A∪B\| | 两档位/两平台的任务集重合多少 |
| Gini 系数 | G = Σ(2i−n−1)pᵢ /(n·Σpᵢ) | 平台任务分布是否过度集中 |
| 余弦相似度 / 变异系数 | cos / CV=σ/μ | 能力画像比较、相对离散度 |
| 覆盖缺口检测 | 集合差 | 哪个分类一条任务都没有 |

```bash
python -m sysweeper score              # 全库评分 + 熵分布 + 覆盖缺口
python -m sysweeper score balance      # 平台间均衡度（Gini / CV）
python -m sysweeper score profile --profile minimal
```

WSM 的四个分项与权重：覆盖广度 `breadth` 0.30、分布均衡 `entropy` 0.25、
任务深度 `depth` 0.25（用饱和指数 `1 − e^(−n/40)`，因为 20 个和 200 个任务的边际价值不同）、
安全性 `safety` 0.20（高危按 1.0 惩罚、中危按 0.5×0.5）。

**它真的诊断出了问题**——本机实测结果：

```
全库覆盖度评分：0.9377（覆盖 9/9 分类，341 项任务）
分类分布：maintenance=103 optimize=72 cleanup=68 network=49
          hardware=15 accessibility=14 arch=8 privacy=6 fonts=6
归一化熵 0.8142 / Gini 0.4829 → 结论：privacy 与 fonts 明显偏少
平台均衡度：Gini 0.4301，CV 0.9577 → any=103 linux=94 … unix=12 harmony=11
```

所有除法都有零分母保护，空集/单元素集绝不抛 `ZeroDivisionError`（有测试覆盖）。

### 3. 顺带修掉的两个既有缺陷

1. **`task_standards` 短关键词劫持长关键词**：原按关键词表**顺序**首次命中即返回，
   短关键词会劫持长关键词——「JPMS 模块系统」会被短词 `pm`（Android PackageManager）误判。
   现改为**最长匹配优先**，取最具体的语义。
2. **档位参数留空时静默当成空档位**：`profiles compare` / `show` / `tasks` 与
   `score profile` 在没给 `--profile` 时会落进一个「不存在但能通过校验」的档位，
   于是照样打印「对比 0 vs 197」这种无效结论。现统一走 `_profile_arg`：
   缺省回落 `minimal`，非法档位直接列出可选档位并退出（`list/scan/clean/notes`
   则按原路径以退出码 2 拒绝）。


## 架构与开源硬件（龙芯 LoongArch / MIPS / RISC-V / OSHWA）

架构是**独立于操作系统的另一维度**：同一条清理/优化在不同指令集上的工具链与做法并不相同
（例如 MIPS 端序、龙芯的二进制翻译层）。因此本项目把架构作为一等公民：

| 架构 | 说明 | 标准/组织 |
|---|---|---|
| **龙芯 LoongArch** | 国产自主指令集（2021 年随 3A5000 发布），含向量 LSX/LASX、虚拟化 LVZ、二进制翻译 LBT | 龙芯中科（国产自主，国家标准见 `std.samr.gov.cn`） |
| **MIPS** | MIPS32/64 Release 6；含龙芯早期 Godson 授权机型与路由器/嵌入式设备 | MIPS Technologies / MIPS Open |
| **RISC-V** | 开源免授权费 ISA，RVA20/RVA22/RVA23 profiles | RISC-V International |
| **OpenPOWER / OpenRISC** | 开放的 Power ISA（含 Microwatt 开源核）、OpenRISC 开源核 | OpenPOWER Foundation / OpenCores |
| **x86 / ARM** | 主流架构；国产兆芯·海光（x86）、飞腾·鲲鹏（ARM）同属 | Intel/AMD/Arm |
| **开源硬件** | 设计文件在开放许可下发布；OSHWA 认证 UID、CERN OHL v2 许可 | OSHWA / CERN / DIN / CHIPS Alliance |

```bash
python -m sysweeper arch                 # 架构探测 + 三层标准 + 工具链 + GOARCH
python -m sysweeper arch --audience intl # 对外：国际标准在前
python -m sysweeper arch --audience eu   # 欧盟：DIN SPEC 3105 / EN 系列优先
```

架构任务（`--category arch`）：`arch_report`、`arch_loongarch`、`arch_mips`、`arch_riscv`、
`arch_open_hardware`、`arch_toolchain`；龙芯与 MIPS 的 Linux 平台专属项
`linux_loongarch_source`（源与包架构核对）、`linux_mips_cleanup`（嵌入式精简清理）；
以及 `arch_go_cross_build`（按架构设置 GOARCH 构建，检测到 Go 才启用）。

探测接口：`uname -m` / `/proc/cpuinfo`（含 RISC-V 的 `isa` 行）/ `sysctl hw.machine` /
Windows `%PROCESSOR_ARCHITECTURE%`；未收录架构会提示可在 `data/arch.json` 补充，不报错。
GOARCH 映射：龙芯 `loong64`、MIPS `mips64le`/`mipsle`、RISC-V `riscv64`、OpenPOWER `ppc64le`、
x86 `amd64`、ARM `arm64`。

> 龙芯国标编号以国家平台（`std.samr.gov.cn`）检索为准——本仓库只声明「国产自主架构」并给出
> 平台检索入口，不臆造标准号；如需精确编号可在 `data/arch.json` 的 `national` 层补充。

## 按「自身协议与接口」跟踪的文档层（系统软件 / 鸿蒙 / 小程序端 / 包管理器 / 容器运行时 / 存储与文件系统）

内核（硬件·软件·网络子系统）与桌面环境（GNOME/KDE/XFCE）之后，同一套
「**权威文档参考 + 只读原生探测 + 任务**」模式继续推广到其余软件。关键在于
**每个软件都按它自己的协议与接口核对**，绝不套用另一套路径：

| 层 | 命令 | 各自的协议 / 接口 |
|---|---|---|
| **其余系统软件** | `sysweeper syssoftware` | systemd 单元 + `org.freedesktop.systemd1`；D-Bus Specification；`org.freedesktop.NetworkManager` + nm-settings(5)；PipeWire 原生 SPA + `org.pipewire`；`org.bluez`；udev(7) 规则 + hwdb(7)；`org.freedesktop.PolicyKit1`；wayland.xml + xdg-shell |
| **鸿蒙** | `sysweeper harmony` | Stage 应用模型（UIAbility/Want）、ArkUI 声明式、SysCap 能力分层（canIUse）、HiLog（域/标签/级别）、hdc（client-server-daemon 三端）、HAP/HSP/HAR 包结构、分布式 IPC；uni-app 鸿蒙端仅支持 vue3 |
| **各小程序端** | `sysweeper miniapp` | 微信 `wx.*`（双线程）、支付宝 `my.*`（域名白名单 + getAuthCode）、百度 `swan.*`、抖音 `tt.*`、QQ `qq.*`、快手 `ks.*`；差异用条件编译 `#ifdef MP-XXX` 隔离 |
| **包管理器** | `sysweeper pkgmgr` | deb(ar 归档) + Debian Policy 控制字段 + `apt-get clean/autoremove`；RPM 标签化头 + rpmdb + `dnf clean all`；`.apk` + APKINDEX + `apk cache clean`；`.pkg.tar.zst` + `*.db` + `paccache -rk2`；Formula/Cask Ruby DSL + `brew cleanup`；WinGet YAML 清单 + REST 源；PEP 503 索引 + wheel + `pip cache purge`；Registry API + `_cacache` + `npm cache verify`；snapd REST + OSTree refs/commit |
| **容器运行时** | `sysweeper container` | OCI runtime-spec（`config.json`）+ Docker 镜像 manifest(v2+json) + Engine API(`/var/run/docker.sock`) → `docker system prune`；OCI + rootless → `podman system prune`；content store + snapshotter → `nerdctl system prune` / `ctr` prune；BuildKit 内容寻址 build cache → `docker builder prune`；OCI image-spec(`digest` 共享层) → `skopeo`；LXC/LXD 存储池(ZFS/Btrfs/LVM) → `lxc image delete` / `lxc storage volume rm`；CRI gRPC → `crictl rmi` |
| **Windows 原生接口** | `sysweeper windows` | Win32 API（stdcall + UTF-16 宽字符 + GetLastError）→ `GetDiskFreeSpaceExW` / `GetTempPathW` / `SHEmptyRecycleBinW`；注册表 hive + REG_DWORD/REG_QWORD → `winreg.OpenKey/QueryValueEx`（只读）与 `reg add`（写）；DMTF CIM + WQL → `Get-CimInstance`（只读）/`Invoke-CimMethod`（写）；电源计划 GUID + subgroup/setting 两级 → `powercfg /list`//`getactivescheme` 只读、`/setactive`//`change`//`h /type` 写；servicing stack + CBS 组件存储 → `DISM /Get-CurrentEdition` 只读、`/StartComponentCleanup` 写（不做 `/ResetBase`）；WRP 资源保护 → `sfc /verifyonly` 只读、`/scannow` 写修复；存储感知 StoragePolicy DWORD → winreg 只读核对；传递优化 P2P 缓存 → `Get-DeliveryOptimizationStatus` 只读；UsoSvc + `Results\Detect` → winreg 只读（不用已弃用的 `wuauclt`） |
| **macOS 原生接口** | `sysweeper macos` | launchd 域层级 + plist 作业 → `launchctl list/bootout/disable`；XNU `sysctlbyname` → `sysctl -n/-w kern.*`；CFPreferences plist 后端 → `defaults read/write`；SUS catalog → `softwareupdate -l/--schedule`；APFS 容器/宗卷/快照 → `diskutil apfs list` / `verifyVolume` / `tmutil thinlocalsnapshots`；IOPMlib 电源配置 → `pmset -g/-a`（ hibernatemode / standbydelay，机型自动判别）；Gatekeeper 代码签名 + 公证 → `spctl --status/--master-enable`（只开不关）；System Configuration → `networksetup -listallnetworkservices/-setdnsservers` |
| **BSD 原生接口** | `sysweeper bsd` | `pkg` SQLite 本地库 + pkg+https 仓库 → `pkg info/audit/clean/autoremove`；rc(8) `xxx_enable` + rcorder 依赖图 → `service -e` / 改 `rc.conf`；BSD MIB → `sysctl -n/-w`（`net.inet.tcp.rfc1323` RFC 7323、`recvspace/sendspace` 只上调、`kern.maxfiles`、`vfs.zfs.arc_max`）；pf.conf 规则集/锚点/表 → `pfctl -s` 只读、`pfctl -e -f` 只启用不停用；OpenZFS zpool/dataset → `zpool list/status/scrub`、`zpool set autotrim=on`；`/etc/periodic/*` 周期脚本 → `periodic daily`；Ports Makefile + distfiles → `du -sh` / `make distclean` |
| **存储与文件系统** | `sysweeper storage` | ext4 extent 布局 + jbd2 日志 → `e2fsck -fn` / `e4defrag`；Btrfs COW B-tree + 子卷/快照 + qgroup → `btrfs balance` / `scrub` / `defrag`；XFS AG 分配组 + B+tree → `xfs_db -r -c frag` / `xfs_fsr` / `xfs_repair`(离线)；ZFS zpool + dataset + DMU/SPA 校验和 → `zpool trim` / `scrub` / `zfs destroy`；LVM PV/VG/LV + device-mapper + thin pool → `lvreduce` / `pvmove` / `thin_check`；fstrim FITRIM ioctl + ATA TRIM/SCSI UNMAP/NVMe DSM → `fstrim -av`；SMART ATA/SCSI/NVMe 属性 → `smartctl -H` / `-A` / `-t`；swap 签名页 + swapon(2) → `swapoff` + `mkswap` + `swapon` |

```bash
python -m sysweeper syssoftware   # 8 个系统软件：探测 + 文档 + 本机只读核对 + 任务
python -m sysweeper harmony       # 鸿蒙：工程侧 + hdc 设备侧（需设备已连接）
python -m sysweeper miniapp       # 6 个小程序端 + 跨端静态检查
python -m sysweeper pkgmgr        # 9 类包管理器：缓存占用 + 可清理项 + 任务
python -m sysweeper container      # 7 类容器运行时：磁盘占用 + 悬空镜像/卷/构建缓存 + 任务
python -m sysweeper storage       # 8 类存储/文件系统：占用/碎片率/健康 + 整理/校验/TRIM/重建任务
python -m sysweeper windows       # Windows 9 个系统接口：只读探测 + 官方写接口清单 + win_tune_* 任务
python -m sysweeper macos         # macOS 9 个系统接口：只读探测 + 官方写接口清单 + macos_tune_* 任务
python -m sysweeper bsd           # BSD 8 个系统接口：只读探测 + 官方写接口清单 + bsd_tune_* 任务
```

这些层的共同约束（也是本项目的底线）：

- **只读优先**：所有探测只读，仅统计大小与数量；未安装该软件时返回降级说明，**不强求安装**。
- **走官方接口**：清理命令用软件自己的官方子命令（`journalctl --vacuum-time`、
  `paccache -rk2`、`brew cleanup`、`pip cache purge`、`npm cache verify`），
  而不是直接删目录——例如 npm 官方把 `npm cache clean --force` 标为破坏性，故只用 `verify`；
  pacman 用保留 2 版的 `paccache` 而非全清 `-Scc`，以便仍能离线降级。
- **删包才标中风险**：只清缓存的是 low（可直接 `--apply`）；会删包/runtime 的是 medium，
  还需 `--yes` 确认。

## Go 组件（跨语言构建）

`src/go/` 是一个**纯标准库、零依赖**的 Go 命令行组件，让同一套分类/无障碍口径在没有
Python 的环境（或需要单文件二进制）下也能查询，并由 CI 交叉编译为多平台二进制：

```bash
cd src/go
go vet ./... && go build -o sysweeper-go .
./sysweeper-go standards --audience cn      # 国内优先：国标在前
./sysweeper-go standards --audience intl    # 对外：国际标准在前
./sysweeper-go a11y                         # ORCA / AT-SPI2 环境自检
./sysweeper-go arch                         # 架构/指令集（龙芯/MIPS/RISC-V）+ 开源硬件 + GOARCH
./sysweeper-go list                         # 支持的平台 / 语言 / 分类
./sysweeper-go version

# 交叉编译（CI 用同样方式产出 5 个平台）
GOOS=windows GOARCH=amd64 go build -trimpath -o sysweeper-go-windows-amd64.exe .
```

同时，语言任务侧也补齐了 Go 工具链相关项（检测到 `go` 才自动启用、未装则隐藏）：
`lang_go_modcache`（模块缓存）、`lang_go_build_cache`（构建缓存 GOCACHE）、
`lang_go_build`（`go build ./...` 预构建校验）、`lang_go_mod_tidy`（整理依赖，medium 风险）。

## uni-app（跨端目标）

uni-app 不是操作系统，而是「一套代码编译到 App / H5 / 各小程序」的跨端框架，因此作为**目标端**存在，需手动指定 `--platform uniapp`：

```bash
python -m sysweeper uniapp                                   # API 清单 + 任务一览
python -m sysweeper list  --platform uniapp --version 4      # 8 项清理/优化任务
python -m sysweeper scan  --platform uniapp --version 4
python -m sysweeper clean --platform uniapp --version 4 --apply --risk low  # 只跑低风险（工程侧）
```

> 端上 storage 清理（会清掉登录态/草稿）不能直接 `clean --apply`，而是做成了一个**真实可运行的 uni-app 页面**：`uniapp-cleaner/pages/cleanup/cleanup.vue`——用 `uni.getStorageInfoSync()` 统计、`uni.showModal` 二次确认、`uni.clearStorageSync/removeStorageSync` 执行，并给清理前后对比报告。复制进你的 uni-app 工程即可作「清理缓存」入口。详见 [`uniapp-cleaner/README.md`](uniapp-cleaner/README.md)。

**端上运行期缓存（按端分支）**：页面另设「清理端上缓存（H5/App）」按钮，先 `detectRuntime()` 识别端再分支——**H5** 走浏览器 Cache API（`caches.keys()` + `caches.delete()`，需 https/localhost 安全上下文）、**App** 走 5+ `plus.cache.clear('/', …)`；小程序/未知端则引导用上方 storage 清理。它与 storage 清理互相独立：storage 清的是 `uni` 键值存储（含登录态），而这里清的是「应用运行期缓存（图片/离线包）」，不碰登录态。

**uni-app 需要的原生能力与 API**（`data/uniapp_api.json`，每条含支持端与标准出处）：

| 能力组 | 代表 API | 与清理的关系 |
|---|---|---|
| 系统与设备信息 | `uni.getSystemInfoSync` / `plus.device.getInfo` | 先识别端，再选策略 |
| 本地存储 | `uni.getStorageInfoSync` / `uni.clearStorageSync` / `plus.cache.clear` | **端上垃圾主来源**，清理前需确认 |
| 网络与协议 | `uni.request` / `uni.getNetworkType` / `uni.connectSocket` | 仅能力参考；调优开关默认关闭 |
| 文件系统与构建产物 | `plus.io` / `unpackage/`、`node_modules/.cache` | 工程侧可自动清理 |
| 运行期与升级 | `plus.runtime.*` / `uni.getUpdateManager` | 安装/重启类一律标手动 |
| 界面与交互 | `uni.showModal` / `plus.nativeUI.confirm` | 清理前后的确认与反馈 |

对应任务分两类：
- **工程侧（开发机，可自动）**：编译产物、构建缓存、依赖缓存 —— 低风险
- **端上（App/小程序/H5，仅指引）**：storage、应用缓存 —— 中风险，需用户确认（清空会连登录态一起没）

> 相关标准出处：W3C Device APIs / Web Storage、RFC 9110(HTTP)、RFC 6455(WebSocket)、IEEE 802.11、HTML5+ (5+ App) 规范。

### 前后对比报告（`--report`）

无论 `scan` 还是 `clean` 都可加 `--report 路径` 生成报告，让「默认只分析不乱删」在结果层面也一目了然：

```bash
python -m sysweeper scan  --platform linux --version 24.04 --report report.md
python -m sysweeper clean --platform linux --version 24.04 --apply --risk low --report report.md
python -m sysweeper clean --platform linux --version 24.04 --apply --risk low --report report.json  # JSON 版
```

报告字段（Markdown 示例）：

- **处理前磁盘**：总容量 / 已用 / 可用（跨平台主盘，Windows 系统盘、其余根分区）
- **处理后磁盘** + **实际释放空间**：仅 `clean --apply` 有；磁盘可用空间增量即真实释放
- **可视化对比**：内嵌 ASCII 条形图（磁盘前/后已用占比 + 各任务预计可回收）
- **任务明细表**：任务 / 分类 / 风险 / 预计可回收 / 状态（分析·已执行·跳过）/ 结果

```bash
# JSON 报告可进一步用 chart 命令打印纯文本条形图（无图形环境也友好）
python -m sysweeper clean --platform linux --version 24.04 --apply --risk low --report report.json
python -m sysweeper chart report.json
```

> 备注：分析模式下「预计可回收」依赖真实存在的目录（如 `/var/cache/apt`），沙箱无对应目录时显示 `—`；真实机器上会给出估算值。`scan` 不会测量「处理后」磁盘（本就没改系统）。

## 低层码制：机器码 / 编译码 / 字符编码 / 通信码 / 逻辑转换码（v0.6.0）

`sysweeper.lowcode` 是包内的「底层视图」子包：把平时靠人肉心算的东西变成**可验证的纯函数**。
五层全部纯标准库、纯函数、只读、不联网，汇入口令 `sysweeper code`。

| 层 | 干什么 | 典型用途 |
|---|---|---|
| `bits` | 端序 / 位域 / 原码-反码-补码 / 格雷码 / BCD / 奇偶 / IEEE 754 | 抓包里 `0x12345678` 看着不对、驱动寄存器位域 |
| `chars` | ASCII 控制表 / Unicode 码点 / UTF-8-16-32 / Base 系列 / 百分号与 HTML 转义 / 摩尔斯 / 字符集互转 | 乱码排查、看一段字节到底是什么编码 |
| `comm` | CRC 六参数模型（8/16/32/32C…）/ 校验和 / HDLC-SLIP-COBS 成帧 / 线路编码 / 汉明码 / 波特率 | 对协议文档验算 CRC、算串口帧时间 |
| `logic` | 布尔求值 / 真值表 / SOP-POS / 卡诺图 / Quine-McCluskey / NAND-NOR 变换 / 加法器 | 看 ALU 与 `add` 指令、化简逻辑 |
| `machine` | Python 字节码 / Java class 常量池与 Code 反汇编 / x86-64 指令结构拆解 | 读 .pyc、看 class 文件、拆指令字段 |

```bash
# 概览
python -m sysweeper code

# 位层：-7 的 8 位补码档案
python -m sysweeper code bits --value -7 --width 8
python -m sysweeper code bits --value 0x3F800000 --action float

# 字符层：乱码排查——同一段字节用各编码试读，看得懂的那个就是答案
python -m sysweeper code chars --value d6d0cec4 --action mojibake
python -m sysweeper code chars --value 中文 --action charset

# 通信层：Modbus RTU 帧的 CRC 实测 + 8 个变种的标准 check 值比对
python -m sysweeper code comm --value 010300000001 --action crc
python -m sysweeper code comm --action baud --clock 16000000

# 逻辑层：化简并**验证等价性**（真值表逐行比对）
python -m sysweeper code logic --value 'A & B | !C' --action simplify
python -m sysweeper code logic --value 'A & B | !C' --action qm
python -m sysweeper code logic --value 100 --action adder --y 100 --width 8   # 看有符号溢出

# 机器码层
python -m sysweeper code machine --action py   --value 'x = 1 + 2'
python -m sysweeper code machine --action x86  --value 4889e5
python -m sysweeper code machine --action java --file /path/to/Hello.class
```

**诚实边界**（写在这里，避免误用）：

- x86-64 部分是**结构化拆解器**——它告诉你这条指令由哪些字段组成，助记符是启发式提示，
  权威表在 Intel SDM Vol.2 Appendix A / AMD APM；
- Java 部分是**够用的教学级**反汇编器，覆盖 0x00–0xC9 的操作数长度，遇到未收录指令会停下并说明位置；
- Python 字节码直接调 CPython 的 `dis`，与解释器版本强相关（3.11+ 有自适应字节码与 CACHE 项）。

每层的标准出处写在各自的 `STANDARD_REFS`（按国内 / 国际 / 地区三层），完整清单与逐项说明见
[`docs/低层码制.md`](../docs/低层码制.md)。实现正确性由单测独立验证，不依赖外部文档的可信度。

## 预警应急系统（v0.6.8）

一句话立项：**预警只有落在"离我多远"上才有意义**。所以第一件事不是接预警源，
而是**先把位置与距离算清楚**。完整说明见 [`docs/预警应急系统.md`](docs/预警应急系统.md)。

**定位口径三条**（按使用者定的，写死在 `native/emergency.py`）：

1. **首选基线 = 网络定位 + 基站定位**。室内、地铁、隧道、省电模式下常常没有导航信号，
   但网络与基站几乎总在——先用它，保证**任何情况下都有一个可用的位置与距离**。
2. **有导航定位时，导航 + 首选基线共同综合**，不是"有导航就丢掉基站"。
   按精度倒数平方加权，并给基线留 **5% 最低话语权**：导航主导但不独占，
   一次 GNSS 跳变不至于把位置甩飞。
3. **两源互相校核**：偏差超 2 km 标**存疑**，两套结果都摆出来，**不替用户判定哪个对**。

实测（基站 ±1500 m + 网络 ±5000 m + GPS ±8 m）：导航 95.0% / 基站 4.6% / 网络 0.4%，
综合结果 ±72 m，两源偏差 34 m。

**预警评估**：字段对齐 OASIS CAP 1.2，给出距你多远、是否在影响半径内、
粗估多久到边界（**只给量级，报告写明"不是预报"**）、以及你的位置精度。
按由近到远排序——预警场景下距离就是优先级。

**红线（写死）**：

- 不自动报警、不拨号、不发短信；SOS **只生成文本**，通道由你选
  （可贴到组网通信的全体广播，在断网时的同网段内发出去）。
- 订阅源**默认关闭**；开了也只拉你自己填的 http(s)，拉不到就报"未能获取"，
  **绝不编造预警**；非 http(s) 直接拒绝。
- **不凭 IP 编造坐标**；拿不到就报"未取到"，编造的定位比没有定位更危险。

**手动开关**（图形界面顶部「预警应急」按钮，勾选即生效、立即记住）：
定位 / 首选基站网络 / 与导航综合 / 预警评估 / 联网订阅（默认关）/ 呼救文本 /
避险点 / 物资核对——**关掉的功能直接返回关闭提示，不偷偷跑**（有测试守着）。

## 组网通信（v0.6.8）：iptux / 飞鸽传书 / wall

同网段的设备，不需要经过外网就能互相说话。断网、隔离网、家里宽带断了——
只要还在同一个局域网，消息就应该能到。完整说明见
[`docs/组网与分布式计算.md`](docs/组网与分布式计算.md)。

- **兼容现成协议**：IPMsg（飞鸽传书）UDP/TCP 2425，Linux 上的 iptux 就是它的开源实现。
  网里已有的飞鸽 / iptux 客户端**能直接收到消息，不用说服所有人装新软件**。
- **wall 式全体广播**：同网段终端都能收到。断网时这是最可靠的通知方式，不依赖外部服务器。
- **消息类型**：文字 / 图片 / 视频 / 文件 / emoji / 颜文字——**载荷不同、通道同一条**。
  颜文字是普通字符拼组，在老设备和纯文本环境里比 emoji 更可靠。
- **红线**：收到的文件**不自动落盘**，进待收清单由你显式接受；附件是**对端来拉不是我们推**。

## 分布式计算（v0.6.8）：BOINC 式，但砍掉信任链

BOINC 让项目方下发可执行程序，信任链是"我信任这个项目方"。本层**砍掉这条链**：
只跑**内置可验证算子**（白名单三个），**绝不下载、绝不执行任何外部代码**。

代价是算不了真实的科学项目；收益是——**网里任何一台机器入网，都不会因此获得
在你机器上执行代码的能力**。

- **冗余双投**：同一工作单元派给 k 个节点独立算，一致才接受，不一致标存疑重投。
  校验必须比计算便宜（哈希 O(1) vs N 次搜索；矩阵抽一行一列 O(n) vs O(n²)）。
- **调度用硬指标做上限**：核心数 × 空闲度 × 供电 × 是否计量网络。
  电池低于 20% 不派活；计量网络降权到 30%（**别让人替你交流量费**）。
- **预算纪律**：默认只出计划不真跑；真跑有硬性预算，**跑满即停**。
- **入网后本机也变强**：计算派活给强机、图形重活找有卡的机器（**只登记型号不跑负载**）、
  网络避开计量链路。
- **跨机派活闭环**（`native/distjob.py`）：工作单元**经组网文本通道**派出去、结果收回来。
  载荷是 `SW-WU1:` / `SW-RES1:` 前缀 + JSON——**通道里传的是参数不是代码**，
  白名单外的算子连解析都不认；收回的结果**必须复算校验**，伪造结果会被打回。
  默认 `dry_run=True` 只编码不出网。

## 安卓优先构建：8 与 14 两头卡住

`tools/build_android.py` —— **Android 8（API 26）是下探底线，14（API 34）是现行主流**。
能过 14，中间版本基本都能过，所以把力气花在代表两端的两条线上：

```
Android 8  (API 26): 248 项任务；low 227 / medium 20 / high 1
Android 14 (API 34): 249 项任务；low 228 / medium 20 / high 1
```

- 产物是**目标配置**（只存任务 id 与元信息，不存任何命令）。
- **不产出 APK**：本工程在安卓上以 Termux / adb shell 方式运行脚本——这点要说清楚。
- 其他平台按你的要求**只跑测试不构建**（`--target other`）。

## 扩展新任务

在 `src/python/sysweeper/tasks/<平台>.py` 的 `TASKS` 列表追加 `Task(...)` 即可，例如：

```python
Task(
    id="win_temp", platform="windows", title="清理临时文件",
    category="cleanup", risk="low",
    actions=[Action("shell", r'powershell -NoProfile -Command "Remove-Item $env:TEMP\* -Recurse -Force"',
                    "清空用户临时目录")],
    notes=["建议每月执行一次。"],
)
```

若某动作能用系统接口更好，直接写 `native` 通道（函数放 `native/<平台>.py`）：

```python
actions=[Action("native", "windows.empty_recycle_bin", "清空回收站（Shell32 API）")]
```

新增版本只需改 `data/versions.json`，任务匹配逻辑无需改动。

## 安全须知

- 工具**不会**删除系统关键文件；Windows/macOS 的系统保护路径、Linux 的当前内核均不在清理范围。
- `apply` 模式下，任何删除动作都可能不可逆，请先 `scan` 确认。
- 移动端：Android 经 adb 操作、iOS 为纯指引，均不连接未知设备、不执行来源不明命令。
- 本工具是「优化/清理助手」，**不替代**系统自带更新与厂商官方工具。
