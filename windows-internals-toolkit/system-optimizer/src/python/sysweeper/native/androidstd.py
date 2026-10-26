"""国内标准知识库（androidstd）：中国境内 App 隐私与信息安全合规标准/法规簇。

把中国境内 App（含小程序/快应用）运营必须对照的国内标准与法规整理成一份
**知识库**：上位法（PIPL）→ 国家标准（GB/T 35273/41391/42574/34975）→
部门规范性文件（四部门认定方法、39 类必要范围、App 备案、App 信息服务
管理规定）→ 标准化实践指南（TC260 自评估/系统权限）。全部条目经官方源
实检（openstd.samr.gov.cn / cac.gov.cn / miit.gov.cn / gov.cn / tc260.org.cn），
编号、名称、发布/施行日期以 2026-10 检索日为准。

红线约束（与整个项目一致）：
- 本工具自身即最小化实践：零权限、零网络、零采集，不落入 PIPL 处理者义务；
- 本子系统**只读知识库 + 出检查项**，不是合规认证器、不代执法、不代申诉；
- 判定与行动始终留给用户（向 App 运营者/分发平台/12321/监管部门反映）。
"""

from __future__ import annotations

import json


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "androidstd_domestic_standards.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:  # noqa: BLE001
        return {}


REFS = _load_refs()


def reference(key: str) -> dict:
    """返回某国内标准/法规主题的文档参考（含 protocols/interfaces/advice）。"""
    return REFS.get(key, {})


def reference_all() -> dict:
    """返回全部国内标准/法规文档参考。"""
    return REFS


def androidstd_doc_list() -> list:
    """返回国内标准/法规文档参考清单（供 CLI/GUI 展示），逐条回链知识库。"""
    lines = []
    for key, ref in REFS.items():
        lines.append(f"· {key} — {ref.get('name', '')}")
        lines.append(f"    机构: {ref.get('org', '')}")
        lines.append(f"    文档: {ref.get('url', '')}")
        lines.append("    要点:")
        for p in ref.get("protocols", [])[:4]:
            lines.append(f"      - {p}")
        lines.append(f"    建议: {ref.get('advice', '')}")
    return lines


# --------------------------------------------------------------------------- #
# 合规检查清单（纯函数，不碰系统，便于单测）。                                  #
# 每项 = {id, title, severity, action_type, rationale}；                       #
# severity 对齐 Severity 取值 info/notice/warn；                              #
# rationale 回链知识库 key（data/androidstd_domestic_standards.json）。        #
# action_type=guidance：只给指引，本工具不代执法、不代申诉。                    #
# --------------------------------------------------------------------------- #

#: 面向「检查某个 App」的对照项（用户视角，人工执行）。
APP_CHECKS = {
    "notice_consent_first": ("gb_t_35273_pi_spec",
        "首次启动先展示隐私政策并取得同意，再开始收集（同意前收集=违规）",
        "warn"),
    "min_necessary": ("necessary_pi_scope",
        "按 39 类清单核对：该 App 索要的信息是否超出其类型对应的必要范围",
        "warn"),
    "reject_not_blocked": ("four_dept_violation_criteria",
        "拒绝非必要权限后基本功能仍可使用（拒绝即闪退=捆绑授权）",
        "warn"),
    "sensitive_separate_consent": ("pipl",
        "敏感个人信息（生物识别/位置/金融账户）已单独取得同意且用途明示",
        "warn"),
    "delete_account_reachable": ("four_dept_violation_criteria",
        "删除/更正/注销账号入口可在两层点击内找到且可实际完成",
        "notice"),
    "consent_withdrawable": ("gb_t_42574_notice_consent",
        "同意的撤回路径可达；撤回后不反复弹窗骚扰",
        "notice"),
    "permission_timing": ("tc260_permission_guide",
        "权限在用到时才申请且附目的说明，而非启动时一揽子索取",
        "notice"),
    "sdk_third_party": ("tc260_app_self_assess",
        "第三方 SDK 收集行为已在隐私政策披露并可单独关闭",
        "notice"),
    "minor_mode": ("minor_mode_guide",
        "面向未成年人的 App/内容已启用青少年模式或未成年人模式",
        "notice"),
    "filing_number": ("app_filing",
        "商店详情页可查备案编号（2024-03 后未备案即属违规运营）",
        "info"),
    "secure_transport": ("gb_t_34975_app_software_sec",
        "账号/支付等敏感通信全程加密（HTTPS），不明文传输",
        "notice"),
}


def app_compliance_checklist() -> list:
    """返回「检查某 App 是否合规」的对照清单（每项回链知识库 key）。"""
    return [
        {"id": cid, "title": title, "severity": sev,
         "action_type": "guidance", "rationale": kb}
        for cid, (kb, title, sev) in APP_CHECKS.items()
    ]


#: 本工具自身定位说明（写入报告，声明工具不是执法/认证机构）。
_SELF_POSITION = (
    "定位声明：sysweeper 自身是零权限、零网络、零采集的只读诊断工具——"
    "不收集任何个人信息，不落入 PIPL 个人信息处理者义务；本清单仅帮助用户"
    "理解国内标准并对照自查，不是合规认证、不代执法、不代申诉。"
)


def androidstd_compliance_report(checks: list | None = None) -> tuple:
    """生成国内 App 隐私合规标准总报告（无参可调用，供任务/CLI/GUI）。

    流程：知识库清单 → 合规检查项（回链标准）→ 行动渠道说明。
    纯知识消费，绝不扫描、绝不上传任何信息。
    """
    names = ["== 国内标准 · Android/App 隐私合规知识库 ==",
             "  上位法 → 国标 → 部门规定 → TC260 实践指南四层（全部经官方源实检）"]

    lines = list(names)
    lines.append("")
    lines.append("-- 标准/法规清单（data/androidstd_domestic_standards.json）--")
    for key, ref in REFS.items():
        lines.append(f"· [{key}] {ref.get('name', '')}")
        lines.append(f"    {ref.get('summary', '')}")

    lines.append("")
    lines.append("-- App 合规检查清单（用户视角，人工执行；每项回链标准）--")
    for i, c in enumerate(app_compliance_checklist(), 1):
        lines.append(f"  {i:>2}. [{c['severity']}] {c['title']}")
        lines.append(f"      依据: {c['rationale']}（{REFS.get(c['rationale'], {}).get('name', '')}）")

    lines.append("")
    lines.append(_SELF_POSITION)
    lines.append("行动渠道：App 内举报 / 分发平台投诉 / 12321 网络不良与垃圾信息"
                 "举报受理中心 / 工信部·网信办监管渠道（判定权始终在用户与监管部门）。")
    return True, "\n".join(lines)
