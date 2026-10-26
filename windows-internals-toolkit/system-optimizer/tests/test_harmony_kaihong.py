"""KaihongOS 发行版只读识别测试（深开鸿 / 基于 OpenHarmony）。

红线：不连设备、绝不改配置；只读 /etc/os-release、/sys/fs/selinux/enforce、shutil.which。
"""

import io
import sys

import pytest

sys.path.insert(0, "src/python")
from sysweeper.native import harmony  # noqa: E402


def test_kaihong_report_not_detected_on_foreign_host():
    """本机（非 KaihongOS）应降级：ok=False 且给出指引。"""
    ok, msg = harmony.kaihong_report()
    assert ok is False
    assert "未检测到 KaihongOS" in msg


def test_detect_kaihong_positive(monkeypatch):
    """伪造 /etc/os-release 含 kaihong 标记，应识别为 KaihongOS（Stan）。"""
    def fake_open(path, *a, **k):
        p = str(path)
        if p == "/etc/os-release":
            return io.StringIO(
                'ID=kaihongos\nNAME="KaihongOS"\nVERSION_ID="5.0.1"\n'
                'PRETTY_NAME="KaihongOS 5.0.1 Stan."\n')
        raise FileNotFoundError(p)

    monkeypatch.setattr("builtins.open", fake_open)
    monkeypatch.setattr(harmony.glob, "glob", lambda _p: [])
    monkeypatch.setattr(harmony.shutil, "which", lambda _c: None)

    info = harmony.detect_kaihong()
    assert info["is_kaihong"] is True
    assert "Stan" in info["variant"]
    assert info["hdc"] is False


def test_kaihong_report_positive(monkeypatch):
    """正向路径：报告 ok=True 且含 KaihongOS / variant / SELinux 降级措辞。"""
    def fake_open(path, *a, **k):
        p = str(path)
        if p == "/etc/os-release":
            return io.StringIO(
                'ID=kaihongos\nNAME="KaihongOS"\nVERSION_ID="5.0.1"\n'
                'PRETTY_NAME="KaihongOS 5.0.1 Stan."\n')
        raise FileNotFoundError(p)

    monkeypatch.setattr("builtins.open", fake_open)
    monkeypatch.setattr(harmony.glob, "glob", lambda _p: [])
    monkeypatch.setattr(harmony.shutil, "which", lambda _c: None)

    ok, msg = harmony.kaihong_report()
    assert ok is True
    assert "KaihongOS" in msg
    assert "Stan" in msg
    assert "SELinux" in msg  # 降级措辞（/sys/fs/selinux 未挂载）


def test_kaihong_in_probes_and_env_report():
    """kaihong_report 已纳入 harmony.PROBES，并被 environment_report 引用。"""
    names = [fn for fn, _lab in harmony.PROBES]
    assert "kaihong_report" in names
    env = harmony.environment_report()
    assert any("KaihongOS" in line for line in env)
