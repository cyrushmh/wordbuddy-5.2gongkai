"""编程语言「概念系统」测试（v0.6.56，CLI 子命令 `plang`）。

覆盖分层分类只读层（concepts/plang）与两条硬性不变量：
  · RFC 依据真实性 —— 概念系统引用的每个 RFC 编号都能在**本仓库 rfc_catalog** 中查到
    （「不足的以 RFC 等底层标准补充」必须补的是真标准，不是编的编号）；
  · 分类覆盖完整 —— 161 条语言全部落入某个执行模型 + 至少一个架构。
另含「各语言尝试编程整体」实测记录的校验。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "python"))

from sysweeper.concepts import plang as pg  # noqa: E402
from sysweeper.native import rfc_catalog as rfc  # noqa: E402

BUILD = ROOT / "research" / "plang" / "build_plang.py"
PROBE = ROOT / "research" / "plang" / "run_probe.py"
TAX = ROOT / "src" / "python" / "sysweeper" / "data" / "concepts" / "plang_taxonomy.json"


def test_info_and_stats():
    m = pg.info()
    assert m["system_root"] == "wordbuddy-github"
    s = pg.stats()
    assert s["lang_total"] == 161
    assert s["model_count"] == 8
    assert s["arch_count"] == 13
    assert s["domain_count"] == 9  # 含新增的 esolang / education 两个域
    # 逐条细化后：不应再有任何「按类推断」的条目
    assert s["by_mapping_source"].get("inferred", 0) == 0
    assert s["by_mapping_source"].get("explicit") == 161


def test_arch_kinds_present():
    """硬件架构子分类必须覆盖 isa / vm / 加速器 / 可重构 / 宿主 / 非执行。"""
    kinds = {a["kind"] for a in pg.archs()}
    assert {"isa", "virtual-isa", "vm", "accelerator", "reconfigurable",
            "host", "non-exec"}.issubset(kinds)


def test_arch_fpga_and_gpu():
    assert sorted(pg.langs_of_arch("fpga")) == ["verilog", "vhdl"]
    assert {"futhark", "bend", "mojo"}.issubset(set(pg.langs_of_arch("gpu-simt")))


def test_arch_vm_groups():
    # 细化后：whiley 编译到 JVM、haxe 多目标含 JVM，故一并归入
    assert {"java", "kotlin", "scala", "clojure", "ballerina", "whiley", "haxe"} == \
        set(pg.langs_of_arch("jvm"))
    assert {"erlang", "elixir", "gleam"} == set(pg.langs_of_arch("beam"))
    assert {"solidity", "move", "cairo", "noir"} == set(pg.langs_of_arch("evm"))


def test_of_rust_classification():
    v = pg.of("rust")
    assert v["model"] == "native"
    assert "x86-64" in v["archs"] and "wasm" in v["archs"]
    assert "systems" in v["domains"] and "network" in v["domains"]
    assert v["mapping_source"] == "explicit"


def test_all_langs_have_model_and_arch():
    doc = json.loads(TAX.read_text(encoding="utf-8"))
    models = {m["model"] for m in doc["execution_models"]}
    archs = {a["arch"] for a in doc["target_archs"]}
    for lid, v in doc["lang_index"].items():
        assert v["model"] in models, lid
        assert v["archs"], lid
        for a in v["archs"]:
            assert a in archs, f"{lid} 架构 {a} 未登记"


def test_every_rfc_ref_exists_in_rfc_catalog():
    """硬性不变量：概念系统引用的每个 RFC 编号都必须能在 rfc_catalog 中查到。"""
    seen = set()
    checked = 0
    for d in pg.domains():
        for s in d.get("standards", []):
            if s.get("kind") != "RFC":
                continue
            num = s["num"]
            if num in seen:
                continue
            seen.add(num)
            info = rfc.rfc_info(num)
            assert info is not None, f"RFC {num} 不在 rfc_catalog 中（编号不实）"
            checked += 1
    assert checked >= 10, f"RFC 依据过少：{checked}"


def test_standards_inherited_by_domain():
    """语言按所属能力域继承底层标准（补足自身标准不足）。"""
    refs = pg.rfc_refs("rust")
    assert {s["num"] for s in refs} >= {9293, 9110, 8446, 1035}
    # 非执行类（如 Verilog）也能拿到所属域的依据
    assert pg.of("verilog")["standards"]
    # 未登记语言返回空
    assert pg.standards_of("__nonexistent__") == []


def test_probe_records_present():
    """「各语言尝试编程整体」实测记录。"""
    p = pg.probe()
    assert p["results"], "无实测记录"
    passed = [r for r in p["results"] if r["status"] == "实测通过"]
    assert len(passed) == 15
    for r in passed:
        assert len(r.get("kv", {})) >= 8, f"{r['id']} 能力面不足 8"
        for k in ("LANG", "OPS", "CONTROL", "FUNC", "DATA", "IO", "ERROR",
                  "CONCURRENCY"):
            assert k in r["kv"], f"{r['id']} 缺能力面 {k}"


def test_build_plang_check_passes():
    """build_plang.py --check 应零错误（RFC 命中 + 架构合法 + 覆盖完整）。"""
    r = subprocess.run([sys.executable, str(BUILD), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_probe_check_passes():
    """run_probe.py --check 应通过（样例存在 + 实测记录完整）。"""
    r = subprocess.run([sys.executable, str(PROBE), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
