"""组网通信（meshchat）与分布式计算（distcompute）测试。

纪律同其它测试：**临时目录 + 假数据**，不真发包、不真连网、不拖慢机器。
每条断言对着"协议正确性"或"写死的安全边界"，不对着实现细节。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "python"))

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _tmp_config(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from sysweeper.native import meshchat
    meshchat.inbox_clear()
    yield
    meshchat.inbox_clear()


# ============================================================ 协议编解码

def test_encode_decode_roundtrip():
    from sysweeper.native import meshchat as m
    pkt, cmd = m.build_send("你好，飞鸽", want_receipt=True)
    d = m.ipmsg_decode(pkt)
    assert d["extra"] == "你好，飞鸽"
    assert d["mode"] == m.C_SENDMSG          # 基本命令字
    assert "SENDCHECK" in d["option_names"]  # 要回执就带 SENDCHECK 选项位


def test_packet_has_six_fields_and_port_2425():
    from sysweeper.native import meshchat as m
    pkt, _ = m.build_send("x")
    assert len(pkt.split(":")) >= 6
    assert m.IPMSG_PORT == 2425


def test_filename_with_escaped_colon_parses():
    """文件名里带冒号必须能正确解析——裸 split(':') 会在这里翻车。"""
    from sysweeper.native import meshchat as m
    pkt, _ = m.build_send("看图", files=[
        {"file_id": 1, "name": "a:photo.png", "size": 123456, "mtime": 1700000000}])
    d = m.ipmsg_decode(pkt)
    atts = m.attachments_decode(d["extra"])
    assert atts and atts[0]["name"] == "a:photo.png"
    assert atts[0]["size"] == 123456


def test_attachment_requires_explicit_accept():
    """收到的文件进待收清单，默认**不接受**、不落盘。"""
    from sysweeper.native import meshchat as m
    pkt, _ = m.build_send("发个文件", files=[
        {"file_id": 1, "name": "v.mp4", "size": 999, "mtime": 1}])
    m.inbox_add(m.ipmsg_decode(pkt), source="192.168.1.9:2425")
    pend = m.pending_files()
    assert pend and pend[0]["name"] == "v.mp4"
    assert pend[0]["accepted"] is False       # 未经你点头，谁都不能落盘


def test_malformed_packet_does_not_raise():
    from sysweeper.native import meshchat as m
    for bad in ("", "1", "1:2:3", "a:b:c:d:e:f"):
        try:
            d = m.ipmsg_decode(bad)
            assert isinstance(d, dict)
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"坏包不应抛异常：{bad!r} -> {exc}")


def test_text_classification():
    from sysweeper.native import meshchat as m
    assert m.classify_text("(＾▽＾)") == "kaomoji"
    assert m.classify_text("👍 搞定") == "emoji"
    assert m.classify_text("普通文字") == "text"


def test_entry_exit_packets():
    from sysweeper.native import meshchat as m
    pkt, cmd = m.build_entry()
    assert cmd == m.C_BR_ENTRY
    pkt2, cmd2 = m.build_exit()
    assert cmd2 == m.C_BR_EXIT


def test_protocol_report_is_readonly():
    from sysweeper.native import meshchat as m
    ok, msg = m.protocol_report()
    assert ok is True and msg


# ============================================================ 分布式计算

def test_all_ops_are_verifiable():
    """白名单内每个算子：算一遍 → 复算校验必须通过。"""
    from sysweeper.native import distcompute as d
    cases = [("mc_pi", {"samples": 5000, "seed": 7}),
             ("hash_preimage", {"zeros": 3, "count": 5000}),
             ("block_matmul", {"n": 16, "seed": 3, "row0": 0, "rows": 4})]
    for op, params in cases:
        r = d.wu_run_local(op, params, budget_s=5.0)
        assert r["ok"] is True and r["verify"] is True, (op, r)


def test_tampered_result_fails_verification():
    """冗余双投的意义：节点自述的结果必须能被打假。"""
    from sysweeper.native import distcompute as d
    ok, msg = d.wu_verify("mc_pi", {"samples": 5000, "seed": 7},
                          {"inside": 1, "samples": 5000, "pi": 3.0})
    assert ok is False and "存疑" in msg


def test_unknown_op_refused():
    """白名单外的算子一律拒绝——这是设计，不是缺陷。"""
    from sysweeper.native import distcompute as d
    r = d.wu_run_local("evil_op", {})
    assert r["ok"] is False and "拒绝执行" in r["reason"]
    assert d.wu_split("evil_op", {}, n=4) == []
    assert d.wu_plan("evil_op", {})["ok"] is False


def test_wu_split_produces_independent_units():
    from sysweeper.native import distcompute as d
    for op in ("hash_preimage", "block_matmul", "mc_pi"):
        wus = d.wu_split(op, {"count": 8000, "n": 32, "samples": 8000}, n=8)
        assert len(wus) == 8
        assert len({str(w["params"]) for w in wus}) == 8  # 参数互不相同 = 可独立复算


def test_wu_split_capped():
    from sysweeper.native import distcompute as d
    assert len(d.wu_split("mc_pi", {}, n=999999)) <= d.MAX_WU


def test_score_zero_on_low_battery():
    from sysweeper.native import distcompute as d
    dead = {"cores": 8, "load_per_core": 0.1, "battery_pct": 5, "charging": False}
    assert d.capability_score(dead) == 0.0


def test_metered_network_discounted():
    from sysweeper.native import distcompute as d
    base = {"cores": 8, "load_per_core": 0.1}
    plain = d.capability_score({**base, "metered": False})
    metered = d.capability_score({**base, "metered": True})
    assert metered < plain                      # 计量网络降权（省钱，不是安全）
    assert abs(metered / plain - d.METERED_WEIGHT) < 0.01


def test_busy_node_scores_lower():
    from sysweeper.native import distcompute as d
    idle = d.capability_score({"cores": 8, "load_per_core": 0.05})
    busy = d.capability_score({"cores": 8, "load_per_core": 0.95})
    assert idle > busy


def test_plan_orders_nodes_by_score():
    from sysweeper.native import distcompute as d
    nodes = [{"cores": 2, "load_per_core": 0.9},
             {"cores": 16, "load_per_core": 0.1},
             {"cores": 8, "load_per_core": 0.3}]
    pl = d.wu_plan("mc_pi", {"samples": 8000}, nodes=nodes, redundancy=2)
    assert pl["ok"] is True
    scores = [n["score"] for n in pl["nodes"]]
    assert scores == sorted(scores, reverse=True)
    assert pl["redundancy"] == 2                # 默认冗余双投


def test_plan_refuses_when_no_usable_node():
    from sysweeper.native import distcompute as d
    pl = d.wu_plan("mc_pi", {}, nodes=[{"cores": 8, "battery_pct": 1,
                                        "charging": False, "load_per_core": 0.1}])
    assert pl["ok"] is False and "没有可用节点" in pl["reason"]


def test_batch_respects_budget():
    """跑满预算立即停——不为跑完而拖慢机器。"""
    from sysweeper.native import distcompute as d
    r = d.wu_batch("hash_preimage", {"zeros": 6, "count": 50_000_000},
                   n=64, budget_s=0.3)
    assert r["elapsed_s"] <= 1.5                # 允许一次单元的尾部溢出
    assert r["done"] < 64                       # 预算内没跑完整批，是预期行为


def test_credit_roundtrip(tmp_path):
    from sysweeper.native import distcompute as d
    assert d.credit_add("node-a", 3) is True
    assert d.credit_ledger()["node-a"]["wu"] == 3
    d.credit_add("node-a", 2)
    assert d.credit_ledger()["node-a"]["wu"] == 5


def test_capability_report_readonly():
    from sysweeper.native import distcompute as d
    ok, msg = d.capability_report()
    assert ok is True and "CPU 核心" in msg
    ok2, msg2 = d.ops_report()
    assert "绝不下载" in msg2
    ok3, msg3 = d.distcompute_report()
    assert ok3 is True


def test_no_exec_of_arbitrary_code():
    """红线：算子里没有任何 eval/exec/subprocess 执行路径（源码级守住）。"""
    src = Path(__file__).resolve().parents[1] / "src" / "python" / "sysweeper" / \
        "native" / "distcompute.py"
    text = src.read_text(encoding="utf-8")
    for bad in ("eval(", "exec(", "subprocess", "os.system", "importlib.import_module("):
        assert bad not in text, f"分布式计算层不该出现 {bad}"


# ============================================================ 任务注册

def test_tasks_registered():
    from sysweeper import registry
    ids = {t.id for t in registry.all_tasks()}
    for tid in ("meshchat_protocol", "meshchat_emoji", "meshchat_inbox", "meshchat_send",
                "distcompute_capability", "distcompute_ops", "distcompute_plan",
                "distcompute_selftest", "mesh_share_policy"):
        assert tid in ids, tid


def test_send_task_is_medium_risk():
    """会发包、会占 CPU 的任务必须标 medium（默认不执行）。"""
    from sysweeper import registry
    by_id = {t.id: t for t in registry.all_tasks()}
    assert by_id["meshchat_send"].risk == "medium"
    assert by_id["distcompute_selftest"].risk == "medium"
    assert by_id["meshchat_protocol"].risk == "low"


def test_native_dispatch():
    from sysweeper import runner
    ok, msg = runner._run_native("distcompute.ops_report")
    assert ok is True and "内置可验证算子" in msg
    ok2, msg2 = runner._run_native("meshchat.protocol_report")
    assert ok2 is True and msg2
