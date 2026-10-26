"""硬件总线/接口枚举测试（只读；读 /sys/bus 与 lspci/lsusb 可用性）。"""

from sysweeper.native import hardware


def test_bus_report_shape():
    ok, msg = hardware.bus_report()
    assert isinstance(ok, bool)
    assert isinstance(msg, str)
    assert "总线" in msg


def test_bus_report_lists_common_buses():
    # 至少应盘点到 platform 这类几乎所有 Linux 都有的总线（除非无 sysfs）
    ok, msg = hardware.bus_report()
    if ok:
        assert "platform" in msg or "pci" in msg or "其他已注册总线" in msg


def test_pci_usb_devices_return_list():
    # 现有函数保持返回 list（不被 bus_report 改动破坏）
    assert isinstance(hardware.pci_devices(), list)
    assert isinstance(hardware.usb_devices(), list)
