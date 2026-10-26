"""游戏/应用兼容层诊断任务（platform="any"，v0.6.14「导入分析学习应用 Proton」）。

立项：把 Valve **Proton**（Steam Play 兼容层，用户量最大的跨平台兼容层）的原理吸收进
本工具——Proton = Wine + DXVK + VKD3D-Proton + wine-mono + Steam Runtime。本任务
只诊断「这台机器能不能跑 Windows 游戏/程序」的前提（Vulkan / 32 位 i386 / 同步原语
fsync·esync·NTSync / Steam Runtime / Proton-Wine 安装），全只读、不修改系统。

同时吸收 microsoft/litebox（安全沙箱库 OS）的「接口面削减 / 隔离」理念，把兼容层运行
原则定为：最小权限、可审计、可接管。

参照（权威文档，仅用于把「该看什么」钉死）：
- ValveSoftware/Proton README —— Runtime Config Options 全表（PROTON_USE_WINED3D /
  PROTON_NO_FSYNC / PROTON_NO_NTSYNC / PROTON_HIDE_NVIDIA_GPU / PROTON_DISABLE_NVAPI …）
- docs.kernel.org  ntsync.html —— NT synchronization primitive driver（/dev/ntsync, ioctl）
- Wine / DXVK / VKD3D-Proton 上游文档 —— 翻译层职责边界
- microsoft/litebox —— 兼容层「接口面削减 / 隔离」理念
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)

PROTON_README = ("[上游] ValveSoftware/Proton README（Runtime Config Options："
                 "PROTON_USE_WINED3D / PROTON_NO_FSYNC / PROTON_NO_NTSYNC / "
                 "PROTON_HIDE_NVIDIA_GPU / PROTON_DISABLE_NVAPI …）")
NTSYNC_DOC = ("[内核] docs.kernel.org ntsync.html（NT 同步原语驱动 /dev/ntsync；"
              "Linux 6.10 合并、6.11+ 可用；semaphore/mutex/event ioctl）")
LITEBOX = ("[微软] microsoft/litebox（安全沙箱库 OS：North 类 nix 接口 + South 平台接口，"
           "削减宿主接口面降低攻击面；兼容层应在隔离环境运行）")


TASKS = [
    Task(
        id="proton_report",
        platform="any",
        title="游戏/应用兼容层诊断（Proton/Wine 前提核验，整体只读）",
        category="network",
        risk="low",
        desc="以 Proton 为坐标系，把「机器能否跑 Windows 游戏/程序」只读结构化地摸一遍："
             "Vulkan 支撑栈(loader+ICD)、32 位 i386 运行时、NT 同步原语(esync/fsync/NTSync)、"
             "Steam Runtime 与 Proton/Wine 安装现状。",
        actions=[
            N("proton.capabilities_report", "能力自检：各维度是否可诊断 + 红线声明"),
            N("proton.proton_report", "输出兼容层整体只读诊断（每项附结论与修复提示）"),
            M("缺 Vulkan/32 位库时按需补：dpkg --add-architecture i386 && apt install "
              "libgl1:i386 libgl1-mesa-dri:i386（写操作，由你决定做不做）",
              "补齐前提（写操作，opt-in）"),
        ],
        standards=[PROTON_README, NTSYNC_DOC, LITEBOX],
        notes=[
            "Vulkan 看 /usr/share/vulkan/icd.d/*.json（驱动 ICD）+ vulkan-loader；"
            "这是 DXVK/VKD3D 运行的硬前提，无则 Proton 起不来。",
            "32 位 i386：Wine/Proton 大量依赖 32 位，用 dpkg --print-foreign-architectures "
            "与 dpkg -l ':i386' 判定，缺失关键库（libc6/i386、libstdc++6:i386…）会列明。",
            "同步原语三档：esync(eventfd, 老内核有) / fsync(futex, 需 FUTEX_WAIT_MULTIPLE≈5.16+) "
            "/ NTSync(/dev/ntsync, 6.11+)；Proton 自动选最佳路径，缺则回退。",
            "Steam Runtime 看 steam 进程、steam-runtime-system-info、steamapps/common/Proton*、"
            "wine --version、compatdata 前缀数量——只读，不启动任何游戏。",
            "运行原则（参照 litebox）：兼容层应在最小权限、可审计、可接管环境中运行；"
            "本工具只诊断不修改。",
        ],
        caveats=[
            "只读任务：不装包、不写 Wine prefix、不改内核参数、不连校外网。",
            "报告里的特性开关（PROTON_*）是运行时环境变量，不落盘；照着优化是 opt-in 下游动作。",
        ],
    ),
]
