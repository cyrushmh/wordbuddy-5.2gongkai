"""虚拟根 DNS 与多 CDN（vdns）：把「虚拟根 dns + 不同 cdn 选择/健康」落为只读子系统。

只读项：
  - 虚拟根 DNS：读 /etc/resolv.conf 的 nameserver 与 search；识别 DoH/DoT（systemd-resolved
    DNS-over-TLS、stubby、cloudflared）是否启用（只读配置/进程，绝不改）
  - 多 CDN：读 /etc/hosts 的 CDN 条目与常见 CDN 域名（cloudfront/fastly/akamai/alicdn…），
    给「按地域/健康选 CDN」的只读观察与指引
  - 健康：只读一次良性解析延迟（dig/nslookup 解析示例域名），绝不持续探测、绝不改 DNS

红线：只读观测 ≠ 授权施工——改 resolv.conf、切 DoH/DoT、改 hosts 一律只给指引。
"""

from __future__ import annotations

import os
import shutil
import subprocess


PROBES = (
    ("rootdns_report", "虚拟根 DNS（resolv.conf / DoH-DoT）"),
    ("cdn_report", "多 CDN 选择与健康"),
    ("health_report", "DNS 解析健康（一次良性探测）"),
)

# 常见 CDN 域名（只读观察用，不存密钥）
KNOWN_CDNS = ("cloudfront.net", "fastly.net", "akamai.net", "akamaihd.net",
              "alicdn.com", "lzd.net", "gslb.com", "edgekey.net", "cloudflare.net")


def _read(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return None


def rootdns_report() -> tuple:
    txt = _read("/etc/resolv.conf")
    if not txt:
        return False, "未检测到 /etc/resolv.conf（可能由 systemd-resolved Stub 管理）；属正常"
    ns = [l.split()[1] for l in txt.splitlines() if l.strip().startswith("nameserver")]
    search = [l.split("search", 1)[1].strip() for l in txt.splitlines() if l.strip().startswith("search")]
    dot = stub = False
    if shutil.which("resolvectl") and os.path.isdir("/etc/systemd/resolved.conf.d"):
        dot = True  # 存在 resolved 配置目录，提示可走 DoT（只读，不判是否启用）
    if shutil.which("stubby") or shutil.which("cloudflared"):
        stub = True
    lines = [f"虚拟根 DNS（只读）: nameserver={ns or '无'}; search={search or '无'}"]
    lines.append(f"   · DoH/DoT: systemd-resolved 配置目录{'存在' if dot else '未见'}、"
                 f"stubby/cloudflared={'可用' if stub else '未见'}")
    return True, "\n".join(lines)


def cdn_report() -> tuple:
    txt = _read("/etc/hosts") or ""
    hit = [h for h in KNOWN_CDNS if h in txt]
    lines = ["多 CDN 选择（只读观察）:"]
    if hit:
        lines.append(f"   · /etc/hosts 命中的 CDN 域名: {', '.join(hit)}（说明有就近/CDN 覆写）")
    else:
        lines.append("   · /etc/hosts 未命中常见 CDN 域名（走默认解析）")
    lines.append("   · 常见 CDN: " + ", ".join(KNOWN_CDNS))
    return True, "\n".join(lines)


def health_report() -> tuple:
    probe = "example.com"
    if shutil.which("dig"):
        try:
            out = subprocess.run(["dig", "+short", "+time=3", probe], capture_output=True,
                                 text=True, timeout=6).stdout.strip()
            if out:
                return True, f"DNS 解析健康（dig {probe}→{out.splitlines()[0]}）"
        except (OSError, subprocess.SubprocessError):
            pass
    if shutil.which("nslookup"):
        try:
            out = subprocess.run(["nslookup", probe], capture_output=True, text=True,
                                 timeout=6).stdout
            if "Address" in out:
                return True, f"DNS 解析健康（nslookup {probe} 成功）"
        except (OSError, subprocess.SubprocessError):
            pass
    return False, "无 dig/nslookup，未做良性解析探测（属正常，不影响其它只读项）"


def environment_report() -> list:
    lines = ["虚拟根 DNS 与多 CDN（vdns）· 本机只读探测："]
    for fn, lab in PROBES:
        ok, msg = getattr(__import__("sys").modules[__name__], fn)()
        lines.append(f"   · {lab}: {'✓ 可用' if ok else '✗ 不适用'}")
        if isinstance(msg, str) and msg.strip():
            lines.append("       " + msg.replace("\n", "\n       "))
    return lines


def vdns_report(env_tags: list | None = None, readings: dict | None = None) -> tuple:
    lines = ["== 虚拟根 DNS 与多 CDN 报告（vdns：根 DNS / DoH-DoT / 多 CDN 选择·健康，只读不写）=="]
    lines.append(f"维度标签: {sorted(set(env_tags or [])) or '未声明（默认基线）'}")
    lines.append("")
    lines.append("[① 虚拟根 DNS]")
    ok, msg = rootdns_report()
    for sub in msg.splitlines():
        lines.append("   " + sub)
    lines.append("")
    lines.append("[② 多 CDN 选择与健康]")
    ok, msg = cdn_report()
    for sub in msg.splitlines():
        lines.append("   " + sub)
    lines.append("")
    lines.append("[③ 解析健康（一次良性探测）]")
    ok, msg = health_report()
    lines.append(f"   · {'✓' if ok else '✗'} {msg}")
    lines.append("")
    lines.append("安全不变量：vdns 只读观测根 DNS 与 CDN；改 resolv.conf / 切 DoH-DoT / 改 hosts 一律只给"
                 "指引；是否施工始终由用户在网络管理或厂商工具确认。")
    return True, "\n".join(lines)


def guide_doh() -> tuple:
    lines = [
        "启用 DoT/DoH 指引（不代执行）:",
        "   1. systemd-resolved: 在 /etc/systemd/resolved.conf.d/ 写 DNSOverTLS=opportunistic + DNS=<DoT 服务>",
        "   2. 或装 stubby/cloudflared 作本地 DoT/DoH stub，resolv.conf 指向 127.0.0.1#53",
        "   3. 改 DNS 前先确认备用可达，避免把自己锁死在外网之外",
    ]
    return True, "\n".join(lines)


TUNES = (
    ("guide_doh", "启用 DoT/DoH（规范指引，不代执行）"),
)


def vdns_tune_list() -> list:
    return [f"· {fn}() — {desc}" for fn, desc in TUNES]
