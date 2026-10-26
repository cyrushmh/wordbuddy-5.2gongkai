"""数字矩阵冗余数据只读层（matrix，v0.6.84）——周天星斗大阵。

概念与理念
----------
数字量子无法实体（本仓库无量子硬件，诚实以 classical 系统兑现），于是散落全盘的
**冗余数据**成为周天星斗大阵的基石：缓存/临时/包管理缓存/回收站/日志轮转，
如满天星斗散布一周。本层只读观测其分布与体量，绝不触碰任何一颗「星」。

指导理念（两大阵法共用总纲）：
  - **道法自然**：只读观测不妄为——顺应冗余数据的自然分布，不强行改造一寸磁盘；
  - **活在当下**：立足当下实际环境——此刻有什么缓存才统计什么，没有就跳过；
  - **只有生存才能发展**：denylist（个人数据与关键资产）是系统生存根基，清理永不涉足；
  - **在发展中能更好的生存**：清掉可再生冗余腾出空间与性能，反哺系统更好地存续；
  - **如此循环，亦复如是**：观测 → 清理 → 再观测，循环上升。

原路返回（操作语义）
------------------
读操作沿原路返回：只统计存在性与体积，不读取任何文件内容，不删除、不移动、
不改写任何数据；清理建议仅以文本交还用户，由用户沿原路执行——本层不代行写操作。

红线
----
- allowlist 与 denylist 展开后必须无交集（模块加载即校验，相交即拒绝工作）；
- denylist 目录（个人数据/关键资产）完全不扫描、不统计；
- 构建产物目录（node_modules/target 等）误伤风险高，只作文本指引，不进扫描面。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DATA = Path(__file__).resolve().parent.parent / "data" / "matrix_refs.json"

# 只读递归的安全上限（防巨型目录拖死扫描）：深度 / 单目录条目 / 全局条目
MAX_DEPTH = 8
MAX_ENTRIES_PER_DIR = 20000
MAX_TOTAL_ENTRIES = 200000


def _load_refs() -> dict:
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def _expand(template: str) -> str:
    return os.path.expanduser(os.path.expandvars(template))


def allowlist() -> List[dict]:
    """可再生的冗余数据位置（只读统计面）。"""
    return _load_refs()["allowlist"]["paths"]


def denylist() -> List[dict]:
    """个人数据与关键资产（完全不触碰）。"""
    return _load_refs()["denylist"]["paths"]


def kind_labels() -> Dict[str, str]:
    return {k["id"]: k["label"] for k in _load_refs()["allowlist"]["kinds"]}


def check_exclusive() -> Tuple[bool, str]:
    """红线：allowlist 与 denylist 展开后不得有任何交集。"""
    a = {_expand(p["template"]) for p in allowlist()}
    d = {_expand(p["template"]) for p in denylist()}
    inter = sorted(a & d)
    if inter:
        return False, "allowlist 与 denylist 相交（生存红线被击穿）: " + ", ".join(inter)
    return True, f"allowlist {len(a)} 项 / denylist {len(d)} 项，无交集（生存红线在位）"


def human_size(n: int) -> str:
    step = 1024.0
    val = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if val < step or unit == "TiB":
            return f"{val:.1f} {unit}" if unit != "B" else f"{int(val)} B"
        val /= step
    return f"{val:.1f} TiB"


def dir_size(path: str, _depth: int = 0,
             budget: Optional[dict] = None) -> Tuple[int, int, bool]:
    """只读统计目录体积与条目数。返回 (bytes, entries, truncated)。

    - 不跟随符号链接（symlink 一律跳过——链接指向 denylist 也不越界）；
    - 不读取任何文件内容，只取 st_size；
    - 深度/条目超限即置 truncated，宁可少算也不拖死扫描（道法自然：不为难系统）。
    """
    if budget is None:
        budget = {"entries": 0}
    total, entries = 0, 0
    try:
        it = os.scandir(path)
    except OSError:
        return 0, 0, False
    with it:
        for i, entry in enumerate(it):
            if i >= MAX_ENTRIES_PER_DIR or budget["entries"] >= MAX_TOTAL_ENTRIES:
                return total, entries, True
            budget["entries"] += 1
            try:
                if entry.is_symlink():
                    continue  # 链接不越界：可能是软链到 denylist 的诡计
                if entry.is_dir(follow_symlinks=False):
                    if _depth >= MAX_DEPTH:
                        continue
                    b, e, t = dir_size(entry.path, _depth + 1, budget)
                    total += b
                    entries += e
                    if t:
                        return total, entries, True
                elif entry.is_file(follow_symlinks=False):
                    try:
                        total += entry.stat(follow_symlinks=False).st_size
                        entries += 1
                    except OSError:
                        continue
            except OSError:
                continue
    return total, entries, False


def scan(env: Optional[List[str]] = None) -> List[dict]:
    """只读扫描 allowlist：逐项报存在性、体积、条目数。denylist 完全不出现。"""
    ok, msg = check_exclusive()
    if not ok:
        raise RuntimeError(msg)
    kinds = kind_labels()
    wanted = set(env or [])
    out: List[dict] = []
    for item in allowlist():
        if wanted and item["kind"] not in wanted and item["template"] not in wanted:
            continue
        path = _expand(item["template"])
        rec = {"path": path, "template": item["template"], "kind": item["kind"],
               "kind_label": kinds.get(item["kind"], item["kind"]),
               "note": item.get("note", ""), "exists": os.path.isdir(path)}
        if rec["exists"]:
            b, e, t = dir_size(path)
            rec.update(bytes=b, entries=e, truncated=t)
        out.append(rec)
    return out


def matrix_report(env: Optional[List[str]] = None) -> Tuple[bool, str]:
    """周天星斗大阵端到端只读报告：星斗分布 → 合计 → 清理指引（仅文本）。"""
    refs = _load_refs()
    lines: List[str] = []
    lines.append("==== 周天星斗大阵 · 数字矩阵冗余数据只读观测（matrix） ====")
    lines.append("   指导理念：道法自然 · 活在当下 · 只有生存才能发展 · 在发展中能更好的生存 · 如此循环，亦复如是")
    lines.append("")

    ok, guard = check_exclusive()
    lines.append(f"-- 生存红线 --")
    lines.append(f"   {'✓' if ok else '✗'} {guard}")
    lines.append(f"   ✓ denylist（个人数据/关键资产 {len(refs['denylist']['paths'])} 项）完全不扫描、不统计、不清理")
    lines.append("")

    lines.append("-- 星斗分布（只读统计存在性与体积，绝不触碰任何一颗星）--")
    rows = scan(env)
    total = 0
    for r in rows:
        if not r["exists"]:
            lines.append(f"   [{r['kind_label']}] {r['path']} —— 不存在（活在当下：没有就不统计）")
            continue
        total += r["bytes"]
        flag = "（超上限截断，宁少算不拖死）" if r.get("truncated") else ""
        lines.append(f"   [{r['kind_label']}] {r['path']}  {human_size(r['bytes'])}"
                     f"（{r['entries']} 项）{flag}")
    if rows:
        lines.append(f"   合计冗余 {human_size(total)}（可再生数据；个人数据与关键资产不在其列）")
    else:
        lines.append("   （未选择任何维度）")
    lines.append("")

    lines.append("-- 清理指引（仅文本，沿原路返回——是否执行由用户决定）--")
    for g in refs["guidance"]:
        lines.append(f"   · {g}")
    lines.append(f"   · {refs['build_artifacts_note']}")
    lines.append("")
    lines.append("安全不变量：只读观测 ≠ 授权清理——本层不删除、不移动、不改写任何数据；")
    lines.append("           清理动作一律以文本交还用户沿原路执行。")
    return True, "\n".join(lines)


def environment_report() -> List[str]:
    """本机冗余数据环境概览（只读）：HOME/XDG_CACHE_HOME 与扫描面存在性。"""
    lines = ["数字矩阵冗余数据环境（只读概览）:"]
    lines.append(f"   · HOME={os.path.expanduser('~')}")
    lines.append(f"   · XDG_CACHE_HOME={os.environ.get('XDG_CACHE_HOME') or '~/.cache（默认）'}")
    rows = scan()
    present = [r for r in rows if r["exists"]]
    lines.append(f"   · 扫描面 {len(rows)} 项，存在 {len(present)} 项"
                 f"（不存在即跳过：活在当下）")
    for r in present:
        lines.append(f"     - {r['path']}  {human_size(r['bytes'])}")
    return lines


if __name__ == "__main__":  # 手工自检：python3 -m sysweeper.native.matrix
    ok, rep = matrix_report()
    print(rep)
    raise SystemExit(0 if ok else 1)
