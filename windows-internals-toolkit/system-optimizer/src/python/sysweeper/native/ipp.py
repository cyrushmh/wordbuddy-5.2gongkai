"""IPP 打印协议发现（ipp）：把「ipp 协议支持」落为只读子系统。

只读项：
  - CUPS：lpstat -v 列已配置打印机队列、/etc/cups 是否就绪（只读，绝不改打印队列）
  - Avahi mDNS：avahi-browse _ipp._tcp 发现网内 IPP 打印机（只读广播，绝不注册/发布）
  - 本地 Web：localhost:631（CUPS 管理页）是否可达（只读探一次，绝不连控制端口写）
  - 协议层面：IPP/IPP Everywhere（RFC 8010/8011）只读说明

红线：只读发现 ≠ 授权施工——lpadmin 加打印机、改 CUPS 配置、发布 mDNS 服务一律只给指引。
"""

from __future__ import annotations

import shutil
import subprocess


PROBES = (
    ("cups_report", "CUPS 打印队列（lpstat）"),
    ("mdns_report", "Avahi mDNS 发现（_ipp._tcp）"),
    ("localweb_report", "CUPS 管理页 localhost:631"),
)

RFC = ("[国际] RFC 8010（IPP 编码）/ RFC 8011（IPP 模型与语义）/ IPP Everywhere（PWG 5100.14）",
       "[国际] PWG 标准打印（AirPrint / IPP-over-USB 同源思路）")


def cups_report() -> tuple:
    if shutil.which("lpstat") is None:
        return False, "未安装 CUPS（lpstat 不可用）；如本机不接打印机则属正常"
    try:
        out = subprocess.run(["lpstat", "-v"], capture_output=True, text=True, timeout=8).stdout
    except (OSError, subprocess.SubprocessError):
        return False, "lpstat -v 调用失败（只读探针跳过）"
    devs = [l for l in out.splitlines() if l.startswith("device for")]
    if not devs:
        return False, "CUPS 已安装但未配置任何打印机队列"
    return True, "CUPS 打印队列（只读）:\n" + "\n".join(f"   · {d}" for d in devs)


def mdns_report() -> tuple:
    if shutil.which("avahi-browse") is None:
        return False, "未安装 avahi-browse；网内 mDNS 打印机发现不可用（属正常）"
    try:
        out = subprocess.run(["avahi-browse", "-rt", "_ipp._tcp"], capture_output=True,
                             text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return False, "avahi-browse 调用失败（只读探针跳过）"
    printers = [l for l in out.splitlines() if "._ipp._tcp" in l]
    if not printers:
        return False, "网内未发现 IPP(mDNS) 打印机"
    return True, "网内 IPP 打印机（mDNS 只读发现）:\n" + "\n".join(f"   · {p}" for p in printers)


def localweb_report() -> tuple:
    import socket
    try:
        with socket.create_connection(("127.0.0.1", 631), timeout=2):
            return True, "CUPS 管理页 localhost:631 可达（只读探一次，绝不连控制端口写）"
    except OSError:
        return False, "localhost:631 不可达（CUPS Web 未启用或本机不接打印机）"


def environment_report() -> list:
    lines = ["IPP 打印协议发现（ipp）· 本机只读探测："]
    for fn, lab in PROBES:
        ok, msg = getattr(__import__("sys").modules[__name__], fn)()
        lines.append(f"   · {lab}: {'✓ 可用' if ok else '✗ 不适用'}")
        if isinstance(msg, str) and msg.strip():
            lines.append("       " + msg.replace("\n", "\n       "))
    return lines


def ipp_report(env_tags: list | None = None, readings: dict | None = None) -> tuple:
    lines = ["== IPP 打印协议发现报告（ipp：CUPS / mDNS / 本地管理页，只读不写）=="]
    lines.append(f"维度标签: {sorted(set(env_tags or [])) or '未声明（默认基线）'}")
    lines.append("")
    lines.append("[① CUPS 队列]")
    ok, msg = cups_report()
    for sub in (msg.splitlines() if isinstance(msg, str) else [msg]):
        lines.append("   " + sub)
    lines.append("")
    lines.append("[② mDNS 发现]")
    ok, msg = mdns_report()
    for sub in (msg.splitlines() if isinstance(msg, str) else [msg]):
        lines.append("   " + sub)
    lines.append("")
    lines.append("[③ 本地管理页]")
    ok, msg = localweb_report()
    lines.append(f"   · {'✓' if ok else '✗'} {msg}")
    lines.append("")
    lines.append("[④ 协议标准]")
    for r in RFC:
        lines.append(f"   · {r}")
    lines.append("")
    lines.append("安全不变量：ipp 只读发现打印设备；lpadmin 加打印机 / 改 CUPS 配置 / 发布 mDNS 服务"
                 "一律只给指引；是否施工始终由用户在系统设置或 CUPS 管理页确认。")
    return True, "\n".join(lines)


def guide_add_printer() -> tuple:
    lines = [
        "添加 IPP 打印机指引（lpadmin，不代执行）:",
        "   1. 先经 mDNS 或 CUPS Web（localhost:631）拿到打印机 URI（ipp://... 或 ippusb://...）",
        "   2. lpadmin -p <队列名> -E -v <URI> -m everywhere（IPP Everywhere 用驱动无关模型）",
        "   3. 绝不连控制端口写配置；敏感打印机请走系统设置图形界面确认",
    ]
    return True, "\n".join(lines)


TUNES = (
    ("guide_add_printer", "添加 IPP 打印机（规范指引，不代执行）"),
)


def ipp_tune_list() -> list:
    return [f"· {fn}() — {desc}" for fn, desc in TUNES]
