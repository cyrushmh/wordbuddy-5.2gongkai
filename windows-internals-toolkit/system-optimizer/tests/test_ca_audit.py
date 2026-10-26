"""WebTrust for CAs 审计图谱（ca_audit + CLI）最小冒烟验证。

覆盖：数据层完整性（35 CA=12 根+8 交叉+15 签发、指纹唯一 64-hex、root 指针
非悬空、记录带 source 页码）、CA 解析入口（en dash 名称/指纹前缀/前缀防误配/
查无返回 None）、下属 CA、事项与条款映射、RFC 5280 跨库反查、CLI 子命令。
"""

import re
import subprocess
import sys

sys.path.insert(0, "src/python")

from sysweeper.native import ca_audit as ca  # noqa: E402


def test_data_completeness():
    data = ca.map_data()
    cas = data["cas"]
    counts = data["meta"]["counts"]
    assert counts == {
        "root_cas": 12, "cross_signed_cas": 8, "issuing_cas": 15,
        "total_cas": 35, "locations": 12, "matters": 4,
        "cpcps_documents": 6, "control_domain_groups": 7,
    }, counts
    assert len(cas) == 35
    # 纪律：指纹唯一且 64 位大写十六进制
    fps = [c["fingerprint"] for c in cas]
    assert len(set(fps)) == 35, "指纹重复"
    assert all(re.fullmatch(r"[0-9A-F]{64}", f) for f in fps)
    # 纪律：每条 CA 带 source 页码；root 指针非悬空
    assert all(c.get("source_page") for c in cas)
    ids = {c["id"] for c in cas}
    assert len(ids) == 35, "id 重复"
    root_ids = {c["id"] for c in cas if c["kind"] == "root"}
    assert all(c["root_id"] in root_ids for c in cas if c["kind"] != "root"), \
        "cross/issuing 存在悬空 root 指针"
    # 地点与事项计数
    assert len(ca.locations()) == 12
    assert len(ca.matters()) == 4


def test_ca_resolution():
    # en dash 名称（报告中 TLS Root 用 – U+2013）
    c = ca.ca_info("Starfield TLS Root CA – R1")
    assert c is not None and c["kind"] == "root"
    # 精确 id
    assert ca.ca_info("root:starfield-class-2-certification-authorit")["kind"] == "root"
    # 指纹前缀
    assert ca.ca_info("C3846BF24B9E93CA")["name"] == "Go Daddy Class 2 Certification Authority"
    # 前缀重名（G2/G5/G6）取最短 id（可解释选择），不能报错也不能外推
    amb = ca.ca_info("Starfield Root Certificate Authority - G")
    assert amb is not None and amb["id"].endswith("-g2")
    # 查无：None 而非臆造
    assert ca.ca_info("不存在的 CA") is None
    assert ca.ca_info("") is None
    assert ca.ca_info(None) is None
    assert ca.ca_info("ZZZZ") is None


def test_children():
    # Starfield G2 根：1 个交叉（TLS R1）+ 3 个签发 = 4
    kids = ca.children("Starfield Root Certificate Authority - G2")
    assert len(kids) == 4
    kinds = sorted(k["kind"] for k in kids)
    assert kinds == ["cross", "issuing", "issuing", "issuing"]
    assert all("Starfield" in k["name"] for k in kids)
    # 叶子 CA 无下属
    leaf = ca.ca_info("Starfield TLS Intermediate CA DV – R1v1")
    assert leaf is not None and ca.children(leaf["id"]) == []
    # 查无
    assert ca.children("不存在") == []


def test_matters_and_standard_refs():
    ms = ca.matters()
    assert [m["bug_id"] for m in ms] == ["2004845", "2002402", "2007216", "2007217"]
    # 事项 3 在报告期末仍开放（如实录入，不粉饰）
    m3 = ca.matter_by_bug("2007216")
    assert m3["status"] == "Open" and m3["closed"] is None
    assert m3["schellman_verdict"] == "pending_implementation"
    # 事项 1 的条款映射：RFC 5280 + BR
    m1 = ca.matter_by_bug("2004845")
    stds = {r["std"] for r in m1["refs"]}
    assert stds == {"RFC 5280", "CA/Browser Forum Baseline Requirements"}
    assert {r["clause"] for r in m1["refs"]} == {"§4.2.2.1", "§7.1.2.10.3"}
    # 事项 4 映射 BR §7.2.2.1（CRL 的 IDP 扩展）
    m4 = ca.matter_by_bug("2007217")
    assert m4["refs"][0]["clause"] == "§7.2.2.1"
    assert m4["status"] == "Closed" and m4["closed"] == "2026-04-17"
    # 查无
    assert ca.matter_by_bug("9999999") is None
    # 标准引用四条
    refs = {s["id"]: s for s in ca.standards_refs()}
    assert set(refs) == {"webtrust:v2.2.2", "rfc:5280",
                         "br:baseline-requirements", "ccadb:policy"}
    assert refs["rfc:5280"]["rfc_number"] == 5280


def test_rfc_cross_reference():
    # 跨库反查：知识库的 RFC 5280 标题与 rfc_catalog 一致（join 验证）
    ref = [s for s in ca.standards_refs() if s["id"] == "rfc:5280"][0]
    info = ca.rfc_ref(5280)
    assert info is not None
    assert info["t"] == ref["title"], "知识库标题与 RFC 目录不一致"
    assert info["n"] == 5280
    # 反查未分配编号返回 None（不臆造）
    assert ca.rfc_ref(99999) is None or ca.rfc_ref(99999) is None


def test_search_and_kinds():
    hits = ca.search("Starfield TLS")
    assert hits and all("TLS" in h["name"] or "tls" in h["id"] for h in hits)
    assert ca.search("") == []
    kinds = {k: len(ca.cas_by_kind(k)) for k in ("root", "cross", "issuing")}
    assert kinds == {"root": 12, "cross": 8, "issuing": 15}


def test_summary_plain_text():
    lines = ca.summary()
    assert isinstance(lines, list) and lines
    joined = "\n".join(lines)
    assert "35 个 CA" in joined
    assert "无保留意见" in joined
    assert "caudit" in joined  # CLI 路径提示
    assert "2026-07-27" in joined


def _run_cli(*argv):
    return subprocess.run(
        [sys.executable, "-m", "sysweeper", "caudit", *argv],
        capture_output=True, text=True, timeout=120,
        env={"PYTHONPATH": "src/python", "PATH": "/usr/bin:/bin"},
    )


def test_cli_actions():
    r = _run_cli()
    assert r.returncode == 0 and "35 个 CA" in r.stdout
    r = _run_cli("matters", "--bug", "2007216")
    assert r.returncode == 0 and "仍开放" in r.stdout and "CCADB" in r.stdout
    r = _run_cli("show", "Go Daddy Class 2 Certification Authority")
    assert r.returncode == 0 and "C3846BF24B9E93CA" in r.stdout
    r = _run_cli("show", "查无")
    assert r.returncode == 0 and "不在图谱中" in r.stdout, "查无必须诚实说明"
    r = _run_cli("children", "Starfield Root Certificate Authority - G2")
    assert r.returncode == 0 and "4 个" in r.stdout
    r = _run_cli("std")
    assert r.returncode == 0 and "RFC 5280" in r.stdout
    r = _run_cli("std", "rfc", "5280")
    assert r.returncode == 0 and "X.509" in r.stdout
    r = _run_cli("locations")
    assert r.returncode == 0 and "Tempe" in r.stdout and "Singapore" in r.stdout
    r = _run_cli("domains")
    assert r.returncode == 0 and "CA Key Generation" in r.stdout
    r = _run_cli("list", "--kind", "issuing")
    assert r.returncode == 0 and "DV" in r.stdout
