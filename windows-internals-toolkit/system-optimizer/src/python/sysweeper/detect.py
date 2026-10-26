"""平台与版本自动探测（纯标准库，跨平台）。

探测优先调用「系统原生接口」（见 sysweeper.native）：
- Windows : winreg 注册表（权威版本源）+ 环境变量
- Linux   : LSB 规范文件 /etc/os-release（与 lsb_release 同源）
- macOS   : sw_vers + libc sysctlbyname
- BSD     : sysctlbyname（libc）/ uname；各 BSD 同源（FreeBSD/OpenBSD/NetBSD/DragonFly）
- Unix    : System V 系（Solaris / illumos），读 /etc/release + uname
- Android : adb getprop（需设备已连接）
- iOS     : libimobiledevice ideviceinfo（需设备已连接）
- 鸿蒙    : hdc list targets + param get（需设备已连接）

探测结果可能不完整（例如容器里读不到 macOS 版本），因此 CLI 始终允许用
--platform / --version 手动覆盖。
"""

from __future__ import annotations

import platform

from . import native


def detect() -> dict:
    """返回 {'platform':..., 'version':..., 'distro':..., 'extra':...}。"""
    sysname = platform.system().lower()
    if sysname == "windows":
        return _detect_windows()
    if sysname == "darwin":
        return _detect_macos()
    if sysname == "linux":
        return _detect_linux()
    # BSD 家族：platform.system() 返回具体发行名（freebsd/openbsd/netbsd/dragonfly）
    if sysname in ("freebsd", "openbsd", "netbsd", "dragonfly"):
        return _detect_bsd(sysname)
    # System V / 商业 Unix：Solaris / illumos 返回 SunOS
    if sysname == "sunos":
        return _detect_unix()
    # 安卓 / iOS / 鸿蒙通常不是运行脚本的宿主（由 PC 端工具连接），回退到接口探测
    for fn in (_detect_android, _detect_ios, _detect_harmony):
        r = fn()
        if r["platform"] != "unknown":
            return r
    return {"platform": "unknown", "version": "", "distro": "", "extra": ""}


def _detect_windows() -> dict:
    ver = native.windows.get_version()          # 注册表：权威版本
    if ver.get("version"):
        display = ver["version"]
    else:
        display = ""
    # 用 ProductName 判定 10/11：11 的 DisplayVersion 形如 24H2，10 为 22H2/21H2
    name = ver.get("product_name", "")
    if "11" in name:
        ver_num = "11"
    elif "10" in name:
        ver_num = "10"
    else:
        ver_num = display.split(".")[0] if display else ""
    return {
        "platform": "windows",
        "version": ver_num or display,
        "distro": name or f"Windows {ver_num}",
        "extra": f"build={ver.get('build','')} display={display}",
    }


def _detect_macos() -> dict:
    sv = native.macos.sw_vers()
    out = sv.get("version") or platform.mac_ver()[0]
    major = out.split(".")[0] if out else ""
    pretty = sv.get("product") or "macOS"
    if out:
        pretty = f"{pretty} {out}"
    return {"platform": "macos", "version": major, "distro": pretty,
            "extra": f"build={sv.get('build','')}"}


def _detect_linux() -> dict:
    d = native.linux.detect_distro()            # LSB /etc/os-release
    # OpenWrt 是面向路由器/嵌入式的 Linux 发行版：os-release ID=openwrt；
    # 识别为独立平台，使其专属任务（tasks/openwrt.py）可被匹配。
    if d.get("id") == "openwrt":
        return {
            "platform": "openwrt",
            "version": d.get("version_id", "") or _openwrt_release_ver(),
            "distro": d.get("pretty") or "OpenWrt",
            "extra": "id=openwrt pkg=opkg/apk",
        }
    return {
        "platform": "linux",
        "version": d.get("version_id", ""),
        "distro": d.get("pretty") or d.get("id", ""),
        "extra": f"id={d.get('id','')} pkg={native.linux.pkg_manager()}",
    }


def _openwrt_release_ver() -> str:
    """从 /etc/openwrt_release 读取 DISTRIB_RELEASE（无 os-release version_id 时回退）。"""
    try:
        with open("/etc/openwrt_release", "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = __import__("re").match(r"^DISTRIB_RELEASE=['\"]?(.*?)['\"]?$", line.strip())
                if m:
                    return m.group(1)
    except OSError:
        pass
    return ""


def _detect_bsd(sysname: str) -> dict:
    """BSD 家族探测：用 sysctlbyname（libc 原生接口）+ uname 版本。"""
    d = native.bsd.detect_distro() or {}
    ver = d.get("version_id", "")
    return {
        "platform": "bsd",
        "version": ver.split(".")[0] if ver else "",
        "distro": d.get("pretty") or d.get("id", sysname.title()),
        "extra": f"id={d.get('id','')} pkg={d.get('pkg_manager','')}",
    }


def _detect_unix() -> dict:
    """System V / 商业 Unix（Solaris / illumos）探测：读 /etc/release + uname。"""
    d = native.unix.detect_distro() or {}
    ver = d.get("version_id", "")
    return {
        "platform": "unix",
        "version": ver.split(".")[0] if ver else "",
        "distro": d.get("pretty") or d.get("id", "Unix"),
        "extra": f"id={d.get('id','')} pkg={d.get('pkg_manager','')}",
    }


def _detect_android() -> dict:
    if not native.android.connected():
        return {"platform": "unknown", "version": "", "distro": "", "extra": ""}
    return {
        "platform": "android",
        "version": native.android.version(),
        "distro": native.android.device_model(),
        "extra": "adb 已连接",
    }


def _detect_harmony() -> dict:
    """鸿蒙：hdc（HarmonyOS Device Connector）连上设备后探测。

    与 Android/iOS 同口径——宿主通常不是鸿蒙设备，需由 PC 端 hdc 连接。
    """
    from .native import harmony
    if not harmony.connected():
        return {"platform": "unknown", "version": "", "distro": "", "extra": ""}
    return {
        "platform": "harmony",
        "version": harmony.version(),
        "distro": harmony.device_model() or "HarmonyOS",
        "extra": "hdc 已连接",
    }


def _detect_ios() -> dict:
    if not native.ios.available():
        return {"platform": "unknown", "version": "", "distro": "", "extra": ""}
    info = native.ios.device_info()
    if not info:
        return {"platform": "unknown", "version": "", "distro": "", "extra": ""}
    return {
        "platform": "ios",
        "version": info.get("productversion", ""),
        "distro": info.get("devicename", ""),
        "extra": f"model={info.get('producttype','')}",
    }
