"""OSI 七层网络诊断（只读）。

以 ISO/IEC 7498-1 / ITU-T X.200「开放系统互连参考模型」为骨架，把本机网络栈
按七层**结构化、只读**地摸一遍：

    L1 物理层   Physical      介质/接口/载波/速率/双工/驱动/总线后端
    L2 数据链路 Data Link     MAC/MTU/卸载/桥接·绑定·VLAN/802.1X
    L3 网络层   Network       IP 地址/路由/邻居/防火墙/反向路径/PMTU
    L4 传输层   Transport    监听套接字/TCP 拥塞/连接跟踪/UDP
    L5 会话层   Session      保活 sysctl/已建连接/隧道(VPN/WireGuard)
    L6 表示层   Presentation TLS 密码套件/DoT·DoH/证书
    L7 应用层   Application  DNS 解析器/可达性探测/代理环境

参照（权威文档，仅用于把「该看什么」钉死，不执行其中任何命令的写操作）：
- ISO/IEC 7498-1:1994 / ITU-T X.200  —— 七层模型与每层服务定义
- RFC 1122 / RFC 1123                —— TCP/IP 各层的实现与运维要求
- RFC 792 / 826 / 2131 / 4861        —— ICMP/ARP/DHCP/NDP
- RFC 793 / 9293 / 9002              —— TCP / 拥塞控制(BBR 见 RFC 9002 附录)
- RFC 8446                            —— TLS 1.3（表示层安全子层）
- RFC 4033 / 7858 / 8484             —— DNSSEC / DNS-over-TLS / DNS-over-HTTPS

红线：全部只读——不增删地址、不改路由、不 reload 防火墙、不连校外网做写操作。
      L7 可达性探测仅 http/https + 短超时，且默认只对本地回环与 DNS 做；
      要探外网请用 CLI `osi probe --url <http(s)>`（显式、可审计）。
"""

from __future__ import annotations

import os
import shutil
import socket
import urllib.request
from typing import Dict, List, Tuple

from . import common

# --------------------------------------------------------------------------- #
# 七层定义（用于报告表头与能力自检；PDU 即该层协议数据单元）                    #
# --------------------------------------------------------------------------- #
LAYER_DEFS: List[Dict[str, str]] = [
    {"n": 1, "name": "物理层", "en": "Physical", "pdu": "比特 (bit)",
     "ref": "ISO/IEC 7498-1 / ITU-T X.200 §L1"},
    {"n": 2, "name": "数据链路层", "en": "Data Link", "pdu": "帧 (frame)",
     "ref": "IEEE 802.3 / 802.11 / RFC 7042(MAC)"},
    {"n": 3, "name": "网络层", "en": "Network", "pdu": "包 (packet)",
     "ref": "RFC 791(IP) / 2460(IPv6) / 792(ICMP)"},
    {"n": 4, "name": "传输层", "en": "Transport", "pdu": "段/数据报 (segment/datagram)",
     "ref": "RFC 9293(TCP) / 768(UDP)"},
    {"n": 5, "name": "会话层", "en": "Session", "pdu": "会话 (session)",
     "ref": "RFC 1122 §4 (keep-alive) / RFC 4301(IPsec)"},
    {"n": 6, "name": "表示层", "en": "Presentation", "pdu": "数据(安全子层)",
     "ref": "RFC 8446(TLS) / RFC 7858(DoT) / RFC 8484(DoH)"},
    {"n": 7, "name": "应用层", "en": "Application", "pdu": "报文 (message)",
     "ref": "RFC 1035(DNS) / 9110(HTTP)"},
]


# --------------------------------------------------------------------------- #
# L1 物理层                                                                     #
# --------------------------------------------------------------------------- #
def _list_ifaces() -> List[str]:
    netd = "/sys/class/net"
    if not os.path.isdir(netd):
        return []
    out = []
    try:
        for name in os.listdir(netd):
            if name == "lo":
                continue
            out.append(name)
    except OSError:
        return []
    return out


def layer1_physical() -> Tuple[bool, str]:
    """物理层：接口存在性/载波/速率/双工/驱动/总线后端（/sys/class/net，只读）。"""
    ifaces = _list_ifaces()
    if not ifaces:
        return False, "未发现非回环网络接口（/sys/class/net 无条目；可能容器/无网卡）"
    lines = [f"L1 物理层（/sys/class/net，只读；{len(ifaces)} 个接口）："]
    for ifc in ifaces[:12]:
        d = f"/sys/class/net/{ifc}"
        try:
            def _rd(p: str) -> str:
                try:
                    with open(os.path.join(d, p), encoding="utf-8") as f:
                        return f.read().strip()
                except OSError:
                    return ""
            carrier = _rd("carrier")
            oper = _rd("operstate")
            speed = _rd("speed")         # 单位 Mbps，未知为 -1
            duplex = _rd("duplex")
            mtue = _rd("mtu")
            # 总线后端：device 软链指向 pci/usb 等
            bus = ""
            devlink = os.path.join(d, "device")
            if os.path.islink(devlink):
                tgt = os.path.realpath(devlink)
                if "/pci" in tgt:
                    bus = "PCIe"
                elif "/usb" in tgt:
                    bus = "USB"
                elif "virtual" in tgt or "bond" in tgt or "bridge" in tgt:
                    bus = "虚拟"
                else:
                    bus = "其他"
            wlan = "wireless" if os.path.isdir(os.path.join(d, "wireless")) else ""
            state = oper or ("已连接" if carrier == "1" else "未连接")
            spd = (f"{speed}Mbps" if speed not in ("", "-1") else "速率未知")
            dx = (f"/{duplex}" if duplex in ("full", "half") else "")
            lines.append(f"   · {ifc:<12} {state:<6} {spd}{dx}  MTU={mtue}  总线={bus}{(' '+wlan) if wlan else ''}")
        except OSError:
            lines.append(f"   · {ifc}: 读取失败")
    lines.append("   · 载波/速率来自网卡与交换机协商；改速率/双工属写操作（ethtool，opt-in）")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# L2 数据链路层                                                                 #
# --------------------------------------------------------------------------- #
def layer2_datalink() -> Tuple[bool, str]:
    """数据链路层：MAC/MTU/卸载/桥·绑·VLAN/802.1X（ip/ethtool，只读）。"""
    if not (shutil.which("ip") and shutil.which("ss")):
        return False, "未安装 iproute2（ip/ss），L2 跳过（Debian/Ubuntu: iproute2）"
    lines = ["L2 数据链路层（ip/ethtool，只读）："]
    rc, link = common.run("ip -br link show 2>/dev/null")
    if rc == 0 and link.strip():
        for l in link.splitlines()[:12]:
            s = l.strip()
            # 形如：eth0  UP  ...  <...>  mac  ...
            parts = s.split()
            if len(parts) >= 2 and "@" not in parts[0]:
                ifc = parts[0]
                # 取 MAC（通常是第 3 个 token 的 xx:xx 形式）
                mac = ""
                for tk in parts[2:]:
                    if ":" in tk and len(tk) >= 17:
                        mac = tk
                        break
                kind = ""
                if "bond" in ifc or "master" in s:
                    kind = " [绑定/桥成员]"
                if "vlan" in ifc or "@" in ifc:
                    kind = " [VLAN]"
                lines.append(f"   · {ifc:<12} MAC={mac or '?':<19}{kind}")
    # 802.1X（wpa_supplicant）存在性
    if shutil.which("wpa_supplicant") or os.path.exists("/run/wpa_supplicant"):
        lines.append("   · 检测到 802.1X 组件（wpa_supplicant）；企业网认证在表示层之上")
    else:
        lines.append("   · 未检测到 802.1X（wpa_supplicant）——家庭/服务器常见")
    lines.append("   · 卸载（GSO/GRO/LRO）状态用 ethtool -k（见 network.ethtool_report）")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# L3 网络层                                                                     #
# --------------------------------------------------------------------------- #
def layer3_network() -> Tuple[bool, str]:
    """网络层：IP 地址/路由/邻居/防火墙/反向路径/PMTU（ip，只读）。"""
    if not shutil.which("ip"):
        return False, "未安装 iproute2（ip），L3 跳过"
    lines = ["L3 网络层（ip，只读）："]
    rc, addr = common.run("ip -br addr show 2>/dev/null")
    v4 = v6 = 0
    if rc == 0 and addr.strip():
        for l in addr.splitlines():
            if "inet " in l:
                v4 += 1
            if "inet6 " in l:
                v6 += 1
        lines.append(f"   · 地址：IPv4 作用域非 lo {v4} 个 · IPv6 {v6} 个（含链路-local）")
    rc, route = common.run("ip route show default 2>/dev/null")
    if rc == 0 and route.strip():
        gw = []
        for l in route.splitlines()[:4]:
            s = l.strip()
            if s.startswith("default"):
                parts = s.split()
                if "via" in parts:
                    gw.append(parts[parts.index("via") + 1])
        lines.append(f"   · 默认路由网关：{', '.join(gw) if gw else '无（仅链路层）'}")
    else:
        lines.append("   · 未配置默认路由（default via）——仅局域网可达")
    # 防火墙
    fw = []
    if shutil.which("nft"):
        fw.append("nftables")
    if shutil.which("iptables"):
        fw.append("iptables(legacy/nft)")
    lines.append(f"   · 防火墙工具：{', '.join(fw) if fw else '未发现（iptables/nft 均未装）'}")
    # 反向路径过滤
    rp = "/proc/sys/net/ipv4/conf/all/rp_filter"
    if os.path.exists(rp):
        try:
            with open(rp, encoding="utf-8") as f:
                val = f.read().strip()
            lines.append(f"   · rp_filter(all)={val}（0=宽松/1=严格/2=松散；RFC 3704）")
        except OSError:
            pass
    lines.append("   · 邻居/ARP 用 ip neigh；PMTU 走 /proc/sys/net/ipv4/ip_no_pmtu_disc")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# L4 传输层                                                                     #
# --------------------------------------------------------------------------- #
def layer4_transport() -> Tuple[bool, str]:
    """传输层：监听套接字/TCP 拥塞算法/连接跟踪/UDP（ss/conntrack，只读）。"""
    if not shutil.which("ss"):
        return False, "未安装 iproute2-ss，L4 跳过"
    lines = ["L4 传输层（ss/conntrack，只读）："]
    rc, ss = common.run("ss -tunlp 2>/dev/null")
    n_listen = n_tcp = n_udp = 0
    if rc == 0:
        for l in ss.splitlines():
            s = l.strip()
            if s.startswith("LISTEN"):
                n_listen += 1
            elif s.startswith("tcp"):
                n_tcp += 1
            elif s.startswith("udp"):
                n_udp += 1
        lines.append(f"   · 监听 {n_listen} · 已建 TCP {n_tcp} · UDP {n_udp}（ss -tunlp）")
    # TCP 拥塞算法
    avail = "/proc/sys/net/ipv4/tcp_available_congestion_control"
    cur = "/proc/sys/net/ipv4/tcp_congestion_control"
    if os.path.exists(avail) and os.path.exists(cur):
        try:
            with open(avail, encoding="utf-8") as f:
                a = f.read().strip()
            with open(cur, encoding="utf-8") as f:
                c = f.read().strip()
            lines.append(f"   · 拥塞算法：当前={c} 可用=[{a}]（BBR 见 RFC 9002 附录；bbr 在可用列表中即可启）")
        except OSError:
            pass
    # 连接跟踪
    mc = "/proc/sys/net/netfilter/nf_conntrack_count"
    mx = "/proc/sys/net/netfilter/nf_conntrack_max"
    if os.path.exists(mc) and os.path.exists(mx):
        try:
            with open(mc, encoding="utf-8") as f:
                cnt = f.read().strip()
            with open(mx, encoding="utf-8") as f:
                lim = f.read().strip()
            lines.append(f"   · nf_conntrack：{cnt}/{lim}（nat/防火墙依赖；满则丢新连接）")
        except OSError:
            pass
    else:
        lines.append("   · 未加载 nf_conntrack（本机可能未用 NAT/状态防火墙）")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# L5 会话层                                                                     #
# --------------------------------------------------------------------------- #
def layer5_session() -> Tuple[bool, str]:
    """会话层：保活 sysctl/已建连接/隧道（VPN/WireGuard，只读）。"""
    lines = ["L5 会话层（sysctl/tunnel，只读）："]
    ka = "/proc/sys/net/ipv4/tcp_keepalive_time"
    if os.path.exists(ka):
        try:
            with open(ka, encoding="utf-8") as f:
                t = f.read().strip()
            lines.append(f"   · tcp_keepalive_time={t}s（会话保活探测起点；RFC 1122 §4.2.3.6）")
        except OSError:
            pass
    else:
        lines.append("   · tcp_keepalive_time 不可读（非 Linux 或 /proc 受限）")
    # 隧道
    tunnels = []
    if shutil.which("wg") or os.path.exists("/proc/net/dev"):
        # WireGuard 接口特征：wg 命令或 /sys/class/net/wg*
        wg_if = [i for i in _list_ifaces() if i.startswith("wg")]
        if wg_if:
            tunnels.append("WireGuard(" + ",".join(wg_if) + ")")
    if shutil.which("ip"):
        rc, out = common.run("ip -br link show type vti 2>/dev/null")
        if rc == 0 and out.strip():
            tunnels.append("IPsec-VTI")
    lines.append(f"   · 隧道/加密通道：{', '.join(tunnels) if tunnels else '未发现（WireGuard/IPsec）'}")
    lines.append("   · 会话保持属应用层职责（HTTP cookie / gRPC / DB 连接池）")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# L6 表示层                                                                     #
# --------------------------------------------------------------------------- #
def layer6_presentation() -> Tuple[bool, str]:
    """表示层：TLS 密码套件/DoT·DoH 解析器/证书（openssl/resolv，只读）。"""
    lines = ["L6 表示层（TLS/DNS 安全，只读）："]
    if shutil.which("openssl"):
        rc, out = common.run("openssl ciphers -v 'ALL:@SECLEVEL=0' 2>/dev/null")
        if rc == 0 and out.strip():
            n = len([l for l in out.splitlines() if l.strip()])
            lines.append(f"   · 本机 OpenSSL 可用密码套件 {n} 个（openssl ciphers）")
            # TLS 1.3 支持
            rc2, v = common.run("openssl ciphers -v -s 'TLSv1.3' 2>/dev/null")
            if rc2 == 0 and v.strip():
                lines.append("   · 支持 TLS 1.3（RFC 8446）——首选；老站点 TLS1.0/1.1 应禁用")
        else:
            lines.append("   · openssl ciphers 无输出")
    else:
        lines.append("   · 未安装 openssl，跳过密码套件检视")
    # DoT/DoH 解析器配置
    dot_doh = []
    resolv = "/etc/resolv.conf"
    if os.path.exists(resolv):
        try:
            with open(resolv, encoding="utf-8") as f:
                txt = f.read()
            nameservers = [l.split()[1] for l in txt.splitlines()
                           if l.strip().startswith("nameserver")]
            lines.append(f"   · /etc/resolv.conf 名称服务器：{', '.join(nameservers) if nameservers else '无'}")
            # 127.0.0.53 通常是 systemd-resolved（支持 DoT/DoH 视配置）
            if any(ns.startswith("127.0.0.53") for ns in nameservers):
                dot_doh.append("systemd-resolved(本地 stub)")
        except OSError:
            pass
    if shutil.which("resolvectl"):
        dot_doh.append("resolvectl 可用(可查 per-link DNS over TLS)")
    lines.append(f"   · 加密 DNS：{', '.join(dot_doh) if dot_doh else '未检测到 DoT/DoH 组件（RFC 7858/8484）'}")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# L7 应用层                                                                     #
# --------------------------------------------------------------------------- #
def _safe_url(url: str) -> bool:
    return url.startswith("http://") or url.startswith("https://")


def dns_resolve(host: str = "example.com", timeout: float = 5.0) -> Tuple[bool, str]:
    """DNS 解析（只读）：返回 (成功, 首个 A/AAAA)。不发送任何数据，只问解析器。"""
    try:
        infos = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        addrs = sorted({i[4][0] for i in infos})
        if addrs:
            return True, f"解析 {host} → {', '.join(addrs[:4])}"
        return False, f"解析 {host} 无结果"
    except (socket.gaierror, OSError) as e:
        return False, f"解析 {host} 失败：{e}"


def probe_http(url: str, timeout: float = 6.0) -> Tuple[bool, str]:
    """可达性探测（只读、仅 http/https、短超时）。默认不对任意外网调用——由 CLI 显式触发。"""
    if not _safe_url(url):
        return False, "仅支持 http:// 或 https://（红线：不探其他协议）"
    try:
        req = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "sysweeper-osi-probe/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return True, f"{url} → HTTP {r.status} ({r.headers.get('Content-Type', '?')})"
    except urllib.error.HTTPError as e:
        return True, f"{url} → HTTP {e.code}（可达，业务状态码非 2xx）"
    except Exception as e:  # noqa: BLE001 - 只读探测，异常即不可达
        return False, f"{url} 探测失败：{type(e).__name__}: {e}"


def layer7_application() -> Tuple[bool, str]:
    """应用层：DNS 解析器可用性 + 本地回环 HTTP 自检（只读，不连校外网）。"""
    lines = ["L7 应用层（DNS/本地可达性，只读）："]
    ok, msg = dns_resolve("localhost", timeout=2.0)
    lines.append(f"   · 本地解析：{msg}")
    ok2, msg2 = dns_resolve("example.com", timeout=5.0)
    lines.append(f"   · 公网 DNS：{'成功' if ok2 else '失败'} —— {msg2}")
    # 本地回环 HTTP 服务自检（不触外网）
    if shutil.which("ss"):
        rc, ss = common.run("ss -tlnp 2>/dev/null")
        if rc == 0:
            ports = set()
            for l in ss.splitlines():
                if "127.0.0.1:" in l or "[::1]:" in l:
                    # 取端口
                    p = l.split(":")[-1].split()[0]
                    if p.isdigit():
                        ports.add(p)
            if ports:
                lines.append(f"   · 本地回环监听端口：{', '.join(sorted(ports)[:10])}（可 curl 127.0.0.1:<port> 自检）")
    lines.append("   · 要探外网可达性用 `osi probe --url <http(s)>`（显式、可审计、不默认开）")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 聚合报告                                                                      #
# --------------------------------------------------------------------------- #
def _layer_call(n: int):
    return {
        1: layer1_physical, 2: layer2_datalink, 3: layer3_network,
        4: layer4_transport, 5: layer5_session, 6: layer6_presentation,
        7: layer7_application,
    }[n]


def osi_report() -> Tuple[bool, str]:
    """OSI 七层整体只读诊断。返回 (ok, 文本)。ok 恒为 True（这是一份报告，不是开关）。"""
    blocks = ["OSI 七层网络诊断（ISO/IEC 7498-1 / ITU-T X.200，全部只读）",
              "════════════════════════════════════════════"]
    for d in LAYER_DEFS:
        ok, msg = _layer_call(d["n"])()
        head = f"【L{d['n']} {d['name']} / {d['en']} · PDU={d['pdu']}】"
        blocks.append(head)
        blocks.append(msg)
        blocks.append(f"   参照：{d['ref']}")
    blocks.append("════════════════════════════════════════════")
    blocks.append("说明：本报告只读——不改地址/路由/防火墙，不连校外网做写操作。"
                  "要探外网用 `osi probe --url <http(s)>`。")
    return True, "\n".join(blocks)


def layer_report(n: int) -> Tuple[bool, str]:
    """单层报告（CLI `osi layer N` 用）。n 取 1–7。"""
    if n not in range(1, 8):
        return False, f"层数 n 必须 1–7，收到 {n}"
    d = LAYER_DEFS[n - 1]
    ok, msg = _layer_call(n)()
    return ok, f"【L{d['n']} {d['name']} / {d['en']}】\n{msg}\n   参照：{d['ref']}"


def capabilities_report() -> Tuple[bool, str]:
    """能力自检（只读）：本机每个 OSI 层是否可诊断 + 红线声明。"""
    lines = ["OSI 诊断能力自检（只读）："]
    for d in LAYER_DEFS:
        ok, msg = _layer_call(d["n"])()
        lines.append(f"   · L{d['n']} {d['name']:<6} {'可诊断' if ok else '跳过'}  —— {d['ref']}")
    lines.append("红线：仅读 /sys/class/net、ip/ss/ethtool/openssl 只读项、DNS 解析、"
                 "显式 http(s) 探测；不写配置、不 reload 防火墙、不连校外网做写。")
    return True, "\n".join(lines)
