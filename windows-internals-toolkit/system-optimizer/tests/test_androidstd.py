"""androidstd 子系统测试（v0.6.67）：国内标准知识库 + 合规检查清单 + 安全不变量。

知识库事实基础：14 条国内标准/法规全部经官方源实检（openstd.samr.gov.cn /
cac.gov.cn / miit.gov.cn / gov.cn / tc260.org.cn，2026-10 检索日）。"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

from sysweeper.native import androidstd as na  # noqa: E402
from sysweeper import registry  # noqa: E402


REQUIRED_KEYS = {
    "pipl", "gb_t_35273_pi_spec", "gb_t_41391_app_collection",
    "gb_t_42574_notice_consent", "gb_t_34975_app_software_sec",
    "four_dept_violation_criteria", "necessary_pi_scope",
    "app_info_service_rule", "app_filing", "minor_online_regulation",
    "minor_mode_guide", "tc260_app_self_assess", "tc260_permission_guide",
    "gb_t_45574_sensitive_pi",
}


def test_refs_loaded_14():
    refs = na.reference_all()
    assert set(refs) == REQUIRED_KEYS
    assert len(refs) == 14


def test_schema_fields_complete():
    for key, ref in na.reference_all().items():
        for field in ("name", "org", "url", "protocols", "interfaces", "docs",
                      "summary", "advice"):
            assert ref.get(field), (key, field)
        assert isinstance(ref["protocols"], list) and len(ref["protocols"]) >= 3
        assert isinstance(ref["interfaces"], list) and len(ref["interfaces"]) >= 1
        assert isinstance(ref["docs"], list) and len(ref["docs"]) >= 1


def test_reference_lookup():
    ref = na.reference("pipl")
    assert "个人信息保护法" in ref["name"]
    assert na.reference("不存在的key") == {}


def test_key_facts_consistent():
    # 关键事实必须与官方源实检一致（2026-10 检索日口径）
    pip = na.reference("pipl")
    assert "2021-11-01" in pip["org"]
    gb35273 = na.reference("gb_t_35273_pi_spec")
    assert "现行" in gb35273["name"] or "代替" in gb35273["org"]
    assert "2020-10-01" in gb35273["org"]
    filing = na.reference("app_filing")
    assert "2023-07" in filing["org"]
    minor = na.reference("minor_online_regulation")
    assert "766" in minor["org"] and "2024-01-01" in minor["org"]


def test_checklist_rationale_resolves():
    # 每条检查项回链的知识库 key 必须真实存在（建议有出处）
    for c in na.app_compliance_checklist():
        assert c["rationale"] in REQUIRED_KEYS, c
        assert c["action_type"] == "guidance"
        assert c["severity"] in ("info", "notice", "warn")


def test_checklist_count():
    assert len(na.app_compliance_checklist()) == len(na.APP_CHECKS)
    assert len(na.APP_CHECKS) >= 10


def test_report_ok_and_contains_sections():
    ok, rep = na.androidstd_compliance_report()
    assert ok is True
    assert isinstance(rep, str)
    assert "国内标准" in rep
    # 定位声明：不代执法、不代申诉
    assert "不是合规认证" in rep and "不代执法" in rep and "不代申诉" in rep
    # 行动渠道
    assert "12321" in rep
    # 清单条目出现（报告列出每项 title 与其依据 key）
    checks = na.app_compliance_checklist()
    assert any(c["title"] in rep and c["rationale"] in rep for c in checks)


def test_report_lists_all_checks_with_rationale():
    ok, rep = na.androidstd_compliance_report()
    for c in na.app_compliance_checklist():
        assert c["rationale"] in rep


def test_doc_list_nonempty():
    docs = na.androidstd_doc_list()
    assert isinstance(docs, list) and len(docs) > 0
    assert any("gb_t_35273_pi_spec" in d for d in docs)
    assert any("openstd.samr.gov.cn" in d for d in docs)


def test_native_module_no_network_no_write():
    """安全不变量：国内标准知识库是纯本地只读消费——无网络、无文件写。"""
    src = open(os.path.join(os.path.dirname(na.__file__), "androidstd.py"),
               encoding="utf-8").read()
    for banned in ("import socket", "import requests", "urllib", "http",
                   "open(", "subprocess"):
        assert banned not in src, banned


def test_tasks_registered():
    tasks = [t for t in registry.all_tasks() if t.id.startswith("androidstd_")]
    assert len(tasks) == 5
    ids = {t.id for t in tasks}
    assert "androidstd_standards_overview" in ids
    # 全部只读低风险、platform=any
    for t in tasks:
        assert t.platform == "any"
        assert t.risk == "low"
        assert t.standards, t.id
        assert t.category == "privacy", t.id


def test_task_native_actions_resolvable():
    """任务的 native action 必须在 native 模块有对应零参/默认参函数。"""
    for t in registry.all_tasks():
        if not t.id.startswith("androidstd_"):
            continue
        for a in t.actions:
            if a.kind == "native":
                fn_name = a.command.split(".", 1)[1]
                assert hasattr(na, fn_name), (t.id, fn_name)
                assert callable(getattr(na, fn_name))


def test_subsystem_registered():
    from sysweeper.native import subsystems
    keys = {s.key for s in subsystems.SUBSYSTEMS}
    assert "androidstd" in keys
    entry = [s for s in subsystems.SUBSYSTEMS if s.key == "androidstd"][0]
    assert entry.module == "androidstd"
    assert hasattr(na, entry.fn)
