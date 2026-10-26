"""v0.6.33「整合统合合并 + 联动连轴」回归测试。

覆盖两件事：
1. **合并**：此前有模块、无登记的六项（linux / snapshot / compress / fonts /
   鸿蒙 HDC / 鸿蒙设备）已进统一子系统清单，且指向真实存在的零参只读函数。
2. **联动**：联动轴两端合法、无悬空、无孤岛、尊重开关；报告与自检可跑。

测试纪律：开关相关用例一律 monkeypatch 配置落点到 tmp_path，绝不污染真实用户配置。
"""

from __future__ import annotations

import importlib

import pytest

from sysweeper.native import linkage, subsystems


# ── 一、合并：六项补齐登记 ────────────────────────────────────────────────
NEW_ITEMS = [
    ("linux", "linux", "linux_report"),
    ("snapshot", "snapshot", "snapshot_report"),
    ("compress", "compress", "compress_report"),
    ("fonts", "fonts", "text_normalize_report"),
    ("harmony_hdc", "harmony", "hdc_report"),
    ("harmony_device", "harmony", "device_report"),
]


@pytest.mark.parametrize("key,module,fn", NEW_ITEMS)
def test_new_items_registered(key, module, fn):
    """六项此前未登记的模块已进入统一清单，且指向真实可调用的函数。"""
    assert key in subsystems.ALL_KEYS, f"{key} 未登记进统一子系统清单"
    sub = subsystems.BY_KEY[key]
    assert sub.module == module and sub.fn == fn
    assert sub.default_on is True
    mod = importlib.import_module(f"sysweeper.native.{sub.module}")
    assert callable(getattr(mod, sub.fn, None)), f"{module}.{fn} 不存在或不可调用"


def test_registry_grew_to_at_least_60():
    """清单总数应包含新增六项（54 → 60）。"""
    assert len(subsystems.SUBSYSTEMS) >= 60
    assert len(set(subsystems.ALL_KEYS)) == len(subsystems.ALL_KEYS), "key 必须唯一"
    labels = [s.label for s in subsystems.SUBSYSTEMS]
    assert len(set(labels)) == len(labels), "label 必须唯一（sysmap 按 label 定位关系端点）"


def test_linux_and_snapshot_reports_callable():
    """两个新增零参聚合报告可直接调用，返回 (bool, str)。"""
    from sysweeper.native import linux, snapshot

    for fn in (linux.linux_report, snapshot.snapshot_report):
        ok, msg = fn()
        assert isinstance(ok, bool)
        assert isinstance(msg, str) and msg.strip()


# ── 二、联动：轴合法 / 无孤岛 / 无悬空 / 尊重开关 ─────────────────────────
def test_all_axes_endpoints_known():
    """每条联动轴的两端都必须在统一清单里（写错 key 会静默失效）。"""
    known = set(subsystems.ALL_KEYS)
    for ax in linkage.all_axes():
        assert ax.from_key in known, f"悬空起点: {ax.from_key}"
        assert ax.to_key in known, f"悬空终点: {ax.to_key}"


def test_axes_kind_in_known_set():
    """轴性质只允许五类，杜绝随手造词。"""
    for ax in linkage.all_axes():
        assert ax.kind in linkage.KINDS, f"未知性质: {ax.kind}"


def test_no_dangling_axes():
    assert linkage.dangling() == []


def test_no_isolated_subsystems():
    """孤岛清零：登记进清单的每一项都至少接入一条联动轴。"""
    assert linkage.isolated() == []


def test_degrees_cover_all_registered():
    deg = linkage.degrees()
    assert set(deg.keys()) == set(subsystems.ALL_KEYS)
    for k, d in deg.items():
        assert d["total"] == d["out"] + d["in"]


def test_linkage_stats_shape():
    st = linkage.linkage_stats()
    for field in ("subsystems", "axes_total", "axes_enabled", "by_kind",
                  "isolated", "dangling", "top", "degrees"):
        assert field in st
    assert st["axes_enabled"] <= st["axes_total"]
    assert sum(st["by_kind"].values()) == st["axes_enabled"]


def test_linkage_report_runs():
    ok, msg = linkage.linkage_report()
    assert ok is True
    for seg in ("[联动概览]", "[联动轴 · 谁喂给谁 / 谁管着谁]", "[孤岛检测 · 登记了但没接上的]",
                "[悬空轴自检 · 端点写错的]"):
        assert seg in msg, f"报告缺段: {seg}"


def test_capabilities_report_ok_when_clean():
    ok, msg = linkage.capabilities_report()
    assert ok is True, f"存在待修项（孤岛/悬空）: {msg}"
    assert "联通覆盖率" in msg


def test_enabled_axes_respect_switch(monkeypatch, tmp_path):
    """关掉一个子系统后，涉及它的联动轴不再生效（关闭项不参与联通）。"""
    cfg = tmp_path / "subsystems.json"
    monkeypatch.setattr(subsystems, "CONFIG_PATH", str(cfg))
    monkeypatch.setattr(subsystems, "CONFIG_DIR", str(tmp_path))

    before = len(linkage.enabled_axes())
    subsystems.set_enabled("linux", False)
    after = len(linkage.enabled_axes())
    assert after < before, "关闭 linux 后生效轴数应减少"
    assert all(ax.from_key != "linux" and ax.to_key != "linux"
               for ax in linkage.enabled_axes())

    subsystems.set_enabled("linux", True)
    assert len(linkage.enabled_axes()) == before


def test_sysmap_relations_endpoints_known():
    """sysmap 关系表两端 label 都能映射到清单 key（新增边也不能写错）。"""
    from sysweeper.native import sysmap

    l2k = {s.label: s.key for s in subsystems.SUBSYSTEMS}
    for a, b, _ in sysmap.RELATIONS:
        assert a in l2k, f"关系表起点 label 不在清单: {a}"
        assert b in l2k, f"关系表终点 label 不在清单: {b}"


def test_new_subsystems_appear_in_sysmap_probes():
    """补齐的六项要真的出现在 sysmap 总览探测项里（嵌入而非只登记）。"""
    from sysweeper.native import sysmap

    keys = {p[0] for p in sysmap.PROBES}
    for key, _m, _f in NEW_ITEMS:
        assert key in keys, f"{key} 未进入 sysmap 探测项"
