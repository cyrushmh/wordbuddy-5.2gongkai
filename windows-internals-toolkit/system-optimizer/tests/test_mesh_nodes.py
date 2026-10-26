"""组网节点发现注册表测试（v0.6.11）。

验证「谁能接活」：能力通告解析、登记、TTL 过期剔除、报告——不真正发包。
"""

import time

from sysweeper.native import distjob, meshchat


def setup_function(_):
    # 每个测试前清空内存节点表
    meshchat._NODES.clear()


def test_decode_offer():
    txt = distjob.offer_text()
    assert txt.startswith("SW-OFFER1:")
    d = distjob.decode_offer(txt)
    assert isinstance(d, dict)
    assert "cores" in d


def test_decode_offer_rejects_garbage():
    assert distjob.decode_offer("hello world") is None
    assert distjob.decode_offer("SW-OFFER1:not json") is None
    assert distjob.decode_offer("") is None


def test_register_offer_and_known():
    ok, _ = meshchat.register_offer(distjob.offer_text(), "10.0.0.5:2425")
    assert ok
    nodes = meshchat.known_nodes()
    assert len(nodes) == 1
    assert nodes[0]["addr"] == "10.0.0.5:2425"
    assert "caps" in nodes[0]


def test_register_offer_ignores_garbage():
    ok, msg = meshchat.register_offer("乱码不是通告", "1.2.3.4:2425")
    assert ok is False
    assert meshchat.known_nodes() == []


def test_expire_old():
    now = time.time()
    meshchat.register_offer(distjob.offer_text(), "10.0.0.6:2425", now=now)
    # 一个早于 TTL 的节点（expires_at 已过去）应被剔除
    meshchat.register_offer(distjob.offer_text(), "10.0.0.7:2425",
                            now=now - (meshchat.OFFER_TTL + 50))
    assert len(meshchat._NODES) == 2
    removed = meshchat.expire_old(now + 1)
    assert removed == 1
    assert len(meshchat._NODES) == 1


def test_node_report():
    meshchat.register_offer(distjob.offer_text(), "10.0.0.8:2425")
    ok, msg = meshchat.node_report()
    assert ok
    assert "10.0.0.8" in msg


def test_node_report_empty():
    ok, msg = meshchat.node_report()
    assert ok
    assert "未登记" in msg or "没有" in msg
