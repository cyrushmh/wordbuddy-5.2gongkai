"""LLVM 工具链与交叉编译任务（platform=any，跨平台）。

只读探测 LLVM 工具链（clang/lld/mlir）并给出交叉编译目标矩阵（按时间序列逐步扩充）；
任何编译/下载 sysroot/改写工具链配置一律只给指引，不代执行——严守只读红线。
"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="llvm_report",
        platform="any",
        title="LLVM 工具链与交叉编译目标矩阵（只读）",
        category="maintenance",
        risk="low",
        desc="只读探测 LLVM 工具链（clang/lld/mlir），并给出按时间序列逐步扩充的交叉编译目标矩阵"
             "（aarch64/armv7/riscv64/x86_64-mingw/wasm32…），含 sysroot 指引与 CHANGELOG。"
             "绝不编译、绝不下载 sysroot、绝不改写工具链配置。",
        actions=[
            N("llvm.llvm_report", "端到端生成 LLVM 工具链报告（工具链探针→交叉编译目标矩阵→CHANGELOG）"),
        ],
        notes=["LLVM 只读探测：只探测、只出矩阵、只给 sysroot 指引。"],
        standards=["[国际] LLVM 项目（clang/lld/MLIR 工具链）",
                  "[国际] LLVM 目标三元组（Target Triple）规范",
                  "[国际] GNU/Mingw-w64 交叉编译 sysroot 约定"],
    ),
    Task(
        id="llvm_cross_guidance",
        platform="any",
        title="LLVM 交叉编译（规范指引）",
        category="maintenance",
        risk="low",
        desc="给出用 clang --target=<triple> 做交叉编译的规范指引，绝不自动编译。",
        actions=[
            M("clang --target=<triple> -sysroot <path> -fuse-ld=lld <src> -o <out>；"
              "用 qemu-user 或真实板跑通测试。",
              "LLVM 交叉编译（规范指引，不代执行）"),
            N("llvm.guide_cross", "输出交叉编译指引（只给步骤，不编译/不下 sysroot）"),
        ],
        notes=["编译属于写操作，一律只给规范指引；是否施工由用户在构建脚本确认。"],
        standards=["[国际] LLVM 交叉编译（--target / -sysroot / -fuse-ld=lld）"],
    ),
]
