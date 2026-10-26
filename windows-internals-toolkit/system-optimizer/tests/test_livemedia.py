"""可启动介质制作能力只读诊断测试（吸收 livecd/dvd/bd/usb 制作技术）。

红线：绝不 mkisofs/xorriso 实际构建、绝不 dd 到设备、绝不挂载/解包 ISO、绝不 modprobe——
仅 shutil.which + 目录与 /sys 存在性 + 给定 ISO 的只读元数据。
"""

import sys

import pytest

sys.path.insert(0, "src/python")
from sysweeper.native import livemedia  # noqa: E402


def test_livemedia_report_shape():
    ok, msg = livemedia.livemedia_report()
    assert ok is True
    assert isinstance(msg, str) and msg
    # 不依赖环境的关键结构项必须出现
    for token in ("xorriso", "ISOLINUX", "El Torito", "squashfs-tools",
                  "dd", "UEFI 侧", "CD", "红线"):
        assert token in msg


def test_tool_detected_via_which(monkeypatch):
    """xorriso 被 which 命中时，应判为「已安装」。"""
    real_which = livemedia.shutil.which

    def fake_which(cmd):
        if cmd == "xorriso":
            return "/usr/bin/xorriso"
        return real_which(cmd)

    monkeypatch.setattr(livemedia.shutil, "which", fake_which)
    _ok, msg = livemedia.livemedia_report()
    for line in msg.splitlines():
        if "xorriso" in line and "已安装" in line:
            assert "✓" in line
            break
    else:
        pytest.fail("未找到 xorriso 的已安装行")


def test_missing_squash_flags(monkeypatch):
    """所有工具 which 均为 None 时，squashfs-tools 应标缺失且不崩。"""
    monkeypatch.setattr(livemedia.shutil, "which", lambda _cmd: None)
    ok, msg = livemedia.livemedia_report()
    assert ok is True
    assert "squashfs-tools" in msg
    assert "✗" in msg  # 缺失标记


def test_readonly_marker_no_write(monkeypatch):
    """仅依赖 which + 目录与 /sys 存在性；把 isdir 设为恒 False 也不崩。"""
    monkeypatch.setattr(livemedia.os.path, "isdir", lambda _p: False)
    monkeypatch.setattr(livemedia.shutil, "which", lambda _cmd: None)
    ok, msg = livemedia.livemedia_report()
    assert ok is True and "xorriso" in msg


def test_iso_check_invalid_path_no_run(monkeypatch):
    """传入无效 ISO 路径时，只读返回提示、绝不执行 file/isoinfo/xorriso。"""
    monkeypatch.setattr(livemedia.shutil, "which", lambda _cmd: None)
    ok, msg = livemedia.livemedia_report("/no/such/file.iso")
    assert ok is True
    assert "未传入有效 ISO 路径" in msg
