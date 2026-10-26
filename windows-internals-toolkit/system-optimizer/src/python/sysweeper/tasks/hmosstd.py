"""HarmonyOS 标准与合规任务（hmosstd，platform=any，跨平台）。

把鸿蒙侧标准口径落成任务层：合规总览（PIPL→AppGallery→备案→权限/隐私→
HUKS/TEE→兼容→测试）+ 上架要件专项 + 安全能力专项。全部只读知识消费——
不代审、不代申诉、不下合规结论；判定权始终在用户与官方来源。

与 native/hmosstd.py 对应：检查项每条回链知识库 key
（data/hmosstd_standards.json），保证「建议有出处」。
与 hmos_ecosystem（工程/生态知识）互补：那边管「怎么干活」，这边管「对齐什么标准」。"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="hmosstd_overview",
        platform="any",
        title="HarmonyOS 标准与合规总览（PIPL→上架→备案→权限/隐私→安全→测试）",
        category="privacy",
        risk="low",
        desc="九段式只读标准总览：①PIPL 上位法（告知-同意、敏感信息单独同意、"
             "跨境规则、个人权利）；②AppGallery 上架要件（软著/备案/隐私政策/"
             "首启同意链路）；③工信部 App 备案（171 号文，2023-08 起）；④权限模型"
             "与 APL 分级（normal/system_basic/system_core，user_grant 敏感权限）；"
             "⑤NEXT 隐私指示器（相机/麦克风/位置/剪贴板可见化）；⑥HUKS 密钥库"
             "（密钥不出 TEE、Attestation）；⑦加解密框架/证书链/TEE；⑧API 版本"
             "兼容（@ohos→@kit 迁移、canIUse 降级）；⑨未成年人保护与后台任务规范、"
             "XTS/Acts 兼容性测试。",
        actions=[
            N("hmosstd.hmosstd_compliance_report", "生成鸿蒙标准/合规知识总报告（只读知识库，不扫描）"),
        ],
        notes=["法规原文以 npc.gov.cn/beian.miit.gov.cn 为准；官方文档以 developer.huawei.com 最新版为准。"],
        standards=["[HMOS-STD] PIPL（npc.gov.cn，2021-11-01 施行）",
                   "[HMOS-STD] AppGallery Connect 审核指南（developer.huawei.com）",
                   "[HMOS-STD] 工信部 App 备案（beian.miit.gov.cn）"],
    ),
    Task(
        id="hmosstd_listing_privacy",
        platform="any",
        title="鸿蒙 App 上架与隐私链路自查（软著/备案/政策/同意时序）",
        category="privacy",
        risk="low",
        desc="上架前的隐私合规链路五查：①三件套硬要件——软著、工信部备案号、"
             "隐私政策 URL（App 内+市场详情双入口）；②同意时序——用户同意前不得"
             "初始化含采集逻辑 SDK（审核机实测点）；③三表对账——requestPermissions "
             "声明清单、隐私政策数据清单、代码实际调用逐条一致；④敏感信息（生物识别/"
             "金融账户/行踪轨迹/14 岁以下）单独同意链路；⑤个人权利可执行——撤回同意"
             "与删除渠道真实可用（PIPL 第 44-49 条）。",
        actions=[
            M("执行顺序：先备软著与备案（周期长）→ 再写隐私政策（与数据清单对账）→ "
              "最后接同意链路（首启弹窗先于任何采集 SDK 初始化）→ 用真机走一遍"
              "首次安装→拒绝权限→撤回同意→删除信息全流程，任何一处闪退即返工。",
              "上架隐私链路自查指引（人工执行）"),
            N("hmosstd.hmosstd_compliance_checklist", "输出合规对照清单（每项回链标准条目）"),
        ],
        notes=["本工具不代审、不代申诉；清单给对照口径，合规结论由用户与官方判定。"],
        standards=["[HMOS-STD] PIPL 第 5-7、28-29、44-49、51-56 条",
                   "[HMOS-STD] AppGallery Connect 审核指南·隐私合规章节",
                   "[HMOS-STD] 工信部 App 备案工作通知（信管函〔2023〕171 号）"],
    ),
    Task(
        id="hmosstd_security_baseline",
        platform="any",
        title="鸿蒙 App 安全能力基线（HUKS/TEE/证书链/国密）",
        category="privacy",
        risk="low",
        desc="鸿蒙侧安全四件基线：①密钥托管——本地令牌/凭据走 HUKS 句柄而非明文，"
             "密钥不出 TEE、可绑定用户认证（指纹/人脸/锁屏）、服务端验 Attestation "
             "证书链判真机；②传输——证书链校验开启、不静默降级 HTTP、敏感场景 "
             "cert pinning；③密码学——对称/非对称/摘要走 cryptoFramework 统一入口，"
             "随机数走 SecureRandom，国密场景（SM2/SM3/SM4）按官方 API 口径；"
             "④权限与后台最小化——APL 只申请 normal 级必需项、长时任务必挂可见通知。",
        actions=[
            M("自检顺序：列出本 App 全部密钥类资产（令牌/缓存号/生物特征）→ 逐个确认"
              "是否 HUKS 托管且不落日志 → 抓一次 TLS 握手确验证书校验与错误码分支 → "
              "核对后台任务类型与通知 → 得到基线报告。",
              "安全基线自查指引（人工执行）"),
            N("hmosstd.hmosstd_compliance_report", "输出安全相关标准条目（HUKS/TEE/证书/国密）"),
        ],
        notes=["算法支持面随 SDK 版本演进（@ohos→@kit 迁移），具体集合以官方 API 文档为准。"],
        standards=["[HMOS-STD] HUKS 通用密钥库（developer.huawei.com/consumer/cn/doc/harmonyos-guides）",
                   "[HMOS-STD] CryptoFramework 加解密框架 / Cert 证书算法库",
                   "[HMOS-STD] OpenHarmony 兼容性测评 XTS/ACTS（gitee.com/openharmony/xts_acts）"],
    ),
]
