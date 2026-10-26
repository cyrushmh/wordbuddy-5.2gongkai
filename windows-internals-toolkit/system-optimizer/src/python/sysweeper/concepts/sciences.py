"""「sciences」自然科学概念系统只读层（v0.6.67，CLI 子命令 `sciences`）。

数据来源：``data/concepts/sciences_taxonomy.json``（由
``research/sciences/build_sciences.py`` 构建，桥接目标经 protec 与八个既有
概念系统逐一校验，无悬空边）。

立意（用户原话）：「材料学、热力学、气候学、环境学、物理、化学、生物等以及相关
对产品（设备设施）长期运行和基本保护的协议和标准查看」。

与 protec（产品保护）构成「科学底座 → 工程保护」对照；七门自然科学 + 科学方法
（methodology = principles）同构于 datong 的「理—用」结构：

    材料学(materials)    : 腐蚀/相变/疲劳/蠕变
    热力学(thermodynamics): 定律/热传导/熵/相平衡
    气候学(climatology)  : 温室效应/洋流/ENSO/碳循环
    环境学(environmental) : 污染/生态/可持续
    物理(physics)        : 电磁/量子/力学
    化学(chemistry)      : 电化学/反应动力学/元素周期
    生物(biology)        : 细胞/进化/基因/生物圈
    科学方法(methodology): 可证伪/可重复/对照/溯因/定量/同行评审/不确定度（= principles）

诚实边界：只读登记、科学表述按通行口径、不臆造实测数字；桥接只作科学原理 ↔
工程保护/编译/量子/网络/工程伦理的结构翻译，不宣称等同；未核对原典/版次者统一
挂 needs_verify。
"""
from __future__ import annotations

from ._common import load_taxonomy
from typing import Any, Dict, List, Optional

_DATA = "sciences_taxonomy.json"


def _load() -> Dict[str, Any]:
    """加载 data/concepts/sciences_taxonomy.json（共享加载器，带缓存，只读）。"""
    return load_taxonomy(_DATA)


def info() -> Dict[str, Any]:
    """返回 _meta（主目录 / 八轴结构 / 诚实边界说明）。"""
    return _load().get("_meta", {})


def layers() -> List[Dict[str, Any]]:
    """八层结构：materials / thermodynamics / climatology / environmental /
    physics / chemistry / biology / methodology。"""
    return list(_load().get("layers", []))


def domains() -> List[Dict[str, Any]]:
    """八轴定义。"""
    return list(_load().get("domains", []))


def domain(name: str) -> Optional[Dict[str, Any]]:
    """按轴名取单轴定义（附带该轴概念 id 清单）。"""
    q = (name or "").strip()
    for d in domains():
        if d["domain"] == q:
            item = dict(d)
            item["concepts"] = concepts_of_domain(q)
            return item
    return None


def concepts() -> List[Dict[str, Any]]:
    """全部概念条目：七门学科 + 科学方法（methodology = principles）。"""
    return list(_load().get("concepts", []))


def concepts_of_domain(name: str) -> List[Dict[str, Any]]:
    """某轴下的概念条目。"""
    q = (name or "").strip()
    return [c for c in concepts() if c.get("domain") == q]


def concept(cid: str) -> Optional[Dict[str, Any]]:
    """按 id 取单条概念。"""
    q = (cid or "").strip()
    for c in concepts():
        if c["id"] == q:
            return c
    return None


def of(cid: str) -> Optional[Dict[str, Any]]:
    """某概念所属的轴定义（含轴内全部概念 id）。"""
    c = concept(cid)
    if not c:
        return None
    return domain(c.get("domain", ""))


def principles() -> List[Dict[str, Any]]:
    """七条科学方法工程原则（含理念依据与工程落法）。"""
    return list(_load().get("principles", []))


def principle(pid: str) -> Optional[Dict[str, Any]]:
    """取单条科学方法工程原则。"""
    q = (pid or "").strip()
    for p in principles():
        if p["id"] == q:
            return p
    return None


def principles_of(cid: str) -> List[Dict[str, Any]]:
    """依据某概念/原则的原则条目（canon_refs 反查）。"""
    q = (cid or "").strip()
    return [p for p in principles() if q in p.get("canon_refs", [])]


def principles_of_canon(canon: str) -> List[Dict[str, Any]]:
    """principles_of 的别名（与 datong/zhuangzi/baigong 同名，v0.6.67 API 归一）。"""
    return principles_of(canon)


def user_face() -> Dict[str, Any]:
    """本仓库用户端面 + 语言面实测事实（构建期实测）。"""
    return _load().get("user_face_facts", {})


def bridges(system: str = "") -> List[Dict[str, Any]]:
    """科学概念 → 既有概念系统的桥接边；给 system 则过滤。"""
    out = list(_load().get("bridges", []))
    if system:
        q = system.strip().lower()
        out = [b for b in out if b.get("system") == q]
    return out


def bridges_of(cid: str) -> List[Dict[str, Any]]:
    """某概念发出的桥接边。"""
    q = (cid or "").strip()
    return [b for b in bridges() if b.get("from") == f"sciences:{q}"]


def search(q: str) -> List[Dict[str, Any]]:
    """跨八轴检索（纲宗 / detail / 工程落法 / 通名）。"""
    term = (q or "").strip()
    if not term:
        return []
    out: List[Dict[str, Any]] = []
    for c in concepts():
        if (term in c["name"] or term in c.get("gist", "")
                or term in c.get("detail", "") or term in c.get("engineering", "")):
            out.append({
                "where": f"sciences·{c['domain']}",
                "name": c["name"],
                "text": c.get("gist", ""),
                "id": c["id"],
                "engineering": c.get("engineering", ""),
            })
    return out


def stats() -> Dict[str, Any]:
    """概念系统规模统计（与 by_domain / layers 一致）。"""
    doc = _load()
    by_domain = doc.get("by_domain", {})
    return {
        "concepts": doc["_meta"].get("concept_total", len(doc.get("concepts", []))),
        "principles": doc["_meta"].get("principle_total", len(doc.get("principles", []))),
        "bridges": doc["_meta"].get("bridge_count", len(doc.get("bridges", []))),
        "by_domain": {k: len(v) for k, v in by_domain.items()},
        "user_face": {k: user_face().get(k) for k in
                      ("cli_subcommands", "webapi_actions", "gui_windows",
                       "deno_console_version", "deno_report_viewer_version",
                       "lang_total", "probe_verified", "comp_lang_needs",
                       "concept_systems")},
    }


def needs_verify() -> List[Dict[str, Any]]:
    """诚实边界：需核实项。"""
    return list(_load().get("needs_verify", []))
