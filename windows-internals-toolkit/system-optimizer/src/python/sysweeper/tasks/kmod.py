"""Linux 内核 module/firmware/eBPF 任务定义（v0.6.66；原 jvm.py 拆分）。

OpenJDK 部分已拆到同目录 `jdk.py`——按 omni 子系统「按 key 归位」原则，
一个任务文件对应一个子系统 key（本文件 ↔ `kmod` 系统，同时以 module 回退
满足 `firmware` / `modules` 两个子系统的 task 接线）。

这块的底线是**只读**：

- 内核 module/firmware/eBPF：只读 `/proc/modules`、`/sys/module`、
  `/sys/module/*/parameters`（**只读！写它=运行期改内核**）、`modinfo`、
  `/lib/firmware`。绝不 insmod/rmmod/modprobe、不替换固件、不 load/attach eBPF。

任务分两类：
- `kmod_*`：内核 module/firmware/eBPF 只读（platform="linux"）。
- 指引类：需要 root 或会改状态的动作，一律以 manual 文本给出，
  并显式写明「本工具不执行」。

对应 native 层：`native/kmod.py`（loaded_modules_report / sys_module_report /
module_params_report / modinfo_report / firmware_report / firmware_class_report /
bpf_capability_report / module_sysctl_report / blacklist_report /
power_state_report / thermal_report / kmod_report）。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)
S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)


TASKS = [
    # ------------------------------------------------------------------ #
    # Linux 内核 module / firmware / eBPF 只读（platform="linux"）        #
    # ------------------------------------------------------------------ #
    Task(
        id="kmod_loaded",
        platform="linux",
        title="已加载内核模块盘点（/proc/modules，只读）",
        category="hardware",
        risk="low",
        desc="读 /proc/modules：已加载可加载模块清单、内存合计、引用计数非 0 的模块。",
        actions=[N("kmod.loaded_modules_report", "读 /proc/modules（只读，不 insmod/rmmod）")],
        standards=["[官方] Linux Kernel Documentation：admin-guide/modules.rst",
                   "[官方] /proc/modules（proc(5) 内核模块表）",
                   "[国际] Linux Kernel 源码：kernel/module（load_module / 模块状态机）"],
        notes=["refcnt 非 0 = 模块仍被引用，卸载必然失败——这是「rmmod 报模块在用」的根因。",
               "内建模块（builtin）不出现在 /proc/modules，而在 /sys/module 下且 initstate=builtin。"],
        caveats=["**卸载内核模块是 root 级高危操作**，用错一个可致网络/存储不可用甚至不可开机。"
                 "本工具只给判断依据与官方指引，绝不代为卸载。"],
    ),
    Task(
        id="kmod_sysfs",
        platform="linux",
        title="模块 sysfs 全景（builtin vs 可加载，只读）",
        category="hardware",
        risk="low",
        desc="遍历 /sys/module，统计内建/可加载模块数与暴露参数节点数量。",
        actions=[N("kmod.sys_module_report", "读 /sys/module（只读，统计模块与参数节点）")],
        standards=["[官方] Linux Kernel Documentation：admin-guide/modules.rst",
                   "[官方] sysfs ABI：/sys/module/<name>/（initstate / refcnt / parameters / sections）",
                   "[国际] Linux Kernel 源码：kernel/kparam.c（kparam 注册与 sysfs 导出）"],
        notes=["「暴露了 parameters 的模块数」= 可调内核行为的入口数量，是判断驱动可调性的量化指标。"],
        caveats=["写 /sys/module/*/parameters/* 等于运行期改内核行为——本工具**只读**。"],
    ),
    Task(
        id="kmod_params",
        platform="linux",
        title="关键模块参数当前值（只读 sysfs）",
        category="hardware",
        risk="low",
        desc="只读列出拥塞控制、intel_powerclamp、nf_conntrack 等模块参数的当前值。",
        actions=[N("kmod.module_params_report", "读 /sys/module/*/parameters（只读，绝不 echo 写入）")],
        standards=["[官方] Linux Kernel Documentation：admin-guide/quick-kparams.rst",
                   "[官方] sysfs ABI：module parameters",
                   "[国际] /proc/sys/net/ipv4/tcp_congestion_control（拥塞控制模块侧对应）"],
        notes=["完整参数清单用只读命令：ls /sys/module/*/parameters/。",
               "调参前务必看 kernel.org 对应 Documentation 确认语义与取值域。"],
        caveats=["**写这些节点=运行期改内核**（如改 rmem_max、改内存回收行为），属高危操作，"
                 "本工具只读且不给自动修复。"],
    ),
    Task(
        id="kmod_modinfo",
        platform="linux",
        title="模块元数据与许可证分布（modinfo，只读）",
        category="hardware",
        risk="low",
        desc="用 modinfo 汇总已加载模块的 license 字段分布，辅助判断 taint 来源。",
        actions=[N("kmod.modinfo_report", "modinfo -F license（只读，批量汇总许可证）")],
        standards=["[官方] Linux Kernel Documentation：admin-guide/modules.rst",
                   "[官方] modinfo(8) / lsmod(8)（kmod 工具）",
                   "[国际] Linux Kernel 源码：include/linux/module.h（MODULE_LICENSE 宏与 taint）"],
        notes=["加载「专有」或「GPL 不兼容」许可证的模块会让内核被标记 tainted，"
               "之后内核会把责任推给该模块、不再报它的 bug。",
               "查单模块：modinfo <name>；查固件需求：modinfo -F firmware <name>。"],
        caveats=["未安装 kmod 工具包时会明确降级，不报错。"],
    ),
    Task(
        id="kmod_firmware",
        platform="linux",
        title="内核固件库盘点（/lib/firmware，只读统计）",
        category="hardware",
        risk="low",
        desc="统计固件库目录的顶层分类、文件数与体积，辅助定位「设备功能静默失效」类问题。",
        actions=[N("kmod.firmware_report", "统计 /lib/firmware（只读，绝不替换固件）")],
        standards=["[官方] Linux Kernel Documentation：driver-api/firmware/（request_firmware 框架）",
                   "[官方] firmware_class 设备模型（/sys/class/firmware）",
                   "[国际] Linux Kernel 源码：drivers/base/firmware_loader/"],
        notes=["固件缺失的表现是「设备功能静默失效」（不报错、不崩），"
               "排查网卡/显卡/打印机/无线不工作时第一件事就是看固件在不在。",
               "只读自查某模块需要哪些固件：modinfo -F firmware <mod>。"],
        caveats=["**绝不从非官方渠道替换固件**——错配的固件会让硬件直接不可用。"
                 "本工具只统计体积与分类，不删不换。"],
    ),
    Task(
        id="kmod_firmware_class",
        platform="linux",
        title="已加载固件标识核对（/sys/class/firmware，只读）",
        category="hardware",
        risk="low",
        desc="读 firmware_class 已注册的设备与实际加载到的固件标识，确认驱动走的是哪份固件。",
        actions=[N("kmod.firmware_class_report", "读 /sys/class/firmware（只读，看已加载固件）")],
        standards=["[官方] Linux Kernel Documentation：driver-api/firmware/",
                   "[官方] sysfs ABI：/sys/class/firmware/<name>/device/firmware",
                   "[国际] request_firmware() 固件缓存机制（同一固件只加载一次）"],
        notes=["纯 CPU 计算节点上通常没有条目（无设备走固件流程），属正常。"],
        caveats=["固件标识可能含内网设备序列号等环境信息，属本机自检，勿外传。"],
    ),
    Task(
        id="kmod_bpf",
        platform="linux",
        title="eBPF 能力体检（BTF / bpffs / 非特权开关，只读）",
        category="maintenance",
        risk="low",
        desc="核对内核 BTF 是否可用、bpffs 是否挂载、非特权 BPF 开关状态与可挂 kprobe 函数数量。",
        actions=[N("kmod.bpf_capability_report", "读 BTF/bpffs/unprivileged_bpf_disabled（只读）")],
        standards=["[官方] Linux Kernel Documentation：bpf/（eBPF 完整文档树）",
                   "[官方] /proc/sys/kernel/unprivileged_bpf_disabled（内核安全开关）",
                   "[国际] Linux Kernel 源码：kernel/bpf/（verifier / CO-RE / BPF-CPU 布局）"],
        notes=["有 BTF → BPF CO 可用：同一份 .o 能跨内核版本加载（libbpf 按 BTF 重定位）。",
               "unprivileged_bpf_disabled=1 是较安全的基线（防非特权注入内核态程序）。",
               "eBPF 是现代 Linux 事实上的「内核级可编程插件」：Cilium/bpftrace/systemd 单元都建在它上面。"],
        caveats=["**不 attach、不 load 任何 BPF 程序**——加载需 CAP_BPF/CAP_SYS_ADMIN，"
                 "挂错程序可能拖垮内核路径。"],
    ),
    Task(
        id="kmod_sysctl",
        platform="linux",
        title="内核模块/加载相关 sysctl（taint / modules_disabled，只读）",
        category="maintenance",
        risk="low",
        desc="读 tainted、modules_disabled、unprivileged_bpf_disabled、kptr_restrict 等关键开关。",
        actions=[N("kmod.module_sysctl_report", "读 /proc/sys/kernel 模块相关 sysctl（只读）")],
        standards=["[官方] Linux Kernel Documentation：admin-guide/sysctl/kernel.rst",
                   "[官方] /proc/sys/kernel/tainted（内核 taint 标记）",
                   "[国际] Linux Kernel 源码：kernel/tainted.c（taint 传播规则）"],
        notes=["tainted 非空 = 内核被标记「不再为其报 bug」，通常因为加载了专有模块等。",
               "modules_disabled=1 表示已禁止再加载新模块（加固状态）。",
               "kptr_restrict=1 限制 /proc 里的内核地址暴露（较安全）。"],
        caveats=["**写这些 sysctl 会真改系统行为**（如清 taint、禁止加载模块），本工具只读。"],
    ),
    Task(
        id="kmod_blacklist",
        platform="linux",
        title="modprobe 黑名单/加载策略（只读）",
        category="maintenance",
        risk="low",
        desc="只读列出 /etc/modprobe.d 与内核命令行里的 blacklist / install 指令。",
        actions=[N("kmod.blacklist_report", "读 /etc/modprobe.d 与 /proc/cmdline 的黑名单（只读）")],
        standards=["[官方] modprobe.d(5)（blacklist / install / remove 指令语义）",
                   "[官方] Linux Kernel Documentation：admin-guide/quick-kparams.rst",
                   "[国际] systemd 视角：modprobe 规则实际是包一层的 udev hook"],
        notes=["黑名单本质是 modprobe 侧拒绝加载，**不是内核级硬禁止**——"
               "用 insmod 仍可能绕过。",
               "批量黑名单第三方驱动（部分开源网卡驱动）省电效果因机型而异。"],
        caveats=["**不写 /etc/modprobe.d**——改加载策略是 root 级改动，"
                 "配错会导致开不了无线网卡，只能从救援模式改回。"],
    ),
    Task(
        id="kmod_power",
        platform="linux",
        title="电源状态与温区（/sys/power、/sys/class/thermal，只读）",
        category="hardware",
        risk="low",
        desc="读睡眠态支持、mem_sleep 策略与各温区当前温度。",
        actions=[N("kmod.power_state_report", "读 /sys/power（只读，不写 sleep state）"),
                 N("kmod.thermal_report", "读 /sys/class/thermal（只读温区）")],
        standards=["[官方] Linux Kernel Documentation：power/（电源管理子系统）",
                   "[官方] sysfs ABI：/sys/power/{state,mem_sleep}",
                   "[国际] Linux Kernel Documentation：thermal/（thermal framework）"],
        notes=["mem_sleep=auto 由系统自行选 suspend/hibernate；deep=进 hibernate。",
               "温区由 thermal framework 统一导出；容器/虚拟机中可能被屏蔽。"],
        caveats=["**写 /sys/power/state 会让机器真的睡下去**（数据风险），本工具绝不执行。",
                 "调温控策略（写 trip_point）属 root 级改动，同样只给指引。"],
    ),
    Task(
        id="kmod_unload_guide",
        platform="linux",
        title="内核模块卸载/固件更换：只给指引的高危清单",
        category="maintenance",
        risk="low",
        desc="把「卸载模块、换固件、锁 BPF、改加载策略」等高危动作与前置检查写成指引文本。",
        actions=[M("卸载前必查：① cat /proc/modules 看该模块 refcnt 是否为 0；"
                   "② lsmod | grep <name> 确认无人使用；"
                   "③ 用 modinfo -F firmware <name> 确认它要哪些固件；"
                   "④ 确认有可用的救援/回滚手段（Live USB 或另一终端）。"
                   "常见场景：开源驱动换回官方驱动省电（rtw88/ath10k 等），"
                   "先用 modprobe -r <name> 卸掉旧模块（**这一步本工具不代做**），"
                   "再装官方包并重启验证。"
                   "固件更换只从发行版官方包或硬件厂商官方渠道获取。",
                  "模块卸载与固件更换的前置检查清单（只读指引）")],
        standards=["[官方] modprobe(8) / rmmod(8) / insmod(8) / depmod(8)",
                   "[官方] Linux Kernel Documentation：admin-guide/modules.rst",
                   "[国标] GB/T 22239《信息安全技术 网络安全等级保护基本要求》（系统变更需审批留痕）"],
        notes=["本任务是 manual 文本：把高危动作的前置条件讲清楚，而不是替用户按下按钮。"],
        caveats=["卸载关键模块（存储/网络/输入子系统）可能直接导致系统不可用甚至不可开机。"],
    ),
]
