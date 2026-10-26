"""供电与环境安全子系统（electrical）：只读感知 + 电气火灾风险自适应引擎。

设计「只读、最小权限、不写任何电气回路」：本工具**绝不**测插座接触电阻、绝不碰
配电箱、绝不下发任何电气写命令。它做的是两件事：

1. **知识库驱动的风险识别**：把用户声明的供电环境标签（旧线/铜铝混接/无接地/
   木座/松动插座/高发热连续负载）与电气火灾科普提炼的 8 类隐患（局部高阻发热 P=I²R、
   铜铝原电池腐蚀、金属蠕变松脱、串联电弧/AFDD、木桶短板过载、接地+RCD、接点老化、
   可燃底座）做交叉，给出「事故前兆链条」判定与风险级——每条都回链知识库 key
   （data/electrical_safety_docs.json），做到「建议有出处」。

2. **自适应运行指引**：据供电环境标签 + 本机可读温度读数，给出「设备长期保障运行」
   的自适应建议——铜铝/无接地/旧线/松动/木座 → 严禁在该回路接高发热连续负载并指引
   重拉全程阻燃铜线；木座/松动 → 立即断开上级回路；温度偏高 → 联动 durability 热管理
   降载。所有写操作（换线/装 RCD/AFDD/换插座）一律**只给官方/规范指引，不代执行**——
   严守本项目只读红线，也契合用户「个人行为在完全图形界面控制操作」的诉求。

本子系统是「设备长期使用保护（durability）」的供电环境维度补完：durability 看设备
自身（电池/温度/SMART/uptime），electrical 看设备**外部与内部供电环境**（回路质量/
接地/负载），二者共同支撑「依据设备外部和内部环境自适应、保持长期保障运行」。

内外环境运行标准（data/env_standards.json，`env_reference()` 只读消费）：
IEC 60529（IP 防护等级，外壳防尘防水）、IEC 62368-1:2018（音视频/ICT 设备安规第三版，
取代 60950-1/60065，GB 4943.1-2022 等同采用）、IEC 60721（环境条件分类，按气候/
生物/化学/机械活性物质分级）、IEC 61000（EMC 电磁兼容系列）、IEC 62321（RoHS 有害
物质测定，GB/T 39560 对应）。环境自适应判定（温湿度/粉尘/腐蚀）以这些标准为分级依据。

v0.6.39 深化（两项，均只读 + 仅指引）：
- **环境温度接入外部温湿度计**：外部 USB/蓝牙温湿度计的读数（ambient_temp_c/humidity）
  经 peripheral 子系统识别后喂入本子系统，做温度降载、高湿防蚀的环境自适应——绝不挂钩
  传感器数据流、绝不伪造读数（`read_external_env_sensor` + `adapt_by_env` 消费温湿度）。
- **回路级动态负载门控**：对声明 overload_risk 的回路，结合真实断路器额定与实测连续负载，
  给出「80% 木桶短板」阈值门控（超阈即门控掉高发热连续负载、错峰、限容），把自适应从
  「定性建议」推进到「按读数闭环」（纯函数 `dynamic_load_gating`，只给指引不代执行）。
"""

from __future__ import annotations

import json
import os


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "electrical_safety_docs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:  # noqa: BLE001
        return {}


REFS = _load_refs()


def reference(key: str) -> dict:
    """返回某 electrical 主题的文档参考（含 protocols/interfaces/advice）。"""
    return REFS.get(key, {})


def reference_all() -> dict:
    """返回全部 electrical 主题文档参考。"""
    return REFS


def _load_env_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "env_standards.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:  # noqa: BLE001
        return {}


# 内外环境运行标准（data/env_standards.json）：IEC 60529 IP 防护等级、
# IEC 62368-1 安规（第三版，取代 60950-1/60065）、IEC 60721 环境条件分类、
# IEC 61000 EMC 电磁兼容、IEC 62321 RoHS 有害物质测定。
ENV_REFS = _load_env_refs()


def env_reference(key: str) -> dict:
    """返回某内外环境运行标准的参考（IP 防护/安规/环境分类/EMC/RoHS）。"""
    return ENV_REFS.get(key, {})


def env_reference_all() -> dict:
    """返回全部内外环境运行标准参考。"""
    return ENV_REFS


# --------------------------------------------------------------------------- #
# 环境标签词表（用户声明其供电环境，工具据以自适应）                          #
# --------------------------------------------------------------------------- #
ENV_TAGS = (
    "old_wiring",     # 旧线/老化布线（房龄大、不明线径工艺）
    "copper_aluminum",  # 铜铝直接混接（墙内暗埋接头）
    "no_ground",      # 无可靠保护接地 PE
    "wood_base",      # 木质/可燃底座
    "loose_outlet",   # 松动/老化插座（弹片疲劳、插脚外露）
    "overload_risk",  # 欲接入大功率/高发热连续负载（空调/取暖器/电热水器）
    "high_dust",      # 多尘导电粉尘（爬电/电痕化）
)


def _norm_env(env_tags) -> set:
    return set(env_tags or [])


# --------------------------------------------------------------------------- #
# 只读探针（仅读本机可读的电源/温度信号，绝不测接触电阻、绝不碰配电箱）          #
# --------------------------------------------------------------------------- #

def read_power_state() -> tuple:
    """只读感知供电状态（Linux sysfs 交流适配器 online + 电池状态，其余降级）。

    仅读链路层电源存在性，绝不测接触电阻、不读任何电气回路参数。
    """
    base = "/sys/class/power_supply"
    if not os.path.isdir(base):
        return False, "本机无 /sys/class/power_supply（非 Linux 或容器隔离）"
    info: dict = {}
    try:
        for name in sorted(os.listdir(base)):
            if name.startswith("ADP") or name.startswith("AC"):
                ue = os.path.join(base, name, "online")
                if os.path.exists(ue):
                    try:
                        info["ac_online"] = int(open(ue, encoding="utf-8").read().strip()) == 1
                    except (OSError, ValueError):
                        pass
            if name.startswith("BAT"):
                stp = os.path.join(base, name, "status")
                if os.path.exists(stp):
                    try:
                        info["battery_status"] = open(stp, encoding="utf-8").read().strip()
                    except OSError:
                        pass
    except OSError:
        return False, "读取 /sys/class/power_supply 失败"
    if info:
        return True, info
    return False, "未探测到电源适配器/电池状态（仅知有电源接口，细节不可用）"


def read_thermal_proxy() -> tuple:
    """只读本机温度（解析 /sys/class/thermal，作为「内部环境」旁证）。

    插座接触发热软件不可测；此处只拿设备自身温感，对高温环境做自适应降载提醒。
    非 Linux 或容器隔离时优雅降级，绝不伪造。
    """
    base = "/sys/class/thermal"
    if not os.path.isdir(base):
        return False, "本机无 /sys/class/thermal（非 Linux 或容器隔离）"
    temps = {}
    try:
        for z in sorted(os.listdir(base)):
            if not z.startswith("thermal_zone"):
                continue
            tp = os.path.join(base, z, "temp")
            if os.path.exists(tp):
                try:
                    with open(tp, encoding="utf-8") as f:
                        temps[z] = int(f.read().strip()) / 1000.0
                except (OSError, ValueError):
                    continue
    except OSError:
        return False, "读取 /sys/class/thermal 失败"
    if temps:
        return True, temps
    return False, "无可用 thermal zone"


def read_external_env_sensor() -> tuple:
    """只读识别外部温湿度计接入状态，作为供电环境的「外部环境」输入。

    具体气象读数（ambient_temp_c/humidity）须由用户/peripheral 子系统识别后经 readings
    喂入本子系统；本工具只读能力面、不挂钩传感器数据流、绝不伪造读数。复用 peripheral
    的识别结果（懒导入，避免模块加载期循环依赖），保持单一事实来源。
    """
    try:
        from . import peripheral as _npf  # 复用 peripheral 的识别结果
        rc, msg = _npf.read_external_env_sensor()
        if isinstance(msg, dict):
            return True, {"note": msg.get("note", ""),
                          "hid_count": msg.get("hid_count", 0),
                          "feed": "外部温湿度读数(ambient_temp_c/humidity)经 readings 喂入"}
        return rc, msg
    except Exception:  # noqa: BLE001  懒导入失败的兜底（peripheral 缺失/隔离）
        return False, ("本机未识别到外部温湿度计；可用 USB/蓝牙温湿度计，"
                       "其读数(ambient_temp_c/humidity)经 readings 喂入做供电环境自适应")


# CLI / GUI 遍历用：探测函数名 + 中文标签
PROBES = (
    ("read_power_state", "供电状态（AC 适配器 online / 电池状态，只读 sysfs）"),
    ("read_thermal_proxy", "设备温度（thermal/sysfs 温感，作内部环境旁证）"),
    ("read_external_env_sensor", "外部温湿度计（复用 peripheral 识别，作供电外部环境输入）"),
)


def environment_report() -> list:
    """返回本机 electrical 探针可用性概览（✓ 可用 / ✗ 降级）。"""
    lines = ["供电与环境安全 · 本机可读信号："]
    for fn_name, label in PROBES:
        ok, msg = globals()[fn_name]()
        mark = "✓" if ok else "✗"
        lines.append(f"   {mark} {label}")
        if not ok:
            lines.append(f"       {msg}")
    return lines


def electrical_doc_list() -> list:
    """返回 electrical 主题文档参考清单（供 CLI/GUI 展示），逐条回链知识库。"""
    lines = []
    for key, ref in REFS.items():
        lines.append(f"· {key} — {ref.get('name', '')}")
        lines.append(f"    机构/标准: {ref.get('org', '')}")
        lines.append(f"    文档: {ref.get('url', '')}")
        lines.append("    机理:")
        for p in ref.get("protocols", []):
            lines.append(f"      - {p}")
        lines.append(f"    建议: {ref.get('advice', '')}")
    return lines


# --------------------------------------------------------------------------- #
# 引擎层（纯函数，不碰系统，便于单测）。每条建议回链知识库 key。                #
# --------------------------------------------------------------------------- #

def _hazard_for_tag(tag: str) -> dict:
    """环境标签 → 对应隐患知识库 key + 处置动作类型。"""
    return {
        "wood_base": ("combustible_base", "critical",
                      "立即断开上级回路电源，勿带电硬拔带自重适配器；拆除木质底座与老化插座，"
                      "更换符合 GB/T 2099 的阻燃 PC 插座+标准阻燃底盒"),
        "copper_aluminum": ("galvanic_corrosion", "critical",
                            "严禁在该回路接高发热连续负载；从配电箱重拉全程贯通阻燃铜芯线"
                            "（严禁中间夹铝线），接头用铜铝过渡端子+抗氧化膏"),
        "no_ground": ("grounding_rcd", "high",
                      "检查地线有效性；在配电箱确保配备额定动作电流 ≤30mA 的 RCD/RCBO，"
                      "定期按试验钮验证动作"),
        "loose_outlet": ("connector_aging", "high",
                         "更换老化插座（GB/T 2099 阻燃 PC + 标准底盒）；消除松动接头以遏电弧，"
                         "配电箱加装 AFDD（GB/T 31143 等同 IEC 62606）"),
        "old_wiring": ("local_high_resistance_heating", "high",
                       "全面排查回路接触电阻与线径工艺；降载运行、高负荷季节红外复测接头温度"),
        "overload_risk": ("barrel_overload", "mid",
                          "确认全程线径一致为铜芯后再接大功率；否则严禁接入持续高功率设备"),
        "high_dust": ("local_high_resistance_heating", "mid",
                      "清理插座/插头周围导电粉尘，防爬电电痕化击穿"),
    }.get(tag, (None, "mid", ""))


def assess_hazard_chain(env_tags: list | None = None) -> dict:
    """由供电环境标签推导「事故前兆链条」与风险级（纯函数，回链知识库 key）。

    返回：{tags, hazards:[{tag, kb, severity, action}], risk, critical:bool}
    risk: low/mid/high；criteria 含 wood_base/copper_aluminum 即 critical。
    """
    tags = _norm_env(env_tags)
    hazards = []
    for t in tags:
        kb, sev, action = _hazard_for_tag(t)
        if kb:
            hazards.append({"tag": t, "kb": kb, "severity": sev, "action": action})
    critical = any(h["tag"] in ("wood_base", "copper_aluminum") for h in hazards)
    risk = ("high" if critical or any(h["severity"] == "high" for h in hazards)
            else "mid" if hazards else "low")
    return {"tags": sorted(tags), "hazards": hazards,
            "risk": risk, "critical": critical}


def adapt_by_env(env_tags: list | None = None, readings: dict | None = None) -> list:
    """由供电环境标签 + 本机温度读数，给出「长期保障运行」自适应建议（纯函数）。

    每项：{id, title, severity, action_type, rationale}；action_type=guidance（只给官方/
    规范指引，不代执行）；rationale 指向 electrical/durability 知识库 key。
    """
    tags = _norm_env(env_tags)
    r = readings or {}
    sug = []

    # 木座/松动/铜铝/无接地/旧线 → 禁高发热连续负载 + 对应工程指引
    if tags & {"copper_aluminum", "no_ground", "old_wiring", "loose_outlet", "wood_base"}:
        sug.append({
            "id": "forbid_high_load",
            "title": "该回路严禁接入持续高功率设备（空调/取暖器/电热水器），防木桶短板过载起火",
            "severity": "warn", "action_type": "guidance", "rationale": "barrel_overload",
        })

    if "wood_base" in tags:
        sug.append({
            "id": "disconnect_now",
            "title": "立即断开上级回路电源，勿带电硬拔带自重适配器（防拉弧/相间短路）",
            "severity": "warn", "action_type": "guidance", "rationale": "combustible_base",
        })
    if "copper_aluminum" in tags:
        sug.append({
            "id": "rewire_copper",
            "title": "从配电箱重拉全程贯通阻燃铜芯线（严禁中间夹铝线），接头用铜铝过渡端子+抗氧化膏",
            "severity": "warn", "action_type": "guidance", "rationale": "galvanic_corrosion",
        })
    if "no_ground" in tags:
        sug.append({
            "id": "install_rcd",
            "title": "配电箱确保配备额定动作电流 ≤30mA 的 RCD/RCBO，定期按试验钮验证",
            "severity": "warn", "action_type": "guidance", "rationale": "grounding_rcd",
        })
    if "loose_outlet" in tags:
        sug.append({
            "id": "replace_outlet",
            "title": "更换 GB/T 2099 阻燃 PC 插座+标准底盒；配电箱加装 AFDD 防串联电弧",
            "severity": "notice", "action_type": "guidance", "rationale": "connector_aging",
        })
    if "old_wiring" in tags:
        sug.append({
            "id": "inspect_wiring",
            "title": "全面排查回路接触电阻与线径工艺；高负荷季节红外复测接头温度",
            "severity": "notice", "action_type": "guidance", "rationale": "local_high_resistance_heating",
        })

    # 本机温度偏高 → 联动 durability 热管理降载（内部环境自适应）
    tm = r.get("thermal_max_c")
    if tm is not None and tm > 80:
        sug.append({
            "id": "thermal_relief",
            "title": f"设备温度 {tm}°C 偏高：降载运行、通风清灰，联动 durability 热管理",
            "severity": "notice", "action_type": "guidance", "rationale": "thermal_throttle",
        })
    bt = r.get("battery_temp_c")
    if bt is not None and bt > 45:
        sug.append({
            "id": "batt_thermal",
            "title": f"电池温度 {bt}°C 过高：停高负载降温，电源回路一并排查（高温加速老化）",
            "severity": "notice", "action_type": "guidance", "rationale": "battery_lithium",
        })

    # 外部温湿度计读数 → 供电环境自适应（温度降载 / 高湿防蚀）
    at = r.get("ambient_temp_c")
    if at is not None and at > 35:
        sug.append({
            "id": "ambient_heat_derate",
            "title": f"环境温度 {at}°C 偏高：回路与设备一并降载通风，"
                     f"高发热连续负载错峰至夜间低温时段",
            "severity": "notice", "action_type": "guidance", "rationale": "thermal_throttle",
        })
    hu = r.get("humidity")
    if hu is not None and hu > 80:
        sug.append({
            "id": "ambient_humid_corrosion",
            "title": f"相对湿度 {hu}% 偏高：无接地/铜铝回路加速电化学腐蚀，"
                     f"加强接线端子防氧化与干燥",
            "severity": "notice", "action_type": "guidance", "rationale": "galvanic_corrosion",
        })

    # 回路级动态负载门控（实测负载 + 断路器额定 → 80% 木桶短板门控）
    gate = dynamic_load_gating(env_tags, readings)
    if gate["active"] or gate["plan"]:
        sug.append({
            "id": "dynamic_load_gating",
            "title": gate["title"],
            "severity": gate["severity"], "action_type": "guidance", "rationale": "barrel_overload",
        })

    if not sug:
        sug.append({
            "id": "env_ok",
            "title": "供电环境标签未声明高风险项；建议定期目检插座焦黑/发热/异味，并保持接地+RCD 有效",
            "severity": "info", "action_type": "guidance", "rationale": "grounding_rcd",
        })
    return sug


def dynamic_load_gating(env_tags: list | None = None, readings: dict | None = None) -> dict:
    """回路级动态负载门控（纯函数，只读读数、只给指引不代执行）。

    输入 readings：breaker_rating_a（回路断路器额定 A）、voltage_v（默认 220）、
    measured_load_w（实测连续负载 W）。仅当 overload_risk 标签存在且具备断路器额定 +
    实测负载时，给出「80% 木桶短板」阈值门控（超阈即门控掉高发热连续负载、错峰、限容）；
    缺读数则退化为「按断路器额定定门控上限」的规划建议。

    返回 {active, title, severity, plan, basis, threshold_a, measured_a, headroom_a}。
    """
    tags = _norm_env(env_tags)
    r = readings or {}
    basis: dict = {}
    threshold_a = None
    measured_a = None
    headroom_a = None
    breaker = r.get("breaker_rating_a")
    voltage = r.get("voltage_v") or 220
    load_w = r.get("measured_load_w")

    if breaker is not None:
        basis["breaker_rating_a"] = breaker
        basis["voltage_v"] = voltage
        threshold_a = breaker * 0.8  # 80% 木桶短板余量
        if load_w is not None:
            measured_a = (load_w / voltage) if voltage else None
            basis["measured_load_w"] = load_w
            if measured_a is not None:
                basis["estimated_current_a"] = round(measured_a, 2)
                headroom_a = round(breaker - measured_a, 2)
                if "overload_risk" in tags and measured_a > threshold_a:
                    return {
                        "active": True,
                        "title": (f"动态负载门控触发：实测电流约 {measured_a:.1f}A 已超 "
                                  f"{breaker}A 断路器 80% 门控阈值 {threshold_a:.1f}A；"
                                  f"立即门控掉高发热连续负载、错峰运行、限容至阈值以内"),
                        "severity": "warn", "plan": True,
                        "basis": basis, "threshold_a": threshold_a,
                        "measured_a": measured_a, "headroom_a": headroom_a,
                    }

    # 未触发 / 缺读数：给规划性门控建议
    if "overload_risk" in tags:
        if breaker is not None and threshold_a is not None:
            plan_title = (f"本回路按 {breaker}A 断路器定 80% 门控阈值 {threshold_a:.1f}A；"
                          f"高发热连续负载须实时测电流并门控在阈值内"
                          f"（缺实测时按额定保守限容）")
        else:
            plan_title = ("本回路声明高发热连续负载诉求，但缺断路器额定/实测读数；"
                          f"请先确认断路器额定(A)与实测连续负载(W)，本工具据此给门控阈值")
        sev = "notice"
    else:
        plan_title = ("回路级动态负载门控规划：以断路器额定 80% 为木桶短板阈值，"
                      "高发热连续负载须在其内运行")
        sev = "info"
    return {
        "active": False, "title": plan_title, "severity": sev,
        "plan": "overload_risk" in tags,
        "basis": basis, "threshold_a": threshold_a,
        "measured_a": measured_a, "headroom_a": headroom_a,
    }


def electrical_safety_report(env_tags: list | None = None,
                             readings: dict | None = None) -> tuple:
    """端到端生成供电与环境安全报告（无参可调用，供任务/CLI/GUI）。

    流程：读本机可读信号 → 据供电环境标签识别事故前兆链条与风险级 → 自适应运行建议。
    每条建议/隐患都回链知识库 key。绝不测接触电阻、绝不碰配电箱、绝不代执行写操作。
    """
    readings = readings or {}
    # 懒取本机可读温度（作内部环境旁证）
    if not readings:
        ok, t = read_thermal_proxy()
        if ok and isinstance(t, dict):
            temps = [v for v in t.values() if isinstance(v, (int, float))]
            if temps:
                readings["thermal_max_c"] = max(temps)
    chain = assess_hazard_chain(env_tags)
    sug = adapt_by_env(env_tags, readings)

    lines = ["== 供电与环境安全报告（只读感知 + 知识库自适应，绝不碰配电箱）=="]
    lines.append(f"供电环境标签: {chain['tags'] or '未声明（默认低风险基线）'}")
    lines.append(f"事故前兆链条风险: {chain['risk']}"
                 + ("  [critical: 含木座/铜铝]" if chain["critical"] else ""))
    if chain["hazards"]:
        lines.append("识别到的隐患链:")
        for h in chain["hazards"]:
            lines.append(f"  · [{h['severity']}] {h['tag']} → {h['kb']}")
            lines.append(f"      处置: {h['action']}")
    else:
        lines.append("隐患链: 未声明高风险环境标签（建议定期目检插座与接地）")
    lines.append("自适应运行建议（长期保障运行）:")
    for s in sug:
        lines.append(f"  · [{s['severity']}] {s['title']}  ({s['rationale']})")

    # 外部环境（外部温湿度计读数，经 peripheral 识别后喂入）
    at = readings.get("ambient_temp_c")
    hu = readings.get("humidity")
    if at is not None or hu is not None:
        lines.append("外部环境（外部温湿度计读数）:")
        if at is not None:
            lines.append(f"  环境温度: {at}°C" + ("  [偏高，降载错峰]" if at > 35 else ""))
        if hu is not None:
            lines.append(f"  相对湿度: {hu}%" + ("  [偏高，防蚀]" if hu > 80 else ""))
    # 回路级动态负载门控（若有 overload_risk 且具备读数）
    gate = dynamic_load_gating(env_tags, readings)
    if gate["plan"]:
        lines.append("回路级动态负载门控:")
        lines.append(f"  · [{gate['severity']}] {gate['title']}")
        if gate["basis"]:
            lines.append(f"      依据: {gate['basis']}")

    lines.append("安全不变量：本工具只读感知 + 出方案，电气改造由持证电工按规范执行，"
                 "是否施工始终由用户确认。")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 写操作（仅指引，不代执行）：返回官方/规范操作指引，绝不对电气回路下写命令。    #
# 契合红线：只读、不自动重启、不执行外部代码；也契合「用户 GUI 控制」诉求。       #
# --------------------------------------------------------------------------- #

def _guidance(fn_name: str, title: str, steps: list, kb: str) -> tuple:
    lines = [f"{title}（规范指引，不代执行；依据 {kb}）:"] + [f"   {i+1}. {s}" for i, s in enumerate(steps)]
    return True, "\n".join(lines)


def guide_rewire_full_copper() -> tuple:
    """指引从配电箱重拉全程贯通阻燃铜芯线（不代执行）。"""
    return _guidance(
        "guide_rewire_full_copper", "重拉全程贯通阻燃铜芯线",
        ["请持证电工确认全程线径一致为铜芯，严禁中间夹杂铝线",
         "铜铝连接点使用铜铝过渡端子（摩擦焊/钎焊）并涂抗氧化导电膏",
         "规范扭矩压接 + 定期复紧，高负荷季节红外复测接头温度"],
        "galvanic_corrosion")


def guide_install_rcd() -> tuple:
    """指引装设 ≤30mA RCD/RCBO（不代执行）。"""
    return _guidance(
        "guide_install_rcd", "装设剩余电流保护器 RCD/RCBO",
        ["配电箱确保配备额定动作电流 ≤30mA 的 RCD（IEC 61008）或 RCBO（IEC 61009）",
         "确认保护接地 PE 有效（设备碰壳经地回归 + RCD 切断）",
         "定期按 RCD 试验钮验证其动作"],
        "grounding_rcd")


def guide_replace_outlet() -> tuple:
    """指引更换老化插座+标准底盒并考虑 AFDD（不代执行）。"""
    return _guidance(
        "guide_replace_outlet", "更换插座与加装 AFDD",
        ["淘汰老旧插座/木底座，更换符合 GB/T 2099 的阻燃 PC 插座 + 标准阻燃底盒",
         "规范配线清灰，检查插脚是否外露/焦黑/发热/异味",
         "配电箱加装 AFDD（GB/T 31143 等同 IEC 62606）防串联电弧"],
        "connector_aging")


def guide_disconnect_now() -> tuple:
    """指引立即断开上级回路（木座/起火前兆，不代执行）。"""
    return _guidance(
        "guide_disconnect_now", "立即断开上级回路",
        ["先断配电箱对应支路，勿在带电状态下用力硬拔带自重适配器（防拉弧/相间短路）",
         "拆除木质底座与老化插座，暂以阻燃底盒 + 合规插座替代",
         "重拉前严禁在该回路接任何高发热量、长时间连续运行设备"],
        "combustible_base")


def guide_load_limit() -> tuple:
    """指引回路负载上限管理（不代执行）。"""
    return _guidance(
        "guide_load_limit", "回路负载上限管理",
        ["确认全程线径一致为铜芯后再接大功率设备，否则严禁接入持续高功率负载",
         "高负荷季节用红外热像复测接头/插座温度，发现异常热点立即降载排查",
         "避免单回路长时间满载，留出木桶短板余量"],
        "barrel_overload")


def guide_dynamic_gating() -> tuple:
    """指引回路动态负载门控（按 80% 木桶短板，不代执行）。"""
    return _guidance(
        "guide_dynamic_gating", "回路动态负载门控（按 80% 木桶短板）",
        ["确认回路断路器额定(A)与导线载流量一致，取 80% 为连续负载门控阈值",
         "实测高发热连续负载电流，超阈即门控掉部分负载或错峰至低温时段",
         "长期满载的回路应扩容或分流，而非硬顶阈值运行"],
        "barrel_overload")


# 写指引清单（仅展示，**不在展示时调用**——调用即只返回指引文本，不对电气回路下写命令）。
TUNES = (
    ("guide_rewire_full_copper", "重拉全程贯通阻燃铜芯线（规范指引，不代执行）"),
    ("guide_install_rcd", "装设 ≤30mA RCD/RCBO（规范指引，不代执行）"),
    ("guide_replace_outlet", "更换阻燃 PC 插座+底盒、加装 AFDD（规范指引，不代执行）"),
    ("guide_disconnect_now", "立即断开上级回路（木座/起火前兆，规范指引）"),
    ("guide_load_limit", "回路负载上限管理（规范指引，不代执行）"),
    ("guide_dynamic_gating", "回路动态负载门控（80% 木桶短板，规范指引，不代执行）"),
)


def electrical_tune_list() -> list:
    """返回 electrical 写指引清单，供 CLI/GUI 展示。只读展示，调用也只回指引。"""
    return [f"· {fn}() — {desc}" for fn, desc in TUNES]
