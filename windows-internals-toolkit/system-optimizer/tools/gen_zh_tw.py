#!/usr/bin/env python3
"""用 OpenCC 从源语言 zh_CN 生成繁体中文（zh_TW）译文目录。

为什么要这个脚本
----------------
源语言是 zh_CN（msgid 即中文）。繁体不是「另一门语言」而是**字形转换**，
手译 137 条既费时又容易与简体源串走偏（改了简体忘了同步繁体）。
用 OpenCC 机械转换，保证繁体与简体**永远同源同义**，后续加串也一条命令就能跟上。

依赖策略「不强求」
----------------
OpenCC 只用于**生成译文**（开发者本地跑一次），编译出的 .mo 进仓库，
**运行时零依赖**——用户机器上没装 OpenCC 也能正常显示繁体。
这与 tools/make_mo.py（零依赖纯 Python 编译器）同一套思路：
把第三方依赖挡在「生成期」，不让它进「运行期」。

用法
----
    pip install opencc-python-reimplemented      # 仅生成期需要
    python3 tools/gen_zh_tw.py                  # 生成 locales/zh_TW/.../sysweeper.po
    python3 tools/make_mo.py                    # 编译成 .mo

转换档位（OpenCC config）：
    s2t   简体 → 繁体（正体字形，不动地区词汇）       ← 默认，技术术语最稳
    s2tw  简体 → 台湾正体（含地区词汇，如「字节」→「位元組」）
    s2twp 简体 → 台湾正体 + 用语习惯（最本地化，术语变动最大）
    s2hk  简体 → 香港繁体
用 `--config s2tw` 切换；默认 s2t 是为了保住系统工具的术语一致性。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCALES = ROOT / "src/python/sysweeper/locales"
DOMAIN = "sysweeper"
TARGET = "zh_TW"


def parse_po(path: Path):
    """读出 (头部行, [(msgid, msgstr), ...])。与 tools/make_mo.py 同一套解析口径。"""
    text = path.read_text(encoding="utf-8")
    header: list[str] = []
    entries: list[tuple[str, str]] = []
    cur_id: str | None = None
    cur_str: str | None = None
    in_header = False

    def commit():
        nonlocal cur_id, cur_str, in_header
        if cur_id is None:
            return
        if in_header:
            in_header = False
        else:
            entries.append((cur_id, cur_str or ""))
        cur_id, cur_str = None, None

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            if cur_id is None:
                header.append(raw)
            continue
        if line.startswith("msgid "):
            commit()
            cur_id = po_unescape("".join(re.findall(r'"([^"]*)"', line)))
            if cur_id == "":
                in_header = True
        elif line.startswith("msgstr "):
            cur_str = po_unescape("".join(re.findall(r'"([^"]*)"', line)))
        elif line.startswith('"'):
            frag = po_unescape("".join(re.findall(r'"([^"]*)"', line)))
            if in_header:
                header.append(raw)
            elif cur_str is not None and cur_id is not None:
                cur_str += frag
            elif cur_id is not None:
                cur_id += frag
    commit()
    return header, entries


def po_unescape(s: str) -> str:
    """PO 串内容 → Python 普通串（只反转义 \\\\/\\" 与常见 \\n \\t，中文原样）。

    与 po_escape 严格互逆；读 .po 必须先反转义再转换——否则文件里已转义的
    反斜杠会被再次 escape，每轮生成翻一倍（真实踩过的坑）。
    """
    out: list[str] = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt == "n":
                out.append("\n")
            elif nxt == "t":
                out.append("\t")
            else:
                out.append(nxt)
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def po_escape(s: str) -> str:
    """PO 字面量转义：反斜杠与双引号。"""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def main() -> int:
    ap = argparse.ArgumentParser(description="用 OpenCC 生成 zh_TW 繁体译文目录")
    ap.add_argument("--config", default="s2t",
                    help="OpenCC 转换档位：s2t(默认)/s2tw/s2twp/s2hk")
    ap.add_argument("--source", default="zh_CN", help="源语言目录（默认 zh_CN）")
    args = ap.parse_args()

    try:
        import opencc  # type: ignore
    except ImportError:
        print("错误：未安装 OpenCC。本脚本仅「生成译文」时需要，运行时不需要。\n"
              "    pip install opencc-python-reimplemented\n"
              "（若 pip 报 externally-managed-environment，加 --break-system-packages）",
              file=sys.stderr)
        return 2

    src_po = LOCALES / args.source / "LC_MESSAGES" / f"{DOMAIN}.po"
    if not src_po.exists():
        print(f"错误：找不到源语言文件 {src_po}", file=sys.stderr)
        return 2

    header, entries = parse_po(src_po)
    if not entries:
        print(f"错误：{src_po} 里没解析到任何条目", file=sys.stderr)
        return 2

    cc = opencc.OpenCC(args.config)
    out_dir = LOCALES / TARGET / "LC_MESSAGES"
    out_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# {TARGET} (sysweeper) — 由 tools/gen_zh_tw.py 用 OpenCC({args.config}) 从 {args.source} 转换生成",
        "# 标准：GNU gettext / PO。编译：tools/make_mo.py",
        "# 注意：这是**字形转换**产物，与简体源串同源同义；改简体后重跑本脚本即可同步。",
        "# 不要手改本文件——手改会在下次生成时被覆盖。要改就改源语言 zh_CN。",
        'msgid ""',
        'msgstr ""',
        '"Project-Id-Version: sysweeper\\n"',
        '"Language: zh_TW\\n"',
        '"MIME-Version: 1.0\\n"',
        '"Content-Type: text/plain; charset=UTF-8\\n"',
        '"Content-Transfer-Encoding: 8bit\\n"',
        '"Plural-Forms: nplurals=1; plural=0;\\n"',
        "",
    ]

    converted = 0
    unchanged = 0
    for msgid, _msgstr in entries:
        if not msgid:
            continue
        converted_text = cc.convert(msgid)
        if converted_text != msgid:
            converted += 1
        else:
            unchanged += 1
        lines.append(f'msgid "{po_escape(msgid)}"')
        lines.append(f'msgstr "{po_escape(converted_text)}"')
        lines.append("")

    (out_dir / f"{DOMAIN}.po").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已生成 {out_dir / (DOMAIN + '.po')}")
    print(f"  条目 {len(entries)} 条：转换 {converted} 条，字形无变化 {unchanged} 条（多为纯英文/数字）")
    print(f"  转换档位 OpenCC={args.config}；下一步：python3 tools/make_mo.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
