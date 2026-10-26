"""数字矩阵冗余数据子系统（matrix，周天星斗大阵）测试。

覆盖：refs schema、生存红线（allowlist/denylist 无交集、关键资产必在 denylist）、
只读扫描语义（体积统计/symlink 不跟随/不存在即跳过）、理念在位、红线 token
（无任何删除/改写调用）、四入口接线。
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "python"))

import pytest  # noqa: E402

from sysweeper import registry  # noqa: E402
from sysweeper.native import matrix as ncf  # noqa: E402

SRC = ROOT / "src" / "python" / "sysweeper" / "native" / "matrix.py"


def _refs() -> dict:
    with open(ROOT / "src" / "python" / "sysweeper" / "data" / "matrix_refs.json",
              encoding="utf-8") as f:
        return json.load(f)


# ── refs schema ──────────────────────────────────────────────────────────────

def test_refs_schema():
    r = _refs()
    assert r["key"] == "matrix"
    assert r["title"] and r["concept"]
    assert r["allowlist"]["kinds"] and r["allowlist"]["paths"]
    assert r["denylist"]["paths"]
    assert r["guidance"] and r["compliance"]
    for p in r["allowlist"]["paths"]:
        assert {"template", "kind"} <= set(p)
    for p in r["denylist"]["paths"]:
        assert {"template", "kind"} <= set(p)


def test_allowlist_kinds_known():
    r = _refs()
    known = {k["id"] for k in r["allowlist"]["kinds"]}
    for p in r["allowlist"]["paths"]:
        assert p["kind"] in known, f"未知 kind: {p['kind']}"


# ── 生存红线 ─────────────────────────────────────────────────────────────────

def test_allowlist_denylist_exclusive():
    ok, msg = ncf.check_exclusive()
    assert ok, msg
    assert "无交集" in msg


def test_denylist_covers_critical_assets():
    r = _refs()
    templates = {p["template"] for p in r["denylist"]["paths"]}
    for must in ("~/.ssh", "~/.gnupg", "~/Documents", "~/.mozilla", "/etc/ssl/private"):
        assert must in templates, f"关键资产未纳入 denylist: {must}"


def test_denylist_kinds_cover_personal_and_keys():
    r = _refs()
    kinds = {p["kind"] for p in r["denylist"]["paths"]}
    assert {"keys", "credentials", "personal"} <= kinds


def test_check_exclusive_detects_intersection(monkeypatch):
    """篡改 allowlist 令其与 denylist 相交，红线必须报警。"""
    monkeypatch.setattr(ncf, "allowlist",
                        lambda: [{"template": "~/.ssh", "kind": "user-cache", "note": "x"}])
    ok, msg = ncf.check_exclusive()
    assert not ok and "生存红线被击穿" in msg


# ── 只读扫描语义 ─────────────────────────────────────────────────────────────

def test_dir_size_counts_files_and_skips_symlinks(tmp_path):
    (tmp_path / "a.bin").write_bytes(b"x" * 1000)
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.bin").write_bytes(b"y" * 500)
    # outside 放在 tmp_path 之外：只有跟随 symlink 才会越界统计到它
    outside = tmp_path.parent / "matrix_outside_secret"
    outside.mkdir(exist_ok=True)
    (outside / "secret.bin").write_bytes(b"z" * 9999)
    os.symlink(outside, tmp_path / "link_to_outside")
    b, e, t = ncf.dir_size(str(tmp_path))
    assert b == 1500 and e == 2 and t is False


def test_scan_marks_missing_paths(monkeypatch, tmp_path):
    """不存在的 allowlist 路径：exists=False（活在当下：没有就不统计）。"""
    monkeypatch.setattr(ncf, "allowlist",
                        lambda: [{"template": str(tmp_path / "nope"), "kind": "tmp",
                                  "note": "x"}])
    rows = ncf.scan()
    assert len(rows) == 1 and rows[0]["exists"] is False and "bytes" not in rows[0]


def test_scan_counts_existing_path(monkeypatch, tmp_path):
    d = tmp_path / "cache"
    d.mkdir()
    (d / "f").write_bytes(b"x" * 2048)
    monkeypatch.setattr(ncf, "allowlist",
                        lambda: [{"template": str(d), "kind": "user-cache", "note": "x"}])
    rows = ncf.scan()
    assert rows[0]["exists"] and rows[0]["bytes"] == 2048


# ── 报告与理念 ───────────────────────────────────────────────────────────────

def test_report_contains_philosophy_and_guardrails():
    ok, rep = ncf.matrix_report()
    assert ok
    for kw in ("道法自然", "活在当下", "只有生存才能发展",
               "在发展中能更好的生存", "如此循环，亦复如是"):
        assert kw in rep
    assert "绝不触碰" in rep and "denylist" in rep
    assert "沿原路" in rep  # 原路返回：不代行写操作


def test_human_size():
    assert ncf.human_size(0) == "0 B"
    assert ncf.human_size(1536) == "1.5 KiB"
    assert ncf.human_size(1024 ** 3) == "1.0 GiB"


# ── 红线 token ───────────────────────────────────────────────────────────────

def test_no_write_calls_in_source():
    """只读红线：源码不得出现任何删除/移动/改写调用。"""
    src = SRC.read_text(encoding="utf-8")
    for bad in ("os.remove", "os.rmdir", "os.unlink", "shutil.rmtree",
                "os.rename", "os.replace", "subprocess"):
        assert bad not in src, f"发现写操作调用: {bad}"


def test_source_reads_only_stat(tmp_path):
    """dir_size 只取 st_size，不 open 读内容（用不可读文件验证不崩）。"""
    d = tmp_path / "cache"
    d.mkdir()
    f = d / "blob.bin"
    f.write_bytes(b"x" * 4096)
    os.chmod(f, 0o000)
    try:
        b, e, t = ncf.dir_size(str(d))
        # 权限拒绝时静默跳过，不崩溃、不读内容
        assert t is False
    finally:
        os.chmod(f, 0o644)


# ── 四入口接线 ───────────────────────────────────────────────────────────────

def test_four_entrypoints_wired():
    # 1. native
    assert callable(ncf.matrix_report) and callable(ncf.scan)
    # 2. tasks
    ids = {t.id for t in registry.all_tasks()}
    assert {"matrix_report", "matrix_reclaim_guidance"} <= ids
    # 3. CLI
    from sysweeper import cli
    assert callable(getattr(cli, "cmd_matrix", None))
    # 4. GUI
    from sysweeper import gui
    assert hasattr(gui.SysweeperGUI, "show_matrix")
