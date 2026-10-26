"""hmos_ecosystem 子系统测试（v0.6.71）：鸿蒙生态知识库 + 评估自检清单 + 安全不变量。

知识库事实基础：8 条 = HAP 工程/侧载工具链/生态版图/版本关系/开发工具链/IoT
（Zitann/HarmonyOS-Haps 与 fenwii/OpenHarmony 社区整理源，needs_verify）
+ 官方 Codelabs 构建块图谱（git tree 实测）+ FA→Stage 范式演进（三方综合）。
双边范式：codelabs=FA（config.json/pageAbility），Haps 生态=Stage（module.json5）。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

from sysweeper.native import hmos_ecosystem as nh  # noqa: E402
from sysweeper import registry  # noqa: E402


REQUIRED_KEYS = {
    "hap_packaging", "sideload_toolchain", "next_ecosystem_landscape",
    "harmony_vs_openharmony", "dev_toolchain", "devboards_and_iothru",
    "codelabs_building_blocks", "fa_stage_evolution",
}

#: 社区整理源条目（org 须含 needs_verify 或 社区）
COMMUNITY_KEYS = set(REQUIRED_KEYS)


def test_refs_loaded_8():
    refs = nh.reference_all()
    assert set(refs) == REQUIRED_KEYS
    assert len(refs) == 8


def test_schema_fields_complete():
    for key, ref in nh.reference_all().items():
        for field in ("name", "org", "url", "protocols", "interfaces", "docs",
                      "summary", "advice"):
            assert ref.get(field), (key, field)
        assert isinstance(ref["protocols"], list) and len(ref["protocols"]) >= 3
        assert isinstance(ref["interfaces"], list) and len(ref["interfaces"]) >= 1
        assert isinstance(ref["docs"], list) and len(ref["docs"]) >= 1


def test_reference_lookup():
    ref = nh.reference("hap_packaging")
    assert "HAP" in ref["name"]
    assert nh.reference("不存在的key") == {}


def test_paradigm_facts_consistent():
    # 双边范式关键事实必须与实测口径一致
    fa = nh.reference("fa_stage_evolution")
    fa_text = " ".join(fa["protocols"])
    for tag in ("config.json", "pageAbility", "module.json5", "UIAbility", "hml"):
        assert tag in fa_text, tag
    cb = nh.reference("codelabs_building_blocks")
    cb_text = " ".join(cb["protocols"])
    assert "53" in cb_text and "DISTRIBUTED_DATASYNC" in cb_text
    eco = nh.reference("next_ecosystem_landscape")
    assert "110" in " ".join(eco["protocols"])


def test_community_marked_unverified():
    # 诚实边界：社区整理源必须标注 needs_verify 或 社区
    for key in COMMUNITY_KEYS:
        ref = nh.reference(key)
        text = " ".join(ref["org"].split())
        assert "needs_verify" in text or "社区" in text, key


def test_harmonyos_version_line_facts():
    line = nh.reference("harmony_vs_openharmony")
    text = " ".join(line["protocols"])
    assert "NEXT" in text and "AOSP" in text
    assert "OpenHarmony" in text and "发行" in text


def test_checklist_rationale_resolves():
    refs = nh.reference_all()
    for c in nh.hmos_compliance_checklist():
        assert c["rationale"] in refs, c
        assert c["severity"] in ("info", "notice", "warn")
        assert c["action_type"] == "guidance"


def test_checklist_count():
    assert len(nh.hmos_compliance_checklist()) == len(nh.HMOS_CHECKS) >= 8


def test_report_ok_and_contains_sections():
    ok, rep = nh.hmos_ecosystem_report()
    assert ok is True
    assert "HarmonyOS" in rep and "HAP" in rep
    # 定位声明必须入报告（诚实边界）
    assert "不代执行" in rep and "判定权" in rep


def test_report_lists_all_checks_with_rationale():
    _, rep = nh.hmos_ecosystem_report()
    for c in nh.hmos_compliance_checklist():
        assert c["title"] in rep
        assert c["rationale"] in rep


def test_doc_list_nonempty():
    lines = nh.hmos_doc_list()
    assert len(lines) >= 32  # 8 条 × 4 行
    assert any("codelabs_building_blocks" in x for x in lines)


def test_native_module_no_network_no_write():
    src = open(nh.__file__, encoding="utf-8").read()
    for bad in ("requests", "urllib", "socket", "subprocess", "os.system",
                "eval(", "exec("):
        assert bad not in src, bad


def test_tasks_registered():
    ids = {t.id for t in registry.all_tasks()}
    for tid in ("hmoseco_overview", "hmoseco_version_line", "hmoseco_sideload"):
        assert tid in ids, tid
    assert len({t for t in ids if t.startswith("hmoseco_")}) == 3


def test_task_native_actions_resolvable():
    for t in registry.all_tasks():
        if not t.id.startswith("hmoseco_"):
            continue
        for a in t.actions:
            if a.kind == "native":
                fn_name = a.command.split(".", 1)[1]
                assert hasattr(nh, fn_name), (t.id, fn_name)
                assert callable(getattr(nh, fn_name))


def test_subsystem_registered():
    from sysweeper.native.subsystems import BY_KEY
    sub = BY_KEY.get("hmos_ecosystem")
    assert sub is not None
    assert sub.fn == "hmos_ecosystem_report"
    # native 入口零参可调（omni 接线判定依赖）
    _, rep = getattr(nh, sub.fn)()
    assert "HarmonyOS" in rep


def test_cli_counts_are_dynamic_not_hardcoded():
    """CLI 计数必须引用数据层实况，不许写死数字——v0.6.71 连环修出两处假计数
    （hmos_ecosystem「6 条」实为 8 条；gmsstd「10 条」实为 15 条）。
    本条守「回灌后忘改 CLI 字面量」这类漂移，同模式扫描全仓相关计数行。"""
    cli = open(Path(__file__).resolve().parents[1] / "src" / "python" /
               "sysweeper" / "cli.py", encoding="utf-8").read()
    # 两处已接入动态引用：ENTRY_KEYS / REFS 的 len()
    assert "len(nh.ENTRY_KEYS)" in cli
    assert "len(ng.REFS)" in cli
    # 旧假计数字面量不得复回 CLI 源码
    for dead in ("：6 条，", "gmsstd_standards.json：10 条"):
        assert dead not in cli, dead
    # native 数据实况与 CLI 打印口径一致（间接）：REFS/ENTRY_KEYS 即真值
    assert len(nh.ENTRY_KEYS) == len(nh.REFS) - sum(
        1 for k in nh.REFS if k.startswith("_"))
