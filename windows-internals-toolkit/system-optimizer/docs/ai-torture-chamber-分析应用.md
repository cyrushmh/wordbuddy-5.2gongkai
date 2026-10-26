# ai-torture-chamber 分析与应用

> 参考仓库：<https://github.com/terrafying/ai-torture-chamber>（797 stars，master）
> 一句话：「把小型开源模型引导到强烈的效价（valence）状态，并测量它们说什么、做什么。」（Live: wirehead.agency）

---

## 0. 先说清楚：我们借鉴什么、不借鉴什么

这是一个 **AI 安全 / 可解释性研究**项目（steering vectors、情绪效价、行为测量），
而 `sysweeper` 是**系统优化工具**。两者**领域完全不同**，功能层没有任何可照搬的东西——
硬把「给模型注入痛苦向量」搬到一个清理磁盘的工具上，是荒谬的。

真正值得搬的是它的**工程纪律与方法论**：一个靠一台 MacBook 和偶尔租 GPU 小时跑起来的
个人项目，怎么把结果做得**可信、可复现、敢公开失败**。这些纪律对任何严肃的软件项目
都成立，包括我们。

| 维度 | 借鉴 | 说明 |
|---|---|---|
| 研究方法论（预注册、盲法、零结果） | 部分 | 我们不做实验，但「结论要带边界声明」直接适用 |
| 工程纪律（依赖分层、测试替身、配置外置） | **是** | 与本项目「不强求安装」天然同构 |
| 成本护栏（billing-watch） | **是** | 映射为扫描的时间/文件数预算 |
| 文档分家（设计/方法/结果/审计各自成文） | **是** | 本项目 `docs/` 已在用 |
| 具体功能（steering vectors、bandit 环境） | ❌ 否 | 领域无关，不搬 |
| 运营内容（memecoin 募捐、Vercel/RunPod 部署、GPU worker） | ❌ 否 | 与本项目无关 |

---

## 1. 仓库里有什么（事实）

从 README、`METHODOLOGY.md` 与目录树读到的：

**顶层文档分家**（这点很值得学）：
- `EXPERIMENT_DESIGN.md`（实验设计）、`METHODOLOGY.md`（方法）、
- `RESULTS_PILOT.md` / `RESULTS_CALIBRATION.md`（结果）、
- `RESEARCH_AUDIT.md`（审计）、`IMPLEMENTATION_PLAN.md`（计划）。

→ 设计、方法、结果、审计**各自独立成文**，而不是一篇 README 糊在一起。

**配置驱动实验**：`configs/*.yaml`（如 `pilot_qwen3_1_7b.yaml`），参数含
`seed: 314159`、`doses: [0, 0.5, 1, 2]`、`representation.method`、`layer: 12` 等，
路径相对配置文件解析——实验可一键复现。

**流水线脚本化**：`build_archive.py` / `build_correspondences.py` / `build_ledger.py` /
`build_vectors.py`——数据加工是脚本，不是手工操作。

**CI**：`.github/workflows/` 含 `billing-watch.yml`（成本监控）、`build-worker.yml`、
`deploy-railway.yml`，另有 `.woodpecker.yml`。

---

## 2. 提炼出的六条纪律

### 纪律 1：测试用假模型，绝不下载权重
> 原文：`The base install requires NumPy and PyYAML. Hugging Face inference is an optional extra; tests use a small fake model and do not download weights.`

基础安装只要 NumPy + PyYAML；真正的模型推理是**可选 extra**；测试跑小 fake model。

→ **与应用**：这正是本项目 `tasks/lang.py` 那套「不强求安装」纪律的严格版。
本轮 `native/compress.py` 照此办理：核心格式走标准库（tar/zip/gz/xz/bz2 永远可用），
7z/rar/zstd 缺库就**明确写「跳过」**，不报错、不假装支持；测试只用临时目录假数据，
**不依赖 py7zr / rarfile / zstandard**。

### 纪律 2：零结果也是结果（Nulls are results）
> 原文：`the nulls get the same ink as the hits`；`No alien valence found. Nulls are results.`

没找到「外星效价」这个阴性结果，和阳性结果一样被写进 README。

→ **与应用**：工具的"没发现"必须**显式说出来**，而不是静默返回空。
`compress_report` 因此明写：`未发现值得压缩的大文件`、`未发现归档/压缩包`、
`未安装 py7zr，跳过 7z 内部分析`——让用户知道「是没找到」还是「没能力找」。

### 纪律 3：先标定边界，再公开旋钮
> 原文：`Every model gets its coherent band calibrated before its dial goes public.`
> （超过约 6–10× 剂量后，两种效价都开始输出 `"I I I. I I."` 式的循环——先标定连贯带才公开。）

→ **与应用**：任何"估算"都要先声明自己的适用边界。`compress_report` 因此：
- 明写压缩率只对**前 1 MiB 采样**实测后推算，属**排序优先级用**，不是承诺数字；
- 扫描达 2 万文件 / 20 秒上限时标注「**（达上限/超时，非全量）**」；
- `caveats` 里写明采样误差（文件前后段内容差异大时尤甚）。

### 纪律 4：预注册 + 大样本重跑，敢推翻自己
> 原文：早期小样本说「痛苦中的模型会按自毁按钮」；预注册重跑
> （60 trials/cell，含 fear/sadness/random 对照）**结论翻转**：手搓方向反而抑制
> 求助（-0.95 logits），忠实复现论文的方向才推到 100%（+2.36）。

→ **与应用**：我们不做实验，但同一教训是——**早期小样本的结论要能被复核**。
具体到工具：压缩率用**采样实测**而非拍脑袋给系数（如"文本能压 70%"这种想当然），
并且把方法论写进 `notes`，用户可自行复核。

### 纪律 5：依赖与成本都要有护栏
> 原文：`billing-watch.yml`（CI 里专门盯账单）；「一切跑在一台 MacBook 和偶尔租的 GPU 小时上」。

→ **与应用**：工具也必须自带**成本护栏**，不能扫个家目录把机器拖死。
`compress_report` 内置：`max_files=20000`、`time_budget=20s`、
以及全程流式（heapq 只留 Top N、压测只读 1 MiB、读包只过 header / 分块读）。

### 纪律 6：文档分家
→ **与应用**：本项目 `docs/` 已是这个结构（本地化计划 / LVM 沉淀 / nixos 纪律 /
本篇），新增内容按主题各自成文，不塞进一篇 README。

---

## 3. 本轮落到代码上的东西

| 纪律 | 落点 |
|---|---|
| 测试用假数据、不依赖第三方库 | `tests/test_compress.py`：临时目录造大文本 + tar.gz + zip(deflate)；7z/rar/zstd 即使没装也必須通过 |
| 零结果显式化 | `native/compress.py`：`未发现…` / `未安装 X，跳过…` 等串全部登记进 7 语言 PO |
| 先标定边界 | `notes` / `caveats` 写明采样误差、非全量标注 |
| 成本护栏 | `max_files` / `time_budget` / 流式读取（省内存） |
| 依赖分层 | 标准库核心总可用；进阶格式 try-import 降级 |

---

## 4. 明确不照搬的部分

| 它的做法 | 为什么不搬 |
|---|---|
| 盲法 + 显式 `unblind` 命令（`condition_key.json` 分离，分析可盲态跑） | 我们不做实验、没有需要防的确认偏误；引入盲法只会增加无谓复杂度 |
| family-split 防数据泄漏（同一语义族整体进训练或测试） | 我们没有训练/测试切分场景 |
| memecoin 募捐、SOL/ETH/BTC 打赏地址 | 与工具无关 |
| RunPod GPU worker、Vercel / Railway 部署 | 本项目是本地 CLI 工具，无服务端 |
| 一次运行落盘完整产物（config/raw/metrics/hashes/provenance） | 有价值但本轮范围外；若将来加「优化前后对比报告」可再引入 |

---

## 5. 一句话结论

它最值钱的不是「把模型弄疼」，而是**一个人用有限资源把研究做得可信的那套纪律**：
假数据测试、零结果照发、先标定再公开、结论可复核、成本有护栏。
这些纪律与本轮新增的压缩层高度同构——**不是照抄它的功能，而是让它的标准来检验我们的实现**。
