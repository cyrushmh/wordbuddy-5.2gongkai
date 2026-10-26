"""遗留 / 嵌入式 / 兼容层任务（v0.6.21「导入分析学习应用」；v0.6.74 扩位宽/PAE）。

把 DOS 3.1 等遗留 DOS 环境、busybox 嵌入式用户态、dosbox DOS 模拟兼容层、位宽世代
能力矩阵（8/16/32/64 位元）、PAE 物理地址扩展（含 32 位 XP 开启口径），作为
**只读诊断**能力登记，并嵌入整体系统（关联 openwrt / proton / wsl / livemedia）。
全部 platform="any" / category="maintenance" / risk="low"；只读引用，不运行任何程序，
不修改任何引导配置（boot.ini/bcdedit/内核命令行）。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)

TASKS = [
    Task(
        id="legacy_dos",
        platform="any",
        title="遗留 DOS 环境只读诊断（DOS 3.1 等 · FreeDOS · DOSEMU2）",
        category="maintenance",
        risk="low",
        standards=[
            "[坐标] Microsoft MS-DOS 3.1（1984/85，x86 实模式 / FAT12）",
            "[仓库] freedos/FreeDOS(MIT/GPL)：开源 MS-DOS 替代（1.4，2025-04）",
            "[仓库] dosemu2(GPL-2.0)：Linux 近原生 DOS 虚拟机（DPMI）",
        ],
        desc="只读核验本机是否有 FreeDOS/DOSEMU2 路径，以及能否制作 DOS 启动盘"
             "（mtools/syslinux）；DOS 3.1 仅作知识坐标，不运行任何 DOS 程序。",
        actions=[N("legacy.dos_report",
                   "列出遗留 DOS 环境检测（FreeDOS/DOSEMU2/启动盘前提/知识坐标）")],
        notes=[
            "MS-DOS 3.1：x86 实模式、FAT12 软盘 360KB/1.2MB、COM/EXE、"
            "CONFIG.SYS/AUTOEXEC.BAT、HIMEM/EMM386、INT 21h/10h/13h/16h。",
            "FreeDOS 1.4 兼容 MS-DOS；DOSEMU2 在 Linux 近原生运行实模式 DOS。",
            "制作 DOS 启动软盘复用 livemedia 的 mtools/syslinux 工具链（你中有我）。",
            "合法 DOS 镜像如需取回，可走第三方 CDN·P2P 开关 aria2（见 thirdparty 引用）。",
        ],
        caveats=["本工具只诊断不运行：绝不写 DOS 镜像、不 dd、不启动 DOS/DOSEMU、不挂载/解包镜像。"],
    ),
    Task(
        id="legacy_busybox",
        platform="any",
        title="busybox 嵌入式用户态只读诊断（单二进制「瑞士军刀」）",
        category="maintenance",
        risk="low",
        standards=[
            "[仓库] mirror/busybox(GPL-2.0)：单文件多调用二进制（ls/cp/cat/mount/ps…）",
            "[系统] OpenWrt 以 busybox 为根用户态；live ISO initramfs 亦常含",
        ],
        desc="只读核验 busybox 版本、内置 applet 数，并判定其嵌入式上下文"
             "（OpenWrt 路由器 / Docker 极简镜像 / initramfs）；不触碰二进制本体。",
        actions=[N("legacy.busybox_report",
                   "列出 busybox 检测（版本/applet 数/嵌入式上下文）")],
        notes=[
            "busybox 把数十个 Unix 命令浓缩进一个可执行，广泛用于嵌入式路由器、安装器 initrd、容器。",
            "嵌入式上下文判定：OpenWrt 标记 / Docker(.dockerenv) / /bin·/sbin 软链到 busybox。",
            "与 OpenWrt 模块共生：路由器系统的根用户态即 busybox；与 livemedia 的 initramfs 同源思路。",
        ],
        caveats=["本工具只诊断不运行：不执行 busybox、不读/写其 applet、不连校外网做写。"],
    ),
    Task(
        id="legacy_dosbox",
        platform="any",
        title="dosbox DOS 模拟兼容层只读诊断（在现系统跑老 DOS 软件）",
        category="maintenance",
        risk="low",
        standards=[
            "[仓库] dosbox/dosbox(GPL-2.0)：SDL x86 实模式模拟器（core/cycles/mount）",
            "[衍生] Em-DOSBox(Emscripten→浏览器) / DOSBox-X(Win9x) / DBGL 前端",
        ],
        desc="只读核验 dosbox 版本与配置，给出核心概念（core/cycles/mount）与"
             "衍生生态；与 proton（兼容层）、wsl（旧环境迁移桥）关联。不启动 dosbox。",
        actions=[N("legacy.dosbox_report",
                   "列出 dosbox 检测（版本/配置/core·cycles·mount 概念）")],
        notes=[
            "dosbox 用 SDL 把 8086/286/386 动态重编译，在现 OS 跑老 DOS 游戏/程序。",
            "CPU core（simple/normal/dynamic/auto）、cycles（fixed/max 调速）、mount C <dir> 是核心。",
            "与 proton 同属兼容层、与 wsl 同属旧环境迁移桥；合法镜像取回可走 aria2 CDN·P2P 开关。",
        ],
        caveats=["本工具只诊断不运行：绝不启动 dosbox、不挂任何目录、不跑任何 DOS 程序。"],
    ),
    Task(
        id="legacy_bitwidth",
        platform="any",
        title="位宽世代能力矩阵（8/16/32/64 位元只读盘点）",
        category="maintenance",
        risk="low",
        standards=[
            "[坐标] 8 位世代（8080/Z80/6502/6809）：MAME/FCEU 等专用模拟器",
            "[坐标] 16 位实模式（8086/286·DOS）：dosbox / DOSEMU2 模拟层覆盖",
            "[坐标] 32 位保护模式（80386+/Win32/PE32/DPMI）：qemu-system-i386 / wine / 32 位用户态",
            "[坐标] 64 位长模式（x86-64/arm64）：cpuinfo lm 标志 + 64 位内核原生全寻址",
        ],
        desc="按位宽世代盘点本机能力：CPU lm/pae 标志、内核与用户态位宽、模拟层"
             "（qemu/dosbox/dosemu2/wine/mame）存在性；先定程序年代再选层，"
             "不启动任何模拟器。",
        actions=[N("legacy.bitwidth_report",
                   "列位宽世代能力矩阵（8/16/32/64 位 × 直接/模拟层）")],
        notes=[
            "位宽世代按数据线/地址线宽度 + 运行模式分档：8 位靠专用模拟器，16 位实模式靠 dosbox/dosemu2，"
            "32 位保护模式靠 qemu/wine，64 位原生全寻址。",
            "能力读法：直接运行 = 本机原生；模拟层覆盖 = 翻译层让一步性能与兼容。",
            "与 pae_report 联动：32 位 + PAE 扩展的是物理寻址，不是进程虚拟地址空间。",
        ],
        caveats=["本工具只盘点存在性：绝不启动任何模拟器、不下载镜像、不装运行时（装不装由你决定）。"],
    ),
    Task(
        id="legacy_pae",
        platform="any",
        title="PAE 物理地址扩展（现状检测 + 开启指引，不代改）",
        category="maintenance",
        risk="low",
        standards=[
            "[官方] Microsoft：PAE Memory and Windows（Win2000/XP/2003 口径，boot.ini /PAE）",
            "[官方] Microsoft：/pae 引导参数（XP/2003 独有；Vista+ 走 BCDEdit pae 项）",
            "[官方] Linux 内核 Kconfig：HIGHMEM64G select X86_PAE（PAE 同时是 32 位内核 NX 前提）",
        ],
        desc="只读检测 PAE 前提（CPU pae 标志、内核位宽、物理内存量），给出官方开启"
             "命令文本：Linux 32 位 -pae 内核/HIGHMEM64G；XP boot.ini /PAE；"
             "Vista/Win7 32 位 bcdedit /set pae ForceEnable。诚实边界：XP 全版本"
             "物理地址空间上限即 4GB，PAE 的意义是硬件 DEP/NX 与热插拔，不是突破 4GB。",
        actions=[N("legacy.pae_report",
                   "列 PAE 现状检测与开启指引（只读 + 命令文本）")],
        notes=[
            "XP/Server 2003：boot.ini 加 /PAE 重启（/NOPAE 禁用）；DEP 启用时 PAE 自动开启。",
            "Vista/Win7 32 位：bcdedit /set {当前项} pae ForceEnable；DEP 开着则 PAE 禁不掉。",
            "64 位系统不需要也不支持 PAE（原生全寻址）；进程虚拟地址空间（用户态 2GB）PAE 不改变。",
            "微软官方口径：Windows XP（所有版本）物理地址空间上限 4GB——开 PAE 不为突破 4GB。",
        ],
        caveats=["本工具只检测与给命令文本：不代改 boot.ini/bcdedit/内核命令行；引导配置属系统写操作，"
                 "执行与否与后果由你决定。"],
    ),
]
