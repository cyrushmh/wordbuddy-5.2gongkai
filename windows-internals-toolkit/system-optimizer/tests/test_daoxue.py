"""「道枢」治理层概念系统测试（v0.6.59，CLI 子命令 `daoxue`）。

覆盖四层结构与三条硬性不变量：
  · 中心完整性 —— 《道德经》81 章连续 1..81，篇属与章号一致（1–37 道经 / 38–81 德经）；
  · 桥接无悬空 —— 每条桥接的目标必须在 plang / netsys / langref 等目标系统中真实存在；
  · 诚实边界 —— 未提供原典的《心经》《论语》与《道德经》古文原文必须登记 needs_verify。

另含构建脚本 --check 防漂移、CLI 冒烟，早晚坛课程序位覆盖，
方术子层（符/箓/咒/法/由/阵 六域 59 条）与阵域 protec 桥接（v0.6.59）。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "python"))

from sysweeper.concepts import daoxue as dx  # noqa: E402

BUILD = ROOT / "research" / "daoxue" / "build_daoxue.py"
TAX = ROOT / "src" / "python" / "sysweeper" / "data" / "concepts" / "daoxue_taxonomy.json"


def test_layers_and_stats():
    """五层：pre(早坛) / center(道德经) / middle(心经+论语) / post(晚坛) / fangshu(方术)。"""
    roles = [l["role"] for l in dx.layers()]
    assert roles == ["pre", "center", "middle", "post", "fangshu"]
    fs = [l for l in dx.layers() if l["role"] == "fangshu"][0]
    assert fs["tier"] == 3 and fs["count"] == 59  # 方术层 tier=3，59 条（含阵域 4 条）
    canon = {l["role"]: l["canon"] for l in dx.layers()}
    assert "早坛" in canon["pre"] and "晚坛" in canon["post"]
    assert canon["center"] == "道德经"
    assert "心经" in canon["middle"] and "论语" in canon["middle"]
    s = dx.stats()
    assert s["center_chapters"] == 81
    assert s["middle_canons"] == 2
    assert s["principle_count"] == 15
    assert s["pre_sections"] > 0 and s["post_sections"] > 0


def test_center_81_chapters():
    """道德经 81 章：章号连续、篇属正确、章旨与原则非空。"""
    chs = dx.chapters()
    assert [c["no"] for c in chs] == list(range(1, 82))
    for c in chs:
        assert c["part"] == ("道经" if c["no"] <= 37 else "德经")
        assert c["theme"] and c["gist"]
        assert c["principle"]
    assert dx.chapter(1)["theme"] == "道可道非常道"
    assert dx.chapter(25)["principle"] == "daofa-ziran"
    assert dx.chapter(81)["principle"] == "xin-yan-bu-mei"
    assert dx.chapter(0) is None and dx.chapter(82) is None


def test_principles_and_chapter_backref():
    """每条原则都有经典依据、义理与工程落法，且至少被一章引用。"""
    pids = {p["id"] for p in dx.principles()}
    assert len(pids) == len(dx.principles()) == 15
    for p in dx.principles():
        assert p["canon_refs"] and p["gist"] and p["engineering"]
    used = {c["principle"] for c in dx.chapters()}
    assert used == pids  # 15 条原则全部有章可溯，无空挂原则


def test_bridges_no_dangling():
    """桥接目标必须在目标系统中真实存在（无悬空边）。"""
    pdoc = json.loads((ROOT / "src/python/sysweeper/data/concepts/plang_taxonomy.json")
                      .read_text(encoding="utf-8"))
    ndoc = json.loads((ROOT / "src/python/sysweeper/data/concepts/netsys_taxonomy.json")
                      .read_text(encoding="utf-8"))
    mods = {m["id"] for m in ndoc["modules"]}
    seen_sys = set()
    for b in dx.bridges():
        seen_sys.add(b["system"])
        sys_, tgt = b["system"], b["target"]
        if tgt.endswith(":*"):   # 整轴引用（如 arch:*），轴名合法性由构建期校验
            assert tgt.split(":", 1)[0] in {"model", "arch", "domain", "layer", "nature"}
            continue
        if sys_ == "netsys" and tgt.startswith("module:"):
            assert tgt.split(":", 1)[1] in mods, f"悬空桥接：{tgt}"
        if sys_ == "plang" and tgt.startswith("model:"):
            assert tgt.split(":", 1)[1] in {m["model"] for m in pdoc["execution_models"]}
        assert b["how"] and b["relation"]
    # daoxue 治理 9 系统 + 方术阵域桥接新增 protec（v0.0.58 阵域，共 10 系统）
    assert {"plang", "netsys", "langref", "datong", "baigong", "quantum",
            "zhuangzi", "comp", "apilab", "protec"} == seen_sys
    # 每个受治理的系统都能查到落法
    for s in ("plang", "netsys", "langref"):
        assert dx.apply_to(s), f"{s} 无适用原则"


def test_offices_phase_coverage():
    """早晚坛：节次序号连续、课程序位齐备（净坛→诵经→礼诰→…→结行）。"""
    for role in ("pre", "post"):
        secs = dx.sections_of(role)
        assert [s["idx"] for s in secs] == list(range(1, len(secs) + 1))
        phases = [p["phase"] for p in dx.phases_of(role)]
        assert phases[0] == "净坛" and phases[-1] == "结行"
        assert "诵经" in phases and "礼诰" in phases
        assert all(s["kind"] and s["gist"] for s in secs)
    # 早坛主课（常清静经）与晚坛主课（救苦妙经）都在册
    assert any("常清静经" in s["name"] for s in dx.sections_of("pre"))
    assert any("救苦妙经" in s["name"] for s in dx.sections_of("post"))
    assert dx.sections_of("pre", "忏悔")


def test_middle_two_canons():
    """中间二级：心经（破相）5 段 + 论语（立礼）20 篇，均带工程落法。"""
    ms = dx.middle()
    assert [m["canon"] for m in ms] == ["般若波罗蜜多心经", "论语"]
    for m in ms:
        assert m["tier"] == 2 and m["role"] == "middle"
        assert len(m["sections"]) >= 5
        for s in m["sections"]:
            assert s["name"] and s["gist"] and s["engineering"]
    assert len(ms[1]["sections"]) == 20  # 论语二十篇


def test_needs_verify_registered():
    """未提供原典的条目必须标 needs_verify（诚实边界）。"""
    items = " ".join(v["item"] for v in dx.needs_verify())
    assert "心经" in items and "论语" in items and "道德经" in items
    assert all(m["needs_verify"] for m in dx.middle())


def test_search_cross_layer():
    hits = dx.search("水")
    assert hits and any("道德经" in h["where"] for h in hits)
    assert dx.search("") == []


def test_build_check_no_drift():
    doc = json.loads(TAX.read_text(encoding="utf-8"))
    cnt = doc["counts"]
    assert cnt["center_chapters"] == len(doc["center"]["chapters"]) == 81
    assert cnt["pre_sections"] == len(doc["pre"]["sections"])
    assert cnt["post_sections"] == len(doc["post"]["sections"])
    assert cnt["bridge_count"] == len(doc["bridges"])
    r = subprocess.run([sys.executable, str(BUILD), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_fangshu_layer():
    """方术子层（tier=3）：符/箓/咒/法/由/阵 六域，条目齐备、归属原则无悬空。"""
    fs = dx.fangshu()
    assert fs["tier"] == 3 and fs["role"] == "fangshu"
    doms = dx.fangshu_domains()
    assert [d["domain"] for d in doms] == ["fu", "lu", "zhou", "fa", "you", "zhen"]
    assert [d["count"] for d in doms] == [12, 9, 11, 10, 13, 4]

    items = dx.fangshu_items()
    assert len(items) == 59
    pids = {p["id"] for p in dx.principles()}
    for x in items:
        for k in ("id", "name", "gist", "detail", "engineering", "principle"):
            assert x.get(k), f"{x.get('id')} 缺字段 {k}"
        assert x["principle"] in pids, f"{x['id']} 归属原则未登记：{x['principle']}"
    ids = [x["id"] for x in items]
    assert len(ids) == len(set(ids))  # id 唯一

    # 祝由一支必须有诚实红线条目：明示不主张疗效、不作医疗建议
    you = dx.fangshu_domain("you")
    hx = dx.fangshu_item("you-hongxian")
    assert hx and hx["domain"] == "you"
    assert "不主张" in hx["gist"] and "医疗建议" in hx["gist"]
    assert hx in you["items"]

    # 存疑挂牌：民间口传与名目分歧项必须挂 needs_verify
    nv = [x for x in items if x.get("needs_verify")]
    assert len(nv) == 28
    assert dx.fangshu_item("you-shisanke")["needs_verify"]   # 民间十三科 ≠ 元代官制
    assert dx.fangshu_item("fu-dan")["needs_verify"]          # 符胆写法属口传
    assert dx.fangshu_item("zhen-zhoutian")["needs_verify"]   # 小说演绎非史实
    assert dx.fangshu_item("zhen-shierdutian")["needs_verify"]
    assert dx.fangshu_item("zhen-hetanluoshu")["needs_verify"]

    # 方术桥接：18 条，端点已登记、目标系统合法（v0.0.58 阵域 +5，protec 入集合）
    fbs = dx.fangshu_bridges()
    assert len(fbs) == 18
    for b in fbs:
        assert b["fangshu"] in set(ids)
        assert b["system"] in {"plang", "netsys", "langref", "protec"}
        assert b["how"] and b["relation"]

    # 检索可达 + stats 含方术计数
    assert any(h.get("id") == "fu-dan" for h in dx.search("符胆"))
    assert any(h.get("id") == "zhou-jjl" for h in dx.search("急急如律令"))
    s = dx.stats()
    assert s["fangshu_items"] == 59 and s["fangshu_bridge_count"] == 18
    assert s["fangshu_domains"] == 6 and s["fangshu_needs_verify"] == 28


def test_fangshu_search():
    """fangshu_search：空词全量、关键词过滤、大小写不敏感、域/字段命中。"""
    assert len(dx.fangshu_items()) == 59
    # 空词/纯空白返回全量
    assert len(dx.fangshu_search("")) == 59
    assert len(dx.fangshu_search("   ")) == 59
    # 精确命中单条
    hit = dx.fangshu_search("符胆")
    assert 1 <= len(hit) < 59 and "fu-dan" in [x["id"] for x in hit]
    # 大小写不敏感
    assert "fu-dan" in [x["id"] for x in dx.fangshu_search("FU-DAN")]
    # 主题词命中整支（祝由）
    you = dx.fangshu_search("祝由")
    assert len(you) >= 5 and all(x["domain"] == "you" for x in you)
    # 工程映射字段也能命中
    assert "fu-yunzhuan" in [x["id"] for x in dx.fangshu_search("云篆")]


def test_cli_daoxue_smoke():
    env = {"PYTHONPATH": str(ROOT / "src" / "python")}
    for args in (["daoxue"], ["daoxue", "center", "8"], ["daoxue", "pre"],
                 ["daoxue", "post"], ["daoxue", "middle"], ["daoxue", "fangshu"],
                 ["daoxue", "fangshu", "you"], ["daoxue", "fangshu", "fu-dan"],
                 ["daoxue", "principles", "wuwei"], ["daoxue", "apply", "netsys"],
                 ["daoxue", "verify"], ["daoxue", "stats"]):
        r = subprocess.run([sys.executable, "-m", "sysweeper", *args],
                           capture_output=True, text=True, env=env, cwd=str(ROOT))
        assert r.returncode == 0, f"{args} -> {r.stderr}"
        assert r.stdout.strip(), f"{args} 无输出"
