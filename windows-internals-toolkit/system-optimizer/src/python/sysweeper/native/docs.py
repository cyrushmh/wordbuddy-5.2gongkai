"""文档与概念联动（docs）：联动网格的文档层一等节点（只读整合）。

用户需求：「docs 文档也算是保证概念系统的联动连轴连动的统合与整合」——
把 docs/ 文档层视作概念系统「联动连轴连动」统合整合的一部分，docs 成为联动
网格中的一等节点：它既被 sysbase / linkage / subsystems 等节点供给与印证，也
反过来把各子系统的知识沉淀为可检索、可审计的文档，供 CLI/GUI 展示与联动体检。

红线（与全工具一致）：本模块只读——不写任何文件、不执行任何命令、不修改
系统；仅枚举 docs/ 文档清单并做交叉引用统计，供 CLI/GUI 展示与联动报告。
"""

from __future__ import annotations

import os

_HERE = os.path.dirname(os.path.abspath(__file__))


def _find_docs_dir() -> "str | None":
    """从本文件向上查找包含 NN_*.md 文档的 docs 目录（鲁棒定位，避免硬编码相对层数）。"""
    cur = _HERE
    prefixes = tuple(f"{i:02d}_" for i in range(1, 100))
    for _ in range(8):
        cand = os.path.join(cur, "docs")
        if os.path.isdir(cand):
            try:
                names = os.listdir(cand)
            except OSError:
                names = []
            if any(n.endswith(".md") and n.startswith(prefixes) for n in names):
                return cand
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return None


def doc_inventory() -> list:
    """返回 docs/ 下规范化文档清单（文件名 + 标题首行）。只读枚举。"""
    d = _find_docs_dir()
    if not d:
        return []
    out = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".md") or fn.upper().startswith("README"):
            continue
        path = os.path.join(d, fn)
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                first = fh.readline().strip()
        except OSError:
            first = ""
        out.append((fn, first))
    return out


def docs_report() -> tuple:
    """文档与概念联动报告：枚举 docs 清单并把文档层接入联动网格。

    返回 (True, msg)。只读、零副作用。
    """
    inv = doc_inventory()
    lines = []
    lines.append("==== 文档与概念联动（docs）：联动网格文档层一等节点 ====")
    lines.append("")
    lines.append("-- docs/ 文档清单（只读枚举；概念系统「联动连轴连动」统合整合的文档承载）--")
    if inv:
        lines.append(f"   共 {len(inv)} 篇规范化文档：")
        for fn, title in inv:
            lines.append(f"   · {fn} — {title.lstrip('#').strip()}")
    else:
        lines.append("   未定位到 docs/ 文档目录（运行环境路径差异），不影响联动体检。")
    lines.append("")
    lines.append("-- 联动接入（docs 作为一等节点：被供给/印证，并反向沉淀知识）--")
    lines.append("   docs → subsystems（供给）：文档登记进统一子系统清单，成为可开关的文档节点")
    lines.append("   docs → linkage（印证）：55_兼容层common 与 54_系统基座 交叉验证联动轴的「接没接上」")
    lines.append("   docs → sysbase（印证）：文档层与系统基座只读诊断互相印证，沉淀为可审计知识")
    lines.append("")
    lines.append("安全不变量：本节点只读——不写任何文件、不执行命令、不修改系统；"
                 "仅枚举文档与交叉引用，供 CLI/GUI 展示与联动体检。")
    return True, "\n".join(lines)
