"""兼容层串联任务（v0.6.34 子系统 / v0.6.35 补任务入口，platform="any"）。

把「我这台机器能不能跑那个平台的软件」做成可执行项，而不是四份散报告：

- **只读盘点**：四层依赖（底座 → 设备与图形 → 兼容运行时 → 供给）+ 场景结论，
  缺哪一层说哪一层，**不适用不报就绪**。
- **指引**：装运行时只给官方路径与命令文本，**本工具绝不代装**。

红线：所有动作只读或纯文本指引——不安装、不启用、不改配置。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)

# 标准出处（与其余任务同款：带 [官方]/[国际] 前缀，进「标准与分类」视图）
WINE = ("[官方] Wine 官方文档（WineHQ）：Win32/Win64 API 重实现与 winecfg 用法")
PROTON = ("[官方] Proton Wiki（Valve）：Wine + DXVK + VKD3D-Proton + Steam Runtime 组合")
DOSBOX = ("[官方] DOSBox Wiki：x86/声卡/显卡模拟与 MOUNT、cycles 配置")
WSL = ("[官方] Microsoft Learn · WSL：安装、wslconfig 与 interop 说明")
VULKAN = ("[国际] Khronos Vulkan 规范：loader / ICD / SPIR-V 能力模型")
BUSYBOX = ("[官方] busybox 官方文档：多调用二进制与 --list 能力清单")


TASKS = [
    Task(
        id="compat_report",
        platform="any",
        title="兼容层串联盘点（四层依赖 + 场景结论，只读）",
        category="maintenance",
        risk="low",
        desc="把 proton/dosbox/wsl/virtgpu/legacy 串成一条四层依赖链：宿主底座 → 设备与图形 → "
             "兼容运行时 → 供给。按场景给结论（跑 Windows 程序 / 跑 DOS 程序 / 在 Windows 上跑 "
             "Linux / 跑遗留嵌入式），缺任一层即判「缺层」，本机不适用不判「已通」。",
        actions=[
            N("compat.compat_report",
              "四层只读盘点 + 场景串联结论（不安装、不启用、不改配置）"),
        ],
        standards=[WINE, PROTON, DOSBOX, WSL, VULKAN],
        notes=[
            "上层能不能用取决于下层给不给得了：Proton 要 Vulkan（设备层）与 32 位运行时（供给层），"
            "缺任何一层，运行时这一层就是空转。",
            "**不适用 ≠ 已就绪**：本机 Linux 时 WSL 探测会跑通但正文是「未识别为 WSL 环境」，"
            "报告判「本机不适用」而不是「链路已通」。",
        ],
        caveats=[
            "只读任务：不安装任何运行时、不启用任何服务、不改任何配置。",
            "盘点结果来自各模块既有的零参只读报告，与同名 CLI `compat` 完全一致。",
        ],
    ),
    Task(
        id="compat_windows_guide",
        platform="any",
        title="跑 Windows 程序/游戏的官方路径（只给命令，不代装）",
        category="maintenance",
        risk="low",
        desc="给出在 Linux 上跑 Windows 程序的两条官方路径与选型：办公老程序用 Wine（独立前缀），"
             "游戏用 Proton（自带依赖与图形转译层）。只输出命令文本，是否安装由你决定。",
        actions=[
            M("办公/老程序：装系统 wine 包后 `WINEPREFIX=~/wine-前缀 winecfg` 建独立前缀，"
              "再 `WINEPREFIX=~/wine-前缀 wine 程序.exe`（见 WineHQ 文档）",
              "Wine + 独立前缀（兼容性路线）"),
            M("游戏：Steam → 设置 → Steam Play → 勾选「为所有其他产品启用」，"
              "或装第三方 Proton 到 compatibilitytool.d（见 Proton Wiki）",
              "Proton（游戏路线，自带依赖）"),
            M("先查图形底座：`vulkaninfo | head` 有输出才有 Vulkan；没有就先装驱动与 loader，"
              "否则兼容层一定起不来",
              "Vulkan 能力自检（兼容层的下游依赖）"),
        ],
        standards=[WINE, PROTON, VULKAN],
        notes=[
            "选型：要「能跑起来」用 Proton；要「干净可控」用 Wine + 独立 WINEPREFIX，别混用默认前缀。",
            "同步原语优先 NTSync（新内核）→ fsync → esync 逐档降级；内核太老就退到 esync。",
            "32 位程序要装对应的 32 位运行时（i386），发行版不给就装不上——这是供给层的事。",
        ],
        caveats=[
            "指引类任务：只打印命令文本，不自动安装、不启用任何东西。",
            "装 Wine/Proton 会占用磁盘与依赖；游戏前缀动辄数 GB，留好空间。",
        ],
    ),
    Task(
        id="compat_legacy_guide",
        platform="any",
        title="跑 DOS 与遗留嵌入式的官方路径（只给命令，不代装）",
        category="maintenance",
        risk="low",
        desc="给出跑老 DOS 程序（DOSBox 模拟）与遗留/嵌入式用户态（busybox）的官方路径与命令文本。",
        actions=[
            M("老 DOS 程序：`dosbox` 进入后用 `MOUNT C ~/dos` 挂目录，再切到 C: 运行；"
              "cycles 按程序年代调（见 DOSBox Wiki）",
              "DOSBox 模拟运行（连 CPU 一起模拟，兼容性最高）"),
            M("极简/嵌入式环境：`busybox --list` 先看编进去了哪些命令，缺的要么重编 busybox、"
              "要么换完整发行版（见 busybox 官方文档）",
              "busybox 能力核对"),
            M("反向桥（在 Windows 上跑 Linux）：`wsl --install`；工程别放 /mnt/c，"
              "放 Linux 根文件系统避免跨文件系统 IO 慢（见 Microsoft Learn · WSL）",
              "WSL 安装与用法（方向相反的桥）"),
        ],
        standards=[DOSBOX, BUSYBOX, WSL],
        notes=[
            "DOSBox 是**模拟**（连 CPU 都模拟），Wine 是**重实现**（翻译 API）——两者思路不同，"
            "前者兼容性高、后者性能好。",
            "WSL 是反向桥：别人在 Windows 上跑 Linux，与 Wine/Proton 方向相反、思路同源。",
        ],
        caveats=[
            "指引类任务：只打印命令文本，不代装、不启用。",
            "DOSBox 的 cycles 调太高会让老程序跑飞；从低档往上试。",
        ],
    ),
]
