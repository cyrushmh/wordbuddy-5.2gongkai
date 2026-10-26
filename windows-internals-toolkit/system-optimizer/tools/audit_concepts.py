"""概念系统全量体检（只读审计，不改任何文件）。

四个层次逐一扫描九个概念系统，把「不一致」列成清单供人判断：
  1. 文件层 —— 数据层 / 只读层 / 构建层 三处命名是否与系统名一致；
  2. 字段层 —— 概念必备字段齐备度、字段命名是否统一；
  3. 命名层 —— schema 串、轴(domain)名、概念 id 风格、桥接 target kind；
  4. API 层 —— 九个只读层模块暴露的函数集是否同构。

用法：
    python3 tools/audit_concepts.py            # 打印体检报告
    python3 tools/audit_concepts.py --strict   # 存在不一致时退出码 1（供 CI）
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "python"
sys.path.insert(0, str(SRC))

from sysweeper import concepts as C  # noqa: E402

DATA_DIR = SRC / "sysweeper" / "data" / "concepts"
PKG_DIR = SRC / "sysweeper" / "concepts"
RESEARCH = ROOT / "research"
REQUIRED_FIELDS = ("gist", "detail", "engineering")


def audit_files() -> list[str]:
    """文件层：三处命名是否与系统名一致。"""
    issues = []
    for name in C.systems():
        if not (DATA_DIR / f"{name}_taxonomy.json").exists():
            issues.append(f"[文件] {name} 缺数据层 {name}_taxonomy.json")
        if not (PKG_DIR / f"{name}.py").exists():
            issues.append(f"[文件] {name} 缺只读层 {name}.py")
        rd = RESEARCH / name
        if not rd.is_dir():
            issues.append(f"[文件] {name} 缺构建层目录 research/{name}/")
            continue
        builds = sorted(rd.glob("build*.py"))
        expect = rd / f"build_{name}.py"
        if expect not in builds:
            got = "、".join(b.name for b in builds) or "无"
            issues.append(f"[文件] {name} 构建脚本命名不一致：应为 build_{name}.py，实为 {got}")
    return issues


def audit_fields() -> tuple[list[str], dict]:
    """字段层：必备字段齐备度（仅 concept 型系统）。"""
    issues, table = [], {}
    for name in C.systems():
        doc = C.load(name)
        cons = doc.get("concepts", [])
        if not cons:
            continue
        miss = {f: [c["id"] for c in cons if not c.get(f)] for f in REQUIRED_FIELDS}
        miss = {k: v for k, v in miss.items() if v}
        table[name] = (len(cons), miss)
        for f, ids in miss.items():
            issues.append(f"[字段] {name} 缺 {f}：{len(ids)} 条（如 {ids[:3]}）")
    return issues, table


def audit_naming() -> list[str]:
    """命名层：schema 串 / 轴名 / id 风格 / 桥接 kind。"""
    issues = []
    kinds = Counter()
    for name in C.systems():
        doc = C.load(name)
        schema = doc.get("_meta", {}).get("schema", "")
        if schema and not schema.startswith(f"{name}_taxonomy/"):
            issues.append(f"[命名] {name} schema 串与系统名不符：{schema}")
        # 概念 id 风格（推荐 kebab-case 小写）
        bad = [c["id"] for c in doc.get("concepts", [])
               if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", c["id"])]
        if bad:
            issues.append(f"[命名] {name} 概念 id 非 kebab-case：{bad[:5]}")
        # 轴名风格
        for d in doc.get("domains", []):
            dom = d.get("domain", "")
            if dom and not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", dom):
                issues.append(f"[命名] {name} 轴名风格异常：{dom}")
        for b in doc.get("bridges", []):
            kind = b.get("target", "").partition(":")[0]
            kinds[(b.get("system"), kind)] += 1
    # 同一目标系统的 kind：多池是合理的（如 plang 有语言/模型/架构/能力域四个池），
    # 真正的问题是「同一个池却用了两个 kind 名」——下列映射给出 kind → 应属的池，
    # 命中同一池却用了不同 kind 名的，才算不一致。
    POOL_OF_KIND = {
        ("plang", "lang"): "lang_index", ("plang", "concept"): "lang_index",
        ("plang", "model"): "execution_models", ("plang", "arch"): "target_archs",
        ("plang", "domain"): "domains", ("plang", "probe"): "probe_results",
        ("baigong", "concept"): "concepts", ("baigong", "principle"): "principles",
        ("zhuangzi", "concept"): "concepts", ("zhuangzi", "principle"): "principles",
        ("daoxue", "principle"): "principles", ("daoxue", "guidance"): "zhengti_zhida",
        ("netsys", "module"): "modules", ("netsys", "layer"): "layers",
        ("netsys", "nature"): "natures",
        ("llvm", "tool"): "tools", ("llvm", "target"): "targets",
    }
    per_pool: dict = {}
    for (sysname, kind), n in kinds.items():
        pool = POOL_OF_KIND.get((sysname, kind), f"?{kind}")
        per_pool.setdefault((sysname, pool), set()).add(kind)
    for (sysname, pool), ks in sorted(per_pool.items()):
        if len(ks) > 1:
            issues.append(
                f"[命名] {sysname} 的「{pool}」池被两种 kind 指向：{sorted(ks)}"
                f"（应统一为一种）")
    return issues


def audit_api() -> tuple[list[str], dict]:
    """API 层：只读层模块暴露的公共函数集是否同构。"""
    def public_fns(name: str) -> set:
        mod = C.module(name)
        return {n for n in dir(mod) if not n.startswith("_")
                and callable(getattr(mod, n))
                and getattr(getattr(mod, n), "__module__", "") == mod.__name__}

    sets = {n: public_fns(n) for n in C.systems()}
    # 按「是否带 principles 轴」分组比较——结构不同的系统不该互相要求同构
    group_a = [n for n in C.systems()                       # 轴型 + 带原则
               if "principle" in sets[n]]
    group_b = [n for n in C.systems()                       # 轴型 / 表型，无原则
               if n not in group_a]
    report, diffs = {}, {}
    for label, members in (("带原则/条目型", group_a), ("无原则型", group_b)):
        if len(members) < 2:
            continue
        common = set.intersection(*(sets[m] for m in members))
        report[label] = (members, sorted(common))
        for m in members:
            missing = sorted(common - sets[m])
            extra = sorted(sets[m] - common)
            if missing:
                diffs[m] = (label, missing)
    issues = [f"[API] {m}（{lb}组）缺公共函数：{ms}" for m, (lb, ms) in diffs.items()]
    return issues, {"groups": {k: (v[0], v[1]) for k, v in report.items()},
                    "diff": diffs}


def main(argv: list[str]) -> int:
    print("=" * 68)
    print("概念系统全量体检（只读审计）")
    print("=" * 68)

    f_issues = audit_files()
    fi_issues, table = audit_fields()
    n_issues = audit_naming()
    a_issues, api = audit_api()

    print(f"\n系统数：{len(C.systems())}（{'、'.join(C.systems())}）")

    print("\n--- 1. 文件层命名 ---")
    print("  " + ("全部一致" if not f_issues else "\n  ".join(f_issues)))

    print("\n--- 2. 字段齐备度（concept 型系统）---")
    if table:
        print(f"  {'系统':<10}{'概念':>6}   缺字段")
        for name, (n, miss) in sorted(table.items()):
            flag = "齐备" if not miss else "、".join(f"{k}×{len(v)}" for k, v in miss.items())
            print(f"  {name:<10}{n:>6}   {flag}")
    print("  " + ("全部齐备" if not fi_issues else "\n  ".join(fi_issues)))

    print("\n--- 3. 命名层 ---")
    print("  " + ("全部一致" if not n_issues else "\n  ".join(n_issues)))

    print("\n--- 4. 只读层 API 同构性（按结构分组比较）---")
    for label, (members, common) in api["groups"].items():
        print(f"  [{label}] {'、'.join(members)}")
        print(f"     公共函数（{len(common)}）：{'、'.join(common)}")
    print("  " + ("各组内同构" if not a_issues else "\n  ".join(a_issues)))

    total = len(f_issues) + len(fi_issues) + len(n_issues) + len(a_issues)
    print("\n" + "=" * 68)
    print(f"不一致项合计：{total}")
    print("=" * 68)
    if "--strict" in argv and total:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
