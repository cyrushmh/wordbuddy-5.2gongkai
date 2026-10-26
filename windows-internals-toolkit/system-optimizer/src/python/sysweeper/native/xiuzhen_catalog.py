# -*- coding: utf-8 -*-
"""修真图谱（只读消费层）
================================
数据来源：data/xiuzhen_map.json —— 由 research/xiuzhen/build_xiuzhen_map.py
从 classics-harmony-app 的 ClassicsData.ts（12 部典籍 / 23 个道藏部类）、
research/harvest/analysis.json（14 篇语料的话题与典籍命中）与
research/suwen_81_index.json 三源可复现 join 生成，并接入 daoxue 整体指导 8 源
（因果记录·全息·感应）作为「整体指导层」（75 节点 / 77 边）。

纪律（与数据层一致）：
  - 节点/边一律带 source，无出处不建——本模块只读，绝不补造；
  - 引用某节点即引用「典籍 / 部类 / 主题 / 语料」的事实本身，
    无一来自网络的现场推断。

用法示例：
    from sysweeper.native import xiuzhen_catalog as xz
    xz.summary()               # 规模与层分布的纯文本速览
    xz.node_info("book:daodejing")
    xz.neighbors("book:daodejing")   # 邻节点 + 边（双向）
    xz.relation_text(edge)     # 一条边的中文关系句
    xz.search("黄庭")          # 按标题/标签检索
"""
import json
import re
from typing import Dict, List, Optional

_DATA_FILE = "xiuzhen_map.json"
_INDEX: Optional[dict] = None
_BY_ID: Optional[Dict[str, dict]] = None
_INCIDENT: Optional[Dict[str, List[dict]]] = None

# 关系类型的中文名（与 App 侧 XiuzhenMapLayout.ts 同口径）
EDGE_RELATIONS = {
    "belongs_to": "属于",
    "has_topic": "主题",
    "mentions": "旁引",
    "same_tradition": "同传统",
    "corpus_covered_by": "由语料覆盖",
    "intro_mentions": "简介提及",
    "is_instance_of": "归于",
    "anchors_in": "锚定于",
}

TYPE_NAMES = {
    "book": "典籍",
    "daozang_category": "道藏部类",
    "topic": "研修主题",
    "classic_mention": "旁参典籍",
    "article": "语料文章",
    "corpus": "语料集",
}


def _index() -> dict:
    """惰性加载图谱（避免 import 期解析大 JSON）。"""
    global _INDEX
    if _INDEX is None:
        try:
            from importlib import resources
            data = resources.files("sysweeper.data").joinpath(
                _DATA_FILE).read_text(encoding="utf-8")
            _INDEX = json.loads(data)
        except Exception:
            _INDEX = {"meta": {}, "layers": [], "nodes": [], "edges": []}
    return _INDEX


def _by_id() -> Dict[str, dict]:
    global _BY_ID
    if _BY_ID is None:
        _BY_ID = {n["id"]: n for n in _index().get("nodes", [])}
    return _BY_ID


def _incident() -> Dict[str, List[dict]]:
    """节点 → 关联边（含方向 dir 与对端 other），双向索引。"""
    global _INCIDENT
    if _INCIDENT is None:
        inc: Dict[str, List[dict]] = {n["id"]: [] for n in _index().get("nodes", [])}
        for e in _index().get("edges", []):
            if e["from"] in inc:
                inc[e["from"]].append({"edge": e, "dir": "out", "other": e["to"]})
            if e["to"] in inc and e["from"] != e["to"]:
                inc[e["to"]].append({"edge": e, "dir": "in", "other": e["from"]})
        _INCIDENT = inc
    return _INCIDENT


def _label(n: Optional[dict]) -> str:
    """节点显示名：label（App 同 synthesized）> title > name > file 去扩展名 > id。"""
    if not n:
        return "?"
    for key in ("label", "title", "name"):
        v = n.get(key)
        if v:
            return str(v)
    f = n.get("file")
    if f:
        return re.sub(r"\.md$", "", f)
    return n["id"]


def display_name(n: Optional[dict]) -> str:
    """节点显示名（公开版，CLI/GUI 用）。"""
    return _label(n)


# 同名精确命中时的优先级（book > daozang_category > corpus > topic > classic_mention > article）
_TYPE_PRIORITY = ["book", "daozang_category", "corpus", "topic", "classic_mention", "article"]


def _node_id_of(probe) -> Optional[str]:
    """归一化入口：精确 id > 标签/标题精确（同名按类型优先级）> id 后缀包含。

    查无返回 None（不臆造）。"""
    if probe is None:
        return None
    s = str(probe).strip()
    if not s:
        return None
    table = _by_id()
    if s in table:
        return s
    # 精确与前缀匹配合并候选：类型优先级 > 精确 > 显示名短（「道德经」应命中典籍而非旁参）
    cands: List[tuple] = []
    for nid, n in table.items():
        disp = _label(n)
        if n.get("title") == s or n.get("label") == s or n.get("name") == s:
            is_exact = 1
        elif disp.startswith(s):
            is_exact = 0
        else:
            continue
        ntype = n.get("type")
        pr = _TYPE_PRIORITY.index(ntype) if ntype in _TYPE_PRIORITY else len(_TYPE_PRIORITY)
        cands.append((pr, 1 - is_exact, len(disp), nid))
    if cands:
        cands.sort()
        return cands[0][3]
    low = s.lower()
    hits = [nid for nid in table if low in nid.lower()]
    if len(hits) >= 1:
        # 多命中时取最短 id（最接近前缀意图），仍属可解释选择
        return sorted(hits, key=len)[0]
    return None


def node_info(probe) -> Optional[dict]:
    """单节点元数据；查无返回 None。"""
    nid = _node_id_of(probe)
    if nid is None:
        return None
    return _by_id().get(nid)


def neighbors(probe) -> List[dict]:
    """某节点的全部关联边（双向，未截断）。"""
    nid = _node_id_of(probe)
    if nid is None:
        return []
    return list(_incident().get(nid, []))


def relation_text(ref: dict) -> str:
    """一条关联边的中文关系句（读屏/文本等价视图同口径）。"""
    edge = ref["edge"]
    table = _by_id()
    f = table.get(edge["from"])
    t = table.get(edge["to"])
    rel = EDGE_RELATIONS.get(edge["type"], edge["type"])
    base = "%s %s %s" % (_label(f), rel, _label(t))
    w = edge.get("weight", 1) or 1
    if w > 1 and edge["type"] in ("has_topic", "mentions"):
        return "%s（命中 %d 次）" % (base, w)
    if w > 1:
        return "%s（关联强度 %d）" % (base, w)
    return base


def layers() -> List[dict]:
    """层清单（含每层节点数）。"""
    counts: Dict[str, int] = {}
    for n in _index().get("nodes", []):
        counts[n.get("layer", "?")] = counts.get(n.get("layer", "?"), 0) + 1
    out = []
    for l in _index().get("layers", []):
        out.append({
            "id": l.get("id"),
            "name": l.get("name"),
            "desc": l.get("desc"),
            "count": counts.get(l.get("id"), 0),
        })
    return out


def by_layer(layer: str) -> List[dict]:
    return [n for n in _index().get("nodes", []) if n.get("layer") == layer]


def search(term: str, limit: int = 20) -> List[dict]:
    """按标题/标签/名称/id 检索（大小写不敏感；id 精确命中优先）。"""
    t = (term or "").strip().lower()
    if not t:
        return []
    table = _by_id()
    exact = table.get(t)
    if exact:
        return [exact]
    starts: List[dict] = []
    contains: List[dict] = []
    for n in table.values():
        title = _label(n).lower()
        nid = n["id"].lower()
        if title.startswith(t):
            starts.append(n)
        elif t in title or t in nid:
            contains.append(n)
    return (starts + contains)[:limit]


def summary() -> List[str]:
    """纯文本速览（一行一事实，读屏可朗读）。"""
    idx = _index()
    meta = idx.get("meta", {})
    nodes = idx.get("nodes", [])
    edges = idx.get("edges", [])
    lines: List[str] = []
    lines.append("==== 修真图谱（只读） ====")
    lines.append("规模：%d 节点 / %d 关系（构建于 %s）"
                 % (len(nodes), len(edges), meta.get("built_utc", "未知")))
    lines.append("纪律：%s" % meta.get("discipline", "节点/边一律带 source"))
    lines.append("")
    lines.append("分层：")
    for l in layers():
        lines.append("  %-12s %2d 个节点  %s" % (l["name"], l["count"], l["desc"] or ""))
    lines.append("")
    types: Dict[str, int] = {}
    for n in nodes:
        types[n.get("type", "?")] = types.get(n.get("type", "?"), 0) + 1
    lines.append("节点类型：" + " / ".join(
        "%s %d" % (TYPE_NAMES.get(k, k), v) for k, v in sorted(types.items())))
    etypes: Dict[str, int] = {}
    for e in edges:
        etypes[e["type"]] = etypes.get(e["type"], 0) + 1
    lines.append("关系类型：" + " / ".join(
        "%s %d" % (EDGE_RELATIONS.get(k, k), v) for k, v in sorted(etypes.items())))
    lines.append("")
    lines.append("子命令：list / search <词> / show <节点> / edges <节点> / layers")
    lines.append("示例：xiuzhen show book:daodejing；xiuzhen edges 道德经；xiuzhen search 黄庭")
    return lines


def map_data() -> dict:
    """完整图谱数据（GUI/测试用；调用方不得修改）。"""
    return _index()
