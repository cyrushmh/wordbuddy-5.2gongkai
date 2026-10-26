"""大同人类文明一体概念系统测试（v0.6.62，CLI 子命令 `datong`）。

覆盖硬性不变量：
  · 五轴完整 —— traditions/theses/six/practices/ethics 共 63 个概念，
    by_domain 自洽（15 传统 + 21 命题 + 6 六象 + 12 实践 + 9 原则）；
  · 用户点名在位 —— 「一体两面」「三位一体」「神恩如狱」「萨满巫觋」
    「唯道独尊」「人类一体」全部落册；
  · 正道六象 —— 固/液/气/电/磁/波六象，天罡元阳（气·电·波·外发）/
    地煞元阴（固·液·磁·内聚）分属登记，各带科学口径与工程落法；
  · 九条人间落法 —— id 唯一、理念依据（canon_refs）非空、落法非空；
  · 桥接无悬空 —— 50 条桥接的目标在八个既有概念系统中真实存在；
  · 用户端面 + 语言面为实测 —— CLI 107/GUI 91/webapi 29/deno 0.6.61
    与源码实测交叉一致，plang 161 条 / probe 实测 15 种 /
    comp 语言编译需要 16 条与数据层交叉一致；
  · needs_verify 挂牌 —— 原典未核对/诗化口径/同构框架/年代分歧/词源争议/
    正名约定/概说共 7 项全部挂牌；
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

from sysweeper.concepts import datong as d  # noqa: E402

BUILD = ROOT / "research" / "datong" / "build_datong.py"
TAX = ROOT / "src" / "python" / "sysweeper" / "data" / "concepts" / "datong_taxonomy.json"


def test_domains_and_stats():
    """五轴 63 概念（15 传统 + 21 命题 + 6 六象 + 12 实践 + 9 原则）；统计自洽。"""
    doms = [x["domain"] for x in d.domains()]
    assert doms == ["traditions", "theses", "six", "practices", "ethics"]
    s = d.stats()
    assert s["concepts"] == 63
    assert s["principles"] == 9
    assert s["bridges"] == 51
    assert s["by_domain"] == {"traditions": 15, "theses": 21, "six": 6,
                              "practices": 12, "ethics": 9}


def test_user_named_items():
    """用户三段原话点名的条目必须落册。"""
    # 「人类命运是一个的」→ 人类一体；「一体两面，三位一体，主的神恩如狱」
    named = {"renti-yiti": "人类一体", "yiti-liangmian": "一体两面",
             "sanwei-yiti": "三位一体", "shenen-ruyu": "神恩如狱"}
    for cid, name in named.items():
        c = d.concept(cid)
        assert c is not None and c["name"] == name, cid
        assert c["gist"] and c["detail"] and c["engineering"]
    # 「还有萨满巫觋等」→ 萨满传统在册（绝地天通与 theses 轴互文）
    saman = d.concept("saman")
    assert saman is not None and saman["name"] == "萨满巫觋"
    assert "绝地天通" in saman["detail"]
    # 「所以古来唯道独成尊」→ 第 21 条核心命题，锚道德经/庄子/周易
    wd = d.concept("weidao-duzun")
    assert wd is not None and "唯道独尊" in wd["name"]
    assert "道德经" in wd["detail"] and "庄子" in wd["detail"]
    assert "周易" in wd["detail"]
    # theses 轴 21 条、末条为唯道独尊（万流殊涂同归，道为所宗）
    theses = [c["id"] for c in d.concepts_of_domain("theses")]
    assert len(theses) == 21 and theses[-1] == "weidao-duzun"


def test_six_phase_yinyang():
    """正道六象：固/液/气/电/磁/波；元阳属气电波、元阴属固液磁。"""
    six = [c["id"] for c in d.concepts_of_domain("six")]
    assert six == ["gu", "ye", "qi", "dian", "ci", "bo"]
    yuan_yang = {"qi", "dian", "bo"}   # 天罡元阳：外发
    yuan_yin = {"gu", "ye", "ci"}      # 地煞元阴：内聚
    for cid in six:
        c = d.concept(cid)
        assert c["name"] and c["gist"] and c["detail"] and c["engineering"]
        if cid in yuan_yang:
            assert "天罡元阳" in c["gist"], f"{cid} 应属天罡元阳"
        else:
            assert "地煞元阴" in c["gist"], f"{cid} 应属地煞元阴"
        assert "科学口径" in c["detail"] and "工程落法" in c["detail"]
    # 电磁共为一体两面的同构登记（麦克斯韦方程组统一）
    assert "一体两面" in d.concept("ci")["detail"]
    # 六象各有一条工程桥接（理念落地既有系统）
    for cid in six:
        assert d.bridges_of(cid), f"{cid} 应有桥接"


def test_fields_complete():
    """v0.6.62 字段齐备：每个概念必备 gist（纲宗）/ detail（详述）/
    engineering（工程落法）三件套，缺一即视为内容账未平。"""
    for c in d.concepts():
        assert c.get("gist"), f"{c['id']} 缺 gist"
        assert c.get("detail"), f"{c['id']} 缺 detail"
        assert c.get("engineering"), f"{c['id']} 缺 engineering"


def test_principles_integrity():
    """九条人间落法工程原则：id 唯一、理念依据非空、落法非空。"""
    ps = d.principles()
    ids = [p["id"] for p in ps]
    assert len(ids) == len(set(ids)) == 9
    for p in ps:
        assert p["gist"] and p["engineering"]
        assert p["canon_refs"], f"{p['id']} 应挂理念依据"
    # 理念依据反查：儒/一体两面命题均有人间落法依靠
    assert d.principles_of("rujia"), "儒 应有原则依靠"
    assert d.principles_of("yiti-liangmian"), "一体两面 应有原则依靠"
    assert d.principle("nonexistent") is None
    # ethics 轴概念与 principles 同 id 同源（9=9）
    ethics = [c["id"] for c in d.concepts_of_domain("ethics")]
    assert sorted(ethics) == sorted(ids)


def test_traditions_and_practices():
    """十五传统（萨满巫觋在册）+ 十二实践；全部概念纲宗/落法非空。"""
    traditions = [c["id"] for c in d.concepts_of_domain("traditions")]
    assert len(traditions) == 15 and len(set(traditions)) == 15
    assert "saman" in traditions
    practices = [c["id"] for c in d.concepts_of_domain("practices")]
    assert len(practices) == 12 and len(set(practices)) == 12
    assert "saman-chushen" in practices
    for c in d.concepts():
        assert c.get("gist") and c.get("engineering"), c["id"]


def test_read_only_api():
    """只读层 API：concept/of/domain/search/bridges_of 均可达。"""
    assert d.concept("rujia")["name"] == "儒"
    assert d.of("rujia")["domain"] == "traditions"
    assert d.domain("six")["concepts"][0]["id"] == "gu"
    assert d.concept("nonexistent") is None
    assert d.domain("nonexistent") is None
    assert d.search("一体"), "应能检索到一体两面条目"
    assert any(h["where"].startswith("大同·") for h in d.search("唯道"))
    assert all(x["system"] == "daoxue" for x in d.bridges("daoxue"))
    assert d.bridges("daoxue") and len(d.bridges("netsys")) == 7
    assert not d.search("不存在的词条xyz")


def test_bridges_no_dangling():
    """50 条桥接的目标在八个既有概念系统中真实存在（数据层反查）。"""
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
    bg = json.loads((p / "baigong_taxonomy.json").read_text(encoding="utf-8"))
    bb = {x["id"] for x in bg["concepts"]} | {x["id"] for x in bg["principles"]}
    pools = {"daoxue": dx | {"zhengti_zhida"}, "apilab": ab, "netsys": ns, "comp": cp,
             "plang": pl, "quantum": qt, "zhuangzi": zz, "baigong": bb}
    assert len(doc["bridges"]) == 51
    for br in doc["bridges"]:
        kind, _, val = br["target"].partition(":")
        pool = pools[br["system"]]
        assert val in pool, f"悬空：{br['system']}:{br['target']}（{kind}）"
        # kind 必须与目标系统的口径一致（v0.6.62：daoxue=principle / netsys=module /
        # plang 语言条目一律 lang:，其余轴型系统=concept: 或 principle:）
        if br["system"] == "plang":
            assert kind == "lang", f"指向 plang 语言条目须用 lang:，实为 {kind}"
        elif br["system"] == "netsys":
            assert kind == "module", f"指向 netsys 须用 module:，实为 {kind}"
        elif br["system"] == "daoxue":
            assert kind in ("principle", "guidance"), f"指向 daoxue 须用 principle:/guidance:，实为 {kind}"
        else:
            assert kind in ("concept", "principle"), f"{br['system']} kind 异常：{kind}"
        assert br.get("relation") and br.get("how")
        assert br["from"].startswith("datong:")


def test_user_face_facts_measured():
    """用户端面 + 语言面事实为实测（与 argparse/gui/plang/comp 交叉一致）。"""
    f = d.user_face()
    for k in ("cli_subcommands", "webapi_actions", "gui_windows",
              "lang_total", "probe_verified", "comp_lang_needs"):
        assert isinstance(f[k], int) and f[k] >= 1, k
    for k in ("deno_console_version", "deno_report_viewer_version"):
        assert re.fullmatch(r"\d{4}\.\d{4}\.\d{4}\.\d{4}\.\d{8}", str(f[k])), k  # 里程表式版本号
    # concept_systems 与注册表现数一致（datong 为第十一个系统之一）
    assert f["concept_systems"] == 11
    from sysweeper import concepts as C
    assert len(C.systems()) == f["concept_systems"]
    # 与 argparse 实测的子命令数交叉一致（含 datong）
    from sysweeper import cli
    parser = cli.build_parser()
    sub = len([a for a in parser._actions
               if a.__class__.__name__ == "_SubParsersAction"][0].choices)
    assert f["cli_subcommands"] == sub >= 107
    assert "datong" in [a for a in parser._actions
                        if a.__class__.__name__ == "_SubParsersAction"][0].choices
    # webapi ACTIONS 数交叉一致
    from sysweeper import webapi
    assert f["webapi_actions"] == len(webapi.ACTIONS) >= 29
    # GUI show_* 窗口数与 gui.py 源码实测一致（含 show_datong）
    gui_src = (ROOT / "src" / "python" / "sysweeper" / "gui.py").read_text(encoding="utf-8")
    assert f["gui_windows"] == len(re.findall(r"def show_\w+\(", gui_src))
    assert "def show_datong(" in gui_src
    # 语言面：plang 161 条（probe 15）+ comp 语言编译需要 16 条
    plang = json.loads((TAX.parent / "plang_taxonomy.json").read_text(encoding="utf-8"))
    comp = json.loads((TAX.parent / "comp_taxonomy.json").read_text(encoding="utf-8"))
    assert f["lang_total"] == len(plang["lang_index"]) == 161
    assert f["probe_verified"] == len(plang["probe_results"]) == 15
    assert f["comp_lang_needs"] == sum(
        1 for c in comp["concepts"] if c.get("domain") == "lang-need") == 16


def test_needs_verify_posted():
    """诚实边界：原典未核对/诗化口径/同构框架/年代/词源/正名约定/概说 7 项挂牌。"""
    nv = d.needs_verify()
    assert len(nv) == 7
    # datong 口径：status 为分类标签（未核对原典/年代分歧/词源争议/…），note 为说明
    for v in nv:
        assert v.get("item") and v.get("note") and v.get("status")
    items = "；".join(v["item"] for v in nv)
    assert "神恩如狱" in items and "元阳元阴" in items
    assert any("shaman" in v["item"] or "词源" in v["item"] for v in nv)
    assert any("未核对原典" == v["status"] for v in nv)


def test_build_check_and_report():
    """构建脚本 --check 防漂移（用户端事实与源码实测漂移即失败）。"""
    r = subprocess.run([sys.executable, str(BUILD), "--check"],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "校验通过" in r.stdout
    r2 = subprocess.run([sys.executable, str(BUILD), "--report"],
                        capture_output=True, text=True, timeout=120)
    assert r2.returncode == 0
    for sysname in ("daoxue", "apilab", "netsys", "comp", "plang", "quantum",
                    "zhuangzi", "baigong"):
        assert sysname in r2.stdout
