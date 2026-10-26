# Sysweeper 系统能力卡（System Card）

> 范式来源：Claude Haiku 5.5 System Card（Anthropic, 2026-10）的「结构化记录系统能力/局限/安全护栏/预期用途/评估」方法。
> 本卡把 **Sysweeper（Windows 内部工具箱 / 跨平台系统优化器）** 自身作为被描述对象，做成一页可审计的能力边界说明。
> 版本：0000.0000.0000.0004.20261024

## 1. 系统概述（Executive summary）

Sysweeper 是一个**跨平台系统只读诊断与优化建议生成器**。它扫描本机（Windows / macOS / Linux / BSD / Android / iOS / OpenWrt / 单板机）的系统状态，生成可执行的优化/修复命令文本与手动指引，**默认不替你执行任何写操作**。设计目标是「让专家级的系统体检人人可做，且不会被工具自己搞坏系统」。

## 2. 能力（Capabilities）

| 能力域 | 能做什么（只读） | 代表模块 |
|---|---|---|
| 网络 | OSI 七层结构诊断、连接/DNS、WSL、虚拟化/GPU、浏览器引擎 | `network` / `osi` / `wsl` / `virtgpu` / `browser` / `dnshealth` |
| 兼容层 | Proton/Wine 前提核验、32 位库、Vulkan、NT 同步原语 | `proton` |
| 硬件 | PCI/USB 枚举、总线绑定、单板机温度/降频/欠压 | `hardware` / `edge` |
| 发行版 | 身份识别、发行注记/变更日志读取 | `distro` |
| 节点/算力 | IPMsg 组网、能力通告、分布式任务派活 | `meshchat` / `distcompute` |
| 资讯 | 新闻/网站聚合优化知识（http(s) 只读） | `webnews` |
| 任务 | 390+ 任务库，按平台/风险/分类 opt-in 编排 | `tasks/*` + `registry` |

## 3. 局限（Limitations）

- **不执行写操作**：优化/修复是「命令文本 + 手动指引」，执行权永远在人。改系统文件、装包、重启服务均为 opt-in。
- **只读探测边界**：依赖当前运行环境的 sysfs/proc/CLI；容器里部分信息不可见（如真实内核模块、宿主 GPU）。
- **兼容知识非实时**：浏览器兼容等为静态子集，精确支持度以 `@mdn/browser-compat-data` 为准。
- **不引入 LLM 运行时**：不联网调用大模型做自动决策，避免不可审计的外部执行路径。
- **语言译文待补**：6 种新语言（ko_KR/es_ES/pt_BR/it_IT/vi_VN/id_ID）仅脚手架，未译串回退中文。

## 4. 安全护栏（Safeguards / 红线）

| 红线 | 约束 |
|---|---|
| 不写系统 | 不 eval、不 subprocess 写、不自动改配置；所有改动 opt-in |
| 只读网采 | webnews 只抓 http(s)，有超时与体积上限，失败如实报不编造 |
| 无执行路径 | 抓来的文本无 eval/无 subprocess；优化建议带「来源归属」 |
| 隔离运行 | 兼容层/AI 类能力遵循「最小权限、可审计、可接管」原则（参照 litebox） |
| 可审计 | 每次诊断可定位、可复现；任务库标注平台/风险/来源 |

## 5. 预期用途（Intended use）

- 系统体检、容量/配置盘点、升级前风险自查、兼容层前提核验、跨平台维护。
- 作为运维/安全人员的**只读副驾**：出结论、出命令，人拍板执行。

## 6. 评估（Evaluation / 自测）

- 全量测试：**605+ passed / 3 skipped**（v0.6.15 起含 4 个新模块共 24 新用例）。
- 版本一致性门：`__version__` / `pyproject` / `src/go/main.go` 三处同步校验。
- 任务引用校验：`test_task_actions_reference_existing_native_funcs` 强制每个 Action 指向存在的原生函数。

## 7. 结论

Sysweeper 的能力边界是**「诊断 + 建议生成」，而非「自动修复」**。这与 System Card 范式一致：
明确能力、坦承局限、把危险操作锁在护栏内、让关键决策留在人手里。
