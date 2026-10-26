"""南华真经用户端概念系统测试（v0.6.60，CLI 子命令 `zhuangzi`）。

覆盖硬性不变量：
  · 四轴完整 —— core/inner/outer/ergonomics 共 20 个概念，by_domain 自洽；
  · 核心理念三篇在位（逍遥游 / 应帝王 / 大宗师），人体工程学七原则齐备；
  · 桥接无悬空 —— 每条桥接的目标必须在 daoxue 原则 / apilab 概念中真实存在；
  · 用户端面为实测 —— CLI 子命令 / GUI 窗口 / webapi ACTIONS / deno 双文件版本；
  · needs_verify 挂牌 —— 原典未核对必须显式挂牌（诚实边界）；
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

from sysweeper.concepts import zhuangzi as z  # noqa: E402

BUILD = ROOT / "research" / "zhuangzi" / "build_zhuangzi.py"
TAX = ROOT / "src" / "python" / "sysweeper" / "data" / "concepts" / "zhuangzi_taxonomy.json"


def test_domains_and_stats():
    """四轴 20 概念（12 篇目 + 8 原则）；统计自洽。"""
    doms = [d["domain"] for d in z.domains()]
    assert doms == ["core", "inner", "outer", "ergonomics"]
    s = z.stats()
    assert s["concepts"] == 20
    assert s["principles"] == 8
    assert s["bridges"] == 18   # v0.6.62 补 4 条确凿落地边 + v0.6.57+ datong 回边 2 条 + v0.6.67 整体指导桥 1 条
    assert s["by_domain"] == {"core": 3, "inner": 4, "outer": 5, "ergonomics": 8}


def test_core_three_chapters():
    """用户指定的核心理念三篇必须在 core 轴首位三席。"""
    core = [c["id"] for c in z.concepts_of_domain("core")]
    assert core[:3] == ["xiaoyaoyou", "yingdiwang", "dazongshi"]
    for cid in core:
        c = z.concept(cid)
        assert c["gist"] and c["detail"] and c["engineering"]
    # 三核心理念各有桥接（daoxue 原则）
    for cid in ("xiaoyaoyou", "yingdiwang", "dazongshi"):
        assert z.bridges_of(cid), f"{cid} 应有桥接"


def test_principles_integrity():
    """八条工程原则：id 唯一、经典依据在内篇七篇、落法非空。"""
    ps = z.principles()
    ids = [p["id"] for p in ps]
    assert len(ids) == len(set(ids)) == 8
    refs = {r for p in ps for r in p["canon_refs"]}
    assert refs == {"逍遥游", "应帝王", "大宗师", "齐物论", "养生主",
                    "人间世", "德充符"}
    for p in ps:
        assert p["gist"] and p["engineering"]
    assert z.principles_of_canon("逍遥游")[0]["id"] == "wudai-yizhi"
    assert z.principle("nonexistent") is None


def test_read_only_api():
    """只读层 API：concept/of/domain/search/bridges_of 均可达。"""
    assert z.concept("xiaoyaoyou")["name"] == "逍遥游"
    assert z.of("xiaoyaoyou")["domain"] == "core"
    assert z.domain("core")["concepts"][0]["id"] == "xiaoyaoyou"
    assert z.concept("nonexistent") is None
    assert any("庄子" in h["where"] or "南华" in h["where"]
               for h in z.search("庖丁"))
    assert z.bridges("daoxue") and all(b["system"] == "daoxue"
                                       for b in z.bridges("daoxue"))


def test_bridges_no_dangling():
    """桥接目标在 daoxue 原则 / apilab 概念 / datong / netsys 模块中真实存在（数据层反查）。"""
    doc = json.loads(TAX.read_text(encoding="utf-8"))
    dx = {p["id"] for p in doc and
          json.loads((TAX.parent / "daoxue_taxonomy.json").read_text(encoding="utf-8"))["principles"]}
    ab = {c["id"] for c in
          json.loads((TAX.parent / "apilab_taxonomy.json").read_text(encoding="utf-8"))["concepts"]}
    dtdoc = json.loads((TAX.parent / "datong_taxonomy.json").read_text(encoding="utf-8"))
    dt = {x["id"] for x in dtdoc.get("concepts", [])} | \
         {x["id"] for x in dtdoc.get("principles", [])}
    ndoc = json.loads((TAX.parent / "netsys_taxonomy.json").read_text(encoding="utf-8"))
    nmods = {m["id"] for m in ndoc["modules"]}
    for b in doc["bridges"]:
        kind, _, val = b["target"].partition(":")
        if b["system"] == "daoxue":
            assert (kind == "principle" and val in dx) or \
                   (kind == "guidance" and val == "zhengti_zhida"), f"悬空：{b['target']}"
        elif b["system"] == "datong":
            assert kind in ("concept", "principle") and val in dt, f"悬空：{b['target']}"
        elif b["system"] == "netsys":
            assert kind == "module" and val in nmods, f"悬空：{b['target']}"
        else:
            assert b["system"] == "apilab" and kind == "concept" and val in ab, \
                f"悬空：{b['target']}"


def test_user_face_facts_measured():
    """用户端面事实为实测正数/合法版本号（与 apilab 活测交叉一致）。"""
    f = z.user_face()
    for k in ("cli_subcommands", "webapi_actions", "gui_windows"):
        assert isinstance(f[k], int) and f[k] >= 1, k
    for k in ("deno_console_version", "deno_report_viewer_version"):
        assert re.fullmatch(r"\d{4}\.\d{4}\.\d{4}\.\d{4}\.\d{8}", str(f[k])), k  # 里程表式版本号
    # 与 argparse 实测的子命令数交叉一致（含 guide）
    from sysweeper import cli
    parser = cli.build_parser()
    sub = len([a for a in parser._actions
               if a.__class__.__name__ == "_SubParsersAction"][0].choices)
    assert f["cli_subcommands"] == sub >= 104
    from sysweeper import webapi
    assert f["webapi_actions"] == len(webapi.ACTIONS) >= 29


def test_needs_verify_posted():
    """诚实边界：原典未核对/未选登 26 篇/原则系工程翻译 全部挂牌。"""
    nv = z.needs_verify()
    assert len(nv) == 3
    assert all(v["status"] == "needs_verify" for v in nv)
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
    assert "daoxue" in r2.stdout and "apilab" in r2.stdout
