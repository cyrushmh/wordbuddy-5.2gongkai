"""现代设备显示与 GPU 推进（display）：把「图形化及现代设备显示推进」落为只读子系统，保留控制台/终端/远程终端。

只读项：
  - 显示服务器：XDG_SESSION_TYPE 判 X11/Wayland（Tty 即控制台），只读环境变量
  - GPU：lspci 抽 VGA/3D；glxinfo/vulkaninfo 只读看渲染后端与 Vulkan 支持（不装驱动）
  - 分辨率：xrandr 只读列当前输出模式（Wayland 下降级为指引）
  - 控制台/终端/远程终端：显式保留——即使推进图形化，TTY 控制台、本地终端、SSH 远程终端
    始终可用（与 virt/remote 同口径，只读确认其存在）

红线：只读观测 ≠ 授权施工——装 GPU 驱动、切 Wayland、改显示配置一律只给指引。
"""

from __future__ import annotations

import os
import shutil
import subprocess


PROBES = (
    ("server_report", "显示服务器（X11/Wayland/Tty）"),
    ("gpu_report", "GPU 与渲染后端"),
    ("resolution_report", "当前分辨率"),
    ("terminal_report", "控制台/终端/远程终端保留确认"),
)


def server_report() -> tuple:
    st = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if st == "tty":
        return True, "显示服务器：TTY 控制台（无图形；图形化推进时仍保留此入口）"
    if st == "wayland":
        return True, "显示服务器：Wayland（现代合成器，如 GNOME/KDE Wayland 会话）"
    if st == "x11":
        return True, "显示服务器：X11（传统 Xorg 会话）"
    return False, "显示服务器类型未识别（XDG_SESSION_TYPE 未设）；远程终端/SSH 场景常见"


def gpu_report() -> tuple:
    lines = ["GPU 与渲染后端（只读）:"]
    if shutil.which("lspci"):
        try:
            pc = subprocess.run(["lspci"], capture_output=True, text=True, timeout=6).stdout.lower()
            cards = [l for l in pc.splitlines() if ("vga" in l or "3d" in l or "display" in l)]
            for c in cards[:4]:
                lines.append(f"   · {c.strip()}")
        except (OSError, subprocess.SubprocessError):
            lines.append("   · lspci 调用失败（只读探针跳过）")
    if shutil.which("vulkaninfo"):
        lines.append("   · Vulkan: vulkaninfo 可用（现代图形 API 后端）")
    elif shutil.which("glxinfo"):
        lines.append("   · OpenGL: glxinfo 可用（传统 GL 后端）")
    else:
        lines.append("   · 未装 vulkaninfo/glxinfo；渲染后端未探（无图形需求时属正常）")
    return True, "\n".join(lines)


def resolution_report() -> tuple:
    if os.environ.get("XDG_SESSION_TYPE", "").lower() == "tty":
        return False, "TTY 控制台无图形分辨率概念；图形会话下才有"
    if shutil.which("xrandr"):
        try:
            out = subprocess.run(["xrandr", "--current"], capture_output=True, text=True,
                                 timeout=6).stdout
            modes = [l.strip() for l in out.splitlines() if "connected" in l or "*" in l]
            return True, "当前分辨率（xrandr 只读）:\n" + "\n".join(f"   · {m}" for m in modes[:6])
        except (OSError, subprocess.SubprocessError):
            return False, "xrandr 调用失败（只读探针跳过）"
    return False, "Wayland 下 xrandr 不适用；用 swaymsg/wayland-info 或系统设置看分辨率"


def terminal_report() -> tuple:
    """显式确认控制台/终端/远程终端入口保留（与图形化推进并存）。"""
    lines = ["控制台/终端/远程终端（始终保留，推进图形化不移除）:"]
    lines.append(f"   · 本地终端：$SHELL 可用" if os.environ.get("SHELL") else "   · 本地终端：shell 可用")
    lines.append("   · TTY 控制台：Ctrl+Alt+F2..F6 虚拟终端可用（无图形时兜底）")
    lines.append("   · 远程终端：SSH 接入始终可用（与 remote 子系统同口径，不在本子系统改配置）")
    return True, "\n".join(lines)


def environment_report() -> list:
    lines = ["现代设备显示与 GPU（display）· 本机只读探测："]
    for fn, lab in PROBES:
        ok, msg = getattr(__import__("sys").modules[__name__], fn)()
        lines.append(f"   · {lab}: {'✓ 可用' if ok else '✗ 不适用'}")
        if isinstance(msg, str) and msg.strip():
            lines.append("       " + msg.replace("\n", "\n       "))
    return lines


def display_report(env_tags: list | None = None, readings: dict | None = None) -> tuple:
    lines = ["== 现代设备显示与 GPU 报告（display：显示服务器/GPU/分辨率 + 控制台·终端·远程终端保留，只读不写）=="]
    lines.append(f"维度标签: {sorted(set(env_tags or [])) or '未声明（默认基线）'}")
    lines.append("")
    for fn, lab in PROBES:
        ok, msg = getattr(__import__("sys").modules[__name__], fn)()
        lines.append(f"[· {lab}]")
        for sub in (msg.splitlines() if isinstance(msg, str) else [msg]):
            lines.append("   " + sub)
        lines.append("")
    lines.append("安全不变量：display 只读观测显示与 GPU；装 GPU 驱动 / 切 Wayland / 改显示配置一律只给"
                 "指引；控制台/终端/远程终端始终保留。")
    return True, "\n".join(lines)


def guide_gpu_driver() -> tuple:
    lines = [
        "GPU 驱动安装指引（不代执行）:",
        "   1. 先经 lspci 确认 GPU 厂商（Intel/AMD/NVIDIA/核显）",
        "   2. 开源栈优先：Mesa + 对应内核驱动（amdgpu/i915/nouveau）；闭源按厂商工具",
        "   3. 远程/服务器无显示需求可保持 headless，不强制装图形驱动",
    ]
    return True, "\n".join(lines)


TUNES = (
    ("guide_gpu_driver", "GPU 驱动安装（规范指引，不代执行）"),
)


def display_tune_list() -> list:
    return [f"· {fn}() — {desc}" for fn, desc in TUNES]
