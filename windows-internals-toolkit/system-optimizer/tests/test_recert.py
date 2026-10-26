"""WCET 续证 PDU 计分方案（recert_docs）最小冒烟验证。

覆盖：数据层完整性（双周期 / 10 活动分类 / 7 技术领域）、全局门槛、
单类查询归一化、封顶合计 > 周期下限（合规提示而非刷分）、诚实边界
（第 7 技术领域标注待核实、停办声明）。
"""

import sys
from pathlib import Path

sys.path.insert(0, "src/python")

from sysweeper.native import recert as rc  # noqa: E402


def test_info_and_status():
    info = rc.info()
    assert "WCET" in (info["certification"] or "")
    assert "停办" in (info["program_status"] or ""), "须诚实声明项目已停办"
    assert info["source_files"], "须登记来源 .xls"


def test_cycles_thresholds():
    cyc = rc.cycles()
    assert set(cyc.keys()) == {"3year", "5year"}
    assert cyc["3year"]["min_pdus"] == 60
    assert cyc["5year"]["min_pdus"] == 100
    req = rc.requirements()
    assert req["min_technical_areas_addressed"] == 3
    assert req["technical_areas_total"] == 7
    assert req["increment_hours"] == 0.25


def test_categories_complete_and_caps():
    cats = rc.categories()
    assert len(cats) == 10, "10 个活动分类（不含 Contact Info / READ FIRST）"
    keys = {c["key"] for c in cats}
    for k in ("work", "volunteering", "teaching", "publications", "training",
              "self_study", "license_cert", "conferences", "wcet_support",
              "member_rank"):
        assert k in keys
    # 每个分类双周期都有封顶
    for c in cats:
        assert c["cycle_cap"]["3year"] and c["cycle_cap"]["5year"]


def test_category_lookup_normalization():
    assert rc.category("work")["key"] == "work"
    assert rc.category("Work ").__class__.__name__ == "dict"  # sheet 名也能查
    assert rc.category("teaching")["cycle_cap"]["3year"] == 20
    assert rc.category("zzz") is None


def test_technical_areas_honest():
    areas = rc.technical_areas()
    assert len(areas) == 7
    assert any("待核实" in a for a in areas), "第 7 类须标注待核实，不臆造"
    assert any("RF and Propagation" in a for a in areas)


def test_max_attainable_exceeds_floor():
    # 各分类理论封顶合计须超过周期下限（合规提示，非刷分建议）
    ma3 = rc.max_attainable("3year")
    ma5 = rc.max_attainable("5year")
    assert sum(ma3.values()) > 60
    assert sum(ma5.values()) > 100
    assert ma3["work"] == 30 and ma5["work"] == 30


def test_validation_rules_present():
    rules = rc.validation_rules()
    assert any("60" in r or "100" in r for r in rules)
    assert rc.summary()
