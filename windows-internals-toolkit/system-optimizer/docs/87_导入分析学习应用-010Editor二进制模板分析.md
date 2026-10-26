# 导入分析学习应用：010 Editor 二进制模板分析（SweetScape，验证核查 + 引用导入）

> **本批来源**：用户指令——「010 editer学习」。即对 **010 Editor**（SweetScape Software 的
> 专业十六进制/文本编辑器，用户笔误 "editer"）做一轮「导入分析学习应用」。
>
> **纪律守约**：只读查据、不克隆不安装不构建外部依赖；标准分层；版本号仅升 D 段（0026→0027）；
> 无真实 counterpart 不加概念（#591）；references 为权威指针而非正文，详实事实落本档；
> `needs_verify` 挂牌不臆造；专有软件不复制不链接。
>
> **核查方法**：WebFetch 抽取官方页可核实事实 + `curl -sI` 实测 HTTP 状态。
> **结论**：7 个候选 URL **全部实测 200 可达**；版本/平台/许可均取官方口径。

---

## 一、归集范围与核查结论（URL 可达性清单）

| # | 资源 | 实测 | 主题（已抽取可核实事实） |
|---|------|------|--------------------------|
| 1 | `sweetscape.com/010editor/`（官方主页） | 200 | 双定位：「Outstanding Text Editor」+「World's Best Hex Editor」；Binary Templates 解析 300+ 格式；Tree-sitter 实时解析 45+ 语法、50GB+ 大文件、列模式；反汇编 X86/ARM/MIPS/PowerPC/SPARC/SystemZ/XCore；校验和/哈希 CRC-16/CRC-32/Adler32/MD2/MD4/MD5/RIPEMD160/SHA-1/SHA-256/TIGER；脚本 350+ 函数、CLI 无界面批处理、断点/监视调试器；驱动器编辑 NTFS/FAT16/FAT32/exFAT/HFS + MBR/EFI 分区 + slack space；Template Repository / Script Archive；暗/亮主题；Intel Hex / Motorola S-Records 导入导出 |
| 2 | `sweetscape.com/download/010editor/`（下载页） | 200 | 稳定版 **16.0.4**（Beta v17 在测）；Windows 11/10 64 位 25.9MB / 32 位 24.2MB / 便携版 32.7MB·30.4MB；macOS 10.14–15 Intel 37.3MB / ARM 33.9MB；Linux Ubuntu 18.04–25.04 64 位 65.1MB / 32 位 44.8MB；逐产物附 SHA256；旧版专页 |
| 3 | `sweetscape.com/010editor/templates.html`（Binary Templates 专页） | 200 | 模板技术专述入口 |
| 4 | `sweetscape.com/010editor/repository/templates/`（Template Repository） | 200 | 在线模板库：下载/分享/提交 |
| 5 | `sweetscape.com/010editor/repository/scripts/`（Script Archive） | 200 | 在线脚本库 |
| 6 | `sweetscape.com/support/kb/kb1038.html`（EULA） | 200 | 最终用户许可协议 |
| 7 | `sweetscape.com/`（官网首页 Buy Now 区） | 200 | **Commercial $149.95 US / Home·Academic $59.95 US**；30 天全功能试用；Copyright © 2002–2026 SweetScape Software Inc. |

> **公司事实**：SweetScape Software Inc.，加拿大爱德华王子岛（Mount Mellick, PEI）；
> 版权线 2002–2026 即存续年限（v4.0 新闻稿联系地址为官方一手来源）。

---

## 二、Counterpart 映射与导入落点

**边界分级（守 #591/docs/59）**：

- **有真实 counterpart → 回填路径**。本仓 `reverse_docs.json`（黑箱逆向与调试工具链知识库，
  v0.6.73 建立）即 010 Editor 的领域归宿：该库已沉淀 UPX 壳特征、熵判据、PE 节解剖、
  MinGW 交叉造样本、GDB 黑箱四连、ELF vs PE、strip 前后对比、只读逆向边界、REA MCP 链
  共 9 条——全部属「二进制格式分析与逆向工具链」域；010 Editor（Binary Templates 结构级
  解析 + 多架构反汇编 + 驱动器级取证）正是同一工作流的商业级形态，且其 `_position`
  明示服务「学习二进制格式与调试方法」，与用户「学习」意图同向。
- 候选排查：`imagefmt`/`compress`/`firmware`/`legacy` 四个 data 文件均为 gen-stub
  **空占位桩**（`items:0`、明确不自动填充正文）——按 #591 纪律**不填空桩**，仅在本文登记。
- **不新增概念域**：本批为数据层知识条目回填，概念系统零改动。

**回填落点**：

| 文件 | 动作 |
|------|------|
| `src/python/sysweeper/data/reverse_docs.json` | 新增 `hexeditor_010_templates` 条目（name/org/url/protocols×8/interfaces×5/docs×5/advice，全官方口径） |
| `src/python/sysweeper/native/reverse.py` | `REVERSE_CHECKS` 增 `template_structural_reading` 检查项（回链新条目）；`reverse_report()` 管线行插入「010 Editor 模板结构细读」步 |
| `tests/test_reverse.py` | `REQUIRED_KEYS` 增补新键；`test_refs_loaded_9→10`（条目 9→10）；`test_checklist_counts`（检查项 8→9） |
| `README.md` | 版本当前口径刷新 + 本批落账块 |
| 版本号 11 处 | D 段 0026→0027.20261026（version/pyproject/main.go/console.ts/report_viewer.ts/cnstd/5 taxonomy deno 字段/test_cnstd 前缀/README） |
| `concept_gui.html` | 重生（版本串入 data-sha256：`1ff79e4a…`→`d5c0cfe1…`） |

---

## 三、事实要点（官方口径，逐条可回查）

### 3.1 Binary Templates——把「猜偏移」变成「读结构」

- 类 C/C++ struct 的领域语言：可含 `if`/`for`/`while`、函数与复杂表达式；把文件解析为
  **层次化结构**（Template Results），可设为打开文件时**自动运行**。
- 官方口径覆盖 **300+ 格式**；BMP/ZIP/WAV 开箱即析（官方 "Try this" 原话）。
- 在线 **Template Repository** 可下载/分享/提交模板；第三方模板脚本官方明示
  *use at your own risk*，仅保证随软件附送者。
- **工程本质**：模板即**机器可读的格式说明书**——格式知识从「人脑里的偏移表」变成
  可版本化、可分享、可自动执行的代码。这与本仓「先认格式再解析」的格式路由纪律
  （detect 层三段式：格式路由→只读解析→降级指引）同构。

### 3.2 脚本引擎与模板集成

- 类 C/C++ 语法、**350+ 函数**；与模板集成——**给模板变量赋值即改文件**。
- 可**命令行无界面批处理**（repeatable editing → batch job）；带断点/监视的集成调试器。
- 与本仓分层同构：native 层纯函数只读 + 任务层 guidance；「一次校正 → 可复现批处理」。

### 3.3 分析工具清单

- 校验和/哈希：CRC-16、CRC-32、Adler32、MD2、MD4、MD5、RIPEMD160、SHA-1、SHA-256、TIGER。
- 反汇编：**X86、ARM、MIPS、PowerPC、SPARC、SystemZ、XCore** 七架构。
- 二进制逐字节比较、直方图、Mini Map/Visualize、书签、表达式计算器、高亮规则。
- 导入导出：Intel Hex Format、Motorola S-Records、Hex Text、C/C++/Java Code、Base64、
  Uuencoding、RTF、HTML。

### 3.4 文本侧与驱动器级

- Tree-sitter 实时解析 **45+ 语法**（ASM/Bash/C/C++/CSS/Go/Haskell/HTML/Java/JS/JSON/
  Markdown/OCaml/Perl/PHP/PowerShell/Python/Ruby/Rust/SQL/TypeScript/XML/YAML 等）；
  **50GB+** 大文件、列模式、无限撤销、暗/亮主题。
- 驱动器编辑：NTFS/FAT16/FAT32/exFAT/HFS；解析逻辑/物理驱动含 **MBR 与 EFI 分区**；
  可看目录、文件块与 **slack space**——数字取证与数据恢复路径（对应本仓 storage/
  winternals 域）。

### 3.5 版本、平台与许可（2026-10-26 官网核实）

| 维度 | 事实 |
|------|------|
| 稳定版 | **16.0.4**（Beta v17 在测，本次未细究） |
| Windows | 11/10，64 位 25.9MB / 32 位 24.2MB；便携版（USB）32.7MB / 30.4MB |
| macOS | 10.14–15，Intel 64 位 37.3MB / ARM 64 位 33.9MB |
| Linux | Ubuntu 18.04–25.04，64 位 65.1MB / 32 位 44.8MB |
| 完整性 | 每个下载产物官网附 SHA256 |
| 许可 | **商业专有一次性买断**：Commercial $149.95 US、Home/Academic $59.95 US；30 天全功能试用（到期需许可密钥，**无免费档**）；EULA 见 kb1038 |

---

## 四、可复用工程纪律（仅纪律层面）

1. **格式说明书代码化** ↔ 本仓 `references`/`items` 分层（权威指针 vs 详实事实）：模板仓库
   是「社区格式知识库」，遇冷门格式先查仓库再动手写——别人已解析过的格式不必从零逆。
2. **模板即断言，须防漂移** ↔ 本仓沙箱实测口径固化（test_reverse 常量断言）：模板随格式
   版本演进而漂移，换版本必须重核验；先用 `binary_scan` 认格式再套模板，模板结论与原始
   字节抽查对照。
3. **两步走工作流** ↔ detect 层三段式：`binary_scan`（零依赖纯标准库，格式+节+熵粗判）
   → 010 Editor 模板（结构级细读），两步不混。
4. **多架构反汇编清单** ↔ 本仓 asm 子系统与七语言 PE 解析 parity 矩阵。
5. **商业专有 ≠ 可依赖** ↔ 本仓零依赖红线：010 Editor 属「人工分析台」参考，不进运行时
   依赖、不做安装捆绑；可复现路径保持 objdump/gdb/自写解析器的开源组合。
6. **只读边界同源** ↔ `readonly_reverse_ethics`：只用只读分析能力学习二进制格式；对他人
   受保护程序不破解不绕过。

---

## 五、诚实边界（needs_verify 挂牌）

- **60 天退款保证、一年免费支持、支持响应时限**：仅见第三方评测站（itechguides/
  thegeeksclub）转述，官网已抓页面未呈现 → `needs_verify`，不纳入知识条目。
- **Beta v17 新特性**：下载页仅一句横幅，未展开 → 未采集。
- **公司地址/成立年份**：版权线 2002–2026 与 v4.0 新闻稿联系地址（加拿大 PEI）为官方
  一手；「2002 年创立」为第三方目录口径（与版权线互证），从宽登记。
- **专有红线**：010 Editor 为商业专有软件，本批**不安装、不试用、不复制、不链接**任何
  其代码/资源；仅登记官方公开事实与可复用纪律。
- 本批为**数据层知识条目回填**，概念系统未动（`audit_concepts --strict` 应归零）。

---

## 六、落点清单与验证

- `reverse_docs.json` +1 条目（`hexeditor_010_templates`，8 protocols / 5 interfaces / 5 docs）；
  `native/reverse.py` +1 检查项、报告管线 +1 步；`test_reverse.py` 三处计数同步。
- 版本号 D 段 0026→0027.20261026 全 11 处同步 + `concept_gui.html` 重生（`--check` 过）。
- **验证**：定向 `test_reverse` **16 passed**；全量 pytest **1755 passed / 6 skipped 零回归**；
  `audit_concepts --strict` 归零。
