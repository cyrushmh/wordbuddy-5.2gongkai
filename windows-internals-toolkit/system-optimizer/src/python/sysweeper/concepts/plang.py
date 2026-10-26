"""编程语言「概念系统」只读层（v0.6.56，CLI 子命令 `plang`）。

数据来源：``data/concepts/plang_taxonomy.json``（由 ``research/plang/build_plang.py``
从 ``data/langs_docs.json`` 构建，构建时经本仓库 ``rfc_catalog`` 交叉验证 RFC 编号存在性）。

把 161 条语言组织成**以仓库 wordbuddy-github 为主目录的分层概念体系**：

    执行模型(8) → 硬件架构子分类(13: isa/virtual-isa/vm/accelerator/reconfigurable/host/n-a)
                → 能力域 → 底层标准依据(RFC/ISO/…)

只读、不联网、不改动数据。
"""
from __future__ import annotations

from ._common import load_taxonomy
from typing import Any, Dict, List, Optional

_DATA = "plang_taxonomy.json"


def _load() -> Dict[str, Any]:
    """加载 data/concepts/<name>_taxonomy.json（共享加载器，带缓存，只读）。"""
    return load_taxonomy(_DATA)


def info() -> Dict[str, Any]:
    """返回 _meta（主目录/分类轴/口径说明）。"""
    return _load().get("_meta", {})


def models() -> List[Dict[str, Any]]:
    """执行模型清单（含每类语言数）。"""
    doc = _load()
    out = []
    for m in doc.get("execution_models", []):
        out.append({**m,
                    "count": len(doc.get("model_langs", {}).get(m["model"], []))})
    return out


def archs() -> List[Dict[str, Any]]:
    """硬件架构子分类清单（含每类语言数）。"""
    doc = _load()
    out = []
    for a in doc.get("target_archs", []):
        out.append({**a,
                    "count": len(doc.get("arch_langs", {}).get(a["arch"], []))})
    return out


def langs_of_arch(arch: str) -> List[str]:
    """某硬件架构下的语言 id 列表（如 x86-64 / wasm / jvm / gpu-simt / fpga）。"""
    q = (arch or "").strip().lower()
    return list(_load().get("arch_langs", {}).get(q, []))


def langs_of_model(model: str) -> List[str]:
    """某执行模型下的语言 id 列表（如 native / bytecode-vm / interpreted）。"""
    q = (model or "").strip().lower()
    return list(_load().get("model_langs", {}).get(q, []))


def of(lang_id: str) -> Optional[Dict[str, Any]]:
    """单条语言的完整分类：执行模型 / 目标架构 / 能力域 / 自身标准 / 继承的底层标准。"""
    q = (lang_id or "").strip().lower()
    v = _load().get("lang_index", {}).get(q)
    if not v:
        return None
    return {**v, "standards": standards_of(q)}


def domains() -> List[Dict[str, Any]]:
    """能力域及其底层标准依据（RFC 等，已回填 rfc_title）。"""
    return _load().get("domains", [])


def standards_of(lang_id: str) -> List[Dict[str, Any]]:
    """某语言**继承**的底层标准依据（按所属能力域展开；去重）。"""
    q = (lang_id or "").strip().lower()
    v = _load().get("lang_index", {}).get(q)
    if not v:
        return []
    doms = set(v.get("domains", []))
    out: List[Dict[str, Any]] = []
    seen = set()
    for d in _load().get("domains", []):
        if d["domain"] not in doms:
            continue
        for s in d.get("standards", []):
            key = (s.get("kind"), s.get("num"))
            if key in seen:
                continue
            seen.add(key)
            out.append({"domain": d["domain"], "domain_label": d["label"], **s})
    return out


def rfc_refs(lang_id: str) -> List[Dict[str, Any]]:
    """某语言继承的 RFC 依据（仅 kind=RFC 项），可直接用 rfc_catalog.rfc_info 反查。"""
    return [s for s in standards_of(lang_id) if s.get("kind") == "RFC"]


def stats() -> Dict[str, Any]:
    """概念系统规模统计。"""
    doc = _load()
    idx = doc.get("lang_index", {})
    by_source: Dict[str, int] = {}
    for v in idx.values():
        by_source[v.get("mapping_source", "?")] = by_source.get(
            v.get("mapping_source", "?"), 0) + 1
    return {
        "lang_total": len(idx),
        "model_count": len(doc.get("execution_models", [])),
        "arch_count": len(doc.get("target_archs", [])),
        "domain_count": len(doc.get("domains", [])),
        "by_mapping_source": by_source,
    }


def probe() -> Dict[str, Any]:
    """「各语言尝试编程整体」的实测结果（来自 research/plang/probe_report.json）。"""
    doc = _load()
    return {"meta": doc.get("probe"), "results": doc.get("probe_results") or []}


def probe_of(lang_id: str) -> Optional[Dict[str, Any]]:
    """某语言的实测记录；无则 None。"""
    q = (lang_id or "").strip().lower()
    for r in probe()["results"]:
        if r.get("id", "").lower() == q:
            return r
    return None
