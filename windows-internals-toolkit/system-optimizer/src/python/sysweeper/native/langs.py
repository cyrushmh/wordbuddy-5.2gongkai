"""编程语言与编译器知识库（只读层，v0.6.53）。

数据来源：``data/langs_docs.json``（精选代表性集合，非穷举普查；结构化元数据，
不复制任何教材/文档原文）。覆盖 2008–2026 新发语言为主体，补历史锚点(古今)与
国内外代表，以及「其他计算机类」(查询/标记/数据/Shell/IR/排版/记号/验证)。

只读、不联网、不改动数据。新增条目只需往 ``languages`` 数组追加，schema 不变；
``research/langs/validate_langs.py`` 负责 schema 与 ``in_window`` 一致性校验（防漂移）。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

_DATA = "langs_docs.json"


@lru_cache(maxsize=1)
def _load() -> Dict[str, Any]:
    """惰性加载知识库（importlib.resources，与 rfc_catalog / recert 同口径）。"""
    try:
        from importlib import resources

        data = resources.files("sysweeper.data").joinpath(_DATA).read_text(
            encoding="utf-8")
    except Exception:
        here = Path(__file__).resolve().parent.parent / "data" / _DATA
        data = here.read_text(encoding="utf-8")
    return json.loads(data)


def info() -> Dict[str, Any]:
    """返回 _meta（标题/范围/窗口/诚实说明/分类枚举）。"""
    return _load().get("_meta", {})


def _langs() -> List[Dict[str, Any]]:
    return _load().get("languages", [])


def stats() -> Dict[str, Any]:
    """口径统计：总数、窗口内数、按分类/来源/状态计数、待核实条目数。"""
    ls = _langs()
    by_cat: Dict[str, int] = {}
    by_origin: Dict[str, int] = {}
    by_status: Dict[str, int] = {}
    in_window = 0
    needs = 0
    for e in ls:
        by_cat[e.get("category", "?")] = by_cat.get(e.get("category", "?"), 0) + 1
        by_origin[e.get("origin", "?")] = by_origin.get(e.get("origin", "?"), 0) + 1
        by_status[e.get("status", "?")] = by_status.get(e.get("status", "?"), 0) + 1
        if e.get("in_window"):
            in_window += 1
        if e.get("needs_verify"):
            needs += 1
    return {
        "total": len(ls),
        "in_window": in_window,
        "out_of_window": len(ls) - in_window,
        "needs_verify": needs,
        "by_category": by_cat,
        "by_origin": by_origin,
        "by_status": by_status,
        "window": info().get("window"),
    }


def all_langs() -> List[Dict[str, Any]]:
    """全量条目（保持数据内顺序）。"""
    return list(_langs())


def get(lang_id: str) -> Optional[Dict[str, Any]]:
    """按 id 取单条（不区分大小写）；无则返回 None。"""
    q = (lang_id or "").strip().lower()
    for e in _langs():
        if e.get("id", "").lower() == q:
            return e
    return None


def search(q: str, limit: int = 30) -> List[Dict[str, Any]]:
    """按名称/中文名/设计者/范式/备注检索（子串、不区分大小写）。"""
    q = (q or "").strip().lower()
    if not q:
        return []
    out = []
    for e in _langs():
        hay = " ".join([
            e.get("name", ""), e.get("name_zh", ""), e.get("designer", ""),
            " ".join(e.get("paradigms", [])), e.get("notes", ""),
        ]).lower()
        if q in hay:
            out.append(e)
    out.sort(key=lambda x: x.get("first_year", 0), reverse=True)
    return out[:max(0, limit)]


def by_category(category: str) -> List[Dict[str, Any]]:
    """按分类取条目（compiled/interpreted/jit/transpiled/query/markup/data/
    config/shell/ir/typesetting/notation/verification）。"""
    q = (category or "").strip().lower()
    return [e for e in _langs() if e.get("category", "").lower() == q]


def by_origin(origin: str) -> List[Dict[str, Any]]:
    """按来源取条目（国外/国内/国际）。"""
    q = (origin or "").strip().lower()
    return [e for e in _langs() if e.get("origin", "").lower() == q]


def window(only: bool = True) -> List[Dict[str, Any]]:
    """``only=True`` 仅返回首现于 2008–2026 窗口内的语言；否则返回全部。"""
    ls = _langs()
    if only:
        ls = [e for e in ls if e.get("in_window")]
    return sorted(ls, key=lambda x: x.get("first_year", 0), reverse=True)


def paradigms() -> List[Dict[str, Any]]:
    """范式分布：[{paradigm, count}]，按数量降序。"""
    counts: Dict[str, int] = {}
    for e in _langs():
        for p in e.get("paradigms", []):
            counts[p] = counts.get(p, 0) + 1
    return [{"paradigm": p, "count": c}
            for p, c in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def needs_verify() -> List[Dict[str, Any]]:
    """返回含 needs_verify 标注的条目（诚实边界：存疑项集中列出）。"""
    return [e for e in _langs() if e.get("needs_verify")]
