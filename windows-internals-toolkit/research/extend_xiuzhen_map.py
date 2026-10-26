#!/usr/bin/env python3
# 扩充修真图谱：接入 daoxue 整体指导 8 源（因果记录·全息·感应）
# 纪律：节点/边一律带 source；无出处不建；不引入悬空边。
import json, datetime, sys

P = "system-optimizer/src/python/sysweeper/data/xiuzhen_map.json"
d = json.load(open(P, encoding="utf-8"))

existing_ids = {n["id"] for n in d["nodes"]}

SRC = "daoxue_taxonomy.json/_meta/overall_guidance"  # 8 源注册处

# ---- 新增「整体指导层」 ----
new_layer = {
    "id": "guidance",
    "name": "整体指导层",
    "desc": "九概念系统共享的元指导：因果记录·全息·感应（阿卡西记录/宇宙全息论/三世石/望乡台/三世因果经/文昌帝君阴鸷文/黄帝阴符经/太上感应篇），由 daoxue 整体指导注册，作为修真图谱元根。",
}
if not any(l["id"] == "guidance" for l in d["layers"]):
    d["layers"].append(new_layer)

# ---- 根节点：整体指导框架 ----
root_node = {
    "id": "guidance:zhengti",
    "title": "整体指导·因果记录·全息·感应",
    "author": None,
    "chapters": None,
    "daozang": None,
    "onlineUrl": None,
    "intro": "九概念系统（comp/plang/netsys/quantum/apilab/baigong/datong/zhuangzi/daoxue）共享的元指导层，不归任一子系统私有。命题：宇宙是一本全量记录（阿卡西记录）、任一片都含全体（宇宙全息论）、种因得果如影随形（三世因果经/太上感应篇）。由 daoxue 整体指导注册，并作为修真图谱元根，向下锚定既有丹道典籍。",
    "source": SRC,
    "type": "topic",
    "layer": "guidance",
}

# ---- 7 个待补源节点（黄帝阴符经 book:yinfu 已存在，仅连边） ----
source_nodes = [
    {
        "id": "guidance:taishang-ganying-pian",
        "title": "太上感应篇",
        "author": "佚名（托太上老君）/ 道教善书",
        "chapters": None, "daozang": None, "onlineUrl": None,
        "intro": "道教重要善书，全称《太上感应篇》，以「祸福无门，惟人自召；善恶之报，如影随形」为总纲，列举善行恶行与因果报应。为整体指导「感应」维度的古典锚点之一。",
        "source": SRC + ".sources[taishang-ganying-pian]",
        "type": "book", "layer": "guidance",
    },
    {
        "id": "guidance:wenchang-yinzhi-wen",
        "title": "文昌帝君阴鸷文",
        "author": "托文昌帝君",
        "chapters": None, "daozang": None, "onlineUrl": None,
        "intro": "道教善书，文昌帝君垂训积阴德、立阴鸷之文，与《太上感应篇》同属劝善因果系列，是整体指导「因果记录」维度的古典表达。",
        "source": SRC + ".sources[wenchang-yinzhi-wen]",
        "type": "book", "layer": "guidance",
    },
    {
        "id": "guidance:three-life-karma-sutra",
        "title": "三世因果经",
        "author": "佚名（民间三教合流劝善文本）",
        "chapters": None, "daozang": None, "onlineUrl": None,
        "intro": "民间流传的三世因果经，以过去/现在/未来三世业报阐明因果相续，是整体指导「因果」维度的通俗表达。来源分级：民间口传/抄本，挂 needs_verify，不与官制典籍等价呈现。",
        "source": SRC + ".sources[three-life-karma-sutra]",
        "type": "book", "layer": "guidance",
    },
    {
        "id": "guidance:akashic-records",
        "title": "阿卡西记录（Akashic Records）",
        "author": "现代灵性/秘学概念",
        "chapters": None, "daozang": None, "onlineUrl": None,
        "intro": "现代秘学中的「宇宙全量记录」隐喻：一切事件、思想、因果皆被记录于一处可查的场。对应整体指导「记录」维度（needs_verify：现代诠释，非传统典籍）。",
        "source": SRC + ".sources[akashic-records]",
        "type": "classic_mention", "layer": "guidance",
    },
    {
        "id": "guidance:holographic-universe",
        "title": "宇宙全息论（Holographic Universe）",
        "author": "现代科学/哲学假说",
        "chapters": None, "daozang": None, "onlineUrl": None,
        "intro": "「任一部分都包含整体信息」的全息隐喻，与道家「其小无内、其大无垠」「一即一切」同构。对应整体指导「全息」维度（needs_verify：现代假说，非传统典籍）。",
        "source": SRC + ".sources[holographic-universe]",
        "type": "classic_mention", "layer": "guidance",
    },
    {
        "id": "guidance:three-life-stone",
        "title": "三世石",
        "author": "民间传说/志怪意象",
        "chapters": None, "daozang": None, "onlineUrl": None,
        "intro": "民间传说中照见前世今生的石（如「三生石」），是整体指导「三世/因果可记可照」维度的意象表达（needs_verify：传说意象，非典籍正文）。",
        "source": SRC + ".sources[three-life-stone]",
        "type": "classic_mention", "layer": "guidance",
    },
    {
        "id": "guidance:wangxiang-platform",
        "title": "望乡台",
        "author": "民间信仰/冥界意象",
        "chapters": None, "daozang": None, "onlineUrl": None,
        "intro": "民间冥界意象中亡者回望故乡之处，喻「记录与回向」之节点，与整体指导「记录/回向」维度相参（needs_verify：民间意象，非典籍正文）。",
        "source": SRC + ".sources[wangxiang-platform]",
        "type": "classic_mention", "layer": "guidance",
    },
]

# ---- 新增节点（去重） ----
added_nodes = 0
for n in [root_node] + source_nodes:
    if n["id"] not in existing_ids:
        d["nodes"].append(n)
        existing_ids.add(n["id"])
        added_nodes += 1

# ---- 新增边 ----
# 8 个源（含已存在的 book:yinfu）-> 根：is_instance_of
instance_sources = [
    "guidance:taishang-ganying-pian", "guidance:wenchang-yinzhi-wen",
    "guidance:three-life-karma-sutra", "guidance:akashic-records",
    "guidance:holographic-universe", "guidance:three-life-stone",
    "guidance:wangxiang-platform", "book:yinfu",
]
# 根 -> 既有丹道典籍：anchors_in
anchor_targets = ["book:daodejing", "book:qingjing", "book:cantongqi"]

new_edges = []
for s in instance_sources:
    new_edges.append({
        "from": s, "to": "guidance:zhengti", "type": "is_instance_of",
        "weight": 1, "source": SRC,
    })
for t in anchor_targets:
    new_edges.append({
        "from": "guidance:zhengti", "to": t, "type": "anchors_in",
        "weight": 1, "source": SRC + " + " + t,
    })

# 去重（避免重复边）
existing_edge_keys = {(e["from"], e["to"], e.get("type")) for e in d.get("edges", [])}
added_edges = 0
for e in new_edges:
    k = (e["from"], e["to"], e.get("type"))
    if k not in existing_edge_keys:
        d["edges"].append(e)
        existing_edge_keys.add(k)
        added_edges += 1

# ---- 校验：无悬空引用 ----
node_ids = {n["id"] for n in d["nodes"]}
dangling = [e for e in d["edges"] if e["from"] not in node_ids or e["to"] not in node_ids]
if dangling:
    print("ERROR: 悬空边:", dangling, file=sys.stderr)
    sys.exit(1)

# ---- 更新 meta ----
d["meta"]["version"] = "1.1"
d["meta"]["built_utc"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
d["meta"]["node_count"] = len(d["nodes"])
d["meta"]["edge_count"] = len(d["edges"])
if SRC.split("/")[0] not in d["meta"]["sources"]:
    d["meta"]["sources"].append(SRC.split("/")[0])
d["meta"]["discipline"] = "节点/边一律带 source；无出处不建节点、不连边（宁缺毋滥）；整体指导层源注册于 daoxue_taxonomy 整体指导"

json.dump(d, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"OK: +{added_nodes} nodes, +{added_edges} edges; total {len(d['nodes'])} nodes / {len(d['edges'])} edges; layers={[l['id'] for l in d['layers']]}")
