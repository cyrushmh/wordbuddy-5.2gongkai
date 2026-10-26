"""外部设备连接与兼容子系统（peripheral）：只读识别 + 星闪/触控/外设兼容引擎。

设计「只读、最小权限、不写任何设备寄存器」：本工具**绝不**刷写星闪/USB 固件、
绝不装私有外设驱动、绝不挂钩输入流。它做的是三件事：

1. **整体引入星闪标准（NearLink / SparkLink）**：把星闪作为外部设备连接与兼容的
   推荐国产短距无线标准整体引入——无线外设（鼠标/键盘/手写笔/耳机）优先按星闪选型，
   并标注其与 BLE/Wi-Fi 的频谱共存与接入校验要求（introduce_nearlink）。

2. **触控技术支持与兼容**：只读识别触控设备与多点触控协议类型（MT-A/MT-B、精确触控板），
   缺驱动即给官方指引，绝不采集按键/触控内容（touch_tech）。

3. **外部设备支持与兼容**：只读盘点 USB/USB4/USB-C PD 供电能力与 HID 即插即用状态，
   出兼容与选型指引（usb_c_pd / hid_compat）；绝不改写 PD 协商、绝不刷接口固件。

4. **线缆/连接器与内外环境运行标准**（v0.6.65 补全，逐条联网核实）：只读登记布线等级
   （ISO/IEC 11801:2017 / ANSI/TIA-568-D）、光纤（ITU-T G.652 / IEC 60793）、视频与高速接口
   （HDMI 2.1 / DisplayPort 2.1 / Thunderbolt 4·5）、电源连接器（IEC 60320）与内外环境运行标准
   （IEC 60529 IP 防护 / IEC 62368-1 安规 / IEC 60721 环境分类 / IEC 61000 EMC / IEC 62321 RoHS 测试，
   见 data/env_standards.json）的合规红线；绝不改动布线、端口协商、供电或设备外壳密封。

所有写操作（刷固件/装驱动/改 PD 协商）一律**只给官方/规范指引，不代执行**——
严守本项目只读红线，也契合用户「个人行为在完全图形界面控制操作」的诉求。

本子系统与「供电与环境安全（electrical）」「设备长期使用保护（durability）」并列：
外部温湿度计等感知设备经本子系统识别后，其读数可喂给 electrical 做供电环境自适应
（见 electrical.read_external_env_sensor 与 linkage 轴），共同支撑「外部设备连接与
设备长期保障运行」。
"""

from __future__ import annotations

import json
import os
import re


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "peripheral_standards_docs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:  # noqa: BLE001
        return {}


REFS = _load_refs()


def reference(key: str) -> dict:
    """返回某 peripheral 主题的文档参考（含 protocols/interfaces/advice）。"""
    return REFS.get(key, {})


def reference_all() -> dict:
    """返回全部 peripheral 主题文档参考。"""
    return REFS


# --------------------------------------------------------------------------- #
# 设备标签词表（用户声明其外部设备能力/诉求，工具据以自适应）                    #
# --------------------------------------------------------------------------- #
ENV_TAGS = (
    "nearlink_desired",   # 希望引入/已支持星闪（国产短距无线标准）
    "touchscreen",        # 触控屏（多点触控）
    "touchpad",           # 精确触控板（Precision Touchpad）
    "stylus",             # 主动/被动手写笔
    "usb_c_pd",           # 需要 USB-C/USB4 + PD 高功率供电
    "legacy_usb",         # 含老旧 USB 2.0 / 转接外设
    "hid_device",         # 通用 HID 外设（键鼠/手柄）
    "external_env_sensor",  # 外接 USB/蓝牙温湿度计（外部感知设备，喂给 electrical）
)


def _norm_env(env_tags) -> set:
    return set(env_tags or [])


# --------------------------------------------------------------------------- #
# 只读探针（仅读本机可读的外设/接口信号，绝不刷固件、绝不装驱动、绝不挂钩输入）  #
# --------------------------------------------------------------------------- #

def read_nearlink_capability() -> tuple:
    """只读感知星闪能力（当前系统多无统一内核协议栈，优雅降级为能力说明）。

    星闪经芯片/复合 dongle 接入，软件侧只能力面识别（设备管理器/系统信息里的
    SparkLink 标识），不探测未公开私有固件。降级即给「如何识别星闪设备」的说明。
    """
    # 现有系统尚无公开统一星闪内核协议栈可被软件枚举；能力面识别依赖设备管理器标识。
    return False, ("本机无统一星闪协议栈枚举入口（星闪经 SoC/复合 dongle 接入，"
                   "能力面识别靠设备管理器/系统信息里的 SparkLink/NearLink 标识）；"
                   "本工具只读能力面，不探测私有固件")


def read_touch_devices() -> tuple:
    """只读识别触控设备与多点触控协议类型（Linux /proc/bus/input/devices，其余降级）。

    解析 Handlers(event*/mouse*) 与名称含 Touch/ELAN/Synaptics/FTSC/Atmel 者；
    据 ABS 位有无 ABS_MT_SLOT 判 MT-B（槽位跟踪，主流）或 MT-A。绝不挂钩输入流。
    """
    dev_path = "/proc/bus/input/devices"
    if not os.path.isfile(dev_path):
        return False, "本机无 /proc/bus/input/devices（非 Linux 或容器隔离）"
    found = []
    try:
        with open(dev_path, encoding="utf-8", errors="ignore") as f:
            blk = {}
            for line in f:
                if line.startswith("N: Name="):
                    blk["name"] = line.split("=", 1)[1].strip().strip('"')
                elif line.startswith("H: Handlers="):
                    blk["handlers"] = line.split("=", 1)[1].strip()
                elif line.startswith("B: ABS="):
                    blk["abs"] = line.split("=", 1)[1].strip()
                elif line.strip() == "" and blk:
                    nm = blk.get("name", "")
                    if re.search(r"Touch|ELAN|Synaptics|FTSC|Atmel|Wacom|Goodix",
                                 nm, re.IGNORECASE) or "mouse" in blk.get("handlers", ""):
                        proto = "MT-B" if "SLOT" in blk.get("abs", "").upper() else (
                            "MT-A" if "MT" in blk.get("abs", "").upper() else "未知")
                        found.append({"name": nm, "protocol": proto,
                                       "handlers": blk.get("handlers", "")})
                    blk = {}
    except OSError:
        return False, "读取 /proc/bus/input/devices 失败"
    if found:
        return True, found
    return False, "未识别到触控设备（无 Touch/ELAN/Synaptics 等，或 hid-multitouch/I2C-HID 未加载）"


def read_usb_devices() -> tuple:
    """只读盘点 USB 外设与端口能力（Linux /sys/bus/usb/devices，其余降级）。

    读 uevent 的 idVendor/idProduct/bcdDevice 与接口类（bInterfaceClass=03 即 HID），
    只读能力面，绝不改写 PD 协商、绝不刷接口固件。
    """
    base = "/sys/bus/usb/devices"
    if not os.path.isdir(base):
        return False, "本机无 /sys/bus/usb/devices（非 Linux 或容器隔离）"
    devs = []
    try:
        for name in sorted(os.listdir(base)):
            d = os.path.join(base, name)
            ue = os.path.join(d, "uevent")
            if not os.path.isfile(ue):
                continue
            kv = {}
            try:
                with open(ue, encoding="utf-8", errors="ignore") as f:
                    for l in f:
                        if "=" in l:
                            k, v = l.strip().split("=", 1)
                            kv[k] = v
            except OSError:
                continue
            vid = kv.get("PRODUCT", "").split("/")[0]
            if not vid:
                continue
            # 只收有 vendor 的真实设备节点（跳过 usb 控制器 root hub 噪声）
            if kv.get("DEVTYPE") == "usb_device" or "idVendor" in kv:
                devs.append({"node": name, "vid": kv.get("idVendor", vid),
                             "pid": kv.get("idProduct", ""),
                             "hid": kv.get("bInterfaceClass", "") == "03"})
    except OSError:
        return False, "读取 /sys/bus/usb/devices 失败"
    if devs:
        return True, {"count": len(devs), "hid_count": sum(1 for x in devs if x["hid"]),
                      "sample": devs[:8]}
    return False, "未枚举到 USB 外设（无 /sys/bus/usb/devices 子节点或容器隔离）"


def read_external_env_sensor() -> tuple:
    """只读识别外部温湿度计（USB/蓝牙 HID 气象设备），作为 electrical 的环境输入。

    当前系统未预置统一气象传感器驱动；本工具只说明「如何把外部温湿度读数喂给
    electrical」，绝不挂钩传感器数据流、绝不伪造读数。
    """
    rc, usb = read_usb_devices()
    if rc and isinstance(usb, dict) and usb.get("hid_count"):
        return True, {"note": "检测到 HID 类外设，其中可能含 USB 温湿度计；"
                              "具体气象读数需厂商驱动/接口，本工具不挂钩数据流",
                      "hid_count": usb["hid_count"]}
    return False, ("本机未识别到外部温湿度计接入；可用 USB/蓝牙温湿度计，"
                   "其读数（ambient_temp_c/humidity）经用户/peripheral 识别后"
                   "喂给 electrical 做供电环境自适应")


# CLI / GUI 遍历用：探测函数名 + 中文标签
PROBES = (
    ("read_nearlink_capability", "星闪(NearLink)能力（当前多无统一协议栈，能力面识别）"),
    ("read_touch_devices", "触控设备与多点触控协议（Linux input，只读识别）"),
    ("read_usb_devices", "USB 外设与端口能力（Linux sysfs，只读）"),
    ("read_external_env_sensor", "外部温湿度计（USB/蓝牙，作为 electrical 的环境输入）"),
)


def environment_report() -> list:
    """返回本机 peripheral 探针可用性概览（✓ 可用 / ✗ 降级）。"""
    lines = ["外部设备连接与兼容 · 本机可读信号："]
    for fn_name, label in PROBES:
        ok, msg = globals()[fn_name]()
        mark = "✓" if ok else "✗"
        lines.append(f"   {mark} {label}")
        if not ok:
            lines.append(f"       {msg}")
    return lines


def peripheral_doc_list() -> list:
    """返回 peripheral 主题文档参考清单（供 CLI/GUI 展示），逐条回链知识库。"""
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

def introduce_nearlink() -> dict:
    """整体引入星闪标准：返回标准概览（空口/特性/对标/接入要求），纯函数。

    回链知识库 key 'nearlink_standard'；只说明标准与选型建议，不探测私有固件。
    """
    return {
        "standard": "nearlink_standard",
        "air_interfaces": {
            "SLB": "SparkLink Basic——高速率、高精定位、低时延，对标 Wi-Fi/5G 短距",
            "SLE": "SparkLink Low Energy——低功耗，对标蓝牙 BLE",
        },
        "features": ["微秒级时延", "一拖上千并发", "Polar 码抗干扰", "μs 级精同步",
                     "轻量加密+设备身份准入"],
        "vs": {"蓝牙 BLE": "功耗低但时延高、一拖七上限", "Wi-Fi": "快但耗电、短距并发弱"},
        "adoption": ("无线外设（鼠标/键盘/手写笔/耳机）优先按星闪选型；"
                     "接入须配对+身份校验，并与 BLE/Wi-Fi 做 2.4G 频谱共存调度"),
    }


def assess_touch_compat(env_tags: list | None = None, readings: dict | None = None) -> list:
    """由设备标签 + 本机触控识别，给触控技术支持与兼容建议（纯函数）。

    每项：{id, title, severity, action_type, rationale}；action_type=guidance
    （只给官方/规范指引，不代执行）；rationale 指向 peripheral 知识库 key。
    """
    tags = _norm_env(env_tags)
    r = readings or {}
    sug = []
    if tags & {"touchscreen", "touchpad", "stylus"}:
        if "stylus" in tags:
            sug.append({
                "id": "stylus_lowlatency",
                "title": "手写笔优先按低时延通道选型（星闪 SLE / 主动笔），压感倾斜跟手不漂移",
                "severity": "info", "action_type": "guidance", "rationale": "touch_tech",
            })
        if "touchpad" in tags:
            sug.append({
                "id": "precision_touchpad",
                "title": "触控板优先选 Precision Touchpad（HID over I2C，手势交系统处理）",
                "severity": "info", "action_type": "guidance", "rationale": "touch_tech",
            })
        # 本机识别到的触控设备若缺 MT-B 槽位跟踪，提示驱动兼容
        td = r.get("touch_devices")
        if isinstance(td, list):
            for d in td:
                if d.get("protocol") in ("MT-A", "未知"):
                    sug.append({
                        "id": "touch_driver",
                        "title": f"触控设备「{d.get('name','')}」仅 {d.get('protocol')} 协议，"
                                 f"建议启用 hid-multitouch/I2C-HID 以获得多点跟手",
                        "severity": "notice", "action_type": "guidance", "rationale": "touch_tech",
                    })
        if not sug:
            sug.append({
                "id": "touch_ok",
                "title": "触控设备已按标准 MT/HID 识别；保持驱动更新即可",
                "severity": "info", "action_type": "guidance", "rationale": "touch_tech",
            })
    else:
        sug.append({
            "id": "touch_none",
            "title": "未声明触控类设备；如后续接入触控屏/精确触控板，本工具可只读识别 MT 协议与驱动状态",
            "severity": "info", "action_type": "guidance", "rationale": "touch_tech",
        })
    return sug


def assess_external_compat(env_tags: list | None = None, readings: dict | None = None) -> list:
    """由设备标签 + 本机 USB/PD/HID 识别，给外部设备支持与兼容建议（纯函数）。

    每项：{id, title, severity, action_type, rationale}；rationale 指向 peripheral 知识库 key。
    """
    tags = _norm_env(env_tags)
    r = readings or {}
    sug = []

    if "nearlink_desired" in tags:
        sug.append({
            "id": "adopt_nearlink",
            "title": "按星闪(SparkLink)选型无线外设：微秒时延+一拖上千，接入须配对与身份校验",
            "severity": "info", "action_type": "guidance", "rationale": "nearlink_standard",
        })

    if "usb_c_pd" in tags:
        sug.append({
            "id": "usb_c_pd_cable",
            "title": "USB-C 高功率/视频须用带 e-Marker 线缆；PD 3.1 EPR 最高 240W，"
                     "无标记线仅能充电/降速",
            "severity": "notice", "action_type": "guidance", "rationale": "usb_c_pd",
        })
        sug.append({
            "id": "usb4_altmode",
            "title": "USB4/Type-C Alt Mode 承载 DP/Thunderbolt/星闪；确认端口与线缆均支持对应 Alt Mode",
            "severity": "info", "action_type": "guidance", "rationale": "usb_c_pd",
        })

    if "legacy_usb" in tags:
        sug.append({
            "id": "legacy_compat",
            "title": "老旧 USB 2.0/转接外设经 HID/USB 兼容识别；转接器本身可能不被自动驱动，"
                     "需用标准 HID 转接",
            "severity": "notice", "action_type": "guidance", "rationale": "hid_compat",
        })

    if "hid_device" in tags or "external_env_sensor" in tags:
        sug.append({
            "id": "hid_pnp",
            "title": "通用 HID 外设经描述符自动加载 hid-generic 即插即用；出现「未知设备」即驱动/"
                     "描述符问题，按厂商指引处理",
            "severity": "info", "action_type": "guidance", "rationale": "hid_compat",
        })
        if "external_env_sensor" in tags:
            sug.append({
                "id": "env_sensor_feed",
                "title": "外部温湿度计读数（ambient_temp_c/humidity）经识别后喂给 electrical "
                         "做供电环境自适应（温度降载/湿度防蚀）",
                "severity": "info", "action_type": "guidance", "rationale": "hid_compat",
            })

    # 本机识别到的 USB 设备若 HID 占比异常（全为未知），提示驱动
    ud = r.get("usb_devices")
    if isinstance(ud, dict) and ud.get("count") and ud.get("hid_count", 0) == 0:
        sug.append({
            "id": "usb_driver",
            "title": f"枚举到 {ud['count']} 个 USB 设备但无 HID 类被识别，可能缺 hid-generic/"
                     "I2C-HID，按厂商指引确认驱动",
            "severity": "notice", "action_type": "guidance", "rationale": "hid_compat",
        })

    if not sug:
        sug.append({
            "id": "ext_ok",
            "title": "未声明外部设备诉求；本工具可对触控/USB-C PD/HID 外设做只读识别与兼容指引",
            "severity": "info", "action_type": "guidance", "rationale": "hid_compat",
        })
    return sug


def peripheral_report(env_tags: list | None = None, readings: dict | None = None) -> tuple:
    """端到端生成外部设备连接与兼容报告（无参可调用，供任务/CLI/GUI）。

    流程：读本机可读外设信号 → 整体引入星闪标准 → 触控技术支持与兼容 →
    外部设备支持与兼容（USB-C PD / HID）。每条建议/标准都回链知识库 key。
    绝不刷固件、绝不装私有驱动、绝不挂钩输入流。
    """
    readings = readings or {}
    chain = introduce_nearlink()
    touch = assess_touch_compat(env_tags, readings)
    ext = assess_external_compat(env_tags, readings)

    lines = ["== 外部设备连接与兼容报告（只读识别 + 标准引入，绝不刷固件/装驱动/挂钩输入）=="]
    lines.append(f"设备标签: {sorted(_norm_env(env_tags)) or '未声明（默认基线）'}")

    lines.append("")
    lines.append("[① 整体引入星闪标准（NearLink / SparkLink）]")
    lines.append(f"  空口：SLB（高速率/高精/对标 Wi-Fi） + SLE（低功耗/对标 BLE）")
    lines.append(f"  特性：{ '、'.join(chain['features']) }")
    lines.append(f"  对标：{ '；'.join(f'{k}：{v}' for k, v in chain['vs'].items()) }")
    lines.append(f"  选型：{chain['adoption']}")

    lines.append("")
    lines.append("[② 触控技术支持与兼容]")
    for s in touch:
        lines.append(f"  · [{s['severity']}] {s['title']}  ({s['rationale']})")

    lines.append("")
    lines.append("[③ 外部设备支持与兼容（USB-C/PD · HID）]")
    for s in ext:
        lines.append(f"  · [{s['severity']}] {s['title']}  ({s['rationale']})")

    lines.append("")
    lines.append("安全不变量：本工具只读识别 + 出方案，外设固件/驱动/PD 协商由用户在"
                 "图形界面或厂商工具确认；是否施工始终由用户决定。")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 写操作（仅指引，不代执行）：返回官方/规范操作指引，绝不刷固件/装私有驱动/改 PD。#
# --------------------------------------------------------------------------- #

def _guidance(fn_name: str, title: str, steps: list, kb: str) -> tuple:
    lines = [f"{title}（规范指引，不代执行；依据 {kb}）:"] + [f"   {i+1}. {s}" for i, s in enumerate(steps)]
    return True, "\n".join(lines)


def guide_nearlink_adopt() -> tuple:
    """指引按星闪选型与接入无线外设（不代执行）。"""
    return _guidance(
        "guide_nearlink_adopt", "按星闪(SparkLink)接入无线外设",
        ["在设备管理器/系统信息确认外设标注 SparkLink/NearLink 即视为已支持",
         "鼠标/键盘/手写笔/耳机优先选星闪版，获得微秒时延与一拖上千并发",
         "首次使用完成配对与身份校验；与既有 BLE/Wi-Fi 设备注意 2.4G 共存调度"],
        "nearlink_standard")


def guide_touch_driver() -> tuple:
    """指引补全触控驱动（hid-multitouch / I2C-HID，不代执行）。"""
    return _guidance(
        "guide_touch_driver", "补全触控驱动以获得多点跟手",
        ["Linux：确认内核加载 hid-multitouch 与 I2C-HID（触控板/屏常见传输），缺失即装对应模块",
         "Windows：选用 Precision Touchpad 认证的触控板，手势由系统统一处理",
         "触控屏/笔优先选主动笔+星闪 SLE 低时延通道"],
        "touch_tech")


def guide_usb_c_pd() -> tuple:
    """指引 USB-C/PD 供电兼容选型（不代执行）。"""
    return _guidance(
        "guide_usb_c_pd", "USB-C/USB4 与 PD 供电兼容选型",
        ["高功率/视频必须选用带 e-Marker 的 USB-C 线缆（否则仅充电/降速）",
         "确认端口与线缆支持目标 Alt Mode（DP/Thunderbolt/星闪）",
         "PD 3.1 EPR 最高 240W；注意欧盟 IEC 62680 强制 USB-C 充电接口"],
        "usb_c_pd")


def guide_hid_compat() -> tuple:
    """指引 HID/外设即插即用兼容（不代执行）。"""
    return _guidance(
        "guide_hid_compat", "HID 外设即插即用与驱动兼容",
        ["通用键鼠/手柄走 HID，系统按描述符自动加载 hid-generic 即插即用",
         "出现「未知设备」即驱动/描述符问题，按厂商指引安装而非随意注入驱动",
         "星闪等无线外设须向上暴露标准 HID 接口方能即插即用"],
        "hid_compat")


# 写指引清单（仅展示，**不在展示时调用**——调用即只返回指引文本，不刷固件/装驱动）。
TUNES = (
    ("guide_nearlink_adopt", "按星闪选型与接入无线外设（规范指引，不代执行）"),
    ("guide_touch_driver", "补全触控驱动 hid-multitouch/I2C-HID（规范指引，不代执行）"),
    ("guide_usb_c_pd", "USB-C/USB4 与 PD 供电兼容选型（规范指引，不代执行）"),
    ("guide_hid_compat", "HID 外设即插即用与驱动兼容（规范指引，不代执行）"),
)


def peripheral_tune_list() -> list:
    """返回 peripheral 写指引清单，供 CLI/GUI 展示。只读展示，调用也只回指引。"""
    return [f"· {fn}() — {desc}" for fn, desc in TUNES]
