#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_mongo_docs.py — 由 MongoDB 权威指南事实底稿生成知识库
==============================================================
输入（唯一数据源）:
  research/mongodb/mongo_book_facts.json   章节体系 + 知识条目 + 系统调优条目
  research/mongodb/manifest.json           书目元数据与版权边界

输出:
  system-optimizer/src/python/sysweeper/data/mongo_docs.json

纪律（与 rfc / xiuzhen / caaudit 三轮同范式）:
  - 章节体系取自 PDF 目录（结构性索引，类同 RFC 目录），逐条可回溯；
  - 知识条目为通用技术知识的自行概括（读书笔记级），不复制正文段落；
  - 构建期断言：章节号连续、概念与调优条目的 chapter 引用非悬空、
    sysweeper_task / sysweeper_cmd 指向项目内真实存在的任务 id 与子命令；
  - PDF 原件按版权声明「仅供个人使用，不得复制传播」不入库，仅留 SHA256 供核验。

用法:
  python3 build_mongo_docs.py [--check]
"""
import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]  # research/mongodb/<本脚本> → 仓库根
SO = REPO / "windows-internals-toolkit" / "system-optimizer"
PKG = SO / "src" / "python" / "sysweeper"
FACTS = REPO / "research" / "mongodb" / "mongo_book_facts.json"
MANIFEST = REPO / "research" / "mongodb" / "manifest.json"
OUT = PKG / "data" / "mongo_docs.json"
CLI = PKG / "cli.py"
TASKS_DIR = PKG / "tasks"

CATEGORY_NAMES = {
    "model": "数据模型",
    "crud": "增删改",
    "query": "查询",
    "index": "索引与特殊集合",
    "aggregate": "聚合",
    "design": "应用设计",
    "replica": "复制",
    "sharding": "分片",
    "admin": "管理与持久性",
}


def _sysweeper_targets():
    """从 cli.py 抓子命令名、从 tasks/ 抓任务 id —— 交叉引用必须真实存在。"""
    commands = set()
    if CLI.exists():
        commands = set(re.findall(r'sub\.add_parser\("([a-z_]+)"',
                                  CLI.read_text(encoding="utf-8")))
    task_ids = set()
    if TASKS_DIR.is_dir():
        for f in TASKS_DIR.glob("*.py"):
            task_ids.update(re.findall(r'id="([a-z0-9_]+)"', f.read_text(encoding="utf-8")))
    return commands, task_ids


def build() -> dict:
    facts = json.loads(FACTS.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    commands, task_ids = _sysweeper_targets()

    chapters = facts["chapters"]
    concepts = facts["concepts"]
    sysops = facts["sysops"]

    # ---- 校验 ----
    problems = []
    nos = [c["no"] for c in chapters]
    if nos != list(range(1, len(chapters) + 1)):
        problems.append("章节号不连续: %s" % nos)
    chapter_set = set(nos)
    for c in concepts:
        if c["chapter"] not in chapter_set:
            problems.append("概念 chapter 悬空: %s → %s" % (c["id"], c["chapter"]))
        if c["category"] not in CATEGORY_NAMES:
            problems.append("未登记的概念类别: %s（%s）" % (c["category"], c["id"]))
    for s in sysops:
        if s["chapter"] not in chapter_set:
            problems.append("调优条目 chapter 悬空: %s" % s["id"])
        # 23.4 网络配置在原书中是二级节（无 23.4.1），故二级/三级都接受
        if not re.match(r"^23(\.\d+)+$", s["section"] or ""):
            problems.append("调优条目 section 格式异常: %s" % s["id"])
        tid = s.get("sysweeper_task")
        if tid and tid not in task_ids:
            problems.append("sysweeper_task 不存在: %s" % tid)
        cmd = s.get("sysweeper_cmd")
        if cmd and cmd not in commands:
            problems.append("sysweeper_cmd 不存在: %s" % cmd)
    ids = [c["id"] for c in concepts] + [s["id"] for s in sysops]
    if len(ids) != len(set(ids)):
        problems.append("条目 id 重复")
    v = facts["verification"]["counts"]
    for key, actual in (("chapters", len(chapters)), ("concepts", len(concepts)),
                        ("sysops", len(sysops)), ("appendixes", len(facts["appendixes"])),
                        ("parts", len(facts["parts"]))):
        if v[key] != actual:
            problems.append("计数不符: %s 底稿=%s 实际=%s" % (key, v[key], actual))
    if problems:
        for p in problems:
            print("FAIL:", p, file=sys.stderr)
        raise SystemExit(1)

    by_cat = {}
    for c in concepts:
        by_cat.setdefault(c["category"], []).append(c)

    return {
        "meta": {
            "name": "MongoDB 权威指南（第2版）知识索引",
            "version": "1.0",
            "built_utc": facts["meta"]["built_utc"],
            "book": {
                "title": facts["book"]["title"],
                "author": facts["book"]["author"],
                "translators": facts["book"]["translators"],
                "isbn": facts["book"]["isbn"],
                "publisher": facts["book"]["publisher"],
                "pages": facts["book"]["pages"],
                "pdf_sha256": manifest.get("pdf_sha256"),
            },
            "copyright_note": manifest["copyright_note"],
            "archiving_note": "PDF 原件与提取全文按版权声明不入库；本库仅含结构性目录与自行概括的知识条目（读书笔记级），不复制正文段落。",
            "discipline": facts["meta"]["discipline"],
            "sources": ["research/mongodb/manifest.json",
                        "research/mongodb/mongo_book_facts.json"],
            "counts": {
                "parts": len(facts["parts"]),
                "chapters": len(chapters),
                "appendixes": len(facts["appendixes"]),
                "concepts": len(concepts),
                "sysops": len(sysops),
                "concept_categories": len(by_cat),
            },
        },
        "parts": facts["parts"],
        "chapters": chapters,
        "appendixes": facts["appendixes"],
        "concepts": concepts,
        "categories": {k: CATEGORY_NAMES[k] for k in sorted(by_cat)},
        "sysops": sysops,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验不写文件")
    args = ap.parse_args()

    doc = build()
    if args.check:
        c = doc["meta"]["counts"]
        print("CHECK_OK: %d 章 / %d 概念 / %d 系统调优条目（交叉引用均已核实存在）"
              % (c["chapters"], c["concepts"], c["sysops"]))
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    c = doc["meta"]["counts"]
    print("WROTE %s" % OUT)
    print("  %d 章 / %d 概念（%d 类）/ %d 系统调优条目"
          % (c["chapters"], c["concepts"], c["concept_categories"], c["sysops"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
