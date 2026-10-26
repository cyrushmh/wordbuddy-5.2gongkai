#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修真图谱构建器（可复现流水线）
================================
输入（全部为仓库内已收录的真实素材，绝不由本脚本臆造）：
  1. classics-harmony-app/entry/src/main/ets/model/ClassicsData.ts
     CLASSICS（12 部典籍元数据）/ DAOZANG_CATALOG（23 个道藏部类）/
     DAOZANG_KEY_TEXTS（重点经典→道藏编号映射）
  2. research/harvest/analysis.json
     道医课堂/道教医学两公众号语料的典籍命中与话题命中（14 篇）
  3. research/suwen_81_index.json
     《黄帝内经·素问》81 篇索引（79 篇已收录正文）

输出：
  research/xiuzhen/map_canonical.json   图谱规范源（nodes/edges/layers/meta）
  PKG/data/xiuzhen_map.json             包内副本（App/CLI 消费层用，同内容）
  classics-harmony-app/entry/src/main/ets/model/XiuzhenMap.generated.ts
                                            App 侧编译期内嵌数据（与 canonical 同源）
  research/xiuzhen/build_report.json     构建报告（节点/边计数 + 诚实标注）

节点一律带 source 字段（真实出处）；边只来自可复现的 join
（daozang.nid 关联 / 语料命中计数 / intro 关键词命中 / 篇名同一性映射）。

用法：
  python3 build_xiuzhen_map.py
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

BASE = "/workspace/windows-internals-toolkit"
APP_TS = os.path.join(BASE, "classics-harmony-app/entry/src/main/ets/model/ClassicsData.ts")
ANALYSIS = os.path.join(BASE, "research/harvest/analysis.json")
SUWEN_INDEX = os.path.join(BASE, "research/suwen_81_index.json")
OUT_CANONICAL = os.path.join(BASE, "research/xiuzhen/map_canonical.json")
OUT_REPORT = os.path.join(BASE, "research/xiuzhen/build_report.json")
PKG_DATA = os.path.join(BASE, "windows-internals-toolkit/system-optimizer/src/python/sysweeper/data")
APP_MODEL = os.path.join(BASE, "classics-harmony-app/entry/src/main/ets/model/XiuzhenMap.generated.ts")


def read_classics_ts():
    """从 ClassicsData.ts 提取 12 部典籍 + 23 个道藏部类 + 11 条重点映射。

    只提取显式元数据字段；章节正文不进入图谱（图谱要的是结构不是全文）。
    """
    text = open(APP_TS, encoding="utf-8").read()
    books_sec = text.split("export const CLASSICS: ClassicBook[] = [", 1)[1]
    books_sec = books_sec.split("export interface DaoZangCategory", 1)[0]

    books = []
    for block in books_sec.split("\n  {\n")[1:]:
        m = re.match(r'\s*id: "([^"]+)",\s*\n\s*title: "([^"]+)",\s*\n\s*author: "([^"]+)",',
                     block)
        if not m:
            continue
        bid, title, author = m.group(1), m.group(2), m.group(3)
        n_chapters = len(re.findall(r"\boriginal:", block))
        dz = re.search(r"daozang: \{ nid: (\d+), id: (\d+) \}", block)
        online = re.search(r'onlineUrl: "([^"]+)"', block)
        intro = re.search(r'intro: "((?:[^"\\]|\\.)*)"', block)
        books.append({
            "id": bid, "title": title, "author": author,
            "chapters": n_chapters,
            "daozang": ({"nid": int(dz.group(1)), "id": int(dz.group(2))} if dz else None),
            "onlineUrl": online.group(1) if online else None,
            "intro": intro.group(1) if intro else "",
            "source": "classics-harmony-app CLASSICS",
        })

    cat_sec = text.split("export const DAOZANG_CATALOG: DaoZangCategory[] = [", 1)[1]
    cat_sec = cat_sec.split("export interface DaoZangRef", 1)[0]
    cats = []
    for m in re.finditer(r'\{ nid: (\d+),\s*name: "([^"]+)",\s*tier: "([^"]+)",\s*desc: "([^"]+)" \}', cat_sec):
        cats.append({"nid": int(m.group(1)), "name": m.group(2),
                     "tier": m.group(3), "desc": m.group(4),
                     "source": "classics-harmony-app DAOZANG_CATALOG"})

    kt_sec = text.split("export const DAOZANG_KEY_TEXTS: DaoZangRef[] = [", 1)[1]
    kt_sec = kt_sec.split("\n];", 1)[0]
    keys = []
    for m in re.finditer(r'\{ bookId: "([^"]+)",\s*nid: (\d+),\s*id: (\d+),\s*title: "([^"]+)" \}', kt_sec):
        keys.append({"bookId": m.group(1), "nid": int(m.group(2)),
                     "id": int(m.group(3)), "title": m.group(4),
                     "source": "classics-harmony-app DAOZANG_KEY_TEXTS"})
    return books, cats, keys


def load_analysis():
    a = json.load(open(ANALYSIS, encoding="utf-8"))
    files, classic_hits, topic_hits = a["files"], a["classic_hits"], a["topic_hits"]
    articles = []
    for f in files:
        articles.append({
            "id": "art:" + f["file"][:36],
            "file": f["file"], "account": f["account"],
            "topics": [{"name": t[0], "hits": t[1]} for t in f["topics"]],
            "classics": f["classics"],
            "chars_total": f.get("chars_total"),
            "source": "research/harvest/analysis.json",
        })
    return articles, classic_hits, topic_hits


def load_suwen():
    try:
        d = json.load(open(SUWEN_INDEX, encoding="utf-8"))
    except Exception:
        return None
    chs = d.get("chapters") or []
    return {
        "id": "corpus:suwen",
        "type": "corpus",
        "layer": "corpus",
        "title": d.get("title", "黄帝内经·素问"),
        "chapters_total": len(chs),
        "chapters_ingested": sum(1 for c in chs if c.get("ingested")),
        "source": "research/suwen_81_index.json + research/suwen/",
    }


# 典籍名 -> 本图谱内 book 节点的同一性映射（篇名/通称 -> book id）
CLASSIC_TO_BOOK = {
    "道德经": "daodejing", "老子": "daodejing",
    "庄子": "nanhuajing", "周易": "cantongqi",
}


def build():
    books, cats, keytexts = read_classics_ts()
    articles, classic_hits, topic_hits = load_analysis()
    suwen = load_suwen()

    nodes, edges = [], []

    layers = [
        {"id": "daozang", "name": "道藏部类层", "desc": "三洞四辅十二类的部类归属（DAOZANG_CATALOG）"},
        {"id": "classics", "name": "典籍层", "desc": "已结构化收录的 12 部道家经典"},
        {"id": "topics", "name": "研修主题层", "desc": "语料话题聚合（穴位经络/脏腑辨证/方药食疗等）"},
        {"id": "external", "name": "旁参典籍层", "desc": "语料中命中、尚未全文结构化收录的经典"},
        {"id": "corpus", "name": "采集层", "desc": "已收录的语料文章（公众号 × 14 篇）与《素问》语料"},
    ]

    # ── 典籍层 ──
    for b in books:
        nodes.append({**b, "id": "book:" + b["id"], "type": "book", "layer": "classics"})
    # ── 道藏部类层 ──
    for c in cats:
        nodes.append({"id": "dzcat:%d" % c["nid"], "type": "daozang_category",
                      "layer": "daozang", **c})
    # ── 典籍 → 部类（daozang.nid join，最硬的边） ──
    for b in books:
        if b["daozang"]:
            edges.append({"from": "book:" + b["id"], "to": "dzcat:%d" % b["daozang"]["nid"],
                          "type": "belongs_to", "weight": 1,
                          "source": "CLASSICS.daozang.nid join DAOZANG_CATALOG"})
    # 重点经典→道藏编号重复条目已在典籍节点内，不另建节点

    # ── 主题层（聚合） ──
    for name, total in sorted(topic_hits.items(), key=lambda kv: -kv[1]):
        arts = [a for a in articles if any(t["name"] == name for t in a["topics"])]
        nodes.append({"id": "topic:" + name, "type": "topic", "layer": "topics",
                      "name": name, "total_hits": total, "articles": len(arts),
                      "source": "research/harvest/analysis.json topic_hits"})

    # ── 旁参典籍（语料命中但未全文收录） ──
    for name, hits in sorted(classic_hits.items(), key=lambda kv: -kv[1]):
        nodes.append({"id": "ext:" + name, "type": "classic_mention", "layer": "external",
                      "name": name, "hits": hits,
                      "source": "research/harvest/analysis.json classic_hits"})

    # ── 采集层 ──
    for a in articles:
        nodes.append({**a, "id": a["id"], "type": "article", "layer": "corpus"})
    if suwen:
        nodes.append(suwen)

    # ── 边：文章 → 主题 / 文章 → 旁参典籍 / 旁参 → 本图谱典籍（同一性） ──
    for a in articles:
        for t in a["topics"]:
            edges.append({"from": a["id"], "to": "topic:" + t["name"],
                          "type": "has_topic", "weight": t["hits"],
                          "source": "analysis.json per-file topics"})
        for cname, hits in a["classics"].items():
            edges.append({"from": a["id"], "to": "ext:" + cname,
                          "type": "mentions", "weight": hits,
                          "source": "analysis.json per-file classics"})
    for cname, bid in CLASSIC_TO_BOOK.items():
        if any(n["id"] == "ext:" + cname for n in nodes) and \
           any(n["id"] == "book:" + bid for n in nodes):
            edges.append({"from": "ext:" + cname, "to": "book:" + bid,
                          "type": "same_tradition", "weight": 1,
                          "source": "篇名同一性映射（道德经/老子→daodejing；庄子→南华真经；周易→参同契立论根基）"})
    # 素问语料 → 旁参（素问/黄帝内经命中指向已收录语料）
    if suwen:
        for cname in ("素问", "黄帝内经"):
            if any(n["id"] == "ext:" + cname for n in nodes):
                edges.append({"from": "ext:" + cname, "to": suwen["id"],
                              "type": "corpus_covered_by",
                              "weight": classic_hits.get(cname, 0) or 1,
                              "source": "research/suwen/ 79 篇正文收录"})
    # 典籍 intro 关键词 → 旁参（可复现：intro 文本命中）
    for b in books:
        intro = b.get("intro") or ""
        for cname in classic_hits:
            if cname in intro and any(n["id"] == "ext:" + cname for n in nodes):
                edges.append({"from": "book:" + b["id"], "to": "ext:" + cname,
                              "type": "intro_mentions", "weight": 1,
                              "source": "CLASSICS intro 关键词命中：%s" % cname})

    canonical = {
        "meta": {
            "name": "修真图谱",
            "version": "1.0",
            "built_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "discipline": "节点/边一律带 source；无出处不建节点、不连边（宁缺毋滥）",
            "sources": [
                "classics-harmony-app/entry/src/main/ets/model/ClassicsData.ts",
                "research/harvest/analysis.json",
                "research/suwen_81_index.json",
            ],
            "node_count": len(nodes),
            "edge_count": len(edges),
        },
        "layers": layers,
        "nodes": nodes,
        "edges": edges,
    }
    # 自检：任何边的端点必须存在于节点表（悬空边 = 图谱坏了一半）
    node_ids = {n["id"] for n in nodes}
    dangling = [e for e in edges if e["from"] not in node_ids or e["to"] not in node_ids]
    if dangling:
        sys.exit("悬空边 %d 条，图谱拒绝落盘：%s" %
                 (len(dangling), [(e["from"], e["to"]) for e in dangling[:5]]))
    return canonical


def ts_model(canonical):
    """生成 App 侧编译期内嵌数据（与 canonical 同源，结构扁平化便于 ArkTS 消费）。"""
    nodes = canonical["nodes"]
    edges = canonical["edges"]
    lines = []
    lines.append("// 本文件由 research/xiuzhen/build_xiuzhen_map.py 自动生成，请勿手改。")
    lines.append("// 与 research/xiuzhen/map_canonical.json 同源（%s）。" % canonical["meta"]["built_utc"])
    lines.append("")
    lines.append("export interface MapNode {")
    lines.append("  id: string;")
    lines.append("  type: string;")
    lines.append("  layer: string;")
    lines.append("  label: string;")
    lines.append("  detail: string;")
    lines.append("  source: string;")
    lines.append("  link?: string;")
    lines.append("}")
    lines.append("")
    lines.append("export interface MapEdge {")
    lines.append("  from: string;")
    lines.append("  to: string;")
    lines.append("  type: string;")
    lines.append("  weight: number;")
    lines.append("}")
    lines.append("")
    lines.append("export const MAP_NODES: MapNode[] = [")

    def esc(s):
        return (s or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")

    for n in nodes:
        ntype = n["type"]
        if ntype == "book":
            label = n["title"]
            dz = "道藏 nid=%d/id=%d；" % (n["daozang"]["nid"], n["daozang"]["id"]) if n.get("daozang") else ""
            detail = "%s%s；%d 篇；%s" % (dz, n["author"], n["chapters"], esc(n.get("intro", ""))[:80])
            link = n.get("onlineUrl") or ""
        elif ntype == "daozang_category":
            label = n["name"]
            detail = "%s：%s" % (n["tier"], esc(n["desc"]))
            link = ""
        elif ntype == "topic":
            label = n["name"]
            detail = "命中 %d 次 / %d 篇文章" % (n["total_hits"], n["articles"])
            link = ""
        elif ntype == "classic_mention":
            label = n["name"]
            detail = "语料命中 %d 次（旁参，未全文收录）" % n["hits"]
            link = ""
        elif ntype == "article":
            label = n["file"][:34]
            detail = "%s · %s" % (n["account"], "、".join(t["name"] for t in n["topics"]))
            link = ""
        elif ntype == "corpus":
            label = n["title"]
            detail = "%d/%d 篇已收录" % (n["chapters_ingested"], n["chapters_total"])
            link = ""
        else:
            label, detail, link = n.get("id", ""), "", ""
        lines.append('  { id: "%s", type: "%s", layer: "%s", label: "%s", detail: "%s", source: "%s"%s },'
                     % (esc(n["id"]), esc(ntype), esc(n.get("layer", "")), esc(label),
                        detail[:160], esc(n.get("source", "")),
                        (', link: "%s"' % esc(link)) if link else ""))
    lines.append("];")
    lines.append("")
    lines.append("export const MAP_EDGES: MapEdge[] = [")
    for e in edges:
        lines.append('  { from: "%s", to: "%s", type: "%s", weight: %d },'
                     % (esc(e["from"]), esc(e["to"]), esc(e["type"]), int(e.get("weight", 1))))
    lines.append("];")
    return "\n".join(lines) + "\n"


def main():
    canonical = build()
    os.makedirs(os.path.dirname(OUT_CANONICAL), exist_ok=True)
    with open(OUT_CANONICAL, "w", encoding="utf-8") as fh:
        json.dump(canonical, fh, ensure_ascii=False, indent=1)

    os.makedirs(PKG_DATA, exist_ok=True)
    with open(os.path.join(PKG_DATA, "xiuzhen_map.json"), "w", encoding="utf-8") as fh:
        json.dump(canonical, fh, ensure_ascii=False, separators=(",", ":"))

    with open(APP_MODEL, "w", encoding="utf-8") as fh:
        fh.write(ts_model(canonical))

    from collections import Counter
    type_dist = Counter(n["type"] for n in canonical["nodes"])
    edge_dist = Counter(e["type"] for e in canonical["edges"])
    books_no_dz = [n["id"] for n in canonical["nodes"]
                   if n["type"] == "book" and not n.get("daozang")]
    report = {
        "built_utc": canonical["meta"]["built_utc"],
        "node_count": len(canonical["nodes"]),
        "edge_count": len(canonical["edges"]),
        "node_type_distribution": dict(type_dist),
        "edge_type_distribution": dict(edge_dist),
        "books_without_daozang_ref": books_no_dz,
        "honesty": "全部节点/边带 source；无出处不建（详见 meta.discipline）",
        "outputs": [OUT_CANONICAL, os.path.join(PKG_DATA, "xiuzhen_map.json"), APP_MODEL],
    }
    with open(OUT_REPORT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in report.items() if k != "outputs"},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
