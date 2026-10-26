"""设备长期使用保护子系统（v0.6.30）：文档完整 + 跨平台安全降级 + 引擎纯函数 + CLI 可跑。

验证 durability 模块：
- 知识库（data/durability_docs.json）结构完整、覆盖天气/气候/材料/耐久/保养/水汽异物；
- 在非目标平台（如 Linux 沙箱）下只读探测安全降级、绝不抛异常、不伪造数据；
- 四大引擎（durability_profile / sensor_health_score / build_maintenance_plan /
  auto_optimize_suggestions）为可复现纯函数；
- CLI 子命令 `sysweeper durability` 正常产出。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from sysweeper.native import durability as d
from sysweeper import registry

REPO = Path(__file__).resolve().parents[1]
PY = str(REPO / "src" / "python")


def _env() -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = PY
    return env


def test_durability_doc_loaded():
    refs = d.reference_all()
    assert isinstance(refs, dict) and refs, "durability_docs.json 应已加载且非空"
    for key in ("battery_lithium", "ip_rating", "ashrae_thermal", "storage_smart",
                "sensor_apis", "humidity_ingress", "thermal_throttle",
                "charge_strategy", "maintenance_schedule"):
        assert key in refs, f"durability 知识库应含 {key}"


def test_durability_reference_shape():
    for key, ref in d.reference_all().items():
        assert "protocols" in ref and "interfaces" in ref, (
            f"durability 接口 {key} 缺 protocols/interfaces")
        assert isinstance(ref["protocols"], list) and ref["protocols"]
        assert isinstance(ref["interfaces"], list) and ref["interfaces"]
        assert "advice" in ref and ref.get("advice"), f"durability {key} 缺 advice"


def test_durability_doc_list_nonempty():
    assert list(d.durability_doc_list())


def test_durability_tune_list_nonempty():
    # 写操作仅指引，不代执行——至少应有充电/过热/TRIM/备份/进水指引
    lines = d.durability_tune_list()
    assert lines
    joined = "\n".join(lines)
    for kw in ("充电", "过热", "TRIM", "备份", "进水"):
        assert kw in joined, f"durability 指引应覆盖 {kw}"


def test_durability_engine_pure():
    # 同一输入应得同一输出（纯函数、可复现）
    prof1 = d.durability_profile("heavy", 5, ["high_humidity", "mobile"])
    prof2 = d.durability_profile("heavy", 5, ["high_humidity", "mobile"])
    assert prof1 == prof2
    assert prof1["charge_ceiling_pct"] == 80
    assert prof1["rh_budget"][1] < 60  # 高湿环境收紧湿度预算上限

    readings = {"battery_temp_c": 48, "battery_health_pct": 72, "battery_cycle": 910,
                "storage_used_pct": 96, "storage_life_pct": 55, "ambient_rh": 85,
                "ambient_temp_c": 33, "thermal_max_c": 95, "uptime_days": 120}
    sh1 = d.sensor_health_score(readings)
    sh2 = d.sensor_health_score(dict(readings))
    assert sh1 == sh2
    assert 0 <= sh1["overall"] <= 100
    assert sh1["risk"] in ("low", "mid", "high")

    plan = d.build_maintenance_plan(prof1, sh1, ["high_humidity", "mobile"])
    assert isinstance(plan, list) and plan
    sug = d.auto_optimize_suggestions(prof1, sh1, ["high_humidity", "mobile"])
    assert isinstance(sug, list)


def test_durability_profile_budget_monotonic():
    # 期望年限越长，充电上限越保守（日历老化更需防护）
    short = d.durability_profile("moderate", 2, [])
    long = d.durability_profile("moderate", 6, [])
    assert long["charge_ceiling_pct"] <= short["charge_ceiling_pct"]
    # 高温环境温度预算更紧
    cool = d.durability_profile("moderate", 4, [])
    hot = d.durability_profile("moderate", 4, ["high_temp"])
    assert hot["temp_budget_c"] <= cool["temp_budget_c"]


def test_durability_report_runs():
    ok, rep = d.durability_report("moderate", 4, [])
    assert ok is True
    assert isinstance(rep, str) and rep
    assert "保护报告" in rep


def test_durability_report_default_graceful():
    # 默认画像（无传感器读数）也应安全产出，不抛异常
    ok, rep = d.durability_report()
    assert ok is True and rep


def test_durability_in_registry():
    tks = [t for t in registry.all_tasks() if t.id.startswith("durability_")]
    assert len(tks) >= 5, "durability 任务应已注册"
    for t in tks:
        assert t.platform == "any"


def test_cli_durability_runs():
    r = subprocess.run([sys.executable, "-m", "sysweeper", "durability"],
                       cwd=REPO, capture_output=True, text=True, env=_env())
    assert r.returncode == 0, r.stderr
    assert "设备长期使用保护" in r.stdout
