"""hmosstd 子系统测试（v0.6.72）：HarmonyOS 标准与合规知识库 + 对照清单 + 安全不变量。

知识库事实基础：11 条 = PIPL 上位法 / AppGallery 上架 / App 备案 / 权限 APL 分级 /
隐私指示器 / HUKS 密钥库 / 加解密框架·证书·TEE / API 版本兼容 / 未成年人保护 /
后台与网络规范 / XTS 兼容测试。
分工基线：hmosstd 对齐 androidstd/gmsstd/fdroidstd 三库范式（法规+官方源口径），
与 hmos_ecosystem（工程/生态知识）互补；社区整理源逐条 needs_verify。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

from sysweeper.native import hmosstd as nh  # noqa: E402
from sysweeper import registry  # noqa: E402


REQUIRED_KEYS = {
    "pipl_harmony", "appgallery_listing", "app_filing_miit", "permission_apl_model",
    "privacy_indicators", "huki_key_management", "crypto_cert_tee",
    "api_version_compat", "minor_protection", "background_network_std", "xts_app_testing",
}

#: 需要标注 needs_verify 的社区整理/口径易变条目
NEEDS_VERIFY = {"appgallery_listing", "privacy_indicators", "api_version_compat",
                "minor_protection", "xts_app_testing"}


def test_refs_loaded_11():
    refs = nh.reference_all()
    assert set(refs) == REQUIRED_KEYS
    assert len(refs) == 11


def test_schema_fields_complete():
    for key, ref in nh.reference_all().items():
        for field in ("name", "org", "url", "protocols", "interfaces", "docs",
                      "advice"):
            assert field in ref, (key, field)


def test_official_urls_present():
    """法规原文与官方源域名在位（npc/miit/developer.huawei.com/gitee）。"""
    hosts = ("npc.gov.cn", "beian.miit.gov.cn", "developer.huawei.com",
             "gitee.com", "gov.cn", "consumer.huawei.com", "docs.openharmony.cn")
    for key, ref in nh.reference_all().items():
        assert any(h in ref["url"] for h in hosts), (key, ref["url"])


def test_community_sources_marked_unverified():
    """官方口径易变的条目，docs 内至少一条 needs_verify。"""
    for key in NEEDS_VERIFY:
        ref = nh.reference(key)
        assert any(d.get("needs_verify") for d in ref["docs"]), key


def test_self_position_boundary():
    """诚实边界：不代审、不代申诉、不下合规结论。"""
    for phrase in ("不代审", "判定权"):
        assert phrase in nh._SELF_POSITION, phrase


def test_checks_link_to_refs():
    """每条检查项回链真实知识库 key（建议有出处）。"""
    for cid, (kb, _title, sev) in nh.HMOSSTD_CHECKS.items():
        assert kb in REQUIRED_KEYS, (cid, kb)


def test_checklist_counts():
    cl = nh.hmosstd_compliance_checklist()
    assert len(cl) == len(nh.HMOSSTD_CHECKS) == 12
    assert all(c["action_type"] == "guidance" for c in cl)
    assert all(c["severity"] in ("info", "notice", "warn") for c in cl)


def test_report_zero_arg_callable():
    ok, rep = nh.hmosstd_compliance_report()
    assert ok is True
    for seg in ("PIPL", "HUKS", "AppGallery", "备案", "不代审"):
        assert seg in rep, seg
    assert "判定权" in rep


def test_doc_list_lines():
    lines = nh.hmosstd_doc_list()
    assert len(lines) >= 44  # 11 条 × 4 行
    assert any("pipl_harmony" in ln for ln in lines)


def test_no_network_in_layer():
    src = open(nh.__file__, encoding="utf-8").read()
    for bad in ("requests", "urllib", "http.client", "socket.",
                "eval(", "exec(", "subprocess"):
        assert bad not in src, bad


def test_tasks_registered():
    ids = {t.id for t in registry.all_tasks()}
    for tid in ("hmosstd_overview", "hmosstd_listing_privacy",
                "hmosstd_security_baseline"):
        assert tid in ids, tid
    assert len({t for t in ids if t.startswith("hmosstd_")}) == 3


def test_task_native_actions_resolvable():
    for t in registry.all_tasks():
        if not t.id.startswith("hmosstd_"):
            continue
        for a in t.actions:
            if a.kind == "native":
                fn_name = a.command.split(".", 1)[1]
                assert hasattr(nh, fn_name), (t.id, fn_name)
                assert callable(getattr(nh, fn_name))


def test_subsystem_registered():
    from sysweeper.native.subsystems import BY_KEY
    sub = BY_KEY.get("hmosstd")
    assert sub is not None
    assert sub.fn == "hmosstd_compliance_report"
    # native 入口零参可调（omni 接线判定依赖）
    _, rep = getattr(nh, sub.fn)()
    assert "PIPL" in rep
