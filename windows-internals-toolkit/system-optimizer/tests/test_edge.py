"""edge 单板机只读探针测试（v0.6.11）。

用 _set_sys_root 把探测根重定向到临时目录，喂假的 sysfs 树，验证只读探测与建议。
不碰真机 /sys、/proc。
"""

import textwrap

import pytest

from sysweeper.native import edge


@pytest.fixture
def fake_sys(tmp_path):
    """造一棵假 sysfs/树莓派 4 风格的目录。"""
    root = tmp_path / "sysroot"
    # 设备树型号（树莓派 4）
    dt = root / "proc" / "device-tree"
    dt.mkdir(parents=True)
    (dt / "model").write_text("Raspberry Pi 4 Model B Rev 1.2\x00", encoding="utf-8")
    # thermal：两个 zone，其中一个 85°C（偏高）
    thermal = root / "sys" / "class" / "thermal"
    z0 = thermal / "thermal_zone0"
    z1 = thermal / "thermal_zone1"
    z0.mkdir(parents=True)
    z1.mkdir(parents=True)
    (z0 / "type").write_text("cpu-thermal")
    (z0 / "temp").write_text("85000")
    (z1 / "type").write_text("gpu-thermal")
    (z1 / "temp").write_text("50000")
    # Broadcom throttled：bit0 under-voltage 置位
    soc = root / "sys" / "devices" / "platform" / "soc"
    th = soc / "fake" / "throttled"
    th.mkdir(parents=True)
    (th / "throttled").write_text("0x1")
    # 启动盘：根挂到 /dev/mmcblk0（SD 卡）
    mi = root / "proc" / "self"
    mi.mkdir(parents=True)
    (mi / "mountinfo").write_text(textwrap.dedent(
        "24 1 179:2 / / rw,relatime - ext4 /dev/mmcblk0p2 rw\n"))
    block = root / "sys" / "class" / "block" / "mmcblk0" / "device"
    block.mkdir(parents=True)
    (block / "device").symlink_to(root / "sys" / "devices" / "platform" / "soc"
                                  / "mmc0")  # 非 emmc 字样
    edge._set_sys_root(root)
    yield root
    edge._reset_sys_root()


def test_detect_board(fake_sys):
    assert "Raspberry Pi 4" in (edge.detect_board() or "")


def test_thermal_zones(fake_sys):
    zones = edge.thermal_zones()
    assert len(zones) == 2
    hottest = max(zones, key=lambda z: z["temp_c"])
    assert hottest["temp_c"] == 85.0


def test_throttle_state(fake_sys):
    th = edge.throttle_state()
    assert th is not None
    assert th["under_voltage"] is True
    assert th["throttled_now"] is False


def test_boot_media_sd(fake_sys):
    assert "SD 卡" in (edge.boot_media() or "")


def test_edge_report_flags(fake_sys):
    ok, msg = edge.edge_report()
    assert ok
    assert "Raspberry Pi 4" in msg
    assert "85" in msg            # 温度被带出来
    assert "under-voltage" in msg or "欠压" in msg
    assert "SD 卡" in msg         # 启动盘建议


def test_edge_report_non_sbc(tmp_path):
    # 没有设备树型号的目录 → 明确说未识别为单板机
    edge._set_sys_root(tmp_path)
    try:
        ok, msg = edge.edge_report()
        assert ok
        assert "未识别为单板机" in msg
    finally:
        edge._reset_sys_root()


def test_capabilities_report():
    ok, msg = edge.capabilities_report()
    assert ok
    assert "只读" in msg
