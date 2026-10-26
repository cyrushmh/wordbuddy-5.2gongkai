"""从零造系统学习应用任务（platform=any，跨平台）：工具链·分配器·模式·总报告。

「导入分析学习应用」pepsipu（Sammy Hajhamid）项目群的任务层。五轴落法
（data/sysdev_docs.json）：

1. allocator_patterns   warpalloc：预分配 + 单空闲链首次适应 + 荒野推进（含适用边界）；
2. compiler_pipeline    aski：字符流→token→作用域栈→分节汇编输出的最小编译器骨架；
3. hobby_os_bringup     xinOS-old/OSpaint：bootloader→保护模式→IDT/PIC→VESA→应用；
4. emulator_tables      ramenbox：表格驱动的 6502 模拟器（opcode 表 + 反射分发）；
5. learning_method      导入分析学习应用五步法（本任务族自身的方法论）。

全部只读：不编译/运行被分析的第三方源码、不改 malloc 环境变量、不写任何文件。
"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="sysdev_report",
        platform="any",
        title="从零造系统学习应用总报告（只读：7 仓库模式 + 工具链 + malloc 体检）",
        category="maintenance",
        risk="low",
        desc="端到端报告：pepsipu 项目群 7 仓库（warpalloc/aski/xinOS-old/OSpaint/"
             "ramenbox/cx/torus）的可复用模式与适用边界、本机从零构建工具链盘点、"
             "glibc malloc 环境变量与内存足迹只读体检。",
        actions=[
            N("sysdev.sysdev_report", "零参生成从零造系统学习应用总报告（只读+知识库驱动）"),
        ],
        notes=["学习不等于打包：引用不等于拷贝，所有模式总结均为本仓原创表述。",
               "warpalloc MIT / xinOS-old BSD 风格声明可学模式；aski/OSpaint/ramenbox/torus/cx "
               "未见许可证文件，默认保留所有权利，只学思想。"],
        standards=["[国际] MIT License（warpalloc）",
                  "[国际] BSD 风格声明（xinOS-old）",
                  "pepsipu 项目群（github.com/pepsipu）"],
    ),
    Task(
        id="sysdev_toolchain",
        platform="any",
        title="本机从零构建工具链盘点（nasm/gcc/qemu/python，只读）",
        category="maintenance",
        risk="low",
        desc="探测本机是否具备「从零造系统」的最小工具集：NASM/YASM 汇编器、GCC/Clang、"
             "Python 3（ramenbox）、Node/pnpm（torus）、QEMU i386（玩具 OS 镜像验收）、"
             "make/cmake（构建驱动）。仅 --version 类只读调用。",
        actions=[
            N("sysdev.probe_toolchain", "只读盘点从零构建工具链（仅 --version 调用）"),
            M("复现 xinOS 验收闭环：qemu-system-i386 -fda xinos.img -s -machine q35 "
              "-soundhw pcspk——「可启动镜像」是玩具 OS 的唯一验收标准。",
              "玩具 OS 的 QEMU 验收命令"),
        ],
        notes=["本任务只盘点不安装：缺工具只报告，绝不代装任何软件。",
               "QEMU i386 是外部唯一硬依赖——没有它，玩具 OS 学习停在读源码层。"],
        standards=["QEMU 系统模拟器（qemu-system-i386）",
                  "NASM（Netwide Assembler）"],
    ),
    Task(
        id="sysdev_alloc",
        platform="any",
        title="分配器策略与预分配体检（glibc malloc 只读 + warpalloc 模式指引）",
        category="maintenance",
        risk="low",
        desc="只读展示本机 glibc 版本与 MALLOC_ARENA_MAX / MALLOC_TRIM_THRESHOLD_ / "
             "MALLOC_MMAP_THRESHOLD_ / MALLOC_PERTURB_ / MALLOC_CHECK_ 五个旋钮的当前值，"
             "解析 /proc/self/status 内存足迹；对照 warpalloc 的预分配 + 单空闲链 + "
             "荒野推进模式，给出适用边界指引（只读展示，绝不代设环境变量）。",
        actions=[
            N("sysdev.probe_malloc_env", "只读展示 glibc malloc 环境变量与版本"),
            N("sysdev.probe_memory_footprint", "只读读取本进程 Vm* 内存足迹"),
            M("warpalloc 的边界（README 原话精神）：25 次分配约快 ptmalloc 300 倍，"
              "但数千次 alloc/free 的 churn 场景 ptmalloc 的分箱与合并长期更快——"
              "「别用 warpalloc 做游戏」。可预估峰值的短生命周期工具才适合预分配思想。",
              "预分配模式的适用边界"),
            M("要调 glibc 旋钮请在官方文档知情下自行决定：MALLOC_ARENA_MAX 控线程 arena 数、"
              "MALLOC_TRIM_THRESHOLD_ 控堆顶归还内核时机——本工具绝不代改环境变量。",
              "glibc 旋钮调优指引"),
        ],
        notes=["本任务红线：只读展示 + 给指引，绝不修改任何进程环境变量。",
               "元数据头内嵌（size 在指针前 8 字节、free 时 fd 复用前 4 字节）意味着"
               "用户指针前后字节不可挪用——自研分配器必须把这条写进接口契约。"],
        standards=["glibc malloc 环境变量（man mallopt）",
                  "warpalloc（MIT，pepsipu）"],
    ),
    Task(
        id="sysdev_patterns",
        platform="any",
        title="从零造系统四模式学习指引（分配器/编译器/OS/模拟器，只读）",
        category="maintenance",
        risk="low",
        desc="按知识库四模式给出学习路径与复现要点：warpalloc 分配器三件套、"
             "aski 四段编译器管线、xinOS 引导链与最小内核集、ramenbox 表格驱动模拟器；"
             "每条附源文件回链与适用边界。",
        actions=[
            M("分配器模式（warpalloc/walloc.asm 110 行）：启动一次 brk 预分配 + "
              "一条空闲链首次适应 + 荒野 bump；热路径零栈变量，唯一 push 的是 ebx。",
              "分配器：预分配 + 单空闲链 + 荒野推进"),
            M("编译器模式（aski 约 1077 行 Rust）：IStream→Tokenizer→Parser→Program "
              "四段各单职责；输出按 .text/.data/.bss 分节累积；寄存器显式暴露（$rax=2 "
              "即 mov rax,2）；未实现的控制流（while/for）在 README 诚实标注。",
              "编译器：四段管线 + 分节输出"),
            M("OS 引导模式（xinOS-old）：bootloader.asm 进保护模式 → remap_pic + "
              "init_idt → VESA 图形 → 应用；手写 memcpy/memset 标 optimize(\"O2\") 并先转 "
              "char* 再偏移；rule 1：硬件尺寸常减一（比较器省钱的历史设计）。",
              "OS：引导链 + 最小内核集 + rule 1"),
            M("模拟器模式（ramenbox）：utils/gen_ops.py 从 oplist 文本生成 opcodes.json，"
              "CPU 类按字节反射分发到 _<name> 指令函数；寻址模式独立成类；外设即 GPIO "
              "位掩码 + ST7789 SPI 帧，与模拟器核心零耦合。",
              "模拟器：表格驱动 + 反射分发"),
            M("导入五步法：浅克隆全景 → README 建意图 → 读最小核心源 → 提炼模式+边界+"
              "反面三件 → 回灌六层（知识/只读/任务/接线/概念/测试）。每个仓库必须产出"
              "至少一条适用边界——只学优点的导入是半成品。",
              "导入分析学习应用五步法"),
        ],
        notes=["本任务只给指引与源文件回链，绝不克隆/编译/运行第三方源码。",
               "四条模式共同的元模式：小到能一次读完的实现最藏思想——找那种"
               "「一个文件讲清核心」的仓库读。"],
        standards=["pepsipu 项目群（github.com/pepsipu）",
                  "6502 ISA（ramenbox 指令集基底）"],
    ),
]
