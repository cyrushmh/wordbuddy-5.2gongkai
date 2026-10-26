# -*- coding: utf-8 -*-
"""WebTrust for CAs 审计图谱（只读消费层）
==========================================
数据来源：data/ca_audit_standards.json —— 由 research/caaudit/
build_ca_audit_standards.py 从用户投递的《GoDaddy - 2026 WebTrust for CAs -
Report.pdf》（Starfield Technologies, LLC，GoDaddy 子公司）事实底稿可复现生成。

收录内容（全部带 source 页码，无出处不录入）：
  - 35 个 CA：12 个根 CA / 8 个交叉签名 CA / 15 个签发 CA（SHA-256 指纹）；
  - 4 项 Mozilla Bugzilla 事项及其标准条款映射（RFC 5280 / BR / CCADB）；
  - 1 项附事项（WebTrust v2.2.2 Control 6.5 公开仓库披露）；
  - 6 份 CP/CPS 文档谱系、7 组控制域、服务清单、排除项、12 个地点。

纪律（与 rfc_catalog / xiuzhen_catalog 两轮同口径）：
  - 本模块只读，绝不联网、绝不补造；拼写/大小写/连接符如实保留原文
    （如 en dash "–"、MPIC 地点原文拼写 "Sount"）；
  - 根指针在构建期已断言非悬空；指纹全库唯一（64 位十六进制）；
  - 标准引用可反查 rfc_catalog（RFC 5280），实现跨库交叉验证。

用法示例：
    from sysweeper.native import ca_audit as ca
    ca.summary()                      # 规模与分组的纯文本速览
    ca.ca_info("道德")                  # 查无返回 None（不臆造）
    ca.ca_info("root:godaddy-class-2")
    ca.children("root:starfield-tls-root-ca-r1")   # 根下的 cross+issuing
    ca.matters()                      # 4 项事项（含条款映射与整改）
    ca.rfc_ref(5280)                  # 反查 rfc_catalog 得 RFC 5280 元数据
"""
import json
import re
from typing import Dict, List, Optional

_DATA_FILE = "ca_audit_standards.json"
_INDEX: Optional[dict] = None
_BY_ID: Optional[Dict[str, dict]] = None

KIND_NAMES = {
    "root": "根 CA",
    "cross": "交叉签名 CA",
    "issuing": "签发 CA",
}

STATUS_NAMES = {
    "Closed": "已关闭",
    "Open": "仍开放",
}

VERDICT_NAMES = {
    "controls_sufficiently_addressed": "Schellman 测试认为已充分解决根因",
    "pending_implementation": "Schellman 认为若正确实施并有效运行可解决根因（报告期末尚在实施）",
}

_FP_RE = re.compile(r"^[0-9A-Fa-f]{8,64}$")


def _index() -> dict:
    """惰性加载知识库（避免 import 期解析 JSON）。"""
    global _INDEX
    if _INDEX is None:
        try:
            from importlib import resources
            data = resources.files("sysweeper.data").joinpath(
                _DATA_FILE).read_text(encoding="utf-8")
            _INDEX = json.loads(data)
        except Exception:
            _INDEX = {"meta": {}, "cas": [], "matters": [],
                      "additional_matters": [], "standards_refs": [],
                      "locations": [], "control_domains": [],
                      "cpcps_documents": [], "services": [], "exclusions": []}
    return _INDEX


def _by_id() -> Dict[str, dict]:
    global _BY_ID
    if _BY_ID is None:
        _BY_ID = {c["id"]: c for c in _index().get("cas", [])}
    return _BY_ID


def _ca_id_of(probe) -> Optional[str]:
    """归一化入口：精确 id > 名称精确 > 名称前缀（名称长的优先，防 G2/G5/G6 误配）
    > 指纹前缀（≥8 位十六进制）。查无返回 None（不臆造）。"""
    if probe is None:
        return None
    s = str(probe).strip()
    if not s:
        return None
    table = _by_id()
    if s in table:
        return s
    cands: List[tuple] = []
    for cid, c in table.items():
        if s in (c.get("name"), c.get("subject_cn")):
            is_exact = 1
        elif c.get("name", "").startswith(s) or c.get("subject_cn", "").startswith(s):
            is_exact = 0
        else:
            continue
        cands.append((1 - is_exact, -len(c.get("name", "")), len(cid), cid))
    if cands:
        cands.sort()
        return cands[0][3]
    if _FP_RE.match(s):
        low = s.lower()
        hits = [cid for cid, c in table.items()
                if c["fingerprint"].lower().startswith(low)]
        if len(hits) == 1:
            return hits[0]
        if hits:  # 多命中取最短 id（仍可解释），宁缺毋滥不外推
            return sorted(hits, key=len)[0]
    return None


def ca_info(probe) -> Optional[dict]:
    """单个 CA 记录（id/kind/name/fingerprint/root_id/source_page）。"""
    cid = _ca_id_of(probe)
    if cid is None:
        return None
    return _by_id().get(cid)


def display_name(ca: Optional[dict]) -> str:
    """CA 显示名（CLI/GUI 用；缺 name 时退回 id）。"""
    if not ca:
        return "?"
    return ca.get("name") or ca.get("id") or "?"


def children(probe) -> List[dict]:
    """某根 CA 下的交叉签名与签发 CA（root_id 指向它；查无返回空列表）。"""
    cid = _ca_id_of(probe)
    if cid is None:
        return []
    return [c for c in _index().get("cas", []) if c.get("root_id") == cid]


def cas_by_kind(kind: str) -> List[dict]:
    return [c for c in _index().get("cas", []) if c.get("kind") == kind]


def search(term: str, limit: int = 20) -> List[dict]:
    """按名称/id/指纹前缀检索（大小写不敏感；id 或指纹精确命中优先）。"""
    t = (term or "").strip()
    if not t:
        return []
    table = _by_id()
    exact = table.get(t)
    if exact:
        return [exact]
    low = t.lower()
    starts: List[dict] = []
    contains: List[dict] = []
    fp_hits: List[dict] = []
    for c in table.values():
        name = c.get("name", "")
        cid = c["id"].lower()
        if name.lower().startswith(low):
            starts.append(c)
        elif low in name.lower() or low in cid:
            contains.append(c)
        if c["fingerprint"].lower().startswith(low):
            fp_hits.append(c)
    out = starts + contains
    for c in fp_hits:  # 指纹命中去重后补后
        if c not in out:
            out.append(c)
    return out[:limit]


def matters() -> List[dict]:
    return list(_index().get("matters", []))


def matter_by_bug(bug_id) -> Optional[dict]:
    s = str(bug_id or "").strip()
    for m in _index().get("matters", []):
        if str(m.get("bug_id")) == s:
            return m
    return None


def standards_refs() -> List[dict]:
    return list(_index().get("standards_refs", []))


def rfc_ref(number) -> Optional[dict]:
    """反查 rfc_catalog（跨库交叉验证；数据缺失/编号未分配返回 None）。"""
    try:
        from . import rfc_catalog
        return rfc_catalog.rfc_info(number)
    except Exception:
        return None


def locations() -> List[dict]:
    return list(_index().get("locations", []))


def summary() -> List[str]:
    """纯文本速览（一行一事实，读屏可朗读）。"""
    idx = _index()
    meta = idx.get("meta", {})
    counts = meta.get("counts", {})
    report = meta.get("report", {})
    lines: List[str] = []
    lines.append("==== WebTrust for CAs 审计图谱（只读） ====")
    lines.append("标的：%s" % report.get("subject", "未知"))
    lines.append("审计机构：%s（%s）" % (report.get("auditor", "未知"),
                                     report.get("auditor_location", "")))
    lines.append("报告日：%s；覆盖期：%s 至 %s；准则：%s" % (
        report.get("report_date", "?"),
        report.get("period", {}).get("start", "?"),
        report.get("period", {}).get("end", "?"),
        report.get("criteria", "?")))
    lines.append("结论：%s" % report.get("opinion", "未知"))
    lines.append("")
    lines.append("规模：%d 个 CA（根 %d / 交叉签名 %d / 签发 %d）+ %d 个地点 + %d 项事项" % (
        counts.get("total_cas", 0), counts.get("root_cas", 0),
        counts.get("cross_signed_cas", 0), counts.get("issuing_cas", 0),
        counts.get("locations", 0), counts.get("matters", 0)))
    lines.append("")
    lines.append("CA 分布：")
    for kind, name in KIND_NAMES.items():
        lines.append("  %-12s %2d 个" % (name, counts.get("%s_cas" % kind if kind != "cross" else "cross_signed_cas", 0)))
    lines.append("")
    lines.append("事项（Bugzilla）：")
    for m in matters():
        refs = "；".join("%s %s" % (r["std"], r["clause"]) for r in m.get("refs", []))
        lines.append("  #%s %s（%s → %s，%s）" % (
            m.get("no"), m.get("topic"), m.get("opened"), m.get("closed") or "未关闭",
            STATUS_NAMES.get(m.get("status"), m.get("status"))))
        if refs:
            lines.append("      条款：%s" % refs)
    lines.append("")
    lines.append("反查示例：caudit matters；caudit show 'Starfield TLS Root CA – R1'；"
                 "caudit std rfc 5280")
    return lines


def map_data() -> dict:
    """完整知识库数据（GUI/测试用；调用方不得修改）。"""
    return _index()
