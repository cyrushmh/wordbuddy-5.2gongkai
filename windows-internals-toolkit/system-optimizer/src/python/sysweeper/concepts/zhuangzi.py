"""「南华」用户端概念系统只读层（v0.6.60，CLI 子命令 `zhuangzi`）。

数据来源：``data/concepts/zhuangzi_taxonomy.json``（由
``research/zhuangzi/build_zhuangzi.py`` 构建，桥接目标经 daoxue 治理原则 /
apilab 接口概念校验，无悬空边）。

以《南华真经》（《庄子》33 篇：内篇 7 / 外篇 15 / 杂篇 11）为**用户端
设计**的中心指导理念，与既有概念系统同构（plang / netsys / daoxue / quantum /
comp / apilab）：

    核心理念(core)       →  内篇三篇：逍遥游（无待一步）/ 应帝王（顺性不抢）/
                            大宗师（意图为宗师）
    内篇辅篇(inner)      →  齐物论（双模平权）/ 养生主（养生不伤）/
                            人间世（人间安命）/ 德充符（德充于内）
    外篇与杂篇(outer)     →  26 篇中选登 5 条（秋水 / 天道 / 达生 / 胠箧 / 概览）
    工程原则(ergonomics) →  七条可审计的用户端人体工程学原则

并把用户端「实测面」登记在案：CLI 子命令数 / GUI 窗口数 / webapi ACTIONS
数 / deno 控制台与报告查看器版本（构建时实测，--check 防漂移）。

只读、不联网、不改动数据；不复制经典全文，只登记篇旨/落法；篇旨按通行本
登记并统一标 needs_verify（用户未上传原典核对）。
"""
from __future__ import annotations

from ._common import load_taxonomy
from typing import Any, Dict, List, Optional

_DATA = "zhuangzi_taxonomy.json"


def _load() -> Dict[str, Any]:
    """加载 data/concepts/zhuangzi_taxonomy.json（共享加载器，带缓存，只读）。"""
    return load_taxonomy(_DATA)


def info() -> Dict[str, Any]:
    """返回 _meta（主目录 / 四轴结构 / 诚实边界说明）。"""
    return _load().get("_meta", {})


def layers() -> List[Dict[str, Any]]:
    """四层结构：core / inner / outer / ergonomics（含各自 sense 与条数）。"""
    return list(_load().get("layers", []))


def domains() -> List[Dict[str, Any]]:
    """四轴定义（core / inner / outer / ergonomics）。"""
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
    """全部概念条目：12 篇目（core/inner/outer）+ 7 条工程原则（ergonomics）。"""
    return list(_load().get("concepts", []))


def concepts_of_domain(name: str) -> List[Dict[str, Any]]:
    """某轴下的概念条目（core / inner / outer / ergonomics）。"""
    q = (name or "").strip()
    return [c for c in concepts() if c.get("domain") == q]


def concept(cid: str) -> Optional[Dict[str, Any]]:
    """按 id 取单条概念（篇目或工程原则）。"""
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
    """七条用户端人体工程学原则（含经典依据与工程落法）。"""
    return list(_load().get("principles", []))


def principle(pid: str) -> Optional[Dict[str, Any]]:
    """取单条人体工程学原则。"""
    q = (pid or "").strip()
    for p in principles():
        if p["id"] == q:
            return p
    return None


def principles_of_canon(canon: str) -> List[Dict[str, Any]]:
    """某篇（逍遥游/应帝王/……）对应的人体工程学原则。"""
    q = (canon or "").strip()
    return [p for p in principles() if q in p.get("canon_refs", [])]


def principles_of(cid: str) -> List[Dict[str, Any]]:
    """principles_of_canon 的别名（v0.6.62 API 归一，与 datong 同名）。"""
    return principles_of_canon(cid)


def user_face() -> Dict[str, Any]:
    """本仓库用户端面实测事实（CLI/GUI/webapi/deno 四端，构建期实测）。"""
    return _load().get("user_face_facts", {})


def bridges(system: str = "") -> List[Dict[str, Any]]:
    """理念 → 既有概念系统的桥接边；给 system 则过滤（daoxue/apilab）。"""
    out = list(_load().get("bridges", []))
    if system:
        q = system.strip().lower()
        out = [b for b in out if b.get("system") == q]
    return out


def bridges_of(cid: str) -> List[Dict[str, Any]]:
    """某概念（篇目或原则）发出的桥接边。"""
    q = (cid or "").strip()
    return [b for b in bridges() if b.get("from") == f"zhuangzi:{q}"]


def search(q: str) -> List[Dict[str, Any]]:
    """跨篇目与原则检索（篇旨 / detail / 工程落法 / 经典依据）。"""
    term = (q or "").strip()
    if not term:
        return []
    out: List[Dict[str, Any]] = []
    for c in concepts():
        if (term in c["name"] or term in c.get("gist", "")
                or term in c.get("detail", "") or term in c.get("engineering", "")):
            out.append({
                "where": f"南华真经·{c['domain']}",
                "name": c["name"],
                "text": c.get("gist", ""),
                "id": c["id"],
                "engineering": c.get("engineering", ""),
            })
    return out


def stats() -> Dict[str, Any]:
    """概念系统规模统计（与 counts / layers 一致）。"""
    doc = _load()
    by_domain = doc.get("by_domain", {})
    return {
        "concepts": doc["_meta"].get("concept_total", len(doc.get("concepts", []))),
        "principles": doc["_meta"].get("principle_total", len(doc.get("principles", []))),
        "bridges": doc["_meta"].get("bridge_count", len(doc.get("bridges", []))),
        "by_domain": {k: len(v) for k, v in by_domain.items()},
        "user_face": {k: user_face().get(k) for k in
                      ("cli_subcommands", "webapi_actions", "gui_windows",
                       "deno_console_version", "deno_report_viewer_version")},
    }


def needs_verify() -> List[Dict[str, Any]]:
    """诚实边界：需核实项（原典未逐字核对 / 外杂 22 篇未选登 / 原则系工程翻译）。"""
    return list(_load().get("needs_verify", []))
