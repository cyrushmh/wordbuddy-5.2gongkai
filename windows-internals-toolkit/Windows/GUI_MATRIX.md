# 多种 Windows GUI 方案对照（同一 PE Viewer 的实现）

> 用户要求「GUI 可以尝试多种，比如 Windows 环境的」。下面用**同一个 PE Viewer** 演示不同 GUI 路线，
> 每一条都在仓库里有对应可运行/可编译代码，便于对比选型。

## 已实现（代码已入库）

| 路线 | 语言 | 目录 | 依赖 | 验证状态 |
|---|---|---|---|---|
| **Win32 API** | C11 | `src/c/win32_gui/` | 无（系统 API） | ✅ mingw 交叉编译通过 |
| **tkinter** | Python 3.14 | `src/python/gui_peview.py` | 标准库 | ✅ 语法校验通过 |
| **egui** | Rust stable | `src/rust/peview-egui/` | eframe 0.29 | ✅ `cargo check` 通过 |
| **WinForms** | PowerShell 5.1 | `src/powershell/PEInfo-Gui.ps1` | .NET Framework（系统自带） | ⚠️ 需在 Windows 运行 |
| **WinForms** | C# / .NET 10 LTS | `src/dotnet/PeView/` | .NET 10 SDK | ⚠️ 参考实现，需 Windows `dotnet build` |
| **Office VBA** | VBA（宏） | `src/vba/PEInfo/` | Office（系统自带） | ⚠️ 需 Windows/Mac Office；解析口径已验证 |
| **无头控制台** | Java 25 LTS | `src/java/peinfo/` | JDK 标准库（纯） | ✅ javac 编译 + 一致性测试（Linux 可验证） |
| **Qt (PySide6)** | Python 3.14 + Qt 6.12 LTS | `src/python/peview_qt.py` | PySide6（Qt 官方绑定） | ✅ 复用 pe_inspect 解析；offscreen 冒烟通过（跨平台） |

## 还可扩展（未写代码，作为路线参考）

| 路线 | 语言 | 特点 | 何时选 |
|---|---|---|---|
| **WPF / XAML** | C# / .NET 8 | MVVM、矢量渲染、现代样式 | 需要复杂布局/动画的企业内工具 |
| **Windows App SDK / WinUI 3** | C# | 最新 Fluent 设计、Win11 原生 | 面向 Win11 的新应用 |
| **Qt / PySide6** | Python/C++ | 跨平台一致、控件丰富 | 既要 Windows 又要 Linux/macOS 一套代码 |
| **Avalonia** | C# | 跨平台 XAML、.NET 生态 | 想用 XAML 但跨平台 |
| **Tauri** | Rust + WebView2 | 前端写 UI、Rust 写逻辑，体积小 | Web 技术栈团队 |

## 选型建议（按场景）

- **最小体积 / 免依赖**：Win32 API（C）—— 单文件 exe，无运行时。
- **最快出活 / 运维脚本**：PowerShell WinForms —— 不用编译，改完即跑。
- **跨平台一致 + Python 生态**：tkinter 或 PySide6。
- **现代原生 + Rust 安全**：egui（本仓库已演示）。
- **企业级托管应用**：.NET 8 WinForms / WPF / WinUI 3（LTS 长支持）。
- **嵌入 Office 自动化 / 不离开 Excel**：Office VBA（宏）——结果输出到立即窗口/单元格/旁挂 .json，零安装。

> 所有 GUI 复用的解析逻辑与 `docs/pe_format_doc.html` 的字段表一致，避免「界面一套、文档一套」。
