"""ZeroTier 虚拟网络只读诊断模块的测试（全只读、不启停、绝不读 identity.secret）。"""
import sys

sys.path.insert(0, "src/python")
from sysweeper.native import zerotier


def test_zerotier_report_shape():
    ok, msg = zerotier.zerotier_report()
    assert isinstance(ok, bool) and isinstance(msg, str) and msg
    assert "ZeroTier" in msg and "已加入网络" in msg and "控制器" in msg


def test_zerotier_capabilities_redline():
    ok, msg = zerotier.capabilities_report()
    assert ok and "红线" in msg and "identity.secret" in msg


def test_zerotier_networks(tmp_path, monkeypatch):
    zt = tmp_path / "zt"
    (zt / "networks.d").mkdir(parents=True)
    (zt / "networks.d" / "a1b2c3.conf").write_text("")
    (zt / "networks.d" / "d4e5f6.conf").write_text("")
    monkeypatch.setattr(zerotier, "ZT_DIR", str(zt))
    nets = zerotier._networks()
    assert nets == ["a1b2c3", "d4e5f6"]


def test_zerotier_identity(tmp_path, monkeypatch):
    zt = tmp_path / "zt"
    zt.mkdir()
    (zt / "identity.public").write_text("PUB")
    (zt / "identity.secret").write_text("SEC")
    monkeypatch.setattr(zerotier, "ZT_DIR", str(zt))
    has_pub, has_sec = zerotier._identity()
    assert has_pub and has_sec


def test_zerotier_report_no_secret_leak(tmp_path, monkeypatch):
    """红线：identity.secret 内容绝不出现在报告里（只报存在名）。"""
    zt = tmp_path / "zt"
    zt.mkdir()
    (zt / "identity.public").write_text("PUBKEY")
    (zt / "identity.secret").write_text("SUPER_SECRET_PRIVATE_KEY")
    monkeypatch.setattr(zerotier, "ZT_DIR", str(zt))
    monkeypatch.setattr(zerotier.shutil, "which", lambda n: None)
    ok, msg = zerotier.zerotier_report()
    assert ok
    assert "SUPER_SECRET_PRIVATE_KEY" not in msg
    assert "identity.public" in msg and "identity.secret" in msg


def test_registry_includes_zerotier():
    from sysweeper import registry
    ids = [t.id for t in registry.all_tasks()]
    assert "zerotier_report" in ids
