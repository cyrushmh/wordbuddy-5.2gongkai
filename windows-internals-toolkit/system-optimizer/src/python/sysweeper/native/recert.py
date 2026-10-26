"""WCET 续证 PDU 计分方案（只读消费层）。

数据来自 data/recert_docs.json——由用户投递的两个 .xls 续证跟踪表
（三年周期 FINAL / 五年周期 Dec2016）解析出的 PDU 计分规则知识层。
本模块只读不联网，供 CLI `recert` 与 GUI 查询、对账使用。

WCET（Wireless Communications Engineering Technologies）认证项目已于 2019 年停办，
本知识库仅供继续教育 / PDU 跟踪方法论参考，不复制表内个人隐私字段。
"""

from typing import Dict, List, Optional

from importlib import resources

_DATA_FILE = "recert_docs.json"
_DATA: Optional[dict] = None


def _load() -> dict:
    """惰性加载 data/recert_docs.json（构建产物 / 知识层）。"""
    global _DATA
    if _DATA is None:
        try:
            data = resources.files("sysweeper.data").joinpath(
                _DATA_FILE).read_text(encoding="utf-8")
            _DATA = __import__("json").loads(data)
        except Exception:
            _DATA = {}
    return _DATA


def info() -> dict:
    """证书与来源元信息（诚实声明 program_status）。"""
    d = _load()
    return {
        "title": d.get("_meta", {}).get("title"),
        "certification": d.get("_meta", {}).get("certification"),
        "certification_zh": d.get("_meta", {}).get("certification_zh"),
        "author": d.get("_meta", {}).get("author"),
        "program_status": d.get("_meta", {}).get("program_status"),
        "source_files": d.get("_meta", {}).get("source_files", []),
        "method": d.get("_meta", {}).get("method"),
    }


def cycles() -> Dict[str, dict]:
    """两个续证周期的下限与跨度要求。"""
    d = _load()
    return d.get("requirements", {}).get("cycles", {})


def technical_areas() -> List[str]:
    """七大技术知识领域（第 7 类标注待核实，不臆造）。"""
    d = _load()
    return d.get("technical_areas", {}).get("areas", [])


def categories() -> List[dict]:
    """全部活动分类（含计分规则与双周期封顶）。"""
    d = _load()
    return d.get("activity_categories", [])


def category(key: str) -> Optional[dict]:
    """按 key 查单类（work/volunteering/teaching/...）。"""
    if not key:
        return None
    q = key.strip().lower()
    for c in categories():
        if c.get("key") == q or c.get("sheet", "").strip().lower() == q:
            return c
    return None


def requirements() -> dict:
    """全局续证门槛（≥60/100 PDU、≥3 年、≥3 领域、0.25h 计量）。"""
    d = _load()
    return d.get("requirements", {})


def validation_rules() -> List[str]:
    """续证合规校验清单（只报告，不改写用户数据）。"""
    d = _load()
    return d.get("validation_rules", [])


def summary() -> List[str]:
    """纯文本速览（适老化 / 无障碍口径，一行一事实）。"""
    d = _load()
    return d.get("summary_lines", [])


def max_attainable(cycle: str = "3year") -> Dict[str, int]:
    """各活动分类在指定周期的理论封顶（cycle_cap），用于对账。

    返回 {key: cycle_cap}；不计入需固定额度的专业工作/会员升级
    （其 cycle_cap 已含在数据中）。仅供合规提示，非建议刷分。
    """
    out = {}
    for c in categories():
        cap = (c.get("cycle_cap") or {}).get(cycle)
        if cap is not None:
            out[c["key"]] = cap
    return out
