# 08 · Swift-on-Linux 与 Arch 打包：跨工具链落地

本轮把一批外部资料（Xcode-on-Linux 系列、Arch Wiki 打包与 man page 规范、编译原理实验文档、Arch 安装指南）**读完后落到代码与包上**，并在落地过程中发现并修复了两个真实缺陷。

---

## 一、资料调研结论（先看懂，再动手）

### 1.1 Xcode 能否在 Linux 上跑？——不能，但 Swift 可以

| 说法 | 结论 |
|---|---|
| 「在 Linux 装 Xcode」 | **不可行**。Xcode 是 macOS 闭源 IDE，深度依赖 Cocoa / AppKit / CoreServices，且许可协议限制在 Apple 硬件上运行。各类教程的实质是「装个替代品」或「用虚拟机 / 远程 Mac」，并非原生 |
| 「在 Linux 开发 Swift」 | **完全可行**。Apple 开源的 Swift 工具链（swift.org 提供 Ubuntu / RHEL / 等发行版 tarball）原生支持 Linux，可编译命令行程序、服务端程序与 SwiftPM 包 |

**这对本项目的直接价值**：`classics-ios-mac` 的 Swift 源码此前只能在 Apple 平台编译。既然 Swift 是跨平台的语言，那么**不含 SwiftUI / AppKit 的纯逻辑层就可以原样搬到 Linux**——不必用 Rust 或 C 重写，直接复用。

> 关于编译原理实验文档（BUAA）与 Arch 安装指南：前者印证了「工具链 = 前端 + 优化 + 后端 + 目标平台」的分层——本项目正是靠这一分层，让**同一份 Swift 源码**在 Apple 与 Linux 两种后端上产出；后者为 Arch 包的目录约定提供了实操侧印证。

### 1.2 Arch PKGBUILD 规范要点（对照 Debian 侧）

| Arch | Debian | 说明 |
|---|---|---|
| `pkgver` / `pkgrel` | `debian/changelog` 的版本与发行号 | Arch 的 `pkgver` 禁止含连字符 |
| `arch=('x86_64' 'aarch64')` | `Architecture:` + `dpkg-buildpackage -a` | 数组显式声明支持的硬件 |
| `depends=()` | `Depends:` | 运行时依赖 |
| `build()` | `override_dh_auto_build` | 编译阶段 |
| `package()` + `$pkgdir` | `override_dh_auto_install` + `$DESTDIR` | 安装到暂存根 |
| `/usr/share/licenses/<pkg>/` | `debian/copyright`（DEP-5） | 许可证落点 |
| `.PKGINFO`（包内） | `control`（包内） | 包元数据 |
| `makepkg -s` | `dpkg-buildpackage -us -uc -b` | 构建命令 |
| `.pkg.tar.zst` | `.deb` | 产物格式 |

**Man page 规范**：章节 1 为可执行程序（`man 1 classics`）；Arch 的 `makepkg` 会自动对 `/usr/share/man/man1/*.1` 做 gzip 压缩，与 Debian 的 `dh_installman` 行为一致。

---

## 二、落地一：Swift 工具链在 Linux 上编译本项目

### 2.1 工具链

```
Swift 6.4.1 (swift-6.4.1-RELEASE)   Target: x86_64-unknown-linux-gnu
下载 swift-6.4.1-RELEASE-ubuntu24.04.tar.gz（1.1 GB）→ 解压至 /opt/swift
```

### 2.2 抽取可移植核心

扫描 `classics-ios-mac/Sources/` 后，4 个文件**只依赖 Foundation**、不含任何 SwiftUI / AppKit / Combine，可直接搬：

| 文件 | 职责 |
|---|---|
| `TextEncoding.swift` | 编码安全解码（项目主线） |
| `ClassicsModels.swift` | 数据契约（与 ArkTS 端镜像） |
| `ClassicsData.swift` | 典籍数据（含参同契 92 条） |
| `BookShelf.swift` | 分组排序器 |

新建 `classics-swift-linux/`（SwiftPM 包：库 `ClassicsCore` + 可执行 `classics`），核心文件**从 iOS 端同源拷贝**，保证数据契约不漂移。

### 2.3 平台适配层（必须解决的分叉）

iOS 版用 `CFStringConvertEncodingToNSStringEncoding` 取 GB18030 编码表。实测 **Linux 的 swift-corelibs-foundation 不提供该 API**，直接编译报 `cannot find 'CFStringConvertEncodingToNSStringEncoding' in scope`。

解法是给**共享的 `TextEncoding.swift`** 加条件编译——一份文件两端共用，Apple 平台行为完全不变：

```swift
#if canImport(Glibc)
import Glibc
#endif

// 第 3 步：严格 GB18030
#if canImport(Glibc)
        if let s = decodeGB18030ViaIconv(data) { return s }   // Linux：glibc iconv
#else
        let cfEnc = CFStringConvertEncodingToNSStringEncoding(   // Apple：CFString 编码表
            CFStringEncoding(CFStringEncodings.GB_18030_2000.rawValue))
        if let s = String(data: data, encoding: String.Encoding(rawValue: cfEnc)) { return s }
#endif
```

Linux 分支用 glibc `iconv` 实现，并恪守**严格**语义：任一字节无法映射即整体返回 `nil`，落回第 4 步有损兜底——与 CoreFoundation 的 `String(data:encoding:)` 行为对齐，不做半途替换。

> 踩坑：`iconv_open` 在 Swift 中返回 `iconv_t`（即 `UnsafeMutableRawPointer`），**不需要** `OpaquePointer` 转换；`iconv()` 返回 `size_t`，失败值是 `UInt.max` 而非 `-1`。

### 2.4 验证

```
swift build -c release   →  Build complete! (3.09 secs)

classics list            →  5 部典籍 / 95 章，按分类分组、组内按朝代时序
classics show cantongqi  →  《周易参同契》92 章（与 ArkTS 端数据一致）
classics decode 纯GBK    →  道德经：道可道，非常道。   （判定 gb18030）
classics lint   混合编码  →  检出乱码指纹，疑似编码错配
```

---

## 三、落地二：Arch Linux 三架构包

### 3.1 先修一个可移植性缺陷

`classics-linux/Makefile` 原样 `include /usr/share/dpkg/architecture.mk` —— **Arch 上没有这个文件，会直接构建失败**。改为 `wildcard` 探测后再 include：

```make
DPKG_MK := $(wildcard /usr/share/dpkg/architecture.mk)
ifneq ($(DPKG_MK),)
  # Debian 系：走 dpkg-buildflags 的全套 hardening
else
  # 非 Debian 系：手写等价安全默认
  CC       ?= cc
  CPPFLAGS ?= -D_FORTIFY_SOURCE=3
  CFLAGS   ?= -O2 -Wall -Wextra -fstack-protector-strong -fstack-clash-protection
  LDFLAGS  ?= -Wl,-z,relro -Wl,-z,now
endif
```

两个分支均已实跑验证：Debian 分支照旧产出全套 hardening，Arch 分支产出等价加固的 ELF。

### 3.2 PKGBUILD 与产物

`classics-linux/PKGBUILD` 按 Guidelines 编写：`arch=('x86_64' 'aarch64' 'riscv64')`、`depends=('glibc')`、man 装 `/usr/share/man/man1/`、许可证装 `/usr/share/licenses/classics/`。

本沙箱是 Ubuntu（无 `makepkg`），故 `build-arch.sh` **严格复刻 makepkg 流程**（生成源码归档 → `build()` → `package()` 到 `$pkgdir` → 写 `.PKGINFO` → zstd 打包），产物可被任何 Arch 系统的 `pacman -U` 安装。

| 产物 | 架构 | ELF 实测 | 体积 |
|---|---|---|---|
| `classics-1.0.0-1-x86_64.pkg.tar.zst` | x86-64 | ELF 64-bit LSB pie, x86-64 | 9.3K |
| `classics-1.0.0-1-aarch64.pkg.tar.zst` | ARM64 | ELF 64-bit LSB pie, ARM aarch64 | 9.5K |
| `classics-1.0.0-1-riscv64.pkg.tar.zst` | RISC-V | ELF 64-bit LSB pie, UCB RISC-V | 9.4K |

三包均含 `.PKGINFO`（pkgname/pkgver/arch/license/depend 齐全）、`classics.1.gz`（man 已按 Arch 惯例压缩）、`LICENSE`、示例典籍数据。

---

## 四、落地过程中发现并修复的两个真实缺陷

### 4.1 严格 GB18030 会「成功」却产出乱码 —— 指纹漏检

构造一个混合编码文件（前段 GBK 字节 + 后段 UTF-8 中文「测试」），三份实现都**一致地**解码出：

```
中国GBK娴嬭瘯        ← 「测试」被误读为「娴嬭瘯」，典型古文码
```

问题在于：GB18030 几乎能映射任意字节序列，所以**解码「成功」、不报错**，乱码堂而皇之地通过了检查——而原有指纹表（锟斤拷 / 烫烫烫 / □□□ 等）**一条都没命中**。这正是项目要防的场景，却漏了。

**修复**：新增「GBK 误读 UTF-8 连续产物字」启发式。这些字（娴、嬭、瘯、噭、浣、犲、ソ、鐢、湀、銆、垚、畾…）本身合法，但极少在正常中文里**彼此相邻**，故要求连续 ≥2 个才判定，避免误伤「拷问」「涓涓」这类正常用词。

已同步到 **Swift 端**（`TextEncoding.swift`，三端共用）与 **Rust 端**（`detect_mojibake` 新增 `MojibakeKind::GbkMisreadRun`，附 2 个单元测试）。实测：

| 样本 | 期望 | Swift | Rust |
|---|---|---|---|
| 混合编码（含「娴嬭瘯」） | 检出 | 检出 | 检出 |
| 纯 GBK | 无误报 | OK | OK |
| UTF-8 正文 | 无误报 | OK | OK |
| 含「涓涓」「拷问」的正常中文 | 无误报 | OK | OK |

> **C 版待办**：`classics-linux` 的指纹检测跑在**原始字节**上（`count_fingerprint`），与另两端架构不同，需改为对转换后文本检测才能复用该启发式——已记入待办，未在本轮改动。

### 4.2 C/iconv 路线藏着一个运行时依赖：gconv 模块

aarch64 / riscv64 的 C 版二进制在 qemu 下对纯 GBK 文件判定「无法安全解码」，而 x86_64 判定正确——**跨架构行为不一致**，必须查清。

根因：glibc 的 `iconv` 是**运行时动态加载**转换模块的，模块位于 `/usr/lib/<triplet>/gconv/`（如 `GB18030.so`）。交叉 sysroot（`/usr/aarch64-linux-gnu/`）**不含 gconv 目录**，`iconv_open("GB18030")` 因此失败。

实证：取 arm64 的 glibc 提取 gconv 后指定 `GCONV_PATH` 重跑——

```
无 gconv  → # 判定：无法安全解码（既非 UTF-8 也非合法 GB18030）
有 gconv  → # 判定：GB18030（原始非 UTF-8，已安全转 UTF-8）
            道德经：道可道，非常道。      ← 与 x86_64 完全一致
```

**结论：二进制本身正确**，失败源于交叉 sysroot 不完整（交叉 libc-dev 包通常不含运行时转换模块）。

**但这条洞察值得记住**：

| 路线 | GB18030 从哪来 | 跨环境风险 |
|---|---|---|
| C + glibc `iconv` | 运行时动态加载 `gconv` 模块 | 目标系统/容器若裁剪掉 gconv，解码即降级 |
| Rust + `encoding_rs` | 纯 Rust 实现，静态链接进二进制 | 无运行时依赖，天然稳定（arm64/riscv64 实测均正常） |
| Swift + glibc `iconv` | 同 C 路线 | 同 C 路线的注意事项 |

若目标是精简容器、嵌入式或不确定 gconv 的环境，**优先选 Rust 内核**。

---

## 五、覆盖矩阵更新

| 系统 | 硬件 | 语言 | 状态 |
|---|---|---|---|
| iOS / macOS | Apple Silicon / x86-64 | Swift | 已有 |
| HarmonyOS NEXT | ARM64 | ArkTS | 已有 |
| Linux (Debian/Ubuntu) | amd64 / arm64 | C + Debian 包 | 已有 |
| Linux (Arch) | x86_64 / aarch64 / riscv64 | C + `.pkg.tar.zst` | **本轮新增** |
| **Linux (SwiftPM)** | **x86-64** | **Swift 6.4.1（复用 iOS 源码）** | **本轮新增** |
| Linux / Windows / Web | x86-64 / ARM64 / RISC-V / WASM | Rust | 已有（本轮修复指纹） |

---

## 六、复现命令

```bash
# Swift on Linux（需先装 Swift 工具链：https://www.swift.org/install/）
export PATH=/opt/swift/usr/bin:$PATH
cd classics-swift-linux && swift build -c release
.build/release/classics list
.build/release/classics decode <gbk文件>

# Arch 三架构包
cd classics-linux && bash build-arch.sh
# 真 Arch 上直接用：makepkg -s

# Debian 包（回归验证仍通过）
cd classics-linux && dpkg-buildpackage -us -uc -b

# Rust 全平台 + 单元测试
cd classics-rs && cargo test --release && bash build-rs.sh
```

---

## 七、待办

1. **C 版指纹检测迁移**：从原始字节检测改为对转换后文本检测，复用新增的「GBK 误读连续产物字」启发式。
2. **Swift 交叉到 ARM64**：本机 Swift 工具链仅 x86-64 target，可加装 aarch64 静态 SDK 扩展。
3. **AUR 提交**：`PKGBUILD` 的 `sha256sums` 现为 `SKIP`，正式提交前应回填真实摘要并补 `.SRCINFO`。

> 延伸参考（未深入抓取）：`github.com/EpicGames/UnrealEngine` 是超大型 C++ 跨平台项目的公开范本，其多平台构建调度（UnrealBuildTool）与本项目 `build-rs.sh` / `build-arch.sh` 的「一份源码、多目标产出」思路同构，可作为后续把构建矩阵工程化的参照。
