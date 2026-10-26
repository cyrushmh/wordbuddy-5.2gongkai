"""内核调优（sysctl）只读体检任务定义（v0.6.66 新增）。

按 omni 子系统「按 key 归位」原则，本文件 ↔ `kernel` 子系统。

说明：软件/网络子系统的单点调优任务（linux_sched_cfs 等 10 项）
已在同库 `linux.py` 注册（带各自的内核文档标准），本文件只补
「内核调优只读聚合总览」一个入口——串联 scheduler / cgroup-v2 /
OOM / PSI / THP / vm-sysctl / TCP / 拥塞控制 / net.core / RPS 十个
native 子报告，一次看完当前值，**不修改任何设置**。

细项任务的优化依据一律指向 kernel.org/Documentation；本机核对只读
/sys、/proc。`sysweaver kernel` 命令会列出所有引用内核文档的 Linux
任务（本任务的 standards 含 "Linux kernel Documentation" 字样，
与细项任务同一口径）。

对应 native 层：`native/kernel.py`（kernel_report 聚合 +
sched_report / cgroup_v2_report / oom_report / psi_report /
thp_compaction_report / vm_dirty_report / tcp_report /
tcp_congestion_report / net_core_report / rps_report）。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)
S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)


TASKS = [
    # ------------------------------------------------------------------ #
    # 内核调优只读聚合总览（platform="linux"）                             #
    # ------------------------------------------------------------------ #
    Task(
        id="kernel_sysctl_overview",
        platform="linux",
        title="内核调优只读总览（调度/内存/网络子系统当前值）",
        category="optimize",
        risk="low",
        desc="一次读完全部内核调优相关子系统的当前值：CFS 调度、cgroups v2、"
             "OOM 防护、PSI 资源压力、THP 规整、vm 脏页/缓存、TCP 协议栈、"
             "TCP 拥塞控制、net.core、RPS/RFS。**只读不改**。",
        actions=[N("kernel.kernel_report", "十项内核子系统只读报告一次串联（不改任何设置）")],
        standards=[
            "[国际] Linux kernel Documentation/admin-guide/sysctl/（内核调优总入口）",
            "[国际] Linux kernel Documentation/scheduler/sched-design-CFS.rst（完全公平调度器）",
            "[国际] Linux kernel Documentation/admin-guide/cgroup-v2.rst（统一资源控制层级）",
            "[国际] Linux kernel Documentation/networking/（TCP / 拥塞控制 / net.core / RPS）",
        ],
        notes=[
            "串联顺序即「先看调度与内存，再看网络」的排障路径：应用响应慢先看 PSI/OOM，"
            "网络吞吐上不去先看拥塞控制与 RPS。",
            "聚合里的每一项都有对应的细项优化任务（linux_sched_cfs 等，见 tasks/linux.py），"
            "本任务是总览入口，细项任务是单点深入。",
            "慢盘/大内存场景常见疑点：vm.dirty_ratio 触发同步写卡顿、"
            "THP 规整时延尖刺、拥塞控制仍是 cubic 而内核已支持 BBR——"
            "都从这里先看到当前值，再决定要不要动手。",
            "sysctl 写入是 root 级改动且需持久化（/etc/sysctl.d），本工具一律只读。",
        ],
        caveats=["**不在容器/虚拟机里改宿主内核参数**——看到的可能是命名空间内口径；"
                 "本工具只报告，任何调整请以 kernel.org Documentation 与实测压测为准。"],
    ),
]
