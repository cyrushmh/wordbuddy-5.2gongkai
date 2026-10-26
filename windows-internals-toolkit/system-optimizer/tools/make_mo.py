#!/usr/bin/env python3
"""纯 Python 的 .po → .mo 编译器（不依赖 msgfmt / Babel）。

为什么自己写：本仓库 CI 镜像里没有 gettext 工具链（msgfmt/xgettext 均缺失），
而 gettext 运行时又需要 .mo 二进制目录。MO 格式很简单（见 GNU gettext 手册
「The Format of the MO File」），这里用标准库直接编，零第三方依赖、可测试。

用法：
    python tools/make_mo.py                 # 编译 locales/ 下所有 .po
    python tools/make_mo.py locales/en      # 只编译指定目录
编译产物：每个 .po 同目录下生成 sysweeper.mo。
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

DOMAIN = "sysweeper"
HEADER_KEY = ""  # PO 里 msgid "" 是文件头


def _unescape(s: str) -> str:
    """还原 PO 转义：\\n \\t \\\\ \\" 。"""
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == "\\" and i + 1 < n:
            nxt = s[i + 1]
            if nxt == "n":
                out.append("\n"); i += 2; continue
            if nxt == "t":
                out.append("\t"); i += 2; continue
            if nxt == "\\":
                out.append("\\"); i += 2; continue
            if nxt == '"':
                out.append('"'); i += 2; continue
        out.append(c); i += 1
    return "".join(out)


def _extract(line: str) -> list[str]:
    """从 `msgid "..."` / `msgstr "..."` 取出引号内的内容。"""
    q1 = line.find('"')
    q2 = line.rfind('"')
    if q1 == -1 or q2 == q1:
        return [""]
    return [line[q1 + 1:q2]]


def parse_po(path: Path) -> list[tuple[str, str]]:
    """极简 PO 解析：提取 (msgid, msgstr) 条目（忽略模糊/上下文/文件头）。

    约定：遇到新的 ``msgid`` 即提交上一条已完整的 (id, str) 对。
    """
    text = path.read_text(encoding="utf-8")
    entries: list[tuple[str, str]] = []
    cur_id, cur_str = None, None
    buf: list[str] = []

    def commit():
        nonlocal cur_id, cur_str
        # 注意：不能跳过 msgid="" 的文件头——它必须进入 .mo，
        # 否则 gettext 读不到 charset=UTF-8，会用 ASCII 解码而崩。
        if cur_id is not None and cur_str is not None:
            entries.append((cur_id, cur_str))
        cur_id, cur_str = None, None

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("msgid"):
            commit()
            cur_id = _unescape("".join(_extract(line)))
            buf = []
        elif line.startswith("msgstr"):
            cur_str = _unescape("".join(_extract(line)))
            buf = []
        elif line.startswith('"') and line.endswith('"'):
            # 续行（msgid/msgstr 的多行内容）
            piece = line[1:-1]
            if cur_id is not None and cur_str is None:
                cur_id += _unescape(piece)
            elif cur_str is not None:
                cur_str += _unescape(piece)
    commit()
    return entries


def compile_mo(entries: list[tuple[str, str]], out: Path) -> None:
    # 未翻译条目（msgstr 为空）**不进 .mo**——对齐 GNU msgfmt：空译文会被写成
    # msgid→""，gettext 命中后返回空串，界面上就是一片空白，比「回退源语言」更糟。
    # 跳过它们 = 未翻译自动回退中文；文件头（msgid=""）必须保留。
    items = [(m, s) for m, s in entries if s or m == ""]
    # 按原文字节升序排列（gettext 要求）
    items = sorted(items, key=lambda kv: kv[0].encode("utf-8"))
    originals = b"\x00".join(m.encode("utf-8") for m, _ in items) + b"\x00"
    translations = b"\x00".join(s.encode("utf-8") for _, s in items) + b"\x00"
    n = len(items)
    assert n > 0, "没有任何可编译条目（连文件头都没有）"

    o_tbl_off = 7 * 4                 # 原语表偏移 = 头部 28 字节
    t_tbl_off = o_tbl_off + 8 * n     # 译文表紧跟原语表
    orig_data_off = t_tbl_off + 8 * n  # 原语数据在两张表之后
    trans_data_off = orig_data_off + len(originals)

    def table(base: int, blob: bytes):
        blk = b""
        pos = 0
        for s in blob.split(b"\x00")[:-1]:
            blk += struct.pack("<II", len(s), base + pos)
            pos += len(s) + 1
        return blk

    o_tbl = table(orig_data_off, originals)
    t_tbl = table(trans_data_off, translations)
    # MO 头：magic / version / n / 原语表偏移 / 译文表偏移 / 哈希表大小 / 哈希表偏移
    header = struct.pack("<IIIIIII", 0x950412DE, 0, n, o_tbl_off, t_tbl_off, 0, 0)
    body = header + o_tbl + t_tbl + originals + translations
    out.write_bytes(body)
    return n


def compile_dir(d: Path) -> int:
    count = 0
    for po in sorted(d.rglob("*.po")):
        entries = parse_po(po)
        mo = po.with_suffix(".mo")
        kept = compile_mo(entries, mo)
        skipped = len([1 for m, s in entries if not s and m != ""])
        count += 1
        extra = f"，跳过未翻译 {skipped} 条" if skipped else ""
        print("  -> %s  (%d entries%s)" % (
            mo.relative_to(po.parent.parent.parent.parent), kept, extra))
    return count


def main(argv=None) -> int:
    # locales 目录固定位于 src/python/sysweeper/locales
    root = Path(__file__).resolve().parent.parent  # system-optimizer
    locales_root = root / "src/python/sysweeper/locales"
    roots = argv or [str(locales_root)]
    total = 0
    for r in roots:
        p = Path(r)
        if p.is_file() and p.suffix == ".po":
            entries = parse_po(p)
            kept = compile_mo(entries, p.with_suffix(".mo"))
            total += 1
            print("  -> %s  (%d entries)" % (p.with_suffix(".mo").name, kept))
        elif p.is_dir():
            total += compile_dir(p)
        else:
            print("跳过（不存在）：%s" % p)
    print("编译完成：%d 个 .po" % total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
