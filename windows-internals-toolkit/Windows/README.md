# Windows Internals Toolkit（Windows 内核机理与优化分析系列）

> 本目录是 `wordbuddy-github` 总仓库下的一个子项目。仓库总览与同步方式见根目录 [`README.md`](../README.md)；新增其他任务时请在根目录另建子目录，而非新建仓库。

基于资料库《Windows Internals, 7th Edition, Part 1》分析的成果合集：从底层程序格式（PE）到磁盘 I/O 与系统整体优化，形成「格式 → 磁盘 → 整体」的完整认知闭环。

## 仓库内容

```
windows-internals-toolkit/
├── docs/                          # 三套自包含文档展示系统（HTML，可离线打开）
│   ├── windows_internals_disk_opt.html   # ① 磁盘/存储优化方案
│   ├── windows10_overall_opt.html        # ② Windows 10 整体优化方案
│   └── pe_format_doc.html                # ③ PE 程序格式文档
├── src/                           # 【多代码共存】按语言/用途分目录，互不干扰
│   ├── c/                         # C 子项目（C11，mingw 交叉编译）
│   │   ├── peinfo/                #   纯标准 C 的 PE 头查看器
│   │   └── win32_gui/            #   Win32 API 原生 GUI 版 PE Viewer
│   ├── rust/                      # Rust 子项目（stable / edition 2021 / MSRV 1.74）
│   │   ├── peinfo/               #   纯标准库 PE 解析 CLI
│   │   └── peview-egui/          #   egui 原生 GUI 版 PE Viewer
│   ├── python/                    # Python 子项目（3.14，标准库，无第三方依赖）
│   │   ├── pe_inspect.py          #   PE 结构解析器（CLI）
│   │   ├── gui_peview.py          #   tkinter 图形界面 PE Viewer
│   │   └── peview_qt.py           #   Qt6 (PySide6) 图形界面 PE Viewer
│   ├── ruby/                      # Ruby 子项目（3.5 稳定版，纯标准库）
│   │   └── peinfo/                #   纯标准库 PE 解析 CLI（--json）
│   ├── powershell/                # Windows 优化 / 诊断脚本（需 Windows 运行）
│   │   ├── Optimize-Windows10.ps1 #   检测 / 应用 / 回退 一体化优化
│   │   └── PEInfo-Gui.ps1         #   WinForms 图形界面 PE Viewer
│   ├── dotnet/
│   │   ├── PeInfo/                 # .NET 无头控制台 PE 解析器（net10.0，跨平台可验证）
│   │   └── PeView/                 # .NET 10 LTS 参考实现（WinForms GUI，Windows-only）
│   ├── vba/                        # Microsoft Office VBA 版 PE 查看器（标准模块 .bas）
│   │   └── PEInfo/                 #   PEInfo.bas：纯 VBA，可导入任意 Office 工程
│   └── java/                       # Java 子项目（OpenJDK 25 LTS，纯标准库）
│       └── peinfo/                 #   PeInfo.java：纯 JDK 标准库 PE 解析 CLI（--json）
├── tools/                         # 预编译二进制产物（交叉编译得到）
│   ├── peinfo.exe / peinfo32.exe  # PE32+ / PE32 控制台版
│   ├── peinfo_rs.exe              # Rust 版 PE 解析 CLI（x64）
│   └── peview.exe                 # Win32 GUI 版 PE Viewer（x64）
├── VERSIONS.md                    # 稳定版/LTS 语言与运行时版本策略
├── GUI_MATRIX.md                  # 多种 Windows GUI 方案对照与选型
├── build.sh                       # 交叉编译脚本（mingw-w64）
├── .github/workflows/build.yml    # GitHub Actions：自动编译并发布 Release 产物
├── LICENSE
├── README.md
└── push-to-github.sh
```

## 多代码共存组织

仓库按「文档 + 多语言代码」共存：`docs/` 放分析文档，`src/` 下按语言/用途分为 `c/`、`rust/`、`python/`、`ruby/`、`powershell/`、`dotnet/`、`vba/`、`java/` 八个子目录（C / Rust / Python / Ruby / PowerShell / C# / VBA / Java），互不影响；`tools/` 放预编译二进制产物。新增语言直接在 `src/` 下新建对应目录即可。

**开发采用 branch 工作流**：新功能在 `feature/*` 分支开发（如 `feature/multi-lang-tools`），推到远端后通过 Pull Request 合并到 `main`——私密仓库下用分支即足以隔离工作线，无需 fork 整个仓库。`push_branch.py <TOKEN> [分支名]` 可把当前工作区推到指定分支（绕过沙箱 git 协议限制）。


## 三套文档的衔接

| 文档 | 定位 | 衔接点 |
|---|---|---|
| 磁盘优化方案 | 存储介质 / I/O 栈机理 | PE 以"映射文件"读入内存；节映射 = 磁盘 I/O 来源 |
| Win10 整体优化 | 启动 / 内存 / 服务 / 视觉 | 导入表大小 → 启动快慢；DLL 劫持 → 启动项审计 |
| PE 格式文档 | 程序底层结构 | 解释"程序在盘上长什么样、加载器怎么翻译它" |

一句话收束：**磁盘优化解决"字节怎么从盘到内存快"，Win10 优化解决"系统怎么为程序让路"，PE 格式解决"程序到底长什么样"**——三者合起来，才是对"Windows 为什么这么运行"的完整回答。

## peinfo 工具

一个最小的 PE 头查看器，运行时会沿 `MZ → e_lfanew → PE\0\0 → COFF头 → 可选头 → 节表` 解析并打印目标 PE 的头部信息（默认解析自身）。它本身就是合法 PE，可作为"程序格式"的活的示例。

**C / Rust / Python / .NET / VBA / Java / Ruby 七个实现同源同义**，且都支持机器可读 JSON 输出（C 用 `-j`、Rust/Python/.NET/Java/Ruby 用 `--json`、VBA 用 `PeInfoJson()`），便于自动化与跨语言对齐。`tests/parity_test.py` 会在 Linux 上把 C（gcc）、Rust（cargo）、.NET（dotnet 无头控制台版）三者编出来并对同一文件比对，确保结果完全一致（详见下方"跨语言一致性测试"）。PowerShell 版额外支持 `-Json` 无 GUI 输出、VBA 版用 `PeInfoJson(path)` 返回 JSON 字符串——二者均属 Windows-only（见各自目录说明），需 Windows 运行时验证。

### 本地编译（交叉编译，无需 Windows）

```bash
bash build.sh
# 等价手动步骤：
x86_64-w64-mingw32-gcc -O2 -s src/c/peinfo/peinfo.c -o tools/peinfo.exe      # PE32+ / x64 控制台
i686-w64-mingw32-gcc   -O2 -s src/c/peinfo/peinfo.c -o tools/peinfo32.exe     # PE32  / x86 控制台
x86_64-w64-mingw32-gcc -O2 -s src/c/win32_gui/peview.c -mwindows -lcomdlg32 -o tools/peview.exe  # 原生 GUI
cargo build --release --target x86_64-pc-windows-gnu  # Rust → tools/peinfo_rs.exe
```

> C 源码唯一真源在 `src/c/peinfo/peinfo.c`（结构体已改用定宽整数类型），Windows(mingw) 与本机 Linux(gcc) 都能正确编译——因此一致性测试能在 Linux 上直接运行 C 本机版。
>
> `build.sh` 在产物编译完成后会自动调用 `tests/parity_test.py`。

### 持续集成（GitHub Actions）

推送到 `main` 后，`.github/workflows/build.yml` 会自动用 mingw-w64 重新编译两个 exe 并上传为 Artifact；打 tag（如 `v1.0`）时还会发布到 Release 附带二进制产物。

### 运行（Windows）

```cmd
peinfo.exe            :: 解析自身
peinfo.exe other.dll  :: 解析任意 PE 文件
```

### 校验（任意支持 Python 的环境，无需第三方库）

```python
import struct
d = open("tools/peinfo.exe","rb").read()
assert d[:2] == b"MZ"
e_lfanew = struct.unpack_from("<I", d, 0x3C)[0]
assert d[e_lfanew:e_lfanew+4] == b"PE\x00\x00"
print("合法 PE：", d[e_lfanew+4:e_lfanew+6].hex())  # 8664 = x64, 014c = x86
```

## 跨语言一致性测试（tests/parity_test.py）

同一份 PE 解析逻辑用 C / Rust / Python / .NET / VBA / Java / Ruby 七种语言实现，最怕"各写各的、悄悄分叉"。`tests/parity_test.py` 把可编译/可运行实现都拉起来（C 用本机 gcc、Rust 用本机 cargo、.NET 用 `src/dotnet/PeInfo` 的 `dotnet build`、Java 用本机 `javac`、Ruby 用本机 `ruby`——五者都能在 Linux 直接运行；Python 直接解释执行；PowerShell 版仅在检测到 `pwsh` 时纳入，否则跳过），对 `tools/` 下每个 `.exe` 跑一遍 `--json`，并比对以下稳定字段：

- `machine` / `number_of_sections` / 可选头 `magic` / `entry_point` / `image_base` / `subsystem` / `number_of_rva_and_sizes`
- 数据目录数量、每个节的 `name / virtual_address / virtual_size / size_of_raw_data / pointer_to_raw_data / characteristics`

比对时**只比对数值字段、不比对可读名称字符串**，避免表述差异误判。任一不一致即视为失败（退出码 1）。当前在 Linux 沙箱内验证：C / Rust / Python / .NET / Java / Ruby 六版对 4 个样本（PE32+ x64 ×3 + PE32 x86）全部一致；VBA 版解析偏移已用 Python 复刻并对照，核心字段同样完全一致（Windows-only，未自动纳入本测试）。

```bash
python3 tests/parity_test.py              # 默认用 tools/ 下全部 PE 作样本
python3 tests/parity_test.py some.dll     # 指定单个文件
```

> .NET 的 WinForms GUI 版（`src/dotnet/PeView`）依赖 Windows 运行时，无法在 Linux 编译；用于一致性验证的是同目录的**无头控制台版** `src/dotnet/PeInfo`（纯 `net10.0`，无 GUI）。PowerShell 版 `-Json` 模式、VBA 版 `PeInfoJson()` 同理需 Windows 运行时验证。
> VBA 解析偏移已用 Python 复刻并对照 Python 版验证：对 `tools/` 下 4 个样本（PE32+ x64 ×3 + PE32 x86），VBA 口径与 Python 实现核心字段完全一致（详见 `src/vba/PEInfo/VBA_README.md`）。
> 修复记录：早期 Python 版对 PE32+ 的数据目录偏移误用 `opt+96`（应为 `opt+112`）；C 版结构体曾用 `unsigned long` 导致本机 Linux 下尺寸错位——均已修正，六版现已在 PE32 / PE32+ 样本上完全对齐。

## PowerShell 优化脚本（src/powershell/Optimize-Windows10.ps1）

将《Windows 10 整体优化方案》与《磁盘优化方案》落地为可执行动作，支持三段式工作流：

```powershell
# 以管理员身份运行 PowerShell
.\Optimize-Windows10.ps1 -WhatIf    # 仅检测当前状态（默认）
.\Optimize-Windows10.ps1 -Apply      # 应用优化，并将原始值写入 rollback.json
.\Optimize-Windows10.ps1 -Rollback   # 读取 rollback.json 一键还原
```

覆盖电源计划（高性能/卓越性能）、视觉性能、传递优化（限局域网）、遥测降级、SysMain、存储感知、游戏模式；系统[红线]组件（Defender / Update / 防火墙）不关闭。每项均记录回退点，遵循"一次只改一项、可回退优先"。

## Python PE 解析器（src/python/pe_inspect.py）

纯标准库（无 `pefile` 依赖）实现 PE 结构解析，对应 `docs/pe_format_doc.html` 与 C 版 `peinfo`：

```bash
python3 src/python/pe_inspect.py tools/peinfo.exe        # 解析 PE 头与节表
python3 src/python/pe_inspect.py tools/peinfo.exe -v     # 含 16 项数据目录与节特征位
python3 src/python/pe_inspect.py tools/peinfo.exe --json # 输出机器可读 JSON（供一致性测试/自动化）
```

## 稳定版 / LTS 语言策略

所有子项目固定在「稳定版或长期支持版」，用工具链清单固化，**避免频繁重写**：

- **Python 3.14** / **Rust stable（edition 2021，MSRV 1.74）** / **PowerShell 5.1（兼容 7.6 LTS）** / **C11/C17** / **.NET 10 LTS** / **Java 25 LTS** / **Ruby 3.5** / **Qt 6.12 LTS（PySide6）**
- 锁定方式：根目录 `.tool-versions` + 各 `Cargo.toml` 的 `rust-version` + `rust-toolchain.toml` + `.csproj` 的 `TargetFramework` + Java 用 `javac --release 25`（字节码级别固化，目标 OpenJDK 25 LTS；`tests/parity_test.py` 的 `build_java()` 会自动回退到本机可用版本以完成本地验证，无需手动降级）+ Ruby 用解释器直接运行（无构建文件）+ Qt GUI 用 PySide6 绑定 Qt 6.12 LTS（解析复用 `pe_inspect.py`）
- 升级纪律：跨大版本走独立 `feature/upgrade-*` 分支，验证后再合并，绝不在 `main` 直接改

详见 [`VERSIONS.md`](VERSIONS.md)。

## 多种 Windows GUI 的 PE Viewer

同一个 PE Viewer 用**多种 GUI 路线**实现，便于对比选型（原生 / 托管 / 脚本）：

| 路线 | 语言 | 目录 | 验证 |
|---|---|---|---|
| Win32 API（原生，零依赖） | C11 | `src/c/win32_gui/` | ✅ mingw 交叉编译 |
| tkinter（标准库） | Python 3.14 | `src/python/gui_peview.py` | ✅ 语法 + 解析实跑 |
| egui（原生 Rust） | Rust stable | `src/rust/peview-egui/` | ✅ `cargo check` |
| WinForms（PowerShell） | PowerShell 5.1 | `src/powershell/PEInfo-Gui.ps1` | ⚠️ 需 Windows 运行（支持 `-Json` 无 GUI 输出） |
| WinForms（.NET 10 LTS） | C# | `src/dotnet/PeView/` | ⚠️ 参考实现 |
| 控制台（无头，纯 net10.0） | C# | `src/dotnet/PeInfo/` | ✅ dotnet 10 编译 + 一致性测试 |
| Qt（PySide6，跨平台） | Python 3.14 + Qt 6.12 LTS | `src/python/peview_qt.py` | ✅ 复用 pe_inspect 解析；offscreen 冒烟通过 |

完整对照、扩展路线（WPF / WinUI 3 / Avalonia / Tauri）与选型建议见 [`GUI_MATRIX.md`](GUI_MATRIX.md)。

## Rust 子项目

- `src/rust/peinfo`：纯标准库 PE 解析 CLI，edition 2021、**零第三方依赖**，构建可复现、永不过期。
- `src/rust/peview-egui`：egui 原生 GUI，仅依赖 `eframe 0.29`（版本已固定）。

构建示例（在各子目录内执行）：

```bash
cd src/rust/peinfo
rustup target add x86_64-pc-windows-gnu
cargo build --release --target x86_64-pc-windows-gnu   # 产出 Windows PE
```

## 推送到 GitHub

仓库对应 GitHub 上的 `cyrushmh/wordbuddy-github`（**private 私有仓库，外部不可见、无法 fork**，便于个人保存与协作增删修补）。推送需要一个具备写权限的 PAT：

```bash
bash push-to-github.sh <你的 GitHub PAT>
# 或 TOKEN=<PAT> bash push-to-github.sh
```

脚本会自动完成：令牌校验 → 仓库存在性检查（不存在则建仓）→ **写权限预检**（读 API 的 `permissions.push` 位，能提前发现权限不足，避免推到一半失败）→ 推送 `main` → 按需要设为 private。

令牌要求（二选一）：

- **经典 PAT**：勾 `repo` 作用域（推荐，最省事）
- **细粒度 PAT**：Repository access = All repositories，且 Contents = Read and write

## 贡献

欢迎通过 Pull Request 参与增删修补：文档修订、优化条目补充、工具增强均可。请保持"一次只改一项、可回退优先"的执行原则。

## 资料来源

- 《Windows Internals, 7th Edition, Part 1》（资料库节点 `GLVCPGSSHEBmgcBFIn3JKs`）的镜像加载 / I/O / 进程 / 内存机理章节。
- 配套资料库页面：磁盘方案 `HqSPtdTwQ57sR2hZYaJUbl`、Win10 方案 `u4B6T95LH556y75cf5kCVA`、PE 文档 `7r9CsxMK3Odq58ZbJ9LZ1s`。

## 使用纪律

本仓库仅用于学习与系统排障；所有优化动作请遵守"一次只改一项、可回退优先"的执行原则。
