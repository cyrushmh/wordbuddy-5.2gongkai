"""开源 Windows 分析学习应用任务（v0.6.76 新建）。

把开源 Windows 分析·学习应用生态（监控/逆向/取证/OS 重实现/驱动示例）作为**只读诊断**
能力登记，并嵌入整体系统。全部 platform="any" / category="arch" / risk="low"。

第一原则是「先定系统，再谈目录」：面向其他系统与硬件时，必须先识别目标所属环境，
再按该环境自身的文件系统、目录约定、路径分隔与运行语言标准去读数——不以本机
（Linux 沙箱）的习俗臆造目标结构。只引用官方源，绝不启动任何分析目标，
DMA 与内核写类工具仅登记存在性。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)

TASKS = [
    Task(
        id="winternals_target_env",
        platform="any",
        title="目标环境与文件系统/目录约定核验（跨平台先认系统与硬件）",
        category="arch",
        risk="low",
        standards=[
            "[开源] ReactOS（GPL-2.0-or-later，Windows 重实现）",
            "[开源] Wine（LGPL-2.1-or-later，Win32 用户态重实现）",
            "[开放] Microsoft Learn · 文件系统与命名空间命名规范",
        ],
        desc="只读判定当前所属的目标环境（Windows 原生 / WSL / Linux / macOS / Android），"
             "然后按那一套环境的规矩核验它的文件系统类型与标准目录：Windows 看盘符与"
             "System32/SysWOW64 之分，Linux 看 FHS 单根树，macOS 看 APFS 与系统/数据卷分离。"
             "不得用一套环境的路径约定去套另一套——这是跨平台只读诊断的第一道门槛。",
        actions=[N("winternals.target_env_report", "判定目标环境与宿主（先看是什么系统）"),
                 N("winternals.fs_layout_report", "核验该环境的文件系统类型与标准目录")],
        notes=[
            "Windows 目录名会骗人：System32 放原生位宽映像、SysWOW64 反而放 32 位映像（WOW64 重定向）。",
            "同一份文件在不同层有不同名字：Win32 层是 C:\\Windows\\System32、NT 层是 \\Device\\HarddiskVolumeN\\Windows、WSL 里变成 /mnt/c/Windows。",
            "SystemRoot 须读环境变量或按 GetSystemDirectory 语义取，绝不硬编码 C:\\Windows；%APPDATA%/%LOCALAPPDATA% 同理。",
            "本机 /proc 与 /sys 是内核的只读投影，不是磁盘上的文件——列目录能命中不代表占存储空间。",
        ],
        caveats=["只读判定与列目录：不改不建任何目录、不改权限、不挂载卸载；"
                 "目录命中率低不等于能力缺失（容器与精简镜像本就少），关键看是否遵循该环境的约定。"],
    ),
    Task(
        id="winternals_runtime_env",
        platform="any",
        title="运行语言环境与运行时依赖核验（目标 ABI + 工具链语言环境）",
        category="arch",
        risk="low",
        standards=[
            "[开放] Microsoft Learn · Windows API 索引与 PE 格式规范",
            "[开源] Volatility 3（GPL-2.0，Python 3 环境）",
            "[开源] Ghidra（Apache-2.0，需 JVM 环境）",
        ],
        desc="运行语言环境两头都要看：一头是**目标**的映像格式与 ABI（PE/PE32+ 还是 ELF "
             "还是 Mach-O、绑定哪个 CRT、有没有托管 CLR），一头是**工具链自己**的语言环境"
             "（Ghidra 要 JVM、Volatility3 要 Python 3、dnSpyEx 要 CLR、生成 PE 目标要交叉编译器）。"
             "两头缺一，任何分析结论都不成立。",
        actions=[N("winternals.runtime_env_report", "核验目标 ABI 与工具链自身语言依赖")],
        notes=[
            "Windows 上并存多套运行时：原生 Win32（MSVC CRT）、MinGW-w64（msvcrt 系，与 MSVC ABI 不互认）、托管 CLR/CoreCLR、内核侧 NTDLL Native API。",
            "混合 CRT（MSVC 与 MinGW 混链）与混合架构（x64 宿主载 x86 目标）是两类最高频的踩坑点。",
            "工具侧同理：Ghidra 装了但没有 JVM、Volatility3 装了但 Python 版本不对，都等于没装。",
        ],
        caveats=["只探测路径存在性与版本口径；不安装任何运行时、不改 JAVA_HOME 或 PYTHONPATH、"
                 "不下载任何运行时组件。"],
    ),
    Task(
        id="winternals_toolchain",
        platform="any",
        title="开源 Windows 分析工具链存在性盘点（只问在不在，不启动）",
        category="arch",
        risk="low",
        standards=[
            "[开源] Ghidra（Apache-2.0）/ x64dbg（GPL-3.0）/ radare2·Cutter（LGPL·GPL）",
            "[开源] Volatility 3（GPL-2.0）/ MemProcFS（AGPL-3.0）",
            "[开源] System Informer（GPL-3.0）/ dnSpyEx（GPL 系）",
            "[对照] Sysinternals / WinDbg —— 微软非开源，仅作能力对照不吸收",
        ],
        desc="只用路径查询盘点开源 Windows 分析工具链的存在性：Ghidra、radare2、Cutter、"
             "Volatility3、System Informer、x64dbg、dnSpyEx，以及 GNU 系（gdb/objdump/upx）、"
             "NTFS 元数据只读查询的 ntfsprogs、取证用的 The Sleuth Kit、磁盘映像工具等。"
             "给出组合读法（有反编译器无调试器 = 只能做静态；有取证框架缺符号表 = 只能枚举不能还原结构）。",
        actions=[N("winternals.toolchain_report",
                   "列开源 Windows 分析工具链存在性矩阵（只查询不启动）")],
        notes=[
            "许可纯度是本轮的取舍主线：MIT/Apache-2.0 宽松；GPL/AGPL 系（x64dbg、MemProcFS、dnSpyEx、PCILeech）只登记不吸收；AGPL 在网络服务场景传达条款更严。",
            "PCILeech 经 PCIe DMA 直接读写物理内存，相当于具备了对目标主机的内核级控制能力——其合法性取决于授权而非工具本身。",
            "本机 native/reverse 已覆盖静态侧主要着力点（PE/ELF 格式、节区解剖、香农熵、UPX 三特征），本任务补的是『开源生态里有谁、什么许可』的坐标。",
        ],
        caveats=["只登记存在性与许可边界：绝不下载、绝不调用、绝不 attach 进程、绝不做 DMA 读写；"
                 "PCILeech 一类具备写能力的工具仅回答有没有，不提供任何操作入口。"],
    ),
    Task(
        id="winternals_anchors",
        platform="any",
        title="Windows 内核原理可对读锚点与许可纯度核对",
        category="arch",
        risk="low",
        standards=[
            "[开源] ReactOS（GPL-2.0-or-later，唯一可读源码的 Windows 兼容内核实现）",
            "[开源] Wine（LGPL-2.1-or-later，Win32 API 的用户态重实现）",
            "[开源] Windows Driver Samples（MIT，许可最宽松的内核态示例）",
            "[参考] 《Windows Internals》/ Vergilius Project / Geoff Chappell",
        ],
        desc="核对 Windows 内核原理的三条可对读路径与各自的许可边界：ReactOS 源码树读 NT "
             "内核实现（注意旧基线）、Wine 源码看 Win32 API 如何落到 POSIX、Windows Driver "
             "Samples 的 MIT 示例读内核态写法；并给出 Vergilius 与 Geoff Chappell 两个结构体/"
             "NT API 参考源作为坐标。",
        actions=[N("winternals.internals_anchors_report",
                   "列内核原理可对读锚点与许可证纯度速查")],
        notes=[
            "ReactOS 目标基线偏旧（大致 Server 2003 层），现代 Windows 的新机制须另行对照微软文档补正。",
            "许可提醒：读 ReactOS 源码参考可以，把它的代码拷进自己的产物则会触发 GPL-2.0。",
            "Driver Samples 是 MIT，没有传染性——想学内核态又希望代码能作为基底时，这是最干净的选项。",
            "结构体数据（Vergilius 按版本与架构给逐字段布局）属公开资料上的协作知识，不含漏洞利用代码。",
        ],
        caveats=["只登记知识坐标：不下载任何数据集、不生成攻击性载荷；"
                 "用于理解自己机器的内存或转储正当，用于他人未授权系统则越界；"
                 "是否构成派生作品或传达因司法辖区而异，本工具不下法律结论。"],
    ),
]
