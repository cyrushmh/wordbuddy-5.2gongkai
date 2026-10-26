"""WSL 环境只读诊断测试（v0.6.15）。全只读，不碰真系统；用 monkeypatch 喂假 /proc。"""
import sys
import types

import pytest

sys.path.insert(0, "src/python")
from sysweeper.native import wsl


def test_wsl_report_returns_tuple():
    ok, msg = wsl.wsl_report()
    assert isinstance(ok, bool)
    assert isinstance(msg, str) and msg


def test_wsl_report_non_wsl(monkeypatch):
    """沙箱 /proc/version 不含 Microsoft → 判为非 WSL。"""
    monkeypatch.setattr(wsl.common, "run",
                        lambda cmd, timeout=5: (0, "Linux version 6.6.117 generic"))
    ok, msg = wsl.wsl_report()
    assert ok is True
    assert "未识别为 WSL" in msg


def test_wsl_version_wsl2(monkeypatch):
    monkeypatch.setattr(wsl.common, "run",
                        lambda cmd, timeout=5: (0, "5.15.167.4-microsoft-standard-WSL2"
                                                if "osrelease" in cmd else "initrd"
                                                if "cmdline" in cmd else ""))
    assert wsl._wsl_version() == "2"


def test_wsl_version_wsl1(monkeypatch):
    monkeypatch.setattr(wsl.common, "run",
                        lambda cmd, timeout=5: (0, "4.4.0-22621-Microsoft"
                                                if "osrelease" in cmd else ""))
    assert wsl._wsl_version() == "1"


def test_wsl_capabilities_markers():
    ok, msg = wsl.capabilities_report()
    assert ok is True
    assert "能力自检" in msg
    assert "wsl2-linux-kernel" in msg or "WSL2" in msg


def test_wsl_systemd_enabled_true(monkeypatch):
    monkeypatch.setattr(wsl, "_read_file",
                        lambda p: (True, "[boot]\nsystemd=true") if p == "/etc/wsl.conf" else (False, ""))
    assert "已启用" in wsl._systemd_enabled()
