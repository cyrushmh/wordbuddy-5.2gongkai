"""cnstd 子系统测试（v0.6.90）：国内标准资源知识库（14 源）+ 任务层 + 安全不变量。

知识库事实基础：14 个国内标准资源链接全部于 2026-10-25 逐只读抓取；
规模数字（强标 6188 / 推标 61615 / 行标 88751·76 行业 / 地标 49114）为
官方源检索日实测；JS 渲染未取到内容统一 needs_verify 挂牌，不臆造。
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

from sysweeper.native import cnstd as nc  # noqa: E402
from sysweeper import registry  # noqa: E402


REQUIRED_KEYS = {
    "openstd_platform", "std_samr_platform", "hbba_platform", "ccsa_platform",
    "htsfwb_platform", "spc_platform", "biaozhuns_platform", "modbus_specs",
    "mqtt_protocol", "open_standards_articles", "rfc_cn_translations",
}

OFFICIAL_KEYS = {"openstd_platform", "std_samr_platform", "hbba_platform",
                 "ccsa_platform", "htsfwb_platform"}


def test_meta_and_entries():
    meta = nc.meta()
    assert meta.get("sources_total") == 14
    assert meta.get("version", "").startswith("0000.0000.0000.0034")
    entries = nc.keys()
    assert set(entries) == REQUIRED_KEYS
    assert len(entries) == 11
    # 红线与分层元信息在场
    assert meta.get("redline") and meta.get("layering")


def test_schema_fields_complete():
    for key in nc.keys():
        e = nc.entry(key)
        for field in ("name", "org", "url", "protocols", "interfaces", "docs",
                      "summary", "advice"):
            assert e.get(field), (key, field)
        assert isinstance(e["protocols"], list) and len(e["protocols"]) >= 2
        assert isinstance(e["interfaces"], list) and len(e["interfaces"]) >= 1
        assert isinstance(e["docs"], list) and len(e["docs"]) >= 1
        assert e["url"].startswith("https://"), key


def test_layers_partition():
    official = {p["key"] for p in nc.official_platforms()}
    assert official == OFFICIAL_KEYS
    assert {p["key"] for p in nc.protocol_specs()} == {"modbus_specs", "mqtt_protocol"}
    assert {p["key"] for p in nc.third_party()} == {
        "spc_platform", "biaozhuns_platform", "rfc_cn_translations"}
    assert {p["key"] for p in nc.concept_layer()} == {"open_standards_articles"}


def test_key_facts_consistent():
    # 关键事实必须与 2026-10-25 官方源实测一致
    openstd = nc.entry("openstd_platform")
    assert "6188" in " ".join(openstd["protocols"])
    assert "61615" in " ".join(openstd["protocols"])
    std = nc.entry("std_samr_platform")
    assert "88751" in " ".join(std["protocols"])
    assert "49114" in " ".join(std["protocols"])
    modbus = nc.entry("modbus_specs")
    assert len(modbus["protocols"]) == 6  # 六规范
    hbba = nc.entry("hbba_platform")
    assert len(hbba.get("samples", [])) == 8  # 备案样本 8 条


def test_standards_count():
    c = nc.standards_count()
    assert c["gb_mandatory"] == 6188
    assert c["gb_recommended"] == 61615
    assert c["industry"] == 88751
    assert c["industry_fields"] == 76
    assert c["local"] == 49114
    assert c["openstd_samples"] == 20   # 两页各 10 条
    assert c["hbba_samples"] == 8
    assert c["modbus_specs"] == 6
    assert c["sources"] == 14
    assert c["entries"] == 11


def test_needs_verify_items():
    items = nc.needs_verify_items()
    assert len(items) == 7  # ccsa 2 + htsfwb 2 + biaozhuns 3
    for it in items:
        assert it["key"] in REQUIRED_KEYS
        assert "needs_verify" in it["item"] or it["item"]


def test_search():
    hits = nc.search("MQTT")
    assert any(h["key"] == "mqtt_protocol" for h in hits)
    hits = nc.search("openstd")
    assert any(h["key"] == "openstd_platform" for h in hits)
    assert nc.search("") == []
    assert nc.search("不存在的关键词xyz") == []


def test_reports_ok_and_contain_sections():
    ok, rep = nc.cnstd_report()
    assert ok is True
    assert "6188" in rep and "88751" in rep
    assert "needs_verify" in rep
    # 定位声明：只读、不代查、不代下载
    assert "只读知识库" in rep and "不代下载" in rep

    ok, guide = nc.cnstd_lookup_guide()
    assert ok is True
    assert "openstd" in guide and "hbba" in guide and "std.samr" in guide

    ok, proto = nc.cnstd_protocol_guide()
    assert ok is True
    assert "Modbus" in proto and "MQTT" in proto
    assert "V1.1b3" in proto  # 应用层规范版本选用建议


def test_doc_list_nonempty():
    docs = nc.cnstd_doc_list()
    assert isinstance(docs, list) and len(docs) > 0
    assert any("openstd_platform" in d for d in docs)
    assert any("openstd.samr.gov.cn" in d for d in docs)
    assert any("needs_verify" in d for d in docs)


def test_native_module_no_network_no_write():
    """安全不变量：国内标准知识库是纯本地只读消费——无网络、无文件写。"""
    src = open(os.path.join(os.path.dirname(nc.__file__), "cnstd.py"),
               encoding="utf-8").read()
    for banned in ("import socket", "import requests", "urllib", "http",
                   "open(", "subprocess"):
        assert banned not in src, banned


def test_tasks_registered():
    tasks = [t for t in registry.all_tasks() if t.id.startswith("cnstd_")]
    assert len(tasks) == 5
    ids = {t.id for t in tasks}
    assert "cnstd_standards_overview" in ids
    assert "cnstd_official_lookup" in ids
    assert "cnstd_protocol_specs" in ids
    assert "cnstd_third_party_caution" in ids
    assert "cnstd_concept_layer" in ids
    # 全部只读低风险、platform=any、standards 分类
    for t in tasks:
        assert t.platform == "any"
        assert t.risk == "low"
        assert t.standards, t.id
        assert t.category == "standards", t.id


def test_task_native_actions_resolvable():
    """任务的 native action 必须在 native 模块有对应零参函数。"""
    for t in registry.all_tasks():
        if not t.id.startswith("cnstd_"):
            continue
        for a in t.actions:
            if a.kind == "native":
                fn_name = a.command.split(".", 1)[1]
                assert hasattr(nc, fn_name), (t.id, fn_name)
                assert callable(getattr(nc, fn_name))


def test_dispatch_via_runner():
    """派发链路：runner._run_native 经 native 包 getattr 找到 cnstd（v0.6.90 缺口补齐）。"""
    from sysweeper.runner import _run_native
    ok, msg = _run_native("cnstd.cnstd_report")
    assert ok is True
    assert "6188" in msg


def test_subsystem_registered():
    from sysweeper.native import subsystems
    keys = {s.key for s in subsystems.SUBSYSTEMS}
    assert "cnstd" in keys
    entry = [s for s in subsystems.SUBSYSTEMS if s.key == "cnstd"][0]
    assert entry.module == "cnstd"
    assert hasattr(nc, entry.fn)


def test_standards_category_wired():
    """standards 分类正式注册：CATEGORIES/ORDER/STANDS 三处联动（v0.6.90）。"""
    from sysweeper.models import (CATEGORIES, CATEGORY_ORDER,
                                  category_standards, STANDARD_TIERS)
    assert "standards" in CATEGORIES
    assert CATEGORY_ORDER[-1] == "standards"
    st = category_standards("standards")
    assert st.get("doc")
    tiers = st.get("standards", {})
    assert set(tiers.keys()) == {t for t, _ in STANDARD_TIERS}
    assert any("openstd" in x for x in tiers["national"])
    assert any("RFC" in x for x in tiers["international"])
