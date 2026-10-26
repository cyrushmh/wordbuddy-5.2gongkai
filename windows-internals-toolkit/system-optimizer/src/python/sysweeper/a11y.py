"""无障碍支持：Linux ORCA 屏幕阅读器与 AT-SPI2 辅助技术接口。

ORCA（GNOME 桌面屏幕阅读器）通过 **AT-SPI2**（Assistive Technology Service
Provider Interface）与应用程序通信；AT-SPI2 本身构建在 D-Bus 之上，即
「辅助技术总线」`org.a11y.Bus`。本模块把这些协议与接口封装成可探测、可报告的
纯标准库函数，并为图形界面提供屏幕阅读器友好的输出。

协议要点（AT-SPI2 / D-Bus）
--------------------------
    总线        : org.a11y.Bus（由 at-spi-bus-launcher 拉起）
    注册表      : org.a11y.atspi.Registry（对象路径 /org/a11y/atspi/registry）
    对象接口    : Accessible / Action / Component / Text / EditableText /
                  Selection / Value / Table / Document / Hyperlink / Image
    事件        : org.a11y.atspi.Event.Object:StateChanged、
                  Event.Object:TextChanged、Event.Focus（应用向读屏器广播）
    客户端库    : libatspi（C）、pyatspi2（Python 绑定）、at-spi2-core

启用开关（GNOME / ORCA）
------------------------
    gsettings get org.gnome.desktop.a11y.applications screen-reader-enabled
    gsettings set org.gnome.desktop.a11y.applications screen-reader-enabled true
    orca --replace   # 重启屏幕阅读器
    orca --setup     # 打开 ORCA 图形设置
    配置目录        : ~/.local/share/orca（用户偏好与语音配置）

设计原则：纯标准库、零依赖、graceful——任何探测失败都返回 ``(False, 说明)``，
绝不因缺少 orca / dbus / gsettings 而在 import 或调用阶段抛异常。
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import List, Optional, Tuple

# ---------------------------------------------------------------- 协议常量

AT_SPI_BUS = "org.a11y.Bus"
AT_SPI_REGISTRY_PATH = "/org/a11y/atspi/registry"
AT_SPI_REGISTRY_IFACE = "org.a11y.atspi.Registry"
AT_SPI_LAUNCHER = "at-spi-bus-launcher"

# AT-SPI2 常用接口（供 DBus 调试 / 无障碍自检时引用）
AT_SPI_INTERFACES = {
    "Accessible": "org.a11y.atspi.Accessible",
    "Action": "org.a11y.atspi.Action",
    "Application": "org.a11y.atspi.Application",
    "Collection": "org.a11y.atspi.Collection",
    "Component": "org.a11y.atspi.Component",
    "Document": "org.a11y.atspi.Document",
    "EditableText": "org.a11y.atspi.EditableText",
    "Hyperlink": "org.a11y.atspi.Hyperlink",
    "Hypertext": "org.a11y.atspi.Hypertext",
    "Image": "org.a11y.atspi.Image",
    "Selection": "org.a11y.atspi.Selection",
    "Socket": "org.a11y.atspi.Socket",
    "Table": "org.a11y.atspi.Table",
    "TableCell": "org.a11y.atspi.TableCell",
    "Text": "org.a11y.atspi.Text",
    "Value": "org.a11y.atspi.Value",
}

# ORCA / GNOME 无障碍开关
GS_SCHEMA = "org.gnome.desktop.a11y.applications"
GS_KEY_SCREEN_READER = "screen-reader-enabled"

# ORCA 配置与缓存目录（相对家目录）
ORCA_CONFIG_DIRS = (".local/share/orca", ".local/share/orca/orca-scripts",
                    ".config/orca", ".cache/orca")


# ---------------------------------------------------------------- 基础工具

def which(cmd: str) -> Optional[str]:
    """返回可执行文件绝对路径；没有就 None。"""
    try:
        return shutil.which(cmd)
    except Exception:  # noqa: BLE001
        return None


def _run(cmd, timeout: int = 8) -> Tuple[bool, str]:
    """跑一条命令，返回 (是否成功, 输出)。失败也返回、不抛。"""
    try:
        r = subprocess.run(cmd, shell=isinstance(cmd, str),
                           capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or "").strip() or (r.stderr or "").strip()
        return r.returncode == 0, out[-1000:]
    except Exception as e:  # noqa: BLE001
        return False, f"执行失败: {e}"


# ---------------------------------------------------------------- 探测

def orca_available() -> bool:
    """ORCA 屏幕阅读器是否已安装。"""
    return which("orca") is not None


def orca_version() -> Tuple[bool, str]:
    """读取 ORCA 版本；未安装或读取失败返回 (False, 说明)。"""
    if not orca_available():
        return False, "未安装 orca（可用包管理器安装 gnome-orca / orca）"
    ok, out = _run(["orca", "--version"])
    return (ok, out) if ok and out else (False, "已安装 orca，但 --version 无输出")


def atspi_bus_available() -> Tuple[bool, str]:
    """探测 AT-SPI2 辅助技术总线（org.a11y.Bus）是否可用。

    依次尝试 dbus-send / gdbus；两者都不可用则降级为「无法探测」并给出提示。
    """
    if which("dbus-send"):
        ok, out = _run(["dbus-send", "--bus=" + AT_SPI_BUS, "--dest=" + AT_SPI_REGISTRY_IFACE,
                        "--type=method_call", "--print-reply", AT_SPI_REGISTRY_PATH,
                        "org.a11y.atspi.Registry.GetRegisteredEvents"])
        if ok:
            return True, "AT-SPI2 总线可用（org.a11y.Bus 已响应）"
        return False, f"org.a11y.Bus 未响应: {out or '无输出'}"
    if which("gdbus"):
        ok, out = _run(["gdbus", "call", "--bus=" + AT_SPI_BUS, "--dest=" + AT_SPI_REGISTRY_IFACE,
                        "--object-path", AT_SPI_REGISTRY_PATH,
                        "--method", "org.a11y.atspi.Registry.GetRegisteredEvents"])
        if ok:
            return True, "AT-SPI2 总线可用（gdbus 探测成功）"
        return False, f"org.a11y.Bus 未响应: {out or '无输出'}"
    return False, "未找到 dbus-send / gdbus，无法探测 AT-SPI2 总线（可安装 dbus-tools）"


def gsettings_get(schema: str, key: str) -> Tuple[bool, str]:
    """读取一个 gsettings 键；无 gsettings（非 GNOME）时降级。"""
    if not which("gsettings"):
        return False, "未找到 gsettings（非 GNOME 桌面或缺少命令）"
    return _run(["gsettings", "get", schema, key])


def screen_reader_enabled() -> Tuple[bool, str]:
    """系统是否启用屏幕阅读器自启动（GNOME 无障碍开关）。"""
    ok, out = gsettings_get(GS_SCHEMA, GS_KEY_SCREEN_READER)
    if not ok:
        return False, out
    val = out.strip().lower()
    if "true" in val:
        return True, "已启用屏幕阅读器自启动（screen-reader-enabled = true）"
    return False, f"未启用屏幕阅读器自启动（screen-reader-enabled = {out.strip()}）"


def orca_config_dirs() -> List[str]:
    """ORCA 相关配置/缓存目录（家目录下），存在的排在前面。"""
    home = os.path.expanduser("~")
    found = []
    for rel in ORCA_CONFIG_DIRS:
        p = os.path.join(home, rel)
        if os.path.isdir(p):
            found.append(p)
    return found


# ---------------------------------------------------------------- 语音输出

# 语音合成后端：命令模板 + 友好名（按顺序尝试，跨平台降级）
_SPEAK_BACKENDS = (
    (["spd-say", "{text}"], "speech-dispatcher（spd-say，ORCA 默认语音服务）"),
    (["espeak-ng", "{text}"], "eSpeak NG"),
    (["espeak", "{text}"], "eSpeak"),
    (["say", "{text}"], "macOS say"),
)


def speak_backend() -> Optional[str]:
    """当前可用的语音合成后端名；无则返回 None（此时朗读降级为「仅显示文本」）。"""
    for cmd, name in _SPEAK_BACKENDS:
        if which(cmd[0]):
            return name
    return None


def speak(text: str) -> Tuple[bool, str]:
    """朗读一段文本（供图形界面「朗读结果」使用）。

    找不到语音后端时返回 (False, 说明)——不报错、不影响主流程。
    """
    text = (text or "").strip()
    if not text:
        return False, "无内容可朗读"
    for cmd, name in _SPEAK_BACKENDS:
        if which(cmd[0]):
            real = [c.replace("{text}", text) for c in cmd]
            ok, out = _run(real, timeout=60)
            return (True, f"已用 {name} 朗读") if ok else (False, f"{name} 朗读失败: {out}")
    return False, "未找到语音后端（spd-say / espeak / say）；结果仍以文本呈现，可复制给读屏器"


# ---------------------------------------------------------------- 友好输出

_DECORATIONS = "─│┌┐└┘━═╔╗╚╝■□●○▪▫★☆→←↑↓✔✗✅❌"


def accessible_text(text: str) -> str:
    """把带装饰符号的文本转成屏幕阅读器友好的纯文本。

    去除制表/框线字符、把项目符号读法统一、压缩空行——读屏器朗读更连贯。
    """
    if not text:
        return ""
    for ch in _DECORATIONS:
        text = text.replace(ch, " ")
    out_lines = []
    for line in text.splitlines():
        line = line.rstrip()
        if not line.strip():
            continue
        # 统一符号读法：•/- 开头读作「项目」
        stripped = line.lstrip()
        if stripped[:1] in ("•", "-", "*"):
            stripped = "项目 " + stripped[1:].lstrip()
        out_lines.append(stripped)
    return "\n".join(out_lines)


# ---------------------------------------------------------------- 综合报告

def atspi_interface_hints() -> List[str]:
    """AT-SPI2 接口的自检命令示例（便于用 ORCA 协议/接口排查问题）。"""
    hints = [
        f"辅助技术总线: {AT_SPI_BUS}（由 {AT_SPI_LAUNCHER} 拉起）",
        f"注册表对象  : {AT_SPI_REGISTRY_PATH} ({AT_SPI_REGISTRY_IFACE})",
        "常用接口    : " + ", ".join(sorted(AT_SPI_INTERFACES)[:6]) + " …",
        "自检命令    : dbus-send --bus=org.a11y.Bus --dest=org.a11y.atspi.Registry "
                      "--type=method_call --print-reply /org/a11y/atspi/registry "
                      "org.a11y.atspi.Registry.GetRegisteredEvents",
        "读屏器      : orca --replace（重启）/ orca --setup（设置）",
        "开关        : gsettings set org.gnome.desktop.a11y.applications "
                      "screen-reader-enabled true",
    ]
    return hints


def orca_enable_commands() -> List[str]:
    """启用 ORCA / 屏幕阅读器的命令清单（供展示或复制执行）。"""
    return [
        "gsettings set org.gnome.desktop.a11y.applications screen-reader-enabled true",
        "orca --replace &",          # 启动/重启 ORCA
        "orca --setup",              # 打开 ORCA 设置（语音/语速/标点）
    ]


def environment_report() -> List[str]:
    """无障碍环境综合报告（纯只读）。每项都 graceful，不会抛异常。"""
    lines = ["=" * 68, "无障碍环境报告（ORCA / AT-SPI2）", "=" * 68]

    ok, msg = orca_version()
    lines.append(f"ORCA 安装      : {'是' if ok else '否'} — {msg}")

    ok, msg = atspi_bus_available()
    lines.append(f"AT-SPI2 总线   : {'可用' if ok else '不可用'} — {msg}")

    ok, msg = screen_reader_enabled()
    lines.append(f"读屏器自启动   : {'已启用' if ok else '未启用'} — {msg}")

    dirs = orca_config_dirs()
    lines.append("ORCA 配置目录  : " + ("；".join(dirs) if dirs else "（无，首次运行 ORCA 后生成）"))

    backend = speak_backend()
    lines.append("语音后端       : " + (backend or "（无——朗读将降级为纯文本呈现）"))

    lines.append("")
    lines.append("-" * 68)
    lines.append("协议与接口（AT-SPI2 / D-Bus）：")
    for h in atspi_interface_hints():
        lines.append("  " + h)
    lines.append("")
    lines.append("标准参考（按受众分层，见 standards --audience）：")
    lines.append("  国标: GB/T 37668 信息技术 无障碍 通用设计规范 / GB/T 38652")
    lines.append("  国际: W3C WCAG 2.2 / WAI-ARIA 1.2 / AT-SPI2（GNOME at-spi2-core）")
    lines.append("  地区: EN 301 549（欧盟）/ Section 508（美国）/ JIS X 8341（日本）")
    return lines


def a11y_report() -> Tuple[bool, str]:
    """供 native 通道调用：返回 (是否探测到可用信息, 报告文本)。"""
    try:
        lines = environment_report()
        return True, accessible_text("\n".join(lines))
    except Exception as e:  # noqa: BLE001
        return False, f"无障碍报告生成失败: {e}"


# --------------------------------------------------------------------------- #
# v0.5.18 无障碍适配多系统：Windows / macOS / Android / iOS / 鸿蒙              #
#                                                                             #
# 每种系统都有各自的屏幕阅读器与无障碍接口（与 Linux ORCA/AT-SPI2 同类机制）：  #
#   Windows : 讲述人(Narrator) + UI Automation(UIA) / MSAA                     #
#   macOS   : VoiceOver + NSAccessibility(AX API)                             #
#   Android : TalkBack + AccessibilityService（经 adb 只读查询）              #
#   iOS     : VoiceOver（设备端设置；PC 端经 libimobiledevice 仅读设备信息）   #
#   鸿蒙     : 系统无障碍 + AccessibilityExtensionAbility（经 hdc 只读查询）    #
# 所有探测只读、优雅降级（非对应平台返回 (False, 指引)，绝不抛）。              #
# --------------------------------------------------------------------------- #

# 多系统无障碍注册表：平台 → (屏幕阅读器, 无障碍接口, 启用快捷键/入口)
PLATFORM_A11Y = {
    "linux": ("ORCA", "AT-SPI2（D-Bus org.a11y.Bus）", "gsettings set … screen-reader-enabled true / orca --replace"),
    "windows": ("讲述人(Narrator)", "UI Automation(UIA) / MSAA", "Win+Ctrl+Enter 启动；或设置→辅助功能→讲述人"),
    "macos": ("VoiceOver", "NSAccessibility（AX API）", "Cmd+F5 启动；系统设置→辅助功能→VoiceOver"),
    "android": ("TalkBack", "AccessibilityService", "设置→辅助功能→TalkBack；或 adb 设 enabled_accessibility_services"),
    "ios": ("VoiceOver", "VoiceOver（设备端）", "设置→辅助功能→VoiceOver；或三击侧边键"),
    "harmony": ("系统无障碍(屏幕朗读)", "AccessibilityExtensionAbility", "设置→辅助功能→无障碍；或 hdc 设 enabled_accessibility_services"),
}


def win_narrator_status() -> Tuple[bool, str]:
    """Windows 讲述人(Narrator)状态（UIA / MSAA）。非 Windows 优雅降级。"""
    import sys
    if sys.platform != "win32":
        return False, "非 Windows 平台，讲述人(Narrator)不可用（可用 Win+Ctrl+Enter 启用）"
    ok, out = _run("tasklist /FI \"IMAGENAME eq Narrator.exe\" 2>nul")
    if ok and "Narrator.exe" in out:
        return True, "讲述人(Narrator)正在运行（UI Automation / UIA + MSAA）"
    return False, "讲述人未运行（可用 Win+Ctrl+Enter 启动；无障碍接口为 UIA/MSAA）"


def mac_voiceover_status() -> Tuple[bool, str]:
    """macOS VoiceOver 状态（NSAccessibility / AX API）。非 macOS 优雅降级。"""
    import sys
    if sys.platform != "darwin":
        return False, "非 macOS 平台，VoiceOver 不可用（可用 Cmd+F5 启用）"
    ok, out = _run(["defaults", "read", "com.apple.Accessibility", "VoiceOverOn"])
    if ok and out.strip() == "1":
        return True, "VoiceOver 已启用（NSAccessibility / AX API）"
    return False, "VoiceOver 未启用（Cmd+F5 启动；无障碍接口为 AX API）"


def android_talkback_status() -> Tuple[bool, str]:
    """Android TalkBack 状态（经 adb 只读查询 AccessibilityService）。无 adb 降级。"""
    if not which("adb"):
        return False, "未检测到 adb，无法探测 TalkBack（指引：adb 连接安卓设备后查询）"
    ok, out = _run("adb shell settings get secure enabled_accessibility_services")
    if ok and "talkback" in out.lower():
        return True, "TalkBack 已启用（Android AccessibilityService，经 adb 只读查询）"
    return False, "TalkBack 未启用（经 adb 设置 enabled_accessibility_services 启用，指引）"


def ios_voiceover_status() -> Tuple[bool, str]:
    """iOS VoiceOver 状态。PC 端经 libimobiledevice 仅读设备信息，不读此开关；给指引。"""
    if which("ideviceinfo"):
        return False, ("iOS VoiceOver 开关需设备端 设置→辅助功能→VoiceOver；"
                       "PC 端经 libimobiledevice 仅读设备信息，不发越权指令读取该开关")
    return False, "未连接 iOS 设备（libimobiledevice）；VoiceOver 开关请在设备端辅助功能设置"


def harmony_a11y_status() -> Tuple[bool, str]:
    """鸿蒙系统无障碍状态（经 hdc 只读查询 AccessibilityExtensionAbility）。无 hdc 降级。"""
    if not which("hdc"):
        return False, "未检测到 hdc，无法探测鸿蒙无障碍（指引：hdc 连接设备后查询）"
    ok, out = _run("hdc shell settings get secure enabled_accessibility_services")
    if ok and out.strip():
        return True, "鸿蒙已启用无障碍服务（AccessibilityExtensionAbility，经 hdc 只读查询）"
    return False, "鸿蒙无障碍服务未启用（hdc 设置 enabled_accessibility_services 启用，指引）"


# 平台 → 只读探测函数（Linux 复用 ORCA 现有函数）
_PROBE_BY_PLATFORM = {
    "linux": screen_reader_enabled,
    "windows": win_narrator_status,
    "macos": mac_voiceover_status,
    "android": android_talkback_status,
    "ios": ios_voiceover_status,
    "harmony": harmony_a11y_status,
}


def screen_reader_status(platform: str) -> Tuple[bool, str]:
    """探测指定平台的屏幕阅读器/无障碍是否可用（只读）。未知平台降级。"""
    fn = _PROBE_BY_PLATFORM.get(platform)
    if fn is None:
        return False, f"未知平台 {platform!r}，无法探测无障碍状态"
    return fn()


def a11y_probe_all(platform: Optional[str] = None) -> List[str]:
    """多系统无障碍只读报告。platform=None/any 时遍历全部系统，否则只报该平台。

    每项都 graceful，不会抛异常。返回文本行列表，供 CLI/GUI 展示。
    """
    lines = ["无障碍（多系统）环境报告（只读，按各自协议与接口）："]
    targets = [platform] if platform and platform != "any" else list(PLATFORM_A11Y)
    for pf in targets:
        sr, api, _entry = PLATFORM_A11Y.get(pf, (pf, "", ""))
        ok, msg = screen_reader_status(pf)
        lines.append(f"  · {pf:<8} 屏幕阅读器={sr}  接口={api}")
        lines.append(f"       状态: {'可用' if ok else '不可用'} — {msg}")
    return lines


def a11y_enable_commands(platform: Optional[str] = None) -> List[str]:
    """返回指定平台（或全部）启用无障碍的指引/命令清单。

    platform=None/any 返回「平台→命令列表」的多行文本；否则只返回该平台列表。
    """
    targets = [platform] if platform and platform != "any" else list(PLATFORM_A11Y)
    out = []
    for pf in targets:
        sr, _api, entry = PLATFORM_A11Y.get(pf, (pf, "", ""))
        out.append(f"# {pf}（屏幕阅读器：{sr}）")
        for c in _enable_list_for(pf):
            out.append("   " + c)
        if entry:
            out.append(f"   入口: {entry}")
    return out


def _enable_list_for(platform: str) -> List[str]:
    """按平台返回启用命令/指引（只读友好）。"""
    if platform == "linux":
        return orca_enable_commands()
    if platform == "windows":
        return [
            "Win+Ctrl+Enter 启动/退出讲述人(Narrator)",
            "设置 → 辅助功能 → 讲述人：配置语音、语速、详细程度",
            "（PowerShell 可选）Start-Process narrator",
        ]
    if platform == "macos":
        return [
            "Cmd+F5 启动/关闭 VoiceOver",
            "系统设置 → 辅助功能 → VoiceOver：配置语音与 rotor",
            "终端校验: defaults read com.apple.Accessibility VoiceOverOn",
        ]
    if platform == "android":
        return [
            "设置 → 辅助功能 → TalkBack（开关）",
            "adb shell settings put secure enabled_accessibility_services "
            "com.google.android.marvin.talkback/.TalkBackService",
            "（只读查询）adb shell settings get secure enabled_accessibility_services",
        ]
    if platform == "ios":
        return [
            "设置 → 辅助功能 → VoiceOver（开关）",
            "三击侧边键/主屏幕键 快速切换 VoiceOver",
            "（PC 端仅经 libimobiledevice 读设备信息，不读该开关）",
        ]
    if platform == "harmony":
        return [
            "设置 → 辅助功能 → 屏幕朗读/无障碍（开关）",
            "hdc shell settings put secure enabled_accessibility_services <bundle>/<Service>",
            "（只读查询）hdc shell settings get secure enabled_accessibility_services",
        ]
    return [f"# 未知平台 {platform!r}"]


def environment_report(platform: Optional[str] = None) -> List[str]:
    """无障碍环境综合报告（纯只读）。

    - platform=None：先报 Linux ORCA/AT-SPI2，再附多系统概览（a11y_probe_all）。
    - platform 指定：优先报该平台的无障碍状态。
    每项都 graceful，不会抛异常。
    """
    lines = ["=" * 68, "无障碍环境报告", "=" * 68]

    if platform and platform != "linux" and platform != "any" and platform is not None:
        # 指定非 Linux 平台：直接报该平台
        ok, msg = screen_reader_status(platform)
        sr, api, entry = PLATFORM_A11Y.get(platform, (platform, "", ""))
        lines.append(f"平台: {platform}  屏幕阅读器={sr}  接口={api}")
        lines.append(f"状态: {'可用' if ok else '不可用'} — {msg}")
        lines.append("")
        lines.append("启用指引：")
        for c in a11y_enable_commands(platform):
            lines.append("  " + c)
        return lines

    # 默认：Linux ORCA/AT-SPI2 详情 + 多系统概览
    ok, msg = orca_version()
    lines.append(f"ORCA 安装      : {'是' if ok else '否'} — {msg}")
    ok, msg = atspi_bus_available()
    lines.append(f"AT-SPI2 总线   : {'可用' if ok else '不可用'} — {msg}")
    ok, msg = screen_reader_enabled()
    lines.append(f"读屏器自启动   : {'已启用' if ok else '未启用'} — {msg}")
    dirs = orca_config_dirs()
    lines.append("ORCA 配置目录  : " + ("；".join(dirs) if dirs else "（无，首次运行 ORCA 后生成）"))
    backend = speak_backend()
    lines.append("语音后端       : " + (backend or "（无——朗读将降级为纯文本呈现）"))
    lines.append("")
    lines.append("-" * 68)
    lines.append("协议与接口（AT-SPI2 / D-Bus）：")
    for h in atspi_interface_hints():
        lines.append("  " + h)
    lines.append("")
    lines.append("-" * 68)
    lines.append("多系统无障碍概览（适配 Windows/macOS/Android/iOS/鸿蒙）：")
    for ln in a11y_probe_all("any"):
        if ln.startswith("无障碍"):
            continue
        lines.append("  " + ln)
    lines.append("")
    lines.append("标准参考（按受众分层，见 standards --audience）：")
    lines.append("  国标: GB/T 37668 信息技术 无障碍 通用设计规范 / GB/T 38652")
    lines.append("  国际: W3C WCAG 2.2 / WAI-ARIA 1.2 / AT-SPI2（GNOME at-spi2-core）")
    lines.append("  地区: EN 301 549（欧盟）/ Section 508（美国）/ JIS X 8341（日本）")
    return lines


# ---------------------------------------------------------------- 权威文档

def _load_a11y_docs() -> dict:
    """从 data/a11y_docs.json 载入多系统无障碍权威文档。"""
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "a11y_docs.json").read_text(encoding="utf-8")
        import json
        return json.loads(data)
    except Exception:  # noqa: BLE001
        return {}


A11Y_REFS = _load_a11y_docs()


def a11y_reference(doc_id: str) -> dict:
    """返回某无障碍文档参考（含 protocols / interfaces / docs）。"""
    return A11Y_REFS.get(doc_id, {})


def a11y_reference_all() -> dict:
    """返回全部无障碍文档参考（多系统）。"""
    return A11Y_REFS


def a11y_doc_list() -> List[str]:
    """列出多系统无障碍权威文档（名称 / 组织 / 协议 / URL）。"""
    lines = ["多系统无障碍权威文档："]
    for doc_id, ref in A11Y_REFS.items():
        name = ref.get("name", doc_id)
        org = ref.get("org", "")
        protos = "、".join(ref.get("protocols", []) or [])
        url = ref.get("url", "")
        lines.append(f"  · [{doc_id}] {name}（{org}）")
        if protos:
            lines.append(f"      协议/标准: {protos}")
        if url:
            lines.append(f"      {url}")
    return lines


__all__ = [
    "AT_SPI_BUS", "AT_SPI_REGISTRY_PATH", "AT_SPI_REGISTRY_IFACE", "AT_SPI_INTERFACES",
    "GS_SCHEMA", "GS_KEY_SCREEN_READER",
    "orca_available", "orca_version", "atspi_bus_available", "gsettings_get",
    "screen_reader_enabled", "orca_config_dirs", "speak_backend", "speak",
    "accessible_text", "atspi_interface_hints", "orca_enable_commands",
    "environment_report", "a11y_report",
    # v0.5.18 多系统无障碍
    "PLATFORM_A11Y", "win_narrator_status", "mac_voiceover_status",
    "android_talkback_status", "ios_voiceover_status", "harmony_a11y_status",
    "screen_reader_status", "a11y_probe_all", "a11y_enable_commands",
    "A11Y_REFS", "a11y_reference", "a11y_reference_all", "a11y_doc_list",
]
