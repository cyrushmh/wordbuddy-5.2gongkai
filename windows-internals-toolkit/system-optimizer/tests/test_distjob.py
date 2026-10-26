"""跨机派活层（distjob）测试。

纪律：默认**不出网**（dispatch 默认 dry_run）；需要真实 UDP 的那一项走
127.0.0.1 回环，且环境不允许绑定时自动 skip——测试不能因为沙箱限制而红。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "python"))

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _clean(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from sysweeper.native import distjob, meshchat
    distjob.job_clear()
    meshchat.inbox_clear()
    yield
    distjob.job_clear()
    meshchat.inbox_clear()


# ---------------- 编解码 ----------------

def test_wu_roundtrip():
    from sysweeper.native import distjob as j
    text = j.encode_wu("job1", "mc_pi", 3, {"samples": 1000, "seed": 5}, 2.0)
    assert text.startswith(j.WU_MAGIC)
    d = j.decode_wu(text)
    assert d["job"] == "job1" and d["op"] == "mc_pi" and d["i"] == 3
    assert d["p"]["seed"] == 5


def test_res_roundtrip():
    from sysweeper.native import distjob as j
    text = j.encode_res("job1", 0, {"inside": 785, "samples": 1000}, 12.3)
    d = j.decode_res(text)
    assert d["i"] == 0 and d["r"]["inside"] == 785


def test_foreign_message_ignored():
    """网里别人说的话（普通聊天）不能被当成 WU。"""
    from sysweeper.native import distjob as j
    assert j.decode_wu("晚上吃什么") is None
    assert j.decode_res("收到") is None
    assert j.decode_wu("SW-WU1:{not json") is None


def test_non_whitelist_op_rejected_at_decode():
    """通道里传的是参数不是代码：白名单外的算子连解析都不认。"""
    from sysweeper.native import distjob as j
    evil = j.encode_wu("job", "rm -rf /", 0, {})   # 编码能编，但解析时拒
    assert j.decode_wu(evil) is None


def test_oversized_payload_rejected():
    from sysweeper.native import distjob as j
    big = j.WU_MAGIC + "x" * (j.MAX_PAYLOAD + 10)
    assert j.decode_wu(big) is None


def test_offer_text_has_capability():
    from sysweeper.native import distjob as j
    t = j.offer_text()
    assert t.startswith(j.OFFER_MAGIC)
    assert "cores" in t and "score" in t


# ---------------- 派活 ----------------

def test_dispatch_dry_run_sends_nothing():
    """默认只出计划不出网——与全工程「默认不代劳」一致。"""
    from sysweeper.native import distjob as j
    r = j.dispatch("mc_pi", {"samples": 8000}, n=4, redundancy=2)
    assert r["ok"] and r["dry_run"] is True and r["sent"] == 0
    assert r["wu_count"] == 4 and r["messages"] == 8   # 4 单元 × 冗余 2 份


def test_dispatch_refuses_unknown_op():
    from sysweeper.native import distjob as j
    r = j.dispatch("evil", {})
    assert r["ok"] is False and "只派白名单" in r["reason"]


def test_dispatch_registers_pending_job():
    from sysweeper.native import distjob as j
    r = j.dispatch("mc_pi", {"samples": 8000}, n=2)
    assert r["job"] in j.jobs()
    assert len(j.jobs()[r["job"]]["units"]) == 2


# ---------------- 结果校验（信任模型的落点）----------------

def _dispatch_and_get_unit(j, op="mc_pi", params=None):
    r = j.dispatch(op, params or {"samples": 8000, "seed": 3}, n=1, redundancy=1)
    job = r["job"]
    unit = j.jobs()[job]["units"][0]
    return job, unit


def test_valid_result_accepted():
    from sysweeper.native import distcompute as d
    from sysweeper.native import distjob as j
    job, unit = _dispatch_and_get_unit(j)
    res = d.wu_run_local("mc_pi", unit["params"])["result"]
    status, _why = j.apply_result({"source": "1.2.3.4:2425"},
                                  j.decode_res(j.encode_res(job, 0, res, 5.0)))
    assert status == "accepted"
    assert j.jobs()[job]["units"][0]["status"] == "accepted"


def test_forged_result_rejected():
    """节点自述的结果必须能被打假——这是冗余双投的意义。"""
    from sysweeper.native import distjob as j
    job, unit = _dispatch_and_get_unit(j)
    fake = {"inside": 1, "samples": unit["params"]["samples"], "pi": 3.999999}
    status, why = j.apply_result({"source": "1.2.3.4:2425"},
                                 j.decode_res(j.encode_res(job, 0, fake, 0.1)))
    assert status == "suspect" and "存疑" in why


def test_result_for_unknown_job_ignored():
    from sysweeper.native import distjob as j
    status, _ = j.apply_result({"source": "x"},
                               j.decode_res(j.encode_res("nosuchjob", 0, {}, 1.0)))
    assert status == "ignored"


def test_wrong_unit_index_ignored():
    from sysweeper.native import distjob as j
    job, _unit = _dispatch_and_get_unit(j)
    status, _ = j.apply_result({"source": "x"},
                               j.decode_res(j.encode_res(job, 99, {}, 1.0)))
    assert status == "ignored"


def test_accepted_result_earns_credit():
    from sysweeper.native import distcompute as d
    from sysweeper.native import distjob as j
    job, unit = _dispatch_and_get_unit(j)
    res = d.wu_run_local("mc_pi", unit["params"])["result"]
    j.apply_result({"source": "node-a:2425"},
                   j.decode_res(j.encode_res(job, 0, res, 1.0)))
    assert d.credit_ledger().get("node-a:2425", {}).get("wu", 0) >= 1


# ---------------- 链路自检与报告 ----------------

def test_loopback_selfcheck_all_green():
    """回环自检：伪造结果必须被打回，白名单外算子必须被拒。"""
    from sysweeper.native import distjob as j
    ok, msg = j.loopback_report()
    assert ok is True
    assert "不能，被打回" in msg          # ⑤ 伪造结果
    assert "被拒" in msg                  # ⑦ 白名单外算子
    assert "忽略，不抛异常" in msg        # ⑥ 坏包


def test_job_report_readonly():
    from sysweeper.native import distjob as j
    ok, msg = j.job_report()
    assert ok is True and j.WU_MAGIC in msg
    j.dispatch("mc_pi", {"samples": 1000}, n=2)
    ok2, msg2 = j.job_report()
    assert "mc_pi" in msg2


# ---------------- 真实通道（回环，环境不允许则跳过）----------------

def test_real_udp_loopback():
    """真发一个 WU 到 127.0.0.1，用 serve_once 接住——验证通道确实能用。

    不是模拟：真的走 UDP 2425。环境不允许绑定端口时跳过（沙箱限制不该让测试变红）。
    """
    import socket
    import threading

    from sysweeper.native import distjob as j
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("", 2425))
        s.close()
    except OSError as exc:
        pytest.skip(f"本环境无法绑定 UDP 2425（{exc}）")

    result = {}
    done = threading.Event()

    def serve():
        try:
            result["r"] = j.serve_once(timeout=4.0, budget=2.0)
        finally:
            done.set()

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    import time
    time.sleep(0.4)                      # 等监听 socket 起来
    d = j.dispatch("mc_pi", {"samples": 5000, "seed": 9}, n=1,
                   redundancy=1, target="127.0.0.1", dry_run=False)
    done.wait(8)
    assert d["sent"] >= 1, d
    r = result.get("r") or {}
    assert r.get("ok") is True, r
    assert r.get("op") == "mc_pi"
    assert r.get("verify") is True
