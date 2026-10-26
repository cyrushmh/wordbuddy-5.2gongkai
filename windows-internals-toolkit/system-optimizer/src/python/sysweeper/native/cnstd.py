# -*- coding: utf-8 -*-
"""国内标准资源知识库（cnstd）：官方平台 + 协议规范 + 第三方渠道 + 概念科普。

把 14 个国内标准资源链接（2026-10-25 逐只读抓取）整理成一份**知识库**：
官方源四平台（openstd 国标全文公开 / std.samr 公共服务总台 / hbba 行业标准 /
CCSA 通信协会）+ 协议规范两组（Modbus 六规范 / MQTT）+ 第三方渠道两家
（spc 商业付费 / biaozhuns 分享站，含版权警示）+ 概念科普三篇 + RFC 中文
翻译集合。全部条目经浏览器实测，编号/数量/日期以 2026-10-25 检索日为准；
JS 渲染未取到的内容统一挂 needs_verify，不臆造。

红线约束（与整个项目一致）：
- 本子系统**只读知识库 + 出索引**，不代查、不代下载、不破解任何付费/受限资源；
- 第三方『免费分享』渠道仅登记存在性与风险，不提供取用方法；
- 引用分层：官方源 > 厂商/社区规范转载 > 第三方渠道 > 科普文章层。

数据：data/cnstd_domestic_standards.json（14 源全量，含 openstd 两页 20 条
标准样本、hbba 8 条备案样本、Modbus 六规范、MQTT 协议要点）。
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional

_DATA_FILE = "cnstd_domestic_standards.json"
_REFS: Optional[dict] = None


def _load() -> dict:
    global _REFS
    if _REFS is None:
        try:
            from importlib import resources
            data = resources.files("sysweeper.data").joinpath(
                _DATA_FILE).read_text(encoding="utf-8")
            _REFS = json.loads(data)
        except Exception:  # noqa: BLE001
            _REFS = {}
    return _REFS


def _entries() -> Dict[str, dict]:
    """知识条目（剔除 _meta）。"""
    return {k: v for k, v in _load().items() if not k.startswith("_")}


def meta() -> dict:
    """知识库元信息（版本/核实日期/来源计数/红线/分层）。"""
    return _load().get("_meta", {})


def entry(key: str) -> dict:
    """单条知识（含 protocols/interfaces/docs/summary/advice/needs_verify）。"""
    return _entries().get(key, {})


def keys() -> List[str]:
    """全部知识条目 key（稳定序：官方平台 → 协议规范 → 第三方 → 概念）。"""
    return list(_entries().keys())


def search(term: str) -> List[dict]:
    """关键词检索（名称/机构/要点/建议/标准号，大小写不敏感）。"""
    t = (term or "").strip().lower()
    if not t:
        return []
    hits = []
    for key, e in _entries().items():
        blob = " ".join([
            key, e.get("name", ""), e.get("org", ""), e.get("url", ""),
            e.get("summary", ""), e.get("advice", ""),
            " ".join(e.get("protocols", [])),
            " ".join(e.get("interfaces", [])),
            " ".join(e.get("docs", [])),
            " ".join(e.get("needs_verify", [])),
            json.dumps(e.get("samples", []), ensure_ascii=False),
            json.dumps(e.get("samples_mandatory", []), ensure_ascii=False),
            json.dumps(e.get("samples_recommended", []), ensure_ascii=False),
        ]).lower()
        if t in blob:
            hits.append({"key": key, "name": e.get("name", ""),
                         "url": e.get("url", ""),
                         "summary": e.get("summary", "")})
    return hits


def official_platforms() -> List[dict]:
    """官方源条目（权威层：openstd/std.samr/hbba/ccsa/htsfwb）。"""
    official = {"openstd_platform", "std_samr_platform", "hbba_platform",
                "ccsa_platform", "htsfwb_platform"}
    return [{"key": k, "name": v.get("name", ""), "url": v.get("url", "")}
            for k, v in _entries().items() if k in official]


def protocol_specs() -> List[dict]:
    """协议规范条目（Modbus 六规范 / MQTT）。"""
    specs = {"modbus_specs", "mqtt_protocol"}
    return [{"key": k, "name": v.get("name", ""), "url": v.get("url", "")}
            for k, v in _entries().items() if k in specs]


def third_party() -> List[dict]:
    """第三方渠道条目（商业付费 / 分享站 / 翻译集合，版权风险面）。"""
    tp = {"spc_platform", "biaozhuns_platform", "rfc_cn_translations"}
    return [{"key": k, "name": v.get("name", ""), "url": v.get("url", "")}
            for k, v in _entries().items() if k in tp]


def concept_layer() -> List[dict]:
    """概念科普条目（标准 vs 协议、专有 vs 开放）。"""
    return [{"key": k, "name": v.get("name", ""), "url": v.get("url", "")}
            for k, v in _entries().items() if k == "open_standards_articles"]


def standards_count() -> dict:
    """收录规模统计（官方源实测数字 + 条目数）。"""
    openstd = entry("openstd_platform")
    std = entry("std_samr_platform")
    return {
        "gb_mandatory": 6188,      # openstd 强标总数（实测）
        "gb_recommended": 61615,   # openstd 推标总数（实测）
        "industry": 88751,         # std.samr 行业标准总数（实测）
        "industry_fields": 76,      # 行业个数（实测）
        "local": 49114,            # 地方标准总数（实测）
        "openstd_samples": len(openstd.get("samples_mandatory", []))
        + len(openstd.get("samples_recommended", [])),
        "hbba_samples": len(entry("hbba_platform").get("samples", [])),
        "modbus_specs": 6,
        "sources": meta().get("sources_total", 0),
        "entries": len(_entries()),
    }


def needs_verify_items() -> List[dict]:
    """全部 needs_verify 挂牌（JS 渲染未取到 / 主体不明的内容）。"""
    out = []
    for key, e in _entries().items():
        for item in e.get("needs_verify", []):
            out.append({"key": key, "name": e.get("name", ""), "item": item})
    return out


def cnstd_doc_list() -> list:
    """国内标准资源清单（供 CLI/GUI 展示），逐条回链知识库。"""
    lines = []
    for key, e in _entries().items():
        lines.append(f"· [{key}] {e.get('name', '')}")
        lines.append(f"    机构: {e.get('org', '')}")
        lines.append(f"    链接: {e.get('url', '')}")
        for p in e.get("protocols", [])[:3]:
            lines.append(f"    要点: {p}")
        if e.get("needs_verify"):
            lines.append(f"    needs_verify: {len(e['needs_verify'])} 项")
        lines.append(f"    建议: {e.get('advice', '')}")
    return lines


def cnstd_report() -> tuple:
    """国内标准资源总览报告（只读知识库，不联网、不扫描任何文件）。

    返回 ``(ok, msg)``：ok 恒 True（知识库就绪即通过，无系统依赖）；
    msg 为多行总览（规模统计 + 分层清单 + needs_verify 计数）。
    """
    c = standards_count()
    lines = [
        "国内标准资源知识库（cnstd）——14 源全量导入（2026-10-25 实测）",
        f"  规模: 强标 {c['gb_mandatory']} 条 / 推标 {c['gb_recommended']} 条 / "
        f"行标 {c['industry']} 条（{c['industry_fields']} 行业）/ 地标 {c['local']} 条",
        f"  样本: openstd {c['openstd_samples']} 条 + hbba {c['hbba_samples']} 条"
        f" + Modbus {c['modbus_specs']} 规范",
        f"  条目: {c['entries']} 个知识域（官方 {len(official_platforms())} / "
        f"协议 {len(protocol_specs())} / 第三方 {len(third_party())} / "
        f"概念 {len(concept_layer())}）",
        "",
        "  官方源（权威）:",
    ]
    for p in official_platforms():
        lines.append(f"    - {p['name']}")
    lines.append("  协议规范:")
    for p in protocol_specs():
        lines.append(f"    - {p['name']}")
    lines.append("  第三方渠道（版权风险自担）:")
    for p in third_party():
        lines.append(f"    - {p['name']}")
    lines.append("  概念科普（非规范源）:")
    for p in concept_layer():
        lines.append(f"    - {p['name']}")
    nv = needs_verify_items()
    lines.append("")
    lines.append(f"  needs_verify 挂牌 {len(nv)} 项（JS 渲染未取到/主体不明，不臆造）")
    lines.append("  红线: 只读知识库；不代查、不代下载、不破解付费/受限资源。")
    return True, "\n".join(lines)


def cnstd_lookup_guide() -> tuple:
    """官方标准检索路径指引（openstd / std.samr / hbba 分工与入口）。

    返回 ``(ok, msg)``：内容全部来自知识库实测字段（规模数字为 2026-10-25
    检索日实测），不联网、不代查。
    """
    openstd = entry("openstd_platform")
    std = entry("std_samr_platform")
    hbba = entry("hbba_platform")
    c = standards_count()
    lines = [
        "国内官方标准检索路径（三平台分工，2026-10-25 实测）",
        "",
        "① 查全文 → 国家标准全文公开系统（openstd.samr.gov.cn）",
        f"   强制性国家标准（GB）{c['gb_mandatory']} 条 / "
        f"推荐性国家标准（GB/T）{c['gb_recommended']} 条，均免费公开全文；",
        "   列表条目字段：标准号 / 是否采标 / 名称 / 状态 / 发布日期 / 实施日期。",
    ]
    for d in openstd.get("docs", []):
        lines.append(f"   入口: {d}")
    lines += [
        "",
        "② 查状态与归属 → 全国标准信息公共服务平台（std.samr.gov.cn）",
        f"   行业标准 {c['industry']} 条（{c['industry_fields']} 个行业）/ "
        f"地方标准 {c['local']} 条（31 省级行政区）；",
        "   覆盖「计划—立项—征求意见—发布—备案—复审」全生命周期与专利公示。",
    ]
    for d in std.get("docs", []):
        lines.append(f"   入口: {d}")
    lines += [
        "",
        "③ 查行标备案与废止 → 行业标准信息服务平台（hbba.sacinfo.org.cn）",
        f"   备案公示样本 {c['hbba_samples']} 条（标准号/名称/行业领域/备案日期）；",
        "   备案月报逐月存档（如 2026 年第 9 号 / 总第 317 号），可作时效锚点。",
    ]
    for d in hbba.get("docs", []):
        lines.append(f"   入口: {d}")
    lines += [
        "",
        "分工口诀：全文找 openstd、状态找 std.samr、行标备案找 hbba；",
        "已废止标准不得作为现行依据；第三方渠道不能替代官方源（版权风险见 biaozhuns_platform）。",
    ]
    return True, "\n".join(lines)


def cnstd_protocol_guide() -> tuple:
    """工业/物联网协议规范指引（Modbus 六规范 + MQTT 要点与版本选用）。

    返回 ``(ok, msg)``：内容来自知识库 protocols 字段（modbus.cn 转载 +
    mqtt.org.cn 中文站实测），不联网。
    """
    modbus = entry("modbus_specs")
    mqtt = entry("mqtt_protocol")
    lines = [
        "工业/物联网协议规范指引（国内可查的规范集，2026-10-25 导入）",
        "",
        "── Modbus 六规范（modbus.cn 中文网转载，Modbus Organization 维护）──",
    ]
    for p in modbus.get("protocols", []):
        lines.append(f"  · {p}")
    lines.append("  选用建议: " + modbus.get("advice", ""))
    lines += ["", "── MQTT 协议（mqtt.org.cn 中文站）──"]
    for p in mqtt.get("protocols", []):
        lines.append(f"  · {p}")
    lines.append("  选用建议: " + mqtt.get("advice", ""))
    lines += [
        "",
        "国内落地口径：Modbus 非 IEC 标准、MQTT 为 OASIS 标准——对应国内行标",
        "（YD/T 等）备案状态以 hbba 公示为权威；本指引只读，不联网、不代下载。",
    ]
    return True, "\n".join(lines)
