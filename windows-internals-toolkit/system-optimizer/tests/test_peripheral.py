"""peripheral 子系统测试（v0.6.39）：知识库加载 + 纯函数引擎 + 只读不变量。

覆盖：整体引入星闪标准(introduce_nearlink) / 触控技术支持与兼容(assess_touch_compat)
/ 外部设备支持与兼容(assess_external_compat) / 端到端报告(peripheral_report) /
文档清单 / 写指引只读 / 探针可调用。
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

from sysweeper.native import peripheral as npf  # noqa: E402


def test_refs_loaded():
    # 4 类外部设备标准知识库 + 4 类线缆/连接器标准知识库应全部加载
    assert set(npf.reference_all()) >= {
        "nearlink_standard", "touch_tech", "usb_c_pd", "hid_compat",
        "cabling_copper", "fiber_cable", "video_conn", "power_conn",
    }
    assert len(npf.reference_all()) == 8


def test_introduce_nearlink_structure():
    nl = npf.introduce_nearlink()
    assert nl["standard"] == "nearlink_standard"
    assert set(nl["air_interfaces"]) >= {"SLB", "SLE"}
    assert "微秒级时延" in nl["features"]
    assert "adopt_nearlink" in nl["adoption"] or "选型" in nl["adoption"]


def test_assess_touch_none():
    sug = npf.assess_touch_compat([])
    assert any(s["id"] == "touch_none" for s in sug)


def test_assess_touch_stylus_precision():
    sug = npf.assess_touch_compat(["stylus", "touchpad"])
    ids = {s["id"] for s in sug}
    assert "stylus_lowlatency" in ids
    assert "precision_touchpad" in ids


def test_assess_touch_driver_hint_from_readings():
    sug = npf.assess_touch_compat(
        ["touchscreen"], {"touch_devices": [{"name": "X", "protocol": "MT-A"}]})
    assert any(s["id"] == "touch_driver" for s in sug)


def test_assess_external_nearlink_cable():
    sug = npf.assess_external_compat(["nearlink_desired", "usb_c_pd", "legacy_usb"])
    ids = {s["id"] for s in sug}
    assert "adopt_nearlink" in ids
    assert "usb_c_pd_cable" in ids
    assert "usb4_altmode" in ids
    assert "legacy_compat" in ids


def test_assess_external_env_sensor_feed():
    sug = npf.assess_external_compat(["external_env_sensor"])
    assert any(s["id"] == "env_sensor_feed" for s in sug)


def test_assess_external_usb_driver_hint():
    sug = npf.assess_external_compat(
        ["hid_device"], {"usb_devices": {"count": 3, "hid_count": 0}})
    assert any(s["id"] == "usb_driver" for s in sug)


def test_peripheral_report_returns_str():
    ok, rep = npf.peripheral_report(["nearlink_desired", "usb_c_pd"])
    assert ok is True
    assert isinstance(rep, str)
    assert "星闪" in rep
    assert "USB-C" in rep or "USB4" in rep


def test_peripheral_report_sections_present():
    ok, rep = npf.peripheral_report([])
    assert ok is True
    assert "[①" in rep and "[②" in rep and "[③" in rep
    # 安全不变量：只读识别，绝不刷固件/装驱动/挂钩输入
    assert "只读" in rep


def test_doc_list_nonempty():
    docs = npf.peripheral_doc_list()
    assert isinstance(docs, list)
    assert len(docs) > 0
    assert any("nearlink_standard" in d for d in docs)


def test_tune_list_readonly_only():
    # 写指引清单只描述不执行（函数存在即代表只回文本，不刷固件/装驱动）
    tunes = npf.peripheral_tune_list()
    assert len(tunes) == len(npf.TUNES)
    for fn, _desc in npf.TUNES:
        assert hasattr(npf, fn)


def test_environment_report_list():
    rep = npf.environment_report()
    assert isinstance(rep, list)
    assert len(rep) >= 1


def test_probe_functions_callable():
    for fn_name, _label in npf.PROBES:
        assert callable(getattr(npf, fn_name))


def test_read_functions_callable_and_safe():
    # 只读探针可调用、绝不抛异常（降级返回 (False, ...) 也是合法）
    for fn in (npf.read_nearlink_capability, npf.read_touch_devices,
               npf.read_usb_devices, npf.read_external_env_sensor):
        rc, msg = fn()
        assert isinstance(rc, bool)
