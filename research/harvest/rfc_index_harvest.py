#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RFC 全量索引采集器（可复现流水线）
====================================
输入：research/rfc/rfc-index.txt（rfc-editor.org 官方 RFC INDEX，见 manifest.json）
处理：解析 10,000+ 条 RFC 引用记录 → 结构化 JSON → 落盘到
      sysweeper 包数据层 data/rfc_standards.json（顶层 dict，key=rfcNNNN 五位零填充）
特性：
  - 忠实转录头段 `Key to citations` 定义的字段：number/title/authors/date/
    formats/obsoletes/obsoleted-by/updates/updated-by/also(STD|BCP|FYI)/status/DOI
  - "Not Issued." 条目如实保留（issued=false），绝不臆造元数据
  - 老 RFC（1969 年前后）少量条目 title 与作者粘连，按既定启发式切分并在
    报告中诚实计数，不手工篡改索引原文
  - 仅解析公开元数据（RFC 标题/状态/DOI），不复制 RFC 正文内容

用法：
  python3 rfc_index_harvest.py                 # 默认读 research/rfc/rfc-index.txt
  SRC=/path/rfc-index.txt python3 rfc_index_harvest.py
"""
import os, re, sys, json, hashlib

BASE = "/workspace/windows-internals-toolkit"
SRC = os.environ.get("SRC", os.path.join(BASE, "research/rfc/rfc-index.txt"))
REPORT = os.path.join(BASE, "research/rfc/rfc_index_harvest_report.json")
PKG_DATA = os.path.join(BASE, "windows-internals-toolkit/system-optimizer/src/python/sysweeper/data")

MONTHS = ("January February March April May June July August September "
          "October November December").split()
MONTH_YEAR_RE = re.compile(
    r"\b(" + "|".join(MONTHS) + r")\s+(\d{4})\.")
ENTRY_START_RE = re.compile(r"^(\d{1,5})\s+(.*)$")
PAREN_FIELD_RE = re.compile(r"\((Format|Obsoletes|Obsoleted by|Updates|Updated by|Also|Status|DOI)[^()]*\)")
RFC_LIST_RE = re.compile(r"RFC\s*(\d+)")


def collapse(s):
    return re.sub(r"\s+", " ", s).strip()


def parse_obsolete_nums(text):
    return [int(x) for x in RFC_LIST_RE.findall(text)]


def split_title_authors(head):
    """把 'Title. Authors.' 切成 (title, authors)。

    规则：'. '+大写字母 为候选句界；若点号前是单个大写字母（V./S.D. 类
    姓名首字母缩写），判为姓名内部缩写而非句界。老 RFC 里极个别条目
    粘连（如 RFC 16 无标题），按同一规则切分并在外层统计如实上报。
    """
    bounds = []
    for m in re.finditer(r"\.(?=\s+[A-Z])", head):
        end = m.start()
        before = head[:end]
        w = re.search(r"([A-Za-z.]+)$", before)
        tok = w.group(1) if w else ""
        letters = tok.rstrip(".")
        if len(letters) == 1 and tok.endswith(".") and "." not in tok[:-1]:
            continue  # 姓名首字母缩写：V. / S.
        if len(letters) == 1 and tok.count(".") <= 1:
            continue  # 单字母+点，仍判缩写
        bounds.append(m)
    if not bounds:
        return head, ""
    m = bounds[0]
    title = collapse(head[:m.start()])
    authors = collapse(head[m.start() + 1:])
    if title.endswith("."):
        title = title[:-1]
    return title, authors


def parse_entry(num, raw):
    """解析单条引用记录。raw 为已折叠空白的整条文本（不含编号前缀多余空白）。"""
    fields = {}
    rest = raw
    parens_removed = PAREN_FIELD_RE.sub(lambda m: " ", rest)
    for m in PAREN_FIELD_RE.finditer(rest):
        seg = m.group(0)[1:-1]
        if ":" in seg:
            k, v = seg.split(":", 1)
            fields[k.strip()] = collapse(v)
        else:
            # 无冒号的关系型字段：Obsoletes / Obsoleted by / Updates /
            # Updated by / Also。注意 "Obsoleted by"/"Updated by" 是双词
            # keywords，必须整词前缀匹配（"Updates" 与 "Updated by" 前缀
            # 不互撞：第 6 字符即分岔）。
            # 历史教训：早期版本把整段当键（fields["Obsoletes RFC8415"]），
            # 而取值用 fields["Obsoletes"] 永远落空——关系字段静默丢失，
            # v2 数据层 obs/oby/upd/udy 全空即此 bug 所致。
            for rk in ("Obsoletes", "Obsoleted by", "Updates", "Updated by", "Also"):
                if seg == rk or seg.startswith(rk + " "):
                    fields[rk] = collapse(seg[len(rk):])
                    break
            else:
                fields[seg.strip()] = True
    head = collapse(parens_removed)
    e = {"n": num, "i": True}

    my = None
    all_my = list(MONTH_YEAR_RE.finditer(head))
    if all_my:
        my = all_my[-1]
        e["d"] = "%s %s" % (my.group(1), my.group(2))
        head_pre = head[:my.start()]
    else:
        head_pre = head

    title, authors = split_title_authors(head_pre)
    e["t"] = title
    if authors:
        e["a"] = authors

    if "Format" in fields:
        e["f"] = [x.strip() for x in fields["Format"].split(",") if x.strip()]
    if "Status" in fields:
        e["s"] = fields["Status"]
    if "DOI" in fields:
        e["doi"] = fields["DOI"]
    for key, dest in (("Obsoletes", "obs"), ("Obsoleted by", "oby"),
                      ("Updates", "upd"), ("Updated by", "udy")):
        if key in fields:
            nums = parse_obsolete_nums(fields[key])
            if nums:
                e[dest] = nums
    if "Also" in fields:
        e["also"] = collapse(fields["Also"])
    return e


def main():
    if not os.path.isfile(SRC):
        sys.exit("缺少输入文件：%s（先抓取 rfc-index.txt，见 manifest.json）" % SRC)
    with open(SRC, "r", encoding="utf-8") as fh:
        text = fh.read()
    raw_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()

    entries = []
    cur_num, cur_lines = None, []
    joined_sticky = 0
    for line in text.splitlines():
        m = ENTRY_START_RE.match(line)
        if m and not line.startswith("     "):
            if cur_num is not None:
                entries.append((cur_num, " ".join(cur_lines)))
            cur_num = int(m.group(1))
            cur_lines = [m.group(2)]
        elif cur_num is not None and line.startswith("     "):
            cur_lines.append(line.strip())
        elif cur_num is not None and line.strip() == "":
            continue
        elif cur_num is not None:
            # 极少数续行不以 5 空格开头（防御性容错）
            cur_lines.append(line.strip())
            joined_sticky += 1
    if cur_num is not None:
        entries.append((cur_num, " ".join(cur_lines)))

    out = {}
    not_issued = []
    odd = []
    for num, raw in entries:
        body = collapse(raw)
        if body in ("Not Issued.", "Not Issued"):
            not_issued.append(num)
            out["rfc%05d" % num] = {"n": num, "i": False}
            continue
        try:
            e = parse_entry(num, body)
            out["rfc%05d" % num] = e
            if "t" not in e or not e.get("d") or not e.get("s"):
                odd.append(num)
        except Exception as exc:  # 防御：单条失败不毁整批
            odd.append(num)
            out["rfc%05d" % num] = {"n": num, "i": False,
                                    "parse_error": str(exc)[:120]}

    os.makedirs(PKG_DATA, exist_ok=True)
    outpath = os.path.join(PKG_DATA, "rfc_standards.json")
    with open(outpath, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    status_dist = {}
    for e in out.values():
        status_dist[e.get("s", "NOT_ISSUED")] = status_dist.get(e.get("s", "NOT_ISSUED"), 0) + 1
    series = {}
    for e in out.values():
        a = e.get("also")
        if a:
            series[a] = series.get(a, 0) + 1
    # 关系字段覆盖统计 + 悬空指针核验（指向编号必须在本索引内）
    rel_cov = {}
    for f in ("obs", "oby", "upd", "udy", "also"):
        rel_cov[f] = sum(1 for e in out.values() if e.get(f))
    dangling = []
    for k, e in out.items():
        for f in ("obs", "oby", "upd", "udy"):
            for num in (e.get(f) or []):
                if "rfc%05d" % num not in out:
                    dangling.append({"from": k, "field": f, "to": num})
    # 诚实标注：1969-1971 前后少量老条目标题与作者粘连（源头形态，未手工篡改）
    legacy_odd = sorted(k for k, e in out.items()
                        if e.get("i") and len(e.get("t", "")) < 8)
    report = {
        "source": SRC,
        "source_sha256": raw_sha,
        "entries_total": len(entries),
        "issued": len(out) - len(not_issued),
        "not_issued": len(not_issued),
        "not_issued_numbers_first20": not_issued[:20],
        "parse_odd": {"count": len(odd), "first20": odd[:20]},
        "legacy_title_concatenated": {"count": len(legacy_odd),
                                       "first20": legacy_odd[:20]},
        "joined_sticky_lines": joined_sticky,
        "status_distribution": dict(sorted(status_dist.items(), key=lambda kv: -kv[1])),
        "series_subseries_count": len(series),
        "relation_coverage": rel_cov,
        "relation_dangling": {"count": len(dangling), "first20": dangling[:20]},
        "output": outpath,
    }
    with open(REPORT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in report.items() if k != "status_distribution"},
                     ensure_ascii=False, indent=2))
    print("status_distribution:", json.dumps(report["status_distribution"], ensure_ascii=False))


if __name__ == "__main__":
    main()
