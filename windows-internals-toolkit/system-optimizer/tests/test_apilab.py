"""接口 API 概念系统测试（v0.6.64，CLI 子命令 `apilab`）。

覆盖三条硬性不变量：
  · 五轴完整 —— style/spec/transport/auth/repo-face 共 35 个概念，by_domain 自洽；
  · 桥接无悬空 —— 每条桥接的目标必须在 netsys / daoxue / plang 中真实存在；
  · RFC 交叉验证 —— 概念引用的每个 RFC 编号都能在 rfc_catalog 中反查到标题；
    repo-face 轴的条目以当前仓库实测事实登记（构建时从源码读出）。

另含构建脚本 `--check` 防漂移、CLI 冒烟与只读层 API。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "python"))

from sysweeper.concepts import apilab as ab  # noqa: E402
from sysweeper.native import rfc_catalog  # noqa: E402

BUILD = ROOT / "research" / "apilab" / "build_apilab.py"
TAX = ROOT / "src" / "python" / "sysweeper" / "data" / "concepts" / "apilab_taxonomy.json"


def test_domains_and_stats():
    """五轴 32 概念；统计自洽。"""
    doms = [d["domain"] for d in ab.domains()]
    assert doms == ["style", "spec", "transport", "auth", "repo-face"]
    s = ab.stats()
    assert s["concept_total"] == 36
    assert s["domain_count"] == 5
    assert s["bridge_count"] == 19
    assert s["standard_count"] == 13
    assert sum(d["count"] for d in ab.domains()) == s["concept_total"]


def test_concepts_integrity():
    """概念 id 唯一、gist/detail 非空。"""
    cs = ab.concepts()
    ids = [c["id"] for c in cs]
    assert len(ids) == len(set(ids)) == 36
    doms = {d["domain"] for d in ab.domains()}
    for c in cs:
        assert c["domain"] in doms
        assert c["gist"] and c["detail"] and c["name"]
    assert ab.of("rest")["domain"] == "style"
    assert ab.of("auth-oauth2")["domain"] == "auth"
    assert ab.of("repo-cli")["domain"] == "repo-face"
    assert ab.of("nonexistent") is None


def test_rfc_refs_verified():
    """每个 RFC 编号经 rfc_catalog 交叉验证，标题已回填。"""
    rfcs = [s for s in ab.standards() if s.get("kind") == "RFC"]
    assert len(rfcs) == 12
    nums = set()
    for s in rfcs:
        num = s.get("num")
        assert isinstance(num, int) and num not in nums
        nums.add(num)
        info = rfc_catalog.rfc_info(num)
        assert info is not None, f"RFC {num} 不在 rfc_catalog"
        title = info.get("t") or ""
        assert s.get("rfc_title"), f"RFC {num} 未回填标题"
        assert s["rfc_title"] == title[:120]
    assert {9110, 9112, 9113, 9114, 9293, 5280, 6455, 6749, 6750, 7519,
            7617, 9000} <= nums


def test_repo_face_facts_measured():
    """repo-face 数字为仓库实测（构建时从 argparse/webapi 读出）。"""
    f = ab.repo_facts()
    assert isinstance(f["cli_subcommands"], int) and f["cli_subcommands"] >= 1
    assert f["webapi_actions"] == 29
    for k in ("webapi_protocol", "plugins_api", "report_schema",
              "report_viewer_guard"):
        assert f.get(k)
    # 与真实源码交叉验证（口径与 build_apilab.repo_face_facts 一致）
    from sysweeper import webapi
    from sysweeper.cli import build_parser
    parser = build_parser()
    sub_count = 0
    for a in parser._actions:
        if a.__class__.__name__ == "_SubParsersAction":
            sub_count = len(a.choices)
    assert sub_count == f["cli_subcommands"], "CLI 子命令数与登记不一致（需重建）"
    assert len(webapi.ACTIONS) == f["webapi_actions"], "ACTIONS 数与登记不一致（需重建）"
    assert f["cli_subcommands"] >= 100, "CLI 子命令数异常偏少（需重建）"


def test_bridges_no_dangling():
    """桥接目标必须在 netsys / daoxue / plang 中真实存在（无悬空边）。"""
    ndoc = json.loads((ROOT / "src/python/sysweeper/data/concepts/netsys_taxonomy.json")
                      .read_text(encoding="utf-8"))
    ddoc = json.loads((ROOT / "src/python/sysweeper/data/concepts/daoxue_taxonomy.json")
                      .read_text(encoding="utf-8"))
    pdoc = json.loads((ROOT / "src/python/sysweeper/data/concepts/plang_taxonomy.json")
                      .read_text(encoding="utf-8"))
    mods = {m["id"] for m in ndoc["modules"]}
    pids = {p["id"] for p in ddoc["principles"]}
    lang_keys = set(pdoc["lang_index"])
    dtdoc = json.loads((ROOT / "src/python/sysweeper/data/concepts/datong_taxonomy.json")
                       .read_text(encoding="utf-8"))
    dids = {x["id"] for x in dtdoc.get("concepts", [])} | \
           {x["id"] for x in dtdoc.get("principles", [])}
    seen_sys = set()
    for b in ab.bridges():
        seen_sys.add(b["system"])
        sys_, tgt = b["system"], b["target"]
        if tgt.endswith(":*"):
            axis = tgt.split(":", 1)[0]
            assert axis in {"model", "arch", "domain", "layer", "nature", "form"}
            continue
        if sys_ == "netsys" and tgt.startswith("module:"):
            assert tgt.split(":", 1)[1] in mods, f"悬空桥接：{tgt}"
        elif sys_ == "daoxue" and tgt.startswith("principle:"):
            assert tgt.split(":", 1)[1] in pids, f"悬空桥接：{tgt}"
        elif sys_ == "daoxue" and tgt.startswith("guidance:"):
            assert tgt.split(":", 1)[1] == "zhengti_zhida", f"悬空桥接：{tgt}"
        elif sys_ == "plang" and tgt.startswith("lang:"):
            assert tgt.split(":", 1)[1] in lang_keys, f"悬空桥接：{tgt}"
        elif sys_ == "datong" and tgt.startswith(("concept:", "principle:")):
            assert tgt.split(":", 1)[1] in dids, f"悬空桥接：{tgt}"
        else:
            raise AssertionError(f"未处理的桥接目标: {sys_}:{tgt}")
    assert {"netsys", "daoxue", "plang"} <= seen_sys


def test_bridges_of_concept():
    """概念级桥接边与顶层 bridges 的 from 字段对齐。"""
    n_top = len(ab.bridges())
    n_from = sum(len(ab.bridges_of(c["id"])) for c in ab.concepts())
    assert n_top == n_from == 19


def test_search():
    """检索命中真实概念；空词返回空。"""
    assert ab.search("REST")
    assert ab.search("") == []


def test_auth_redline_registered():
    """认证红线条目在案（令牌禁入 URL/localStorage、短时效+服务端刷新）。"""
    c = ab.of("auth-redlines")
    assert c and c["domain"] == "auth"
    text = c["gist"] + c.get("detail", "")
    assert "URL" in text and "localStorage" in text


def test_build_check_no_drift():
    """构建脚本 --check 防漂移（含 rfc_catalog 回填与 repo-face 实测）。"""
    r = subprocess.run([sys.executable, str(BUILD), "--check"],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "无悬空" in r.stdout


def test_cli_smoke():
    """CLI 冒烟：overview / of / repo / rfc / verify / stats。"""
    def run(*a):
        return subprocess.run(
            [sys.executable, "-m", "sysweeper.cli", *a],
            capture_output=True, text=True, timeout=120, cwd=str(ROOT / "src" / "python"))
    r = run("apilab")
    assert r.returncode == 0, r.stderr
    assert "repo-face" in r.stdout and "诚实边界" in r.stdout
    r = run("apilab", "of", "repo-cli")
    assert r.returncode == 0 and "子命令" in r.stdout
    r = run("apilab", "repo")
    assert r.returncode == 0 and "webapi_actions" in r.stdout and "29" in r.stdout
    r = run("apilab", "rfc")
    assert r.returncode == 0 and "9110" in r.stdout and "HTTP Semantics" in r.stdout
    r = run("apilab", "search", "令牌")
    assert r.returncode == 0
