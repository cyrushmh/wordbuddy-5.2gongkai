"""软件包管理器（dpkg/APT · RPM/DNF · apk · pacman · Homebrew · winget · pip · npm · Snap/Flatpak）
的原生接口与文档引用。

「触类旁通、举一反三」：内核（硬件/软件/网络）、桌面环境、其余系统软件（systemd/D-Bus/
NetworkManager/…）、鸿蒙、各小程序端之后，本层把同一模式推广到**包管理器**。它们的接口
彼此完全不同，因此逐个按**自身的协议与接口**核对，绝不套用同一套路径：

- dpkg/APT    : deb(ar 归档) + Debian Policy 控制字段 + Packages 索引(RFC822) + apt-get clean/autoremove
- RPM/DNF     : RPM 标签化头 + rpmdb(SQLite) + repomd.xml 元数据 + dnf clean all
- apk-tools   : .apk(gzip 分段) + APKINDEX.tar.gz + /lib/apk/db/installed + apk cache clean
- pacman      : .pkg.tar.zst + *.db 仓库归档 + /var/lib/pacman/local + paccache
- Homebrew    : Formula/Cask Ruby DSL + bottle 二进制 + brew cleanup
- winget      : YAML 清单(schema v1.x) + 源 REST 接口 + %LOCALAPPDATA%\\Temp\\WinGet
- pip         : PEP 503 简单索引 + PEP 427 wheel + pip cache purge
- npm         : Registry HTTP API + 内容寻址 _cacache(index-v5) + npm cache verify
- Snap/Flatpak: snapd REST(Unix socket) + OSTree refs/commit + flatpak uninstall --unused

所有探测只读：仅统计缓存大小与可清理项数量，不做任何删除/安装。未安装该包管理器时返回
(False, 说明)，由上层降级为指引。参考文档见 data/pkgmgr_docs.json。
"""

from __future__ import annotations

import json
import os
import shutil


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "pkgmgr_docs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:
        return {}


REFS = _load_refs()


def reference(pkg_id: str) -> dict:
    """返回某包管理器的文档参考（含协议 protocols 与接口 interfaces）。"""
    return REFS.get(pkg_id, {})


def reference_all() -> dict:
    """返回全部包管理器文档参考。"""
    return REFS


def pkg_name(key: str) -> str:
    """返回该包管理器在参考表中的名称（无则回退键名）。"""
    return REFS.get(key, {}).get("name", key)


def detect_pkgmgr() -> dict:
    """探测本机可用的包管理器（按各自的官方 CLI 是否可用判断，只读 which 查询）。"""
    return {
        "apt_dpkg": bool(shutil.which("apt-get") or shutil.which("dpkg")),
        "rpm_dnf": bool(shutil.which("dnf") or shutil.which("yum")
                        or shutil.which("rpm") or shutil.which("zypper")),
        "apk": bool(shutil.which("apk")),
        "pacman": bool(shutil.which("pacman")),
        "brew": bool(shutil.which("brew")),
        "winget": bool(shutil.which("winget")),
        "pip": bool(shutil.which("pip") or shutil.which("pip3")
                    or shutil.which("python3")),
        "npm": bool(shutil.which("npm")),
        "universal": bool(shutil.which("snap") or shutil.which("flatpak")),
    }


def _common_run(cmd: str, timeout: int = 30):
    from . import common
    return common.run(cmd, timeout=timeout)


def _fmt_size(n: int) -> str:
    if n >= 1024 * 1024 * 1024:
        return f"{n / 1024 / 1024 / 1024:.2f} GiB"
    if n >= 1024 * 1024:
        return f"{n / 1024 / 1024:.1f} MiB"
    if n >= 1024:
        return f"{n / 1024:.1f} KiB"
    return f"{n} B"


def _dir_size(path: str) -> int:
    """递归统计目录字节数（只读）。不存在或不可读返回 0。"""
    total = 0
    if not path or not os.path.isdir(path):
        return 0
    try:
        for root, _dirs, files in os.walk(path):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
    except OSError:
        return total
    return total


def _cache_line(label: str, path: str) -> str:
    size = _dir_size(path)
    if size:
        return f"   · {label}: {_fmt_size(size)}（{path}）"
    return f"   · {label}: 无/不可读（{path}）"


def _count_lines(out: str) -> int:
    return len([l for l in (out or "").splitlines() if l.strip()])


# ---------------------------------------------------------------------------
# 各包管理器只读探测（均返回 (ok, msg)，ok=False 表示「当前不适用」并给出降级说明）
# ---------------------------------------------------------------------------

def apt_report() -> tuple:
    """dpkg/APT：已装包数、.deb 缓存占用、可 autoremove 包数（只读）。"""
    if not (shutil.which("apt-get") or shutil.which("dpkg")):
        return False, "非 Debian 系（无 apt-get / dpkg）；RHEL/Arch/Alpine 等请用各自的接口核对。"
    lines = []
    if shutil.which("dpkg-query"):
        _rc, out = _common_run("dpkg-query -f '.\\n' -W 2>/dev/null | wc -l")
        n = (out or "").strip().split()
        if n and n[0].isdigit():
            lines.append(f"已安装包: {n[0]} 个（dpkg-query -W，读 /var/lib/dpkg/status）")
    lines.append(_cache_line(".deb 下载缓存", "/var/cache/apt/archives"))
    if shutil.which("apt-get"):
        # -s 为模拟（dry-run），绝不修改系统
        _rc, out = _common_run("apt-get -s autoremove 2>/dev/null | grep -c '^Remv'")
        c = (out or "").strip().split()
        if c and c[0].isdigit():
            lines.append(f"可 autoremove: {c[0]} 个（apt-get -s autoremove 模拟，未实际删除）")
    lines.append("接口: dpkg(1) / dpkg-query(1) / apt-get(8) clean|autoremove / apt-mark(8)；"
                 "协议: deb 包格式(ar) + Debian Policy 控制字段 + Packages 索引(RFC822)")
    return True, "\n".join(lines)


def dnf_report() -> tuple:
    """RPM/DNF：已装包数、缓存占用、未被引用的包（只读）。"""
    tool = next((t for t in ("dnf", "yum", "zypper") if shutil.which(t)), None)
    if not tool and not shutil.which("rpm"):
        return False, "非 RPM 系（无 dnf / yum / zypper / rpm）；Debian/Arch/Alpine 等请用各自接口核对。"
    lines = []
    if shutil.which("rpm"):
        _rc, out = _common_run("rpm -qa 2>/dev/null | wc -l", timeout=45)
        n = (out or "").strip().split()
        if n and n[0].isdigit():
            lines.append(f"已安装包: {n[0]} 个（rpm -qa，读 rpmdb /usr/lib/sysimage/rpm）")
    for p in ("/var/cache/dnf", "/var/cache/yum", "/var/cache/zypp"):
        size = _dir_size(p)
        if size:
            lines.append(f"   · 仓库缓存: {_fmt_size(size)}（{p}）")
    if tool == "dnf":
        _rc, out = _common_run("dnf -q repoquery --unneeded 2>/dev/null | wc -l", timeout=60)
        c = (out or "").strip().split()
        if c and c[0].isdigit():
            lines.append(f"未被引用的包: {c[0]} 个（dnf repoquery --unneeded，只读查询）")
    lines.append(f"接口: rpm(8) / {tool or 'rpm'}(8) clean all；（openSUSE 同层为 zypper(8)）；"
                 "协议: RPM 标签化头 + rpmdb(SQLite) + repomd.xml 元数据")
    return True, "\n".join(lines)


def apk_report() -> tuple:
    """apk-tools：已装包数、缓存占用（只读）。"""
    if not shutil.which("apk"):
        return False, "非 Alpine（无 apk）；Debian/RHEL/Arch 等请用各自接口核对（容器镜像多为 Alpine）。"
    lines = []
    _rc, out = _common_run("apk info 2>/dev/null | wc -l")
    n = (out or "").strip().split()
    if n and n[0].isdigit():
        lines.append(f"已安装包: {n[0]} 个（apk info，读 /lib/apk/db/installed）")
    for p in ("/etc/apk/cache", "/var/cache/apk"):
        size = _dir_size(p)
        if size:
            lines.append(f"   · 包缓存: {_fmt_size(size)}（{p}）")
    lines.append("接口: apk(8) add|del|info|cache clean|fix；"
                 "协议: .apk(gzip 分段) + APKINDEX.tar.gz 签名索引")
    return True, "\n".join(lines)


def pacman_report() -> tuple:
    """pacman：已装包数、缓存占用、孤儿包数（只读）。"""
    if not shutil.which("pacman"):
        return False, "非 Arch 系（无 pacman）；Debian/RHEL/Alpine 等请用各自接口核对。"
    lines = []
    _rc, out = _common_run("pacman -Q 2>/dev/null | wc -l")
    n = (out or "").strip().split()
    if n and n[0].isdigit():
        lines.append(f"已安装包: {n[0]} 个（pacman -Q，读 /var/lib/pacman/local）")
    lines.append(_cache_line("包缓存", "/var/cache/pacman/pkg"))
    _rc, out = _common_run("pacman -Qdt 2>/dev/null | wc -l")
    c = (out or "").strip().split()
    if c and c[0].isdigit():
        lines.append(f"孤儿包(未被任何包依赖): {c[0]} 个（pacman -Qdt，只读查询）")
    lines.append("接口: pacman(8) -Q|-Sc|paccache(8) -rk2；"
                 "协议: .pkg.tar.zst + *.db 仓库归档 + PGP 签名")
    return True, "\n".join(lines)


def brew_report() -> tuple:
    """Homebrew：已装 formula/cask 数、缓存占用（只读；-n 为干跑）。"""
    if not shutil.which("brew"):
        return False, "未安装 Homebrew（brew）；macOS 未装或 Linux 未装 Linuxbrew 时跳过。"
    lines = []
    _rc, out = _common_run("brew list --formula 2>/dev/null | wc -l", timeout=45)
    n = (out or "").strip().split()
    if n and n[0].isdigit():
        lines.append(f"已装 formula: {n[0]} 个（brew list --formula）")
    _rc, cache = _common_run("brew --cache 2>/dev/null")
    cache_dir = (cache or "").strip().splitlines()[0] if (cache or "").strip() else ""
    if cache_dir:
        lines.append(_cache_line("下载缓存", cache_dir))
    # -n = dry-run：只列出将清理的内容，绝不删除
    _rc, out = _common_run("brew cleanup -n 2>/dev/null | grep -ci 'would remove\\|remove:'", timeout=60)
    c = (out or "").strip().split()
    if c and c[0].isdigit() and c[0] != "0":
        lines.append(f"可清理条目: {c[0]} 条（brew cleanup -n 干跑，未实际删除）")
    lines.append("接口: brew(1) cleanup|doctor|outdated|autoremove；"
                 "协议: Formula/Cask Ruby DSL + bottle 预编译包")
    return True, "\n".join(lines)


def winget_report() -> tuple:
    """winget：版本信息与下载缓存占用（只读）。"""
    if not shutil.which("winget"):
        return False, "未安装 winget（Windows Package Manager）；Windows 上可从 Microsoft Store 获取 App Installer。"
    lines = []
    _rc, out = _common_run("winget --version 2>/dev/null")
    if (out or "").strip():
        lines.append("winget 版本: " + out.strip().splitlines()[0])
    local = os.environ.get("LOCALAPPDATA", "")
    for label, sub in (("下载缓存", os.path.join("Temp", "WinGet")),
                       ("包安装目录", os.path.join("Microsoft", "WinGet", "Packages"))):
        p = os.path.join(local, sub) if local else ""
        if p:
            lines.append(_cache_line(label, p))
    lines.append("接口: winget(1) list|upgrade|uninstall|show；"
                 "协议: YAML 清单(schema v1.x) + 源 REST 接口(manifestSearch/manifest)")
    return True, "\n".join(lines)


def pip_report() -> tuple:
    """pip：缓存目录与占用（只读；优先官方 pip cache dir）。"""
    pipe = next((t for t in ("pip3", "pip") if shutil.which(t)), None)
    if not pipe and not shutil.which("python3"):
        return False, "未安装 pip / python3；Python 包缓存项跳过。"
    lines = []
    cache_dir = ""
    if pipe:
        _rc, out = _common_run(f"{pipe} cache dir 2>/dev/null", timeout=45)
        cache_dir = (out or "").strip().splitlines()[-1] if (out or "").strip() else ""
    if not cache_dir:
        cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "pip")
    lines.append(_cache_line("下载缓存", cache_dir))
    if pipe:
        _rc, out = _common_run(f"{pipe} cache list 2>/dev/null | tail -3", timeout=45)
        rows = [l.strip().lstrip("- ").strip()
                for l in (out or "").splitlines() if l.strip()]
        for r in rows[-2:]:
            lines.append("   · 最近缓存: " + r)
    lines.append("接口: pip cache(1) dir|purge|list / pip(1) install --no-cache-dir；"
                 "协议: PEP 503 简单索引 + PEP 427 wheel + PEP 517/518 构建接口")
    return True, "\n".join(lines)


def npm_report() -> tuple:
    """npm：缓存目录与占用（只读；不用 verify，因为 verify 会改写缓存）。"""
    if not shutil.which("npm"):
        return False, "未安装 npm（Node.js）；前端/Node 项目外的机器上跳过该项。"
    lines = []
    _rc, out = _common_run("npm config get cache 2>/dev/null", timeout=45)
    base = (out or "").strip().splitlines()[-1] if (out or "").strip() else ""
    if not base or not os.path.isdir(base):
        base = os.path.join(os.path.expanduser("~"), ".npm")
    # `npm config get cache` 给出的是缓存根（如 ~/.npm 或 ~/.npm/_cacache，版本间有差异）；
    # 内容寻址的实际子层固定是 _cacache/index-v5 + _cacache/content-v2
    cache_dir = os.path.join(base, "_cacache")
    if not os.path.isdir(cache_dir):
        cache_dir = base if os.path.isdir(base) else \
            os.path.join(os.path.expanduser("~"), ".npm", "_cacache")
    lines.append(f"   · 缓存根目录: {base}（npm config get cache）")
    lines.append(_cache_line("内容寻址缓存", cache_dir))
    # 只统计 index-v5 / content-v2 两个子层，展示缓存分层结构（只读）
    for sub in ("content-v2", "index-v5"):
        size = _dir_size(os.path.join(cache_dir, sub))
        if size:
            lines.append(f"   · {sub}: {_fmt_size(size)}")
    lines.append("接口: npm-cache(1) verify|clean / npm(1) ci|prune|outdated；"
                 "协议: Registry HTTP API + _cacache 内容寻址(SRI sha512)")
    return True, "\n".join(lines)


def universal_report() -> tuple:
    """Snap / Flatpak：已装应用数与占用（只读；snapd 走 CLI 而非直连 socket）。"""
    has_snap, has_flatpak = bool(shutil.which("snap")), bool(shutil.which("flatpak"))
    if not (has_snap or has_flatpak):
        return False, "未安装 snap / flatpak（通用打包）；纯发行版原生包管理的机器跳过。"
    lines = []
    if has_snap:
        _rc, out = _common_run("snap list 2>/dev/null | tail -n +2 | wc -l")
        n = (out or "").strip().split()
        if n and n[0].isdigit():
            lines.append(f"snap 包: {n[0]} 个（snap list）")
        _rc, out = _common_run("snap get system refresh.retain 2>/dev/null")
        r = (out or "").strip()
        lines.append(f"   · refresh.retain（保留版本数）: {r or '(默认 3)'}")
    if has_flatpak:
        _rc, out = _common_run("flatpak list --app 2>/dev/null | wc -l")
        n = (out or "").strip().split()
        if n and n[0].isdigit():
            lines.append(f"flatpak 应用: {n[0]} 个（flatpak list --app）")
        _rc, out = _common_run("flatpak list --runtime 2>/dev/null | wc -l")
        n = (out or "").strip().split()
        if n and n[0].isdigit():
            lines.append(f"flatpak runtime/扩展: {n[0]} 个（可 flatpak uninstall --unused 清理无引用者）")
    lines.append("接口: snap(8) list|remove --revision|set system refresh.retain / "
                 "flatpak(1) list|uninstall --unused；"
                 "协议: snapd REST(Unix socket /run/snapd.socket) + OSTree refs/commit")
    return True, "\n".join(lines)


# 探测函数 → 展示标签（CLI/GUI 统一遍历，避免重复列表）
PROBES = (
    ("apt_report", "dpkg / APT（Debian 系：deb + Packages 索引）"),
    ("dnf_report", "RPM / DNF（RHEL 系：rpmdb + repomd.xml）"),
    ("apk_report", "apk-tools（Alpine：APKINDEX + .apk）"),
    ("pacman_report", "pacman（Arch：.pkg.tar.zst + *.db）"),
    ("brew_report", "Homebrew（Formula/Cask DSL + bottle）"),
    ("winget_report", "winget（Windows：YAML 清单 + REST 源）"),
    ("pip_report", "pip（PEP 503 索引 + wheel 缓存）"),
    ("npm_report", "npm（Registry API + _cacache）"),
    ("universal_report", "Snap / Flatpak（snapd REST + OSTree）"),
)


def environment_report() -> list:
    """返回包管理器环境跟踪报告（多行文本），供 CLI/GUI 展示。"""
    det = detect_pkgmgr()
    lines = ["本机包管理器探测（按各自官方 CLI 判定）："]
    for key in REFS:
        lines.append(f"   {pkg_name(key).split('（')[0]:<26} : "
                     f"{'✓ 可用' if det.get(key) else '✗ 未安装'}")
    lines.append("（未安装者不强求安装——对应任务自动降级为指引）")
    return lines


def pkgmgr_doc_list(key: str = None) -> list:
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
