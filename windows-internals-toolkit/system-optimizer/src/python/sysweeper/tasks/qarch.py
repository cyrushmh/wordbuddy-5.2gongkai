"""量子架构内核任务（v0.6.78 新建）。

盘点 quantum-kernel/ 内核树：Linux 6.18.57 LTS + arch/quantum 纯新增架构 +
QPU 模拟设备。全部 platform="any" / risk="low"；树/架构类归 category="arch"，
设备类归 category="hardware"。

红线：纯只读——绝不执行内核构建、绝不写内核树、绝不加载内核模块。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)

TASKS = [
    Task(
        id="qarch_tree_arch",
        platform="any",
        title="量子架构内核树与架构覆盖盘点（6.18.57 LTS + arch/quantum 纯新增）",
        category="arch",
        risk="low",
        standards=[
            "[标准] kernel.org · Linux 6.18.57 longterm（当期最新 LTS）",
            "[标准] kernel.org · Kconfig 语言参考（arch/Kconfig 动态 source 机制）",
            "[本仓] quantum-kernel/linux-6.18.57（完整树本地保留）",
        ],
        desc="只读盘点量子架构内核树：Linux 6.18.57 LTS 基线在位、arch/ 目录清单"
             "（既有架构全部原封保留 + quantum 纯新增）、arch/quantum 骨架文件、"
             "drivers 两处注册点的纯追加核验。架构注册是零修改的：arch/Kconfig 动态"
             " source 与顶层 SRCARCH 默认映射让新目录本身即注册。",
        actions=[N("qarch.tree_report", "内核树在位与基线盘点"),
                 N("qarch.arch_report", "架构覆盖与纯新增核验")],
        notes=[
            "既有 21 个架构目录一个不动；x86_64 defconfig 正常生成（4395 项配置）证明无破坏。",
            "mandatory-y 头自动 fallback 到 asm-generic；架构只补 byteorder/ptrace/sigcontext 三个无 generic 版的 uapi 头。",
            "git 侧只上传补丁+增量镜像（保持 Linux 目录结构），完整树凭 scripts/fetch_kernel.sh 重建。",
        ],
        caveats=["纯只读：不构建、不写树、不动任何既有架构文件。"],
    ),
    Task(
        id="qarch_qpu_semantics",
        platform="any",
        title="QPU 模拟设备与 Π_k 门语义盘点（4KiB 页纪律贯通）",
        category="hardware",
        risk="low",
        standards=[
            "[标准] kernel.org · misc 设备接口（/dev/qpuN）",
            "[本仓] drivers/quantum（QPU_ENC/DEC/STATS/RESET）",
            "[本仓] quantum 子系统（Π_k 门/8q 寄存器/PiLink 链路语义对照）",
        ],
        desc="只读盘点 QPU 模拟设备的落地与语义一致性：/dev/qpuN 的 UAPI（enc/dec/"
             "link_stats/reset）、Π_k 置换矩阵门的翻转语义契约、4KiB 页纪律与存储域 "
             "ext4 4K 对齐口径的贯通（/proc/qpuinfo 自报）。内核侧量子能量激发态模型"
             "（离散能级/叠加/相位/干涉/测量坍缩/T1T2 退相干）随 quantum-energy.c 一并"
             "编译进 vmlinux，/proc/quantum-energy 只读自报；idle=mwait（基态等待）"
             "经 GRUB/LILO 双样本固化。构建验收三层如实报告：defconfig 全解析、整树"
             "编译并链接出真实 vmlinux（宿主工具链诚实编译）、真实量子硬件运行不可达"
             "（无量子处理器与其编译器后端是硬事实）。",
        actions=[N("qarch.qpu_report", "QPU 设备与语义盘点"),
                 N("qarch.dist_report", "补丁分发与重建路径盘点")],
        notes=[
            "内核内新增代码全部 GPL-2.0（内核树纪律）；与本仓 MIT 是分发关系，互不传染。",
            "构建验收如实记录：vmlinux 已链接（EXIT=0 零警告，15 个 quantum_* 符号在位）——但产出是宿主机器码的模拟架构内核，不虚报「能在量子处理器上运行」。",
            "后续可延展项：向 arch/um 级完整宿主模拟推进（需 os-Linux 层与 syscall 透传）。",
        ],
        caveats=["纯只读：不执行内核构建、不加载内核模块、不触碰真实量子硬件。"],
    ),
]
