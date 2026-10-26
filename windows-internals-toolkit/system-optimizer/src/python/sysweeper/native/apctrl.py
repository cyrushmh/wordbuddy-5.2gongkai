"""AP 集中控制器只读审计（apctrl）：把 apcontroller 的「集中管理轻量 AP」思路接进整体系统。

导入学习 obsy/apcontroller（README 解析结论）：cron 轮询 + scp/ssh 从各 AP 取数、按 AP Group
下发 WiFi 配置、不读不改现有配置、known_hosts 防 MITM、key-based（dropbear）免密、
用户脚本 /usr/share/apcontroller/scripts（#desc:/#warn: 头）。本子系统把它收口成**只读审计**：
只探测本机/网内有哪些 AP 栈（hostapd / NetworkManager 共享热点 / dnsmasq / apcontroller 脚本），
绝不读解密口令、绝不改任何 AP 配置、绝不新增/下发配置——任何写操作只给指引。

覆盖：
  hostapd      : /etc/hostapd/*.conf 只读抽取 ssid/interface/hw_mode/channel（不回显口令/密钥）
  NetworkManager: nmcli 只读看「共享热点」连接（ap 模式）与可见 SSID
  dnsmasq      : /etc/dnsmasq.conf / dnsmasq.d 只读看 DHCP 网段与上游 DNS
  apcontroller  : 探测脚本目录与配置目录是否存在（按 obsy/apcontroller 思路），只读列脚本 #desc:

红线：只读审计 ≠ 授权施工——改 hostapd/dnsmasq、用 apcontroller 下发 AP Group 配置一律只给指引。
"""

from __future__ import annotations

import os
import shutil


# 探针清单：CLI 按此逐项展示本机只读信号
PROBES = (
    ("hostapd_report", "hostapd 主机热点配置"),
    ("nm_ap_report", "NetworkManager 共享热点"),
    ("dnsmasq_report", "dnsmasq DHCP/DNS"),
    ("apcontroller_report", "AP 集中控制器（apcontroller 学习）"),
)

# apcontroller 约定目录（按 obsy/apcontroller 思路，只读探测是否存在）
APCTRL_SCRIPTS_DIR = "/usr/share/apcontroller/scripts"
APCTRL_CONF_DIR = "/etc/apcontroller"


def _read(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return None


def _safe_conf(txt: str, keys: tuple) -> dict:
    """从 conf 文本只读抽安全字段（跳过口令/密钥/psk 类）。"""
    out = {}
    for line in txt.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k in keys and "pass" not in k.lower() and "psk" not in k.lower() and "key" not in k.lower():
            out[k] = v
    return out


def hostapd_report() -> tuple:
    """只读抽 hostapd 配置（ssid/interface/hw_mode/channel，不含密钥）。"""
    confs = []
    for base in ("/etc/hostapd",):
        try:
            for fn in os.listdir(base):
                if fn.endswith(".conf"):
                    confs.append(os.path.join(base, fn))
        except OSError:
            pass
    if not confs:
        return False, "未检测到 hostapd 配置（/etc/hostapd/*.conf）；如本机不作 AP 则属正常"
    lines = ["hostapd（主机热点）只读抽取（不含口令/密钥）:"]
    for c in confs:
        txt = _read(c)
        if not txt:
            continue
        safe = _safe_conf(txt, ("interface", "ssid", "hw_mode", "channel", "country_code",
                                "ctrl_interface", "driver"))
        lines.append(f"   · {c}: " + ", ".join(f"{k}={v}" for k, v in safe.items()) or "（无可抽安全字段）")
    return True, "\n".join(lines)


def nm_ap_report() -> tuple:
    """只读看 NetworkManager 是否把某连接设为 AP 共享热点。"""
    if shutil.which("nmcli") is None:
        return False, "未安装 NetworkManager（nmcli 不可用）；如本机用其它网络管理则属正常"
    import subprocess
    try:
        out = subprocess.run(["nmcli", "-t", "-f", "NAME,TYPE,DEVICE",
                              "connection", "show"], capture_output=True, text=True,
                             timeout=8).stdout
    except (OSError, subprocess.SubprocessError):
        return False, "nmcli 调用失败（只读探针跳过）"
    aps = [l for l in out.splitlines() if "802-11-wireless" in l and ("ap" in l.lower() or "hotspot" in l.lower())]
    if not aps:
        return False, "NetworkManager 当前无可识别的 AP/热点连接"
    return True, "NetworkManager 共享热点连接:\n" + "\n".join(f"   · {l}" for l in aps)


def dnsmasq_report() -> tuple:
    """只读看 dnsmasq 的 DHCP 网段与上游 DNS（不含口令）。"""
    txt = _read("/etc/dnsmasq.conf")
    extra = []
    try:
        for fn in os.listdir("/etc/dnsmasq.d"):
            if fn.endswith(".conf"):
                extra.append(_read(os.path.join("/etc/dnsmasq.d", fn)) or "")
    except OSError:
        pass
    blob = "\n".join([txt or "", *extra])
    if not blob.strip():
        return False, "未检测到 dnsmasq 配置（/etc/dnsmasq.conf 或 dnsmasq.d）；如未做 AP DHCP 则属正常"
    safe = _safe_conf(blob, ("interface", "dhcp-range", "server", "listen-address", "bind-interfaces"))
    return True, "dnsmasq（AP DHCP/DNS，只列网段与上游，不含密钥）:\n" + "\n".join(
        f"   · {k}={v}" for k, v in safe.items()) or "   · （无可抽安全字段）"


def apcontroller_report() -> tuple:
    """只读探测 apcontroller 思路的集中控制器痕迹（脚本目录/配置目录）。

    不读任何 AP 的现有配置（apcontroller 本身也「不读不改现有配置」），只确认本机是否
    部署了集中管理工具，并列出用户脚本的 #desc 摘要（#warn 用于风险提示）。
    """
    lines = ["AP 集中控制器（apcontroller 思路，只读探测）:"]
    found = False
    if os.path.isdir(APCTRL_SCRIPTS_DIR):
        found = True
        lines.append(f"   · 脚本目录存在: {APCTRL_SCRIPTS_DIR}")
        try:
            for fn in sorted(os.listdir(APCTRL_SCRIPTS_DIR)):
                if not fn.endswith((".sh", ".py", ".bash")):
                    continue
                t = _read(os.path.join(APCTRL_SCRIPTS_DIR, fn)) or ""
                desc = warn = ""
                for l in t.splitlines()[:30]:
                    if l.startswith("#desc:"):
                        desc = l.split(":", 1)[1].strip()
                    elif l.startswith("#warn:"):
                        warn = l.split(":", 1)[1].strip()
                tag = f" ｜ #warn: {warn}" if warn else ""
                lines.append(f"     - {fn}: {desc}{tag}".rstrip())
        except OSError:
            pass
    if os.path.isdir(APCTRL_CONF_DIR):
        found = True
        lines.append(f"   · 配置目录存在: {APCTRL_CONF_DIR}（只读，不改动）")
    if not found:
        return False, "未检测到 apcontroller 类集中控制器（脚本/配置目录均不存在）；如需集中下发 WiFi 配置可参考 obsy/apcontroller"
    return True, "\n".join(lines)


def environment_report() -> list:
    """返回本机 AP 栈探测概览（只读）。"""
    lines = ["AP 集中控制器审计（apctrl）· 本机只读探测："]
    for fn, lab in PROBES:
        ok, msg = getattr(__import__("sys").modules[__name__], fn)()
        lines.append(f"   · {lab}: {'✓ 可用' if ok else '✗ 不适用'}")
        if isinstance(msg, str) and msg.strip():
            lines.append("       " + msg.replace("\n", "\n       "))
    return lines


def apctrl_report(env_tags: list | None = None, readings: dict | None = None) -> tuple:
    """端到端生成 AP 集中控制器审计报告：探测各 AP 栈 → 给出集中管理思路与合规指引。只读不写。"""
    lines = ["== AP 集中控制器审计报告（apctrl：hostapd/NetworkManager/dnsmasq/apcontroller 只读审计，只读不写）=="]
    lines.append(f"维度标签: {sorted(set(env_tags or [])) or '未声明（默认基线）'}")
    lines.append("")
    lines.append("[① 本机 AP 栈探测（只读，绝不回显口令/密钥）]")
    for fn, lab in PROBES:
        ok, msg = getattr(__import__("sys").modules[__name__], fn)()
        lines.append(f"   · {lab}: {'✓ 可用' if ok else '✗ 不适用'}")
        if isinstance(msg, str) and msg.strip():
            for sub in msg.splitlines():
                lines.append("       " + sub)
    lines.append("")
    lines.append("[② 集中管理思路（学习 obsy/apcontroller，只陈述不代执行）]")
    for tip in (
        "cron 轮询 + scp/ssh 从各 AP 取数（只读取，不改现有配置）",
        "按 AP Group 分组下发 WiFi 配置（ssid/加密/VLAN 等）",
        "known_hosts 固定指纹防 MITM；key-based（dropbear）免密，不落口令",
        "用户脚本放 /usr/share/apcontroller/scripts，#desc 写说明、#warn 写风险提示",
    ):
        lines.append(f"   · {tip}")
    lines.append("")
    lines.append("安全不变量：apctrl 只审计 + 出指引；改 hostapd/dnsmasq、用 apcontroller 下发 AP Group "
                 "配置、ssh 到任何 AP 一律只给规范指引；是否施工始终由用户在厂商/控制器工具确认。")
    return True, "\n".join(lines)


# ── 写操作（仅指引，不代执行）──
def guide_push_apgroup(ap_group: str | None = None) -> tuple:
    """指引用 apcontroller 思路按 AP Group 下发 WiFi 配置（不代执行）。"""
    g = ap_group or "<ap-group>"
    lines = [
        f"AP Group 下发指引（{g}，不代执行）:",
        "   1. 在控制器侧维护该 Group 的 WiFi 模板（ssid/加密/VLAN/信道），按 obsy/apcontroller 约定",
        "   2. cron 驱动下发前先 scp 取各 AP 现状快照（只读），与模板比对差异",
        "   3. 用 key-based（dropbear）+ known_hosts 固定指纹连 AP，禁止明文口令",
        "   4. 仅下发增量；现有未纳入模板的配置不触碰（apcontroller 原则：不读不改现有配置）",
    ]
    return True, "\n".join(lines)


TUNES = (
    ("guide_push_apgroup", "AP Group 下发 WiFi 配置（规范指引，不代执行）"),
)


def apctrl_tune_list() -> list:
    """返回 apctrl 写指引清单，供 CLI/GUI 展示。只读展示，调用只回指引。"""
    return [f"· {fn}() — {desc}" for fn, desc in TUNES]
