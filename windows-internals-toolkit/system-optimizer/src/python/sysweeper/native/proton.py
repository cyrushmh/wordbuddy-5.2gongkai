"""游戏/应用兼容层只读诊断（Proton / Wine 兼容性前提核验）。

以 Valve **Proton**（Steam Play 兼容层）为坐标系，把「这台机器能不能跑 Windows
游戏/程序」这件事**只读、结构化**地摸一遍。Proton 自身基于 Wine 并叠加：

    Wine            —— Windows NT API(kernel32/ntdll/user32/d3d*/dxgi…) → POSIX 翻译
    DXVK            —— D3D9/10/11 → Vulkan（替代 Wine 内置软 D3D，大幅降 CPU 开销）
    VKD3D-Proton    —— D3D12     → Vulkan（Wine 原生不支持 DX12）
    wine-mono       —— .NET Framework 运行时替代
    Steam Runtime   —— steamrt(scout/soldier/sniper)，pressure-vessel 容器化保 ABI

本模块只回答「**前提是否满足、缺什么**」，不修改任何系统、不下载、不执行写操作。

检测维度（依据 Valve 官方 README 的 Runtime Config Options + Linux 内核文档）：
- Vulkan 支撑栈    ：vulkan-loader + ICD（/usr/share/vulkan/icd.d/*.json）或 vulkaninfo
- 32 位运行时       ：i386  Foreign Architecture + libstdc++/libgcc/zlib 等 :i386 库
                      （Wine/Proton 大量依赖 32 位，缺则多数游戏起不来）
- 同步原语          ：
    · esync  —— eventfd（Linux 2.6.22+ 普遍有）
    · fsync  —— futex，需内核 FUTEX_WAIT_MULTIPLE 支持（≈ Linux 5.16+；
               系统无此支持时 Proton 自动回退 esync，见 PROTON_NO_FSYNC）
    · NTSync —— 内核 /dev/ntsync 字符驱动（Linux 6.10 合并、6.11+ 可用；
               docs.kernel.org 已收录 ntsync.html；见 PROTON_NO_NTSYNC）
- Steam Runtime     ：steam 进程 / ~/.steam / steam-runtime-system-info
- Proton/Wine 安装  ：steamapps/common/Proton*、wine --version、compatdata

参照（权威文档，仅用于把「该看什么」钉死，绝不执行其中写操作）：
- ValveSoftware/Proton README —— Runtime Config Options 全表
- docs.kernel.org  ntsync.html —— NT synchronization primitive driver（/dev/ntsync, ioctl）
- Wine / DXVK / VKD3D-Proton 上游文档 —— 翻译层职责边界
- microsoft/litebox —— 兼容层「接口面削减 / 隔离」理念（本模块把该理念作为
  兼容层运行原则写入：兼容层应在最小权限、可审计、可接管的环境中运行）

红线（与全项目一致）：仅读——不改内核参数、不装包、不写 Wine prefix、不连校外网。
      只读探测用 vulkaninfo（若已安装）仅取其 summary，不触碰游戏进程。
"""

from __future__ import annotations

import os
import re
import shutil
from typing import List, Tuple

from . import common

# --------------------------------------------------------------------------- #
# 路径与常量                                                                    #
# --------------------------------------------------------------------------- #
VULKAN_ICD_DIR = "/usr/share/vulkan/icd.d"
VULKAN_ICD_DIR_ALT = "/usr/share/vulkan/icd.d"  # 部分发行版同位置
NTSYNC_DEV = "/dev/ntsync"
STEAM_HOME = os.path.expanduser("~/.steam")
STEAM_APPS = os.path.expanduser("~/.steam/steam/steamapps/common")
COMPATDATA = os.path.expanduser("~/.steam/steam/steamapps/compatdata")

# 32 位关键库（Debian/Ubuntu 命名）；缺一个都可能让 32 位 Windows 程序起不来
I386_CRITICAL = ["libc6:i386", "libstdc++6:i386", "libgcc-s1:i386", "zlib1g:i386",
                 "libgl1:i386", "libgl1-mesa-dri:i386"]


def _kernel_version() -> Tuple[int, int, int]:
    """读 /proc/sys/kernel/osrelease，返回 (major, minor, patch) 三元组。"""
    p = "/proc/sys/kernel/osrelease"
    if not os.path.exists(p):
        return (0, 0, 0)
    try:
        with open(p, encoding="utf-8") as f:
            s = f.read().strip()
        m = re.match(r"(\d+)\.(\d+)(?:\.(\d+))?", s)
        if m:
            return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))
    except OSError:
        pass
    return (0, 0, 0)


def _kernel_ge(major: int, minor: int) -> bool:
    """内核版本是否 >= (major, minor)。"""
    return _kernel_version() >= (major, minor, 0)


# --------------------------------------------------------------------------- #
# Vulkan 支撑栈                                                                 #
# --------------------------------------------------------------------------- #
def vulkan_report() -> Tuple[bool, str]:
    """Vulkan 支撑栈：loader + ICD（驱动）。这是 DXVK/VKD3D 运行的硬前提。"""
    lines = ["Vulkan 支撑栈（DXVK/VKD3D-Proton 的硬前提，只读）："]
    # 1) loader
    has_loader = shutil.which("vulkaninfo") is not None or \
        os.path.exists("/usr/lib/x86_64-linux-gnu/libvulkan.so.1")
    lines.append(f"   · vulkan-loader：{'已装' if has_loader else '未装（apt: libvulkan1 / vulkan-tools）'}")
    # 2) ICD（显卡驱动提供的 Vulkan 实现）
    icds: List[str] = []
    for d in (VULKAN_ICD_DIR, VULKAN_ICD_DIR_ALT):
        if os.path.isdir(d):
            for fn in os.listdir(d):
                if fn.endswith(".json"):
                    icds.append(fn)
    if icds:
        # 从 ICD 文件名猜厂商
        vendors = []
        for j in icds:
            low = j.lower()
            if "nvidia" in low:
                vendors.append("NVIDIA")
            elif "amd" in low or "radeon" in low or "mesa" in low:
                vendors.append("AMD/radeon(mesa)")
            elif "intel" in low:
                vendors.append("Intel")
            else:
                vendors.append(j.replace(".json", ""))
        lines.append(f"   · Vulkan ICD（驱动）：{len(icds)} 个 → {', '.join(sorted(set(vendors)))}")
    else:
        lines.append("   · 未发现 Vulkan ICD（/usr/share/vulkan/icd.d 为空）——需装显卡驱动 Vulkan 实现")
    # 3) vulkaninfo summary（若已安装，只读取其版本摘要，不触游戏）
    if shutil.which("vulkaninfo"):
        rc, out = common.run("vulkaninfo --summary 2>/dev/null | head -20")
        if rc == 0 and out.strip():
            for l in out.splitlines()[:6]:
                s = l.strip()
                if "Vulkan Instance" in s or "GPU id" in s or "apiVersion" in s:
                    lines.append(f"   · {s}")
    else:
        lines.append("   · vulkaninfo 未装（可选；apt: vulkan-tools），无法取设备摘要")
    if icds and has_loader:
        return True, "\n".join(lines)
    return False, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 32 位运行时                                                                   #
# --------------------------------------------------------------------------- #
def i386_report() -> Tuple[bool, str]:
    """32 位 i386 运行时：Wine/Proton 大量依赖 32 位库，缺则多数 Windows 程序起不来。"""
    lines = ["32 位 i386 运行时（Wine/Proton 硬依赖，只读）："]
    # 1) 是否启用 i386 foreign architecture（Debian/Ubuntu 系）
    fa_enabled = False
    if shutil.which("dpkg"):
        rc, out = common.run("dpkg --print-foreign-architectures 2>/dev/null")
        if rc == 0 and "i386" in out:
            fa_enabled = True
            lines.append("   · i386 架构已启用（dpkg --print-foreign-architectures 含 i386）")
        else:
            lines.append("   · i386 架构未启用（dpkg --print-foreign-architectures 无 i386）")
    # 2) 关键 :i386 库是否在位
    missing: List[str] = []
    if shutil.which("dpkg"):
        rc, out = common.run("dpkg -l 2>/dev/null | grep ':i386'")
        installed = set()
        if rc == 0:
            for l in out.splitlines():
                parts = l.split()
                if len(parts) >= 2 and parts[0].startswith("ii"):
                    installed.add(parts[1])  # 形如 libstdc++6:i386
        for pkg in I386_CRITICAL:
            if pkg not in installed:
                missing.append(pkg)
    else:
        # 非 dpkg 系（RHEL/Fedora/Arch）：退化检查 32 位 loader 与库目录
        ld32 = any(os.path.exists(p) for p in
                   ("/lib/ld-linux.so.2", "/usr/lib/ld-linux.so.2",
                    "/lib/i386-linux-gnu/ld-linux.so.2"))
        lines.append(f"   · 非 dpkg 系；32 位动态加载器 {'(存在)' if ld32 else '(缺失)'} "
                     f"（/lib/ld-linux.so.2 或 /lib/i386-linux-gnu）")
        if not ld32:
            missing.append("ld-linux.so.2(32位)")
    if missing:
        lines.append(f"   · 缺失关键 32 位库：{', '.join(missing)}")
        lines.append("   · Debian/Ubuntu 修复：sudo dpkg --add-architecture i386 && "
                     "sudo apt update && sudo apt install libgl1:i386 libgl1-mesa-dri:i386")
    else:
        lines.append("   · 关键 32 位库齐全（或已启用架构且核心库在位）")
    return (len(missing) == 0, "\n".join(lines))


# --------------------------------------------------------------------------- #
# 同步原语（fsync / esync / NTSync）                                            #
# --------------------------------------------------------------------------- #
def sync_report() -> Tuple[bool, str]:
    """NT 同步原语：esync(eventfd) / fsync(futex,需 FUTEX_WAIT_MULTIPLE) / NTSync(/dev/ntsync)。"""
    kv = _kernel_version()
    lines = [f"NT 同步原语（Proton 用其替代 Wine 用户态模拟；内核 {kv[0]}.{kv[1]}.{kv[2]}）："]
    # esync：eventfd，老内核就有
    esync = _kernel_ge(2, 6)
    lines.append(f"   · esync  (eventfd)      ：{'可用' if esync else '不可用（极老内核）'}")
    # fsync：futex，需 FUTEX_WAIT_MULTIPLE（≈ Linux 5.16 合并）
    fsync = _kernel_ge(5, 16)
    lines.append(f"   · fsync  (futex)        ：{'可用(需 FUTEX_WAIT_MULTIPLE)' if fsync else '不可用（内核 <5.16，Proton 自动回退 esync）'}")
    # NTSync：/dev/ntsync 字符设备（6.10 合并但标记 broken，6.11+ 可用）
    ntsync = os.path.exists(NTSYNC_DEV)
    lines.append(f"   · NTSync (/dev/ntsync)  ：{'可用(内核驱动就绪)' if ntsync else '不可用（无 /dev/ntsync；Linux 6.11+ 才有）'}")
    best = "NTSync" if ntsync else ("fsync" if fsync else ("esync" if esync else "无（Wine 默认用户态，慢）"))
    lines.append(f"   · Proton 将选用的最佳同步路径：{best}")
    lines.append("   · 关闭某路径用 PROTON_NO_FSYNC / PROTON_NO_NTSYNC（运行时选项，不改系统）")
    return (esync, "\n".join(lines))


# --------------------------------------------------------------------------- #
# Steam Runtime / Proton / Wine 安装                                            #
# --------------------------------------------------------------------------- #
def steam_runtime_report() -> Tuple[bool, str]:
    """Steam Runtime 与 Proton/Wine 安装现状（只读）。"""
    lines = ["Steam Runtime / 兼容层安装（只读）："]
    # steam 进程
    steam_running = False
    if shutil.which("pgrep"):
        rc, _ = common.run("pgrep -u $(id -u) -x steam 2>/dev/null")
        steam_running = (rc == 0)
    lines.append(f"   · Steam 客户端：{'运行中' if steam_running else '未运行/未装'}")
    # Steam Runtime 工具
    if shutil.which("steam-runtime-system-info"):
        lines.append("   · 检测到 steam-runtime-system-info（steamrt 诊断工具在位）")
    else:
        lines.append("   · 未检测到 steam-runtime-system-info（Steam 自带，无需单独装）")
    # Proton 安装
    protons: List[str] = []
    if os.path.isdir(STEAM_APPS):
        try:
            for nm in os.listdir(STEAM_APPS):
                if nm.lower().startswith("proton"):
                    protons.append(nm)
        except OSError:
            pass
    if protons:
        lines.append(f"   · 已装 Proton：{', '.join(protons)}")
    else:
        lines.append("   · 未发现 Proton（Steam → 设置 → 兼容性 → 勾选 Steam Play 后自动下载）")
    # Wine 直装
    if shutil.which("wine"):
        rc, out = common.run("wine --version 2>/dev/null")
        ver = out.strip().splitlines()[0] if rc == 0 and out.strip() else "?"
        lines.append(f"   · 系统 Wine：{ver}")
    else:
        lines.append("   · 未单独安装 Wine（Proton 自带 Wine，无需系统 Wine）")
    # compatdata（已配置的兼容前缀数量）
    if os.path.isdir(COMPATDATA):
        try:
            n = len([d for d in os.listdir(COMPATDATA)
                     if os.path.isdir(os.path.join(COMPATDATA, d))])
            lines.append(f"   · 兼容前缀 compatdata：{n} 个（每个 = 一个 Windows 程序的 Wine prefix）")
        except OSError:
            pass
    return (bool(protons) or steam_running, "\n".join(lines))


# --------------------------------------------------------------------------- #
# 聚合报告 + 能力自检                                                           #
# --------------------------------------------------------------------------- #
def proton_report() -> Tuple[bool, str]:
    """兼容层整体只读诊断。返回 (ok, 文本)。ok 表示「缺的前提」是否已清零。"""
    blocks = ["游戏/应用兼容层诊断（Proton / Wine 坐标系，全部只读）",
              "════════════════════════════════════════════"]
    checks = [
        ("Vulkan 支撑栈", vulkan_report),
        ("32 位 i386 运行时", i386_report),
        ("NT 同步原语", sync_report),
        ("Steam Runtime / 兼容层", steam_runtime_report),
    ]
    fails = 0
    for title, fn in checks:
        ok, msg = fn()
        blocks.append(f"【{title}】{'✓' if ok else '✗ 缺前提'}")
        blocks.append(msg)
        if not ok:
            fails += 1
    blocks.append("════════════════════════════════════════════")
    verdict = ("前提基本满足，可跑 Proton/Wine 兼容层" if fails == 0
               else f"有 {fails} 项前提未满足，详见上；补齐后即可跑")
    blocks.append(f"结论：{verdict}")
    blocks.append("运行原则（参照 microsoft/litebox 兼容层隔离理念）：兼容层应在最小权限、"
                  "可审计、可接管的环境中运行；本工具只诊断不修改。")
    blocks.append("特性开关参考：PROTON_USE_WINED3D=1(退回 OpenGL 软渲染) / "
                  "PROTON_HIDE_NVIDIA_GPU=1(报成 AMD) / PROTON_DISABLE_NVAPI=1 / "
                  "PROTON_NO_FSYNC / PROTON_NO_NTSYNC —— 均运行时选项，不落盘。")
    return (fails == 0, "\n".join(blocks))


def capabilities_report() -> Tuple[bool, str]:
    """能力自检（只读）：本机兼容层诊断能看哪些维度 + 红线。"""
    lines = ["兼容层诊断能力自检（只读）："]
    for title, fn in [("Vulkan 支撑栈", vulkan_report),
                      ("32 位 i386 运行时", i386_report),
                      ("NT 同步原语", sync_report),
                      ("Steam Runtime / 兼容层", steam_runtime_report)]:
        try:
            ok, _ = fn()
            lines.append(f"   · {title:<18} {'可诊断' if ok else '可诊断(有缺项)'}")
        except Exception:  # noqa: BLE001
            lines.append(f"   · {title:<18} 诊断异常")
    lines.append("红线：仅读 /usr/share/vulkan/icd.d、dpkg/ldconfig 只读查询、"
                 "/proc/sys/kernel/osrelease、/dev/ntsync、steam 目录；"
                 "不装包、不写 Wine prefix、不连校外网。")
    return True, "\n".join(lines)
