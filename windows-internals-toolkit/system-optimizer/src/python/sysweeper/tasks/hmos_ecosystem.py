"""HarmonyOS/OpenHarmony 生态任务（hmos_ecosystem，platform=any，跨平台）。

把鸿蒙生态工程事实落成任务层：生态总览（HAP 工程 → 侧载工具链 → 生态版图
→ 版本关系 → 开发工具链 → IoT）+ 版本线判定专项 + 侧载路径专项。全部只读
知识消费——不扫描、不联网、不代执行任何安装/签名；判定与行动留给用户。

与 native/hmos_ecosystem.py 对应：检查项每条回链知识库 key
（data/hmos_ecosystem_docs.json），保证「建议有出处」。"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="hmoseco_overview",
        platform="any",
        title="HarmonyOS/OpenHarmony 生态总览（HAP 工程→侧载→版图→版本→工具链→IoT）",
        category="privacy",
        risk="low",
        desc="六段式只读知识总览：①HAP 工程结构与 deviceTypes 三分类判定；"
             "②NEXT 侧载工具链（PC 助手 Auto-Installer/HoKit ↔ 端侧 HapInstaller/"
             "HapStore）；③NEXT 第三方生态版图（2026-10 快照 110 款：多端 60/手机"
             "平板 42/电脑 8，原生为主 Flutter 7 款 + 兼容层 3 类）；④OpenHarmony 开源"
             "基座与 HarmonyOS 商业发行关系、NEXT 分水岭；⑤开发工具链（Deveco Studio/"
             "方舟编译器/ArkTS/仓颉/ArkUI）；⑥HiSpark 开发板与 HDF 驱动框架。",
        actions=[
            N("hmos_ecosystem.hmos_ecosystem_report", "生成鸿蒙生态知识总报告（只读知识库，不扫描）"),
        ],
        notes=["来源分社区整理源（needs_verify）与华为官方公开文档两类，逐条标注；生态数据为快照口径。"],
        standards=["[HMOS] HAP 工程规范（developer.huawei.com/consumer/cn/doc/harmonyos-guides）",
                   "[HMOS] OpenHarmony 官方仓库（gitee.com/openharmony）",
                   "[HMOS] HarmonyOS NEXT 生态收录快照（Zitann/HarmonyOS-Haps，2026-10）"],
    ),
    Task(
        id="hmoseco_version_line",
        platform="any",
        title="鸿蒙版本线判定：AOSP 兼容层（4.x）还是纯血 NEXT",
        category="privacy",
        risk="low",
        desc="任何『鸿蒙兼容性』讨论的前置判定：HarmonyOS 4.x 仍含 AOSP 兼容层"
             "（可装 GMS 三件套、可跑 APK 侧载）；NEXT（5.x）为纯血鸿蒙，第三方应用"
             "均为 HAP/ArkTS 原生，不再有 APK 兼容问题。EMUI 更早期直接原生支持 GMS。"
             "误判版本线会导致整套方案（GMS 部署、迁移评估、工具链选择）建立在错误前提上。",
        actions=[
            M("判定流程：确认设备/目标系统具体版本（设置-关于手机）→ 4.x 对照兼容层生态"
              "（含 gmsstd 的 harmonyos_gms_deploy）→ NEXT 对照纯血生态（HAP 侧载、"
              "ArkTS 迁移）→ 在需求文档里写明版本线前提。",
              "版本线判定指引（人工执行）"),
            N("hmos_ecosystem.hmos_compliance_checklist", "输出生态评估自检清单（每项回链知识库）"),
        ],
        notes=["版本边界随 OTA 演进，社区教程口径可能滞后，以设备实际系统版本为准。"],
        standards=["[HMOS] HarmonyOS 版本演进（fenwii/OpenHarmony 资料索引，needs_verify）"],
    ),
    Task(
        id="hmoseco_sideload",
        platform="any",
        title="鸿蒙 NEXT 侧载路径：PC 助手与端侧安装器选择",
        category="privacy",
        risk="low",
        desc="侧载生态三层：PC 侧——小白调试助手（Auto-Installer，跨平台 HAP 安装/"
             "重签名）、HoKit（投屏/性能监控/解析/重签名/文件管理）；端侧——HapInstaller"
             "（端侧签名安装，免 PC）、HapStore（未上架 HAP 聚合目录）。共性模式：PC 侧"
             "批量调试 + 端侧自服务分发互补。",
        actions=[
            M("选择判据：开发调试用 PC 助手（功能全、可投屏排障）；日常分发用端侧安装器；"
              "未上架目录按需。签名密钥（调试/发布）由用户自担保管——涉及密钥与设备状态的"
              "操作一律显式执行，本工具只给路径指引。",
              "侧载路径选择指引（人工执行）"),
            N("hmos_ecosystem.hmos_ecosystem_report", "输出侧载工具链知识条目（只读）"),
        ],
        notes=["第三方工具均为开源社区项目，安全性与可用性由用户自行评估；引用注明来源。"],
        standards=["[HMOS] Auto-Installer（likuai2010/auto-installer）",
                   "[HMOS] HoKit（yabi-zzh/HoKit）",
                   "[HMOS] HapInstaller（LMV475/hap-installer）/ HapStore（zhailinlang/hapstore）"],
    ),
]
