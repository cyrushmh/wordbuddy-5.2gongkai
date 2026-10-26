"""hmosstd：HarmonyOS NEXT 标准与合规只读知识层（v0.6.72）。

第四生态标准库（前三：androidstd 国内 Android / gmsstd GMS / fdroidstd 免 GMS），
口径 = 国内法规（PIPL / 工信部 / 未成年人条例）+ 华为官方公开文档 +
AppGallery 上架要求。与 hmos_ecosystem（工程/生态知识）的分工：

- hmos_ecosystem 回答「鸿蒙生态怎么干活」：HAP 工程、侧载、工具链、版图；
- hmosstd 回答「鸿蒙 App 对齐什么标准」：权限、隐私、上架、安全、测试、兼容。

本工具**只读知识库 + 出检查项**：不代审、不代申诉、不判合规结论；
判定权始终在用户与各官方来源。社区整理内容一律 needs_verify。
"""

from __future__ import annotations

from importlib import resources
import json


def _load_refs() -> dict:
    try:
        text = (resources.files("sysweeper.data")
                .joinpath("hmosstd_standards.json")
                .read_text(encoding="utf-8"))
        return json.loads(text)
    except Exception:
        return {}


REFS = _load_refs()

#: 知识条目 key 序列（跳过 _note/_position 等下划线字段）
ENTRY_KEYS = tuple(k for k in REFS if not k.startswith("_"))


def reference(key: str) -> dict:
    """返回某标准主题的知识条目（含 protocols/interfaces/docs/advice）。"""
    return dict(REFS.get(key, {}))


def reference_all() -> dict:
    """返回全部知识条目（跳过 _note/_position）。"""
    return {k: v for k, v in REFS.items() if not k.startswith("_")}


def hmosstd_doc_list() -> list:
    """返回鸿蒙标准/合规文档参考清单（供 CLI/GUI 展示），逐条回链知识库。"""
    lines = []
    for key, ref in reference_all().items():
        lines.append(f"· {key} — {ref.get('name', '')}")
        lines.append(f"    机构: {ref.get('org', '')}")
        lines.append(f"    文档: {ref.get('url', '')}")
        lines.append("    要点:")
        for p in ref.get("protocols", [])[:4]:
            lines.append(f"      - {p}")
        lines.append(f"    建议: {ref.get('advice', '')}")
    return lines


# --------------------------------------------------------------------------- #
# 合规对照检查清单（纯函数，不碰系统，便于单测）。                              #
# 每项 = {id, title, severity, action_type, rationale}；                       #
# rationale 回链知识库 key（data/hmosstd_standards.json）。                     #
# action_type=guidance：只给指引，本工具不代审、不下合规结论。                   #
# --------------------------------------------------------------------------- #

#: 面向「自查鸿蒙 App 是否对齐法律/官方/市场标准」的对照项（人工执行）。
HMOSSTD_CHECKS = {
    "privacy_policy_gated": ("pipl_harmony",
        "隐私政策在首次启动即公示，且用户同意前不初始化任何含采集逻辑的 SDK/接口",
        "warn"),
    "minimal_permission_declared": ("permission_apl_model",
        "requestPermissions 清单与实际调用、隐私政策数据清单三对照，多声明/少声明都修正",
        "warn"),
    "sensitive_consent_separate": ("pipl_harmony",
        "敏感个人信息（生物识别/金融账户/行踪轨迹/14 岁以下）取得单独同意，有专门处理规则",
        "warn"),
    "withdraw_delete_channel": ("pipl_harmony",
        "提供撤回同意与个人信息删除渠道（PIPL 第 44-49 条个人权利可执行）",
        "notice"),
    "app_filing_done": ("app_filing_miit",
        "通过 beian.miit.gov.cn 可查备案号；bundleName/软著/备案三处一致",
        "warn"),
    "listing_kit_ready": ("appgallery_listing",
        "上架四件套齐备：软著、备案号、隐私政策 URL、功能描述与实际一致",
        "warn"),
    "key_in_huki": ("huki_key_management",
        "本地令牌/凭据走 HUKS：密钥不出 TEE、可绑定用户认证、不硬编码不落日志",
        "warn"),
    "crypto_tls_hardened": ("crypto_cert_tee",
        "网络层证书链校验开启、错误码不静默降级；国密场景按 cryptoFramework 官方口径实现",
        "notice"),
    "canius_compat_degraded": ("api_version_compat",
        "跨 4.x/NEXT 的接口面用 canIUse + @ohos→@kit 迁移表逐条对账，缺能力有降级分支",
        "notice"),
    "background_task_visible": ("background_network_std",
        "长时任务必有可见通知；定时提醒走 reminderAgent；蜂窝下跳过自动更新",
        "notice"),
    "minor_rules_applied": ("minor_protection",
        "面向未成年人群体适配青少年模式感知与 14 岁分界的单独同意流程",
        "notice"),
    "xts_selfcheck_before_release": ("xts_app_testing",
        "发布前跑安装/卸载/权限拒绝/生命周期恢复最小兼容套件，Acts 自检过一遍",
        "info"),
}


def hmosstd_compliance_checklist() -> list:
    """返回「自查鸿蒙 App 是否对齐法律/官方/市场标准」的对照清单（回链知识库 key）。"""
    return [
        {"id": cid, "title": title, "severity": sev,
         "action_type": "guidance", "rationale": kb}
        for cid, (kb, title, sev) in HMOSSTD_CHECKS.items()
    ]


_SELF_POSITION = (
    "本工具自身合规自评：sysweeper 零权限、零网络、零采集（不经应用市场分发），"
    "不落入 App 备案与隐私政策义务场景；对鸿蒙 App 的判定只落在『对照清单』层，"
    "本工具不代审、不代申诉、不下合规结论——判定权在用户与官方来源。"
)


def hmosstd_compliance_report(checks: list | None = None) -> tuple:
    """生成 HarmonyOS 标准/合规知识总报告（无参可调用，供任务/CLI/GUI）。

    流程：标准清单 → 合规对照项（回链条目）→ 定位与边界说明。
    纯知识消费，不扫描、不联网、不上传任何信息。
    """
    lines = [
        "== HarmonyOS NEXT 标准与合规知识库 ==",
        "  PIPL 上位法 → AppGallery 上架 → App 备案 → 权限/隐私 → HUKS/密码学/TEE →",
        "  版本兼容 → 未成年人保护 → 后台与网络 → XTS 兼容性测试",
    ]
    lines.append("")
    lines.append("-- 标准条目（data/hmosstd_standards.json："
                 f"{len(ENTRY_KEYS)} 条，官方源 + 法规原文；社区整理 needs_verify）--")
    for key in ENTRY_KEYS:
        ref = REFS[key]
        lines.append(f"· [{key}] {ref.get('name', '')}")
        lines.append(f"    {ref.get('org', '')}")

    lines.append("")
    lines.append("-- 合规对照清单（人工执行；每项回链标准条目）--")
    for i, c in enumerate(hmosstd_compliance_checklist(), 1):
        lines.append(f"  {i:>2}. [{c['severity']}] {c['title']}")
        lines.append(f"      依据: {c['rationale']}"
                     f"（{REFS.get(c['rationale'], {}).get('name', '')}）")

    lines.append("")
    lines.append(_SELF_POSITION)
    lines.append("行动渠道：华为开发者联盟文档（developer.huawei.com）→ "
                 "工信部备案系统（beian.miit.gov.cn）→ 国家人大网法规原文（npc.gov.cn）；"
                 "AppGallery Connect 审核指南随市场政策更新，以站内最新版为准。")
    return True, "\n".join(lines)
