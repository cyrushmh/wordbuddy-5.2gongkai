"""chrono 子系统测试：知识库 / 量子观测透镜 / 时间·空间·施时空组合·未来兼容 / 全维度循环管理器。"""
from __future__ import annotations

import json
import os

import pytest

from sysweeper.native import chrono as ncf
from sysweeper.tasks import chrono as tcf


def _data_path():
    return os.path.join(os.path.dirname(ncf.__file__), "..", "data", "chrono_theory_docs.json")


def test_knowledge_base_loads():
    # 知识库 JSON 必须可解析且含 6 个理论主题
    raw = open(_data_path(), encoding="utf-8").read()
    data = json.loads(raw)
    for key in ("quantum_principles", "computer_principles", "time_theory",
                "space_theory", "spacetime_theory", "future_compat"):
        assert key in data, f"缺少理论主题 {key}"
        assert data[key].get("protocols") and data[key].get("advice")


def test_reference_accessors():
    assert ncf.reference("time_theory")["name"]
    assert ncf.reference_all()  # 全部主题
    assert ncf.reference("nonexistent") == {}  # 未知 key 安全返回空


def test_probes_callable():
    for fn_name, _label in ncf.PROBES:
        assert callable(getattr(ncf, fn_name))


def test_environment_report_returns_lines():
    lines = ncf.environment_report()
    assert isinstance(lines, list) and lines[0].startswith("时空与全维度")


def test_doc_and_tune_lists():
    docs = ncf.chrono_doc_list()
    assert any("quantum" in d.lower() or "时间" in d for d in docs)
    tunes = ncf.chrono_tune_list()
    assert len(tunes) == len(ncf.TUNES)


def test_cycle_dimensions_round_robin():
    """全时空全维度循环往复：周而复始、每轮全维覆盖、无差别。"""
    c = ncf.cycle_dimensions(ncf.DIMENSION_REGISTRY, max_rounds=3)
    assert c["principle"] == "循环往复，周而复始，亦复如是"
    assert len(c["dimensions"]) == 11
    assert c["rounds"] == 3
    # 末维之后回到首维 = 周而复始
    assert c["schedule"][0][-1] == "compat"
    assert c["schedule"][1][0] == "time"
    # 每轮覆盖全部维度、序列一致
    assert c["schedule"][0] == c["schedule"][1] == c["schedule"][2]
    assert len(c["schedule"][0]) == 11


def test_cycle_dimensions_subset_and_single_round():
    sub = [d for d in ncf.DIMENSION_REGISTRY if d[0] in ("time", "space")]
    c = ncf.cycle_dimensions(sub, max_rounds=1)
    assert c["rounds"] == 1
    assert c["schedule"][0] == ["time", "space"]


def test_assess_time_domain_degradation():
    sug = ncf.assess_time_domain([], {})  # 无读数 → 退化观测指引
    assert any(s["id"] == "time_readonly" for s in sug)
    assert all(s["action_type"] == "guidance" for s in sug)


def test_assess_time_domain_eol_flag():
    sug = ncf.assess_time_domain([], {"time_domain": {"uptime_days": 2000, "lifecycle": "eol_risk"}})
    assert any(s["id"] == "time_eol" and s["severity"] == "warning" for s in sug)


def test_assess_space_domain_numa():
    sug = ncf.assess_space_domain([], {"space_domain": {"numa_nodes": 2, "mem_total_kb": 16 * 1048576}})
    assert any(s["id"] == "numa_aware" for s in sug)
    assert any(s["id"] == "mem_budget" for s in sug)


def test_compose_spacetime_pairing():
    sug = ncf.compose_spacetime([], {"time_domain": {"lifecycle": "steady"},
                                    "space_domain": {"numa_nodes": 1}})
    assert any(s["id"] == "causal_pair" for s in sug)
    assert any(s["id"] == "entangle_observe" for s in sug)


def test_assess_future_compat_eol_and_pq():
    sug = ncf.assess_future_compat([], {})
    assert any(s["id"] == "eol_track" for s in sug)
    assert any(s["id"] == "pq_migrate" for s in sug)


def test_chrono_report_round_trip():
    ok, rep = ncf.chrono_report(["time", "space"])
    assert ok is True
    assert "时空与全维度" in rep
    assert "循环往复，周而复始，亦复如是" in rep
    assert "全维度" in rep
    assert "安全不变量" in rep  # 只读红线落款


def test_chrono_report_no_args():
    ok, rep = ncf.chrono_report()
    assert ok and "全维度" in rep


def test_read_quantum_lens_no_hardware():
    ok, info = ncf.read_quantum_lens()
    assert ok and "superposition" in info and "post_quantum" in info


def test_tasks_registered():
    ids = {t.id for t in tcf.TASKS}
    assert {"chrono_report", "chrono_time_guidance", "chrono_space_guidance",
            "chrono_future_guidance"} <= ids
    for t in tcf.TASKS:
        assert t.risk == "low"
        assert t.category == "maintenance"


def test_tasks_in_registry():
    from sysweeper import registry
    reg_ids = {t.id for t in registry.all_tasks() if t.id.startswith("chrono_")}
    assert len(reg_ids) == 4


def test_subsystem_registered():
    from sysweeper.native import subsystems
    assert "chrono" in subsystems.ALL_KEYS
    sub = subsystems.BY_KEY["chrono"]
    assert sub.module == "chrono" and sub.fn == "chrono_report"
