# 打包与分发策略（因地制宜 · 各自规范 · 兼容层）

本仓库是一个**多平台 monorepo**。`classics-*` 与 `windows-internals-toolkit` 各自独立打包、
按目标系统与发行版的原生规范产出，互不耦合。本文把「软件包和打包根据各自系统与文件系统，
需要因地制宜、分段讨论、分别应用；共同的需要集合、集合的分别应用；除非类似安装了相同兼容层，
或默认应用概念整体组网的自身兼容层」落为可执行规范。

---

## 1. 总原则

| 原则 | 含义 | 落到本仓库 |
|------|------|-----------|
| **因地制宜** | 打包按目标系统与文件系统各自形态，不套一个万能模板 | 每个子项目用各自构建系统（Gradle/Cargo/debian+PKGBUILD/SwiftPM/Xcode/pip） |
| **分段讨论、分别应用** | 按平台/发行版分段设计，分别落地 | `classics-linux` 同时维护 `debian/`（Debian 系）与 `PKGBUILD`（Arch 系）两套元数据 |
| **共同的需要集合、集合的分别应用** | 跨平台的共性需求先聚合成一份「集合」，再各自取用 | 概念整体组网（sysweeper 九系统知识库 + CLI）是唯一跨平台共性层，各端按需消费 |
| **兼容层** | 未装相同兼容层时，默认用「概念整体组网」自身兼容层 | sysweeper `.pyz` 零依赖、任意 `python3` 可跑，是各端的默认兼容底座 |
| **各自规范与目录结构** | 每个系统/发行版必须遵循自身规范、文件系统、目录结构 | Debian 用 `debian/`(control/rules/changelog)，Arch 用 `PKGBUILD`，Rust 用 `Cargo.toml`，不混淆 |
| **按硬件优化、共性处置相近** | 按目标架构/硬件调构建参数；共性（hardening/UTF-8/零依赖）统一口径 | Arch `arch=('x86_64' 'aarch64' 'riscv64')`；Debian 用 `DEB_HOST_GNU_TYPE` 交叉；hardening 标志一套口径 |

---

## 2. 各自系统与发行版：原生规范对照

| 子项目 | 目标系统/发行版 | 原生构建系统 | 原生目录/文件 | 兼容层取用 |
|--------|---------------|------------|--------------|-----------|
| `classics-harmony-app` | HarmonyOS（鸿蒙） | DevEco / ArkTS 构建 | `AppScope/ entry/ tests/` | 经 config/桥接引用知识库 |
| `classics-ios-mac` | iOS / macOS（Apple） | Xcode / SwiftPM | `Apps/ Sources/` | 同上 |
| `classics-linux` | Linux（Debian/Ubuntu + Arch） | `Makefile` + `dpkg-buildpackage` + `makepkg` | `debian/` `PKGBUILD` `arch-out/` | 同上 |
| `classics-rs` | 跨平台（Rust 运行时 + WASM） | Cargo / crates | `Cargo.toml` `bindings/` `wasm/` `target/` | 同上 |
| `classics-swift-linux` | Linux（SwiftPM） | `swift build` / SwiftPM | `Sources/ .build/` | 同上 |
| `windows-internals-toolkit/android` | Android（API 26–34） | Gradle (AGP) | `build.gradle.kts` `gradlew` `gradle-wrapper.jar` | 同上 |
| `windows-internals-toolkit/system-optimizer` | 任意带 `python3` 的机器 | `zipapp`(pyz) + 手写 wheel/sdist | `pyproject.toml` `tools/syspkg.py` `dist/` | 自身即兼容层 |
| `windows-internals-toolkit/Windows` | Windows（原生） | MSBuild / 原生工具链 | `Windows/.github/workflows/build.yml` | 同上 |
| `windows-internals-toolkit/novel-website` | Web（Node 运行时） | npm / 静态站点 | `package.json` | 同上 |

**关键事实**：`classics-linux` 是「因地制宜」的范本——
同一份 C 源码，Debian 侧走 `debian/control`+`rules`+`changelog`，Arch 侧走 `PKGBUILD`
（拆分包 `classics` + `classics-data`，`classics-data` 覆盖 `arch=('any')`），
`Makefile` 用 `$(wildcard /usr/share/dpkg/*.mk)` 探测：Debian 系注入 `dpkg-buildflags`
hardening 默认值，非 Debian 系退化为手写安全默认（`-D_FORTIFY_SOURCE=3` 等），行为不崩。
`PKGBUILD` 注释里显式列出 Arch↔Debian 元数据一一对照（pkgver/pkgrel↔changelog、
arch↔Architecture、depends↔Depends、makepkg↔dpkg-buildpackage、.pkg.tar.zst↔.deb）。

---

## 3. 兼容层（默认 = 概念整体组网自身）

- **默认兼容层**：`windows-internals-toolkit/system-optimizer` 产出的
  `sysweeper-*.pyz`（zipapp，零第三方依赖，任意 `python3` 可直接跑）与 wheel/sdist。
  这是全仓库唯一的「共同需要集合」载体：九系统概念知识库 + 只读审计 CLI
  （`audit_concepts.py` / `check_concept_mesh.py`）。
- **集合的分别应用**：各端不直接复制知识库，而是按自身规范引用/内嵌 `.pyz`：
  鸿蒙/Apple/Swift/Web/Rust/Windows 侧通过各自的桥接或构建步骤消费，
  不把概念 JSON 拷进各自源码树。
- **相同兼容层优先复用**：若某几个目标系统已装同一运行时（如都带 `python3`），
  直接共用同一份 `.pyz`，不各打一份；仅当目标系统无该运行时（纯 WASM / 原生二进制）
  才各自产出对应工件（`.wasm` / 各架构二进制）。

---

## 4. 目录与命名（重构约定）

- **顶层命名一致性**：除 `windows-internals-toolkit` 外，各端目录统一 `classics-<平台>`。
  `windows-internals-toolkit` 因被全部 CI 路径（`windows-internals-toolkit/android/**` 等）
  与 `pyproject`/导入路径强引用，**重命名需协调迁移**（改 CI `paths`、导入根、Release 归档路径），
  属高影响操作，单列迁移任务，不在日常重构中顺手改。
- **子项目自包含**：每个子项目自带 `.gitignore`（根 `.gitignore` 只覆盖 monorepo 总览与通用噪声），
  临时构建产物按各自规范排除，不污染源码树。
- **交付件显式归档**：`classics-linux/build/*.deb` 等交付包经 `force-add` 显式归档，
  根 `.gitignore` 已声明「根级 `*.deb` 一律忽略，交付用归档在子项目 `build/` 下」，二者口径一致。

---

## 5. 按硬件优化（共性处置相近）

- **架构矩阵**：Arch 侧 `arch=('x86_64' 'aarch64' 'riscv64')`，`classics-data` 覆盖 `any`；
  Debian 侧 `DEB_HOST_GNU_TYPE` 自动选原生/交叉编译器（原生 `x86_64-linux-gnu-gcc`
  与交叉 `aarch64-linux-gnu-gcc` 同套代码）。
- **通用硬件优化口径（各端一致）**：
  - UTF-8 优先、GB18030 回退，绝不假装解码成功（经典文本严格性）；
  - 构建期 hardening 一套口径（`-D_FORTIFY_SOURCE=3` / `-fstack-protector-strong` /
    `-fcf-protection` / `-Wl,-z,relro -z,now` / LTO），Debian 系经 `dpkg-buildflags`、
    非 Debian 系手写对齐；
  - 零第三方依赖优先（Python 层零依赖 → 单文件 `.pyz` 任意机器可跑）；
  - 平台字节序/对齐/路径分隔按各自文件系统规范处理，不假设。

---

## 6. CI 护栏（与打包同生命周期）

| 工作流 | 守护对象 |
|--------|---------|
| `build-android.yml` | Android APK（按 ABI 拆分 + 通用包），gradle wrapper 须为官方发行包 |
| `build-python.yml` | 语言底层 `.pyz` + wheel/sdist，跨 Linux/macOS/Windows 同一份验证 |
| `build-harmony.yml` | 鸿蒙 App 构建 |
| `audit-standards-eol.yml` | 标准库 EOL 审计 |
| **`audit-concepts.yml`** | **概念整体组网护栏**：`audit_concepts.py --strict` + `check_concept_mesh.py --strict`，保证九系统始终连通为单一整体、零悬空桥** |

> 打包改动与概念组网改动共用同一套「提交前门禁全绿」纪律：任何一端打包或知识层变更，
> 都先过各自构建 + 概念体检，再合入 main。
