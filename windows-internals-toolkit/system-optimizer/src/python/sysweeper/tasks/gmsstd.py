"""GMS 标准任务（gmsstd，platform=any，跨平台）。

把 GMS 兼容与 Google Play 上架标准簇（CDD/CTS/VTS/STS → GMS 许可 → Play
三件套 → Data safety → 安全公告补丁体系，除 STS 细节外全部经官方源实检）
落成任务层：兼容体系总览 + Play 上架自查清单 + 专项指引。全部只读知识
消费——不扫描、不联网、不代审；判定与行动留给用户与 Google 官方。

与 native/gmsstd.py 对应：检查项每条回链知识库 key，保证「建议有出处」。"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="gmsstd_compat_overview",
        platform="any",
        title="GMS 兼容体系总览（CDD/CTS/VTS/STS 与 GMS 许可）",
        category="privacy",
        risk="low",
        desc="Android 兼容性三层递进：CDD 是『规范文本』（声明什么是兼容设备）→ CTS 是"
             "『自动体检』（免费商业级测试套件，Trade Federation + CTS-V 手工项）→ VTS 覆盖"
             "内核与 HAL（Treble 后 system/vendor 分区契约）。官方原话：SafetyNet "
             "Attestation 即『确定设备是否与 CTS 兼容』的 API——CTS 兼容是 GMS 服务栈门槛。",
        actions=[
            N("gmsstd.gms_compliance_report", "生成 GMS 兼容体系总览与上架自查清单（只读知识库，不扫描）"),
        ],
        notes=["STS 官方单页在本仓检索环境未实检到，其细节为社区整理并逐条标注 needs_verify（以 Google 官方文档为准）。"],
        standards=["[GMS] Android 兼容性定义文档 CDD（source.android.google.cn/compatibility/cdd）",
                   "[GMS] 兼容性测试套件 CTS（source.android.google.cn/docs/compatibility/cts）",
                   "[GMS] 供应商测试套件 VTS（source.android.google.cn/docs/core/tests/vts）",
                   "[GMS] 安全测试套件 STS（社区整理待核；官方锚点：Android 安全公告体系）"],
    ),
    Task(
        id="gmsstd_play_integrity",
        platform="any",
        title="Play Integrity API 接入自查（反滥用三 verdict + 分层执法）",
        category="privacy",
        risk="low",
        desc="Play Integrity API 判定用户操作是否来自『Play 安装、正版认证设备、正版应用』："
             "核心 verdict（appLicensingVerdict=LICENSED / appRecognitionVerdict=PLAY_RECOGNIZED / "
             "deviceIntegrity 分层）+ 可选风险信号（appAccessRisk/playProtect/recentDeviceActivity/"
             "deviceRecall）。默认每应用每日 10,000 次请求；官方建议：适时请求、不缓存、"
             "分层执法而非一禁了之。",
        actions=[
            M("接入核对：高敏操作（支付/账号/排行榜）在服务端校验基础 verdict；设备标签分层"
              "放行（BASIC→DEVICE→STRONG）；判定不缓存；错误码与 Play 中断有降级路径；"
              "在 Play 管理中心申请提高配额。",
              "Play Integrity 接入自查清单（指引，不代执行）"),
            N("gmsstd.gms_compliance_checklist", "输出 Play Integrity 对照检查项（每项回链知识库）"),
        ],
        notes=["端上仅请求令牌、后端解密校验——私钥只放服务端；国内发行版可保留该能力作纵深防御一层。"],
        standards=["[GMS] Play Integrity API 概览（developer.android.google.cn/google/play/integrity/overview）",
                   "[GMS] Play Integrity API 服务条款（developer.android.google.cn/google/play/integrity/terms）"],
    ),
    Task(
        id="gmsstd_play_signing",
        platform="any",
        title="Play 应用签名与密钥管理自查（上传密钥/应用签名密钥）",
        category="privacy",
        risk="low",
        desc="Play 应用签名：应用签名密钥托管 Google（生成 4096 位 RSA / 自定义≥2048 位，"
             "注册后不可取回），上传密钥开发者自管（.jks，RSA≥2048，丢失可重置）。AAB 分发"
             "强制接入（条款 2021-08-01 生效）；密钥升级仅 AAB 支持、新旧双发布；符合条件"
             "应用自动走 v4 签名；多商店分发要自持密钥（导入而非 Google 生成）。",
        actions=[
            M("密钥治理：生成独立上传密钥（与签名密钥分开）；keystore/密码只走环境变量与"
              "本地文件、不入仓库不落 CI 日志；登记第三方 API 的 SHA-1/SHA-256 指纹；"
              "备份上传密钥丢失后的 Play 管理中心重置路径。",
              "密钥管理与发布链路自查（指引，不代执行）"),
            N("gmsstd.gms_compliance_checklist", "输出密钥管理对照检查项（每项回链知识库）"),
        ],
        notes=["本仓库 android 工程构建本地 APK，不入 Play 分发；.gitignore 已防 keystore 误提交。"],
        standards=["[GMS] Play 应用签名（developer.android.google.cn/studio/publish/app-signing）",
                   "[GMS] Play 应用签名服务条款（play.google，2021-08-01 生效）"],
    ),
    Task(
        id="gmsstd_target_sdk",
        platform="any",
        title="Play targetSdk 门槛对照（2026-08-31 起 API 36）",
        category="privacy",
        risk="low",
        desc="Google Play 目标 API 级别一年一抬：2026-08-31 起新 App 与更新必须 target "
             "Android 16（API level 36）或更高；Wear OS 与 Android Automotive OS 例外，须 "
             "target Android 15（API 35）。此前节点 2025-08-31 为 API 34。升级前评估前台"
             "服务类型、精确闹钟、通知权限（POST_NOTIFICATIONS）等行为变更。",
        actions=[
            M("版本计划：每年 Q3 前完成 compileSdk/targetSdk 升级与回归（前台服务类型声明、"
              "动态权限、后台限制）；用本工具 androidstd 权限探针核对升级影响面；压哨不提交。",
              "targetSdk 升级计划指引（指引，不代执行）"),
            N("gmsstd.gms_compliance_checklist", "输出 targetSdk 与上架门槛对照检查项"),
        ],
        notes=["本仓库 android 工程当前 targetSdk 34；上架前需评估升 35/36 的行为变更。"],
        standards=["[GMS] Google Play targetSdk 要求（developer.android.com/google/play/requirements/target-sdk）"],
    ),
    Task(
        id="gmsstd_data_safety",
        platform="any",
        title="Play 数据安全表单与隐私披露自查",
        category="privacy",
        risk="low",
        desc="Play 数据安全（Data safety，2021-05 上线）要求向用户披露应用的数据收集、共享"
             "与安全做法；官方明确开发者对表单填写负全责。第三方 SDK 隐式收集（广告 ID、"
             "崩溃日志）最易漏填。与国内 PIPL 隐私政策可复用同一张数据清单，一次盘点两处"
             "披露，口径一致。",
        actions=[
            M("披露盘点：列全部 SDK 与数据流（收集项/用途/共享对象/传输加密/删除路径）→ "
              "Data safety 表单如实填写 → 与国内隐私政策交叉核对一致 → 上架后变更即更新表单。",
              "Data safety 表单填写与复核指引（指引，不代执行）"),
            N("gmsstd.gms_compliance_checklist", "输出数据安全披露对照检查项（每项回链知识库）"),
        ],
        notes=["本工具零采集：若上架，表单如实填『不收集任何数据』并与 manifest 一致。"],
        standards=["[GMS] Google Play 数据披露（developers.google.cn/admob/android/privacy/play-data-disclosure）",
                   "[GMS] Play Data safety 表单帮助（support.google.com/googleplay/android-developer/answer/10787469）",
                   "[法律] PIPL 告知-同意（国内同步披露，见 androidstd 知识库）"],
    ),
]
