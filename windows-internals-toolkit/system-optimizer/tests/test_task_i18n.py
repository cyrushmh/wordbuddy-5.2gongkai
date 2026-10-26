"""任务串（title/desc/caveats/notes）的显示层国际化测试。

背景
----
364 项任务的显示串写在 `tasks/*.py` 的字段里，不在任何 `_()` 字面量中，
静态扫描器抓不到。显示层改用 `Task.display_title()` 等方法过一遍翻译，
msgid 由 `tools/extract_task_strings.py` 入册。本文件守住这条链路：

1. 源语言（zh_CN）显示原文；
2. zh_TW 由 OpenCC 生成 → 真的变繁体（不是回退）；
3. 尚无译文的语言（en/fr/ru/de/ja）**回退中文而不能显示空白**——
   空白是「空 msgstr 被编进 .mo」造成的，比不翻译更糟；
4. 各语言 .po 的头部元数据完好（缺 charset 会让 gettext 按 ASCII 解码而崩）。

不依赖 OpenCC：本文件只验证**已编译好的 .mo**，生成期依赖不进运行时。
"""

from __future__ import annotations

import gettext
from pathlib import Path

import pytest

from sysweeper import i18n, registry

LOCALES = Path(i18n._LOCALE_DIR)
DOMAIN = i18n._DOMAIN
OTHER_LOCALES = ["en", "fr", "ru", "de", "ja"]


@pytest.fixture(autouse=True)
def _restore_locale():
    """每个用例后把语言恢复成源语言，避免污染其他测试。"""
    yield
    i18n.set_locale("zh_CN")


def _sample_tasks(n: int = 40):
    tasks = registry.all_tasks()
    assert len(tasks) > n
    return tasks[:n]


def test_source_locale_shows_original():
    """源语言直接显示原文（msgid 即中文）。"""
    i18n.set_locale("zh_CN")
    for t in _sample_tasks(20):
        assert t.display_title() == t.title
        if t.desc:
            assert t.display_desc() == t.desc


def test_zh_tw_is_really_converted():
    """繁体目录是真转换：多数任务标题与简体原文不同（而不是回退原文）。"""
    i18n.set_locale("zh_TW")
    tasks = _sample_tasks(60)
    changed = sum(1 for t in tasks if t.display_title() != t.title)
    assert changed > len(tasks) * 0.5, (
        f"60 条里只有 {changed} 条被转成繁体——八成是回退了中文，检查 .mo 是否编译")
    # 转换不能把内容弄丢：长度应保持一致（字形转换不改字数）
    for t in tasks:
        assert len(t.display_title()) == len(t.title)


def test_untranslated_locales_fall_back_not_blank():
    """没有译文的语言：回退中文，绝不显示空串。"""
    tasks = _sample_tasks(20)
    for loc in OTHER_LOCALES:
        i18n.set_locale(loc)
        for t in tasks:
            assert t.display_title(), f"{loc}: 标题为空（空 msgstr 被编进 .mo 了）"
            assert t.display_title() == t.title, f"{loc}: 应回退源语言原文"


def test_empty_msgstr_not_compiled_into_mo():
    """未翻译条目不得进入 .mo——否则命中后返回空串，界面一片空白。"""
    for loc in OTHER_LOCALES:
        mo = LOCALES / loc / "LC_MESSAGES" / f"{DOMAIN}.mo"
        assert mo.exists(), f"缺少编译产物 {mo}"
        with open(mo, "rb") as f:
            tr = gettext.GNUTranslations(f)
        catalog = tr._catalog
        blanks = [k for k, v in catalog.items() if k and v == ""]
        assert not blanks, f"{loc}: .mo 里有 {len(blanks)} 条空译文：{blanks[:3]}"


def test_po_headers_keep_charset():
    """每个 .po 的文件头必须带 charset=UTF-8（丢过一次，gettext 直接崩）。"""
    for po in sorted(LOCALES.glob("*/LC_MESSAGES/*.po")):
        head = po.read_text(encoding="utf-8")[:1200]
        assert 'msgid ""' in head, f"{po.name}: 文件头条目缺失"
        assert "charset=UTF-8" in head, f"{po.name}: 缺 charset=UTF-8"


def test_task_strings_are_registered_as_msgid():
    """任务串必须已入册，否则「翻了但词典里没这个词」。"""
    po = LOCALES / "zh_CN" / "LC_MESSAGES" / f"{DOMAIN}.po"
    text = po.read_text(encoding="utf-8")
    missing = [t.title for t in _sample_tasks(30) if f'msgid "{t.title}"' not in text]
    assert not missing, f"这些任务标题还没入册：{missing[:5]}"


def test_caveats_and_notes_are_translated_too():
    """风险提示与注意事项同样过翻译（它们也是给人看的）。"""
    i18n.set_locale("zh_TW")
    checked = 0
    for t in registry.all_tasks():
        for c in t.caveats or []:
            assert t.display_caveats(), "caveats 翻译后不该为空"
            checked += 1
            break
        if checked >= 5:
            break
    for t in registry.all_tasks():
        if t.notes:
            assert len(t.display_notes()) == len(t.notes)
            assert all(t.display_notes())
            break
