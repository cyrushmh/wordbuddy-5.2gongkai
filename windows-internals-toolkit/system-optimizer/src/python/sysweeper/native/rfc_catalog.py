# -*- coding: utf-8 -*-
"""
RFC 全量标准目录（只读消费层）
================================
数据来源：data/rfc_standards.json —— 由 research/harvest/rfc_index_harvest.py
从 rfc-editor.org 官方 RFC INDEX 解析生成（10,036 条，含 188 个 Not Issued）。
本模块不联网、不修改数据，只提供查询与「按 RFC 聚合任务引用」视图，
让 sysweeper 每一条 standards 里的 "RFC NNNN" 都能回溯到官方索引条目。

用法示例：
    from sysweeper.native import rfc_catalog as cat
    cat.catalog_size()          # {'total': 10036, 'issued': 9848, ...}
    cat.rfc_info(9846)          # 单条（int / '9846' / 'rfc09846' 均可）
    cat.search("TLS")           # 标题/作者检索
    cat.citing_tasks_for(9846)  # 反向：哪些任务引用了 RFC 9846
    cat.rfc_relations(8415)     # 关系视图（obsoletes/obsoleted-by/...）
    cat.rfc_current(8415)       # 废止链末端：现行 RFC（8415 -> 9915）
    cat.series_members("STD13") # STD13（DNS）系列成员
    cat.topics()                # 主题域速览（heuristic 索引）
    cat.topic_members("tls-pki")# 某主题域成员
    cat.topic_of(9846)          # 单条 RFC 的主题域归属（含命中规则）
    cat.citation_audit()        # 任务引用对账：悬空/已废止仍被引用
"""
import json
import re
from typing import Dict, List, Optional

_DATA_FILE = "rfc_standards.json"
_TOPIC_FILE = "rfc_topic_index.json"
_WG_FILE = "rfc_wg_index.json"
_CATALOG: Optional[dict] = None
_CITING: Optional[Dict[str, List[str]]] = None
_TOPIC: Optional[dict] = None
_WG: Optional[dict] = None

_RFC_TOKEN_RE = re.compile(r"RFC\s*(\d{1,5})")


def _catalog() -> dict:
    """惰性加载全量 RFC 索引（2.3MB JSON，避免 import 期阻塞）。"""
    global _CATALOG
    if _CATALOG is None:
        try:
            from importlib import resources
            data = resources.files("sysweeper.data").joinpath(
                _DATA_FILE).read_text(encoding="utf-8")
            _CATALOG = json.loads(data)
        except Exception:
            _CATALOG = {}
    return _CATALOG


def _key(num) -> Optional[str]:
    """归一化 RFC 编号入口：9846 / '9846' / 'rfc09846' -> 'rfc09846'。"""
    if num is None:
        return None
    s = str(num).strip().lower()
    m = re.match(r"^(?:rfc)?\s*0*(\d{1,5})$", s)
    if not m:
        return None
    return "rfc%05d" % int(m.group(1))


def rfc_info(num) -> Optional[dict]:
    """单条 RFC 元数据；编号未出现（未分配）或格式非法返回 None。"""
    k = _key(num)
    if not k:
        return None
    return _catalog().get(k)


def catalog_size() -> dict:
    """目录规模统计（总条目/已发布/未发布/状态分布）。"""
    cat = _catalog()
    issued = sum(1 for e in cat.values() if e.get("i"))
    dist: Dict[str, int] = {}
    for e in cat.values():
        s = e.get("s") or "NOT_ISSUED"
        dist[s] = dist.get(s, 0) + 1
    return {
        "total": len(cat),
        "issued": issued,
        "not_issued": len(cat) - issued,
        "status_distribution": dict(sorted(dist.items(), key=lambda kv: -kv[1])),
        "source": "data/rfc_standards.json（rfc-editor.org RFC INDEX 解析）",
    }


def search(term: str, limit: int = 20) -> List[dict]:
    """按标题/作者检索（大小写不敏感）。标题前缀 > 标题包含 > 作者包含。"""
    t = (term or "").strip().lower()
    if not t:
        return []
    hits = []
    for e in _catalog().values():
        if not e.get("i"):
            continue
        title = (e.get("t") or "").lower()
        authors = (e.get("a") or "").lower()
        if title.startswith(t):
            hits.append((0, e))
        elif t in title:
            hits.append((1, e))
        elif t in authors:
            hits.append((2, e))
    hits.sort(key=lambda x: (x[0], x[1]["n"]))
    return [e for _, e in hits[:limit]]


def by_status(status: str, limit: int = 50) -> List[dict]:
    """按状态过滤（INTERNET STANDARD / BEST CURRENT PRACTICE / HISTORIC ...）。"""
    s = (status or "").strip().upper()
    if not s:
        return []
    out = [e for e in _catalog().values() if e.get("i") and e.get("s") == s]
    out.sort(key=lambda e: e["n"])
    return out[:limit]


def latest(limit: int = 20) -> List[dict]:
    """最新发布的若干条（按编号倒序，索引即按编号=时间顺序）。"""
    out = sorted((e for e in _catalog().values() if e.get("i")),
                 key=lambda e: -e["n"])
    return out[:limit]


def citing_tasks() -> Dict[str, List[str]]:
    """反向索引：RFC 编号 -> 引用它的 sysweeper 任务 ID 列表。

    扫描 registry 全量任务的 standards 字段中的 "RFC NNNN" 记号。
    """
    global _CITING
    if _CITING is not None:
        return _CITING
    result: Dict[str, List[str]] = {}
    try:
        from ..registry import all_tasks
        tasks = all_tasks()
    except Exception:
        tasks = []
    for t in tasks:
        for s in (getattr(t, "standards", None) or []):
            for m in _RFC_TOKEN_RE.findall(s):
                result.setdefault("rfc%05d" % int(m), [])
                if t.id not in result["rfc%05d" % int(m)]:
                    result["rfc%05d" % int(m)].append(t.id)
    _CITING = result
    return result


def citing_tasks_for(num) -> List[str]:
    """哪些任务引用了该 RFC（可能为空列表——未被引用不代表不重要）。"""
    k = _key(num)
    if not k:
        return []
    return citing_tasks().get(k, [])


# ---------------------------------------------------------------
# v2 关系层：obsoletes / obsoleted-by / updates / updated-by / also
# ---------------------------------------------------------------

_REL_FIELDS = (("obs", "obsoletes"), ("oby", "obsoleted_by"),
               ("upd", "updates"), ("udy", "updated_by"))
_MAX_CHAIN_HOPS = 30


def _rel_target(cat: dict, n: int) -> dict:
    """关系指向目标：始终带编号 n；能解析出元数据时 resolved=True。

    编号不在本索引（目录外引用）时只给 n 与 resolved=False——
    不臆造标题/状态，也不丢失编号（调用方需要如实展示「指向谁」）。
    """
    e = cat.get("rfc%05d" % n)
    if not e:
        return {"n": n, "resolved": False}
    return {"n": n, "resolved": True, "t": e.get("t"), "s": e.get("s"),
            "d": e.get("d")}


def relations_stats() -> dict:
    """关系字段覆盖统计（数据层口径，忠于 rfc_standards.json v2）。"""
    cat = _catalog()
    cov = {dest: sum(1 for e in cat.values() if e.get(src))
           for src, dest in _REL_FIELDS}
    cov["also"] = sum(1 for e in cat.values() if e.get("also"))
    return {
        "total": len(cat),
        "coverage": cov,
        "series_count": len(series_index()),
    }


def rfc_relations(num) -> Optional[dict]:
    """单条 RFC 的关系视图。

    返回 {n, t, s, obsoletes, obsoleted_by, updates, updated_by, also}，
    每个指向编号尽力解析出标题/状态/日期；指向编号不在本索引时该槽位
    为 None（如实标注，不臆造元数据）。
    """
    cat = _catalog()
    k = _key(num)
    if not k or k not in cat:
        return None
    e = cat[k]
    out = {"n": e.get("n"), "t": e.get("t"), "s": e.get("s")}
    for src, dest in _REL_FIELDS:
        nums = e.get(src)
        if not nums:
            continue
        out[dest] = [_rel_target(cat, n) for n in nums]
    if e.get("also"):
        out["also"] = e["also"]
    return out


def rfc_current(num) -> dict:
    """沿 obsoleted-by 链解析现行 RFC。

    返回 {input, current, chain, cycle, status, current_title, note}：
      status ∈ OK / NOT_IN_CATALOG / DANGLING_TARGET / CYCLE / TOO_DEEP
    链条罕见分叉（多个替代者）时以第一个为主线并记录 other_successors。
    """
    cat = _catalog()
    k = _key(num)
    base = {"input": num, "current": None, "chain": [], "cycle": False,
            "current_title": None}
    if not k or k not in cat:
        base["status"] = "NOT_IN_CATALOG"
        base["note"] = "编号不在官方 RFC INDEX 中"
        return base
    chain = [cat[k]["n"]]
    seen = {k}
    cur = k
    for _ in range(_MAX_CHAIN_HOPS):
        oby = (cat[cur].get("oby") or [])
        if not oby:
            entry = cat[cur]
            base.update(status="OK", current=entry["n"], chain=chain,
                        current_title=entry.get("t"))
            return base
        if len(oby) > 1:
            base["other_successors"] = [n for n in oby[1:]]
        nxt = oby[0]
        chain.append(nxt)
        nk = "rfc%05d" % nxt
        if nk not in cat:
            base.update(status="DANGLING_TARGET", chain=chain,
                        note="obsoleted-by 指向编号 %d 不在本索引" % nxt)
            return base
        if nk in seen:
            base.update(status="CYCLE", chain=chain,
                        note="obsoleted-by 链成环（%d）" % nxt)
            return base
        seen.add(nk)
        cur = nk
    base.update(status="TOO_DEEP", chain=chain,
                note="链长超过 %d 跳，疑似异常" % _MAX_CHAIN_HOPS)
    return base


def _norm_series(name) -> Optional[str]:
    """'STD 102' / 'std102' / 'STD102' -> 'STD102'；非系列名返回 None。"""
    if not name:
        return None
    s = re.sub(r"\s+", "", str(name)).upper()
    m = re.match(r"^(STD|BCP|FYI)(\d{1,4})$", s)
    if not m:
        return None
    return s


def series_index() -> Dict[str, List[int]]:
    """STD / BCP / FYI 系列 -> 成员 RFC 编号（升序，空目录返回空 dict）。"""
    idx: Dict[str, List[int]] = {}
    for e in _catalog().values():
        a = e.get("also")
        nk = _norm_series(a)
        if nk:
            idx.setdefault(nk, []).append(e["n"])
    for nk in idx:
        idx[nk] = sorted(idx[nk])
    return dict(sorted(idx.items(), key=lambda kv: (kv[0][:3], int(kv[0][3:]))))


def series_members(series) -> List[dict]:
    """某系列（'STD102' / 'bcp47' / 'STD 47'）的成员条目，按编号升序。"""
    nk = _norm_series(series)
    if not nk:
        return []
    nums = set(series_index().get(nk, []))
    out = [e for e in _catalog().values() if e.get("n") in nums]
    out.sort(key=lambda e: e["n"])
    return out


def _citing_with_context() -> Dict[str, List[dict]]:
    """带上下文的引用索引：RFC 编号 -> [{task, text}]（text 为命中的
    standards 原文）。供 citation_audit 区分「真引用」与「顺带提及」——
    例如 "[国际] RFC 9846（…废弃 RFC 8446…）" 里 8446 是废止说明而非引用。
    """
    result: Dict[str, List[dict]] = {}
    try:
        from ..registry import all_tasks
        tasks = all_tasks()
    except Exception:
        tasks = []
    for t in tasks:
        for s in (getattr(t, "standards", None) or []):
            for m in _RFC_TOKEN_RE.findall(s):
                k = "rfc%05d" % int(m)
                result.setdefault(k, []).append({"task": t.id, "text": s})
    return result


def citation_audit() -> dict:
    """任务侧 RFC 引用全量核验（应用对账口径）。

    扫描 registry 全部任务 standards 中的 "RFC NNNN" 记号，分三类：
      - dangling：编号不在官方索引（疑似笔误/私有扩展），附任务 ID
      - obsolete_cited：真引用且已被 obsoleted-by 取代，附任务 ID 与现行编号
        ——任务文本是否更新由维护者定夺，此处只报告不改写
      - obsolete_mention：同一条 standards 文本里废止者与现行编号共现
        （形如「RFC 9846（…废弃 RFC 8446…）」），属说明性提及，不算过期引用
    """
    cat = _catalog()
    cites = _citing_with_context()
    dangling: Dict[str, List[str]] = {}
    obsolete: Dict[str, dict] = {}
    mention: Dict[str, List[str]] = {}
    resolved = 0
    for k, hits in cites.items():
        if k not in cat:
            dangling[k] = sorted({h["task"] for h in hits})
            continue
        resolved += 1
        chain = rfc_current(k)
        if not (chain["status"] == "OK" and chain["current"] != cat[k]["n"]):
            continue
        cur_key = "rfc%05d" % chain["current"]
        # 同文本内已含现行编号 → 废止说明性提及；否则 → 过期真引用
        fresh = [h for h in hits
                 if any("rfc%05d" % int(m) == cur_key
                        for m in _RFC_TOKEN_RE.findall(h["text"]))]
        stale = [h for h in hits if h not in fresh]
        if fresh:
            mention.setdefault(k, sorted({h["task"] for h in fresh}))
        if stale:
            obsolete[k] = {
                "tasks": sorted({h["task"] for h in stale}),
                "current": chain["current"],
                "current_title": chain.get("current_title"),
            }
    return {
        "cited_total": len(cites),
        "resolved": resolved,
        "dangling_count": len(dangling),
        "dangling": dict(sorted(dangling.items())),
        "obsolete_cited_count": len(obsolete),
        "obsolete_cited": dict(sorted(obsolete.items())),
        "obsolete_mention_count": len(mention),
        "obsolete_mention": dict(sorted(mention.items())),
    }


# ---------------------------------------------------------------
# v3 主题域层：heuristic 分类索引（data/rfc_topic_index.json）
# ---------------------------------------------------------------

def _topic_index() -> dict:
    """惰性加载主题域索引（rfc_topic_index.json，build 脚本产物）。"""
    global _TOPIC
    if _TOPIC is None:
        try:
            from importlib import resources
            data = resources.files("sysweeper.data").joinpath(
                _TOPIC_FILE).read_text(encoding="utf-8")
            _TOPIC = json.loads(data)
        except Exception:
            _TOPIC = {}
    return _TOPIC


def topic_stats() -> dict:
    """主题域索引口径统计（忠于 data/rfc_topic_index.json）。"""
    ti = _topic_index()
    m = ti.get("_meta", {})
    issued = m.get("catalog_issued") or 0
    classified = m.get("classified") or 0
    return {
        "domain_count": m.get("domain_count"),
        "rule_count": m.get("rule_count"),
        "classified": classified,
        "unclassified": m.get("unclassified"),
        "coverage": (classified / issued) if issued else 0.0,
        "method": m.get("method"),
        "match_scope": m.get("match_scope"),
        "source": m.get("source"),
    }


def topics() -> List[dict]:
    """主题域速览：[{domain, label, count, rule_count}]，按成员数降序。"""
    ti = _topic_index()
    counts: Dict[str, int] = {}
    for v in ti.get("assignments", {}).values():
        for d in set(v.get("domains", [])):
            counts[d] = counts.get(d, 0) + 1
    out = []
    for d, info in ti.get("domains", {}).items():
        out.append({"domain": d, "label": info.get("label"),
                    "count": counts.get(d, 0),
                    "rule_count": len(info.get("rules", []))})
    out.sort(key=lambda x: (-x["count"], x["domain"]))
    return out


def topic_members(domain, limit: int = 50) -> List[dict]:
    """某主题域的 RFC 成员（按编号升序）。域名不存在时返回空列表。"""
    ti = _topic_index()
    d = (domain or "").strip().lower()
    if d not in ti.get("domains", {}):
        return []
    cat = _catalog()
    out = [cat[k] for k, v in ti["assignments"].items()
           if d in v.get("domains", []) and k in cat]
    out.sort(key=lambda e: e["n"])
    return out[:max(0, limit)]


def topic_of(num) -> dict:
    """单条 RFC 的主题域归属。

    返回 {n, classified, domains, rules}；未命中任何规则时
    domains/rules 为空列表、classified=False（如实反映，不臆造）。
    """
    ti = _topic_index()
    k = _key(num)
    v = ti.get("assignments", {}).get(k) if k else None
    n = int(k[3:]) if k else None
    if not v:
        return {"n": n, "classified": False, "domains": [], "rules": []}
    return {"n": n, "classified": True,
            "domains": list(v.get("domains", [])),
            "rules": list(v.get("rules", []))}


def summary() -> List[str]:
    """纯文本目录速览（适老化：一句话一行，屏幕阅读器可朗读）。"""
    size = catalog_size()
    cites = citing_tasks()
    rel = relations_stats()
    st = wg_stats()
    lines = [
        "RFC 标准目录：共收录 %d 条 RFC 索引记录（其中已发布 %d 条，"
        "编号保留未发布 %d 条）。" % (size["total"], size["issued"],
                                    size["not_issued"]),
        "目录来自 IETF 官方 RFC INDEX（rfc-editor.org），由本地脚本解析生成，"
        "本工具只读，不改动标准原文。",
        "本系统中已有 %d 个 RFC 被优化任务引用。" % len(cites),
        "关系索引：%d 条 RFC 标注了废止/更新关系（obsoletes %d、"
        "obsoleted-by %d、updates %d、updated-by %d），"
        "%d 条归属 STD/BCP/FYI 系列。" % (
            rel["coverage"]["obsoletes"] + rel["coverage"]["updates"],
            rel["coverage"]["obsoletes"], rel["coverage"]["obsoleted_by"],
            rel["coverage"]["updates"], rel["coverage"]["updated_by"],
            rel["coverage"]["also"]),
        "用 rfc show <编号> 查看单条详情，rfc search <关键词> 检索，"
        "rfc citing <编号> 看哪些任务引用了它；"
        "rfc relations <编号> 看废止链，rfc current <编号> 找现行版本，"
        "rfc series 浏览 STD/BCP/FYI 系列。",
        "主题域索引（heuristic，标题规则匹配）：%d 个域覆盖 %d 条已发布 RFC，"
        "用 rfc topics 浏览、rfc topic <域名> 看成员；"
        "rfc refs 做任务侧引用全量核验（悬空/过期引用）。" % (
            topic_stats()["domain_count"] or 0,
            topic_stats()["classified"]),
        "官方 WG/RG 索引（rfc-index.xml + datatracker 名录，第二索引源）："
        "%d 个工作组/研究组覆盖 %d 条已发布 RFC（WG %d、RG %d；"
        "IAB %d、独立投稿 %d、早期 Legacy %d 无 WG 归属，由 heuristic 层兜底）；"
        "用 rfc wgs 浏览、rfc wg <名> 看成员。两层模态一致率 %.1f%%。" % (
            st["wg_count"] or 0, st["wg_covered"],
            st["kind_counts"].get("wg", 0), st["kind_counts"].get("rg", 0),
            st["kind_counts"].get("iab", 0),
            st["kind_counts"].get("independent", 0),
            st["kind_counts"].get("legacy", 0),
            (st.get("reconciliation") or {}).get("modal_agreement_rate_fmt", 0.0)),
    ]
    return lines


# ---------------------------------------------------------------
# v4 官方 WG/RG 归属层：data/rfc_wg_index.json（第二索引源）
#   与 v3 heuristic 主题域层互补：WG 层给官方分组口径，
#   heuristic 层覆盖 IAB/独立投稿/早期 Legacy RFC。
# ---------------------------------------------------------------

def _wg_index() -> dict:
    """惰性加载官方 WG 索引（rfc_wg_index.json，build 脚本产物）。"""
    global _WG
    if _WG is None:
        try:
            from importlib import resources
            data = resources.files("sysweeper.data").joinpath(
                _WG_FILE).read_text(encoding="utf-8")
            _WG = json.loads(data)
        except Exception:
            _WG = {}
    return _WG


def wg_stats() -> dict:
    """WG 索引口径统计（忠于 data/rfc_wg_index.json）。"""
    wi = _wg_index()
    m = wi.get("_meta", {})
    rec = m.get("reconciliation") or {}
    rate = rec.get("modal_agreement_rate")
    return {
        "issued": m.get("issued_total"),
        "kind_counts": m.get("kind_counts") or {},
        "wg_covered": m.get("wg_covered"),
        "wg_coverage": m.get("wg_coverage"),
        "wg_count": m.get("wg_count"),
        "area_count": m.get("area_count"),
        "source": m.get("source"),
        "method": m.get("method"),
        "reconciliation": {
            "both_classified": rec.get("both_classified"),
            "modal_agreement": rec.get("modal_agreement"),
            "modal_agreement_rate": rate,
            "modal_agreement_rate_fmt": round((rate or 0) * 100, 1),
        },
    }


def wgs(limit: int = 20) -> dict:
    """官方 WG 速览：{areas:[...按RFC数降序], top_wgs:[...按RFC数降序]}。"""
    wi = _wg_index()
    areas = [{"area": a, "name": g.get("name"), "wg_count": g.get("wg_count"),
              "rfc_count": g.get("rfc_count")}
             for a, g in wi.get("areas", {}).items()]
    areas.sort(key=lambda x: (-(x["rfc_count"] or 0), x["area"]))
    top = [{"wg": w, "name": g.get("name"), "area": g.get("area"),
            "state": g.get("state"), "kind": g.get("kind"),
            "count": g.get("count")}
           for w, g in wi.get("groups", {}).items()]
    top.sort(key=lambda x: (-(x["count"] or 0), x["wg"]))
    return {"areas": areas, "top_wgs": top[:max(0, limit)]}


def wg_members(name, limit: int = 50) -> List[dict]:
    """某 WG/RG 或 area 的 RFC 成员（按编号升序）。area 名取 datatracker 代码。"""
    wi = _wg_index()
    cat = _catalog()
    q = (name or "").strip().lower()
    if not q:
        return []
    out = []
    if q in wi.get("groups", {}):
        for n in wi["groups"][q].get("rfcs", []):
            k = "rfc%05d" % n
            if k in cat:
                out.append(cat[k])
    elif q in wi.get("areas", {}):
        for n in wi["areas"][q].get("rfcs", []):
            k = "rfc%05d" % n
            if k in cat:
                out.append(cat[k])
    out.sort(key=lambda e: e["n"])
    return out[:max(0, limit)]


def wg_of(num) -> dict:
    """单条 RFC 的官方 WG 归属。

    返回 {n, kind, wg, wg_name, area, stream, draft}；非 WG/RG 归属时
    wg/wg_name/area 为 None，kind ∈ wg/rg/iab/independent/legacy（如实反映）。
    """
    wi = _wg_index()
    k = _key(num)
    v = wi.get("assignments", {}).get(k) if k else None
    n = int(k[3:]) if k else None
    if not v:
        return {"n": n, "kind": None, "wg": None, "wg_name": None,
                "area": None, "stream": None, "draft": None}
    wg = v.get("w")
    g = wi.get("groups", {}).get(wg, {}) if wg else {}
    return {"n": n, "kind": v.get("t"), "wg": wg, "wg_name": g.get("name"),
            "area": v.get("a"), "stream": v.get("s"), "draft": v.get("d")}
