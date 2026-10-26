"""i18n 新语言框架测试（v0.6.11）。

验证「新语言」是数据+翻译而非代码改动：登记的语言能被 set_locale 加载、
available_locales 列出、list_ui_languages 带 translated 标记；ko_KR 已填的
分类标签确实渲染为韩文。
"""

import pytest

from sysweeper import i18n


@pytest.fixture(autouse=True)
def _reset_locale():
    saved = i18n._current
    saved_trans = i18n._trans
    yield
    i18n._trans = saved_trans
    i18n._current = saved


def test_supported_ui_langs_has_new():
    for code in ("ko_KR", "es_ES", "pt_BR", "it_IT", "vi_VN", "id_ID"):
        assert code in i18n.SUPPORTED_UI_LANGS
        assert i18n.SUPPORTED_UI_LANGS[code]["native"]


def test_available_locales_includes_new():
    avail = i18n.available_locales()
    for code in ("ko_KR", "es_ES", "pt_BR", "it_IT", "vi_VN", "id_ID"):
        assert code in avail


def test_list_ui_languages_marks_translated():
    langs = i18n.list_ui_languages()
    by_code = {d["code"]: d for d in langs}
    assert by_code["zh_CN"]["translated"] is True   # 源语言
    assert by_code["ko_KR"]["translated"] is True    # 已填样例
    # 已建目录（有 .mo）的语言都标记为可用，哪怕多数串回退中文
    assert by_code["es_ES"]["translated"] is True


def test_ko_kr_renders_translated():
    i18n.set_locale("ko_KR")
    assert i18n.get_locale().startswith("ko_KR")
    # 已填的分类标签应渲染为韩文
    assert i18n._("性能优化") == "성능 최적화"
    assert i18n._("硬件优化") == "하드웨어 최적화"
    # 未翻译的串回退源语言（中文）
    assert i18n._("不存在的测试串 xyz") == "不存在的测试串 xyz"


def test_set_locale_unknown_falls_back():
    # 没有 .mo 的任意新语言 → 回退源语言，不崩
    i18n.set_locale("xx_XX")
    assert i18n._("性能优化") == "性能优化"
