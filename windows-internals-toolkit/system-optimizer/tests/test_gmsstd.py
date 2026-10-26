"""gmsstd 子系统测试（v0.6.71）：GMS 标准知识库 + 上架自查清单 + 安全不变量。

知识库事实基础：15 条事实 = 10 条 GMS/Play 标准（除 STS 细节外全部经官方源实检，
source.android.google.cn / developer.android.com / play.google.com，2026-10 检索日；
STS 官方单页未实检到，其细节为社区整理并逐条标注 needs_verify）
+ 5 条 HarmonyOS 设备侧 GMS 部署实战（源自 to-alan/HarmonyOSInstallGMS 社区教程，
2024-05 最后更新，逐条标注 needs_verify）。"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

from sysweeper.native import gmsstd as ng  # noqa: E402
from sysweeper import registry  # noqa: E402


#: 官方标准 10 条（官方源实检口径）
REQUIRED_STD_KEYS = {
    "cdd", "cts_suite", "vts_suite", "sts_suite", "gms_compat_licensing",
    "play_integrity_api", "play_app_signing", "play_target_api",
    "play_data_safety", "security_bulletin_patching",
}

#: HarmonyOS 设备侧 GMS 部署实战 5 条（社区源，needs_verify）
REQUIRED_DEPLOY_KEYS = {
    "gms_packages_map", "harmonyos_gms_deploy", "microg_fallback",
    "fcm_push_keepalive", "adb_multi_user_control",
}

REQUIRED_KEYS = REQUIRED_STD_KEYS | REQUIRED_DEPLOY_KEYS


def test_refs_loaded_15():
    refs = ng.reference_all()
    assert set(refs) == REQUIRED_KEYS
    assert len(refs) == 15


def test_schema_fields_complete():
    for key, ref in ng.reference_all().items():
        for field in ("name", "org", "url", "protocols", "interfaces", "docs",
                      "summary", "advice"):
            assert ref.get(field), (key, field)
        assert isinstance(ref["protocols"], list) and len(ref["protocols"]) >= 3
        assert isinstance(ref["interfaces"], list) and len(ref["interfaces"]) >= 1
        assert isinstance(ref["docs"], list) and len(ref["docs"]) >= 1


def test_reference_lookup():
    ref = ng.reference("play_target_api")
    assert "targetSdk" in ref["name"] or "API" in ref["name"]
    assert ng.reference("不存在的key") == {}


def test_key_facts_consistent():
    # 关键事实必须与官方源实检一致（2026-10 检索日口径）
    target = ng.reference("play_target_api")
    joined = " ".join(target["protocols"])
    assert "Android 16" in joined and "API level 36" in joined
    assert "Android 15" in joined and "API level 35" in joined
    pi = ng.reference("play_integrity_api")
    pi_text = " ".join(pi["protocols"])
    for tag in ("PLAY_RECOGNIZED", "LICENSED", "MEETS_STRONG_INTEGRITY",
                "MEETS_DEVICE_INTEGRITY", "MEETS_BASIC_INTEGRITY", "10,000"):
        assert tag in pi_text, tag
    signing = ng.reference("play_app_signing")
    sign_text = " ".join(signing["protocols"])
    assert "2048" in sign_text and "4096" in sign_text and "2021-08-01" in sign_text
    ds = ng.reference("play_data_safety")
    assert "2021 年 5 月" in " ".join(ds["protocols"])
    cts = ng.reference("cts_suite")
    assert "CTS Verifier" in " ".join(cts["protocols"])


def test_sts_is_marked_unverified():
    # 诚实边界：官方单页未实检到的 STS 条目必须显式标注 needs_verify
    sts = ng.reference("sts_suite")
    text = " ".join(sts["org"].split()) + " " + " ".join(sts["protocols"])
    assert "needs_verify" in text or "未实检" in sts["org"]
    docs_text = " ".join(sts["docs"])
    assert "needs_verify" in docs_text or "社区整理" in docs_text


def test_checklist_rationale_resolves():
    refs = ng.reference_all()
    for c in ng.gms_compliance_checklist():
        assert c["rationale"] in refs, c
        assert c["severity"] in ("info", "notice", "warn")
        assert c["action_type"] == "guidance"


def test_checklist_count():
    assert len(ng.gms_compliance_checklist()) == len(ng.GMS_CHECKS) >= 15


def test_deploy_entries_marked_unverified():
    # 诚实边界：HarmonyOS 设备侧部署实战 5 条为社区源，必须逐条标注 needs_verify
    for key in REQUIRED_DEPLOY_KEYS:
        ref = ng.reference(key)
        text = " ".join(ref["org"].split()) + " " + " ".join(ref["protocols"])
        assert "needs_verify" in text or "社区" in ref["org"], key


def test_report_ok_and_contains_sections():
    ok, rep = ng.gms_compliance_report()
    assert ok is True
    assert "GMS" in rep
    assert "Play" in rep
    # 定位声明与行动渠道必须入报告（诚实边界）
    assert "不是认证" in rep and "不代审" in rep
    assert "判定权" in rep


def test_report_lists_all_checks_with_rationale():
    _, rep = ng.gms_compliance_report()
    for c in ng.gms_compliance_checklist():
        assert c["title"] in rep
        assert c["rationale"] in rep


def test_doc_list_nonempty():
    lines = ng.gmsstd_doc_list()
    assert len(lines) >= 50
    assert any("play_integrity" in x for x in lines)


def test_native_module_no_network_no_write():
    src = open(ng.__file__, encoding="utf-8").read()
    for bad in ("requests", "urllib", "socket", "subprocess", "os.system",
                "eval(", "exec("):
        assert bad not in src, bad


def test_tasks_registered():
    ids = {t.id for t in registry.all_tasks()}
    for tid in ("gmsstd_compat_overview", "gmsstd_play_integrity",
                "gmsstd_play_signing", "gmsstd_target_sdk",
                "gmsstd_data_safety"):
        assert tid in ids, tid
    assert len({t for t in ids if t.startswith("gmsstd_")}) == 5


def test_task_native_actions_resolvable():
    for t in registry.all_tasks():
        if not t.id.startswith("gmsstd_"):
            continue
        for a in t.actions:
            if a.kind == "native":
                fn_name = a.command.split(".", 1)[1]
                assert hasattr(ng, fn_name), (t.id, fn_name)
                assert callable(getattr(ng, fn_name))


def test_subsystem_registered():
    from sysweeper.native.subsystems import BY_KEY, SUBSYSTEMS
    sub = BY_KEY.get("gmsstd")
    assert sub is not None
    assert sub.fn == "gms_compliance_report"
    # native 入口零参可调（omni 接线判定依赖）
    _, rep = getattr(ng, sub.fn)()
    assert "GMS" in rep
    keys = {s.key for s in SUBSYSTEMS}
    assert {"androidstd", "gmsstd", "fdroidstd"} <= keys
