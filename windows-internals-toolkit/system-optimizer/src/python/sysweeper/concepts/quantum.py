"""量子理念概念系统只读层（v0.6.65，CLI 子命令 `quantum`）。

数据来源：``data/concepts/quantum_taxonomy.json``（由 ``research/quantum/build_quantum.py``
构建；桥接目标经 plang / netsys / daoxue / datong 校验，无悬空边；标准登记逐条标注核实状态）。

以仓库 wordbuddy-github 为主目录的**量子理念**概念系统，按八域组织：

    量子态表示(state)      : 量子比特、叠加、纠缠、Bloch 球、密度矩阵、测量公设
    量子线路(circuit)     : Pauli/Hadamard 门、相位、受控门、通用门集、测量与回路
    量子算法(algorithm)   : Deutsch-Jozsa、Shor、Grover、QAOA、VQE、HHL、退火…
    硬件(hardware)     : 超导/离子阱/光量子/中性原子/硅自旋/拓扑 + NISQ 与纠错开销
    量子纠错(error)        : 阈值定理、表面码、稳定子、逻辑比特、容错门…
    量子网络(network)     : QKD、量子中继、量子互联网、 teleportation…
    工具链(toolchain)     : OpenQASM / QIR / Qiskit / Cirq 等前端与执行栈
    经典模拟与语义(qsim) : 本仓库自建模拟器（research/quantum/simulator/）：
                           电压三极 / 相变矩阵 / 数制双读出 / Born 观测 / 缺失态等

本仓库是经典系统工程工具箱：不含量子硬件探针、不接入量子设备、不在真实量子硬件上
执行量子线路，本系统只做理念与标准登记（qsim 域为经典模拟器，O(2ⁿ) 墙内 ≤6 比特，
诚实边界见 ``_meta.honesty`` / ``needs_verify``）。

只读、不联网、不改动数据。
"""
from __future__ import annotations

from ._common import load_taxonomy
from typing import Any, Dict, List, Optional

_DATA = "quantum_taxonomy.json"


def _load() -> Dict[str, Any]:
    """加载 data/concepts/<name>_taxonomy.json（共享加载器，带缓存，只读）。"""
    return load_taxonomy(_DATA)


def info() -> Dict[str, Any]:
    """返回 _meta（主目录 / 八域 / 诚实边界 / 红线说明）。"""
    return _load().get("_meta", {})


def domains() -> List[Dict[str, Any]]:
    """八域清单（含每域概念数）。"""
    doc = _load()
    by = doc.get("by_domain", {})
    out = []
    for d in doc.get("domains", []):
        ids = by.get(d["domain"], [])
        out.append({**d, "count": len(ids)})
    return out


def domain(name: str) -> Optional[Dict[str, Any]]:
    """取单域（含概念数）。"""
    q = (name or "").strip().lower()
    for d in domains():
        if d["domain"] == q:
            return d
    return None


def concepts() -> List[Dict[str, Any]]:
    """全部概念（66 条）。"""
    return list(_load().get("concepts", []))


def concepts_of_domain(name: str) -> List[Dict[str, Any]]:
    """某域下的概念（如 state / circuit / algorithm / hardware / error / network /
    toolchain / qsim）。"""
    q = (name or "").strip().lower()
    return [c for c in concepts() if c.get("domain") == q]


def concept(cid: str) -> Optional[Dict[str, Any]]:
    """取单个概念（含其 standards 引用与 bridges）。"""
    q = (cid or "").strip().lower()
    for c in concepts():
        if c["id"] == q:
            return c
    return None


def of(cid: str) -> Optional[Dict[str, Any]]:
    """``concept`` 的别名（与 plang/netsys/comp/apilab 的 ``of`` 口径一致）。"""
    return concept(cid)


def standards() -> List[Dict[str, Any]]:
    """标准登记册（逐条带 status：verified=本轮核实 / needs_verify=待核实）。"""
    out = []
    for sid, s in _load().get("standards", {}).items():
        out.append({"id": sid, **s})
    return out


def standard(sid: str) -> Optional[Dict[str, Any]]:
    """取单条标准登记。"""
    q = (sid or "").strip().lower()
    for s in standards():
        if s["id"] == q:
            return s
    return None


def needs_verify() -> List[Dict[str, Any]]:
    """诚实边界：待核实项（标准发布状态未核实的逐条列出，不臆造）。"""
    out: List[Dict[str, Any]] = []
    for s in standards():
        if s.get("status") != "verified":
            out.append({
                "kind": "standard",
                "id": s["id"],
                "item": s.get("name", s["id"]),
                "why": s.get("reason", s.get("note", "")),
            })
    for c in concepts():
        if c.get("needs_verify"):
            out.append({
                "kind": "concept",
                "id": c["id"],
                "item": c.get("name", c["id"]),
                "why": c["needs_verify"],
            })
    return out


def bridges(system: str = "") -> List[Dict[str, Any]]:
    """量子理念 → 既有概念系统的桥接边；给 system 则过滤（plang/netsys/daoxue）。"""
    out = list(_load().get("bridges", []))
    if system:
        q = system.strip().lower()
        out = [b for b in out if b.get("system") == q]
    return out


def bridges_of(cid: str) -> List[Dict[str, Any]]:
    """某个概念发出的桥接边（顶层 bridges 中 from == quantum:<cid>）。"""
    q = (cid or "").strip().lower()
    return [b for b in bridges() if b.get("from") == f"quantum:{q}"]


def search(q: str) -> List[Dict[str, Any]]:
    """跨域检索（id / 名称 / 纲宗 / 详述）。"""
    term = (q or "").strip().lower()
    if not term:
        return []
    out: List[Dict[str, Any]] = []
    for c in concepts():
        hay = " ".join([
            c.get("id", ""), c.get("name", ""), c.get("gist", ""),
            c.get("detail", ""),
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
    return {
        "concept_total": len(doc.get("concepts", [])),
        "domain_count": len(doc.get("domains", [])),
        "bridge_count": len(doc.get("bridges", [])),
        "standard_count": len(doc.get("standards", {})),
        "needs_verify_count": len(needs_verify()),
    }
