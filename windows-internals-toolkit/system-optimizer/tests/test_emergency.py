"""预警应急层测试：定位口径、安全红线、开关真生效。

测试纪律与 test_compress.py 一致：**临时目录 + 假数据**，不依赖真实定位/网络/图形环境。
每条断言都对着"使用者定的口径"或"写死的红线"，不是对着实现细节。
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "python"))

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _tmp_config(tmp_path, monkeypatch):
    """每项测试用独立配置目录，绝不碰用户真实的 ~/.config。"""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from sysweeper.native import emergency
    emergency._MANUAL = None
    emergency._MEMORY_SW = None
    emergency.alert_clear()
    yield


def _srcs(cell=True, net=True, gnss=None):
    from sysweeper.native import emergency as e
    out = []
    if cell:
        out.append(e.LocSource(e.SRC_CELL, 31.2304, 121.4737, 1500, "基站"))
    if net:
        out.append(e.LocSource(e.SRC_NET, 31.2400, 121.4800, 5000, "IP 归属"))
    if gnss:
        out.append(e.LocSource(e.SRC_GNSS, gnss[0], gnss[1], gnss[2], "GPS"))
    return out


# ---------------- 几何 ----------------

def test_haversine_known_distance():
    from sysweeper.native import emergency as e
    d = e.haversine_m(31.2304, 121.4737, 39.9042, 116.4074)  # 上海 → 北京
    assert 1_050_000 < d < 1_090_000, d
    assert e.haversine_m(31.2304, 121.4737, 31.2304, 121.4737) == 0.0


def test_invalid_coords_rejected():
    from sysweeper.native import emergency as e
    assert e._valid(91.0, 0.0) is False
    assert e._valid(0.0, 181.0) is False
    assert e._valid(0.0, 0.0) is False          # 经纬度全 0 视为无效（Null Island）
    assert e._valid(float("nan"), 1.0) is False  # nan 不算有效坐标
    assert e._valid(31.2, 121.4) is True


# ---------------- 定位口径（核心三条）----------------

def test_baseline_is_cell_plus_network():
    """口径一：没有导航时，首选基线 = 网络 + 基站。"""
    from sysweeper.native import emergency as e
    r = e.resolve_position(_srcs())
    assert r["final"]["mode"] == "baseline-only"
    assert r["nav"] is None
    assert r["baseline"]["n"] == 2
    # 精度高的基站应占更大权重
    w = r["baseline"]["weights"]
    assert w["cell"] > w["network"]


def test_nav_fuses_with_baseline():
    """口径二：有导航时，导航与首选基线**共同综合**（不是丢掉基线）。"""
    from sysweeper.native import emergency as e
    r = e.resolve_position(_srcs(gnss=(31.2310, 121.4745, 8)))
    f = r["final"]
    assert f["mode"] == "nav+baseline"
    assert f["weights"]["gnss"] > 0.5        # 导航主导
    assert sum(v for k, v in f["weights"].items() if k != "gnss") > 0  # 基线仍在
    assert f["n"] == 3


def test_baseline_keeps_minimum_voice():
    """导航精度高两个量级时，基线仍保留最低 5% 话语权（防一次跳变甩飞）。"""
    from sysweeper.native import emergency as e
    r = e.resolve_position(_srcs(gnss=(31.2310, 121.4745, 8)))
    base_share = 1.0 - r["final"]["weights"]["gnss"]
    assert base_share >= e.BASELINE_MIN_W - 1e-6, base_share
    # 综合点应落在导航点与基线点之间（真综合，不是二选一）
    nav, base = r["nav"], r["baseline"]
    lat = r["final"]["lat"]
    assert min(nav["lat"], base["lat"]) <= lat <= max(nav["lat"], base["lat"])


def test_disagreement_flagged_suspect():
    """口径三：偏差超阈值标存疑，两套结果都摆出来。"""
    from sysweeper.native import emergency as e
    r = e.resolve_position(_srcs(net=False, gnss=(31.4000, 121.9000, 10)))
    assert r["suspect"] is True
    assert r["disagreement_m"] > e.DISAGREE_M
    assert r["baseline"] is not None and r["nav"] is not None  # 两个都在，不替用户判定


def test_agreement_not_suspect():
    from sysweeper.native import emergency as e
    r = e.resolve_position(_srcs(gnss=(31.2310, 121.4745, 8)))
    assert r["suspect"] is False


def test_no_sources_means_no_position():
    from sysweeper.native import emergency as e
    r = e.resolve_position([])
    assert r["final"] is None
    ok, msg = e.position_report()
    assert ok and "未取得任何定位源" in msg   # 诚实报"没有"，不编造坐标


def test_source_without_fix_shows_as_visible_but_no_coords():
    """基站可见但缺经纬度库时，要显示"可见但无坐标"，而不是塞个假坐标。"""
    from sysweeper.native import emergency as e
    s = e.LocSource(e.SRC_CELL, float("nan"), float("nan"), 1500, "基站 LAC=1 CID=2")
    d = s.as_dict()
    assert d["has_fix"] is False and d["lat"] is None
    line = e._src_line(d)
    assert "可见但无坐标" in line


# ---------------- 手动录入 ----------------

def test_manual_position_roundtrip(tmp_path):
    from sysweeper.native import emergency as e
    assert e.set_manual_position(31.2304, 121.4737, 100) is True
    assert e.set_manual_position(999.0, 0.0) is False     # 非法坐标拒绝
    r = e.resolve_position([e._load_manual()])
    assert r["final"]["mode"] == "manual"
    # 落盘后重读仍生效
    e._MANUAL = None
    m = e._load_manual()
    assert m is not None and abs(m.lat - 31.2304) < 1e-6


# ---------------- 预警评估 ----------------

def test_assess_distance_and_inside():
    from sysweeper.native import emergency as e
    pos = e.resolve_position(_srcs(gnss=(31.2310, 121.4745, 8)))
    near = e.Alert("近处事件", "Severe", lat=31.2400, lon=121.4800, radius_m=5000,
                   kind="earthquake_p")
    far = e.Alert("远处事件", "Minor", lat=32.0000, lon=122.0000, radius_m=1000,
                  kind="typhoon")
    a_near, a_far = e.assess(near, pos), e.assess(far, pos)
    assert a_near["inside"] is True
    assert a_far["inside"] is False
    assert a_far["eta_s"] > 0                        # 半径外才给粗估到达
    assert a_near["distance_m"] < a_far["distance_m"]


def test_assess_without_position_reports_unknown():
    from sysweeper.native import emergency as e
    a = e.assess(e.Alert("无位置事件", lat=31.2, lon=121.4), e.resolve_position([]))
    assert a["distance_m"] is None and "无法计算距离" in a["note"]


def test_assess_all_sorted_by_distance():
    from sysweeper.native import emergency as e
    pos = e.resolve_position(_srcs(gnss=(31.2310, 121.4745, 8)))
    e.alert_add(e.Alert("远", lat=32.0, lon=122.0))
    e.alert_add(e.Alert("近", lat=31.2320, lon=121.4750))
    rows = e.assess_all(pos)
    assert rows[0]["event"] == "近" and rows[1]["event"] == "远"
    assert len(rows) == 2


def test_eta_is_magnitude_only():
    """粗估到达是量级参考，报告里必须写明不是预报。"""
    from sysweeper.native import emergency as e
    # 让"本机位置"真的可用（手动录入兜底），否则报告只会写"无法计算距离"
    e.set_manual_position(31.2310, 121.4745, 8)
    quake = e.Alert("地震", lat=32.0, lon=122.0, radius_m=1000, kind="earthquake_p")
    e.alert_add(quake)
    a = e.assess(quake)
    assert a["eta_s"] > 0
    ok, msg = e.alert_report()
    assert "不是预报" in msg


# ---------------- 安全红线 ----------------

def test_no_alerts_is_not_fake_safety():
    from sysweeper.native import emergency as e
    ok, msg = e.alert_report()
    assert "没有预警就是没有预警" in msg


def test_feed_disabled_by_default():
    from sysweeper.native import emergency as e
    assert e.switch_on("feed_enabled") is False
    ok, msg = e.feed_fetch("https://example.invalid/cap.json")
    assert ok is False and "订阅源开关是关的" in msg


def test_feed_rejects_non_http():
    from sysweeper.native import emergency as e
    e.set_switch("feed_enabled", True)
    ok, msg = e.feed_fetch("file:///etc/passwd")
    assert ok is False and "只接受 http(s)" in msg
    ok, msg = e.feed_fetch("ftp://x/y")
    assert ok is False


def test_sos_is_text_only():
    """呼救只生成文本；关闭开关后直接拒绝（不做"关了还偷偷跑"）。"""
    from sysweeper.native import emergency as e
    pos = e.resolve_position(_srcs(gnss=(31.2310, 121.4745, 8)))
    txt = e.sos_text(pos, contacts=["家人"], note="地震后失联")
    assert "31.231" in txt and "家人" in txt
    assert "未自动发送" in txt
    e.set_switch("sos_enabled", False)
    assert "已关闭" in e.sos_text(pos)


def test_switch_unknown_name_rejected():
    from sysweeper.native import emergency as e
    assert e.set_switch("does_not_exist", True) is False
    assert e.set_switch("feed_enabled", True) is True
    assert e.switch_on("feed_enabled") is True


def test_switch_persists_and_resets(tmp_path):
    from sysweeper.native import emergency as e
    e.set_switch("shelter_enabled", False)
    assert e.switches()["shelter_enabled"] is False
    assert (tmp_path / "sysweeper" / "emergency.json").exists()
    st = e.reset_switches()
    assert st["shelter_enabled"] is True


def test_corrupted_switch_file_falls_back(tmp_path):
    from sysweeper.native import emergency as e
    p = tmp_path / "sysweeper" / "emergency.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{ not json", encoding="utf-8")
    assert e.switches() == e.DEFAULT_SWITCHES   # 坏配置回退默认，不抛异常


def test_disabled_features_do_not_run():
    from sysweeper.native import emergency as e
    e.set_switch("shelter_enabled", False)
    assert e.shelter_sort([{"name": "x", "lat": 31.2, "lon": 121.4}]) == []
    e.set_switch("kit_enabled", False)
    assert e.kit_check([])["enabled"] is False
    e.set_switch("alert_enabled", False)
    ok, msg = e.alert_report()
    assert "已关闭" in msg


# ---------------- 应急功能 ----------------

def test_shelter_sorted_by_distance():
    from sysweeper.native import emergency as e
    pos = e.resolve_position(_srcs(gnss=(31.2310, 121.4745, 8)))
    pts = [{"name": "远操场", "lat": 31.30, "lon": 121.55},
           {"name": "近体育馆", "lat": 31.232, "lon": 121.476}]
    out = e.shelter_sort(pts, pos)
    assert [p["name"] for p in out] == ["近体育馆", "远操场"]
    assert out[0]["distance_m"] < out[1]["distance_m"]


def test_shelter_without_position_keeps_distance_none():
    from sysweeper.native import emergency as e
    out = e.shelter_sort([{"name": "x", "lat": 31.2, "lon": 121.4}],
                         e.resolve_position([]))
    assert out and out[0]["distance_m"] is None


def test_kit_check_ratio():
    from sysweeper.native import emergency as e
    k = e.kit_check([])
    assert k["missing"] == list(e.DEFAULT_KIT) and k["ratio"] == 0.0
    k2 = e.kit_check(list(e.DEFAULT_KIT))
    assert k2["ratio"] == 1.0 and k2["missing"] == []


# ---------------- 报告与注册 ----------------

def test_reports_are_readonly_and_ok():
    from sysweeper.native import emergency as e
    for fn in (e.position_report, e.alert_report, e.emergency_report,
               e.capabilities_report):
        ok, msg = fn()
        assert ok is True and isinstance(msg, str) and msg


def test_tasks_registered_low_risk():
    from sysweeper import registry
    ids = {t.id for t in registry.all_tasks()}
    for tid in ("emergency_locate", "emergency_alert_assess", "emergency_sos",
                "emergency_preparedness", "emergency_switches"):
        assert tid in ids
    em = [t for t in registry.all_tasks() if t.id.startswith("emergency_")]
    assert len(em) == 5
    assert all(t.risk == "low" for t in em)
    assert all(t.platform == "any" for t in em)


def test_emergency_native_dispatch():
    from sysweeper import runner
    ok, msg = runner._run_native("emergency.capabilities_report")
    assert ok is True and "预警应急能力自检" in msg


def test_report_strings_have_no_untranslated_leftovers():
    """报告里不该出现 nan / None 这类内部值漏给用户。"""
    from sysweeper.native import emergency as e
    ok, msg = e.position_report()
    assert "nan" not in msg.lower()
    ok, msg = e.emergency_report()
    assert "None" not in msg
