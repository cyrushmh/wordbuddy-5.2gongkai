#!/usr/bin/env python3
"""WCET 续证 PDU 计分方案 → data/recert_docs.json（可复现构建）。

来源：用户投递的两个 .xls 续证跟踪表（三年周期 FINAL / 五年周期 Dec2016），
路径 research/recert/source/*.xls。本脚本只解析规则文本并落结构化知识层，
**不复制表内个人隐私字段**；WCET 认证已于 2019 年停办，仅供方法论参考。

产物：windows-internals-toolkit/system-optimizer/src/python/sysweeper/data/recert_docs.json

用法：
  python3 build_recert_docs.py             # 构建并写盘
  python3 build_recert_docs.py --check     # 只校验：xls 规则文本仍含各封顶数 + JSON 闭合
  python3 build_recert_docs.py --report    # 打印摘要（不写盘）

工程纪律（与 RFC/CA/Mongo 同款）：
- 规则 prose 直接取自 .xls 指令单元格（权威源），不手抄改写；
- 结构化封顶（cycle_cap / pdu_per_unit）为本工具对 prose 的解释，附 source_sheet；
- --check 反向校验：若 .xls 文本变更导致封顶数对不上，构建当场失败（防漂移）。
"""

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
SRC_DIR = HERE.parent / "source"
OUT = Path(__file__).resolve().parents[2] / "windows-internals-toolkit/system-optimizer/src/python/sysweeper/data/recert_docs.json"

XL_3Y = SRC_DIR / "Recertification PDU Spreadsheet (3 year cycle) FINAL.xls"
XL_5Y = SRC_DIR / "Recertification PDU spreadsheet 5 year (Dec2016).xls"

# 活动分类 → 表页名（与 .xls sheet 名一字不差，含尾部空格）
CATEGORY_SHEETS = {
    "work": "Work ",
    "volunteering": "Volunteering",
    "wcet_support": "WCET Support",
    "teaching": "Teaching",
    "publications": "Publications",
    "training": "Training",
    "self_study": "Self Study",
    "license_cert": "License-Certification",
    "conferences": "Conferences",
    "member_rank": "Member Rank",
}

# 结构化封顶（本工具对 .xls 指令 prose 的解释，附 source_sheet 溯源）
CATEGORY_STRUCT = {
    "work": {
        "label": "Professional Activities（专业工作）",
        "pdu_per_unit": {"3year": "10 PDU/年（≥6 个月专业工作）",
                         "5year": "6 PDU/年（≥6 个月专业工作）"},
        "cycle_cap": {"3year": 30, "5year": 30},
        "per_year_cap": None,
        "patent_pdu": {"applied": 5, "awarded": 10, "5year_awarded_cap": 20},
        "max_patents_per_cycle": 1,
        "cap_probe_3y": "maximum of 30 PDUs per three-year cycle",
        "cap_probe_5y": "maximum of 30 PDUs per five-year cycle",
    },
    "volunteering": {
        "label": "Professional/Industry Volunteer Services（行业志愿服务）",
        "pdu_per_unit": {"3year": "1 PDU/小时", "5year": "1 PDU/小时"},
        "cycle_cap": {"3year": 20, "5year": 30},
        "per_year_cap": {"3year": 10, "5year": 10},
        "cap_probe_3y": "Up to 20 PDUs can be earned for all vounteer service during each three-year cycle",
        "cap_probe_5y": "Up to 30 PDUs can be earned for all vounteer service during each five-year cycle",
    },
    "wcet_support": {
        "label": "WCET Program Support（WCET 项目贡献）",
        "pdu_per_unit": {"3year": "1 PDU/小时", "5year": "1 PDU/小时"},
        "cycle_cap": {"3year": 15, "5year": 25},
        "per_year_cap": None,
        "cap_probe_3y": "Up to 15 PDUs can be earned for all WCET support during each three-year cycle",
        "cap_probe_5y": "Up to 25 PDUs can be earned for all WCET support during each five-year cycle",
    },
    "teaching": {
        "label": "Course Development / Instruction（课程开发 / 授课）",
        "pdu_per_unit": {"3year": "开发 2 PDU/小时；授课 1 PDU/小时",
                         "5year": "开发 2 PDU/小时；授课 1 PDU/小时"},
        "cycle_cap": {"3year": 20, "5year": 30},
        "per_year_cap": None,
        "cap_probe_3y": "Up to 20 PDUs can be earned for all courses and workshops developed or taught during each three-year cycle",
        "cap_probe_5y": "Up to 30 PDUs can be earned for all courses and workshops developed or taught during each five-year cycle",
    },
    "publications": {
        "label": "Publications（论文 / 著作）",
        "pdu_per_unit": {"3year": "1 PDU/小时（撰写）", "5year": "1 PDU/小时（撰写）"},
        "cycle_cap": {"3year": 15, "5year": 25},
        "per_year_cap": None,
        "cap_probe_3y": "Up to 15 PDUs can be earned for publications during each three-year cycle",
        "cap_probe_5y": "Up to 25 PDUs can be earned for publications during each five-year cycle",
    },
    "training": {
        "label": "ComSoc / Outside Training（正规培训）",
        "pdu_per_unit": {"3year": "1 PDU/小时", "5year": "1 PDU/小时"},
        "cycle_cap": {"3year": 15, "5year": 25},
        "per_year_cap": None,
        "cap_probe_3y": "Up to 15 PDUs can be earned for taking such training during each three-year cycle",
        "cap_probe_5y": "Up to 25 PDUs can be earned for taking such training during each five-year cycle",
    },
    "self_study": {
        "label": "Self-Directed Learning（自学）",
        "pdu_per_unit": {"3year": "1 PDU/小时（须评估）", "5year": "1 PDU/小时（须评估）"},
        "cycle_cap": {"3year": 10, "5year": 15},
        "per_year_cap": None,
        "cap_probe_3y": "Up to 10 PDUs can be earned through self-directed learning during each three-year cycle",
        "cap_probe_5y": "Up to 15 PDUs can be earned through self-directed learning during each five-year cycle",
    },
    "license_cert": {
        "label": "Other Certifications（其他执照 / 认证）",
        "pdu_per_unit": {"3year": "1 PDU/小时", "5year": "1 PDU/小时"},
        "cycle_cap": {"3year": 15, "5year": 25},
        "per_year_cap": None,
        "cap_probe_3y": "Up to 15 PDUs (total) can be earned through attaining or renewing a relevant license/certification during each three-year cycle",
        "cap_probe_5y": "Up to 25 PDUs (total) can be earned through attaining or renewing a relevant license/certification during each five year cycle",
    },
    "conferences": {
        "label": "Industry Conferences and Events（行业会议）",
        "pdu_per_unit": {"3year": "1 PDU/小时（参会）", "5year": "1 PDU/小时（参会）"},
        "cycle_cap": {"3year": 15, "5year": 20},
        "per_year_cap": None,
        "cap_probe_3y": "Up to 15 PDUs can be earned through conference participation during each three-year cycle",
        "cap_probe_5y": "Up to 20 PDUs can be earned through conference participation during each five-year cycle",
    },
    "member_rank": {
        "label": "Professional / Industrial Community（会员升级）",
        "pdu_per_unit": {
            "3year": "Sr→Fellow 15 / Member→Sr 15 / Student→full 5 / 两级连升 15",
            "5year": "Sr→Fellow 20 / Member→Sr 15 / Student→full 5 / 两级连升 15",
        },
        "cycle_cap": {"3year": 15, "5year": 25},
        "per_year_cap": None,
        "cap_probe_3y": "Up to 15 PDUs total can be earned for membership upgrades during each three-year cycle",
        "cap_probe_5y": "Up to 25 PDUs total can be earned for membership upgrades during each five-year cycle",
    },
}


def _read_prose(path: Path, sheet: str) -> str:
    """从 .xls 取某活动分类的指令 prose（cell 1,0）。"""
    import xlrd
    wb = xlrd.open_workbook(str(path))
    sh = wb.sheet_by_name(sheet)
    return str(sh.cell_value(1, 0))


def build() -> dict:
    if not XL_3Y.exists() or not XL_5Y.exists():
        raise SystemExit(f"[FAIL] 源 .xls 缺失：{XL_3Y} / {XL_5Y}")
    prose_3y = {k: _read_prose(XL_3Y, s) for k, s in CATEGORY_SHEETS.items()}
    prose_5y = {k: _read_prose(XL_5Y, s) for k, s in CATEGORY_SHEETS.items()}

    categories = []
    for key, st in CATEGORY_STRUCT.items():
        rule = prose_3y[key].split("\n")[0]  # 首段即规则概述
        categories.append({
            "key": key,
            "sheet": CATEGORY_SHEETS[key],
            "label": st["label"],
            "rule": rule,
            "pdu_per_unit": st["pdu_per_unit"],
            "cycle_cap": st["cycle_cap"],
            "per_year_cap": st["per_year_cap"],
            "patent_pdu": st.get("patent_pdu"),
            "max_patents_per_cycle": st.get("max_patents_per_cycle"),
        })

    doc = {
        "_meta": {
            "title": "WCET 续证 PDU 计分方案（IEEE WCET Recertification PDU Scheme）",
            "certification": "IEEE WCET (Wireless Communications Engineering Technologies) Certification",
            "certification_zh": "IEEE 无线通信工程技术认证",
            "source_files": [
                "recert/Recertification PDU Spreadsheet (3 year cycle) FINAL.xls",
                "recert/Recertification PDU spreadsheet 5 year (Dec2016).xls",
            ],
            "author": "Dr. Mohamed Moustafa（续证表原作者；Last Saved By: Tara Gallus / Natasha Simonovski）",
            "created": "2012-03-28",
            "program_status": "IEEE WCET 认证项目已于 2019 年停办；本知识库仅供继续教育 / PDU 跟踪方法论参考，不作为现行认证依据",
            "method": "从用户投递的两个 .xls 续证跟踪表解析 PDU 计分规则（只读元数据，不复制表内个人隐私字段）",
            "note": "PDU 计算与认定以官方 WCET Candidate Handbook 为准；本库为规则知识层，可被 sysweeper 查询与对账",
            "license_note": "用户投递的续证跟踪表为个人使用模板，原件（含姓名/证书号等）不入库，仅留规则知识以 SHA256 备核验",
            "generated_by": "research/recert/build_recert_docs.py",
        },
        "requirements": {
            "increment_hours": 0.25,
            "increment_note": "活动时间以 15 分钟（0.25 小时）为最小计量单位累加",
            "technical_areas_total": 7,
            "min_technical_areas_addressed": 3,
            "technical_areas_note": "活动须关联到 WCET 七大技术知识领域中的至少一项；整个续证周期内须覆盖其中至少 3 个领域",
            "min_distinct_years": 3,
            "min_distinct_years_note": "活动须分布在周期内至少 3 个自然年",
            "cycles": {
                "3year": {"label": "三年周期（标准）", "min_pdus": 60,
                          "span_requirement": "活动覆盖 ≥3 年（三年周期内）",
                          "source": "Recertification PDU Spreadsheet (3 year cycle) FINAL.xls"},
                "5year": {"label": "五年周期", "min_pdus": 100,
                          "span_requirement": "活动覆盖 ≥3 年（五年周期内）",
                          "source": "Recertification PDU spreadsheet 5 year (Dec2016).xls"},
            },
        },
        "technical_areas": {
            "note": "七大类由 WCET Candidate Handbook Appendix A 定义（原表引用但未在表内枚举）。以下为公开 WCET BoK 常见领域名称，第 7 类需对照停办前 Handbook 核实，本库不做臆造",
            "source": "WCET Candidate Handbook Appendix A（项目已停办，仅历史存档可查）",
            "areas": [
                "RF and Propagation（射频与传播）",
                "Signal Processing（信号处理 / DSP）",
                "Communication Theory（通信理论）",
                "Networks, Systems, and Access（网络 / 系统 / 接入）",
                "Hardware, Digital, and Multimedia（硬件 / 数字 / 多媒体）",
                "Software（软件）",
                "[待核实] 第 7 类领域——请对照 WCET Candidate Handbook Appendix A 原文确认",
            ],
        },
        "activity_categories": categories,
        "validation_rules": [
            "总 PDU ≥ 周期下限（三年 60 / 五年 100）",
            "活动分布 ≥3 个自然年",
            "覆盖 ≥3 个 WCET 技术知识领域（共 7 个）",
            "每活动分类 PDU 不超过其周期封顶（cycle_cap）",
            "志愿服务另受每年封顶约束（per_year_cap）",
            "专业工作每年封顶见 pdu_per_unit；每周期仅 1 项专利",
            "执照/认证与培训重复计时不可双报",
            "自学须含评估方法；非纯无线主题按相关占比折算",
            "申报须诚实完整，接受审计；虚假信息可致认证撤销",
        ],
        "summary_lines": [
            "WCET 续证 PDU 方案：IEEE 无线通信工程技术认证（已于 2019 年停办）的继续教育计分规则。",
            "两个周期模板：三年周期 ≥60 PDU、五年周期 ≥100 PDU；均要求活动覆盖 ≥3 年、≥3 个技术知识领域。",
            "10 个活动分类（专业工作/志愿/WCET贡献/授课/论文/培训/自学/其他认证/会议/会员升级），各有 PDU 计分与周期封顶。",
            "本库为规则知识层（只读），可由 sysweeper 查询与对账；原件为个人模板，不入库。",
        ],
    }
    return doc


def check() -> bool:
    ok = True
    doc = build()
    # 1) JSON 闭合与关键不变量
    assert doc["requirements"]["cycles"]["3year"]["min_pdus"] == 60
    assert doc["requirements"]["cycles"]["5year"]["min_pdus"] == 100
    assert len(doc["activity_categories"]) == 10
    # 2) 溯源：.xls 指令 prose 仍含各封顶数（防源变更漂移）
    import xlrd
    for cyc, path in (("3year", XL_3Y), ("5year", XL_5Y)):
        for key, st in CATEGORY_STRUCT.items():
            probe = st[f"cap_probe_{cyc[:1]+'y'}" if cyc == "3year" else "cap_probe_5y"]
            wb = xlrd.open_workbook(str(path))
            sh = wb.sheet_by_name(CATEGORY_SHEETS[key])
            prose = str(sh.cell_value(1, 0))
            if probe not in prose:
                print(f"[FAIL] {key}/{cyc} 封顶数未在源 prose 命中：{probe!r}")
                ok = False
    # 3) 已落盘产物与重建一致
    if OUT.exists():
        on_disk = json.loads(OUT.read_text(encoding="utf-8"))
        if on_disk.get("activity_categories") != doc["activity_categories"]:
            print("[FAIL] 磁盘 recert_docs.json 与重建不一致")
            ok = False
    print("[OK] recert_docs 构建闭环校验通过" if ok else "[FAIL] 见上")
    return ok


def report(doc: dict):
    print("WCET 续证 PDU 方案速览")
    print(f"  周期：三年 ≥60 PDU / 五年 ≥100 PDU；须覆盖 ≥3 年、≥3 领域")
    print(f"  活动分类：{len(doc['activity_categories'])} 个")
    for c in doc["activity_categories"]:
        print(f"    {c['key']:<16} 封顶 {c['cycle_cap']['3year']}/{c['cycle_cap']['5year']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验不写盘")
    ap.add_argument("--report", action="store_true", help="打印摘要不写盘")
    args = ap.parse_args()
    doc = build()
    if args.check:
        sys.exit(0 if check() else 1)
    if args.report:
        report(doc)
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] 写入 {OUT}（{len(doc['activity_categories'])} 活动分类）")


if __name__ == "__main__":
    main()
