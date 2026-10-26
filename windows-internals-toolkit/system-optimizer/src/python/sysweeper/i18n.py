"""sysweeper 国际化（i18n）支持。

设计原则（呼应项目「中文优先、界面可读、后台不变」）
----------------------------------------------------
- 源语言 = 简体中文（zh_CN）：所有用户可见串以中文书写，即 gettext 的 msgid。
- 默认语言 = zh_CN（源语言）：不加载 .mo，直接回退到 msgid，保证零配置即中文。
- 仅在显式指定时才切换：环境变量 ``SYSWEEPER_LOCALE`` 或 CLI ``--locale``。
  不做基于 ``LANG`` 的自动探测——避免测试/CI 环境因 ``LANG=en`` 而意外翻译、破坏断言。
- 机器数据（opcode 助记符 add/mov、寄存器名 x0/rax、字节等）属于「后台」，不翻译。

标准
----
- GNU gettext / PO 文件格式（msgid/msgstr、charset=UTF-8、Content-Type）。
- 目录约定：``locales/<语言>/LC_MESSAGES/<domain>.mo``。
- 完整工作流、支持语言与扩展计划见 ``docs/本地化计划.md``。
"""
from __future__ import annotations

import gettext
import os
from pathlib import Path

_LOCALE_DIR = Path(__file__).resolve().parent / "locales"
_DOMAIN = "sysweeper"
_SOURCE_LOCALE = "zh_CN"

# 已登记（或计划登记）的界面语言清单。源语言 zh_CN 永远在列且不依赖 .mo。
# 新增语言只需在此登记 + 在 locales/ 下建好 .po/.mo 即可，无需改任何业务逻辑。
# 这是「新语言」框架：加一种 UI 语言是数据 + 翻译，不是代码改动。
SUPPORTED_UI_LANGS = {
    "zh_CN": {"english": "Chinese (Simplified)", "native": "简体中文", "region": "CN"},
    "zh_TW": {"english": "Chinese (Traditional)", "native": "繁體中文", "region": "TW"},
    "en":    {"english": "English", "native": "English", "region": "US"},
    "en_US": {"english": "English (United States)", "native": "English", "region": "US"},
    "fr":    {"english": "French", "native": "Français", "region": "FR"},
    "fr_FR": {"english": "French (France)", "native": "Français", "region": "FR"},
    "de":    {"english": "German", "native": "Deutsch", "region": "DE"},
    "de_DE": {"english": "German (Germany)", "native": "Deutsch", "region": "DE"},
    "ru":    {"english": "Russian", "native": "Русский", "region": "RU"},
    "ru_RU": {"english": "Russian (Russia)", "native": "Русский", "region": "RU"},
    "ja":    {"english": "Japanese", "native": "日本語", "region": "JP"},
    "ja_JP": {"english": "Japanese (Japan)", "native": "日本語", "region": "JP"},
    # ---- v0.6.11 新增登记（框架就绪，翻译按需填充）----
    "ko_KR": {"english": "Korean", "native": "한국어", "region": "KR"},
    "es_ES": {"english": "Spanish (Spain)", "native": "Español", "region": "ES"},
    "pt_BR": {"english": "Portuguese (Brazil)", "native": "Português", "region": "BR"},
    "it_IT": {"english": "Italian", "native": "Italiano", "region": "IT"},
    "vi_VN": {"english": "Vietnamese", "native": "Tiếng Việt", "region": "VN"},
    "id_ID": {"english": "Indonesian", "native": "Bahasa Indonesia", "region": "ID"},
}

# 当前已加载的翻译对象；未加载（源语言或找不到 .mo）时为 None。
_trans = None
_current = _SOURCE_LOCALE


def set_locale(locale: str | None = None) -> str:
    """设定当前语言，返回最终生效的语言码。

    locale 为 None 时：优先读环境变量 ``SYSWEEPER_LOCALE``，否则保持默认源语言。
    解析顺序：先试完整语言码（en_US），再退到语言部分（en），最后回退源语言。
    """
    global _trans, _current
    if locale is None:
        locale = os.environ.get("SYSWEEPER_LOCALE") or _SOURCE_LOCALE
    locale = (locale or _SOURCE_LOCALE).replace("-", "_")
    _current = locale
    tried = [locale]
    if "_" in locale:
        tried.append(locale.split("_", 1)[0])
    for cand in tried:
        try:
            _trans = gettext.translation(
                _DOMAIN, str(_LOCALE_DIR), languages=[cand], fallback=False
            )
            return _current
        except FileNotFoundError:
            continue
    _trans = None  # 没有对应 .mo → 回退到源语言（msgid 原样返回）
    return _current


def get_locale() -> str:
    return _current


def available_locales() -> list[str]:
    """已提供翻译目录的语言码列表（不含源语言 zh_CN）。"""
    out = []
    for d in sorted(_LOCALE_DIR.iterdir()) if _LOCALE_DIR.exists() else []:
        if d.is_dir() and (d / "LC_MESSAGES" / (_DOMAIN + ".mo")).exists():
            out.append(d.name)
    return out


def list_ui_languages() -> list[dict]:
    """返回所有已登记 UI 语言的展示信息（含是否已有译文 .mo）。

    用于 CLI `--locale` 帮助与 GUI 语言选择：列出「能切到哪些语言」，
    已提供翻译的高亮、只登记未翻译的标「待填充」。
    """
    have = set(available_locales())
    out = []
    for code, meta in SUPPORTED_UI_LANGS.items():
        out.append({
            "code": code,
            "english": meta["english"],
            "native": meta["native"],
            "region": meta.get("region", ""),
            "translated": code == _SOURCE_LOCALE or code in have,
        })
    return out


def _(message: str) -> str:
    """翻译用户可见串；无 .mo 时原样返回（即源语言）。"""
    if _trans is None:
        return message
    return _trans.gettext(message)


def ngettext(singular: str, plural: str, n: int) -> str:
    if _trans is None:
        return singular if n == 1 else plural
    return _trans.ngettext(singular, plural, n)
