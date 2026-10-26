"""产品长期运行与基本保护概念系统测试（protec，v0.6.69）。

覆盖：
  · 只读层 API 同构 —— info/domains/concepts/principles/bridges/search/stats/needs_verify；
  · 构建脚本 `--check` 防漂移（用户端·语言面事实与源码实测漂移即失败）；
  · 用户端面事实为实测（与 argparse/gui/plang/comp 交叉一致）；
  · 诚实边界：8 项 needs_verify 挂牌（标准编号/机构口径/非 RFC 算法/安全公告/星闪国标/SEND 生态等）。

数据层由 research/protec/build_protec.py 构建，八域 53 个概念 / 34 条桥接 / 7 条原则。
（v0.6.67 新增 transfer 传输与可用性域；v0.6.68 新增 access 接入与链路域：以太网/WLAN/
WiFi 安全/802.1X/VLAN/PPPoE，与 docs/75 同源；v0.6.69 access 域补星闪 sparklink、
新增 ipv6 IPv6 与 ICMPv6 控制面域 10 概念，与 docs/76 同源）
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "python"))

from sysweeper.concepts import protec as p  # noqa: E402
from sysweeper import concepts as C  # noqa: E402

TAX = ROOT / "src" / "python" / "sysweeper" / "data" / "concepts" / "protec_taxonomy.json"
BUILD = ROOT / "research" / "protec" / "build_protec.py"


def test_domains_and_stats():
    """八域（耐久/电气/环境/应急/保护/传输与可用性/接入与链路/IPv6 控制面）与统计自洽。"""
    doms = p.domains()
    assert [d["domain"] for d in doms] == [
        "durability", "electrical", "environment", "emergency", "protection",
        "transfer", "access", "ipv6"]
    st = p.stats()
    assert st["concepts"] == 53
    assert st["bridges"] == 34
    assert st["principles"] == 7
    # 各域概念数之和等于总数
    assert sum(len(p.concepts_of_domain(d["domain"])) for d in doms) == 53


def test_read_only_api():
    """只读层函数全部可用且不抛异常（与 datong 同构）。"""
    assert p.info()["title"]
    assert callable(p.concept) and callable(p.of)
    assert callable(p.principles_of) and callable(p.principles_of_canon)
    # principles_of_canon 与 principles_of 同构（别名）
    assert p.principles_of_canon("datong") == p.principles_of("datong")
    assert callable(p.bridges) and callable(p.bridges_of)
    assert callable(p.search) and callable(p.needs_verify)


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
    f = p.user_face()
    for k in ("cli_subcommands", "webapi_actions", "gui_windows",
              "lang_total", "probe_verified", "comp_lang_needs"):
        assert isinstance(f[k], int) and f[k] >= 1, k
    for k in ("deno_console_version", "deno_report_viewer_version"):
        assert re.fullmatch(r"\d{4}\.\d{4}\.\d{4}\.\d{4}\.\d{8}", str(f[k])), k
    # concept_systems 与注册表现数一致（protec 为第十一系统之一）
    assert f["concept_systems"] == 11
    assert len(C.systems()) == f["concept_systems"]
    # 与 argparse 实测的子命令数交叉一致（含 protec）
    from sysweeper import cli
    parser = cli.build_parser()
    sub = len([a for a in parser._actions
               if a.__class__.__name__ == "_SubParsersAction"][0].choices)
    assert f["cli_subcommands"] == sub >= 107
    assert "protec" in [a for a in parser._actions
                        if a.__class__.__name__ == "_SubParsersAction"][0].choices
    # webapi ACTIONS 数交叉一致
    from sysweeper import webapi
    assert f["webapi_actions"] == len(webapi.ACTIONS) >= 29
    # GUI show_* 窗口数与 gui.py 源码实测一致（含 show_protec）
    gui_src = (ROOT / "src" / "python" / "sysweeper" / "gui.py").read_text(encoding="utf-8")
    assert f["gui_windows"] == len(re.findall(r"def show_\w+\(", gui_src))
    assert "def show_protec(" in gui_src
    # 语言面：plang 161 条（probe 15）+ comp 语言编译需要 16 条
    plang = json.loads((TAX.parent / "plang_taxonomy.json").read_text(encoding="utf-8"))
    comp = json.loads((TAX.parent / "comp_taxonomy.json").read_text(encoding="utf-8"))
    assert f["lang_total"] == len(plang["lang_index"]) == 161
    assert f["probe_verified"] == len(plang["probe_results"]) == 15
    assert f["comp_lang_needs"] == sum(
        1 for c in comp["concepts"] if c.get("domain") == "lang-need") == 16


def test_needs_verify_posted():
    """诚实边界：标准编号/机构口径/非 RFC 算法/安全公告/星闪国标/SEND 生态等 8 项挂牌（item/status/note 齐备）。"""
    nv = p.needs_verify()
    assert len(nv) == 8
    for v in nv:
        assert v.get("item") and v.get("note") and v.get("status")
    items = "；".join(v["item"] for v in nv)
    assert "标准" in items
    assert "非 IETF" in items
    assert "KRACK" in items


def test_build_check_and_report():
    """构建脚本 --check 防漂移（用户端·语言面事实与源码实测漂移即失败）。"""
    r = subprocess.run([sys.executable, str(BUILD), "--check"],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "校验通过" in r.stdout
    r2 = subprocess.run([sys.executable, str(BUILD), "--report"],
                        capture_output=True, text=True, timeout=120)
    assert r2.returncode == 0
    assert "protec" in r2.stdout
