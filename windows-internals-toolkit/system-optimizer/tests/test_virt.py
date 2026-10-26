"""virt 子系统测试：虚拟化层识别 / 优雅降级计划 / 端到端报告 / 任务注册。"""
from __future__ import annotations

import json
import os

from sysweeper.native import virt as ncf
from sysweeper.tasks import virt as tcf


def _data_path():
    return os.path.join(os.path.dirname(ncf.__file__), "..", "data", "virt_docs.json")


def test_knowledge_base_loads():
    raw = open(_data_path(), encoding="utf-8").read()
    data = json.loads(raw)
    for key in ("virt_overview", "kvm_qemu", "vmware", "virtualbox", "hyperv",
                "xen", "container", "wsl"):
        assert key in data, f"缺少虚拟化知识 {key}"
        assert data[key].get("advice")


def test_detect_hypervisor_tuple():
    ok, info = ncf.detect_hypervisor()
    assert ok is True
    assert "env" in info
    assert info["env"] in dict(ncf.HYPERVISORS)


def test_virt_environment_in_registry():
    env = ncf.virt_environment()
    assert env in dict(ncf.HYPERVISORS)


def test_degradation_plan_tiers():
    # 纯函数，按 env 给出确定档位
    bare = ncf.degradation_plan("baremetal")
    assert bare[0]["tier"] == "full"
    vm = ncf.degradation_plan("kvm")
    assert vm[0]["tier"] == "vm_degraded"
    cont = ncf.degradation_plan("container")
    assert cont[0]["tier"] == "strong_isolated"
    unk = ncf.degradation_plan("unknown")
    assert unk[0]["tier"] == "conservative"


def test_environment_report_returns_lines():
    lines = ncf.environment_report()
    assert isinstance(lines, list) and lines[0].startswith("虚拟机环境")


def test_virt_report_markers():
    ok, rep = ncf.virt_report([])
    assert ok is True
    assert "虚拟机环境报告" in rep
    assert "优雅降级计划" in rep
    assert "安全不变量" in rep
    # 自动识别也能产出非空报告
    ok2, rep2 = ncf.virt_report(None, {"hypervisor": {"env": "kvm", "method": "test"}})
    assert ok2 and "KVM" in rep2


def test_tasks_registered():
    ids = {t.id for t in tcf.TASKS}
    assert {"virt_report", "virt_guest_tools_guidance"} <= ids
    for t in tcf.TASKS:
        assert t.risk == "low"
        assert t.platform == "any"
