"""压缩 / 归档只读层测试（native/compress.py + tasks/compress.py）。

纪律（对齐 ai-torture-chamber 的「测试用小 fake model、不下载权重」）：
- **造临时目录假数据**，绝不依赖真实家目录，也绝不依赖真实系统状态。
- **不依赖第三方压缩库**：核心断言只用标准库（tar/zip/gz/xz/bz2），
  7z/rar/zstd 即使没装也必须通过——它们本就设计为「缺库则明确跳过」。
- 只验证只读行为：绝不产生任何压缩/解压/删除动作。
"""

from __future__ import annotations

import os
import tarfile
import tempfile
import zipfile

import pytest

from sysweeper.native import compress


@pytest.fixture
def sample_dir(tmp_path):
    """临时目录：一个大文本（高可压）+ 一个 tar.gz + 一个 deflate 的 zip。"""
    big = tmp_path / "big.log"
    line = "2026-10-08 INFO 这是一条可压缩的日志记录 hello world\n"
    big.write_text(line * 40000, encoding="utf-8")
    with tarfile.open(tmp_path / "arc.tar.gz", "w:gz") as tf:
        tf.add(str(big), arcname="big.log")
    with zipfile.ZipFile(tmp_path / "arc.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(str(big), "big.log")
    return str(tmp_path)


def test_kind_of_classifies_correctly():
    """分类口径：已压缩/媒体/文本，决定「还值不值得再压」。"""
    assert compress._kind_of("/a/b.tar.gz") == "compressed"
    assert compress._kind_of("/a/b.zip") == "compressed"
    assert compress._kind_of("/a/b.7z") == "compressed"
    assert compress._kind_of("/a/b.rar") == "compressed"
    assert compress._kind_of("/a/b.png") == "media"      # 已编码，别白压
    assert compress._kind_of("/a/b.mp4") == "media"
    assert compress._kind_of("/a/b.pdf") == "media"
    assert compress._kind_of("/a/b.log") == "text"       # 高可压
    assert compress._kind_of("/a/b.json") == "text"
    assert compress._kind_of("/a/b.bin") == "other"


def test_sample_ratio_on_repetitive_text():
    """重复文本采样压测：压后占比应远小于 1（即确实能省）。"""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "rep.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write("重复重复重复 repeated repeated repeated\n" * 20000)
        ratio = compress._sample_ratio(p)
    assert ratio is not None
    assert 0.0 <= ratio < 0.2, f"重复文本的压后占比应远小于 1，实际 {ratio}"


def test_capabilities_always_cover_stdlib_formats():
    """核心格式走标准库，永远可用；7z/rar/zstd 缺库时明确写「跳过」。"""
    ok, msg = compress.compress_format_capabilities()
    assert ok is True
    assert "tar" in msg and "zip" in msg
    # 标准库三件套必须可用
    assert "标准库 tarfile" in msg or "tarfile" in msg
    # 缺失项必须显式说明，而不是假装支持
    for kw in ("7z", "rar", "zst"):
        assert kw in msg


def test_report_missing_dir_returns_false():
    ok, msg = compress.compress_report(scan_dir="/nonexistent/path/for/test")
    assert ok is False
    assert "目录不存在" in msg


def test_report_empty_dir_returns_false(tmp_path):
    ok, msg = compress.compress_report(scan_dir=str(tmp_path))
    assert ok is False
    assert "未扫描到任何文件" in msg


def test_report_finds_savable_text(sample_dir):
    """大文本应被识别为「可省」，且给出压后占比与可省百分比。"""
    ok, msg = compress.compress_report(scan_dir=sample_dir)
    assert ok is True
    assert "可省" in msg
    # 措辞必须是「压后占比…可省…」，不能只写有歧义的「压缩率 0%」
    assert "压后占比" in msg
    assert "文本/日志/结构化数据" in msg


def test_report_streams_archive_entries(sample_dir):
    """流式读包：tar.gz / zip 都能列出条目数与内部未压缩大小（不解压）。"""
    ok, msg = compress.compress_report(scan_dir=sample_dir)
    assert ok is True
    assert "个条目" in msg
    # tar.gz 与 zip 都是高压缩率的重复文本，应显示「省了」百分比
    assert "省了" in msg or "几乎未压缩" in msg


def test_report_is_read_only(sample_dir):
    """只读承诺：报告必须声明未压缩/未解压/未删除。"""
    ok, msg = compress.compress_report(scan_dir=sample_dir)
    assert ok is True
    assert "未压缩、未解压、未删除" in msg


def test_tasks_registered():
    """compress 任务必须被 registry 收进 all_tasks（否则用户永远看不到）。"""
    from sysweeper.registry import all_tasks

    ids = {t.id for t in all_tasks()}
    for expect in ("compress_formats", "compress_report", "compress_archive_guide"):
        assert expect in ids, f"{expect} 未注册到 registry"


def test_compress_strings_translated_in_all_locales():
    """compress 界面串必须在 7 个语言下都有译文。

    zh_TW 不手译：由 tools/gen_zh_tw.py 用 OpenCC 从 zh_CN 转换，保证与简体同源同义。
    """
    from sysweeper.i18n import get_locale, set_locale

    expected = {
        "zh_CN": "本机压缩格式可读性",
        "zh_TW": "本機壓縮格式可讀性",
        "en": "Readable compression formats",
        "fr": "Formats de compression lisibles",
        "ru": "Читаемые форматы сжатия",
        "de": "Lesbare Kompressionsformate",
        "ja": "本機で読める圧縮形式",
    }
    saved = get_locale()
    try:
        for loc, needle in expected.items():
            set_locale(loc)
            ok, msg = compress.compress_format_capabilities()
            assert ok is True
            assert needle in msg, f"{loc} 未翻译，实际首行：{msg.splitlines()[0]}"
    finally:
        set_locale(saved)


def test_tasks_are_low_risk_and_read_only_actions():
    """三个任务一律 low risk；动作只能是 native 只读或 manual 指引，不得有 shell 写操作。"""
    from sysweeper.registry import all_tasks

    for t in all_tasks():
        if not t.id.startswith("compress_"):
            continue
        assert t.risk == "low"
        for a in t.actions:
            assert a.kind in ("native", "manual"), \
                f"{t.id} 出现非只读动作 {a.kind}（压缩层不得自动写）"
