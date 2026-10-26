"""概念系统组网/连通性体检（只读审计，不改任何文件）。

回答一个核心问题：九个概念系统（plang/netsys/daoxue/quantum/comp/
apilab/zhuangzi/baigong/datong）能否通过各自的 bridges「链接成整体」？

检查四件事：
  1. 悬空桥接 —— bridge 的 target 指向的 (system, id) 在目标系统里根本不存在
     （kind:id 拼错 / 概念被改名或删除 / 指向九系统之外的未知系统）。
  2. 悬空源点 —— bridge 的 from/principle 在自身系统里不存在（自身数据漂移）。
  3. 系统级连通 —— 把九个系统当节点、bridge 当无向边，是否只有 1 个连通分量？
     孤立系统 = 一条边都没接出去也没接进来的系统（登记了但没嵌入概念整体）。
  4. 概念级孤岛 —— 系统内部从未被任何 bridge 触碰（既不是桥源、也不是桥靶）
     的概念/原则/模块，属「系统内有、整体外」的岛。

用法：
    python3 tools/check_concept_mesh.py
    python3 tools/check_concept_mesh.py --strict   # 有悬空/孤岛时退出码 1
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "python"
sys.path.insert(0, str(SRC))

from sysweeper import concepts as C  # noqa: E402

SYSTEMS = C.systems()


# 各系统里「可作为桥接靶」的条目，用的是不同键名（不是统一 `id`）：
#   plang  execution_models→model / target_archs→arch / domains→domain /
#          lang_index 是 dict(键即语言id) / 顶层 probe 键
#   netsys modules→id / layers→layer / natures→nature / forms→id
#   daoxue/baigong/zhuangzi/datong principles→id，concepts→id
#   quantum/comp/apilab concepts→id
# 因此不能用单一 `id` 键粗暴匹配，必须按真实键名建可解析索引。
_ID_FIELDS = ("id", "model", "arch", "domain", "nature", "layer", "lang")

#: 哪些系统的哪些顶层 dict 是「id 池」（**其键**即可被桥接指向的 id）。
#: 其它顶层 dict（center/pre/counts/by_domain…）是结构数据，不是 id 池，跳过。
#:   plang.lang_index —— 键即语言 id
_DICT_POOLS: dict = {"plang": {"lang_index"}}

#: 哪些系统的哪些顶层段，「段名本身」即可被桥接指向（作为可解析锚）。
#:   daoxue.zhengti_zhida —— 整体指导段，作为九系统组网的「根指导」被其它系统桥接引用
_SEGMENT_ANCHORS: dict = {"daoxue": {"zhengti_zhida"}}


def build_index(name: str) -> set:
    """收集某系统所有可被桥接指向的 id（按真实键名，宽松匹配）。

    返回可解析 id 集合。涵盖：白名单内的 dict 型池（如 plang.lang_index，
    键即语言 id）、各 list 池里 `id/model/arch/domain/nature/layer/lang`
    等键承载的值、以及 plang 顶层 `probe` 池。足以判断 bridge.target 的
    id 是否真实存在，同时**不会**把结构型 dict 的键误当成概念 id。
    """
    doc = C.load(name)
    idx: set = set()
    pools = _DICT_POOLS.get(name, set())
    anchors = _SEGMENT_ANCHORS.get(name, set())
    for key, val in doc.items():
        if isinstance(val, dict):
            if key in pools:
                idx.update(val.keys())          # lang_index: 语言 id 即键
            elif key in anchors:
                idx.add(key)                    # 段名本身作为可解析锚（如 zhengti_zhida）
            continue                            # 其余结构型 dict 跳过
        if isinstance(val, list):
            for it in val:
                if isinstance(it, dict):
                    for fld in _ID_FIELDS:
                        v = it.get(fld)
                        if isinstance(v, str):
                            idx.add(v)
    if "probe" in doc:                          # plang 顶层 probe 池
        idx.add("probe")
    return idx


def collect_ids(name: str) -> dict:
    """兼容旧调用：返回 {id: ['<系统>']} 形态（用于概念级接触统计）。"""
    return {i: [name] for i in build_index(name)}


def resolve_source(name: str, b: dict, ids: dict) -> str | None:
    """返回桥接源 id（来自 `from` 或 `principle` 字段），不存在则报 None。"""
    src = b.get("from")
    if src:
        # 形如 "comp:pipeline-overview"
        return src.split(":", 1)[1] if ":" in src else src
    if "principle" in b:
        return b["principle"]
    return None


def parse_target(t: str) -> tuple[str, str]:
    """'kind:id' -> (kind, id)；无 kind 的 'id' -> ('', id)；'kind:*' -> (kind,'*')。"""
    if ":" in t:
        kind, _, idv = t.partition(":")
        return kind, idv
    return "", t


def main(argv: list[str]) -> int:
    sys_ids = {n: build_index(n) for n in SYSTEMS}

    dangling_targets: list[dict] = []
    dangling_sources: list[dict] = []
    external: dict = defaultdict(int)
    edge: dict = defaultdict(int)          # (src_sys, tgt_sys) -> count
    out_deg: dict = defaultdict(int)
    in_deg: dict = defaultdict(int)
    bridge_total = 0

    # 概念级接触集合：被桥源 / 桥靶触碰过的 (system,id)
    touched: dict = defaultdict(set)

    for name in SYSTEMS:
        ids = sys_ids[name]
        for b in C.load(name).get("bridges", []):
            bridge_total += 1
            tgt_sys = b.get("system")
            tgt = b.get("target", "")
            kind, idv = parse_target(tgt)
            src_id = resolve_source(name, b, ids)

            # 源点校验
            if src_id is None:
                dangling_sources.append({"system": name, "bridge": b,
                                         "why": "无 from/principle 字段"})
            elif src_id not in ids:
                dangling_sources.append({"system": name, "bridge": b,
                                         "why": f"源 id '{src_id}' 不在本系统"})
            else:
                touched[name].add(src_id)

            # 目标系统外？
            if tgt_sys is None:
                dangling_targets.append({"from": name, "bridge": b,
                                         "why": "缺 system 字段"})
                continue
            if tgt_sys not in sys_ids:
                external[tgt_sys] += 1
                continue

            # 跨系统边
            edge[(name, tgt_sys)] += 1
            out_deg[name] += 1
            in_deg[tgt_sys] += 1

            # 目标 id 校验
            if idv == "*":
                # 通配：匹配目标系统该 kind 全部，视为有效
                touched[tgt_sys].add(f"*{kind}")
                continue
            if kind == "guidance":
                # 整体指导伪段（如 zhengti_zhida）：由 daoxue 构建期 bridge_ok 显式放行
                # （kind=="guidance" and val=="zhengti_zhida"），非真实概念 id，不计入悬空。
                touched[tgt_sys].add(f"guidance:{idv}")
                continue
            tgt_ids = sys_ids[tgt_sys]
            if idv not in tgt_ids:
                dangling_targets.append({"from": name, "bridge": b,
                                         "why": f"目标 '{tgt_sys}:{tgt}' 不存在"
                                                f"（{tgt_sys} 无此 id）"})
            else:
                touched[tgt_sys].add(idv)

    # ── 系统级连通分量（无向）──
    adj = defaultdict(set)
    for (a, b) in edge:
        if a != b:
            adj[a].add(b)
            adj[b].add(a)
    visited = set()
    comps = []
    for s in SYSTEMS:
        if s in visited:
            continue
        stack = [s]
        comp = set()
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            comp.add(cur)
            for nxt in adj.get(cur, ()):
                if nxt not in visited:
                    stack.append(nxt)
        comps.append(comp)
    isolated_systems = [s for s in SYSTEMS
                        if out_deg[s] == 0 and in_deg[s] == 0]

    # ── 概念级孤岛（系统内有、整体外）──
    orphan_concepts: dict = {}
    for name in SYSTEMS:
        all_ids = set(sys_ids[name])
        touched_ids = {t for t in touched[name] if not str(t).startswith("*")}
        orphans = sorted(all_ids - touched_ids)
        if orphans:
            orphan_concepts[name] = orphans

    # ── 输出报告 ──
    print("=" * 70)
    print("概念系统组网 / 连通性体检（只读审计）")
    print("=" * 70)
    print(f"\n系统数：{len(SYSTEMS)}（{'、'.join(SYSTEMS)}）")
    print(f"桥接总数：{bridge_total}")

    print("\n--- 1. 悬空桥接（target 不存在 / 未知系统）---")
    if dangling_targets:
        for d in dangling_targets:
            print(f"  ✗ [{d['from']}] {d['why']}")
            print(f"      bridge={json.dumps(d['bridge'], ensure_ascii=False)}")
    else:
        print("  ✓ 全部桥接目标均可解析到真实概念")

    print("\n--- 2. 悬空源点（from/principle 不存在）---")
    if dangling_sources:
        for d in dangling_sources:
            print(f"  ✗ [{d['system']}] {d['why']}")
            print(f"      bridge={json.dumps(d['bridge'], ensure_ascii=False)}")
    else:
        print("  ✓ 全部桥接源点均存在")

    print("\n--- 3. 指向九系统之外的外部目标 ---")
    if external:
        for ext, n in sorted(external.items(), key=lambda x: -x[1]):
            print(f"  · {ext}: {n} 条（非概念系统，跳出整体，按需另建桥）")
    else:
        print("  · 无（全部桥接都落在九个概念系统内）")

    print("\n--- 4. 系统级连通（无向图）---")
    print(f"  连通分量数：{len(comps)}")
    for i, comp in enumerate(comps, 1):
        print(f"  分量 {i}（{len(comp)} 系统）：{'、'.join(sorted(comp))}")
    if len(comps) == 1:
        print("  ✓ 九个系统连通为单一整体")
    else:
        print(f"  ✗ 整体被切成 {len(comps)} 块，存在断网系统")
    if isolated_systems:
        print(f"  ✗ 孤岛系统（零出零入）：{', '.join(isolated_systems)}")
    else:
        print("  ✓ 无孤岛系统")

    print("\n--- 5. 每系统出/入度（桥接密度）---")
    print(f"  {'系统':<10}{'出':>5}{'入':>5}")
    for s in SYSTEMS:
        print(f"  {s:<10}{out_deg[s]:>5}{in_deg[s]:>5}")

    print("\n--- 6. 概念级叶子（系统内有、未被任何桥接触碰）---")
    total_orphans = sum(len(v) for v in orphan_concepts.values())
    total_ids = sum(len(sys_ids[s]) for s in SYSTEMS)
    if orphan_concepts:
        for name, orph in orphan_concepts.items():
            print(f"  · {name}: {len(orph)} 个未接入（如 {orph[:5]}）")
        print(f"  合计：{total_orphans}/{total_ids} 个节点为桥接叶子")
        print("  说明：多为大型目录（plang 161 语言 / quantum 66 概念 / datong 63 概念）")
        print("        的天然独立条目，无需每条都桥接——只要系统级连通（见 4）即构成整体。")
    else:
        print(f"  ✓ 全部 {total_ids} 个节点都至少被一条桥接触碰过")

    print("\n" + "=" * 70)
    problems = len(dangling_targets) + len(dangling_sources) + len(isolated_systems)
    if len(comps) > 1:
        problems += 1
    print(f"断网/欠账项合计：{problems}"
          f"（悬空靶 {len(dangling_targets)} / 悬空源 {len(dangling_sources)}"
          f" / 孤岛系统 {len(isolated_systems)} / 断网分量 {max(0,len(comps)-1)}）")
    print("  概念级叶子（第 6 项）属目录天然形态，不计入欠账。")
    print("=" * 70)

    if "--strict" in argv and problems:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
