#!/usr/bin/env python3
"""一次性修复：PO 反斜杠过度转义（历史构建缺陷的损害回收）。

背景：extract_task_strings.py / gen_zh_tw.py 旧版「读不反转义、写再转义」，
每轮构建把 .po 里已转义的反斜杠翻一倍（4→8→16→32→64→128），且每轮追加一个
新的转义变体——13 个语言全部中招，.mo 键与运行时 msgid 对不上，翻译静默失效。

本脚本（工具已修好后只需跑一次）：
  1. 容错解析每个 .po（头段原样保留，注释挂回条目）；
  2. 折叠：文件里任意 2+ 连续反斜杠规范成 2（即「一个真实反斜杠」的 PO 形式），
     再按标准 PO 反转义 → 真实串；
  3. 按真实 msgid 去重（保序；msgstr 取首个非空）；
  4. 以规范转义写回。

之后由修好的 gen_zh_tw.py 重生成 zh_TW、make_mo.py 重编译全部 .mo。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCALES = ROOT / "src/python/sysweeper/locales"
DOMAIN = "sysweeper"

_VAL_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')


def _frag_vals(line: str) -> str:
    return "".join(_VAL_RE.findall(line))


def po_unescape(s: str) -> str:
    """PO 串内容 → 真实串（只反转义 \\\\/\\" 与常见 \\n \\t，中文原样）。"""
    out: list[str] = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            out.append("\n" if nxt == "n" else "\t" if nxt == "t" else nxt)
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def po_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def collapse_overescape(raw: str) -> str:
    """文件形态：任意 2+ 连续反斜杠折叠为 2（单反斜杠的规范 PO 形式）。

    历史缺陷是「倍数翻倍」（4/8/16/32/64/128），折叠回 2 即恢复本意；
    本来就正确的（恰好 2）不受影响。
    """
    return re.sub(r"\\{2,}", r"\\\\", raw)


def split_file(lines):
    """→ (header_lines, entries)；entry = (comments, true_id, true_str)。

    头段（文件注释 + msgid ""/msgstr "" + 元数据行）原样保留；
    条目间的注释行按行序挂到紧随其后的条目上。
    """
    header: list[str] = []
    entries: list[tuple[list[str], str, str]] = []
    pending: list[str] = []
    cur_id: str | None = None
    cur_str: str | None = None
    in_header = False
    seen_entry = False

    def commit():
        nonlocal cur_id, cur_str
        if cur_id is None:
            return
        if seen_entry and cur_id != "":
            entries.append((pending, cur_id, cur_str or ""))
        cur_id, cur_str = None, None

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            if cur_id is None:
                header.append(raw)
            else:
                pending.append(raw)
            continue
        if line.startswith("msgid "):
            commit()
            val = po_unescape(collapse_overescape(_frag_vals(line)))
            if val == "" and not seen_entry:
                in_header = True
                header.append(raw)
                cur_id = ""
                continue
            in_header = False
            seen_entry = True
            cur_id = val
            cur_str = None
            pending = []
            continue
        if line.startswith("msgstr "):
            val = po_unescape(collapse_overescape(_frag_vals(line)))
            if in_header or cur_id == "":
                header.append(raw)
                cur_id = None
                continue
            cur_str = val
            continue
        if line.startswith('"'):
            if in_header or cur_id == "":
                header.append(raw)
                continue
            frag = po_unescape(collapse_overescape(_frag_vals(line)))
            if cur_str is not None:
                cur_str += frag
            elif cur_id is not None:
                cur_id += frag
    commit()
    # pending 归属修正：上面的 append 发生在 cur_str 就绪后，pending 已被清空，
    # 这里按行序二次扫描把注释挂回（第一次扫描只用于切头/条目）。
    return header, _reattach_comments(lines)


def _reattach_comments(lines):
    entries: list[tuple[list[str], str, str]] = []
    pending: list[str] = []
    cur_id: str | None = None
    cur_str: str | None = None
    in_header = False
    seen_entry = False

    def commit():
        nonlocal cur_id, cur_str
        if cur_id is None:
            return
        if seen_entry and cur_id != "":
            entries.append((pending, cur_id, cur_str or ""))
        cur_id, cur_str = None, None

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            if cur_id is not None:
                pending.append(raw)
            continue
        if line.startswith("msgid "):
            commit()
            val = po_unescape(collapse_overescape(_frag_vals(line)))
            if val == "" and not seen_entry:
                in_header = True
                cur_id = ""
                continue
            in_header = False
            seen_entry = True
            cur_id = val
            cur_str = None
            pending = []
            continue
        if line.startswith("msgstr "):
            val = po_unescape(collapse_overescape(_frag_vals(line)))
            if in_header or cur_id == "":
                cur_id = None
                continue
            cur_str = val
            continue
        if line.startswith('"'):
            if in_header or cur_id == "":
                continue
            frag = po_unescape(collapse_overescape(_frag_vals(line)))
            if cur_str is not None:
                cur_str += frag
            elif cur_id is not None:
                cur_id += frag
    commit()
    # 注释重挂：第一遍只切分，第二遍按「msgid 出现顺序」把累积 pending 挂上
    out: list[tuple[list[str], str, str]] = []
    idx = 0
    pend: list[str] = []
    for raw in lines:
        line = raw.strip()
        if line.startswith("#") and idx < len(entries):
            pend.append(raw)
            continue
        if line.startswith("msgid ") and idx < len(entries):
            _c, mid, mstr = entries[idx]
            out.append((pend, mid, mstr))
            pend = []
            idx += 1
    if idx < len(entries):
        out.extend(entries[idx:])
    return out


def repair(path: Path) -> tuple[int, int, int]:
    text = path.read_text(encoding="utf-8")
    header, entries = split_file(text.splitlines())
    seen: dict[str, tuple[list[str], str]] = {}
    order: list[str] = []
    over = 0
    for _c, mid, mstr in entries:
        if re.search(r"\\{4,}", po_escape(mid)):
            over += 1
        if mid in seen:
            comments, old = seen[mid]
            if not old and mstr:
                seen[mid] = (comments, mstr)
            continue
        seen[mid] = (_c, mstr)
        order.append(mid)
    lines = [h for h in header]
    if lines and lines[-1].strip():
        lines.append("")
    for mid in order:
        comments, mstr = seen[mid]
        for c in comments:
            lines.append(c)
        lines.append(f'msgid "{po_escape(mid)}"')
        lines.append(f'msgstr "{po_escape(mstr)}"')
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(entries), len(order), over


def main() -> int:
    total_before = total_after = total_over = 0
    for d in sorted(LOCALES.iterdir()):
        po = d / "LC_MESSAGES" / f"{DOMAIN}.po"
        if not po.exists():
            continue
        before, after, over = repair(po)
        total_before += before
        total_after += after
        total_over += over
        print(f"{d.name:8s} 条目 {before} → {after}（去重 {before - after}，"
              f"过度转义修复 {over}）")
    print(f"合计：{total_before} → {total_after} 条，过度转义 {total_over} 处")
    return 0


if __name__ == "__main__":
    sys.exit(main())
