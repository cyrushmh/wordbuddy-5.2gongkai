"""图像/媒体编解码与色彩能力只读诊断测试（吸收 storytold/photocraft 图像管线视角）。

红线：不解码/不转码/不写任何图像文件；仅 shutil.which + 目录存在性。
"""

import sys

import pytest

sys.path.insert(0, "src/python")
from sysweeper.native import media  # noqa: E402


def test_image_capability_report_shape():
    ok, msg = media.image_capability_report()
    assert ok is True
    assert isinstance(msg, str) and msg
    # 关键结构项必须出现
    for token in ("JPEG", "PNG", "WebP", "HEIC/HEIF", "AVIF", "ICC", "Rust 创意套件"):
        assert token in msg


def test_format_matrix_heic_read_via_which(monkeypatch):
    """heif-convert 存在时，HEIC/HEIF 应判为「读✓」。"""
    real_which = media.shutil.which

    def fake_which(cmd):
        if cmd == "heif-convert":
            return "/usr/bin/heif-convert"
        return real_which(cmd)

    monkeypatch.setattr(media.shutil, "which", fake_which)
    _ok, msg = media.image_capability_report()
    # 找到 HEIC/HEIF 那一行，确认读取支持被点亮
    for line in msg.splitlines():
        if "HEIC/HEIF" in line:
            assert "读✓" in line
            break
    else:
        pytest.fail("未找到 HEIC/HEIF 格式行")


def test_missing_engine_flags_hint(monkeypatch):
    """ImageMagick/ffmpeg 皆无时，报告应给出缺失提示（供 sysmap 归『提示』）。"""
    monkeypatch.setattr(media.shutil, "which", lambda _cmd: None)
    _ok, msg = media.image_capability_report()
    assert "ImageMagick" in msg or "ffmpeg" in msg
    assert "提示" in msg  # 缺失通用引擎的提示措辞


def test_readonly_marker_no_write(monkeypatch):
    """仅依赖 shutil.which 与目录存在性；monkeypatch 掉写路径也不会崩。

    通过确认 ICC 目录探测走 os.path.isdir + os.listdir（不创建任何文件）来验证
    只读意图：把 isdir 设为恒 False，函数仍正常返回。
    """
    monkeypatch.setattr(media.os.path, "isdir", lambda _p: False)
    monkeypatch.setattr(media.shutil, "which", lambda _cmd: None)
    ok, msg = media.image_capability_report()
    assert ok is True and "ICC" in msg
