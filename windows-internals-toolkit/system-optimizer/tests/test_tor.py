"""Tor（洋葱路由）只读诊断模块的测试（全只读、不启停 tor、不连控制端口、不打印密钥明文）。"""
import sys

sys.path.insert(0, "src/python")
from sysweeper.native import tor


def test_tor_report_shape():
    ok, msg = tor.tor_report()
    assert isinstance(ok, bool) and isinstance(msg, str) and msg
    assert "Tor" in msg and "SOCKS" in msg and "控制端口" in msg


def test_tor_capabilities_redline():
    ok, msg = tor.capabilities_report()
    assert ok and "红线" in msg and "torrc" in msg


def test_tor_binary_found(monkeypatch):
    monkeypatch.setattr(tor.shutil, "which",
                        lambda name: "/usr/bin/tor" if name == "tor" else None)
    monkeypatch.setattr(tor.common, "run",
                        lambda cmd, timeout=10: (0, "Tor version 0.4.8.10 (git-abc)")
                        if "--version" in cmd else (1, ""))
    found, ver = tor._tor_binary()
    assert found and ver == "0.4.8.10"


def test_torrc_report_parses(tmp_path, monkeypatch):
    rc = tmp_path / "torrc"
    rc.write_text(
        "SocksPort 9050\n"
        "ControlPort 9051\n"
        "Bridge obfs4 1.2.3.4:443 cert=abc\n"
        "ClientTransportPlugin obfs4 exec /usr/bin/obfs4proxy\n"
        "ORPort 9001\n"
        "ExitRelay 1\n"
        "HashedControlPassword 16:abcdef\n"
    )
    monkeypatch.setattr(tor, "TORRC_PATHS", [str(rc)])
    info = tor._torrc_report()
    assert info["path"] == str(rc)
    assert "9050" in info["socks"]
    assert "9051" in info["control"]
    assert info["bridge"] is True
    assert "obfs4" in info["pt"]
    assert info["relay"] is True
    assert info["exit"] is True
    assert "HashedControlPassword" in info["sensitive"]


def test_tor_report_no_secret_leak(tmp_path, monkeypatch):
    """红线：torrc 里的密钥类敏感项只报存在名，绝不回显明文。"""
    rc = tmp_path / "torrc"
    rc.write_text("HashedControlPassword 16:TOPSECRETVALUE\n")
    monkeypatch.setattr(tor, "TORRC_PATHS", [str(rc)])
    monkeypatch.setattr(tor.shutil, "which", lambda n: None)
    ok, msg = tor.tor_report()
    assert ok
    assert "HashedControlPassword" in msg
    assert "TOPSECRETVALUE" not in msg


def test_registry_includes_tor():
    from sysweeper import registry
    ids = [t.id for t in registry.all_tasks()]
    assert "tor_report" in ids
