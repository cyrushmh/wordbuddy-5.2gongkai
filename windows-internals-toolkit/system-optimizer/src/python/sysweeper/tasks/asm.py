"""汇编语言优化任务（platform=any，跨平台）。

只读探测汇编器（nasm/yasm/gas/llvm-mc/gcc -S），并给出优化要点
（SIMD：SSE/AVX/NEON/SVE/RVV；对齐/寄存器/缓存/分支/指令/内联约束）与 LLVM 交叉编译汇编指引。
任何编译/改源码/写汇编文件一律只给规范指引，不代执行——严守本项目只读红线。

引擎（asm_report / guide_cross_asm）是纯函数，由 asm_report 串联；GUI 让用户看到当前汇编器与
优化要点，确认整体在只读口径下只给优化路径不施工。
"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="asm_report",
        platform="any",
        title="汇编语言优化（只读报告）",
        category="maintenance",
        risk="low",
        desc="只读探测汇编器（nasm/yasm/gas/llvm-mc/gcc -S），并给出优化要点（SIMD：SSE/AVX/NEON/SVE/RVV；"
             "对齐/寄存器/缓存/分支/指令/内联约束）与 LLVM 交叉编译汇编指引（clang -target=<triple> -S）。"
             "绝不编译、绝不改源码、绝不写汇编文件。",
        actions=[
            N("asm.asm_report", "端到端生成汇编语言优化报告（汇编器探针→SIMD 矩阵→优化要点→交叉汇编指引）"),
        ],
        notes=["软件只读能力面：只探测、只给优化要点与指引，不编译/不改源码/不写汇编文件。"],
        standards=["[国际] NASM / YASM（x86/x86_64 汇编器）",
                  "[国际] GNU Assembler（GAS，随 binutils）",
                  "[国际] LLVM MachineCoder（llvm-mc）",
                  "[国际] Intel SSE/AVX、ARM NEON/SVE、RISC-V Vector（RVV）、龙芯 LSX/LASX 指令集规范"],
    ),
    Task(
        id="asm_cross_asm_guide",
        platform="any",
        title="LLVM 交叉编译汇编指引（规范指引）",
        category="maintenance",
        risk="low",
        desc="给出用 clang -target=<triple> -S 为各架构生成汇编（只读观察自动向量化与指令选择）的规范指引，"
             "绝不自动交叉汇编。",
        actions=[
            M("clang -target=<triple> -march=<arch> -O3 -S <src>.c -o <src>.s；"
              "查看产出 .s 观察自动向量化；内联汇编跨目标用 .intel_syntax noprefix 或统一约束。",
              "LLVM 交叉编译汇编（规范指引，不代执行）"),
            N("asm.guide_cross_asm", "输出 LLVM 交叉编译汇编指引（只给步骤，不编译/不写汇编文件）"),
        ],
        notes=["交叉汇编属于写操作，一律只给规范指引；是否施工由用户在构建脚本确认。"],
        standards=["[国际] LLVM Target Triple 规范（arch-vendor-os-abi）",
                  "[国际] clang --target 交叉编译（复用 llvm 子系统交叉编译目标矩阵）"],
    ),
]
