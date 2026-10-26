"""其他系统软件（systemd / D-Bus / NetworkManager / PipeWire / BlueZ / udev / polkit / Wayland）
原生接口与文档引用。

「触类旁通、举一反三」：v0.5.0 已把 Linux 内核（硬件/软件/网络子系统）与桌面环境
（GNOME/KDE/XFCE）的「文档跟踪 + 只读探测 + 任务」模式落地；本层把同一模式推广到
**其余系统软件**——各自按自身的协议与接口核对，而不是套用内核那套：

- systemd        : 单元文件指令(systemd.unit(5)) + D-Bus org.freedesktop.systemd1 + journal 字段
- D-Bus          : D-Bus Specification + Introspectable / Properties 标准接口
- NetworkManager : D-Bus org.freedesktop.NetworkManager + nm-settings(5) keyfile
- PipeWire       : PipeWire 原生协议(SPA 节点图) + D-Bus org.pipewire
- BlueZ          : D-Bus org.bluez（Adapter1 / Device1）
- udev           : 规则语法(udev(7)) + hwdb(7) + 内核 uevent
- polkit         : D-Bus org.freedesktop.PolicyKit1 + .policy / .rules
- Wayland        : wayland.xml 核心协议 + xdg-shell 等扩展协议

所有探测只读、惰性守卫：未安装该软件 / 非该运行环境时返回 (False, 说明)，由上层降级为
指引，绝不修改系统。参考文档见 data/syssoftware_docs.json。
"""

from __future__ import annotations

import json
import os
import shutil


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "syssoftware_docs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:
        return {}


REFS = _load_refs()


def reference(software_id: str) -> dict:
    """返回某系统软件的文档参考（含协议 protocols 与接口 interfaces）。"""
    return REFS.get(software_id, {})


def reference_all() -> dict:
    """返回全部系统软件文档参考。"""
    return REFS


def software_name(key: str) -> str:
    """返回该软件在参考表中的名称（无则回退键名）。"""
    return REFS.get(key, {}).get("name", key)


def detect_syssoftware() -> dict:
    """探测本机可用/运行的系统软件（按官方 CLI 接口与会话环境判断）。"""
    rt = os.environ.get("XDG_RUNTIME_DIR", "")
    pw_sock = os.path.join(rt, "pipewire-0") if rt else ""
    return {
        "systemd": bool(shutil.which("systemctl")),
        "dbus": bool(shutil.which("busctl") or shutil.which("dbus-send")),
        "networkmanager": bool(shutil.which("nmcli")),
        "pipewire": bool(shutil.which("pw-cli") or shutil.which("pw-top")
                         or (pw_sock and os.path.exists(pw_sock))),
        "bluez": bool(shutil.which("bluetoothctl")),
        "udev": bool(shutil.which("udevadm")),
        "polkit": bool(shutil.which("pkaction")),
        "wayland": bool(os.environ.get("WAYLAND_DISPLAY")),
    }


def _common_run(cmd: str):
    from . import common
    return common.run(cmd)


# ---------------------------------------------------------------------------
# 各软件只读探测（均返回 (ok, msg)，ok=False 表示「当前不适用」并给出降级说明）
# ---------------------------------------------------------------------------

def systemd_report() -> tuple:
    """systemd：失败单元 / journal 占用 / 启动耗时（只读）。"""
    if not shutil.which("systemctl"):
        return False, "未安装 systemd（无 systemctl）；非 systemd 发行版（SysV init / OpenRC / runit）跳过。"
    lines = []
    _rc, out = _common_run("systemctl --failed --no-legend 2>/dev/null")
    failed = [l.strip() for l in (out or "").splitlines() if l.strip()]
    lines.append("失败单元: " + (f"{len(failed)} 个" if failed else "无"))
    for l in failed[:5]:
        lines.append("   · " + l)
    _rc2, out2 = _common_run("journalctl --disk-usage 2>/dev/null | tail -1")
    if (out2 or "").strip():
        lines.append("journal 占用: " + out2.strip())
    _rc3, out3 = _common_run("systemd-analyze 2>/dev/null | head -2")
    if (out3 or "").strip():
        lines.append("启动耗时: " + " / ".join(
            l.strip() for l in out3.strip().splitlines() if l.strip()))
    lines.append("接口: systemctl(1) / journalctl(1) / systemd-analyze(1) / busctl(1)；"
                 "协议: systemd.unit(5) + org.freedesktop.systemd1")
    return True, "\n".join(lines)


def dbus_report() -> tuple:
    """D-Bus：系统总线服务名自省（只读，按 D-Bus Specification）。"""
    if not (shutil.which("busctl") or shutil.which("dbus-send")):
        return False, "未安装 busctl / dbus-send；无法自省 D-Bus 总线（容器/极简环境常见）。"
    if not shutil.which("busctl"):
        return True, "仅有 dbus-send（无 busctl）：可用 `dbus-send --system --dest=...` 按规范调用；" \
                     "列出总线名建议安装 systemd 提供的 busctl。"
    _rc, out = _common_run("busctl list --no-legend 2>/dev/null")
    names = []
    for l in (out or "").splitlines():
        parts = l.split()
        if parts:
            names.append(parts[0])
    lines = [f"系统总线服务名: {len(names)} 个"]
    for n in names[:6]:
        lines.append("   · " + n)
    if len(names) > 6:
        lines.append(f"   …（共 {len(names)} 个）")
    lines.append("标准接口: org.freedesktop.DBus / .Introspectable / .Properties；"
                 "协议见 D-Bus Specification")
    return True, "\n".join(lines)


def networkmanager_report() -> tuple:
    """NetworkManager：全局状态与活动连接数（只读 D-Bus 状态）。"""
    if not shutil.which("nmcli"):
        return False, "未安装 nmcli（NetworkManager）；网络由 systemd-networkd / netplan / 手工配置时跳过。"
    lines = []
    _rc, out = _common_run("nmcli -t -f STATE general 2>/dev/null")
    state = (out or "").strip().splitlines()
    if state:
        lines.append("NM 状态: " + state[0])
    _rc2, out2 = _common_run("nmcli -t -f NAME,TYPE connection show --active 2>/dev/null")
    conns = [l.strip() for l in (out2 or "").splitlines() if l.strip()]
    lines.append(f"活动连接: {len(conns)} 个")
    for c in conns[:5]:
        lines.append("   · " + c)
    lines.append("接口: nmcli(1)；协议: org.freedesktop.NetworkManager + nm-settings(5)")
    return True, "\n".join(lines)


def pipewire_report() -> tuple:
    """PipeWire：节点图与守护进程状态（只读）。"""
    rt = os.environ.get("XDG_RUNTIME_DIR", "")
    sock = os.path.join(rt, "pipewire-0") if rt else ""
    has = bool(shutil.which("pw-cli") or shutil.which("pw-top"))
    if not has and not (sock and os.path.exists(sock)):
        return False, "未运行 PipeWire（无 pw-cli/pw-top 且无 $XDG_RUNTIME_DIR/pipewire-0）；" \
                      "仍用 PulseAudio 或无音频服务时跳过。"
    if shutil.which("pw-cli"):
        _rc, out = _common_run("pw-cli ls 2>/dev/null | head -20")
        rows = [l.strip() for l in (out or "").splitlines() if l.strip()]
        if rows:
            return True, (f"PipeWire 图对象（pw-cli ls 前 {len(rows)} 行）:\n   "
                          + "\n   ".join(rows[:6])
                          + "\n接口: pw-cli(1) / pw-top(1) / pw-metadata(1)；"
                            "协议: PipeWire 原生(SPA) + org.pipewire")
    if sock and os.path.exists(sock):
        return True, f"PipeWire 套接字存在: {sock}（未装 pw-cli，无法展开节点图）；" \
                     "装 pw-cli 后可 `pw-cli info` 按 SPA 节点图核对。"
    return True, "检测到 PipeWire 工具但未取得节点图（可能守护进程未运行）。"


def bluez_report() -> tuple:
    """BlueZ：适配器与已配对设备（只读 D-Bus org.bluez）。"""
    if not shutil.which("bluetoothctl"):
        return False, "未安装 bluetoothctl（BlueZ）；未启用蓝牙或极简环境跳过。"
    lines = []
    _rc, out = _common_run("bluetoothctl list 2>/dev/null")
    ctrls = [l.strip() for l in (out or "").splitlines() if l.strip()]
    lines.append(f"蓝牙适配器: {len(ctrls)} 个")
    for c in ctrls[:3]:
        lines.append("   · " + c)
    _rc2, out2 = _common_run("bluetoothctl devices 2>/dev/null")
    devs = [l.strip() for l in (out2 or "").splitlines() if l.strip()]
    lines.append(f"已配对设备: {len(devs)} 个")
    for d in devs[:5]:
        lines.append("   · " + d)
    lines.append("接口: bluetoothctl(1) / bluetoothd(8)；协议: org.bluez（Adapter1/Device1）")
    return True, "\n".join(lines)


def udev_report() -> tuple:
    """udev：自定义规则数与调试接口（只读，按 udev(7) 规则语法）。"""
    if not shutil.which("udevadm"):
        return False, "未安装 udevadm（systemd-udev）；非 systemd 或容器环境（无设备事件）跳过。"
    n = 0
    d = "/etc/udev/rules.d"
    if os.path.isdir(d):
        try:
            n = len([f for f in os.listdir(d) if f.endswith(".rules")])
        except OSError:
            n = 0
    return True, (f"自定义 udev 规则: {n} 个（{d}/*.rules，按 udev(7) 规则语法）\n"
                  "调试: `udevadm info`（只读查属性）/ `udevadm monitor`（监听 uevent）；\n"
                  "协议: udev(7) 规则 + hwdb(7) + 内核 netlink kobject uevent")


def polkit_report() -> tuple:
    """polkit：已注册 action 与默认授权（只读 pkaction）。"""
    if not shutil.which("pkaction"):
        return False, "未安装 pkaction（polkit）；极简/容器环境通常不含授权框架。"
    _rc, out = _common_run("pkaction 2>/dev/null")
    actions = [l.strip() for l in (out or "").splitlines() if l.strip()]
    lines = [f"已注册 action: {len(actions)} 个（pkaction）"]
    for a in actions[:5]:
        lines.append("   · " + a)
    if len(actions) > 5:
        lines.append(f"   …（共 {len(actions)} 个）")
    lines.append("接口: pkaction(1) / pkexec(1) / pkcheck(1)；"
                 "协议: org.freedesktop.PolicyKit1 + .policy / .rules")
    return True, "\n".join(lines)


def wayland_report() -> tuple:
    """Wayland：会话合成器判定与协议核对（只读环境变量 + wayland-info）。"""
    wd = os.environ.get("WAYLAND_DISPLAY", "")
    st = os.environ.get("XDG_SESSION_TYPE", "")
    if not (st == "wayland" or wd):
        return False, (f"当前非 Wayland 会话（XDG_SESSION_TYPE={st or '(未设置)'}，"
                       f"WAYLAND_DISPLAY={wd or '(未设置)'}）；X11 或纯控制台环境跳过。")
    lines = [f"Wayland 会话: WAYLAND_DISPLAY={wd or '(空)'} / XDG_SESSION_TYPE={st or '(空)'}"]
    if shutil.which("wayland-info"):
        _rc, out = _common_run("wayland-info 2>/dev/null | grep -c '^interface:'")
        cnt = (out or "").strip()
        if cnt:
            lines.append(f"合成器全局接口数（wayland-info）: {cnt}")
    else:
        lines.append("未装 wayland-info：装后可按协议列出合成器支持的全部全局接口。")
    lines.append("协议: wayland.xml 核心 + xdg-shell（及 xdg-decoration / linux-dmabuf 等扩展）")
    return True, "\n".join(lines)


# 探测函数 → 展示标签（CLI/GUI 统一遍历，避免重复列表）
PROBES = (
    ("systemd_report", "systemd（单元 / D-Bus / journal）"),
    ("dbus_report", "D-Bus（org.freedesktop.DBus 规范）"),
    ("networkmanager_report", "NetworkManager（org.freedesktop.NetworkManager）"),
    ("pipewire_report", "PipeWire（协议 / SPA / org.pipewire）"),
    ("bluez_report", "BlueZ（org.bluez）"),
    ("udev_report", "udev（规则 / hwdb / uevent）"),
    ("polkit_report", "polkit（org.freedesktop.PolicyKit1）"),
    ("wayland_report", "Wayland（wayland.xml / xdg-shell）"),
)


def environment_report() -> list:
    """返回系统软件环境跟踪报告（多行文本），供 CLI/GUI 展示。"""
    det = detect_syssoftware()
    lines = ["本机系统软件探测（按各自官方接口）："]
    for key in REFS:
        lines.append(f"   {software_name(key).split('（')[0]:<22} : "
                     f"{'✓ 可用' if det.get(key) else '✗ 未安装/未运行'}")
    lines.append("（未安装者不强求安装——对应任务自动降级为指引）")
    return lines


def syssoftware_doc_list(key: str = None) -> list:
    """返回文档引用行（含协议 protocols 与接口 interfaces），供 CLI/GUI 展示。"""
    items = {key: REFS[key]} if (key and key in REFS) else REFS
    lines = []
    for _k, ref in items.items():
        lines.append(f"   · {ref.get('name','')}  [{ref.get('org','')}]")
        lines.append(f"       文档: {ref.get('url','')}")
        for p in ref.get("protocols", [])[:2]:
            lines.append(f"       协议: {p}")
        for i in ref.get("interfaces", [])[:2]:
            lines.append(f"       接口: {i}")
    return lines
