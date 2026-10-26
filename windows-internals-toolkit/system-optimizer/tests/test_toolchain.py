"""工具链全景子系统测试（0000.0000.0000.0017.20261025）：catalog 数据层 + 只读探针 + 任务层 + 接线。

只读不变量贯穿：不安装/卸载、不构建、不下载、不启动 msfconsole；setup_steps/commands
是 README 性质的逻辑顺序，不是自动执行队列。
"""

from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.abspath(os.path.join(HERE, "..", "src", "python"))
if PKG_ROOT not in __import__("sys").path:
    __import__("sys").path.insert(0, PKG_ROOT)


CATALOG = os.path.join(PKG_ROOT, "sysweeper", "data", "toolchain_catalog.json")


# ── 数据层：catalog 结构与引用 ──
def test_catalog_schema_and_counts():
    d = json.load(open(CATALOG, encoding="utf-8"))
    assert d["schema"] == "toolchain_catalog/v1"
    assert len(d["host_toolchains"]) >= 20
    assert len(d["repo_tools"]) >= 7
    assert len(d["target_matrix"]) >= 10
    assert len(d["categories"]) == 10  # #603 新增 vcs-network/container/media 三类


def test_catalog_category_refs_legal():
    d = json.load(open(CATALOG, encoding="utf-8"))
    keys = {c["key"] for c in d["categories"]}
    for grp in ("host_toolchains", "repo_tools"):
        for e in d[grp]:
            assert e["category"] in keys, f"{grp}/{e['id']} 类别引用悬空: {e['category']}"


def test_catalog_required_fields():
    d = json.load(open(CATALOG, encoding="utf-8"))
    for e in d["host_toolchains"]:
        for f in ("id", "category", "name", "version", "status", "commands"):
            assert f in e, f"host_toolchains/{e.get('id')} 缺字段 {f}"
        assert e.get("setup_steps") or e["category"] in (
            "native-build", "emulation", "editor-browser", "packaging", "quality",
            "security-detect", "vcs-network", "container", "media"), \
            f"{e['id']} 交叉/关键条目应有 setup_steps"
    for e in d["repo_tools"]:
        for f in ("id", "category", "name", "paths", "setup_steps", "commands", "verify"):
            assert f in e, f"repo_tools/{e.get('id')} 缺字段 {f}"


def test_catalog_key_entries_present():
    d = json.load(open(CATALOG, encoding="utf-8"))
    ids = {e["id"] for e in d["host_toolchains"]}
    for must in ("gcc-multilib", "mingw-w64", "android-ndk-r26d", "ohos-sdk", "libiconv-android",
                 "osxcross", "rust", "go", "dotnet", "openjdk", "python", "node", "deno", "ruby",
                 "qt", "qemu-user", "wine", "firefox", "dpkg-lintian", "metasploit",
                 # #603 新增 19 条
                 "git", "http-clients", "rsync", "openssl", "ssh", "compression-suite",
                 "docker", "ffmpeg", "chrome", "editor-suite", "terminal-mux",
                 "binary-inspect", "autotools-suite", "debug-trace", "lint-format",
                 "build-extra", "text-data-utils", "perl", "tcl"):
        assert must in ids, f"宿主工具链缺条: {must}"
    tools = {e["id"] for e in d["repo_tools"]}
    for must in ("pe-viewer-family", "classics-cli", "classics-rs", "sysweeper", "syspkg",
                 "novel-website", "classics-swift-linux", "classics-harmony-app",
                 "classics-ios-mac", "android-app", "quantum-kernel",
                 # #603 新增 3 条
                 "docker-support", "ci-workflows", "repo-guard"):
        assert must in tools, f"仓库工具缺条: {must}"


def test_catalog_freshness_two_columns():
    d = json.load(open(CATALOG, encoding="utf-8"))
    fr = d["version_freshness"]
    assert fr["needs_action"] and fr["fresh"]
    for e in fr["needs_action"]:
        for f in ("item", "host", "upstream", "action"):
            assert f in e


# ── 原生探针：只读报告（本机实采，不装不卸）──
def test_host_probe_report():
    from sysweeper.native import toolchain
    ok, msg = toolchain.host_probe_report()
    assert ok is True
    assert "小结" in msg
    # 本机（2026-10-24 实录）交叉链三件均在位：NDK/OHOS/libiconv
    assert "android-ndk-r26d" in msg and "ohos-sdk" in msg
    assert "✓" in msg
    # #638：探针与 catalog 宿主条目全覆盖（42/42），缺席仅 osxcross（未安装）
    assert "全覆盖" in msg


def test_probe_covers_catalog():
    """#638 回归守卫：catalog 每个宿主条目都有探针（HOST_PROBES ∪ HOST_PROBE_PATHS）。"""
    from sysweeper.native import toolchain
    probed = set(toolchain.HOST_PROBES) | set(toolchain.HOST_PROBE_PATHS)
    ids = {e["id"] for e in json.load(open(CATALOG, encoding="utf-8"))["host_toolchains"]}
    assert ids <= probed, f"catalog 条目无探针: {sorted(ids - probed)}"


def test_ver_flags_align_with_probes():
    """#638 回归守卫：VER_FLAGS 每个旗标特例都对应真实探针命令。"""
    from sysweeper.native import toolchain
    for exe in toolchain.VER_FLAGS:
        assert exe in toolchain.HOST_PROBES.values(), f"VER_FLAGS/{exe} 无对应探针"
    assert toolchain.VER_FLAGS["ssh"] == ("-V",) and toolchain.VER_FLAGS["openssl"] == ("version",)


def test_catalog_and_matrix_reports():
    from sysweeper.native import toolchain
    ok, msg = toolchain.catalog_report()
    assert ok and "toolchain_catalog/v1" in msg
    ok, msg = toolchain.target_matrix_report()
    assert ok and "aarch64-linux-android21" in msg and "aarch64-unknown-linux-ohos" in msg


def test_repo_tools_report_has_logic_order():
    from sysweeper.native import toolchain
    ok, msg = toolchain.repo_tools_report()
    assert ok is True
    assert "配置[1]" in msg and "命令[1]" in msg and "验收:" in msg
    ok, msg = toolchain.repo_tools_report("cross-compile")
    assert ok is True  # 分类别过滤不报错（repo_tools 无此类别时给空说明）


def test_toolchain_report_end_to_end():
    from sysweeper.native import toolchain
    ok, rep = toolchain.toolchain_report(["cross-compile", "ndk"])
    assert ok is True
    assert "工具链全景报告" in rep
    assert "安全不变量" in rep
    assert "不是自动执行队列" in rep


def test_environment_report_runs():
    from sysweeper.native import toolchain
    lines = toolchain.environment_report()
    assert isinstance(lines, list) and lines
    assert any("编目全景" in x for x in lines)


# ── 任务层与接线 ──
def test_tasks_registered():
    from sysweeper import registry
    ids = [t.id for t in registry.all_tasks() if t.id.startswith("toolchain_")]
    assert len(ids) == 4, f"toolchain_* 任务应为 4 项，实得 {ids}"
    for must in ("toolchain_catalog", "toolchain_host_probe", "toolchain_target_matrix",
                 "toolchain_freshness"):
        assert must in ids


def test_subsystem_registered_default_on():
    from sysweeper.native import subsystems
    sub = subsystems.BY_KEY.get("toolchain")
    assert sub is not None, "toolchain 未登记进统一子系统清单"
    assert sub.default_on is True
    assert sub.module == "toolchain" and sub.fn == "toolchain_report"
    assert sub.version.startswith("0000.0000.0000.0002")


def test_subsystem_report_callable():
    from sysweeper.native import subsystems
    probes = subsystems.enabled_probes()
    keys = [p[0] if isinstance(p, (tuple, list)) else getattr(p, "key", p) for p in probes]
    assert "toolchain" in keys, "toolchain 未进入启用探针清单"
    from sysweeper.native import toolchain
    assert subsystems.is_enabled("toolchain") is True
    assert callable(toolchain.toolchain_report)


def test_no_write_paths_in_source():
    """红线：源码不得出现安装/构建/下载执行路径。"""
    p = os.path.join(PKG_ROOT, "sysweeper", "native", "toolchain.py")
    src = open(p, encoding="utf-8").read()
    for bad in ("apt-get install", "apt install", "pip install", "cargo build", "go build",
                "dpkg -i", "curl ", "wget ", "msfconsole -"):
        assert bad not in src, f"toolchain.py 出现执行路径: {bad}"
