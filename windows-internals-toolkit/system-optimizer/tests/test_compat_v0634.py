"""v0.6.34「图形 + 兼容层 + 串联」回归测试。

三块：
1. **兼容层串联**（`native/compat.py`）：四层依赖模型、场景结论、
   **不适用 ≠ 已就绪**（本机 Linux 时 WSL 报告 ok 但正文是「未识别为 WSL」）。
2. **串联**（`linkage.path/reachable/longest_chain/chains_report`）：
   从「有边」升级到「能沿边走通」。
3. **图形**（`linkage.graph/layout/svg/ascii_graph`）：结构化图数据、分层布局、
   纯标准库生成的 SVG 与命令行 ASCII 图。
"""

from __future__ import annotations

import pytest

from sysweeper.native import compat, linkage, subsystems


# ── 一、兼容层串联 ────────────────────────────────────────────────────────
def test_compat_registered():
    """compat 已登记进统一清单，指向真实的零参只读报告。"""
    assert "compat" in subsystems.ALL_KEYS
    sub = subsystems.BY_KEY["compat"]
    assert sub.module == "compat" and sub.fn == "compat_report"
    assert sub.default_on is True
    assert callable(compat.compat_report)


def test_layer_scan_shape():
    """四层依赖模型：每层都有盘点项，每项带 key/label/ok/brief。"""
    scan = compat.layer_scan()
    assert len(scan) == 4, "应为四层：底座 / 设备与图形 / 兼容运行时 / 供给"
    for layer in scan:
        assert layer["layer"] and layer["items"]
        for it in layer["items"]:
            for field in ("key", "label", "ok", "brief"):
                assert field in it
            assert isinstance(it["ok"], bool)


def test_compat_chain_shape():
    """每个场景都给出 ready / missing / na 三态，而不是只有就绪与否。"""
    chains = compat.compat_chain()
    assert chains and len(chains) == len(compat.SCENARIOS)
    for c in chains:
        for field in ("scene", "entry", "deps", "missing", "na", "ready", "advice"):
            assert field in c
        assert c["ready"] == (not c["missing"] and not c["na"]), (
            "ready 必须等价于「既不缺层也不不适用」")


def test_na_is_not_ready(monkeypatch):
    """**不适用 ≠ 已就绪**：报告 ok=True 但正文明示不适用时，必须判 na。

    真实场景：本机 Linux 上 wsl_report 返回 ok=True，正文却是
    「未识别为 WSL 环境…其余维度不适用」——直接当就绪，结论就反了。
    """
    monkeypatch.setattr(
        compat, "_probe",
        lambda module, fn: (True, "未识别为 WSL 环境（/proc/version 不含 Microsoft）；"
                                 "其余维度不适用。"))
    chains = compat.compat_chain()
    assert chains, "即便全部不适用也要产出场景结论"
    for c in chains:
        assert c["ready"] is False, "正文明示不适用时不得判就绪"
        assert c["na"], "不适用必须落在 na 里，而不是 missing 里"


def test_compat_report_sections():
    ok, msg = compat.compat_report()
    assert isinstance(ok, bool)
    for seg in ("[第 1 层 · 宿主底座]", "[场景串联结论", "[串联链 · 谁依赖谁]", "[缺层指引"):
        assert seg in msg, f"报告缺段: {seg}"


def test_compat_capabilities_report():
    ok, msg = compat.capabilities_report()
    assert ok is True
    assert "四层依赖模型" in msg and "红线" in msg


# ── 二、串联：能沿联动轴走通 ──────────────────────────────────────────────
def test_series_kind_registered():
    """「串联」是本轮新增的联动性质，必须在白名单里。"""
    assert "串联" in linkage.KINDS


def test_compat_axes_present():
    """兼容层相关的串联轴两端都在清单里，且性质正确。"""
    known = set(subsystems.ALL_KEYS)
    wanted = {("arch", "compat"): "门控", ("kmod", "compat"): "门控",
              ("distro", "compat"): "供给", ("virtgpu", "compat"): "供给",
              ("compat", "proton"): "串联", ("compat", "dosbox"): "串联",
              ("compat", "wsl"): "串联", ("compat", "pkgmgr"): "串联"}
    got = {(ax.from_key, ax.to_key): ax.kind for ax in linkage.all_axes()}
    for pair, kind in wanted.items():
        assert pair[0] in known and pair[1] in known
        assert got.get(pair) == kind, f"{pair} 性质应为 {kind}，实为 {got.get(pair)}"


def test_path_arch_to_pkgmgr():
    """兼容层把 arch 与 pkgmgr 串成一条链（此前两者没有直接通路）。"""
    chain = linkage.path("arch", "pkgmgr")
    assert chain, "arch → pkgmgr 应可走通"
    assert chain[0].from_key == "arch"
    assert chain[-1].to_key == "pkgmgr"
    # 链路必须首尾相接
    for prev, nxt in zip(chain, chain[1:]):
        assert prev.to_key == nxt.from_key, "链路必须首尾相接"


def test_path_unknown_key_returns_empty():
    assert linkage.path("nope", "pkgmgr") == []
    assert linkage.path("arch", "nope") == []
    assert linkage.path("arch", "arch") == []  # 自己到自己不算链


def test_reachable_excludes_self_and_is_sorted():
    reach = linkage.reachable("linux")
    assert reach and "linux" not in reach
    assert reach == sorted(reach)


def test_longest_chain_is_a_real_chain():
    chain, hops = linkage.longest_chain()
    assert hops >= 2 and len(chain) == hops
    for prev, nxt in zip(chain, chain[1:]):
        assert prev.to_key == nxt.from_key


def test_chains_report_sections():
    ok, msg = linkage.chains_report()
    assert ok is True
    for seg in ("[最长串联链]", "[串联深度 Top", "[示范 · 兼容层四层串联]"):
        assert seg in msg, f"串联报告缺段: {seg}"


# ── 三、图形：结构化图数据 / 布局 / SVG / ASCII ───────────────────────────
def test_graph_shape():
    g = linkage.graph()
    for field in ("nodes", "edges", "layers"):
        assert field in g
    assert len(g["nodes"]) == len(subsystems.SUBSYSTEMS)
    assert g["edges"]
    for e in g["edges"]:
        for field in ("from", "to", "kind", "desc", "color"):
            assert field in e
        assert e["kind"] in linkage.KINDS
        assert e["color"].startswith("#")
    # 每个节点的层都必须在 layers 里（否则 GUI 分组会漏画）
    for n in g["nodes"]:
        assert n["layer"] in g["layers"]


def test_layout_covers_all_nodes():
    g = linkage.graph()
    pos = linkage.layout(g, 1000, 700)
    assert set(pos.keys()) == {n["key"] for n in g["nodes"]}
    for x, y in pos.values():
        assert 0 <= x <= 1000 and 0 <= y <= 700


def test_svg_is_wellformed():
    svg = linkage.svg()
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    assert str(len(linkage.graph()["nodes"])) in svg or "联动连轴图" in svg
    # 每种性质的颜色都要出现在图里（图例）
    for color in linkage.KIND_COLORS.values():
        assert color in svg


def test_ascii_graph_lists_layers():
    text = linkage.ascii_graph()
    g = linkage.graph()
    for layer in g["layers"][:3]:
        assert layer in text


# ── 四、回归：新增不得破坏既有的联通体检 ──────────────────────────────────
def test_no_isolated_or_dangling_after_compat():
    assert linkage.isolated() == [], "新增 compat 后不得出现孤岛"
    assert linkage.dangling() == [], "新增轴不得出现悬空端点"


@pytest.mark.parametrize("fn", [compat.compat_report, compat.capabilities_report,
                                linkage.linkage_report, linkage.chains_report])
def test_reports_return_bool_str(fn):
    ok, msg = fn()
    assert isinstance(ok, bool)
    assert isinstance(msg, str) and msg.strip()
