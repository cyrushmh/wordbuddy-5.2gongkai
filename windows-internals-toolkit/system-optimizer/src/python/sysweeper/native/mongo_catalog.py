# -*- coding: utf-8 -*-
"""MongoDB 权威指南（第2版）知识索引（只读消费层）
================================================
数据来源：data/mongo_docs.json —— 由 research/mongodb/build_mongo_docs.py
从 mongo_book_facts.json 可复现生成（6 部分 / 23 章 / 2 附录 / 43 概念 / 16 条系统调优）。

纪律（与 rfc_catalog / xiuzhen_catalog / ca_audit 三轮同口径）：
  - 只含结构性目录（取自 PDF 目录页，类同 RFC 目录）与自行概括的知识条目
    （读书笔记级通用技术知识），**不复制正文段落**；
  - 原书为商业出版物（图灵/O'Reilly 授权简体中文版），版权页明确「仅供个人
    使用，不得复制传播」——故 PDF 原件与提取全文均不入库，只留 SHA256 备核；
  - 每条概念/调优条目标注所属章节编号，可回书核对；
  - 系统调优条目（第 23 章）交叉引用 sysweeper 真实存在的任务 id 与子命令
    （构建期已 grep 断言，运行期可再核）。

用法示例：
    from sysweeper.native import mongo_catalog as mg
    mg.summary()                 # 书目 + 章节/概念统计 + 分类分布
    mg.chapter(5)                # 第 5 章的节清单
    mg.concepts("index")         # 某类概念
    mg.search("副本集")           # 按名称/描述检索
    mg.sysops()                  # 第 23 章系统调优条目（含 sysweeper 对账入口）
    mg.cross_ref()               # 只列出与 sysweeper 任务/子命令对得上的条目
"""
import json
from typing import Dict, List, Optional

_DATA_FILE = "mongo_docs.json"
_INDEX: Optional[dict] = None


def _index() -> dict:
    """惰性加载知识库（避免 import 期解析 JSON）。"""
    global _INDEX
    if _INDEX is None:
        try:
            from importlib import resources
            data = resources.files("sysweeper.data").joinpath(
                _DATA_FILE).read_text(encoding="utf-8")
            _INDEX = json.loads(data)
        except Exception:
            _INDEX = {"meta": {}, "parts": [], "chapters": [], "appendixes": [],
                      "concepts": [], "categories": {}, "sysops": []}
    return _INDEX


def book() -> dict:
    """书目元数据（含版权声明与不入库说明）。"""
    return _index().get("meta", {})


def chapters(part: str = "") -> List[dict]:
    """章节清单（可按 part 过滤，如 p3=复制）。"""
    out = _index().get("chapters", [])
    if part:
        out = [c for c in out if c.get("part") == part]
    return list(out)


def chapter(no) -> Optional[dict]:
    """按章号取章（1..23）；查无返回 None。"""
    try:
        n = int(no)
    except (TypeError, ValueError):
        return None
    for c in _index().get("chapters", []):
        if c.get("no") == n:
            return c
    return None


def parts() -> List[dict]:
    return list(_index().get("parts", []))


def concepts(category: str = "") -> List[dict]:
    """概念条目（可按类别过滤）。"""
    out = _index().get("concepts", [])
    if category:
        out = [c for c in out if c.get("category") == category]
    return list(out)


def categories() -> Dict[str, str]:
    return dict(_index().get("categories", {}))


def concept(cid: str) -> Optional[dict]:
    for c in _index().get("concepts", []):
        if c.get("id") == cid:
            return c
    return None


def sysops() -> List[dict]:
    """第 23 章「部署 MongoDB」的系统层调优条目。"""
    return list(_index().get("sysops", []))


def search(term: str, limit: int = 20) -> List[dict]:
    """按名称/描述/id 检索概念与调优条目（大小写不敏感）。"""
    t = (term or "").strip().lower()
    if not t:
        return []
    starts: List[dict] = []
    contains: List[dict] = []
    for c in _index().get("concepts", []):
        name = (c.get("name") or "").lower()
        desc = (c.get("desc") or "").lower()
        hit = c.get("id", "").lower()
        if name.startswith(t):
            starts.append({"kind": "concept", "item": c})
        elif t in name or t in desc or t in hit:
            contains.append({"kind": "concept", "item": c})
    for s in _index().get("sysops", []):
        name = (s.get("name") or "").lower()
        desc = (s.get("desc") or "").lower()
        if name.startswith(t):
            starts.append({"kind": "sysop", "item": s})
        elif t in name or t in desc:
            contains.append({"kind": "sysop", "item": s})
    return (starts + contains)[:limit]


def cross_ref() -> List[dict]:
    """与 sysweeper 任务/子命令对得上的调优条目（运行期二次核验存在性）。"""
    out = []
    for s in sysops():
        tid = s.get("sysweeper_task")
        cmd = s.get("sysweeper_cmd")
        if not (tid or cmd):
            continue
        rec = dict(s)
        rec["task_exists"] = _task_exists(tid) if tid else None
        rec["command_exists"] = _command_exists(cmd) if cmd else None
        out.append(rec)
    return out


def _task_exists(task_id: str) -> bool:
    """运行期核验：该任务 id 在 registry 中是否真实存在（不臆造引用）。"""
    try:
        from sysweeper import registry
        return registry.by_id(task_id) is not None
    except Exception:
        return False


def _command_exists(name: str) -> bool:
    try:
        from importlib import resources
        import re
        cli = resources.files("sysweeper").joinpath("cli.py").read_text(encoding="utf-8")
        return bool(re.search(r'sub\.add_parser\("%s"' % re.escape(name), cli))
    except Exception:
        return False


def summary() -> List[str]:
    """纯文本速览（一行一事实，读屏可朗读）。"""
    idx = _index()
    meta = idx.get("meta", {})
    bk = meta.get("book", {})
    counts = meta.get("counts", {})
    lines: List[str] = []
    lines.append("==== MongoDB 权威指南（第2版）知识索引（只读） ====")
    lines.append("书目：%s｜%s 著｜%s 译｜ISBN %s｜%d 页" % (
        bk.get("title", "?"), bk.get("author", "?"),
        "、".join(bk.get("translators") or []) or "?",
        bk.get("isbn", "?"), bk.get("pages", 0)))
    lines.append("规模：%d 部分 / %d 章 / %d 附录 / %d 概念 / %d 条系统调优" % (
        counts.get("parts", 0), counts.get("chapters", 0),
        counts.get("appendixes", 0), counts.get("concepts", 0),
        counts.get("sysops", 0)))
    lines.append("")
    lines.append("版权边界：%s" % meta.get("archiving_note", ""))
    lines.append("")
    lines.append("部分：")
    for p in idx.get("parts", []):
        lines.append("  %-22s 第 %s 章" % (p.get("name"), "、".join(str(n) for n in p.get("chapters", []))))
    lines.append("")
    lines.append("概念分类：" + " / ".join(
        "%s %d" % (name, len(concepts(cid)))
        for cid, name in sorted(idx.get("categories", {}).items())))
    lines.append("")
    lines.append("子命令：chapters / show <章号> / concepts / search <词> / deploy / cross / book")
    lines.append("示例：mongo show 23；mongo concepts --cat index；mongo deploy；mongo cross")
    return lines


def map_data() -> dict:
    """完整知识库数据（GUI/测试用；调用方不得修改）。"""
    return _index()
