#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_classics_data.py — 道藏原文 → 四端典籍数据构建器
========================================================

数据源（本项目已核验的抓取通道）：
  https://m.daorenjia.com/api/neirongapi.php?id={id}
    - 649  《道德真经》（道藏无注本，分章同《河上公章句》，底本《正统道藏》洞神部本文类）
    - 992  《太上黄庭内景玉经》（晋·魏华存，底本《正统道藏》洞玄部本文类，36 章）
    - 993  《太上黄庭外景玉经》（不著撰人，成书于晋，底本《正统道藏》洞玄部本文类，上/中/下三部）
    - 997  《黄庭内外玉景经解》（宋·蒋慎修注，残卷，底本《正统道藏》洞玄部玉诀类）

产出（单一数据源 → 四端契约）：
  1. classics-linux/data/*.txt          C CLI 运行时数据（install-data 通配复制，自动入 deb/arch 包）
  2. classics-rs/data/*.txt             Rust include_str! 编译期数据
  3. canonical.json                     规范化中间产物（复跑/审计用）
  4. out_arkts.ts.txt                   HarmonyOS ArkTS ClassicsData.ts 插入片段
  5. out_swift.swift.txt                iOS/macOS + Swift-Linux ClassicsData.swift 插入片段

编码安全约定（承 classics.c/lib.rs 哲学）：一律以严格 UTF-8 落盘，不引入 BOM。
"""
import json
import html
import re
import sys
from pathlib import Path

SRC = Path(__file__).parent
REPO = SRC.parents[2]                      # windows-internals-toolkit/
DATA_DIR = REPO / "classics-linux" / "data"
RS_DATA_DIR = REPO / "classics-rs" / "data"

# ---------------------------------------------------------------- 基础清洗

def clean_text(s: str) -> str:
    """去 HTML 标签 / 实体 / 内部换行，保留底本全角标点原貌。"""
    s = re.sub(r"<sup>.*?</sup>", "", s, flags=re.S)   # 参校脚注标记，不入正文
    s = html.unescape(s)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("\r", "").replace("\n", "")
    s = re.sub(r"[ \t]+", "", s)
    return s.strip()


def strip_table(s: str) -> tuple:
    """提取卷首校勘表（来源说明）与正文。"""
    m = re.search(r"<table.*?</table>", s, flags=re.S)
    if not m:
        return "", s
    return clean_text(m.group(0)), s[m.end():]


def paragraphs(body: str) -> list:
    """提取 <p> 段（保留 <strong> 以便识别章题）。"""
    return re.findall(r"<p>(.*?)</p>", body, flags=re.S)


# ---------------------------------------------------------------- 各经解析

def parse_chaptered(src: dict):
    """992 内景（<strong>章题）/ 649 道德真经（裸 <p> 章题）：章题段 + 经文段结构。"""
    _, body = strip_table(src["content"])
    chapters, volumes = [], []
    cur = None
    for p in paragraphs(body):
        t = clean_text(p)
        if not t:
            continue
        if re.match(r"^.+章第[一二三四五六七八九十百零]+$", t):
            cur = {"label": t, "original": ""}
            chapters.append(cur)
        elif re.search(r"卷[上下]$", t) and len(t) <= 8:      # 「道德真经卷上」等
            volumes.append(t)
            cur = None
        elif cur is not None:
            cur["original"] += t
    return chapters, volumes


def parse_waijing(src: dict):
    """993 外景：上/中/下三部，每部一大段七言歌诀；底本含重复部题、&nbsp; 分页残留与参校记。"""
    _, body = strip_table(src["content"])
    chapters, notes = [], []
    cur_label, cur_text = None, ""
    for p in paragraphs(body):
        t = clean_text(p)
        if not t:
            continue
        if re.match(r"^\d+[.、]", t):                      # 参校记（如「1.向：疑当作何」）
            notes.append(t)
            continue
        m = re.match(r"^太上黄庭外景玉经([上中下])$", t)
        if m:
            if cur_label and cur_text:
                chapters.append({"label": cur_label, "original": cur_text})
            cur_label, cur_text = t, ""
            continue
        if cur_label is not None:
            cur_text += t
    if cur_label and cur_text:
        chapters.append({"label": cur_label, "original": cur_text})
    return chapters, notes


def parse_jiejie(src: dict):
    """997 蒋慎修《黄庭内外玉景经解》：章题 + （经文 , 注文）对偶。"""
    _, body = strip_table(src["content"])
    items = paragraphs(body)
    chapters, cur_zhang, cur_no = [], None, 0
    i = 0
    while i < len(items):
        p = items[i]
        m = re.match(r"^<strong>(.*?)</strong>$", p.strip())
        if m:                                   # 章题，如「仙人章」
            cur_zhang = clean_text(m.group(1))
            cur_no = 0
            i += 1
            continue
        text = clean_text(p)
        if not text or text == src["title"]:    # 空段 / 站点页脚书名残留
            i += 1
            continue
        # 经文（非括号开头）→ 下一段若为（…）即蒋慎修注
        if not text.startswith("（"):
            note = ""
            if i + 1 < len(items):
                nxt = clean_text(items[i + 1])
                if nxt.startswith("（"):
                    note = nxt
                    i += 1
            cur_no += 1
            label = f"{cur_zhang or '经解'}·第{cur_no}则"
            ch = {"label": label, "original": text}
            if note:
                ch["commentary"] = note
            chapters.append(ch)
        i += 1
    return chapters


# ---------------------------------------------------------------- 元数据（四端共用）

BOOKS_META = [
    {
        "id": "daodejing-daozang",
        "file": "daodejing-daozang.txt",
        "title": "道德经（道藏无注本）",
        "short_title": "道德经·道藏本",
        "author": "春秋·老子（李耳）",
        "swift_author": "老子（李耳）",
        "dynasty": "春秋",
        "category": "道藏",
        "volumes": 2,
        "commentator": "无注（分章题名同《老子河上公章句》）",
        "daozang": {"nid": 15, "id": 649},
        "online_url": "https://a.daorenjia.com/daozang15-649",
        "ark_author": "春秋·老子（李耳）",
        "has_translation": False,
        "intro": (
            "又称《道德真经》。此本经文及分章与《河上公章句》本相同，约出于宋代，"
            "底本为《正统道藏》洞神部本文类，参校《老子道德经河上公章句》。"
            "全书八十一章，卷上《道经》三十七章、卷下《德经》四十四章，章题自「体道章」至「显质章」，"
            "为传世注疏（河上公、唐玄宗御注、宋徽宗御解等经世解读）所共用的分章系统。"
            "本应用原文取自道藏在线阅读站（a.daorenjia.com）对应条目；"
            "中国哲学书电子化计划（ctext.org）所收《道德经》注本可作为异文参校。"
        ),
        "note": "河上公章句系底本，81 章带章题；与应用内帛书本（daodejing.org）对读，可互校异文。",
        "swift_summary": "道藏无注本，八十一章，河上公分章带章题；经世注疏共用的分章系统。",
        "swift_category": "子部·道家",
    },
    {
        "id": "huangting-neijing",
        "file": "huangting-neijing.txt",
        "title": "黄庭内景经（太上黄庭内景玉经）",
        "short_title": "黄庭内景经",
        "author": "晋·魏华存",
        "swift_author": "魏华存",
        "dynasty": "东晋",
        "category": "道藏",
        "volumes": 1,
        "commentator": "无注（参校：道藏辑要本、清·董德宁《太上一黄庭经发微》本）",
        "daozang": {"nid": 20, "id": 992},
        "online_url": "https://a.daorenjia.com/daozang20-992",
        "ark_author": "晋·魏华存",
        "has_translation": False,
        "intro": (
            "道教上清派核心经典，全称《太上黄庭内景玉经》，传为晋代女仙魏华存所传。"
            "七言韵文，凡三十六章，自「上清章第一」至「沐浴章第三十六」，"
            "以存思内视、漱咽咽液为要，令身神安宁而百病不侵。"
            "底本《正统道藏》洞玄部本文类，参校《道藏辑要》本与清·董德宁《太上一黄庭经发微》本。"
        ),
        "note": "36 章七言韵文；与《外景经》互为内外篇，可对照《黄庭内外玉景经解》合参。",
        "swift_summary": "上清派存思经典，三十六章七言韵文，述身神居守与内视修炼。",
        "swift_category": "道藏",
    },
    {
        "id": "huangting-waijing",
        "file": "huangting-waijing.txt",
        "title": "黄庭外景经（太上黄庭外景玉经）",
        "short_title": "黄庭外景经",
        "author": "不著撰人",
        "swift_author": "不著撰人",
        "dynasty": "东晋",
        "category": "道藏",
        "volumes": 1,
        "commentator": "无注（参校：《云笈七签》务成子注本、道藏辑要蒋国祚本）",
        "daozang": {"nid": 20, "id": 993},
        "online_url": "https://a.daorenjia.com/daozang20-993",
        "ark_author": "不著撰人",
        "has_translation": False,
        "intro": (
            "道教上清派经典，全称《太上黄庭外景玉经》，成书于晋，不著撰人。"
            "七言歌诀，分上、中、下三部，内容与《内景经》相仿而文字更简，"
            "以存思身神、守固精气为核心，提三丹田之说，主「扶养性命守虚无，恬淡无为何思虑」。"
            "底本《正统道藏》洞玄部本文类，参校《云笈七签》所收务成子注本与《道藏辑要》蒋国祚注本。"
        ),
        "note": "上中下三部七言歌诀；与《内景经》合称《黄庭经》，为魏晋上清派双璧。",
        "swift_summary": "上清派经典，七言歌诀上中下三部，言存思身神、恬淡守无。",
        "swift_category": "道藏",
    },
    {
        "id": "huangting-shuangjing",
        "file": "huangting-shuangjing.txt",
        "title": "黄庭经（内外双景合参·蒋慎修经解）",
        "short_title": "黄庭内外玉景经解",
        "author": "宋·蒋慎修 注",
        "swift_author": "蒋慎修 注",
        "dynasty": "宋",
        "category": "道藏",
        "volumes": 1,
        "commentator": "蒋慎修",
        "daozang": {"nid": 20, "id": 997},
        "online_url": "https://a.daorenjia.com/daozang20-997",
        "ark_author": "宋·蒋慎修 注",
        "has_translation": False,
        "intro": (
            "全称《黄庭内外玉景经解》，宋·蒋慎修注，残卷。"
            "融汇《黄庭内景经》《黄庭外景经》经文逐句作解，是现存最早的「内外双景合参」注本。"
            "底本《正统道藏》洞玄部玉诀类。本应用按「经文 + 蒋慎修注」逐则呈现（commentary 字段）。"
        ),
        "note": "内外双景合参注本（残卷）；经文入 original，蒋慎修注入 commentary。",
        "swift_summary": "宋·蒋慎修注，内外双景合参残卷，逐句经文附注。",
        "swift_category": "道藏",
    },
]


def build_txt(meta: dict, chapters: list) -> str:
    """生成 C/Rust 端纯文本（与既有 daodejing.txt 版式一致：书名行 + 章题行 + 正文）。"""
    lines = [meta["title"], ""]
    for ch in chapters:
        lines.append(ch["label"])
        if ch.get("commentary"):
            lines.append(ch["original"])
            lines.append(ch["commentary"])
        else:
            lines.append(ch["original"])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def esc_ts(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def esc_swift(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def emit_arkts(meta: dict, chapters: list) -> str:
    out = []
    out.append("  {")
    out.append(f'    id: "{meta["id"]}",')
    out.append(f'    title: "{esc_ts(meta["title"])}",')
    out.append(f'    author: "{esc_ts(meta["ark_author"])}",')
    out.append(f'    intro: "{esc_ts(meta["intro"])}",')
    out.append(f'    hasTranslation: {str(meta["has_translation"]).lower()},')
    nid, cid = meta["daozang"]["nid"], meta["daozang"]["id"]
    out.append(f"    daozang: {{ nid: {nid}, id: {cid} }},")
    out.append(f'    onlineUrl: "{meta["online_url"]}",')
    out.append(f'    note: "{esc_ts(meta["note"])}",')
    out.append(f'    dynasty: "{meta["dynasty"]}",')
    out.append(f'    category: "{meta["category"]}",')
    out.append(f'    volumes: {meta["volumes"]},')
    out.append(f'    commentator: "{esc_ts(meta["commentator"])}",')
    out.append("    chapters: [")
    for ch in chapters:
        out.append("      {")
        out.append(f'        label: "{esc_ts(ch["label"])}",')
        out.append(f'        original: "{esc_ts(ch["original"])}",')
        if ch.get("commentary"):
            out.append(f'        commentary: "{esc_ts(ch["commentary"])}",')
        out.append("      },")
    out.append("    ],")
    out.append("  },")
    return "\n".join(out)


def emit_swift(meta: dict, chapters: list) -> str:
    out = []
    out.append("        ClassicBook(")
    out.append(f'            id: "{meta["id"]}",')
    out.append(f'            title: "{esc_swift(meta["title"])}",')
    out.append(f'            author: "{esc_swift(meta["swift_author"])}",')
    out.append(f'            dynasty: "{meta["dynasty"]}",')
    out.append(f'            category: "{esc_swift(meta["swift_category"])}",')
    out.append(f'            summary: "{esc_swift(meta["swift_summary"])}",')
    out.append("            chapters: [")
    for idx, ch in enumerate(chapters):
        out.append("                ClassicChapter(")
        out.append(f'                    id: "{meta["id"]}-{idx + 1}",')
        out.append(f'                    title: "{esc_swift(ch["label"])}",')
        out.append(f'                    original: "{esc_swift(ch["original"])}",')
        out.append('                    translation: "",')
        if ch.get("commentary"):
            out.append(f'                    commentary: "{esc_swift(ch["commentary"])}"')
        out.append("                ),")
    out.append("            ],")
    out.append(f'            volumes: {meta["volumes"]},')
    out.append(f'            commentator: "{esc_swift(meta["commentator"])}",')
    out.append(f'            daozangNid: {meta["daozang"]["nid"]},')
    out.append(f'            daozangId: {meta["daozang"]["id"]},')
    out.append(f'            onlineUrl: "{meta["online_url"]}"')
    out.append("        ),")
    return "\n".join(out)


# ---------------------------------------------------------------- 主流程

def main():
    srcs = {i: json.load(open(SRC / f"daozang_{i}.json", encoding="utf-8")) for i in (649, 992, 993, 997)}
    ddj_ch, ddj_vol = parse_chaptered(srcs[649])
    wj_ch, wj_notes = parse_waijing(srcs[993])
    sj_ch = parse_jiejie(srcs[997])
    nj_ch, nj_vol = parse_chaptered(srcs[992])
    results = {
        "daodejing-daozang": (ddj_ch, ddj_vol),
        "huangting-waijing": (wj_ch, []),
        "huangting-shuangjing": (sj_ch, []),
        "huangting-neijing": (nj_ch, nj_vol),
    }

    # 质检：章数对账
    expect = {"daodejing-daozang": 81, "huangting-neijing": 36,
              "huangting-shuangjing": None, "huangting-waijing": 3}
    ark_snippets, swift_snippets = [], []
    canonical = {}
    ok = True
    for meta in BOOKS_META:
        chapters, volumes = results[meta["id"]]
        exp = expect.get(meta["id"])
        flag = "" if exp is None or len(chapters) == exp else "  <<< 章数异常!"
        if flag:
            ok = False
        empty = [i for i, c in enumerate(chapters) if len(c["original"]) < 4]
        if empty:
            flag += f"  <<< 空正文章: {empty[:5]}"
            ok = False
        print(f'{meta["id"]:22s} 章数={len(chapters):3d} 卷册标记={volumes}{flag}')

        # 1/2. txt（C CLI + Rust 编译期数据）
        txt = build_txt(meta, chapters)
        for d in (DATA_DIR, RS_DATA_DIR):
            (d / meta["file"]).write_text(txt, encoding="utf-8")

        # 3. canonical
        entry = {"meta": {k: v for k, v in meta.items() if k not in ("intro", "note", "swift_summary")},
                 "volumes": volumes, "chapters": chapters}
        if meta["id"] == "huangting-waijing" and wj_notes:
            entry["collation_notes"] = wj_notes
        canonical[meta["id"]] = entry

        # 4/5. 端侧片段
        ark_snippets.append(emit_arkts(meta, chapters))
        swift_snippets.append(emit_swift(meta, chapters))

    (SRC / "canonical.json").write_text(
        json.dumps(canonical, ensure_ascii=False, indent=1), encoding="utf-8")
    (SRC / "out_arkts.ts.txt").write_text("\n".join(ark_snippets) + "\n", encoding="utf-8")
    (SRC / "out_swift.swift.txt").write_text("\n".join(swift_snippets) + "\n", encoding="utf-8")

    if not ok:
        print("\n[FAIL] 章数对账未过，终止。", file=sys.stderr)
        return 1
    print("\n[OK] 四端数据已生成：classics-linux/data/*.txt, classics-rs/data/*.txt, "
          "canonical.json, out_arkts.ts.txt, out_swift.swift.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
