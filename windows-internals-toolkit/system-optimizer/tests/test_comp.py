"""编译与工具链概念系统测试（v0.6.64，CLI 子命令 `comp`）。

覆盖三条硬性不变量：
  · 九轴完整 —— pipeline/toolchain/build/artifact/lang-need/reverse/bitwidth/bringup/cross-reality 共 83 个概念，
    by_domain 自洽、id 唯一；
  · 桥接无悬空 —— 每条桥接的目标必须在 plang / netsys / daoxue / llvm_docs / datong / quantum 中真实存在；
  · 诚实边界 —— 语言编译需要仅对 plang probe 实测通过的 15 种语言逐条登记明细
    （证据取自 probe_results），其余 146 种汇总为一条 needs_verify。

另含构建脚本 `--check` 防漂移、CLI 冒烟与只读层 API。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "python"))

from sysweeper.concepts import comp as cp  # noqa: E402

BUILD = ROOT / "research" / "comp" / "build_comp.py"
TAX = ROOT / "src" / "python" / "sysweeper" / "data" / "concepts" / "comp_taxonomy.json"


def test_domains_and_stats():
    """九轴 87 概念；统计自洽。"""
    doms = [d["domain"] for d in cp.domains()]
    assert doms == ["pipeline", "toolchain", "build", "artifact", "lang-need", "reverse", "bitwidth", "bringup", "cross-reality"]
    s = cp.stats()
    assert s["concept_total"] == 87
    assert s["domain_count"] == 9
    assert s["bridge_count"] == 100
    assert s["lang_need_total"] == 16
    assert s["lang_need_verified"] == 15
    assert s["needs_verify_count"] == 1
    assert sum(d["count"] for d in cp.domains()) == s["concept_total"]


def test_concepts_integrity():
    """概念 id 唯一、gist/detail 非空。"""
    cs = cp.concepts()
    ids = [c["id"] for c in cs]
    assert len(ids) == len(set(ids)) == 87
    doms = {d["domain"] for d in cp.domains()}
    for c in cs:
        assert c["domain"] in doms
        assert c["gist"] and c["detail"] and c["name"]
    assert cp.of("pipeline-overview")["domain"] == "pipeline"
    assert cp.of("need-python")["domain"] == "lang-need"
    assert cp.of("nonexistent") is None


def test_lang_needs_evidence():
    """15 种实测语言逐条带证据（plang probe_results）；146 种汇总 needs_verify。"""
    verified = cp.verified_lang_needs()
    assert len(verified) == 15
    pdoc = json.loads((ROOT / "src/python/sysweeper/data/concepts/plang_taxonomy.json")
                      .read_text(encoding="utf-8"))
    probes = {e["id"]: e for e in pdoc["probe_results"]}
    for c in verified:
        ev = c.get("evidence")
        assert ev and ev.get("status") == "实测通过"
        pid = c.get("probe_id") or c.get("lang")
        assert pid in probes, f"证据源缺失：{pid}"
        assert ev.get("returncode") == probes[pid].get("returncode")
        assert c.get("driver") and c.get("artifact")
    # 汇总条目
    rest = [c for c in cp.lang_needs()
            if c.get("evidence_status") == "needs_verify"]
    assert len(rest) == 1
    assert rest[0]["id"] == "need-rest-unverified"
    assert "146" in rest[0].get("needs_verify", "")
    # 语言名查询
    assert cp.lang_need("python")["id"] == "need-python"
    assert cp.lang_need("makefile")["id"] == "need-makefile"
    assert cp.lang_need("no-such-lang") is None


def test_needs_verify_honesty():
    """诚实边界只登记汇总待核实项。"""
    vs = cp.needs_verify()
    assert len(vs) == 1
    assert vs[0]["id"] == "need-rest-unverified"


def test_bridges_no_dangling():
    """桥接目标必须在目标系统中真实存在（无悬空边）。"""
    pdoc = json.loads((ROOT / "src/python/sysweeper/data/concepts/plang_taxonomy.json")
                      .read_text(encoding="utf-8"))
    ndoc = json.loads((ROOT / "src/python/sysweeper/data/concepts/netsys_taxonomy.json")
                      .read_text(encoding="utf-8"))
    ddoc = json.loads((ROOT / "src/python/sysweeper/data/concepts/daoxue_taxonomy.json")
                      .read_text(encoding="utf-8"))
    ldoc = json.loads((ROOT / "src/python/sysweeper/data/llvm_docs.json")
                      .read_text(encoding="utf-8"))
    lang_keys = set(pdoc["lang_index"])
    models = {m["model"] for m in pdoc.get("execution_models", [])}
    archs = {a["arch"] for a in pdoc.get("target_archs", [])}
    mods = {m["id"] for m in ndoc["modules"]}
    pids = {p["id"] for p in ddoc["principles"]}
    tools = set(ldoc.get("tools", {}))
    triplets = set(ldoc.get("targets", []))
    dtdoc = json.loads((ROOT / "src/python/sysweeper/data/concepts/datong_taxonomy.json")
                       .read_text(encoding="utf-8"))
    dids = {x["id"] for x in dtdoc.get("concepts", [])} | \
           {x["id"] for x in dtdoc.get("principles", [])}
    qdoc = json.loads((ROOT / "src/python/sysweeper/data/concepts/quantum_taxonomy.json")
                      .read_text(encoding="utf-8"))
    qids = {x["id"] for x in qdoc.get("concepts", [])}
    seen_sys = set()
    for b in cp.bridges():
        seen_sys.add(b["system"])
        sys_, tgt = b["system"], b["target"]
        kind, _, val = tgt.partition(":")
        if tgt.endswith(":*"):
            axis = kind
            assert axis in {"model", "arch", "domain", "layer", "nature", "form"}
            continue
        if sys_ == "plang" and kind == "lang":
            assert val in lang_keys, f"悬空桥接：{tgt}"
        elif sys_ == "plang" and kind == "model":
            assert val in models, f"悬空桥接：{tgt}"
        elif sys_ == "plang" and kind == "arch":
            assert val in archs, f"悬空桥接：{tgt}"
        elif sys_ == "netsys" and kind == "module":
            assert val in mods, f"悬空桥接：{tgt}"
        elif sys_ == "daoxue" and kind == "principle":
            assert val in pids, f"悬空桥接：{tgt}"
        elif sys_ == "daoxue" and kind == "guidance":
            assert val == "zhengti_zhida", f"悬空桥接：{tgt}"
        elif sys_ == "llvm" and kind == "tool":
            assert val in tools, f"悬空桥接：{tgt}"
        elif sys_ == "llvm" and kind == "target":
            assert val in triplets, f"悬空桥接：{tgt}"
        elif sys_ == "datong" and kind in ("concept", "principle"):
            assert val in dids, f"悬空桥接：{tgt}"
        elif sys_ == "quantum" and kind == "concept":
            assert val in qids, f"悬空桥接：{tgt}"
        else:
            raise AssertionError(f"未处理的桥接目标: {sys_}:{tgt}")
    assert {"plang", "llvm", "daoxue"} <= seen_sys


def test_bridges_of_concept():
    """概念级桥接边与顶层 bridges 的 from 字段对齐。"""
    n_top = len(cp.bridges())
    n_from = sum(len(cp.bridges_of(c["id"])) for c in cp.concepts())
    assert n_top == n_from == 100


def test_search():
    """检索命中真实概念；空词返回空。"""
    hits = cp.search("编译")
    assert hits
    assert cp.search("") == []


def test_info_honesty():
    """_meta 带主目录与诚实边界。"""
    m = cp.info()
    assert m["main_root"] == "wordbuddy-github"
    assert "15 种" in m["honesty"] and "146" in m["honesty"]
    assert m["redline_note"]


def test_build_check_no_drift():
    """构建脚本 --check 防漂移。"""
    r = subprocess.run([sys.executable, str(BUILD), "--check"],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "无悬空" in r.stdout


def test_cli_smoke():
    """CLI 冒烟：overview / domains / of / need / needs / verify / stats。"""
    def run(*a):
        return subprocess.run(
            [sys.executable, "-m", "sysweeper.cli", *a],
            capture_output=True, text=True, timeout=120, cwd=str(ROOT / "src" / "python"))
    r = run("comp")
    assert r.returncode == 0, r.stderr
    assert "诚实边界" in r.stdout and "桥接边 100 条" in r.stdout
    r = run("comp", "of", "need-python")
    assert r.returncode == 0 and "实测证据" in r.stdout and "CPython" in r.stdout
    r = run("comp", "need", "rust")
    assert r.returncode == 0 and "rustc" in r.stdout
    r = run("comp", "needs")
    assert r.returncode == 0 and "实测通过" in r.stdout
    r = run("comp", "verify")
    assert r.returncode == 0 and "146" in r.stdout
    r = run("comp", "bridge", "plang")
    assert r.returncode == 0 and "lang:" in r.stdout
    r = run("comp", "search", "链接")
    assert r.returncode == 0
