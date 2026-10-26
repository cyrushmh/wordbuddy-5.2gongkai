"""工具链全景子系统（toolchain）：宿主工具链 × 仓库工具软件 × 目标架构矩阵（只读）。

用户指令的落地：「以概念系统与子系统，将你整的工具链和生成的工具软件与使用方法 readme
（包括配置和命令的逻辑顺序过程）都分类别与系统架构和仓库目录适配存放」。

本模块把 **data/toolchain_catalog.json**（结构化编目）与**本机实采**合成为只读报告：

  1. catalog_report      编目全景：类别 × 宿主工具链条目 × 仓库工具软件 × 目标矩阵
  2. host_probe_report   本机实采：catalog 宿主条目全覆盖探测（which + 首行版本，
     版本旗标特例按上游口径：openssl/go 用 version、ssh/tmux 用 -V、perl 用 -v、
     ffmpeg 用 -version、tclsh 走 stdin 读 $tcl_version）
  3. repo_tools_report   仓库工具软件：分类别 + 仓库目录 + 配置逻辑顺序 + 命令序列
  4. target_matrix_report 目标架构矩阵：三元组 → 工具链 → 验证口径
  5. freshness_report    上游新鲜度：needs_action / fresh 两栏（来源官网与安全公告）

红线（与全工具一致）：
- **只读探测**：which / --version / 文件存在性；绝不安装、绝不卸载、绝不构建、绝不下载；
- catalog 的 setup_steps / commands 是**给人看的逻辑顺序**（README 性质），不是自动执行队列；
- msf 条目只做存在性检测（沿用 secdetect 口径），绝不启动 msfconsole。
"""

from __future__ import annotations

import json
import shutil
import subprocess

PROBES = (
    ("catalog_report", "编目全景（类别×工具链×仓库工具×目标矩阵）"),
    ("host_probe_report", "本机实采（which + 版本实读）"),
    ("repo_tools_report", "仓库工具软件（分类别+目录+命令序列）"),
    ("target_matrix_report", "目标架构矩阵"),
    ("freshness_report", "上游新鲜度（needs_action / fresh）"),
)


def _load_catalog() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "toolchain_catalog.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:  # noqa: BLE001
        return {}


CATALOG = _load_catalog()


# 版本旗标特例（默认 --version；以下按上游口径实采，与 catalog commands 对齐）
VER_FLAGS = {
    "go": ("version",),        # go version（子命令，非 --version）
    "openssl": ("version",),   # openssl version（非 --version）
    "ssh": ("-V",),            # OpenSSH 大写 -V
    "tmux": ("-V",),           # tmux 大写 -V
    "perl": ("-v",),           # Perl 小写 -v
    "ffmpeg": ("-version",),   # FFmpeg 单横线 -version
}


def _ver_line(exe: str) -> str | None:
    # tclsh 无版本旗标：经 stdin 输入 puts $tcl_version 读内建变量（catalog 实采口径）
    if exe == "tclsh":
        argv, stdin_data = [exe], "puts $tcl_version\n"
    else:
        argv = [exe, *VER_FLAGS.get(exe, ("--version",))]
        stdin_data = None
    try:
        out = subprocess.run(argv, input=stdin_data, capture_output=True, text=True, timeout=6)
        # 跳过空行（perl -v 等首行为空），取第一条非空输出
        line = next((l.strip() for l in (out.stdout or out.stderr).splitlines() if l.strip()), "")
        return line or "(版本读取失败)"
    except (OSError, subprocess.SubprocessError, IndexError):
        return None


# 本机实采：catalog id → 探测命令（与 catalog.commands 对齐，每个宿主条目取一个代表命令；
# 版本旗标特例见 VER_FLAGS；#603 补全后与 catalog host_toolchains 全覆盖）
HOST_PROBES = {
    # ── 语言/编译/仿真/打包/安全检测（原有 19 项）──
    "gcc-multilib": "gcc",
    "mingw-w64": "x86_64-w64-mingw32-gcc",
    "gcc-native": "gcc",
    "clang": "clang",
    "binutils-make-cmake": "make",
    "rust": "rustc",
    "go": "go",
    "dotnet": "dotnet",
    "openjdk": "java",
    "python": "python3",
    "node": "node",
    "deno": "deno",
    "ruby": "ruby",
    "qt": "qmake",
    "qemu-user": "qemu-aarch64-static",
    "wine": "wine",
    "firefox": "firefox",
    "dpkg-lintian": "dpkg",
    "metasploit": "msfconsole",
    # ── vcs-network：版本控制与网络（#603 新增 6 项）──
    "git": "git",
    "http-clients": "curl",
    "rsync": "rsync",
    "openssl": "openssl",
    "ssh": "ssh",
    "compression-suite": "tar",
    # ── container：容器（#603 新增 1 项）──
    "docker": "docker",
    # ── media：媒体（#603 新增 1 项）──
    "ffmpeg": "ffmpeg",
    # ── editor-browser：编辑器与浏览器（#603 新增 3 项）──
    "chrome": "google-chrome",
    "editor-suite": "vim",
    "terminal-mux": "tmux",
    # ── quality：质量套件（#603 新增 4 项）──
    "binary-inspect": "file",
    "autotools-suite": "autoconf",
    "debug-trace": "gdb",
    "lint-format": "clang-format",
    # ── native-build：原生构建附加（#603 新增 4 项）──
    "build-extra": "ninja",
    "text-data-utils": "jq",
    "perl": "perl",
    "tcl": "tclsh",
    # ── cross-compile：macOS 交叉（osxcross 未安装，如实记缺席）──
    "osxcross": "o64-clang",
}

# 交叉工具链绝对路径回退（PATH 里没有时按 catalog paths 实采；不装不卸只探测）
HOST_PROBE_PATHS = {
    "android-ndk-r26d": "/opt/android-ndk/android-ndk-r26d/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android21-clang",
    "ohos-sdk": "/opt/ohos-sdk/linux/native/llvm/bin/aarch64-unknown-linux-ohos-clang",
    "libiconv-android": "/opt/libiconv-android-a64/lib/libiconv.a",
}


def catalog_report() -> tuple:
    cat = CATALOG
    if not cat:
        return False, "toolchain_catalog.json 缺失或不可解析（data 层损坏）"
    lines = [f"工具链全景编目（{cat.get('schema')}，built {cat.get('built')}，宿主 {cat.get('host', {}).get('os')}）:"]
    lines.append("   · 类别（分类别存放的第一维）:")
    for c in cat.get("categories", []):
        lines.append(f"     - {c['label']}（{c['key']}）：{c['note']}")
    lines.append(f"   · 宿主工具链 {len(cat.get('host_toolchains', []))} 条 / "
                 f"仓库工具软件 {len(cat.get('repo_tools', []))} 条 / "
                 f"目标架构矩阵 {len(cat.get('target_matrix', []))} 条")
    return True, "\n".join(lines)


def host_probe_report() -> tuple:
    import os
    lines = ["本机工具链实采（which + 首行版本，只读；未装即缺席）:"]
    hit = miss = 0
    for tid, exe in HOST_PROBES.items():
        path = shutil.which(exe)
        if path is None:
            miss += 1
            lines.append(f"   · {tid:<22} ✗ 未探测到（{exe} 不在 PATH）")
            continue
        hit += 1
        v = _ver_line(exe)
        lines.append(f"   · {tid:<22} ✓ {path}")
        lines.append(f"       {v or '(版本读取失败)'}")
    # 交叉工具链：PATH 缺席时按 catalog 绝对路径回退（文件存在性只读探测）
    for tid, abs_path in HOST_PROBE_PATHS.items():
        if tid in HOST_PROBES:
            continue
        if os.path.exists(abs_path):
            hit += 1
            lines.append(f"   · {tid:<22} ✓ {abs_path}（绝对路径回退，未入 PATH）")
            if abs_path.endswith("clang"):
                lines.append(f"       {_ver_line(abs_path) or '(版本读取失败)'}")
        else:
            miss += 1
            lines.append(f"   · {tid:<22} ✗ 未探测到（{abs_path} 不存在）")
    # 探针覆盖率：本模块探测键 vs catalog 宿主条目（只读统计，无副作用）
    probed = set(HOST_PROBES) | set(HOST_PROBE_PATHS)
    cat_ids = {t.get("id") for t in CATALOG.get("host_toolchains", [])}
    covered = len(probed & cat_ids)
    gap = sorted(cat_ids - probed)
    lines.append(f"   小结：在位 {hit} 项 / 缺席 {miss} 项 / 探针覆盖 catalog 宿主条目 "
                 f"{covered}/{len(cat_ids)} 条"
                 + (f"（未覆盖: {'、'.join(gap)}）" if gap else "（全覆盖）"))
    lines.append("   （缺席≠异常：osxcross 等交叉链按需安装；版本旗标特例见 VER_FLAGS）")
    return True, "\n".join(lines)


def repo_tools_report(category: str | None = None) -> tuple:
    tools = CATALOG.get("repo_tools", [])
    if category:
        tools = [t for t in tools if t.get("category") == category]
    if not tools:
        return True, "仓库工具软件：无匹配条目"
    lines = ["仓库工具软件（分类别 × 仓库目录 × 配置逻辑顺序 × 命令序列）:"]
    for t in tools:
        lines.append(f"   ■ {t['name']}（{t.get('version', 'needs_verify')}，{t.get('status')}）")
        lines.append(f"     类别: {t.get('category')}")
        for p in t.get("paths", []):
            lines.append(f"     目录: {p}")
        for i, s in enumerate(t.get("setup_steps", []), 1):
            lines.append(f"     配置[{i}] {s}")
        for i, c in enumerate(t.get("commands", []), 1):
            lines.append(f"     命令[{i}] {c}")
        lines.append(f"     验收: {t.get('verify', '')}")
    return True, "\n".join(lines)


def target_matrix_report() -> tuple:
    rows = CATALOG.get("target_matrix", [])
    lines = ["目标架构矩阵（triple → OS → 工具链 → 验证口径）:"]
    for r in rows:
        lines.append(f"   · {r['triple']}")
        lines.append(f"       OS: {r['os']}｜工具链: {r['toolchain']}｜验证: {r['verified']}")
    return True, "\n".join(lines)


def freshness_report() -> tuple:
    fr = CATALOG.get("version_freshness", {})
    lines = [f"上游新鲜度（{fr.get('note', '')}）:"]
    lines.append("   · 需要关注（needs_action）:")
    for e in fr.get("needs_action", []):
        lines.append(f"     - {e['item']}：宿主 {e['host']} → 上游 {e['upstream']}")
        lines.append(f"       处置: {e['action']}")
    lines.append("   · 当前新鲜（fresh）:")
    for e in fr.get("fresh", []):
        lines.append(f"     - {e['item']}：宿主 {e['host']}（{e['note']}）")
    return True, "\n".join(lines)


def environment_report() -> list:
    lines = ["工具链全景（toolchain）· 本机只读探测："]
    for fn, lab in PROBES:
        ok, msg = globals()[fn]()
        lines.append(f"   · {lab}: {'✓ 完成' if ok else '✗ 失败'}")
        if isinstance(msg, str) and msg.strip():
            lines.append("       " + msg.replace("\n", "\n       "))
    return lines


def toolchain_report(env_tags: list | None = None, readings: dict | None = None) -> tuple:
    lines = ["== 工具链全景报告（toolchain：宿主工具链 × 仓库工具软件 × 目标架构矩阵，只读不写）=="]
    lines.append(f"维度标签: {sorted(set(env_tags or [])) or '未声明（默认基线）'}")
    lines.append("")
    lines.append("[① 编目全景]")
    ok, msg = catalog_report()
    lines.append(msg)
    lines.append("")
    lines.append("[② 本机实采（which + 版本实读）]")
    ok, msg = host_probe_report()
    lines.append(msg)
    lines.append("")
    lines.append("[③ 目标架构矩阵]")
    ok, msg = target_matrix_report()
    lines.append(msg)
    lines.append("")
    lines.append("[④ 上游新鲜度]")
    ok, msg = freshness_report()
    lines.append(msg)
    lines.append("")
    lines.append("安全不变量：toolchain 只探测与编目；绝不安装/卸载/构建/下载；"
                 "catalog 的 setup_steps 与 commands 是给人看的逻辑顺序（README 性质），不是自动执行队列。")
    return True, "\n".join(lines)


TUNES = (
    ("repo_tools_report", "仓库工具软件清单（分类别+目录+命令序列）"),
    ("target_matrix_report", "目标架构矩阵"),
    ("freshness_report", "上游新鲜度两栏"),
)


def toolchain_tune_list() -> list:
    return [f"· {fn}() — {desc}" for fn, desc in TUNES]
