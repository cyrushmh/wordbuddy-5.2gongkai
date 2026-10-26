"""「道枢」概念系统只读层（v0.6.58，CLI 子命令 `daoxue`）。

数据来源：``data/concepts/daoxue_taxonomy.json``（由 ``research/daoxue/build_daoxue.py`` 从
用户提供的《道德经》/《太上玄门早坛功课经》/《太上玄门晚坛功课经》源文本解析构建，
桥接目标经 plang / netsys / langref 校验，无悬空边）。

以仓库 wordbuddy-github 为主目录的**治理层**概念系统：

    前置指导思想(pre)  →  太上玄门早坛功课经：启明·清净·立愿
    中心指导理念(center)→  《道德经》：81 章（道经 1–37 / 德经 38–81）
    中间二级(middle)   →  《般若波罗蜜多心经》破相 + 《论语》立礼
    后置指导思想(post) →  太上玄门晚坛功课经：忏悔·解冤·回向·普度
    方术子层(fangshu)  →  符箓·咒语·画符仪轨·祝由（tier=3，符/箓/咒/法/由 五域）
    整体元指导(zhengti)→  因果记录·全息·感应（tier=0）：阿卡西记录/宇宙全息论/三世石/望乡台/
                          三世因果经/文昌帝君阴鸷文/黄帝阴符经/太上感应篇（九系统共享理念底座）

并把理念翻译成 15 条**可审计的工程治理原则**，桥接到本仓库既有概念系统
（plang 编程语言 / netsys 网络组网 / langref 语言知识库）。

治理层讲「理」，方术层讲「用」——同一套治理原则落到的具体形制、仪轨与名籍。
方术层的诚实红线（与 _meta.honesty 一致）：

    · 只登记文献、形制、仪轨结构与分类，**不录入符图笔画与咒文全文**
    · 不主张符咒祝由有任何超自然效力或医疗疗效
    · 涉医疗的祝由一支只作文文献与官制沿革登记，**不构成医疗建议**
    · 民间法脉口传内容按来源分级（官制 > 典籍 > 抄本 > 口传）挂 needs_verify

只读、不联网、不改动数据；不复制经典全文，只登记章旨/节旨/纲宗与映射。
"""
from __future__ import annotations

from ._common import load_taxonomy
from typing import Any, Dict, List, Optional

_DATA = "daoxue_taxonomy.json"


def _load() -> Dict[str, Any]:
    """加载 data/concepts/<name>_taxonomy.json（共享加载器，带缓存，只读）。"""
    return load_taxonomy(_DATA)


def info() -> Dict[str, Any]:
    """返回 _meta（主目录 / 四层结构 / 诚实边界说明）。"""
    return _load().get("_meta", {})


def layers() -> List[Dict[str, Any]]:
    """五层结构：pre / center / middle / post / fangshu（含各自 sense 说明）。"""
    doc = _load()
    out = []
    for l in doc.get("_meta", {}).get("layers", []):
        item = dict(l)
        if l["role"] == "center":
            item["count"] = len(doc.get("center", {}).get("chapters", []))
        elif l["role"] in ("pre", "post"):
            item["count"] = len(doc.get(l["role"], {}).get("sections", []))
        elif l["role"] == "fangshu":
            item["count"] = sum(len(d.get("items", []))
                                for d in doc.get("fangshu", {}).get("domains", []))
        else:
            item["count"] = sum(len(m["sections"]) for m in doc.get("middle", []))
        out.append(item)
    return out


def center() -> Dict[str, Any]:
    """中心指导理念《道德经》：篇属 + 81 章。"""
    return _load().get("center", {})


def chapters() -> List[Dict[str, Any]]:
    """81 章清单（章号 / 篇属 / 章旨 / 节旨 / 归属原则）。"""
    return list(_load().get("center", {}).get("chapters", []))


def chapter(no: int) -> Optional[Dict[str, Any]]:
    """按章号取单章（1–81）。"""
    try:
        n = int(no)
    except (TypeError, ValueError):
        return None
    for c in chapters():
        if c["no"] == n:
            return c
    return None


def chapters_of_principle(pid: str) -> List[Dict[str, Any]]:
    """某治理原则对应的《道德经》章节。"""
    q = (pid or "").strip()
    return [c for c in chapters() if c.get("principle") == q]


def office(role: str) -> Dict[str, Any]:
    """前置(pre=早坛) / 后置(post=晚坛) 功课经全文结构。"""
    return _load().get(role, {}) if role in ("pre", "post") else {}


def sections_of(role: str, phase: str = "") -> List[Dict[str, Any]]:
    """某功课经的节次；给 phase 则按课程序位过滤（如 净坛 / 诵经 / 礼诰 / 忏悔 / 结行）。"""
    secs = list(office(role).get("sections", []))
    if phase:
        q = phase.strip()
        secs = [s for s in secs if s.get("phase") == q]
    return secs


def phases_of(role: str) -> List[Dict[str, Any]]:
    """某功课经的课程序位清单（含每序位节数）。"""
    cnt: Dict[str, int] = {}
    order: List[str] = []
    for s in office(role).get("sections", []):
        p = s.get("phase", "?")
        if p not in cnt:
            cnt[p] = 0
            order.append(p)
        cnt[p] += 1
    return [{"phase": p, "count": cnt[p]} for p in order]


def middle() -> List[Dict[str, Any]]:
    """中间二级思想：心经（破相）+ 论语（立礼）。"""
    return list(_load().get("middle", []))


def fangshu() -> Dict[str, Any]:
    """方术子层（tier=3）整体：符/箓/咒/法/由 五域（canon / sense / 工程映射）。

    定位：治理层讲「理」，方术层讲「用」。只登记文献、形制、仪轨结构与分类，
    **不录入符图笔画与咒文全文**，不主张任何超自然效力或医疗疗效。
    """
    return _load().get("fangshu", {})


def fangshu_domains() -> List[Dict[str, Any]]:
    """方术六域：fu 符 / lu 箓 / zhou 咒 / fa 法 / you 由 / zhen 阵（各含 items）。"""
    return list(_load().get("fangshu", {}).get("domains", []))


def fangshu_domain(name: str) -> Optional[Dict[str, Any]]:
    """按域名取单域（fu / lu / zhou / fa / you / zhen）。"""
    q = (name or "").strip()
    for d in fangshu_domains():
        if d["domain"] == q:
            return d
    return None


def fangshu_items(domain: str = "") -> List[Dict[str, Any]]:
    """方术条目；给 domain 则只取该域（如 ``fangshu_items("you")`` 取祝由一支）。"""
    q = (domain or "").strip()
    out: List[Dict[str, Any]] = []
    for d in fangshu_domains():
        if q and d["domain"] != q:
            continue
        out.extend(d.get("items", []))
    return out


def fangshu_item(fid: str) -> Optional[Dict[str, Any]]:
    """按 id 取单条方术条目（如 ``fu-dan`` / ``you-shisanke``）。"""
    q = (fid or "").strip()
    for x in fangshu_items():
        if x["id"] == q:
            return x
    return None


def fangshu_of_principle(pid: str) -> List[Dict[str, Any]]:
    """某治理原则落到方术层的条目（principle 反查）。"""
    q = (pid or "").strip()
    return [x for x in fangshu_items() if x.get("principle") == q]


def fangshu_search(term: str) -> List[Dict[str, Any]]:
    """方术子层检索：按关键词过滤条目（name/gist/detail/engineering/domain/id）。

    空词返回全量；大小写不敏感；供 GUI 方术页实时检索联动，与 ``search()`` 同源口径。
    """
    q = (term or "").strip().lower()
    if not q:
        return fangshu_items()
    out: List[Dict[str, Any]] = []
    for x in fangshu_items():
        hay = " ".join([
            x.get("name", ""), x.get("gist", ""), x.get("detail", ""),
            x.get("engineering", ""), x.get("domain", ""), x.get("id", ""),
        ]).lower()
        if q in hay:
            out.append(x)
    return out


def fangshu_bridges(system: str = "") -> List[Dict[str, Any]]:
    """方术层发出的桥接边（带 ``fangshu`` 字段溯源到条目）；给 system 则过滤。"""
    out = [b for b in _load().get("bridges", []) if b.get("fangshu")]
    if system:
        q = system.strip().lower()
        out = [b for b in out if b.get("system") == q]
    return out


def principles() -> List[Dict[str, Any]]:
    """15 条工程治理原则（含经典依据与工程落法）。"""
    return list(_load().get("principles", []))


def principle(pid: str) -> Optional[Dict[str, Any]]:
    """取单条治理原则。"""
    q = (pid or "").strip()
    for p in principles():
        if p["id"] == q:
            return p
    return None


def bridges(system: str = "") -> List[Dict[str, Any]]:
    """理念 → 既有概念系统的桥接边；给 system 则过滤（plang/netsys/langref）。"""
    out = list(_load().get("bridges", []))
    if system:
        q = system.strip().lower()
        out = [b for b in out if b.get("system") == q]
    return out


def apply_to(system: str) -> List[Dict[str, Any]]:
    """某系统（plang/netsys/langref）适用的治理原则及落法（按原则展开）。"""
    q = (system or "").strip().lower()
    pmap = {p["id"]: p for p in principles()}
    out = []
    for b in bridges(q):
        p = pmap.get(b["principle"], {})
        out.append({
            "principle": b["principle"],
            "name": p.get("name", ""),
            "target": b["target"],
            "relation": b["relation"],
            "how": b["how"],
            "canon_refs": p.get("canon_refs", []),
        })
    return out


def search(q: str) -> List[Dict[str, Any]]:
    """跨层检索（章旨 / 节名 / 节旨 / 原则 / 纲宗 / 工程落法）。"""
    term = (q or "").strip()
    if not term:
        return []
    out: List[Dict[str, Any]] = []
    for c in chapters():
        if term in c["theme"] or term in c.get("gist", ""):
            out.append({"where": f"道德经 第{c['no']}章", "name": c["theme"],
                        "text": c.get("gist", ""), "principle": c["principle"]})
    for role in ("pre", "post"):
        canon = office(role).get("canon", role)
        for s in office(role).get("sections", []):
            if term in s["name"] or term in s.get("gist", ""):
                out.append({"where": f"{canon}·{s['phase']}", "name": s["name"],
                            "text": s.get("gist", ""), "principle": ""})
    for m in middle():
        for s in m.get("sections", []):
            if (term in s["name"] or term in s.get("gist", "")
                    or term in s.get("engineering", "")):
                out.append({"where": f"{m['canon']}·二级", "name": s["name"],
                            "text": s.get("gist", ""),
                            "principle": s.get("engineering", "")})
    for p in principles():
        if (term in p["name"] or term in p.get("gist", "")
                or term in p.get("engineering", "") or term in p["id"]):
            out.append({"where": "治理原则", "name": f"{p['name']}（{p['id']}）",
                        "text": p.get("gist", ""),
                        "principle": p.get("engineering", "")})
    dom_name = {d["domain"]: d["name"] for d in fangshu_domains()}
    for x in fangshu_items():
        if (term in x["name"] or term in x.get("gist", "")
                or term in x.get("detail", "") or term in x.get("engineering", "")
                or term in x["id"]):
            out.append({"where": f"方术·{dom_name.get(x['domain'], x['domain'])}",
                        "name": x["name"], "text": x.get("gist", ""),
                        "id": x["id"],
                        "principle": x.get("engineering", ""),
                        "needs_verify": x.get("needs_verify", "")})
    return out


def stats() -> Dict[str, Any]:
    """概念系统规模统计（与 counts 一致）。"""
    doc = _load()
    return dict(doc.get("counts", {}))


def needs_verify() -> List[Dict[str, Any]]:
    """诚实边界：需核实的条目（心经/论语未提供原典、道德经古文原文缺失）。"""
    return list(_load().get("needs_verify", []))
