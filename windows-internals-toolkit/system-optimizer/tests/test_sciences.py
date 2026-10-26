"""自然科学概念系统测试（sciences，v0.6.67）。

覆盖：
  · 只读层 API 同构 —— info/domains/concepts/principles/bridges/search/stats/needs_verify；
  · 构建脚本 `--check` 防漂移（用户端·语言面事实与源码实测漂移即失败）；
  · 用户端面事实为实测（与 argparse/gui/plang/comp 交叉一致）；
  · 诚实边界：3 项 needs_verify 挂牌（标准编号/最新版次等）。

数据层由 research/sciences/build_sciences.py 构建，32 个概念 / 18 条桥接 / 7 条原则。
sciences 是 protec 工程保护的科学底座。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "python"))

from sysweeper.concepts import sciences as sc  # noqa: E402
from sysweeper import concepts as C  # noqa: E402

TAX = ROOT / "src" / "python" / "sysweeper" / "data" / "concepts" / "sciences_taxonomy.json"
BUILD = ROOT / "research" / "sciences" / "build_sciences.py"


def test_domains_and_stats():
    """八域（材料/热/气候/环境/物理/化学/生物/方法）与统计自洽。"""
    doms = sc.domains()
    assert [d["domain"] for d in doms] == [
        "materials", "thermodynamics", "climatology", "environmental",
        "physics", "chemistry", "biology", "methodology"]
    st = sc.stats()
    assert st["concepts"] == 32
    assert st["bridges"] == 18
    assert st["principles"] == 7
    assert sum(len(sc.concepts_of_domain(d["domain"])) for d in doms) == 32


def test_read_only_api():
    """只读层函数全部可用且不抛异常（与 datong/protec 同构）。"""
    assert sc.info()["title"]
    assert callable(sc.concept) and callable(sc.of)
    assert callable(sc.principles_of) and callable(sc.principles_of_canon)
    assert sc.principles_of_canon("datong") == sc.principles_of("datong")
    assert callable(sc.bridges) and callable(sc.bridges_of)
    assert callable(sc.search) and callable(sc.needs_verify)


def test_bridges_no_dangling():
    """桥接目标均指向已登记系统或外部靶，无悬空（构建期亦校验）。"""
    doc = json.loads(TAX.read_text(encoding="utf-8"))
    systems = set(C.systems())
    for b in doc["bridges"]:
        tgt = b["system"]
        assert tgt in systems or tgt in doc.get("external_targets", {}), \
            f"悬空桥接：{b['from']} → {tgt}"


def test_user_face_facts_measured():
    """用户端面 + 语言面事实为实测（与 argparse/gui/plang/comp 交叉一致）。"""
    f = sc.user_face()
    for k in ("cli_subcommands", "webapi_actions", "gui_windows",
              "lang_total", "probe_verified", "comp_lang_needs"):
        assert isinstance(f[k], int) and f[k] >= 1, k
    for k in ("deno_console_version", "deno_report_viewer_version"):
        assert re.fullmatch(r"\d{4}\.\d{4}\.\d{4}\.\d{4}\.\d{8}", str(f[k])), k
    assert f["concept_systems"] == 11
    assert len(C.systems()) == f["concept_systems"]
    from sysweeper import cli
    parser = cli.build_parser()
    sub = len([a for a in parser._actions
               if a.__class__.__name__ == "_SubParsersAction"][0].choices)
    assert f["cli_subcommands"] == sub >= 107
    assert "sciences" in [a for a in parser._actions
                          if a.__class__.__name__ == "_SubParsersAction"][0].choices
    from sysweeper import webapi
    assert f["webapi_actions"] == len(webapi.ACTIONS) >= 29
    gui_src = (ROOT / "src" / "python" / "sysweeper" / "gui.py").read_text(encoding="utf-8")
    assert f["gui_windows"] == len(re.findall(r"def show_\w+\(", gui_src))
    assert "def show_sciences(" in gui_src
    plang = json.loads((TAX.parent / "plang_taxonomy.json").read_text(encoding="utf-8"))
    comp = json.loads((TAX.parent / "comp_taxonomy.json").read_text(encoding="utf-8"))
    assert f["lang_total"] == len(plang["lang_index"]) == 161
    assert f["probe_verified"] == len(plang["probe_results"]) == 15
    assert f["comp_lang_needs"] == sum(
        1 for c in comp["concepts"] if c.get("domain") == "lang-need") == 16


def test_needs_verify_posted():
    """诚实边界：标准编号/最新版次等 3 项挂牌（item/status/note 齐备）。"""
    nv = sc.needs_verify()
    assert len(nv) == 3
    for v in nv:
        assert v.get("item") and v.get("note") and v.get("status")
    items = "；".join(v["item"] for v in nv)
    assert "标准" in items


def test_build_check_and_report():
    """构建脚本 --check 防漂移（用户端·语言面事实与源码实测漂移即失败）。"""
    r = subprocess.run([sys.executable, str(BUILD), "--check"],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "校验通过" in r.stdout
    r2 = subprocess.run([sys.executable, str(BUILD), "--report"],
                        capture_output=True, text=True, timeout=120)
    assert r2.returncode == 0
    assert "sciences" in r2.stdout
