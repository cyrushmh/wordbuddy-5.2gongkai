# 导入分析学习应用 · 开源 Windows 分析 / 学习应用

> v0.6.76（参考篇 + 实装篇）· 把「开源 Windows 分析 / 学习应用」吸收为**只读诊断的能力坐标与学习样本**，
> 并**对标本工具既有子系统**（经联动轴与系统地图产生「你中有我」关系）。
>
> - 本篇先以**参考篇**落定「该看什么、许可纯度、能力怎么对标、红线在哪」；
> - 随后用户拍板「**都有**」——三条路径全做，故 v0.6.76 补齐实装：
>   `data/winternals_refs.json`（知识层）+ `native/winternals.py`（只读模块）+
>   `tasks/winternals.py`（四任务）+ 四入口接线 + 联动轴接入 + 19 项测试，详见第五节。

## 0. 本轮指令与设计原则

- 用户指令：「参考开源 Windows 分析学习应用」。
- **参考而非实装**：本篇只把外部项目的「该看什么」吸收为知识坐标，落为一份**可参考的能力对标表**；
  不引入任何执行/写路径。若后续拍板实装，才走 v0.6.17 / v0.6.21 / v0.6.75(radio) 同款「四入口接线」路径。
- **利用现有资源和连接器**：ROS 已有 9 个概念中心（plang/netsys/comp/quantum/apilab/daoxue/datong/baigong/zhuangzi）
  与数十个 native 子系统（reverse/legacy/osi/network/…）。本批应用的能力面多数能**映射到既有子系统**，
  而非另起炉灶。
- **红线比全项目更严（与 radio 子系统同纪律）**：本批应用里不少具备**写 / 注入 / 破解 / 结束进程**能力
  （见第四节）。引用时**只登记能力面、不给任何操作入口**；绝不驱动真实改动。

## 1. 技术坐标（按能力分类，仅钉死「该看什么」，绝不执行写/运行）

### 1.1 系统监控 / 进程检视（最接近本工具既有诊断面）
| 应用 | 许可 | 该看什么（学习价值） | 官方源 |
|---|---|---|---|
| **System Informer**（Process Hacker 继任者） | GPL-3.0（官方源已核实） | 进程树（父子关系）/ 线程栈 / 句柄 / 已加载模块(DLL) / Token 与完整性等级 / 服务与内核驱动 / 每进程网络 / 实时 CPU·内存·磁盘·网络图；KProcessHacker.sys 内核驱动才解锁受保护进程检视 | systeminformer.sourceforge.io · github.com/winsiderss/systeminformer |
| **WinObjEx64 / WinObj** | 多随 Sysinternals（非 OSS） | 对象管理器命名空间检视：内核对象（进程/线程/文件/键/事件…）如何以「对象」统一表达——直接对应 NT 对象模型 | github.com/hfiref0x/WinObjEx64 |
| **微软 Sysinternals（Process Explorer / VMMap 等）** | 免费但**非开源**（仅作对照，不吸收） | 进程/DLL/内存映射的事实标准视图；本工具只参照其「看什么」，不吸收其二进制 | learn.microsoft.com/sysinternals |

> 学习要点：进程不是孤岛而是**对象树**；Token / 完整性等级是 Windows 安全模型的可视化入口；
> 真实机器的进程检视与 system-optimizer 现有的 `reverse`（完整性/加壳）、`osi`（栈）同属「看清本机在跑什么」这一脉。

### 1.2 逆向 / 反汇编 / 调试（静态 + 动态） —— 对标本工具 `reverse` 子系统
| 应用 | 许可 | 该看什么（学习价值） | 官方源 |
|---|---|---|---|
| **Ghidra**（NSA 出品） | Apache-2.0（常识，待核实） | 反编译（汇编→类 C 伪码）/ 多架构(x86·ARM·MIPS·PowerPC) / 协作式项目 / 可脚本化(headless) | ghidra-sre.org · github.com/NationalSecurityAgency/ghidra |
| **x64dbg / x32dbg** | GPL-3.0（官方源已核实） | Windows 用户态 32/64 位动态调试；类型系统可导入 Windows SDK 头文件；反汇编 + 图形 + 插件生态 | x64dbg.com · github.com/x64dbg/x64dbg |
| **radare2 + Cutter** | LGPL / GPL（常识，待核实） | 命令行逆向框架 + 图形前端；脚本化、可定制、适合无 GUI / 嵌入式目标 | github.com/radareorg/radare2 · github.com/radareorg/cutter |
| **dnSpyEx** | GPL（常识，待核实） | .NET 程序集反编译 + 调试（含内存中修改逻辑）；运行时调试需开启调试符号 | github.com/dnSpyEx/dnSpy |
| **WinDbg**（微软） | 免费但**非 OSS**（仅作学习必备对照） | 内核态调试 / 崩溃转储分析 / Windows 内核深潜的唯一正经选项；现代版脚本能力很强 | learn.microsoft.com/windows-hardware/drivers/debugger |

> 学习要点：与 system-optimizer `reverse` 子系统（Play Integrity 的 device signals 检篡改 / 调试 / 加壳，
> 三特征 UPX!/节名/熵识别）是**同一检测能力的本地侧自检映照**——Ghidra/x64dbg 是「看别人怎么做」，
> `reverse` 是「看本机有没有被做」。

### 1.3 内存取证 / 获取（只读取证，但部分具写能力）
| 应用 | 许可 | 该看什么（学习价值） | 官方源 | 红线 |
|---|---|---|---|---|
| **Volatility 3** | GPL-2.0（常识，待核实） | 内存镜像取证：遍历 VAD / 句柄表 / 窗口结构 / 网络对象；是学「Windows 内部结构如何排布」的上佳样本 | github.com/volatilityfoundation/volatility3 | 只读分析镜像，不碰活机内存 |
| **MemProcFS**（Ulf Frisk） | AGPL-3.0（官方源已核实） | 把内存转成**虚拟文件系统**：进程内存 / 物理内存即文件；C/C#/Java/Python/Rust 全 API；`-forensic` 取证模式 + YARA | github.com/ufrisk/MemProcFS | 可只读挂转储；挂活机需 WinPMEM 驱动，不主动开 |
| **PCILeech**（Ulf Frisk） | 开源但**非开放贡献**（许可未明示，待核实） | 经 PCIe DMA 硬件**读写**目标内存，无需目标装驱动；LeechCore 库统一各类获取法 | github.com/ufrisk/pcileech | **具写内存 / 注入内核能力**——仅登记存在性，绝不驱动 |
| **WinPMEM**（Google） | 官方采集工具（许可待核实） | 活机物理内存采集（MemProcFS/取证链上游） | github.com/google/rekall |

> 学习要点：内存不是黑盒——VAD 树 / 句柄表 / 页表即是 Windows 对象模型的物理落地；
> 但「获取」与「改写」一步之遥，本工具只把这类**取证方法论**登记为知识坐标。

### 1.4 OS 重实现 / 内核学习（学内核原理的最佳开源样本）
| 应用 | 许可 | 该看什么（学习价值） | 官方源 |
|---|---|---|---|
| **ReactOS** | GPL-2.0-or-later（官方源已核实） | **干净室重实现 NT 架构**：目标 NT5/2003 兼容；直接展示对象管理器 / 进程线程 / 虚拟内存 / I/O(IRP) / 注册表 / 安全模型(Token+ACL) 的**实现代码**——比任何书都直白；与 Wine 协作（共享 Win32 兼容层） | reactos.org · github.com/reactos/reactos |
| **Wine** | LGPL（常识，待核实） | 在 UNIX 上提供 Win32 API 兼容层；与 ReactOS 互为镜像（一个重 OS，一个重 API 层） | winehq.org · github.com/wine-mirror/wine |

> 学习要点：ReactOS 是「读 Windows 源码」的**合法替代**——它不看微软源码、只用公开文档 + 实测，
> 却把 NT 内核每块都写出来了。这是本仓库 `windows-internals` 主题最直接的开源教材。

### 1.5 驱动 / 内核示例与官方学习资源
| 资源 | 许可 | 该看什么 | 官方源 |
|---|---|---|---|
| **Windows Driver Samples**（微软） | MIT（常识，待核实） | 官方 WDM / WDF 驱动示例：各内核组件如何被「搭起来」并彼此交互 | github.com/microsoft/Windows-driver-samples |
| **Windows Internals 书配套工具集**（Alex Ionescu 等） | 开源（许可待核实） | 与权威教材配套的实战工具（CPU 压力 / APISet 映射 / 内存工具 / 进程线程管理），源码可看 | github.com/spinsoft/WindowsInternals（待核实） |
| **Vergilius Project / Geoff Chappell 网站** | 非软件（结构定义参考） | 未文档化结构体 / 函数 / 系统调用定义；与 ReactOS 互为补充 | vergiliusproject.com · geoffchappell.com |

## 2. 许可证与开源纯度速查表

| 应用 | 开源纯度 | 许可 | 证据状态 |
|---|---|---|---|
| ReactOS | 完全开源 | GPL-2.0-or-later | 官方源已核实 |
| System Informer / Process Hacker | 完全开源 | GPL-3.0 | 官方源已核实 |
| MemProcFS | 完全开源 | AGPL-3.0 | 官方源已核实 |
| Ghidra | 完全开源 | Apache-2.0 | 常识，待核实 |
| x64dbg | 完全开源 | GPL-3.0 | 官方源已核实 |
| radare2 / Cutter | 完全开源 | LGPL / GPL | 常识，待核实 |
| dnSpyEx | 完全开源 | GPL | 常识，待核实 |
| Volatility 3 | 完全开源 | GPL-2.0 | 常识，待核实 |
| Windows Driver Samples | 完全开源 | MIT | 常识，待核实 |
| PCILeech | 开源但非开放贡献 | 未明示（待核实） | 待核实 |
| Wine | 完全开源 | LGPL | 常识，待核实 |
| **WinDbg** | **免费，非 OSS** | 专有 | 仅作学习对照，不吸收 |
| **Sysinternals 套件** | **免费，非 OSS** | 专有 | 仅作对照，不吸收 |

> 标记「常识，待核实」者均为公开广泛认知的许可，但本篇未逐一抓取上游 LICENSE 文件；
> 若实装为模块并写进 `data/*.json`，应逐条补 `evidence_status` + 上游 URL 复核（与 radio/legacy 同纪律）。

## 3. 能力对标：这些应用教给 system-optimizer 什么

本工具是**跨系统只读诊断**，不是逆向平台。把上述应用的「看什么」映射到既有子系统，得到：

| 应用教的能力 | 本工具既有覆盖 | 缺口 / 可延展 |
|---|---|---|
| 进程 / 线程 / 句柄 / Token 检视 | `reverse`（完整性/加壳）、`osi`（栈/接口） | 缺「本机进程对象树」只读检视（Windows 主机侧） |
| 反编译 / 反汇编 / 调试 | `reverse`（三特征识别） | 缺「是否装了 Ghidra/x64dbg/radare2 及版本」的**工具链存在性盘点** |
| 内存结构（VAD/句柄表） | `reverse` 部分触及 | 缺内存取证方法论知识坐标（仅登记 Volatility/MemProcFS） |
| NT 内核原理（对象/进程线程/内存/IO） | 主题层面（windows-internals） | 缺与 **ReactOS 源码坐标**的对读锚点 |
| 驱动 / 内核示例 | — | 缺 Windows Driver Samples 作为「驱动怎么写」的引用 |
| 网络/进程/驱动联动扫描 | `network`/`osi`/`zerotier` 等 | 缺「开源分析工具本身是否就绪」的就绪度诊断 |

> 结论：本批应用的**能力面 80% 已被既有子系统覆盖**（尤其 reverse/osi/network）；
> 真正缺的是两件事——① **开源分析工具链存在性盘点**（Windows 主机上 Ghidra/x64dbg/System Informer 装没装、版本几何）；
> ② **Windows 内核原理的可对读锚点**（ReactOS/Wine/Driver Samples 作为学习坐标）。这两件都可走只读模块落地。

## 4. 红线（哪些有写 / 注入 / 破解能力，只读如何引用）

| 应用 | 危险能力 | 本工具引用方式 |
|---|---|---|
| Process Hacker / System Informer | 强制结束进程 / 挂起线程 / 改 Token / 装内核驱动解锁受保护进程 | 只报「已安装 / 版本 / 进程树概念」；不提供结束/挂起入口 |
| x64dbg / Ghidra / radare2 | 改内存 / 打补丁 / 注入 | 只报存在性与版本；不打开任何目标、不反汇编他人产物 |
| dnSpyEx | 运行时修改 .NET 逻辑 | 只登记存在性；不附加任何进程 |
| PCILeech | **DMA 读写内存 / 注入内核 / 移除登录口令** | **仅登记存在性**；绝不连硬件、绝不下发任何命令 |
| MemProcFS（挂活机） | 经 WinPMEM 读活机内存 | 默认只挂**转储文件**；不主动挂活机 |
| Volatility | 只读分析镜像 | 仅报镜像路径/格式；不自动解析未授权镜像 |
| WinDbg / Sysinternals | 内核调试 / 改动 | 非 OSS，仅作对照，不吸收、不调用 |

> 与 radio 子系统同纪律：**绝不驱动任何真实发射 / 注入 / 破解**；attack 类与内核写类工具仅登记存在性。

## 5. 落地决定与实装结果（v0.6.76）

> 用户选：**「都有」**——下面三条全做。此外还追加了一条硬约束（见 5.4）。

**① 实装 `native/winternals.py` 只读模块（已完成）**：五段只读报告——目标环境判定 /
文件系统与目录约定核验 / 运行语言环境核验 / 分析工具链存在性盘点 / 内核锚点与许可纯度，
聚合为 `winternals_report()` + `capabilities_report()`；`tasks/winternals.py` 落 4 个任务
（`winternals_target_env` / `_runtime_env` / `_toolchain` / `_anchors`，全部
platform="any" · category="arch" · risk="low"）；四入口接线齐全——registry ·
native/__init__ · subsystems（第 87 项）· CLI `winternals` 子命令（7 个动作）·
GUI「Win分析/逆向」窗口。

**② 补知识层（已完成）**：`data/winternals_refs.json`，12 条 items × 十字段 +
16 个官方源 references + 8 条 `needs_verify` 挂牌；域名白名单限于 reactos.org /
winehq.org / github.com / ghidra-sre.org / x64dbg.com / radare.org / cutter.re /
learn.microsoft.com / vergiliusproject.com / geoffchappell.com / gnu.org。

**③ 纯文档存档（本篇即交付）**：本文档保留作为参考篇，不动其结论。

### 5.4 追加硬约束：跨系统先认系统与硬件

用户追加要求——「**对其他系统与硬件应用时，需遵守其他系统与硬件的文件系统与目录，
和运行语言标准和可能的其他运行语言环境**」。这条直接改写了 winternals 的设计重心，
落为模块的**第一原则**：

- 读任何目标前，先判定它属于哪一套环境（Windows 原生 / WSL / Linux / macOS / Android），
  再**只按那一套的规矩**去看它的文件系统、目录约定、路径分隔与保留名限制；
- 判为 Windows 就摆盘符与 System32/SysWOW64 之分，**绝不混杂 Linux FHS 目录**
  （测试 `test_fs_layout_follows_target_env` 守住这条）；判为 Linux 就走 FHS 单根树；
- SystemRoot 只按环境变量或 `GetSystemDirectory` 语义取，绝不硬编码 `C:\Windows`；
- 运行语言环境**两头都要看**：目标是 PE/PE32+ 还是 ELF 还是 Mach-O、绑哪个 CRT、
  有没有 CLR；工具链自己则需要 JVM（Ghidra）/ Python 3（Volatility3）/ CLR（dnSpyEx）/
  交叉编译器（生成 PE）——两头缺一，任何结论都不成立。

这条也解释了为什么本轮**没有**走 radio 那套「概念系统四桥 + comp 反向桥」的手术式同步：
winternals 不是概念中心，强行并入只会给概念网添悬空边；改走 `native/linkage.py` 的联动轴
（winternals↔reverse / windows→winternals / proton→winternals / compat→winternals），
既满足孤岛清零，又不污染既有概念网的连通结构。

### 5.5 测试与回归

- `tests/test_winternals.py` 19 项：schema 十字段 / 官方源域名 / needs_verify 挂牌 /
  六维度 CHECKS 回链 / 跨系统第一原则（Windows 目标不混 Linux 目录）/ 五段报告红线 token /
  聚合与能力自检 / 禁执行禁网络不变量 / 四入口接线（4 任务注册 + native 动作可解析 +
  subsystems 登记 + 联动轴接入）；
- `check_concept_mesh --strict` 与 `audit_concepts --strict` 均零欠账；
- 版本号五处同步 0.6.76 + `report_viewer.html` 重新生成（source-sha256 同步）；
  实测计数 CLI 114→115、GUI 99→100（gui.py 实测 100 个窗口方法）。
