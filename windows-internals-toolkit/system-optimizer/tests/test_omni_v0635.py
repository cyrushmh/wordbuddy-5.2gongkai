"""v0.6.35「全能全知」回归测试。

覆盖三件事：
1. **自述边界三层**：我知道什么（覆盖面/接线）、我知道我不知道什么（已知未知）、
   我不知道我不知道什么（无探针域声明）。
2. **接线判定不误报**：key→module→入口别名三级回退，共用入口
   （`netlink`/`mesh`/`kaihong`/`import`）不得被当成欠账。
3. **本轮补齐的入口真的补上了**：linux / compress / emergency 的命令与面板，
   compat 的任务与知识库，omni 的登记与入口。
"""

from __future__ import annotations

import pytest

from sysweeper.native import omni, subsystems


# ── 一、我知道什么：覆盖面与接线 ──────────────────────────────────────────
def test_wiring_covers_all_registered():
    rows = omni.wiring()
    assert len(rows) == len(subsystems.SUBSYSTEMS)
    for r in rows:
        for field in ("key", "label", "layer", "module", "domain", "wiring",
                      "missing", "complete"):
            assert field in r
        assert set(r["wiring"].keys()) == set(omni.WIRING_KINDS)
        assert r["complete"] == (not r["missing"])


def test_domains_group_every_item():
    doms = omni.domains()
    total = sum(len(v) for v in doms.values())
    assert total == len(subsystems.SUBSYSTEMS)
    for items in doms.values():
        for it in items:
            assert it["domain"]


def test_shared_entries_not_reported_as_missing():
    """共用入口不得误报：这几个 key 实际走的是别人的命令/面板。"""
    by_key = {r["key"]: r for r in omni.wiring()}
    for key in ("netauth", "reshare", "meshchat", "distcompute", "distjob",
                "importio", "harmony_hdc", "harmony_device"):
        assert key in by_key, f"{key} 未登记"
        row = by_key[key]
        # 走共用入口，CLI/GUI 至少应被判为已接（不再因找不到 cmd_<key> 而误报）
        if key in omni.ENTRY_ALIASES and "cli" in omni.ENTRY_ALIASES[key]:
            assert row["wiring"]["cli"] is True, f"{key} 的 CLI 共用入口被误报为缺失"
        if key in omni.ENTRY_ALIASES and "gui" in omni.ENTRY_ALIASES[key]:
            assert row["wiring"]["gui"] is True, f"{key} 的 GUI 共用入口被误报为缺失"


def test_blind_spots_shape():
    bs = omni.blind_spots()
    for b in bs:
        for field in ("key", "label", "domain", "missing", "remedies"):
            assert field in b
        assert len(b["missing"]) >= 2
        assert len(b["remedies"]) == len(b["missing"])


def test_blind_spots_threshold_respected():
    assert len(omni.blind_spots(4)) <= len(omni.blind_spots(2))


# ── 二、我不知道我不知道什么：无探针域的边界声明 ──────────────────────────
def test_unknown_domains_declared():
    ud = omni.unknown_domains()
    assert ud
    for u in ud:
        for field in ("domain", "state", "reason", "remedy"):
            assert field in u and u[field]
    # 敏感维度必须被显式声明为「不采集」，而不是默默没有
    joined = " ".join(u["domain"] for u in ud)
    for must in ("生物识别", "定位", "摄像头", "文件"):
        assert must in joined, f"边界声明缺了：{must}"


def test_coverage_report_sections():
    ok, msg = omni.coverage_report()
    assert ok is True
    for seg in ("[一 · 能力覆盖面]", "[二 · 接线完整度", "[三 · 半截能力"):
        assert seg in msg


def test_omni_report_three_layers():
    ok, msg = omni.omni_report(deep=False)
    assert ok is True
    assert "[第一层 · 我知道什么]" in msg
    assert "[第二层 · 我知道我不知道什么" in msg
    assert "[第三层 · 我不知道我不知道什么" in msg
    assert "边界声明" in msg
    # 未 deep 时不应实跑
    assert "未实跑" in msg


def test_capabilities_report_ok():
    ok, msg = omni.capabilities_report()
    assert ok is True
    assert "登记能力" in msg and "无探针域" in msg


# ── 三、本轮补齐的入口 ────────────────────────────────────────────────────
@pytest.mark.parametrize("key,need", [
    ("linux", ("cli", "gui")),
    ("compress", ("cli", "gui")),
    ("emergency", ("cli",)),
    ("edge", ("gui",)),
    ("compat", ("task", "data")),
    ("omni", ("cli", "gui")),
])
def test_this_round_wired(key, need):
    """v0.6.35 补齐的入口必须真的被判定为已接（否则等于没补）。"""
    by_key = {r["key"]: r for r in omni.wiring()}
    assert key in by_key, f"{key} 未登记进统一清单"
    row = by_key[key]
    for kind in need:
        assert row["wiring"][kind] is True, f"{key} 的 {kind} 入口仍未接上"


def test_omni_registered_and_callable():
    assert "omni" in subsystems.ALL_KEYS
    sub = subsystems.BY_KEY["omni"]
    assert sub.module == "omni" and sub.fn == "omni_report"
    assert callable(omni.omni_report)


def test_compat_tasks_registered():
    from sysweeper import registry
    ids = {t.id for t in registry.all_tasks()}
    assert "compat_report" in ids
    assert "compat_windows_guide" in ids


def test_compat_docs_json_loadable():
    import json
    import pathlib
    p = pathlib.Path("src/python/sysweeper/data/compat_docs.json")
    assert p.is_file()
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d
    for key, item in d.items():
        for field in ("name", "org", "url", "protocols", "interfaces", "docs",
                      "summary", "advice"):
            assert field in item, f"{key} 缺字段 {field}"


# ── 四、回归：新增 omni 不得破坏联通体检 ──────────────────────────────────
def test_no_isolated_or_dangling():
    from sysweeper.native import linkage
    assert linkage.isolated() == [], "新增 omni 后不得出现孤岛"
    assert linkage.dangling() == []


def test_omni_has_axes():
    from sysweeper.native import linkage
    pairs = {(a.from_key, a.to_key) for a in linkage.all_axes()}
    assert ("subsystems", "omni") in pairs
    assert ("omni", "linkage") in pairs


# ── 五、zipapp 内不得误报：包内读取必须走 importlib.resources（v0.6.70） ──
def test_pkg_reads_go_through_resources_not_pathlib():
    """v0.6.70 修：wiring() 曾用 pathlib 直读包内文本，.pyz 里 sysweeper.__file__
    指向 zip 内部路径，read_text/glob/is_file 全部失效——82 项全被误报成
    半截能力。守住：_read/_has_file/_data_files 三件套在磁盘与 zip 下同结论。"""
    from sysweeper.native import omni
    # 包内源码文本读得到且长得像 cli.py
    assert "def cmd_omni" in omni._read("cli.py")
    assert "def show_quantum" in omni._read("gui.py")
    # 文件存在性：真实存在与不存在都不能误判
    assert omni._has_file("tasks/quantum.py")
    assert omni._has_file("data/quantum.json")
    assert not omni._has_file("tasks/__no_such_task__.py")
    # data 前缀枚举（原 glob 逻辑）
    assert "quantum.json" in omni._data_files("quantum")
    assert "kernel_docs.json" in omni._data_files("kernel")
    assert omni._data_files("__no_such_key__") == []


def test_wiring_identical_from_resources_api():
    """接线结果与「按 resources 视图重算一遍」一致（防实现漂移回 pathlib）。"""
    from sysweeper.native import omni, subsystems
    rows = {r["key"]: r for r in omni.wiring()}
    for s in subsystems.SUBSYSTEMS:
        # task 接线的判据就是「包内 tasks/<key>.py 或 tasks/<module>.py 存在」
        expect = (omni._has_file(f"tasks/{s.key}.py")
                  or omni._has_file(f"tasks/{s.module}.py"))
        if expect:
            assert rows[s.key]["wiring"]["task"] is True, (
                f"{s.key} 的 task 文件在包内存在，接线却判 False")
