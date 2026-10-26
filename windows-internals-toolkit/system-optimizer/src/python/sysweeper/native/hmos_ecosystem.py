"""HarmonyOS / OpenHarmony 生态知识库（hmos_ecosystem）。

定位（v0.6.71 新增）：把鸿蒙侧的工程事实整理成一份**只读知识库**：
HAP 工程结构与设备类型判定 → NEXT 侧载工具链 → 第三方生态版图（110 款收录画像）
→ HarmonyOS/OpenHarmony 版本关系 → 开发工具链（Deveco/方舟/仓颉/ArkUI）
→ 开发板与 IoT 生态。来源分社区整理源（Zitann/HarmonyOS-Haps、
fenwii/OpenHarmony，needs_verify）与华为官方公开文档两类，逐条在 org 字段标注。

红线约束（与整个项目一致）：
- 本工具零网络、零采集，不访问任何鸿蒙服务，纯本地知识消费；
- 不集成 hdc/Deveco/签名工具链，不解析本地 HAP，不执行任何安装/签名操作；
- 生态数据为快照口径，标注检索日期，不当作实时统计。
"""

from __future__ import annotations

import json


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "hmos_ecosystem_docs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:  # noqa: BLE001
        return {}


REFS = _load_refs()

#: 去掉说明键后的知识条目键
ENTRY_KEYS = tuple(k for k in REFS if not k.startswith("_"))


def reference(key: str) -> dict:
    """返回某鸿蒙生态主题的知识条目（含 protocols/interfaces/advice）。"""
    return REFS.get(key, {})


def reference_all() -> dict:
    """返回全部鸿蒙生态知识条目。"""
    return {k: v for k, v in REFS.items() if not k.startswith("_")}


def hmos_doc_list() -> list:
    """返回鸿蒙生态知识库清单（供 CLI/GUI 展示），逐条回链知识库。"""
    lines = []
    for key in ENTRY_KEYS:
        ref = REFS[key]
        lines.append(f"· {key} — {ref.get('name', '')}")
        lines.append(f"    来源: {ref.get('org', '')}")
        lines.append(f"    文档: {ref.get('url', '')}")
        lines.append(f"    要点: {ref.get('summary', '')}")
    return lines


# --------------------------------------------------------------------------- #
# 生态自检清单（纯函数，不碰系统，便于单测）。                                  #
# 每项 = {id, title, severity, action_type, rationale}；                       #
# severity 对齐 Severity 取值 info/notice/warn；                              #
# rationale 回链知识库 key（data/hmos_ecosystem_docs.json）。                   #
# action_type=guidance：只给指引，不代执行。                                    #
# --------------------------------------------------------------------------- #

#: 面向「评估/迁移鸿蒙生态」的对照项（人工执行）。
HMOS_CHECKS = {
    "version_line_confirmed": ("harmony_vs_openharmony",
        "先确认目标版本线：HarmonyOS 4.x（含 AOSP 兼容层，可装 GMS）还是 NEXT（纯血，无 APK 兼容）",
        "notice"),
    "devicetypes_declared": ("hap_packaging",
        "HAP 工程 module.json5 的 deviceTypes 组合与目标覆盖（phone/tablet/2in1）一致，未声明即按最小集处理",
        "info"),
    "app_name_from_stringjson": ("hap_packaging",
        "应用展示名从 AppScope/resources/base/element/string.json 取官方口径，不用仓库名顶替",
        "info"),
    "sideload_path_known": ("sideload_toolchain",
        "侧载路径明确：PC 助手（Auto-Installer/HoKit）或端侧（HapInstaller）；签名密钥用户自担保管",
        "info"),
    "ecosystem_snapshot_dated": ("next_ecosystem_landscape",
        "引用生态画像注明快照日期（当前 2026-10），不把 110 款收录当实时统计",
        "info"),
    "toolchain_version_matched": ("dev_toolchain",
        "Deveco Studio/SDK 版本与目标设备系统版本匹配；@ohos → @kit 类 API 迁移按官方文档核对",
        "notice"),
    "paradigm_identified": ("fa_stage_evolution",
        "读鸿蒙教程/代码先认范式：config.json+pageAbility=FA（老仓）；module.json5+UIAbility=Stage（新工程）",
        "notice"),
    "codelabs_index_known": ("codelabs_building_blocks",
        "找官方最小样件（分布式/生物识别/远程输入）按 53 个 Codelab 主题图谱定位，注意其为 2022 FA 口径",
        "info"),
}


def hmos_compliance_checklist() -> list:
    """返回「鸿蒙生态评估自检」清单（每项回链知识库 key）。"""
    return [
        {"id": cid, "title": title, "severity": sev,
         "action_type": "guidance", "rationale": kb}
        for cid, (kb, title, sev) in HMOS_CHECKS.items()
    ]


#: 本工具自身定位说明（写入报告，声明工具不是生态裁判）。
_SELF_POSITION = (
    "定位声明：sysweeper 是跨平台只读诊断工具，零网络、零采集，不访问任何鸿蒙"
    "服务；本报告仅帮助用户理解 HarmonyOS/OpenHarmony 生态事实并对照自查，"
    "不推荐任何具体应用、不代执行安装/签名、不充当生态裁判。"
)


def hmos_ecosystem_report(checks: list | None = None) -> tuple:
    """生成 HarmonyOS/OpenHarmony 生态知识总报告（无参可调用，供任务/CLI/GUI）。

    流程：知识库清单 → 生态自检项（回链条目）→ 定位与边界说明。
    纯知识消费，不扫描、不联网、不上传任何信息。
    """
    names = ["== HarmonyOS/OpenHarmony 生态知识库 ==",
             "  HAP 工程 → 侧载工具链 → NEXT 生态版图 → 版本关系 → 开发工具链 → IoT"]

    lines = list(names)
    lines.append("")
    lines.append("-- 知识条目（data/hmos_ecosystem_docs.json）--")
    for key in ENTRY_KEYS:
        ref = REFS[key]
        lines.append(f"· [{key}] {ref.get('name', '')}")
        lines.append(f"    {ref.get('summary', '')}")

    lines.append("")
    lines.append("-- 生态评估自检清单（人工执行；每项回链知识库）--")
    for i, c in enumerate(hmos_compliance_checklist(), 1):
        lines.append(f"  {i:>2}. [{c['severity']}] {c['title']}")
        lines.append(f"      依据: {c['rationale']}（{REFS.get(c['rationale'], {}).get('name', '')}）")

    lines.append("")
    lines.append(_SELF_POSITION)
    lines.append("行动渠道：华为开发者联盟文档（developer.huawei.com）→ "
                 "OpenHarmony 官方仓库（gitee.com/openharmony）→ 社区收录仓库"
                 "（Zitann/HarmonyOS-Haps）；判定权始终在用户与各官方来源。")
    return True, "\n".join(lines)
