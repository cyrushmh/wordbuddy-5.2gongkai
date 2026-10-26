"""fdroidstd 子系统测试（v0.6.67）：F-Droid 标准知识库 + 分发自查清单 + 安全不变量。

知识库事实基础：10 条 F-Droid 标准事实经 GitHub/GitLab API（f-droid/fdroidclient
GPL-3.0、f-droid/fdroiddata）与官方文档检索快照实检（2026-10；f-droid.org 直连
不可达，官方中文/韩文文档取检索快照）。"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

from sysweeper.native import fdroidstd as nf  # noqa: E402
from sysweeper import registry  # noqa: E402


REQUIRED_KEYS = {
    "fdroid_repo_model", "inclusion_policy", "anti_features",
    "build_metadata", "reproducible_builds", "client_and_repo_proto",
    "gms_independence", "fdroid_vs_play", "security_signing",
    "fdroid_client_build",
}


def test_refs_loaded_10():
    refs = nf.reference_all()
    assert set(refs) == REQUIRED_KEYS
    assert len(refs) == 10


def test_schema_fields_complete():
    for key, ref in nf.reference_all().items():
        for field in ("name", "org", "url", "protocols", "interfaces", "docs",
                      "summary", "advice"):
            assert ref.get(field), (key, field)
        assert isinstance(ref["protocols"], list) and len(ref["protocols"]) >= 3
        assert isinstance(ref["interfaces"], list) and len(ref["interfaces"]) >= 1
        assert isinstance(ref["docs"], list) and len(ref["docs"]) >= 1


def test_reference_lookup():
    ref = nf.reference("fdroid_repo_model")
    assert "F-Droid" in ref["name"]
    assert nf.reference("不存在的key") == {}


def test_key_facts_consistent():
    # 关键事实必须与实检一致（GitHub/GitLab API + 官方文档检索快照，2026-10）
    model = nf.reference("fdroid_repo_model")
    assert "无需注册账号" in model["protocols"][0] or "without registering" in model["protocols"][0]
    policy = nf.reference("inclusion_policy")
    assert "FLOSS" in policy["protocols"][1]
    anti = nf.reference("anti_features")
    joined = " ".join(anti["protocols"])
    for tag in ("Ads", "Tracking", "NonFreeNet", "NonFreeDep", "Known Vulnerability"):
        assert tag in joined, tag
    client = nf.reference("fdroid_client_build")
    assert "GPL-3.0" in client["protocols"][0] and "3222" in client["org"]


def test_checklist_rationale_resolves():
    refs = nf.reference_all()
    for c in nf.fdroid_compliance_checklist():
        assert c["rationale"] in refs, c
        assert c["severity"] in ("info", "notice", "warn")
        assert c["action_type"] == "guidance"


def test_checklist_count():
    assert len(nf.fdroid_compliance_checklist()) == len(nf.FDROID_CHECKS) >= 8


def test_report_ok_and_contains_sections():
    ok, rep = nf.fdroid_compliance_report()
    assert ok is True
    assert "F-Droid" in rep
    assert "收录" in rep or "分发" in rep
    # 定位声明与行动渠道必须入报告（诚实边界）
    assert "不是认证" in rep and "不代分发" in rep
    assert "判定权" in rep


def test_report_lists_all_checks_with_rationale():
    _, rep = nf.fdroid_compliance_report()
    for c in nf.fdroid_compliance_checklist():
        assert c["title"] in rep
        assert c["rationale"] in rep


def test_doc_list_nonempty():
    lines = nf.fdroidstd_doc_list()
    assert len(lines) >= 50
    assert any("fdroidstd_standards.json" in x or "F-Droid" in x for x in lines)


def test_native_module_no_network_no_write():
    src = open(nf.__file__, encoding="utf-8").read()
    for bad in ("requests", "urllib", "socket", "subprocess", "os.system",
                "open(", "eval(", "exec("):
        assert bad not in src, bad


def test_tasks_registered():
    ids = {t.id for t in registry.all_tasks()}
    for tid in ("fdroidstd_channel_overview", "fdroidstd_inclusion_selfcheck",
                "fdroidstd_reproducible_build", "fdroidstd_repo_protocol",
                "fdroidstd_channel_matrix"):
        assert tid in ids, tid
    assert len({t for t in ids if t.startswith("fdroidstd_")}) == 5


def test_task_native_actions_resolvable():
    for t in registry.all_tasks():
        if not t.id.startswith("fdroidstd_"):
            continue
        for a in t.actions:
            if a.kind == "native":
                fn_name = a.command.split(".", 1)[1]
                assert hasattr(nf, fn_name), (t.id, fn_name)
                assert callable(getattr(nf, fn_name))


def test_subsystem_registered():
    from sysweeper.native.subsystems import BY_KEY, SUBSYSTEMS
    sub = BY_KEY.get("fdroidstd")
    assert sub is not None
    assert sub.fn == "fdroid_compliance_report"
    # native 入口零参可调（omni 接线判定依赖）
    _, rep = getattr(nf, sub.fn)()
    assert "F-Droid" in rep
    keys = {s.key for s in SUBSYSTEMS}
    assert {"androidstd", "gmsstd", "fdroidstd"} <= keys
