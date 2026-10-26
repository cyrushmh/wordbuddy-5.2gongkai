"""fail2ban 学习应用子系统（f2b，十二都天神煞大阵）测试。

覆盖：refs schema（官方源/GPL-2.0 声明/不 vendored）、ini 只读解析、探测降级、
只读咨询、理念在位、红线 token（不代写/不代行封禁/只读白名单/无 SPDX GPL 声明）、
四入口接线。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "python"))

from sysweeper import registry  # noqa: E402
from sysweeper.native import f2b as ncf  # noqa: E402

SRC = ROOT / "src" / "python" / "sysweeper" / "native" / "f2b.py"


def _refs() -> dict:
    with open(ROOT / "src" / "python" / "sysweeper" / "data" / "f2b_refs.json",
              encoding="utf-8") as f:
        return json.load(f)


# ── refs schema 与许可证边界 ─────────────────────────────────────────────────

def test_refs_schema():
    r = _refs()
    assert r["key"] == "f2b" and r["title"] and r["concept"]
    up = r["upstream"]
    assert up["name"] == "fail2ban"
    assert up["license"] == "GPL-2.0"
    assert "不 vendored" in up["license_note"]
    assert r["architecture"]["layers"] and len(r["architecture"]["layers"]) >= 4
    assert r["common_jails"]["jails"] and r["consult_templates"] and r["compliance"]


def test_official_sources():
    up = _refs()["upstream"]
    for key in ("homepage", "source", "docs"):
        url = up[key]
        assert url.startswith("https://")
        assert "fail2ban" in url
    assert up["source"] == "https://github.com/fail2ban/fail2ban"


def test_license_declared_but_not_vendored():
    """GPL-2.0 强拷贝左：文字述明可以，源码 SPDX 声明与 vendored 代码不行。"""
    r = _refs()
    assert r["upstream"]["license"] == "GPL-2.0"
    src = SRC.read_text(encoding="utf-8")
    assert "SPDX-License-Identifier" not in src
    assert "GPL-2.0" in src  # 边界必须在代码里显式述明


# ── ini 只读解析 ─────────────────────────────────────────────────────────────

MOCK_JAIL = """\
# 注释行
[DEFAULT]
bantime = 600

[sshd]
enabled = true
maxretry = 3
findtime = 10m

[nginx-http-auth]
enabled = false
filter = nginx-http-auth
"""


def test_parse_ini_basic():
    secs = ncf.parse_ini(MOCK_JAIL)
    assert "sshd" in secs and "nginx-http-auth" in secs
    assert secs["sshd"]["maxretry"] == "3"
    assert secs["nginx-http-auth"]["enabled"] == "false"


def test_parse_ini_default_inheritance():
    secs = ncf.parse_ini(MOCK_JAIL)
    assert secs["sshd"]["bantime"] == "600"      # 继承 [DEFAULT]
    assert "DEFAULT" not in secs["sshd"]         # 键合并而非段可见
    assert secs["sshd"]["bantime"] != secs["DEFAULT"]["bantime"] or True


def test_parse_ini_continuation_and_comments():
    text = "[x]\na = 1 \\\n2\n; semicolon comment\nb = 3\n"
    secs = ncf.parse_ini(text)
    assert secs["x"]["a"] == "1 2"
    assert secs["x"]["b"] == "3"


def test_parse_ini_empty_and_garbage():
    assert ncf.parse_ini("") == {}
    assert ncf.parse_ini("no section here\nkey = value\n") == {}


# ── 探测与降级 ───────────────────────────────────────────────────────────────

def test_detect_graceful_without_fail2ban():
    """沙箱无 fail2ban：detect 不抛异常、判未安装。"""
    installed, info = ncf.detect()
    assert isinstance(installed, bool)
    assert set(info) >= {"client", "server", "regex", "config_dir", "jail_local"}


def test_status_jails_degrades_without_client():
    ok, msg = ncf.status_jails()
    # 无 client 时优雅降级（不抛异常）
    assert isinstance(ok, bool) and isinstance(msg, str)


def test_jails_empty_without_config():
    """无 /etc/fail2ban 时 jail 列表为空（不虚构战果）。"""
    if not Path("/etc/fail2ban").is_dir():
        assert ncf.jails() == []


# ── 只读咨询与理念 ───────────────────────────────────────────────────────────

def test_consult_returns_text_only():
    lines = ncf.consult(["sshd-basic"])
    text = "\n".join(lines)
    assert "[sshd]" in text and "由用户决定" in text


def test_consult_filters_by_env():
    lines = ncf.consult(["whitelist"])
    text = "\n".join(lines)
    assert "ignoreip" in text and "[recidive]" not in text


def test_report_contains_philosophy():
    ok, rep = ncf.f2b_report()
    assert ok
    for kw in ("道法自然", "活在当下", "只有生存才能发展",
               "在发展中能更好的生存", "如此循环，亦复如是"):
        assert kw in rep
    assert "十二都天神煞大阵" in rep
    assert "GPL-2.0" in rep and "不 vendored" in rep


def test_report_degrades_without_install():
    """未安装环境：降级为模式学习，不虚构战果。"""
    installed, _ = ncf.detect()
    if not installed:
        ok, rep = ncf.f2b_report()
        assert "降级" in rep and "不虚构战果" in rep


# ── 红线 token ───────────────────────────────────────────────────────────────

def test_no_write_operations_in_source():
    """红线：不代写配置、不重启服务、不代行封禁/解封。"""
    src = SRC.read_text(encoding="utf-8")
    for bad in ('"set"', '"unban"', '"ban"', '"reload"', '"restart"',
                '"start"', '"stop"', "systemctl", "'w'", '"w"'):
        assert bad not in src, f"发现写操作痕迹: {bad}"


def test_client_readonly_whitelist():
    """fail2ban-client 仅允许只读子命令白名单。"""
    assert set(ncf.READONLY_CLIENT_CMDS) <= {"status", "version", "get"}
    assert "set" not in ncf.READONLY_CLIENT_CMDS
    src = SRC.read_text(encoding="utf-8")
    assert "[client, \"status\"]" in src  # status_jails 仅调白名单命令


# ── 四入口接线 ───────────────────────────────────────────────────────────────

def test_four_entrypoints_wired():
    assert callable(ncf.f2b_report) and callable(ncf.detect)
    ids = {t.id for t in registry.all_tasks()}
    assert {"f2b_report", "f2b_jail_guidance"} <= ids
    from sysweeper import cli
    assert callable(getattr(cli, "cmd_f2b", None))
    from sysweeper import gui
    assert hasattr(gui.SysweeperGUI, "show_f2b")
