"""iOS 原生接口：通过 libimobiledevice（ideviceinfo 等）读设备信息 + 官方写接口深度调优。

设计「不麻烦、不越权」：
- iOS 沙盒严格，PC 端无法直接写系统文件（那需越狱，强烈不推荐）；能做的系统接口
  主要是 libimobiledevice 暴露的安全通道：读设备值、备份、归档 App、清诊断日志、
  同步时间、清模拟定位等，全部走 Apple 自身的 lockdown 服务。
- 文档层（data/ios_docs.json）：每个子系统按自身协议 + 接口写，不套别的平台写法。
- 只读探测（PROBES）：9 个，全部经 libimobiledevice 只读；未装/未连接时优雅降级。
- 官方写接口（TUNES）：8 个，全零参数、只往安全方向写（备份/归档/清日志/同步时间/
  清定位/归一化设备名/优雅重启/挂开发者镜像），绝不 remount 改系统分区、绝不卸载 App。

非 iOS 环境 import 不崩溃；专属调用检测不到设备就返回 (False, 降级说明)。
"""

from __future__ import annotations

import glob
import json
import os
import re

from . import common

_HERE = os.path.dirname(os.path.abspath(__file__))


# --------------------------------------------------------------------------- #
# 基础 helper（保留既有，runner 依赖 available / connected / trim 等语义）        #
# --------------------------------------------------------------------------- #

def available() -> bool:
    return common.run("ideviceinfo --version 2>/dev/null")[0] == 0


def device_info() -> dict:
    """读取设备型号/系统版本/序列号前缀等（不触碰隐私字段）。"""
    rc, out = common.run("ideviceinfo 2>/dev/null")
    info = {}
    if rc != 0 or not out:
        return info
    for m in re.finditer(r"^([\w]+):?\s*(.+)$", out, re.M):
        info[m.group(1).strip().lower()] = m.group(2).strip()
    return info


def product_version() -> str:
    return device_info().get("productversion", "")


def device_name() -> str:
    return device_info().get("devicename", "")


# --------------------------------------------------------------------------- #
# 文档层（data/ios_docs.json，与其它 X_docs.json 同 schema）                    #
# --------------------------------------------------------------------------- #

def _load_refs() -> dict:
    try:
        with open(os.path.join(_HERE, "..", "data", "ios_docs.json"),
                  encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


REFS = _load_refs()


def reference(key=None):
    """返回单条或全量文档引用。"""
    if key is None:
        return REFS
    return REFS.get(key)


def reference_all() -> dict:
    return REFS


def ios_doc_list():
    """返回 [(key, name, org, advice), ...]，供 CLI/GUI 展示文档引用。"""
    rows = []
    for k, v in REFS.items():
        rows.append((k, v.get("name", ""), v.get("org", ""), v.get("advice", "")))
    return rows


# --------------------------------------------------------------------------- #
# 设备在线探测（所有 iOS 原生函数先经此判定，避免误写）                          #
# --------------------------------------------------------------------------- #

def _first_udid() -> str:
    """取首个在线设备的 UDID；无则返回空串。"""
    rc, out = common.run("idevice_id -l 2>/dev/null")
    if rc == 0 and out.strip():
        return out.strip().splitlines()[0].strip()
    return ""


def _device_online() -> bool:
    return bool(_first_udid())


def _w(base: str) -> str:
    """若有多台设备，自动按首台 UDID 派发（-u）。"""
    udid = _first_udid()
    return f"{base} -u {udid}" if udid else base


# --------------------------------------------------------------------------- #
# 只读探测（PROBES）：9 个，全部经 libimobiledevice 只读                        #
# --------------------------------------------------------------------------- #

def device_report():
    """设备型号/系统版本/设备名（ideviceinfo）。"""
    if not _device_online():
        return False, "当前无已授权 iOS 设备（降级为文档指引）"
    rc, out = common.run("ideviceinfo 2>/dev/null")
    if rc != 0 or not out:
        return False, "读取设备信息失败（未安装 libimobiledevice 或设备未信任）"
    lines = [l for l in out.splitlines() if l.strip()][:40]
    return True, "\n".join(lines)


def battery_report():
    """电量与充电状态（com.apple.mobile.battery）。"""
    if not _device_online():
        return False, "当前无已授权 iOS 设备（降级为文档指引）"
    rc, out = common.run("ideviceinfo -q com.apple.mobile.battery 2>/dev/null")
    if rc != 0 or not out:
        return False, "电量信息不可用（设备未信任或版本不支持）"
    return True, out.strip()


def apps_report():
    """已安装 App 清单（ideviceinstaller -l），并统计用户 App 数。"""
    if not _device_online():
        return False, "当前无已授权 iOS 设备（降级为文档指引）"
    rc, out = common.run("ideviceinstaller -l -o list_all 2>/dev/null")
    if rc != 0 or not out:
        return False, "App 列表不可用（未安装 ideviceinstaller 或设备未信任）"
    user = len([l for l in out.splitlines()
                if l.strip().endswith("User")])
    return True, f"已安装 App（含系统）约 {len(out.splitlines())} 行；用户 App 约 {user} 个"


def storage_report():
    """存储容量与可用空间（com.apple.disk_usage）。"""
    if not _device_online():
        return False, "当前无已授权 iOS 设备（降级为文档指引）"
    rc, out = common.run("ideviceinfo -q com.apple.disk_usage 2>/dev/null")
    if rc != 0 or not out:
        return False, "容量信息不可用（设备未信任或版本不支持）"
    d = {}
    for line in out.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            d[k.strip()] = v.strip()

    def gb(x):
        try:
            return f"{int(x) / 1e9:.1f} GB"
        except Exception:
            return x

    total = d.get("TotalDataCapacity") or d.get("TotalDiskCapacity")
    avail = d.get("AvailableDataCapacity")
    if total and avail:
        return True, f"总容量约 {gb(total)}，可用约 {gb(avail)}"
    return True, out.strip()


def syslog_report():
    """系统日志快照（idevicesyslog，3 秒截断，只读）。"""
    if not _device_online():
        return False, "当前无已授权 iOS 设备（降级为文档指引）"
    rc, out = common.run("idevicesyslog 2>/dev/null", timeout=3)
    if rc == 0 and out.strip():
        return True, "系统日志（最近 3 秒快照）:\n" + out.strip()[-1500:]
    return False, "系统日志快照不可用（设备未信任或 idevicesyslog 不支持）"


def crash_report():
    """崩溃报告列表（idevicecrashreport -l，只读）。"""
    if not _device_online():
        return False, "当前无已授权 iOS 设备（降级为文档指引）"
    rc, out = common.run("idevicecrashreport -l 2>/dev/null")
    if rc != 0:
        return False, "崩溃报告列表不可用（未安装 idevicecrashreport 或设备未信任）"
    n = len([l for l in out.splitlines() if l.strip()])
    return True, f"设备端崩溃报告 {n} 条（清理用 ios_clear_crash：拷贝+删除日志，可逆）"


def diagnostics_report():
    """诊断快照（idevicediagnostics diagnostics all，只读）。"""
    if not _device_online():
        return False, "当前无已授权 iOS 设备（降级为文档指引）"
    rc, out = common.run("idevicediagnostics diagnostics all 2>/dev/null")
    if rc != 0 or not out:
        return False, "诊断快照不可用（未安装 idevicediagnostics 或设备未信任）"
    return True, out.strip()[:1500]


def pair_report():
    """配对状态（idevicepair list）。"""
    rc, out = common.run("idevicepair list 2>/dev/null")
    if rc == 0 and out.strip():
        return True, "已配对设备: " + out.strip()
    return False, "未配对或无已授权 iOS 设备（降级为文档指引）"


def connectivity_report():
    """在线设备（idevice_id -l）。"""
    rc, out = common.run("idevice_id -l 2>/dev/null")
    if rc == 0 and out.strip():
        ids = [l.strip() for l in out.splitlines() if l.strip()]
        return True, f"在线 iOS 设备 {len(ids)} 台: " + ", ".join(ids[:3])
    return False, "未找到已授权 iOS 设备（降级为文档指引）"


PROBES = (
    ("device_report", "设备型号/系统版本/设备名（ideviceinfo）"),
    ("battery_report", "电量与充电状态（com.apple.mobile.battery）"),
    ("apps_report", "已安装 App 清单（ideviceinstaller -l）"),
    ("storage_report", "存储容量与可用空间（com.apple.disk_usage）"),
    ("syslog_report", "系统日志快照（idevicesyslog，3 秒截断）"),
    ("crash_report", "崩溃报告列表（idevicecrashreport -l）"),
    ("diagnostics_report", "诊断快照（idevicediagnostics diagnostics all）"),
    ("pair_report", "配对状态（idevicepair list）"),
    ("connectivity_report", "在线设备（idevice_id -l）"),
)


def environment_report():
    """汇总本机 iOS 环境（只读）。返回行列表。"""
    lines = []
    ok, msg = connectivity_report()
    lines.append(f"在线设备: {msg if ok else '无（降级为文档指引）'}")
    ok, msg = device_report()
    if ok:
        for l in msg.splitlines()[:12]:
            lines.append(l)
    ok, msg = battery_report()
    if ok:
        lines.append("电量: " + msg.replace("\n", " | "))
    ok, msg = storage_report()
    if ok:
        lines.append("存储: " + msg)
    return lines


# --------------------------------------------------------------------------- #
# 官方写接口（TUNES）：8 个，全零参数、只往安全方向写                            #
# --------------------------------------------------------------------------- #

def ios_backup():
    """idevicebackup2 backup：备份到本地（单向导出，安全、可逆）。"""
    if not _device_online():
        return False, "当前无已授权 iOS 设备（降级为文档指引）"
    rc, out = common.run(_w("idevicebackup2 backup ./ios_backup") + " 2>/dev/null",
                          timeout=600)
    if rc == 0:
        return True, "已备份到 ./ios_backup（单向导出，未写回设备）"
    return False, f"备份失败: {out[:300]}"


def ios_archive_apps():
    """ideviceinstaller -a：归档用户 App（保留数据，可逆；绝不做卸载 -U）。"""
    if not _device_online():
        return False, "当前无已授权 iOS 设备（降级为文档指引）"
    rc, out = common.run(_w("ideviceinstaller -l -o list_all") + " 2>/dev/null")
    if rc != 0:
        return False, "无法列出 App（未安装 ideviceinstaller 或设备未信任）"
    bids = []
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 4 and parts[-1] == "User":
            bids.append(parts[0])
    if not bids:
        return True, "未发现可归档的用户 App（或已全是系统 App）"
    archived = []
    for b in bids[:50]:  # 限制数量，避免过长循环
        r, _o = common.run(_w(f"ideviceinstaller -a {b}") + " 2>/dev/null", timeout=120)
        if r == 0:
            archived.append(b)
    return True, f"已归档 {len(archived)}/{len(bids)} 个用户 App（保留数据，可恢复）"


def ios_clear_crash():
    """idevicecrashreport -e：拷贝+删除崩溃报告（仅诊断日志，可逆）。"""
    if not _device_online():
        return False, "当前无已授权 iOS 设备（降级为文档指引）"
    rc, out = common.run(_w("idevicecrashreport -e ./ios_crashlogs") + " 2>/dev/null",
                          timeout=120)
    if rc == 0:
        return True, "已拷贝并删除设备端崩溃报告（仅诊断日志，可逆）"
    return False, f"清理崩溃报告失败: {out[:300]}"


def ios_sync_date():
    """idevicedate -s：设备时间同步为当前主机时间（可逆）。"""
    if not _device_online():
        return False, "当前无已授权 iOS 设备（降级为文档指引）"
    rc, out = common.run(_w("idevicedate -s") + " 2>/dev/null")
    if rc == 0:
        return True, "已把设备时间同步为当前主机时间（可逆）"
    return False, f"同步时间失败: {out[:300]}"


def ios_clear_location():
    """idevicesetlocation clear：清除模拟定位（恢复真实 GPS，可逆）。"""
    if not _device_online():
        return False, "当前无已授权 iOS 设备（降级为文档指引）"
    rc, out = common.run(_w("idevicesetlocation clear") + " 2>/dev/null")
    if rc == 0:
        return True, "已清除模拟定位（恢复真实 GPS，可逆）"
    return False, f"清除模拟定位失败: {out[:300]}"


def ios_set_name():
    """idevicename：归一化设备名（设置中可随时改回，可逆）。"""
    if not _device_online():
        return False, "当前无已授权 iOS 设备（降级为文档指引）"
    rc, out = common.run(_w('idevicename "Optimized-iOS"') + " 2>/dev/null")
    if rc == 0:
        return True, "已把设备名归一化为 Optimized-iOS（设置中可随时改回，可逆）"
    return False, f"设置设备名失败: {out[:300]}"


def ios_restart():
    """idevicediagnostics restart：优雅重启释放内存（无数据丢失，medium 风险）。"""
    if not _device_online():
        return False, "当前无已授权 iOS 设备（降级为文档指引）"
    rc, out = common.run(_w("idevicediagnostics restart") + " 2>/dev/null", timeout=30)
    if rc == 0:
        return True, "已发送优雅重启指令（释放内存，无数据丢失）"
    return False, f"重启指令失败: {out[:300]}"


def ios_mount_devimage():
    """ideviceimagemounter：挂载开发者磁盘镜像（启用开发者服务，可逆；缺镜像则降级）。"""
    if not _device_online():
        return False, "当前无已授权 iOS 设备（降级为文档指引）"
    ver = product_version() or ""
    cands = []
    if ver:
        cands.append(os.path.join(
            "/Applications/Xcode.app/Contents/Developer/Platforms/"
            "iPhoneOS.platform/DeviceSupport", ver, "DeveloperDiskImage.dmg"))
    cands += glob.glob(os.path.expanduser(
        "~/Library/Developer/Xcode/iOS DeviceSupport/*/DeveloperDiskImage.dmg"))
    found = next((c for c in cands if os.path.exists(c)), None)
    if not found:
        return False, "未找到匹配版本的 DeveloperDiskImage（降级为文档指引，不联网下载）"
    rc, out = common.run(_w(f'ideviceimagemounter -i "{found}"') + " 2>/dev/null",
                          timeout=120)
    if rc == 0:
        return True, f"已挂载开发者磁盘镜像（启用开发者服务，可卸载）: {found}"
    return False, f"挂载开发者镜像失败: {out[:300]}"


TUNES = (
    ("ios_backup", "idevicebackup2 backup（备份到本地，单向、安全）"),
    ("ios_archive_apps", "ideviceinstaller -a（归档用户 App，保留数据、可逆）"),
    ("ios_clear_crash", "idevicecrashreport -e（拷贝+删除崩溃日志，仅日志）"),
    ("ios_sync_date", "idevicedate -s（设备时间同步为主机时间）"),
    ("ios_clear_location", "idevicesetlocation clear（清除模拟定位）"),
    ("ios_set_name", "idevicename（归一化设备名，可逆）"),
    ("ios_restart", "idevicediagnostics restart（优雅重启释放内存）"),
    ("ios_mount_devimage", "ideviceimagemounter（挂载开发者磁盘镜像，可逆）"),
)


def ios_tune_list():
    """返回 TUNES 清单（只展示不调用）。"""
    return TUNES
