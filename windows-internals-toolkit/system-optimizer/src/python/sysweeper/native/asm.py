"""汇编语言优化只读子系统（asm）：探测汇编器（nasm/yasm/gas/llvm-mc/gcc -S），并给出优化要点
（SIMD：SSE/AVX/NEON/SVE/RVV；对齐 / 寄存器 / 缓存 / 分支 / 指令选择 / 内联约束），附 LLVM 交叉编译汇编指引。

只读：只探测汇编器 + 给优化要点与交叉汇编指引；绝不编译、绝不改源码、绝不写汇编文件。
"""

from __future__ import annotations

import shutil
import subprocess


# ── 汇编器探针（id, 中文名）── 只读 which + --version ──
ASSEMBLERS = (
    ("nasm_report", "NASM 汇编器（x86/x86_64 主流）"),
    ("yasm_report", "YASM 汇编器（NASM 语法超集）"),
    ("gas_report", "GAS（GNU Assembler，AT&T/Intel 语法）"),
    ("llvm_mc_report", "LLVM MachineCoder（llvm-mc）"),
    ("gcc_s_report", "GCC -S（从 C 生成汇编，观察编译器产出）"),
)

# ── 各架构 SIMD / 向量扩展矩阵（按时间序列逐步扩充；CHANGELOG 记录）──
# (架构, 扩展, 中文说明, 编译标志)
SIMD_MATRIX = (
    ("x86_64", "SSE2/SSE3/SSSE3/SSE4.1/SSE4.2", "128 位基础 SIMD，标量循环的天然替代",
     "gcc/clang 默认开启 SSE2；更高档 -msse4.2"),
    ("x86_64", "AVX/AVX2", "256 位整数/浮点 SIMD，吞吐量翻倍",
     "-mavx2 或 -march=haswell"),
    ("x86_64", "AVX-512（F/CD/BW/VL/DQ）", "512 位 SIMD，密度最高（留意降频/功耗权衡）",
     "-mavx512f 或 -march=skylake-avx512 / cascadelake"),
    ("aarch64", "NEON（Advanced SIMD）", "128 位 SIMD，AArch64 基线标配",
     "默认开启（AArch64 自带）"),
    ("aarch64", "SVE / SVE2", "可伸缩向量（128–2048 位按硬件长度自适应）",
     "-march=armv9-a+sve2 / -mcpu=neoverse-v2"),
    ("arm (32)", "NEON", "32 位 ARM 的 SIMD 扩展",
     "-mfpu=neon -march=armv7-a"),
    ("riscv64", "RVV（RISC-V Vector v1.0）", "可伸缩向量，与 SVE 思路一致",
     "-march=rv64gcv / -march=rv64imafdcv_zvl256b"),
    ("loongarch64", "LSX / LASX", "128 位 / 256 位 SIMD（龙芯自主向量扩展）",
     "-march=la664 / -mloongson-ext"),
)

# ── 优化要点（三板斧：向量化 / 对齐 / 寄存器 / 缓存 / 分支 / 指令 / 内联约束）──
# (key, 中文标题, 要点)
OPT_POINTS = (
    ("simd", "向量化（SIMD）",
     "优先让编译器自动向量化（-O3 -ftree-vectorize -fopt-info-vec），再用手写 intrinsics 兜底；"
     "热点循环避免数据依赖链过长、避免循环内有函数调用打断。"),
    ("alignment", "内存对齐",
     "数据按 16/32/64 字节对齐，避免跨 cache line 与非对齐装载惩罚；"
     "汇编用 .balign 16、C 用 alignas()/__attribute__((aligned(64)))；结构体 packed 谨慎使用。"),
    ("register", "寄存器分配",
     "减少栈溢出（spill）：把关键循环变量留在寄存器，控制同时 live 的变量数；"
     "分清 caller-saved / callee-saved，减少保存恢复开销。"),
    ("cache", "缓存友好",
     "提升空间局部性（循环分块/tiling 让工作集落在 L1/L2）；用 prefetch 预取远数据；"
     "多线程避免 false sharing（每线程独立 cache line）。"),
    ("branch", "分支优化",
     "热点分支用 __builtin_expect / likely-unlikely 或 cmov 改无分支；减少预测失败；"
     "用位运算与条件传送替代条件跳转。"),
    ("instruction", "指令选择",
     "优先单周期/少微码指令；用 LEA 做地址与简单算术；善用 BMI/ADCX/PCLMUL 等扩展指令。"),
    ("inline_asm", "内联汇编约束",
     "asm volatile 必须正确声明输入/输出操作数与改动的寄存器与内存（\"memory\" clobber），"
     "否则编译器可能误移指令导致错乱；能用 intrinsics 就不手写 asm。"),
)

CHANGELOG = (
    ("v0.6.43", "首次引入 asm 子系统：探针 nasm/yasm/gas/llvm-mc/gcc -S；"
                "优化要点覆盖 SIMD(SSE/AVX/NEON/SVE/RVV)/对齐/寄存器/缓存/分支/指令/内联约束；"
                "附 LLVM 交叉编译汇编指引（clang -target=<triple> -S）。"),
)


def _ver(exe: str) -> str | None:
    if shutil.which(exe) is None:
        return None
    try:
        return subprocess.run([exe, "--version"], capture_output=True, text=True,
                               timeout=6).stdout.splitlines()[0].strip()
    except (OSError, subprocess.SubprocessError, IndexError):
        return "(已安装，版本读取失败)"


def nasm_report() -> tuple:
    v = _ver("nasm")
    if v is None:
        return False, "未安装 nasm；x86 汇编可用 yasm/gas 替代"
    return True, f"nasm: {v}"


def yasm_report() -> tuple:
    v = _ver("yasm")
    if v is None:
        return False, "未安装 yasm（NASM 语法超集）；可用 nasm/gas 替代"
    return True, f"yasm: {v}"


def gas_report() -> tuple:
    if shutil.which("as") is not None:
        v = _ver("as")
        return True, f"GAS(as): {v}"
    if shutil.which("gcc") is not None:
        return True, "gcc 驱动 GAS 可用（as 未单独暴露，经 gcc 调用）"
    return False, "未安装 GAS/binutils；C→汇编需 gcc/binutils"


def llvm_mc_report() -> tuple:
    v = _ver("llvm-mc")
    if v is None:
        return False, "未安装 llvm-mc（随 LLVM 提供）；交叉汇编可用对应 GNU 工具链替代"
    return True, f"llvm-mc: {v}"


def gcc_s_report() -> tuple:
    if shutil.which("gcc") is None:
        return False, "未安装 gcc；无法用 gcc -S 观察编译器产出的汇编"
    return True, "gcc 可用（gcc -S <src> -o <src>.s 只读生成汇编，不汇编不链接）"


def _probe(fn: str) -> tuple:
    return getattr(__import__("sys").modules[__name__], fn)()


def environment_report() -> list:
    lines = ["汇编语言优化（asm）· 本机只读探测："]
    for fn, lab in ASSEMBLERS:
        ok, msg = _probe(fn)
        lines.append(f"   · {lab}: {'✓ 可用' if ok else '✗ 不适用'}")
        if isinstance(msg, str) and msg.strip():
            lines.append("       " + msg.replace("\n", "\n       "))
    return lines


def asm_report(env_tags: list | None = None, readings: dict | None = None) -> tuple:
    lines = ["== 汇编语言优化报告（asm：汇编器探测 + 优化要点 + LLVM 交叉汇编指引，只读不写）=="]
    lines.append(f"维度标签: {sorted(set(env_tags or [])) or '未声明（默认基线）'}")
    lines.append("")
    lines.append("[① 汇编器探针]")
    for fn, lab in ASSEMBLERS:
        ok, msg = _probe(fn)
        lines.append(f"   · {lab}: {'✓ 可用' if ok else '✗ 不适用'}")
        if isinstance(msg, str) and msg.strip():
            lines.append("       " + msg)
    lines.append("")
    lines.append("[② 各架构 SIMD / 向量扩展矩阵（按时间序列逐步扩充）]")
    for arch, ext, zh, flag in SIMD_MATRIX:
        lines.append(f"   · [{arch}] {ext} — {zh}")
        lines.append(f"       编译标志: {flag}")
    lines.append("")
    lines.append("[③ 优化要点（向量化 / 对齐 / 寄存器 / 缓存 / 分支 / 指令 / 内联约束）]")
    for _key, title, body in OPT_POINTS:
        lines.append(f"   · {title}: {body}")
    lines.append("")
    lines.append("[④ LLVM 交叉编译汇编指引]")
    for line in guide_cross_asm()[1].splitlines():
        lines.append("   " + line)
    lines.append("")
    lines.append("[⑤ CHANGELOG（久久为功，常态化回头看）]")
    for ver, note in CHANGELOG:
        lines.append(f"   · {ver}: {note}")
    lines.append("")
    lines.append("安全不变量：asm 只探测汇编器 + 给优化要点与交叉汇编指引；绝不编译、绝不改源码、"
                 "绝不写汇编文件；是否施工始终由用户在构建脚本/编译器标志确认。")
    return True, "\n".join(lines)


def guide_cross_asm(triple: str | None = None) -> tuple:
    tgt = triple or "<target-triple>"
    lines = [
        f"LLVM 交叉编译汇编指引（clang -target={tgt} -S，不代执行）:",
        "   1. clang -target=<triple> -march=<arch> -O3 -S <src>.c -o <src>.s   # 只读生成汇编，不汇编不链接",
        "   2. 查看产出的 .s 观察自动向量化（-ftree-vectorize）与指令选择",
        "   3. 内联汇编跨目标用 .intel_syntax noprefix（x86）或统一约束；RISC-V/AArch64 用 intrinsics 更稳",
        "   4. 绝不改动本机默认工具链；交叉只用 --target 与 sysroot",
    ]
    return True, "\n".join(lines)


TUNES = (
    ("guide_cross_asm", "LLVM 交叉编译汇编（规范指引，不代执行）"),
)


def asm_tune_list() -> list:
    return [f"· {fn}() — {desc}" for fn, desc in TUNES]
