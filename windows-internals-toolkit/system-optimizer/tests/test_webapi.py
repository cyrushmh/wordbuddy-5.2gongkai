"""统一 JSON 接口层（webapi）测试（v0.6.26）。

覆盖六类：
1. 白名单与红线：未知动作拒绝；白名单里**绝不存在**改系统类动作；
   只读标记与 handler 实际性质一致。
2. 派发健壮性：缺 action / 坏 JSON / 子系统炸了都转成 ok=false，永不抛。
3. 参数与阈值链路：set → 留痕 → 单项复位 → 全部复位（隔离用户配置）。
4. 子系统与诊断：开关、单子系统只读诊断、快照报告结构。
5. 档位 / 量化评分 / 内核模块：只读视图的形状、取值边界、只读标记。
6. JSONL 长连接：一行进一行出，空行跳过，坏行不断连。
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "python"))

from sysweeper import webapi as wa  # noqa: E402
from sysweeper.native import settings as st  # noqa: E402
from sysweeper.native import subsystems as subs  # noqa: E402


@pytest.fixture()
def _isolated(tmp_path, monkeypatch):
    """把配置与留痕指到临时目录，清空观察者，避免污染用户真实配置。"""
    monkeypatch.setattr(st, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(st, "CONFIG_PATH", str(tmp_path / "settings.json"))
    monkeypatch.setattr(st, "HISTORY_PATH", str(tmp_path / "settings-history.json"))
    monkeypatch.setattr(subs, "CONFIG_PATH", str(tmp_path / "subsystems.json"))
    st.reload()
    st._LISTENERS.clear()
    yield tmp_path


# ── 1. 白名单与红线 ───────────────────────────────────────────────────────────
def test_unknown_action_rejected():
    r = wa.dispatch({"action": "clean.apply"})
    assert r["ok"] is False
    assert "未知动作" in r["error"]


def test_no_system_writing_action_in_allowlist():
    """红线：白名单里绝不允许出现清理/应用/启停服务类动作。"""
    banned = ("clean", "apply", "optimize", "exec", "eval", "run", "write",
              "delete", "install", "uninstall", "service", "reboot", "shutdown")
    for name in wa.ACTIONS:
        low = name.lower()
        for b in banned:
            assert b not in low, f"白名单出现可疑动作: {name}（含 {b}）"


def test_manifest_lists_all_and_flags_readonly():
    r = wa.dispatch({"action": "manifest"})
    assert r["ok"] is True
    names = {a["action"] for a in r["data"]["actions"]}
    assert names == set(wa.ACTIONS)
    for a in r["data"]["actions"]:
        assert isinstance(a["readonly"], bool)
        assert a["desc"]
    # 写配置类动作必须显式标 readonly=False，绝不混进只读堆里
    assert wa.ACTIONS["settings.set"][1] is False
    assert wa.ACTIONS["diagnose"][1] is True
    assert wa.ACTIONS["sysmap"][1] is True


# ── 2. 派发健壮性 ─────────────────────────────────────────────────────────────
def test_missing_action_and_bad_params():
    assert wa.dispatch({})["ok"] is False
    assert wa.dispatch({"action": "settings.get"})["ok"] is False  # 缺 key
    assert wa.dispatch({"action": "settings.get", "params": {"key": "nope"}})["ok"] is False
    r = wa.dispatch("not a dict")  # type: ignore[arg-type]
    assert r["ok"] is False


def test_dispatch_never_raises_on_broken_subsystem(_isolated, monkeypatch):
    """单个子系统报告函数炸了 → 该项标「异常」，接口本身仍 ok。"""
    monkeypatch.setattr(subs, "SUBSYSTEMS", [subs.Subsystem(
        "boom", "炸药桶", "测试", "settings", "nonexistent_fn_xyz")])
    monkeypatch.setattr(subs, "BY_KEY", {s.key: s for s in subs.SUBSYSTEMS})
    r = wa.dispatch({"action": "diagnose", "params": {"keys": ["boom"]}})
    assert r["ok"] is True
    assert r["data"]["items"][0]["status"] == "异常"


# ── 3. 参数与阈值链路 ─────────────────────────────────────────────────────────
def test_settings_roundtrip_with_history(_isolated):
    r = wa.dispatch({"action": "settings.set",
                     "params": {"pairs": {"cmd.timeout": 300, "bogus.key": 1},
                                "note": "测试写入"}})
    assert r["ok"] is True
    ok_rows = [x for x in r["data"]["results"] if x["ok"]]
    bad_rows = [x for x in r["data"]["results"] if not x["ok"]]
    assert [x["key"] for x in ok_rows] == ["cmd.timeout"]
    assert [x["key"] for x in bad_rows] == ["bogus.key"]
    assert r["data"]["changed"] == ["cmd.timeout"]

    h = wa.dispatch({"action": "settings.history", "params": {"limit": 10}})
    assert h["data"]["rows"], "写入必须有留痕"
    row = h["data"]["rows"][-1]
    assert row["changes"]["cmd.timeout"] == {"from": 120, "to": 300}
    # 值未变的重复写入不应再产生留痕
    before = len(h["data"]["rows"])
    wa.dispatch({"action": "settings.set", "params": {"pairs": {"cmd.timeout": 300}}})
    assert len(wa.dispatch({"action": "settings.history"})["data"]["rows"]) == before

    # 单项复位
    r2 = wa.dispatch({"action": "settings.reset_one", "params": {"key": "cmd.timeout"}})
    assert r2["data"]["value"] == 120
    assert r2["data"]["changed"] == []
    # 全部复位
    wa.dispatch({"action": "settings.set", "params": {"pairs": {"scan.limit": 77}}})
    r3 = wa.dispatch({"action": "settings.reset"})
    assert r3["data"]["values"]["scan.limit"] == 10


def test_settings_list_reports_changed(_isolated):
    wa.dispatch({"action": "settings.set", "params": {"pairs": {"qr.camera_index": 3}}})
    d = wa.dispatch({"action": "settings.list"})["data"]
    assert "qr.camera_index" in d["changed"]
    item = next(x for x in d["items"] if x["key"] == "qr.camera_index")
    assert item["value"] == 3
    assert item["apply"], "每个参数必须登记真实生效点"


# ── 4. 子系统与诊断 ───────────────────────────────────────────────────────────
def test_subsystems_toggle_via_api(_isolated):
    r = wa.dispatch({"action": "subsystems.set", "params": {"key": "tor", "on": False}})
    assert r["ok"] is True and r["data"]["enabled"] is False
    item = next(x for x in r["data"]["items"] if x["key"] == "tor")
    assert item["enabled"] is False
    assert wa.dispatch({"action": "subsystems.set",
                        "params": {"key": "nope"}})["ok"] is False
    r2 = wa.dispatch({"action": "subsystems.set_many",
                      "params": {"pairs": {"kernel": False, "wsl": True, "ghost": True}}})
    assert set(r2["data"]["applied"]) == {"kernel", "wsl"}
    assert r2["data"]["rejected"] == ["ghost"]


def test_diagnose_single_and_tally(_isolated):
    r = wa.dispatch({"action": "diagnose", "params": {"keys": ["settings"], "max_chars": 500}})
    assert r["ok"] is True
    it = r["data"]["items"][0]
    assert it["key"] == "settings"
    assert it["status"] in ("正常", "提示", "不适用", "异常")
    assert it["truncated"] is True  # 500 上限必然截断
    assert r["data"]["tally"].get(it["status"], 0) >= 1


def test_report_build_structure(_isolated):
    rep = wa.build_report(include=["host", "settings", "history", "subsystems"], max_chars=800)
    assert rep["schema"] == wa.REPORT_SCHEMA
    assert rep["generated_at"] and rep["version"]
    assert "host" in rep and "settings" in rep and "subsystems" in rep
    assert rep["subsystems"]["enabled"] + rep["subsystems"]["disabled"] == subs.ALL_KEYS
    assert "diagnose" not in rep  # 未请求就不跑，省时间
    r = wa.dispatch({"action": "report.build",
                     "params": {"include": "host,settings", "max_chars": 800}})
    assert r["ok"] is True
    assert r["data"]["schema"] == wa.REPORT_SCHEMA


# ── 5. 档位 / 量化评分 / 内核模块（只读视图）──────────────────────────────────
def test_profiles_list_and_counts_ascend():
    d = wa.dispatch({"action": "profiles.list",
                     "params": {"platform": "linux", "version": "24.04"}})["data"]
    names = [x["name"] for x in d["profiles"]]
    assert names == ["minimal", "lite", "standard", "full"]
    counts = [x["count"] for x in d["profiles"]]
    assert counts == sorted(counts) and counts[0] > 0
    assert d["scenarios"] and all("base" in s for s in d["scenarios"])


def test_profiles_show_shape_and_unknown_rejected():
    d = wa.dispatch({"action": "profiles.show",
                     "params": {"name": "minimal", "platform": "linux",
                                "version": "24.04", "limit": 3}})["data"]
    assert d["count"] > 0 and len(d["ids"]) == d["count"]
    assert len(d["tasks"]) == 3
    assert d["rule"]["max_risk"] == "low" and d["rule"]["include_opt_in"] is False
    bad = wa.dispatch({"action": "profiles.show", "params": {"name": "nope"}})
    assert bad["ok"] is False and "未知档位" in bad["error"]


def test_profiles_compare_reports_subset():
    d = wa.dispatch({"action": "profiles.compare",
                     "params": {"name": "minimal", "against": "full",
                                "platform": "linux", "version": "24.04"}})["data"]
    assert d["count_a"] < d["count_b"]
    assert d["only_a_count"] == 0, "minimal 必须是 full 的子集"
    assert 0.0 < d["jaccard"] < 1.0
    assert wa.dispatch({"action": "profiles.compare",
                        "params": {"name": "minimal", "against": "nope"}})["ok"] is False


def test_score_overview_bounds_and_components():
    d = wa.dispatch({"action": "score.overview",
                     "params": {"platform": "linux", "version": "24.04"}})["data"]
    assert d["total_tasks"] > 0
    assert 0.0 <= d["global_score"] <= 1.0
    assert d["gaps"] == [] or isinstance(d["gaps"], list)
    parts = d["global_parts"]
    assert set(parts) == {"breadth", "entropy", "depth", "safety"}
    for v in parts.values():
        assert 0.0 <= v <= 1.0
    # 权重之和为 1，否则总分不代表「加权平均」
    from sysweeper.native import metrics as mt
    assert sum(mt.SCORE_WEIGHTS.values()) > 0.99
    assert 0.0 <= d["normalized_entropy"] <= 1.0
    assert isinstance(d["profile_counts"], dict)
    assert "text" in d and d["text"]


def test_kmod_report_via_api_is_readonly_and_statused():
    d = wa.dispatch({"action": "kmod.report", "params": {"max_chars": 2000}})["data"]
    assert d["status"] in ("正常", "提示", "不适用", "异常")
    assert isinstance(d["environment"], list) and d["environment"]
    assert d["docs"], "必须给出 kernel.org 文档出处"
    assert d["forbidden"], "必须明确列出不执行的高危命令"
    assert d["readonly_only"] is True
    # 状态与摘要必须一致：有可读探针就按比例给，没有就明说
    if "/" in (d["summary"] or ""):
        a, total = d["summary"].split("/")[0], d["summary"].split("/")[1].split()[0]
        assert 0 <= int(a) <= int(total)


def test_report_includes_score_and_kmod_sections(_isolated):
    rep = wa.build_report(include=["host", "score", "kmod"], max_chars=1200)
    assert "diagnose" not in rep, "未请求就不跑重诊断"
    assert rep["score"]["total_tasks"] > 0
    assert rep["kmod"]["status"] in ("正常", "提示", "不适用", "异常")
    assert isinstance(rep["kmod"]["text"], str)


def test_new_actions_all_marked_readonly():
    """三件套在接口层只暴露读视图——任何一条被标成可写都是红线。"""
    for name in ("profiles.list", "profiles.show", "profiles.compare",
                 "score.overview", "kmod.report"):
        meta = wa.ACTIONS[name]
        assert meta[1] is True, f"{name} 必须是只读动作"
        r = wa.dispatch({"action": name})
        assert r["ok"] is True and r["readonly"] is True


# ── 6. JSONL 长连接 ───────────────────────────────────────────────────────────
def test_run_loop_line_protocol(_isolated):
    stdin = io.StringIO(
        '{"action":"ping"}\n'
        '\n'                             # 空行跳过
        'not-json\n'                     # 坏行只回错误，不断连
        '{"action":"settings.get","params":{"key":"cmd.timeout"}}\n'
    )
    out = io.StringIO()
    rc = wa.run_loop(stdin, out)
    assert rc == 0
    lines = [l for l in out.getvalue().splitlines() if l.strip()]
    assert len(lines) == 3
    r1, r2, r3 = (json.loads(l) for l in lines)
    assert r1["ok"] is True and r1["action"] == "ping"
    assert r2["ok"] is False and "JSON" in r2["error"]
    assert r3["ok"] is True and r3["data"]["value"] == 120
    for l in lines:
        assert "\n" not in l, "响应必须单行（JSONL 协议）"


def test_dispatch_text_single_line(_isolated):
    s = wa.dispatch_text('{"action":"manifest"}')
    assert s.count("\n") == 0
    assert json.loads(s)["data"]["actions"]


def test_cli_webapi_once(_isolated, capsys):
    from sysweeper import webapi
    assert webapi.main(["--once", '{"action":"ping"}']) == 0
    out = capsys.readouterr().out
    assert json.loads(out)["ok"] is True
