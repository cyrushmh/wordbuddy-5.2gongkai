"""预警应急与定位融合只读层（emergency）。

一句话立项：**先知道自己大概在哪，才知道预警离自己多远、往哪儿撤。**

定位的口径（这是本层最关键的设计，按你的要求定死）
------------------------------------------------
1. **首选基线 = 网络定位 + 基站定位**。
   为什么不是先拿 GPS：导航定位（GNSS）在室内、地铁、隧道、省电模式下常常拿不到，
   而"网络 + 基站"几乎总能给出一个**粗略但存在**的位置。所以基线先用它，
   保证「任何情况下都有一个可用的地理位置与距离」，不出现"定位不可用"的空洞。
2. **检测到导航定位（GNSS / fused）时，导航与首选基线**共同综合**。
   综合不是"两个取一个"，而是按**精度倒数平方加权**（inverse-variance weighting）：
   精度半径越小权重越大，所以 GNSS 一旦可用就自然主导结果，但基线仍参与，
   不会因 GNSS 一次跳变就把位置甩飞。
3. **两个源互相校核**：基线点与导航点距离偏差超过阈值（默认 2 km）时标记为
   **存疑**，并把两套距离**都摆出来**——不替用户判定哪个对。

融合公式（纯标准库，无第三方依赖）：
    w_i = 1 / max(acc_i, min_acc)^2
    lat = Σ(w_i·lat_i) / Σ(w_i)      lon 同理（经纬度近似平面加权，城市尺度误差可忽略）
    融合精度半径 = 1 / sqrt(Σ w_i)    （各源独立的方差合成，比取最小值诚实）

设计边界（红线，任何情况下不越）
--------------------------------
- **不自动报警、不拨号、不发短信、不呼救**。SOS 只生成**文本**，由用户自己决定
  用什么通道发（可以贴到 meshchat 的全体广播，也可以自己打电话）。
- **不擅自联网抓预警源**。联网订阅默认**关闭**，开启后也只拉取用户自己填的 URL，
  且拉取失败只报"未能获取"，绝不编造预警内容——**没有预警就是没有预警**。
- **只做只读**：探测用 `nmcli` / `mmcli` / `adb shell dumpsys location` 这类只读命令，
  拿不到就写"未知"，绝不假装定位成功。
- 手动开关持久化在 `guistate`（XDG `~/.config/sysweeper/gui.json` 的 emergency 段），
  只存**布尔开关与坐标数字**，不存命令、不存代码。
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..i18n import _
from . import common

# ---------------------------------------------------------------- 常量

EARTH_R_M = 6_371_008.8          # IUGG 平均地球半径（米）
MIN_ACC_M = 5.0                  # 精度半径下限：防止 acc=0 导致权重爆炸
DEFAULT_CELL_ACC_M = 1_500.0     # 基站定位默认精度（城区站距数百米，郊区数公里）
DEFAULT_NET_ACC_M = 5_000.0      # 网络/IP 定位默认精度（IP 归属点，常偏几十公里）
DISAGREE_M = 2_000.0             # 基线与导航偏差超过此值 → 标记存疑

SRC_GNSS = "gnss"        # 导航定位：GPS / 北斗 / GLONASS / Galileo
SRC_CELL = "cell"        # 基站定位：MCC/MNC/LAC/CID + 覆盖半径
SRC_NET = "network"      # 网络定位：Wi-Fi BSSID / IP 归属
SRC_MANUAL = "manual"    # 用户手动录入

_PREFERRED = (SRC_CELL, SRC_NET)      # 首选基线：网络 + 基站
_FUSABLE = (SRC_GNSS, SRC_CELL, SRC_NET, SRC_MANUAL)

# 预警等级：CAP 1.2 的 severity + 国内四色预警对照（仅作显示映射，不改变判定逻辑）
SEVERITY_ORDER = ["Extreme", "Severe", "Moderate", "Minor", "Unknown"]
SEVERITY_CN = {
    "Extreme": _(" Extremely severe / 红色"),
    "Severe": _(" Severe / 橙色"),
    "Moderate": _(" Moderate / 黄色"),
    "Minor": _(" Minor / 蓝色"),
    "Unknown": _(" Unknown / 未定级"),
}

# 传播速度粗估值（m/s）：只用于给「大概还有多久」的量级，不是预报
SPEED_LABELS = {
    "earthquake_p": _("地震 P 波"),
    "earthquake_s": _("地震 S 波"),
    "typhoon": _("台风移动"),
    "flood": _("洪水推进"),
    "fire": _("火势蔓延"),
    "other": _("该类事件"),
}

SPEED_PROFILES = {
    "earthquake_p": 6_000.0,
    "earthquake_s": 3_500.0,
    "typhoon": 8.0,
    "flood": 2.0,
    "fire": 1.0,
    "other": 5.0,
}

MAX_ALERTS = 200          # 本地预警缓存上限
MAX_FEED_BYTES = 512_000  # 订阅源单次抓取上限（防止被超大响应拖死）


def _state_dir() -> Path:
    """应急数据落盘目录（与 guistate 同 XDG 口径）。"""
    import os
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "sysweeper"


# ---------------------------------------------------------------- 开关

SWITCHES: Dict[str, Tuple[bool, str]] = {
    # 名称: (默认, 说明)
    "locate_enabled": (True, _("启用定位（关掉后只用手动录入的坐标，不探测本机）")),
    "prefer_cell_network": (True, _("以网络 + 基站定位为首选基线（本层核心口径）")),
    "fuse_with_nav": (True, _("检测到导航定位时，与首选基线共同综合")),
    "alert_enabled": (True, _("启用预警评估（只评估，不自动报警）")),
    "feed_enabled": (False, _("联网订阅预警源（默认关闭；开启后只拉你自己填的 URL）")),
    "sos_enabled": (True, _("启用应急呼救文本生成（只生成文本，绝不自动发送）")),
    "shelter_enabled": (True, _("启用避险点距离排序")),
    "kit_enabled": (True, _("启用应急物资清单核对")),
}

DEFAULT_SWITCHES = {k: v[0] for k, v in SWITCHES.items()}

_MEMORY_SW: Optional[Dict] = None  # 家目录不可写时降级为内存态


def _switch_path() -> Path:
    return _state_dir() / "emergency.json"


def switches() -> Dict[str, bool]:
    """读出当前开关状态；任何异常都回退默认值（界面绝不因配置坏而打不开）。"""
    global _MEMORY_SW
    if _MEMORY_SW is not None:
        return dict(_MEMORY_SW)
    p = _switch_path()
    out = dict(DEFAULT_SWITCHES)
    try:
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for k in out:
                    if k in data and isinstance(data[k], bool):
                        out[k] = data[k]
    except Exception:  # noqa: BLE001 - 配置损坏不该拖垮功能
        return dict(DEFAULT_SWITCHES)
    return out


def set_switch(name: str, on: bool) -> bool:
    """手动开关：开 / 关某一项。未知开关名直接拒绝（不静默吞掉）。"""
    if name not in DEFAULT_SWITCHES:
        return False
    global _MEMORY_SW
    st = switches()
    st[name] = bool(on)
    try:
        p = _switch_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
        _MEMORY_SW = None
        return True
    except Exception:  # noqa: BLE001
        _MEMORY_SW = st
        return False


def switch_on(name: str) -> bool:
    return switches().get(name, DEFAULT_SWITCHES.get(name, False))


def reset_switches() -> Dict[str, bool]:
    global _MEMORY_SW
    _MEMORY_SW = None
    try:
        p = _switch_path()
        if p.exists():
            p.unlink()
    except Exception:  # noqa: BLE001
        pass
    return dict(DEFAULT_SWITCHES)


# ---------------------------------------------------------------- 几何

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """两点球面距离（米）。Haversine，城市尺度足够准。"""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R_M * math.asin(min(1.0, math.sqrt(a)))


def _fmt_dist(m: float) -> str:
    if m < 1000:
        return f"{m:.0f} m"
    return f"{m / 1000:.2f} km"


# ---------------------------------------------------------------- 定位源

class LocSource:
    """一个定位来源。"""

    __slots__ = ("kind", "lat", "lon", "acc", "detail", "ts")

    def __init__(self, kind: str, lat: float, lon: float,
                 acc: float, detail: str = "", ts: float = 0.0):
        self.kind = kind
        self.lat = lat
        self.lon = lon
        self.acc = max(float(acc or MIN_ACC_M), MIN_ACC_M)
        self.detail = detail
        self.ts = ts

    def as_dict(self) -> dict:
        """无坐标时 lat/lon 输出 None（而不是 nan——nan 进不了 JSON）。"""
        ok = _valid(self.lat, self.lon)
        return {"kind": self.kind,
                "lat": round(self.lat, 6) if ok else None,
                "lon": round(self.lon, 6) if ok else None,
                "acc_m": round(self.acc, 1), "detail": self.detail,
                "has_fix": ok}

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<LocSource {self.kind} {self.lat:.5f},{self.lon:.5f} ±{self.acc:.0f}m>"


def fuse(sources: List[LocSource]) -> Optional[dict]:
    """按精度倒数平方加权融合多个定位源。

    返回 {lat, lon, acc_m, n, weights}；源为空返回 None。
    融合精度 = 1/sqrt(Σw)——各源独立时方差可加，这比"取最小精度"诚实得多。
    """
    srcs = [s for s in sources if s and _valid(s.lat, s.lon)]
    if not srcs:
        return None
    ws = [1.0 / (s.acc ** 2) for s in srcs]
    wsum = sum(ws)
    if wsum <= 0:
        return None
    lat = sum(w * s.lat for w, s in zip(ws, srcs)) / wsum
    lon = sum(w * s.lon for w, s in zip(ws, srcs)) / wsum
    acc = 1.0 / math.sqrt(wsum)
    return {"lat": lat, "lon": lon, "acc_m": max(acc, MIN_ACC_M),
            "n": len(srcs),
            "weights": {s.kind: round(w / wsum, 4) for w, s in zip(ws, srcs)}}


BASELINE_MIN_W = 0.05   # 有导航时，首选基线的最低话语权（防止一次 GNSS 跳变把位置甩飞）


def fuse_with_floor(nav_src: LocSource, base_srcs: List[LocSource],
                    floor: float = BASELINE_MIN_W) -> Optional[dict]:
    """导航 + 首选基线的**共同综合**（本层口径的第二条）。

    为什么不直接逆方差融合：GNSS 精度（~8 m）比基站（~1500 m）高两个量级，
    纯逆方差会让基线权重趋近 0——那就退化成"只用导航"，不是你要的"共同综合"。
    所以给基线留出**最低话语权**（默认 5%）：导航主导但不独占，一次 GNSS 跳变
    不至于把位置甩到几公里外；基线仍然参与校核。
    """
    if not nav_src or not _valid(nav_src.lat, nav_src.lon):
        return fuse(base_srcs)
    bs = [s for s in base_srcs if _valid(s.lat, s.lon)]
    if not bs:
        return dict(nav_src.as_dict()) | {"acc_m": nav_src.acc, "n": 1,
                                          "weights": {nav_src.kind: 1.0}}
    base = fuse(bs)
    if not base:
        return None
    w_nav = 1.0 / (nav_src.acc ** 2)
    w_base = 1.0 / (base["acc_m"] ** 2)
    total = w_nav + w_base
    if total <= 0:
        return None
    share_nav = w_nav / total
    if share_nav > 1.0 - floor:          # 导航太强势 → 压到 95%，留给基线 5%
        share_nav = 1.0 - floor
    share_base = 1.0 - share_nav
    lat = share_nav * nav_src.lat + share_base * base["lat"]
    lon = share_nav * nav_src.lon + share_base * base["lon"]
    # 加权平均的方差 = Σ w_i² · σ_i²（权重和为 1）
    acc = math.sqrt(share_nav ** 2 * nav_src.acc ** 2 + share_base ** 2 * base["acc_m"] ** 2)
    return {"lat": lat, "lon": lon, "acc_m": max(acc, MIN_ACC_M),
            "n": 1 + len(bs),
            "weights": {nav_src.kind: round(share_nav, 4),
                        **{k: round(v * share_base, 4)
                           for k, v in base["weights"].items()}}}


def _valid(lat, lon) -> bool:
    try:
        return -90.0 <= float(lat) <= 90.0 and -180.0 <= float(lon) <= 180.0 \
            and not (float(lat) == 0.0 and float(lon) == 0.0)
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------- 本机定位探测（只读）

_MANUAL: Optional[LocSource] = None  # 手动录入的坐标（进程内；落盘走 set_manual_position）


def set_manual_position(lat: float, lon: float, acc: float = 100.0,
                        persist: bool = True) -> bool:
    """手动录入坐标（定位不可用时的兜底，也是"用户说了算"的通道）。"""
    global _MANUAL
    if not _valid(lat, lon):
        return False
    _MANUAL = LocSource(SRC_MANUAL, float(lat), float(lon), float(acc),
                        _("手动录入"))
    if persist:
        try:
            p = _state_dir() / "position.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(_MANUAL.as_dict(), ensure_ascii=False),
                         encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    return True


def _load_manual() -> Optional[LocSource]:
    global _MANUAL
    if _MANUAL is not None:
        return _MANUAL
    try:
        p = _state_dir() / "position.json"
        if p.exists():
            d = json.loads(p.read_text(encoding="utf-8"))
            if _valid(d.get("lat"), d.get("lon")):
                _MANUAL = LocSource(SRC_MANUAL, float(d["lat"]), float(d["lon"]),
                                    float(d.get("acc_m") or 100.0), _("手动录入（已保存）"))
                return _MANUAL
    except Exception:  # noqa: BLE001
        pass
    return None


_NUM = r"(-?\d+(?:\.\d+)?)"


def probe_android_location() -> List[LocSource]:
    """Android：读 `adb shell dumpsys location` 的最后已知位置（只读）。

    dumpsys 输出形如：
        last location=Location[fused 31.230416,121.473701 acc=20 et=+1d2h ...]
        Location[gps 31.230000,121.470000 acc=8 ...]
        Location[network 31.200000,121.500000 acc=1500 ...]
    """
    rc, out = common.run(["adb", "shell", "dumpsys", "location"], timeout=15, tail=200_000)
    if rc != 0 or not out:
        return []
    found: Dict[str, LocSource] = {}
    for m in re.finditer(
            r"Location\[(?P<prov>[a-zA-Z_]+)\s+" + _NUM + r"\s*,\s*" + _NUM +
            r"(?:[^\]]*?acc(?:uracy)?[=:]\s*" + _NUM + r")?", out):
        prov = m.group("prov").lower()
        lat, lon = float(m.group(2)), float(m.group(3))
        acc = float(m.group(4)) if m.group(4) else 0.0
        if not _valid(lat, lon):
            continue
        if prov in ("fused", "gps", "gnss"):
            kind, defacc = SRC_GNSS, 20.0
        elif prov == "network":
            kind, defacc = SRC_NET, DEFAULT_NET_ACC_M
        elif prov in ("cell", "cdma"):
            kind, defacc = SRC_CELL, DEFAULT_CELL_ACC_M
        else:
            continue
        src = LocSource(kind, lat, lon, acc or defacc, f"Android dumpsys: {prov}")
        # 同一 kind 保留精度更好的那个（dumpsys 里可能同时有 fused 与 gps）
        old = found.get(kind)
        if old is None or src.acc < old.acc:
            found[kind] = src
    return list(found.values())


def probe_linux_location() -> List[LocSource]:
    """Linux：只读探测可用的定位通道，返回**能拿到坐标**的源。

    诚实边界：Linux 上没有 modenmanager/geoclue 时**拿不到坐标**，此时返回空列表，
    由上层标注"本机未取到定位"，绝不凭 IP 编造一个坐标出来。
    """
    out: List[LocSource] = []
    # 基站：ModemManager
    rc, txt = common.run(["mmcli", "-m", "0", "--location-status"], timeout=8, tail=20_000)
    if rc == 0 and txt:
        m = re.search(r"3GPP.*?lac:\s*(\d+).*?cid:\s*(\d+)", txt, re.S | re.I)
        if m:
            # 只有 LAC/CID 没有基站经纬度库 → 报"基站可用但无坐标"
            out.append(LocSource(SRC_CELL, float("nan"), float("nan"),
                                 DEFAULT_CELL_ACC_M,
                                 _("基站可见（LAC=%s CID=%s），缺基站经纬度库，无坐标")
                                 % (m.group(1), m.group(2))))
    # 网络：geoclue / NetworkManager 的 Wi-Fi 扫描可证明"能定位"，但不等于有坐标
    rc2, _t2 = common.run(["systemctl", "is-active", "geoclue"], timeout=6, tail=2_000)
    if rc2 == 0:
        out.append(LocSource(SRC_NET, float("nan"), float("nan"),
                             DEFAULT_NET_ACC_M, _("GeoClue 服务运行中（需授权应用才有坐标）")))
    return [s for s in out if _valid(s.lat, s.lon)] or []


def probe_local_position() -> List[LocSource]:
    """按平台探测本机定位源（只读）。关掉 locate_enabled 时只返回手动坐标。"""
    if not switch_on("locate_enabled"):
        m = _load_manual()
        return [m] if m else []
    srcs: List[LocSource] = []
    try:
        srcs += probe_android_location()
    except Exception:  # noqa: BLE001
        pass
    try:
        srcs += probe_linux_location()
    except Exception:  # noqa: BLE001
        pass
    m = _load_manual()
    if m:
        srcs.append(m)
    # 去重：同 kind 留精度最好的
    best: Dict[str, LocSource] = {}
    for s in srcs:
        old = best.get(s.kind)
        if old is None or s.acc < old.acc:
            best[s.kind] = s
    return list(best.values())


# ---------------------------------------------------------------- 综合定位（核心逻辑）

def resolve_position(sources: Optional[List[LocSource]] = None) -> dict:
    """按你的口径解算位置：

    1. 先取**首选基线** = 网络 + 基站（两者都有则融合；只有一个就用它）。
    2. 若有**导航定位**（GNSS），则导航 + 首选基线**共同综合**。
    3. 两者偏差超过阈值 → 标"存疑"，两套结果都摆出来，不替用户判定。

    返回 dict：baseline / nav / final / disagreement_m / suspect / sources。
    """
    all_srcs = sources if sources is not None else probe_local_position()
    srcs = [s for s in all_srcs if _valid(s.lat, s.lon)]
    by_kind = {s.kind: s for s in srcs}

    prefer_on = switch_on("prefer_cell_network")
    fuse_on = switch_on("fuse_with_nav")

    base_srcs = [by_kind[k] for k in _PREFERRED if k in by_kind]
    baseline = fuse(base_srcs) if (prefer_on and base_srcs) else None
    if baseline is None and base_srcs:
        baseline = fuse(base_srcs)  # 关闭"首选"开关时仍算出基线用于展示差异

    nav_src = by_kind.get(SRC_GNSS)
    nav = nav_src.as_dict() if nav_src else None

    final: Optional[dict] = None
    suspect = False
    dis_m = 0.0

    if nav_src and baseline and fuse_on:
        dis_m = haversine_m(baseline["lat"], baseline["lon"], nav_src.lat, nav_src.lon)
        fused = fuse_with_floor(nav_src, base_srcs)
        final = dict(fused) if fused else None
        if final:
            final["mode"] = "nav+baseline"
        suspect = dis_m > DISAGREE_M
    elif nav_src:
        final = dict(nav_src.as_dict())
        final["acc_m"] = nav_src.acc
        final["n"] = 1
        final["mode"] = "nav-only"
        if baseline:
            dis_m = haversine_m(baseline["lat"], baseline["lon"], nav_src.lat, nav_src.lon)
            suspect = dis_m > DISAGREE_M
    elif baseline:
        final = dict(baseline)
        final["mode"] = "baseline-only"
    elif by_kind.get(SRC_MANUAL):
        m = by_kind[SRC_MANUAL]
        final = dict(m.as_dict())
        final["mode"] = "manual"

    return {
        # 全部探测到的源都列出（含"可见但无坐标"的），诚实呈现"探测到了什么"
        "sources": [s.as_dict() for s in all_srcs],
        "baseline": baseline,
        "nav": nav,
        "final": final,
        "disagreement_m": round(dis_m, 1),
        "suspect": suspect,
        "preferred_first": prefer_on,
        "fused_with_nav": bool(fuse_on and nav_src and baseline),
    }


def distance_to(pos: dict, lat: float, lon: float) -> Optional[float]:
    """从综合位置到目标点的距离（米）。无位置返回 None。"""
    if not pos or not _valid(lat, lon):
        return None
    f = pos.get("final")
    if not f:
        return None
    return haversine_m(f["lat"], f["lon"], float(lat), float(lon))


# ---------------------------------------------------------------- 预警事件

class Alert:
    """一条预警（字段对齐 CAP 1.2 的常用子集）。"""

    __slots__ = ("event", "severity", "urgency", "certainty", "headline",
                 "lat", "lon", "radius_m", "effective", "expires",
                 "instruction", "sender", "kind")

    def __init__(self, event: str, severity: str = "Unknown",
                 urgency: str = "Unknown", certainty: str = "Observed",
                 headline: str = "", lat: float = float("nan"),
                 lon: float = float("nan"), radius_m: float = 0.0,
                 effective: str = "", expires: str = "",
                 instruction: str = "", sender: str = "local",
                 kind: str = "other"):
        self.event = event or _("未命名事件")
        self.severity = severity if severity in SEVERITY_ORDER else "Unknown"
        self.urgency = urgency
        self.certainty = certainty
        self.headline = headline or self.event
        self.lat = lat
        self.lon = lon
        self.radius_m = max(float(radius_m or 0.0), 0.0)
        self.effective = effective
        self.expires = expires
        self.instruction = instruction
        self.sender = sender
        self.kind = kind if kind in SPEED_PROFILES else "other"

    def as_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__slots__}

    def has_center(self) -> bool:
        return _valid(self.lat, self.lon)


_ALERTS: List[Alert] = []


def alert_add(alert: Alert) -> bool:
    """本地登记一条预警（手动录入 / 订阅源解析后调用）。"""
    if len(_ALERTS) >= MAX_ALERTS:
        _ALERTS.pop(0)
    _ALERTS.append(alert)
    return True


def alert_add_dict(d: dict) -> bool:
    try:
        return alert_add(Alert(
            event=str(d.get("event") or ""),
            severity=str(d.get("severity") or "Unknown"),
            urgency=str(d.get("urgency") or "Unknown"),
            certainty=str(d.get("certainty") or "Observed"),
            headline=str(d.get("headline") or ""),
            lat=float(d.get("lat") if d.get("lat") is not None else float("nan")),
            lon=float(d.get("lon") if d.get("lon") is not None else float("nan")),
            radius_m=float(d.get("radius_m") or 0.0),
            effective=str(d.get("effective") or ""),
            expires=str(d.get("expires") or ""),
            instruction=str(d.get("instruction") or ""),
            sender=str(d.get("sender") or "local"),
            kind=str(d.get("kind") or "other"),
        ))
    except (TypeError, ValueError):
        return False


def alerts() -> List[Alert]:
    return list(_ALERTS)


def alert_clear() -> None:
    _ALERTS.clear()


def assess(alert: Alert, pos: Optional[dict] = None) -> dict:
    """评估一条预警对本机的影响。

    给出：距离（米）/ 是否落在影响半径内 / 剩余距离到边界 / 粗估到达时间。
    **粗估到达时间只是量级参考**，不是预报——报告里会明确写这句。
    """
    p = pos if pos is not None else resolve_position()
    final = (p or {}).get("final")
    res = {
        "event": alert.event,
        "severity": alert.severity,
        "severity_cn": SEVERITY_CN.get(alert.severity, alert.severity),
        "has_position": bool(final),
        "distance_m": None,
        "inside": None,
        "margin_to_edge_m": None,
        "eta_s": None,
        "accuracy_m": round(final.get("acc_m", 0.0), 1) if final else None,
        "note": "",
    }
    if not final or not alert.has_center():
        res["note"] = _("缺少位置或事件中心点，无法计算距离（只显示事件本身）")
        return res
    d = haversine_m(final["lat"], final["lon"], alert.lat, alert.lon)
    res["distance_m"] = round(d, 1)
    r = alert.radius_m
    if r > 0:
        res["inside"] = d <= r
        res["margin_to_edge_m"] = round(max(d - r, 0.0), 1)
    # 粗估到达：只在「在半径外且该类型有速度剖面」时给，按到边界的距离算
    if r > 0 and d > r:
        v = SPEED_PROFILES.get(alert.kind, SPEED_PROFILES["other"])
        res["eta_s"] = round((d - r) / v, 1)
        res["note"] = _("按%s的典型速度粗估，仅供量级参考，不是预报") \
            % SPEED_LABELS.get(alert.kind, SPEED_LABELS["other"])
    elif r > 0:
        res["note"] = _("你已在影响范围内，按指引行动，不要等下一次更新")
    return res


def assess_all(pos: Optional[dict] = None) -> List[dict]:
    p = pos if pos is not None else resolve_position()
    rows = [assess(a, p) for a in _ALERTS]
    # 按「离你由近到远」排——预警场景下距离就是优先级；无距离的排最后
    rows.sort(key=lambda r: (r["distance_m"] is None,
                             r["distance_m"] if r["distance_m"] is not None else 0.0))
    return rows


# ---------------------------------------------------------------- 应急功能

DEFAULT_KIT = [
    _("饮用水（每人每天 3 升，至少 3 天量）"),
    _("即食食品（压缩饼干、罐头，3 天量）"),
    _("手电筒 + 备用电池（或手摇发电）"),
    _("急救包（纱布、止血带、常用药、处方药）"),
    _("口哨（呼救比喊叫省力且传得远）"),
    _("充电宝（满电，配短线）"),
    _("收音机（接收官方广播，网络断了还能听）"),
    _("重要证件复印件 + 少量现金（断电时扫码付不了）"),
    _("口罩 / 防尘巾（火灾与地震扬尘）"),
    _("救生哨、手套、结实的鞋"),
]


def shelter_sort(points: List[dict], pos: Optional[dict] = None) -> List[dict]:
    """避险点按距离排序。points: [{name, lat, lon, note}]。"""
    if not switch_on("shelter_enabled"):
        return []
    p = pos if pos is not None else resolve_position()
    out = []
    for i, pt in enumerate(points):
        try:
            lat, lon = float(pt.get("lat")), float(pt.get("lon"))
        except (TypeError, ValueError):
            continue
        if not _valid(lat, lon):
            continue
        d = distance_to(p, lat, lon)
        out.append({"name": pt.get("name") or _("避险点 %d") % (i + 1),
                    "distance_m": None if d is None else round(d, 1),
                    "note": pt.get("note", "")})
    out.sort(key=lambda r: (r["distance_m"] is None, r["distance_m"] or 0))
    return out


def kit_check(owned: Optional[List[str]] = None) -> dict:
    """应急物资核对。owned = 已备好的条目名（与 DEFAULT_KIT 文案匹配）。"""
    if not switch_on("kit_enabled"):
        return {"enabled": False, "have": [], "missing": []}
    have = [k for k in DEFAULT_KIT if k in (owned or [])]
    missing = [k for k in DEFAULT_KIT if k not in (owned or [])]
    return {"enabled": True, "total": len(DEFAULT_KIT),
            "have": have, "missing": missing,
            "ratio": round(len(have) / len(DEFAULT_KIT), 3) if DEFAULT_KIT else 0.0}


def sos_text(pos: Optional[dict] = None, contacts: Optional[List[str]] = None,
             note: str = "", shelters: Optional[List[dict]] = None) -> str:
    """生成应急呼救文本。**只生成，绝不发送。**

    通道由用户自己选：贴到 meshchat 的全体广播（局域网内）、自己发短信、打电话……
    本层不碰任何发送动作，这是红线。
    """
    if not switch_on("sos_enabled"):
        return _("应急呼救文本已关闭（手动开关 sos_enabled=关）")
    p = pos if pos is not None else resolve_position()
    f = (p or {}).get("final")
    lines = [_("【应急呼救】"), ""]
    if f:
        acc = f.get("acc_m", 0.0)
        mode = f.get("mode", "")
        lines.append(_("我的位置：纬度 %.6f，经度 %.6f（精度约 %.0f 米，解算方式 %s）")
                     % (f["lat"], f["lon"], acc, mode))
    else:
        lines.append(_("我的位置：未能确定（请在安全处手动录入坐标，或说明周边标志物）"))
    if note:
        lines.append(_("情况：%s") % note)
    if shelters:
        near = shelters[0]
        if near.get("distance_m") is not None:
            lines.append(_("最近避险点：%s（约 %s）")
                         % (near["name"], _fmt_dist(near["distance_m"])))
        else:
            lines.append(_("最近避险点：%s（距离未知）") % near["name"])
    if contacts:
        lines.append(_("已通知：%s") % "、".join(contacts))
    alerts_near = [a for a in assess_all(p)][:3]
    if alerts_near:
        lines.append(_("当前预警：%s")
                     % "；".join(f"{a['event']}（{a['severity_cn'].strip()}）"
                                 for a in alerts_near))
    lines.append("")
    lines.append(_("本文本由 sysweeper 本地生成，未自动发送——请你自己选择发送方式。"))
    return "\n".join(lines)


# ---------------------------------------------------------------- 订阅源（默认关闭）

def feed_fetch(url: str, timeout: float = 8.0) -> Tuple[bool, str]:
    """拉取用户自己填的预警源。默认开关是**关**的，不主动联网。

    支持 JSON 数组 / 单个 CAP JSON 对象；XML CAP 只做最小字段提取。
    失败只报"未能获取"，**绝不编造预警内容**。
    """
    if not switch_on("feed_enabled"):
        return False, _("订阅源开关是关的（默认关闭）；先打开 feed_enabled 再拉。")
    if not url:
        return False, _("未配置订阅源地址")
    if not url.lower().startswith(("http://", "https://")):
        return False, _("只接受 http(s) 地址，拒绝其他协议（防止本地文件被当源读）")
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "sysweeper/emergency"})
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            raw = r.read(MAX_FEED_BYTES)
    except Exception as exc:  # noqa: BLE001
        return False, _("未能获取订阅源：%s（没有预警就是没有预警，不编造）") % type(exc).__name__
    txt = raw.decode("utf-8", "replace")
    n0 = len(_ALERTS)
    try:
        data = json.loads(txt)
        items = data if isinstance(data, list) else [data]
        for it in items:
            if isinstance(it, dict):
                alert_add_dict(it)
    except Exception:  # noqa: BLE001 - JSON 不成则试 XML
        for m in re.finditer(r"<event>(.*?)</event>", txt, re.S):
            alert_add_dict({"event": _strip_tags(m.group(1))})
        for m in re.finditer(r"<severity>(.*?)</severity>", txt, re.S):
            if _ALERTS:
                _ALERTS[-1].severity = _strip_tags(m.group(1)).capitalize()
    return True, _("已获取并登记 %d 条预警") % (len(_ALERTS) - n0)


def _strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").strip()


# ---------------------------------------------------------------- 报告

def _src_line(s: dict) -> str:
    if s.get("lat") is None or s.get("lon") is None:
        return f"  • {s['kind']:<8} {_('（可见但无坐标）'):<22} {s['detail']}"
    return (f"  • {s['kind']:<8} {s['lat']:.5f},{s['lon']:.5f} "
            f"±{s['acc_m']:.0f} m   {s['detail']}")


def position_report() -> Tuple[bool, str]:
    """定位综合报告：先网络+基站，有导航再共同综合。"""
    r = resolve_position()
    L = [_("定位与距离综合（口径：先网络 + 基站，检测到导航再共同综合）"), ""]
    if not r["sources"]:
        L.append(_("本机未取得任何定位源。"))
        L.append(_("可以做：在有导航的设备上开启定位后重探；或用手动录入坐标兜底。"))
        return True, "\n".join(L)
    L.append(_("可用定位源："))
    for s in r["sources"]:
        L.append(_src_line(s))
    L.append("")
    if r["baseline"]:
        b = r["baseline"]
        L.append(_("首选基线（网络 + 基站）：%.5f,%.5f ±%.0f m（源 %d 个，权重 %s）")
                 % (b["lat"], b["lon"], b["acc_m"], b["n"],
                    "、".join(f"{k}={v:.0%}" for k, v in b["weights"].items())))
    else:
        L.append(_("首选基线（网络 + 基站）：无（未取到网络/基站坐标）"))
    L.append(_("导航定位（GNSS）：%s")
             % (_("%.5f,%.5f ±%.0f m") % (r["nav"]["lat"], r["nav"]["lon"], r["nav"]["acc_m"])
                if r["nav"] else _("未检测到")))
    L.append("")
    f = r["final"]
    if f:
        mode_cn = {"nav+baseline": _("导航 + 首选基线共同综合"),
                   "nav-only": _("仅导航"),
                   "baseline-only": _("仅网络 + 基站基线"),
                   "manual": _("手动录入")}.get(f.get("mode", ""), f.get("mode", ""))
        L.append(_("最终采用：%.5f,%.5f ±%.0f m（%s）")
                 % (f["lat"], f["lon"], f.get("acc_m", 0.0), mode_cn))
        if r["fused_with_nav"]:
            L.append(_("两源偏差 %.0f m：%s")
                     % (r["disagreement_m"],
                        _("偏差超过 %.0f m，位置存疑——两套结果都在上面，请你判断")
                        % DISAGREE_M if r["suspect"] else _("两源一致")))
    else:
        L.append(_("最终采用：无法确定（没有可用坐标）"))
    return True, "\n".join(L)


def alert_report() -> Tuple[bool, str]:
    """预警评估报告：按距离排序，标注是否落在影响半径内。"""
    if not switch_on("alert_enabled"):
        return True, _("预警评估已关闭（手动开关 alert_enabled=关）")
    rows = assess_all()
    L = [_("预警评估（只评估，不自动报警）"), ""]
    if not rows:
        L.append(_("当前没有登记的预警。"))
        L.append(_("没有预警就是没有预警——本层不会凭空生成，也不会在未取到数据时猜测。"))
        return True, "\n".join(L)
    for r in rows:
        L.append(f"■ {r['event']}  [{r['severity_cn'].strip()}]")
        if r["distance_m"] is None:
            L.append(f"  {r['note']}")
        else:
            dist = _fmt_dist(r["distance_m"])
            if r["inside"] is None:
                L.append(_("  距你约 %s（事件未给影响半径，只给距离）") % dist)
            elif r["inside"]:
                L.append(_("  距中心约 %s：在影响范围内。%s") % (dist, r["note"]))
            else:
                eta = r["eta_s"]
                eta_s = _("，粗估还有约 %.0f 秒到达边界") % eta if eta else ""
                L.append(_("  距中心约 %s，影响半径外 %s%s")
                         % (dist, _fmt_dist(r["margin_to_edge_m"]), eta_s))
            if r["accuracy_m"]:
                L.append(_("  （你的位置精度约 %.0f m，距离值同量级误差）") % r["accuracy_m"])
        if r["note"] and r["distance_m"] is not None:
            L.append("  " + r["note"])
        L.append("")
    return True, "\n".join(L)


def emergency_report() -> Tuple[bool, str]:
    """总报告：定位 → 预警 → 应急功能与开关状态。"""
    L = [_("预警应急系统"), ""]
    ok1, t1 = position_report()
    L.append(t1)
    L.append("")
    ok2, t2 = alert_report()
    L.append(t2)
    L.append("")
    L.append(_("—— 手动开关 ——"))
    st = switches()
    for k, (dflt, desc) in SWITCHES.items():
        L.append(f"  [{'开' if st.get(k, dflt) else '关'}] {k}: {desc}")
    L.append("")
    L.append(_("改法：set_switch('开关名', True/False)；例如关掉联网订阅 "
               "set_switch('feed_enabled', False)。"))
    return True, "\n".join(L)


def capabilities_report() -> Tuple[bool, str]:
    """本层能力自检：哪些真能用、哪些依赖缺失（xnu-hd2 式诚实声明）。"""
    srcs = probe_local_position()
    L = [_("预警应急能力自检"), ""]
    L.append(_("定位源探测：%s") % (_("取到 %d 个") % len(srcs) if srcs else _("未取到（只读命令不可用或不匹配）")))
    L.append(_("  · Android：adb shell dumpsys location（只读，取 fused/gps/network 最后已知位置）"))
    L.append(_("  · Linux：mmcli / geoclue 只读探测（**没有基站经纬度库就拿不到坐标，绝不凭 IP 编造**）"))
    L.append(_("  · 兜底：手动录入坐标（set_manual_position）"))
    L.append("")
    L.append(_("已登记预警：%d 条（上限 %d）") % (len(_ALERTS), MAX_ALERTS))
    L.append(_("联网订阅：默认关闭（开关 feed_enabled=%s）")
             % (_("开") if switch_on("feed_enabled") else _("关")))
    L.append("")
    L.append(_("本层**不做**的事（红线）：自动报警 / 拨号 / 发短信 / 自动发送任何内容；"
               "SOS 只生成文本。"))
    return True, "\n".join(L)
