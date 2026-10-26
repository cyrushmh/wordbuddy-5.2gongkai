"""编译与工具链概念系统只读层（v0.6.59，CLI 子命令 `comp`）。

数据来源：``data/concepts/comp_taxonomy.json``（由 ``research/comp/build_comp.py``
构建；桥接目标经 plang / daoxue / llvm_docs 校验，无悬空边）。

以仓库 wordbuddy-github 为主目录，把「公开的计算机编程语言和编译需要」按七轴组织：

    编译流水线(pipeline)   : 前端→中端(IR/优化)→后端→目标文件→链接 的标准阶段链
    工具链(toolchain)      : 编译器驱动、预处理器、汇编器、链接器、构建系统、包管理器…
    构建形态(build)        : 本地/交叉/增量/分布式构建、构建缓存与可复现构建
    产物形态(artifact)     : 目标文件、静态/动态库、可执行、字节码、wasm…
    语言编译需要(lang-need): 逐语言登记驱动工具与典型产物（诚实边界：仅 plang
                             probe 实测通过的 15 种语言有明细，其余 146 种汇总
                             为一条 needs_verify，不逐条臆造）
    黑箱逆向(reverse)      : 不读源码看清可执行文件——UPX 壳识别/熵判据/格式解剖/
                             GDB 黑箱调试/符号可见性/自造样本（沙箱只读实测）
    位宽与寻址世代(bitwidth): 8 位/16 位实模式/32 位保护模式/PAE 物理地址扩展/
                             64 位长模式五档 + 遗留 DOS·BusyBox 栈只读落地

67 条桥接边接到 plang（语言/执行模型/硬件架构轴）/ daoxue（治理原则）/
datong（文明通名）/ netsys（模块）/ llvm_docs（工具与目标三元组矩阵），
构建期校验无悬空。

本概念系统只读登记，**不驱动任何真实编译**（编译动作属各工具链自身）；
语言编译需要的证据口径见 ``_meta.honesty`` 与 ``needs_verify``。

只读、不联网、不改动数据。
"""
from __future__ import annotations

from ._common import load_taxonomy
from typing import Any, Dict, List, Optional

_DATA = "comp_taxonomy.json"


def _load() -> Dict[str, Any]:
    """加载 data/concepts/<name>_taxonomy.json（共享加载器，带缓存，只读）。"""
    return load_taxonomy(_DATA)


def info() -> Dict[str, Any]:
    """返回 _meta（主目录 / 七轴 / 诚实边界 / 红线说明）。"""
    return _load().get("_meta", {})


def domains() -> List[Dict[str, Any]]:
    """七轴清单（含每轴概念数）。"""
    doc = _load()
    by = doc.get("by_domain", {})
    out = []
    for d in doc.get("domains", []):
        ids = by.get(d["domain"], [])
        out.append({**d, "count": len(ids)})
    return out


def domain(name: str) -> Optional[Dict[str, Any]]:
    """取单轴（含概念数）。"""
    q = (name or "").strip().lower()
    for d in domains():
        if d["domain"] == q:
            return d
    return None


def concepts() -> List[Dict[str, Any]]:
    """全部概念（60 条）。"""
    return list(_load().get("concepts", []))


def concepts_of_domain(name: str) -> List[Dict[str, Any]]:
    """某轴下的概念（pipeline / toolchain / build / artifact / lang-need / reverse）。"""
    q = (name or "").strip().lower()
    return [c for c in concepts() if c.get("domain") == q]


def concept(cid: str) -> Optional[Dict[str, Any]]:
    """取单个概念（lang-need 轴条目带 evidence 实测证据）。"""
    q = (cid or "").strip().lower()
    for c in concepts():
        if c["id"] == q:
            return c
    return None


def of(cid: str) -> Optional[Dict[str, Any]]:
    """``concept`` 的别名（与 plang/netsys/quantum/apilab 的 ``of`` 口径一致）。"""
    return concept(cid)


def lang_needs() -> List[Dict[str, Any]]:
    """lang-need 轴全部条目（15 条实测明细 + 1 条汇总 needs_verify）。"""
    return concepts_of_domain("lang-need")


def lang_need(name: str) -> Optional[Dict[str, Any]]:
    """按语言名取编译需要（参数匹配 ``lang`` 或概念 id ``need-<name>``）。"""
    q = (name or "").strip().lower()
    for c in lang_needs():
        if c.get("lang") == q or c["id"] == q or c["id"] == f"need-{q}":
            return c
    return None


def verified_lang_needs() -> List[Dict[str, Any]]:
    """仅 plang probe 实测通过的 15 种语言的编译需要明细。"""
    return [c for c in lang_needs()
            if c.get("evidence_status") == "probe_verified"]


def needs_verify() -> List[Dict[str, Any]]:
    """诚实边界：未逐条核实的编译需要（146 种语言的汇总条目）。"""
    out: List[Dict[str, Any]] = []
    for c in lang_needs():
        if c.get("evidence_status") == "needs_verify" or c.get("needs_verify"):
            out.append({
                "kind": "concept",
                "id": c["id"],
                "item": c.get("name", c["id"]),
                "why": c.get("needs_verify", c.get("detail", "")),
            })
    return out


def bridges(system: str = "") -> List[Dict[str, Any]]:
    """编译概念 → 既有概念系统的桥接边；给 system 则过滤（plang/daoxue/llvm）。"""
    out = list(_load().get("bridges", []))
    if system:
        q = system.strip().lower()
        out = [b for b in out if b.get("system") == q]
    return out


def bridges_of(cid: str) -> List[Dict[str, Any]]:
    """某个概念发出的桥接边（顶层 bridges 中 from == comp:<cid>）。"""
    q = (cid or "").strip().lower()
    return [b for b in bridges() if b.get("from") == f"comp:{q}"]


def search(q: str) -> List[Dict[str, Any]]:
    """跨轴检索（id / 名称 / 纲宗 / 详述；lang-need 另匹配语言名）。"""
    term = (q or "").strip().lower()
    if not term:
        return []
    out: List[Dict[str, Any]] = []
    for c in concepts():
        hay = " ".join([
            c.get("id", ""), c.get("name", ""), c.get("gist", ""),
            c.get("detail", ""), c.get("lang", ""),
        ]).lower()
        if term in hay:
            out.append({
                "where": c.get("domain", ""),
                "id": c["id"],
                "name": c.get("name", ""),
                "text": c.get("gist", ""),
            })
    return out


def stats() -> Dict[str, Any]:
    """概念系统规模统计。"""
    doc = _load()
    ln = lang_needs()
    return {
        "concept_total": len(doc.get("concepts", [])),
        "domain_count": len(doc.get("domains", [])),
        "bridge_count": len(doc.get("bridges", [])),
        "lang_need_total": len(ln),
        "lang_need_verified": len(verified_lang_needs()),
        "needs_verify_count": len(needs_verify()),
    }
