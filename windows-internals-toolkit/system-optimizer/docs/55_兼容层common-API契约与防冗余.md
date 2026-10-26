# 55 · 兼容层 `common` —— API 契约、设计哲学与防冗余机制 —— v0.6.88

> 用户需求原文（#531 收口遗留）：「docs 文档也算是保证概念系统的联动连轴连动的统合与整合」；并确认「docs 文档经重新验证后可以完善补全优化，继续」。
>
> 本文是 `native/common.py` 的**独立 API 文档页**：把兼容层的公开契约、设计哲学与防误判冗余机制集中成文，使其成为联动网格中可被引用、可被审计的一等文档节点。

## 1. 它是什么 —— 单一事实源（single source of truth）

`native/common.py` 是 sysweeper **唯一**的跨子系统共享工具库（兼容层）。它的职责边界非常窄：

> 为所有 native 子系统（windows / linux / macos / bsd / unix / android / ios / harmony / …）提供**与具体 OS 无关**的只读辅助——命令执行、字节格式化、磁盘用量、缓存/临时/大目录盘点、DNS 缓存刷新指引、多系统无障碍探测。

它**不承担**任何具体平台的诊断逻辑，也不写任何系统状态。平台相关性由各 `native/<platform>.py` 自行负责；`common` 只提供它们共用的、确定性的小工具。

## 2. 身份契约（机器可读的唯一性标记）

模块顶部的三个属性是**机器可读的身份契约**，被测试 `tests/test_native_common_lib.py` 直接断言：

| 属性 | 值 | 含义 | 测试 |
|---|---|---|---|
| `__role__` | `"shared_compat_lib"` | 声明自己是唯一兼容层 | `test_common_is_canonical_compat_lib` 断言等于此值 |
| `__canonical__` | `True` | 声明自己是正典、非副本/冗余 | 同上，断言为 `True` |
| `__version__` | `"0.6.88"` | 公开契约版本，跟随包版本同步 | 同上，断言匹配 `^\d+\.\d+\.\d+$` |

> **关键**：`__role__` 在全 sysweeper 包内**必须唯一**。任何第二个定义 `__role__ = "shared_compat_lib"` 的模块，都会被防冗余测试判定为「幽灵副本」并 FAIL。

## 3. 设计哲学（四条硬纪律）

| 纪律 | 落点 | 违反后果 |
|---|---|---|
| **单一事实源** | 跨子系统共用的小工具只此一份，扩展请在文件内新增函数并更新 `__all__`，或新建**语义不同**的模块 | 出现副本 → 行为漂移、双份维护、历史「振荡/还原事故」 |
| **零第三方依赖** | 仅用标准库 `os / shutil / subprocess / sys / typing` | 引入第三方 → 破坏各平台可移植性与冷启动 |
| **失败不抛** | 所有公开函数失败时返回 `(False/None, 说明)`，把降级决定权交给上层 | 抛异常 → 一个平台探针失败拖垮整个报告 |
| **只读不写** | 绝不安装/卸载、不删除、不写系统目录；系统级动作（如 DNS 刷新）只**给命令指引**，需 `--apply --yes` 才执行 | 越权写盘 → 破坏「默认只分析不乱改」的安全底线 |

## 4. 防误判冗余机制（三道防线）

历史上有过「振荡/还原事故」：因误判而生成拼写错误的幽灵副本（如三 e 的 `sysweerer`），以及 `common` 的形似副本。为此固化为三道防线，**扫描根已覆盖整个 `sysweeper` 包**（含 `native/`、`tasks/`、顶层模块与子包）：

| 防线 | 测试函数 | 校验内容 |
|---|---|---|
| **① 身份契约** | `test_common_is_canonical_compat_lib` | `__role__`/`__canonical__`/`__version__` 三标记正确 |
| **① API 契约** | `test_common_public_api_contract` | `__all__` 列出的每个符号都存在且 `callable`（契约不悬空） |
| **② 实际被依赖** | `test_common_is_actually_used` | 被 ≥30 个模块以 `from . import common` 等方式引用（引用数过低即告警「沦为冗余文件」） |
| **③ 角色不重复** | `test_no_duplicate_compat_role` | 全包 `__role__` 不得重复（重复即幽灵副本） |
| **③ 形似副本侦测** | `test_no_lookalike_compat_duplicate` | 全包不得出现 `common` 的**编辑距离 ≤1** 公开形似副本（`commonn`/`commons`/`commom` …）；前导下划线私有模块（如 `concepts/_common.py`）豁免 |
| **③ 包名形似侦测** | `test_no_lookalike_package_duplicate` | `src/python` 层不得出现 `sysweeper` 拼写错误形似副本（如 `sysweerer`，编辑距离 ≤2） |

> **实测验证**：临时在 `native/` 放入 `commonn.py`（带 `__role__`，编辑距离 1），`test_no_lookalike_compat_duplicate` 立即 FAIL；删除后 6 项全绿。防线可拦截注入。

> **私有模块豁免说明**：`concepts/_common.py` 是合法的内部 helper，前导下划线即「刻意私有」语义，不属于「公开名幽灵副本」防范对象，故形似检查跳过 `_`-前缀名。

## 5. 公开 API 契约（15 个符号）

下表即 `__all__` 的全部 15 个公开符号。**所有函数返回 `(ok, msg)` 或具体值，失败不抛。**

### 5.1 命令执行

| 符号 | 签名 | 语义 |
|---|---|---|
| `run` | `run(cmd, timeout=None, tail=None) -> (rc, out)` | 跑一条命令，返回 `(returncode, 合并 stdout+stderr)`。失败也返回 `(−1, 说明)`，不抛。`timeout`/`tail` 不传时取可调阈值 `cmd.timeout`（默认 120）/ `cmd.tail`（默认 2000，防超长输出灌爆报告）；`tail=0` 表示不截断。 |

### 5.2 字节格式化

| 符号 | 签名 | 语义 |
|---|---|---|
| `human` | `human(n: int) -> str` | 把字节数转人类可读串（B/KB/MB/GB/TB/PB，1024 进制）。 |

### 5.3 磁盘 / 体积

| 符号 | 签名 | 语义 |
|---|---|---|
| `disk_usage` | `disk_usage(path=".") -> Optional[dict]` | 返回 `{total, used, free}`（字节），拿不到返回 `None`。 |
| `free_space` | `free_space(path=".") -> Optional[int]` | 取 `disk_usage` 的 `free` 字段，失败返回 `None`。 |
| `list_dir_size` | `list_dir_size(path) -> Optional[int]` | 递归统计目录字节数（只读）。路径非法/失败返回 `None`。 |
| `find_large_subdirs` | `find_large_subdirs(root, top=None) -> List[(path, bytes)]` | 列出 `root` 下体积最大的子目录。`top` 不传取阈值 `scan.limit`（默认 10）。 |

### 5.4 只读盘点

| 符号 | 签名 | 语义 |
|---|---|---|
| `user_cache_report` | `user_cache_report() -> (ok, msg)` | 汇总当前用户可清理缓存（POSIX `~/.cache` / Windows `LOCALAPPDATA`）。**只列体积、不删除**。 |
| `temp_report` | `temp_report() -> (ok, msg)` | 汇总系统/用户临时目录（`/tmp` / `%TEMP%`）体积。只列不删。 |
| `large_dirs_report` | `large_dirs_report(top=None, limit=None) -> (ok, msg)` | 列出某根目录下最大子目录辅助定位可瘦身项。`top` 缺省 `~`，支持 `~` 展开；`limit` 缺省 `scan.limit`。只读。 |
| `dns_flush_hint` | `dns_flush_hint() -> (ok, msg)` | 跨平台探测并给出刷新 DNS 缓存的命令（Windows `ipconfig /flushdns`、macOS `dscacheutil`+`killall`、Linux `resolvectl`/`systemd-resolve`/`nscd`）。**只指引不执行**，需 `--apply --yes`。 |

### 5.5 多系统无障碍（只读探测）

| 符号 | 签名 | 语义 |
|---|---|---|
| `a11y_report` | `a11y_report() -> (ok, msg)` | ORCA / AT-SPI2 无障碍环境报告（读屏器、辅助技术总线、语音后端）。 |
| `a11y_atspi_bus` | `a11y_atspi_bus() -> (ok, msg)` | 探测 AT-SPI2 辅助技术总线（`org.a11y.Bus`）是否响应。 |
| `a11y_orca_status` | `a11y_orca_status() -> (ok, msg)` | ORCA 屏幕阅读器：是否安装 + 版本 + 是否随会话自启动。 |
| `a11y_multi_report` | `a11y_multi_report() -> (ok, msg)` | **多系统**无障碍适配（Windows 讲述人+UIA / macOS VoiceOver+AX / Linux ORCA+AT-SPI2 / Android TalkBack / iOS VoiceOver / 鸿蒙屏幕朗读）。 |
| `a11y_docs_report` | `a11y_docs_report() -> (ok, msg)` | 多系统无障碍**权威文档**清单（协议 protocols + 接口 interfaces）。 |

## 6. 调用约定（给上层子系统）

- **统一解包**：`ok, msg = common.run(...)`；`ok` 为布尔/整数状态码，`msg` 为说明或数据。不要假设 `msg` 非空。
- **不要捕获之外的异常**：`common` 已自行兜底；上层只需判断 `ok`。
- **扩展请内联**：新增共用工具请直接在本文件加函数并补进 `__all__`，并同步更新本文「5. 公开 API 契约」表与 `__version__`；勿新建 `common` 形似副本。
- **阈值来自 settings**：`run` 的 `timeout`/`tail`、`find_large_subdirs` 的 `top`、`large_dirs_report` 的 `root`/`limit` 等均可经 `native/settings.py` 在 GUI/CLI 调，保持「单一可调参数面」。

## 7. 与联动网格的关系

`common` 是**被依赖的底层事实源**，不直接挂接 linkage 轴（它不是业务子系统，而是业务子系统的共享底座）。它的「存在性」由 #536 的三道防线保证——只有底座不被误判为冗余、不被幽灵副本污染，上层 `sysbase`/`docs` 等子系统的只读诊断才能稳定复用同一套工具。本文作为独立文档节点，与 `54_系统基座` 文档互为印证，共同构成概念系统「联动连轴连动」统合整合的文档层一环。
