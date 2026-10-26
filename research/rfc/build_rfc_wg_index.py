#!/usr/bin/env python3
"""RFC 主题域第二索引源：官方 WG/RG 归属（rfc-editor rfc-index.xml + IETF datatracker WG 名录）。

定位：**补充**而非替换本地启发式主题域索引（heuristic 层对 IAB/独立投稿/早期 Legacy
RFC 仍是唯一覆盖手段）。本脚本从官方 XML 提取每条 RFC 的 draft/area/stream 字段，
按 draft-ietf-{wg}-* / draft-irtf-{rg}-* 解析官方工作组归属，并与本地 heuristic
主题域索引做对账（一致率/分歧样例），产出 data/rfc_wg_index.json。

用法：
    python3 build_rfc_wg_index.py            # 构建
    python3 build_rfc_wg_index.py --check    # 重算并与磁盘对账（防篡改）
    python3 build_rfc_wg_index.py --report   # 打印分布与对账摘要
"""
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
XML_IN = Path(os.environ.get("RFC_INDEX_XML", HERE.parent / "rfc-index.xml"))
WG_LIST = Path(os.environ.get("RFC_WG_LIST", HERE.parent / "harvest" / "ietf_wg_list.json"))
_DEFAULT_DATA = (REPO / "windows-internals-toolkit/system-optimizer/"
                 "src/python/sysweeper/data")
TOPIC_INDEX = Path(os.environ.get("RFC_TOPIC_INDEX", _DEFAULT_DATA / "rfc_topic_index.json"))
OUT = Path(os.environ.get("RFC_WG_OUT", _DEFAULT_DATA / "rfc_wg_index.json"))

NS = "{https://www.rfc-editor.org/rfc-index}"
DRAFT_RGX = re.compile(r"^draft-(ietf|irtf)-([a-z0-9]+)")


def parse_entries(xml_path: Path):
    tree = ElementTree.parse(xml_path)
    root = tree.getroot()
    rows = []
    for e in root.findall(f"{NS}rfc-entry"):
        num_text = e.findtext(f"{NS}doc-id", "")
        if not num_text.startswith("RFC"):
            continue
        try:
            num = int(num_text[3:])
        except ValueError:
            continue
        rows.append({
            "num": num,
            "title": (e.findtext(f"{NS}title") or "").strip(),
            "draft": (e.findtext(f"{NS}draft") or "").strip(),
            "area": (e.findtext(f"{NS}area") or "").strip(),
            "stream": (e.findtext(f"{NS}stream") or "").strip(),
        })
    return rows


def load_reference(wg_list_path: Path):
    data = json.loads(wg_list_path.read_text(encoding="utf-8"))
    areas_by_id = {int(gid): a for gid, a in data["areas"].items()}
    area_names = {a["acronym"]: a.get("name", "") for a in areas_by_id.values()}
    wgs = {}
    for g in data["wgs"]:
        parent = (g.get("parent") or "").rstrip("/").rsplit("/", 1)[-1]
        state = (g.get("state") or "").rstrip("/").rsplit("/", 1)[-1]
        try:
            parent_area = areas_by_id.get(int(parent), {}).get("acronym", "")
        except ValueError:
            parent_area = ""
        wgs[g["acronym"]] = {
            "name": g.get("name") or "",
            "area": parent_area,
            "state": state,
        }
    return area_names, wgs


def classify(rows, area_names, wg_meta):
    """rows -> assignments / groups / area_agg / unclassified"""
    assignments = {}
    wg_rfcs = defaultdict(list)
    area_rfcs = defaultdict(set)
    for r in rows:
        draft, stream = r["draft"], r["stream"]
        org = wg = None
        kind = None
        if draft:
            m = DRAFT_RGX.match(draft)
            if m and m.group(1) == "ietf":
                org, wg, kind = "ietf", m.group(2), "wg"
            elif m and m.group(1) == "irtf":
                org, wg, kind = "irtf", m.group(2), "rg"
            elif draft.startswith("draft-iab-"):
                org, kind = "iab", "iab"
            else:
                org, kind = None, "independent"
        else:
            kind = "legacy"
        area = r["area"]
        if not area and wg and wg in wg_meta:
            area = wg_meta[wg]["area"]
        rec = {"s": stream, "d": draft or None}
        if wg:
            rec["w"] = wg
            wg_rfcs[wg].append(r["num"])
        if org:
            rec["o"] = org
        if area:
            rec["a"] = area
            area_rfcs[area].add(r["num"])
        rec["t"] = kind
        assignments[f"rfc{r['num']:05d}"] = rec
    groups = {}
    wg_kind = {}
    for key, rec in assignments.items():
        if rec.get("w"):
            wg_kind.setdefault(rec["w"], "wg" if rec.get("o") == "ietf" else "rg")
    for wg, nums in wg_rfcs.items():
        meta = wg_meta.get(wg, {})
        groups[wg] = {
            "name": meta.get("name", ""),
            "area": meta.get("area", ""),
            "state": meta.get("state", ""),
            "kind": wg_kind.get(wg, "wg"),
            "count": len(nums),
            "rfcs": sorted(nums),
        }
    area_agg = {
        a: {"name": area_names.get(a, ""),
            "wg_count": sum(1 for g in groups.values() if g["area"] == a),
            "rfc_count": len(nums), "rfcs": sorted(nums)}
        for a, nums in sorted(area_rfcs.items(), key=lambda kv: -len(kv[1]))
    }
    return assignments, groups, area_agg


def reconcile(assignments, topic_index_path: Path):
    """与本地 heuristic 主题域对账：以每个 WG 的众数 heuristic 域为基准算一致率。"""
    if not topic_index_path.exists():
        return None
    topics = json.loads(topic_index_path.read_text(encoding="utf-8"))
    topic_domains = {k: v.get("domains", []) for k, v in topics["assignments"].items()}
    wg_modal = {}
    wg_domain_count = defaultdict(Counter)
    both = 0
    agree = 0
    disagreements = []
    for key, rec in assignments.items():
        wg = rec.get("w")
        if not wg:
            continue
        doms = topic_domains.get(key)
        if not doms:
            continue
        both += 1
        d0 = doms[0]
        wg_domain_count[wg][d0] += 1
        modal = wg_domain_count[wg].most_common(1)[0][0]
        # 先累积再判一致（流式众数近似：用累计众数）
        if d0 == modal:
            agree += 1
        else:
            disagreements.append({"rfc": key, "wg": wg, "topic": doms})
    wg_modal = {wg: c.most_common(1)[0][0] for wg, c in wg_domain_count.items()}
    # 用最终众数复算一致率（避免流式偏差）
    agree_final = 0
    for key, rec in assignments.items():
        wg = rec.get("w")
        if not wg or wg not in wg_modal:
            continue
        doms = topic_domains.get(key)
        if not doms:
            continue
        if doms[0] == wg_modal[wg]:
            agree_final += 1
    # WG 的 modal（含第二 domain）分布
    modal_dist = Counter(wg_modal.values())
    return {
        "both_classified": both,
        "modal_agreement": agree_final,
        "modal_agreement_rate": round(agree_final / both, 4) if both else None,
        "wg_modal_domain_dist": dict(modal_dist.most_common()),
        "disagreement_samples": sorted(disagreements, key=lambda d: d["rfc"])[:20],
    }


def build():
    rows = parse_entries(XML_IN)
    area_names, wg_meta = load_reference(WG_LIST)
    assignments, groups, area_agg = classify(rows, area_names, wg_meta)
    kinds = Counter(r["t"] for r in assignments.values())
    issued = len(assignments)
    wg_covered = sum(1 for r in assignments.values() if r.get("w") or r["t"] == "rg")
    doc = {
        "_meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "rfc-editor rfc-index.xml (official) + IETF datatracker WG/area registry (labels)",
            "method": "official WG/RG from draft name; heuristic topic index remains fallback layer",
            "issued_total": issued,
            "kind_counts": dict(kinds),
            "wg_covered": wg_covered,
            "wg_coverage": round(wg_covered / issued, 4) if issued else None,
            "wg_count": len(groups),
            "area_count": len(area_agg),
        },
        "areas": area_agg,
        "groups": {wg: g for wg, g in sorted(groups.items(), key=lambda kv: -kv[1]["count"])},
        "assignments": assignments,
    }
    rec = reconcile(assignments, TOPIC_INDEX)
    if rec:
        doc["_meta"]["reconciliation"] = rec
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[+] wrote {OUT} ({OUT.stat().st_size} bytes)")
    print(f"    issued={issued} kinds={dict(kinds)} wgs={len(groups)} areas={len(area_agg)}")
    if rec:
        print(f"    reconcile: both={rec['both_classified']} agree={rec['modal_agreement']} "
              f"rate={rec['modal_agreement_rate']}")
    return doc


def check():
    disk = json.loads(OUT.read_text(encoding="utf-8"))
    rows = parse_entries(XML_IN)
    area_names, wg_meta = load_reference(WG_LIST)
    assignments, groups, area_agg = classify(rows, area_names, wg_meta)
    errs = []
    if disk.get("assignments") != assignments:
        diff = [k for k in set(disk.get("assignments", {})) ^ set(assignments)]
        for k in list(diff)[:5]:
            errs.append(f"assignments key mismatch: {k}")
        for k in set(disk.get("assignments", {})) & set(assignments):
            if disk["assignments"][k] != assignments[k]:
                errs.append(f"assignment value mismatch: {k}: disk={disk['assignments'][k]} recompute={assignments[k]}")
                break
    if set(disk.get("groups", {})) != set(groups):
        errs.append("group set mismatch")
    if set(disk.get("areas", {})) != set(area_agg):
        errs.append("area set mismatch")
    m = disk.get("_meta", {})
    if m.get("issued_total") != len(assignments):
        errs.append(f"issued_total mismatch: disk={m.get('issued_total')} recompute={len(assignments)}")
    if errs:
        for e in errs:
            print(f"[FAIL] {e}")
        sys.exit(1)
    print(f"[OK] WG index consistent with source (issued={len(assignments)}, wgs={len(groups)})")


def report():
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    m = doc["_meta"]
    print(f"issued={m['issued_total']} kinds={m['kind_counts']} wgs={m['wg_count']} areas={m['area_count']}")
    print("top areas:")
    for a, g in list(doc["areas"].items())[:12]:
        print(f"  {a:<10} {g['name'][:40]:<40} wgs={g['wg_count']:<4} rfcs={g['rfc_count']}")
    print("top WGs:")
    for wg, g in list(doc["groups"].items())[:15]:
        print(f"  {wg:<14} {g['name'][:44]:<44} area={g['area']:<5} {g['count']}  ({g['state']})")
    rec = m.get("reconciliation")
    if rec:
        print(f"reconcile: both={rec['both_classified']} agree={rec['modal_agreement']} rate={rec['modal_agreement_rate']}")
        print("wg modal domain dist:", rec["wg_modal_domain_dist"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    if args.check:
        check()
    elif args.report:
        report()
    else:
        build()
