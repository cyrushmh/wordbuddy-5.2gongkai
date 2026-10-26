"""packages 子系统测试：包管理器检测 / 四类操作规范审计 / 端到端报告 / 任务注册。"""
from __future__ import annotations

import json
import os

from sysweeper.native import packages as ncf
from sysweeper.tasks import packages as tcf


def _data_path():
    return os.path.join(os.path.dirname(ncf.__file__), "..", "data", "packages_docs.json")


def test_knowledge_base_loads():
    raw = open(_data_path(), encoding="utf-8").read()
    data = json.loads(raw)
    for mgr in ("apt", "dnf", "pacman", "brew", "winget", "choco", "apk", "scoop", "zypper"):
        assert mgr in data, f"缺少包管理器规范 {mgr}"
        for op in ("install", "uninstall", "configure", "optimize"):
            assert op in data[mgr], f"{mgr} 缺操作 {op}"
            assert data[mgr][op].get("spec") and data[mgr][op].get("tier")


def test_detect_pkgmgr_tuple():
    ok, info = ncf.detect_pkgmgr()
    assert isinstance(ok, bool)
    assert "managers" in info and "primary" in info
    assert isinstance(info["managers"], list)


def test_audit_operation_known_compliant():
    res = ncf.audit_operation("apt", "install")
    assert res[0]["compliant"] is True
    assert res[0]["tier"]
    assert res[0]["action_type"] == "guidance"


def test_audit_operation_unknown_generic():
    res = ncf.audit_operation("does_not_exist", "install")
    assert res[0]["compliant"] is None
    assert res[0]["tier"] == "generic_guidance"


def test_audit_package_four_ops():
    res = ncf.audit_package("dnf", "nginx")
    ops = {a["op"] for a in res}
    assert ops == {"install", "uninstall", "configure", "optimize"}


def test_packages_report_markers():
    ok, rep = ncf.packages_report([])
    assert ok is True
    assert "软件包规范审计" in rep
    assert "四类操作层级应对" in rep
    assert "安全不变量" in rep
    # 显式包管理器也能产出
    ok2, rep2 = ncf.packages_report(["apt"], {"pkgmgr": {"primary": "apt", "managers": ["apt"], "os_id": "ubuntu"}})
    assert ok2 and "apt" in rep2


def test_tasks_registered():
    ids = {t.id for t in tcf.TASKS}
    assert {"packages_report", "packages_install_guidance", "packages_uninstall_guidance",
            "packages_configure_guidance", "packages_optimize_guidance"} <= ids
    for t in tcf.TASKS:
        assert t.risk == "low"
        assert t.platform == "any"
