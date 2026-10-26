"""v0.6.30-31 新子系统「嵌入整体」验证：统一开关 + sysmap 总览。

验证 durability / remote / cert 三者已登记进 subsystems 单一事实源（因此自动进入
CLI --enable/--disable/--list-subsystems、subsystems 子命令、GUI 模块开关面板、
sysmap 系统总览），且登记的报告函数零参可调用、返回可归一化的 (ok, str)。
"""

import importlib
import sys

import pytest

sys.path.insert(0, "src/python")

from sysweeper.native import subsystems as ss  # noqa: E402
from sysweeper.native import sysmap  # noqa: E402

NEW_KEYS = ("durability", "remote", "cert")
EXPECTED = {
    "durability": ("设备长期使用保护", "durability", "durability_report"),
    "remote": ("远程接入审计", "remote", "remote_audit_report"),
    "cert": ("证书与加密", "cert", "cert_audit_report"),
}


def test_new_subsystems_registered():
    for key in NEW_KEYS:
        assert key in ss.ALL_KEYS, f"{key} 应登记进统一子系统清单"
        assert key in ss.BY_KEY, f"{key} 应可按 key 索引"


def test_new_subsystems_fields():
    for key, (label, module, fn) in EXPECTED.items():
        s = ss.BY_KEY[key]
        assert s.label == label, f"{key} 标签应为 {label}，实为 {s.label}"
        assert s.module == module, f"{key} 模块应为 {module}"
        assert s.fn == fn, f"{key} 报告函数应为 {fn}"
        assert s.default_on is True, f"{key} 默认应开启"


def test_new_subsystems_report_callable():
    """登记的报告函数必须零参可调用，且返回可归一化的 (bool, str)。"""
    for key in NEW_KEYS:
        s = ss.BY_KEY[key]
        mod = importlib.import_module("sysweeper.native." + s.module)
        fn = getattr(mod, s.fn)
        ok, msg = fn()                      # 零参调用
        assert isinstance(ok, bool), f"{key}.{s.fn} 应返回 bool"
        assert isinstance(msg, str), f"{key}.{s.fn} 应返回 str"


def test_sysmap_probes_include_new():
    """sysmap.PROBES 由清单派生，新子系统应自动出现在总览探测项里。"""
    labels = [p[1] for p in sysmap.PROBES]
    for key, (label, _m, _f) in EXPECTED.items():
        assert label in labels, f"sysmap 总览应含 {label}（{key}）"


def test_sysmap_relations_endpoints_exist():
    """新增关系边的两个端点必须都在清单里（否则 sysmap 画不出这条边）。"""
    known = {s.label for s in ss.SUBSYSTEMS}
    new_edges = [
        ("证书与加密", "远程接入审计"),
        ("证书与加密", "设备长期使用保护"),
        ("设备长期使用保护", "硬件本征"),
        ("设备长期使用保护", "网络接口/路由"),
        ("远程接入审计", "网络接口/路由"),
    ]
    pairs = {(a, b) for a, b, _r in sysmap.RELATIONS}
    for a, b in new_edges:
        assert (a, b) in pairs, f"sysmap 应含关系边 {a} → {b}"
        assert a in known and b in known, f"关系边端点 {a}/{b} 应在子系统清单中"


def test_list_subsystems_exposes_enabled_flag():
    """CLI/GUI 依赖 list_subsystems 的 enabled 字段驱动开关。"""
    rows = {r["key"]: r for r in ss.list_subsystems()}
    for key in NEW_KEYS:
        assert key in rows, f"{key} 应出现在 list_subsystems 输出"
        assert isinstance(rows[key]["enabled"], bool)


def test_sysmap_report_runs_with_new_subsystems():
    """总览报告能跑通，不因新增三个子系统而崩。"""
    ok, rep = sysmap.sysmap_report()
    assert isinstance(ok, bool)
    assert isinstance(rep, str)
    assert "设备长期使用保护" in rep
    assert "证书与加密" in rep
