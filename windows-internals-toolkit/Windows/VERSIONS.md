# 语言与运行时版本策略（稳定版 / LTS）

> 目标：**锁版本、可复现、少重写**。所有子项目都固定在「稳定版或长期支持版」，
> 用工具链清单固化，避免半年后依赖漂移导致重写。

## 总原则

1. **只进稳定通道**：不用 nightly、不用 beta、不用 `latest` 浮动标签。
2. **锁定可复现**：Rust 用 `Cargo.lock` + `rust-toolchain.toml`；跨语言用根目录 `.tool-versions`（asdf）集中记录版本。
3. **最小依赖**：能用标准库就不引第三方；Rust CLI/GUI 纯标准库，无外源依赖，永不过期。
4. **跨版本兼容**：PowerShell 脚本仅用 5.1（Win10 内置）即可运行的语法；Python 仅用 3.8+ 通用写法。

## 各语言固定版本

| 语言 / 运行时 | 固定版本 | 性质 | 锁定方式 | 备注 |
|---|---|---|---|---|
| Python | **3.14** | 稳定发行版（最新稳定版；3.8+ 语法通用，3.11 仍在维护期内） | `.tool-versions` | 标准库工具无需任何第三方包 |
| Rust | **stable 通道 / edition 2021 / MSRV 1.74** | 稳定 | `rust-toolchain.toml` + `Cargo.toml: rust-version` | 自动锁定 Cargo.lock，构建可复现 |
| PowerShell | **5.1（Win10 内置）兼容，7.6 LTS 验证** | LTS | 脚本内 `#requires -Version 5.1` | 不依赖 7.x 专属 cmdlet |
| C | **C11 / C17（ISO/IEC 9899:2011/2018）** | 标准 | 编译器 GCC 13（mingw-w64） | 纯标准库，跨平台可编译 |
| .NET | **.NET 10 LTS** | LTS | `*.csproj: TargetFramework=net10.0` | 无头控制台版（PeInfo）与 WinForms GUI 版（PeView）统一 net10.0 |
| Java | **25 LTS** | LTS | `javac --release 25`（字节码级别固化） | 纯标准库，无构建/依赖文件，跨平台（Linux）可验证 |
| Ruby | **3.5 稳定版** | 稳定发行版 | `ruby` 解释器直接运行（无构建文件） | 纯标准库，零依赖，跨平台可验证 |
| Qt（GUI） | **6.12 LTS** | LTS | `PySide6`（Qt 官方 Python 绑定）+ 解析复用 `pe_inspect.py` | 跨平台一致；GUI 需 Qt 运行时（pip 安装 PySide6：当前 6.11.2 / Qt 6.11；Qt 6.12 LTS 的 PySide6 wheels 待官方发布，届时直接升级即可） |

## 锁定文件清单

```
.tool-versions                  # asdf：python 3.14 / rust 1.93.0 / dotnet 10.0 / java 25 / ruby 3.5
src/rust/peinfo/rust-toolchain.toml   # channel = "stable"，锁定 Rust 工具链
src/rust/peinfo/Cargo.toml           # edition = "2021", rust-version = "1.74"
src/rust/peview-egui/rust-toolchain.toml
src/rust/peview-egui/Cargo.toml      # edition 2021，依赖固定到具体版本
src/dotnet/PeView/PeView.csproj      # TargetFramework = net10.0-windows
```

## 升级纪律

- 跨大版本升级（如 Rust edition 2024、Python 3.12）走独立 `feature/upgrade-*` 分支，
  验证通过后再合并，**绝不在 main 直接改大版本**。
- 第三方依赖升级用 `cargo update -p <crate> --precise <ver>` 定点升级，不一次性全飘。
- 所有升级都跑一遍对应子项目的构建/校验脚本后再提交。

> 这套策略落实了用户要求：**语言用稳定版或长期支持版，就不用频繁重写代码**。
