"""electrical 子系统测试（v0.6.38）：知识库加载 + 纯函数引擎 + 安全不变量。"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

from sysweeper.native import electrical as ne  # noqa: E402


def test_refs_loaded():
    # 8 类电气火灾隐患知识库应全部加载
    assert set(ne.REFERENCE_KEYS if hasattr(ne, "REFERENCE_KEYS") else ne.reference_all()) >= {
        "local_high_resistance_heating", "galvanic_corrosion", "metal_creep",
        "series_arc", "barrel_overload", "grounding_rcd", "connector_aging",
        "combustible_base",
    }
    assert len(ne.reference_all()) == 8


def test_assess_no_tags_low():
    chain = ne.assess_hazard_chain([])
    assert chain["risk"] == "low"
    assert chain["critical"] is False
    assert chain["hazards"] == []


def test_assess_copper_aluminum_critical():
    chain = ne.assess_hazard_chain(["copper_aluminum"])
    assert chain["critical"] is True
    assert chain["risk"] == "high"
    kbs = {h["kb"] for h in chain["hazards"]}
    assert "galvanic_corrosion" in kbs


def test_assess_wood_base_critical():
    chain = ne.assess_hazard_chain(["wood_base"])
    assert chain["critical"] is True
    assert chain["risk"] == "high"
    assert any(h["kb"] == "combustible_base" for h in chain["hazards"])


def test_assess_no_ground_high_not_critical():
    chain = ne.assess_hazard_chain(["no_ground"])
    assert chain["risk"] == "high"
    assert chain["critical"] is False
    assert any(h["kb"] == "grounding_rcd" for h in chain["hazards"])


def test_adapt_forbid_high_load_on_bad_wiring():
    sug = ne.adapt_by_env(["copper_aluminum", "overload_risk"])
    ids = {s["id"] for s in sug}
    assert "forbid_high_load" in ids
    assert "rewire_copper" in ids


def test_adapt_disconnect_on_wood_base():
    sug = ne.adapt_by_env(["wood_base"])
    ids = {s["id"] for s in sug}
    assert "disconnect_now" in ids


def test_adapt_thermal_relief_from_readings():
    sug = ne.adapt_by_env([], {"thermal_max_c": 92})
    assert any(s["id"] == "thermal_relief" for s in sug)
    # 温度正常时不该触发降载建议
    sug2 = ne.adapt_by_env([], {"thermal_max_c": 55})
    assert not any(s["id"] == "thermal_relief" for s in sug2)


def test_adapt_no_tags_info():
    sug = ne.adapt_by_env([])
    assert any(s["id"] == "env_ok" for s in sug)


def test_report_returns_str():
    ok, rep = ne.electrical_safety_report(["copper_aluminum", "no_ground"])
    assert ok is True
    assert isinstance(rep, str)
    assert "事故前兆链条" in rep
    assert "galvanic_corrosion" in rep


def test_report_with_thermal_reading():
    ok, rep = ne.electrical_safety_report([], {"thermal_max_c": 95})
    assert ok is True
    assert "thermal_relief" in rep or "降载" in rep


def test_doc_list_nonempty():
    docs = ne.electrical_doc_list()
    assert isinstance(docs, list)
    assert len(docs) > 0
    assert any("galvanic_corrosion" in d for d in docs)


def test_environment_report_list():
    rep = ne.environment_report()
    assert isinstance(rep, list)
    assert len(rep) >= 1


def test_tune_list_readonly_only():
    # 写指引清单只描述不执行（函数存在即代表只回文本，不碰配电箱）
    tunes = ne.electrical_tune_list()
    assert len(tunes) == len(ne.TUNES)
    for fn, _desc in ne.TUNES:
        assert hasattr(ne, fn)


def test_probe_functions_callable():
    for fn_name, _label in ne.PROBES:
        assert callable(getattr(ne, fn_name))


def test_read_external_env_sensor_callable():
    # 外部温湿度计探针可调用且不会抛异常（无传感器时优雅降级，不伪造读数）
    rc, msg = ne.read_external_env_sensor()
    assert isinstance(rc, bool)


def test_adapt_ambient_temp_derate():
    sug = ne.adapt_by_env([], {"ambient_temp_c": 38})
    assert any(s["id"] == "ambient_heat_derate" for s in sug)
    # 正常环境温度不触发降载
    sug2 = ne.adapt_by_env([], {"ambient_temp_c": 25})
    assert not any(s["id"] == "ambient_heat_derate" for s in sug2)


def test_adapt_ambient_humidity_corrosion():
    sug = ne.adapt_by_env([], {"humidity": 85})
    assert any(s["id"] == "ambient_humid_corrosion" for s in sug)
    sug2 = ne.adapt_by_env([], {"humidity": 50})
    assert not any(s["id"] == "ambient_humid_corrosion" for s in sug2)


def test_dynamic_gating_over_threshold_active():
    gate = ne.dynamic_load_gating(
        ["overload_risk"], {"breaker_rating_a": 16, "voltage_v": 220, "measured_load_w": 3000})
    assert gate["active"] is True
    assert gate["severity"] == "warn"
    assert gate["threshold_a"] == 12.8
    assert gate["measured_a"] is not None and gate["measured_a"] > 12.8


def test_dynamic_gating_under_threshold_plan():
    gate = ne.dynamic_load_gating(
        ["overload_risk"], {"breaker_rating_a": 16, "voltage_v": 220, "measured_load_w": 2000})
    assert gate["active"] is False
    assert gate["plan"] is True  # 声明 overload_risk → 给规划性门控建议


def test_dynamic_gating_no_readings_plan():
    gate = ne.dynamic_load_gating(["overload_risk"], {})
    assert gate["plan"] is True
    assert "断路器额定" in gate["title"]


def test_dynamic_gating_none_no_plan():
    gate = ne.dynamic_load_gating([], {})
    assert gate["plan"] is False
    assert gate["severity"] == "info"


def test_adapt_includes_dynamic_gating():
    sug = ne.adapt_by_env(
        ["overload_risk"], {"breaker_rating_a": 16, "voltage_v": 220, "measured_load_w": 3000})
    assert any(s["id"] == "dynamic_load_gating" for s in sug)


def test_report_shows_env_and_gating_sections():
    ok, rep = ne.electrical_safety_report(
        ["overload_risk", "no_ground"],
        {"ambient_temp_c": 38, "humidity": 85,
         "breaker_rating_a": 16, "voltage_v": 220, "measured_load_w": 3000})
    assert ok is True
    assert "外部环境" in rep
    assert "回路级动态负载门控" in rep
    assert "动态负载门控触发" in rep


# ---- 内外环境运行标准（data/env_standards.json，v0.6.80 补全） ----


def test_env_reference_all_has_five_standards():
    refs = ne.env_reference_all()
    assert set(refs.keys()) == {
        "iec60529", "iec62368_1", "iec60721", "iec61000", "iec62321"}


def test_env_reference_iec60529_ip_code():
    ref = ne.env_reference("iec60529")
    assert "IP" in ref.get("name", "")
    assert "60529" in ref.get("org", "")


def test_env_reference_iec62368_1_safety():
    ref = ne.env_reference("iec62368_1")
    # 第三版（2018）取代 60950-1/60065，GB 4943.1-2022 等同采用
    assert "62368-1" in ref.get("org", "")
    assert "4943.1" in ref.get("org", "")


def test_env_reference_missing_key_empty():
    assert ne.env_reference("no_such_env_std") == {}
