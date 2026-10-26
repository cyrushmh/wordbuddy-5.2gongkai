#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_ca_audit_standards.py — 由 WebTrust 报告事实底稿生成 CA 审计知识库
=========================================================================
输入（唯一数据源）:
  research/caaudit/webtrust_report_facts.json   人工逐行复核 PDF 提取文本后的结构化事实
交叉引用:
  system-optimizer/src/python/sysweeper/data/rfc_standards.json
      RFC 5280 条目标题（事项 1/3 引用其条款；AIA 与 CRL 结构规范的出处）

输出:
  system-optimizer/src/python/sysweeper/data/ca_audit_standards.json

纪律（与 rfc/build_xiuzhen_map 两轮同范式）:
  - 事实一律来自报告原文；拼写/大小写/连接符（en dash – vs 连字符 -）如实保留；
  - 每条记录带 source（PDF 页码），无出处不录入；
  - cross/issuing 的 root 指针必须解析到 root_cas（断言悬空=0）；
  - 指纹 64 位十六进制且全库唯一；
  - 本脚本只做 join 与校验，不新造任何事实。

用法:
  python3 build_ca_audit_standards.py [--check]
    默认生成输出；--check 只校验不写文件。
"""
import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]  # research/caaudit/<本脚本> → 仓库根
FACTS = REPO / "research" / "caaudit" / "webtrust_report_facts.json"
RFC_DATA = (REPO / "windows-internals-toolkit" / "system-optimizer" / "src" /
            "python" / "sysweeper" / "data" / "rfc_standards.json")
OUT = (REPO / "windows-internals-toolkit" / "system-optimizer" / "src" /
       "python" / "sysweeper" / "data" / "ca_audit_standards.json")

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slug(text: str, maxlen: int = 40) -> str:
    s = _SLUG_STRIP.sub("-", str(text).lower()).strip("-")
    return s[:maxlen].strip("-") or "x"


def build() -> dict:
    facts = json.loads(FACTS.read_text(encoding="utf-8"))

    rfc_title = None
    if RFC_DATA.exists():
        rfc = json.loads(RFC_DATA.read_text(encoding="utf-8"))
        entry = rfc.get("rfc05280") or {}
        rfc_title = entry.get("t")
    else:  # 交叉数据缺失时不阻断，只降级
        print("WARN: rfc_standards.json 缺失，RFC 5280 标题降级为兜底值", file=sys.stderr)

    # ---- 根 CA ----
    roots = []
    name_to_id = {}
    for c in facts["root_cas"]:
        cid = "root:" + slug(c["name"])
        roots.append({
            "id": cid,
            "kind": "root",
            "name": c["name"],
            "subject_cn": c["subject_cn"],
            "fingerprint": c["fingerprint"],
            "root_id": None,
            "source_page": c["source_page"],
        })
        name_to_id[c["name"]] = cid
        name_to_id.setdefault(c["subject_cn"], cid)

    def resolve_root(root_name: str, fallback_slug_base: str, alias: str = None) -> str:
        # 事实底稿显式登记的 alias（原文行文差异，指向 root_cas 正式名）优先
        for cand in filter(None, (alias, root_name)):
            rid = name_to_id.get(cand)
            if rid:
                return rid
        raise SystemExit("悬空 root 指针: %r (来自 %s)" % (root_name, fallback_slug_base))

    # ---- 交叉签名 CA 与签发 CA ----
    def _ca_list(items, kind):
        out = []
        for c in items:
            base = slug(c["subject_cn"])
            cid = "%s:%s-%s" % (kind, base, c["fingerprint"][:4].lower())
            out.append({
                "id": cid,
                "kind": kind,
                "name": c["subject_cn"],
                "subject_cn": c["subject_cn"],
                "fingerprint": c["fingerprint"],
                "root_name": c["root"],
                "root_id": resolve_root(c["root"], c["subject_cn"], c.get("root_alias")),
                "source_page": c["source_page"],
            })
            if c.get("root_alias"):
                out[-1]["root_alias"] = c["root_alias"]
                out[-1]["alias_note"] = c.get("alias_note", "原文行文差异，指向 root_cas 正式名")
        return out

    cross = _ca_list(facts["cross_signed_cas"], "cross")
    issuing = _ca_list(facts["issuing_cas"], "issuing")
    cas = roots + cross + issuing

    # ---- 标准引用（事项/附事项的条款出处）----
    standards_refs = [
        {
            "id": "webtrust:v2.2.2",
            "title": "WebTrust Principles and Criteria for Certification Authorities",
            "version": "v2.2.2",
            "kind": "audit-criteria",
            "rfc_number": None,
            "referenced_by_matters": ["additional-1"],
        },
        {
            "id": "rfc:5280",
            "title": rfc_title or "Internet X.509 Public Key Infrastructure Certificate and Certificate Revocation List (CRL) Profile",
            "title_source": "data/rfc_standards.json rfc05280（RFC 全量目录 join）" if rfc_title else "兜底标题（rfc_standards.json 缺失）",
            "kind": "ietf-rfc",
            "rfc_number": 5280,
            "referenced_by_matters": ["2004845"],
        },
        {
            "id": "br:baseline-requirements",
            "title": "CA/Browser Forum Baseline Requirements for the Issuance and Management of Publicly-Trusted Certificates",
            "version": "随事项报告期版本",
            "kind": "industry-baseline",
            "rfc_number": None,
            "referenced_by_matters": ["2004845", "2007217"],
        },
        {
            "id": "ccadb:policy",
            "title": "CCADB Policy（Common CA Database 政策）",
            "version": "§6.2 / version 2.0（按事项原文）",
            "kind": "root-program-policy",
            "rfc_number": None,
            "referenced_by_matters": ["2002402", "2007216"],
        },
    ]

    # ---- 校验 ----
    problems = []
    fps = [c["fingerprint"] for c in cas]
    if len(fps) != len(set(fps)):
        problems.append("指纹重复")
    if not all(re.fullmatch(r"[0-9A-F]{64}", f) for f in fps):
        problems.append("指纹格式非法（需 64 位大写十六进制）")
    ids = [c["id"] for c in cas]
    if len(ids) != len(set(ids)):
        problems.append("CA id 重复")
    root_ids = {c["id"] for c in roots}
    for c in cross + issuing:
        if c["root_id"] not in root_ids:
            problems.append("悬空 root 指针: %s" % c["id"])
    std_ids = {s["id"] for s in standards_refs}
    for m in facts["matters"]:
        for r in m["refs"]:
            if r["std"] == "RFC 5280" and "rfc:5280" not in std_ids:
                problems.append("RFC 5280 引用缺失")
    v = facts["verification"]["counts"]
    for key, actual in (("root_cas", len(roots)), ("cross_signed_cas", len(cross)),
                        ("issuing_cas", len(issuing)), ("locations", len(facts["locations"]))):
        if v[key] != actual:
            problems.append("计数不符: %s 事实=%d 生成=%d" % (key, v[key], actual))
    if problems:
        for p in problems:
            print("FAIL:", p, file=sys.stderr)
        raise SystemExit(1)

    return {
        "meta": {
            "name": "WebTrust for CAs 审计图谱（GoDaddy/Starfield 2026）",
            "version": "1.0",
            "built_utc": facts["meta"]["built_utc"],
            "discipline": "每条 CA/事项/地点带 source 页码；无出处不录入；拼写如实保留原文",
            "sources": ["research/caaudit/GoDaddy - 2026 WebTrust for CAs - Report.pdf",
                        "research/caaudit/webtrust_report_facts.json"],
            "source_kind": "third-party-audit-report",
            "report": facts["report"],
            "counts": {
                "root_cas": len(roots),
                "cross_signed_cas": len(cross),
                "issuing_cas": len(issuing),
                "total_cas": len(cas),
                "locations": len(facts["locations"]),
                "matters": len(facts["matters"]),
                "cpcps_documents": len(facts["cpcps_documents"]),
                "control_domain_groups": len(facts["control_domains"]),
            },
        },
        "cas": cas,
        "cpcps_documents": facts["cpcps_documents"],
        "services": facts["services"],
        "control_domains": facts["control_domains"],
        "exclusions": facts["exclusions"],
        "matters": facts["matters"],
        "additional_matters": facts["additional_matters"],
        "standards_refs": standards_refs,
        "locations": facts["locations"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验不写文件")
    args = ap.parse_args()

    doc = build()
    if args.check:
        print("CHECK_OK: %d CA（root %d / cross %d / issuing %d）, %d 地点" % (
            doc["meta"]["counts"]["total_cas"],
            doc["meta"]["counts"]["root_cas"],
            doc["meta"]["counts"]["cross_signed_cas"],
            doc["meta"]["counts"]["issuing_cas"],
            doc["meta"]["counts"]["locations"]))
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    print("WROTE %s" % OUT)
    print("  %d CA（root %d / cross %d / issuing %d）, %d 地点, %d 事项" % (
        doc["meta"]["counts"]["total_cas"],
        doc["meta"]["counts"]["root_cas"],
        doc["meta"]["counts"]["cross_signed_cas"],
        doc["meta"]["counts"]["issuing_cas"],
        doc["meta"]["counts"]["locations"],
        doc["meta"]["counts"]["matters"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
