"""网络协议 / ITU 标准相关的原生调优接口（默认关闭、需用户选择+确认）。

每个函数对应一个网络/协议开关，按 RFC / IEEE / ITU-T 标准施加。约定：
- 仅在 Linux 等能用 sysctl/ip/iw 的平台真正生效；其他平台返回指引，不硬来。
- 这些函数由 opt_in 任务在「用户显式选择 + 确认」后才调用，不会默认执行。

参考标准（详见 data/network_standards.json）：
- RFC 8981（取代 RFC 4941）IPv6 隐私扩展 / RFC 8200 IPv6 / RFC 3168 ECN / RFC 9002 BBR
- RFC 1191 PMTUD / RFC 7858 DoT / RFC 8484 DoH
- IEEE 802.11 节能 / ITU-T Y.1541 QoS / ITU-T G.992 ADSL / ITU-T G.711 语音
- L4S 低时延低丢包：RFC 9330（架构 Informational）/ 9331（ECN 协议 Experimental）/ 9332（DualQ 耦合 AQM Experimental）
- Wi-Fi 6（IEEE 802.11ax-2021）/ Wi-Fi 7（IEEE 802.11be-2024）
- 时间同步：NTP RFC 5905 / PTP IEEE 1588-2019 / gPTP IEEE 802.1AS-2020 /
  SyncE ITU-T G.8261·G.8262 / 分组网时间相位同步 ITU-T G.8271·G.8275.1 / White Rabbit（CERN 扩展）

自动适应调优参考（详见 data/network_docs.json 的 l4s / wifi_ax_be / ntp / ptp 条目）：
- L4S：tc qdisc add root dualpi2 + ECN（RFC 9332 DualQ），先 fq_codel/cake 验证无 bufferbloat 再升级
- 时间同步：普通系统用 chrony/NTP（RFC 5905）；亚微秒场景上 PTP（IEEE 1588，需网卡 PHC，ethtool -T 探测）；
  亚纳秒光纤长距评估 White Rabbit；安全敏感场景启用 NTS（RFC 8915）防时间欺骗
"""

from __future__ import annotations

import json
import os
import shutil
import sys

from . import common


def _is_linux() -> bool:
    return sys.platform == "linux"


def _sysctl_set(key: str, val: str) -> tuple:
    if not _is_linux():
        return False, f"非 Linux 平台，{key} 调优需在对应系统用原生方式设置（指引）"
    rc, out = common.run(f"sysctl -w {key}={val}")
    return rc == 0, out or f"{key}={val}"


def ipv6_privacy(on: bool = True) -> tuple:
    """IPv6 隐私扩展（RFC 8981，2021 取代 RFC 4941）。on=True 用临时地址。"""
    return _sysctl_set("net.ipv6.conf.all.use_tempaddr", "2" if on else "0")


def ipv6_enabled(on: bool = True) -> tuple:
    """IPv6 总开关（RFC 8200）。"""
    return _sysctl_set("net.ipv6.conf.all.disable_ipv6", "0" if on else "1")


def ecn(on: bool = True) -> tuple:
    """ECN 显式拥塞通知（RFC 3168）。"""
    return _sysctl_set("net.ipv4.tcp_ecn", "1" if on else "0")


def tcp_bbr() -> tuple:
    """改用 BBR 拥塞控制（IETF CCRG / RFC 9002 思路）。"""
    if not _is_linux():
        return False, "非 Linux 平台，BBR 需在对应系统按原生方式启用（指引）"
    # 先确认内核支持
    rc, out = common.run("sysctl -n net.ipv4.tcp_available_congestion_control")
    if rc == 0 and "bbr" in out:
        return _sysctl_set("net.ipv4.tcp_congestion_control", "bbr")
    return False, f"内核未提供 BBR（可用：{out.strip()}）；需装载 tcp_bbr 模块"


def mtu_pmtud(on: bool = True) -> tuple:
    """路径 MTU 发现（RFC 1191）。"""
    return _sysctl_set("net.ipv4.ip_no_pmtu_disc", "0" if on else "1")


def wifi_powersave(on: bool = True) -> tuple:
    """Wi-Fi 节能（IEEE 802.11）。需 iw 与无线接口。"""
    iface = _wifi_iface()
    if not iface:
        return False, "未检测到无线接口（或没有 iw），跳过 Wi-Fi 节能"
    rc, out = common.run(f"iw dev {iface} set power_save {'on' if on else 'off'}")
    return rc == 0, out or f"Wi-Fi({iface}) 节能={'开' if on else '关'}"


def _wifi_iface() -> str:
    rc, out = common.run("iw dev 2>/dev/null | awk '/Interface/ {print $2; exit}'")
    return out.strip() if rc == 0 and out.strip() else ""


# --------------------------------------------------------------------------- #
# v0.5.9 网络栈深度调优（eBPF / ethtool 维度）——文档跟踪 + 只读运维探测 + 调优接口
#
# 「触类旁通、举一反三」：在内核 / 桌面 / 系统软件 / 鸿蒙 / 小程序端 / 包管理器 /
# 容器运行时 / 存储与文件系统之后，把同一模式推广到**网络栈运维与可观测性**。每个工具
# 接口彼此完全不同，逐个按**自身的协议与接口**核对，绝不套用同一套路径：
#   - iproute2 : netlink / rtnetlink + sock_diag；ip -br addr / ss / tc qdisc show
#   - ethtool  : ETHTOOL ioctl / netlink；-k/-i/-l/-g/-c/-S 只读，-K/-C 写
#   - eBPF     : bpf() 系统调用 + libbpf；bpftool prog/map/net list 只读检视
#   - tc       : rtnetlink(TC) qdisc；show 只读，add/replace 写
#   - conntrack: nf_conntrack；-S / /proc 只读，sysctl max 写
#   - nm_resolved: NM D-Bus / networkd INI / resolved stub；nmcli/networkctl/resolvectl 只读
#   - scaling  : RPS/RFS/XPS sysfs + net.core；cat/sysctl 只读，echo/sysctl 写
# 所有探测只读：仅统计接口/卸载/程序/队列/连接表，不做任何写操作；未安装该工具
# 或接口不可用返回 (False, 说明)，由上层降级为指引。参考文档见 data/network_docs.json。
# --------------------------------------------------------------------------- #


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "network_docs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:
        return {}


REFS = _load_refs()


def reference(net_id: str) -> dict:
    """返回某网络运维工具的文档参考（含协议 protocols 与接口 interfaces）。"""
    return REFS.get(net_id, {})


def reference_all() -> dict:
    """返回全部网络栈深度调优文档参考。"""
    return REFS


def _common_run(cmd: str, timeout: int = 30):
    return common.run(cmd, timeout=timeout)


def _list_ifaces() -> list:
    """从 ip -o link 读接口名列表（只读）。"""
    rc, out = _common_run("ip -o link show 2>/dev/null", timeout=20)
    ifaces = []
    if rc == 0:
        for l in out.splitlines():
            parts = l.split(":", 2)
            if len(parts) >= 2:
                name = parts[1].strip()
                if name:
                    ifaces.append(name)
    return ifaces


def detect_network() -> dict:
    """探测本机可用的网络栈运维工具（按各自官方 CLI 是否可用判断，只读 which 查询）。"""
    return {
        "iproute2": bool(shutil.which("ip")) and bool(shutil.which("ss")),
        "ethtool": bool(shutil.which("ethtool")),
        "ebpf": bool(shutil.which("bpftool")),
        "tc": bool(shutil.which("tc")),
        "conntrack": bool(shutil.which("conntrack")),
        "nm_resolved": bool(shutil.which("nmcli") or shutil.which("networkctl")
                            or shutil.which("resolvectl")),
        "scaling": _is_linux(),
    }


# --------------------------------------------------------------------------- #
# 各运维工具只读探测：返回 (ok: bool, msg: str)。ok 表示该项可用且探测成功。   #
# --------------------------------------------------------------------------- #

def iproute2_report() -> tuple:
    """iproute2 接口/地址/监听套接字（ip/ss，netlink）——只读诊断。"""
    if not (shutil.which("ip") and shutil.which("ss")):
        return False, "未安装 iproute2（ip / ss），跳过（Debian/Ubuntu: iproute2）"
    rc, links = _common_run("ip -br link show 2>/dev/null", timeout=20)
    lines = ["接口状态（ip -br link，只读）："]
    if rc == 0 and links.strip():
        for l in links.splitlines()[:16]:
            lines.append("   · " + l.strip())
    rc2, addr = _common_run("ip -br addr show 2>/dev/null", timeout=20)
    if rc2 == 0 and addr.strip():
        up = [l for l in addr.splitlines() if "UP" in l]
        lines.append(f"   · 已 UP 接口: {len(up)} 个（ip -br addr）")
    rc3, ss = _common_run("ss -tunlp 2>/dev/null", timeout=20)
    if rc3 == 0:
        n = len([l for l in ss.splitlines() if l.strip() and not l.startswith("State")])
        lines.append(f"   · 监听套接字: {n} 个（ss -tunlp）；逐连接 TCP 指标用 ss -tinp")
    return True, "\n".join(lines)


def ethtool_report() -> tuple:
    """网卡卸载/特性（ethtool -k/-i，ETHTOOL）——只读诊断。"""
    if not shutil.which("ethtool"):
        return False, "未安装 ethtool，跳过（Debian/Ubuntu: ethtool）"
    ifaces = _list_ifaces()
    if not ifaces:
        return False, "未发现网络接口（ip link 无输出）"
    lines = [f"网卡卸载/特性（ethtool -k，只读；前 {min(len(ifaces), 4)} 接口）："]
    for ifc in ifaces[:4]:
        rc, info = _common_run(f"ethtool -i {ifc!r} 2>/dev/null", timeout=20)
        drv = ""
        if rc == 0:
            for l in info.splitlines():
                if l.lower().startswith("driver:"):
                    drv = l.split(":", 1)[1].strip()
                    break
        rc2, feat = _common_run(f"ethtool -k {ifc!r} 2>/dev/null", timeout=20)
        off = []
        if rc2 == 0:
            for l in feat.splitlines():
                s = l.strip()
                if s.startswith(("tcp-segmentation-offload", "generic-segmentation-offload",
                                 "generic-receive-offload", "large-receive-offload",
                                 "tx-checksumming")):
                    key = s.split(":", 1)[0].split()[0]
                    val = s.split(":", 1)[1].strip()
                    off.append(f"{key}={val}")
        lines.append(f"   · {ifc}  驱动={drv or '?'}  " + "  ".join(off))
    lines.append("   · 诊断 ethtool -k/-i/-l/-g/-c/-S（只读）；调优 ethtool -K/-C（写，opt-in）")
    return True, "\n".join(lines)


def ebpf_report() -> tuple:
    """eBPF 程序/映射（bpftool prog/map/net list）——只读检视。"""
    if not shutil.which("bpftool"):
        return False, "未安装 bpftool，跳过（多数发行版包名 bpftool）"
    rc, prog = _common_run("bpftool prog list 2>/dev/null", timeout=20)
    if rc != 0 or not (prog or "").strip():
        return False, "未发现已加载的 eBPF 程序（bpftool prog list 无输出）"
    nprog = len([l for l in prog.splitlines() if l.strip() and l.strip()[0].isdigit()])
    lines = [f"eBPF 程序（bpftool prog list，只读）：{nprog} 个已加载"]
    rc2, mp = _common_run("bpftool map list 2>/dev/null", timeout=20)
    if rc2 == 0 and (mp or "").strip():
        nmap = len([l for l in mp.splitlines() if l.strip() and l.strip()[0].isdigit()])
        lines.append(f"   · 映射(map): {nmap} 个（bpftool map list）")
    rc3, net = _common_run("bpftool net list 2>/dev/null", timeout=20)
    if rc3 == 0 and (net or "").strip() and len(net.splitlines()) > 1:
        lines.append("   · 已 attach: bpftool net list（XDP / tc / flow）")
    lines.append("   · 只读检视即可；切勿 detach/删除不认识的程序（Cilium/监控/防火墙依赖）")
    return True, "\n".join(lines)


def tc_report() -> tuple:
    """流量控制 qdisc（tc qdisc show）——只读诊断。"""
    if not shutil.which("tc"):
        return False, "未安装 iproute2-tc（tc），跳过"
    rc, out = _common_run("tc qdisc show 2>/dev/null", timeout=20)
    if rc != 0 or not (out or "").strip():
        return False, "未发现流量控制 qdisc（tc qdisc show 无输出；可能全是默认 pfifo_fast）"
    lines = ["流量控制 qdisc（tc qdisc show，只读）："]
    for l in out.splitlines()[:16]:
        if l.strip():
            lines.append("   · " + l.strip())
    lines.append("   · 缓解 bufferbloat 用 fq_codel/cake（tc qdisc add ... root fq_codel，写，opt-in）")
    return True, "\n".join(lines)


def conntrack_report() -> tuple:
    """连接跟踪表（conntrack -S / /proc/netfilter）——只读诊断。"""
    if not _is_linux():
        return False, "非 Linux 平台，nf_conntrack 不可用（指引）"
    maxp = "/proc/sys/net/netfilter/nf_conntrack_max"
    cntp = "/proc/sys/net/netfilter/nf_conntrack_count"
    if not os.path.exists(maxp) or not os.path.exists(cntp):
        return False, "未启用 nf_conntrack（/proc 无 conntrack_max/count；可能未加载模块或不用防火墙）"
    try:
        with open(maxp) as f:
            mx = f.read().strip()
        with open(cntp) as f:
            cnt = f.read().strip()
    except OSError:
        return False, "无法读取 nf_conntrack 计数"
    pct = ""
    try:
        if int(mx) > 0:
            pct = f"（{int(cnt) * 100 // int(mx)}%）"
    except (ValueError, ZeroDivisionError):
        pct = ""
    lines = [f"连接跟踪表（只读）：当前 {cnt} / 上限 {mx} {pct}"]
    if shutil.which("conntrack"):
        rc, s = _common_run("conntrack -S 2>/dev/null", timeout=20)
        if rc == 0 and (s or "").strip():
            for l in s.splitlines()[:6]:
                if l.strip():
                    lines.append("   · " + l.strip())
    lines.append("   · 逼近上限调 net.netfilter.nf_conntrack_max（写，opt-in）；勿 flush 在用表")
    return True, "\n".join(lines)


def nm_resolved_report() -> tuple:
    """连接与 DNS（nmcli / networkctl / resolvectl）——只读诊断。"""
    if shutil.which("nmcli"):
        rc, out = _common_run("nmcli -t -f DEVICE,TYPE,STATE device status 2>/dev/null",
                              timeout=20)
        lines = ["连接管理（nmcli device status，只读）："]
        if rc == 0 and (out or "").strip():
            for l in out.splitlines()[:10]:
                if l.strip():
                    lines.append("   · " + l.replace(":", " ").strip())
        if shutil.which("resolvectl"):
            rc2, dns = _common_run("resolvectl dns 2>/dev/null", timeout=20)
            if rc2 == 0 and (dns or "").strip():
                lines.append("   · DNS(resolvectl):")
                for l in dns.splitlines()[:6]:
                    if l.strip():
                        lines.append("       " + l.strip())
        lines.append("   · 改 DNS/DoT 在 NM 连接配（写，opt-in）；勿直接改被接管的 /etc/resolv.conf")
        return True, "\n".join(lines)
    if shutil.which("networkctl"):
        rc, out = _common_run("networkctl status 2>/dev/null", timeout=20)
        lines = ["连接管理（networkctl status，只读）："]
        if rc == 0 and (out or "").strip():
            for l in out.splitlines()[:10]:
                if l.strip():
                    lines.append("   · " + l.strip())
        return True, "\n".join(lines)
    return False, ("未安装 NetworkManager（nmcli）/ systemd-networkd（networkctl）/ "
                   "resolved（resolvectl），跳过")


def scaling_report() -> tuple:
    """接收/发送侧缩放（RPS/RFS/XPS，sysfs + net.core）——只读诊断。"""
    if not _is_linux():
        return False, "非 Linux 平台，RPS/XPS 不可用（指引）"
    ifaces = _list_ifaces()
    if not ifaces:
        return False, "未发现网络接口（ip link 无输出）"
    lines = ["接收/发送侧缩放（RPS/RFS/XPS，sysfs 只读）："]
    seen = False
    for ifc in ifaces[:4]:
        qdir = f"/sys/class/net/{ifc}/queues"
        try:
            rxq = [d for d in os.listdir(qdir) if d.startswith("rx-")]
        except OSError:
            rxq = []
        if not rxq:
            continue
        masks = []
        for q in rxq[:4]:
            p = os.path.join(qdir, q, "rps_cpus")
            try:
                with open(p) as f:
                    masks.append(f.read().strip())
            except OSError:
                masks.append("?")
        lines.append(f"   · {ifc}  rx 队列 {len(rxq)}  RPS 掩码(前4)={masks}")
        seen = True
    if not seen:
        return False, "未发现带 rx 队列的接口（无法读 RPS 掩码）"
    rc, b = _common_run("sysctl -n net.core.netdev_max_backlog 2>/dev/null", timeout=20)
    if rc == 0 and (b or "").strip():
        lines.append(f"   · net.core.netdev_max_backlog={b.strip()}")
    lines.append("   · 单队列网卡多核场景：echo <cpumask> > rps_cpus 开 RPS（写，opt-in）；多队列优先 RSS")
    return True, "\n".join(lines)


# CLI / GUI 遍历用：探测函数名 + 中文标签
PROBES = (
    ("iproute2_report", "iproute2 接口/地址/监听套接字（ip/ss，netlink）"),
    ("ethtool_report", "网卡卸载/特性（ethtool -k/-i，ETHTOOL）"),
    ("ebpf_report", "eBPF 程序/映射（bpftool prog/map/net list）"),
    ("tc_report", "流量控制 qdisc（tc qdisc show）"),
    ("conntrack_report", "连接跟踪表（conntrack -S / /proc/netfilter）"),
    ("nm_resolved_report", "连接与 DNS（nmcli/networkctl/resolvectl）"),
    ("scaling_report", "RPS/RFS/XPS 缩放（sysfs + net.core）"),
)


def environment_report() -> list:
    """返回本机网络栈运维工具可用性概览（✓ 已装 / ✗ 未装）。"""
    det = detect_network()
    lines = ["网络栈运维工具可用性："]
    for key, label in (
        ("iproute2", "iproute2 (ip/ss)"), ("ethtool", "ethtool (网卡特性)"),
        ("ebpf", "bpftool (eBPF)"), ("tc", "tc (流量控制)"),
        ("conntrack", "conntrack (nf_conntrack)"),
        ("nm_resolved", "NetworkManager/resolved (nmcli/resolvectl)"),
        ("scaling", "RPS/XPS (sysfs, Linux)"),
    ):
        mark = "✓" if det.get(key) else "✗"
        lines.append(f"   {mark} {label}")
    return lines


def network_doc_list() -> list:
    """返回文档参考清单文本行（供 CLI/GUI 展示）。"""
    lines = []
    for key, ref in REFS.items():
        lines.append(f"· {key} — {ref.get('name', '')}")
        lines.append(f"    机构: {ref.get('org', '')}")
        lines.append(f"    文档: {ref.get('url', '')}")
        lines.append("    协议:")
        for p in ref.get("protocols", []):
            lines.append(f"      - {p}")
        lines.append("    接口:")
        for i in ref.get("interfaces", []):
            lines.append(f"      - {i}")
        lines.append(f"    建议: {ref.get('summary', '')}")
    return lines


# --------------------------------------------------------------------------- #
# opt_in 调优原生函数（写操作）：仅在用户选择 + 确认后由对应任务调用，绝不默认执行。
# 每一项都走该工具自身的官方写接口（ethtool -K / sysfs / tc qdisc / sysctl），
# 不套用 DNS/协议层的 sysctl 写法，也不做 rm/dd 之类破坏性操作。
# 这些函数被 Task 以无参方式派发（runner 调 fn()），因此接口名/CPU 掩码均自动探测，
# 仅当作库函数手动调用时可显式传入参数。
# --------------------------------------------------------------------------- #

def _primary_iface() -> str:
    """挑一个「主」网络接口：已 UP、有 IPv4、非 lo/虚拟网桥优先（只读探测）。"""
    rc, out = _common_run("ip -o -4 addr show up 2>/dev/null", timeout=20)
    cand = []
    if rc == 0:
        for l in out.splitlines():
            parts = l.split()
            if len(parts) >= 2:
                name = parts[1].split("@")[0]
                if name != "lo" and not name.startswith(("docker", "br-", "veth", "virbr")):
                    cand.append(name)
    if not cand:
        rc, out = _common_run("ip -o link show up 2>/dev/null", timeout=20)
        if rc == 0:
            for l in out.splitlines():
                parts = l.split(":", 2)
                if len(parts) >= 2:
                    name = parts[1].strip().split("@")[0]
                    if name and name != "lo" and not name.startswith(("docker", "br-", "veth")):
                        cand.append(name)
    return cand[0] if cand else ""


def _online_cpu_mask() -> str:
    """读 /sys/devices/system/cpu/online（如 0-3）转成十六进制 RPS/XPS 掩码（只读）。"""
    p = "/sys/devices/system/cpu/online"
    try:
        with open(p) as f:
            spec = f.read().strip()
    except OSError:
        return ""
    mask = 0
    for seg in spec.split(","):
        if "-" in seg:
            lo, hi = seg.split("-")
            mask |= sum(1 << c for c in range(int(lo), int(hi) + 1))
        elif seg:
            mask |= 1 << int(seg)
    return format(mask, "x")


def ethtool_offload(iface: str | None = None, on: bool = True) -> tuple:
    """网卡卸载开关（ethtool -K）：GRO/GSO/TSO。转发设备不要开 LRO。"""
    if not _is_linux():
        return False, "非 Linux 平台，ethtool -K 需按对应系统原生方式设置（指引）"
    if not shutil.which("ethtool"):
        return False, "未安装 ethtool，无法设置卸载"
    if iface is None:
        iface = _primary_iface()
        if not iface:
            return False, "未发现可用网络接口（ip link 无输出），无法设置卸载"
    state = "on" if on else "off"
    rc, out = common.run(
        f"ethtool -K {iface!r} gro {state} gso {state} tso {state}")
    return rc == 0, out or f"{iface} 卸载={'on' if on else 'off'}"


def ethtool_coalesce(iface: str | None = None, rx_usec: int = 50,
                     tx_usec: int = 50) -> tuple:
    """网卡中断聚合（ethtool -C）：降低中断率、省 CPU。"""
    if not _is_linux():
        return False, "非 Linux 平台，ethtool -C 需按原生方式设置（指引）"
    if not shutil.which("ethtool"):
        return False, "未安装 ethtool，无法设置中断聚合"
    if iface is None:
        iface = _primary_iface()
        if not iface:
            return False, "未发现可用网络接口，无法设置中断聚合"
    rc, out = common.run(
        f"ethtool -C {iface!r} rx-usecs {rx_usec} tx-usecs {tx_usec}")
    return rc == 0, out or f"{iface} 中断聚合 rx/tx-usecs={rx_usec}/{tx_usec}"


def rps_enable(iface: str | None = None, mask: str | None = None) -> tuple:
    """单队列网卡开 RPS：把 rx-*/rps_cpus 写成 CPU 掩码（sysfs 写）。"""
    if not _is_linux():
        return False, "非 Linux 平台，RPS 需按 sysfs 原生方式设置（指引）"
    if iface is None:
        iface = _primary_iface()
        if not iface:
            return False, "未发现可用网络接口，无法开 RPS"
    if mask is None:
        mask = _online_cpu_mask()
        if not mask:
            return False, "无法读取 CPU 拓扑（/sys/devices/system/cpu/online），无法构造 RPS 掩码"
    qdir = f"/sys/class/net/{iface}/queues"
    try:
        rxq = [d for d in os.listdir(qdir) if d.startswith("rx-")]
    except OSError:
        return False, f"找不到 {iface} 的 rx 队列目录"
    if not rxq:
        return False, f"{iface} 无 rx 队列，无法开 RPS"
    errs = []
    for q in rxq:
        p = os.path.join(qdir, q, "rps_cpus")
        try:
            with open(p, "w") as f:
                f.write(mask)
        except OSError as e:
            errs.append(f"{q}: {e}")
    if errs:
        return False, f"写入 RPS 掩码部分失败: {'; '.join(errs)}"
    return True, f"{iface} 已对 {len(rxq)} 个 rx 队列设置 RPS 掩码 {mask}"


def xps_enable(iface: str | None = None, mask: str | None = None) -> tuple:
    """发送侧 XPS：把 tx-*/xps_cpus 写成 CPU 掩码（sysfs 写）。"""
    if not _is_linux():
        return False, "非 Linux 平台，XPS 需按 sysfs 原生方式设置（指引）"
    if iface is None:
        iface = _primary_iface()
        if not iface:
            return False, "未发现可用网络接口，无法开 XPS"
    if mask is None:
        mask = _online_cpu_mask()
        if not mask:
            return False, "无法读取 CPU 拓扑（/sys/devices/system/cpu/online），无法构造 XPS 掩码"
    qdir = f"/sys/class/net/{iface}/queues"
    try:
        txq = [d for d in os.listdir(qdir) if d.startswith("tx-")]
    except OSError:
        return False, f"找不到 {iface} 的 tx 队列目录"
    if not txq:
        return False, f"{iface} 无 tx 队列，无法开 XPS"
    errs = []
    for q in txq:
        p = os.path.join(qdir, q, "xps_cpus")
        try:
            with open(p, "w") as f:
                f.write(mask)
        except OSError as e:
            errs.append(f"{q}: {e}")
    if errs:
        return False, f"写入 XPS 掩码部分失败: {'; '.join(errs)}"
    return True, f"{iface} 已对 {len(txq)} 个 tx 队列设置 XPS 掩码 {mask}"


def tc_fq_codel(iface: str | None = None) -> tuple:
    """出口挂 fq_codel 对抗缓冲膨胀（tc qdisc add ... root fq_codel）。"""
    if not _is_linux():
        return False, "非 Linux 平台，tc qdisc 需按原生方式设置（指引）"
    if not shutil.which("tc"):
        return False, "未安装 iproute2-tc（tc），无法设置 qdisc"
    if iface is None:
        iface = _primary_iface()
        if not iface:
            return False, "未发现可用网络接口，无法设置 qdisc"
    rc, out = common.run(f"tc qdisc replace dev {iface!r} root fq_codel")
    return rc == 0, out or f"{iface} 出口已设 fq_codel（缓冲膨胀缓解）"


def conntrack_max(value: int = 262144) -> tuple:
    """调高连接跟踪表上限（sysctl -w net.netfilter.nf_conntrack_max）。"""
    return _sysctl_set("net.netfilter.nf_conntrack_max", str(value))


def netdev_backlog(value: int = 5000) -> tuple:
    """调高 NAPI 收包 backlog 上限（net.core.netdev_max_backlog）。"""
    return _sysctl_set("net.core.netdev_max_backlog", str(value))
