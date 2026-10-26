"""Linux 平台任务定义。

版本按发行版（Ubuntu/Debian/Fedora/Arch…）区分，命令内用 `command -v` 做
发行版自适应，未安装对应包管理器的发行版该任务自动空转，不会报错。
大多数深度清理需要 root（sudo）。
"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="linux_pkg_cache",
        platform="linux",
        title="清理包管理器缓存",
        category="cleanup",
        risk="low",
        desc="清除 apt / dnf / pacman 的下载缓存。",
        actions=[
            S('if command -v apt-get >/dev/null; then sudo apt-get clean; fi',
              "清理 apt 缓存", rev=True),
            S('if command -v dnf >/dev/null; then sudo dnf clean all; fi',
              "清理 dnf 缓存", rev=True),
            S('if command -v paccache >/dev/null; then sudo paccache -r; fi',
              "清理 pacman 旧包", rev=True),
        ],
        notes=["仅删除已下载的安装包，不影响已装软件。"],
    ),
    Task(
        id="linux_orphan",
        platform="linux",
        title="移除孤立/无用依赖",
        category="maintenance",
        risk="medium",
        desc="卸载不再被需要的依赖包（autoremove / 孤包）。",
        actions=[
            S('if command -v apt-get >/dev/null; then sudo apt-get autoremove -y; fi',
              "apt 自动移除孤包"),
            S('if command -v pacman >/dev/null; then sudo pacman -Rns $(pacman -Qtdq) 2>/dev/null; fi',
              "pacman 移除孤包"),
        ],
        caveats=["可能顺带移除你手动装但无其他依赖的软件，执行前会列出。"],
    ),
    Task(
        id="linux_journal",
        platform="linux",
        title="压缩/清理 systemd 日志",
        category="maintenance",
        risk="medium",
        desc="将日志体积限制到 200MB。用 journalctl 原生接口。",
        actions=[Action("native", "linux.journal_vacuum", "压缩日志至 200M（journalctl 接口）")],
        caveats=["journalctl 不存在的发行版（如非 systemd）该任务自动跳过。"],
    ),
    Task(
        id="linux_thumbnail",
        platform="linux",
        title="清理缩略图缓存",
        category="cleanup",
        risk="low",
        desc="删除 ~/.cache/thumbnails。",
        actions=[S('rm -rf "$HOME/.cache/thumbnails"', "清空缩略图缓存", rev=True)],
        notes=["下次打开文件管理器会重新生成。"],
    ),
    Task(
        id="linux_user_cache",
        platform="linux",
        title="清理用户缓存目录",
        category="cleanup",
        risk="low",
        desc="清理 ~/.cache 下可安全删除的缓存。",
        actions=[S('find "$HOME/.cache" -type f -mtime +30 -delete 2>/dev/null',
                   "删除 30 天前的用户缓存文件", rev=True)],
        notes=["仅删旧文件，不影响正在使用的缓存。"],
    ),
    Task(
        id="linux_swappiness",
        platform="linux",
        title="优化交换倾向（swappiness）",
        category="optimize",
        risk="medium",
        desc="桌面/大内存机器可降低 swappiness 减少不必要换页。",
        actions=[
            S('echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.d/99-sysweeper.conf >/dev/null',
              "设置 swappiness=10"),
            S('sudo sysctl -w vm.swappiness=10', "立即生效"),
        ],
        caveats=["服务器/低内存机器不建议过低；修改前请了解 swap 策略。"],
        notes=["重启后由 sysctl.d 文件持久化。"],
        standards=["[国际] Linux kernel Documentation/admin-guide/sysctl/vm.rst（vm.swappiness）"],
    ),
    Task(
        id="linux_kernel_note",
        platform="linux",
        title="内核清理注意事项",
        category="maintenance",
        risk="low",
        desc="保留正在运行的内核，不要删除当前启动内核。",
        actions=[],
        caveats=["apt autoremove 默认会保留当前及上一个内核；切勿手动 rm /boot/vmlinuz-* 当前内核。"],
        notes=["可用 `uname -r` 确认当前内核，再决定清理哪些旧内核。"],
    ),
    Task(
        id="linux_distro_report",
        platform="linux",
        title="发行版信息报告（LSB）",
        category="maintenance",
        risk="low",
        desc="用 LSB 规范文件 /etc/os-release 读取发行版与版本，供优化前确认环境。",
        actions=[Action("native", "linux.detect_distro", "读取发行版（LSB /etc/os-release）")],
        notes=["LSB 是 Linux 标准基线的发行版信息规范；解析失败会自动降级到 lsb_release 命令与 uname。"],
    ),
    Task(
        id="linux_docker_prune",
        platform="linux",
        title="清理 Docker 闲置资源",
        category="cleanup",
        risk="medium",
        desc="用 docker system prune 清理已停止容器、未用网络与悬空镜像（需 docker 守护进程）。",
        actions=[S(
            'if command -v docker >/dev/null; then docker system prune -f; else echo "未安装 docker，跳过"; fi',
            "清理 Docker 悬空资源（不含卷，保守）", rev=True)],
        notes=["仅删除「悬空（dangling）」镜像与已停止容器；不含命名卷，避免误删数据。"],
        caveats=["会移除未打标签的悬空镜像；运行中的容器不受影响。docker 未运行则自动跳过。"],
    ),
    Task(
        id="linux_flatpak_cache",
        platform="linux",
        title="清理 Flatpak 未用运行时",
        category="cleanup",
        risk="low",
        desc="用 flatpak uninstall --unused 移除不再被任何应用引用的运行时（需 flatpak）。",
        actions=[S(
            'if command -v flatpak >/dev/null; then flatpak uninstall --unused -y; else echo "未安装 flatpak，跳过"; fi',
            "卸载未使用的 Flatpak 运行时", rev=True)],
        notes=["仅移除「无应用引用」的运行时；当前已装应用不受影响。"],
        caveats=["无 flatpak 时自动跳过——不强求安装。"],
    ),
    Task(
        id="linux_snap_cache",
        platform="linux",
        title="清理 Snap 旧版本修订",
        category="cleanup",
        risk="low",
        desc="移除 Snap 已禁用（被新版取代）的旧修订，回收空间（需 snap）。",
        actions=[S(
            'if command -v snap >/dev/null; then '
            'snap list --all | awk \'NR>1 && $4=="disabled" {print "snap remove "$1" --revision="$2}\' | sh; '
            'else echo "未安装 snap，跳过"; fi',
            "移除已禁用的 Snap 旧修订", rev=True)],
        notes=["仅删除标记为 disabled 的旧修订（升级后产生），当前版本不受影响。"],
        caveats=["无 snap 时自动跳过；误删当前版本会由 snap 自动保护（awk 只选 disabled）。"],
    ),
    Task(
        id="linux_io_scheduler",
        platform="linux",
        title="SSD / NVMe IO 调度器调优",
        category="optimize",
        risk="medium",
        desc="为 SSD/NVMe 设置 none 或 mq-deadline 调度器，降低延迟、延长寿命（需 root）。",
        actions=[S(
            'for d in /sys/block/*/queue/scheduler; do '
            'if grep -q "none" "$d" 2>/dev/null; then echo none | sudo tee "$d" >/dev/null; fi; done; '
            'echo "已为块设备设置 none 调度器（NVMe 本就默认 none）"',
            "为块设备设置 none/mq-deadline 调度器（需 root）")],
        notes=["NVMe 默认即为 none，无需改动；SATA SSD 建议 none 或 mq-deadline。"
                "此修改重启后失效，需写 udev 规则或内核参数才能持久化。"],
        caveats=["需 root；高负载磁盘改错调度可能影响吞吐，建议先测再固化。"],
        standards=["[国际] Linux kernel Documentation/block/（I/O 调度器 mq-deadline/bfq/kyber）"],
    ),
    Task(
        id="linux_swap_tuning",
        platform="linux",
        title="swappiness / 缓存回收调优",
        category="optimize",
        risk="low",
        desc="下调 vm.swappiness 减少过早换出、提升交互响应（内存充足时）；可临时或写 sysctl 持久。",
        actions=[S(
            "sudo sysctl -w vm.swappiness=10; "
            'echo "已临时设置 vm.swappiness=10（重启失效）"',
            "临时下调 swappiness（需 root；持久可写 /etc/sysctl.d）")],
        notes=["默认多为 60；大内存桌面可降到 10；仅影响换出倾向，不影响功能。"],
        caveats=["内存紧张时过低 swappiness 可能触发 OOM；按实际内存调整。"],
        standards=["[国际] Linux kernel Documentation/admin-guide/sysctl/vm.rst（vm.swappiness）"],
    ),

    Task(
        id="linux_zfs_trim",
        platform="linux",
        title="ZFS 存储池 TRIM / autotrim",
        category="maintenance",
        risk="low",
        desc="按 OpenZFS 规范对 zpool 执行 trim（或开启 autotrim），维持 SSD 上的空间回收。",
        actions=[S('if command -v zpool >/dev/null; then zpool trim -w $(zpool list -H -o name) 2>/dev/null || zpool trim $(zpool list -H -o name); else echo "无 zpool，跳过"; fi',
                   "对全部 zpool 执行 TRIM（OpenZFS 原生命令）")],
        standards=["[国际] OpenZFS（ZFS On-Disk Specification / zpool(8)）"],
        notes=["也可 `zpool set autotrim=on <pool>` 让 ZFS 自动回收；机械盘无需 TRIM。"],
        caveats=["大规模 TRIM 期间 IO 有开销；生产环境建议低峰执行。"],
    ),
    Task(
        id="linux_fwupd",
        platform="linux",
        title="固件更新检查（fwupd / LVFS）",
        category="maintenance",
        risk="low",
        desc="用 fwupd 查询可用固件更新（LVFS 源），列出待更新的固件版本。",
        actions=[S('if command -v fwupdmgr >/dev/null; then fwupdmgr get-devices 2>/dev/null; fwupdmgr get-updates 2>/dev/null || echo "无可用更新或无权限"; else echo "未安装 fwupd，跳过"; fi',
                   "查询固件设备与可用更新（fwupd 原生命令）")],
        standards=["[国际] LVFS / fwupd（Linux 厂商固件服务，UEFI 胶囊更新）",
                   "[国际] UEFI Specification（UEFI Forum，胶囊更新机制）"],
        notes=["只读查询；实际刷新需 `fwupdmgr update` 且常需重启。"],
        caveats=["固件更新有风险，务必在供电稳定的情况下进行。"],
    ),
    Task(
        id="linux_loongarch_source",
        platform="linux",
        arch="loongarch",
        title="龙芯平台（LoongArch）源与包管理核对",
        category="arch",
        risk="low",
        desc="在龙芯 Linux 上核对发行版源与包架构（loong64/loongarch64），避免装错架构包。",
        actions=[S('echo "arch=$(uname -m)"; if command -v dpkg >/dev/null; then dpkg --print-architecture; '
                   'elif command -v rpm >/dev/null; then rpm -E %{_arch}; fi; '
                   'if command -v apt-get >/dev/null; then apt-get -s upgrade 2>/dev/null | tail -3; '
                   'elif command -v dnf >/dev/null; then dnf -q check-update 2>/dev/null | tail -3; fi',
                   "核对架构与可用更新（发行版包管理原生命令）")],
        standards=["[国标] 龙芯 LoongArch 指令集架构（国产自主，国家平台 std.samr.gov.cn）"],
        notes=["龙芯平台应使用对应架构的源（如 loongnix/Loong 源）；x86 包不可用（除非经 LBT 翻译）。"],
        caveats=["仅做模拟/查询，不实际升级。"],
    ),
    Task(
        id="linux_mips_cleanup",
        platform="linux",
        arch="mips",
        title="MIPS / 嵌入式设备精简清理",
        category="arch",
        risk="low",
        desc="MIPS 路由器与嵌入式设备上按端序与 ABI 核对后清理缓存与日志，释放有限存储。",
        actions=[S('echo "machine=$(uname -m)"; '
                   'for d in /tmp /var/log /var/cache; do [ -d "$d" ] && du -sh "$d" 2>/dev/null; done; '
                   'find /var/log -type f -name "*.log.*" -mtime +7 -print 2>/dev/null | head -20',
                   "清点临时与日志占用并列出可归档的旧日志")],
        standards=["[国际] MIPS Architecture for Programmers（MIPS32 / MIPS64 Release 6）"],
        notes=["端序（mips 大端 / mipsel 小端）与 ABI（o32/n32/n64）需与已装软件一致。",
               "嵌入式设备存储小，先清缓存与轮转日志收益最直接。"],
        caveats=["嵌入式固件常为只读文件系统，清理前确认可写分区。"],
    ),

    # ── Linux 整体优化：标准依据一律指向 Linux kernel 源码文档（kernel.org/Documentation）──
    # 软件子系统（scheduler / cgroup-v2 / oom / psi / thp-compaction / vm-sysctl）与
    # 网络子系统（tcp / 拥塞控制 / net.core / rps）的核对任务。仅「分析/核对」系统已
    # 暴露的 /sys、/proc 接口，默认不修改；调优动作以 manual 指引呈现，需确认后才落地。

    Task(
        id="linux_sched_cfs",
        platform="linux",
        title="CFS 调度器参数核对",
        category="optimize",
        risk="low",
        desc="按内核文档 scheduler/sched-design-CFS.rst 核对 CFS 关键 sysctl"
             "（sched_latency_ns / min_granularity_ns / migration_cost_ns），给响应/吞吐建议。",
        actions=[N("kernel.sched_report",
                   "读取 CFS sysctl（参考 sched-design-CFS.rst）")],
        standards=[
            "[国际] Linux kernel Documentation/scheduler/sched-design-CFS.rst（完全公平调度器）",
        ],
        notes=["CFS 以 vruntime 公平分配 CPU；桌面可略降 sched_latency_ns 提升响应，服务器保持默认。"],
        caveats=["改调度 sysctl 影响全局公平性与延迟；生产环境先评估再固化。"],
    ),
    Task(
        id="linux_cgroup_v2",
        platform="linux",
        title="cgroups v2 层级核对",
        category="optimize",
        risk="low",
        desc="按内核文档 admin-guide/cgroup-v2.rst 核对 cgroups v2 统一层级与已委托控制器，"
             "给出资源隔离（cpu.weight/memory.max）建议。",
        actions=[N("kernel.cgroup_v2_report",
                   "读取 cgroup.controllers / subtree_control（参考 cgroup-v2.rst）")],
        standards=[
            "[国际] Linux kernel Documentation/admin-guide/cgroup-v2.rst（统一资源控制层级）",
        ],
        notes=["桌面发行版默认由 systemd 挂载 v2；为关键服务设 cpu.weight/memory.max 可防单进程拖垮整机。"],
        caveats=["误配 subtree_control 可能使子组收不到控制器；改前确认层级结构。"],
    ),
    Task(
        id="linux_oom_guard",
        platform="linux",
        title="OOM 防护核对",
        category="maintenance",
        risk="low",
        desc="按内核文档 mm/oom_kill.rst 核对 OOM 防护 sysctl 与当前进程 oom_score_adj，"
             "给出关键守护进程保护建议。",
        actions=[N("kernel.oom_report",
                   "读取 panic_on_oom / oom_score_adj（参考 oom_kill.rst）")],
        standards=[
            "[国际] Linux kernel Documentation/mm/oom_kill.rst（OOM 终止与内存压力防护）",
        ],
        notes=["用 oom_score_adj(-1000~1000) 保护关键守护进程（如设为 -500）；-1000 使其永不成为牺牲品。"],
        caveats=["oom_score_adj 误设为 -1000 会令该进程永不回收，可能拖垮系统；谨慎保护。"],
    ),
    Task(
        id="linux_psi",
        platform="linux",
        title="资源压力失忆（PSI）核对",
        category="maintenance",
        risk="low",
        desc="按内核文档 accounting/psi.rst 读取 CPU/内存/IO 压力占比，预警资源争用瓶颈。",
        actions=[N("kernel.psi_report",
                   "读取 /proc/pressure/{cpu,memory,io}（参考 psi.rst）")],
        standards=[
            "[国际] Linux kernel Documentation/accounting/psi.rst（资源压力失忆 PSI）",
        ],
        notes=["监控 memory/io 的 full 占比可提前发现瓶颈；容器与桌面守护进程常用 PSI 做自适应限流。"],
        caveats=["未启用 PSI 的内核无 /proc/pressure（自动降级为说明）。"],
    ),
    Task(
        id="linux_thp_compaction",
        platform="linux",
        title="THP 规整策略核对",
        category="optimize",
        risk="low",
        desc="按内核文档 admin-guide/mm/transhuge.rst 核对 transparent_hugepage/defrag 与"
             " compaction 策略，给延迟敏感负载建议。",
        actions=[N("kernel.thp_compaction_report",
                   "读取 transparent_hugepage/defrag（参考 transhuge.rst）")],
        standards=[
            "[国际] Linux kernel Documentation/admin-guide/mm/transhuge.rst（透明大页与规整 compaction）",
        ],
        notes=["延迟敏感负载用 defrag=madvise 避免分配时同步规整抖动；compact_memory 可手动触发全系统规整。"],
        caveats=["改 defrag 策略需 root；never 可消除抖动但增加 TLB 压力。"],
    ),
    Task(
        id="linux_vm_dirty",
        platform="linux",
        title="脏页回写/缓存回收核对",
        category="optimize",
        risk="low",
        desc="按内核文档 admin-guide/sysctl/vm.rst 核对 dirty_* 与 vfs_cache_pressure，"
             "给写缓冲与目录缓存回收建议。",
        actions=[N("kernel.vm_dirty_report",
                   "读取 vm/dirty_* / vfs_cache_pressure（参考 sysctl/vm.rst）")],
        standards=[
            "[国际] Linux kernel Documentation/admin-guide/sysctl/vm.rst（脏页回写与缓存回收）",
        ],
        notes=["大内存/数据库可调高 dirty_* 平滑写峰；频繁列目录负载可降 vfs_cache_pressure 保目录缓存。"],
        caveats=["极端值可能引发写阻塞或目录缓存频繁回收；按实际负载调整。"],
    ),
    Task(
        id="linux_tcp_tuning",
        platform="linux",
        title="TCP 协议栈参数核对",
        category="network",
        risk="low",
        desc="按内核文档 networking/ip-sysctl.rst 核对 TCP 缓冲(tcp_rmem/wmem)与特性开关"
             "（SACK/时间戳/窗口缩放），给吞吐建议。",
        actions=[N("kernel.tcp_report",
                   "读取 tcp_rmem/wmem/sack/timestamps（参考 ip-sysctl.rst）")],
        standards=[
            "[国际] Linux kernel Documentation/networking/ip-sysctl.rst（TCP 协议栈参数）",
        ],
        notes=["长肥管道可调高 tcp_rmem 上限提升吞吐；时间戳/SACK 一般保持开启，仅老旧链路异常才关。"],
        caveats=["改 tcp_* 影响全机网络；跨境/高延迟链路调优前先测基线。"],
    ),
    Task(
        id="linux_tcp_congestion",
        platform="linux",
        title="TCP 拥塞控制核对（BBR）",
        category="network",
        risk="low",
        desc="按内核文档 networking/ip-sysctl.rst 核对当前拥塞控制算法与可用项，"
             "给长肥管道改用 BBR 的建议。",
        actions=[N("kernel.tcp_congestion_report",
                   "读取 tcp_congestion_control / available（参考 ip-sysctl.rst）")],
        standards=[
            "[国际] Linux kernel Documentation/networking/ip-sysctl.rst（拥塞控制含 BBR）",
        ],
        notes=["长肥管道与跨境链路用 BBR 更稳定高效（需内核编译 tcp_bbr）；普通内网 Cubic 足够。"],
        caveats=["误选未编译算法会回退到默认；改拥塞控制需 root。"],
    ),
    Task(
        id="linux_net_core",
        platform="linux",
        title="网络核心参数核对（net.core）",
        category="network",
        risk="low",
        desc="按内核文档 networking/ip-sysctl.rst 核对 net.core（netdev_max_backlog/budget/"
             "rmem_max/wmem_max/somaxconn），给高 PPS 服务器建议。",
        actions=[N("kernel.net_core_report",
                   "读取 net/core/*（参考 ip-sysctl.rst）")],
        standards=[
            "[国际] Linux kernel Documentation/networking/ip-sysctl.rst（net.core 参数）",
        ],
        notes=["高 PPS 服务器可调高 netdev_max_backlog/netdev_budget 与 rmem_max/wmem_max；somaxconn 影响并发 accept。"],
        caveats=["盲目调大缓冲可能增大延迟与内存占用；按实测吞吐调整。"],
    ),
    Task(
        id="linux_rps",
        platform="linux",
        title="接收侧缩放（RPS/RFS）核对",
        category="network",
        risk="low",
        desc="按内核文档 networking/scaling.rst 核对网卡 RPS/RFS 配置，给单队列网卡多核利用建议。",
        actions=[N("kernel.rps_report",
                   "读取 rx-*/rps_cpus（参考 scaling.rst）")],
        standards=[
            "[国际] Linux kernel Documentation/networking/scaling.rst（RPS / RFS 接收侧缩放）",
        ],
        notes=["单队列/多队列不足网卡用 RPS/RFS 提升多核利用率；多队列智能网卡通常无需开启。"],
        caveats=["rps_cpus 填错 CPU 位可能把软中断集中到少数核，需按拓扑设置。"],
    ),
]
