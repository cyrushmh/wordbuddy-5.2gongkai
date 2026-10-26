"""网络与组网「概念系统」只读层（v0.6.57+，CLI 子命令 `netsys`）。

数据来源：``data/concepts/netsys_taxonomy.json``（由 ``research/netsys/build_netsys.py`` 构建，
构建时经本仓库 ``rfc_catalog`` 交叉验证 RFC 编号存在性）。

以仓库 wordbuddy-github 为主目录，把散落的 20+ 个网络/组网子系统按四轴重组：

    网络层次(8) → 组网形态(8) → 能力性质(7) → 标准依据(RFC/ISO/ITU)

并显式登记**依赖关系(depends)与互补关系(complements)**，红线随模块登记。
只读、不联网、不改动任何配置——本层只做「重组视图」，不代调用各模块。
"""
from __future__ import annotations

from ._common import load_taxonomy
from typing import Any, Dict, List, Optional

_DATA = "netsys_taxonomy.json"


def _load() -> Dict[str, Any]:
    """加载 data/concepts/<name>_taxonomy.json（共享加载器，带缓存，只读）。"""
    return load_taxonomy(_DATA)


def info() -> Dict[str, Any]:
    """返回 _meta（主目录/四轴/重组说明/红线口径）。"""
    return _load().get("_meta", {})


def layers() -> List[Dict[str, Any]]:
    """网络层次轴（含每层的模块数）。"""
    doc = _load()
    return [{**l, "count": len(doc.get("by_layer", {}).get(l["layer"], []))}
            for l in doc.get("layers", [])]


def forms() -> List[Dict[str, Any]]:
    """组网形态轴（含每形态的模块数）。"""
    doc = _load()
    return [{**f, "count": len(doc.get("by_form", {}).get(f["form"], []))}
            for f in doc.get("forms", [])]


def natures() -> List[Dict[str, Any]]:
    """能力性质轴（含每性质的模块数）。"""
    doc = _load()
    return [{**n, "count": len(doc.get("by_nature", {}).get(n["nature"], []))}
            for n in doc.get("natures", [])]


def modules() -> List[Dict[str, Any]]:
    """全量模块清单。"""
    return list(_load().get("modules", []))


def by_layer(layer: str) -> List[str]:
    """某网络层次下的模块 id（如 L1/L2/L3/L4/L5-6/L7/overlay/mesh）。"""
    return list(_load().get("by_layer", {}).get((layer or "").strip(), []))


def by_form(form: str) -> List[str]:
    """某组网形态下的模块 id（standalone/lan/mesh/overlay/sdwan/distributed/anonymous/wan）。"""
    return list(_load().get("by_form", {}).get((form or "").strip().lower(), []))


def by_nature(nature: str) -> List[str]:
    """某能力性质下的模块 id（diagnose/tune/communicate/share/audit/discover/reference）。"""
    return list(_load().get("by_nature", {}).get((nature or "").strip().lower(), []))


def _name_of(mid: str) -> str:
    for m in modules():
        if m["id"] == mid:
            return m["name"]
    return mid


def _raw(module_id: str) -> Optional[Dict[str, Any]]:
    """取原始模块条目（不展开，避免与 of/rfc_refs 互相调用形成递归）。"""
    q = (module_id or "").strip().lower()
    for m in modules():
        if m["id"].lower() == q:
            return m
    return None


def of(module_id: str) -> Optional[Dict[str, Any]]:
    """单个模块的完整视图：层次/形态/性质/依赖/互补/标准依据/红线。"""
    m = _raw(module_id)
    if not m:
        return None
    deps = [{"id": d, "name": _name_of(d), "kind": "depends"}
            for d in m.get("depends", [])]
    comps = [{"id": c, "name": _name_of(c), "kind": "complements"}
             for c in m.get("complements", [])]
    # 直接内联取 RFC，不经 rfc_refs/standards_of，避免递归
    rfc = [s for s in m.get("standards", []) if s.get("kind") == "RFC"]
    return {**m, "depends_detail": deps, "complements_detail": comps, "rfc_refs": rfc}


def relations(kind: Optional[str] = None) -> List[Dict[str, Any]]:
    """关系边（depends 依赖 / complements 互补）；kind 可过滤。"""
    rs = _load().get("relations", [])
    if kind:
        rs = [r for r in rs if r["kind"] == kind]
    return list(rs)


def standards_of(module_id: str) -> List[Dict[str, Any]]:
    """某模块的标准依据（RFC 已回填 rfc_title；ISO/ITU 给名称）。"""
    m = _raw(module_id)
    return list(m.get("standards", [])) if m else []


def rfc_refs(module_id: str) -> List[Dict[str, Any]]:
    """某模块引用的 RFC（可直接用 rfc_catalog.rfc_info 反查）。"""
    return [s for s in standards_of(module_id) if s.get("kind") == "RFC"]


def redlines() -> List[Dict[str, Any]]:
    """全部模块的红线声明（越界防线，审计用）。"""
    return [{"id": m["id"], "name": m["name"], "nature": m["nature"],
             "redline": m["redline"]} for m in modules()]


def stats() -> Dict[str, Any]:
    """概念系统规模统计。"""
    doc = _load()
    return {
        "module_total": len(doc.get("modules", [])),
        "layer_count": len(doc.get("layers", [])),
        "form_count": len(doc.get("forms", [])),
        "nature_count": len(doc.get("natures", [])),
        "relation_count": len(doc.get("relations", [])),
        "depends_count": sum(1 for r in doc.get("relations", [])
                             if r["kind"] == "depends"),
        "complements_count": sum(1 for r in doc.get("relations", [])
                                 if r["kind"] == "complements"),
    }
