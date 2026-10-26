"""无线电技术与标准只读诊断（v0.6.75 新建）。

把「无线电」这件事按本工具的**只读诊断**口径结构化摸一遍，并嵌入整体系统：
- 射频与无线接口盘点：rfkill 开关态、iw 无线物理能力（频段/信道）、regdom、
  /sys/class/ieee80211 设备树、蓝牙控制器、PCI/USB 总线上的射频器件；
- SDR 与无线工具链存在性：GNU Radio / rtl-sdr / SoapySDR / Hamlib / gqrx /
  multimon-ng / direwolf / kismet / aircrack-ng 等（只问在不在 PATH，不启动）；
- 法规与频段口径：型号核准 / 微功率目录（2019-52 号公告）/ ISM 频段 / 业余
  无线电 A·B·C 类 / 无线充电专项规定，全部来自 data/radio_docs.json 官方源。

与 link_protocols（ble/ieee802154 链路能力）、meshnet（自组网）、openwrt
（路由射频）、recert（WCET 无线认证续证）、comp 第七轴（位宽世代：AVR/ESP32
等射频 MCU 的算力底座）构成「你中有我」关系，由 sysmap 关联图显式登记。

红线（比全项目更严）：**只读诊断，绝不驱动任何真实发射**——不改 regdom/
信道/发射功率、不开 monitor 注入、不解码他人通信内容、不抓包破解未授权网络、
不连校外网做写。法规结论只引用官方源与给出合规路径，不代办执照。
"""

from __future__ import annotations

import os
import shutil
from typing import Dict, List, Tuple

from . import common

# --------------------------------------------------------------------------- #
# 路径与常量                                                                    #
# --------------------------------------------------------------------------- #
SYS_80211 = "/sys/class/ieee80211"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# 无线/SDR 工具链：name → (可执行名, 说明)。仅做存在性盘点。
WIRELESS_TOOLS = [
    ("gnuradio", "gnuradio-companion", "GNU Radio 流图 IDE（SDR 信号处理）"),
    ("rtl_sdr", "rtl_sdr", "RTL2832U 电视棒 SDR 工具"),
    ("soapysdr", "SoapySDRUtil", "SDR 设备抽象层工具"),
    ("hamlib", "rigctl", "业余电台 CAT 控制（Hamlib）"),
    ("gqrx", "gqrx", "基于 GNU Radio 的通用接收机"),
    ("multimon", "multimon-ng", "多制式数字信号解调（POCSAG/DTMF 等）"),
    ("direwolf", "direwolf", "APRS TNC/调制解调"),
    ("kismet", "kismet", "无线探测器/嗅探器"),
    ("aircrack", "aircrack-ng", "802.11 审计工具集（仅登记存在性）"),
    ("wireshark", "wireshark", "通用抓包分析仪"),
    ("bluetoothctl", "bluetoothctl", "蓝牙控制 CLI（只读查询）"),
    ("iw", "iw", "无线配置查询工具（nl80211）"),
]

# 本机射频相关的总线关键词（lsusb/lspci 文本过滤）
RF_BUS_KEYWORDS = ("wifi", "wi-fi", "wireless", "802.11", "bluetooth", "bt ",
                   "wlan", "network", "radio", "sdr", "rtl", "broadcom", "intel(r) wi",
                   "realtek rtl", "atheros", "mediatek")


# --------------------------------------------------------------------------- #
# 知识库加载（consumes data/radio_docs.json；与 legacy/reverse 同范式）         #
# --------------------------------------------------------------------------- #
def _load_refs() -> List[dict]:
    """只读加载 data/radio_docs.json 的 items；失败返回空列表（不崩）。"""
    import json
    path = os.path.join(DATA_DIR, "radio_docs.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        return list(doc.get("items") or [])
    except Exception:  # noqa: BLE001 —— 知识库缺失不拖垮探测
        return []


REFS: List[dict] = _load_refs()

# 只读层自查项：每项回链知识库条目 key。
RADIO_CHECKS: Dict[str, tuple] = {
    "rf_switches": ("radio", "射频开关（rfkill）只读探查",
                    ["radio-regulation-cn", "radio-security-audit"]),
    "wifi_phys": ("radio", "Wi-Fi 物理能力（iw phy / ieee80211 sysfs）只读探查",
                  ["radio-freq-allocation-cn", "radio-links-wireless"]),
    "bluetooth_ctl": ("radio", "蓝牙控制器只读探查",
                      ["radio-links-wireless"]),
    "rf_devices": ("radio", "总线射频器件（PCI/USB）只读探查",
                   ["radio-iot-mcus"]),
    "sdr_toolchain": ("radio", "SDR/无线工具链存在性盘点（不启动）",
                      ["radio-sdr-toolchain", "radio-security-audit"]),
    "regulation_kb": ("radio", "无线电法规与频段口径（型号核准/微功率/ISM/业余）",
                     ["radio-regulation-cn", "radio-type-approval-srrc",
                      "radio-micropower-2019-52", "radio-amateur-cn",
                      "radio-itu-regs", "radio-wireless-charging",
                      "radio-wcet-continuity"]),
}

_SELF_POSITION = (
    "本层只读诊断：绝不驱动任何真实发射——不改 regdom/信道/发射功率、不开 monitor "
    "注入、不解码他人通信内容、不抓包破解未授权网络、不连校外网做写。"
    "法规结论只引用官方源并给合规路径，不代办频率许可/台站执照/型号核准。"
)


def doc_list() -> List[str]:
    """知识条目清单（回链 data 层 key）。"""
    out: List[str] = []
    for ref in REFS:
        out.append(f"· [{ref.get('key', '?')}] {ref.get('name', '?')}"
                   f"（{ref.get('org', '未注明')}）")
    return out


def reference(key: str) -> dict:
    """按 key 取知识条目；无则空 dict。"""
    for ref in REFS:
        if ref.get("key") == key:
            return ref
    return {}


# --------------------------------------------------------------------------- #
# 只读探测辅助                                                                #
# --------------------------------------------------------------------------- #
def _have(cmd: str) -> bool:
    """shutil.which 命中即视为已安装（不触碰二进制本体）。"""
    return shutil.which(cmd) is not None


def _rf_lines() -> List[str]:
    """rfkill list 的只读输出行；无 rfkill 或为空返回 []。"""
    if not _have("rfkill"):
        return []
    _rc, out = common.run("rfkill list 2>/dev/null", timeout=15, tail=4000)
    return [ln for ln in out.splitlines() if ln.strip()]


def _sys80211_phys() -> List[str]:
    """ /sys/class/ieee80211 下的 phy* 目录名（只读目录列表）。"""
    try:
        return sorted(e for e in os.listdir(SYS_80211) if e.startswith("phy"))
    except OSError:
        return []


def _iw_phys_count() -> int:
    """iw phy 列出的物理设备数（只读；iw 缺失时回退 sysfs）。"""
    if _have("iw"):
        _rc, out = common.run("iw phy 2>/dev/null", timeout=15, tail=20000)
        n = sum(1 for ln in out.splitlines() if ln.startswith("Wiphy "))
        if n:
            return n
    return len(_sys80211_phys())


def _iw_reg() -> str:
    """iw reg get 的只读输出（监管域）；无则空串。"""
    if not _have("iw"):
        return ""
    _rc, out = common.run("iw reg get 2>/dev/null", timeout=15, tail=3000)
    return out


def _bt_controllers() -> int:
    """bluetoothctl show 输出的控制器计数（只读）。"""
    if not _have("bluetoothctl"):
        return 0
    _rc, out = common.run("bluetoothctl show 2>/dev/null", timeout=15, tail=4000)
    return sum(1 for ln in out.splitlines() if ln.strip().startswith("Controller "))


def _rf_bus_hits() -> List[str]:
    """lsusb/lspci 中命中射频关键词的行（只读），最多 12 条。"""
    hits: List[str] = []
    for tool, args in (("lsusb", "lsusb 2>/dev/null"), ("lspci", "lspci 2>/dev/null")):
        if not _have(tool):
            continue
        _rc, out = common.run(args, timeout=15, tail=6000)
        for ln in out.splitlines():
            low = ln.lower()
            if any(k in low for k in RF_BUS_KEYWORDS):
                hits.append(f"[{tool}] {ln.strip()}")
    return hits[:12]


# --------------------------------------------------------------------------- #
# 五段只读报告                                                                 #
# --------------------------------------------------------------------------- #
def rf_switch_report() -> Tuple[bool, str]:
    """射频开关（rfkill）只读探查。"""
    lines = ["射频开关（rfkill）只读探查（不改动任何开关）："]
    lines.append("─" * 60)
    lines_ = _rf_lines()
    if not lines_:
        lines.append("   · 本机没有 rfkill 输出（无射频开关机制、或容器/精简环境未提供）")
        return False, "\n".join(lines)
    soft = hard = 0
    for ln in lines_:
        low = ln.lower()
        if "soft blocked: yes" in low:
            soft += 1
        if "hard blocked: yes" in low:
            hard += 1
    lines.append(f"   · rfkill 条目：{len([l for l in lines_ if l and not l.startswith(' ')][:0]) or len(lines_)} 行")
    lines.append(f"   · 软阻塞（软件关射频）：{soft} 项" + ("→ 本机射频已被软件关闭" if soft else ""))
    lines.append(f"   · 硬阻塞（硬件开关/飞行模式）：{hard} 项" + ("→ 本机射频被物理开关关闭" if hard else ""))
    for ln in lines_[:8]:
        lines.append(f"     {ln.strip()}")
    lines.append("   · 【红线】只读查看；开关射频属用户场景操作，本工具不代切换")
    return True, "\n".join(lines)


def wifi_phys_report() -> Tuple[bool, str]:
    """Wi-Fi 物理能力只读探查（频段/信道/监管域）。"""
    lines = ["Wi-Fi 物理能力只读探查（iw phy / sysfs / regdom）："]
    lines.append("─" * 60)
    n = _iw_phys_count()
    sys_phys = _sys80211_phys()
    if not n and not sys_phys:
        lines.append("   · 本机未见无线物理设备（无 Wi-Fi 网卡、或容器透传受限）")
        lines.append("   · 这类机器仍可用 SDR 工具链盘点（见 sdr_toolchain_report）")
        return False, "\n".join(lines)
    lines.append(f"   · 无线物理设备（Wiphy）：{n or len(sys_phys)} 个")
    if sys_phys:
        lines.append(f"   · sysfs phy 目录：{' '.join(sys_phys)}")
    reg = _iw_reg()
    if reg:
        first = [ln for ln in reg.splitlines() if ln.strip()][:2]
        lines.append("   · 监管域（regdom）：" + (first[0].strip() if first else "未知"))
    else:
        lines.append("   · regdom：读不到（iw 缺失或权限受限）")
    lines.append("   · 【读法】regdom 决定 2.4/5GHz 信道与发射功率的合法上限；")
    lines.append("     6GHz（Wi-Fi 6E/7）受《频率划分规定》6425-7125MHz IMT 划分影响")
    lines.append("   · 【红线】只读；绝不改 regdom/信道/txpower（写入属发射参数配置）")
    return True, "\n".join(lines)


def bluetooth_report() -> Tuple[bool, str]:
    """蓝牙控制器只读探查。"""
    lines = ["蓝牙控制器只读探查（bluetoothctl show）："]
    lines.append("─" * 60)
    n = _bt_controllers()
    if not n:
        lines.append("   · 未见蓝牙控制器（未内置蓝牙、或 bluez/容器未提供）")
        lines.append("   · 注：link_protocols 库仍登记 BLE 协议本身的知识坐标")
        return False, "\n".join(lines)
    lines.append(f"   · 控制器数量：{n}")
    lines.append("   · 【读法】控制器在 = 有 BLE/BR-EDR 物理面；能否广播/扫描另看开关态")
    lines.append("   · 【红线】不扫描、不配对、不改任何控制器参数（只 show）")
    return True, "\n".join(lines)


def rf_devices_report() -> Tuple[bool, str]:
    """总线射频器件（PCI/USB）只读探查。"""
    lines = ["总线射频器件只读探查（lsusb / lspci 文本过滤）："]
    lines.append("─" * 60)
    hits = _rf_bus_hits()
    if not hits:
        lines.append("   · 未在 USB/PCI 总线看到射频器件关键词命中")
        lines.append("   · 纯容器/精简机常见此态；不代表无线电能力不存在（看 sysfs/iw）")
        return False, "\n".join(lines)
    lines.append(f"   · 命中射频关键词的总线设备：{len(hits)} 条")
    for ln in hits:
        lines.append(f"     {ln}")
    lines.append("   · 【读法】Wi-Fi 网卡/蓝牙控制器/USB SDR 棒都走这两条总线枚举；")
    lines.append("     注意同一器件可能同时命中多个关键词，去重看灯位")
    lines.append("   · 【红线】只读枚举；不绑定/解绑驱动、不动电源管理")
    return True, "\n".join(lines)


def sdr_toolchain_report() -> Tuple[bool, str]:
    """SDR/无线工具链存在性盘点（绝不启动任何工具）。"""
    lines = ["SDR 与无线工具链存在性盘点（只 which，绝不启动）："]
    lines.append("─" * 60)
    present = [(key, cmd, desc) for key, cmd, desc in WIRELESS_TOOLS if _have(cmd)]
    for key, cmd, desc in WIRELESS_TOOLS:
        mark = "✓" if _have(cmd) else "✗"
        lines.append(f"   · {mark} {cmd:<22} {desc}")
    lines.append("─" * 60)
    lines.append(f"   · 命中 {len(present)}/{len(WIRELESS_TOOLS)} 项")
    lines.append("   · 【读法】有 GNU Radio 无 rtl_sdr = 有流图环境无宽带前端；")
    lines.append("     有 rigctl 说明宿主机接电台 CAT——再看 rfkill 确认发射链路")
    lines.append("   · 【红线】盘点存在性；启动任何接收/发射流程由用户在合规前提下自行决定")
    return bool(present), "\n".join(lines)


def regulation_report() -> Tuple[bool, str]:
    """无线电法规与频段口径（引用 data/radio_docs.json 官方源）。"""
    lines = ["无线电法规与频段口径（官方源登记；只读引用）："]
    lines.append("─" * 60)
    if not REFS:
        lines.append("   · 知识库未加载（data/radio_docs.json 缺失）")
        return False, "\n".join(lines)
    for ln in doc_list():
        lines.append("   " + ln)
    lines.append("─" * 60)
    lines.append("   · 中国 ISM 常规可用频段（2019-52 号公告口径）：")
    lines.append("     13553-13567kHz / 26957-27283kHz / 40.66-40.7MHz / "
                 "2400-2500MHz / 5725-5875MHz / 24-24.25GHz")
    lines.append("   · 433.05-434.79MHz（一区部分欧洲国家）与 902-928MHz（二区含美国）")
    lines.append("     是国外的 ISM 频段——中国所在第三区 100MHz-1GHz 无 ISM 专用划分")
    lines.append("   · 合规三线：有发射 → 型号核准（SRRC/CMIIT ID）；")
    lines.append("     微功率目录内 → 免核准仍受技术要求约束；个人收发 → 业余电台执照+呼号")
    lines.append("   · 【诚实边界】法条以 gov.cn / miit.gov.cn 官方文本为准；")
    lines.append("     具体产品是否合规以型号核准与当期公告为准，本工具不代办")
    return True, "\n".join(lines)


REPORTS = [
    ("射频开关（rfkill）", rf_switch_report),
    ("Wi-Fi 物理能力", wifi_phys_report),
    ("蓝牙控制器", bluetooth_report),
    ("总线射频器件", rf_devices_report),
    ("SDR 与无线工具链", sdr_toolchain_report),
    ("法规与频段口径", regulation_report),
]


def radio_report() -> Tuple[bool, str]:
    """无线电技术与标准整体只读诊断。返回 (ok, 文本)。"""
    blocks = ["无线电技术与标准诊断（射频·链路·SDR 工具链·法规口径，全部只读）",
              "════════════════════════════════════════════"]
    any_ok = False
    for title, fn in REPORTS:
        ok, msg = fn()
        blocks.append(f"【{title}】{'✓ 已检测' if ok else '✗ 本机无/未装'}")
        blocks.append(msg)
        any_ok = any_ok or ok
    blocks.append("════════════════════════════════════════════")
    blocks.append("结论：已把「射频物理面 + 无线链路 + SDR 工具链 + 法规口径」纳入整体系统"
                  "的只读诊断；嵌入方式见 sysmap 关联图（radio↔link_protocols·meshnet·"
                  "openwrt·recert·comp 位宽轴）。")
    blocks.append("红线：绝不驱动任何真实发射——不改 regdom/信道/txpower、不开 monitor "
                  "注入、不抓包破解未授权网络；法规结论只引用官方源。")
    return (any_ok, "\n".join(blocks))


def capabilities_report() -> Tuple[bool, str]:
    """能力自检（只读）：本机可诊断哪些无线电维度 + 红线。"""
    lines = ["无线电技术只读诊断能力自检："]
    for title, fn in REPORTS:
        try:
            ok, _ = fn()
            lines.append(f"   · {title:<18} {'可诊断(本机有)' if ok else '可诊断(本机无/未装)'}")
        except Exception:  # noqa: BLE001
            lines.append(f"   · {title:<18} 诊断异常")
    lines.append(f"   · 知识条目回链：{len(REFS)} 条（radio_docs.json）")
    lines.append("红线：仅读 which/版本首行/rfkill·iw·bluetoothctl 只读查询/目录存在性；"
                 "不驱动任何发射、不破解未授权网络、不连校外网做写。")
    return True, "\n".join(lines)
