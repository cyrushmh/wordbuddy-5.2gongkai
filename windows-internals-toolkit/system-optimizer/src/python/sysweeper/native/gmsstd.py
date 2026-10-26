"""GMS 标准知识库（gmsstd）：Google 移动服务（GMS）与 Google Play 兼容/合规标准簇。

把出海 App 与 GMS 设备必须对照的标准整理成一份**知识库**：
兼容性体系（CDD → CTS → VTS/STS）→ GMS 兼容与许可 → Play 上架三件套
（Play Integrity API / Play App Signing / targetSdk 要求）→ Play 数据安全
披露 → 安全公告与补丁体系。除 STS 官方单页外全部经官方源实检
（source.android.google.cn / developer.android.google.cn / play.google.com，
检索日 2026-10）；STS 细节为社区整理源并逐条标注 needs_verify。

红线约束（与整个项目一致）：
- 本工具自身零依赖 GMS、零网络、零采集，纯 AOSP 公开接口可运行；
- 本子系统**只读知识库 + 出检查项**，不是认证机构、不代审、不代申诉；
- 是否上架/如何整改的判定与行动始终留给用户与 Google/监管方。
"""

from __future__ import annotations

import json


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "gmsstd_standards.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:  # noqa: BLE001
        return {}


REFS = _load_refs()


def reference(key: str) -> dict:
    """返回某 GMS/Play 标准主题的文档参考（含 protocols/interfaces/advice）。"""
    return REFS.get(key, {})


def reference_all() -> dict:
    """返回全部 GMS/Play 标准文档参考。"""
    return REFS


def gmsstd_doc_list() -> list:
    """返回 GMS/Play 标准文档参考清单（供 CLI/GUI 展示），逐条回链知识库。"""
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
# 兼容/上架检查清单（纯函数，不碰系统，便于单测）。                              #
# 每项 = {id, title, severity, action_type, rationale}；                       #
# severity 对齐 Severity 取值 info/notice/warn；                              #
# rationale 回链知识库 key（data/gmsstd_standards.json）。                     #
# action_type=guidance：只给指引，本工具不代审、不代申诉。                      #
# --------------------------------------------------------------------------- #

#: 面向「自查 App/设备是否对齐 GMS 与 Play 标准」的对照项（人工执行）。
GMS_CHECKS = {
    "target_sdk_current": ("play_target_api",
        "targetSdk 达到当年度 Play 门槛（2026-08-31 起新 App/更新需 API 36；Wear/车机 API 35）",
        "warn"),
    "aab_signing_enrolled": ("play_app_signing",
        "发布 AAB 已接入 Play 应用签名；上传密钥（RSA≥2048）独立保管并已备份",
        "warn"),
    "key_material_scoped": ("play_app_signing",
        "keystore/密码/密钥指纹只走环境变量与本地文件，不入仓库、不入 CI 日志",
        "warn"),
    "integrity_verdicts_checked": ("play_integrity_api",
        "高敏操作（支付/账号/排行榜）服务端校验 LICENSED + PLAY_RECOGNIZED + 设备分层",
        "notice"),
    "integrity_no_cache": ("play_integrity_api",
        "完整性判定不缓存、按需请求；错误码与 Play 中断有降级路径",
        "notice"),
    "data_safety_form_complete": ("play_data_safety",
        "Data safety 表单覆盖全部 SDK 的数据收集/共享/删除口径，填后有人复核",
        "warn"),
    "privacy_policy_aligned": ("play_data_safety",
        "Play 数据安全披露与国内隐私政策（PIPL 告知-同意）共用同一数据清单、口径一致",
        "notice"),
    "patch_level_fresh": ("security_bulletin_patching",
        "目标设备安全补丁日期在 3 个月内（STS/GTS 硬指标社区整理，以官方为准）",
        "notice"),
    "cts_green_for_rom": ("cts_suite",
        "自研 ROM/设备按 CDD 声明版本跑 CTS 全绿（含 CTS-V 手工项）",
        "notice"),
    "vendor_kernel_vts": ("vts_suite",
        "内核/HAL 变更跑 VTS 回归，保证 system 镜像可在兼容 vendor 上升级",
        "info"),
    "gms_independent": ("gms_compat_licensing",
        "本体确认不依赖 GMS/谷歌服务框架（国内无 GMS 设备可运行）",
        "info"),
    "gms_packages_mapping": ("gms_packages_map",
        "排障先分清代管域：gsf（账号）/gms（服务）/vending（商店）；"
        "「GMS 不可用」先 *#*#426#*#* 看 FCM 通不通再逐组件核对",
        "info"),
    "fcm_keepalive_understood": ("fcm_push_keepalive",
        "出海 IM/工具 App 接 FCM 并处理 token 刷新；国内无 GMS 设备按厂商推送兜底（HMSCore/push kit）",
        "notice"),
    "multi_user_pm_aware": ("adb_multi_user_control",
        "分身/隐私空间类 Play 弹窗按 user 维度诊断（pm list users → disable-user --user <id>），不误伤主用户",
        "info"),
    "harmonyos_gms_boundary": ("harmonyos_gms_deploy",
        "知悉 HarmonyOS 装 GMS 的版本边界：仅 4.x 兼容层可行，NEXT 不支持；"
        "老机型（2019-05 前）Go安装器可直接原生装",
        "info"),
}


def gms_compliance_checklist() -> list:
    """返回「自查是否对齐 GMS 与 Play 标准」的对照清单（每项回链知识库 key）。"""
    return [
        {"id": cid, "title": title, "severity": sev,
         "action_type": "guidance", "rationale": kb}
        for cid, (kb, title, sev) in GMS_CHECKS.items()
    ]


#: 本工具自身定位说明（写入报告，声明工具不是认证/执法机构）。
_SELF_POSITION = (
    "定位声明：sysweeper 自身零依赖 GMS、零网络、零采集，纯 AOSP 公开接口"
    "即可运行——国内无 GMS 设备正是其典型形态；本清单仅帮助用户理解 GMS 与 "
    "Play 标准体系并对照自查，不是认证、不代审、不代申诉。"
)


def gms_compliance_report(checks: list | None = None) -> tuple:
    """生成 GMS/Play 兼容标准总报告（无参可调用，供任务/CLI/GUI）。

    流程：知识库清单 → 兼容检查项（回链标准）→ 行动渠道说明。
    纯知识消费，不扫描、不联网、不上传任何信息。
    """
    names = ["== GMS 标准 · GMS 兼容与 Play 上架知识库 ==",
             "  兼容体系（CDD/CTS/VTS/STS）→ GMS 许可 → Play 三件套 → 数据安全 → 补丁体系"]

    lines = list(names)
    lines.append("")
    lines.append("-- 标准/规范清单（data/gmsstd_standards.json）--")
    for key, ref in REFS.items():
        lines.append(f"· [{key}] {ref.get('name', '')}")
        lines.append(f"    {ref.get('summary', '')}")

    lines.append("")
    lines.append("-- GMS/Play 兼容检查清单（用户视角，人工执行；每项回链标准）--")
    for i, c in enumerate(gms_compliance_checklist(), 1):
        lines.append(f"  {i:>2}. [{c['severity']}] {c['title']}")
        lines.append(f"      依据: {c['rationale']}（{REFS.get(c['rationale'], {}).get('name', '')}）")

    lines.append("")
    lines.append(_SELF_POSITION)
    lines.append("行动渠道：Google Play 管理中心（签名/数据安全/targetSdk 状态）→ "
                 "Play 政策中心（开发者政策）→ source.android.com 兼容性文档；"
                 "判定权始终在用户与 Google 官方。")
    return True, "\n".join(lines)
