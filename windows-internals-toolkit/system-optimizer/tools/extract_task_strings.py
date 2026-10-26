#!/usr/bin/env python3
"""把任务库里「显示给人看」的串抽成 msgid，补进各语言的 .po。

为什么需要它
------------
364 项任务的 title / desc / caveats / notes 是**用户可见文本**，但写在
`tasks/*.py` 的字段里，不在任何 `_()` 调用中——xgettext 这类静态扫描器抓不到
（它们只认 `_("...")` 字面量）。而显示层已经改成 `t.display_title()` 过翻译，
msgid 却还不在译文目录里，等于「翻译了但词典里没这个词」。

本脚本从**运行时加载的任务库**里把串全量抓出来，按 gettext 口径写回 .po：
- 源语言 zh_CN：msgid 入册（msgstr 空——源语言不加载 .mo，直接回退 msgid）。
- 其他语言：msgid 入册、msgstr **留空**（= 回退中文，绝不拿机器翻译充数）。
  空 msgstr 是 gettext 的标准「未翻译」表示，不是 bug。
- zh_TW 由 `tools/gen_zh_tw.py` 用 OpenCC 从本脚本更新后的 zh_CN.po 重新生成。

只**追加**不覆盖：已有的 msgstr（人工翻译过的）一律保留。

用法
----
    python3 tools/extract_task_strings.py            # 追加所有缺的 msgid
    python3 tools/extract_task_strings.py --dry-run  # 只看会加多少，不写
    python3 tools/gen_zh_tw.py && python3 tools/make_mo.py
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "python"))

LOCALES = ROOT / "src" / "python" / "sysweeper" / "locales"
DOMAIN = "sysweeper"
SOURCE = "zh_CN"

# 分类与风险标签也显示在界面上（`[cleanup/low]`），一并入册。
from sysweeper.models import CATEGORIES  # noqa: E402


def task_strings() -> list[str]:
    """任务库全部显示串（去重、保序、去空）。"""
    from sysweeper import registry

    out: list[str] = []
    seen = set()

    def add(s: str):
        # 不 strip：前导/尾随空白是显示内容的一部分（如缩进的列表项）。
        # 早年 strip 过，导致 .po msgid 与运行时 _() 实参对不上、翻译静默失效。
        if s and s not in seen:
            seen.add(s)
            out.append(s)

    for t in registry.all_tasks():
        add(t.title)
        add(t.desc)
        for c in t.caveats or []:
            add(c)
        for n in t.notes or []:
            add(n)
    for label in CATEGORIES.values():
        add(label)
    return out


def source_strings() -> list[str]:
    """扫描源码里的 `_("...")` 字面量（xgettext 的最小可用版）。

    为什么用 ast 而不是正则：正则会把注释里、跨行拼接、f-string 里的东西一起抓进来，
    误报的条目进了 .po 就是永远翻不完的债。**ast 只认真正的 `_` 调用 + 字符串常量**，
    与 GNU xgettext 的关键字口径一致（这里关键字只有 `_`，本工程不使用 gettext 别名）。

    只扫 `src/python/sysweeper/`（运行时代码），tests / tools 不进译文表。
    """
    import ast

    pkg = ROOT / "src" / "python" / "sysweeper"
    out: list[str] = []
    seen: set[str] = set()

    def add(s: str):
        # 同 task_strings()：不 strip，保住缩进等显示空白。
        if s and s not in seen:
            seen.add(s)
            out.append(s)

    for py in sorted(pkg.rglob("*.py")):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        except SyntaxError:
            continue  # 语法坏了的文件跳过，不拖垮整个抽取
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            if isinstance(fn, ast.Name) and fn.id == "_" and node.args:
                a = node.args[0]
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    add(a.value)
    return out


def parse_po(path: Path) -> tuple[list[str], dict[str, str], dict[str, list[str]]]:
    """读出 (头部行, {msgid: msgstr}, {msgid: 其上方的注释行})。

    头部段必须**整段原样保留**：`msgid ""` / `msgstr ""` 与紧跟其后的
    `"Content-Type: ... charset=UTF-8"` 元数据决定了 .mo 的编码。丢掉它们，
    编译出的 .mo 会被 gettext 按 ASCII 解码而崩（真实踩过的坑）。
    条目间的分节注释（如 `# —— bits 层 ——`）也一并保留，方便译者定位。
    """
    if not path.exists():
        return [], {}, {}
    header: list[str] = []
    entries: dict[str, str] = {}
    comments: dict[str, list[str]] = {}
    pending: list[str] = []
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
            entries[cur_id] = cur_str or ""
        cur_id, cur_str = None, None

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            # 还没进入条目区（含文件头）→ 归头部；否则挂到下一条目上
            if in_header or (cur_id is None and not entries):
                header.append(raw)
            else:
                pending.append(raw)
            continue
        if line.startswith("msgid "):
            commit()
            val = po_unescape("".join(re.findall(r'"([^"]*)"', line)))
            if val == "":
                # 文件头条目：必须把 cur_id 记成 ""（而不是留 None），
                # 否则下一次 commit() 认不出它、in_header 关不掉，
                # 会连着吞掉紧随其后的第一个真条目（真实踩过的坑）。
                in_header = True
                cur_id = ""
                header.append(raw)
                continue
            cur_id = val
            comments[cur_id] = pending
            pending = []
            continue
        if line.startswith("msgstr "):
            cur_str = po_unescape("".join(re.findall(r'"([^"]*)"', line)))
            if in_header:
                header.append(raw)
            continue
        if line.startswith('"'):
            if in_header:
                header.append(raw)
            elif cur_str is not None and cur_id is not None:
                cur_str += po_unescape("".join(re.findall(r'"([^"]*)"', line)))
            elif cur_id is not None:
                cur_id += po_unescape("".join(re.findall(r'"([^"]*)"', line)))
    commit()
    return header, entries, comments


def po_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def po_unescape(s: str) -> str:
    """PO 串内容 → Python 普通串（只反转义 \\\\/\\" 与常见 \\n \\t，中文原样）。

    与 po_escape 严格互逆；**读 .po 时必须走本函数**——否则把文件里的
    已转义文本（如 ``C:\\\\Windows``）当字面键，dump 时再 escape 一次，
    反斜杠每轮构建翻一倍（真实踩过的坑：4→8→16→32→64→128）。
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


FALLBACK_HEADER = [
    'msgid ""',
    'msgstr ""',
    '"Project-Id-Version: sysweeper\\n"',
    '"MIME-Version: 1.0\\n"',
    '"Content-Type: text/plain; charset=UTF-8\\n"',
    '"Content-Transfer-Encoding: 8bit\\n"',
]


def dump(header: list[str], entries: dict[str, str],
         comments: dict[str, list[str]], order: list[str]) -> str:
    """按给定顺序写回（先原有条目、后新增），保住头部与分节注释。"""
    head = [h for h in header if h.strip()]
    if not any(h.startswith('msgid ""') for h in head):
        head = FALLBACK_HEADER + ["", *head]
    lines = list(head)
    if lines and lines[-1] != "":
        lines.append("")
    for k in order:
        for c in comments.get(k) or []:
            lines.append(c)
        lines.append(f'msgid "{po_escape(k)}"')
        lines.append(f'msgstr "{po_escape(entries.get(k, ""))}"')
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="抽取任务库显示串到各语言 .po")
    ap.add_argument("--dry-run", action="store_true", help="只统计不写文件")
    ap.add_argument("--locales", default="", help="只处理指定语言（逗号分隔）")
    ap.add_argument("--tasks-only", action="store_true",
                    help="只抽任务定义串，不扫源码里的 _() 调用")
    args = ap.parse_args()

    strings = task_strings()
    print(f"任务库显示串：{len(strings)} 条（title/desc/caveats/notes + 分类标签）")
    if not args.tasks_only:
        src = source_strings()
        print(f"源码 _() 字面量：{len(src)} 条（ast 精确匹配，不用正则猜）")
        for s in src:
            if s not in strings:
                strings.append(s)
        print(f"合计入册：{len(strings)} 条")

    want = [x for x in args.locales.split(",") if x] or sorted(
        p.name for p in LOCALES.iterdir()
        if p.is_dir() and (p / "LC_MESSAGES" / f"{DOMAIN}.po").exists())

    for loc in want:
        po = LOCALES / loc / "LC_MESSAGES" / f"{DOMAIN}.po"
        header, entries, comments = parse_po(po)
        have = set(entries)
        missing = [s for s in strings if s not in have]
        if not missing:
            print(f"  {loc:<6} 已齐全（{len(entries)} 条），无需追加")
            continue
        for s in missing:
            # 源语言的 msgstr 就是它自己（msgid 即中文）；其他语言留空 = 回退源语言
            entries[s] = s if loc == SOURCE else ""
        order = [k for k in entries]
        if args.dry_run:
            print(f"  {loc:<6} 缺 {len(missing)} 条（dry-run，未写）")
            continue
        po.parent.mkdir(parents=True, exist_ok=True)
        po.write_text(dump(header, entries, comments, order), encoding="utf-8")
        print(f"  {loc:<6} 追加 {len(missing)} 条 → {len(entries)} 条"
              f"（msgstr 留空，回退中文；zh_TW 请用 gen_zh_tw.py 生成）")

    print("\n下一步：")
    print("  python3 tools/gen_zh_tw.py     # 繁体自动转换（需 OpenCC，仅生成期）")
    print("  python3 tools/make_mo.py       # 编译 .mo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
