"""OSI 七层网络诊断模块测试（只读；不依赖外部网络）。"""

import pytest

from sysweeper.native import osi


def test_osi_report_has_seven_layers():
    ok, msg = osi.osi_report()
    assert ok is True
    assert isinstance(msg, str)
    for n in range(1, 8):
        assert f"L{n}" in msg, f"报告应含 L{n} 层标记"
    # 每层中文名都出现
    for name in ("物理层", "数据链路层", "网络层", "传输层",
                 "会话层", "表示层", "应用层"):
        assert name in msg
    # 每层附了参照文档
    assert "ISO/IEC 7498-1" in msg


def test_layer_report_valid():
    ok, msg = osi.layer_report(3)
    assert ok is True
    assert "L3" in msg and "网络层" in msg


@pytest.mark.parametrize("n", [0, 8, -1])
def test_layer_report_invalid(n):
    ok, msg = osi.layer_report(n)
    assert ok is False
    assert "1" in msg and "7" in msg


def test_capabilities_report_seven_layers_and_redline():
    ok, msg = osi.capabilities_report()
    assert ok is True
    for n in range(1, 8):
        assert f"L{n}" in msg
    assert "红线" in msg


def test_dns_resolve_localhost_returns_tuple():
    ok, msg = osi.dns_resolve("localhost", timeout=2.0)
    assert isinstance(ok, bool)
    assert isinstance(msg, str)


def test_probe_http_rejects_non_http():
    ok, msg = osi.probe_http("ftp://example.com")
    assert ok is False
    assert "仅支持" in msg


def test_layer1_degrade_when_no_ifaces(monkeypatch):
    monkeypatch.setattr(osi, "_list_ifaces", lambda: [])
    ok, msg = osi.layer1_physical()
    assert ok is False
    assert "未发现" in msg


def test_all_layers_callable_and_return_tuple():
    for n in range(1, 8):
        ok, msg = osi._layer_call(n)()
        assert isinstance(ok, bool)
        assert isinstance(msg, str)


def test_probe_http_safe_url_guard():
    # 仅 http/https 通过白名单
    assert osi._safe_url("http://x") is True
    assert osi._safe_url("https://x") is True
    assert osi._safe_url("ftp://x") is False
    assert osi._safe_url("file:///x") is False
