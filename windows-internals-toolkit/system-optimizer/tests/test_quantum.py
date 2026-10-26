"""量子理念概念系统测试（v0.6.65，CLI 子命令 `quantum`）。

覆盖四条硬性不变量：
  · 八域完整 —— state/circuit/algorithm/hardware/error/network/toolchain/qsim 共 66 个概念，
    by_domain 自洽、id 唯一、gist/detail 非空；
  · 桥接无悬空 —— 每条桥接的目标必须在 plang / netsys / daoxue / datong 中真实存在；
  · 诚实边界 —— 标准核实状态逐条标注（verified 带 source / needs_verify 带 reason），
    不臆造发布状态；
  · qsim 资产同源 —— 模拟器与验证链在 research/quantum/simulator/ 原地可重放，
    honesty 字段如实写明「经典模拟、O(2ⁿ) 墙内」。

另含构建脚本 `--check` 防漂移、CLI 冒烟与只读层 API。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "python"))

from sysweeper.concepts import quantum as qm  # noqa: E402

BUILD = ROOT / "research" / "quantum" / "build_quantum.py"
TAX = ROOT / "src" / "python" / "sysweeper" / "data" / "concepts" / "quantum_taxonomy.json"


def test_domains_and_stats():
    """九域 81 概念（v0.6.78 增 qkern 量子架构内核域；v0.6.79 补全 3 条 + needs_verify 清零；0031 增 qudit/level-dissipation/log-value-exchange）；统计与 counts 一致。"""
    doms = [d["domain"] for d in qm.domains()]
    assert doms == ["state", "circuit", "algorithm", "hardware",
                    "error", "network", "toolchain", "qsim", "qkern"]
    s = qm.stats()
    assert s["concept_total"] == 82
    assert s["domain_count"] == 9
    assert s["bridge_count"] == 56
    assert s["standard_count"] == 11
    # by_domain 自洽
    total = sum(d["count"] for d in qm.domains())
    assert total == s["concept_total"]


def test_concepts_integrity():
    """概念 id 唯一、gist/detail 非空、域归属真实。"""
    cs = qm.concepts()
    ids = [c["id"] for c in cs]
    assert len(ids) == len(set(ids)) == 82
    doms = {d["domain"] for d in qm.domains()}
    for c in cs:
        assert c["domain"] in doms
        assert c["gist"] and c["detail"]
        assert c["name"]
    # 抽样代表性概念
    assert qm.of("qubit")["domain"] == "state"
    assert qm.of("shor")["domain"] == "algorithm"
    assert qm.of("surface-code")["domain"] == "error"
    assert qm.of("qkd-overview")["domain"] == "network"
    assert qm.of("qsim-engine")["domain"] == "qsim"
    assert qm.of("nonexistent") is None


def test_concepts_of_domain_filter():
    """按域过滤与 concepts_of_domain 一致。"""
    for d in qm.domains():
        cs = qm.concepts_of_domain(d["domain"])
        assert len(cs) == d["count"]
        assert all(c["domain"] == d["domain"] for c in cs)


def test_standards_registry():
    """11 条标准登记（v0.6.79：IEEE 7130 草案已核实 + 新增 4 条 kernel.org 参考）：
    verified 带 source，needs_verify 带 reason。"""
    stds = qm.standards()
    assert len(stds) == 11
    for s in stds:
        if s["status"] == "verified":
            assert s.get("source"), f"{s['id']} 缺来源"
        elif s["status"] == "needs_verify":
            assert s.get("reason"), f"{s['id']} 缺待核实原因"
        else:
            raise AssertionError(f"未知状态 {s['status']}")
    # 本轮核实到的关键标准
    verified = {s["id"] for s in stds if s["status"] == "verified"}
    assert {"openqasm3", "qir", "iso-iec-4879", "itu-y3800",
            "etsi-qkd-014", "fips-pqc"} <= verified
    # v0.6.79：IEEE 7130 草案已核实（IEEE Xplore D14 在册），不再挂 needs_verify
    nv = {s["id"] for s in stds if s["status"] == "needs_verify"}
    assert "ieee-7130" not in nv
    assert "ieee-7130" in verified


def test_needs_verify_honesty():
    """v0.6.79 起 needs_verify 清零：IEEE 7130（草案 D14 已核实）与
    quantum-volume（方法论引 Phys. Rev. A 100, 032328）均已消项；
    本测试锁定清零状态，并抽查两条已核实来源在位。"""
    vs = qm.needs_verify()
    assert vs == []
    stds = {s["id"]: s for s in qm.standards()}
    ieee = stds["ieee-7130"]
    assert ieee["status"] == "verified"
    assert "P7130/D14" in ieee.get("source", "") and "2026-08-05" in ieee["source"]
    qv = qm.of("quantum-volume")
    assert not qv.get("needs_verify")
    assert "Phys. Rev. A 100, 032328" in qv["detail"]
    # 草案诚实口径：IEEE 7130 只可称草案，不可称已发布
    assert "草案" in ieee["name"]
    assert "不可称已发布" in ieee["note"] or "正式标准未发布" in ieee["note"]


def test_bridges_no_dangling():
    """桥接目标必须在目标系统中真实存在（无悬空边）。"""
    pdoc = json.loads((ROOT / "src/python/sysweeper/data/concepts/plang_taxonomy.json")
                      .read_text(encoding="utf-8"))
    ndoc = json.loads((ROOT / "src/python/sysweeper/data/concepts/netsys_taxonomy.json")
                      .read_text(encoding="utf-8"))
    ddoc = json.loads((ROOT / "src/python/sysweeper/data/concepts/daoxue_taxonomy.json")
                      .read_text(encoding="utf-8"))
    lang_keys = set(pdoc["lang_index"])
    mods = {m["id"] for m in ndoc["modules"]}
    pids = {p["id"] for p in ddoc["principles"]}
    dtdoc = json.loads((ROOT / "src/python/sysweeper/data/concepts/datong_taxonomy.json")
                       .read_text(encoding="utf-8"))
    dids = {x["id"] for x in dtdoc.get("concepts", [])} | \
           {x["id"] for x in dtdoc.get("principles", [])}
    bgdoc = json.loads((ROOT / "src/python/sysweeper/data/concepts/baigong_taxonomy.json")
                       .read_text(encoding="utf-8"))
    bgids = {x["id"] for x in bgdoc.get("concepts", [])}
    seen_sys = set()
    for b in qm.bridges():
        seen_sys.add(b["system"])
        sys_, tgt = b["system"], b["target"]
        if tgt.endswith(":*"):
            axis = tgt.split(":", 1)[0]
            assert axis in {"model", "arch", "domain", "layer", "nature", "form"}
            continue
        if sys_ == "plang" and tgt.startswith("lang:"):
            assert tgt.split(":", 1)[1] in lang_keys, f"悬空桥接：{tgt}"
        elif sys_ == "netsys" and tgt.startswith("module:"):
            assert tgt.split(":", 1)[1] in mods, f"悬空桥接：{tgt}"
        elif sys_ == "daoxue" and tgt.startswith("principle:"):
            assert tgt.split(":", 1)[1] in pids, f"悬空桥接：{tgt}"
        elif sys_ == "daoxue" and tgt.startswith("guidance:"):
            assert tgt.split(":", 1)[1] == "zhengti_zhida", f"悬空桥接：{tgt}"
        elif sys_ == "datong" and tgt.startswith(("concept:", "principle:")):
            assert tgt.split(":", 1)[1] in dids, f"悬空桥接：{tgt}"
        elif sys_ == "baigong" and tgt.startswith("concept:"):
            assert tgt.split(":", 1)[1] in bgids, f"悬空桥接：{tgt}"
        else:
            raise AssertionError(f"未处理的桥接目标: {sys_}:{tgt}")
    assert {"plang", "netsys", "daoxue"} <= seen_sys


def test_bridges_of_concept():
    """概念级桥接边与顶层 bridges 的 from 字段对齐。"""
    n_top = len(qm.bridges())
    n_from = sum(len(qm.bridges_of(c["id"])) for c in qm.concepts())
    assert n_top == n_from == 56


def test_search():
    """检索命中真实概念；空词返回空。"""
    hits = qm.search("量子")
    assert hits
    ids = {h["id"] for h in hits}
    assert "qubit" in ids
    # 命中可来自 id/名称/纲宗/详述，不要求都出现在 text 里
    assert all(h.get("name") and h.get("where") for h in hits)
    assert qm.search("") == []
    assert qm.search("zzz-not-exist") == []


def test_info_and_redline_notes():
    """_meta 带主目录、诚实边界与红线说明。"""
    m = qm.info()
    assert m["main_root"] == "wordbuddy-github"
    assert m["honesty"] and m["redline_note"]
    assert m["needs_verify_note"]
    # honesty 如实写明：qsim 是经典模拟器，在 O(2ⁿ) 墙内执行
    assert "O(2ⁿ)" in m["honesty"] and "classical" not in m["honesty"].lower()


QSIM_IDS = [
    "qsim-engine", "voltage-view", "phase-matrix", "numeral-convert",
    "trit-register", "log-value-exchange", "born-collapse", "missing-state",
    "swap-cut", "qft-spectrum", "yinyang-entangle", "six-phase-64", "qsim-asset",
]


def test_qsim_domain_contracts():
    """qsim 域 13 概念齐备、engineering 落法非空、桥接指向真实目标。"""
    qsim = qm.concepts_of_domain("qsim")
    assert [c["id"] for c in qsim] == QSIM_IDS
    for c in qsim:
        assert c.get("engineering", "").strip(), f"{c['id']} 缺工程落法"
        assert c["gist"] and c["detail"]
    # 六态位序同构：six-phase-64 桥接覆盖 datong 六象
    six = {b["target"].split(":", 1)[1]
           for b in qm.bridges_of("six-phase-64") if b["system"] == "datong"}
    assert six == {"dian", "ci", "bo", "gu", "ye", "qi"}


def test_qsim_asset_in_place():
    """模拟器资产与同源验证链在 research/quantum/simulator/ 原地在位。"""
    sim = ROOT / "research" / "quantum" / "simulator"
    for f in ("quantum-viewer.html", "extract_engine.py",
              "verify3.mjs", "verify4.mjs", "verify5.mjs"):
        assert (sim / f).exists(), f"资产缺失：{f}"
    assert not (ROOT / "docs" / "quantum-viewer").exists(), "旧目录应已迁走"


def test_qsim_engine_extract_and_assert():
    """同源链原地可跑：extract_engine.py 提取后 verify3 全绿。"""
    import subprocess as sp
    sim = ROOT / "research" / "quantum" / "simulator"
    r = sp.run([sys.executable, "extract_engine.py"], cwd=sim,
               capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "html_engine.mjs" in r.stdout
    r = sp.run(["node", "verify3.mjs"], cwd=sim,
               capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "✗" not in r.stdout and "✓" in r.stdout


def test_build_check_no_drift():
    """构建脚本 --check 防漂移（内容一致应通过）。"""
    r = subprocess.run([sys.executable, str(BUILD), "--check"],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "无悬空" in r.stdout


def test_cli_smoke():
    """CLI 冒烟：overview / domains / of / standards / verify / stats。"""
    def run(*a):
        return subprocess.run(
            [sys.executable, "-m", "sysweeper.cli", *a],
            capture_output=True, text=True, timeout=120, cwd=str(ROOT / "src" / "python"))
    r = run("quantum")
    assert r.returncode == 0, r.stderr
    assert "66" in r.stdout and "八域" in r.stdout or "state" in r.stdout
    assert "诚实边界" in r.stdout
    assert "桥接边 56 条" in r.stdout and "概念共 82 条" in r.stdout
    r = run("quantum", "domains")
    assert r.returncode == 0 and "toolchain" in r.stdout and "qsim" in r.stdout
    r = run("quantum", "of", "shor")
    assert r.returncode == 0 and "Shor" in r.stdout
    r = run("quantum", "standards")
    assert r.returncode == 0 and "needs_verify" in r.stdout and "IEEE 7130" in r.stdout
    r = run("quantum", "verify")
    assert r.returncode == 0 and "已清零" in r.stdout
    r = run("quantum", "stats")
    assert r.returncode == 0 and "concept_total" in r.stdout
    r = run("quantum", "bridge", "netsys")
    assert r.returncode == 0 and "module:" in r.stdout
    r = run("quantum", "search", "纠错")
    assert r.returncode == 0
