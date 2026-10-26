"""虚拟化与 GPU 虚拟化只读诊断测试（v0.6.15）。全只读，monkeypatch 喂假 /proc/sys。"""
import sys

import pytest

sys.path.insert(0, "src/python")
from sysweeper.native import virtgpu


def test_virtgpu_report_returns_tuple():
    ok, msg = virtgpu.virtgpu_report()
    assert isinstance(ok, bool) and isinstance(msg, str) and msg


def test_virtgpu_capabilities_markers():
    ok, msg = virtgpu.capabilities_report()
    assert "能力自检" in msg and "virtio-gpu" in msg


def test_hypervisor_detect(monkeypatch):
    monkeypatch.setattr(virtgpu.common, "run",
                        lambda cmd, timeout=5: (0, "flags : fpu vme de pse tsc msr pae mce "
                                                "cx8 apic sep mtrr pge mca cmov pat pse36 clflush "
                                                "mmx fxsr sse sse2 ht syscall nx mmxext fxsr_opt "
                                                "hypervisor vmcb_flush_asid\n")
                        if "cpuinfo" in cmd else (1, ""))
    assert "虚拟化" in virtgpu._hypervisor()


def test_hypervisor_physical(monkeypatch):
    monkeypatch.setattr(virtgpu.common, "run",
                        lambda cmd, timeout=5: (0, "flags : fpu vme de pse tsc msr pae\n")
                        if "cpuinfo" in cmd else (1, ""))
    assert "物理机" in virtgpu._hypervisor()


def test_gpu_cards_filter(monkeypatch):
    # /sys/class/drm 下 card0 是 GPU，card0-VGA-1 / card0-DP-1 是连接器符号链接
    monkeypatch.setattr(virtgpu.common, "run",
                        lambda cmd, timeout=5: (0, "card0\ncard0-VGA-1\ncard0-DP-1\n")
                        if "card" in cmd else (1, ""))
    assert virtgpu._gpu_cards() == ["card0"]


def test_virtio_gpu_true(monkeypatch):
    monkeypatch.setattr(virtgpu.common, "run",
                        lambda cmd, timeout=5: (0, "virtio:00000007-0000-0000-0000-"
                                                "000000000001gpu\n") if "modalias" in cmd else (1, ""))
    assert virtgpu._virtio_gpu() is True
