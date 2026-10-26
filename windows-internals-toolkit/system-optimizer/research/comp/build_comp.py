#!/usr/bin/env python3
"""编译与工具链「概念系统」构建（以 wordbuddy-github 为主目录，v0.6.74）。

把「从源码到产物」的全链路按**八轴**重组为概念系统，与 plang / netsys /
daoxue / quantum 同构（数据层 ``data/concepts/`` + 只读层 ``concepts/`` + CLI/GUI）：

    ├─ 轴1 pipeline    编译流水线（前端→中端→后端→汇编→链接：词法/语法/语义/IR/优化/
    │                  代码生成/寄存器分配/目标文件/链接）
    ├─ 轴2 toolchain   工具链家族（GNU / LLVM / MSVC / MinGW-w64 / rustc / go / JVM /
    │                  .NET / BEAM / 解释器-JIT 连续体）
    ├─ 轴3 build       构建系统（make / cmake / ninja / meson / scons / bazel /
    │                  gradle·maven / cargo·pnpm / msbuild·xcodebuild /
    │                  dockerfile·compose 容器化 / lint-gate 门禁）
    ├─ 轴4 artifact    目标产物（静态库/动态库/原生可执行/目标文件/字节码/wasm/IR/
    │                  安装包/容器镜像）
    ├─ 轴5 lang-need   语言编译需要（15 种实测语言带证据 + 其余 needs_verify）
    ├─ 轴6 reverse     黑箱逆向（UPX 壳识别/熵判据/格式解剖/GDB 调试/符号可见性/
    │                  自造样本；沙箱实测口径 + 只读边界）
    └─ 轴7 bitwidth    位宽与寻址世代（8 位/16 位实模式/32 位保护模式/PAE 物理地址
                      扩展/64 位长模式/128 位 SIMD 向量档/遗留 DOS·BusyBox 栈）
    └─ 轴8 bringup     引导与实测纪律（诊断优先引导/在役设备树探查/绝对重定位门禁/
                      宿主测试 harness/工具链安全响应时钟）

证据口径：**只有 plang probe 实测通过的 15 种语言**登记「编译需要」明细
（证据取自 ``data/concepts/plang_taxonomy.json`` 的 ``probe_results``）；
其余 146 种语言统一汇为一条 needs_verify，不逐条臆造其工具链形态。

桥接：目标必须在目标数据层真实存在（plang 语言/轴、netsys 模块、llvm_docs 工具/
目标三元组、daoxue 原则），构建期校验无悬空。

用法：
    python3 build_comp.py            # 构建 data/concepts/comp_taxonomy.json
    python3 build_comp.py --check    # 校验（轴合法、桥接无悬空、counts 自洽）
    python3 build_comp.py --report   # 打印八轴统计与桥接图
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "src" / "python" / "sysweeper" / "data" / "concepts" / "comp_taxonomy.json"
CONCEPTS_DIR = OUT.parent

SCHEMA = "comp_taxonomy/v1"

# ---- 八轴（v0.6.85 增 bringup：引导与实测纪律） ----
DOMAINS = [
    {"domain": "pipeline", "label": "编译流水线",
     "note": "源码→产物的阶段链：前端（词法/语法/语义）→中端（IR 优化）→后端"
             "（指令选择/寄存器分配）→汇编→链接"},
    {"domain": "toolchain", "label": "工具链家族",
     "note": "成套工具的组合：GNU / LLVM / MSVC / MinGW-w64 / rustc / go / JVM / .NET / BEAM"},
    {"domain": "build", "label": "构建系统",
     "note": "驱动编译与打包的编排层：make / cmake / ninja / bazel / cargo 等"},
    {"domain": "artifact", "label": "目标产物",
     "note": "产物形态：库/可执行/字节码/wasm/IR/安装包/镜像"},
    {"domain": "lang-need", "label": "语言编译需要",
     "note": "每种语言的驱动工具与产物形态：15 种实测（带证据）+ 其余 needs_verify"},
    {"domain": "reverse", "label": "黑箱逆向",
     "note": "不读源码也能看清一个可执行文件：壳识别/熵判据/格式解剖/GDB 黑箱调试/"
             "符号可见性/自造样本；全部沙箱只读实测，不碰未授权目标"},
    {"domain": "bitwidth", "label": "位宽与寻址世代",
     "note": "8 位 / 16 位实模式 / 32 位保护模式 / PAE 物理地址扩展 / 64 位长模式"
             "五档分档，加遗留 DOS·BusyBox 栈在本仓的只读落地；位宽是能力分档，"
             "不是「新=旧」的优劣判词"},
    {"domain": "bringup", "label": "引导与实测纪律",
     "note": "把运行期才炸的错误提前到构建期/引导期：诊断优先引导 / 在役设备树探查 / "
             "绝对重定位门禁 / 宿主测试 harness（v0.6.85，源：ios-instantnoodle）/ "
             "工具链安全响应时钟（v0.6.86，源：2026-10 eMudhra 中间 CA 事件）"},
    {"domain": "cross-reality", "label": "交叉工具链实境",
     "note": "把本仓真实做过的交叉构建经验沉淀为概念（全部 2026-10-24 实证）："
             "bionic 无 iconv 需 libiconv 补齐 / musl iconv 原生 GB18030 / "
             "qemu-user 对 bionic 三连坎（构建级验证的口径）/ MinGW-w64 线程模型变体 / "
             "Wine 仿真验收 PE 产物 / OpenHarmony SDK 目录布局 / NDK API 级别门控 / "
             "deb 版本迁移税（A 段置 1 保版本序）/ 里程表版本号（odometer 进位循环 + CalVer 映射）"},
]

# ---- 语言编译需要：实测 15 种的明细（证据由构建时从 plang probe_results 回填）----
# 字段：lang, driver（驱动工具）, artifact（典型产物）, note
LANG_NEEDS = [
    {"lang": "python", "driver": "CPython 解释器（另有 PyPy 等）",
     "artifact": ".pyc 字节码缓存 / wheel 发行包",
     "note": "解释执行；编译产物是 import 时生成的 .pyc，不是独立可执行"},
    {"lang": "javascript", "driver": "Node/V8（解释→基线→优化分层 JIT）",
     "artifact": "npm 包（源码分发）",
     "note": "无独立编译步骤；打包工具（esbuild/webpack）可选"},
    {"lang": "typescript", "driver": "tsc 转译为 JavaScript",
     "artifact": "JS 源码 + 类型声明 .d.ts",
     "note": "transpile：类型层编译期擦除，运行仍靠 JS 引擎"},
    {"lang": "go", "driver": "go build（自研 gc 工具链）",
     "artifact": "单静态可执行文件",
     "note": "GOOS/GOARCH 一键交叉；链接期去未用符号"},
    {"lang": "rust", "driver": "rustc（LLVM 后端）+ cargo",
     "artifact": "ELF/PE/Mach-O 可执行 / rlib 静态库 / cdylib 动态库",
     "note": "可切 lld 链接；交叉依赖 target sysroot"},
    {"lang": "c", "driver": "gcc 或 clang（GNU / LLVM 两家族）",
     "artifact": "可执行 / .o 目标文件 / .a 静态库 / .so 动态库",
     "note": "预处理→编译→汇编→链接四段分明（gcc -E/-S/-c 可分段观察）"},
    {"lang": "cplusplus", "probe_id": "cpp", "driver": "g++ 或 clang++",
     "artifact": "可执行 / .o/.a/.so（同 C）",
     "note": "模板实例化在编译期展开，头文件成本高；标准 ISO/IEC 14882"},
    {"lang": "java", "driver": "javac → JVM 字节码",
     "artifact": ".class / jar；jlink 可裁剪运行时镜像",
     "note": "「一次编译、到处运行」靠 JVM；GraalVM native-image 可选 AOT"},
    {"lang": "ruby", "driver": "CRuby 解释器（源码→YARV 字节码）",
     "artifact": "源码发行（gem）",
     "note": "无常规预编译交付形态"},
    {"lang": "perl", "driver": "perl 解释器",
     "artifact": "源码发行（cpan 模块）",
     "note": "perlcc 等非常规，主流是解释执行"},
    {"lang": "bash", "driver": "bash 解释器",
     "artifact": "脚本本身",
     "note": "无编译产物；分发靠源码与 shebang"},
    {"lang": "awk", "driver": "mawk / gawk 解释器",
     "artifact": "脚本本身",
     "note": "模式-动作模型；无编译产物"},
    {"lang": "tcl", "driver": "tclsh 解释器",
     "artifact": "源码；tclkit/starpack 可封装单文件",
     "note": "解释执行；封装工具做文件系统打包"},
    {"lang": "fsharp", "driver": "dotnet fsc → IL",
     "artifact": ".dll（IL）+ F# 脚本 .fsx",
     "note": "Fable 可转 JS；宿主为 .NET 工具链"},
    {"lang": "makefile", "driver": "make 解析 Makefile 驱动 cc/as/ld",
     "artifact": "Makefile 指定的任意产物",
     "note": "元构建：本身不是语言编译，而是编排其他工具链"},
]

# ---- 概念条目 ----
# 字段：id, name, domain, gist, detail, bridges[], needs_verify(可选), extra(轴相关)
CONCEPTS: List[dict] = [
    # ============ 轴1 编译流水线 ============
    {"id": "pipeline-overview", "name": "编译流水线总览", "domain": "pipeline",
     "gist": "源码→可执行的标准阶段链：前端→中端→后端→汇编→链接。",
     "detail": "前端（词法/语法/语义）与目标无关，中端做 IR 级优化，后端做目标相关"
               "代码生成；IR 的引入让「n 前端 × m 后端」不必写 n×m 套代码。",
     "bridges": [
         {"system": "daoxue", "target": "principle:daofa-ziran", "relation": "理念映射",
          "how": "按源码与目标本性选流水线段与优化级，不一律开满"}]},
    {"id": "aski-pipeline", "name": "aski 小编译器管线（导入学习应用实例）", "domain": "pipeline",
     "gist": "约 1077 行 Rust 写成的「汇编执行、C 的样貌」编译器：四段管线各单职责，"
             "输出直接映射 NASM 分节。",
     "detail": "IStream（字符流+位置）→ Tokenizer（组合子谓词切 token）→ Parser"
               "（作用域栈 Vec<ScopeImpl>）→ Program（header/text/ro_data/bss 四节"
               "累积输出）；寄存器显式暴露（$rax=2 即 mov rax,2），类型只管尺寸"
               "（[byte,32]/[qword,32]），函数结尾自动补 ret，extern fn 暴露链接符号，"
               "# 前缀内联汇编；未实现的 while/for 在 README 诚实标注——「诚实标注"
               "未完成面」本身是工程范本。源：pepsipu/aski（无许可证，只学模式）。",
     "engineering": "落法：写小编译器就照 aski 的顺序——先 IStream+Tokenizer（字符→token，"
               "字符类别提成 combinator.rs 式纯谓词表），再 Parser（token→作用域树，"
               "Statement 枚举穷尽形态），最后 Program（树→.text/.data/.bss 四节文本，"
               "节结构与 global 声明在一开始就进数据结构）；每段可独立单测，加一种"
               "token/语句只改一处。本仓 asm 子系统的 SIMD 矩阵与 reverse 的 PE 解剖"
               "都是「先建表再驱动」的同构落法。",
     "bridges": [
         {"system": "daoxue", "target": "principle:daofa-ziran", "relation": "理念映射",
          "how": "语法包装顺应汇编线性执行的本性（寄存器显式、控制流从简），不违本性"
                 "地降低书写成本"},
         {"system": "plang", "target": "lang:rust", "relation": "实现载体",
          "how": "aski 自身以 Rust 实现——用现代语言写「面向汇编」的编译器"},
         {"system": "plang", "target": "lang:assembly", "relation": "目标产物",
          "how": "产物是 NASM 汇编（.text/.data/.bss 分节），再交汇编器与链接器"}]},
    {"id": "lex-parse", "name": "词法与语法分析", "domain": "pipeline",
     "gist": "字符流→token→AST；语法错误在这一层暴露。",
     "detail": "手写递归下降或生成器（flex/bison、ANTLR、LALRPOP）；AST 设计决定"
               "后续扩展面。",
     "bridges": [
         {"system": "plang", "target": "model:ir", "relation": "上游",
          "how": "AST→IR 的转换是解释型/编译型分道的中枢"}]},
    {"id": "sema", "name": "语义分析", "domain": "pipeline",
     "gist": "类型检查、名字解析、常量求值；类型错误在这一层拦截。",
     "detail": "静态语言把大量错误前移到编译期；动态语言把检查推迟到运行期，"
               "换来灵活性但错误栈更深。",
     "bridges": []},
    {"id": "ir", "name": "中间表示（IR）", "domain": "pipeline",
     "gist": "源码与目标机之间的中立表示：优化在此进行，与前后端解耦。",
     "detail": "形态从 AST 到 SSA 到三地址码；LLVM IR/QIR 均为代表；「IR 层可替换」"
               "是工具链工程的关键空位。",
     "bridges": [
         {"system": "plang", "target": "model:ir", "relation": "同一模型轴",
          "how": "plang 执行模型轴的 ir 类语言直接对应本概念"},
         {"system": "llvm", "target": "tool:mlir", "relation": "多级 IR 代表",
          "how": "MLIR 把 IR 分层抽象，多面体优化类在此落地"}]},
    {"id": "opt", "name": "优化 pass", "domain": "pipeline",
     "gist": "IR 级等价变换：常量折叠、内联、死代码消除、循环变换。",
     "detail": "pass 管线化、按位分级 -O0..-O3（及 size/speed 变体）；优化以不改变"
               "可观察行为为契约。",
     "bridges": [
         {"system": "llvm", "target": "tool:lld", "relation": "链路协同",
          "how": "链接期优化（LTO）跨越 .o 边界做跨模块优化"}]},
    {"id": "codegen", "name": "代码生成（后端）", "domain": "pipeline",
     "gist": "IR→目标指令：指令选择、指令调度、寄存器分配。",
     "detail": "寄存器分配是 NP-难的启发式主战场；后端与目标 ISA 绑定（x86-64/arm64/"
               "riscv/loongarch 各有后端）。",
     "bridges": [
         {"system": "plang", "target": "arch:x86-64", "relation": "目标架构",
          "how": "后端按目标架构生成代码；plang 的硬件架构轴即后端落点"},
         {"system": "plang", "target": "arch:riscv", "relation": "目标架构",
          "how": "RISC-V 后端为开源工具链重点支持对象"}]},
    {"id": "object-file", "name": "目标文件与符号", "domain": "pipeline",
     "gist": "汇编产物 .o/.obj：代码段+数据段+重定位入口+符号表。",
     "detail": "ELF/PE/Mach-O 三格式；符号可见性与弱定义在链接期消解；"
               "本仓库 PE 查看器即解析此层。",
     "bridges": [
         {"system": "plang", "target": "lang:c", "relation": "宿主语言",
          "how": "目标文件格式解析工具多用 C/C++ 编写（含本仓库 PE 查看器）"}]},
    {"id": "link", "name": "链接", "domain": "pipeline",
     "gist": "符号解析+重定位合成最终镜像：静态链接/动态链接/PIE。",
     "detail": "动态库版本与 soname、运行时加载器、延迟绑定；sysroot 决定交叉链接"
               "时能看到哪些系统库。",
     "bridges": [
         {"system": "llvm", "target": "tool:lld", "relation": "链接器实现",
          "how": "lld 统一链接 ELF/PE/Mach-O-Wasm 目标"}]},

    # ============ 轴2 工具链家族 ============
    {"id": "gnu-toolchain", "name": "GNU 工具链", "domain": "toolchain",
     "gist": "gcc/g++ + binutils(as/ld) + glibc：跨发行版 Linux 的默认栈。",
     "detail": "目标三元组 arch-vendor-os-abi（如 x86_64-linux-gnu、"
               "x86_64-w64-mingw32）选择交叉变体；glibc/musl 影响兼容面。",
     "bridges": [
         {"system": "llvm", "target": "tool:clang", "relation": "竞合",
          "how": "clang 以 GCC 兼容驱动界面分流用户；两者可混链（需注意 ABI）"}]},
    {"id": "llvm-toolchain", "name": "LLVM 工具链", "domain": "toolchain",
     "gist": "clang/opt/llc/lld/mlir/flang：模块化库化设计，后端可插拔。",
     "detail": "LLVM 版本与 QIR 版本有对应（v2.0 需 LLVM 16+）；本仓库 native/llvm "
               "子系统只读探测本机 clang/lld/mlir。",
     "bridges": [
         {"system": "llvm", "target": "tool:clang", "relation": "本仓库已接入",
          "how": "native/llvm 探针检测本机 clang 版本与已构建目标"},
         {"system": "llvm", "target": "tool:llvm-config", "relation": "本仓库已接入",
          "how": "llvm-config --targets-built 实读本机可用目标三元组"}]},
    {"id": "msvc", "name": "MSVC 工具链", "domain": "toolchain",
     "gist": "Windows 原生栈：cl.exe/link.exe/lib.exe + Windows SDK + CRT/UCRT。",
     "detail": "ABI 与 GNU 不兼容（名称修饰/结构体传递约定不同），混链需显式规范；"
               "vs 生成器以 MSBuild 驱动。",
     "bridges": []},
    {"id": "mingw", "name": "MinGW-w64", "domain": "toolchain",
     "gist": "Windows 上的 GNU 栈：GCC 语义 + PE 产物；wine 下可本地验证。",
     "detail": "本仓库即用 mingw-w64 交叉编译 PE 查看器 exe；需配 sysroot 与"
               "运行时库分发策略。",
     "bridges": [
         {"system": "llvm", "target": "target:x86_64-w64-mingw32", "relation": "目标三元组",
          "how": "llvm_docs 交叉矩阵登记该三元组"}]},
    {"id": "rust-toolchain", "name": "Rust 工具链（rustc+cargo）", "domain": "toolchain",
     "gist": "rustc 借 LLVM 出码，cargo 管依赖/profile/target 目录。",
     "detail": "nightly/stable/beta 频道；no_std/embedded 目标无完整 libc；"
               "交叉编译需 target spec 与 -Z build-std。",
     "bridges": [
         {"system": "plang", "target": "lang:rust", "relation": "同语言",
          "how": "plang 161 语言中 rust 的执行模型为 native（经 LLVM）"}]},
    {"id": "go-toolchain", "name": "Go 工具链（go build）", "domain": "toolchain",
     "gist": "自研 gc 编译器+链接器，一键交叉，默认静态链接成单文件。",
     "detail": "GOROOT/GOPATH 模块模式；CGO 开关决定是否链接 libc；"
               "linker flags 可裁剪（-ldflags \"-s -w\"）。",
     "bridges": [
         {"system": "plang", "target": "lang:go", "relation": "同语言",
          "how": "plang 中 go 为 native 执行模型"}]},
    {"id": "jvm-toolchain", "name": "JVM 工具链（javac/jlink）", "domain": "toolchain",
     "gist": "javac 产 .class；jar 打包；jlink 按模块裁剪运行时。",
     "detail": "JDK 版本（8/11/17/21…）语言与 API 面差异；模块系统 JMPS  aftermath；"
               "本仓库 native/jdk 只读探测本机 JDK。",
     "bridges": [
         {"system": "plang", "target": "lang:java", "relation": "同语言",
          "how": "plang 中 java 为 bytecode-vm 执行模型"}]},
    {"id": "dotnet-toolchain", "name": ".NET 工具链（Roslyn/dotnet）", "domain": "toolchain",
     "gist": "Roslyn 编译器平台+csc→IL；dotnet CLI 管 SDK/运行时/发布。",
     "detail": "AOT（NativeAOT）与 JIT 双模式；self-contained 发布含运行时；"
               "本仓库 .NET PE 解析器即 net6.0 构建。",
     "bridges": [
         {"system": "plang", "target": "lang:csharp", "relation": "同语言",
          "how": "plang 中 csharp 为 bytecode-vm（CLR）执行模型"}]},
    {"id": "beam-toolchain", "name": "BEAM 工具链（erlc）", "domain": "toolchain",
     "gist": "Erlang/Elixir 编译到 BEAM 字节码，热升级是招牌能力。",
     "detail": ".beam 文件由 VM 加载；OTP release 打包；分布式/容错语义内建。",
     "bridges": [
         {"system": "plang", "target": "lang:erlang", "relation": "同语言",
          "how": "plang 中 erlang 为 bytecode-vm（beam）执行模型"}]},
    {"id": "compile-interpret", "name": "编译-解释连续体", "domain": "toolchain",
     "gist": "不是二选一：JIT/transpile/AOT/字节码是光谱上的不同点。",
     "detail": "同一语言常跨点存在（Python 解释+pyc；JS 引擎分层 JIT；Java 字节码+"
               "Graal AOT）。判定编译形态要看实际运行方式而非印象。",
     "bridges": [
         {"system": "plang", "target": "model:*", "relation": "分类依据",
          "how": "plang 执行模型轴（native/bytecode-vm/interpreted/jit/transpiled/ir/hdl）"
                "即本概念的语言学映射"},
         {"system": "daoxue", "target": "principle:zhi-bu-zhi", "relation": "理念映射",
          "how": "形态按可验证事实判定；无实证标「未实测」不臆造"}]},

    # ============ 轴3 构建系统 ============
    {"id": "make", "name": "Make", "domain": "build",
     "gist": "最经典的按依赖驱动：Makefile 规则+时间戳增量。",
     "detail": "隐式规则/自动变量/模式规则；并行 -j；递归 make 是大工程常见痛点。",
     "bridges": []},
    {"id": "cmake", "name": "CMake", "domain": "build",
     "gist": "跨平台生成器：CMakeLists→(Ninja|Make|VS|Xcode) 原生构建。",
     "detail": "target_* 声明式属性优于目录变量；presets 固化配置；"
               "export compile_commands.json 服务 LSP/clang-tools。",
     "bridges": []},
    {"id": "ninja", "name": "Ninja", "domain": "build",
     "gist": "只做「尽可能快地执行已计算好的依赖图」，与生成器配合。",
     "detail": "输入是 build.ninja（CMake 等生成）；极致并行与最小重算；"
               "本身不提供配置抽象。",
     "bridges": []},
    {"id": "meson", "name": "Meson", "domain": "build",
     "gist": "Python 语法+声明式配置，默认后端 Ninja，开箱即用。",
     "detail": "相较 CMake 语法更一致；wrap 管子项目依赖；"
               "GLib/GNOME 生态默认。",
     "bridges": []},
    {"id": "scons", "name": "SCons", "domain": "build",
     "gist": "Python 驱动的构建系统：SConstruct 即构建逻辑，依赖扫描自动完成。",
     "detail": "make 的自研 DAG 替代路线：不手写隐式规则与依赖行，配置即 Python 代码；"
               "宿主实采 4.5.2（2023-03-21），上游 4.11.1（2026-08-26）已多轮"
               "（toolchain catalog 记 needs_action）。本仓库不引入，仅认知登记。",
     "bridges": []},
    {"id": "bazel", "name": "Bazel", "domain": "build",
     "gist": "Google 系 hermetic 构建：Starlark 规则+远程缓存+沙箱执行。",
     "detail": "可复现性是设计核心（ hermetic toolchain）；学习曲线陡；"
               "buck2/pants 为同类路线。",
     "bridges": []},
    {"id": "gradle-maven", "name": "Gradle / Maven", "domain": "build",
     "gist": "JVM 生态构建：生命周期/插件/仓库坐标依赖管理。",
     "detail": "Maven 约定优于配置；Gradle 以任务 DAG 与增量见长；"
               "两者共治依赖解析（冲突调解/版本目录）。",
     "bridges": []},
    {"id": "native-build", "name": "语言原生构建（cargo/pnpm/dotnet）", "domain": "build",
     "gist": "「构建即命令」：cargo build / pnpm run / dotnet build 自带依赖锁。",
     "detail": "锁文件（Cargo.lock/pnpm-lock.yaml/packages.lock.json）保证可复现；"
               "工作区（workspace）管多包。",
     "bridges": [
         {"system": "plang", "target": "lang:rust", "relation": "工具即语言生态",
          "how": "cargo 与 rustc 版本频道绑定"}]},
    {"id": "ide-build", "name": "IDE 构建（MSBuild/Xcodebuild）", "domain": "build",
     "gist": "平台 IDE 的工程文件驱动的构建：.vcxproj/.csproj、xcodeproj。",
     "detail": "CI 上常以 msbuild/xcodebuild 无头调用；工程文件手改易碎，"
               "生成器路线（CMake/Xcodegen）更稳。",
     "bridges": []},
    {"id": "container-toolchain", "name": "容器化工具链（Dockerfile/compose）", "domain": "build",
     "gist": "把构建与运行环境固化为镜像声明：宿主差异被容器边界抹平，构建可复现。",
     "detail": "本仓 counterpart 真实在位：system-optimizer/Dockerfile（多阶段构建，"
               "builder 只产 wheel/sdist，经 tools/syspkg 打包；最终镜像非 root 用户、"
               "除 Python 外零新增依赖）+ docker-compose.yml（read_only 根文件系统、"
               "cap_drop: ALL、no-new-privileges、不暴露端口）。宿主 Docker 27.5.1 vs "
               "上游 29.9.1（toolchain catalog 记 needs_action）。红线延续：catalog "
               "只读编目，不本地构建、不拉取镜像。",
     "bridges": [
         {"system": "datong", "target": "concept:yiti-liangmian", "relation": "理念映射",
          "how": "多阶段构建一张 Dockerfile 两面读：builder 面产 wheel/sdist，"
                 "终镜像面只带成品——同一声明的两个面相"}]},
    {"id": "lint-gate", "name": "Lint 与格式化门禁", "domain": "build",
     "gist": "入库前门禁：clang-format/clang-tidy/shellcheck 把风格与缺陷拦截在提交前。",
     "detail": "宿主实采 clang-format/clang-tidy 18.1.3 与 shellcheck 均在位。"
               "shellcheck 一环已落地（#652）：scripts/check_shell_lint.sh 白名单"
               "门禁 lint 本仓自有 11 个 .sh（排除 quantum-kernel 上游内核源码树与 "
               "plang 语法样例），附防漏网全仓扫描；"
               ".github/workflows/lint-shell.yml 把它接入 CI（apt 装 shellcheck 保证"
               "在场，本地 SKIP 不适用于 CI）；system-optimizer/tests/test_lint_gate.py "
               "守卫白名单双向契约（无漏网、无失效条目、防 hadolint/actionlint 伪接入）。"
               "落地时修复既有 5 处告警（build-arch.sh SC2015/SC2012、build-mobile.sh "
               "SC2015/SC2086、push-to-github.sh SC2164），全仓 .sh 现零告警。"
               "clang-format/clang-tidy（C/C++ 侧）与 hadolint/actionlint 尚未接入，"
               "宿主仅 shellcheck 在位——如实分级「部分落地」。",
     "bridges": [
         {"system": "daoxue", "target": "principle:zhi-bu-zhi", "relation": "理念映射",
          "how": "如实分级：shellcheck 一环有脚本、有 CI、有守卫即登记落地；"
                 "hadolint/actionlint 宿主缺席即挂 needs_action——知止于已验证的事实，"
                 "不把没投产的能力写成已具备，也不把已投产的写成没有"}]},

    # ============ 轴4 目标产物 ============
    {"id": "artifact-static-lib", "name": "静态库（.a/.lib）", "domain": "artifact",
     "gist": "ar 归档的目标文件集合，链接期整体拷入可执行。",
     "detail": "优点：无运行时依赖；缺点：体积冗余与更新需重链；thin archive 存路径。",
     "bridges": []},
    {"id": "artifact-shared-lib", "name": "动态库（.so/.dll/.dylib）", "domain": "artifact",
     "gist": "运行时加载共享；soname/版本治理部署兼容性。",
     "detail": "延迟绑定省启动；ABI 兼容是长期负担；Windows 侧 DLL 搜索顺序有安全面。",
     "bridges": []},
    {"id": "artifact-exe", "name": "原生可执行（ELF/PE/Mach-O）", "domain": "artifact",
     "gist": "OS 直接加载的镜像：头+段+入口点。",
     "detail": "三大格式各有段/节模型；PE 为本仓库 PE 查看器解析对象；"
               "PIE/ASLR 是现代默认。",
     "bridges": [
         {"system": "llvm", "target": "tool:lld", "relation": "产出链接器",
          "how": "lld 产出的三格式可执行与本仓库 PE 工具互通"}]},
    {"id": "artifact-bytecode", "name": "字节码（.class/.pyc/.beam）", "domain": "artifact",
     "gist": "虚拟机加载的中间产物，与 OS/ISA 解耦。",
     "detail": "一次编译到处运行；分发时版本兼容看 VM 大版本；"
               "Jlink/jar 可裁剪分发。",
     "bridges": [
         {"system": "plang", "target": "model:bytecode-vm", "relation": "产物对应模型",
          "how": "字节码产物即 bytecode-vm 执行模型的语言的标准落点"}]},
    {"id": "artifact-wasm", "name": "WebAssembly（.wasm）", "domain": "artifact",
     "gist": "面向浏览器的可移植字节码；组件模型（Component Model）扩展跨语言 ABI。",
     "detail": "工具：Emscripten/wasm-pack/ wasi-sdk；wasi 把系统能力接口化；"
               "线程/GC 提案演进中。",
     "bridges": [
         {"system": "llvm", "target": "target:wasm32-unknown-unknown", "relation": "目标三元组",
          "how": "llvm_docs 交叉矩阵登记 wasm32 目标"}]},
    {"id": "artifact-ir", "name": "IR 落盘（.ll/.bc/QIR）", "domain": "artifact",
     "gist": "把中间表示当交付物：供分析、链接期优化或编译服务。",
     "detail": "LLVM bitcode/IR 文本可被 opt/llc 接力；量子侧 QIR 同理（.ll 子集）。",
     "bridges": [
         {"system": "plang", "target": "model:ir", "relation": "产物对应模型",
          "how": "ir 执行模型的语言以 IR 文件为主交付形态"}]},
    {"id": "artifact-pkg", "name": "安装包（deb/rpm/msi/pkg/apk）", "domain": "artifact",
     "gist": "OS 级分发形态：包管理器可查询/可回滚。",
     "detail": "deb/rpm 走发行版仓库；msi 走 Windows Installer；flatpak/snap/appimage "
               "是第三种路线（自包含）。",
     "bridges": []},
    {"id": "artifact-container", "name": "容器镜像", "domain": "artifact",
     "gist": "分层文件系统+运行时元数据；构建用 Dockerfile/OCI 工具。",
     "detail": "多阶段构建把「编译环境」与「运行环境」分层，是 hermetic 构建思想的"
               "交付侧投影。",
     "bridges": []},
    # ============ v0.6.63 续：导入学习应用（SonicBoom / Linux 7.3）============
    {"id": "mlir", "name": "MLIR 多级中间表示", "domain": "toolchain",
     "gist": "多层 IR 的编译器基建：同一框架内定义方言与降级 pass，从高层算子一路降到 LLVM IR。",
     "detail": "SonicBoom 以 MLIR 为编译器核心，把 GEMM/归一化等高层算子降级为内核；"
               "多级 IR 让『IR 层可替换』从理念落为可操作的方言层级。",
     "bridges": [
         {"system": "llvm", "target": "tool:mlir", "relation": "编译器基建",
          "how": "MLIR 是 LLVM 家族的多级 IR 框架，本仓库 native/llvm 只读探测 mlir"},
         {"system": "plang", "target": "model:ir", "relation": "多级 IR 模型",
          "how": "plang 执行模型轴的 ir 类语言对应本概念的多级中间表示"}]},
    {"id": "kernel-fusion", "name": "算子融合（内核融合）", "domain": "pipeline",
     "gist": "把相邻算子（如 RMS 归一化 + 残差加 + 缩放）融合进同一内核/区域，"
             "减少中间读写与启动开销。",
     "detail": "SonicBoom 的 FuseGlueRegions/FoldScaleIntoGluePass 把 GEMM epilogue 后的"
               "scale 折叠进区域 epilogue；属等价变换的优化 pass，不引入新语义。",
     "bridges": [
         {"system": "plang", "target": "model:ir", "relation": "IR 级优化",
          "how": "融合在 IR/区域表示上做等价变换，与优化 pass 同构"}]},
    {"id": "bpf-binfmt", "name": "BPF 驱动的 binfmt 处理器", "domain": "toolchain",
     "gist": "Linux 7.3 让 binfmt_misc 的处理器可用 BPF 程序按 exec 计算，"
             "免 patchelf/包装脚本即可做可重定位二进制。",
     "detail": "每 exec 由 BPF 程序决定解释器（如相对二进制定位动态加载器），"
               "是『解释器即策略』的运行时落地；与编译/加载工具链同源。",
     "bridges": [
         {"system": "plang", "target": "lang:c", "relation": "BPF 程序语言",
          "how": "BPF 处理器以受限 C 子集编写，经 LLVM 后端编译进内核"}]},
    # ============ v0.6.64 续：导入学习应用（openKylin skills：UKUI 桌面小插件 skill）============
    {"id": "plugin-install-layout", "name": "插件安装布局（三类产物与运行时发现路径）", "domain": "build",
     "gist": "构建的终点不是编译成功，而是安装结果被运行时发现：QML 插件库+qmldir、"
             "widget 元数据、QML 运行文件三类产物各有安装路径，漏一项运行时就少一项发现。",
     "detail": "openKylin peony widget 的安装契约：widget 文件扁平装到 "
               "/usr/share/ukui/widgets/<Id>/（metadata.json 只写扁平文件名，同包辅助 QML "
               "与字体必须一并安装）；QML 插件库与 qmldir 装到 $$[QT_INSTALL_QML]/org/ukui/"
               "<module>，且 TARGET/qmldir/plugin.cpp 注册的模块名三者一致。qmake 用 INSTALLS "
               "声明，CMake 需显式写出等价的 install()——『能编译』不等于『装得对』。",
     "bridges": [
         {"system": "netsys", "target": "module:ukui-desktop-widget", "relation": "安装契约实例",
          "how": "UKUI 桌面小插件的三类产物安装路径即本概念的活样本"}]},
    # ============ v0.6.73 续：黑箱实战（UPX / MinGW / GDB 实测，reverse 子系统落地）============
    {"id": "upx-packer-signature", "name": "UPX 加壳特征识别", "domain": "reverse",
     "gist": "壳把原程序包进一层自解压/自解密壳：识别靠三特征——UPX! 字节 marker、"
             "UPX0/UPX1/UPX2 节名、数据节高熵。",
     "detail": "沙箱实测（v0.6.73 固化）：mingw GCC 13 造 win64/win32 两样本，"
               "UPX 4.2.2 --best --lzma 加壳后 win64→121050B（48.50%）、"
               "win32 --best→126378B（53.22%）；marker 落在 .text 末尾偏移 0x205，"
               "整体熵 5.898→7.035。三特征任一即可标记『疑似加壳』，不必解壳即可判断。",
     "bridges": [
         {"system": "plang", "target": "lang:c", "relation": "同生态",
          "how": "UPX 与被壳样本同为 C 生态产物；壳识别读的正是编译器产出的容器"},
         {"system": "daoxue", "target": "principle:zhi-bu-zhi", "relation": "理念映射",
          "how": "壳内容不可见即按『已加壳』标记，不猜壳内之物——知止于可见事实"}]},
    {"id": "entropy-signal", "name": "熵判据（压缩与加密的信号）", "domain": "reverse",
     "gist": "字节的香农熵度量随机性：压缩/加密后的数据节熵趋近 8 比特/字节，"
             "是人写代码与机器致密化的分界。",
     "detail": "只读静态分析的第一道筛子：逐节算熵，数据节 >7.5 且节数少的可执行"
               "大概率被加壳。实测整体熵 5.898→7.035；strip 后熵反降（1.522→1.235，"
               "本地符号被移除）。熵不判好坏，只提示『这里值得细看』。",
     "bridges": [
         {"system": "datong", "target": "concept:yiti-liangmian", "relation": "理念映射",
          "how": "同一段字节两面读：低熵是人写代码、高熵是压缩加密——一体两面"}]},
    {"id": "binfmt-anatomy", "name": "可执行格式解剖（PE/ELF）", "domain": "reverse",
     "gist": "不运行程序也能读出格式与节区：MZ→e_lfanew→PE\\0\\0→COFF→可选头→节表；"
             "ELF 侧读 e_ident 与 machine 字段。",
     "detail": "实测：PE32 可选头 magic 0x10B、PE32+ 0x20B；节表在 COFF+20+optsz 处，"
               "每节 40 字节记名字/虚拟大小/原始大小/数据位置；ELF64 的 machine=0x3E（62）"
               "即 x86-64。格式解剖是壳识别、符号检查、熵分析共用的底座。",
     "bridges": [
         {"system": "plang", "target": "arch:x86-64", "relation": "同一架构两格式",
          "how": "PE32+（magic 0x20B）与 ELF64（machine=0x3E）都指向 x86-64："
                 "格式差异不改变指令面"},
         {"system": "llvm", "target": "tool:clang", "relation": "工具对照",
          "how": "llvm-objdump/readelf 一族与自写解剖器同属只读二进制分析面"}]},
    {"id": "blackbox-debug", "name": "黑箱调试（GDB 四连）", "domain": "reverse",
     "gist": "没有源码也能问运行态问题：info functions 看符号、disassemble 看指令、"
             "info proc mappings 看内存映射、break+continue 看执行流。",
     "detail": "沙箱实测：对未 strip 的 ELF 样本 info functions 列全符号、"
               "disassemble main 出函数体指令；strip 后仅剩 PLT 动态符号（"
               "符号表瘦身直接抬高黑箱门槛）。GDB 只读观察，不下断写内存——"
               "调试是提问，不是修改。",
     "bridges": [
         {"system": "plang", "target": "lang:c", "relation": "调试对象语言",
          "how": "GDB 四连读的是 C 样本的符号与反汇编；DWARF 调试信息由编译器写入"}]},
    {"id": "symbol-visibility", "name": "符号可见性（strip 前后）", "domain": "reverse",
     "gist": "strip 移除本地符号表：文件变小、静态可读性下降，但动态符号"
             "（PLT/导入导出）因运行时需要而保留。",
     "detail": "实测：strip 前后 16000→14472 字节、熵 1.522→1.235。"
               "可见性分级是刻意设计而非全有全无：拿去调试的符号，留运行必需的符号；"
               "黑箱分析前先看符号还剩多少，决定用静态解剖还是动态调试。",
     "bridges": [
         {"system": "plang", "target": "lang:go", "relation": "同纪律",
          "how": "Go 链接期同样裁剪未用符号（-ldflags \"-s -w\"）：去符号是通用瘦身"}]},
    {"id": "crossbuild-sample", "name": "自造样本（交叉构建实验对象）", "domain": "reverse",
     "gist": "黑箱分析的前提是可复现的实验对象：用 MinGW-w64 同源造 PE32/PE32+ "
             "双样本，ELF 侧由本机 GCC 产出，壳与裸本一一对照。",
     "detail": "实测：mingw GCC 13 产 PE32 237482B/17 节、PE32+ 249562B/19 节"
               "（-O1 更重因静态链接 runtime）；每个样本留裸本/UPX 壳本/strip 本三态，"
               "换口径时三态重测。wine 在沙箱启动 PE 失败（ExecuteEx），"
               "故动态侧以 ELF+GDB 为主路径——事实登记，不硬凑。",
     "bridges": [
         {"system": "llvm", "target": "target:x86_64-w64-mingw32", "relation": "目标三元组",
          "how": "llvm_docs 交叉矩阵登记该三元组；本概念的双格式样本即按此口径产出"},
         {"system": "datong", "target": "concept:gu", "relation": "先做后拆",
          "how": "先自造样本再解剖——固：可复现的实验对象是黑箱结论的地基"}]},
    {"id": "license-compliance-boundary", "name": "许可合规边界（逆向分析的守界）", "domain": "reverse",
     "gist": "黑箱逆向只做合规与协议层分析：把「许可规避」类工具当合规分析对象，绝不编目为可装可跑工具、不复制其代码、不提供任何绕过手段。",
     "detail": "以 massgrave.dev / Microsoft-Activation-Scripts 为案例：它是研究 Windows 激活服务（SPP）的激活绕过工具集，含 HWID / Ohook / TSforge / Online KMS，GPL-3.0、Batchfile 为主、约 195k★。本仓只把它当「许可合规边界」的反面教材与合规分析对象——边界在『分析激活服务的协议与机制』与『提供可绕过的激活手段』之间；本仓守后者不越。",
     "engineering": "落法：真落地。本仓库 reverse 子系统（docs/40）口径——黑箱逆向全部沙箱只读实测、不碰未授权目标；needs_verify 纪律 + audit_concepts --strict 拦截『未核实冒充已核实』；工具链 catalog 的 setup_steps/commands 是 README 性质的逻辑顺序而非自动执行队列（docs/57 §红线）。massgravel 类项目在本仓的落点是『合规分析对象 + needs_verify 挂牌』，绝不进入 repo_tools 可装清单（docs/59）。",
     "bridges": [
         {"system": "daoxue", "target": "principle:zhi-bu-zhi", "relation": "理念映射",
          "how": "知止于可见事实、知边界而不过界——许可规避是『不可越』之界，分析止于合规"}]},
    # ============ v0.6.74 续：位宽与寻址世代（legacy 子系统位宽/PAE 落地）============
    {"id": "bit8-era", "name": "8 位世代（微控制器年代）", "domain": "bitwidth",
     "gist": "8 位数据线 + 16 位地址线（典型 64KB 寻址）的年代：8080/Z80/6502/6809，"
             "无 MMU、无保护模式，程序直接面对硬件。",
     "detail": "本机无 8 位原生执行路径，但 8 位**编译与运行双路径**均已实测落地"
               "（2026-10-26 构建批次 + 补全批次）：编译侧 sdcc 4.2.0+dfsg-1（apt）"
               "以 -mz80 产 Z80 Intel HEX——hello8.ihx 358B（hex 内 :03000000C3000139 "
               "= jp 0x0100、CF=RST 08h、18 FD=jr 循环，Z80 crt0+main 指令指纹可核）。"
               "运行侧（补全批次闭合）：自含 Z80 执行内核 research/comp/z80core.py"
               "（全基础集 256 + CB 全块 + ED 常用块 + DD/FD 前缀，已知答案自测 "
               "22/22）+ research/comp/z80_runner.py（Intel HEX 加载、OUT 端口捕获、"
               ".map 符号回读、HALT 停机）实跑 hello8run.ihx 618B：OUT(01) 端口流"
               "『Z80-RT-OK68\\n』、_counter@8000 回读 0x68（=0x55+9 字符+0x0A，"
               "与手算一致）、HALT 停机 PC=0264、196 指令 ~1710 T 态（标称）；"
               "独立反汇编器 dz80（d52 包）交叉核对：已执行指令拼接流线性反汇编，"
               "助记符序列 197/197 一致。asz80 语法纪律新增：绝对寻址须括号"
               "ld a,(_sym)（裸写 ld a,_sym 被拒 error a）；OUT 立即数写十进制"
               "out (1),a（0x01 亦可，1h 后缀不可）。sdcc 4.2 纪律：必须 ANSI C"
               "（K&R main() 拒收，error 7）；z80 目标下裸 __at 声明被拒"
               "（error 1 + warning 166），须写 __sfr __at 形式（实测通过）。"
               "诚实边界：自含内核非参考级实现——不建模中断接受/精确 T 态/内存竞争，"
               "覆盖范围在模块 docstring 文档化；qemu/MAME/FCEU 仍维持存在性只读"
               "探测（不启动、不下载 ROM）。位宽是能力分档不是优劣判词——8 位机的"
               "实时性约束正是当年程序员的创造力来源；今天跑 8 位程序是为了保存与"
               "考古，不是为了替代现代栈。",
     "bridges": [
         {"system": "plang", "target": "arch:host", "relation": "能力对照",
          "how": "宿主机架构不含 8 位数据通路，8 位程序只能以模拟层存在于宿主之上"},
         {"system": "netsys", "target": "module:radio", "relation": "算力底座对照",
          "how": "AVR 等 8 位射频 MCU 是位宽世代里最小几档的算力底座，"
                 "射频信号处理就跑在这类裸机/RTOS 上；无线电只读诊断即看这块底座"},
         {"system": "netsys", "target": "module:sysmesh", "relation": "系统互联协调",
          "how": "编译产物经组网分发与协同（sysmesh）：构建终点=被发现，与系统互联协调同一『产物即服务』纪律"}]},
    {"id": "real-mode-16", "name": "16 位实模式（DOS 年代）", "domain": "bitwidth",
     "gist": "8086/286 的实模式：段:偏移寻址 20 位 = 1MB 天花板，无特权级、无内存保护，"
             "操作系统界面就是中断调用（DOS INT 21h/10h/13h/16h）。",
     "detail": "知识坐标：MS-DOS 3.1（FAT12、360KB 软盘、640KB 常规内存、HIMEM/EMM386）、"
               "开源替代 FreeDOS 1.4（2025-04，GPL）、Linux 上的 dosbox（完整 CPU 模拟）"
               "与 DOSEMU2（近原生 DPMI）——模拟层覆盖，不是原生。构建批次实测落地"
               "（2026-10-26）：bcc 0.16.17-3.5build1（dev86）以 -Md -0 从 K&R C 产 16 位"
               "实模式 COM（hello16.com 228B 无头，指纹 mov ax,42 + int 21h/20h，"
               "dosbox 0.74-3 无头实跑 exit 0）；手写 as86/ld86 链同源——as86 -0 + "
               "ld86 -d 产 60B COM，经 int 21h 3Ch/40h/3Eh 建写关文件，宿主机回读 "
               "R7.TXT『ROUNDTRIP-OK-16BIT』（18B）——16 位实模式文件往返闭环已验证。"
               "工程纪律：ld86 -d 以 origin 0 产 COM，而 DOS 把 COM 装在 PSP:0x100，"
               "手写汇编的 #label 立即数在汇编期解析且不带重定位，必须自加 $100 基址"
               "（nasm org 0x100 的等价物；bcc 驱动给 ld86 传 -T100，C 代码走可重定位"
               "引用故无恙）。",
     "bridges": [
         {"system": "plang", "target": "arch:x86-64", "relation": "同源底座",
          "how": "x86-64 复位态即 16 位实模式：现代 CPU 启动第一步正是这一档"
                 "（BIOS/引导扇区运行其间）"},
         {"system": "datong", "target": "concept:gu", "relation": "先定档再选层",
          "how": "先认程序年代（16 位实模式）再选运行层（dosbox/DOSEMU2）——固而后拆"}]},
    {"id": "protected-32", "name": "32 位保护模式（Win32 年代）", "domain": "bitwidth",
     "gist": "80386 起的保护模式：32 位线性寻址 4GB、四级特权级、分页机制、门描述符；"
             "Win32/PE32/DPMI 都活在这一档。",
     "detail": "在 64 位宿主上跑 32 位程序的路径本批全实测（2026-10-26）：DOS 侧 "
               "binutils-djgpp 2.35.1+dfsg-2 的 i586-pc-msdosdjgpp-as/ld 从手写汇编"
               "产 go32 DPMI 可执行——hello32.exe 7628B（MZ+COFF+DJ Delorie stub "
               "1993-1995/2022 重建），dosbox 0.74-3 下 exit 0（int 21h 4Ch 经 DPMI "
               "反射生效）；宿主侧 gcc -m32（gcc-multilib）产 ELF 32-bit i386 实跑 "
               "exit 0。另有 qemu-system-i386（整机用户态模拟）、wine（Win32 API "
               "翻译）两条存在性路径由 bitwidth_report 探测。【补全批次 #690 闭合 C 编译"
               "路径缺口】DJGPP 的 GCC/libc/stub 不在 apt（仅 binutils 侧），本批自上游 "
               "andrewwutw/build-djgpp v3.4 取 Linux64 预构建工具链（GCC 12.2.0 + DJGPP "
               "libc + go32 stub，80,596,981B，sha256 8464f170…）：i586-pc-msdosdjgpp-gcc "
               "编译 hello32c.c（ANSI C，-O2 零警告）→ hello32c.exe 197852B（MS-DOS MZ + "
               "COFF + DJGPP go32 extender），dosbox 0.74-3 实跑双面证据——OUT.TXT(stdout "
               "重定向，DOS 文本模式 \\r\\n 计 18B) 与 Z32C.TXT(fopen/fprintf/fclose 二进制，"
               "16B) 均为 \"Z32C-RT-OK55\\nFB\\n\"，0xFB 与 0x55+0x29C+0x0A 独立复算一致，"
               "dosbox rc=0。工程坑：wget 中断尾部半块 + aria2 续传拼接致 bzip2 CRC 坏须"
               "从头干净重下；dosbox dpmi=true 不被 DJGPP 12.2 桩接受须自带 CWSDPMI"
               "(csdpmi7b)。缺口闭合。",
     "bridges": [
         {"system": "llvm", "target": "target:i686-linux-gnu", "relation": "工具链目标",
          "how": "llvm_docs 交叉矩阵登记 i686 三元组：32 位目标至今是一等公民"}]},
    {"id": "pae-extension", "name": "PAE 物理地址扩展", "domain": "bitwidth",
     "gist": "Pentium Pro 起 IA-32 的物理地址扩展：页表项 32→64 位、两级→三级页表，"
             "物理寻址上限扩到 36 位（64GB）；只扩物理寻址，不改进程虚拟地址空间。",
     "detail": "微软官方口径（Learn/MSDN）：XP/Server 2003 用 boot.ini 加 /PAE"
               "（/NOPAE 禁用；DEP 启用即自动开）；Vista/Win7 用 bcdedit /set pae "
               "ForceEnable。诚实边界：XP 全版本物理地址空间上限即 4GB——开 PAE 的"
               "意义是硬件 DEP/NX 与热插拔内存，不是突破 4GB。Linux 侧：HIGHMEM64G "
               "选中后 select X86_PAE，PAE 同时是 32 位内核 NX 的前提，代价是页表"
               "查找开销。64 位系统原生全寻址，不需要也不支持 PAE。",
     "bridges": [
         {"system": "daoxue", "target": "principle:zhi-bu-zhi", "relation": "理念映射",
          "how": "不宣称 PAE「突破 4GB」——知止于官方口径，诚实边界先于能力叙事"},
         {"system": "datong", "target": "concept:yiti-liangmian", "relation": "理念映射",
          "how": "同一张页表两面读：32 位项映射 4GB 以内，64 位项把物理面扩到 36 位"}]},
    {"id": "long-mode-64", "name": "64 位长模式", "domain": "bitwidth",
     "gist": "x86-64/arm64 的长模式：大幅虚拟寻址空间 + 原生物理寻址（看具体实现），"
             "cpuinfo 的 lm 标志即 CPU 长模式能力位。",
     "detail": "本机 bitwidth_report 直接读 /proc/cpuinfo 的 lm 标志与 uname.machine "
               "内核位宽：64 位内核下 PAE 不需要也不支持；wine 在 64 位宿主跑 Win32 "
               "程序走 WoW64 翻译层（本仓 compat 子系统登记）。构建批次实测（2026-10-26）："
               "gcc 13.3.0 -m64 产 ELF 64-bit x86-64 实跑 exit 0——宿主原生档闭环。"
               "长模式不是「更大的 32 位」——寻址结构、寄存器面、调用约定都换了一代。",
     "bridges": [
         {"system": "plang", "target": "arch:x86-64", "relation": "原生档",
          "how": "plang target_archs 登记 x86-64/arm64：64 位是编译目标的一等档位"}]},
    {"id": "simd-128", "name": "128 位 SIMD 世代（向量档）", "domain": "bitwidth",
     "gist": "128 位不作为通用整数寄存器存在，而作为 SIMD 向量寄存器宽度存在："
             "x86 XMM（SSE/SSE2，1999 起）、ARM NEON；软件侧 __int128 整型补足 "
             "128 位算术。",
     "detail": "经典位宽阶梯到 128 位为止、且只到向量档。构建批次实测（2026-10-26）："
               "gcc 13.3.0 的 unsigned __int128 sizeof=16、hi/lo 拆分算术正确"
               "（0x123456789abcdef0·0fedcba987654321 原样往返）；SSE2 movdqa 把 "
               "4×int32 经 XMM 内存往返一致（1 2 3 4）——但 ELF 仍报 64 位："
               "128 位是数据通路宽度，不是进程位宽。诚实边界两条：一是不存在 128 位"
               "通用 CPU（x86 最长模式仍是 64 位 GP；RISC-V RV128 只是研究提案，"
               "needs_verify）；二是位宽阶梯不向量子延伸——qubit 无位宽、OpenQASM/QIR "
               "无经典寄存器宽度档，本沙箱无任何量子工具链（qiskit/cirq 不可导入、"
               "apt 无候选包），『多少位元的量子架构』是不成立的提法。",
     "bridges": [
         {"system": "plang", "target": "arch:x86-64", "relation": "同代并存",
          "how": "x86-64 同一颗 CPU 上 64 位 GP 寄存器与 128 位 XMM 向量寄存器并存"
                 "——位宽阶梯的相邻两档活在同一个硅片上"},
         {"system": "quantum", "target": "concept:qubit", "relation": "范式边界",
          "how": "qubit 不是『更宽的 bit』：量子计算不走经典位宽轴，位宽阶梯到 128 位"
                 "SIMD 为止，再往上的『位元量子架构』无对应物"}]},
    {"id": "retro-dos-stack", "name": "遗留 DOS·BusyBox 栈只读落地", "domain": "bitwidth",
     "gist": "DOS/BusyBox/开源 DOS 不是古董陈列，而是「16 位实模式 + 嵌入式根用户态」"
             "两档位宽能力在本仓的只读诊断落地。",
     "detail": "native/legacy.py 五报告（dos/busybox/dosbox/位宽/PAE）+ data 三库"
               "（dos.json 5 条、busybox.json 4 条、dosbox.json 3 条知识条目回链）"
               "+ compat_docs 的 bitwidth/pae 主题。两车道纪律：只读诊断车道不启动"
               "任何模拟器、不写镜像、不代改任何引导配置（boot.ini/bcdedit/内核命令行），"
               "PAE 只检测并给官方命令文本；用户显式请求的构建车道（2026-10-26 批次："
               "装 dosbox/bcc/sdcc/binutils-djgpp/gcc-multilib 并实跑验证）另论，"
               "属先例 #8 mingw-w64/#9 PE viewer 的可装可跑例外——两车道不混用，"
               "构建车道的产物与证据只落在用户显式指定的目录。",
     "bridges": [
         {"system": "datong", "target": "concept:he-butong-yong", "relation": "理念映射",
          "how": "8/16/32/64 各档各安其位而不判优劣——和而不同：每档都有它仍擅长的语境"}]},

    # ============ 轴8 引导与实测纪律（v0.6.85；源：ios-instantnoodle 导入分析） ============
    # 源仓库 haxi0/ios-instantnoodle：XNU(iOS 16) 引导 shim（arm64 Linux Image 头 +
    # 自管 MMU + live-FDT 探查 + UFS）。本轴登记其四条可复用工程纪律——全部是
    # 「把运行期才炸的错误提前」的构建期/引导期门禁，无一条要求本仓库拥有目标硬件。
    {"id": "diagnostic-first-boot", "name": "诊断优先引导", "domain": "bringup",
     "gist": "无载荷可引导时先出诚实的诊断报告，而非静默失败或伪造成功。",
     "detail": "ios-instantnoodle 的 shim 在 ramdisk 无 payload（或 payload 启动失败）时，"
               "打印 live-FDT bring-up 报告：内存库、reserved-memory  carve-out、"
               "GIC/timer/UFS/USB/SPMI/RPMh/TLMM/GCC 的 MMIO 地址、CPU MPIDR 与 /chosen，"
               "与编译期 profile 值并列对照；报告受控制台行数约束，超出即降级 truncated，"
               "不跑出面板。诊断镜像本身就是交付物——先能回答「板子实际给了什么」，"
               "再谈加载内核。",
     "engineering": "落法：本仓量子架构桌面基座沿同一纪律——quantum-core 读不到 "
                    "/proc/quantum-energy 或 /proc/quantum-net 时，state.json 记 "
                    "available=false、Genmon 面板显示「host(模拟)」（v0.6.84 实测），"
                    "先出诊断再谈运行；测试床 initrd 缺接口同样只报「未能获取」。",
     "bridges": [
         {"system": "quantum", "target": "concept:qsim-asset", "relation": "可验证诊断",
          "how": "无载荷 shim 出 live-FDT 诊断报告 ↔ 模拟器资产附验证链：先可验证地"
                 "报告现状，再谈运行——诊断先行，两头都诚实"}]},
    {"id": "live-fdt-probe", "name": "在役设备树探查", "domain": "bringup",
     "gist": "先观测后信任：编译期 profile 里的数字未经硬件观测，永远标 *(verify)*。",
     "detail": "shim/probe.c 直走 FDT structure block（MMU 关闭时全部 load 都是 Device "
               "memory，天然 4 字节对齐），把在役设备树与 shim/boards/<board>.h 的编译期"
               "假设并列输出。上游 README 原话：run it before trusting any *(verify)* "
               "number in tools/devices.py——观测先于信任，未观测的登记为待核实而非事实。",
     "engineering": "落法：与本仓 needs_verify 纪律同构——data 层每条知识可挂 "
                    "needs_verify 原因，audit_concepts --strict 与各 build --check "
                    "把「未核实冒充已核实」当漂移拦截；native 探测一律实测降级"
                    "（如 qstore 对齐 sysfs→lsblk→statvfs 三级降级）而非照抄假设。",
     "bridges": [
         {"system": "daoxue", "target": "principle:zhi-bu-zhi", "relation": "先观测后信任",
          "how": "*(verify)* 数字未经硬件观测不信任 ↔ 知不知上：知道自己有所不知，"
                 "才是踏实认知的起点"}]},
    {"id": "abs-reloc-gate", "name": "绝对重定位门禁", "domain": "bringup",
     "gist": "构建期对每个 C 目标文件跑 readelf -r，ABS64 重定位非零即构建失败。",
     "detail": "ios-instantnoodle 的 shim/build.sh 在链接前统计全部 C 对象的绝对重定位"
               "计数：镜像将被启动加载器原样拷走、没有重定位遍，任何 ABS64 都意味着运行期"
               "跳到错误地址。门禁把这类错误钉死在构建期——链接命令直接拒绝出镜像。",
     "engineering": "落法：本仓的同构门禁——scripts/check_repo_guard.py（许可/私钥/"
                    "生成产物同步）、各 build_*.py --check 防漂移、两个 HTML 生成器的 "
                    "sha256 同步校验：一律把「本应在运行期才炸的错误」提前到构建期，"
                    "CI 不过就不算完成。",
     "bridges": [
         {"system": "quantum", "target": "concept:qkern-patch-distribution", "relation": "可复现门禁",
          "how": "构建期 readelf ABS64=0 才放行 ↔ 补丁 round-trip 洁净回放：两者都是"
                 "「可复现」在各自层的门禁形态"}]},
    {"id": "host-test-harness", "name": "宿主测试 harness", "domain": "bringup",
     "gist": "以 -DHOST_TEST=1 在宿主编译运行同一份 C：无目标硬件也能验证逻辑。",
     "detail": "shim 的 console.c / probe.c / host_test.c 组成宿主 harness：gcc "
               "-DHOST_TEST=1 直接编出可运行程序，把控制台布局与 live-FDT 报告渲染成 "
               "out/probe.ppm 供目视核对。硬件不在场时，验证不停止——换到宿主继续验。",
     "engineering": "落法：与本仓「宿主模拟架构」诚实边界同构——量子是 arch/um 同型宿主"
                    "模拟（docs/44 §8），sysweeper 全量测试跑在宿主（pytest 1579 项）；"
                    "quantum-core 的 make check 同样在宿主编译运行 C 单测。",
     "bridges": [
         {"system": "quantum", "target": "concept:qsim-engine", "relation": "宿主验证",
          "how": "-DHOST_TEST=1 宿主渲染控制台/FDT 报告 ↔ 经典模拟引擎在宿主可执行验证："
                 "两条路都不依赖目标硬件，也都不假装拥有它"}]},
    {"id": "toolchain-security-response", "name": "工具链安全响应时钟", "domain": "bringup",
     "gist": "解释型语言换运行时即生效，编译型语言必须重新编译部署才生效——两种补丁响应时钟。",
     "detail": "2026-10 eMudhra 中间 CA 事件（密钥仪式 wrap/unwrap 缺陷致 P-384 私钥仅 "
               "3–8 bit 熵，8 张中间 CA 被 Mozilla 三小时内拦进 OneCRL）把两类语言的补丁"
               "时钟差异暴露到极致：Python / Node / OpenJDK 升级解释器或依赖（certifi / "
               "ca-cert / blocked.certs）即完成信任库更新；而 Go 的 crypto/x509 以硬编码 "
               "SPKI SHA-256 列表拦截受损 CA（CVE-2026-111943，1.27.3 / 1.26.10 加急）——"
               "只升级工具链而不重编主程序，二进制里旧的信任逻辑原样存活。上游 Go 只维护"
               "最近两个大版本，更老的线（如本机 Go 1.21.4）连补丁都没有，唯一路径是升级"
               "工具链并重编全部产物。供应链恶意包则连 CVE 补丁路径都没有，只能移除/回滚"
               "加轮换凭证（FIRST 口径）——本仓零第三方依赖正是对此的结构性防线。",
     "engineering": "落法：本仓 Go 七平台产物由 CI 每次从 tag 全量重编（不缓存旧二进制），"
                    "补丁随工具链升级自动进入产物；宿主解释器版本（pyenv Python / Node / "
                    "Deno / OpenJDK）在 langdetect 与 tasks/jdk.py 里是一等字段——补丁评估"
                    "先读这栏再定动作；docs/52 的九项评估表即按此时钟逐项定性（应升 / "
                    "可选 / 无动作 / 宿主持有者责任），不把「公告发了」当「补丁打了」。",
     "bridges": [
         {"system": "plang", "target": "lang:go", "relation": "补丁时钟实例",
          "how": "Go 编译型补丁必须重编译部署才生效 ↔ plang 在册的 go 语言条目："
                 "同一门语言的信任库补丁，产物形态决定响应时钟"},
         {"system": "quantum", "target": "concept:qkern-patch-distribution", "relation": "分发即补丁",
          "how": "语言生态靠重编译把补丁送进运行态 ↔ 内核补丁 round-trip 洁净回放："
                 "两者都要求「补丁可达运行态」才算打完"}]},

    # ── 轴9 cross-reality 交叉工具链实境（0000.0000.0000.0004.20261024 实证）──
    {"id": "bionic-no-iconv", "name": "bionic 无 iconv", "domain": "cross-reality",
     "gist": "NDK r15 起 bionic 移除 iconv——依赖 iconv_open 的 C 程序必须静态链入 GNU libiconv 才能交叉到 Android。",
     "detail": "classics.c 调用 iconv_open 做 GB18030 转换，交叉编译 aarch64-linux-android21 时报 "
               "call to undeclared function 'iconv_open'。解法：下载 GNU libiconv 1.17 源码，"
               "./configure --host=aarch64-linux-android CC=<ndk-clang> 静态编出 libiconv.a + "
               "libcharset.a，编译 classics 时 -I<prefix>/include 并静态链入。armv7a 与 "
               "aarch64 的库不通用（incompatible with armelf_linux_eabi 实测），须为每个 ABI "
               "独立 configure/make/install。",
     "engineering": "落法：classics-linux/build-mobile.sh 的 build_iconv 函数把这条经验固化为"
                    "自动步骤——检测 /opt/libiconv-android-a64|a32 缺失即现场交叉编译并缓存；"
                    "docs/37 §5.2 记录完整命令序列。工具链全景编目（toolchain 子系统 + "
                    "data/toolchain_catalog.json）的 libiconv-android 条目即此概念的账。",
     "bridges": [
         {"system": "plang", "target": "lang:c", "relation": "语言库缺口实例",
          "how": "C 的标准库覆盖面由目标 libc 决定 ↔ plang 在册的 c 语言条目："
                 "同一份 C 源码，glibc/musl/bionic 三个目标的库边界并不一致"},
         {"system": "daoxue", "target": "principle:zhi-bu-zhi", "relation": "缺口如实登记",
          "how": "bionic 无 iconv 不掩饰、补齐即登记 ↔ 知不知上：目标平台的库缺口"
                 "先承认再补，不假装「标准 C 到哪都能编"}]},
    {"id": "musl-gb18030", "name": "musl iconv 原生 GB18030", "domain": "cross-reality",
     "gist": "与 bionic 相反：OHOS musl 的 iconv 原生支持 GB18030，classics 直编即可，无需 libiconv 外挂。",
     "detail": "同样一份 classics.c，交叉到 aarch64-unknown-linux-ohos（musl）时 iconv_open "
               "直接可用——musl 的字符集表覆盖 GB18030。且 musl 静态二进制是 qemu-user 友好"
               "目标：qemu-aarch64-static ./classics-ohos 实跑成功、典籍文本输出无损"
               "（与 glibc 静态同属 qemu 友好目标；对比 bionic 三连坎）。",
     "engineering": "落法：build-mobile.sh 对 OHOS 目标跳过 libiconv 步骤（直编），并附"
                    "qemu 实跑验证；docs/37 §5.3 与 toolchain catalog 的 ohos-sdk 条目"
                    "登记「musl 原生 GB18030 + 静态实跑通过」双结论。",
     "bridges": [
         {"system": "plang", "target": "lang:c", "relation": "libc 能力分档",
          "how": "同一 C 程序在 musl 直编、在 bionic 要外挂 libiconv ↔ plang 的 c 条目："
                 "产物可信度按目标 libc 的字符集覆盖逐档认定，不搞一刀切"},
         {"system": "daoxue", "target": "principle:daofa-ziran", "relation": "按本性选路",
          "how": "musl 原生支持就不外挂、bionic 缺就补齐 ↔ 道法自然：按目标平台本性"
                 "选交叉路径，不把一套做法硬套所有目标"}]},
    {"id": "qemu-user-bionic-limits", "name": "qemu-user 对 bionic 三连坎", "domain": "cross-reality",
     "gist": "qemu-user 8.2.2 跑不了 bionic 静态二进制：TLS 段对齐 8<64 / personality 被沙箱拒 / 动态 linker init SIGSEGV——运行级验证不可行，构建级完整。",
     "detail": "实测三连坎：①aarch64 bionic 静态报 TLS segment is underaligned: alignment "
               "is 8, needs 64 for ARM64 Bionic（qemu 已知限制）；②armv7 静态 person"
               "ality 系统调用被沙箱拒（Operation not permitted）；③动态 + libc.so 顶替 "
               "linker64 后 SIGSEGV（rc=139）。结论如实记录：Android 交叉产物只做构建级"
               "验证（file/readelf/链接通过），不谎称运行级通过。",
     "engineering": "落法：docs/37 §5.2 与 §7 遗留清单把三连坎逐条登记为环境限制；"
                    "HANDOFF-arm-deb.md §10 落账；toolchain catalog 的 qemu-user 条目"
                    "「已知边界」段即此概念——验证口径分「构建级/运行级」两档，不混为一谈。",
     "bridges": [
         {"system": "daoxue", "target": "principle:zhi-bu-zhi", "relation": "不可为即不为",
          "how": "qemu 跑不了 bionic 就如实降级为构建级验证 ↔ 知不知上：环境所限"
                 "明确标注，不伪造「实跑通过」"},
         {"system": "quantum", "target": "concept:qkern-page-discipline", "relation": "对齐纪律同构",
          "how": "TLS 段 8<64 对齐要求 ↔ 量子内核 4KiB 页纪律：两者都是「对齐不到"
                 "规定档位就不放行」的门禁，只是门禁发生的层不同"}]},
    {"id": "mingw-thread-variants", "name": "MinGW-w64 线程模型变体", "domain": "cross-reality",
     "gist": "同一 mingw-w64 交叉链按线程模型（win32/posix）与异常模型（sjlj/dwarf/seh）分变体，产物行为与依赖面随之不同。",
     "detail": "PE 查看器家族的 exe（peinfo.exe/peinfo32.exe）由 x86_64/i686-w64-mingw32-gcc "
               "13-win32 产出，file 报 PE32+ executable (console)，wine 9.0 仿真实跑验收。"
               "mingw-w64 的 triple 后缀决定线程模型：-win32（原生 Win32 线程）与 -posix"
               "（pthread 映射）影响 C11 threads/std::thread 可用性；选错变体的症状是链接期"
               "缺 pthread 符号或运行期行为差异——选型属构建配置决策，不在运行时暴露。",
     "engineering": "落法：Windows/VERSIONS.md 与 tools/wine-sni-bridge 记录双架构 PE 产物"
                    "口径；toolchain catalog 的 mingw-w64 条目登记 targets 与 file 验收结论；"
                    "parity_test 用 wine 跑各语言实现保证跨语言一致。",
     "bridges": [
         {"system": "llvm", "target": "target:x86_64-w64-mingw32", "relation": "目标三元组实例",
          "how": "mingw 线程变体是 triple 后缀的语义展开 ↔ llvm_docs 在册的 "
                 "x86_64-w64-mingw32 目标：同一个三元组，配置维度不止架构一项"},
         {"system": "plang", "target": "arch:x86-64", "relation": "配置维度提醒",
          "how": "plang 按真实目标架构归类（x86-64 在册）↔ 交叉实境补一刀：架构之外还有 OS ABI、"
                 "线程模型、异常模型三个配置轴，缺一不可复现"}]},
    {"id": "wine-emulation", "name": "Wine 仿真验收", "domain": "cross-reality",
     "gist": "Linux 宿主上没有 Windows，用 Wine 9.0 把 PE 产物跑起来做运行级验收——仿真≠真机，结论如实标注。",
     "detail": "peinfo.exe 由 wine 直接执行验证输出；wine --version 报 9.0 (Ubuntu "
               "9.0~repack-4build3)。仿真验收的口径边界：能验「PE 加载→入口→控制台输出」"
               "这条主链路，不能验「真实 Windows 内核行为/驱动/图形栈」——报告里区分"
               "「wine 实跑通过」与「真机未验」，不把仿真结论当全平台结论。",
     "engineering": "落法：toolchain catalog 的 wine 条目与 PE 查看器家族条目的 verify 字段"
                    "均写「wine 实跑」字样；docs/37 各系统安装教程对 Windows 产物同样"
                    "只给 wine 口径 + 真机路径指引。",
     "bridges": [
         {"system": "plang", "target": "lang:c", "relation": "产物验收手段",
          "how": "C 交叉产物在无 Windows 宿主由 wine 验收 ↔ plang 的 c 条目："
                 "验收手段按宿主能力选，仿真结论标注边界"},
         {"system": "daoxue", "target": "principle:zhi-bu-zhi", "relation": "仿真非真机",
          "how": "wine 实跑通过不写成「Windows 实测通过」 ↔ 知不知上："
                 "仿真与真机的差别自己先说清"}]},
    {"id": "ohos-sdk-layout", "name": "OpenHarmony SDK 目录布局", "domain": "cross-reality",
     "gist": "ohos-sdk 的 Linux 版是「外层压缩包 + 内层多 zip」两层结构：native/llvm/bin 放 clang wrapper，sysroot 放 musl 系统头与库，ets/js/previewer 各司其职。",
     "detail": "华为云镜像 ohos-sdk-windows_linux-public.tar.gz（2.4GB）解压后，native/"
               "toolchains 仍是 zip，需二次解压：native-linux-x64-6.0.0.47-Beta1.zip 与 "
               "toolchains-linux-x64-6.0.0.47-Beta1.zip。LLVM 在 native/llvm/bin："
               "aarch64/loongarch64/x86_64-unknown-linux-ohos-clang（clang 15.0.4，"
               "OHOS (dev) based on llvm-project）。动态 link 时 qemu -L 前缀要能解析 "
               "ld-musl-aarch64.so.1——ln -sfn usr/lib sysroot/lib 补软链即可。",
     "engineering": "落法：build-mobile.sh 的 OHOS_BIN 默认路径即此布局；docs/37 §5.3 给"
                    "下载→解压→二次解压→软链的完整顺序；toolchain catalog 的 ohos-sdk "
                    "条目登记 root/llvm/sysroot 三个 paths 与实测版本串。",
     "bridges": [
         {"system": "llvm", "target": "tool:clang", "relation": "同一前端多目标",
          "how": "ohos clang wrapper 与宿主 clang 18.1.3 同属 LLVM 家族 ↔ llvm_docs "
                 "在册的 clang 工具：SDK 布局再变，--target 三元组是稳定抓手"},
         {"system": "plang", "target": "arch:arm64", "relation": "架构覆盖面实例",
          "how": "ohos-sdk 一次覆盖 aarch64/loongarch64/x86_64 三个 triple ↔ plang "
                 "在册的 arm64 架构条目：一个 SDK 的多架构事实进编目"}]},
    {"id": "ndk-api-levels", "name": "NDK API 级别门控", "domain": "cross-reality",
     "gist": "NDK 的 clang wrapper 名即 API 级别：aarch64-linux-android21-clang 的 21 就是最低支持 Android 5.0——旧版打底与项目口径是两个不同的门。",
     "detail": "NDK r26d 的 wrapper 把 minSdkVersion 编进编译器名：API 21（Android 5.0）"
               "是旧版打底（classics 移动端最低目标），API 26（Android 8.0）是本仓"
               "Android 工程口径（android/ gradle min 26）。wrapper 实测存在："
               "aarch64-linux-android21-clang / armv7a-linux-androideabi21-clang / "
               "x86_64-linux-android21-clang，clang 17.0.2。API 级别同时决定可用符号面"
               "与可用指令集——选低级别是兼容决策，不是编译参数小事。",
     "engineering": "落法：build-mobile.sh 用 android21 wrapper 构建并记录「API 21 旧版"
                    "打底 / API 26 项目口径」双轨；docs/37 §5.2 与 android/ 工程 README "
                    "各自标注；toolchain catalog 的 android-ndk-r26d 条目 targets 字段"
                    "列出 21/26 两档。",
     "bridges": [
         {"system": "plang", "target": "lang:c", "relation": "符号面门控实例",
          "how": "API 21 下 bionic 符号面收缩 ↔ plang 的 c 条目：同一源码的可用库函数"
                 "随目标 API 级别变化，低级别是显式兼容决策"},
         {"system": "quantum", "target": "concept:qkern-lts", "relation": "基线选择同构",
          "how": "API 21 旧版打底 ↔ 量子内核 LTS 基线：两者都是「主动选旧基线换取"
                 "兼容面」的决策，且都要长期维护"}]},
    {"id": "dpkg-version-migration", "name": "deb 版本迁移税", "domain": "cross-reality",
     "gist": "semver 迁 odometer 格式时 A 段置 1（0001.0000.0000.0000.YYYYMMDD）——保证 dpkg --compare-versions 版本序不降级。",
     "detail": "classics deb 从旧 semver（如 0.1.0）迁到里程表格式时若直接写 "
               "0000.0000.0000.0000.20261024，dpkg 版本比较会判定为「降级」"
               "（0000 < 0001 的字段序问题）。解法即「迁移税」：A 段置 1。实测 "
               "dpkg --compare-versions 0001.0000.0000.0000.20261024 gt 0.1.0 "
               "与 gt 0000.0000.0000.0001.20261023 全部通过；四发行版变体"
               "（ubuntu1/~jammy1/~bpo12+1）后缀不变。",
     "engineering": "落法：classics-linux/build-debs.sh 的 VER 数组四发行版统一 "
                    "0001.0000.0000.0000.20261024；debian/changelog 与 quantum-kernel "
                    "desktop changelog 同步落账；docs/56 版本号体系文档的 monorepo "
                    "迁移表专列「deb 迁移税」一节。",
     "bridges": [
         {"system": "quantum", "target": "concept:qkern-patch-distribution", "relation": "序不降级同构",
          "how": "deb 版本序 gt 断言 ↔ 补丁增量序列 round-trip：两者都要求「新的必须"
                 "压过旧的」，版本/补丁序倒退即构建失败"},
         {"system": "daoxue", "target": "principle:shou-zhong", "relation": "迁移守中",
          "how": "A 段置 1 是不多不少的迁移税 ↔ 守中：迁移动作恰好在「不降级」这条"
                 "红线上，不多移也不少移"}]},
    {"id": "odometer-versioning", "name": "里程表版本号", "domain": "cross-reality",
     "gist": "NNNN.NNNN.NNNN.NNNN.YYYYMMDD 四段里程表：进位、循环归零、可选日期后缀；semver 强制场景用 to_semver() 映射 CalVer YYYY.MM.DD。",
     "detail": "去中心化版本体系的事实源是 version.py：PACKAGE_VERSION 现为 "
               "0000.0000.0000.0017.20261025。里程表语义——每段 4 位零填充，段内进位、"
               "段满归零进上一段（odometer 本义）；日期后缀可选，带日期即 CalVer 口径"
               "（年份打头显长青，cargo/npm 等 semver 强制场景 to_semver() → "
               "2026.10.24）。monorepo 各子项目独立推进：classics-rs 2026.10.24、"
               "novel-website 2026.10.24、deb 系 0001.0000.0000.0000.20261024，"
               "互不绑架。",
     "engineering": "落法：五处活版本（version.py / pyproject / main.go / console.ts / "
                    "report_viewer.ts）每次 bump 同步 + _self_check 断言；docs/56 记载"
                    "全体系；toolchain catalog 的 built 字段与各条目 version 均用此格式；"
                    "全量回归 1668→1683 项随版本推进。",
     "bridges": [
         {"system": "daoxue", "target": "principle:fan-zhe", "relation": "循环归零",
          "how": "里程表段满归零、进位上段 ↔ 反者道之动：版本号的循环不是重置而是"
                 "进位，旧段归零恰是新段开始的记号"},
         {"system": "quantum", "target": "concept:qkern-lts", "relation": "长青基线",
          "how": "CalVer 年份打头显长青 ↔ 量子内核 LTS 基线：版本号本身就是"
                 "「这个项目准备活很久」的声明"}]},
    {"id": "qkern-patch-distribution", "name": "内核补丁分发（工具链侧）", "domain": "cross-reality",
     "gist": "量子内核补丁靠工具链脚本把「增量序列」变成「可 round-trip 重放的产物」——补丁分发即编译部署。",
     "detail": "quantum-kernel 的补丁分发不是手工贴 patch，而是由 scripts/ 把「目标版本内核面」重生为分支补丁：gen_version_patch.py 按目标内核版本重生分支补丁（消除行号漂移，零 fuzz/offset），regen_base_patch.py 从源码重生基线补丁并做完整性硬校验，build.sh 三层构建验收（补丁 round-trip + 内核构建 + deb 产物）。deb 经 dpkg 分发（quantum-core_0.6.80 + xfce4-quantum_0.6.80），版本序由 dpkg-version-migration 的 A 段置 1 迁移税保证 gt 不降级。本仓没有「贴完即完」的错觉：补丁必须 round-trip 洁净回放 + 进入运行态（deb 可装）才算打完。",
     "engineering": "落法：与 comp 既有桥同构——abs-reloc-gate 的 readelf ABS64=0 门禁（构建期钉死可复现）、toolchain-security-response 的「分发即补丁」（编译型必须重编译部署）、dpkg-version-migration 的版本序 gt 断言（新必须压过旧）。三处共同把「补丁可达运行态」钉成硬门禁；native 只读层不替你打补丁，只把「已 round-trip + 可装」作为验收事实登记。",
     "bridges": [
        {"system": "quantum", "target": "concept:qkern-patch-distribution", "relation": "工具链镜像",
         "how": "scripts/gen_version_patch.py 重生分支补丁 + deb 分发 ↔ 量子内核补丁分发概念：comp 工具链是量子内核补丁分发的工程实现面，补丁 round-trip 洁净 + deb 可装即「打完」"}]},
]

# ---- 概念级桥接自动登记：语言编译需要 15 条 → plang:lang:<id>（实测证据）----
def lang_need_entries() -> List[dict]:
    """15 种实测语言的「编译需要」明细 + 1 条 needs_verify 汇总（其余 146 种）。"""
    out: List[dict] = []
    for ln in LANG_NEEDS:
        out.append({
            "id": f"need-{ln['lang']}",
            "name": f"{ln['lang']} 编译需要",
            "domain": "lang-need",
            "gist": f"驱动：{ln['driver']}；典型产物：{ln['artifact']}。",
            "detail": ln["note"],
            "lang": ln["lang"],
            "probe_id": ln.get("probe_id", ln["lang"]),
            "driver": ln["driver"],
            "artifact": ln["artifact"],
            "evidence_status": "probe_verified",   # 证据回填见 build()：取自 plang probe_results
            "bridges": [{"system": "plang", "target": f"lang:{ln['lang']}",
                         "relation": "同语言条目",
                         "how": "plang 161 语言条目；本条登记其编译需要"}],
        })
    out.append({
        "id": "need-rest-unverified",
        "name": "其余语言的编译需要（汇总待核实）",
        "domain": "lang-need",
        "gist": "plang 未实测的 146 种语言，其驱动工具与产物形态逐条未核实。",
        "detail": "只登记汇总事实：这些语言在 plang 中存在条目且有执行模型分类，"
                  "但本轮未逐条验证工具链；需要时按同一格式（驱动/产物/证据）补齐，"
                  "不把推断当事实。",
        "evidence_status": "needs_verify",
        "bridges": [{"system": "plang", "target": "model:*", "relation": "分类已登记",
                     "how": "未实测语言的执行模型分类已在 plang，编译需要待逐条补"}],
        "needs_verify": "146 种语言的工具链明细逐一未核实；按语言逐个补证据后再拆分登记",
    })
    return out


def load_probe() -> Dict[str, dict]:
    """从 plang taxonomy 读 probe_results，供实测证据回填。"""
    p = CONCEPTS_DIR / "plang_taxonomy.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    return {r["id"]: r for r in doc.get("probe_results", [])}


ENGINEERING: Dict[str, str] = {
    # 轴1 编译流水线
    "pipeline-overview": "落法：本仓库是这条流水线的活样本——纯标准库 Python 走解释执行加 .pyc 缓存，"
                         "CI 里 python -m build 打成 sdist/wheel；src/go 则由同一条 tag 流水线"
                         "交叉编译七个平台的二进制。同一份代码、两条流水线，产物形态完全不同。",
    "lex-parse": "落法：本仓库不写解析器，但每天都在经历这一步——改了 .py 之后 mtime 变化会触发"
                 "重新生成 .pyc；这也解释了为何清掉 __pycache__ 后首次启动略慢。",
    "sema": "落法：Python 不做静态类型检查，类型错往往运行到那一行才炸。本仓库的补法是"
            "把运行期的错提前到构建期——各 build_*.py --check 就是这么来的，用工程手段"
            "补静态语义检查的缺口。",
    "ir": "落法：本仓库无 IR 层。其价值在于提醒：写多目标生成器之前先想清目标 IR 是什么，"
          "否则每换一个目标就要重写一遍，这正是 IR 存在的唯一理由。",
    "opt": "落法：Python 侧不指望字节码优化，宁可读得懂。真要提速时本仓库的取舍是少做事："
           "缓存只读结果、能一次扫描就不扫两遍，而不是依赖编译器的优化 pass。",
    "codegen": "落法：未直接落地。唯一沾边的是 report_viewer.html 由 tools/gen_report_viewer.py "
               "从 report_viewer.ts 生成——生成而非手抄，是单一事实源原则在这里的具体形态。",
    "object-file": "落法：未落地，本仓库不产出 .o/.obj。认知价值在于 Windows 的 PE 与 Linux 的 ELF "
                   "符号规则不同，跨端构建失败多源于此，CI 里七个平台的矩阵正是为此而设。",
    "link": "落法：Python 侧没有传统链接期，依赖在 import 时解析；这也是零运行时依赖原则"
            "得以成立的原因——没有第三方库要链接，就没有链接期的版本地狱。",
    # 轴2 工具链家族
    "gnu-toolchain": "落法：本仓库自身不产出 C 产物，不依赖 GNU 工具链；但在宿主机上做只读诊断时，"
                     "不少底层信息恰恰来自这些工具链产出的二进制与系统接口。",
    "llvm-toolchain": "落法：未落地。其工具与目标三元组与 data/llvm_docs.json 核对后登记，"
                      "仅作工具链认知，不声称本机装有 clang。",
    "msvc": "落法：未落地。仓库对 Windows 的支持一律走 PowerShell 原生接口，"
            "不需要 MSVC 工具链参与。",
    "mingw": "落法：未落地。交叉编译 Windows 产物目前只用 Go 的 GOOS=windows 原生交叉能力，"
             "不需要 MinGW 这一层。",
    "rust-toolchain": "落法：未落地。本机是否装有 rustc/cargo，以 plang probe 实测登记的 15 种语言"
                      "清单为准，不在清单里就不声称。",
    "go-toolchain": "落法：真落地。src/go/main.go 由 CI 用 go build 交叉编译 linux/windows/darwin "
                    "配 amd64/arm64 及 riscv64，产物附到 Release；这是本仓库唯一的原生编译产物。",
    "jvm-toolchain": "落法：未落地。Java 若在场也只用其认知登记，本仓库不产生 JVM 产物；"
                     "probe 实测清单里 java 已通过八面能力契约。",
    "dotnet-toolchain": "落法：未落地。probe 实测清单中 fsharp 已通过，但本仓库自身无 .NET 产物。",
    "beam-toolchain": "落法：未落地。Erlang/BEAM 仅作生态认知条目登记。",
    "compile-interpret": "落法：本仓库横跨两端——Python 在解释端并带 .pyc 这一中间形态，"
                         "Go 在完全编译端，Deno 的 TypeScript 在运行时即时编译的中间地带；"
                         "别把它们当成同一个模型。",
    # 轴3 构建系统
    "make": "落法：未落地，仓库无 Makefile。值得记的反面教材是：手写 Make 容易把依赖写漏，"
            "所以本仓库把一致性交给构建脚本加 --check，而不是靠人记得跑某条命令。",
    "cmake": "落法：未落地。跨平台构建的诉求在本仓库由 Go 交叉编译加 Python 打包两件事满足，"
             "没有引入 CMake 的必要。",
    "ninja": "落法：未落地。本仓库构建规模远未到需要 Ninja 提速的程度，先别引入构建期工具债。",
    "meson": "落法：未落地。认知登记：Meson 的声明式可读性优于手写 Make，代价是多一层依赖。",
    "scons": "落法：未落地。宿主装有 SCons 4.5.2 但本仓库不引入；认知价值在于它与 make "
             "的路线差异——依赖扫描自动、配置即 Python 代码。",
    "bazel": "落法：未落地。多语言大仓才需要 Bazel 的增量与远端缓存，本仓库规模不到那个量级。",
    "gradle-maven": "落法：未落地。JVM 生态专属，本仓库无 JVM 产物。",
    "native-build": "落法：真落地但局限在两种语言——Python 侧用 python -m build（PEP 621 与 "
                    "setuptools），Go 侧用 go build；两者都是语言原生，不必额外构建系统。",
    "ide-build": "落法：未落地。CI 是权威构建路径，IDE 构建结果从不作为交付依据，"
                 "以免出现本地能编、远端挂掉的假象。",
    "container-toolchain": "落法：真落地。system-optimizer/Dockerfile 多阶段构建"
                           "（builder 经 tools/syspkg 产 wheel/sdist，终镜像非 root 零新增"
                           "依赖）+ docker-compose.yml 把最小权限红线固化为声明式配置"
                           "（read_only / cap_drop: ALL / no-new-privileges）；toolchain "
                           "catalog 的 docker-support 条与本概念互为 counterpart，"
                           "只读编目不构建。",
    "lint-gate": "落法：部分落地（shellcheck 一环，#652）。scripts/check_shell_lint.sh "
                 "白名单门禁（本仓自有 11 个 .sh，排除 quantum-kernel 内核树与 plang "
                 "样例，附防漏网扫描）+ .github/workflows/lint-shell.yml 接入 CI（apt "
                 "安装保证在场）+ system-optimizer/tests/test_lint_gate.py 白名单守卫；"
                 "clang-format/clang-tidy 与 hadolint/actionlint 宿主仅部分在位、未接入，"
                 "如实挂 needs_action。约束延续：不引入新的第三方 CI 动作依赖。",
    # 轴4 目标产物
    "artifact-static-lib": "落法：未落地。零运行时依赖的原则决定了本仓库不产出也不链接静态库。",
    "artifact-shared-lib": "落法：未落地。动态库意味着版本地狱，纯标准库实现在这里省下的是长期维护成本。",
    "artifact-exe": "落法：真落地，仅限 Go 侧产出原生可执行三系统二进制；Python 侧刻意不产出独立 exe，"
                    "保持源码可审计，也避免打包解释器带来的安全争议。",
    "artifact-bytecode": "落法：真落地。Python 的 __pycache__ 下的 .pyc 就是它；清理这类缓存是安全的，"
                         "因为可以再度生成，这也是本项目自身清理任务的常见项之一。",
    "artifact-wasm": "落法：未落地。前端 src/deno/web/app.js 是原生 JS，未引入 wasm 产物。",
    "artifact-ir": "落法：未落地。本仓库无 IR 层，故无 IR 落盘；quantum 侧的 QIR 仅作认知登记。",
    "artifact-pkg": "落法：真落地。CI 产出 sdist 与 wheel，打 v 开头 tag 时自动附到 GitHub Release；"
                    "这是本仓库对外的交付形态。",
    "artifact-container": "落法：真落地。system-optimizer/Dockerfile 多阶段构建 sysweeper 镜像"
                          "（终镜像非 root、除 Python 外零新增依赖），docker-compose.yml 以 "
                          "read_only / cap_drop: ALL / no-new-privileges 固化最小权限；"
                          "镜像即本概念的容器产物形态，与 container-toolchain 概念互为印证"
                          "（toolchain catalog 只读编目不构建）。",
    # 轴5 语言编译需要（16 条）
    "need-python": "落法：本仓库主力语言，零第三方依赖是硬约束；解释执行加 .pyc 缓存，"
                   "交付时打包为 wheel 与 sdist。",
    "need-javascript": "落法：前端 src/deno/web/app.js 用它，不经打包器直接由静态页加载，"
                       "以免引入另一条前端构建链。",
    "need-typescript": "落法：真落地。src/deno/console.ts 与 report_viewer.ts 由 Deno 直接执行，"
                       "不经手写 tsconfig 与打包步骤；这也决定了 report_viewer.html 必须用脚本"
                       "反向生成并靠 sha256 守住一致性。",
    "need-go": "落法：真落地。src/go/main.go 编译为七种平台二进制；Go 侧刻意保持单文件、"
               "零外部依赖，交叉编译时无需下载模块。",
    "need-rust": "落法：未落地。probe 实测通过不意味着本仓库用它——清单登记的是语言能力，"
                 "不是本项目的依赖。",
    "need-c": "落法：未落地。纯标准库原则排除了写 C 扩展这条路。",
    "need-cplusplus": "落法：未落地。同理，不引入需要编译的外部原生扩展。",
    "need-java": "落法：未落地。仅作 JDK 相关子系统的认知参照。",
    "need-ruby": "落法：未落地。probe 实测通过八面能力契约，但不参与本仓库构建。",
    "need-perl": "落法：未落地。经典脚本语言的 POSIX 能力基准线。",
    "need-bash": "落法：真落地。Linux 与 macOS 侧的清理和巡检由本地 shell 执行；"
                 "命令拼接必须走白名单参数数组，不做字符串拼接后的注入。",
    "need-awk": "落法：未落地。POSIX 文本处理能力的认知位。",
    "need-tcl": "落法：未落地。Tcl 与 Expect 自动化能力仅登记不依赖。",
    "need-fsharp": "落法：未落地。函数式与 .NET 生态的认知位。",
    "need-makefile": "落法：未落地。make 语法作为能力面的一员登记，Makefile 本身也是一种语言，"
                     "但仓库不用它做构建。",
    "need-rest-unverified": "落法：诚实边界。其余 146 种语言不逐条臆造，汇总为一条待核实。"
                            "宁可留白，也不假装测过。",
    # ---- v0.6.63 续：导入学习应用（SonicBoom / Linux 7.3）----
    "mlir": "落法：未落地为本仓库编译器。其价值在于印证『IR 层可替换』——本仓库无 IR 层，"
            "但写多目标生成器前先想清目标 IR 是什么，正是 MLIR 多级降级的反题。",
    "kernel-fusion": "落法：未落地。本仓库 Python 侧不指望字节码优化，宁可读得懂；"
                     "真要提速的取舍是少做事（缓存只读结果），与『等价融合减少中间读写』同源思路。",
    "bpf-binfmt": "落法：未落地。其『每 exec 程序化决定解释器』与 CLI 子命令契约（认不出即拒）"
                  "同属『入口策略化、不靠手写第二份真相』的纪律。",
    "plugin-install-layout": "落法：未落地，本仓库无 QML 插件产物；但同一纪律已在用——CI 产物"
                             "必须落到 Release 可发现位置（打 tag 即附资产），report_viewer 生成物"
                             "靠 sha256 守护漂移。『装不上的产物等于没做』，对本仓库即『发不出去的"
                             "交付等于没做』。",
    # ---- v0.6.73 续：黑箱逆向（UPX / MinGW / GDB 实测）----
    "upx-packer-signature": "落法：真落地。native/reverse.py 的 binary_scan() 按 UPX! marker"
                            "偏移、UPX0/1/2 节名、数据节熵>7.5 三特征判 packed_guess；"
                            "数据固化在 data/reverse_docs.json（win64→121050/48.50%、"
                            "win32→126378/53.22%），换口径必须显式改测试。",
    "entropy-signal": "落法：真落地。binary_scan() 逐节算香农熵并回传 whole_entropy；"
                      "高低熵锚定测试钉死读数（裸本 5.898→壳本 7.035，strip 1.522→1.235）。",
    "binfmt-anatomy": "落法：真落地。_pe_sections() 走 MZ→e_lfanew→PE\\0\\0→COFF→"
                      "可选头→节表全链，magic 0x10B/0x20B 分 PE32/PE32+，ELF 侧读 "
                      "machine；合成最小 PE 的测试保住偏移算术（pe_off+4+20）不漂移。",
    "blackbox-debug": "落法：真落地（方法层）。tasks/reverse.py 的 reverse_gdb_playbook "
                      "把四连固化为可执行清单；GDB 只读观察不下断写内存——调试是提问，"
                      "不是修改，与全仓只读诊断红线一致。",
    "symbol-visibility": "落法：真落地。strip 前后对照（16000→14472B、熵 1.522→1.235）"
                         "已入测试常量；二进制扫描前先看符号残量，决定静态解剖还是动态路径。",
    "crossbuild-sample": "落法：真落地。reverse 黑箱任务的自造样本由 mingw GCC 13 双格式产出"
                         "（PE32 237482B/17 节、PE32+ 249562B/19 节），裸本/壳本/strip 本"
                         "三态对照；wine 启动失败的事实同样登记，不写成『已动态验证』。",
    # ---- 位宽与寻址世代（legacy 子系统位宽/PAE 落地；0028 轮全档实测）----
    "bit8-era": "落法：真落地（编译+运行双实测）。bitwidth_report 保持 MAME/FCEU 存在性只读"
                "探测（不启动、不下载 ROM）；构建批次 sdcc -mz80 编译闭环"
                "（exit 0 + ihx 358B + Z80 指令指纹可核）；补全批次运行层闭合："
                "自含 Z80 内核 research/comp/z80core.py（基础集+CB+ED 常用+DD/FD，"
                "已知答案自测 22/22）+ z80_runner.py 实跑 hello8run.ihx 618B"
                "（OUT(01) 流『Z80-RT-OK68\\n』、_counter@8000=0x68 与手算一致、"
                "HALT 停机 PC=0264、196 指令 ~1710 T 态标称），dz80 独立反汇编"
                "交叉核对 197/197 助记符一致。内核边界诚实文档化：非参考级实现"
                "（不建模中断接受/精确 T 态），覆盖范围见 docstring。",
    "real-mode-16": "落法：真落地（编译+运行双实测）。dos_report/busybox_report 保持 "
                    "which 只读探测 + data/dos.json 五条知识坐标；构建批次新增实测层："
                    "bcc -Md -0 产 COM（228B，int 21h/20h 指纹）、dosbox 0.74-3 无头"
                    "实跑（SDL dummy + -c mount + C:\\ 显式路径——-c 'C:' 换驱对后续"
                    "命令不生效须写全路径，已实测）、as86+ld86 -d 手写链 + int 21h "
                    "3Ch/40h/3Eh 文件往返（宿主机回读 R7.TXT 18B 成功）。工程坑已入账："
                    "ld86 -d origin 0 与 COM 装载基址 0x100 的错位，手写汇编 #label "
                    "立即数须自加 $100。sysmap 关联图仍把遗留 DOS 环境挂 livemedia"
                    "（启动介质制作）。",
    "protected-32": "落法：真落地（三路径实测）。bitwidth_report 保持 qemu-system-i386/"
                    "wine/32 位用户态存在性探测；构建批次新增：i586-pc-msdosdjgpp-as+ld "
                    "交叉汇编链接（-e _start 干净构建，entry 符号警告已消除）、go32 "
                    "DPMI exe dosbox 实跑 exit 0（DPMI int 21h 反射）、gcc -m32 宿主"
                    "实跑 exit 0。补全批次 #690 闭合 C 编译路径缺口：DJGPP GCC/libc/"
                    "stub 不在 apt，自上游 andrewwutw/build-djgpp v3.4 取 Linux64 预构建"
                    "（GCC 12.2.0，80,596,981B，sha256 8464f170…），i586-pc-msdosdjgpp-gcc "
                    "-O2 编译 hello32c.c → hello32c.exe 197852B（MZ+COFF+go32 extender），"
                    "dosbox 0.74-3 实跑双面证据（OUT.TXT 18B / Z32C.TXT 16B 均 "
                    "\"Z32C-RT-OK55\\nFB\\n\"，0xFB 独立复算一致，rc=0）。三工程坑入账："
                    "①wget 中断尾部半块 + aria2 续传拼接致 bzip2 CRC 坏，须从头干净重下；"
                    "②dosbox dpmi=true 不被 DJGPP 12.2 go32 桩接受，须自带 CWSDPMI."
                    "EXE(csdpmi7b)；③批处理+CWSDPMI 下 %ERRORLEVEL% 不 propagate 且 "
                    "dosbox 退出挂起（rc=124），进程完成证据取直跑 rc=0 + fclose 写全，"
                    "退出码面不伪证。",
    "pae-extension": "落法：真落地（检测 + 命令文本）。pae_report 读 cpuinfo pae 标志/"
                     "内核位宽/MemTotal，给官方命令文本（XP boot.ini /PAE、Vista/Win7 "
                     "bcdedit pae ForceEnable、Linux HIGHMEM64G/-pae 内核）；诚实边界写入"
                     "tasks/legacy.py 的 legacy_pae：XP 全版本上限即 4GB，PAE 的意义是 "
                     "DEP/NX 与热插拔。红线：只读检测，不代改任何引导配置。",
    "long-mode-64": "落法：真落地（读标志+编译实测）。bitwidth_report/pae_report 读 "
                    "uname.machine + cpuinfo lm/pae 标志；本批 gcc -m64 编译实跑闭环"
                    "（ELF 64-bit x86-64，exit 0）。沙箱实测 x86_64/64 位/lm✓/pae✓，"
                    "64 位内核结论即『不需要也不支持 PAE』。",
    "simd-128": "落法：真落地（编译实测）。gcc 13.3.0 __int128（sizeof=16、hi/lo 算术"
                "验证）+ SSE2 movdqa XMM 内存往返（4×int32 一致）；ELF 仍报 64 位——"
                "128 位是数据通路宽度不是进程位宽，概念文本明载此边界。量子侧边界同批"
                "核查：qiskit/cirq 不可导入、apt 无候选，『位元量子架构』无对应物，"
                "桥接 quantum:qubit 标明范式分界而非能力延伸。",
    "retro-dos-stack": "落法：真落地（两车道）。native/legacy.py 的 _load_refs 消费 "
                       "data/ 下 dos/busybox/dosbox 三个 JSON 与 compat_docs 的 "
                       "bitwidth/pae 主题（共 14 条知识回链）；LEGACY_CHECKS 五维度"
                       "全部回链真实 key；tasks/legacy.py 现 5 个只读任务"
                       "（dos/busybox/dosbox/bitwidth/pae）。只读诊断车道不启动模拟器"
                       "的边界不变；用户显式请求的构建车道（本批）可装可跑，产物只落"
                       "用户指定目录。",
}

def apply_engineering(concepts: List[dict]) -> None:
    """给每个概念注入「工程落法」（v0.6.62 字段齐备化）。

    与 baigong/zhuangzi/datong/apilab 的 engineering 同义：这一条对本仓库意味着什么。
    真落地就写真构件（如 CI 的 `python -m build`、Go 七平台交叉编译），未落地就写
    「未落地」并给出将来要接时的约束——**不把没投产的能力写成已具备**。
    """
    for c in concepts:
        eng = ENGINEERING.get(c["id"])
        if eng:
            c["engineering"] = eng


# v0.6.62 续：回链大同（使综摄系统双向可达，仅确凿关系）
DATONG_BACKLINKS = [
    {"from": "comp:codegen", "system": "datong", "target": "concept:gu",
     "relation": "翻译", "how": "代码/产物一次性固化 ↔ 固：不可变发布物（状态固化）"},
    {"from": "comp:cmake", "system": "datong", "target": "concept:yuzhou-gongmin",
     "relation": "翻译", "how": "跨平台一次编写处处构建 ↔ 宇宙公民：跨端同口径"},
]


def build() -> dict:
    concepts = CONCEPTS + lang_need_entries()
    apply_engineering(concepts)
    probe = load_probe()

    for c in concepts:
        if c["domain"] == "lang-need" and c.get("evidence_status") == "probe_verified":
            # probe_id 显式覆盖（plang 中 lang_index=cplusplus 而 probe_results=cpp）
            pr = probe.get(c.get("probe_id") or c.get("lang", ""), {})
            c["evidence"] = {
                "source": "data/concepts/plang_taxonomy.json#probe_results",
                "status": pr.get("status", ""),
                "returncode": pr.get("returncode"),
                "sample": pr.get("sample", ""),
                "contract_kv": {k: v for k, v in (pr.get("kv") or {}).items()},
            }
            if not pr:
                c["evidence_status"] = "needs_verify"
                c["needs_verify"] = f"plang probe_results 未见 {c.get('lang')} 实测记录"

    bridges: List[dict] = []
    for c in concepts:
        for b in c.get("bridges", []):
            bridges.append({
                "from": f"comp:{c['id']}",
                "system": b["system"],
                "target": b["target"],
                "relation": b.get("relation", ""),
                "how": b.get("how", ""),
            })
    bridges.extend(DATONG_BACKLINKS)

    by_domain: Dict[str, List[str]] = {d["domain"]: [] for d in DOMAINS}
    for c in concepts:
        by_domain.setdefault(c["domain"], []).append(c["id"])

    verified = sum(1 for c in concepts
                   if c["domain"] == "lang-need"
                   and c.get("evidence_status") == "probe_verified")

    return {
        "_meta": {
            "schema": SCHEMA,
            "built_by": "research/comp/build_comp.py",
            "main_root": "wordbuddy-github",
            "title": "编译与工具链概念系统（以 wordbuddy-github 为主目录）",
            "system_root": "wordbuddy-github",
            "version": "0000.0000.0000.0072.20261026",
            "concept_total": len(concepts),
            "axes": ["pipeline", "toolchain", "build", "artifact", "lang-need", "reverse", "bitwidth", "bringup", "cross-reality"],
            "lang_need_verified": verified,
            "lang_need_total": sum(1 for c in concepts if c["domain"] == "lang-need"),
            "bridge_count": len(bridges),
            "honesty": "语言编译需要仅对 plang probe 实测通过的 15 种语言逐条登记明细"
                       "（证据取自 probe_results）；其余 146 种汇总为一条 needs_verify，"
                       "不逐条臆造工具链形态。",
            "redline_note": "本概念系统只读登记，不驱动任何真实编译；编译动作属各工具链自身。",
            "import_note_065": "v0.6.65 导入学习应用（pepsipu/aski，2026-10-23 浅克隆逐文件核对）："
                       "新增 aski-pipeline 概念——约 1077 行 Rust 的最小编译器骨架"
                       "（IStream→Tokenizer→Parser→Program 四段管线 + NASM 分节输出 + "
                       "寄存器显式暴露），桥接 daoxue 道法自然与 plang 的 rust/assembly；"
                       "aski 仓库无许可证，默认保留所有权利，本仓只学模式不拷代码。",
            "import_note_068": "v0.6.68 导入分析学习应用（massgravel / CF-Workers-TGProxy / "
                       "is-rust-gui-ready / dsh-our-free-model，2026-10-24 只读 WebFetch 抓取）："
                       "补回 #589 遗漏同步的 qkern-patch-distribution（cross-reality，桥 quantum）；"
                       "新增 license-compliance-boundary（reverse，桥 daoxue zhi-bu-zhi）——"
                       "以 massgrave.dev 激活绕过工具集为反面教材，把『许可规避』类工具钉为"
                       "合规分析对象、绝不编目为可装可跑；另三仓（边缘多 lane 代理 / Rust GUI "
                       "成熟度清单 / 插件化协议适配省 Token）仅作 docs/59 学习笔记，不新增概念。",
        },
        "domains": DOMAINS,
        "concepts": concepts,
        "bridges": bridges,
        "by_domain": by_domain,
    }


def check(doc: dict) -> List[str]:
    errs: List[str] = []
    sys.path.insert(0, str(ROOT / "src" / "python"))
    from sysweeper.concepts import _common

    if doc.get("_meta", {}).get("schema") != SCHEMA:
        errs.append("schema 不符")

    def load_other(name: str) -> dict:
        return json.loads((CONCEPTS_DIR / f"{name}_taxonomy.json")
                          .read_text(encoding="utf-8"))

    def load_data(name: str) -> dict:
        return json.loads((ROOT / "src" / "python" / "sysweeper" / "data" / name)
                          .read_text(encoding="utf-8"))

    plang = load_other("plang")
    netsys = load_other("netsys")
    daoxue = load_other("daoxue")
    datong = load_other("datong")
    quantum = load_other("quantum")
    llvm_docs = load_data("llvm_docs.json")

    plang_langs = set(plang.get("lang_index", {}))
    plang_models = {m["model"] for m in plang.get("execution_models", [])}
    plang_archs = {a["arch"] for a in plang.get("target_archs", [])}
    netsys_mods = {m["id"] for m in netsys.get("modules", [])}
    dx_principles = {p["id"] for p in daoxue.get("principles", [])}
    datong_ids = {c["id"] for c in datong.get("concepts", [])} | {
        p["id"] for p in datong.get("principles", [])}
    quantum_ids = {c["id"] for c in quantum.get("concepts", [])}
    llvm_tools = set((llvm_docs.get("tools") or {}).keys())
    llvm_targets = set(llvm_docs.get("targets") or [])

    # 1) 轴合法 / id 唯一 / gist 非空
    valid_domains = {d["domain"] for d in doc["domains"]}
    ids = set()
    for c in doc["concepts"]:
        if c["id"] in ids:
            errs.append(f"概念 id 重复：{c['id']}")
        ids.add(c["id"])
        if c["domain"] not in valid_domains:
            errs.append(f"{c['id']} 轴 {c['domain']} 未登记")
        if not c.get("gist"):
            errs.append(f"{c['id']} 缺 gist")
        # v0.6.62 字段齐备：每个概念必须有「工程落法」，不得只有原理没有用法
        if not str(c.get("engineering") or "").strip():
            errs.append(f"{c['id']} 缺 engineering（工程落法）")

    # 2) 反查视图自洽
    inverted: Dict[str, List[str]] = {}
    for c in doc["concepts"]:
        inverted.setdefault(c["domain"], []).append(c["id"])
    for d in set(inverted) | set(doc["by_domain"]):
        if inverted.get(d, []) != doc["by_domain"].get(d, []):
            errs.append(f"by_domain 视图与 concepts 不一致：{d}")

    # 3) 语言编译需要：实测必须带证据，needs_verify 必须带原因
    for c in doc["concepts"]:
        if c["domain"] != "lang-need":
            continue
        st = c.get("evidence_status")
        if st == "probe_verified":
            ev = c.get("evidence") or {}
            if ev.get("status") != "实测通过" or not ev.get("contract_kv"):
                errs.append(f"{c['id']} 标 probe_verified 但证据不完整")
        elif st == "needs_verify":
            if not c.get("needs_verify"):
                errs.append(f"{c['id']} needs_verify 缺原因")

    # 4) 桥接无悬空
    for b in doc["bridges"]:
        sysname, tgt = b["system"], b["target"]
        kind, _, val = tgt.partition(":")
        if sysname == "plang":
            if kind == "lang" and val not in plang_langs:
                errs.append(f"桥接悬空：plang 无语言 {val}")
            elif kind == "model" and val != "*" and val not in plang_models:
                errs.append(f"桥接悬空：plang 无执行模型 {val}")
            elif kind == "arch" and val not in plang_archs:
                errs.append(f"桥接悬空：plang 无架构 {val}")
            elif kind not in ("lang", "model", "arch"):
                errs.append(f"plang 桥接 target 形态未知：{tgt}")
        elif sysname == "netsys":
            if kind != "module" or val not in netsys_mods:
                errs.append(f"桥接悬空：netsys 无模块 {val}")
        elif sysname == "daoxue":
            if kind != "principle" or val not in dx_principles:
                errs.append(f"桥接悬空：daoxue 无原则 {val}")
        elif sysname == "llvm":
            if kind == "tool" and val not in llvm_tools:
                errs.append(f"桥接悬空：llvm_docs 无工具 {val}")
            elif kind == "target" and val not in llvm_targets:
                errs.append(f"桥接悬空：llvm_docs 无目标三元组 {val}")
            elif kind not in ("tool", "target"):
                errs.append(f"llvm 桥接 target 形态未知：{tgt}")
        elif sysname == "datong":
            if kind not in ("concept", "principle") or val not in datong_ids:
                errs.append(f"桥接悬空：datong 无{'原则' if kind == 'principle' else '概念'} {val}")
        elif sysname == "quantum":
            if kind != "concept" or val not in quantum_ids:
                errs.append(f"桥接悬空：quantum 无概念 {val}")
        else:
            errs.append(f"桥接目标系统未登记：{sysname}")

    # 5) counts 自洽
    m = doc["_meta"]
    if m["concept_total"] != len(doc["concepts"]):
        errs.append("counts.concept_total 漂移")
    if m["lang_need_verified"] != sum(
            1 for c in doc["concepts"] if c.get("evidence_status") == "probe_verified"):
        errs.append("counts.lang_need_verified 漂移")
    if m["lang_need_total"] != sum(1 for c in doc["concepts"]
                                   if c["domain"] == "lang-need"):
        errs.append("counts.lang_need_total 漂移")
    if m["bridge_count"] != len(doc["bridges"]):
        errs.append("counts.bridge_count 漂移")

    # 6) 加载器可用性
    if OUT.exists():
        try:
            if _common.load_taxonomy(OUT.name) != json.loads(
                    OUT.read_text(encoding="utf-8")):
                errs.append("concepts 共享加载器与磁盘内容不一致")
        except Exception as ex:  # noqa: BLE001
            errs.append(f"concepts 共享加载器读取失败：{ex}")
    else:
        probe_path = _common.data_path("plang_taxonomy.json")
        if not probe_path.exists():
            errs.append(f"concepts 共享加载器路径机制失效：{probe_path} 不存在")

    return errs


def report(doc: dict) -> None:
    print(f"编译概念条目：{doc['_meta']['concept_total']} 个\n")
    print("按轴：")
    for d in doc["domains"]:
        print(f"  {d['domain']:<10} {len(doc['by_domain'].get(d['domain'], [])):>2}  {d['label']}")
    m = doc["_meta"]
    print(f"\n语言编译需要：{m['lang_need_verified']} 实测 / 共 {m['lang_need_total']} 条")
    nv = [c["id"] for c in doc["concepts"] if c.get("needs_verify")]
    print("待核实：", nv or "无")
    print(f"桥接边：{m['bridge_count']} 条")
    by_sys: Dict[str, int] = {}
    for b in doc["bridges"]:
        by_sys[b["system"]] = by_sys.get(b["system"], 0) + 1
    for s, n in sorted(by_sys.items()):
        print(f"  → {s:<8} {n}")


def main(argv: List[str]) -> int:
    doc = build()
    if "--report" in argv:
        report(doc)
        return 0
    errs = check(doc)
    if errs:
        for e in errs:
            print("✗", e)
        return 1
    if "--check" in argv:
        print(f"✓ 校验通过：{doc['_meta']['concept_total']} 个概念 / "
              f"语言编译需要 {doc['_meta']['lang_need_verified']} 实测 / "
              f"{doc['_meta']['bridge_count']} 条桥接无悬空")
        return 0
    from datetime import datetime, timezone
    doc["_meta"]["generated_at"] = datetime.now(timezone.utc).isoformat()
    errs = check(doc)
    if errs:
        for e in errs:
            print("✗ 写盘前校验失败：", e)
        return 1
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ 已构建 {OUT}：{doc['_meta']['concept_total']} 个概念")
    report(doc)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
