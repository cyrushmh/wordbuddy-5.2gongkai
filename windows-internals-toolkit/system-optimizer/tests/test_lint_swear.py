#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/lint_swear.py 脏话检测器自测（外部代码准入前置检查的工具自身守护）

两侧都要守住：
  1. 真脏话必须拦住（含规避写法：音标 cào / 分隔符 c.a.o / 同形字 с.а.о / 中文直写）
  2. 技术词不得误报（minimal / mojibake / Brainfuck / -mabi=lp64d / RFC 作者姓）
误报一旦泛化，这个门禁就会被人关掉，等于没有。
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
_TOOLS = str(ROOT / "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

import lint_swear as L  # noqa: E402


def _scan_text(text, name="sample.txt", tmp_path=None):
    if tmp_path is None:
        import tempfile
        tmp_path = pathlib.Path(tempfile.mkdtemp())
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return L.scan([str(p)])


def test_detects_plain_pinyin(tmp_path):
    res = _scan_text("这个结果真是 wocao 了\n", tmp_path=tmp_path)
    assert res["errors"], "wocao 应被检出"
    assert res["errors"][0]["word"] == "wocao"


def test_detects_chinese_literal(tmp_path):
    res = _scan_text("你这个人真是傻逼\n", tmp_path=tmp_path)
    assert res["errors"], "傻逼 应被检出"
    assert res["errors"][0]["kind"] == "中文直写"


def test_detects_accented_pinyin(tmp_path):
    """带声调音标的规避写法：cào / shǎ bī 去调后必须命中"""
    res = _scan_text("结果真是 cào 了\n", tmp_path=tmp_path)
    assert res["errors"], "cào（带音标）去调后应命中 cao"
    assert res["errors"][0]["word"] == "cao"


def test_detects_separator_evasion(tmp_path):
    """c.a.o / c-a-o 这类标点分隔符规避，归一化后必须命中

    注意：「c a o」用**空格**分隔的写法刻意检不出 —— 归一化若删除空格，
    英文句子会被粘成一团（what the fuck -> whatthefuck）导致真脏话漏网，
    得不偿失。这是已知取舍，不是 bug。
    """
    for s in ("c.a.o", "c-a-o", "c_a_o", "c*a*o"):
        res = _scan_text(f"结果真是 {s} 了\n", tmp_path=tmp_path)
        assert res["errors"], f"{s} 分隔符规避未检出"


def test_detects_homoglyph(tmp_path):
    """西里尔同形字伪装：с.а.о（с 是西里尔）映射后必须命中"""
    res = _scan_text("结果真是 с.а.о 了\n", tmp_path=tmp_path)
    assert res["errors"], "西里尔同形字规避未检出"


def test_detects_english(tmp_path):
    res = _scan_text("what the fuck is this\n", tmp_path=tmp_path)
    assert res["errors"], "fuck 应被检出"


def test_no_false_positive_tech_terms(tmp_path):
    """本仓库高频技术词，一个都不许误报"""
    samples = [
        "python -m sysweeper scan --profile minimal\n",       # nima
        "looksLikeMojibake(decoded)\n",                        # jiba
        "\"id\": \"brainfuck\", \"name\": \"Brainfuck\"\n",    # fuck
        "常用编译参数 -march=rv64gc -mabi=lp64d。\n",          # mabi
        "npm install; marker-end: url(#a)\n",                  # eren
        "const sb = document.getElementById('sidebar')\n",
        "Cao, S. Ning, F. Jounay. January 2014.\n",            # RFC 作者姓
        "J.B. North. December 1970. (Format: TXT, HTML)\n",    # 人名缩写
        "声（梵 shabda）、犹太安息日（Shabbat）\n",
        "const allowOrigin = pinned || origin || '*';\n",      # wori
        "Fetched and registered %d alerts\n",                  # chedan
        "draft-rfced-info-varilength-table-00\n",              # rile
        "FormExtensionAbility extends FormExtensionAbility\n", # mabi
    ]
    for s in samples:
        res = _scan_text(s, tmp_path=tmp_path)
        assert not res["errors"], f"误报：{s!r} -> {res['errors']}"


def test_no_false_positive_cyrillic_translation(tmp_path):
    """纯俄文译文行不得因同形字映射产生假阳性"""
    res = _scan_text('msgstr "Ошибка общего бита чётности, исправлен бит 8"\n',
                     tmp_path=tmp_path)
    assert not res["errors"], f"俄文译文误报：{res['errors']}"


def test_zero_width_reported_as_info(tmp_path):
    """零宽字符是数据污染，报 INFO 而非 ERROR（不挡门，但要看得见）"""
    res = _scan_text("正常文本\u200b含有零宽\n", tmp_path=tmp_path)
    assert not res["errors"]
    assert len(res["infos"]) == 1
    assert res["infos"][0]["kind"] == "零宽字符"


def test_exit_code_clean(tmp_path):
    p = tmp_path / "clean.txt"
    p.write_text("hello world 正常文本\n", encoding="utf-8")
    assert L.main([str(p)]) == 0


def test_exit_code_dirty(tmp_path):
    p = tmp_path / "dirty.txt"
    p.write_text("wocao 这不对\n", encoding="utf-8")
    assert L.main([str(p)]) == 1
