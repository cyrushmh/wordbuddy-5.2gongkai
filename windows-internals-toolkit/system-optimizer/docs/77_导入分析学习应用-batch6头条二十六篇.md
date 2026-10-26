# 77 导入分析学习应用：今日头条 batch-6 二十六篇（UltraVNC / DsoFramer·AA / IOPaint / Ansible / TabClustPFN / DigUp / LangGraph / Code Video Model / Harness² / HatchZip / ioDraw / B码·PTP / agent.md / VBA / REA / gpu-unlock / Snow Shot / DeepInfer / 数学软件 / 导航大模型验证 / Prometheus·nVisual / ipset / GitHub 涨星榜 / DSH·CAD / MQTT / Cua）

> **来源**：用户指令「导入学习分析应用引用」batch-6（2026-10-25），今日头条技术文章 26 篇，已全部只读抓取正文核实（WebFetch 26/26）。
> **落点**：全部资源**只作只读分析**，不克隆、不安装、不构建、不下载、不复制其代码进本仓。
> **纪律红线**：只登记可核实事实；文章单方陈述的数字/结论标 `needs_verify`，不臆造；本仓守「无真实 counterpart 不加概念」纪律（#591 先例 docs/59、docs/70、docs/71、docs/76）——本轮 6 个数据层有真实 counterpart（remote_clients_docs / winternals_refs / chrono_theory_docs / network_docs / reverse_docs / toolchain_catalog），**同步回填 7 条**；其余各篇无 counterpart 或仅编目参考，**只沉淀为学习笔记**。

## 一、资源概览表（2026-10-25 只读核实）

| # | 文章 | 性质 | 技术要点（页面口径） | 边界分级 |
|---|---|---|---|---|
| 1 | UltraVNC 远程桌面 | 开源远程工具深度拆解 | GPL 永久免费无带宽限制；自研压缩算法弱网自适应；AES/SecureVNC/MSRC4 加密插件；双向文件传输/多显示器/文字聊天/安全模式远程；Server+Viewer 架构；防火墙放行端口 | **可回填**：remote_clients_docs.json 补 `ultravnc`（VNC/RFB 协议、GPL、加密插件口径） |
| 2 | 用 AA 复活 DsoFramer | COM/OLE 嵌入控件复活实践 | DsoFramer 为数十年停更的 C++/COM 原生 Office 嵌入控件；作者以 aardio（AA）+ AI（GPT 6 Astra→Gemini 4 Argon）重构，打开速度提升「数十倍」，发行体积缩至 96KB，兼容 Office/WPS；token 成本数千元级 | **可回填**：winternals_refs.json 补 COM/OLE 文档嵌入控件条目 + aardio 工具链参考 |
| 3 | IOPaint（AI 修图） | 开源 AI 图像修复工具 | 23,300+ Star（文章口径 `needs_verify`）；本地运行不上传；重绘/擦除/抠图/超分/老照片修复；Web UI 拖拽涂抹；MIT 生态模型可选 | 纯技术可学习（本仓无 AI 图像 counterpart） |
| 4 | Ansible 批量部署 100 台 | 自动化运维实战教程 | Inventory 分组+变量分层（host_vars>group_vars 小组>大组>all）；Playbook/Role 结构；声明式幂等（ok/changed/failed/skipped）；`-f 30` 并发、`--serial` 滚动、`--check --diff` 预演、`max_fail_percentage` 熔断；ansible-vault 管敏感信息；100 台 15~25 分钟（文章口径） | 纯技术可学习（候选 needs_action：toolchain_catalog 未见编排类目，不硬塞） |
| 5 | TabClustPFN | 研究论文解读（NeurIPS 2026） | 人大/罗格斯/新国大/MBZUAI；PFN 先验拟合网络做表格聚类；单次前向出划分+簇数概率分布（2–10 类）；SoftARI 可微目标；44 真实数据集 ARI 中位第一/并列第二；3,200 合成集 95% 候选集覆盖 96.8% | 纯技术可学习（无 counterpart） |
| 6 | DigUp | 语义搜索工具实测 | ARahim3/DigUp，5600+ 星（文章口径）；EmbeddingGemma 2 跨模态向量空间；一句话搜图片/PDF/文档/录音/视频并跳转到时刻；只读选定文件夹、不联网上传；Windows 0.7.0-beta.3/Mac 0.6.2；中文分词缺陷已确认待修；865MB 模型 | 纯技术可学习（无 counterpart） |
| 7 | LangGraph Agent 架构图 | 架构科普（一张图） | StateGraph 流程：任务输入→State 初始化→LLM 理解→工具调用→条件判断→输出；记忆管理/RAG/API/代码执行/外部系统/安全控制/运行监控 | 纯技术可学习（无 counterpart） |
| 8 | Code Video Model | 研究解读（微软） | 可执行代码（Three.js 程序）作为视频控制表示；「编程—渲染—检查—修订」迭代；proxy video 预演 <1 分钟；双通路（Qwen-VL 外观 / VAE 结构）互补；免训练阶段化条件调度（前 25% 去噪阶段介入） | 纯技术可学习（无 counterpart） |
| 9 | Harness² | 研究解读（Google Cloud AI Research） | Agent = Model + Harness；harness 8 组件（prompt/guardrails/memory/skills/tool guidance/scripts/subagents/plugin）；Propose→Probe→Compose 任务级递归 + 经验库（EXPERIENCE.md）harnessing 级递归；12 组配置全部涨分；skills/scripts 消融贡献最大；「较弱模型+改进 harness 可超较强模型原样」 | 纯技术可学习（无 counterpart，但流程纪律与本仓 needs_verify/门禁同构，重点笔记） |
| 10 | HatchZip | 存储工具实测 | xevrion/hatchzip，Rust，4 天 1,738 星；边解压边从尾部截掉压缩包省磁盘（180G 包 200G 空间 vs 传统 380G）；动工前 check 峰值空间规划（退出码 3=空间不足）；sidecar 抄底索引；五步固定顺序崩溃安全；进度本带版本号；restore 中途反悔；130+ 测试三真机；0.1.3 修两洞（重复命名/符号链接） | **可回填候选**：protec durability 域（磁盘空间纪律）——见落实动作 |
| 11 | ioDraw v3.7.0 | 桌面绘图工具发布 | 七种编辑器（流程图/思维导图/甘特/白板/代码图/数据图/海报）；AI 助手会话化（历史会话/连续追问改图/随时中断/先预览再插入/每文件 20 会话带 6 轮上下文）；甘特图自定义工作日历+AI 生成；文件存 AtomGit/GitHub/GitLab/Gitee | 纯技术可学习（无 counterpart） |
| 12 | B码对时 vs PTP 授时 | 电力授时技术对比 | IRIG-B（DC 精度优于 1μs，独立链路抗干扰，但单向无法补偿时延、不能跨交换机、无冗余切换）；IEEE 1588-2008 PTPv2 + 电力轮廓 C37.238-2017/61850-9-3:2016（双向测量自动补偿、BMCA 选主、硬件时间戳亚微秒）；北斗 B 码授时主流；混合架构（PTP 转 B 码网关）；DL/T 1100.1-2018、BD 520002-2019、BD 420012-2015 | **可回填**：chrono_theory_docs.json 补 `power_grid_time_sync`（IRIG-B/PTP/电力标准，RFC/标准编号经交叉核实） |
| 13 | agent.md | LLM 编码规范实践（译） | Fabien Sanglard 的 agent.md：代码风格 14 条（最少词/常量替魔法数字/early return/函数名≤30 字符/枚举替布尔参数/单向层次通信/即使一行 if 也用 {}）+ Git 提交 7 规则（主题≤50 字符祈使语气/正文 72 换行）+ Bug 修复先写测试；context dilution 对抗（Lost in the Middle arXiv:2307.03172；新 session/显式 reload） | 纯技术可学习（无 counterpart；「规则显式化+上下文稀释」纪律可学） |
| 14 | VBA 类模块作用域 | 编程语言教学 | 类模块作用域：模块级 Dim=Private；Private/Public/Friend 三成员可见性表；Instancing（Private/PublicNotCreatable/MultiUse/GlobalMultiUse/SingleUse）控制外部可见性；每实例独立变量副本；对象销毁释放；类模块不支持 Option Private Module | 纯技术可学习（作用域语义与 comp 语言域不构成 counterpart，仅笔记） |
| 15 | REA 复刻 VLC | 逆向工程 agent 工具实测 | REA（Reverse Engineer Anything）经 MCP 接 Claude Code/Codex + Ghidra/Hopper/IDA；无源码时分析功能并重写近似实现；10–15 分钟出可用 VLC 复刻（MP3 播放/快捷键正常）；问题：引擎换 Chromium、部分格式打不开、全屏黑屏；「功能复刻≠搬运源码，并非每个克隆都合法」 | **可回填**：reverse_docs.json 补 `rea_mcp_reverse`（MCP+逆向工具链；版权边界如实登记） |
| 16 | gpu-unlock | 内核 hack 实测解读 | Linux 内核模块，NVIDIA 驱动加载前改寄存器放开 RTX30/40 消费卡 FP16/BF16 Tensor Core 发射上限；3090Ti BF16 87.5→157.4 TFLOPS（合成基准口径）；Prefill +33%/首 token -24%（vLLM 口径），Decode 仅 +1%；INT8/FP8 无增益；需改 initramfs、启动顺序；实验性有稳定性风险 | 纯技术可学习（候选 needs_action：hardware_kernel.json 未见 GPU 解锁条目；风险口径如实登记） |
| 17 | Snow Shot 1.3.3 | 截图录屏工具发布 | 截图/标注/贴图/拼图/录屏/OCR 一体；Win+macOS；1.3.3 独立图片编辑器、录屏叠加摄像头、硬件 H.265 编码、ARM64 拼图提速；完整版/Mini 版双轨 | 纯技术可学习（无 counterpart） |
| 18 | DeepInfer | 推理框架实测（云轴科技） | DeepSeek 2026-10-20 开源推理框架（支撑 V4.1 Flash）；官方 64 卡 1.6 万并发需 GPUDirect RDMA；本文 4×B200 EP4 + PCIe 本机取数替代 RDMA（/dev/shm ~400GB，DEEPINFER_ENGRAM_LOCAL_FETCH=1）；1,024 并发总输出约 6.2 万 token/s（每用户约 61）；128k 上下文 nextn=3 投机解码；单卡吞吐较官方 EP8 少约 25% | 纯技术可学习（候选 needs_action：distcompute 无独立数据层，推理框架条目暂无落点） |
| 19 | 数学软件一览 | 工具盘点科普 | 按任务分层：符号计算（Mathematica/Maple/Maxima/SageMath/Wolfram Alpha）、数值（MATLAB/Octave/Scilab/NumPy/SciPy）、统计（R/SAS/SPSS/Stata/pandas）、动态几何（GeoGebra/Desmos/几何画板）、优化建模（Lingo/Lindo）、排版（LaTeX/MathType/Mathpix）；「工具链比单款软件更重要」 | **可回填候选**：toolchain_catalog.json 数学/科学计算类目——见落实动作 |
| 20 | 多星座导航信号模拟器+导航大模型验证 | 测试方法学论文 | 北斗/GPS/Galileo/GLONASS 多星座射频/中频信号可控生成（多径/电离层/欺骗/失锁退化）；真值与信号严格时间对齐；数据集场景八分类；四层框架（编排/生成/推理/评估）；指标四类（精度/连续性/完好性/鲁棒）；TEXBAT/Tuni2025 公开数据集局限；SYN5206 型模拟器口径；BD 420012-2015 计量标准 | 纯技术可学习（GNSS/导航域留给 S2 sciences 概念系统构建时纳入，见 #665） |
| 21 | Prometheus + nVisual Viewer | 运维监控组合方案 | Prometheus/AlertManager/Grafana + nVisual Viewer：告警 IP 匹配机房 2D/3D 拓扑设备、60s 拉取、机柜红色脉冲闪烁、一键跳 Grafana；零侵入不改既有三件套；主动拉取无需入站端口；定位耗时 8~23 分钟→「提升 90% 以上」（文章口径 `needs_verify`） | 纯技术可学习（native/metrics.py 为量化评分 counterpart，非监控告警；不硬塞） |
| 22 | ipset | 网络运维实战 | iptables 线性匹配 O(n) vs ipset 内核哈希 O(1)；`ipset create blacklist hash:net timeout 86400`；`iptables -I INPUT -m set --match-set blacklist src -j DROP` 一条规则管万级；`ipset restore` 批量导入秒级；timeout 自动解封替代轻量 fail2ban；ipset-persistent 存盘（重启不丢）；白名单优先；200 条以上该迁；nftables set 为新内核推荐 | **可回填**：network_docs.json 补 `ipset`（集合匹配；与 f2b_refs「分级响应」互补——本仓已有 fail2ban 只读咨询层） |
| 23 | GitHub 涨星榜 Top3 | 生态编目 | ① heygen-com/hyperframes（HTML/CSS+GSAP 时间轴写视频、无头浏览器逐帧出 MP4；craft 检查把「好不好看」变成数字阈值：单行<0.4s=line_unread、>3s 静止=dead_stretch、<28px 字拦、>15s 无声=film_silent）；② anthropics/sandbox-runtime（OS 级沙箱：macOS Seatbelt/Linux bubblewrap+只读 bind mount/Windows ACL+WFP；网络默认全禁+校验解析后 IP 防 DNS rebinding/SSRF；allow-only 写+deny-then-allow 读）；③ Nutlope/hallmark（反 AI 味设计 skill；Floor/Reflex/Finish 三档门禁；sloplint 真浏览器 lint） | 纯技术可学习（无 counterpart；sandbox-runtime 与 disposable-env.sh 隔离理念同构，可学） |
| 24 | DSH CAD 自动生成插件 | AI 工业软件流水线 | 27painter/dsh-sw-cad：把 AutoCAD MCP + SolidWorks 自动化技能接进 DSH/Codex；发现模式把 242 工具 schema 从 83,732 token 砍到 365 token（-99.4%）；shim 挡 66 工具服务器（23,404→256 token）；惰性加载 SKILL.md；不 vendor 上游代码；CAD 必须同用户同权限运行；版本验证矩阵诚实标注（AutoCAD 2026 实测/2027 预期） | 纯技术可学习（无 counterpart；「schema 惰性发现」与 Harness² skills 按需加载同构，可学） |
| 25 | MQTT 遗嘱消息+心跳 | 协议实战（七） | 四层防假在线：KeepAlive（1.5×超时判死）+ LWT 遗嘱（QoS≥1+Retain）+ 在线状态表（双向 Retain 对称）+ 应用层心跳（ping/pong/单调序号/Watchdog）；WillDelay<SessionExpiry；TCP KeepAlive 7200s vs NAT 5~10 分钟；MQTTnet 5.x 移除 ManagedMqttClient，重连/重订阅/发送队列业务层自管；MQTT 5.0 支持 WillDelay，3.1.1 静默忽略 | **可回填**：network_docs.json 补 `mqtt_lwt_keepalive`（遗嘱/心跳/掉线判死机制） |
| 26 | Cua 2.8MB 决策模型 | 小模型专精化 | CUA-S1-FORMS：70.6 万参数/2.8MB 专做表单信息匹配；System One 路线（只做选择判断不生成文字）；填表任务自测 99.7% vs Jev 83.6%（主场优势，文章自陈）；「任务足够固定时甚至不需要通用决策模型」 | 纯技术可学习（无 counterpart） |

## 二、边界分级与诚实边界

本仓按「是否有真实 counterpart」分档：

- **可回填档（本轮同步回填数据层，共 7 条）**：
  - **UltraVNC** → `remote_clients_docs.json` 补 `ultravnc`：remote 子系统（native/remote.py 只读探针）已有 openssh/telnet/filezilla/putty 四条远程客户端登记，VNC/RFB 协议族缺席，UltraVNC 补上「开源免费远程桌面」生态位（GPL、无带宽限制、加密插件口径均按文章呈现）。
  - **DsoFramer/AA** → `winternals_refs.json` 补 references 1 条（aardio + DsoFramer 复活实践）+ items 1 条（COM/OLE 文档嵌入控件）：winternals 域本登记 Windows 内部机理，COM/OLE 嵌入是 Windows 桌面程序与 Office 集成的经典机制，DsoFramer 为该生态标志性控件。
  - **B码/PTP** → `chrono_theory_docs.json` 补 `power_grid_time_sync`：chrono（时空全维度子系统）已有时间同步标准登记（#552 异位同步/高延时异位同步），电力授时（IRIG-B/IEEE 1588/C37.238/61850-9-3）是时间同步在电力行业的轮廓落地，标准编号经文章参考文献交叉核实（IEEE Std 1588-2008、IEEE C37.238-2017、IEC/IEEE 61850-9-3:2016、IRIG 200-04、DL/T 1100.1-2018、BD 520002-2019）；BD 420012-2015（北斗模拟器性能要求及测试方法）同时服务 #663 国内标准线。
  - **ipset** → `network_docs.json` 补 `ipset`：network_docs 已有 iproute2/ethtool/ebpf/tc/conntrack 等网络工具层，ipset 是 iptables 集合匹配搭档，且与本仓 f2b_refs（fail2ban 只读咨询）构成「轻量替代」互补；timeout 自动解封思想与本仓「限时记因」（绝地天通）纪律同构。
  - **MQTT** → `network_docs.json` 补 `mqtt_lwt_keepalive`：遗嘱消息+心跳的「防假在线」四层机制是物联网/组网场景的通用可靠性模式，netsys meshchat/distcompute 的心跳语义同域。
  - **REA** → `reverse_docs.json` 补 `rea_mcp_reverse`：reverse 子系统已有 UPX/MinGW/GDB 黑箱实战登记，REA（MCP+逆向工具+编码体重写）是「逆向→重实现」链条的新形态；版权边界（功能复刻≠搬运源码）如实登记。
  - **HatchZip** → protec durability 域候选：磁盘空间峰值规划（动工前 check、退出码编号、崩溃安全五步顺序、进度本版本号）与 protec「冗余/可维护/监控」保护原则同构；因 protec 域为概念系统（#591 纪律严），本轮仅在笔记登记 + 落实动作提 needs_action，不直接加概念（见第四节）。
- **纯技术可学习档（仅笔记，不加概念不建数据层）**：IOPaint、TabClustPFN、DigUp、LangGraph、Code Video Model、Harness²、ioDraw、agent.md、VBA、gpu-unlock、Snow Shot、DeepInfer、GNSS 大模型验证、Prometheus/nVisual、GitHub 涨星榜、DSH CAD、Cua、Ansible、数学软件。本仓对上述能力均无 counterpart，按 docs/71 先例一律只沉淀笔记。
- **第三方口径档（needs_verify 挂牌）**：IOPaint 23,300 星、DigUp 5,600 星、HatchZip 1,738 星与「四天」、Ansible 15~25 分钟、nVisual 定位提升 90%+、gpu-unlock 的 TFLOPS 数字、DeepInfer 的 6.2 万 token/s 与 61 token/s、Cua 99.7% vs Jev 83.6%、TabClustPFN 的 96.8% 覆盖——均为文章/社区单方陈述或作者自测，未独立复核。

诚实边界重申：本文技术要点均来自 2026-10-25 只读抓取的页面，以当时呈现为准；文章标题与用户所给链接短码存在错位时（历史上 batch-5 出现过），按**实际抓取内容**归类。所有「可回填」条目只登记协议/机制/工具事实与标准编号，不复制被分析项目的代码与文案。

## 三、分主题学习笔记

### 3.1 UltraVNC：开源远程桌面的工程定位

- **架构**：Server（被控端服务）+ Viewer（主控端）双件套，基于 VNC/RFB 协议；局域网输入内网 IP 即连，外网经转发服务器模式跨网段。
- **差异化四点**（文章口径）：① GPL 全功能免费无带宽限制；② 自研智能压缩按实时带宽适配画质帧率（弱网优先保操作流畅）；③ AES/SecureVNC/MSRC4 多重加密插件 + 每连接专属密码；④ 双向文件传输（断点续传+传输前压缩）、多显示器、内置文字聊天、Windows 安全模式远程。
- **运维口径**：连接失败先查防火墙放行；密码必须自定义高强度（默认密码是最大坑）；按网络环境调画质/帧率档位。
- **本仓落点**：remote_clients_docs 补 `ultravnc`（VNC/RFB、GPL、加密插件、Server/Viewer 分工）。

### 3.2 AA 复活 DsoFramer：COM/OLE 嵌入的 AI 重构实践

- **背景**：DsoFramer 是微软 DsoFramer 控件停更数十年后仍是「在自己桌面程序里嵌入原生 Office/WPS 控件」的少数方案——C++/COM 原生接口复杂，无人维护。
- **实践**：作者用 aardio（AA）+ AI 编码体重构：先可行性分析→GPT 6 Astra 主体改造（token 成本数千元）→Gemini 4 Argon 优化一整天→打开 Office 文档速度「快数十倍」、清光崩溃/显示异常/高分屏错乱、发行体积缩至 96KB。
- **可学纪律**：① **可行性分析先行**（AI 时代仍值得先问「值不值得做」）；② 多模型分工（一个主力实现+一个专门优化）；③ 发行体积是硬指标（96KB vs 增大十几倍的两个版本）。
- **本仓落点**：winternals_refs 补 COM/OLE 文档嵌入控件条目 + aardio 参考。

### 3.3 IOPaint：本地 AI 修图的隐私范式

- **定位**：Inpainting+Paint 组合的 Web UI 重绘工具；涂抹遮罩→模型本地补全；模型列表可换（社区生态）。
- **场景**：去路人/杂物、去水印/台标、局部替换（鸭子→猫）、画幅外扩、抠图、人脸修复、动漫超分。
- **隐私口径**：全部模型本地显卡/CPU 运算，不上传第三方服务器——这是对「云端修图偷传隐私」商业模式的直接反例。
- **边界**：本仓无 AI 图像 counterpart，仅笔记；「本地运算=隐私可控」与 f2b「配置建议以文本交还用户，绝不代行」的本地主义同构。

### 3.4 Ansible：声明式批量运维的工程结构

- **核心公式**：Inventory 管「对谁做」（分组+变量分层 host_vars>小组>大组>all）→ Role 管「做什么」（common 复用+专属按组装配）→ 执行参数管「怎么做才安全」（--limit 试点→--serial 滚动→--check --diff 预演→-f 控并发）。
- **幂等性**：yum state=present / template / service started enabled / lineinfile 带 regexp 均幂等；command/shell 非幂等，须 creates/when/changed_when 明确条件。第二次跑 changed 趋近 0 即幂等的直接证据。
- **避坑**：-f 太大打爆 sshd MaxStartups；主机密钥确认卡住（高安全环境应 ssh-keyscan 预收集而非关 StrictHostKeyChecking）；python 解释器路径歧义；ignore_errors+注册结果收集失败主机不阻断全批；密钥/密码走 ansible-vault 不写 Inventory。
- **可学纪律**：① 「可重复、可审计、失败可回滚」与本仓每阶段独立提交+全量回归门禁同构；② 声明式幂等 ↔ 本仓构建脚本 --check 模式；③ 高危操作滚动+熔断（max_fail_percentage）↔ 本仓「破坏性维护二次确认」。

### 3.5 TabClustPFN：把聚类变成一次前向

- **问题**：无标签表格聚类要「先选算法再调超参」，每换一张表重新「算到收敛」，还要外部试不同簇数。
- **方案**：PFN（先验数据拟合网络）预训练阶段学「群体可能长什么样」（GMM+ZEUS 两先验合成任务），新表单次前向出样本归属 + 2–10 类候选簇数概率分布；PIN（划分推断）+CIN（簇数推断）双模块；SoftARI 可微目标解决「组名互换即同划分」的置换对称。
- **结果口径**（文章/论文）：44 真实数据集（OpenML 22+UCI 22）ARI 排名中位第一（给真实簇数）/并列第二（自动估计）；簇数误差中位数 1；3,200 未训练高斯混合集上 95% 候选集覆盖真实簇数比例 96.8%（覆盖率≠单数准确率，论文自陈）。
- **可学纪律**：① **把不确定性输出给用户**（簇数概率分布）↔ 本仓 needs_verify 挂牌不臆造；② 「候选集覆盖率」与「单点准确率」的区分 ↔ 本仓诚实边界纪律。

### 3.6 DigUp：按内容搜本机的另一半

- **定位**：Everything 只认文件名；DigUp 按内容——EmbeddingGemma 2 把文字/图片/声音/视频放进同一向量空间，一句话同时排照片/PDF 页/录音片段，录音视频跳到说到那句话的时刻；原样字（发票号/错误码）也按字面匹配。
- **边界（文章如实）**：中文只在「意思」层，按原样匹配不拆中文词（「辅导」搜不到「学生情绪辅导记录.pdf」，作者确认待修）；界面仅英文；Windows beta；首次下载 865MB 模型；纯 CPU 索引一图约 5 秒（2017 i5 口径）。
- **隐私口径**：只读用户自选文件夹；密钥/密码文件/隐藏文件夹/程序缓存跳过；索引不离开本机；联网仅首次下载模型+每天一次可关的更新检查。
- **可学纪律**：① **排除清单显式化**（什么不读）↔ 本仓只读探针边界；② 隐私承诺逐条可核对（联网仅两件事）↔ 本仓 honesty 字段范式。

### 3.7 LangGraph Agent 架构：执行闭环的构成

- **流程**：用户任务输入→State 状态初始化→大模型理解任务→调用工具→处理结果→条件判断→最终输出；外围能力：记忆管理、知识库检索（RAG）、API 调用、代码执行、外部系统连接、安全控制、运行监控。
- **边界**：一张架构图科普，无实现细节；本仓无 counterpart，仅编目。

### 3.8 Code Video Model：代码作为视频的控制表示

- **问题**：视频扩散模型缺物理规律显式约束（球会悬浮）与精确控制（演员站位/物件大小/相机时序），镜头迭代靠反复改提示词。
- **方案**：Coding Agent 把 Prompt 转成 Three.js 程序（几何/运动/相机/事件时序统一为可执行场景表示），渲染出 proxy video 提供时空参考，参考图定外观，视频模型补细节；「编程—渲染—检查—修订」迭代，预演 <1 分钟，验证先于生成。
- **机制发现**（论文口径）：双通路互补——Qwen-VL 编码器通路主导外观、VAE 通路主导结构/运动；条件介入前约 25% 去噪阶段影响最大；阶段化调度（早期结构约束、后期撤预演由文本+参考图引导外观）免训练解决「low-poly 风格泄漏」。
- **可学纪律**：① **生成前可检查可编辑**（程序预演）↔ 本仓「构建期校验无悬空」；② 通路分工实验方法（交换条件归因）↔ 本仓消融/对照测试纪律。

### 3.9 Harness²：递归改 harness 的工程闭环（重点）

- **公式**：Agent = Model + Harness；模型权重冻结，能改的只有 harness（8 组件：system prompt/guardrails/memory/skills/tool guidance/scripts/subagents/plugin——每个都是运行时可挂载文件，每次修改即一个 diff）。
- **任务级递归**（无标准答案场景）：Propose（invariant 通用缺陷 + domain 领域知识两方向各提候选）→ Probe（同任务同配置重跑做**行为对照**——参考执行揭示 harness 行为而非交付物对错）→ Compose（按证据合成，每个决定对应一条观察）。
- **harnessing 级递归**：任务结束把「完整 harness + EXPERIENCE.md」写进经验库；**下一任务仍从初始 harness 出发**，组件经 Propose 有选择复用——成品带不走，改的过程留下可复用东西。
- **结果**（论文口径，`needs_verify` 独立复核）：12 组配置单步全部涨分；k=5 并行继续单调涨且帕累托前沿；较弱模型 GLM-5 改一步后在 WorkBuddy 上超过原样的 Gemini 3.5 Flash；消融：经验库/skills/scripts 贡献最大（去 skills -5.3、去 scripts -3.7、去 prompt 类仅 -1.5）；附录案例：禁「伪工具调用」60→100 分，plugin 代码强制「无产出即警告」72→100。
- **可学纪律**（与本仓直接同构）：① **改之前先留参考执行，改完同条件重跑对比** ↔ 本仓每轮改前改后全量 pytest 基线；② **分通用缺陷/领域知识两方向改** ↔ 本仓「标准分层」；③ **经验与改动一起存**（为什么改+改完发生了什么）↔ 本仓 HANDOFF 逐轮落账；④ 流程写成 skill、检查写成脚本 ↔ 本仓「脚本化的门禁」优于「文档里的要求」；⑤ 论文局限自陈（同族评委/算力不对等/选择会出错/样本量/未折算钱） ↔ 本仓 honesty 字段。

### 3.10 HatchZip：边解压边吃壳的磁盘纪律

- **核心**：老工具解压「壳和小鸡同时在窝里」（180G 包需 380G）；HatchZip 从尾部吃起——文件变短从尾巴截最省事（全平台认账），孵完一批截一截，180G 包 200G 出头办完。
- **关键设计**：① 动工前 check 找峰值空间时刻出计划表，不够拒绝开工退出码 3（盘上一个字节不碰）；② ZIP/7z 目录索引在文件尾，先抄家到 sidecar 再解析；③ 每批五步固定顺序（写文件→刷盘→记进度本→截档案），任何时刻拔电源不存在两头空；④ 进度本带版本号，旧代码读新号罢工（防止半成品被当垃圾删）；⑤ restore 中途反悔补索引变回普通压缩包；⑥ 130+ 测试三真机+崩溃杀进程+续跑逐字节比对+CI 盯 ext4/APFS/NTFS 真还空间。
- **局限（文章如实）**：下载本身损坏则「坏点前孵出、坏点后进下水道」，唯一副本必须 --verify-first；默认保留 2GB 小盘上误伤（--keep-free 调小）；盘越空越白搭（839M 包在 97.5G 空闲盘上峰值与 unzip 无异）；7z solid 整块拒收；.tar.gz 连续流在 FAT32/exFAT 退化双倍空间；0.1.x 新车期（10-24 当天两洞当天修）。
- **可学纪律**：① **先把丑话说前面（check+编号退出码）** ↔ 本仓构建期悬空校验先行；② 崩溃安全五步顺序+进度本版本号 ↔ 本仓快照 diff/断点续跑思想；③ 「README 每个数字后面跟测量环境，改数字必须附实测」 ↔ 本仓 live_user_face 实测纪律。

### 3.11 ioDraw v3.7.0：会话化 AI 助手的交互范式

- **AI 助手改造**：一次性生成→会聊天的搭档：历史会话列表（每文件独立）、连续追问基于上一版改（不推倒重来）、随时中断、一键重新生成、先预览再插入（不弄脏画布）、模型自选+自定义 API Key、每文件最多 20 会话自动带最近 6 轮上下文。
- **甘特图工作日历**：自定义每周工作日（双休/单休/大小周）、节假日调休单独标记、非工作日自动顺延、父子任务联动重算；AI 生成项目计划套用日历（不把任务排在休息日）。
- **可学纪律**：① **连续修改而非重新生成** ↔ 本仓增量提交而非重写；② 「确认后再插入」 ↔ 本仓报告先给用户审再落地；③ 上下文窗口管理（20 会话/6 轮） ↔ 本仓 context dilution 应对（见 3.13）。

### 3.12 B码 vs PTP：电力授时的互补逻辑

- **IRIG-B 的稳**：DC 码 RS-422 精度优于 1μs；独立信号链路不依赖以太网交换机；协议简单（秒帧含完整 UTC+质量标识）；北斗 B 码授时主流；强电磁环境容错。
- **IRIG-B 的固有短板**：单向传输无法自动补偿链路时延（人工固定补偿，线缆一改动就失准）；不能跨交换机组网（要加中继）；无标准冗余切换与链路状态上报。
- **PTP（IEEE 1588-2008）**：Sync/Follow_Up/Delay_Req/Delay_Resp 四步双向测算自动扣时延；硬件时间戳（PHY/交换机芯片层）百 ns~亚 μs；BMCA 自动选主；复用 IEC 61850 以太网不单独布线；电力轮廓 C37.238-2017/61850-9-3:2016；支持 PTP 的交换机（BC/TC）直接转发。
- **结论口径**：互补非替代——老旧改造（只有 B 码模块的 IED）、高压室强干扰、小型站保留 B 码；新数字化站、多间隔频繁改扩建、全网统一监控用 PTP；主流混合架构 = 主时钟 PTP 上以太网 + PTP 转 B 码网关喂传统 IED。
- **避坑**：PTP 必须硬件时间戳工业交换机（软件打戳抖动大）；B 码分有源/无源、DC/AC 不能混用；NTP 毫秒级不能替代 PTP。
- **本仓落点**：chrono_theory_docs 补 `power_grid_time_sync`（IRIG-B/IEEE 1588/电力轮廓/北斗授时/混合架构）。

### 3.13 agent.md：LLM 编码规范的显式化

- **背景**：作者 2025 年中 LLM 代码不能编译→2026-01 能用但质量绝望→agentic IDE 可迭代但「每个新 session 重复相同的话」。
- **方案**：项目根 `agent.md` 被 IDE 加载注入提示词——编码风格偏好一劳永逸。核心规则：代码风格 14 条（写给人看的用最少的词/不用夸张赞美/常量枚举替魔法数字/减少缩进 early return/函数名≤30 字符/枚举替布尔参数/逻辑块间空行/注释解释做什么为什么/可见性是重大设计保持 private/分层抽象/不碰无关代码/单向层次通信/一行 if 也用 {}）；Git 提交 7 规则（空行分隔主题正文/主题≤50 字符（72 硬上限）/首字母大写/不以句号结尾/祈使语气/正文 72 换行/正文释是什么为什么）；Bug 修复流程（先写测试→看失败→写修复→看通过）。
- **context dilution**：随上下文变长模型忽略中段指令（Lost in the Middle arXiv:2307.03172）；缓解=每功能新 session + 质量下降时显式「Reload agent.md」；规则被违反时直接让 agent 把规则加进 agent.md。
- **作者自陈**：「不是魔法子弹，还是要验证迭代」；LLM 经常幻觉不能被信任。
- **可学纪律**：① **规则显式化+可自动增长** ↔ 本仓 AGENTS.md/构建脚本门禁；② 上下文中段稀释 ↔ 本仓长会话靠文档落盘（HANDOFF/docs）对抗；③ 先测试后修复 ↔ 本仓 TDD 式门禁。

### 3.14 VBA 类模块作用域：可见性语义速查

- **语义表**：模块级 Dim=Private（仅类内）；Private 类内可见；Public 对外接口（受 Instancing 约束）；Friend 同工程可见外部不可见；过程内 Dim 过程级；每实例独立变量副本；对象销毁（Set obj=Nothing）模块级变量释放。
- **Instancing 五值**：Private（外部不可见不可建）/PublicNotCreatable（可引不可建）/MultiUse（可建多实例）/GlobalMultiUse（全局可用）/SingleUse（单实例）。
- **易错清单**：类模块写 Option Private Module（不支持，标准模块专用）；把模块级 Dim 当全局共享；外部不实例化直接调 Public Sub；Friend 当 Public；Public 变量直接暴露（应 Property）；混淆标准/类模块调用方式。
- **边界**：作用域语义教学，无 counterpart，仅笔记（Private/Friend/Instancing 的「最小可见性」思想与本仓模块封装纪律哲学同构）。

### 3.15 REA：逆向工程 agent 的工具链形态

- **形态**：REA（Reverse Engineer Anything）经 MCP 把 Claude Code/Codex 接 Ghidra/Hopper/IDA——没有源码时，代理分析二进制功能再重写功能相近代码。
- **实测口径**（Notebookcheck 作者，用免费带广告的 Freebuff）：装 REA+MCP+Ghidra 输入提示词，代理反问三个选择题，10–15 分钟交出 VLC 复刻——MP3 拖入即播、进度/静音快捷键正常、可打开文件夹（不含子目录）；问题具体：引擎换 Chromium 而非 libVLC、部分格式打不开、全屏黑屏。
- **法律边界（报道口径）**：功能复刻≠搬运源码，并非每个克隆都合法；「厂商写的代码作为竞争优势，价值正在变薄」。
- **本仓落点**：reverse_docs 补 `rea_mcp_reverse`（MCP+逆向工具链形态 + 版权边界登记）。

### 3.16 gpu-unlock：寄存器解锁的收益边界

- **机制**：Linux 内核模块在 NVIDIA 驱动加载前写保护寄存器，放开 RTX30（Ampere）/RTX40（Ada）消费卡被软限制的 FP16/BF16 Tensor Core 发射上限；不超频不改 VBIOS 不改驱动；INT8/FP8 路径无增益；40 系仅 4090/4070Ti Super/4060Ti 16G 有验证。
- **收益结构**（文章/社区口径 `needs_verify`）：合成基准 3090Ti BF16 87.5→157.4 TFLOPS；真实推理分两阶段——Prefill（批量矩阵密集）+33% 吞吐/首 token -24%（vLLM 口径），Decode（访存带宽瓶颈）仅 +1%；Strata（llama.cpp/GGUF INT 量化 MoE）大部分场景吃不到；Ada 切 FP8 后无效。
- **风险口径**：仅 Linux；要改 initramfs 调启动顺序；休眠唤醒/多卡/非公 PCB 可能翻车；最坏开机黑屏；厂商不保修。
- **可学纪律**：① **理论跑分≠真实收益**（合成 GEMM vs 带宽瓶颈） ↔ 本仓「实测为准，不臆造数字」；② 收益边界按场景讲清（Prefill/Decode/量化路径） ↔ 本仓诚实边界逐条划。

### 3.17 Snow Shot：截图录屏工具的功能矩阵

- **形态**：截图/标注/贴图/拼图/录屏/OCR 一体，Win+macOS，完整版+Mini 版双轨（Mini 首次识别自动下载 OCR 组件）。
- **1.3.3 更新**：独立图片编辑器（从历史/贴图打开二次编辑：标注/裁剪/撤销重做/智能擦除）；录屏叠加摄像头并预览；硬件 H.265 编码选项；ARM64 拼图提速；历史定位已存文件；字号按像素设置。
- **边界**：无 counterpart，仅笔记（ARM64 专项优化与「硬件编码降负载」思路可学）。

### 3.18 DeepInfer：推理框架的部署门槛实测

- **官方口径**：DeepSeek 2026-10-20 开源（支撑 V4.1 Flash 线上）；64 卡每卡 256 请求、全集群约 1.6 万并发、128k 上下文、nextn=3 投机解码（75% 接受率折算每用户约 103 token/s、全集群约 168 万 token/s）；Engram n-gram 嵌入表约 197GB 按 rank 分片放主机内存，GPU 经 RDMA（NCCL GIN/GDAKI）直接读——**没有 IB/RoCE 网卡的机器根本启动不了**。
- **云轴方案**：4×B200 EP4（权重 510GB，每卡余约 90GB 给 KV cache）；专家 EP4 切分+attention DP4；兼容接口替换 Engram 取数——表按 rank 拼同一块共享内存，GPU 走 PCIe 直读（/dev/shm 约 400GB，环境变量 DEEPINFER_ENGRAM_LOCAL_FETCH=1 开启，不开走上游原路径）。
- **实测口径**（`needs_verify` 独立复核）：128k 上下文 1,024 并发 4 卡总输出约 6.2 万 token/s（每用户约 61）；256 并发每用户约 110；单请求 32k 无投机每步 7.6ms；GPQA 310 万 token 4 卡平均约 2,900 token/s；prefill 打满（功耗中位 920–930W/1000W 上限）；并发不足时 GPU 有余力（单请求 decode 受访存限制）。
- **工程细节**：编译需 README 没写的 pciutils/libdw-dev；DeepEP 用 ibstat 探测网卡装 infiniband-diags；FlashMLA 寄存器溢出检查设 FLASH_MLA_SKIP_REG_SPILL_CHECK=1；虚拟机 PCI NUMA -1 段错误补丁跳过绑核；正确性逐字节一致三类检查；镜像 zstackai/deepinfer:774ce24-r1。
- **可学纪律**：① **「官方最低门槛」到「单机可跑」的降门槛改造**（环境变量开关、不开时完全走上游原路径） ↔ 本仓 opt-in 写引导默认关；② 部署坑逐条补（pciutils/ibstat/寄存器检查/NUMA） ↔ 本仓 docs 踩坑登记；③ 正确性验证先行（逐字节一致）。

### 3.19 数学软件：按任务分层的工具链观

- **分层**：符号计算（Mathematica/Maple/Maxima/SageMath/Wolfram Alpha）/数值（MATLAB/Octave/Scilab/NumPy/SciPy）/统计（R/SAS/SPSS/Stata/Minitab/pandas）/动态几何（GeoGebra/Desmos/几何画板）/优化建模（Lingo/Lindo）/排版（LaTeX/MathType/Mathpix/AxMath）/学习辅导（拍照搜题类）。
- **选型逻辑**：先看任务→再看阶段（学前小学兴趣数感/中学高中理解查漏/大学考研计算统计证明排版/科研建模可复现）→再看预算（零预算从 Python/Octave/Scilab/SageMath/Maxima/GeoGebra/Desmos/R/LaTeX 入手）。
- **核心论点**：「工具链比单款软件更重要」——组合拳（Desmos 看图+纸笔推导+Wolfram Alpha 核对；Mathematica 符号推导+Python 数值验证+LaTeX 排版）；「数学软件是钥匙，思考才是门」。
- **边界**：工具盘点无 counterpart；候选 needs_action：toolchain_catalog 是否设数学/科学计算类目（见落实动作）。

### 3.20 多星座导航信号模拟器：导航大模型的可复现验证

- **问题**：导航大模型（IQ 端到端定位/干扰检测/欺骗识别）缺数据——野外实测真值贵、参数不可控、场景难复现；外场欺骗试验有合规风险；公开数据集（TEXBAT/Tuni2025）大多只覆盖 GPS 单星座。
- **方案**：多星座模拟器（北斗/GPS/Galileo/GLONASS 多频点）按 ICD 生成星历/PRN/电文，注入电离层/对流层/多径/窄带干扰/欺骗/遮挡退化，同步输出 PVA 真值与误差注入参数——**真值与信号严格时间对齐**，无惯导/激光真值设备的时间同步误差。
- **框架四层**：场景编排（轨迹/星座/遮挡/误差配置，批量自动生成）→信号生成（射频送被测+IQ/真值/标签入库，同脚本可回放对照）→大模型推理（IQ/相关器/观测序列→定位结果+检测标签）→评估反馈（定位误差/失锁恢复/欺骗 F1/虚警漏警，反向补难例）。
- **指标体系**：定位精度（ENE 误差/速度误差/固定成功率）、连续性（恢复时间/可用时长/漂移速率）、完好性（告警延迟/虚警漏警/F1）、鲁棒性（信噪比/多径/欺骗功率梯度曲线）。
- **边界（论文自陈）**：误差模型是理论简化（建筑非镜面反射/天线畸变/射频非线性难完全复现）；预设欺骗范式覆盖不了自适应智能欺骗；仪器自身计量不确定度（伪距误差可控 0.05m 内、通道延迟数 ns，需定期溯源校准 BD 420012-2015）；稳妥做法=仿真做前期训练/筛选/压测+标定野外实测二次验证。
- **本仓落点**：GNSS/导航域留给 S2 sciences 概念系统（#665）构建时纳入；BD 420012-2015 同时服务 #663。

### 3.21 Prometheus + nVisual Viewer：告警的最后一公里

- **问题**：Prometheus 三件套有 IP 有指标有曲线，**没有位置**——运维翻 Excel 台账+Visio 图纸+打电话，8~23 分钟（可能就是一次 P0）。
- **方案**：加 nVisual Viewer：渲染机房 2D/3D 拓扑（机柜/U 位/线缆）；每 60s 拉 AlertManager 活跃告警；按 IP 匹配拓扑设备；告警设备红色脉冲闪烁+点击定位；一键跳 Grafana。
- **部署口径**：零侵入（不改 Prometheus/AlertManager 路由，唯一要求拓扑数据设备填 management_ip）；主动拉取无需入站端口（政企合规）；对比商业方案 50~100 万/年授权费（文章口径 `needs_verify`）。
- **边界**：native/metrics.py 是量化评分引擎 counterpart，非监控告警拓扑；不硬塞，仅笔记（「告警到物理定位」的最后一公里思路可学）。

### 3.22 ipset：一条规则管万级黑名单

- **原理**：iptables filter 表按规则顺序线性匹配 O(n)，1 万条 -s DROP 平均匹配几千次；ipset 是内核态哈希表，iptables 只挂一条 `-m set --match-set blacklist src -j DROP`，查找 O(1)。
- **操作链**：`ipset create blacklist hash:net timeout 86400`（hash:net 吃 C 段/B 段；timeout 默认元素超时）→ `-I`（插链头优先）挂规则 → `ipset restore < blacklist.txt` 批量导入（十万条几秒，别 for 循环）→ `ipset add 9.9.9.9 timeout 3600` 动态封禁自动解封 → `ipset save > /etc/ipset.conf` + ipset-persistent systemd 开机恢复（**默认只在内存，重启全放行**）。
- **补丁**：被扫服务挂 INPUT、转发网关挂 FORWARD；白名单优先（先 ACCEPT 白名单再 DROP 黑名单，防把自己关外面）；新内核推荐 nftables set（type ipv4_addr flags interval），存量 iptables 环境 ipset 最低风险。
- **自查线**：`iptables -L INPUT -n | wc -l`——<200 忍、200~2000 该迁、>2000 别敲了直接上。
- **本仓落点**：network_docs 补 `ipset`；与 f2b_refs（fail2ban 单一守护进程统观日志源集中响应）构成互补——ipset 是「轻量无 Python 依赖」的集合匹配后端，auth.log→脚本→`ipset add timeout 600` 即最小 fail2ban。

### 3.23 GitHub 涨星榜：agent 落地四道关卡

- **hyperframes（HeyGen，71.5k 总星）**：写 HTML/CSS+GSAP 时间轴描述分镜，无头浏览器逐帧截图出 MP4；内置 craft 检查把「好不好看」翻成 agent 可读数字：单行文字停留<0.4s=line_unread、>3s 静止=dead_stretch、1080p 下<28px 字拦、>15s 无声=film_silent；snapshot --review 自动分镜评审表。核心价值：解决「agent 看不见自己做的东西」。
- **sandbox-runtime（Anthropic，6.5k）**：不用容器的 OS 级沙箱——macOS sandbox-exec Seatbelt/Linux bubblewrap+只读 bind mount/Windows NTFS ACL+WFP 出口过滤；网络默认全禁只放行白名单域名且**校验解析后 IP**（防 DNS rebinding/SSRF：白名单域名解析到 127.0.0.1/内网/云 metadata）；写 allow-only、读 deny-then-allow；环境变量/密钥 mask；.mcp.json command 换 srt 一键沙箱化 MCP server。
- **hallmark（Together AI，32.1k）**：反 AI 味设计 skill——48 套主题随机三套按访客目的搭页；点名 AI 痕迹（eyebrow 小标签/全大写 label/标题挑词上色/满屏空框/hero 溢出/每页邮件订阅/假感谢表单）；三档门禁 Floor（永不发布：对比度/焦点/reduced motion/编造事实/手机布局崩）/Reflex（模型默认坑可说明推翻）/Finish（工艺不拦发布）；sloplint 真浏览器 lint 给可判定失败条件。
- **观察（文章口径）**：四个方向（视频/安全边界/设计审美/记忆）都在补同一件事——把 agent 从「能写代码」推向「能对结果负责」。
- **可学纪律**：① craft 阈值化 ↔ 本仓 quality 门禁数字化；② 校验解析后 IP ↔ 本仓「桥接目标必须真实存在（构建期悬空校验）」同构的出口校验；③ Floor/Reflex/Finish 分档 ↔ 本仓红线/needs_verify/可学三档边界分级。

### 3.24 DSH CAD 插件：AI 驱动工业软件的流水线

- **形态**：27painter/dsh-sw-cad 把 AutoCAD MCP（上游 U-C4N/Autocad-MCP，PyPI，MIT）+ SolidWorks 自动化技能（上游 wzyn20051216，clone，MIT）接进 DeepSeek Harness（DSH）/Codex；本身只做「配置与粘合」：隔离环境、启动参数、按需加载、客户端注册；**不 vendor 上游代码**。
- **核心 trick——发现模式**：242 个 AutoCAD 工具 schema 全暴露要 83,732 token，改发现模式（DISCOVERY_MODE=search 只露 search_tools+call_tool）后客户端只见 2 工具 365 token（-99.4%）；目录带 206 命令名+1,439 同义词（「chamfer」找到 FILLET）；SolidWorks 上游无条件注册 66 工具首请求前背 23,404 token，本仓补 shim 挡成 256 token（sw_lexicon.json 57 组中英别名：「拉伸凸台」→solidworks_sketch_and_extrude）。
- **边界（作者自陈）**：发现模式不是免费是延迟（每次调用多一个搜的来回；shim 目录上游更新后要重跑 --build-catalog 否则过期）；ALLOWED_PATHS 圈住工作目录；CAD 必须与编码体同 Windows 用户同完整性级别运行（否则「工具没反应」）；版本验证诚实（AutoCAD 2026 实测/2027 预期，老版本先跑小任务）；原生 .dwg/.sldprt 无 headless 替代。
- **可学纪律**：① **schema 惰性发现** ↔ Harness²「skills 按需加载不占 context」（3.9）同构；② 不 vendor 上游+安装时拉最新 ↔ 本仓只读引用不复制；③ 权限等级对齐 ↔ 本仓「维护通道唯一提升、限时记因」。

### 3.25 MQTT 遗嘱消息+心跳：四层防假在线

- **问题**：TCP 连接还在但设备已死（假在线）——指令发出去没人收，数据「发成功」其实进黑洞。
- **四层机制**：① KeepAlive 心跳（1.5×超时判死；KeepAlive≤离线 SLA÷1.5 反推）；② LWT 遗嘱消息（连接建立时预注册，异常断开时代理自动发布——QoS≥1+Retain 保证到达；MQTT 5.0 有 WillDelay 可延迟发布，3.1.1 静默忽略此字段；WillDelay 必须<SessionExpiry）；③ 在线状态表（双向 Retain 对称设计：上线/下线都走 Retain 主题，任何时刻订阅者拿到即最新状态）；④ 应用层心跳（ping/pong+单调序号+Watchdog，序号断档即异常）。
- **细节口径**：TCP KeepAlive 默认 7200s vs NAT 超时 5~10 分钟（NAT 表早过期，连接半开）；MQTTnet 5.x 移除 ManagedMqttClient，重连/重订阅/发送队列需业务层完全自管。
- **本仓落点**：network_docs 补 `mqtt_lwt_keepalive`；「假在线」检测与 netsys meshchat 节点发现注册表（#186）+ distcompute 看门狗重启（#213）同域。

### 3.26 Cua 2.8MB：小模型专精化的信号

- **形态**：CUA-S1-FORMS 70.6 万参数/2.8MB 专做表单信息匹配（PDF 提字段→模型判该进哪个字段→Cua Driver 执行）；System One 路线（只做选择判断不生成文字）。
- **对照**：Jev 面向更通用决策任务；Cua 缩窄到表单域——「任务足够固定时，甚至不需要一个通用决策模型」。自测填表 99.7% vs Jev 83.6%，文章自陈主场优势不能外推。
- **边界**：无 counterpart，仅笔记（「按任务固定程度选模型规模」的思路与 Cua/DeepInfer 的量化/投机解码同属「推理成本工程」主题）。

## 四、落实动作

1. **数据层回填（本轮完成，7 条）**：
   - `remote_clients_docs.json` + `ultravnc`（VNC/RFB、GPL、加密插件、Server/Viewer 分工、弱网自适应口径）。
   - `winternals_refs.json` + references `aardio-dsoframer-revival`（COM/OLE 嵌入控件 AI 重构实践）+ items `com-ole-embedded-office-control`（COM/OLE 文档嵌入控件机制登记）。
   - `chrono_theory_docs.json` + `power_grid_time_sync`（IRIG-B DC/AC、IEEE 1588-2008 四步双向、C37.238-2017/61850-9-3:2016 电力轮廓、BMCA、北斗 B 码、PTP 转 B 码混合架构；DL/T 1100.1-2018/BD 520002-2019 登记）。
   - `network_docs.json` + `ipset`（hash:net/timeout/restore 批量/持久化/nftables 演进）+ `mqtt_lwt_keepalive`（LWT/WillDelay/KeepAlive 1.5×/双向 Retain/单调序号）。
   - `reverse_docs.json` + `rea_mcp_reverse`（MCP+逆向工具+编码体重写；版权边界：功能复刻≠搬运源码）。
2. **needs_action 候选（不硬塞，登记待用户决策）**：
   - protec durability 域：HatchZip 的「动工前峰值空间 check+编号退出码+崩溃安全五步+进度本版本号」具备保护原则同构性，但是否加概念待议（#591 纪律）。
   - toolchain_catalog.json：Ansible（配置编排）与数学软件（科学计算）两类是否设类目待议。
   - hardware_kernel.json：gpu-unlock 实验性 hack 是否登记待议（风险口径需完整）。
   - distcompute 无独立数据层：DeepInfer 推理框架条目暂无落点。
   - GNSS/导航域：随 S2 sciences 概念系统（#665）构建时纳入。
3. **文档落账**：本文档 + README 学习块 + HANDOFF 段落 + 版本号升 D 段。
4. **验证门禁**：数据层 JSON 可解析 + 相关 native 层测试（remote/winternals/chrono/network/reverse 探针加载不受影响）+ 全量 pytest 0 failed + audit_concepts --strict 0 不一致 + 提交推送 origin/main。
