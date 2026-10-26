"""proton 兼容层只读诊断模块的测试（全只读、不触网、不装包）。"""

from sysweeper.native import proton


def test_proton_report_shape():
    ok, msg = proton.proton_report()
    assert isinstance(ok, bool)
    assert isinstance(msg, str)
    assert "兼容层诊断" in msg
    assert "Vulkan" in msg and "32 位" in msg and "NT 同步原语" in msg


def test_vulkan_report_shape():
    ok, msg = proton.vulkan_report()
    assert isinstance(ok, bool) and isinstance(msg, str)
    assert "Vulkan" in msg


def test_i386_report_shape():
    ok, msg = proton.i386_report()
    assert isinstance(ok, bool) and isinstance(msg, str)
    assert "i386" in msg


def test_sync_report_mentions_three():
    ok, msg = proton.sync_report()
    assert "esync" in msg and "fsync" in msg and "NTSync" in msg
    # 内核版本解析可用
    assert len(proton._kernel_version()) == 3


def test_capabilities_report_redline():
    ok, msg = proton.capabilities_report()
    assert ok is True
    assert "红线" in msg
    assert "Vulkan" in msg and "Steam" in msg


def test_ntsync_detection(monkeypatch, tmp_path):
    """NTSync 检测：把设备节点重定向到临时文件，验证 /dev/ntsync 存在即判可用。"""
    dev = tmp_path / "ntsync"
    dev.write_text("")
    monkeypatch.setattr(proton, "NTSYNC_DEV", str(dev))
    ok, msg = proton.sync_report()
    assert "NTSync (/dev/ntsync)  ：可用" in msg


def test_registry_includes_proton():
    from sysweeper import registry
    ids = [t.id for t in registry.all_tasks()]
    assert "proton_report" in ids
