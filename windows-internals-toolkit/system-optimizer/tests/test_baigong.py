"""百工匠作概念系统测试（v0.6.61，CLI 子命令 `baigong`）。

覆盖硬性不变量：
  · 四轴完整 —— core/craft/schools/scenes 共 27 个概念，by_domain 自洽；
  · 五偶在位 —— 墨子/公输般/鲁班/公孙策/三教九流总纲，三场景对应用户点名的
    「具体无解 / 暂时不允许 / 构建程序具体结构」；
  · 七条匠作工程原则 —— id 唯一、理念依据限于四偶、落法非空；
  · 三教九流 12 条 —— 三教 3 + 九流 9，一流一工程域；
  · 桥接无悬空 —— 48 条桥接的目标必须在七个既有概念系统中真实存在；
  · 用户端面 + 语言面为实测 —— CLI/GUI/webapi/deno 与源码实测交叉一致，
    plang 161 条 / probe 实测 15 种 / comp 语言编译需要 16 条与数据层交叉一致；
  · needs_verify 挂牌 —— 引文未核对/一名两译/文学形象/工程翻译全部挂牌；
  · 构建脚本 `--check` 防漂移（用户端事实与源码实测漂移即失败）。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "python"))

from sysweeper.concepts import baigong as b  # noqa: E402

BUILD = ROOT / "research" / "baigong" / "build_baigong.py"
TAX = ROOT / "src" / "python" / "sysweeper" / "data" / "concepts" / "baigong_taxonomy.json"


def test_domains_and_stats():
    """四轴 27 概念（5 偶 + 7 原则 + 12 教流 + 3 场景）；统计自洽。"""
    doms = [d["domain"] for d in b.domains()]
    assert doms == ["core", "craft", "schools", "scenes"]
    s = b.stats()
    assert s["concepts"] == 27
    assert s["principles"] == 7
    assert s["bridges"] == 50   # v0.6.62 补 5 条确凿落地边 + v0.6.57+ datong 回边 1 条 + v0.6.67 整体指导桥 1 条
    assert s["by_domain"] == {"core": 5, "craft": 7, "schools": 12, "scenes": 3}


def test_core_five_figures():
    """用户点名的五偶必须在 core 轴（墨子/公输般/鲁班/公孙策/三教九流总纲）。"""
    core = [c["id"] for c in b.concepts_of_domain("core")]
    assert core == ["mozi", "gongshuban", "luban", "gongsunce", "sanjiao-jiuliu"]
    for cid in core:
        c = b.concept(cid)
        assert c["name"] and c["gist"] and c["engineering"]
    # 四偶各至少一条桥接（理念落地既有系统）
    for cid in ("mozi", "gongshuban", "luban", "gongsunce"):
        assert b.bridges_of(cid), f"{cid} 应有桥接"


def test_principles_integrity():
    """七条匠作工程原则：id 唯一、理念依据限于四偶、落法非空。"""
    ps = b.principles()
    ids = [p["id"] for p in ps]
    assert len(ids) == len(set(ids)) == 7
    refs = {r for p in ps for r in p["canon_refs"]}
    assert refs == {"墨子", "公输般", "鲁班", "公孙策"}
    for p in ps:
        assert p["gist"] and p["engineering"]
        assert p["canon_refs"], f"{p['id']} 应挂理念依据"
    assert b.principles_of_canon("墨子") and b.principles_of_canon("鲁班")
    assert b.principle("nonexistent") is None


def test_schools_and_scenes():
    """三教九流 12 条（3+9）；三场景对应用户点名的三个工程场景。"""
    schools = [c["id"] for c in b.concepts_of_domain("schools")]
    assert schools[:3] == ["rujiao", "fojiao", "daojiao"]
    assert len(schools) == 12
    assert len(set(schools)) == 12
    scenes = {c["id"]: c["name"] for c in b.concepts_of_domain("scenes")}
    assert scenes == {"scene-wujie": "具体无解",
                      "scene-buyunxu": "暂时不允许",
                      "scene-jiegou": "构建程序具体结构"}
    for c in b.concepts():
        assert c.get("gist") and c.get("engineering")


def test_read_only_api():
    """只读层 API：concept/of/domain/search/bridges_of 均可达。"""
    assert b.concept("mozi")["name"] == "墨子"
    assert b.of("mozi")["domain"] == "core"
    assert b.domain("core")["concepts"][0]["id"] == "mozi"
    assert b.concept("nonexistent") is None
    assert b.domain("nonexistent") is None
    assert b.search("守御"), "应能检索到墨子守御条目"
    assert any(h["where"].startswith("百工·") for h in b.search("绳墨"))
    assert all(x["system"] == "plang" for x in b.bridges("plang"))
    assert not b.search("不存在的词条xyz")


def test_bridges_no_dangling():
    """43 条桥接的目标在七个既有概念系统中真实存在（数据层反查）。"""
    doc = json.loads(TAX.read_text(encoding="utf-8"))
    p = TAX.parent
    dx = {x["id"] for x in
          json.loads((p / "daoxue_taxonomy.json").read_text(encoding="utf-8"))["principles"]}
    ab = {x["id"] for x in
          json.loads((p / "apilab_taxonomy.json").read_text(encoding="utf-8"))["concepts"]}
    ns = {x["id"] for x in
          json.loads((p / "netsys_taxonomy.json").read_text(encoding="utf-8"))["modules"]}
    cp = {x["id"] for x in
          json.loads((p / "comp_taxonomy.json").read_text(encoding="utf-8"))["concepts"]}
    pl = set(json.loads((p / "plang_taxonomy.json").read_text(encoding="utf-8"))["lang_index"])
    qt = {x["id"] for x in
          json.loads((p / "quantum_taxonomy.json").read_text(encoding="utf-8"))["concepts"]}
    zl = json.loads((p / "zhuangzi_taxonomy.json").read_text(encoding="utf-8"))
    zz = {x["id"] for x in zl["concepts"]} | {x["id"] for x in zl["principles"]}
    dtdoc = json.loads((p / "datong_taxonomy.json").read_text(encoding="utf-8"))
    dt = {x["id"] for x in dtdoc.get("concepts", [])} | \
         {x["id"] for x in dtdoc.get("principles", [])}
    pools = {"daoxue": dx | {"zhengti_zhida"}, "apilab": ab, "netsys": ns, "comp": cp,
             "plang": pl, "quantum": qt, "zhuangzi": zz, "datong": dt}
    assert len(doc["bridges"]) == 50
    for br in doc["bridges"]:
        kind, _, val = br["target"].partition(":")
        pool = pools[br["system"]]
        assert val in pool, f"悬空：{br['system']}:{br['target']}（{kind}）"
        assert br.get("relation") and br.get("how")
        assert br["from"].startswith("baigong:")


def test_user_face_facts_measured():
    """用户端面 + 语言面事实为实测（与 argparse/gui/plang/comp 交叉一致）。"""
    f = b.user_face()
    for k in ("cli_subcommands", "webapi_actions", "gui_windows",
              "lang_total", "probe_verified", "comp_lang_needs"):
        assert isinstance(f[k], int) and f[k] >= 1, k
    for k in ("deno_console_version", "deno_report_viewer_version"):
        assert re.fullmatch(r"\d{4}\.\d{4}\.\d{4}\.\d{4}\.\d{8}", str(f[k])), k  # 里程表式版本号
    # 与 argparse 实测的子命令数交叉一致（含 baigong）
    from sysweeper import cli
    parser = cli.build_parser()
    sub = len([a for a in parser._actions
               if a.__class__.__name__ == "_SubParsersAction"][0].choices)
    assert f["cli_subcommands"] == sub >= 104
    assert "baigong" in [a for a in parser._actions
                         if a.__class__.__name__ == "_SubParsersAction"][0].choices
    # webapi ACTIONS 数交叉一致
    from sysweeper import webapi
    assert f["webapi_actions"] == len(webapi.ACTIONS) >= 29
    # GUI show_* 窗口数与 gui.py 源码实测一致
    gui_src = (ROOT / "src" / "python" / "sysweeper" / "gui.py").read_text(encoding="utf-8")
    assert f["gui_windows"] == len(re.findall(r"def show_\w+\(", gui_src))
    # 语言面：plang 161 条（probe 15）+ comp 语言编译需要 16 条
    plang = json.loads((TAX.parent / "plang_taxonomy.json").read_text(encoding="utf-8"))
    comp = json.loads((TAX.parent / "comp_taxonomy.json").read_text(encoding="utf-8"))
    assert f["lang_total"] == len(plang["lang_index"]) == 161
    assert f["probe_verified"] == len(plang["probe_results"]) == 15
    assert f["comp_lang_needs"] == sum(
        1 for c in comp["concepts"] if c.get("domain") == "lang-need") == 16


def test_needs_verify_posted():
    """诚实边界：引文未核对/一名两译/文学形象/工程翻译全部挂牌。"""
    nv = b.needs_verify()
    assert len(nv) == 4
    assert all(v["status"] == "needs_verify" for v in nv)
    assert all(v.get("note") for v in nv)
    assert any("通行本" in v["note"] for v in nv)


def test_build_check_and_report():
    """构建脚本 --check 防漂移（用户端事实与源码实测漂移即失败）。"""
    r = subprocess.run([sys.executable, str(BUILD), "--check"],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "校验通过" in r.stdout
    r2 = subprocess.run([sys.executable, str(BUILD), "--report"],
                        capture_output=True, text=True, timeout=120)
    assert r2.returncode == 0
    for sysname in ("daoxue", "apilab", "netsys", "comp", "plang", "quantum", "zhuangzi"):
        assert sysname in r2.stdout
