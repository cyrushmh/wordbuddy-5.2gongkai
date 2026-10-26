"""Linux kernel 源码文档（kernel.org/Documentation）引用 + 软件/网络子系统只读探测。

本模块把「Linux 整体优化」的依据统一指向内核文档，覆盖三类子系统：

- 硬件（hardware）：CPUFreq/thermal/THP/zswap/NUMA/block…（见 data/hardware_kernel.json，
  与 native/hardware.py 同源；此处合并以便 `kernel` 命令一站式展示）。
- 软件（software）：scheduler(CFS)/cgroup-v2/oom/psi/THP-compaction/vm-sysctl。
- 网络（network）：TCP(ip-sysctl)/拥塞控制(BBR)/net.core/RPS-RFS。

所有探测只读核对系统已暴露的 /sys、/proc 接口，不写、不调优；工具/接口不存在即
返回 (False, 说明)，由上层降级为「指引」，绝不抛异常。
"""

from __future__ import annotations

import json
import os

from . import common


def _load(name: str) -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(name).read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:
        return {}


# 硬件内核文档（与 native/hardware.py 同一份，合并展示）
_HW = _load("hardware_kernel.json")
# 软件 + 网络内核文档
_SW_NET = _load("kernel_docs.json")

# 合并成统一引用表；并给硬件项打 group 标签便于分组
KERNEL_DOCS: dict = {}
for _k, _v in _SW_NET.items():
    KERNEL_DOCS[_k] = dict(_v)
for _k, _v in _HW.items():
    _e = dict(_v)
    _e.setdefault("group", "hardware")
    KERNEL_DOCS[_k] = _e


def kernel_doc(key: str) -> dict:
    """返回某内核子系统的文档参考（name/path/group/subsystem/interfaces/summary/advice）。"""
    return KERNEL_DOCS.get(key, {})


def kernel_doc_all() -> dict:
    """返回全部内核文档参考。"""
    return KERNEL_DOCS


def kernel_doc_grouped() -> dict:
    """按 group（hardware/software/network）分组返回内核文档参考。"""
    out: dict = {"hardware": {}, "software": {}, "network": {}}
    for k, v in KERNEL_DOCS.items():
        g = v.get("group", "hardware")
        out.setdefault(g, {})[k] = v
    return out


def kernel_doc_list(group: str = None) -> list:
    """返回内核文档引用清单（纯文本行），可按 group 过滤。"""
    out: list = []
    for key, ref in KERNEL_DOCS.items():
        if group and ref.get("group") != group:
            continue
        path = ref.get("path", "")
        out.append(f"   · [{ref.get('group','?')}] {ref.get('name', key)}  "
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


def _read_int(path: str) -> str:
    s = _read(path)
    return s


# ---------------------------------------------------------------------------
# 软件子系统（software）只读探测
# ---------------------------------------------------------------------------

def sched_report() -> tuple:
    """读 CFS 调度器关键 sysctl（参考 scheduler/sched-design-CFS.rst）。"""
    keys = ["sched_latency_ns", "sched_min_granularity_ns",
            "sched_migration_cost_ns", "sched_wakeup_granularity_ns"]
    base = "/proc/sys/kernel"
    if not os.path.isfile(f"{base}/sched_latency_ns"):
        return False, "当前非 Linux（/proc/sys/kernel/sched_latency_ns 不存在）"
    lines = [f"CFS sysctl（参考 sched-design-CFS.rst）:"]
    for k in keys:
        v = _read(f"{base}/{k}")
        if v:
            lines.append(f"   {k} = {v}")
    return True, "\n".join(lines)


def cgroup_v2_report() -> tuple:
    """读 cgroups v2 统一层级（参考 admin-guide/cgroup-v2.rst）。"""
    cg = "/sys/fs/cgroup"
    if not os.path.isdir(cg):
        return False, "当前未挂载 cgroup（/sys/fs/cgroup 不存在）"
    controllers = _read(f"{cg}/cgroup.controllers")
    subctl = _read(f"{cg}/cgroup.subtree_control")
    lines = ["cgroups v2（参考 admin-guide/cgroup-v2.rst）:"]
    lines.append(f"   可用控制器: {controllers or '(空)'}")
    lines.append(f"   已委托控制器(subtree_control): {subctl or '(空)'}")
    return True, "\n".join(lines)


def oom_report() -> tuple:
    """读 OOM 防护相关 sysctl 与当前进程 oom_score（参考 mm/oom_kill.rst）。"""
    p_oom = _read("/proc/sys/vm/panic_on_oom")
    alloc = _read("/proc/sys/vm/oom_kill_allocating_task")
    if p_oom == "" and alloc == "":
        return False, "当前非 Linux（/proc/sys/vm/panic_on_oom 不存在）"
    try:
        self_score = _read("/proc/self/oom_score")
        self_adj = _read("/proc/self/oom_score_adj")
    except OSError:
        self_score = self_adj = ""
    lines = [f"panic_on_oom: {p_oom or '?'}  oom_kill_allocating_task: {alloc or '?'}",
             f"本进程 oom_score={self_score or '?'} oom_score_adj={self_adj or '?'}"]
    return True, "\n".join(lines)


def psi_report() -> tuple:
    """读 PSI 资源压力（参考 accounting/psi.rst）。"""
    out: list = []
    for res in ("cpu", "memory", "io"):
        p = f"/proc/pressure/{res}"
        if not os.path.exists(p):
            continue
        txt = _read(p)
        if txt:
            out.append(f"{res}: {txt.splitlines()[0] if txt.splitlines() else txt}")
    if not out:
        return False, "当前内核未启用 PSI（/proc/pressure/* 不存在）"
    return True, "资源压力(PSI, 参考 accounting/psi.rst):\n  " + "\n  ".join(out)


def thp_compaction_report() -> tuple:
    """读 THP 规整策略（参考 admin-guide/mm/transhuge.rst）。"""
    p = "/sys/kernel/mm/transparent_hugepage/defrag"
    s = _read(p)
    if s == "":
        return False, "当前非 Linux 或内核未暴露 transparent_hugepage 接口"
    import re as _re
    active = _re.search(r"\[([^\]]+)\]", s)
    cur = active.group(1) if active else s.split()[0] if s.split() else "?"
    return True, f"transparent_hugepage/defrag: {cur}（参考 transhuge.rst 规整策略）"


def vm_dirty_report() -> tuple:
    """读脏页回写与缓存回收 sysctl（参考 admin-guide/sysctl/vm.rst）。"""
    base = "/proc/sys/vm"
    keys = ["dirty_ratio", "dirty_background_ratio", "dirty_expire_centisecs",
            "vfs_cache_pressure"]
    if not os.path.isfile(f"{base}/dirty_ratio"):
        return False, "当前非 Linux（/proc/sys/vm/dirty_ratio 不存在）"
    lines = ["vm 脏页/缓存 sysctl（参考 sysctl/vm.rst）:"]
    for k in keys:
        v = _read(f"{base}/{k}")
        if v:
            lines.append(f"   {k} = {v}")
    return True, "\n".join(lines)


# ---------------------------------------------------------------------------
# 网络子系统（network）只读探测
# ---------------------------------------------------------------------------

def tcp_report() -> tuple:
    """读 TCP 缓冲与特性开关（参考 networking/ip-sysctl.rst）。"""
    base = "/proc/sys/net/ipv4"
    if not os.path.isfile(f"{base}/tcp_rmem"):
        return False, "当前非 Linux（/proc/sys/net/ipv4/tcp_rmem 不存在）"
    lines = ["TCP sysctl（参考 networking/ip-sysctl.rst）:"]
    for k in ("tcp_rmem", "tcp_wmem", "tcp_sack", "tcp_timestamps",
              "tcp_window_scaling"):
        v = _read(f"{base}/{k}")
        if v:
            lines.append(f"   {k} = {v}")
    return True, "\n".join(lines)


def tcp_congestion_report() -> tuple:
    """读当前/可用 TCP 拥塞控制算法（参考 ip-sysctl.rst）。"""
    base = "/proc/sys/net/ipv4"
    cur = _read(f"{base}/tcp_congestion_control")
    avail = _read(f"{base}/tcp_available_congestion_control")
    if cur == "" and avail == "":
        return False, "当前非 Linux（/proc/sys/net/ipv4/tcp_congestion_control 不存在）"
    lines = [f"当前拥塞控制: {cur or '?'}",
             f"可用算法: {avail or '?'}"]
    return True, "\n".join(lines)


def net_core_report() -> tuple:
    """读 net.core 队列/缓冲参数（参考 networking/ip-sysctl.rst）。"""
    base = "/proc/sys/net/core"
    if not os.path.isfile(f"{base}/netdev_max_backlog"):
        return False, "当前非 Linux（/proc/sys/net/core/netdev_max_backlog 不存在）"
    lines = ["net.core sysctl（参考 networking/ip-sysctl.rst）:"]
    for k in ("netdev_max_backlog", "netdev_budget", "rmem_max", "wmem_max",
              "somaxconn"):
        v = _read(f"{base}/{k}")
        if v:
            lines.append(f"   {k} = {v}")
    return True, "\n".join(lines)


def rps_report() -> tuple:
    """读网卡 RPS/RFS 接收侧缩放配置（参考 networking/scaling.rst）。"""
    ndir = "/sys/class/net"
    if not os.path.isdir(ndir):
        return False, "当前非 Linux（/sys/class/net 不存在）"
    rows = []
    for iface in sorted(os.listdir(ndir)):
        qdir = os.path.join(ndir, iface, "queues")
        if not os.path.isdir(qdir):
            continue
        for q in sorted(os.listdir(qdir)):
            if not q.startswith("rx-"):
                continue
            cpus = _read(os.path.join(qdir, q, "rps_cpus"))
            rows.append(f"{iface}/{q}: rps_cpus={cpus or '0'}")
            break  # 仅取首条 rx 队列示意
    if not rows:
        return False, "未读到任何网卡的 RPS 配置（/sys/class/net/<if>/queues/rx-*/rps_cpus）"
    return True, "RPS/RFS（参考 networking/scaling.rst）:\n  " + "\n  ".join(rows)


def _agg_norm(r):
    """归一化报告返回：tuple→(ok,msg)；list→(True,拼接)；其它→(True,str)。"""
    if isinstance(r, tuple):
        ok = bool(r[0]) if r else False
        msg = str(r[1]) if len(r) > 1 else ""
        return ok, msg
    if isinstance(r, list):
        return True, "\n".join(str(x) for x in r)
    return True, str(r)


def kernel_report() -> tuple:
    """内核调优只读聚合：串联 scheduler/OOM/PSI/THP/vm-net 各子系统报告。

    仅串联既有只读子报告，不写、不调优；任一子报告异常即跳过该项。
    """
    parts = []
    ok_any = False
    for fn in (sched_report, oom_report, psi_report, thp_compaction_report,
               vm_dirty_report, tcp_report, tcp_congestion_report, net_core_report, rps_report):
        try:
            ok, msg = _agg_norm(fn())
        except Exception:  # noqa: BLE001
            continue
        ok_any = ok_any or ok
        if msg.strip():
            parts.append(msg.strip())
    if not parts:
        return False, "未读到任何内核调优接口（非 Linux 或接口未暴露）"
    return ok_any, "\n".join(parts)
