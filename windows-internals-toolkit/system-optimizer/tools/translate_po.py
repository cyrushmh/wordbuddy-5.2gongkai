#!/usr/bin/env python3
"""用离线翻译引擎（argos-translate）把未翻译的 .po 条目补齐。

这是 v0.6.16「全选」轮次留给 6 门新语言的收口工具：zh_TW 已用 OpenCC 收口，
ko_KR/es_ES/pt_BR/it_IT/vi_VN/id_ID 已落地分类标签核心串；其余约 2000 条/语言
可由本脚本在有 argos-translate 的环境里一键补齐。

用法：
    python tools/translate_po.py es_ES          # 只补某语言
    python tools/translate_po.py --all           # 补 locales/ 下所有未完成的 .po
    python tools/translate_po.py es_ES --dry     # 仅统计未翻译条数，不写盘

前置：
    pip install argos-translate
    # 首次运行会自动下载 zh-><目标> 模型（约 50–90 MB/语言）；
    # 离线环境请先在有网处装好模型再拷到本机缓存。

红线（与项目一致）：只读 .po / 写回 .po，绝不触碰系统、绝不 eval。
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCALES = ROOT / "src" / "python" / "sysweeper" / "locales"

# 目标语言码 -> argos 的 ISO-639-1（zh 为源）
ARGOS_CODE = {
    "ko_KR": "ko", "es_ES": "es", "pt_BR": "pt", "it_IT": "it",
    "vi_VN": "vi", "id_ID": "id", "fr": "fr", "de": "de", "ru": "ru",
    "ja": "ja", "en": "en",
}
SRC = "zh"


def _parse(path: Path):
    entries, cur, key = [], None, None
    for ln in open(path, encoding="utf-8"):
        if ln.startswith("msgid "):
            cur = {"id": _unescape(ln[6:].strip()).strip('"'), "str": ""}; key = "id"; entries.append(cur)
        elif ln.startswith("msgstr "):
            key = "str"; cur["str"] = _unescape(ln[7:].strip()).strip('"')
        elif ln.startswith('"') and cur:
            cur[key] += _unescape(ln.strip()).strip('"')
    return entries


def _unescape(s: str) -> str:
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == "\\" and i + 1 < n:
            nx = s[i + 1]
            if nx == "n": out.append("\n"); i += 2; continue
            if nx == "t": out.append("\t"); i += 2; continue
            if nx == "\\": out.append("\\"); i += 2; continue
            if nx == '"': out.append('"'); i += 2; continue
        out.append(c); i += 1
    return "".join(out)


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")


def _has_cjk(s: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


def _load_translator(target_code: str):
    try:
        import argostranslate.package as pkg
        import argostranslate.translate as tr
    except ImportError:
        sys.exit("未安装 argos-translate：pip install argos-translate 后再运行本脚本")
    packages = pkg.get_available_packages()
    p = next((x for x in packages if x.from_code == SRC and x.to_code == target_code), None)
    if p is None:
        print(f"  下载 zh->{target_code} 模型…")
        pkg.update_package_index()
        packages = pkg.get_available_packages()
        p = next((x for x in packages if x.from_code == SRC and x.to_code == target_code), None)
        if p is None:
            sys.exit(f"找不到 zh->{target_code} 模型，请手动安装 argos 模型")
        pkg.install_from_path(p.download())
    return lambda text: tr.translate(text, SRC, target_code)


def _fill(locale: str, translate, dry: bool) -> tuple:
    po = LOCALES / locale / "LC_MESSAGES" / "sysweeper.po"
    if not po.exists():
        print(f"跳过 {locale}：无 {po}")
        return (0, 0)
    lines = open(po, encoding="utf-8").read().split("\n")
    cur_id, in_id, filled, skipped = None, False, 0, 0
    out = []
    for ln in lines:
        if ln.startswith("msgid "):
            cur_id = _unescape(ln[6:].strip()); in_id = True; out.append(ln); continue
        if ln.startswith("msgstr "):
            in_id = False
            if cur_id and ln.strip() == 'msgstr ""':
                if _has_cjk(cur_id):
                    if dry:
                        out.append(ln); skipped += 1
                    else:
                        out.append('msgstr "' + _escape(translate(cur_id)) + '"'); filled += 1
                else:
                    out.append(ln)  # 机器数据：保持原样（回退 msgid）
            else:
                out.append(ln)
            cur_id = None; continue
        if ln.startswith('"') and in_id:
            cur_id += _unescape(ln.strip()); out.append(ln); continue
        out.append(ln)
    if not dry and filled:
        open(po, "w", encoding="utf-8").write("\n".join(out))
    return (filled, skipped)


def main() -> int:
    ap = argparse.ArgumentParser(description="用 argos-translate 补齐 .po 未翻译条目")
    ap.add_argument("locale", nargs="?", help="语言码，如 es_ES；与 --all 互斥")
    ap.add_argument("--all", action="store_true", help="处理 locales/ 下所有 ARGOS_CODE 中的语言")
    ap.add_argument("--dry", action="store_true", help="仅统计未翻译条数，不写盘")
    args = ap.parse_args()
    targets = list(ARGOS_CODE) if args.all else ([args.locale] if args.locale else [])
    if not targets:
        ap.error("需指定 locale 或 --all")
    total = 0
    for locale in targets:
        if locale not in ARGOS_CODE:
            print(f"跳过 {locale}：未登记 argos 目标码"); continue
        if args.dry:
            po = LOCALES / locale / "LC_MESSAGES" / "sysweeper.po"
            ents = _parse(po)
            left = sum(1 for e in ents if e["id"] and e["str"] == "" and _has_cjk(_unescape(e["id"])))
            print(f"{locale}: 未翻译（含中文）{left} 条"); total += left
            continue
        print(f"=== {locale} ===")
        translate = _load_translator(ARGOS_CODE[locale])
        filled, _ = _fill(locale, translate, dry=False)
        total += filled
        print(f"  {locale}: 补齐 {filled} 条")
    if not args.dry and total:
        print("重新编译 .mo …")
        subprocess.run([sys.executable, str(ROOT / "tools" / "make_mo.py")], check=False)
    print(f"完成：共处理 {total} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
