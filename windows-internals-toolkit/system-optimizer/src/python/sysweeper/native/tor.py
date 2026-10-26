"""Tor（The Onion Router）匿名/隐私网络只读诊断。

Tor 是覆盖网络（overlay），在应用层用洋葱路由把「谁在连什么」拆开——流量经多跳中继，
每跳只知前后一跳，出口节点才看到明文目的。本模块只做只读核验：

- tor 是否安装、版本（tor --version）
- 守护进程是否在跑（systemd active / 进程存在）
- torrc 关键配置：SOCKS 端口、控制端口、桥接、可插拔传输、中继/出口角色
- 可插拔传输二进制是否就位（obfs4proxy / snowflake / meek / lyrebird）
- 数据目录存在性（/var/lib/tor、~/.tor）

红线：不启动/停止 tor、不改 torrc、不连控制端口下发写命令、不连校外网做写操作；
      只读本地文件（torrc、数据目录、进程表）与版本号。torrc 中的密钥/密码类敏感项
      只报「是否存在」，绝不打印明文。
"""
import os
import re
import shutil
from . import common

# torrc 候选路径（按常见打包/分布位置）
TORRC_PATHS = [
    "/etc/tor/torrc",
    "/usr/local/etc/tor/torrc",
    "/run/tor/torrc",
]
DATA_DIRS = ["/var/lib/tor", "/run/tor", os.path.expanduser("~/.tor")]

# 敏感键：只报存在，不打印明文（HashedControlPassword / 私钥 / HS 目录等）
_SENSITIVE = ("HashedControlPassword", "ControlPassword", "CookieAuthFile",
              "HiddenServiceDir", "ClientOnionAuthDir", "HiddenServiceAuthorizedClient")

# 可插拔传输二进制（受审查网络靠它绕过封锁）
_PT_BINS = {
    "obfs4proxy": ("/usr/bin/obfs4proxy", "/usr/libexec/obfs4proxy"),
    "obfsproxy": ("/usr/bin/obfsproxy",),
    "meek-client": ("/usr/bin/meek-client",),
    "snowflake-client": ("/usr/bin/snowflake-client",),
    "lyrebird": ("/usr/bin/lyrebird",),
}


def _tor_binary() -> tuple:
    """返回 (found, version_str)。"""
    binpath = shutil.which("tor")
    if not binpath:
        for p in ("/usr/sbin/tor", "/usr/bin/tor"):
            if os.path.exists(p):
                binpath = p
                break
    if not binpath:
        return (False, "")
    rc, out = common.run(f'"{binpath}" --version', timeout=10)
    if rc == 0:
        m = re.search(r"Tor version (\S+)", out)
        return (True, m.group(1) if m else "（版本未知）")
    return (True, "（版本未知）")


def _running() -> str:
    rc, out = common.run("systemctl is-active tor 2>/dev/null", timeout=5)
    if rc == 0 and "active" in out:
        return "运行中（systemd active）"
    rc, out = common.run("pgrep -x tor 2>/dev/null", timeout=5)
    if rc == 0 and out.strip():
        return "运行中（tor 守护进程存在）"
    rc, out = common.run("pgrep -f 'tor' 2>/dev/null", timeout=5)
    if rc == 0 and out.strip():
        return "疑似运行（tor 相关进程，含浏览器/daemon）"
    return "未运行"


def _torrc_report() -> dict:
    """读第一个存在的 torrc，抽出只读可见的关键项（敏感键只报存在）。"""
    info = {"path": "", "socks": [], "control": [], "bridge": False,
            "pt": [], "relay": False, "exit": False, "sensitive": []}
    for p in TORRC_PATHS:
        if os.path.exists(p):
            info["path"] = p
            try:
                text = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                return info
            for line in text.splitlines():
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                low = s.lower()
                if low.startswith("socksport"):
                    info["socks"].append(s.split(None, 1)[-1])
                elif low.startswith("controlport"):
                    info["control"].append(s.split(None, 1)[-1])
                elif low.startswith("bridge"):
                    info["bridge"] = True
                elif low.startswith("clienttransportplugin"):
                    parts = s.split()
                    info["pt"].append(parts[1] if len(parts) > 1 else "（未指定）")
                elif low.startswith("orport") or low.startswith("dirport"):
                    info["relay"] = True
                elif low.startswith("exitpolicy") or low.startswith("exitrelay"):
                    info["exit"] = True
                for k in _SENSITIVE:
                    if low.startswith(k.lower()):
                        info["sensitive"].append(k)
                        break
            break
    return info


def _pt_binaries() -> list:
    found = []
    for b, paths in _PT_BINS.items():
        if shutil.which(b) or any(os.path.exists(p) for p in paths):
            found.append(b)
    return found


def capabilities_report() -> tuple:
    lines = [
        "Tor 匿名/隐私网络诊断 · 能力自检",
        "可诊断维度：",
        "  1. tor 是否安装 + 版本（tor --version）",
        "  2. 守护进程状态（systemd active / 进程存在）",
        "  3. torrc 关键配置：SOCKS/控制端口、桥接、可插拔传输、中继/出口",
        "  4. 可插拔传输二进制（obfs4proxy/snowflake/meek/lyrebird）是否就位",
        "  5. 数据目录存在性（/var/lib/tor、~/.tor）",
        "红线：不启动/停止 tor、不改 torrc、不连控制端口、不连校外网做写操作；",
        "      torrc 中密钥/密码类敏感项只报存在、不打印明文。",
    ]
    return (True, "\n".join(lines))


def tor_report() -> tuple:
    lines = ["==== Tor（洋葱路由）匿名/隐私网络只读诊断 ===="]
    found, ver = _tor_binary()
    lines.append(f"[tor] {'已安装（' + ver + '）' if found else '未安装'}")
    lines.append(f"[运行状态] {_running()}")
    info = _torrc_report()
    if info["path"]:
        lines.append(f"[torrc] {info['path']}")
        lines.append(f"[SOCKS 端口] {', '.join(info['socks']) if info['socks'] else '默认 9050（客户端）/ 9150（Tor 浏览器）'}")
        lines.append(f"[控制端口] {', '.join(info['control']) if info['control'] else '未显式配置（默认 9051）'}")
        lines.append(f"[桥接] {'是（含 Bridge 行）' if info['bridge'] else '否'}")
        lines.append(f"[可插拔传输] {', '.join(info['pt']) if info['pt'] else '未配置'}")
        lines.append(f"[角色] {'中继' if info['relay'] else '纯客户端'} / {'出口' if info['exit'] else '非出口'}")
        if info["sensitive"]:
            lines.append(f"[敏感配置] 存在（不打印明文）：{', '.join(info['sensitive'])}")
    else:
        lines.append("[torrc] 未找到（tor 可能以默认配置运行，或仅作为浏览器内置）")
    pts = _pt_binaries()
    lines.append(f"[可插拔传输二进制] {', '.join(pts) if pts else '未安装（obfs4/snowflake 等；受审查网络需它）'}")
    for d in DATA_DIRS:
        if os.path.exists(d):
            lines.append(f"[数据目录] 存在 {d}")
            break
    else:
        lines.append("[数据目录] 未找到（/var/lib/tor、~/.tor）")
    lines.append("")
    lines.append("提示：Tor 在应用层做洋葱加密，流量经≥3 跳中继才到出口节点；")
    lines.append("SOCKS 9050/9150 是本地代理入口，控制端口 9051/9151 可下发写命令（本工具不连）。")
    lines.append("受审查网络靠 Bridge + 可插拔传输（obfs4/snowflake）绕过封锁；做中继/出口节点有")
    lines.append("带宽与法务责任，出口节点看得到明文目的，务必读懂 Relay 文档再决定。")
    return (True, "\n".join(lines))
