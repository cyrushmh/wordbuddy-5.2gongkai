"""任务注册表：收集各平台任务定义，并提供按平台/版本/分类过滤的能力。"""

from __future__ import annotations

from typing import Dict, List, Optional

from .models import Task

# 各平台任务模块，按顺序导入即可把 TASKS 注册进来
from .tasks import a11y, android, bsd, cert, chrono, cross, durability, electrical, ios, linux, macos, openwrt, packages, peripheral, remote, unix, virt, windows, apctrl, llvm, toolchain, meshnet, vdns, ipp, display, retro, restart, asm, androidstd, gmsstd, fdroidstd, hmos_ecosystem, hmosstd, reverse, matrix, f2b, cnstd  # noqa: F401

# 平台中文名
PLATFORM_NAMES = {
    "windows": "Windows",
    "macos": "macOS",
    "linux": "Linux",
    "bsd": "BSD",
    "unix": "Unix (System V)",
    "android": "Android",
    "ios": "iOS",
    "openwrt": "OpenWrt（路由器/嵌入式 Linux）",
    "uniapp": "uni-app（跨端目标：App/H5/小程序）",
    "harmony": "鸿蒙 HarmonyOS / OpenHarmony",
    "any": "通用（跨平台）",
}


def all_tasks() -> List[Task]:
    tasks: List[Task] = []
    # a11y 含 linux/windows/macos 平台专属任务，也含 platform="any" 的只读报告
    for mod in (windows, macos, linux, bsd, unix, android, ios, openwrt, a11y):
        tasks.extend(getattr(mod, "TASKS", []))
    # 跨平台 / 语言 / 硬件 / 网络类任务（platform="any"）
    # 以及 uni-app 这类「跨端目标」（platform="uniapp"，非操作系统）
    from .tasks import (arch, compress, container, desktop, distcompute, distro, edge,  # noqa: F401
                        emergency, electrical, fonts, harmony, hardware, jdk, kernel, kmod,
                        netauth, netlink, lang, meshchat, androidstd, gmsstd, fdroidstd, hmos_ecosystem, hmosstd, reverse,
                        miniapp, network, osi, pkgmgr, peripheral, plugins, quantum, storage, syssoftware,
                        thirdparty, uniapp, webnews, proton, wsl, virtgpu, browser,
                        dnshealth, tor, zerotier, sysmap, media, livemedia, legacy, compat, chrono,
                        packages, virt, apctrl, llvm, toolchain, meshnet, vdns, ipp, display, retro, restart,
                        tls13, asm, radio, winternals, qstore, qarch,                         matrix, f2b,
                        acoustics, sysbase, docs, sysdev, cnstd)
    for mod in (lang, hardware, network, uniapp, fonts, cross, arch, compress, desktop,
                syssoftware, harmony, miniapp, pkgmgr, container, storage, thirdparty,
                plugins, emergency, meshchat, distcompute, webnews, edge, osi, distro,
                proton, wsl, virtgpu, browser, dnshealth, tor, zerotier, sysmap, media,
                livemedia, legacy, durability, electrical, remote, cert, compat, peripheral,
                chrono, packages, virt, apctrl, llvm, toolchain, meshnet, vdns, ipp, display, retro, restart,
                tls13, asm, jdk, kmod, kernel, netauth, netlink, quantum, androidstd, gmsstd, fdroidstd, hmos_ecosystem, hmosstd, reverse, radio, winternals, qstore, qarch,
                matrix, f2b, acoustics, sysbase, sysdev, cnstd):
        tasks.extend(getattr(mod, "TASKS", []))
    return tasks


def applicable(platform: str, version: str, category: str = None,
               max_risk: str = "high", include_opt_in: bool = False,
               only_ids: Optional[List[str]] = None,
               include_lang_missing: bool = False,
               arch: Optional[str] = None) -> List[Task]:
    """返回匹配平台/版本/分类、且风险不超过 max_risk 的任务。

    - include_opt_in: 是否纳入默认关闭的 opt_in 开关（网络/ITU 调优）。
    - only_ids: 仅保留指定 id（用户精确选择）。
    - include_lang_missing: 是否保留「需要某种语言但该语言未安装」的任务
      （默认不保留——即「自动启用」：有语言才出现，没装就隐藏、不强求安装）。
    - arch: 架构/指令集维度过滤。非空时仅保留 arch 为空（任意架构适用）或
      arch 与之相同的任务——即「龙芯上不显示 MIPS/RISC-V 专属项」。
      arch=None（未指定）时不按架构过滤（默认行为，向后兼容）。
    """
    from .models import RISK_ORDER
    from .langdetect import available as lang_available

    out = []
    for t in all_tasks():
        if not t.matches(platform, version):
            continue
        if not include_opt_in and t.opt_in:
            continue
        if category and t.category != category:
            continue
        if RISK_ORDER.get(t.risk, 0) > RISK_ORDER.get(max_risk, 2):
            continue
        if only_ids and t.id not in only_ids:
            continue
        if arch and t.arch and t.arch != arch:
            continue
        if t.requires_lang and not lang_available(t.requires_lang):
            if not include_lang_missing:
                continue
        out.append(t)
    return out


def arch_summary() -> Dict[str, int]:
    """各架构/指令集任务总数（用于概览，呼应「架构维度」）。"""
    s: Dict[str, int] = {}
    for t in all_tasks():
        if not t.arch:
            continue
        s[t.arch] = s.get(t.arch, 0) + 1
    return s


def opt_in_tasks(platform: str = "any") -> List[Task]:
    """列出所有默认关闭的 opt_in 开关（网络/ITU 调优），供 toggles 命令展示。"""
    out = []
    for t in all_tasks():
        if not t.opt_in:
            continue
        if platform not in (t.platform, "any"):
            continue
        out.append(t)
    return out


def by_id(task_id: str) -> Task | None:
    for t in all_tasks():
        if t.id == task_id:
            return t
    return None


def by_lang(lang: str) -> List[Task]:
    """返回依赖某语言运行时的任务（不论当前是否可用）。"""
    return [t for t in all_tasks() if t.requires_lang == lang]


def by_lang_any() -> List[Task]:
    """返回所有「依赖某种语言运行时」的任务（用于 langs 命令展示开关状态）。"""
    return [t for t in all_tasks() if t.requires_lang]


def platform_summary() -> Dict[str, int]:
    """各平台任务总数（用于概览）。"""
    s: Dict[str, int] = {}
    for t in all_tasks():
        s[t.platform] = s.get(t.platform, 0) + 1
    return s


def category_summary() -> Dict[str, int]:
    """各分类任务总数（用于「分类规范整体」概览；opt_in 单独计一列）。"""
    from .models import CATEGORY_ORDER
    s: Dict[str, int] = {c: 0 for c in CATEGORY_ORDER}
    s["(opt_in)"] = 0
    for t in all_tasks():
        if t.opt_in:
            s["(opt_in)"] += 1
        else:
            s[t.category] = s.get(t.category, 0) + 1
    return s


def tasks_by_category() -> Dict[str, List[Task]]:
    """分类 → 该分类下任务列表（用于「标准与分类」视图逐条列出任务 id）。

    - 普通任务按 category 归集；
    - opt_in 默认关闭的开关（网络/ITU 调优）单独计入 "(opt_in)" 一组，
      不污染普通分类计数，但同样可在标准视图里查看其归属。
    返回字典的键顺序固定为 CATEGORY_ORDER + ["(opt_in)"]。
    """
    from .models import CATEGORY_ORDER
    s: Dict[str, List[Task]] = {c: [] for c in CATEGORY_ORDER}
    s["(opt_in)"] = []
    for t in all_tasks():
        if t.opt_in:
            s["(opt_in)"].append(t)
        else:
            s.setdefault(t.category, []).append(t)
    return s


def standards_for_category(cat: str) -> dict:
    """返回某分类对应的标准出处（见 models.CATEGORY_STANDARDS）。"""
    from .models import category_standards
    return category_standards(cat)
