"""新硬件：单板机 / ARM SBC 只读探针与优化建议（v0.6.11 新增）。

立项一句话
----------
「新硬件」不止是安卓手机。树莓派、Orange Pi、NanoPi、RK3399/RK3566 这类
**单板机（SBC）** 跑着完整 Linux，却有一套桌面/服务器没有的痛点：SD 卡掉速、
被动散热降频、供电不足触发 under-voltage、启动盘类型决定寿命。本层只做**只读探测**
+ **建议**，不替你改任何设置——SBC 上改错了（比如误关散热策略）比桌面更危险。

探测对象（都是 Linux 上真实可读的接口）
--------------------------------------
- 板型：/proc/device-tree/model 或 /sys/firmware/devicetree/base/model
  （设备树在几乎所有 ARM SBC 上都有，是最稳的「这是什么板」来源）。
- 温度：/sys/class/thermal/thermal_zone*/{type,temp}（Linux 通用 thermal 子系统）。
- 降频/欠压：Broadcom 平台读 /sys/devices/platform/soc/*/throttled 的位掩码；
  其它平台退化到「看温度 + 看是否有 throttle 相关 sysfs」。
- 启动盘：/sys/class/block/<boot>/device/model 或 lsblk 思路，判断是 SD / eMMC / NVMe / SATA。

红线（写死）
----------
- **只读**：不写 sysfs、不调 vcgencmd 去改频率/电压、不装任何散热服务。
- **惰性守卫**：非 SBC（x86 笔记本 / 服务器）上 detect_board 返回 None，
  所有函数优雅降级，绝不因「没有设备树」而崩。
- 建议带「为什么」：SBC 用户需要懂因果，不是被按头改。

测试性：所有路径都走模块级 ``_SYS_ROOT``（默认 ``/``），测试用 ``_set_sys_root``
把根重定向到临时目录，即可喂假的 sysfs 而不碰真机器。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 测试可重定向的「系统根」：所有探测路径都相对它拼出来。
_SYS_ROOT = Path("/")

# Broadcom 平台 throttled 位掩码（树莓派系），与 vcgencmd get_throttled 同义。
# 位定义见树莓派官方文档：bit0 under-voltage、bit1 arm freq cap、
# bit2 当前被节流、bit3 软温度限速、bit16+ 为「曾经发生过」的锁存位。
_UNDER_VOLT = 0b0001
_ARM_CAP = 0b0010
_THROTTLED = 0b0100
_SOFT_TEMP = 0b1000


def _set_sys_root(root: Path) -> None:
    """测试用：把系统根重定向到临时目录。"""
    global _SYS_ROOT
    _SYS_ROOT = Path(root)


def _reset_sys_root() -> None:
    global _SYS_ROOT
    _SYS_ROOT = Path("/")


def _dt_model_paths() -> List[Path]:
    return [
        _SYS_ROOT / "proc" / "device-tree" / "model",
        _SYS_ROOT / "sys" / "firmware" / "devicetree" / "base" / "model",
    ]


def detect_board() -> Optional[str]:
    """读设备树型号；拿不到返回 None（很可能不是 SBC，或内核没给设备树）。"""
    for p in _dt_model_paths():
        try:
            s = p.read_text(encoding="utf-8", errors="replace").strip("\x00").strip()
            if s:
                return s
        except Exception:  # noqa: BLE001
            continue
    return None


def thermal_zones() -> List[Dict[str, object]]:
    """读全部 thermal zone（type + 毫摄氏度→摄氏度）。无则空列表。"""
    out: List[Dict[str, object]] = []
    base = _SYS_ROOT / "sys" / "class" / "thermal"
    if not base.exists():
        return out
    for z in sorted(base.glob("thermal_zone*")):
        try:
            typ = (z / "type").read_text(encoding="utf-8", errors="replace").strip()
            raw = (z / "temp").read_text(encoding="utf-8", errors="replace").strip()
            millic = int(raw)
            out.append({"zone": z.name, "type": typ,
                        "temp_c": round(millic / 1000.0, 1)})
        except Exception:  # noqa: BLE001
            continue
    return out


def throttle_state() -> Optional[Dict[str, bool]]:
    """读 Broadcom 平台 throttled 位掩码；不是该平台返回 None（不硬猜）。"""
    p = None
    soc = _SYS_ROOT / "sys" / "devices" / "platform" / "soc"
    if soc.exists():
        for f in soc.rglob("throttled"):
            if not f.is_file():
                continue
            p = f
            break
    if p is None:
        return None
    try:
        val = int((p.read_text(encoding="utf-8", errors="replace").strip()), 0)
    except Exception:  # noqa: BLE001
        return None
    return {
        "under_voltage": bool(val & _UNDER_VOLT),
        "arm_freq_capped": bool(val & _ARM_CAP),
        "throttled_now": bool(val & _THROTTLED),
        "soft_temp_limit": bool(val & _SOFT_TEMP),
        "raw": val,
    }


def boot_media() -> Optional[str]:
    """判断启动盘类型：SD / eMMC / NVMe / SATA / 未知。

    走根设备回溯：mountinfo 找 / 的挂载设备 → 回溯到最底层块设备
    → 看它的子系统（mmcblk? nvme? sd?）与父设备名（含 emmc / sd 字样）。
    """
    try:
        root_dev = _root_block_device()
    except Exception:  # noqa: BLE001
        return None
    if not root_dev:
        return None
    name = root_dev.split("/")[-1]
    if name.startswith("nvme"):
        return "NVMe（SSD，最耐用）"
    if name.startswith("sd"):
        return "SATA / USB（磁盘或固态，视具体设备）"
    if name.startswith("mmcblk"):
        try:
            p = _SYS_ROOT / "sys" / "class" / "block" / name / "device"
            path = str(p.resolve())
            if "emmc" in path.lower():
                return "eMMC（板载，比 SD 耐用）"
        except Exception:  # noqa: BLE001
            pass
        return "SD 卡（最易掉速/损坏，建议换 eMMC 或 SSD）"
    return "未知"


def _root_block_device() -> Optional[str]:
    """从 mountinfo 找 / 的底层块设备。"""
    mi = _SYS_ROOT / "proc" / "self" / "mountinfo"
    try:
        for line in mi.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) < 10:
                continue
            if parts[4] == "/":
                # /proc/self/mountinfo 第 9 字段（0-based index 8）是挂载源设备
                dev = parts[8] if len(parts) > 8 else parts[-1]
                m = re.match(r"(/dev/[a-z]+)(\d+)?", dev)
                if m:
                    return m.group(1)
                return dev
    except Exception:  # noqa: BLE001
        return None
    return None


def edge_report() -> Tuple[bool, str]:
    """把探测结果整理成只读建议。非 SBC 时明确说「未识别为单板机」。"""
    board = detect_board()
    if not board:
        return True, ("未识别为单板机（detect_board 读不到设备树型号）。\n"
                     "本层只在 ARM / RISC-V 等带设备树的 SBC 上才有数据；"
                     "x86 桌面/服务器走各自的硬件优化任务即可。")
    lines = [f"==== 单板机探测：{board} ====", ""]

    zones = thermal_zones()
    if zones:
        hottest = max(zones, key=lambda z: z["temp_c"])  # type: ignore[arg-type]
        lines.append(f"  温度：最高 {hottest['temp_c']}°C（{hottest['type']}）")
        if hottest["temp_c"] >= 80:  # type: ignore[operator]
            lines.append("    ⚠ 偏高：被动散热的 SBC 长期 >80°C 会降频、伤寿命。"
                        " 建议加散热片/风扇、避免密闭外壳、降负载。")
        elif hottest["temp_c"] >= 70:  # type: ignore[operator]
            lines.append("    偏暖：关注机箱通风，必要时加被动散热。")
    else:
        lines.append("  温度：未读到 thermal zone（内核未暴露或不是标准 SBC）。")

    th = throttle_state()
    if th is None:
        lines.append("  降频/欠压：本板未暴露 throttled 位（非 Broadcom 平台），"
                    " 以温度为准判断。")
    else:
        flags = [k for k in ("under_voltage", "arm_freq_capped", "throttled_now",
                             "soft_temp_limit") if th[k]]
        if flags:
            lines.append(f"    ⚠ 降频/供电标志：{', '.join(flags)}。")
            lines.append("    最常见是供电不足（under-voltage）：换 5V≥3A 的电源，"
                        " 用太细/太长的线会掉压；降频会直接拖慢一切。")
        else:
            lines.append("  降频/供电：当前无异常标志。")

    media = boot_media()
    if media:
        lines.append(f"  启动盘：{media}")
        if "SD 卡" in media:
            lines.append("    SD 卡寿命最短、最易在意外断电时损坏文件系统。"
                        " 建议：根分区换 eMMC/NVMe，SD 只做应急启动；"
                        " 开 fstrim 没用（SD 不支持），但要做定期备份。")

    lines += ["",
              "红线：以上全是只读建议。本层不改频率、不改电压、不装散热服务、"
              "不写任何 sysfs——要不要照做、怎么做，由你决定。"]
    return True, "\n".join(lines)


def board_only_report() -> Tuple[bool, str]:
    """只回板型（GUI/CLI 快速展示用）。"""
    board = detect_board()
    if board:
        return True, f"识别到单板机：{board}"
    return True, "未识别为单板机（无设备树型号，或当前不是 ARM/RISC-V SBC）。"


def capabilities_report() -> Tuple[bool, str]:
    """本层能力自检。"""
    lines = [
        "==== 单板机（SBC）只读层 ====",
        "  板型：设备树 /proc/device-tree/model ✓",
        "  温度：/sys/class/thermal/* ✓",
        "  降频/欠压：Broadcom throttled 位掩码（其它平台退化到看温度）✓",
        "  启动盘：/proc/self/mountinfo 回溯 ✓",
        "",
        "红线：只读。不写 sysfs、不调 vcgencmd 改频率/电压、不装服务。",
    ]
    return True, "\n".join(lines)


def edge_profile() -> dict:
    """结构化返回探测结果（测试与任务层共用，不碰 IO 之外的副作用）。"""
    return {
        "board": detect_board(),
        "thermal": thermal_zones(),
        "throttle": throttle_state(),
        "boot_media": boot_media(),
    }
