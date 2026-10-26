"""「protec」产品（设备设施）长期运行与基本保护概念系统只读层（v0.6.66，CLI 子命令 `protec`）。

数据来源：``data/concepts/protec_taxonomy.json``（由
``research/protec/build_protec.py`` 构建，桥接目标经 netsys 与七个既有概念系统
逐一校验，无悬空边）。

立意（用户原话）：「材料学、热力学、气候学、环境学、物理、化学、生物等以及相关
对产品（设备设施）长期运行和基本保护的协议和标准查看」。

整合 sysweeper 既有产品保护域四个原生引擎（durability/electrical/env/emergency）
与 IEC/ASHRAE/IP/GB 标准，统于七条基本保护原则（protection = principles）：

    材料耐久(durability)  : 腐蚀/疲劳/蠕变/热老化/湿气侵入/电池衰减/材料选型
    电气安全(electrical)  : 接触高阻发热/电偶腐蚀/串联电弧/接地RCD/连接器老化/可燃底座
    环境标准(environment) : IP代码/IEC 60721/ASHRAE TC9.9/IEC 62368-1
    应急保护(emergency)   : CAP 1.2 四级预警/定位融合/求救报文/应急物资清单
    基本保护(protection)  : 冗余/降额/隔离/监控/接地/防护/可维护（= principles）
    传输与可用性(transfer) : TCP/QUIC/HTTP Range/完整性/TLS/Anycast/一致性哈希/熔断
    接入与链路(access)    : 以太网/WLAN/WiFi 安全/802.1X/VLAN/PPPoE/星闪
    IPv6 控制面(ipv6)     : IPv6 基址/ICMPv6/NDP/SLAAC/DHCPv6/PMTUD/NAT64·DNS64/
                            6LoWPAN/SEND·CGA/MLD（v0.6.69 新增，与 docs/76 同源）

与 sciences（自然科学）构成「科学底座 → 工程保护」对照。诚实边界：只读登记、
标准编号按通行口径、不臆造实测数字；桥接只作保护原则 ↔ 工程伦理/接口/编译/量子
缓解的结构翻译，不宣称等同；应急定位 ETA 按置信下限诚实标注。
"""
from __future__ import annotations

from ._common import load_taxonomy
from typing import Any, Dict, List, Optional

_DATA = "protec_taxonomy.json"


def _load() -> Dict[str, Any]:
    """加载 data/concepts/protec_taxonomy.json（共享加载器，带缓存，只读）。"""
    return load_taxonomy(_DATA)


def info() -> Dict[str, Any]:
    """返回 _meta（主目录 / 八轴结构 / 诚实边界说明）。"""
    return _load().get("_meta", {})


def layers() -> List[Dict[str, Any]]:
    """八层结构：durability / electrical / environment / emergency / protection /
    transfer / access / ipv6（v0.6.67 transfer、v0.6.68 access、v0.6.69 ipv6 先后新增）。"""
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
    """全部概念条目：材料耐久 7 + 电气安全 6 + 环境标准 4 + 应急保护 4 +
    基本保护 7（protection = principles）。"""
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
    """七条基本保护工程原则（含理念依据与工程落法）。"""
    return list(_load().get("principles", []))


def principle(pid: str) -> Optional[Dict[str, Any]]:
    """取单条基本保护工程原则。"""
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
    """principles_of 的别名（与 datong/zhuangzi/baigong 同名，v0.6.66 API 归一）。"""
    return principles_of(canon)


def user_face() -> Dict[str, Any]:
    """本仓库用户端面 + 语言面实测事实（构建期实测）。"""
    return _load().get("user_face_facts", {})


def bridges(system: str = "") -> List[Dict[str, Any]]:
    """保护概念 → 既有概念系统的桥接边；给 system 则过滤。"""
    out = list(_load().get("bridges", []))
    if system:
        q = system.strip().lower()
        out = [b for b in out if b.get("system") == q]
    return out


def bridges_of(cid: str) -> List[Dict[str, Any]]:
    """某概念发出的桥接边。"""
    q = (cid or "").strip()
    return [b for b in bridges() if b.get("from") == f"protec:{q}"]


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
                "where": f"protec·{c['domain']}",
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
    """诚实边界：需核实项（标准版次 / 经验模型 / 结构性翻译 / 量级诚实标注）。"""
    return list(_load().get("needs_verify", []))
