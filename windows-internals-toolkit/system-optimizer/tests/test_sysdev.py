"""从零造系统学习应用子系统测试（v0.6.89）：数据层 + 只读探针 + 任务层 + 接线。

只读不变量贯穿：不编译/运行被分析的第三方源码、不改 malloc 环境变量、
不 vendored 第三方源代码。
"""

from __future__ import annotations

import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.abspath(os.path.join(HERE, "..", "src", "python"))
if PKG_ROOT not in sys.path:
    sys.path.insert(0, PKG_ROOT)

from sysweeper.native import sysdev  # noqa: E402
from sysweeper.native import omni, subsystems  # noqa: E402
from sysweeper import registry  # noqa: E402

DATA = os.path.join(PKG_ROOT, "sysweeper", "data", "sysdev_docs.json")


def _load() -> dict:
    return json.load(open(DATA, encoding="utf-8"))


# ── 数据层：八主题知识库 ──
AXES = ("sysdev", "allocator_patterns", "compiler_pipeline", "hobby_os_bringup",
        "emulator_tables", "env_isolation", "service_api_workspace", "learning_method")


def test_docs_eight_themes():
    data = _load()
    for ax in AXES:
        assert ax in data, f"缺失主题: {ax}"
        for field in ("name", "org", "url", "protocols", "interfaces",
                      "docs", "summary", "advice"):
            assert field in data[ax], f"{ax} 缺字段 {field}"


@pytest.mark.parametrize("ax", AXES)
def test_theme_protocols_nonempty(ax):
    data = _load()
    assert len(data[ax]["protocols"]) >= 1
    assert len(data[ax]["advice"]) >= 1


# ── 事实核验：关键结论必须在知识库里留痕 ──
def test_warpalloc_facts_recorded():
    blob = json.dumps(_load()["allocator_patterns"], ensure_ascii=False)
    assert "prewalloc" in blob, "应记录预分配入口 prewalloc"
    assert "brk" in blob, "应记录 brk 系统调用取内存"
    assert "300" in blob, "应记录 README 自述的 25 次分配约 300 倍性能"
    assert "ptmalloc" in blob, "应记录对照对象 ptmalloc 与适用边界"


def test_license_boundary_recorded():
    blob = json.dumps(_load()["sysdev"], ensure_ascii=False)
    assert "MIT" in blob, "warpalloc 为 MIT"
    assert "BSD" in blob, "xinOS-old 为 BSD 风格声明"
    assert "保留所有权利" in blob, "无许可证仓库须标注默认保留所有权利"


def test_compiler_pipeline_four_stages():
    blob = json.dumps(_load()["compiler_pipeline"], ensure_ascii=False)
    for stage in ("IStream", "Tokenizer", "Parser", "Program"):
        assert stage in blob, f"编译器四段管线缺 {stage}"


def test_emulator_table_driven():
    blob = json.dumps(_load()["emulator_tables"], ensure_ascii=False)
    assert "opcodes.json" in blob, "ramenbox 指令表应留痕"
    assert "gen_ops.py" in blob, "表格生成器应留痕"
    assert "6502" in blob


# ── native 只读层 ──
def test_reference_and_reference_all():
    assert sysdev.reference_all().keys() == _load().keys()
    assert sysdev.reference("allocator_patterns")["name"]
    assert sysdev.reference("no_such_theme") == {}


def test_probe_toolchain_shape():
    ok, tools = sysdev.probe_toolchain()
    assert ok is True
    assert tools["found_n"] + len(tools["missing"]) == tools["total"]
    assert tools["total"] >= 8
    for row in tools["found"]:
        assert row["version"], "已找到的工具必须带版本串"
    for row in tools["missing"]:
        assert row["version"] == ""


def test_probe_malloc_env_readonly_shape():
    ok, env = sysdev.probe_malloc_env()
    assert ok is True
    names = {r["var"] for r in env["vars"]}
    assert "MALLOC_ARENA_MAX" in names
    assert "MALLOC_TRIM_THRESHOLD_" in names
    for r in env["vars"]:
        assert "value" in r  # 未设置时为空串，绝不代设


def test_probe_memory_footprint_readonly():
    fp = sysdev.probe_memory_footprint()
    # Linux 上应有 VmRSS；其他平台允许空 dict（只读，绝不注入）
    if fp:
        assert "VmRSS" in fp


def test_report_zero_arg_and_redlines():
    ok, rep = sysdev.sysdev_report()
    assert ok is True
    assert "红线" in rep
    assert "绝不编译/运行" in rep
    assert "绝不修改 malloc 环境变量" in rep
    assert "warpalloc" in rep


def test_doc_list_nonempty():
    lines = sysdev.sysdev_doc_list()
    assert len(lines) == len(AXES)


# ── 任务层与四入口接线 ──
def test_tasks_registered():
    ids = [t.id for t in registry.all_tasks() if t.id.startswith("sysdev_")]
    assert ids == ["sysdev_report", "sysdev_toolchain",
                   "sysdev_alloc", "sysdev_patterns"]


def test_tasks_all_readonly_low_risk():
    for t in registry.all_tasks():
        if t.id.startswith("sysdev_"):
            assert t.platform == "any"
            assert t.risk == "low"


def test_omni_wiring_complete():
    rows = {r["key"]: r for r in omni.wiring()}
    assert "sysdev" in rows, "sysdev 未登记进统一子系统清单"
    row = rows["sysdev"]
    assert row["wiring"] == {"cli": True, "gui": True, "task": True, "data": True}
    assert row["complete"] is True


def test_subsystem_registered():
    keys = {s.key for s in subsystems.SUBSYSTEMS}
    assert "sysdev" in keys
    s = [x for x in subsystems.SUBSYSTEMS if x.key == "sysdev"][0]
    assert s.module == "sysdev" and s.fn == "sysdev_report"
    assert s.version.startswith("0000.0000.0000.")
