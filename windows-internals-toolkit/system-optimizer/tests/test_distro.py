"""发行版识别与发行注记模块测试（只读；不依赖外部网络）。"""

import pytest

from sysweeper.native import distro


def test_detect_returns_identity():
    rel = distro.detect()
    assert isinstance(rel, dict)
    for k in ("id", "version_id", "pretty", "name"):
        assert k in rel


def test_release_notes_report():
    ok, msg = distro.release_notes(pkg="", limit=6000)
    assert ok is True
    assert "发行版" in msg
    # 至少列出 os-release 字段
    assert "os-release" in msg


def test_release_notes_missing_pkg():
    ok, msg = distro.release_notes(pkg="zzz-no-such-pkg-xyz-9999", limit=2000)
    assert ok is False
    assert "未安装" in msg or "本地注记" in msg


def test_distro_report_alias():
    ok, msg = distro.distro_report()
    assert ok is True
    assert "发行版" in msg


def test_capabilities_report():
    ok, msg = distro.capabilities_report()
    assert ok is True
    assert "识别" in msg
    assert "红线" in msg
    # 应报出本地注记目录是否可用
    assert "/usr/share/doc" in msg


def test_release_notes_specific_pkg_shape():
    # 用一个几乎肯定存在的基底包试探；无论命中与否都应是合法 (bool, str)
    ok, msg = distro.release_notes(pkg="bash", limit=2000)
    assert isinstance(ok, bool)
    assert isinstance(msg, str)
