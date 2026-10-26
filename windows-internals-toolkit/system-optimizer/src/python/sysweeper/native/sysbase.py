"""系统基座子系统（sysbase）：系统目录·包管理·网络仓库·安全工具检测（只读）。

用户指令三问的落地：「你应该了解系统目录、包管理器和网络包管理器的工作，
软件包类似 deb 和 rpm 等是软件包，还有把 msf 给我安装了，如果使用 git 或
二进制包就整合到概念系统」。四轴知识库（data/sysbase_docs.json）：

1. **system_layout**    系统目录：FHS 与「什么是系统/基础工具链/系统关键组件」（LFS 口径）
2. **package_formats**  软件包格式与本地包管理器：deb / rpm / pacman / apk
3. **network_repos**    网络包管理器：apt/yum 仓库协议、GPG 签名链、pin 优先级
4. **msf_distro**       Metasploit 分发渠道、安装路径与检测面（安全与检测）

红线（与全工具一致，本模块**绝不**越界）：
- **绝不安装/卸载任何软件**（无 apt-get install、dpkg -i、rpm -e 路径）；
- **绝不添加/删除仓库源、绝不导入 GPG 密钥**（只读盘点已订阅的源与 pin）；
- **不启动 msfconsole 跑任何模块**（不利用、不扫描、不发载荷——只查安装痕迹）；
- **不写任何系统目录**（只做存在性枚举与包数据库查询）。

本机状态（2026-10-23 实录）：用户要求安装的 metasploit-framework 6.5.3
已由官方 msfinstall 落盘，本探针可完整检出——「装了就能报出来」。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "sysbase_docs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:  # noqa: BLE001
        return {}


REFS = _load_refs()


def reference(key: str) -> dict:
    """返回某系统基座主题的文档参考（含 protocols/interfaces/advice）。"""
    return REFS.get(key, {})


def reference_all() -> dict:
    """返回全部系统基座主题文档参考。"""
    return REFS


# --------------------------------------------------------------------------- #
# 只读命令执行（仅查询类命令；绝不放置任何写路径）                              #
# --------------------------------------------------------------------------- #

def _run(cmd: list, timeout: float = 8.0) -> tuple:
    """跑一个只读命令，返回 (ok, stdout或错误串)。"""
    if not shutil.which(cmd[0]):
        return False, f"未找到命令 {cmd[0]}"
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, env={**os.environ, "LC_ALL": "C"})
    except (OSError, subprocess.TimeoutExpired) as e:  # noqa: BLE001
        return False, f"{cmd[0]} 执行失败: {e}"
    out = (r.stdout or "").strip()
    if r.returncode != 0 and not out:
        return False, f"{cmd[0]} 返回码 {r.returncode}"
    return True, out


def _read_first_line(path: str) -> str:
    """读文件第一行（不存在返回空串）。只读。"""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.readline().strip()
    except OSError:
        return ""


def _listdir(path: str) -> list:
    """列目录（不存在返回空列表）。只读。"""
    try:
        return sorted(os.listdir(path))
    except OSError:
        return []


def _read_lines(path: str) -> list:
    """读全部行（不存在返回空列表）。只读。"""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read().splitlines()
    except OSError:
        return []


# --------------------------------------------------------------------------- #
# 轴一：系统目录（FHS 关键目录存在性、usrmerge、/opt 附加软件清点）              #
# --------------------------------------------------------------------------- #

FHS_PROBE_DIRS = [
    "/etc", "/usr/bin", "/usr/sbin", "/usr/lib", "/usr/share", "/usr/local",
    "/opt", "/var/log", "/boot", "/proc", "/sys", "/run", "/tmp",
]


def probe_system_layout() -> tuple:
    """只读探测 FHS 关键目录存在性、usrmerge 状态与 /opt 附加软件清点。"""
    present = {}
    for d in FHS_PROBE_DIRS:
        present[d] = os.path.isdir(d)
    missing = [d for d, ok in present.items() if not ok]

    # usrmerge：/bin、/sbin、/lib 是否为指向 /usr 下对应目录的符号链接
    usrmerge = {}
    for legacy, merged in (("/bin", "/usr/bin"), ("/sbin", "/usr/sbin"), ("/lib", "/usr/lib")):
        if os.path.islink(legacy):
            target = os.readlink(legacy)
            usrmerge[legacy] = f"符号链接 → {target}"
        elif os.path.isdir(legacy):
            usrmerge[legacy] = "仍是真实目录（未 usrmerge）"
        else:
            usrmerge[legacy] = "不存在"
    merged_count = sum(1 for v in usrmerge.values() if "符号链接" in v)

    # /opt 附加软件清点（目录名 + 是否含 bin/）
    opt_pkgs = []
    for name in _listdir("/opt"):
        full = os.path.join("/opt", name)
        if os.path.isdir(full):
            has_bin = os.path.isdir(os.path.join(full, "bin"))
            opt_pkgs.append({"name": name, "has_bin": has_bin})

    ok = bool(present.get("/etc")) and bool(present.get("/usr/bin"))
    info = {
        "fhs_dirs": present,
        "missing": missing,
        "usrmerge": usrmerge,
        "usrmerge_merged": merged_count,
        "opt_packages": opt_pkgs,
        "note": "只读枚举；绝不创建/删除/修改任何系统目录",
    }
    return ok, info


# --------------------------------------------------------------------------- #
# 轴二：软件包格式与本地包管理器（dpkg/rpm/pacman/apk 存在性 + 包查询）          #
# --------------------------------------------------------------------------- #

def probe_package_managers() -> tuple:
    """只读探测本机包管理器（底层工具存在性）与已登记的关键包。"""
    managers = {
        "dpkg": bool(shutil.which("dpkg")),
        "apt": bool(shutil.which("apt-get")),
        "rpm": bool(shutil.which("rpm")),
        "dnf": bool(shutil.which("dnf")),
        "yum": bool(shutil.which("yum")),
        "pacman": bool(shutil.which("pacman")),
        "apk": bool(shutil.which("apk")),
        "zypper": bool(shutil.which("zypper")),
    }
    found = [m for m, ok in managers.items() if ok]

    # 查询 metasploit-framework 包记录（只读；git 安装的软件在此无记录——
    # 这正是「检测必须两路都查」的实证）
    pkg_record = None
    if managers["dpkg"]:
        ok, out = _run(["dpkg", "-l", "metasploit-framework"])
        if ok and out:
            for line in out.splitlines():
                if line.startswith("ii"):
                    parts = line.split()
                    pkg_record = {"manager": "dpkg", "status": parts[0],
                                  "name": parts[1] if len(parts) > 1 else "",
                                  "version": parts[2] if len(parts) > 2 else "",
                                  "arch": parts[3] if len(parts) > 3 else ""}
                    break
    if pkg_record is None and managers["rpm"]:
        ok, out = _run(["rpm", "-q", "metasploit-framework"])
        if ok and "not installed" not in out:
            pkg_record = {"manager": "rpm", "raw": out}

    return bool(found), {"managers": managers, "found": found,
                         "metasploit_pkg": pkg_record}


def parse_deb_version(version: str) -> dict:
    """拆分 deb 式版本串（epoch:upstream~nightly-revision）。

    例：``6.5.3~20260818061200~1rapid7-1`` →
    upstream=6.5.3、nightly=20260818061200、packager=1rapid7、revision=1。
    """
    v = (version or "").strip()
    out = {"raw": v, "epoch": "", "upstream": "", "nightly": "", "packager": "", "revision": ""}
    if ":" in v:
        out["epoch"], _, v = v.partition(":")
    head, sep, tail = v.rpartition("-")
    if sep:
        v = head
        out["revision"] = tail
    if "~" in v:
        parts = v.split("~")
        out["upstream"] = parts[0]
        # 取最后一个 ~ 段作为打包者修订之前的 nightly 时间戳（如有多段）
        if len(parts) >= 3:
            out["nightly"] = parts[-2]
            out["packager"] = parts[-1]
        elif len(parts) == 2:
            out["nightly"] = parts[1]
    else:
        out["upstream"] = v
    return out


# --------------------------------------------------------------------------- #
# 轴三：网络包管理器（第三方仓库订阅：源文件 / pin / keyring / yum repo）        #
# --------------------------------------------------------------------------- #

def probe_network_repos() -> tuple:
    """只读盘点本机订阅的第三方仓库（apt sources/pin/keyring + yum repo）。

    不添加/删除源、不导入密钥、不执行 apt-get update。
    """
    apt_sources = []
    for name in _listdir("/etc/apt/sources.list.d"):
        if name.endswith((".list", ".sources")):
            path = os.path.join("/etc/apt/sources.list.d", name)
            for line in _read_lines(path):
                if line.strip() and not line.strip().startswith("#"):
                    apt_sources.append({"file": name, "line": line.strip()})

    pins = []
    for name in _listdir("/etc/apt/preferences.d"):
        if name.endswith(".pref"):
            path = os.path.join("/etc/apt/preferences.d", name)
            entry = {"file": name, "package": "", "pin": "", "priority": ""}
            for line in _read_lines(path):
                s = line.strip()
                if s.startswith("Package:"):
                    entry["package"] = s.split(":", 1)[1].strip()
                elif s.startswith("Pin:"):
                    entry["pin"] = s.split(":", 1)[1].strip()
                elif s.startswith("Pin-Priority:"):
                    entry["priority"] = s.split(":", 1)[1].strip()
            pins.append(entry)

    keyrings = [n for n in _listdir("/usr/share/keyrings") if n.endswith(".gpg")]

    yum_repos = []
    for name in _listdir("/etc/yum.repos.d"):
        if name.endswith(".repo"):
            path = os.path.join("/etc/yum.repos.d", name)
            entry = {"file": name, "name": "", "baseurl": "", "enabled": ""}
            for line in _read_lines(path):
                s = line.strip()
                if s.startswith("name="):
                    entry["name"] = s.split("=", 1)[1].strip()
                elif s.startswith("baseurl="):
                    entry["baseurl"] = s.split("=", 1)[1].strip()
                elif s.startswith("enabled="):
                    entry["enabled"] = s.split("=", 1)[1].strip()
            yum_repos.append(entry)

    info = {"apt_sources": apt_sources, "apt_pins": pins,
            "keyrings": keyrings, "yum_repos": yum_repos,
            "note": "只读盘点；第三方源订阅是系统可信边界变更，应人工复核"}
    ok = bool(apt_sources or yum_repos)
    return ok, info


# --------------------------------------------------------------------------- #
# 轴四：Metasploit 检测面（命令 / 包记录 / apt 痕迹 / /opt / git 克隆）           #
# --------------------------------------------------------------------------- #

MSF_COMMANDS = [
    "msfconsole", "msfvenom", "msfupdate", "msfdb", "msfd", "msfrpc", "msfrpcd",
    "msfrop", "msfpescan", "msfelfscan", "msfmachscan", "msfbinscan",
]


def probe_msf() -> tuple:
    """只读检测本机 Metasploit 安装痕迹（deb/rpm 路径 + git 路径两路都查）。

    绝不启动 msfconsole 跑模块、不生成载荷、不做任何扫描/利用动作。
    """
    commands = {}
    for cmd in MSF_COMMANDS:
        path = shutil.which(cmd)
        if path:
            commands[cmd] = path

    install_dir = None
    if os.path.isdir("/opt/metasploit-framework"):
        install_dir = {
            "path": "/opt/metasploit-framework",
            "has_bin": os.path.isdir("/opt/metasploit-framework/bin"),
            "has_embedded": os.path.isdir("/opt/metasploit-framework/embedded"),
            "version_manifest": os.path.isfile(
                "/opt/metasploit-framework/version-manifest.json"),
        }

    # git 路径：常见克隆位置（只查存在性）
    git_clones = []
    for cand in (os.path.expanduser("~/metasploit-framework"),
                 "/opt/src/metasploit-framework",
                 "/usr/local/src/metasploit-framework"):
        if os.path.isdir(os.path.join(cand, ".git")):
            git_clones.append(cand)

    # apt 痕迹（与 network_repos 轴共享事实源，这里做定向判定）
    apt_traces = {
        "sources_list_d": os.path.isfile(
            "/etc/apt/sources.list.d/metasploit-framework.list"),
        "pin": os.path.isfile("/etc/apt/preferences.d/pin-metasploit.pref"),
        "keyring": os.path.isfile("/usr/share/keyrings/metasploit-framework.gpg"),
        "yum_repo": os.path.isfile("/etc/yum.repos.d/metasploit-framework.repo"),
        "rpm_gpg_key": os.path.isfile("/etc/pki/rpm-gpg/RPM-GPG-KEY-Metasploit"),
    }

    detected = bool(commands) or install_dir is not None or bool(git_clones)
    info = {
        "detected": detected,
        "commands": commands,
        "install_dir": install_dir,
        "git_clones": git_clones,
        "apt_traces": apt_traces,
        "note": "只读检测；不启动 msfconsole、不生成载荷、不做任何利用动作",
    }
    return detected, info


def msf_version_report() -> tuple:
    """汇总 msf 检测结果并给出路径判定（二进制包 vs git）与版本解析。"""
    ok, info = probe_msf()
    pm_ok, pm = probe_package_managers()
    lines = ["-- Metasploit 安装痕迹只读检测（命令/包记录/apt痕迹//opt/git 两路都查）--"]
    if not info["detected"]:
        lines.append("   未检测到本机 Metasploit 安装痕迹。")
        return False, "\n".join(lines)

    lines.append(f"   PATH 命令（{len(info['commands'])}）："
                 + "、".join(sorted(info["commands"])) )
    if info["install_dir"]:
        d = info["install_dir"]
        lines.append(f"   安装目录：{d['path']}"
                     f"（bin={'有' if d['has_bin'] else '无'}，"
                     f"embedded={'有' if d['has_embedded'] else '无'}，"
                     f"version-manifest={'有' if d['version_manifest'] else '无'}）")
    if info["git_clones"]:
        lines.append("   git 克隆目录：" + "、".join(info["git_clones"]))
    traces = [k for k, v in info["apt_traces"].items() if v]
    if traces:
        lines.append("   包管理器痕迹：" + "、".join(traces))

    pkg = pm.get("metasploit_pkg")
    if pkg and pkg.get("version"):
        lines.append(f"   包记录（{pkg['manager']}）：{pkg.get('name')} "
                     f"{pkg.get('version')} {pkg.get('arch', '')}")
        pv = parse_deb_version(pkg["version"])
        lines.append(f"   版本解析：upstream={pv['upstream'] or '—'}，"
                     f"nightly 时间戳={pv['nightly'] or '—'}，"
                     f"打包者={pv['packager'] or '—'}，deb 修订={pv['revision'] or '—'}")
        path_kind = "二进制包（deb/rpm 仓库路径）"
    elif info["git_clones"]:
        path_kind = "git 源码路径（无包数据库记录）"
    else:
        path_kind = "二进制安装器路径（pkg/msi 或散落安装）"
    lines.append(f"   安装路径判定：{path_kind}")
    lines.append("   提示：msfconsole 启动时会自检副本陈旧（超两周提示 msfupdate）；"
                 "版本新鲜度亦可由 EOL 巡检统一管理。")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 汇总报告                                                                      #
# --------------------------------------------------------------------------- #

def sysbase_report() -> tuple:
    """端到端系统基座报告（目录布局 + 包管理器 + 仓库订阅 + msf 检测 + 知识库引用）。"""
    lines: list = []
    lines.append("==== 系统基座（只读：系统目录·包管理·网络仓库·安全检测） ====")
    lines.append("")

    lines.append("-- 系统目录（FHS 存在性 / usrmerge / /opt 清点，绝不写任何目录）--")
    ok, layout = probe_system_layout()
    miss = layout.get("missing") or []
    lines.append(f"   FHS 关键目录：{len(layout.get('fhs_dirs', {})) - len(miss)}"
                 f"/{len(layout.get('fhs_dirs', {}))} 在位"
                 + (f"；缺：{'、'.join(miss)}" if miss else ""))
    lines.append(f"   usrmerge：{layout.get('usrmerge_merged', 0)}/3 已合并"
                 f"（{' '.join(f'{k}{v}' for k, v in layout.get('usrmerge', {}).items())}）")
    opts = layout.get("opt_packages") or []
    lines.append(f"   /opt 附加软件（{len(opts)}）："
                 + ("、".join(p["name"] for p in opts) if opts else "无"))
    lines.append("")

    lines.append("-- 本地包管理器（存在性只查；metasploit 包记录查询）--")
    _, pm = probe_package_managers()
    lines.append("   可用：" + ("、".join(pm.get("found") or []) or "无"))
    pkg = pm.get("metasploit_pkg")
    if pkg:
        lines.append(f"   metasploit-framework 包记录：{pkg.get('version', '')}"
                     f"（{pkg.get('manager', '')}）")
    else:
        lines.append("   metasploit-framework 包记录：无（若 /opt 或 git 目录有痕迹，"
                     "说明走的是非包管理器路径）")
    lines.append("")

    lines.append("-- 网络包管理器（第三方仓库订阅：源/pin/keyring，只读盘点）--")
    _, repos = probe_network_repos()
    srcs = repos.get("apt_sources") or []
    lines.append(f"   apt 附加源（{len(srcs)}）：")
    for s in srcs:
        lines.append(f"     · [{s['file']}] {s['line']}")
    for p in repos.get("apt_pins") or []:
        lines.append(f"   pin：[{p['file']}] {p['package']} → {p['pin']}"
                     f"（优先级 {p['priority']}）")
    if repos.get("keyrings"):
        lines.append("   keyring：" + "、".join(repos["keyrings"]))
    for y in repos.get("yum_repos") or []:
        lines.append(f"   yum 源：[{y['file']}] {y['name']} → {y['baseurl']}")
    lines.append("")

    lines.append("-- 安全工具检测面（Metasploit 痕迹，绝不启动利用）--")
    ok, msf = probe_msf()
    if msf.get("detected"):
        lines.append(f"   检出：{len(msf.get('commands', {}))} 个命令在 PATH"
                     + (f"；安装目录 {msf['install_dir']['path']}" if msf.get("install_dir") else ""))
    else:
        lines.append("   未检出本机 Metasploit 痕迹。")
    lines.append("")

    lines.append("-- 知识库引用（data/sysbase_docs.json：目录/包格式/网络仓库/msf 分发）--")
    for key, ref in REFS.items():
        lines.append(f"· {key} — {ref.get('name', '')}")
        lines.append(f"    机构/标准: {ref.get('org', '')}")
        lines.append(f"    文档: {ref.get('url', '')}")
    lines.append("")
    lines.append("安全不变量：本子系统只读——不安装/卸载软件、不动仓库源与密钥、"
                 "不启动 msfconsole 跑任何模块、不写任何系统目录。")
    return True, "\n".join(lines)


def sysbase_doc_list() -> list:
    """返回系统基座主题文档参考清单（供 CLI/GUI 展示）。"""
    lines = []
    for key, ref in REFS.items():
        lines.append(f"· {key} — {ref.get('name', '')}")
        lines.append(f"    机构/标准: {ref.get('org', '')}")
        lines.append(f"    文档: {ref.get('url', '')}")
    return lines
