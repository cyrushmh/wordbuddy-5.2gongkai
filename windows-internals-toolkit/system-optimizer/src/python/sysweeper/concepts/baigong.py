"""「百工」概念系统只读层（v0.6.61，CLI 子命令 `baigong`）。

数据来源：``data/concepts/baigong_taxonomy.json``（由
``research/baigong/build_baigong.py`` 构建，桥接目标经七个既有概念系统逐一
校验，无悬空边）。

以**墨子、公输般、公孙策、鲁班**（可扩大为三教九流）为工程理念，落实用户
点名的三个场景——「具体无解 / 暂时不允许 / 构建程序具体结构」——与七系统
同构（plang / netsys / daoxue / quantum / comp / apilab / zhuangzi）：

    核心理念(core)     →  五偶：墨子（守御·明辩）/ 公输般（九设九距）/
                            鲁班（绳墨）/ 公孙策（锦囊）/ 三教九流总纲
    匠作原则(craft)    →  七条可审计的匠作工程原则
    三教九流(schools)  →  三教 3 + 九流 9，一流一工程域映射
    工程场景(scenes)   →  无解（悬置降级）/ 暂不允许（守御 opt-in）/
                            具体结构（绳墨与九设九距）

并把「实测面」登记在案：CLI 子命令数 / GUI 窗口数 / webapi ACTIONS 数 /
deno 两文件版本 + 语言面三项（plang 161 条 / probe 实测 15 种 / comp 语言
编译需要 16 条），构建期实测、--check 防漂移。

只读、不联网、不改动数据；不复制经典全文，引文按通行本登记并统一标
needs_verify（用户未上传原典核对；公输般即鲁班一名两译；公孙策系文学形象）。
"""
from __future__ import annotations

from ._common import load_taxonomy
from typing import Any, Dict, List, Optional

_DATA = "baigong_taxonomy.json"


def _load() -> Dict[str, Any]:
    """加载 data/concepts/baigong_taxonomy.json（共享加载器，带缓存，只读）。"""
    return load_taxonomy(_DATA)


def info() -> Dict[str, Any]:
    """返回 _meta（主目录 / 四轴结构 / 诚实边界说明）。"""
    return _load().get("_meta", {})


def layers() -> List[Dict[str, Any]]:
    """四层结构：core / craft / schools / scenes（含各自 sense 与条数）。"""
    return list(_load().get("layers", []))


def domains() -> List[Dict[str, Any]]:
    """四轴定义（core / craft / schools / scenes）。"""
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
    """全部概念条目：五偶（core）+ 三教九流 12（schools）+ 场景 3（scenes）
    + 匠作原则 7（craft）。"""
    return list(_load().get("concepts", []))


def concepts_of_domain(name: str) -> List[Dict[str, Any]]:
    """某轴下的概念条目（core / craft / schools / scenes）。"""
    q = (name or "").strip()
    return [c for c in concepts() if c.get("domain") == q]


def concept(cid: str) -> Optional[Dict[str, Any]]:
    """按 id 取单条概念（五偶 / 匠作原则 / 教派条目 / 场景条目）。"""
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
    """七条匠作工程原则（含理念依据与工程落法）。"""
    return list(_load().get("principles", []))


def principle(pid: str) -> Optional[Dict[str, Any]]:
    """取单条匠作工程原则。"""
    q = (pid or "").strip()
    for p in principles():
        if p["id"] == q:
            return p
    return None


def principles_of_canon(canon: str) -> List[Dict[str, Any]]:
    """某理念人物（墨子/公输般/鲁班/公孙策）对应的匠作工程原则。"""
    q = (canon or "").strip()
    return [p for p in principles() if q in p.get("canon_refs", [])]


def principles_of(cid: str) -> List[Dict[str, Any]]:
    """principles_of_canon 的别名（v0.6.62 API 归一，与 datong 同名）。"""
    return principles_of_canon(cid)


def user_face() -> Dict[str, Any]:
    """本仓库用户端面 + 语言面实测事实（构建期实测）。"""
    return _load().get("user_face_facts", {})


def bridges(system: str = "") -> List[Dict[str, Any]]:
    """理念 → 既有概念系统的桥接边；给 system 则过滤
    （plang/netsys/daoxue/quantum/comp/apilab/zhuangzi）。"""
    out = list(_load().get("bridges", []))
    if system:
        q = system.strip().lower()
        out = [b for b in out if b.get("system") == q]
    return out


def bridges_of(cid: str) -> List[Dict[str, Any]]:
    """某概念（五偶 / 原则 / 教派 / 场景）发出的桥接边。"""
    q = (cid or "").strip()
    return [b for b in bridges() if b.get("from") == f"baigong:{q}"]


def search(q: str) -> List[Dict[str, Any]]:
    """跨四轴检索（纲宗 / detail / 工程落法 / 理念依据）。"""
    term = (q or "").strip()
    if not term:
        return []
    out: List[Dict[str, Any]] = []
    for c in concepts():
        if (term in c["name"] or term in c.get("gist", "")
                or term in c.get("detail", "") or term in c.get("engineering", "")):
            out.append({
                "where": f"百工·{c['domain']}",
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
                       "deno_console_version", "deno_report_viewer_version",
                       "lang_total", "probe_verified", "comp_lang_needs")},
    }


def needs_verify() -> List[Dict[str, Any]]:
    """诚实边界：需核实项（引文未核对 / 一名两译 / 文学形象 / 工程翻译）。"""
    return list(_load().get("needs_verify", []))
