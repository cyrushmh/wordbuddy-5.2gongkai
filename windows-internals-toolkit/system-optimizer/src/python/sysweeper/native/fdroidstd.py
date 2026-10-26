"""F-Droid 标准知识库（fdroidstd）：免 GMS 的自由软件分发标准簇。

把 F-Droid 生态的标准整理成一份**知识库**：存储库模型（免账号/免 GMS）→
收录政策（FLOSS 准入）→ 反特征体系（广告/追踪/非自由依赖透明标注）→
构建元数据与 fdroiddata（配方化投稿）→ 可复现构建（服务器从源码构建签名）
→ 客户端与仓库协议（index/签名/特权扩展）→ 免 GMS 国内分发 → F-Droid 与
Play 对照 → 签名信任模型 → 客户端自身（GPL-3.0）。全部事实经 GitHub/
GitLab API 与官方文档检索快照实检（2026-10；f-droid.org 直连不可达，
官方中文/韩文文档取检索快照，仓库层数据取 GitHub/GitLab API）。

红线约束（与整个项目一致）：
- 本工具自身零权限、零网络、零依赖，AOSP 公开 API 即可运行——正是 F-Droid
  主仓库友好形态；
- 本子系统**只读知识库 + 出检查项**，不是认证机构、不代审、不代分发；
- 装什么、从哪装、加哪个仓库的判定与行动始终留给用户。
"""

from __future__ import annotations

import json


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "fdroidstd_standards.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:  # noqa: BLE001
        return {}


REFS = _load_refs()


def reference(key: str) -> dict:
    """返回某 F-Droid 标准主题的文档参考（含 protocols/interfaces/advice）。"""
    return REFS.get(key, {})


def reference_all() -> dict:
    """返回全部 F-Droid 标准文档参考。"""
    return REFS


def fdroidstd_doc_list() -> list:
    """返回 F-Droid 标准文档参考清单（供 CLI/GUI 展示），逐条回链知识库。"""
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
# 分发/收录检查清单（纯函数，不碰系统，便于单测）。                              #
# 每项 = {id, title, severity, action_type, rationale}；                       #
# severity 对齐 Severity 取值 info/notice/warn；                              #
# rationale 回链知识库 key（data/fdroidstd_standards.json）。                  #
# action_type=guidance：只给指引，本工具不代审、不代分发。                      #
# --------------------------------------------------------------------------- #

#: 面向「自查 App/设备是否对齐 F-Droid 标准」的对照项（人工执行）。
FDROID_CHECKS = {
    "floss_license": ("inclusion_policy",
        "许可证是 OSI/FSF 认可的自由软件许可，源码全量公开（主收录前提）",
        "warn"),
    "anti_features_clear": ("anti_features",
        "反特征盘点：无广告、无用户追踪、无非自由依赖；有则如实标注再发第三方仓库",
        "warn"),
    "no_gms_dependency": ("gms_independence",
        "不依赖 GMS/Play 服务，国内无谷歌框架设备可安装可运行",
        "warn"),
    "apk_direct_install": ("gms_independence",
        "分发物是可直装的 APK（能下载即可安装），安装链路不经过任何商业商店",
        "notice"),
    "recipe_ready": ("build_metadata",
        "入主仓库的 .yml 配方就绪：源码 tag/许可/反特征/构建入口，过构建服务器验证",
        "notice"),
    "reproducible_build": ("reproducible_builds",
        "构建可复现：锁依赖版本、去掉时间戳/绝对路径不确定性，可重复构建比对签名",
        "notice"),
    "repo_fingerprint_out_of_band": ("security_signing",
        "自建仓库指纹经站外可信渠道发布；用户加仓库时核对指纹",
        "notice"),
    "client_channel_choice": ("fdroid_vs_play",
        "分发通道按受众选择明确：GitHub Release / F-Droid / 国内商店（备案）并行不悖",
        "info"),
}


def fdroid_compliance_checklist() -> list:
    """返回「自查是否对齐 F-Droid 标准」的对照清单（每项回链知识库 key）。"""
    return [
        {"id": cid, "title": title, "severity": sev,
         "action_type": "guidance", "rationale": kb}
        for cid, (kb, title, sev) in FDROID_CHECKS.items()
    ]


#: 本工具自身定位说明（写入报告，声明工具不是认证/分发机构）。
_SELF_POSITION = (
    "定位声明：sysweeper 自身零权限、零网络、零依赖，AOSP 公开 API 即可运行"
    "——国内无 GMS 设备下载即装即用，正是 F-Droid 通道的理想载荷；本清单"
    "仅帮助用户理解 F-Droid 标准并对照自查，不是认证、不代审、不代分发。"
)


def fdroid_compliance_report(checks: list | None = None) -> tuple:
    """生成 F-Droid 标准总报告（无参可调用，供任务/CLI/GUI）。

    流程：知识库清单 → 分发检查项（回链标准）→ 行动渠道说明。
    纯知识消费，不扫描、不联网、不上传任何信息。
    """
    names = ["== F-Droid 标准 · 免 GMS 自由软件分发知识库 ==",
             "  存储库模型 → 收录政策 → 反特征 → 配方/复现构建 → 仓库协议 → 免 GMS 分发"]

    lines = list(names)
    lines.append("")
    lines.append("-- 标准/规范清单（data/fdroidstd_standards.json）--")
    for key, ref in REFS.items():
        lines.append(f"· [{key}] {ref.get('name', '')}")
        lines.append(f"    {ref.get('summary', '')}")

    lines.append("")
    lines.append("-- F-Droid 分发检查清单（用户视角，人工执行；每项回链标准）--")
    for i, c in enumerate(fdroid_compliance_checklist(), 1):
        lines.append(f"  {i:>2}. [{c['severity']}] {c['title']}")
        lines.append(f"      依据: {c['rationale']}（{REFS.get(c['rationale'], {}).get('name', '')}）")

    lines.append("")
    lines.append(_SELF_POSITION)
    lines.append("行动渠道：F-Droid 客户端与主仓库 → 第三方仓库（核对指纹后添加）→ "
                 "GitHub Releases 直装；装什么、加哪个仓库的判定权始终在用户。")
    return True, "\n".join(lines)
