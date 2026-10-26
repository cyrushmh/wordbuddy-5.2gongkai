# 70 导入分析学习应用：Hermes 多项目只读分析（M-Lab×Google / Cornell Tech / Nous Research / Lean 数学验证 / 流式视频 KV 缓存）

> **来源**：用户指令「导入分析学习应用 github/google-research2 、github/google-research，其实忘记仓库了，主要是Hermes或类似的英文；继续」。
> **落点**：五个资源均**只作只读分析**（2026-10-25 GitHub 仓库页 / 论文页只读 WebFetch + 官方博客与方法学页面），不克隆、不安装、不构建、不下载、不复制其代码进本仓。
> **纪律红线**：只登记可核实事实；无法核实的标 `needs_verify`，不臆造；本仓无网络性能观测 / RAG 检索 / Agent 运行时 / Lean 形式化验证 / 视频理解 counterpart，按 #591 先例（docs/59）**一律只沉淀为学习笔记，不新增概念**。

## 一、资源概览与可复用点（2026-10-25 只读抓取核实）

| 资源 | 性质 | 许可证 | 规模 / 技术要点 | 可复用工程纪律（仅学习，不落地代码） |
|---|---|---|---|---|
| `m-lab/hermes` | Internet 性能观测系统（研究系统 + 运行管道） | 论文 CC BY 4.0（代码许可以仓库页为准 `needs_verify`） | ACM SIGCOMM 2026 论文（DOI 10.1145/3789240.3829129）；把用户主动发起的 M-Lab NDT 测速（延迟/吞吐/丢包 + 前向 traceroute + 推断反向路径）聚合成「用户组」（源 AS × 都会区 × M-Lab 站点）做统计退化检测，再以**时间层析 + 相关层析**双法定位网络实体；事件三级分类 localized / ambiguous / unresolved；2024-08 起运行；公开 BigQuery 数据集 `mlab-collaboration.hermes_union.events_enriched` + 仪表盘 hermes-dashboard.org；Docker 一体化管道（默认处理最近 2 天，适合每日 cron） | ① **每一步输入输出都落公开数据**（SQL 产出每个字段）——可复现、可审计、可不同意；② **关联非因果**的诚实分级（localized/ambiguous/unresolved 三值而非二值断言）；③ **分组最小密度阈值**（≥25 次基线测试、≥5 个不同客户端 IP、单 IP 支配防控、地理一致性校验）防个体 artifact 误判为网络事件；④ **双向路径分别分析**（前后向不对称，半数的肇事链路只在一个方向可见）；⑤ **「列名即契约」**（稳定接口列名承诺不变）↔ 本仓只读层 API 同构 + `--check` 防漂移 |
| `S4AI-CornellTech/Hermes` | RAG 算法-系统协同设计评估框架 | **MIT** | ISCA 2025（pp.958–973）；层次化搜索簇跨机分布 + **两阶段检索**（sample-nprobe 浅采 ~8 / deep-nprobe 深搜 ~128）+ **DVFS** 调延迟-能耗平衡；栈：Python 3.11 + conda、faiss-gpu 1.8.0、PyTorch CUDA 11、vLLM、pyRAPL/pynvml/pymongo；数据 SPHERE_899M/100M/100K（BERT 编码 Common Crawl 子集）+ TriviaQA；模型 GEMMA-2 9B / BGE-Large / BERT-Base；Docker 需 `--gpus all --privileged -v /sys:/sys`；末次提交 2025-05-02（README 2025-06-25） | ① **能耗即一等公民**：Intel RAPL（`uarch-configure/rapl-read`）+ `perf stat -e power/energy-pkg/ -e power/energy-ram/` 实测，不靠估算；② **测量-建模-仿真分离**（measurements/ 实测、modeling/ trace_generator·latency_sim·dvfs_sim、figures/ 出图）；③ **Artifact Evaluation 流程**固化（build.sh → isca_figures.sh）——论文数字可复现；④ 子模块 + torchvision 版本修正脚本等**环境细节显式化** |
| `nousresearch/hermes-agent` | 开源 AI Agent（旗舰） | **MIT**（多数仓库） | 组织仓库列表：`hermes-agent` 主仓 **257k stars**（Python），自述「The agent that grows with you」；生态含 official/labs/example 三层插件集、六个记忆提供器独立插件（supermemory/openviking/honcho/mem0/byterover/retaindb）、`hermes-agent-self-evolution`（DSPy + GEPA 进化式自我改进）、`hermes-toolperf-evals`（工具集 A/B 评估）、`hermes-compression-eval`（ContextCompressor 离线探针评估，方法论改编自 Factory 2025-12《Evaluating Compression》）；大量插件仓归档并入 official/labs | ① **插件生态分层**（官方维护 / 实验不受支持 / 示例参考）且**维护状态明示**（⚠ 无人维护、寻找负责人标注）；② **评估闭环**：工具效率 A/B（toolperf）+ 上下文压缩离线评估（compression-eval）；③ **生态整合趋势**：碎片插件仓归档收敛到单一 official/labs 仓——治理随规模演进；④ 第三方报道（凤凰网，`needs_verify`：称其居 OpenRouter token 消耗榜首、日耗 271B token、一个月前 14 万星翻倍至 25.7 万——与组织页 257k 量级互证但精确值未核） |
| `aziksh-ospanov/HERMES` | 数学推理单步形式化验证器 | **MIT** | arXiv 2511.18760（2025-11-24；仓库页称 ICML 2026，两处口径并登 `needs_verify`）；作者 Azim Ospanov、Zijin Feng、Jiacheng Sun、Haoli Bai、Xin Shen、Farzan Farnia（华为基础模型部 / 港中文 / Celia Team）；对 LLM agent（LangGraph）暴露唯一工具 `verify_one_mathematical_step`：英文证明步骤自动形式化为 **Lean 4** 并尝试证明，返回 **CORRECT / INCORRECT（Lean 证否）/ VERIFICATION FAILURE（无法证也不能驳）** 三值；记忆模块（HuggingFaceEmbeddings + InMemoryStore，Qwen3-Embedding-0.6B，默认关）；prover 改编自 Goedel-Prover-V2；栈 Python 3.10+ / LangChain / Lean 4 + Mathlib4 + REPL / OpenAI 兼容 API（默认 DeepSeek）/ Linux only | ① **单步验证器工具化**：把形式化验证包装成 agent 可调用的一个工具，幻觉在传播前拦截；② **三值标签**（CORRECT/INCORRECT/FAILURE）↔ 本仓 needs_verify / 未知 降级口径；③ **诚实标注边界**：reward-model 对比行依赖仓外 pipeline，README 明言不在本仓；④ Lean4ServerScheduler 的**并发/超时/内存限额显式配置**（4 并发、120s 超时、内存 10）↔ 本仓探针限额纪律 |
| `haowei-freesky/HERMES` | 流式视频理解 KV 缓存管理 | 仓库页可见 LICENSE（条款未抓取 `needs_verify`） | ACL 2026 Main；arXiv 2601.14724；作者 Haowei Zhang、Shudong Yang、Jinlan Fu、See-Kiong Ng、Xipeng Qiu；把 KV Cache 当**层次化记忆系统**管理（细粒度保留/淘汰 + 可解释），替代「外挂 CPU/磁盘/DB 检索」与「裸复用缓存」两条老路；2026-03-23 全量代码发布，末次提交 2026-05-08；栈 Python 3.12 + flash-attn；模型 LLaVA-OneVision（0.5b/7b/72b）+ Qwen2.5-VL（3B/7B/32B）；基准 StreamingBench / OVO-Bench / RVS-Ego / RVS-Movie（流式）+ VideoMME / MVBench / EgoSchema（离线）；代码基于 ReKV | ① **缓存预算硬上限参数化**（`kv_size 6000`）↔ 上下文预算思想（与 §3.3 compression-eval、docs/69 workbuddy-slim 互证）；② **层次记忆 vs 外部检索**的路线对比纪律（先列全路线再论证取舍）；③ 基于 ReKV 的**致谢与代码归属明示**；④ 流式约束（未来帧未知、问题未知、时长不定）驱动设计的**约束先行**方法论 |

## 二、边界分级与诚实边界

本仓库按「是否可实做落地」分档，本仓守界如右：

- **纯技术可学习类（仅笔记，不新增概念）**：五个 Hermes 项目全部属此档。本仓（windows-internals-toolkit/system-optimizer）**无网络性能观测 counterpart**（netsys/dnshealth 为网络诊断概念编目，无测速观测台、无 NDT 数据管道实装）；**无 RAG 检索 / 向量索引 counterpart**（无 embedding/faiss/推理服务栈）；**无 Agent 运行时 counterpart**（本仓非助手本体，不管理外部 Skill / MCP 挂载——docs/69 已登记）；**无 Lean / 形式化验证 counterpart**（无定理证明器接线）；**无视频理解 counterpart**（无多模态推理栈）。按 docs/59（#591）纪律**只沉淀为学习笔记**，不新增 comp / netsys / 任何概念系统概念。
- **基础设施类（只作架构学习，不落地代码）**：M-Lab HERMES 的 Docker 管道 + BigQuery 公开数据集 + 仪表盘形态——属外部云数据设施，本仓**不接入、不查询、不镜像**；仅学习其「公开数据 + 可复现管道」的观测台纪律。
- **第三方口径类（needs_verify 挂牌，不背书）**：Nous Hermes 的 star 数（组织页 257k vs 报道 14 万→翻倍）、OpenRouter 消耗榜首与日耗 271B token、aziksh-ospanov/HERMES 的发表 venue（arXiv 2025-11-24 vs 仓库页 ICML 2026）、m-lab/hermes 的 star 数与代码许可条款、haowei-freesky/HERMES 的许可条款与「HF 每日论文第 3」（2025-01-23，页面自述）——均为页面/报道单方陈述，未独立复核。

诚实边界重申：本文所有技术要点均来自 2026-10-25 的只读抓取，以页面当时呈现为准。五个项目分属不同团队与领域，仅因同名「Hermes/HERMES」被用户一并点名——**同名不同物**，本文按项目分别登记，不混为一谈；各项目的论文宣称指标（94.5% 片段一致率、11× 事件数、AIME'25 +67% 准确率/省 80% FLOPs 等）均为论文/页面单方陈述，未独立复现（`needs_verify`）。

## 三、分主题学习笔记

### 3.1 m-lab/hermes —— 公开测速数据上的统计退化检测 + 双向路径层析定位

- **问题定位**：Internet 的失效不止「掉线」——网络可达但延迟升高、吞吐下降 enough 到视频卡顿、交互应用不可用，现有公共观测台（看可达性/路由的 Cloudflare Radar、IODA）不登记这类退化；私有系统（微软 BlameIt）只看自家服务且数据封闭。HERMES 用 M-Lab 多年公开的 NDT 测速记录填补这个空白。
- **方法四件套**：
  1. **用户分组**：按源 AS × 都会区 × M-Lab 站点 × IP 版本分组——把「用户网络、位置、测试目的地」固定住，组内变化才可能是网络事件而非某家 Wi-Fi；准入门槛（基线窗口 ≥25 次测试、≥5 个不同客户端 IP、单 IP 支配防控、地理一致性校验）。
  2. **性能信号**：延迟——统计显著上升 + 最小效应量双门槛（防「显著但无意义」）；吞吐——全分布比较（Wasserstein 距离 + Mann–Whitney U）+ 要求有意义降幅；丢包——谨慎解读（对本地无线敏感），与其他信号并列而非孤立定性。
  3. **双向路径上下文**：前向 traceroute（服务器→客户端）+ 可得时的反向推断路径，逐跳标注 AS/IXP/城市；两个方向**分别分析**——论文称半数肇事链路只在一个方向可见。
  4. **层析定位**：时间层析（事件期 vs 基线期路径参与变化——抓改道/链路消失）+ 相关层析（受影响组 vs 未受影响组的实体共现——抓拥塞类无路由变化事件）；跨方向、跨粒度（AS/都会区/IXP/AS-都会区链路）合并候选，按证据强度分级 localized / ambiguous / unresolved。
- **诚实口径**：HERMES **报关联不报因果**——「最可能相关的实体集合 + 证据支持到哪一级」，不定责；评估也按此口径：无 ground truth 目录，改用独立来源互证（云厂商监控重实现检测到 91.4% 的 HERMES 事件、片段一致率 94.5%；27 起有记录事件检出 25 起、23 起定位与报告一致；公开讨论事件约为对比观测台的 10 倍）。
- **工程形态**：Docker 一体化管道（`docker build -t hermes-pipeline:latest`，凭据经 `GOOGLE_APPLICATION_CREDENTIALS` + env file 注入 IPINFO_TOKEN/HOIHO_TOKEN，缓存卷持久化，默认跑最近 2 天——为每日 cron 设计，支持 `--start-date/--end-date` 处理区间）；每个字段由仓库内 SQL 产出；数据集 `events_enriched`（稳定接口，六类记录：client/server/performance/server_to_client_path/client_to_server_path/quality，列名承诺不变）+ 底层 `events_with_as_and_geoloc` + `events_explained_daily`（事件解释）。
- **可复用纪律（映射到本仓，仅纪律层面）**：
  - ① **每一步输入输出落公开数据** ↔ 本仓 catalog/docs 只读编目 + `--check` 全链可重放——结论必须可复算，不接受「summary score」式黑箱；
  - ② **三值分级（localized/ambiguous/unresolved）** ↔ 本仓 verified / needs_verify / needs_action 三档旗标——证据不足就挂中间档，不二值硬断；
  - ③ **分组最小密度阈值** ↔ 本仓探针多次采样/审计阈值防偶发误判（如 freshness 两栏口径）；
  - ④ **列名即契约** ↔ 本仓只读报告 schema 版本化（`toolchain_catalog/v1`）+ 测试守护 schema 不被改漂移；
  - ⑤ **定向补测**（现有路径无法区分候选时补发少量 traceroute，评估称平均降低 47% 歧义、31% 案例收敛到单一链路）↔ 本仓「缺证据时定向补探测」而非硬猜。

### 3.2 S4AI-CornellTech/Hermes —— RAG 的算法-系统协同设计：层次搜索簇 + DVFS

- **问题定位**：大规模 RAG 推理的检索延迟与能耗在商品硬件上难以扩展——单体巨型索引检索效率低，能耗随规模失控。
- **方法三支柱**：① **层次化搜索簇**跨多机分布；② **两阶段检索**（sample-nprobe 浅采样定位候选簇 → deep-nprobe 深搜，如 8 → 128）权衡延迟与召回；③ **DVFS** 在延迟-能耗间找运行点（`measurements/dvfs/set_frequency.sh` 设频率、`profile_dvfs_latency.sh` 剖析）。
- **能耗实测栈**：Intel RAPL（`sudo chmod -R a+r /sys/class/powercap/intel-rapl/` 后 `uarch-configure/rapl-read/rapl-read -s`）+ `perf stat -e power/energy-pkg/ -e power/energy-ram/`——包能量与内存能量分项测，配合 pynvml 取 GPU 侧。
- **目录组织纪律**：`index/`（单体/分裂/簇/扁平四种索引构建脚本，合成数据 `synthetic_create_monolithic_index.py` 支持 1M×768 维×32 线程）、`measurements/`（latency/power/dvfs/accuracy 分目录）、`modeling/`（trace_generator 生成簇访问轨迹、latency_sim 多节点聚合、dvfs_sim 仿真）、`figures/`（fig_06…fig_21 逐图脚本）——**实测、建模、出图三段分离，每段可独立重放**。
- **可复用纪律（仅纪律层面）**：
  - ① **能耗实测不估算** ↔ 本仓 toolchain 探针「宿主实采」纪律（版本/能力以实测为准，needs_action 不臆造）；
  - ② **两阶段检索的浅采-深搜** ↔ 本仓「先粗筛后精查」的分层检查（如 audit --strict 全量 + 定向复跑）；
  - ③ **Artifact Evaluation 固化**（Docker 镜像 + build/profile/eval/figures 四脚本）↔ 本仓「门禁可重放」纪律（pytest + 四构建 --check + 双 HTML --check 全链绿才算数）；
  - ④ **环境细节显式化**（torchvision 版本修正脚本、RAPL 权限、submodule 恢复提交记录）↔ 本仓宿主环境事实逐条入册（toolchain_catalog 的 setup_steps 字段）。

### 3.3 nousresearch/hermes-agent —— Agent 生态：插件分层、记忆提供器与评估闭环

- **生态版图（组织仓库列表，2026-10-25 抓取）**：主仓 `hermes-agent`（Python，**257k stars**，自述「The agent that grows with you」）；`hermes-agent-self-evolution`（DSPy + GEPA 进化式自我改进，优化技能/提示词/代码，5.6k）；插件三层——`hermes-official-plugins`（官方维护：Home Assistant/Spotify/Claude Subscription DirectSDK 等，461）、`hermes-labs-plugins`（实验不受支持，110）、`hermes-example-plugins`（示例参考，44）；六个记忆提供器独立插件（supermemory/openviking/honcho/mem0/byterover/retaindb）；评估工具 `hermes-toolperf-evals`（核心工具集 A/B 评估 + 基准用例，支撑 15-PR 工具效率追踪）、`hermes-compression-eval`（ContextCompressor 离线探针评估，方法论改编自 Factory 2025-12《Evaluating Compression》）。
- **治理演进**：大量独立插件仓（spotify/homeassistant/blender/snyk/telegram-business…）**归档并入 official/labs 单仓**——生态从碎片化走向收敛；无人维护仓明确 ⚠ 标注「寻找负责人（2026-10-15 离开 Hermes 核心）」。
- **评估闭环**：工具效率有 A/B 框架（toolperf），上下文压缩有离线探针评估（compression-eval）——**任何「变聪明」的宣称都有对应测量框架**，与 §3.4 的形式化验证、docs/69 的 workbuddy-slim 体检报告构成同一思想家族：能力宣称必须挂可复现测量。
- **可复用纪律（仅纪律层面）**：
  - ① **插件分层 + 维护状态明示** ↔ 本仓 repo_tools/catalog 逐条状态（verified / needs_action）与「只读编目不安装」边界；
  - ② **评估框架先于宣称** ↔ 本仓「先有 --check 门禁再谈改造」的纪律（如 #605 a11y 契约先立测试后改生成器）；
  - ③ **压缩可评估**（compression-eval）↔ docs/69 §3.1 记忆蒸馏压缩思想互证——压缩质量必须可测量，不能只凭感觉；
  - ④ **生态收敛演进**（碎片仓归档合并）↔ 本仓 docs 按轮次追加、概念拓扑稳定的「只增不改」治理。

### 3.4 aziksh-ospanov/HERMES —— Lean 4 单步形式化验证器：幻觉在传播前拦截

- **核心设计**：不做端到端证明合成，而是做**单步验证器**——对 agent 暴露唯一工具 `verify_one_mathematical_step`，把英文数学证明步骤自动形式化为 Lean 4 并尝试证明，返回三值之一：**CORRECT**（Lean 证成）、**INCORRECT**（Lean 证否——agent 产生幻觉）、**VERIFICATION FAILURE**（证不了也驳不倒，结论不确定）。目标：在幻觉算术/代数传播到后续推理链之前拦截。
- **记忆模块（可选，默认关）**：每个验证通过的步骤总结为一条 claim 存入 embedding 向量存储，后续调用语义相关 top-k claims 前置到问题陈述——跨长推理链保持证明连续性（论文称记忆模块维持 multi-step 链的 continuity）。
- **栈与配置**：Python 3.10+ / LangChain / LangGraph / Lean 4 + Mathlib4 + REPL（`prover/` 改编自 Goedel-Prover-V2，经 `Lean4ServerScheduler` 桥接：并发 4、超时 120s、内存限额 10）/ OpenAI 兼容 API（默认 DeepSeek `deepseek-chat`/`deepseek_v4_flash`）或本地 vLLM / 嵌入 `Qwen/Qwen3-Embedding-0.6B`；入口 `hermes.py`（`HermesReasoner` 标准 `BaseTool`，可插入任何 LangGraph agent）与 `demo.py`（默认题「Prove that 2+2=4」）；仅官方支持 Linux。
- **结果口径（仓库页表格，论文宣称需复现 `needs_verify`）**：MATH500 / AIME'25 / CollegeMath / HARDMath2 × Qwen3-8B / o3-mini / DeepSeek-V3.2；HERMES@5+Skywork 组合全面最佳（如 DeepSeek-V3.2：98.2 / 80.0 / 84.0 / 36.5）；论文另称 AIME'25 最高 +67% 准确率提升且比 reward-based 方法省 80% 推理 FLOPs；reward-model 对比行依赖仓外 pipeline，README 明言不在本仓。
- **可复用纪律（仅纪律层面）**：
  - ① **验证器即工具**（一个函数名说清契约）↔ 本仓只读层 API 同构纪律（同名同签名跨语言）；
  - ② **三值返回（含「不确定」）** ↔ 本仓探针「探测失败降级为 needs_verify/未知，不抛异常炸主流程」；
  - ③ **拦截前置**（幻觉在传播前 vs 事后 reward 筛选）↔ 本仓「把运行期的错提前到构建期」（--check 门禁哲学）；
  - ④ **限额显式**（并发/超时/内存）↔ 本仓工具调用限额与 opt-in 边界。

### 3.5 haowei-freesky/HERMES —— KV Cache 即层次化记忆：流式视频理解的缓存预算

- **问题定位**：流式视频理解（未来帧未知、用户问题未知、视频时长持续增长）下，历史上下文两条老路都有病——**外挂记忆**（转 CPU/磁盘/DB，提问时检索重建：延迟高、链路长）与**裸复用缓存**（无精细保留淘汰：被增长流挤爆或压缩丢关键信息）。缺的是「更小的缓存」之外的**缓存管理机制**——接近人类记忆组织方式的层次化记忆。
- **方法**：把 KV Cache 视作层次化记忆系统——分层的注意力偏好 + 细粒度保留/淘汰 + 可解释的管理；缓存预算硬参数化（`kv_size 6000`），采样率 `sample_fps 0.5`，并行评估进程 `num_chunks 8`（按 GPU 数）。
- **栈与基准**：Python 3.12 + flash-attn（`--no-build-isolation`）；LLaVA-OneVision 0.5b/7b/72b + Qwen2.5-VL 3B/7B/32B；流式基准 StreamingBench / OVO-Bench / RVS-Ego / RVS-Movie，离线基准 VideoMME / MVBench / EgoSchema；评估分选择题（`eval_multiple_choice.py`，VideoMME 按时长分段、EgoSchema 出提交 CSV）与开放题（`eval_open_ended.py`，GPT 评分）；代码基于 **ReKV**（致谢明示）。
- **可复用纪律（仅纪律层面）**：
  - ① **缓存预算硬上限参数化** ↔ docs/69 §3.1 上下文预算体检 + §3.3 compression-eval——三个独立项目互证「预算是硬约束、压缩可评估」；
  - ② **路线对比先行**（外挂 vs 裸复用 vs 层次管理，先列全再论证）↔ 本仓「边界分级三档」文档纪律（docs/59 起先例）；
  - ③ **约束先行方法论**（流式三不定驱动架构）↔ 本仓「先立红线再讲能力」；
  - ④ **代码归属致谢**（built upon ReKV）↔ 本仓 counterpart 引用与「不复制代码」纪律。

## 四、拓扑与验证

- **未新增概念**：本仓无网络观测 / RAG / Agent 运行时 / Lean 形式化 / 视频理解 counterpart（全仓 grep 核实：netsys/dnshealth 仅有网络诊断概念编目，无 NDT/测速/层析实装；无 embedding/faiss/vLLM/Lean/KV-cache 多模态栈），守 docs/59（#591）纪律，九概念系统（comp / plang / daoxue / apilab / netsys / quantum / baigong / zhuangzi / datong）拓扑与桥接不变（`build --check` 不受影响）。
- 本文档为纯文档落点；版本号按 monorepo 里程表纪律升一版（`0000.0000.0000.0016.20261025` → `0000.0000.0000.0017.20261025`，仅升 D 段、日期后缀不变），README 加 #607 块、HANDOFF 落账 §29。
- 全量 pytest 零回归；双 HTML 仅因版本串重生、`--check` 同步，数据语义不变。

## 五、落点清单与下一步

- 已落账：本文档（docs/70）+ README 学习块（#607）+ 版本 0017 落点 + HANDOFF §29（第二十一轮）。
- 守界：不新增概念、不进 `repo_tools` 可装清单、不接入 M-Lab BigQuery、不安装任何 Agent/Skill、不复制任何项目代码；各项目 star 数、venue、许可条款与论文指标均按 `needs_verify` 登记。
- 下一步（opt-in，不主动执行）：若本仓后续真做「网络性能观测」类只读功能（如对本仓主机出网延迟/丢包做分组基线 + 三值分级报告），再按「真实 counterpart 存在 + `--check` 通过」纪律把 §3.1 方法四件套升级为工程契约；五个项目的共同思想——**公开可复现的测量 + 三值诚实分级 + 限额显式**——已在本仓 catalog 新鲜度两栏、needs_verify 旗标、探针限额中同构存在，无需另立工具。

> ③ 版本号已按纪律升一版（`0000.0000.0000.0016.20261025` → `0000.0000.0000.0017.20261025`，五处源文件 + 三 taxonomy + 双 HTML 同步），本学习笔记仅增加 docs/70 文档与落账，不改 HTML / 数据语义、零回归（见 README #607 / HANDOFF §29）。
