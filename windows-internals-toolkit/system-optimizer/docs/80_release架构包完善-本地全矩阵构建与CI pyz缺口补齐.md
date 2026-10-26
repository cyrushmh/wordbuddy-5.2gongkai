# 80 release 架构包完善（#662）：本地全矩阵构建 + CI pyz 缺口补齐 + 资产矩阵登记

> **任务**：#662 release 架构包完善——排查现有 release 打包脚本/CI，补全缺失架构（macOS darwin、Linux arm64 等）的包，构建并登记。
> **实测日期**：2026-10-25（沙箱 Ubuntu 22.04 声明 / 实测 noble 24.04.3 / root / x86_64；go 1.27.3 / rustc 1.93.0 / python 3.11.17）。
> **诚实边界**：本轮所有「构建」均指**本机交叉编译产出目标机器码**（file 校验架构正确），不声称在任何目标硬件上实跑（darwin/Windows 二进制无宿主机可执行；linux 非原生架构未逐一 qemu 实跑——qemu 验收口径见 docs/57 与 catalog target_matrix）。CI 改动未经 GitHub Actions 实跑（沙箱无 runner），以 YAML 语法校验 + 本地等价命令实跑替代。

## 一、调研结论：三方对账（CI 矩阵 × syspkg targets × 宿主工具链）

| 维度 | CI（`.github/workflows/build.yml` 外层 + 内层两份） | syspkg targets | 宿主工具链 | 结论 |
|---|---|---|---|---|
| Python noarch | sdist + wheel（**缺 .pyz**） | pyz/wheel/sdist | python3 stdlib zipapp | **缺口：docs/37 首推的 .pyz 从未进 CI/Release** |
| Go ×7（linux amd64/arm64/riscv64、windows amd64/arm64、darwin arm64/amd64） | ✓ 完整 7 矩阵（含 darwin） | ✓ 同 7 目标 | go 1.27.3 在场 | 无缺口 |
| Rust-native（peinfo + peview-egui） | ✗ 不在 CI | ✓ | rustc 1.93.0 + cargo registry 缓存 encoding_rs-0.8.42（可离线） | CI 缺项（本地可构建，登记备补） |
| classics-rs ×10（Linux 7 架构 + Windows×2 + WASM） | ✓ build-rs.sh（apt 装 6 交叉 gcc + mingw） | —（独立脚本） | 10 rustup targets + 6 交叉 gcc 全在场 | 无缺口（上游不可能两项如实缺席） |
| Windows PE 家族（C/Rust/.NET/Java/PowerShell…） | Windows 侧独立 workflow | — | mingw x86_64/i686 在场 | **缺口：aarch64-w64-mingw32-gcc 缺席** |
| Android APK ×4 ABI | build-android.yml 存在 | android ×4 ABI | NDK r26d 在场 | APK 可构建；**设备端审计因 adb 缺席跳过**（syspkg 如实 SKIP） |

**本轮实际改动只有两处**（其余为构建验证与登记）：① 两个 build.yml 的 build-python 补 `.pyz` 构建 + 冒烟步；② toolchain_catalog.json 登记资产矩阵与缺口。syspkg 目标矩阵、go/rust 交叉矩阵本身已完备——「补全缺失架构」的实质缺口是 **pyz 未上 CI** 与 **Windows ARM64 工具链**（后者本环境不可建，见 §五）。

## 二、本地全矩阵构建（2026-10-25 实跑）

### 2.1 syspkg all → 12 产物（`/tmp/dist-662`，共 44MB）

```
python3 tools/syspkg.py all --only pyz,wheel,sdist,go:linux-amd64,go:linux-arm64,\
  go:linux-riscv64,go:windows-amd64,go:windows-arm64,go:darwin-arm64,go:darwin-amd64,\
  rust-native --out /tmp/dist-662
```

| 产物 | 类型（file 实测） | SHA256 前 16 位 |
|---|---|---|
| sysweeper-…0022.20261025.pyz | python3 script executable（zipapp，15MB） | 27766a52925311ce |
| sysweeper-…0022.20261025-py3-none-any.whl | Zip（PEP 427 手写，2.7MB） | 6719c945afd460f9 |
| sysweeper-…0022.20261025.tar.gz | gzip（sdist，4.7MB） | a55c5d273d598bdb |
| sysweeper-go-linux-amd64 | ELF x86-64 静态 | 9cf4a295fb0e45fd |
| sysweeper-go-linux-arm64 | ELF aarch64 静态 | bfb65da684f17aca |
| sysweeper-go-linux-riscv64 | ELF UCB RISC-V 静态 | 17ad5dcd2f97d573 |
| sysweeper-go-windows-amd64.exe | PE32+ x86-64 | acc1acd067e77e35 |
| sysweeper-go-windows-arm64.exe | PE32+ Aarch64 | 015f193db5a19069 |
| sysweeper-go-darwin-arm64 | Mach-O arm64 | db557faf68657e4f |
| sysweeper-go-darwin-amd64 | Mach-O x86_64 | 50ea3ca5a8fc692e |
| peinfo-peinfo | ELF x86-64（Rust native） | 1509548d0f70db11 |
| peview-egui-peview-egui | ELF x86-64（Rust native，9.2MB） | 9e3b6900167a91af |

`syspkg smoke --out /tmp/dist-662`：**ok=true**（pyz 可运行、知识库未被静默吞掉，含 lowcode 低层码制抽查用例）。pyz 直接 `python3 <pyz>` 亦可启动（CLI 全量子命令列表正常输出）。

### 2.2 classics-rs build-rs.sh → 10/10 目标

x86_64/aarch64/armv7/riscv64gc/i686/powerpc64le/s390x × Linux（静态 ELF）+ x86_64/i686 × Windows GNU（PE32+/PE32）+ wasm32（WASM MVP）。file 逐一行校验通过（含 MSB 的 s390x 与 32 位 ARM EABI5）。

### 2.3 Windows/build.sh → 4 产物后于 arm64 步如实中断

按序产出 `tools/peinfo.exe`（PE32+ x64）、`peinfo32.exe`（PE32 x86）、`peview.exe`（PE32+ GUI x64）、`peinfo_rs.exe`（Rust PE32+ x64）；第 5 步 `aarch64-w64-mingw32-gcc: command not found` 中断（`set -e`）。已重建的 4 个 exe 为**已跟踪文件**的等价重建（同源同工具链，仅构建 ID 差异），验证后 `git checkout` 还原，不留二进制噪音。跨语言一致性测试（parity_test.py）未跑到——属脚本中断后的既有步骤，非本轮引入。

## 三、CI 缺口补齐：.pyz 上 CI（docs/37 首推产物）

docs/37 各系统安装方式 A 均为「从 Release 下载 `sysweeper-<版本>.pyz`，python3 直接跑」，但**两份 build.yml 的 build-python 历来只构建 sdist/wheel**——Release 资产里从来没有 .pyz，文档路径与发布现实脱节。本次给**外层** `.github/workflows/build.yml` 与**内层** `windows-internals-toolkit/.github/workflows/build.yml` 的 build-python 各补两步（置于 sdist/wheel 之后、上传之前）：

```yaml
- name: Build single-file pyz (docs/37 recommended artifact)
  run: python3 ../../tools/syspkg.py pyz --out dist
- name: Smoke test pyz (run + knowledge-base sanity)
  run: python3 ../../tools/syspkg.py smoke --out dist
```

要点：① syspkg 为纯标准库单文件，CI 无需装任何依赖，路径相对脚本自身解析（`ROOT=parents[1]`），working-directory 无关；② 上传与 Release 发布步路径均为 `dist/*`，.pyz 落盘即被天然覆盖，无需改上传配置；③ smoke 步即本地已实跑的同一命令（ok=true）；④ 两份 YAML 均过 `yaml.safe_load` 语法校验。

## 四、资产矩阵登记

- **`src/python/sysweeper/data/toolchain_catalog.json`**：
  - `repo_tools` 新增 **`release-matrix`**（packaging 类）：12 syspkg 产物 + 10 classics-rs + Windows PE 家族的资产矩阵、本地构建证据（SHA256 前 16 位）、CI 覆盖与 §五 缺口清单；
  - `ci-workflows` 条目刷新：build-python 由「sdist/wheel」改「sdist/wheel + **pyz + smoke**」（两份 build.yml 同口径）；
  - `syspkg` 条目 verify 刷新：三形态 + pyz 冒烟 + 已上 CI；
  - `target_matrix` 新增 19 行：go ×7、classics-rs ×10、Python noarch ×1、Windows ARM64（aarch64-w64-mingw32，**不可构建**标注行）。
- **README** `## 版本更新` 新增 0023 块（本目录文档编号顺延为 docs/80）。

## 五、诚实缺口（needs_action，不臆造可构建性）

| 缺口 | 根因（实测） | 处置 |
|---|---|---|
| Windows ARM64 · C（`aarch64-w64-mingw32-gcc`） | Ubuntu apt 无 mingw aarch64 包（`gcc-mingw-w64*` 仅 i686/x86_64 两族，`apt-cache search` 实证 65 个 mingw 包无一 aarch64） | go-windows-arm64 已覆盖该架构（CI 矩阵 + 本地构建）；C/Rust 侧挂 needs_action |
| Windows ARM64 · Rust（`aarch64-pc-windows-gnu`） | rustc target-list 无此项；变体 `aarch64-pc-windows-gnullvm` 在列但 rust-std 组件下载在本环境停滞（`~/.rustup/downloads/*.partial` 12.9MB 不再增长；`curl` 直下 rust-std tarball 240s 超时——static.rust-lang.org 大文件传输被断，HEAD 小请求正常） | 挂 needs_action；网络可达环境执行 `rustup target add aarch64-pc-windows-gnullvm` 后可补（build-rs.sh 头注释已预告该目标性质） |
| classics-rs · aarch64-pc-windows-gnu | 上游 rustc 不提供该 target（target-list 实证） | 上游不可能，长期缺席（.cargo/config.toml 头注释已记） |
| classics-rs · `*-apple-darwin` | 无 macOS SDK（osxcross 未安装） | 上游不可能，长期缺席；darwin 用户侧由 go-darwin ×2 + pyz 覆盖 |
| Android APK 上 CI / 设备端审计 | APK 可构建但 build-android 之外无 release 打包路径；adb 缺席（syspkg `android-audit` 如实 SKIP） | 挂 needs_action（SDK 需网络，CI 化属另一轮） |

## 六、验证

- 两个 build.yml：`yaml.safe_load` 通过；
- 本地全矩阵：syspkg 12 产物 file 校验 + smoke ok=true；classics-rs 10/10；Windows 4 产物后如实中断；
- toolchain_catalog.json：`tests/test_toolchain.py` 定向（结构契约：repo_tools 必填字段、类别合法、target_matrix ≥10）+ 全量 pytest 零回归；
- 工作树：除两份 workflow 与 catalog/docs/README 外无杂散变更（重建 exe 已还原、dist 产物不入库）。
