"""DNS 解析健康度只读诊断（聚焦，不与 network.nm_resolved 重复）。

network.nm_resolved 负责「连接管理与 resolved 配置」；本模块聚焦「解析链路本身是否健康」：
nameserver 来源、systemd-resolved stub 监听、一次良性解析的延迟。

基于 python-dnspython 的视角（Arch 打包元数据）：DNS 是诊断链路的第一跳，
任何网络问题常先卡在名字解析。本模块只读，解析探测默认关闭（零出网）。

红线：不写 /etc/resolv.conf、不重启 resolved、不改 DNS、不连校外网做写操作；
      解析探测仅在显式传入 query=True（CLI ``--query``）时发一次良性 A 查询
      （getaddrinfo example.com），不修改任何状态；默认不发起任何解析请求。
"""
import time
import socket
from . import common

_DEFAULT_TEST = "example.com"
_DEF = "（未知）"


def _resolv_conf() -> tuple:
    rc, out = common.run("cat /etc/resolv.conf 2>/dev/null", timeout=5)
    if rc != 0:
        return (False, ("", False, ""))
    nameservers = [l.split()[1] for l in out.splitlines()
                   if l.strip().startswith("nameserver")]
    generated = any(k in out.lower() for k in ("systemd-resolved", "resolvectl", "# generated"))
    return (True, (nameservers, generated, out.strip()))


def _resolved_stub() -> str:
    rc, out = common.run("resolvectl status 2>/dev/null", timeout=8)
    if rc == 0 and out.strip():
        return "systemd-resolved 运行中（resolvectl 可用）"
    rc, out = common.run("ss -lun 2>/dev/null | grep -q 127.0.0.53 && echo yes", timeout=5)
    if rc == 0 and "yes" in out:
        return "疑似 systemd-resolved stub 127.0.0.53:53 监听"
    return "未检测到 systemd-resolved"


def _query_latency(host: str = _DEFAULT_TEST) -> tuple:
    """做一次良性 A 解析，测往返延迟（只读，不改状态）。"""
    t0 = time.monotonic()
    try:
        socket.getaddrinfo(host, None)
        dt = (time.monotonic() - t0) * 1000.0
        return (True, f"{host} 解析成功，约 {dt:.0f} ms")
    except Exception as e:  # noqa: BLE001
        return (False, f"{host} 解析失败：{e}")


def capabilities_report() -> tuple:
    lines = [
        "DNS 解析健康度诊断 · 能力自检",
        "可诊断维度：",
        "  1. /etc/resolv.conf 的 nameserver 来源（systemd-resolved 生成？）",
        "  2. systemd-resolved stub 127.0.0.53:53 监听",
        "  3. 一次良性解析（getaddrinfo）的延迟与健康度",
        "红线：不写 resolv.conf、不重启 resolved、不改 DNS；解析探测只读不改状态。",
    ]
    return (True, "\n".join(lines))


def dnshealth_report(query: bool = False) -> tuple:
    lines = []
    lines.append("==== DNS 解析健康度只读诊断 ====")
    ok, (nameservers, generated, _raw) = _resolv_conf()
    if ok:
        lines.append(f"[nameserver] {', '.join(nameservers) if nameservers else '（无）'}")
        lines.append(f"[来源] {'由 systemd-resolved 生成' if generated else '静态/其他'}")
    else:
        lines.append("[nameserver] 读取失败")
    lines.append(f"[resolved] {_resolved_stub()}")
    if query:
        okq, msg = _query_latency()
        lines.append(f"[解析探测] [{'OK' if okq else '失败'}] {msg}")
    else:
        lines.append("[解析探测] 跳过（默认不探测；--query 开启一次良性 A 查询）")
    lines.append("")
    lines.append("提示（基于 python-dnspython 视角）：名字解析是网络诊断第一跳；")
    lines.append("resolved stub 127.0.0.53 与 /etc/resolv.conf 不一致是常见的「能 ping IP 不能开网页」根因。")
    return (True, "\n".join(lines))
