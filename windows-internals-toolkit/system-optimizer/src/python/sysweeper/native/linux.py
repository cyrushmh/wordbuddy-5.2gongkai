"""Linux 原生接口：以 LSB 规范文件 /etc/os-release 为主，兼容 lsb_release 命令。

LSB（Linux Standard Base）规定发行版信息写在 /etc/os-release（与
`lsb_release -a` 同源）。我们优先解析该文件，解析不了再用命令，最后降级到
uname。全程标准库，跨发行版（Ubuntu/Debian/Fedora/Arch/manjaro…）可用。"""

from __future__ import annotations

import os
import re
import shutil

from . import common


def read_os_release(path: str = "/etc/os-release") -> dict:
    """解析 LSB 的 /etc/os-release。返回如 {'id':'ubuntu','version_id':'24.04',
    'pretty':'Ubuntu 24.04.1 LTS','name':'Ubuntu'}；拿不到返回 {}。"""
    out = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                out[k] = v
    except OSError:
        return {}
    return out


def lsb_release() -> dict:
    """调用 `lsb_release -a`（若存在）。返回字段字典；不存在返回 {}。"""
    rc, out = common.run("lsb_release -a 2>/dev/null")
    if rc != 0 or not out:
        return {}
    res = {}
    for m in re.finditer(r"^([A-Za-z ]+):\s*(.+)$", out, re.M):
        res[m.group(1).strip().lower().replace(" ", "_")] = m.group(2).strip()
    return res


def detect_distro() -> dict:
    """综合探测发行版，返回 {id, version_id, pretty, name}。"""
    rel = read_os_release()
    if rel:
        return {
            "id": rel.get("ID", ""),
            "version_id": rel.get("VERSION_ID", ""),
            "pretty": rel.get("PRETTY_NAME", ""),
            "name": rel.get("NAME", ""),
        }
    ls = lsb_release()
    if ls:
        return {
            "id": ls.get("distributor_id", "").lower(),
            "version_id": ls.get("release", ""),
            "pretty": ls.get("description", ""),
            "name": ls.get("distributor_id", ""),
        }
    return {"id": "", "version_id": "", "pretty": "", "name": ""}


def pkg_manager() -> str:
    """探测主流包管理器（apt-get/dnf/yum/pacman/zypper/apk）。"""
    for pm in ("apt-get", "dnf", "yum", "pacman", "zypper", "apk"):
        if shutil.which(pm):
            return pm
    return ""


def journal_size() -> str:
    """用 journalctl 取当前日志占用（仅 systemd 系统）。"""
    rc, out = common.run("journalctl --disk-usage 2>/dev/null")
    return out if rc == 0 else ""


def journal_vacuum(size: str = "200M") -> tuple:
    """限制 systemd 日志体积。返回 (ok, msg)。"""
    rc, out = common.run(f"journalctl --vacuum-size={size}")
    return rc == 0, out


def disk_usage(path: str = "/") -> dict | None:
    """标准库 shutil.disk_usage 封装。"""
    return common.disk_usage(path)


def journal_usage() -> dict:
    """把 journalctl --disk-usage 的文本解析成结构化体积（拿不到返回 {}）。"""
    out = journal_size()
    if not out:
        return {}
    import re as _re
    m = _re.search(r"([\d.]+)\s*([KMGT]?B)", out, _re.I)
    if not m:
        return {}
    mult = {"B": 1, "K": 1024, "M": 1024 ** 2, "G": 1024 ** 3, "T": 1024 ** 4}
    unit = m.group(2).upper()
    scale = 1
    for k, v in mult.items():
        if unit.startswith(k):
            scale = v
            break
    try:
        return {"bytes": int(float(m.group(1)) * scale), "raw": m.group(0)}
    except ValueError:
        return {}


def linux_report() -> tuple:
    """Linux 本机发行面零参聚合报告（只读，供统一子系统清单嵌入整体）。

    串联四个既有只读探测：发行版（LSB /etc/os-release）／包管理器／
    systemd 日志体积／根分区用量。非 Linux 平台直接判「不适用」，不报错。

    返回 (ok, msg)。全程只读：不改任何配置、不清日志（清日志只在任务层
    以命令文本形式给出，由用户自己决定）。
    """
    import platform as _platform

    if _platform.system().lower() != "linux":
        return False, "非 Linux 平台，Linux 本机发行面不适用"

    lines = ["Linux 本机发行面（只读聚合：发行版 / 包管理 / 日志 / 根分区）"]

    d = detect_distro()
    pretty = d.get("pretty") or d.get("name") or ""
    if pretty:
        lines.append(f"   · 发行版：{pretty}"
                     + (f"（id={d.get('id','')} {d.get('version_id','')}）" if d.get("id") else ""))
    else:
        lines.append("   · 发行版：未能识别（/etc/os-release 与 lsb_release 都取不到）")

    pm = pkg_manager()
    lines.append(f"   · 包管理器：{pm or '未探测到（apt-get/dnf/yum/pacman/zypper/apk 均无）'}")

    ju = journal_usage()
    if ju:
        lines.append(f"   · systemd 日志占用：{common.human(ju['bytes'])}"
                     + "（只报告不清；要收缩由你自己执行 journalctl --vacuum-size）")
    else:
        lines.append("   · systemd 日志占用：无（未用 systemd-journald 或 journalctl 不可用）")

    du = disk_usage("/")
    if du:
        total = du.get("total", 0) or 0
        used = du.get("used", 0) or 0
        free = du.get("free", 0) or 0
        pct = (used / total * 100) if total else 0.0
        lines.append(f"   · 根分区：已用 {common.human(used)} / 共 {common.human(total)}"
                     f"（{pct:.1f}%，空闲 {common.human(free)}）")
        if total and free / total < 0.10:
            lines.append("   · 提示：根分区空闲不足 10%，建议先清理再谈优化（只读提示，不代劳）")
    else:
        lines.append("   · 根分区：取不到用量（shutil.disk_usage 失败）")

    return True, "\n".join(lines)
