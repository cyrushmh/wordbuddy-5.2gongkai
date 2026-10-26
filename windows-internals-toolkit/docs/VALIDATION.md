# 验证记录

做法参考 DiPlay 的 `docs/VALIDATION.md`：每个值得记住的节点，记录**测了什么、产物是什么（校验和）、
以及哪些没验证**。不写就没发生过；写不清楚"没验证什么"等于没写。

## 2026-10-17 · RFC 全量标准目录导入（数据层 + CLI + 引用核验）

### 测了什么

- **官方索引抓取**：`https://www.rfc-editor.org/rfc-index.txt` 一次拉取即全文
  （服务端忽略 Range 头）→ `research/rfc/rfc-index.txt`，2,027,473 字节 / 42,904 行，
  sha256 `24cc02402437a1e0c3679b879cbc2f9f933a99ec4f8a846f4a96f12e295726b5`（manifest.json 记录）。
- **解析器**：`research/harvest/rfc_index_harvest.py` → `sysweeper/data/rfc_standards.json`
  （顶层 dict、key=rfcNNNN，**10,036 条**：issued 9,848 / Not Issued 188）。
  解析失败 0；抽查 RFC 9846 / 8446 / 8996 / 后续编号至 10065 全部字段正确；
  作者/日期分离回归 0 残留。已知瑕疵：1969–1971 前后 11 条老条目标题粘连（源头形态，
  写入 harvest report 诚实标注，未手工篡改）。
- **消费层**：`native/rfc_catalog.py` 冒烟 + 5 项单测（编号归一化 9846/"rfc09846"/
  "RFC 9846"、未分配 10544 返回 None、Not Issued 14 返回 `i=false`、search/by_status/
  citing 反向索引）。
- **CLI**：`python -m sysweeper rfc` 家族 5 项子进程级测试（overview / show 9846 含
  citing 任务 / show 10544 与 14 的诚实分支 / search 与 list --status / citing rfc08996）。
- **任务引用全量核验**：`models.py` + 全部 `tasks/*.py` 的 `RFC NNNN` 对照官方索引：
  **可核验 185 处 / 不可核验 0 处 / 误引 Not Issued 0 处**。修正 3 处含混引用
  （dnshealth 补 RFC 1035；meshnet「RFC 牵引」改为 7748/7693/8439/5869 精确原语引用——
  官方索引证实截至 2026-10 不存在 WireGuard RFC）；无据的 6891/8020/9110/9111/9112 不加。
- **全量回归**：`pytest tests/ -q` → **1065 passed / 3 skipped**（179s）。
- **巡检**：`scripts/audit_standards_eol.py` → 69 个知识库纳入巡检
  （rfc_standards.json 10,036 项），结构校验通过、需复核 0。

### 产物

| 文件 | 说明 |
|---|---|
| `research/rfc/rfc-index.txt` | 官方 RFC INDEX 原文（2.0MB，sha256 见 manifest.json） |
| `research/rfc/manifest.json` | 抓取出处/字节/行数/指纹 |
| `research/rfc/rfc_index_harvest_report.json` | 解析统计（状态分布/Not Issued 数/粘连标注） |
| `research/harvest/rfc_index_harvest.py` | 可复现解析器 |
| `sysweeper/data/rfc_standards.json` | 全量结构化目录（2.3MB，10,036 条） |
| `sysweeper/native/rfc_catalog.py` | 只读消费层（lazy load，import 期不阻塞） |
| `docs/14_RFC全量标准目录与CLI检索.md` | 完整说明 |

### 没验证的（诚实声明）

- **未逐条阅读 RFC 正文**：本层只收录官方索引元数据（标题/作者/日期/状态/关系/DOI），
  不复制正文；引用核验止于「编号-状态-标题存在性」。
- **CLI 仅 Linux 实跑**：跨系统运行交给既有 CI（.pyz 冒烟矩阵）。
- **WireGuard 规范未进一步溯源**：只用官方索引证明了「IETF 无 WireGuard RFC」这一事实，
  协议细节以 wireguard.com 论文为准，本轮未抓取该论文。

## 2026-10-08 · CI 失败复盘：exit 120 与 exit 1（不是 Node 20 警告）

> 完整方法论与本案例细节见 [`docs/CI-排错.md`](CI-排错.md)。

### 起因

`Build Python Layer` 在 Linux / Windows 红、macOS 绿。日志末尾是
`Node.js 20 is deprecated ... actions/download-artifact@v4`，但那个 action 状态是
**success**——它只是警告，不是原因。用 API 拉到真实日志后定位到两个互不相干的 bug。

### 真实原因与修复

| Job | 退出码 | 真实原因 | 修法 |
|---|---|---|---|
| Linux（跑同一 .pyz） | **120** | `hardware \| head -6`：head 提前关管道，Python 在**解释器退出阶段**那次 flush 抛 `BrokenPipeError`，退出码被抬成 120，叠加 runner 的 `pipefail` 判整步失败 | `cli.main()` 捕获 `BrokenPipeError` 并把 fd 1 指向 `/dev/null`；返回前**主动 flush** 覆盖"退出时才炸"的路径；工作流改为落盘后再 `head` |
| Windows（跑同一 .pyz） | **1** | Git Bash 下 stdout 编码是控制台 ANSI 代码页（**cp1252**），中文与 `→ ✓` 一 print 就 `UnicodeEncodeError`。**英文版 Windows 用户本机跑同样会崩**，macOS/Linux 是 UTF-8 所以永远测不出来 | 新增 `cli.harden_streams()`：入口把 stdout/stderr `reconfigure` 成 UTF-8（`errors="replace"`），失败则降级只改 `errors` |

### 测了什么

- **本地复现旧行为**：绕过防护直接调命令函数 → `rc=120`，且 stderr 与 CI 日志逐字一致
  （`Exception ignored in: <_io.TextIOWrapper ...>` + `BrokenPipeError`）；修复后同命令 `rc=0`。
- **本地复现旧崩溃**：`PYTHONIOENCODING=cp1252` 下 `UnicodeEncodeError: 'charmap' codec ...`；
  修复后同一命令 `rc=0` 且中文正常输出。
- **新增 `tests/test_streams.py` 9 个用例**，单元级（替换 `sys.stdout` 为会抛
  `BrokenPipeError` 的假流，覆盖"命令中炸"和"退出 flush 才炸"两条路径）+ 子进程级
  （`PYTHONIOENCODING=cp1252` / `ascii` 真实端到端、`bash -o pipefail ... \| head -1` 断言 `rc != 120`）。
- **全量回归**：`PYTHONPATH=src/python python3 -m pytest -q` → **417 passed / 3 skipped**（新增 9）。
- **工作流 YAML**：三个文件均通过 `yaml.safe_load`；`upload-artifact` / `download-artifact`
  由 v4 升到 **v5**（消除 Node 20 警告，同一流水线内 upload 与 download 同步升级）。
- **护栏**：`python3 scripts/check_repo_guard.py` 通过。

### 真机 CI 结果（run `37682971131`）

推到 `main` 后真实跑了一次，**五个 job 全绿**：护栏 / 构建产物 / Linux / macOS / Windows。
Windows 日志里新增的窄编码步骤确实打出了中文「探测结果：`platform: windows`」，
cp1252 与 ascii 都没崩——上面"只在 Linux 模拟"的疑虑至此消除。

### 没验证的 / 推测被推翻的（诚实声明）

- **「升到 artifact v5 就能消掉 Node 20 警告」是错的**：真机日志里警告原样还在，
  只是版本从 `download-artifact@v4` 变成 `@v5`。v5 自身仍声明 node20。
  升级照做（为 Node 20 真正下线做准备），但不能指望它消警告——别拿它当排错的线索。
- **macOS 那次是绿的属于竞态侥幸**，未复现它触发失败的条件；修复是根治性的（不再依赖时序），
  但"macOS 为什么恰好没触发"没有继续追。
- **真实 cmd.exe / PowerShell 未覆盖**：CI 走的是 Git Bash（`shell: bash`）。
  纯 `cmd.exe` 下 Python 会走 `WriteConsoleW` 而不是 ANSI 代码页，行为不同，没测。
- **cp936（中文 Windows 代码页）没在真机上测**：只测了 cp1252 与 ascii。
  理论上 harden 之后任何代码页都一样（强制 UTF-8），但没有真机证据。

## 2026-10-08 · 低层码制（机器码 / 编码 / 通信码 / 逻辑转换码）

> 对应提交：本文件所在的那次提交，`git log -1 --format=%h` 可查（不写死哈希，避免 amend 后失效）。
> 详细说明见 [`docs/低层码制.md`](低层码制.md)。

### 测了什么

- **单元测试**：`PYTHONPATH=src/python python3 -m pytest -q` → **408 passed / 3 skipped**（约 80s）。
  新增 46 个（`test_lowcode`），覆盖 bits / chars / comm / logic / machine 五层。
- **固定向量**（不是"跑通不报错"）：8 个 CRC 变种对 `b"123456789"` 的 check 值全部命中，
  CRC-32 与 `zlib.crc32` 交叉一致；Modbus RTU 帧 `01 03 00 00 00 01` 附加 CRC 得 `84 0A`；
  RFC 1071 示例反码和 `0xDDF2`、校验和 `0x220D`、整段复核 `0xFFFF`；Adler-32 `hello` = `0x062C0215`；
  COBS `11 22 00 33` → `03 11 22 02 33`；IEEE 754 `0x3F800000` = 1.0；8 位补码 `-7` = `0xF9`。
- **往返与穷举**：进制 2/8/10/16/36 往返；格雷码 0–255 往返且相邻码只差一位；
  Base 六方案往返；HDLC / SLIP / COBS 成帧往返；汉明(7,4) **16 个码字 × 7 个单比特错**全部纠正；
  汉明(8,4) 任意两位错判为不可纠正；8 位补码加法器 `x,y ∈ {-128,-1,0,1,127}` 全组合无矛盾。
- **逻辑化简等价性**：随机 300 个两/三/四变量表达式，QM 化简后与原式**真值表逐行比对**全部一致。
- **Java class 真文件解析**：沙箱有 `javac 20`，编译 `LowCodeProbe.java` 后用本层解析——
  魔数/主版本号（64 → Java SE 20）、类名、父类、常量池解析、方法 `twice(I)I` 的 Code 属性
  与反汇编结果（`imul` / `ireturn`）全部正确，与 `javap` 语义一致。
- **x86-64 拆解**：8 条内置样例（`55` / `4889e5` / `b801000000` / `4801d8` / `4831c0` / `c3` /
  `0f1f440000` / `e800000000`）长度自洽且字段正确；RIP 相对寻址在位移字节不足时也不崩。
- **打包冒烟**：`tools/syspkg.py smoke` 增加 6 条 lowcode 用例（概览 + 每层各一例），
  `.pyz`（1,776 KB）在独立进程全部 rc=0 —— 证明新子包随单文件分发一起可用。

### 产物（本地 python3.11.1 构建）

| 文件 | 字节 |
|---|---|
| `sysweeper-0.6.0.pyz` | 1,776 KB |

### 没验证的（诚实声明）

- **x86-64 助记符只是启发式提示**：本层是结构化拆解器（前缀/REX/ModRM/SIB/位移/立即数），
  未做完整 opcode 表；权威表在 Intel SDM Vol.2 Appendix A / AMD APM，未逐条比对。
- **Java 反汇编只覆盖 0x00–0xC9**：`tableswitch` / `lookupswitch` / `wide` 已实现但未用
  含这些指令的真实 class 文件验证（样例里没生成到）。
- **未验证非 x86 架构的机器码**：ARM64 / LoongArch 指令未纳入本层（RISC-V 64I 已纳入，
  见「进制对照」一节上方；用独立参考编码器交叉验证，覆盖 RV64I + 双字扩展共 28 条指令 +
  流解码/边界/`RV_SAMPLES` 自洽 + 子进程级 CLI）。
- **未做性能基准**：CRC 用的是逐位实现（教学优先），大块数据场景未与查表实现比对耗时。

---

## 2026-10-08 · 进制对照：二进制 / 三进制 / 十进制等，十进制为人类可读默认

> 详细说明见 [`docs/低层码制.md`](低层码制.md)「进制：使用者视角默认十进制」。

### 测了什么

- **单元测试**：`PYTHONPATH=src/python python3 -m pytest -q` → **422 passed / 3 skipped**（约 85s）。
  本次新增 4 个（`test_lowcode`）：`test_ternary_and_arbitrary_bases` / `test_human_readable_decimal`
  / `test_from_base_defaults_to_decimal_for_humans` / `test_bases_cli_actions_subprocess`（子进程级）。
- **三进制固定向量**：`to_base(100, 3) == "10201"`、`to_base(-7, 3) == "-21"`、`from_base("10201", 3) == 100`；
  任意进制 2/3/4/7/9/12/16/20/36 与 `from_base` 往返一致。
- **人类可读十进制**：`human_int(1234567) == "1,234,567"`、`human_int(-1234) == "-1,234"`；
  `render_bases(255)` 第一行即「十进制（人类可读·默认）: 255」，`render_bases(9876543210)` 含千分位。
- **输入默认十进制（关键取舍）**：`from_base("255", default_base=10) == 255`，而旧默认
  `from_base("255") == 0x255`（597，机器视角）——`bits` CLI 已改用 `default_base=10`，
  裸数字不再误当十六进制；`0x/0o/0b` 前缀仍可切换进制。
- **越界静默跳过**：`bases(5, (1, 2, 37))` 只返回 base 2 一项，base 1 / 37 被忽略，不抛异常。
- **CLI 子进程级**：`code bits --action bases --value 255`、`--action base --value 0xFF --base 3`
  （255 的三进制 `100 110`）、`--action base --value 255 --base 2`（二进制 `1111 1111`）、
  `--base 40`（越界提示「2-36」）全部 rc=0 且输出符合预期。

### 产物（本地 python3.11.1 构建）

| 文件 | 字节 |
|---|---|
| `sysweeper-0.6.2.pyz` | 待构建 |

### 没验证的（诚实声明）

- **大数性能**：`to_base` 是循环除法实现，对超大整数（数百位）未做性能基准；教学用途足够。
- **非阿拉伯数字进制**：只支持 0–9A–Z（base ≤ 36），未实现更高基（如 base64 用 `-_/.` 之类）；
  上层字符编码的 Base 系列在 `chars` 层独立实现，不在此处。

---

## 2026-10-08 · 语言底层 + 诊断/护栏

> 对应提交：本文件所在的那次提交，`git log -1 --format=%h` 可查（不写死哈希，避免 amend 后失效）。

### 测了什么

- **单元测试**：`PYTHONPATH=src/python python3 -m pytest -q` → **362 passed / 3 skipped**（约 79s）。
  新增 24 个：打包层 7（`test_pkg_layer`）、诊断层 11（`test_diagnostics`）、仓库护栏 6（`test_repo_guard`）。
- **单文件 .pyz 冒烟**（`tools/syspkg.py smoke`）：`detect` / `hardware` / `arch` / `--platform windows --version 11 list`
  全部 rc=0；`android` 输出 18,855 字符，证明包内 JSON 知识库在 zip 中完整可读。
  强制走兼容层（`SYSWEEPER_ZIPRES_SHIM=1`）时 `arch` 仍输出正常 —— 覆盖 Python 3.9/3.10 那条路径。
- **wheel**：`pip install` 实测成功（生成 console script `sysweeper`）；
  `sys.path` 直接塞 wheel 路径也能 import（`sysweeper.__version__` = 0.5.22）——PEP 427 结构合规。
- **Go 交叉编译实测**：`linux/arm64` → ELF aarch64 静态链接；`windows/arm64` → PE32+ Aarch64。
- **仓库护栏**：`python3 scripts/check_repo_guard.py` 通过，无凭据容器 / 私钥块，
  `AndroidManifest.xml` 权限在白名单内（当前白名单仅 `INTERNET`，实际声明为零权限）。
- **护栏负向验证**：临时构造含 `.key` 文件、内嵌 PEM 私钥块、声明 `CAMERA` 权限的仓库，护栏三类问题全部拦截（exit 1）。

### 产物（本地 python3.11.1 构建，noarch，跨系统跨硬件通用）

| 文件 | 字节 | SHA-256 |
|---|---|---|
| `sysweeper-0.5.22.pyz` | 1,623,083 | `490789bc71c0b8ef9738578c3477ddc5e571ec893a83da14eedab1bd6240d921` |
| `sysweeper-0.5.22-py3-none-any.whl` | 582,424 | `25878bffe5383e9853dcb05e27715e303c46966e26bcd0e695000790ab441280` |
| `sysweeper-0.5.22.tar.gz` | 570,368 | `b0ed476be0ea7396dc4fcafa9656133118ddc76824b1b297528c38613064fff5` |

> 字节数/SHA-256 随源码变化而变；这里记录的是 0.5.22 这一版的可复现基线。

### 没验证的（诚实声明）

- **Android APK 未真机安装**：沙箱无 Android SDK/设备，APK 由 `build-android.yml` 在 CI 产出。
- **Windows / macOS 未本地实跑 .pyz**：本地只有 Linux；跨系统验证交给 `build-python.yml`
  的 `verify-cross`（在三大 runner 上用系统自带 Python 跑同一个 .pyz）。
- **Rust（cargo）未本地构建**：`peview-egui` 需联网拉 crates，本轮跳过（`syspkg` 的跳过策略：缺工具链不失败）。
- **Go 二进制未在目标硬件上运行**：只验证了产物格式（ELF/PE 头），未在真实 arm64 / riscv64 机器上执行。
