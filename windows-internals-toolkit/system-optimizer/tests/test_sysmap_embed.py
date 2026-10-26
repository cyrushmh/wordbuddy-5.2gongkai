"""sysmap 全量嵌入测试（v0.6.22）。

验证：sysmap 由统一清单驱动（不再硬编码零散子集）、关闭的子系统不诊断不展示、
关联图只画两端均已开启的耦合。
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

from sysweeper.native import subsystems, sysmap  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_config(tmp_path, monkeypatch):
    """隔离配置落点，避免污染真实用户配置。"""
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(subsystems, "CONFIG_DIR", str(cfg_dir))
    monkeypatch.setattr(subsystems, "CONFIG_PATH", str(cfg_dir / "subsystems.json"))
    yield


def _only(*keys):
    """只开启指定 key（其余全关）——让 sysmap_report 跑得快，避开全量 49 项的耗时。"""
    for s in subsystems.SUBSYSTEMS:
        subsystems.set_enabled(s.key, s.key in keys)


def test_sysmap_driven_by_registry():
    """总览编排项与清单登记项一一对应（默认全开时全量嵌入）。"""
    assert len(sysmap.PROBES) == len(subsystems.SUBSYSTEMS)
    assert {(p[0], p[1]) for p in sysmap.PROBES} == {
        (s.key, s.label) for s in subsystems.SUBSYSTEMS}


def test_sysmap_report_renders_all_enabled_subsystems():
    """默认全开：48 个子系统的标签都应出现在总览局部状态里。"""
    ok, msg = sysmap.sysmap_report()
    assert isinstance(ok, bool) and isinstance(msg, str) and msg
    for s in subsystems.SUBSYSTEMS:
        assert s.label in msg, f"总览未嵌入已开启子系统：{s.label}"


def test_disabled_subsystem_not_diagnosed_nor_shown(monkeypatch):
    """关闭：既不诊断（函数不被调用）也不展示（标签不出现）。"""
    _only("tor")
    called = []
    monkeypatch.setattr(
        "sysweeper.native.tor.tor_report",
        lambda: (called.append(1), (True, "x"))[1])
    ok, msg = sysmap.sysmap_report()
    assert "Tor 覆盖层" in msg, "已开启却未展示"
    assert called == [1], "已开启却未被诊断"

    called.clear()
    _only()  # 全部关闭
    ok, msg = sysmap.sysmap_report()
    assert "Tor 覆盖层" not in msg, "已关闭的子系统仍在展示"
    assert called == [], "已关闭的子系统仍被诊断（不该调用其报告函数）"


def test_relations_only_when_both_ends_enabled():
    """关联图只画两端均已开启的耦合；关掉一端后该条消失。"""
    _only("network", "dnshealth")
    ok, msg = sysmap.sysmap_report()
    assert "网络接口/路由 ↔ DNS 解析" in msg, "两端均开启，该耦合应画出"

    _only("network")  # 关掉 dnshealth
    ok, msg = sysmap.sysmap_report()
    assert "网络接口/路由 ↔ DNS 解析" not in msg, "一端已关闭，该耦合不该再画"


def test_relations_reference_registered_labels():
    """每条关系的两端都必须能在清单里查到（否则永远画不出来）。"""
    known = {s.label for s in subsystems.SUBSYSTEMS}
    for a, b, _ in sysmap.RELATIONS:
        assert a in known, f"关系端点不在清单：{a}"
        assert b in known, f"关系端点不在清单：{b}"


def test_toggle_status_line_present():
    """总览须给出开关状态行，让用户看见当前嵌入/关闭了几项。"""
    total = len(subsystems.SUBSYSTEMS)
    _only("network")
    ok, msg = sysmap.sysmap_report()
    assert "已登记子系统" in msg and "已开启" in msg
    assert f"已开启 1" in msg and f"已关闭 {total - 1}" in msg, (
        f"开关状态行未反映实际开关：\n{msg[:300]}")
