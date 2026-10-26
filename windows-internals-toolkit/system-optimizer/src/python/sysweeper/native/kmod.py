"""Linux 内核 **module(s) / firmware / plugin(s)** 只读层。

用户诉求是「引入、参考、模仿、进阶、超越 linux 的 kernel 源码的 module(s)、
firmware、plugin(s)」。这里的做法很明确：**不把内核源码搬进来，而是按内核源码
自己的组织方式，把「模块 / 固件 / 可插拔机制」这套体系映射成只读体检与优化
指引**。理由与本仓库一贯原则一致：

- 内核模块是 **root 权限的加载/卸载/写参数**操作，属于全系统最高危动作之一。
  本工具**只读不写**：不 insmod / rmmod / modprobe、不改 `/etc/modprobe.d`、
  不 `echo` 任何 `/sys/module/*/parameters/*`。只把内核已经暴露的
  `/proc`、`/sys` 事实读出来，指出问题与可执行的官方建议命令。
- firmware 绝不替换：只统计 `/lib/firmware` 的体积/年代/缺失项。
- 「plugin(s)」在 Linux 世界的对应物有三层，本模块各给一个只读视图：
  1. **loadable module** —— `/proc/modules`、`/sys/module`、`lsmod`、`modinfo`；
  2. **firmware blob** —— `/lib/firmware`（内核通过 request_firmware 加载的
     硬件微码/驱动固件）；
  3. **eBPF** —— 事实上是现代 Linux 的「内核级可编程插件」：
     `/sys/kernel/debug/tracing/available_filter_functions`、`bpftool prog`、
     `/sys/fs/bpf`（pin 目录）、`/proc/sys/kernel/unprivileged_bpf_disabled`。

对应 kernel.org Documentation 的位置（本模块每条报告都注明）：

- `Documentation/admin-guide/modules.rst`（可加载内核模块）
- `Documentation/admin-guide/quick-kparams.rst`（模块参数）
- `Documentation/driver-api/firmware/`（request_firmware 固件框架）
- `Documentation/bpf/`（eBPF 与 BPF 工具链）
- `Documentation/admin-guide/sysctl/kernel.rst`（`/proc/sys/kernel` 开关）
- `Documentation/trace/`（ftrace / tracefs）

**全部只读**。凡是需要 root 且会改变系统状态的命令（insmod/rmmod/modprobe -r/
`echo` 写 parameters），一律以「指引文本」形式给出，交由用户自行判断执行。
"""

from __future__ import annotations

import os
import re
import shutil
from typing import Dict, List, Tuple

from . import common

# --------------------------------------------------------------------------- #
# 文档层：内核 module / firmware / eBPF 专题（对齐 kernel.org Documentation）
# --------------------------------------------------------------------------- #

KMOD_DOCS: Dict[str, dict] = {
    "modules": {
        "name": "可加载内核模块（Loadable Kernel Modules）",
        "path": "Documentation/admin-guide/modules.rst",
        "subsystem": "kernel/module",
        "group": "module",
        "interfaces": [
            "/proc/modules（已加载模块：名/大小/引用计数/状态）",
            "/sys/module/<name>/（每模块一个目录：parameters/ refcnt/ initstate/ sections/）",
            "lsmod（libkmod 对 /proc/modules 的格式化视图，只读）",
            "modinfo -F <field> <mod>（读 .modinfo 元数据：license/depends/vermagic/alias）",
        ],
        "summary": ("模块的装载由 userspace（modprobe/libkmod）发起、经 finit_module "
                    "系统调用进入内核的 __finit_module/sys_init_module，最终由 load_module() "
                    "完成符号解析与重定位。/sys/module 下同时存在内建模块与已加载模块，"
                    "内建模块的 initstate 为 builtin。"),
        "advice": ("排查顺序：/proc/modules 看谁占着（refcnt 高 = 被大量引用，"
                   "rmmod 会失败）→ /sys/module/<n>/parameters 看可调参数（**只读**）→ "
                   "modinfo 看依赖与 vermagic 是否与当前内核匹配。"
                   "**卸载模块是 root 级高危操作，本工具只给指引不执行。**"),
    },
    "module_params": {
        "name": "模块参数（kernel parameters / sysfs）",
        "path": "Documentation/admin-guide/quick-kparams.rst",
        "subsystem": "kernel/module + kparam",
        "group": "module",
        "interfaces": [
            "/sys/module/<name>/parameters/<param>（读为当前值，写即改行为——本工具只读）",
            "/proc/cmdline（内核命令行参数，很多参数在此固化）",
            "modinfo -p <mod>（列出该模块支持的参数及默认值）",
        ],
        "summary": ("模块参数以 kparam 结构注册，多数会同步导出到 /sys/module/*/parameters/。"
                    "写这个 sysfs 节点等于运行期改内核行为（如 THP/swap 类的 "
                    "rmem_max、nr_cpus 参数），属高危写操作。"),
        "advice": ("本工具**只读**这些节点并在报告里标注哪些参数「可安全调 / 敏感」。"
                   "调参前务必看 Documentation 对应条目确认语义与取值范围。"),
    },
    "firmware": {
        "name": "固件加载框架（request_firmware）",
        "path": "Documentation/driver-api/firmware/",
        "subsystem": "drivers/base + firmware_class",
        "group": "firmware",
        "interfaces": [
            "/lib/firmware（多数发行版的主固件目录；也可为 /usr/lib/firmware）",
            "/sys/class/firmware/（内核 firmware_class 导出的 class 设备）",
            "/sys/bus/platform/devices/*/firmware/（各设备实际加载到的固件版本）",
            "modinfo -F firmware <mod>（该模块声明需要哪些固件文件）",
        ],
        "summary": ("驱动通过 request_firmware() 请求固件，内核在 firmware_class 的"
                    "搜索路径里找同名文件并缓存。缺固件往往表现为设备功能缺失而非报错，"
                    "排查「网卡/显卡/打印机不工作」第一件事就是看对应固件在不在。"),
        "advice": ("本工具只统计固件库体积、顶层分类与文件数，**绝不替换或删除固件**——"
                   "缺/错固件会导致硬件直接不可用。缺失项给 `modinfo -F firmware` "
                   "自查命令即可，不要从非官方渠道下固件。"),
    },
    "bpf": {
        "name": "eBPF（内核级可编程「插件」机制）",
        "path": "Documentation/bpf/",
        "subsystem": "kernel/bpf",
        "group": "bpf",
        "interfaces": [
            "/sys/kernel/debug/tracing/available_filter_functions（当前内核可挂 kprobe 的函数）",
            "/sys/fs/bpf（bpffs 挂载点：BPF 对象的 pin 目录，libbpf 在此持久化）",
            "bpftool prog|map|net show（列出已加载的 BPF 程序/映射/网络挂载，只读）",
            "/proc/sys/kernel/unprivileged_bpf_disabled（非特权 BPF 开关）",
            "/sys/kernel/btf/vmlinux（内核 BTF，供 CO-RE/BPF CO 一次编译到处运行用）",
        ],
        "summary": ("eBPF 是现代 Linux 的可编程扩展底座：经 verifier 校验的内联程序"
                    "挂在 kernel hook 上，性能接近原生。它是今天事实上的「内核插件」——"
                    "Cilium、bpftrace、systemd 的 BPF 单元、多数可观测性 agent 都建在它上面。"
                    "BPF CO（Compile Once, Run Everywhere）靠 BTF 做重定位，"
                    "让同一个 .o 跨内核版本可用。"),
        "advice": ("BPF 程序的加载需 CAP_BPF/CAP_SYS_ADMIN（5.8+ 已细分权限），"
                   "属特权操作——本工具**只读**列出现有程序与开关状态，不 attach、不 load。"
                   "`unprivileged_bpf_disabled=1` 是较安全的默认值。"),
    },
    "trace": {
        "name": "ftrace / tracefs（内核追踪设施）",
        "path": "Documentation/trace/",
        "subsystem": "kernel/trace",
        "group": "module",
        "interfaces": [
            "/sys/kernel/debug/tracing/（tracefs 挂载点，需 debugfs 已挂）",
            "/sys/kernel/tracing/（较新内核的 tracefs 路径）",
            "/proc/sys/kernel/ftrace_*（各 tracer 开关）",
        ],
        "summary": ("ftrace 是内核自带追踪器（function tracer + kprobe/uprobe + tracepoint），"
                    "是 bpftrace、perf 等一切内核级观测工具的底座。"),
        "advice": ("tracefs 多为只读用途可安全挂载查看；但写 events/*/enable 会真的挂钩内核，"
                   "高开销，属诊断期短时操作，本工具不写。"),
    },
    "module_blacklist": {
        "name": "模块黑名单 / modprobe 策略",
        "path": "Documentation/admin-guide/quick-kparams.rst",
        "subsystem": "kernel/module + udev/modprobe",
        "group": "module",
        "interfaces": [
            "/etc/modprobe.d/*.conf（install/alias/blacklist 指令）",
            "/proc/cmdline 的 blacklist= 参数",
            "/sys/module/<name>/taints（模块是否被 tainted，见内核 taint 文档）",
        ],
        "summary": ("黑名单通过 modprobe 的 install/remove hook 实现，"
                    "本质是「包一层 udev 规则拒绝加载」，不是内核级禁止。"),
        "advice": ("本工具**只读**列出黑名单条目供参考。批量黑名单第三方驱动（如某些"
                   "开源网卡驱动）省电效果因机型而异，改动前务必保留可回滚的配置备份。"),
    },
}


def kmod_reference(key: str) -> dict:
    """返回某内核 module/firmware/bpf 主题的文档参考。"""
    return KMOD_DOCS.get(key, {})


def kmod_reference_all() -> dict:
    """返回全部 module/firmware/bpf 文档参考。"""
    return KMOD_DOCS


def kmod_reference_grouped() -> Dict[str, dict]:
    """按 group（module/firmware/bpf）分组返回文档参考。"""
    out: Dict[str, dict] = {}
    for k, v in KMOD_DOCS.items():
        out.setdefault(v.get("group", "module"), {})[k] = v
    return out


def kmod_doc_list(group: str = None) -> List[str]:
    """返回 module/firmware/bpf 文档清单（纯文本行），可按 group 过滤。"""
    out: List[str] = []
    for key, ref in KMOD_DOCS.items():
        if group and ref.get("group") != group:
            continue
        path = ref.get("path", "")
        out.append(f"   · [{ref.get('group','?'):<8}] {ref.get('name', key)}  "
                   f"[kernel.org/.../{path}]({path})")
        if ref.get("summary"):
            out.append(f"       {ref['summary']}")
    return out


def _is_linux() -> bool:
    """当前是否 Linux（/proc/self 存在且 sysname 可判定）。"""
    return os.path.isdir("/proc") and os.path.isdir("/sys") and os.name == "posix"


def _read(path: str) -> str:
    """读文件并 strip；不存在/不可读返回空串。"""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except OSError:
        return ""


def _off_linux(what: str) -> Tuple[bool, str]:
    """非 Linux 时的统一降级出口。"""
    return False, (f"当前非 Linux 或内核接口未挂载（/proc、/sys），"
                   f"无法探测{what}（降级为文档指引）")


# --------------------------------------------------------------------------- #
# 1) 已加载模块（参考 admin-guide/modules.rst）
# --------------------------------------------------------------------------- #

def loaded_modules_report() -> tuple:
    """读 /proc/modules：已加载可加载模块清单（只读）。

    字段：模块名 / 内存占用 / 引用计数 / 依赖者个数 / 状态（Live/Loading/O）。
    refcnt 非 0 表示仍被别的模块或用户态持有——这类模块**卸载不了**，
    是「rmmod 报模块在用」的根本原因。
    """
    if not _is_linux():
        return _off_linux("已加载模块")
    txt = _read("/proc/modules")
    if not txt:
        return False, ("/proc/modules 为空或不可读（容器/精简内核可能未挂载，"
                       "或模块全部编译为内建 builtin）")
    rows = []
    total_size = 0
    for line in txt.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        name, size, refcnt = parts[0], parts[1], parts[2]
        dep = parts[3] if parts[3] != "-" else "0"
        state = parts[4] if len(parts) > 4 else "?"
        try:
            total_size += int(size)
        except ValueError:
            pass
        rows.append((name, size, refcnt, dep, state))
    if not rows:
        return False, "未从 /proc/modules 解析出任何模块（可能全部为内建模块）"
    live = [r for r in rows if r[4] == "Live"]
    held = [r for r in rows if r[2] not in ("0",)]
    lines = [f"已加载可加载模块（/proc/modules，只读）：共 {len(rows)} 个"
             f"（Live {len(live)} 个）"]
    lines.append(f"   模块内存合计约 {common.human(total_size)}"
                 f"（含各模块代码段，不含已释放部分）")
    if held:
        held.sort(key=lambda r: -int(r[2] or 0))
        lines.append(f"   引用计数非 0 的模块 {len(held)} 个（= 卸载不掉的模块，"
                     "卸载时会被占用）：")
        for name, size, refcnt, dep, state in held[:10]:
            lines.append(f"     · {name:<28} refcnt={refcnt:<5} size={size:>9}")
    else:
        lines.append("   引用计数全为 0：所有已加载模块理论上可卸载"
                     "（**仍不建议卸载内核关键模块**）")
    lines.append("   · 内建模块（builtin）不出现在 /proc/modules，"
                 "它们在 /sys/module 下且 initstate=builtin")
    return True, "\n".join(lines)


def sys_module_report() -> tuple:
    """读 /sys/module：全部模块目录（含内建），统计 builtin vs 可加载（只读）。"""
    if not _is_linux():
        return _off_linux("模块 sysfs 目录")
    base = "/sys/module"
    if not os.path.isdir(base):
        return _off_linux("模块 sysfs 目录")
    try:
        names = sorted(os.listdir(base))
    except OSError as e:
        return False, f"/sys/module 不可读: {e}"
    if not names:
        return False, "/sys/module 下无任何模块目录（内核未导出 sysfs）"
    builtin = []
    loadable = []
    with_params = []
    for n in names:
        st = _read(os.path.join(base, n, "initstate"))
        if st == "builtin":
            builtin.append(n)
        else:
            loadable.append(n)
        if os.path.isdir(os.path.join(base, n, "parameters")):
            with_params.append(n)
    lines = [f"模块 sysfs 全景（/sys/module，只读）：共 {len(names)} 个模块目录"]
    lines.append(f"   · 内建 builtin: {len(builtin)} 个（编译进内核，无 /proc 条目）")
    lines.append(f"   · 可加载 live  : {len(loadable)} 个（与 /proc/modules 对应）")
    lines.append(f"   · 暴露了 parameters/ 的模块: {len(with_params)} 个"
                 f"（这些是**可调内核行为**的入口，只读不改）")
    # 统计暴露参数总数
    ptotal = 0
    for n in with_params:
        try:
            ptotal += len(os.listdir(os.path.join(base, n, "parameters")))
        except OSError:
            pass
    lines.append(f"   · 可读参数节点合计约 {ptotal} 个"
                 f"（改这些等于运行期改内核行为——**高危，本工具绝不写**）")
    if loadable:
        lines.append(f"   · 可加载模块名样例: {', '.join(loadable[:8])}"
                     f"{' …' if len(loadable) > 8 else ''}")
    return True, "\n".join(lines)


def module_params_report() -> tuple:
    """读一批关键模块的可调参数当前值（**只读**；不写 sysfs）。

    只挑「读起来安全、语义明确」的常见内核/网络/存储模块参数列值，
    供判断「当前这台机器网络/内存/文件系统行为如何」。
    """
    base = "/sys/module"
    if not _is_linux():
        return _off_linux("模块参数")
    if not os.path.isdir(base):
        return _off_linux("模块参数（/sys/module 未挂载）")
    #: (模块, 参数, 中文说明)
    WATCH = (
        ("tcp_congestion", None, "拥塞控制算法当前值（net.ipv4.tcp_congestion_control 的模块侧）"),
        ("drm", "i915_enable_guc", "iGPU GuC（微码）调度开关，涉及省电/唤醒"),
        ("intel_powerclamp", "unstable_power", "Intel 降频封顶（powerclamp）参数"),
        ("ipv6", "disable_ipv6", "内核侧 IPv6 模块开关（模块内禁用，优先用 sysctl）"),
        ("nf_conntrack", "ac", "conntrack 记账开关（关掉丢 NAT/状态，勿动）"),
        ("scsi_mod", "use_blk_mq", "SCSI 块队列切换标志"),
        ("r8189", "ascension_timeout", "部分 RTL 驱动参数的典型样例（不存在即跳过）"),
    )
    lines = ["关键模块参数当前值（**只读**，写这些 sysfs 节点=运行期改内核，高危）："]
    hit = 0
    for mod, param, desc in WATCH:
        if param is None:
            v = _read("/proc/sys/net/ipv4/tcp_congestion_control")
            if v:
                hit += 1
                lines.append(f"   · {desc}: {v}")
            continue
        p = os.path.join(base, mod, "parameters", param)
        v = _read(p)
        if v:
            hit += 1
            lines.append(f"   · {mod}/{param} = {v}  # {desc}")
    if hit == 0:
        lines.append("   · 未读到上述任何关键模块参数（多为容器环境或该内核未编译对应模块）")
    lines.append("   · 完整参数清单用只读命令：ls /sys/module/*/parameters/")
    lines.append("   · 调参前先看 kernel.org 对应 Documentation 确认语义与取值域")
    return True, "\n".join(lines)


def modinfo_report() -> tuple:
    """modinfo 只读元数据：若本机有 modinfo/lsmod，列出版本与许可证概况。"""
    if not _is_linux():
        return _off_linux("modinfo")
    if not shutil.which("modinfo"):
        return False, ("未找到 modinfo（kmod 工具包未安装；"
                       "部分精简发行版不带 libkmod——降级为文档指引）")
    # 只读列出已加载模块的 license 字段汇总，不 dump 每个模块全文
    rc, out = common.run("for m in $(awk '{print $1}' /proc/modules 2>/dev/null | head -40); "
                         "do modinfo -F license \"$m\" 2>/dev/null; done | "
                         "sort | uniq -c | sort -rn", timeout=180)
    if rc != 0 or not (out or "").strip():
        return False, "modinfo 批量查询无输出（模块文件可能已被替换/不可读）"
    lines = ["模块许可证分布（modinfo -F license，只读，限前 40 个已加载模块）："]
    for l in out.splitlines():
        if l.strip():
            lines.append("   " + l.strip())
    lines.append("   · 许可证只影响模块能否随内核分发（taint），不影响本机功能")
    lines.append("   · 查单个模块：`modinfo <name>`；查固件需求：`modinfo -F firmware <name>`")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 2) 固件（firmware）：只统计，不替换
# --------------------------------------------------------------------------- #

#: 常见固件库搜索路径（按优先级）
_FW_DIRS = ("/lib/firmware", "/usr/lib/firmware", "/usr/local/lib/firmware")


def firmware_dirs() -> List[str]:
    """返回本机实际存在的固件目录列表。"""
    return [d for d in _FW_DIRS if os.path.isdir(d)]


def firmware_report() -> tuple:
    """统计 /lib/firmware 固件库（**只读**，绝不替换/删除固件）。"""
    if not _is_linux():
        return _off_linux("固件库统计")
    dirs = firmware_dirs()
    if not dirs:
        return False, ("未发现固件库目录（/lib/firmware、/usr/lib/firmware 均不存在）——"
                       "常见于容器/精简系统；或固件随驱动另行分发（降级为文档指引）")
    lines = ["内核固件库（firmware，只读统计；**绝不替换固件**）："]
    for d in dirs:
        size = common.list_dir_size(d)
        try:
            top = sorted(os.listdir(d))
        except OSError:
            top = []
        nfiles = 0
        for root, _dirs, files in os.walk(d):
            nfiles += len(files)
        lines.append(f"   · {d}：顶层 {len(top)} 类，文件约 {nfiles} 个，"
                     f"体积 {common.human(size) if size else '无法读取'}")
        if top:
            lines.append(f"       顶层分类样例: {', '.join(top[:10])}"
                         f"{' …' if len(top) > 10 else ''}")
    lines.append("   · 固件缺失的表现是「设备功能静默失效」（不报错、不崩），"
                 "排查网卡/显卡/打印机/无线不工作时先看这里")
    lines.append("   · 只读自查某模块需要哪些固件：`modinfo -F firmware <mod>`")
    return True, "\n".join(lines)


def firmware_class_report() -> tuple:
    """读 /sys/class/firmware 与设备实际加载的固件版本（只读）。"""
    if not _is_linux():
        return _off_linux("firmware_class 设备")
    base = "/sys/class/firmware"
    if not os.path.isdir(base):
        return False, ("/sys/class/firmware 不存在（该内核未启用 firmware_class，"
                       "或未挂载对应 sysfs——降级为文档指引）")
    try:
        items = sorted(os.listdir(base))
    except OSError as e:
        return False, f"/sys/class/firmware 不可读: {e}"
    if not items:
        return True, ("/sys/class/firmware 下暂无设备（当前无设备在走 request_firmware 流程，"
                      "常见于纯 CPU 计算节点）")
    lines = [f"firmware_class 设备（/sys/class/firmware，只读）：共 {len(items)} 个"]
    for n in items[:12]:
        p = os.path.join(base, n, "device", "firmware")
        v = _read(p)
        lines.append(f"   · {n}" + (f" → 已加载固件标识 {v}" if v else "（无版本标识）"))
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 3) eBPF —— 现代 Linux 事实上的「内核级可编程插件」
# --------------------------------------------------------------------------- #

def bpf_capability_report() -> tuple:
    """读 eBPF 能力（BTF / bpffs / 非特权开关 / kprobe 可挂函数数），**只读**。

    这是「现代 Linux 有什么可编程插件位」的体检视图：
    - 有 BTF → 意味着可用 BPF CO（Compile Once, Run Everywhere）；
    - 非特权 BPF 是否被禁 → 决定安全性基线。
    """
    if not _is_linux():
        return _off_linux("eBPF 能力")
    lines = ["eBPF 能力体检（**只读**，不 attach、不 load）："]
    btf = _read("/sys/kernel/btf/vmlinux")
    lines.append(f"   · 内核 BTF: {'可用 ' + common.human(os.path.getsize('/sys/kernel/btf/vmlinux')) if btf else '不可用（内核未开 CONFIG_DEBUG_INFO_BTF）'}")
    if btf:
        lines.append("       有 BTF → BPF CO 可用：同一份 .o 能跨内核版本加载（libbpf 重定位）")
    dis = _read("/proc/sys/kernel/unprivileged_bpf_disabled")
    if dis:
        val = "1（已禁用非特权 BPF——较安全的基线）" if dis == "1" else "0（允许非特权 BPF）"
        lines.append(f"   · unprivileged_bpf_disabled = {dis}  → {val}")
    bpf_fsys = "/sys/fs/bpf"
    if os.path.isdir(bpf_fsys):
        try:
            pinned = os.listdir(bpf_fsys)
        except OSError:
            pinned = []
        lines.append(f"   · bpffs 已挂载于 {bpf_fsys}，pin 目录 {len(pinned)} 项"
                     f"（pin 是 BPF 对象持久化，libbpf 靠它跨进程复用）")
    else:
        lines.append(f"   · bpffs 未挂载于 {bpf_fsys}（BPF 对象无法 pin，重启即失效）")
    # tracefs 上的可挂 kprobe 函数数
    for tf in ("/sys/kernel/debug/tracing", "/sys/kernel/tracing"):
        af = os.path.join(tf, "available_filter_functions")
        if os.path.isfile(af):
            n = sum(1 for l in _read(af).splitlines() if l.strip())
            lines.append(f"   · {tf}：可挂 kprobe 的函数约 {n} 个"
                         "（bpftrace/perf 的挂钩面；挂载即监控，勿常驻高开销探针）")
            break
    else:
        lines.append("   · tracefs 未挂载（需 debugfs/tracefs；可用 kprobe 面无法统计）")
    if shutil.which("bpftool"):
        rc, out = common.run("bpftool prog show 2>&1 | head -20", timeout=90)
        lines.append("   bpftool prog show（只读）:")
        if rc == 0 and (out or "").strip():
            for l in out.splitlines()[:20]:
                if l.strip():
                    lines.append("     " + l.rstrip()[:130])
        else:
            lines.append("     无输出（未加载 BPF 程序，或需更高权限）")
    else:
        lines.append("   · bpftool 未安装（通常随 kernel-tools/bpftool 包提供）")
    lines.append("   · 本工具只读现有状态；attach / load BPF 需 CAP_BPF，"
                 "属特权操作，仅给指引不做")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 4) 模块相关 sysctl 与加载策略（只读）
# --------------------------------------------------------------------------- #

def module_sysctl_report() -> tuple:
    """读 /proc/sys/kernel 下与模块/加载/taint 相关的开关（只读）。"""
    if not _is_linux():
        return _off_linux("内核 sysctl")
    base = "/proc/sys/kernel"
    if not os.path.isdir(base):
        return _off_linux("内核 sysctl")
    keys = ("tainted", "taint", "modules_disabled", "taint_fatal",
            "unprivileged_bpf_disabled", "kptr_restrict",
            "dmesg_restrict", "perf_event_paranoid", "sched_rt_runtime_us")
    lines = ["内核模块/加载相关 sysctl（/proc/sys/kernel，只读）："]
    hit = 0
    for k in keys:
        v = _read(os.path.join(base, k))
        if v:
            hit += 1
            note = ""
            if k == "tainted":
                note = "（非空表示内核被标记 tainted：加载过专有/违规模块等）"
            elif k == "modules_disabled":
                note = "（=1 表示已禁止再加载新模块；2 为强制卸载中）"
            elif k == "unprivileged_bpf_disabled":
                note = "（=1 为较安全的非特权 BPF 基线）"
            elif k == "kptr_restrict":
                note = "（限制 /proc 中内核地址暴露，=1 较安全）"
            lines.append(f"   · {k} = {v}{note}")
    if hit == 0:
        lines.append("   · 未读到相关 sysctl 键（容器或受限内核可能未暴露）")
    return True, "\n".join(lines)


def blacklist_report() -> tuple:
    """读 modprobe 黑名单配置（**只读**；绝不写 /etc/modprobe.d）。"""
    if not _is_linux():
        return _off_linux("modprobe 黑名单")
    found = []
    conf_dir = "/etc/modprobe.d"
    if os.path.isdir(conf_dir):
        for n in sorted(os.listdir(conf_dir)):
            if not n.endswith((".conf", ".cfg")):
                continue
            p = os.path.join(conf_dir, n)
            for i, line in enumerate(_read(p).splitlines(), 1):
                s = line.strip()
                if s.startswith(("blacklist", "install ", "remove ")):
                    found.append(f"{p}:{i}: {s[:100]}")
    cmdline = _read("/proc/cmdline")
    if "blacklist=" in cmdline:
        for tok in cmdline.split():
            if tok.startswith("blacklist="):
                found.append(f"/proc/cmdline: {tok}")
    if not found:
        return False, ("未发现任何 modprobe 黑名单配置（/etc/modprobe.d 无 blacklist/"
                       "指令、内核命令行也无 blacklist=；属正常，未做限制）")
    lines = [f"modprobe 黑名单 / 加载策略（只读，共 {len(found)} 条）："]
    for f in found[:20]:
        lines.append("   · " + f)
    if len(found) > 20:
        lines.append(f"   … 另有 {len(found) - 20} 条")
    lines.append("   · 黑名单本质是 modprobe 侧的 udev hook 拒绝加载，不是内核硬禁止")
    lines.append("   · 本工具只读列出；新增/移除黑名单是 root 级改动，**仅给指引不写**")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 5) 电源/温控（与模块固件配套的整机状态，只读）
# --------------------------------------------------------------------------- #

def power_state_report() -> tuple:
    """读 /sys/power 电源状态（只读；写 suspend 是 root 危险操作，不做）。"""
    if not _is_linux():
        return _off_linux("电源状态")
    base = "/sys/power"
    if not os.path.isdir(base):
        return _off_linux("电源状态")
    lines = ["电源状态（/sys/power，只读）："]
    mem = _read(os.path.join(base, "mem_sleep"))
    if mem:
        lines.append(f"   · mem_sleep: {mem}"
                     "（auto=由系统选 suspend/hibernate；deep=进 hibernate）")
    st = _read(os.path.join(base, "state"))
    if st:
        lines.append(f"   · 可用睡眠态: {st}")
    cur = _read("/proc/power/sleep_count")
    lines.append(f"   · sleep_count: {cur or '未知'}（本机历史休眠次数）")
    lines.append("   · 写 /sys/power/state（echo mem > …）会让机器真的睡下去，"
                 "属危险 root 操作，本工具绝不执行")
    return True, "\n".join(lines)


def thermal_report() -> tuple:
    """读 /sys/class/thermal 温区（只读）。"""
    if not _is_linux():
        return _off_linux("温控区")
    base = "/sys/class/thermal"
    if not os.path.isdir(base):
        return _off_linux("温控区（该内核未导出 thermal class）")
    zones = []
    for n in sorted(os.listdir(base)):
        if not n.startswith("thermal_zone"):
            continue
        typ = _read(os.path.join(base, n, "type")) or "?"
        try:
            temp = int(_read(os.path.join(base, n, "temp"))) / 1000.0
        except (ValueError, OSError):
            temp = None
        zones.append((n, typ, temp))
    if not zones:
        return False, "/sys/class/thermal 下没有温区（可能被 cgroup/虚拟机屏蔽）"
    lines = ["温区（/sys/class/thermal，只读）："]
    for n, typ, temp in zones:
        t = f"{temp:.1f}°C" if temp is not None else "读不到"
        lines.append(f"   · {n:<18} {typ:<22} {t}")
    lines.append("   · 温区是内核 thermal framework 导出的只读视图；"
                 "写 trip_point 才算调策略（root 级），本工具不写")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 聚合入口
# --------------------------------------------------------------------------- #

#: 只读探针清单：(函数名, 中文标签)
KMOD_PROBES = (
    ("loaded_modules_report", "已加载可加载模块（/proc/modules）"),
    ("sys_module_report", "模块 sysfs 全景（/sys/module，builtin vs live）"),
    ("module_params_report", "关键模块参数当前值（只读 sysfs）"),
    ("modinfo_report", "模块元数据与许可证分布（modinfo -F license）"),
    ("firmware_report", "内核固件库统计（/lib/firmware，绝不替换）"),
    ("firmware_class_report", "firmware_class 已加载固件（/sys/class/firmware）"),
    ("bpf_capability_report", "eBPF 能力（BTF/bpffs/非特权开关/kprobe 面）"),
    ("module_sysctl_report", "模块相关 sysctl（taint/modules_disabled 等）"),
    ("blacklist_report", "modprobe 黑名单 / 加载策略（只读）"),
    ("power_state_report", "电源状态（/sys/power，只读）"),
    ("thermal_report", "温区（/sys/class/thermal，只读）"),
)


def kmod_report() -> tuple:
    """Linux module/firmware/eBPF 体检总报告：逐项只读。"""
    if not _is_linux():
        return _off_linux("内核 module/firmware/eBPF（当前非 Linux 平台）")
    head = ["Linux 内核 module/firmware/eBPF 只读体检总报告："]
    okc = 0
    for fn_name, label in KMOD_PROBES:
        ok, msg = globals()[fn_name]()
        head.append("")
        head.append(f"-- {label} --")
        head.append(msg if ok else f"（不适用）{msg}")
        if ok:
            okc += 1
    head.append("")
    head.append(f"小结：{len(KMOD_PROBES)} 项只读体检中 {okc} 项可读。"
                "全部动作只读：**不 insmod/rmmod/modprobe、不写 /sys/module/*/parameters/**、"
                "不替换固件、不 attach/load eBPF 程序。")
    return True, "\n".join(head)


def environment_report() -> List[str]:
    """返回本机 module/firmware/eBPF 接口可用性概览（✓/✗）。"""
    lines = ["Linux 内核 module/firmware/eBPF 只读接口可用性："]
    for fn_name, label in KMOD_PROBES:
        ok, msg = globals()[fn_name]()
        lines.append(f"   {'✓' if ok else '✗'} {label}")
        if not ok:
            lines.append(f"       {msg}")
    return lines


#: 明确**不执行**的高危命令（文档化禁令，防止后续误加）
FORBIDDEN_COMMANDS = (
    "insmod / rmmod / modprobe -r   # root 级装卸内核模块，卸载错=不可开机",
    "echo ... > /sys/module/*/parameters/*  # 运行期改内核行为（写 sysfs）",
    "modprobe -b / blacklist 改写     # 改 /etc/modprobe.d 影响后续所有开机加载",
    "dpkg -P / pacman -R <内核包>      # 卸载内核包会连带不可恢复的模块链",
    "替换 /lib/firmware 下任何文件      # 固件错配=硬件直接不可用",
    "bpftool prog load / map create   # 需 CAP_BPF，挂错程序可能拖垮内核路径",
    "echo deep > /sys/power/mem_sleep # 让机器进休眠/hibernate（数据风险）",
)


__all__ = [
    "KMOD_DOCS", "kmod_reference", "kmod_reference_all", "kmod_reference_grouped",
    "kmod_doc_list", "firmware_dirs",
    "loaded_modules_report", "sys_module_report", "module_params_report",
    "modinfo_report", "firmware_report", "firmware_class_report",
    "bpf_capability_report", "module_sysctl_report", "blacklist_report",
    "power_state_report", "thermal_report",
    "kmod_report", "environment_report",
    "KMOD_PROBES", "FORBIDDEN_COMMANDS", "_FW_DIRS",
]
