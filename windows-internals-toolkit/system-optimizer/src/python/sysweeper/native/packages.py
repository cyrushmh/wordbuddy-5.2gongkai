"""软件包规范审计（packages）：按系统/硬件/相关软件包检测包管理器，只读审计其包规范合规，并给出
「安装 / 卸载 / 配置 / 设置优化」四类操作的相应层级应对措施。

本子系统与 pkgmgr（缓存清理）互补：pkgmgr 清理缓存，packages 审计「一个包在该包管理器下是否符合
安装/卸载/配置/优化规范、不合规怎么处置」。所有探测只读，任何 install/uninstall/configure/optimize
一律只给规范指引（层级应对），不代执行——严守本项目只读红线。

覆盖范围（包管理器 → 系统/硬件/相关软件包判定）：
  apt/dpkg   : Debian/Ubuntu 系（/etc/os-release ID=debian/ubuntu… 或 which apt）
  dnf/rpm    : Fedora/RHEL 系（ID=fedora/rhel/centos… 或 which dnf）
  pacman     : Arch 系（ID=arch 或 which pacman）
  brew       : macOS/Linux（which brew，前缀 /opt/homebrew）
  winget     : Windows（which winget）
  choco      : Windows（which choco）
  apk        : Alpine（ID=alpine 或 which apk）
  scoop      : Windows 用户态（which scoop）
  zypper     : openSUSE/SUSE（ID=opensuse*/sles 或 which zypper）
"""

from __future__ import annotations

import json
import os
import shutil


# 包管理器注册表（id, 可执行名, 关联发行版 ID/家族）
PKG_MANAGERS = (
    ("apt", "apt-get", ("debian", "ubuntu", "linuxmint", "raspbian", "kali")),
    ("dnf", "dnf", ("fedora", "rhel", "centos", "rocky", "almalinux", "oracle")),
    ("pacman", "pacman", ("arch", "manjaro", "endeavouros")),
    ("brew", "brew", ("darwin",)),
    ("winget", "winget", ("windows",)),
    ("choco", "choco", ("windows",)),
    ("apk", "apk", ("alpine",)),
    ("scoop", "scoop", ("windows",)),
    ("zypper", "zypper", ("opensuse", "opensuse-leap", "opensuse-tumbleweed", "sles")),
)

# 四类操作（安装/卸载/配置/优化）——审计维度
OPS = ("install", "uninstall", "configure", "optimize")

_OP_CN = {
    "install": "安装",
    "uninstall": "卸载",
    "configure": "配置",
    "optimize": "设置优化",
}


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "packages_docs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:  # noqa: BLE001
        return {}


REFS = _load_refs()


def reference(pkg_id: str) -> dict:
    """返回某包管理器的规范文档（含四类操作 spec + tier）。"""
    return REFS.get(pkg_id, {})


def reference_all() -> dict:
    """返回全部包管理器规范文档。"""
    return REFS


# --------------------------------------------------------------------------- #
# 只读探测：按系统/硬件/相关软件包判定包管理器                                    #
# --------------------------------------------------------------------------- #

def _os_id() -> str:
    """读 /etc/os-release 的 ID（只读）。"""
    txt = None
    for p in ("/etc/os-release", "/usr/lib/os-release"):
        try:
            with open(p, encoding="utf-8") as f:
                txt = f.read()
            break
        except OSError:
            continue
    if not txt:
        return ""
    for line in txt.splitlines():
        if line.startswith("ID="):
            return line.split("=", 1)[1].strip().strip('"').lower()
    return ""


def detect_pkgmgr() -> tuple:
    """只读探测当前系统的包管理器。返回 (ok, dict)。

    判定顺序：可执行 which() 优先 → 否则用 /etc/os-release ID 映射 → 否则 unknown。
    可返回多个候选（如 Windows 同时有 winget/choco/scoop）。
    """
    os_id = _os_id()
    if os_id in ("darwin",):
        os_id = "darwin"
    elif os.name == "nt":
        os_id = "windows"
    found = []
    for pid, exe, ids in PKG_MANAGERS:
        if shutil.which(exe) is not None:
            found.append(pid)
        elif os_id in ids:
            found.append(pid)
    if found:
        # 去重保序
        seen = set()
        uniq = [p for p in found if not (p in seen or seen.add(p))]
        primary = uniq[0]
        info = {"managers": uniq, "primary": primary, "os_id": os_id,
                "method": "which" if shutil.which(PKG_MANAGERS[[m[0] for m in PKG_MANAGERS].index(primary)][1]) else "os-release"}
        return True, info
    return False, {"managers": [], "primary": None, "os_id": os_id,
                   "note": "未检测到已知包管理器（可能是裸应急环境/未知发行版），按 unknown 处理"}


# --------------------------------------------------------------------------- #
# 审计引擎（纯函数，不碰系统，便于单测）                                          #
# --------------------------------------------------------------------------- #

def audit_operation(pkgmgr: str | None, op: str) -> list:
    """对某一包管理器的一类操作做规范审计，返回层级应对清单（纯函数）。

    只读查 REFS 规范库；任何 install/uninstall/configure/optimize 只给规范指引（不代执行）。
    """
    if pkgmgr not in REFS:
        return [{
            "op": op,
            "pkgmgr": pkgmgr,
            "compliant": None,
            "title": f"无 {pkgmgr} 的包规范库；按通用包规范：安装/卸载/配置/优化一律走官方接口，"
                     f"禁止手工改包数据库，签名校验失败即停",
            "tier": "generic_guidance",
            "action_type": "guidance",
        }]
    ref = REFS[pkgmgr].get(op, {})
    return [{
        "op": op,
        "pkgmgr": pkgmgr,
        "compliant": True,
        "title": ref.get("spec", ""),
        "tier": ref.get("tier", "guidance"),
        "action_type": "guidance",
        "rationale": f"{pkgmgr}/{op}",
    }]


def audit_package(pkgmgr: str | None, pkg_name: str | None = None) -> list:
    """对一个包（或整类）做四类操作规范审计，返回层级应对清单。"""
    out = []
    label = pkg_name or "（泛指：按包管理器整体口径）"
    for op in OPS:
        for a in audit_operation(pkgmgr, op):
            a = dict(a)
            a["scope"] = label
            out.append(a)
    return out


def environment_report() -> list:
    """返回本机包管理器探测概览。"""
    ok, info = detect_pkgmgr()
    lines = ["软件包规范审计（packages）· 本机只读探测："]
    if info.get("managers"):
        lines.append(f"   · 检测到包管理器: {', '.join(info['managers'])}（主: {info['primary']}，via {info.get('method')}）")
    else:
        lines.append(f"   · 未检测到已知包管理器（os_id={info.get('os_id')}）")
    return lines


# --------------------------------------------------------------------------- #
# 端到端报告（无参可调用，供任务/CLI/GUI）                                        #
# --------------------------------------------------------------------------- #

def packages_report(env_tags: list | None = None, readings: dict | None = None) -> tuple:
    """端到端生成软件包规范审计报告：检测包管理器 → 四类操作层级应对。只读不写。"""
    readings = readings or {}
    if "pkgmgr" not in readings:
        ok, pm = detect_pkgmgr()
        readings["pkgmgr"] = pm
    else:
        pm = readings["pkgmgr"]
    primary = pm.get("primary")
    managers = pm.get("managers", [])

    lines = ["== 软件包规范审计报告（packages：按系统/硬件/相关软件包检测包管理器 + 四类操作层级应对，只读不写）=="]
    lines.append(f"维度标签: {sorted(set(env_tags or [])) or '未声明（默认基线）'}")
    lines.append("")
    lines.append("[① 包管理器检测（系统/硬件/相关软件包）]")
    if managers:
        lines.append(f"   · 候选: {', '.join(managers)}（主用: {primary}，检测方式: {pm.get('method')}）")
    else:
        lines.append(f"   · 未检测到已知包管理器（os_id={pm.get('os_id')}）；按 unknown 给通用层级应对")

    lines.append("")
    lines.append(f"[② 四类操作层级应对（安装/卸载/配置/设置优化，目标包管理器: {primary or 'unknown'}）]")
    for op in OPS:
        lines.append(f"   ▸ {_OP_CN[op]}（{op}）")
        for a in audit_operation(primary, op):
            lines.append(f"     · [{a['tier']}] {a['title']}")

    lines.append("")
    lines.append("[③ 规范合规判据（回链知识库）]")
    if primary in REFS:
        lines.append(f"   · 依据 {REFS[primary].get('org', '')} 规范：{REFS[primary].get('url', '')}")
    lines.append("   · 合规铁律：安装/卸载/配置/优化一律走官方接口（apt/dnf/pacman/brew/winget…），"
                 "禁止手工改包数据库，签名/GPG 校验失败即停；任何写操作只给层级应对指引")

    lines.append("")
    lines.append("安全不变量：packages 只审计 + 出层级应对；install/uninstall/configure/optimize 由用户在"
                 "系统包管理器或厂商工具确认；是否施工始终由用户决定。")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 写操作（仅指引，不代执行）                                                      #
# --------------------------------------------------------------------------- #

def guide_install(pkgmgr: str | None = None, pkg: str | None = None) -> tuple:
    """指引某包管理器的安装规范（不代执行）。"""
    ref = REFS.get(pkgmgr, {}).get("install", {})
    tgt = pkg or "<包名>"
    lines = [f"安装规范指引（{pkgmgr or 'unknown'}，不代执行）:", f"   目标: {tgt}", f"   规范: {ref.get('spec', '走官方接口，禁止手工改包数据库')}",
             f"   层级应对: {ref.get('tier', '签名校验失败即停')}"]
    return True, "\n".join(lines)


def guide_uninstall(pkgmgr: str | None = None, pkg: str | None = None) -> tuple:
    """指引某包管理器的卸载规范（不代执行）。"""
    ref = REFS.get(pkgmgr, {}).get("uninstall", {})
    tgt = pkg or "<包名>"
    lines = [f"卸载规范指引（{pkgmgr or 'unknown'}，不代执行）:", f"   目标: {tgt}", f"   规范: {ref.get('spec', '走官方接口回收依赖，不手工删库')}",
             f"   层级应对: {ref.get('tier', '优先 autoremove/孤儿回收')}"]
    return True, "\n".join(lines)


def guide_configure(pkgmgr: str | None = None, pkg: str | None = None) -> tuple:
    """指引某包管理器的配置规范（不代执行）。"""
    ref = REFS.get(pkgmgr, {}).get("configure", {})
    tgt = pkg or "<包名>"
    lines = [f"配置规范指引（{pkgmgr or 'unknown'}，不代执行）:", f"   目标: {tgt}", f"   规范: {ref.get('spec', '源与钉版走 drop-in 片段')}",
             f"   层级应对: {ref.get('tier', '不内联改主文件')}"]
    return True, "\n".join(lines)


def guide_optimize(pkgmgr: str | None = None, pkg: str | None = None) -> tuple:
    """指引某包管理器的优化规范（不代执行）。"""
    ref = REFS.get(pkgmgr, {}).get("optimize", {})
    tgt = pkg or "<包名>"
    lines = [f"设置优化指引（{pkgmgr or 'unknown'}，不代执行）:", f"   目标: {tgt}", f"   规范: {ref.get('spec', '缓存回收走官方 clean 接口')}",
             f"   层级应对: {ref.get('tier', '升级逐包确认')}"]
    return True, "\n".join(lines)


TUNES = (
    ("guide_install", "安装规范指引（不代执行）"),
    ("guide_uninstall", "卸载规范指引（不代执行）"),
    ("guide_configure", "配置规范指引（不代执行）"),
    ("guide_optimize", "设置优化指引（不代执行）"),
)


def packages_tune_list() -> list:
    """返回 packages 写指引清单，供 CLI/GUI 展示。只读展示，调用只回指引。"""
    return [f"· {fn}() — {desc}" for fn, desc in TUNES]
