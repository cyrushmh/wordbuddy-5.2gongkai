"""单板机 / ARM SBC 优化建议任务（platform="any"，v0.6.11 新增「新硬件」）。

立项：树莓派、Orange Pi、NanoPi、RK3399 这类单板机跑完整 Linux，却有 SD 掉速、
被动散热降频、供电不足欠压等桌面没有的痛点。本任务**只读探测 + 给建议**，
不替你改任何设置——SBC 上改错了比桌面更危险。

非 SBC（x86 笔记本/服务器）上探测返回 None，任务会明确说「未识别为单板机」，
不硬套建议。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)

DT = ("[官方] 各 SoC 厂商设备树（Devicetree）规范——板型识别的权威来源")
THERMAL = ("[国际] Linux 内核 thermal sysfs 接口（Documentation/ABI/testing/sysfs-class-thermal）")
PI = ("[官方] Raspberry Pi 官方文档：get_throttled 位掩码（欠压/降频/温度限速定义）")


TASKS = [
    Task(
        id="edge_advisory",
        platform="any",
        title="单板机优化建议（板型/温度/降频/启动盘，只读）",
        category="optimize",
        risk="low",
        desc="只读探测单板机：设备树板型、thermal 温度、Broadcom 平台降频/欠压位、"
             "启动盘类型（SD/eMMC/NVMe），并给出带因果的优化建议。",
        actions=[
            N("edge.capabilities_report", "本层能力自检（板型/温度/降频/启动盘探测可用性）"),
            N("edge.edge_report", "输出探测结果与优化建议（温度/供电/启动盘）"),
            M("温度长期 >80°C：加散热片/风扇、避免密闭外壳、降负载——不要硬改频率策略",
              "散热建议（只读，由你决定）"),
            M("启动盘是 SD 卡：根分区换 eMMC/NVMe，SD 只做应急启动并定期备份——"
              "SD 不支持 fstrim，意外断电易损文件系统", "启动盘建议（只读，由你决定）"),
        ],
        standards=[DT, THERMAL, PI],
        notes=[
            "板型读 /proc/device-tree/model 或 /sys/firmware/devicetree/base/model——"
            "几乎所有 ARM/RISC-V SBC 都有，是最稳的「这是什么板」来源。",
            "温度读 /sys/class/thermal/*；降频/欠压读 Broadcom throttled 位掩码，"
            "其它平台退化到「看温度」判断，不硬猜。",
            "启动盘类型由 /proc/self/mountinfo 回溯根设备判定：SD / eMMC / NVMe / SATA。",
            "非 SBC 上 detect_board 返回 None，本任务会明确说「未识别为单板机」，"
            "不走桌面/服务器的硬件优化任务。",
        ],
        caveats=[
            "只读任务：不写 sysfs、不调 vcgencmd 改频率/电压、不装散热服务。",
            "建议带「为什么」——SBC 用户需要懂因果，不是被按头改。",
        ],
    ),
]
