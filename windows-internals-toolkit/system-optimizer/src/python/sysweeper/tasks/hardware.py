"""硬件标准相关的优化/维护任务（跨平台，platform="any"）。

按 T13/ATA（S.M.A.R.T.、TRIM）、UEFI Forum（ACPI）、PCI-SIG、USB-IF 等
硬件标准文档给出维护项；原生读取失败（未装 smartctl/lspci 等）时自动降级为指引，
不强求安装工具。详见 native/hardware.py 与 data/hardware.json。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)


TASKS = [
    Task(
        id="hw_smart_check",
        platform="any",
        title="磁盘 S.M.A.R.T. 健康自检",
        category="maintenance",
        risk="low",
        desc="按 T13/ATA8-ACS 标准读取磁盘 SMART 健康，预警坏道/重映射扇区。",
        actions=[N("hardware.smart_health", "读取 S.M.A.R.T. 健康（smartctl，参考 T13/ATA）")],
        notes=["参考标准：INCITS T13 ATA8-ACS；重映射扇区/待映射扇区升高即应备份换盘。"],
        caveats=["未安装 smartmontools 时无此能力；安装后即可启用，本工具不强求。"],
    ),
    Task(
        id="hw_acpi_optimize",
        platform="any",
        title="ACPI 电源状态优化",
        category="optimize",
        risk="medium",
        desc="按 UEFI Forum ACPI 规范核对可用睡眠态，给出节能建议。",
        actions=[N("hardware.acpi_states", "读取内核支持的 ACPI 睡眠态（/sys/power/state）")],
        notes=["参考标准：ACPI Specification（UEFI Forum）；笔记本用 S3/S4 节能，服务器慎用深度睡眠。"],
        caveats=["修改 CPU/设备电源态可能影响唤醒延迟，服务器/虚拟机谨慎。"],
    ),
    Task(
        id="hw_ssd_trim",
        platform="any",
        title="SSD TRIM 维护",
        category="maintenance",
        risk="low",
        desc="按 ATA TRIM（DATA SET MANAGEMENT）定期释放无效块，维持 SSD 性能。",
        actions=[N("hardware.disk_trim", "对根分区执行 fstrim（参考 ATA/ATAPI TRIM）")],
        notes=["参考标准：INCITS T13 ATA/ATAPI Command Set；已启用连续 TRIM 的文件系统可不定时跑。"],
        caveats=["未安装 util-linux（fstrim）时无此能力。"],
    ),
    Task(
        id="hw_pci_usb_report",
        platform="any",
        title="PCI/USB 设备清单（按标准类代码）",
        category="maintenance",
        risk="low",
        desc="按 PCI-SIG / USB-IF 类代码列出设备，辅助排查驱动缺失。",
        actions=[
            N("hardware.pci_devices", "列出 PCI/PCIe 设备（lspci -nn，参考 PCI-SIG 类代码）"),
            N("hardware.usb_devices", "列出 USB 设备（lsusb，参考 USB-IF 设备类）"),
        ],
        notes=["参考标准：PCI-SIG PCIe Base Spec / USB-IF Device Class Definitions。"],
        caveats=["未装 lspci/lsusb 时仅给指引。"],
    ),
    Task(
        id="hw_cpu_report",
        platform="any",
        title="CPU 信息报告",
        category="maintenance",
        risk="low",
        desc="读取 CPU 型号/核心数（跨平台：sysctl / /proc/cpuinfo），供调优前确认硬件。",
        actions=[N("hardware.cpu_info", "读取 CPU 信息（跨平台原生接口）")],
        notes=["CPU 频率调节参考 P-state/C-state（ACPI）；修改前确认硬件与散热。"],
    ),

    # ── 硬件优化：标准依据一律指向 Linux kernel 源码文档（kernel.org/Documentation）──
    # 这些任务仅「分析/核对」系统已暴露的硬件可调项（/sys、/proc），默认不修改；
    # 调优动作以 manual 指引呈现，需用户确认后才落地。原生读取失败（非 Linux /
    # 内核未启用对应子系统）时优雅降级为「当前不适用」说明。

    Task(
        id="hw_cpufreq_governor",
        platform="linux",
        title="CPU 频率调节策略核对（CPUFreq）",
        category="hardware",
        risk="low",
        desc="按内核文档 admin-guide/pm/cpufreq.rst 核对当前调频 governor"
             "（schedutil/powersave/performance/ondemand），给出功耗/性能取舍建议。",
        actions=[N("hardware.cpufreq_governor",
                   "读取当前 scaling_governor 与可选 governor（参考 cpufreq.rst）")],
        standards=[
            "[国际] Linux kernel Documentation/admin-guide/pm/cpufreq.rst（CPUFreq 框架与 governor）",
        ],
        notes=[
            "参考内核文档 cpufreq.rst：schedutil/powersave 偏节能，performance 偏性能，"
            "ondemand/conservative 为经典采样策略。",
            "改 governor：echo schedutil > /sys/devices/system/cpu/cpufreq/policy0/scaling_governor"
            "（需 root，且不同发行版持久化方式不同）。",
        ],
        caveats=["改 governor 影响功耗与响应；笔记本用 schedutil/powersave 节能，"
                 "高负载服务器用 performance。"],
    ),
    Task(
        id="hw_cpuidle_optimize",
        platform="linux",
        title="CPU 空闲状态核对（cpuidle）",
        category="hardware",
        risk="low",
        desc="按内核文档 admin-guide/pm/cpuidle.rst 核对可用 C-state，"
             "给出节能/唤醒延迟权衡建议。",
        actions=[N("hardware.cpuidle_report",
                   "读取 cpuidle 空闲态（参考 cpuidle.rst）")],
        standards=[
            "[国际] Linux kernel Documentation/admin-guide/pm/cpuidle.rst（cpuidle 框架与 C-state）",
        ],
        notes=["参考内核文档 cpuidle.rst：越深 C-state 越省电，但唤醒延迟越大。"
               "限制最深 C-state 需内核/固件支持。"],
        caveats=["服务器/低延迟负载可限制最深 C-state，但会牺牲节能。"],
    ),
    Task(
        id="hw_intel_pstate",
        platform="linux",
        title="Intel P-State 调速器核对",
        category="hardware",
        risk="low",
        desc="按内核文档 admin-guide/pm/intel_pstate.rst 核对 intel_pstate 状态"
             "（active/passive），建议配合 schedutil。",
        actions=[N("hardware.intel_pstate_status",
                   "读取 intel_pstate/status（参考 intel_pstate.rst）")],
        standards=[
            "[国际] Linux kernel Documentation/admin-guide/pm/intel_pstate.rst（Intel P-State 调速器）",
        ],
        notes=["现代 Intel CPU 建议保留 intel_pstate（active），配合 schedutil 最稳；"
               "可经 max_perf_pct/min_perf_pct 限制性能窗口。"],
        caveats=["仅 Intel 平台有此接口；AMD 请改用 amd_pstate（amd-pstate.rst）。"],
    ),
    Task(
        id="hw_thermal_throttle",
        platform="linux",
        title="温控与降频核对（thermal sysfs）",
        category="hardware",
        risk="medium",
        desc="按内核文档 admin-guide/thermal/sysfs-api.rst 读取热区温度与策略，"
             "预警过热降频。",
        actions=[N("hardware.thermal_report",
                   "读取 /sys/class/thermal 热区（参考 thermal/sysfs-api.rst）")],
        standards=[
            "[国际] Linux kernel Documentation/admin-guide/thermal/sysfs-api.rst（thermal sysfs 接口）",
        ],
        notes=["过热降频会拖慢系统；软件仅能核对热区与阈值，硬件层面需清灰/换硅脂/改善风道。"],
        caveats=["温度阈值由固件/内核定义，软件层面无法长期压制过热，"
                 "属硬件维护范畴。"],
    ),
    Task(
        id="hw_thp_tune",
        platform="linux",
        title="透明大页（THP）策略核对",
        category="hardware",
        risk="low",
        desc="按内核文档 admin-guide/mm/transhuge.rst 核对 transparent_hugepage 状态"
             "（always/madvise/never），给出内存/延迟权衡。",
        actions=[N("hardware.thp_enabled",
                   "读取 transparent_hugepage/enabled（参考 transhuge.rst）")],
        standards=[
            "[国际] Linux kernel Documentation/admin-guide/mm/transhuge.rst（Transparent Hugepage）",
        ],
        notes=["THP 对大内存/数据库有收益，但对延迟敏感负载可能引入 compaction 抖动；"
               "用 madvise 更稳妥。"],
        caveats=["改 THP 状态需 root；never 可消除抖动但增加 TLB 压力。"],
    ),
    Task(
        id="hw_zswap",
        platform="linux",
        title="zswap 压缩交换缓存核对",
        category="hardware",
        risk="low",
        desc="按内核文档 mm/zswap.rst 核对 zswap 是否启用，"
             "给出换页压力下的内存扩展建议。",
        actions=[N("hardware.zswap_enabled",
                   "读取 /sys/module/zswap/parameters/enabled（参考 zswap.rst）")],
        standards=[
            "[国际] Linux kernel Documentation/mm/zswap.rst（压缩写回交换缓存）",
        ],
        notes=["zswap 以 CPU 换内存：换页前先压缩存入内存池，"
               "超限或失败再落入后端 swap。"],
        caveats=["低端机或已大量 swap 时收益明显，但会增加一点 CPU 占用；"
                 "可调 max_pool_percent 控制内存占用。"],
    ),
    Task(
        id="hw_zram",
        platform="linux",
        title="zram 内存压缩块设备核对",
        category="hardware",
        risk="low",
        desc="按内核文档 admin-guide/blockdev/zram.rst 核对 zram 设备，"
             "建议以压缩内存块替代磁盘 swap。",
        actions=[N("hardware.zram_report",
                   "读取 /sys/block/zram*（参考 blockdev/zram.rst）")],
        standards=[
            "[国际] Linux kernel Documentation/admin-guide/blockdev/zram.rst（内存压缩块设备）",
        ],
        notes=["把 /dev/zram<N> 用作 swap 比磁盘 swap 快得多；"
               "注意设置合理 disksize 并监控压缩率。"],
        caveats=["配置 zram 需 root；disksize 过大可能挤占可用内存。"],
    ),
    Task(
        id="hw_io_sched",
        platform="linux",
        title="I/O 调度器核对（BFQ/mq-deadline）",
        category="hardware",
        risk="low",
        desc="按内核文档 block/ 核对根盘队列调度器，"
             "SSD 建议 none/mq-deadline，机械盘建议 bfq。",
        actions=[N("hardware.io_scheduler",
                   "读取根盘 /queue/scheduler（参考 block/）")],
        standards=[
            "[国际] Linux kernel Documentation/block/（mq-deadline / bfq-iosched / kyber）",
        ],
        notes=["SSD/NVMe 用 none 或 mq-deadline；机械盘用 bfq 更顺滑；"
               "数据库盘改调度器前先评估延迟。"],
        caveats=["改调度器需重挂或写入 /sys；部分发行版默认已合理，谨慎改动。"],
    ),
    Task(
        id="hw_nvme",
        platform="linux",
        title="NVMe 固态盘核对（队列/TRIM）",
        category="hardware",
        risk="low",
        desc="按内核文档 nvme/index.rst 核对 NVMe 设备与多队列，"
             "结合 TRIM 维持性能。",
        actions=[
            N("hardware.nvme_report", "读取 /sys/class/nvme（参考 nvme/index.rst）"),
            N("hardware.disk_trim", "对 NVMe 根分区执行 fstrim（参考 ATA TRIM）"),
        ],
        standards=[
            "[国际] Linux kernel Documentation/nvme/index.rst（NVMe 子系统）",
            "[国际] INCITS T13 ATA/ATAPI TRIM（DATA SET MANAGEMENT）",
        ],
        notes=["NVMe 多队列默认可用，无需手工调 nr_requests；"
               "定期 fstrim 维持性能与寿命。"],
        caveats=["fstrim 需 util-linux；未装时仅 report。"],
    ),
    Task(
        id="hw_epb",
        platform="linux",
        arch="x86",
        title="x86 能效偏好（EPB）核对",
        category="hardware",
        risk="medium",
        desc="按内核 intel_pstate 文档核对 energy_perf_bias，"
             "给出性能/能效偏好建议（x86 专属）。",
        actions=[N("hardware.epb_read",
                   "读取 energy_perf_bias（参考 intel_pstate.rst / x86 MSR）")],
        standards=[
            "[国际] Linux kernel Documentation/admin-guide/pm/intel_pstate.rst"
            "（Intel P-State / x86 energy_perf_bias）",
        ],
        notes=["energy_perf_bias 0=性能优先、15=能效优先、6=平衡；"
               "可经 x86_energy_perf_policy 或 sysfs 设置。"],
        caveats=["改 EPB 需特权；仅 x86 Intel/AMD 支持，ARM/龙芯等无此接口（自动隐藏）。"],
    ),
    Task(
        id="hw_numa_balance",
        platform="linux",
        title="NUMA 自动平衡核对",
        category="hardware",
        risk="low",
        desc="按内核文档 admin-guide/mm/numa_memory_policy.rst 核对 numa_balancing，"
             "给出多路内存延迟优化建议。",
        actions=[N("hardware.numa_balancing",
                   "读取 /proc/sys/kernel/numa_balancing（参考 numa_memory_policy.rst）")],
        standards=[
            "[国际] Linux kernel Documentation/admin-guide/mm/numa_memory_policy.rst（NUMA 内存策略）",
        ],
        notes=["NUMA 平衡对单路/桌面收益有限，多路服务器才明显；"
               "误开可能引入跨节点开销。"],
        caveats=["多路服务器开启收益明显；单路/桌面误开反而有跨节点开销。"],
    ),
    Task(
        id="hw_watchdog",
        platform="linux",
        title="硬件看门狗心跳核对",
        category="hardware",
        risk="low",
        desc="按内核文档 watchdog/watchdog-api.rst 核对看门狗设备，"
             "确认守护进程保活，避免假死无重启。",
        actions=[N("hardware.watchdog_report",
                   "读取 /sys/class/watchdog（参考 watchdog-api.rst）")],
        standards=[
            "[国际] Linux kernel Documentation/watchdog/watchdog-api.rst（看门狗 API）",
        ],
        notes=["关键服务器应启用看门狗并配守护进程（如 watchdog/systemd）定期喂狗；"
               "超时则硬重启。"],
        caveats=["误关守护进程会导致周期性硬重启。"],
    ),
    Task(
        id="hw_vm_swappiness",
        platform="linux",
        title="交换倾向 vm.swappiness 核对",
        category="hardware",
        risk="low",
        desc="按内核文档 admin-guide/sysctl/vm.rst 核对 swappiness，"
             "给出内存压力下换页激进度建议。",
        actions=[N("hardware.vm_swappiness",
                   "读取 /proc/sys/vm/swappiness（参考 sysctl/vm.rst）")],
        standards=[
            "[国际] Linux kernel Documentation/admin-guide/sysctl/vm.rst（vm.swappiness）",
        ],
        notes=["0=尽量不换页、100=激进换页；桌面/服务器可适当降低以减少换页抖动。"],
        caveats=["内存极端紧张时过低 swappiness 易触发 OOM。"],
    ),
    Task(
        id="hw_sched_eas",
        platform="linux",
        title="能耗感知调度（EAS）核对",
        category="hardware",
        risk="low",
        desc="按内核文档 scheduler/sched-energy.rst 核对 sched_energy_aware，"
             "给出移动/笔记本节能调度建议。",
        actions=[N("hardware.eas_available",
                   "读取 /proc/sys/kernel/sched_energy_aware（参考 sched-energy.rst）")],
        standards=[
            "[国际] Linux kernel Documentation/scheduler/sched-energy.rst（Energy Aware Scheduling）",
        ],
        notes=["异构大小核（big.LITTLE / 混合架构）开启 EAS 收益最大；"
               "需 Energy Model 与 schedutil 配合。"],
        caveats=["仅异构/能效敏感平台意义大；同构桌面影响不大。"],
    ),
]
