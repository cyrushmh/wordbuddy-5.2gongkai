"""RFC 全量标准目录（rfc_catalog）最小冒烟验证。

覆盖：数据层完整性（10,036 条，含 188 个 Not Issued）、单条查询归一化、
未分配编号诚实返回 None、检索、按状态过滤、任务反向引用（按 RFC 聚合）、
纯文本速览（适老化/无障碍口径）。
v2 增补：关系视图（obsoletes/obsoleted-by/updates/updated-by）、废止链
现行版本、STD/BCP/FYI 系列索引、任务引用三分审计（悬空/过期/说明性提及）。
v3 增补：主题域索引（heuristic）消费层 + 构建脚本 --check 对账。
v4 增补：官方 WG/RG 归属层（第二索引源，rfc-index.xml + datatracker 名录）
消费层 + 构建脚本 --check 对账。
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "src/python")

from sysweeper.native import rfc_catalog as cat  # noqa: E402


def test_catalog_size_complete():
    size = cat.catalog_size()
    assert size["total"] >= 10000, "RFC INDEX 全量应 >= 10000 条"
    assert size["issued"] > 9000
    assert size["not_issued"] >= 100, "Not Issued 条目必须如实保留"
    assert "source" in size and "rfc-editor.org" in size["source"]


def test_rfc_info_normalization():
    for probe in (9846, "9846", "rfc09846", "RFC 9846"):
        e = cat.rfc_info(probe)
        assert e is not None, probe
        assert e["n"] == 9846
        assert "TLS" in e["t"]
    # 未发布编号：诚实存在但 issued=False
    e14 = cat.rfc_info(14)
    assert e14 is not None and e14["i"] is False
    # 未分配编号：绝不存在（KeyError 语义由 None 表达，不臆造）
    assert cat.rfc_info(10544) is None
    assert cat.rfc_info("abc") is None
    assert cat.rfc_info(None) is None


def test_search_and_status():
    hits = cat.search("TLS")
    assert hits and hits[0]["n"] >= 1
    assert all("tls" in (h.get("t") or "").lower()
               or "tls" in (h.get("a") or "").lower() for h in hits)
    assert cat.search("") == []
    stds = cat.by_status("INTERNET STANDARD", 5)
    assert stds and all(s["s"] == "INTERNET STANDARD" for s in stds)
    assert cat.latest(3)[0]["n"] >= 10000, "最新条目应为最新编号"


def test_citing_tasks_reverse_index():
    cites = cat.citing_tasks()
    assert "rfc09846" in cites
    assert "tls13_posture_audit" in cites["rfc09846"]
    ids = cat.citing_tasks_for("rfc08996")
    assert "tls13_posture_audit" in ids
    # 未被引用的 RFC 返回空列表而非 None（诚实表达「没被引用」）
    assert cat.citing_tasks_for(20) == []


def test_summary_plain_text():
    lines = cat.summary()
    assert isinstance(lines, list) and lines
    joined = "\n".join(lines)
    assert "RFC" in joined and "只读" in joined  # 适老化口吻
    assert "rfc show" in joined  # CLI 路径提示


# ---------------------------------------------------------------
# v2：关系 / 现行版 / 系列 / 引用审计
# ---------------------------------------------------------------

def test_relations_view():
    rel = cat.rfc_relations(8415)
    assert rel is not None
    assert rel["n"] == 8415
    obss = rel.get("obsoletes") or []
    assert 3315 in [it["n"] for it in obss]
    assert all(it["resolved"] for it in obss), "目录内指向都应解析出标题"
    obys = rel.get("obsoleted_by") or []
    assert len(obys) == 1 and obys[0]["n"] == 9915 and obys[0]["resolved"]
    # 编号不在目录：如实 None，不臆造
    assert cat.rfc_relations(10544) is None
    # 无任何关系的 RFC：返回视图但四个关系键均缺席
    bare = cat.rfc_relations(1149)
    assert bare is not None and "obsoletes" not in bare


def test_current_version_chain():
    cur = cat.rfc_current(8415)
    assert cur["status"] == "OK" and cur["current"] == 9915
    assert cur["chain"] == [8415, 9915]
    # 链上每一步都带现行标题
    assert "DHCPv6" in (cur.get("current_title") or "")
    # 自身即现行：current == input
    self_cur = cat.rfc_current(9915)
    assert self_cur["status"] == "OK" and self_cur["current"] == 9915
    # 未分配编号：诚实状态
    assert cat.rfc_current(10544)["status"] == "NOT_IN_CATALOG"
    # 非法输入不炸
    assert cat.rfc_current("abc")["status"] == "NOT_IN_CATALOG"


def test_series_index_and_members():
    idx = cat.series_index()
    assert "STD13" in idx and idx["STD13"] == [1034, 1035]
    assert "STD102" in idx and idx["STD102"] == [9915]
    assert "BCP47" in idx and 4647 in idx["BCP47"]
    members = cat.series_members("STD 13")  # 归一化：空格/大小写
    assert [m["n"] for m in members] == [1034, 1035]
    assert cat.series_members("STD999") == []  # 不存在系列：空列表
    assert cat.series_members("junk") == []


def test_citation_audit_classification():
    audit = cat.citation_audit()
    assert audit["cited_total"] >= 40
    assert audit["resolved"] == audit["cited_total"]
    assert audit["dangling_count"] == 0, "任务引用不得悬空"
    # 修复后无「真过期引用」；4941/7231/8446 的共现属说明性提及
    assert audit["obsolete_cited_count"] == 0
    assert set(audit["obsolete_mention"]) == {
        "rfc04941", "rfc07231", "rfc08446"}
    stats = cat.relations_stats()
    assert stats["coverage"]["obsoletes"] >= 1000
    assert stats["coverage"]["also"] == 449


# ---------------------------------------------------------------
# v3：主题域索引（heuristic，消费层）
# ---------------------------------------------------------------

def test_topic_stats_consistency():
    stats = cat.topic_stats()
    assert stats["domain_count"] == 13
    assert stats["rule_count"] >= 80
    assert stats["classified"] + stats["unclassified"] == \
        cat.catalog_size()["issued"], "classified+unclassified 必须闭合"
    assert 0 < stats["coverage"] < 1, "heuristic 不应宣称 100% 覆盖"
    assert "heuristic" in (stats.get("method") or "")


def test_topics_overview_sorted():
    rows = cat.topics()
    assert len(rows) == 13
    counts = [r["count"] for r in rows]
    assert counts == sorted(counts, reverse=True)
    by_domain = {r["domain"]: r for r in rows}
    assert by_domain["tls-pki"]["label"]
    assert by_domain["dns"]["rule_count"] >= 3


def test_topic_members_and_lookup():
    dns = cat.topic_members("dns", limit=10)
    assert dns and all(e["n"] >= 1 for e in dns)
    nums = [e["n"] for e in dns]
    assert nums == sorted(nums)
    for e in dns:
        assert "dns" in cat.topic_of(e["n"])["domains"]
    assert cat.topic_members("no-such-domain") == []
    # limit 截断与 0 边界
    assert len(cat.topic_members("dns", limit=3)) <= 3
    assert cat.topic_members("dns", limit=0) == []


def test_topic_of_traceability():
    tp = cat.topic_of(9846)
    assert tp["classified"] is True
    assert "tls-pki" in tp["domains"]
    assert "tls" in tp["rules"], "命中规则 id 必须留痕"
    # 9846 同时归 tls-pki 与 security 类规则时 domains 唯一（去重）
    assert len(tp["domains"]) == len(set(tp["domains"]))
    # 未命中任何规则：诚实空归属，不臆造
    bare = cat.topic_of(20)
    assert bare == {"n": 20, "classified": False, "domains": [], "rules": []}
    assert cat.topic_of("abc")["classified"] is False


def test_topic_index_build_check_mode():
    # 构建脚本 --check 对账（防篡改断言全绿才放行）
    # 仓库根 parents[3]：tests/ -> system-optimizer/ -> windows-internals-toolkit/
    # -> 仓库根（research/ 所在层）
    script = (Path(__file__).resolve().parents[3] / "research" / "rfc"
              / "build_rfc_topic_index.py")
    assert script.exists(), "构建脚本应随仓库提交（可复现流水线）"
    r = subprocess.run([sys.executable, str(script), "--check"],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "[OK]" in r.stdout


def test_wg_index_build_check_mode():
    # 官方 WG 索引构建脚本 --check 对账（名单/area 映射/归属闭合）
    script = (Path(__file__).resolve().parents[3] / "research" / "rfc"
              / "build_rfc_wg_index.py")
    assert script.exists(), "WG 构建脚本应随仓库提交（可复现流水线）"
    r = subprocess.run([sys.executable, str(script), "--check"],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "[OK]" in r.stdout


# v4：官方 WG/RG 归属层（第二索引源，消费层）
# ---------------------------------------------------------------

def test_wg_stats_consistency():
    st = cat.wg_stats()
    assert st["wg_count"] >= 500, "datatracker 全量 WG/RG 名录应 >= 500"
    assert st["wg_covered"] > 5000
    assert 0 < st["wg_coverage"] < 1, "WG 层不应覆盖全部（heuristic 兜底独立投稿）"
    assert st["area_count"] >= 10
    assert "wg" in st["kind_counts"] and st["kind_counts"]["wg"] >= 500
    rc = st["reconciliation"]
    assert 0 < rc["modal_agreement_rate"] < 1, "两层模态一致率应在合理区间"
    assert rc["modal_agreement"] <= rc["both_classified"]


def test_wgs_overview_sorted():
    ov = cat.wgs(limit=0)
    areas = ov["areas"]
    assert areas and all(a["rfc_count"] for a in areas)
    counts = [a["rfc_count"] for a in areas]
    assert counts == sorted(counts, reverse=True), "area 按 RFC 数降序"
    top = cat.wgs(limit=15)["top_wgs"]
    assert len(top) == 15
    tcounts = [g["count"] for g in top]
    assert tcounts == sorted(tcounts, reverse=True), "top_wgs 按 RFC 数降序"


def test_wg_members_and_lookup():
    tls = cat.wg_members("tls", limit=10)
    assert tls and all(e["n"] >= 1 for e in tls)
    nums = [e["n"] for e in tls]
    assert nums == sorted(nums), "成员按编号升序"
    # 大 limit 取全量校验标杆 RFC 归属（8446 较晚，需放开 limit）
    tls_all = cat.wg_members("tls", limit=200)
    assert 8446 in [e["n"] for e in tls_all], "RFC 8446 (TLS 1.3) 应归 tls WG"
    # area 代码（datatracker acronym）按 RFC 数聚合
    sec = cat.wg_members("sec", limit=5)
    assert sec and len(sec) <= 5
    assert cat.wg_members("no-such-wg") == []
    assert cat.wg_members("") == []


def test_wg_of_traceability():
    w = cat.wg_of(8446)
    assert w["wg"] == "tls"
    assert w["area"] == "sec"
    assert w["kind"] == "wg"
    assert w["wg_name"]
    # 独立投稿 / 早期 Legacy：诚实返回归属为空，不臆造
    bare = cat.wg_of(1)
    assert bare["kind"] in (None, "legacy", "independent")
    assert cat.wg_of("abc")["kind"] is None
