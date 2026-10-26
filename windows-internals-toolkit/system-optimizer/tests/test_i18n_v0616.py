"""i18n 补全验收（v0.6.16）：zh_TW 全量收口 + 6 门新语言核心串落地。

验证「全选」轮次的两类收口：
1. zh_TW 的 .po 必须 0 条未翻译（OpenCC s2tw 收口）；
2. ko_KR/es_ES/pt_BR/it_IT/vi_VN/id_ID 至少已落地分类标签核心串，
   且 .mo 能加载、渲染为非中文。
"""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "src/python")
from sysweeper import i18n


@pytest.fixture(autouse=True)
def _reset_locale():
    """本文件的 set_locale 不得泄漏到后续测试文件（i18n 全局态）。"""
    saved = i18n._current
    saved_trans = i18n._trans
    yield
    i18n._trans = saved_trans
    i18n._current = saved


LOCALE_DIR = i18n._LOCALE_DIR
NEW_LANGS = ("ko_KR", "es_ES", "pt_BR", "it_IT", "vi_VN", "id_ID")
CORE_EXPECT = {
    "ko_KR": {"性能优化": "성능 최적화", "硬件优化": "하드웨어 최적화"},
    "es_ES": {"性能优化": "Optimización de rendimiento"},
    "pt_BR": {"性能优化": "Otimização de desempenho"},
    "it_IT": {"性能优化": "Ottimizzazione delle prestazioni"},
    "vi_VN": {"性能优化": "Tối ưu hóa hiệu năng"},
    "id_ID": {"性能优化": "Optimasi kinerja"},
}


def _parse_po(path):
    entries, cur, key = [], None, None
    for ln in open(path, encoding="utf-8"):
        if ln.startswith("msgid "):
            cur = {"id": ln[6:].strip(), "str": ""}; key = "id"; entries.append(cur)
        elif ln.startswith("msgstr "):
            key = "str"; cur["str"] = ln[7:].strip()
        elif ln.startswith('"') and cur:
            cur[key] += ln.strip()
    out = {}
    for e in entries:
        mid = re.sub(r'^"|"$', "", e["id"])
        mstr = re.sub(r'^"|"$', "", e["str"])
        if mid:
            out[mid] = mstr
    return out


def test_zh_tw_po_fully_translated():
    po = _parse_po(LOCALE_DIR / "zh_TW" / "LC_MESSAGES" / "sysweeper.po")
    untranslated = [m for m, s in po.items() if s == ""]
    assert untranslated == [], f"zh_TW 仍有 {len(untranslated)} 条未翻译"


def test_zh_tw_renders_traditional():
    i18n.set_locale("zh_TW")
    s = i18n._("删除 %TEMP% 与 C:\\Windows\\Temp 下的临时文件。")
    assert "臨時" in s, "zh_TW 未渲染为繁体"


def test_new_langs_core_renders_native():
    for lang in NEW_LANGS:
        i18n.set_locale(lang)
        for src, expect in CORE_EXPECT[lang].items():
            got = i18n._(src)
            assert got == expect, f"{lang}: {src!r} 期望 {expect!r}，实际 {got!r}"


def test_new_langs_po_at_least_core():
    for lang in NEW_LANGS:
        po = _parse_po(LOCALE_DIR / lang / "LC_MESSAGES" / "sysweeper.po")
        done = sum(1 for s in po.values() if s)
        assert done >= 13, f"{lang} 核心串不足（已译 {done}）"


# --------------------------------------------------------------------------
# v0.6.61：PO 转义规范回归（历史缺陷：工具「读不反转义、写再转义」使反斜杠
# 每轮构建翻倍 4→8→16→32→64→128，且每轮追加新变体；.mo 键与运行时 msgid
# 对不上，翻译静默失效。此处守住规范形态与工具互逆性。
# --------------------------------------------------------------------------

def test_po_no_overescaped_backslashes():
    """任一语言 .po 的 msgid/msgstr 行都不得出现 4+ 连续反斜杠（过度转义）。"""
    for d in sorted(LOCALE_DIR.iterdir()):
        po = d / "LC_MESSAGES" / "sysweeper.po"
        if not po.exists():
            continue
        for i, line in enumerate(po.read_text(encoding="utf-8").splitlines(), 1):
            if line.startswith(("msgid ", "msgstr ", '"')):
                assert not re.search(r"\\\\{2,}", line), \
                    f"{po}:{i} 疑似过度转义：{line[:80]}"


def test_po_escape_roundtrip_tools():
    """extract / gen_zh_tw 的 po_escape 与 po_unescape 必须互逆（防再漂移）。"""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))  # noqa: E402
    from extract_task_strings import po_escape, po_unescape  # noqa: E402
    for s in ("删除 %TEMP% 与 C:\\Windows\\Temp 下的临时文件。",
              '他说"你好"然后 C:\\path\\to',
              "普通中文标签\n带换行"):
        assert po_unescape(po_escape(s)) == s, repr(s)


def test_backslash_string_translates_in_zh_tw():
    """含反斜杠的任务串在 zh_TW 必须命中译文（.mo 键与运行时 msgid 一致）。"""
    i18n.set_locale("zh_TW")
    s = i18n._("删除 %TEMP% 与 C:\\Windows\\Temp 下的临时文件。")
    assert "臨時" in s and "\\" in s, f"反斜杠串未命中译文：{s!r}"
