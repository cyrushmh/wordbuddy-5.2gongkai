"""硬件标准相关的原生接口层。

以「系统本身提供的接口」读取硬件信息，并对照硬件标准文档（data/hardware.json）
给出优化/维护建议。参考的标准：

- S.M.A.R.T. : T13 / ATA8-ACS（用 smartctl 读取磁盘健康）
- ACPI       : UEFI Forum（读 /sys/power/state 等内核接口）
- PCI/PCIe   : PCI-SIG（用 lspci -nn 读取类代码）
- USB        : USB-IF（用 lsusb 读取设备类）
- ATA TRIM  : T13（用 fstrim 维护 SSD）

所有调用惰性守卫：工具不存在 / 文件不存在就返回 None/空，由上层降级为「指引」。
"""

from __future__ import annotations

import json
import os
import shutil

from . import common


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath("hardware.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:
        return {}


REFS = _load_refs()


def reference(standard_id: str) -> dict:
    """返回某硬件标准的参考信息（name/standard/org/summary/...）。"""
    return REFS.get(standard_id, {})


def reference_all() -> dict:
    """返回全部硬件标准参考（供 hardware 命令列出）。"""
    return REFS


def smart_health(dev: str = "/dev/sda") -> tuple:
    """读 S.M.A.R.T. 健康状态（参考 T13/ATA8-ACS）。返回 (ok, msg)。"""
    if not shutil.which("smartctl"):
        return False, "未安装 smartctl（smartmontools）；无法读取 S.M.A.R.T.（需安装后才有此能力）"
    if not os.path.exists(dev):
        # 尝试自动挑第一个块设备
        dev = _first_block_dev() or ""
    if not dev:
        return False, "未找到可用块设备"
    rc, out = common.run(f"smartctl -H {dev} 2>/dev/null")
    if rc != 0:
        return False, out or f"smartctl 读取 {dev} 失败"
    return True, out.strip()[-500:]


def _first_block_dev() -> str:
    for d in ("sda", "nvme0n1", "hda", "vda"):
        if os.path.exists(f"/dev/{d}"):
            return f"/dev/{d}"
    return ""


def acpi_states() -> str:
    """读内核支持的 ACPI 睡眠态（参考 ACPI 规范 /sys/power/state）。"""
    p = "/sys/power/state"
    if not os.path.exists(p):
        return ""
    try:
        with open(p, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def disk_trim(path: str = "/") -> tuple:
    """对挂载点执行 fstrim（参考 ATA TRIM）。返回 (ok, msg)。"""
    if not shutil.which("fstrim"):
        return False, "未安装 fstrim（util-linux）；无法 TRIM（需安装后才有此能力）"
    rc, out = common.run(f"fstrim -v {path} 2>&1 | tail -2")
    return rc == 0, out


def pci_devices() -> list:
    """用 lspci -nn 列出 PCI/PCIe 设备（参考 PCI-SIG 类代码）。"""
    if not shutil.which("lspci"):
        return []
    rc, out = common.run("lspci -nn 2>/dev/null")
    return out.splitlines() if rc == 0 and out else []


def usb_devices() -> list:
    """用 lsusb 列出 USB 设备（参考 USB-IF 设备类）。"""
    if not shutil.which("lsusb"):
        return []
    rc, out = common.run("lsusb 2>/dev/null")
    return out.splitlines() if rc == 0 and out else []


def bus_report() -> tuple:
    """总线/接口枚举（/sys/bus/*，只读）：列出已注册总线与关键设备的驱动绑定。

    把「接口文档」落到可读的设备树：PCI/PCIe、USB、platform、i2c、spi、acpi 等
    总线在 sysfs 下都有 /sys/bus/<bus>/devices 与 /sys/bus/<bus>/drivers，本函数
    只读这些目录，给出「本机有哪些总线、各总线挂了多少设备、设备是否绑了驱动」。
    参照 PCI-SIG / USB-IF / kernel Documentation driver-model，全部只读。
    """
    bus_root = "/sys/bus"
    if not os.path.isdir(bus_root):
        return False, "未发现 /sys/bus（非 Linux 或 sysfs 未挂载），跳过总线枚举"
    lines = ["总线/接口枚举（/sys/bus/*，只读）："]
    try:
        buses = sorted(d for d in os.listdir(bus_root)
                       if os.path.isdir(os.path.join(bus_root, d)))
    except OSError:
        return False, "读取 /sys/bus 失败"
    if not buses:
        return False, "/sys/bus 为空（无已注册总线）"
    # 重点总线优先展示设备数
    focus = ("pci", "pci_express", "usb", "platform", "i2c", "spi", "acpi", "scsi")
    counts = {}
    for b in buses:
        devdir = os.path.join(bus_root, b, "devices")
        drvdir = os.path.join(bus_root, b, "drivers")
        try:
            ndev = len([x for x in os.listdir(devdir) if not x.startswith(".")])
        except OSError:
            ndev = 0
        try:
            ndrv = len([x for x in os.listdir(drvdir) if not x.startswith(".")])
        except OSError:
            ndrv = 0
        counts[b] = (ndev, ndrv)
    for b in buses:
        if b in focus or counts[b][0] > 0:
            lines.append(f"   · {b:<12} 设备 {counts[b][0]:<4} 驱动 {counts[b][1]}")
    hidden = [b for b in buses if b not in focus and counts[b][0] == 0]
    if hidden:
        lines.append(f"   · 其他已注册总线（无设备）：{', '.join(hidden)}")
    # PCI 设备驱动绑定抽样（接口文档落点）
    pci_dev = os.path.join(bus_root, "pci", "devices")
    if os.path.isdir(pci_dev):
        bound = 0
        sample = []
        try:
            for addr in sorted(os.listdir(pci_dev))[:40]:
                dpath = os.path.join(pci_dev, addr, "driver")
                if os.path.islink(dpath):
                    bound += 1
                    if len(sample) < 6:
                        sample.append(f"{addr}={os.path.basename(os.readlink(dpath))}")
        except OSError:
            pass
        lines.append(f"   · PCI 设备已绑驱动 {bound} 个；抽样：{', '.join(sample) if sample else '无'}")
    lines.append("   · 详情：lspci -nn / lsusb（PCI-SIG / USB-IF 类代码）；改驱动属写操作")
    return True, "\n".join(lines)


def cpu_info() -> dict:
    """尽量读取 CPU 信息（跨平台：sysctl / /proc/cpuinfo / platform）。"""
    import platform as _plat
    info = {"processor": _plat.processor() or "", "machine": _plat.machine() or ""}
    if sys_is_bsd_or_darwin():
        from . import macos
        model = macos.sysctl("hw.model")
        if model:
            info["model"] = model
        ncpu = macos.sysctl("hw.ncpu")
        if ncpu:
            info["cpus"] = ncpu
    elif os.path.exists("/proc/cpuinfo"):
        try:
            with open("/proc/cpuinfo", encoding="utf-8") as f:
                txt = f.read()
            m = _re_search(r"model name\s*:\s*(.+)", txt)
            if m:
                info["model"] = m
            info["cpus"] = str(txt.count("processor"))
        except OSError:
            pass
    return info


def sys_is_bsd_or_darwin() -> bool:
    import sys
    return sys.platform in ("darwin", "freebsd", "openbsd", "netbsd", "dragonfly")


def _re_search(pat: str, txt: str) -> str:
    import re
    m = re.search(pat, txt, re.M)
    return m.group(1).strip() if m else ""


# ---------------------------------------------------------------------------
# Linux kernel 源码文档（kernel.org/Documentation）引用表 + 硬件可调项原生探测
#
# 这些可调项在内核里由对应子系统文档化（见 data/hardware_kernel.json）：
#   CPUFreq/ cpuidle/intel_pstate  → admin-guide/pm/
#   thermal                         → admin-guide/thermal/
#   THP / zswap / NUMA / vm sysctl  → admin-guide/mm/ 与 sysctl/vm.rst
#   block / bfq / nvme              → block/ 与 nvme/
#   watchdog                        → watchdog/watchdog-api.rst
#   EAS                             → scheduler/sched-energy.rst
# 本层只「读取系统已暴露的接口」（/sys、/proc），不写、不调频；写操作由任务层
# 以 manual 指引告知用户，默认分析不修改。所有接口惰性守卫：文件/目录不存在即
# 返回 (False, 说明)，由上层降级为「指引」，绝不抛异常。
# ---------------------------------------------------------------------------

def _load_kernel_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "hardware_kernel.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:
        return {}


KERNEL_REFS = _load_kernel_refs()


def kernel_reference(key: str) -> dict:
    """返回某硬件子系统的内核文档参考（name/path/subsystem/interfaces/summary/advice）。"""
    return KERNEL_REFS.get(key, {})


def kernel_reference_all() -> dict:
    """返回全部硬件内核文档参考（供 hardware 命令列出）。"""
    return KERNEL_REFS


def kernel_doc_list() -> list:
    """返回内核文档引用清单（纯文本行），供 CLI/GUI 展示。"""
    out: list = []
    for key, ref in KERNEL_REFS.items():
        path = ref.get("path", "")
        out.append(f"   · {ref.get('name', key)}  "
                   f"[kernel.org/.../{path}]({path})")
    return out


def _read(path: str) -> str:
    """读单文件并 strip；不存在/不可读返回空串。"""
    if not os.path.exists(path):
        return ""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except OSError:
        return ""


def cpufreq_governor(policy: int = 0) -> tuple:
    """读 CPUFreq 当前 governor 与可用项（参考 admin-guide/pm/cpufreq.rst）。"""
    base = f"/sys/devices/system/cpu/cpufreq/policy{policy}"
    gov = _read(f"{base}/scaling_governor")
    avail = _read(f"{base}/scaling_available_governors")
    if not gov and not avail:
        # 回退：扫描是否存在任何 policy 目录
        if not os.path.isdir("/sys/devices/system/cpu/cpufreq"):
            return False, "当前非 Linux 或内核未暴露 CPUFreq 接口（/sys/.../cpufreq 不存在）"
        return False, "未读到 policy0 的 governor（接口存在但无数据）"
    cur = _read(f"{base}/scaling_cur_freq")
    lines = [f"governor: {gov or '(空)'}",
             f"可选: {avail or '(空)'}"]
    if cur:
        lines.append(f"当前频率(kHz): {cur}")
    return True, "\n".join(lines)


def cpuidle_report(cpu: int = 0) -> tuple:
    """读 cpuidle 空闲态（参考 admin-guide/pm/cpuidle.rst）。"""
    base = f"/sys/devices/system/cpu/cpu{cpu}/cpuidle"
    if not os.path.isdir(base):
        return False, "当前非 Linux 或内核未暴露 cpuidle 接口（/sys/.../cpu<N>/cpuidle 不存在）"
    states = []
    try:
        for name in sorted(os.listdir(base)):
            d = os.path.join(base, name)
            sname = _read(os.path.join(d, "name"))
            lat = _read(os.path.join(d, "latency"))
            if sname:
                states.append(f"{name}={sname} 唤醒延迟={lat or '?'}")
    except OSError:
        return False, "读取 cpuidle 失败"
    if not states:
        return False, "未读到任何 cpuidle 状态"
    return True, "空闲态(C-state):\n  " + "\n  ".join(states)


def intel_pstate_status() -> tuple:
    """读 intel_pstate 状态（参考 admin-guide/pm/intel_pstate.rst）。"""
    p = "/sys/devices/system/cpu/intel_pstate/status"
    s = _read(p)
    if not s:
        return False, "当前非 Intel P-State 平台（/sys/.../intel_pstate 不存在；"
    minp = _read("/sys/devices/system/cpu/intel_pstate/min_perf_pct")
    maxp = _read("/sys/devices/system/cpu/intel_pstate/max_perf_pct")
    lines = [f"intel_pstate/status: {s}"]
    if minp:
        lines.append(f"性能窗口: min={minp}% max={maxp or '?'}")
    return True, "\n".join(lines)


def thermal_report() -> tuple:
    """读热区温度与类型（参考 admin-guide/thermal/sysfs-api.rst）。"""
    base = "/sys/class/thermal"
    if not os.path.isdir(base):
        return False, "当前非 Linux 或内核未暴露 thermal 接口（/sys/class/thermal 不存在）"
    zones = []
    try:
        for name in sorted(os.listdir(base)):
            if not name.startswith("thermal_zone"):
                continue
            ttype = _read(os.path.join(base, name, "type"))
            temp = _read(os.path.join(base, name, "temp"))
            if temp and temp.isdigit():
                temp = f"{int(temp) / 1000:.1f}°C"
            zones.append(f"{name}({ttype or '?'}): {temp or '?'}")
    except OSError:
        return False, "读取 thermal_zone 失败"
    if not zones:
        return False, "未读到任何热区"
    return True, "热区:\n  " + "\n  ".join(zones)


def thp_enabled() -> tuple:
    """读透明大页状态（参考 admin-guide/mm/transhuge.rst）。"""
    p = "/sys/kernel/mm/transparent_hugepage/enabled"
    s = _read(p)
    if not s:
        return False, "当前非 Linux 或内核未暴露 transparent_hugepage 接口"
    # 内核以 [always] madvise never 形式标出当前生效项
    import re as _re
    active = _re.search(r"\[([^\]]+)\]", s)
    cur = active.group(1) if active else s.split()[0] if s.split() else "?"
    return True, f"transparent_hugepage: {cur}  (可用: {s})"


def zswap_enabled() -> tuple:
    """读 zswap 是否启用（参考 mm/zswap.rst）。"""
    p = "/sys/module/zswap/parameters/enabled"
    s = _read(p)
    if s == "":
        return False, "当前非 Linux 或内核未启用 zswap 模块（/sys/module/zswap 不存在）"
    pool = _read("/sys/module/zswap/parameters/max_pool_percent")
    return True, f"zswap: {'启用' if s == 'Y' or s == '1' else '禁用'}  max_pool={pool or '?'}"


def zram_report() -> tuple:
    """读 zram 设备（参考 admin-guide/blockdev/zram.rst）。"""
    base = "/sys/block"
    if not os.path.isdir(base):
        return False, "当前非 Linux（/sys/block 不存在）"
    devs = [d for d in os.listdir(base) if d.startswith("zram")]
    if not devs:
        return False, "未创建 zram 设备（/sys/block/zram* 不存在）"
    lines = []
    for d in sorted(devs):
        size = _read(os.path.join(base, d, "disksize"))
        lines.append(f"{d}: disksize={size or '?'} bytes")
    return True, "zram 设备:\n  " + "\n  ".join(lines)


def _root_block_dev() -> str:
    """尽力挑一个实体块设备（排除 loop/ram/dm/sr）。"""
    base = "/sys/block"
    if not os.path.isdir(base):
        return ""
    for d in sorted(os.listdir(base)):
        if d.startswith(("loop", "ram", "dm", "sr", "nbd")):
            continue
        return d
    return ""


def io_scheduler(dev: str = "") -> tuple:
    """读块设备队列调度器（参考 block/）。dev 为空时自动挑实体盘。"""
    dev = dev or _root_block_dev()
    if not dev:
        return False, "未找到实体块设备（/sys/block 不存在或无实体盘）"
    p = f"/sys/block/{dev}/queue/scheduler"
    s = _read(p)
    if not s:
        return False, f"/sys/block/{dev}/queue/scheduler 不存在（可能非 Linux 或不支持多队列）"
    import re as _re
    active = _re.search(r"\[([^\]]+)\]", s)
    cur = active.group(1) if active else s.split()[0] if s.split() else "?"
    return True, f"{dev} 调度器: {cur}  (可选: {s})"


def nvme_report() -> tuple:
    """读 NVMe 设备（参考 nvme/index.rst）。"""
    base = "/sys/class/nvme"
    if not os.path.isdir(base):
        return False, "未找到 NVMe 控制器（/sys/class/nvme 不存在）"
    devs = []
    try:
        for name in sorted(os.listdir(base)):
            if name.startswith("nvme"):
                model = _read(os.path.join(base, name, "model"))
                devs.append(f"{name}: {model or '?'}")
    except OSError:
        return False, "读取 NVMe 失败"
    if not devs:
        return False, "未找到 NVMe 设备"
    return True, "NVMe 控制器:\n  " + "\n  ".join(devs)


def epb_read(cpu: int = 0) -> tuple:
    """读 x86 能效偏好 energy_perf_bias（参考 intel_pstate.rst / x86 MSR）。"""
    p = f"/sys/devices/system/cpu/cpu{cpu}/power/energy_perf_bias"
    s = _read(p)
    if s == "":
        return False, "当前非 x86 或不支持 energy_perf_bias（/sys/.../cpu0/power/energy_perf_bias 不存在）"
    epb_map = {"0": "performance(性能优先)", "6": "balanced(平衡)",
               "15": "power(能效优先)"}
    return True, f"energy_perf_bias(cpu{cpu}): {s}  ({epb_map.get(s.strip(), '自定义')})"


def numa_balancing() -> tuple:
    """读 NUMA 自动平衡开关（参考 admin-guide/mm/numa_memory_policy.rst）。"""
    p = "/proc/sys/kernel/numa_balancing"
    s = _read(p)
    if s == "":
        return False, "当前非 Linux 或无 NUMA 平衡接口（/proc/sys/kernel/numa_balancing 不存在）"
    return True, f"numa_balancing: {'启用' if s == '1' else '禁用'} (值={s})"


def watchdog_report() -> tuple:
    """读硬件看门狗设备（参考 watchdog/watchdog-api.rst）。"""
    base = "/sys/class/watchdog"
    if not os.path.isdir(base):
        return False, "未暴露看门狗接口（/sys/class/watchdog 不存在）"
    devs = [d for d in os.listdir(base) if d.startswith("watchdog")] if os.path.isdir(base) else []
    if not devs:
        return False, "未找到看门狗设备"
    return True, "看门狗设备:\n  " + "\n  ".join(devs)


def vm_swappiness() -> tuple:
    """读 vm.swappiness（参考 admin-guide/sysctl/vm.rst）。"""
    p = "/proc/sys/vm/swappiness"
    s = _read(p)
    if s == "":
        return False, "当前非 Linux（/proc/sys/vm/swappiness 不存在）"
    return True, f"vm.swappiness: {s}（0=尽量不换页，100=激进换页）"


def eas_available() -> tuple:
    """读能耗感知调度开关（参考 scheduler/sched-energy.rst）。"""
    p = "/proc/sys/kernel/sched_energy_aware"
    s = _read(p)
    if s == "":
        return False, "当前非 Linux 或内核未启用 EAS（/proc/sys/kernel/sched_energy_aware 不存在）"
    return True, f"sched_energy_aware: {'启用' if s == '1' else '禁用'} (值={s})"


def _agg_norm(r):
    """归一化报告返回：tuple→(ok,msg)；list→(True,拼接)；其它→(True,str)。"""
    if isinstance(r, tuple):
        ok = bool(r[0]) if r else False
        msg = str(r[1]) if len(r) > 1 else ""
        return ok, msg
    if isinstance(r, list):
        return True, "\n".join(str(x) for x in r)
    return True, str(r)


def hardware_report() -> tuple:
    """硬件本征只读聚合：串联 bus/thermal/zram/nvme/watchdog/cpuidle 各探测。"""
    parts = []
    ok_any = False
    for fn in (bus_report, thermal_report, zram_report, nvme_report, watchdog_report, cpuidle_report):
        try:
            ok, msg = _agg_norm(fn())
        except Exception:  # noqa: BLE001
            continue
        ok_any = ok_any or ok
        if msg.strip():
            parts.append(msg.strip())
    if not parts:
        return False, "未读到任何硬件本征接口（非 Linux 或无对应 sysfs）"
    return ok_any, "\n".join(parts)
