"""编程语言知识库校验（可复现 / 防漂移，v0.6.53）。

数据来源：``data/langs_docs.json``（手工精选，无外部源解析）。本脚本负责：
  · 回填 ``_meta.entry_count`` 使其与 ``languages`` 实际长度一致（防手抖漂移）；
  · 校验每条目 schema 完备、category / origin 落在 _meta 枚举内；
  · 校验 ``in_window`` 与 ``first_year`` 一致（2008–2026 窗口内 ⇔ in_window=true）；
  · 校验 ``needs_verify`` 为列表或缺失。

用法：
  python validate_langs.py            # 写回 entry_count + 打印统计
  python validate_langs.py --check    # 仅校验，不一致则非零退出（CI / 防漂移）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List

# 与既有的 research/rfc、research/recert 构建脚本同款约定：
#   REPO = __file__.parents[2] → monorepo 根
#   DATA = REPO/windows-internals-toolkit/system-optimizer/src/python/sysweeper/data/
REPO = Path(__file__).resolve().parents[2]
_CANDIDATES = [
    REPO / "windows-internals-toolkit" / "system-optimizer" / "src" / "python" \
        / "sysweeper" / "data" / "langs_docs.json",
    REPO / "src" / "python" / "sysweeper" / "data" / "langs_docs.json",
]
DATA = next((p for p in _CANDIDATES if p.exists()), _CANDIDATES[0])

REQUIRED = ["id", "name", "name_zh", "first_year", "first_release", "paradigms",
            "type_system", "implementation", "designer", "origin", "status",
            "standard", "category", "in_window", "notes"]
WINDOW_LO = 2008
WINDOW_HI = 2026


def load() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def validate(doc: dict) -> List[str]:
    errors: List[str] = []
    meta = doc.get("_meta", {})
    cats = set(meta.get("categories", []))
    origins = set(meta.get("origin_values", []))
    langs = doc.get("languages", [])
    seen_ids = set()
    for i, e in enumerate(langs):
        tag = f"#{i}(id={e.get('id')})"
        for k in REQUIRED:
            if k not in e:
                errors.append(f"{tag} 缺字段 {k}")
        eid = e.get("id")
        if eid in seen_ids:
            errors.append(f"{tag} 重复 id {eid}")
        seen_ids.add(eid)
        if e.get("category") not in cats:
            errors.append(f"{tag} category={e.get('category')} 不在枚举 {sorted(cats)}")
        if e.get("origin") not in origins:
            errors.append(f"{tag} origin={e.get('origin')} 不在枚举 {sorted(origins)}")
        fy = e.get("first_year")
        if not isinstance(fy, int):
            errors.append(f"{tag} first_year 非整数: {fy!r}")
        else:
            expected_window = WINDOW_LO <= fy <= WINDOW_HI
            if bool(e.get("in_window")) != expected_window:
                errors.append(f"{tag} in_window={e.get('in_window')} 与 first_year={fy} 不一致")
        nv = e.get("needs_verify")
        if nv is not None and not isinstance(nv, list):
            errors.append(f"{tag} needs_verify 应为列表或缺失")
    return errors


def check_entry_count(doc: dict) -> List[str]:
    """entry_count 一致性（仅 --check 用，写模式会先回填）。"""
    errors: List[str] = []
    n = len(doc.get("languages", []))
    if doc.get("_meta", {}).get("entry_count") != n:
        errors.append(f"_meta.entry_count={doc['_meta'].get('entry_count')} != 实际 {n}")
    return errors


def stats(doc: dict) -> dict:
    ls = doc.get("languages", [])
    by_cat, by_origin = {}, {}
    inw = 0
    for e in ls:
        by_cat[e.get("category", "?")] = by_cat.get(e.get("category", "?"), 0) + 1
        by_origin[e.get("origin", "?")] = by_origin.get(e.get("origin", "?"), 0) + 1
        inw += 1 if e.get("in_window") else 0
    return {"total": len(ls), "in_window": inw, "by_category": by_cat,
            "by_origin": by_origin}


def main(argv: List[str]) -> int:
    check = "--check" in argv
    doc = load()
    if check:
        errors = validate(doc) + check_entry_count(doc)
        if errors:
            for er in errors:
                print("✗", er)
            return 1
        s = stats(doc)
        print(f"✓ 校验通过：{s['total']} 条（窗口内 {s['in_window']}）")
        print("  分类：", s["by_category"])
        print("  来源：", s["by_origin"])
        return 0
    # 写模式：先回填 entry_count，再校验其余 schema（防漂移）
    doc["_meta"]["entry_count"] = len(doc["languages"])
    DATA.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    errors = validate(doc)
    if errors:
        for er in errors:
            print("✗", er)
        return 1
    s = stats(doc)
    print(f"✓ 校验通过并写回 entry_count={s['total']}（窗口内 {s['in_window']}）")
    print("  分类：", s["by_category"])
    print("  来源：", s["by_origin"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
