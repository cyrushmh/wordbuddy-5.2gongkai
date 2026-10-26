"""OpenWrt 路由器系统原生接口（只读探针 + 文档引用）。

OpenWrt 是面向路由器/嵌入式设备的 Linux 发行版。本模块把它的核心子系统
**仅做只读探测与文档引用**：

- 固件/板型  : /etc/openwrt_release（DISTRIB_*）、/etc/os-release（ID=openwrt）、
              /tmp/sysinfo/{board_name,model}
- UCI 配置   : /etc/config/*（uci 文件格式，纯文本解析只读；可选 `uci show`）
- 包管理     : opkg（23.05 及更早）/ apk（24.10 起默认），仅读已装清单
- 网络       : /etc/config/network（UCI 解析）+ 可选 `ubus call network.interface dump`
- 服务/procd : 可选 `ubus call service list` / /etc/init.d/* status
- 构建系统   : ImageBuilder / SDK / feeds / 完整构建（仅文档引用，绝不调用 make）

设计原则（与全局一致）：纯标准库、零依赖、离线优先；所有函数返回 ``(ok, msg)``
元组；非 OpenWrt 环境优雅降级为「指引」（说明需在 OpenWrt 设备上运行）。
**绝不自动执行任何写操作**（opkg install / uci set / sysupgrade / make image 等均只给指引）。

引用标准（见 data/openwrt_docs.json）：
- UCI  : OpenWrt UCI 文档（guide-user/base-system/uci + techref/uci）
- opkg : OpenWrt opkg 文档（guide-user/additional-software/opkg）
- apk  : OpenWrt opkg→apk 迁移文档（guide-user/additional-software/opkg-to-apk-migration）
- procd/netifd/ubus/rpcd/LuCI/ImageBuilder/SDK/feeds/Buildroot：各自官方文档
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Dict, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# 文档层（data/openwrt_docs.json）                                              #
# --------------------------------------------------------------------------- #


def _load_docs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "openwrt_docs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:  # noqa: BLE001
        return {}


OWRT_DOCS = _load_docs()

OPENWRT_RELEASE = "/etc/openwrt_release"
OS_RELEASE = "/etc/os-release"
SYSINFO_DIR = "/tmp/sysinfo"
UCI_DIR = "/etc/config"

# 敏感配置项关键字（只报告「存在性」，绝不回显 secret 明文）
_SENSITIVE_KEYS = ("key", "password", "secret", "psk", "passphrase", "private_key",
                   "secret_key", "auth_key", "token")


def _read_text(path: str) -> Optional[str]:
    """读一个文本文件，失败/不存在返回 None（只读）。"""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def _which(cmd: str) -> Optional[str]:
    try:
        import shutil
        return shutil.which(cmd)
    except Exception:  # noqa: BLE001
        return None


def _run_ro(cmd: List[str], timeout: float = 10.0) -> Tuple[bool, str]:
    """只读地跑一条命令（用于 uci show / ubus call 等检视命令）。

    仅用于**只读**子命令；绝不传含 set/install/commit 的参数。返回 (ok, stdout)。
    """
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            return False, (r.stderr or r.stdout).strip()[-600:]
        return True, (r.stdout or "").strip()
    except Exception as e:  # noqa: BLE001
        return False, f"执行失败: {e}"


# --------------------------------------------------------------------------- #
# 探测：是否运行在 OpenWrt 上                                                   #
# --------------------------------------------------------------------------- #


def is_openwrt() -> Tuple[bool, Dict[str, str]]:
    """探测当前是否运行在 OpenWrt。只读读取 /etc/openwrt_release 与 /etc/os-release。

    返回 (ok, info)：ok=True 时 info 含 DISTRIB_RELEASE/DISTRIB_TARGET/
    DISTRIB_ARCH/DISTRIB_DESCRIPTION/board_name/model 等。
    """
    info: Dict[str, str] = {}
    rel = _read_text(OPENWRT_RELEASE)
    if rel:
        for line in rel.splitlines():
            m = re.match(r"^DISTRIB_(\w+)=['\"]?(.*?)['\"]?$", line.strip())
            if m:
                info[m.group(1)] = m.group(2)
    # /etc/os-release 也能识别（ID=openwrt）
    osr = _read_text(OS_RELEASE)
    if osr:
        for line in osr.splitlines():
            m = re.match(r"^([A-Z_]+)=['\"]?(.*?)['\"]?$", line.strip())
            if m and m.group(1) in ("ID", "VERSION_ID", "PRETTY_NAME"):
                info.setdefault(m.group(1), m.group(2))
    if info.get("ID") != "openwrt" and "RELEASE" not in info and "DESCRIPTION" not in info:
        return False, {}
    # 板型
    bn = _read_text(os.path.join(SYSINFO_DIR, "board_name"))
    model = _read_text(os.path.join(SYSINFO_DIR, "model"))
    if bn:
        info["board_name"] = bn.strip()
    if model:
        info["model"] = model.strip()
    return True, info


def firmware_info() -> Dict[str, str]:
    """只读固件信息（DISTRIB_* + 板型）；非 OpenWrt 返回空 dict。"""
    ok, info = is_openwrt()
    return info if ok else {}


# --------------------------------------------------------------------------- #
# UCI 解析（/etc/config/* 纯文本，只读）                                         #
# --------------------------------------------------------------------------- #


def parse_uci_file(path: str) -> List[dict]:
    """把单个 UCI 配置文件解析为节（section）列表（只读）。

    每节: {"type":..., "name":..., "options":{...}, "lists":{...}}。
    不修改任何文件；解析失败返回空列表。
    """
    text = _read_text(path)
    if text is None:
        return []
    sections: List[dict] = []
    cur: Optional[dict] = None
    try:
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r"^config\s+(\S+)(?:\s+['\"]?(\S+?)['\"]?)?$", line)
            if m:
                cur = {"type": m.group(1), "name": m.group(2) or "",
                       "options": {}, "lists": {}}
                sections.append(cur)
                continue
            m = re.match(r"^option\s+(\S+)\s+(.*)$", line)
            if m and cur is not None:
                val = m.group(2).strip().strip("'\"")
                cur["options"][m.group(1)] = val
                continue
            m = re.match(r"^list\s+(\S+)\s+(.*)$", line)
            if m and cur is not None:
                val = m.group(2).strip().strip("'\"")
                cur.setdefault("lists", {}).setdefault(m.group(1), []).append(val)
                continue
            # 其它（package/include/comment 续行）忽略
    except Exception:  # noqa: BLE001
        return sections
    return sections


def uci_audit() -> Tuple[bool, str]:
    """只读审计 UCI 配置：列出每个配置文件与其节数、接口、桥接、含密码/密钥的配置项。

    安全：仅展示**配置项存在性**（如「存在 option key」「存在 option password」），
    绝不回显 secret 的明文值。需 OpenWrt 环境；否则降级为指引。
    """
    ok, info = is_openwrt()
    if not ok:
        return False, ("当前不在 OpenWrt 环境（未发现 /etc/openwrt_release 或 "
                       "os-release ID=openwrt）。请在 OpenWrt 路由器上运行；"
                       "UCI 配置文件位于 /etc/config/*。")
    if not os.path.isdir(UCI_DIR):
        return False, f"未发现 {UCI_DIR}（非标准 OpenWrt 布局？）"
    lines = ["UCI 配置只读审计（仅展示项存在性，绝不回显 secret 明文）："]
    try:
        files = sorted(f for f in os.listdir(UCI_DIR)
                       if os.path.isfile(os.path.join(UCI_DIR, f)))
    except OSError as e:
        return False, f"读取 {UCI_DIR} 失败: {e}"
    # 敏感键名（只报告「存在」，不打印值）
    SENSITIVE = _SENSITIVE_KEYS
    for fn in files:
        secs = parse_uci_file(os.path.join(UCI_DIR, fn))
        if not secs:
            continue
        # 统计接口/桥接/含敏感项的节
        ifaces, bridges, sens = [], [], set()
        for s in secs:
            t = s["type"]
            if t in ("interface",) and s.get("name"):
                ifaces.append(s["name"])
            if s["options"].get("type") == "bridge" or "bridge" in s["options"].get("name", ""):
                bridges.append(s.get("name") or s["type"])
            for k in list(s["options"]) + list(s.get("lists", {})):
                if any(sk in k.lower() for sk in SENSITIVE):
                    sens.add(k)
        lines.append(f"  · {fn}: {len(secs)} 节"
                     + (f"  接口={', '.join(ifaces)}" if ifaces else "")
                     + (f"  桥接={', '.join(bridges)}" if bridges else ""))
        if sens:
            lines.append(f"      ⚠ 含敏感配置项（存在性，不打印值）: {', '.join(sorted(sens))}")
    lines.append("")
    lines.append("写配置请用 `uci set` + `uci commit`（本工具不自动执行任何 uci set）。")
    return True, "\n".join(lines)


def uci_dump() -> Tuple[bool, str]:
    """UCI 全量只读检视：优先 `uci show`（若存在），否则回退到文件解析摘要。"""
    if _which("uci"):
        ok, out = _run_ro(["uci", "show"])
        if ok:
            return True, "uci show（只读）：\n" + out
    ok, msg = uci_audit()
    return ok, ("（uci 命令不可用，使用文件解析）\n" + msg if ok else msg)


# --------------------------------------------------------------------------- #
# 包管理（opkg / apk）只读盘点                                                   #
# --------------------------------------------------------------------------- #


def package_manager() -> str:
    """返回当前 OpenWrt 的包管理器：'apk' / 'opkg' / ''（非 OpenWrt 或未知）。"""
    if _which("apk"):
        return "apk"
    if _which("opkg"):
        return "opkg"
    return ""


def list_installed() -> Tuple[bool, List[str]]:
    """只读盘点已装软件包。返回 (ok, [pkg, ...])。非 OpenWrt 返回 (False, [])。"""
    ok, _ = is_openwrt()
    if not ok:
        return False, []
    # 优先命令（只读）
    pm = package_manager()
    if pm == "apk" and _which("apk"):
        ok2, out = _run_ro(["apk", "info", "-e"])
        if ok2:
            return True, [l.split()[0] for l in out.splitlines() if l.strip()]
        # 回退解析状态文件
        return _parse_apk_db()
    if pm == "opkg" and _which("opkg"):
        ok2, out = _run_ro(["opkg", "list-installed"])
        if ok2:
            return True, [l.split()[0] for l in out.splitlines() if l.strip()]
        return _parse_opkg_status()
    # 无命令：直接解析状态文件
    return _parse_apk_db() if os.path.exists("/usr/lib/apk/db/installed") else _parse_opkg_status()


def _parse_opkg_status() -> Tuple[bool, List[str]]:
    text = _read_text("/usr/lib/opkg/status")
    if text is None:
        return False, []
    pkgs = []
    for blk in text.split("\n\n"):
        m = re.search(r"^Package:\s*(\S+)", blk, re.M)
        if m:
            pkgs.append(m.group(1))
    return True, pkgs


def _parse_apk_db() -> Tuple[bool, List[str]]:
    text = _read_text("/usr/lib/apk/db/installed")
    if text is None:
        return False, []
    pkgs = []
    for blk in text.split("\n\n"):
        m = re.search(r"^P:\s*(\S+)", blk, re.M)
        if m:
            pkgs.append(m.group(1))
    return True, pkgs


def package_report() -> Tuple[bool, str]:
    """已装软件包只读报告（opkg/apk 自适应）。"""
    ok, info = is_openwrt()
    if not ok:
        return False, ("当前不在 OpenWrt 环境。OpenWrt 包管理：23.05 用 opkg，"
                       "24.10 起默认 apk；已装清单分别位于 /usr/lib/opkg/status"
                       "与 /usr/lib/apk/db/installed。")
    pm = package_manager() or "(命令不可用，按状态文件解析)"
    ok2, pkgs = list_installed()
    if not ok2:
        return True, (
            f"包管理器: {pm}\n（未能读取已装清单；可在 OpenWrt 上用 "
            f"`{'apk info' if pm=='apk' else 'opkg list-installed'}` 查看）"
        )
    lines = [f"包管理器: {pm}", f"已装软件包: {len(pkgs)} 个（只读盘点）"]
    if pkgs:
        lines.append("  样例: " + ", ".join(pkgs[:20]) + (" …" if len(pkgs) > 20 else ""))
    lines.append("")
    lines.append("安装/升级为写操作（`opkg install` / `apk add`），本工具不自动执行。")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 网络（/etc/config/network 解析 + 可选 ubus）                                  #
# --------------------------------------------------------------------------- #


def network_report() -> Tuple[bool, str]:
    """网络接口只读报告：解析 /etc/config/network，可选 `ubus call network.interface dump`。"""
    ok, info = is_openwrt()
    if not ok:
        return False, ("当前不在 OpenWrt 环境。OpenWrt 网络配置位于 "
                       "/etc/config/network（UCI），运行时状态可经 ubus 读取。")
    path = os.path.join(UCI_DIR, "network")
    if not os.path.isfile(path):
        return False, f"未发现 {path}（非标准布局？）"
    secs = parse_uci_file(path)
    ifaces = [s for s in secs if s["type"] == "interface"]
    switches = [s for s in secs if s["type"] in ("switch", "switch_vlan")]
    lines = ["网络配置（/etc/config/network，只读解析）："]
    for s in ifaces:
        opts = s["options"]
        parts = [f"if={s.get('name') or '(匿名)'}"]
        if opts.get("proto"):
            parts.append(f"proto={opts['proto']}")
        if opts.get("ifname") or opts.get("device"):
            parts.append(f"dev={opts.get('device') or opts.get('ifname')}")
        if opts.get("type") == "bridge":
            parts.append("bridge")
        lines.append("  · " + "  ".join(parts))
    if switches:
        lines.append(f"  · 交换机/VLAN: {len(switches)} 节")
    lines.append("")
    # 运行时状态（可选，只读）
    if _which("ubus"):
        ok2, out = _run_ro(["ubus", "call", "network.interface", "dump"])
        if ok2 and out:
            lines.append("-- 运行时状态（ubus，只读）--")
            lines.append(out[:1200])
    lines.append("改接口为写操作（uci set + commit / 或 ubus 写方法），本工具不自动执行。")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 服务 / procd 只读                                                             #
# --------------------------------------------------------------------------- #


def services_report() -> Tuple[bool, str]:
    """服务状态只读报告（procd）：优先 `ubus call service list`，回退 /etc/init.d 列举。"""
    ok, info = is_openwrt()
    if not ok:
        return False, "当前不在 OpenWrt 环境；服务脚本位于 /etc/init.d/*。"
    lines = ["服务（procd，只读）："]
    if _which("ubus"):
        ok2, out = _run_ro(["ubus", "call", "service", "list"])
        if ok2 and out:
            try:
                svcs = list(json.loads(out).keys())
                lines.append(f"  运行中服务: {len(svcs)} 个")
                lines.append("  样例: " + ", ".join(svcs[:20]) + (" …" if len(svcs) > 20 else ""))
                lines.append("（完整 JSON 见 `ubus call service list`）")
                return True, "\n".join(lines)
            except Exception:  # noqa: BLE001
                pass
    # 回退：列举 /etc/init.d 脚本
    d = "/etc/init.d"
    try:
        names = sorted(os.listdir(d))
    except OSError:
        names = []
    if names:
        lines.append(f"  /etc/init.d 脚本: {len(names)} 个")
        lines.append("  样例: " + ", ".join(names[:20]) + (" …" if len(names) > 20 else ""))
    else:
        lines.append("  （未发现 /etc/init.d 脚本）")
    return True, "\n".join(lines)


def board_report() -> Tuple[bool, str]:
    """板型与固件只读报告。"""
    ok, info = is_openwrt()
    if not ok:
        return False, ("当前不在 OpenWrt 环境。OpenWrt 板型信息位于 "
                       "/tmp/sysinfo/board_name、/tmp/sysinfo/model，"
                       "固件信息位于 /etc/openwrt_release。")
    lines = ["OpenWrt 板型与固件（只读）："]
    for k in ("board_name", "model", "RELEASE", "TARGET", "SUBTARGET",
              "ARCH", "DESCRIPTION", "ID", "VERSION_ID", "PRETTY_NAME"):
        v = info.get(k)
        if v:
            lines.append(f"  · {k}: {v}")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 构建系统（ImageBuilder / SDK / feeds）参考 —— 仅文档，绝不调用 make            #
# --------------------------------------------------------------------------- #


def build_report() -> Tuple[bool, str]:
    """OpenWrt 构建系统参考（ImageBuilder / SDK / feeds / 完整构建）。只读引用。"""
    try:
        lines = ["OpenWrt 构建系统（仅文档引用，本工具不调用 make / 不刷机）："]
        for key in ("imagebuilder", "sdk", "feeds", "buildroot"):
            d = OWRT_DOCS.get(key, {})
            if not d:
                continue
            lines.append(f"  · {d.get('name','')}")
            lines.append(f"      文档: {d.get('url','')}")
            lines.append(f"      接口: {'; '.join(d.get('interfaces', []) or [])}")
            lines.append(f"      说明: {d.get('summary','')}")
        lines.append("")
        lines.append("定制固件：ImageBuilder 最快（基于预编译根文件挑包）；SDK 用于交叉编译软件包；"
                     "完整 menuconfig 编译最灵活。三者均为写操作，本工具只给指引。")
        return True, "\n".join(lines)
    except Exception as e:  # noqa: BLE001
        return False, f"构建系统报告生成失败: {e}"


# --------------------------------------------------------------------------- #
# 防火墙 / 无线 / DHCP / 存储（只读）                                            #
# --------------------------------------------------------------------------- #


def _uci_opt(section: dict, key: str, default: str = "") -> str:
    """取某节的单个 option 值（不存在返回 default）。"""
    return str(section.get("options", {}).get(key, default) or default)


def _sensitive_in(secs: List[dict]) -> List[str]:
    """扫描若干节里出现的敏感配置项名（只返回键名，绝不返回值）。"""
    found = set()
    for s in secs:
        for k in list(s.get("options", {})) + list(s.get("lists", {})):
            if any(sk in k.lower() for sk in _SENSITIVE_KEYS):
                found.add(k)
    return sorted(found)


def firewall_report() -> Tuple[bool, str]:
    """防火墙只读报告：解析 /etc/config/firewall（zone/forwarding/rule/redirect）。"""
    ok, _info = is_openwrt()
    if not ok:
        return False, ("当前不在 OpenWrt 环境。OpenWrt 防火墙配置位于 "
                       "/etc/config/firewall（UCI），当前实现（firewall4/nftables）"
                       "状态可用 `fw4 print` 只读检视。")
    path = os.path.join(UCI_DIR, "firewall")
    if not os.path.isfile(path):
        return False, f"未发现 {path}（非标准布局？）"
    secs = parse_uci_file(path)
    zones = [s for s in secs if s["type"] == "zone"]
    fwd = [s for s in secs if s["type"] == "forwarding"]
    rules = [s for s in secs if s["type"] == "rule"]
    redir = [s for s in secs if s["type"] == "redirect"]
    lines = ["防火墙（/etc/config/firewall，只读解析）：",
             f"  区域(zone): {len(zones)}  转发(forwarding): {len(fwd)}  "
             f"规则(rule): {len(rules)}  重定向(redirect): {len(redir)}"]
    for z in zones:
        name = z.get("name") or "(匿名)"
        net = _uci_opt(z, "network", "-")
        extra = []
        if _uci_opt(z, "masq") in ("1", "true", "yes"):
            extra.append("masq")
        if _uci_opt(z, "input"):
            extra.append(f"input={_uci_opt(z, 'input')}")
        if _uci_opt(z, "output"):
            extra.append(f"output={_uci_opt(z, 'output')}")
        lines.append(f"    · zone {name}  network={net}"
                     + ("  " + " ".join(extra) if extra else ""))
    sens = _sensitive_in(secs)
    if sens:
        lines.append(f"    ⚠ 含敏感配置项（存在性，不打印值）: {', '.join(sens)}")
    if _which("fw4"):
        lines.append("  运行时：firewall4/nftables（`fw4 print` 只读检视）")
    elif _which("fw3"):
        lines.append("  运行时：firewall3/iptables（`fw3 print` 只读检视）")
    lines.append("改防火墙规则为写操作（uci set + commit + reload），本工具不自动执行。")
    return True, "\n".join(lines)


def wireless_report() -> Tuple[bool, str]:
    """无线只读报告：解析 /etc/config/wireless（radio/wifi-iface），绝不回显无线密码。"""
    ok, _info = is_openwrt()
    if not ok:
        return False, ("当前不在 OpenWrt 环境。OpenWrt 无线配置位于 "
                       "/etc/config/wireless（UCI），无线状态可用 `iw dev` / "
                       "`ubus call ... wireless status` 只读检视。")
    path = os.path.join(UCI_DIR, "wireless")
    if not os.path.isfile(path):
        return False, f"未发现 {path}（非标准布局？）"
    secs = parse_uci_file(path)
    radios = [s for s in secs if s["type"] == "wifi-device"]
    ifaces = [s for s in secs if s["type"] == "wifi-iface"]
    lines = ["无线（/etc/config/wireless，只读解析）：",
             f"  无线电(wifi-device): {len(radios)}  无线接口(wifi-iface): {len(ifaces)}"]
    for r in radios:
        name = r.get("name") or "(匿名)"
        band = _uci_opt(r, "band")
        ch = _uci_opt(r, "channel")
        disabled = _uci_opt(r, "disabled") in ("1", "true", "yes")
        lines.append(f"    · radio {name}  band={band or '-'}  channel={ch or '-'}"
                     + ("  [已禁用]" if disabled else ""))
    for i in ifaces:
        name = i.get("name") or "(匿名)"
        dev = _uci_opt(i, "device")
        mode = _uci_opt(i, "mode")
        enc = _uci_opt(i, "encryption")
        # SSID 属可公开信息，仅显示是否存在（此处只列接口，不打印 SSID/密钥）
        has_key = bool(_uci_opt(i, "key"))
        lines.append(f"    · iface {name}  dev={dev or '-'}  mode={mode or '-'}"
                     f"  encryption={enc or 'none'}"
                     + ("  🔑含密码(不显示)" if has_key else ""))
    sens = _sensitive_in(secs)
    if sens:
        lines.append(f"    ⚠ 含敏感配置项（存在性，不打印值）: {', '.join(sens)}")
    lines.append("改无线为写操作（uci set + commit + wifi reload），本工具不自动执行。")
    return True, "\n".join(lines)


def dhcp_report() -> Tuple[bool, str]:
    """DHCP/DNS 只读报告：解析 /etc/config/dhcp（dnsmasq/odhcpd，静态租约）。"""
    ok, _info = is_openwrt()
    if not ok:
        return False, ("当前不在 OpenWrt 环境。OpenWrt DHCP/DNS 配置位于 "
                       "/etc/config/dhcp（UCI dnsmasq/odhcpd）。")
    path = os.path.join(UCI_DIR, "dhcp")
    if not os.path.isfile(path):
        return False, f"未发现 {path}（非标准布局？）"
    secs = parse_uci_file(path)
    dnsmasq = [s for s in secs if s["type"] == "dnsmasq"]
    dhcp = [s for s in secs if s["type"] == "dhcp"]
    host = [s for s in secs if s["type"] == "host"]
    lines = ["DHCP/DNS（/etc/config/dhcp，只读解析）：",
             f"  dnsmasq 实例: {len(dnsmasq)}  DHCP 区段: {len(dhcp)}  静态租约(host): {len(host)}"]
    for d in dnsmasq:
        n = d.get("name") or "(默认)"
        upstream = len(d.get("lists", {}).get("server", []))
        lines.append(f"    · dnsmasq[{n}]  端口={_uci_opt(d, 'port') or '53'}  "
                     f"上游DNS={upstream}  域={_uci_opt(d, 'domain') or '(继承)'}")
    for h in dhcp:
        iface = _uci_opt(h, "interface", "(全局)")
        start = _uci_opt(h, "start")
        limit = _uci_opt(h, "limit")
        lines.append(f"    · dhcp[{iface}]  start={start or '-'}  limit={limit or '-'}")
    lines.append(f"  静态租约条目: {len(host)}（仅数量，不回显 MAC/地址细节以外的敏感项）")
    sens = _sensitive_in(secs)
    if sens:
        lines.append(f"    ⚠ 含敏感配置项（存在性，不打印值）: {', '.join(sens)}")
    lines.append("改 DHCP/DNS 为写操作（uci set + commit + dnsmasq restart），本工具不自动执行。")
    return True, "\n".join(lines)


def storage_report() -> Tuple[bool, str]:
    """存储只读报告：/etc/config/fstab 挂载点 + df 容量（只读，不 resize/格式化）。"""
    ok, _info = is_openwrt()
    if not ok:
        return False, ("当前不在 OpenWrt 环境。OpenWrt 挂载配置位于 /etc/config/fstab，"
                       "overlay（叠加根）容量可用 `df -h` 只读查看。")
    lines = ["存储（只读，不 resize/格式化）："]
    fstab = os.path.join(UCI_DIR, "fstab")
    if os.path.isfile(fstab):
        secs = parse_uci_file(fstab)
        mounts = [s for s in secs if s["type"] == "mount"]
        lines.append(f"  fstab 挂载点: {len(mounts)}")
        for m in mounts[:20]:
            target = _uci_opt(m, "target")
            uuid = _uci_opt(m, "uuid") or _uci_opt(m, "device")
            fstype = _uci_opt(m, "fstype")
            enabled = _uci_opt(m, "enabled", "1")
            lines.append(f"    · {target or '(匿名)'}  fstype={fstype or '-'}  "
                         f"enabled={enabled}  ({uuid[:16] + '…' if len(uuid) > 16 else uuid or '-'})")
    else:
        lines.append("  fstab: （未发现 /etc/config/fstab）")
    if _which("df"):
        _o, out = _run_ro(["df", "-h"])
        if _o and out:
            lines.append("  -- df -h（只读）--")
            lines.extend("    " + l for l in out.splitlines()[:20])
    if os.path.isdir("/overlay"):
        lines.append("  overlay 目录存在（固件叠加层；清理/扩容为写操作，本工具不自动执行）。")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 任务派发用的无参包装（runner 以 fn() 派发；详见 runner._run_native）           #
# 这些函数无必填参数，非 OpenWrt 环境优雅降级为指引，绝不抛异常、绝不执行写操作。  #
# --------------------------------------------------------------------------- #


def openwrt_detect_report() -> Tuple[bool, str]:
    """OpenWrt 探测与板型/固件（只读）。供任务 native 通道调用。"""
    ok, info = is_openwrt()
    if not ok:
        return False, ("当前不在 OpenWrt 环境（未发现 /etc/openwrt_release 或 "
                       "os-release ID=openwrt）。OpenWrt 任务需在 OpenWrt 路由器上运行；"
                       "可用 `python -m sysweeper --platform openwrt list` 预览可用任务。")
    return board_report()


def openwrt_uci_report() -> Tuple[bool, str]:
    """UCI 配置只读审计。供任务 native 通道调用。"""
    return uci_audit()


def openwrt_pkgs_report() -> Tuple[bool, str]:
    """已装软件包只读盘点（opkg/apk 自适应）。供任务 native 通道调用。"""
    return package_report()


def openwrt_network_report() -> Tuple[bool, str]:
    """网络接口只读报告。供任务 native 通道调用。"""
    return network_report()


def openwrt_build_report() -> Tuple[bool, str]:
    """OpenWrt 构建系统参考（只读）。供任务 native 通道调用。"""
    return build_report()


def openwrt_firewall_report() -> Tuple[bool, str]:
    """防火墙只读报告（/etc/config/firewall）。供任务 native 通道调用。"""
    return firewall_report()


def openwrt_wireless_report() -> Tuple[bool, str]:
    """无线只读报告（/etc/config/wireless，不回显密码）。供任务 native 通道调用。"""
    return wireless_report()


def openwrt_dhcp_report() -> Tuple[bool, str]:
    """DHCP/DNS 只读报告（/etc/config/dhcp）。供任务 native 通道调用。"""
    return dhcp_report()


def openwrt_storage_report() -> Tuple[bool, str]:
    """存储只读报告（fstab + df）。供任务 native 通道调用。"""
    return storage_report()


def openwrt_report() -> Tuple[bool, str]:
    """OpenWrt 能力总览（只读）：探测 + UCI + 包 + 网络 + 服务 + 构建参考。"""
    try:
        ok, info = is_openwrt()
        head = ("OpenWrt 路由器系统 · 只读能力总览\n"
                "本工具对 OpenWrt 只做只读探测与文档引用，绝不自动执行写操作"
                "（opkg install / uci set / sysupgrade / make image 等均只给指引）。\n"
                "------------------------------------------------------------")
        if not ok:
            return False, (head + "\n当前不在 OpenWrt 环境（未发现 /etc/openwrt_release"
                           " 或 os-release ID=openwrt）。请在 OpenWrt 路由器上运行；"
                           "可用 `python -m sysweeper --platform openwrt list` 预览任务。")
        blocks = []
        for fn in (board_report, uci_audit, package_report, network_report,
                   services_report, firewall_report, wireless_report,
                   dhcp_report, storage_report, build_report):
            _ok, msg = fn()
            blocks.append(msg)
        return True, head + "\n\n" + "\n\n".join(blocks)
    except Exception as e:  # noqa: BLE001
        return False, f"OpenWrt 报告生成失败: {e}"


__all__ = [
    "OWRT_DOCS", "OPENWRT_RELEASE", "UCI_DIR", "SYSINFO_DIR",
    "is_openwrt", "firmware_info", "parse_uci_file", "uci_audit", "uci_dump",
    "package_manager", "list_installed", "package_report",
    "network_report", "services_report", "board_report", "build_report",
    "firewall_report", "wireless_report", "dhcp_report", "storage_report",
    "openwrt_detect_report", "openwrt_uci_report", "openwrt_pkgs_report",
    "openwrt_network_report", "openwrt_build_report",
    "openwrt_firewall_report", "openwrt_wireless_report",
    "openwrt_dhcp_report", "openwrt_storage_report", "openwrt_report",
]
