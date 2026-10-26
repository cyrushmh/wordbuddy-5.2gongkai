"""设备长期使用保护子系统（durability）：只读传感器采集 + 保养/优化引擎。

设计「只读、最小权限、不写任何设备寄存器」：

- 传感器采集：跨平台读取电池温/循环/健康、CPU/表面温度、存储 SMART、运行时长、
  环境温湿度（若有外部传感器）。任一项读不到即标记「本机未提供」，优雅降级，绝不伪造。
- 引擎层（durability_profile / sensor_health_score / build_maintenance_plan /
  auto_optimize_suggestions）是**纯函数**，只吃显式参数、不碰系统，便于单测。
  每条建议都回链知识库 key（durability_docs.json），做到「建议有出处」。
- 写操作（充电上限、拆机清灰、系统修复）一律**只给官方工具指引，不代执行**——
  这是本项目的硬红线（只读、不自动重启、不执行外部代码），也契合用户「个人行为在
  完全图形界面控制操作」的诉求：工具出方案，用户点官方工具做。

平台判定：linux / macos / windows / bsd / android / ios，按 sys.platform 与特征探测。
"""

from __future__ import annotations

import json
import os
import re
import sys

from . import common


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "durability_docs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:  # noqa: BLE001
        return {}


REFS = _load_refs()


def reference(key: str) -> dict:
    """返回某 durability 主题的文档参考（含 protocols 与 interfaces）。"""
    return REFS.get(key, {})


def reference_all() -> dict:
    """返回全部 durability 主题文档参考。"""
    return REFS


# --------------------------------------------------------------------------- #
# 平台判定                                                                     #
# --------------------------------------------------------------------------- #

def detect_platform() -> str:
    """判定当前平台：linux/macos/windows/bsd/android/ios。"""
    p = sys.platform
    if p.startswith("linux"):
        # android 检测：存在 /system/build.prop 且无桌面常见路径
        if os.path.exists("/system/build.prop") and not os.path.exists("/usr"):
            return "android"
        return "linux"
    if p == "darwin":
        return "macos"
    if p.startswith("win") or p == "cygwin":
        return "windows"
    if p in ("freebsd", "openbsd", "netbsd", "dragonfly"):
        return "bsd"
    if p == "ios" or p == "darwin" and os.path.exists("/System/Library/CoreServices"):
        return "ios"
    return "linux"


# --------------------------------------------------------------------------- #
# 只读传感器采集（跨平台，优雅降级）                                          #
# 每个采集函数返回 (ok, data)；ok=False 时 data 为说明文字。                   #
# --------------------------------------------------------------------------- #

def _linux_battery() -> dict:
    """解析 /sys/class/power_supply/BAT*/uevent（Linux 只读 sysfs）。"""
    base = "/sys/class/power_supply"
    if not os.path.isdir(base):
        return {}
    for name in sorted(os.listdir(base)):
        if not name.startswith("BAT"):
            continue
        ue = os.path.join(base, name, "uevent")
        if not os.path.exists(ue):
            continue
        kv = {}
        try:
            with open(ue, encoding="utf-8") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        kv[k] = v
        except OSError:
            continue
        d: dict = {}
        if "POWER_SUPPLY_TEMP" in kv:
            try:
                d["battery_temp_c"] = int(kv["POWER_SUPPLY_TEMP"]) / 10.0
            except ValueError:
                pass
        if "POWER_SUPPLY_CYCLE_COUNT" in kv:
            try:
                d["battery_cycle"] = int(kv["POWER_SUPPLY_CYCLE_COUNT"])
            except ValueError:
                pass
        if "POWER_SUPPLY_HEALTH" in kv:
            d["battery_health_str"] = kv["POWER_SUPPLY_HEALTH"]
        if "POWER_SUPPLY_CAPACITY" in kv:
            try:
                d["battery_capacity_pct"] = int(kv["POWER_SUPPLY_CAPACITY"])
            except ValueError:
                pass
        cf, cfd = kv.get("POWER_SUPPLY_CHARGE_FULL"), kv.get("POWER_SUPPLY_CHARGE_FULL_DESIGN")
        if cf and cfd:
            try:
                cfv, cfdv = int(cf), int(cfd)
                if cfdv:
                    d["battery_health_pct"] = round(cfv / cfdv * 100, 1)
            except ValueError:
                pass
        d["battery_status"] = kv.get("POWER_SUPPLY_STATUS", "")
        return d
    return {}


def read_battery() -> tuple:
    """读电池电量/温度/健康/循环（Linux sysfs，其余平台降级）。"""
    plat = detect_platform()
    if plat == "linux":
        d = _linux_battery()
        if d:
            return True, d
        return False, "未找到 /sys/class/power_supply/BAT*（无电池或台式机）"
    if plat == "macos":
        return False, "macOS 需 IOKit 私有接口（诊断用），本工具不越权读取"
    if plat == "windows":
        return False, "Windows 经 WMI/Windows.Devices.Power.Battery 只读取，沙箱未提供 PowerShell"
    return False, f"平台 {plat} 暂无内置电池只读接口"


def read_thermal() -> tuple:
    """读温区温度（Linux thermal sysfs，其余平台降级）。"""
    plat = detect_platform()
    if plat == "linux":
        temps = {}
        try:
            for z in sorted(os.listdir("/sys/class/thermal")):
                if not z.startswith("thermal_zone"):
                    continue
                tp = os.path.join("/sys/class/thermal", z, "temp")
                if os.path.exists(tp):
                    try:
                        with open(tp, encoding="utf-8") as f:
                            temps[z] = int(f.read().strip()) / 1000.0
                    except (OSError, ValueError):
                        continue
        except OSError:
            return False, "未找到 /sys/class/thermal"
        if temps:
            return True, temps
        return False, "无可用 thermal zone"
    return False, f"平台 {plat} 暂无内置温度只读接口（可用外部温感器接入）"


def read_storage() -> tuple:
    """读存储剩余/SMART（Linux 经 smartctl/nvme，需权限，降级友好）。"""
    plat = detect_platform()
    if plat == "linux":
        # 容量占用（任何用户可读）
        du = common.disk_usage("/")
        info = {"root_used_pct": round(du["used"] / du["total"] * 100, 1)} if du else {}
        # SMART（需 root/设备权限，失败即降级）
        rc, out = common.run("which smartctl nvme 2>/dev/null")
        if rc == 0 and (out or "").strip():
            info["smart_tool"] = (out or "").strip().split()[0]
            info["smart_note"] = "smartctl/nvme 可用，详读需 root（本工具只列工具名，不读盘）"
        else:
            info["smart_note"] = "未装 smartctl/nvme（装后可用只读 SMART）"
        return True, info
    return False, f"平台 {plat} 暂无内置存储只读接口"


def read_uptime() -> tuple:
    """读系统运行时长（Linux /proc/uptime，其余平台降级）。"""
    plat = detect_platform()
    if plat == "linux" and os.path.exists("/proc/uptime"):
        try:
            with open("/proc/uptime", encoding="utf-8") as f:
                secs = float(f.read().split()[0])
            return True, {"uptime_days": round(secs / 86400.0, 2)}
        except (OSError, ValueError):
            return False, "读取 /proc/uptime 失败"
    return False, f"平台 {plat} 暂无内置运行时长只读接口"


def read_env() -> tuple:
    """读环境温湿度（多数设备无内置湿度传感器，降级为外部传感器指引）。"""
    rc, out = common.run("which sensors 2>/dev/null")
    if rc == 0 and (out or "").strip():
        return True, {"env_tool": "lm_sensors 可用（部分主板暴露温/风扇）",
                       "humidity": None, "humidity_note": "lm_sensors 通常不含湿度，湿度需外部温湿度计"}
    return False, "本机无内置环境湿度传感器；可用外部蓝牙/USB 温湿度计数据接入本工具比对 ASHRAE 包络"


def read_weather_climate() -> tuple:
    """只读感知天气/气候（主板 hwmon 温感 / lm-sensors；湿度多无，降级外部接入）。

    这是「整体通过感应器硬件组件感知环境天气和气候」的落点：优先读 /sys/class/hwmon
    温感、再用 lm-sensors 输出解析；读不到即标记「本机未提供」，绝不伪造。
    """
    temps = []
    base = "/sys/class/hwmon"
    if os.path.isdir(base):
        try:
            for d in sorted(os.listdir(base)):
                for f in sorted(os.listdir(os.path.join(base, d))):
                    if f.startswith("temp") and f.endswith("_input"):
                        fp = os.path.join(base, d, f)
                        try:
                            with open(fp, encoding="utf-8") as fh:
                                temps.append(int(fh.read().strip()) / 1000.0)
                        except (OSError, ValueError):
                            continue
        except OSError:
            pass
    rc, out = common.run("which sensors 2>/dev/null")
    if rc == 0 and (out or "").strip():
        import re as _re
        for m in _re.finditer(r"([+-]?\d+\.\d+)°?C", out or ""):
            try:
                temps.append(float(m.group(1)))
            except ValueError:
                pass
    if temps:
        ambient = round(max(temps), 1)  # 取最高温感近似环境与表面温度
        return True, {"ambient_temp_c": ambient, "humidity": None,
                      "humidity_note": "hwmon/lm-sensors 通常不含湿度；湿度需外部温湿度计接入"}
    return False, "本机无内置温/湿传感器；可用外部蓝牙/USB 温湿度计数据接入本工具比对 ASHRAE 包络"


def read_comms() -> tuple:
    """只读感知通信能力（网卡 operstate /sys/class/net，绝不外发任何包）。

    仅读链路层 up/down，不解析路由、不发 DNS 查询；上层可达性另由 netauth/netlink 判定。
    """
    base = "/sys/class/net"
    if not os.path.isdir(base):
        return False, "本机无 /sys/class/net（非 Linux 或容器隔离）"
    up, down = [], []
    try:
        for iface in sorted(os.listdir(base)):
            if iface == "lo":
                continue
            op = os.path.join(base, iface, "operstate")
            if os.path.exists(op):
                try:
                    st = open(op, encoding="utf-8").read().strip()
                except OSError:
                    st = ""
                (up if st == "up" else down).append(iface)
    except OSError:
        return False, "读取 /sys/class/net 失败"
    if up:
        return True, {"links_up": up, "links_down": down, "reachable": True,
                      "note": "有网络接口处于 up（链路层连通，上层仍需 DNS/路由/证书）"}
    return False, f"未发现 up 的网络接口（down={down}）；通信能力可能中断"


def sensor_snapshot() -> dict:
    """聚合所有传感器采集，返回 {reading 名: (available, value/原因)}。"""
    snap: dict = {}
    for name, fn in (("battery", read_battery), ("thermal", read_thermal),
                     ("storage", read_storage), ("uptime", read_uptime),
                     ("env", read_env), ("weather_climate", read_weather_climate),
                     ("comms", read_comms)):
        ok, data = fn()
        snap[name] = {"available": ok, "data": data}
    return snap


# CLI / GUI 遍历用：探测函数名 + 中文标签
PROBES = (
    ("read_battery", "电池（电量/温度/健康/循环，只读 sysfs/IOKit）"),
    ("read_thermal", "温度（CPU/表面温区，只读 thermal sysfs）"),
    ("read_storage", "存储（剩余/SMART 工具，只读）"),
    ("read_uptime", "运行时长（/proc/uptime，只读）"),
    ("read_env", "环境（温湿度传感器，缺则降级外部接入）"),
    ("read_weather_climate", "天气/气候（主板 hwmon / lm-sensors 温感，缺则降级外部）"),
    ("read_comms", "通信能力（网卡 operstate 只读，绝不外发）"),
)


def environment_report() -> list:
    """返回本机 durability 传感器可用性概览（✓ 可用 / ✗ 未提供/降级）。"""
    lines = ["设备长期使用保护 · 传感器可用性："]
    for fn_name, label in PROBES:
        ok, msg = globals()[fn_name]()
        mark = "✓" if ok else "✗"
        lines.append(f"   {mark} {label}")
        if not ok:
            lines.append(f"       {msg}")
    return lines


def durability_doc_list() -> list:
    """返回 durability 主题文档参考清单（供 CLI/GUI 展示）。"""
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
# 引擎层（纯函数，不碰系统，便于单测）。每条建议回链知识库 key。                #
# --------------------------------------------------------------------------- #

def _norm_intensity(usage_intensity: str) -> int:
    return {"light": 1, "moderate": 2, "heavy": 3}.get((usage_intensity or "moderate").lower(), 2)


def durability_profile(usage_intensity: str = "moderate",
                       longevity_years: int = 4,
                       env_tags: list | None = None) -> dict:
    """由「使用量 + 期望使用年限 + 环境标签」推导保养目标包络。

    usage_intensity: light/moderate/heavy（设备使用量）
    longevity_years: 期望使用年限（生活综合水平决定的长期使用需求）
    env_tags: 环境标签，如 high_temp/high_humidity/dusty/mobile/plugged_in
    返回保养目标（充电上限/温湿预算/清灰与备份周期/目标循环）。
    """
    intensity = _norm_intensity(usage_intensity)
    tags = set(env_tags or [])
    high_temp = "high_temp" in tags
    high_hum = "high_humidity" in tags
    dusty = "dusty" in tags
    mobile = "mobile" in tags
    plugged = "plugged_in" in tags

    # 充电上限：长期插电或期望用得久 → 80% 上限最省寿
    ceiling = 80 if (plugged or longevity_years >= 4) else 100
    # 温度预算：本就高温环境更严
    temp_budget = 25 if high_temp else 27
    # 湿度预算：高湿环境收紧防凝露/霉变
    rh_low = 35 if high_hum else 40
    rh_high = 50 if high_hum else 60
    # 清灰周期：多尘/移动设备更频
    clean_cadence = "6-12 月" if (dusty or mobile) else "12 月"
    # 备份周期：用得越狠越频
    backup_cadence = "季度" if intensity >= 2 else "半年"
    # 目标循环：用越久要求衰减越慢
    target_cycle = 1000 if longevity_years <= 3 else 800

    notes = []
    if ceiling == 80:
        notes.append("长期插电/期望长用 → 建议 80% 充电上限（charge_strategy）")
    if high_temp or high_hum:
        notes.append("高温/高湿环境 → 收紧温湿预算，加强通风除湿（ashrae_thermal/humidity_ingress）")
    if dusty or mobile:
        notes.append("多尘/移动场景 → 加密清灰、避免风道堵塞（maintenance_schedule/humidity_ingress）")

    return {
        "usage_intensity": usage_intensity,
        "intensity_score": intensity,
        "longevity_years": longevity_years,
        "env_tags": sorted(tags),
        "charge_ceiling_pct": ceiling,
        "temp_budget_c": temp_budget,
        "rh_budget": [rh_low, rh_high],
        "clean_cadence": clean_cadence,
        "backup_cadence": backup_cadence,
        "target_cycle": target_cycle,
        "notes": notes,
    }


def sensor_health_score(readings: dict | None = None) -> dict:
    """对一组传感器读数做健康评分（0-100/项）+ 总评 + 风险级，回链知识库 key。

    readings 可含：battery_temp_c / battery_health_pct / battery_cycle /
    battery_status / storage_used_pct / storage_life_pct(=SMART 已用%) /
    ambient_rh / ambient_temp_c / thermal_max_c / uptime_days
    缺项不参与评分（不伪造）。
    """
    r = readings or {}
    comps: dict = {}

    bt = r.get("battery_temp_c")
    if bt is not None:
        if bt <= 35:
            comps["battery_temp"] = (100, "正常", "battery_lithium")
        elif bt <= 45:
            comps["battery_temp"] = (70, "偏高，注意散热", "battery_lithium")
        else:
            comps["battery_temp"] = (40, "过高，停高负载并降温", "battery_lithium")

    bh = r.get("battery_health_pct")
    if bh is not None:
        if bh >= 80:
            comps["battery_health"] = (100, "健康", "battery_lithium")
        elif bh >= 60:
            comps["battery_health"] = (70, "衰减中，浅充浅放", "battery_lithium")
        else:
            comps["battery_health"] = (40, "明显衰减，考虑更换", "battery_lithium")

    cyc = r.get("battery_cycle")
    if cyc is not None:
        if cyc < 500:
            comps["battery_cycle"] = (100, "循环少", "battery_lithium")
        elif cyc < 800:
            comps["battery_cycle"] = (80, "中等循环", "battery_lithium")
        elif cyc < 1000:
            comps["battery_cycle"] = (60, "接近设计寿命", "battery_lithium")
        else:
            comps["battery_cycle"] = (40, "超设计寿命", "battery_lithium")

    su = r.get("storage_used_pct")
    if su is not None:
        if su <= 85:
            comps["storage_space"] = (100, "余量充足", "storage_smart")
        elif su <= 95:
            comps["storage_space"] = (70, "偏满，不利磨损均衡", "storage_smart")
        else:
            comps["storage_space"] = (40, "过满，恶化写放大", "storage_smart")

    sl = r.get("storage_life_pct")  # SMART Percentage Used
    if sl is not None:
        if sl <= 10:
            comps["storage_life"] = (100, "寿命余量足", "storage_smart")
        elif sl <= 30:
            comps["storage_life"] = (80, "轻度磨损", "storage_smart")
        elif sl <= 60:
            comps["storage_life"] = (60, "中度磨损", "storage_smart")
        else:
            comps["storage_life"] = (40, "重度磨损，准备备份", "storage_smart")

    rh = r.get("ambient_rh")
    if rh is not None:
        if 40 <= rh <= 60:
            comps["ambient_rh"] = (100, "湿度适宜", "ashrae_thermal")
        elif rh < 40:
            comps["ambient_rh"] = (70, "偏干，静电风险", "ashrae_thermal")
        elif rh <= 80:
            comps["ambient_rh"] = (70, "偏湿，注意通风", "ashrae_thermal")
        else:
            comps["ambient_rh"] = (40, "过湿，霉变/短路风险", "humidity_ingress")

    at = r.get("ambient_temp_c")
    if at is not None:
        if 18 <= at <= 27:
            comps["ambient_temp"] = (100, "温区适宜", "ashrae_thermal")
        elif at < 18 or at <= 32:
            comps["ambient_temp"] = (80, "略偏，可接受", "ashrae_thermal")
        elif at <= 35:
            comps["ambient_temp"] = (60, "偏高，加速老化", "ashrae_thermal")
        else:
            comps["ambient_temp"] = (40, "过高，立即降温", "ashrae_thermal")

    tm = r.get("thermal_max_c")
    if tm is not None:
        if tm <= 80:
            comps["thermal_max"] = (100, "温度可控", "thermal_throttle")
        elif tm <= 90:
            comps["thermal_max"] = (70, "偏高，清灰通风", "thermal_throttle")
        elif tm <= 100:
            comps["thermal_max"] = (50, "接近上限，长期伤焊点", "thermal_throttle")
        else:
            comps["thermal_max"] = (30, "触顶节流，封口散热", "thermal_throttle")

    up = r.get("uptime_days")
    if up is not None:
        if up <= 30:
            comps["uptime"] = (100, "正常", "maintenance_schedule")
        elif up <= 90:
            comps["uptime"] = (80, "较久未重启", "maintenance_schedule")
        else:
            comps["uptime"] = (60, "长期不重启，建议补更新备份", "maintenance_schedule")

    scores = [v[0] for v in comps.values()]
    overall = round(sum(scores) / len(scores)) if scores else None
    risk = ("low" if overall is not None and overall >= 80
            else "mid" if overall is not None and overall >= 60
            else "high")
    return {"components": comps, "overall": overall, "risk": risk,
            "scored_items": len(comps)}


def build_maintenance_plan(profile: dict | None = None,
                           sensor_health: dict | None = None,
                           env_tags: list | None = None) -> list:
    """由目标包络 + 健康分 + 环境，生成保养待办清单（每项回链知识库 key）。

    每项：{id, title, cadence, action, rationale}
    action: readonly（本工具可只读核查）/ guidance（指引用户走官方工具）
    """
    prof = profile or durability_profile()
    sh = sensor_health or sensor_health_score()
    tags = set(env_tags or prof.get("env_tags", []))
    risk = sh.get("risk", "low")

    items = []

    items.append({
        "id": "backup",
        "title": "核对备份完整性",
        "cadence": prof.get("backup_cadence", "季度"),
        "action": "guidance",
        "rationale": "maintenance_schedule",
    })
    items.append({
        "id": "software_update",
        "title": "检查并安装系统安全补丁",
        "cadence": "月度/随发布",
        "action": "readonly",
        "rationale": "maintenance_schedule",
    })
    items.append({
        "id": "disk_space",
        "title": "清理缓存/日志，保留 ≥10-15% 空闲",
        "cadence": "月度",
        "action": "readonly",
        "rationale": "storage_smart",
    })
    items.append({
        "id": "clean_dust",
        "title": "外部清灰（风扇/接口软刷气吹）",
        "cadence": prof.get("clean_cadence", "12 月"),
        "action": "guidance",
        "rationale": "maintenance_schedule",
    })
    if prof.get("charge_ceiling_pct", 100) == 80:
        items.append({
            "id": "charge_ceiling",
            "title": "在 OEM 控制中心设 80% 充电上限",
            "cadence": "一次性设置",
            "action": "guidance",
            "rationale": "charge_strategy",
        })
    if "high_humidity" in tags or "high_temp" in tags:
        items.append({
            "id": "dehumidify",
            "title": "高湿/高温环境加强通风除湿、配防潮箱",
            "cadence": "持续",
            "action": "guidance",
            "rationale": "humidity_ingress",
        })
    if risk in ("mid", "high"):
        items.append({
            "id": "battery_check",
            "title": "评估电池健康（循环/最大容量），必要时更换",
            "cadence": "半年",
            "action": "readonly",
            "rationale": "battery_lithium",
        })
    return items


def auto_optimize_suggestions(profile: dict | None = None,
                              sensor_health: dict | None = None,
                              env_tags: list | None = None) -> list:
    """由目标包络 + 健康分，生成自动优化建议（每条回链知识库 key）。

    每项：{id, title, severity, action_type, rationale}
    severity: info/notice/warn
    action_type: readonly（本工具可做只读核查）/ guidance（指引用户操作）
    """
    prof = profile or durability_profile()
    sh = sensor_health or sensor_health_score()
    comps = sh.get("components", {})
    tags = set(env_tags or prof.get("env_tags", []))
    sug = []

    # 电池温度
    bt = comps.get("battery_temp")
    if bt and bt[0] < 100:
        sev = "warn" if bt[0] <= 40 else "notice"
        sug.append({"id": "batt_temp", "title": f"电池温度{bt[1]}",
                     "severity": sev, "action_type": "guidance",
                     "rationale": "battery_lithium"})
    # 电池健康
    bh = comps.get("battery_health")
    if bh and bh[0] < 100:
        sug.append({"id": "batt_health", "title": f"电池{bh[1]}",
                     "severity": "notice" if bh[0] >= 60 else "warn",
                     "action_type": "guidance", "rationale": "battery_lithium"})
    # 存储余量
    ss = comps.get("storage_space")
    if ss and ss[0] < 100:
        sug.append({"id": "disk_full", "title": f"存储{ss[1]}",
                     "severity": "notice" if ss[0] >= 70 else "warn",
                     "action_type": "readonly", "rationale": "storage_smart"})
    # 环境湿度
    rh = comps.get("ambient_rh")
    if rh and rh[0] < 100:
        sug.append({"id": "rh", "title": f"环境湿度{rh[1]}",
                     "severity": "notice" if rh[0] >= 70 else "warn",
                     "action_type": "guidance", "rationale": "ashrae_thermal"})
    # 温区
    tm = comps.get("thermal_max")
    if tm and tm[0] < 100:
        sug.append({"id": "thermal", "title": f"设备温度{tm[1]}",
                     "severity": "notice" if tm[0] >= 70 else "warn",
                     "action_type": "guidance", "rationale": "thermal_throttle"})
    # 长期插电 → 充电策略
    if prof.get("charge_ceiling_pct", 100) == 80:
        sug.append({"id": "charge_opt", "title": "长期插电：启用优化/自适应充电或设 80% 上限",
                     "severity": "info", "action_type": "guidance",
                     "rationale": "charge_strategy"})
    # 高湿环境 → 防水
    if "high_humidity" in tags or "high_temp" in tags:
        sug.append({"id": "env_guard", "title": "温湿偏高：避开暴晒/封闭散热、防凝露",
                     "severity": "info", "action_type": "guidance",
                     "rationale": "humidity_ingress"})
    return sug


def auto_climate_tags(readings: dict | None = None) -> list:
    """由传感器读数自动推导环境标签（天气/气候感知），与用户显式标签合并。"""
    r = readings or {}
    tags = []
    at = r.get("ambient_temp_c")
    if at is not None and at >= 30:
        tags.append("high_temp")
    rh = r.get("ambient_rh")
    if rh is not None and rh >= 70:
        tags.append("high_humidity")
    return tags


def protect_assets(profile: dict | None = None,
                   sensor_health: dict | None = None,
                   cert_summary: dict | None = None,
                   comms_summary: dict | None = None) -> list:
    """保护关键资产 / 个人数据 / 通信能力（纯函数，回链知识库 key，不碰系统）。

    输入：
      - profile / sensor_health：来自 durability 引擎
      - cert_summary：来自 native.cert.cert_status_summary()（只读；含 tpm_present/
        keystore_present/openssl_eol/min_cert_days；绝不读私钥）
      - comms_summary：来自 read_comms() 或 netauth/netlink（含 reachable）
    每项：{id, title, cadence, action, rationale}，rationale 指向 cert/durability 知识库 key。
    """
    prof = profile or durability_profile()
    sh = sensor_health or sensor_health_score()
    items = []

    # 关键资产 / 个人数据：备份（始终，源自 maintenance_schedule）
    items.append({
        "id": "protect_backup",
        "title": "关键资产与个人数据备份（≥2 份、跨介质本地+异地/云）",
        "cadence": prof.get("backup_cadence", "季度"),
        "action": "guidance",
        "rationale": "maintenance_schedule",
    })

    # 通信能力：链路中断即提示排查（绝不外发，只给排查指引）
    cs = comms_summary or {}
    if cs.get("reachable") is False:
        items.append({
            "id": "protect_comms",
            "title": "通信能力异常：排查网卡/天线 → 路由/DNS → 证书链",
            "cadence": "即时",
            "action": "guidance",
            "rationale": "netlink",
        })
    elif cs.get("reachable") is None:
        items.append({
            "id": "protect_comms_hint",
            "title": "当前未探测到通信能力状态；建议保持证书链有效以保障加密通信",
            "cadence": "持续",
            "action": "guidance",
            "rationale": "netlink",
        })

    # 证书 / 密钥：硬件信任根 + EOL 加密库 + 临近过期
    if cert_summary:
        if not cert_summary.get("tpm_present") and not cert_summary.get("keystore_present"):
            items.append({
                "id": "protect_keyroot",
                "title": "启用硬件信任根/平台密钥库保护密钥（TPM/Secure Enclave/Keystore）",
                "cadence": "一次性",
                "action": "guidance",
                "rationale": "tpm",
            })
        if cert_summary.get("openssl_eol"):
            items.append({
                "id": "protect_crypto",
                "title": "升级 EOL 开源加密库（OpenSSL 等停止安全支持的分支）",
                "cadence": "随发布",
                "action": "guidance",
                "rationale": "openssl",
            })
        mcd = cert_summary.get("min_cert_days")
        if mcd is not None and mcd <= 30:
            items.append({
                "id": "protect_cert",
                "title": "续期临近过期证书（优先 ACME 自动续期，避免通信中断）",
                "cadence": "即时",
                "action": "guidance",
                "rationale": "acme",
            })
        if not cert_summary.get("device_cert_present"):
            items.append({
                "id": "protect_device_id",
                "title": "无设备身份证书（IDevID）：高价值设备启用硬件背书身份以增强互信",
                "cadence": "按需",
                "action": "guidance",
                "rationale": "device_cert",
            })

    # 健康分差 → 优先保护数据（先备份再处理硬件）
    if sh.get("risk") in ("mid", "high"):
        items.append({
            "id": "protect_prior_backup",
            "title": "设备健康分偏低：优先完成备份再评估硬件更换",
            "cadence": "即时",
            "action": "guidance",
            "rationale": "maintenance_schedule",
        })
    return items


def collect_readings() -> dict:
    """把各传感器探针的可用读数拍平成 sensor_health_score 能吃的 readings 字典。

    读不到的项直接不出现（不伪造）；引擎对缺项自动跳过。
    """
    r: dict = {}
    ok, b = read_battery()
    if ok and isinstance(b, dict):
        for k in ("battery_temp_c", "battery_health_pct", "battery_cycle", "battery_status"):
            if k in b:
                r[k] = b[k]
    ok, t = read_thermal()
    if ok and isinstance(t, dict):
        temps = [v for v in t.values() if isinstance(v, (int, float))]
        if temps:
            r["thermal_max_c"] = max(temps)
    ok, s = read_storage()
    if ok and isinstance(s, dict) and "root_used_pct" in s:
        r["storage_used_pct"] = s["root_used_pct"]
    ok, u = read_uptime()
    if ok and isinstance(u, dict) and "uptime_days" in u:
        r["uptime_days"] = u["uptime_days"]
    ok, wc = read_weather_climate()
    if ok and isinstance(wc, dict) and "ambient_temp_c" in wc:
        r["ambient_temp_c"] = wc["ambient_temp_c"]
    ok, cm = read_comms()
    if ok and isinstance(cm, dict) and cm.get("reachable"):
        r["comms_up"] = True
    return r


def durability_report(usage_intensity: str = "moderate",
                      longevity_years: int = 4,
                      env_tags: list | None = None,
                      cert_summary: dict | None = None,
                      comms_summary: dict | None = None) -> tuple:
    """端到端生成一份可读性保护报告（无参可调用，供任务/CLI/GUI）。

    流程：采集可读传感器 → **自动感知天气/气候**（hwmon/lm-sensors）→ 推导目标包络 →
    健康评分 → 优化建议 + 保养清单；并融合**证书/加密**与**通信能力**状态，给出
    「关键资产 / 个人数据 / 通信能力」保护段。每条建议/待办都回链知识库 key。

    cert_summary / comms_summary 缺省时由本函数只读懒取（不读私钥、绝不外发）。
    """
    readings = collect_readings()
    # 自动气候感知：把传感器读出的温/湿并入环境标签，与用户显式标签合并
    auto_tags = auto_climate_tags(readings)
    merged_env = list(env_tags or []) + auto_tags
    prof = durability_profile(usage_intensity, longevity_years, merged_env)
    sh = sensor_health_score(readings)
    plan = build_maintenance_plan(prof, sh, merged_env)
    sug = auto_optimize_suggestions(prof, sh, merged_env)

    # 懒取证书/通信状态（只读）：证书绝不读私钥；通信只判链路不外出
    if cert_summary is None:
        try:
            from . import cert as _nc
            cert_summary = _nc.cert_status_summary()
        except Exception:  # noqa: BLE001
            cert_summary = None
    if comms_summary is None:
        ok, cm = read_comms()
        comms_summary = cm if (ok and isinstance(cm, dict)) else {"reachable": None,
                                                                  "note": "未探测"}
    protect = protect_assets(prof, sh, cert_summary, comms_summary)

    lines = ["== 设备长期使用保护报告 =="]
    lines.append(f"使用量={usage_intensity}  期望年限={longevity_years}年  环境={merged_env or '默认'}"
                 + (f"（自动气候感知: {auto_tags}）" if auto_tags else ""))
    lines.append(f"目标: 充电上限={prof['charge_ceiling_pct']}%  温预算={prof['temp_budget_c']}°C  "
                 f"湿预算={prof['rh_budget']}  清灰={prof['clean_cadence']}  备份={prof['backup_cadence']}")
    lines.append(f"健康总评={sh['overall']}  风险={sh['risk']}  (评分项 {sh['scored_items']})")
    if sh["components"]:
        lines.append("分项评分:")
        for k, (sc, desc, kb) in sh["components"].items():
            lines.append(f"  · {k}: {sc} {desc}  [{kb}]")
    else:
        lines.append("分项评分: 本机暂无可用传感器读数（采集层已降级）")
    lines.append("优化建议:")
    for s in sug:
        lines.append(f"  · [{s['severity']}] {s['title']}  ({s['rationale']})")
    lines.append("保养待办:")
    for it in plan:
        lines.append(f"  · {it['title']}  ({it['cadence']} · {it['action']} · {it['rationale']})")
    lines.append("")
    lines.append("关键资产 / 个人数据 / 通信能力保护:")
    for it in protect:
        lines.append(f"  · {it['title']}  ({it['cadence']} · {it['action']} · {it['rationale']})")
    if cert_summary:
        lines.append(f"   [证书状态] TPM={cert_summary.get('tpm_present')} "
                     f"密钥库={cert_summary.get('keystore_present')} "
                     f"EOL加密库={cert_summary.get('openssl_eol')} "
                     f"设备身份证书={cert_summary.get('device_cert_present')}")
    lines.append(f"   [通信状态] reachable={comms_summary.get('reachable') if isinstance(comms_summary, dict) else '未探测'}")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 写操作（仅指引，不代执行）：返回官方工具操作指引，绝不对设备下写命令。         #
# 契合红线：只读、不自动重启、不执行外部代码；也契合「用户 GUI 控制」诉求。       #
# --------------------------------------------------------------------------- #

def _guidance(fn_name: str, title: str, steps: list, kb: str) -> tuple:
    """统一的「只给指引、不写系统」返回。"""
    lines = [f"{title}（指引，不代执行；依据 {kb}）:"] + [f"   {i+1}. {s}" for i, s in enumerate(steps)]
    return True, "\n".join(lines)


def guide_charge_ceiling() -> tuple:
    """指引用户在 OEM 控制中心设充电上限（不写寄存器）。"""
    return _guidance(
        "guide_charge_ceiling", "设 80% 充电上限",
        ["打开 OEM 电源管理（联想 Vantage / 戴尔 Power Manager / 手机设置·电池健康）",
         "找到「充电阈值 / 养护模式 / 优化电池充电」并设为 80% 或开启",
         "长期插电设备保持该设置，临出行前可临时调回 100%"],
        "charge_strategy")


def guide_thermal_relief() -> tuple:
    """指引用户缓解过热（不写热策略、不强制解锁降频）。"""
    return _guidance(
        "guide_thermal_relief", "缓解设备过热",
        ["移到硬面、留散热缝，勿在被褥/包内使用",
         "停下高负载任务，让设备降温至温区再继续",
         "定期用软刷/气吹清风扇灰（外部，不拆机）"],
        "thermal_throttle")


def guide_backup_now() -> tuple:
    """指引用户立即备份（不替用户改写任何盘）。"""
    return _guidance(
        "guide_backup_now", "立即核对并备份",
        ["用系统/云备份做一次完整备份并验证可恢复",
         "重要数据保持 ≥2 份、跨介质（本地+异地/云）",
         "SMART 显示磨损时优先备份再考虑更换"],
        "maintenance_schedule")


def guide_storage_trim() -> tuple:
    """指引用户开启/执行 TRIM（不替用户下发写盘命令）。"""
    return _guidance(
        "guide_storage_trim", "SSD TRIM 回收",
        ["Linux：确认 fstrim 定时（systemctl status fstrim.timer）已启用",
         "Windows：默认开启「存储优化」，无需手动",
         "保留 ≥10-15% 空闲，利于磨损均衡与写放大"],
        "storage_smart")


def guide_water_care() -> tuple:
    """指引用户落水/受潮后的安全处理（不替用户拆机烘干）。"""
    return _guidance(
        "guide_water_care", "进水/受潮处理",
        ["立即断电、擦干外表，接口朝下晾通风处 ≥24-48h",
         "海水/饮料后用清水冲净残留再晾（勿热风猛吹）",
         "确认干燥后再充电；充电口潮气被拒充属正常保护"],
        "humidity_ingress")


# 写指引清单（仅展示，**不在展示时调用**——调用即只返回指引文本，不对设备下写命令）。
TUNES = (
    ("guide_charge_ceiling", "OEM 控制中心设 80% 充电上限（指引，不写寄存器）"),
    ("guide_thermal_relief", "缓解过热：通风/清灰/降负载（指引，不写热策略）"),
    ("guide_backup_now", "立即核对并备份（指引，不替用户改写盘）"),
    ("guide_storage_trim", "确认 TRIM 已启用（指引，不下发写盘命令）"),
    ("guide_water_care", "进水/受潮安全处理（指引，不替用户拆机）"),
)


def durability_tune_list() -> list:
    """返回 durability 写指引清单，供 CLI/GUI 展示。只读展示，调用也只回指引。"""
    return [f"· {fn}() — {desc}" for fn, desc in TUNES]
