"""系统基座子系统测试（v0.6.88）：数据层五轴 + 只读探针 + 任务层 + 接线。

只读不变量贯穿：不安装/卸载、不动仓库源与密钥、不启动 msfconsole、不写系统目录。
"""

from __future__ import annotations

import json
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.abspath(os.path.join(HERE, "..", "src", "python"))
if PKG_ROOT not in __import__("sys").path:
    __import__("sys").path.insert(0, PKG_ROOT)


# ── 数据层：五轴知识库 ──
def test_sysbase_docs_five_axes():
    p = os.path.join(PKG_ROOT, "sysweeper", "data", "sysbase_docs.json")
    data = json.load(open(p, encoding="utf-8"))
    for ax in ("system_layout", "package_formats", "network_repos", "msf_distro", "path_namespace"):
        assert ax in data, f"缺失轴: {ax}"
        for field in ("name", "org", "url", "protocols", "interfaces", "docs", "summary", "advice"):
            assert field in data[ax], f"{ax} 缺字段 {field}"


@pytest.mark.parametrize("ax", ["system_layout", "package_formats", "network_repos", "msf_distro", "path_namespace"])
def test_axis_protocols_nonempty(ax):
    data = json.load(open(os.path.join(PKG_ROOT, "sysweeper", "data", "sysbase_docs.json"), encoding="utf-8"))
    assert len(data[ax]["protocols"]) >= 1


# ── 概念课落点：相对路径 + 互联网即目录服务 ──
def test_path_namespace_concepts():
    data = json.load(open(os.path.join(PKG_ROOT, "sysweeper", "data", "sysbase_docs.json"), encoding="utf-8"))
    pns = data["path_namespace"]
    blob = json.dumps(pns, ensure_ascii=False)
    assert "相对路径" in blob, "path_namespace 应含「相对路径」机理"
    assert "目录服务" in blob, "path_namespace 应含「目录服务」概念"


# ── 原生探针：纯函数与探测（只读）──
def test_parse_deb_version():
    from sysweeper.native import sysbase
    v = "6.5.3~20260818061200~1rapid7-1"
    res = sysbase.parse_deb_version(v)
    assert res["upstream"] == "6.5.3"
    assert res["nightly"] == "20260818061200"
    assert res["packager"] == "1rapid7"
    assert res["revision"] == "1"


def test_parse_deb_version_no_tilde():
    from sysweeper.native import sysbase
    res = sysbase.parse_deb_version("6.5.3-1")
    assert res["upstream"] == "6.5.3"
    assert res["revision"] == "1"
    assert res["nightly"] == ""


def test_sysbase_report_readonly_runs():
    """sysbase_report 端到端只读运行（本机 msf 已装，应给出路径判定）。"""
    from sysweeper.native import sysbase
    ok, msg = sysbase.sysbase_report()
    assert ok is True
    assert "系统基座" in msg
    assert "安全不变量" in msg
    # 报告含安全不变量声明（只读红线），且给出 Metasploit 安装路径判定
    assert "Metasploit" in msg
    # 报告只是描述性文本：出现的是「不安装/不写」这类红线声明，而非任何真实改动动作
    assert "不启动 msfconsole" in msg


def test_msf_version_report_runs():
    from sysweeper.native import sysbase
    ok, msg = sysbase.msf_version_report()
    assert ok is True


# ── 任务层：六个任务齐全 + 红线注解 ──
def test_tasks_present():
    from sysweeper.tasks import sysbase as ts
    ids = {t.id for t in ts.TASKS}
    for tid in ("sysbase_report", "sysbase_layout", "sysbase_pkgmgr",
                "sysbase_netrepo", "sysbase_msf_detect", "sysbase_path_concept"):
        assert tid in ids, f"缺失任务: {tid}"


def test_tasks_readonly_risk():
    from sysweeper.tasks import sysbase as ts
    for t in ts.TASKS:
        assert t.risk == "low", f"{t.id} 风险应为 low（只读）"
        # 没有任何任务要求 --apply 之外的高危动作；红线以 manual/native 描述呈现
        assert t.platform == "any"


# ── 接线：registry / subsystems / models / ergonomics ──
def test_registry_wires_sysbase():
    from sysweeper import registry
    ids = {t.id for t in registry.all_tasks() if t.id.startswith("sysbase_")}
    assert len(ids) == 6, f"registry 应含 6 个 sysbase_ 任务，实得 {sorted(ids)}"


def test_subsystems_registers_sysbase():
    from sysweeper.native import subsystems
    keys = {s.key for s in subsystems.SUBSYSTEMS}
    assert "sysbase" in keys, "subsystems.SUBSYSTEMS 应登记 sysbase"


def test_models_keyword_standards_sysbase():
    from sysweeper import models
    # KEYWORD_STANDARDS 是模块级元组
    keys = [k for k, _ in getattr(models, "KEYWORD_STANDARDS", [])]
    assert "sysbase" in keys, "models.KEYWORD_STANDARDS 应含 sysbase 条目"


def test_linkage_bridges_sysbase():
    from sysweeper.native import linkage
    keys = {a.from_key for a in linkage.all_axes()}
    assert "sysbase" in keys, "linkage 应含以 sysbase 为源的轴（概念系统桥接）"


def test_ergonomics_entry():
    from sysweeper import ergonomics
    all_cmds = []
    for scene in ergonomics.SCENES:
        all_cmds.extend(scene["commands"])
    assert "sysbase" in all_cmds, "ergonomics 场景应含 sysbase 入口"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
