"""编程语言与编译器知识库测试（v0.6.53）。

覆盖 data/langs_docs.json 的只读层（native/langs）与 schema 一致性校验
（research/langs/validate_langs.py）。不复制教材、不联网；只验证结构化元数据
的口径与防漂移不变量。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "python"))

from sysweeper.native import langs as lg  # noqa: E402

# 校验脚本在 monorepo 根的 research/langs/（与 research/rfc、research/recert 同款位置）
VALIDATE = ROOT.parents[1] / "research" / "langs" / "validate_langs.py"
DATA = ROOT / "src" / "python" / "sysweeper" / "data" / "langs_docs.json"
_doc = json.loads(DATA.read_text(encoding="utf-8"))


def test_entry_count_consistent():
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    assert doc["_meta"]["entry_count"] == len(doc["languages"])


def test_stats_shape():
    s = lg.stats()
    assert s["total"] == 161
    assert s["in_window"] == 72
    assert s["out_of_window"] == 89
    assert s["needs_verify"] == 12
    assert s["by_category"]["compiled"] == 73


def test_get_known_entries():
    rust = lg.get("rust")
    assert rust["name"] == "Rust"
    assert rust["first_year"] == 2010
    assert rust["in_window"] is True

    cj = lg.get("cangjie")
    assert cj["origin"] == "国内"
    assert cj["in_window"] is True


def test_window_sorted_desc():
    w = lg.window(only=True)
    years = [e["first_year"] for e in w]
    assert years == sorted(years, reverse=True)
    assert all(2008 <= y <= 2026 for y in years)
    # 最近一条应为 2024 的仓颉
    assert w[0]["id"] == "cangjie"


def test_in_window_invariants():
    """每条 in_window 必须与 first_year 落在 2008–2026 一致（防漂移核心不变量）。"""
    for e in _doc["languages"]:
        fy = e["first_year"]
        assert bool(e["in_window"]) == (2008 <= fy <= 2026), e["id"]


def test_search_finds_rust():
    hits = lg.search("rust")
    assert any(e["id"] == "rust" for e in hits)
    assert all("rust" in (
        e["name"] + e["name_zh"] + e["designer"] + " ".join(e["paradigms"]) + e["notes"]
    ).lower() for e in hits)


def test_by_origin_domestic():
    cn = lg.by_origin("国内")
    ids = {e["id"] for e in cn}
    assert {"wenyan", "cangjie", "wa", "goplus", "easylanguage",
            "hanyu", "arkts"}.issubset(ids)
    assert len(cn) == 10
    # 易语言/周蟒/汉语编程为历史锚点（in_window=False）但来源仍属国内
    assert lg.get("easylanguage")["in_window"] is False
    assert lg.get("hanyu")["in_window"] is False
    # ArkTS 是窗口内的国产语言
    assert lg.get("arkts")["in_window"] is True


def test_esolangs_present():
    """esolang（深奥语言）家族已入库。"""
    ids = {e["id"] for e in lg.all_langs()}
    assert {"brainfuck", "befunge", "intercal", "malbolge", "piet",
            "whitespace", "lolcode", "unlambda", "shakespeare", "chef"}.issubset(ids)
    bf = lg.get("brainfuck")
    assert bf["category"] == "interpreted"
    assert "esolang" in bf["paradigms"]


def test_hdl_category():
    """硬件描述语言（hdl）分类。"""
    hdl = lg.by_category("hdl")
    assert {e["id"] for e in hdl} == {"verilog", "vhdl"}
    assert lg.get("verilog")["standard"].startswith("IEEE")


def test_paradigm_family_apl_and_logic():
    """数组(APL)家族与逻辑/定理证明家族。"""
    ids = {e["id"] for e in lg.all_langs()}
    assert {"apl", "jlang", "klang", "bqn"}.issubset(ids)      # APL 家族
    assert {"coq", "agda", "isabelle", "mercury", "curry"}.issubset(ids)
    assert lg.get("coq")["category"] == "verification"


def test_category_ir_unique():
    ir = lg.by_category("ir")
    assert [e["id"] for e in ir] == ["wasm"]


def test_needs_verify_listed():
    nv = lg.needs_verify()
    assert len(nv) == 12
    assert all(isinstance(e["needs_verify"], list) for e in nv)
    # 存疑项必须真在库里，且都是「以官网为准」类说明
    assert "assembly" in {e["id"] for e in nv}
    assert "coq" in {e["id"] for e in nv}


def test_validate_script_check_passes():
    """research/langs/validate_langs.py --check 应零错误退出（schema + entry_count 一致）。"""
    r = subprocess.run([sys.executable, str(VALIDATE), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
