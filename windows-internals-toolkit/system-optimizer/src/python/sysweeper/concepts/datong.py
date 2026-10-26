"""「大同」概念系统只读层（v0.6.62，CLI 子命令 `datong`）。

数据来源：``data/concepts/datong_taxonomy.json``（由
``research/datong/build_datong.py`` 构建，桥接目标经八个既有概念系统逐一
校验，无悬空边）。

立意（用户原话）：「人类命运是一个的，古今中外的宗教哲学都融合起来，
这才是人类文明文化生活」，「一体两面，三位一体，主的神恩如狱，还有
萨满巫觋等」；「虽然人类是一体的，但是想要人类健康科学有序的发展，
还是要宣扬天罡元阳、地煞元阴的正道，类似科学的，把固液气、电磁波，
这六样是正道」；「古来唯道独成尊」。

与 daoxue（治理理念面）构成「理—用」两面，与既有八系统同构：

    文明传统(traditions) → 儒/道/佛/基督/伊斯兰/犹太/印度/耆那/锡克/
                           琐罗亚斯德/希腊/神道/萨满巫觋/古埃及两河/巴哈伊
    核心命题(theses)     → 唯道独尊为宗，一体两面/三位一体/神恩如狱等 21 条
    正道六象(six)        → 固/液/气/电/磁/波——天罡元阳（气·电·波·外发）/
                           地煞元阴（固·液·磁·内聚），类科学的自然正道
    实践形态(practices)  → 12 条文化生活实践（祷告/禅定/萨满出神/朝觐…）
    人间落法(ethics)     → 九条可审计工程原则（= principles）

诚实边界：只读登记、不宣扬任何宗教为真理、不复制经典全文；跨传统
条目只作结构同构登记（神学内涵各自不同）；元阳元阴六象之分属为本
系统正名约定（非物理学分类）；未核对原典/年代分歧/词源争议统一挂
needs_verify。
"""
from __future__ import annotations

from ._common import load_taxonomy
from typing import Any, Dict, List, Optional

_DATA = "datong_taxonomy.json"


def _load() -> Dict[str, Any]:
    """加载 data/concepts/datong_taxonomy.json（共享加载器，带缓存，只读）。"""
    return load_taxonomy(_DATA)


def info() -> Dict[str, Any]:
    """返回 _meta（主目录 / 五轴结构 / 诚实边界说明）。"""
    return _load().get("_meta", {})


def layers() -> List[Dict[str, Any]]:
    """五层结构：traditions / theses / six / practices / ethics。"""
    return list(_load().get("layers", []))


def domains() -> List[Dict[str, Any]]:
    """五轴定义。"""
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
    """全部概念条目：文明传统 15 + 核心命题 21 + 正道六象 6 + 实践形态 12
    + 人间落法 9。"""
    return list(_load().get("concepts", []))


def concepts_of_domain(name: str) -> List[Dict[str, Any]]:
    """某轴下的概念条目（traditions / theses / six / practices / ethics）。"""
    q = (name or "").strip()
    return [c for c in concepts() if c.get("domain") == q]


def concept(cid: str) -> Optional[Dict[str, Any]]:
    """按 id 取单条概念（传统 / 命题 / 六象 / 实践 / 原则）。"""
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
    """九条人间落法工程原则（含理念依据与工程落法）。"""
    return list(_load().get("principles", []))


def principle(pid: str) -> Optional[Dict[str, Any]]:
    """取单条人间落法工程原则。"""
    q = (pid or "").strip()
    for p in principles():
        if p["id"] == q:
            return p
    return None


def principles_of(cid: str) -> List[Dict[str, Any]]:
    """依据某传统/命题/原则的原则条目（canon_refs 反查）。"""
    q = (cid or "").strip()
    return [p for p in principles() if q in p.get("canon_refs", [])]


def principles_of_canon(canon: str) -> List[Dict[str, Any]]:
    """principles_of 的别名（与 zhuangzi/baigong 同名，v0.6.62 API 归一）。"""
    return principles_of(canon)


def user_face() -> Dict[str, Any]:
    """本仓库用户端面 + 语言面实测事实（构建期实测）。"""
    return _load().get("user_face_facts", {})


def bridges(system: str = "") -> List[Dict[str, Any]]:
    """理念 → 既有概念系统的桥接边；给 system 则过滤
    （daoxue/zhuangzi/baigong/plang/comp/quantum/netsys/apilab）。"""
    out = list(_load().get("bridges", []))
    if system:
        q = system.strip().lower()
        out = [b for b in out if b.get("system") == q]
    return out


def bridges_of(cid: str) -> List[Dict[str, Any]]:
    """某概念（传统/命题/六象/实践/原则）发出的桥接边。"""
    q = (cid or "").strip()
    return [b for b in bridges() if b.get("from") == f"datong:{q}"]


def search(q: str) -> List[Dict[str, Any]]:
    """跨五轴检索（纲宗 / detail / 工程落法 / 通名）。"""
    term = (q or "").strip()
    if not term:
        return []
    out: List[Dict[str, Any]] = []
    for c in concepts():
        if (term in c["name"] or term in c.get("gist", "")
                or term in c.get("detail", "") or term in c.get("engineering", "")):
            out.append({
                "where": f"大同·{c['domain']}",
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
                       "lang_total", "probe_verified", "comp_lang_needs")},
    }


def needs_verify() -> List[Dict[str, Any]]:
    """诚实边界：需核实项（原典未核对 / 诗化表达口径 / 同构框架自定 /
    年代分歧 / 词源争议 / 正名约定 / 概说）。"""
    return list(_load().get("needs_verify", []))
