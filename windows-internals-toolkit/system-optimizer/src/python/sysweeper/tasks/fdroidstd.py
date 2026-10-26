"""F-Droid 标准任务（fdroidstd，platform=any，跨平台）。

把 F-Droid 自由软件分发标准簇（存储库模型 → 收录政策 → 反特征 → fdroiddata
配方 → 可复现构建 → 仓库协议 → 免 GMS 国内分发 → F-Droid/Play 对照 → 签名
信任 → 客户端自身）落成任务层：分发通道总览 + 收录自查清单 + 专项指引。
全部只读知识消费——不扫描、不联网、不代审、不代分发；装什么、加哪个仓库
的判定与行动留给用户。

与 native/fdroidstd.py 对应：检查项每条回链知识库 key，保证「建议有出处」。"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="fdroidstd_channel_overview",
        platform="any",
        title="免 GMS 分发通道总览（F-Droid 存储库与国内可用性）",
        category="privacy",
        risk="low",
        desc="国内拿不到 GMS 授权，Play 通道客观上不可用；F-Droid 提供免账号、免 GMS 的"
             "分发网络——只要能下载 APK 即可安装。主仓库只收自由软件（FLOSS），运行其"
             "上的服务器也全部是自由软件；任何第三方都可自建仓库。国内可用路径：F-Droid "
             "客户端 + 可达镜像，装完即用，不需要任何谷歌组件。",
        actions=[
            N("fdroidstd.fdroid_compliance_report", "生成 F-Droid 标准总览与分发自查清单（只读知识库，不扫描）"),
        ],
        notes=["F-Droid 由英格兰非营利机构 F-Droid Limited 运营；2010 年创建（Wikipedia 2026-10 实检）。"],
        standards=["[分发] F-Droid 存储库模型（f-droid.org，免账号免 GMS）",
                   "[分发] F-Droid 收录政策（FLOSS 准入，f-droid.org/docs/Inclusion_Policy）"],
    ),
    Task(
        id="fdroidstd_inclusion_selfcheck",
        platform="any",
        title="F-Droid 收录自查（FLOSS + 反特征 + 配方）",
        category="privacy",
        risk="low",
        desc="拟入 F-Droid 主仓库的三道门槛：①许可证为 OSI/FSF 认可的自由软件许可且源码全量"
             "公开；②反特征盘点清零或如实标注（Ads/Tracking/NonFreeNet/NonFreeDep/UpstreamNonFree/"
             "KnownVuln/DisabledAlgorithm/NoSourceSince）；③fdroiddata .yml 配方过构建服务器验证。"
             "不满足主收录也可走第三方仓库分发，但反特征必须透明。",
        actions=[
            M("收录自查：确认许可证与源码仓库公开 → 盘点全部依赖的反特征（广告/追踪/非自由库）"
              "→ 写 metadata/<包名>.yml 配方（源码 tag/许可/反特征/构建入口）→ 向 fdroiddata 提 PR。",
              "F-Droid 主仓库收录自查（指引，不代审）"),
            N("fdroidstd.fdroid_compliance_checklist", "输出收录自查检查项（每项回链知识库）"),
        ],
        notes=["反特征不阻断主仓库收录，但必须标注；主仓库不收含阻断性问题（如源码不可得）的应用。"],
        standards=["[分发] F-Droid 收录政策（FLOSS 准入）",
                   "[分发] Anti-Features 反特征体系（f-droid.org/docs/Anti-Features）",
                   "[分发] fdroiddata 构建元数据（github.com/f-droid/fdroiddata）"],
    ),
    Task(
        id="fdroidstd_reproducible_build",
        platform="any",
        title="可复现构建与配方治理",
        category="privacy",
        risk="low",
        desc="F-Droid 主仓库不收开发者上传的二进制：APK 由服务器从源码构建并签名，官方承诺"
             "『与此源代码 Tarball 一致』。含义：构建可复现（同源同环境位级一致）是入库硬"
             "前提；配方（.yml）是构建的机器可读声明；任何第三方可重复构建比对。对照 Play："
             "Play 收 AAB 由 Google 重签，F-Droid 收配方由自己构建——二进制来源可审计性更强。",
        actions=[
            M("工程化清单：锁依赖版本（AGP/Kotlin/三方库）→ 消除时间戳与绝对路径类不确定性"
              "→ 用官方复现流程自校验一次 → 配方中固化构建参数；发布 tag 与配方版本一一对应。",
              "可复现构建改造指引（指引，不代执行）"),
            N("fdroidstd.fdroid_compliance_checklist", "输出可复现构建检查项"),
        ],
        notes=["本仓库 android/ 工程（Gradle Kotlin AGP）即配方输入；锁版本与去不确定性是投稿前最后两公里。"],
        standards=["[分发] F-Droid Reproducible Builds（服务端从源码构建签名）",
                   "[分发] Build Metadata Reference（配方规范）"],
    ),
    Task(
        id="fdroidstd_repo_protocol",
        platform="any",
        title="仓库协议与自建分发（指纹/索引/特权扩展）",
        category="privacy",
        risk="low",
        desc="F-Droid 仓库协议：索引文件描述应用/版本/反特征/哈希，索引由仓库维护者密钥签名，"
             "客户端添加仓库时核对指纹后才信任内容。自建仓库 = 用户自担信任：指纹是唯一锚点，"
             "加错仓库等于交出安装权。F-Droid Privileged Extension（系统特权）可使客户端免逐次"
             "确认安装/更新，适合企业内网分发。",
        actions=[
            M("内部分发搭建：fdroidserver 生成签名索引 → 指纹经站外渠道（官网/公告）发布 → "
              "客户端『添加仓库→核对指纹』→ 需要免确认时部署特权扩展；私钥离线保管。",
              "自建 F-Droid 仓库指引（指引，不代执行）"),
            N("fdroidstd.fdroid_compliance_checklist", "输出仓库协议安全检查项"),
        ],
        notes=["客户端本体 GPL-3.0（GitHub 3222 stars 实检）；第三方客户端（Neo Store/Droid-ify）生态活跃。"],
        standards=["[分发] fdroidclient 客户端与仓库协议（github.com/f-droid/fdroidclient，GPL-3.0）",
                   "[分发] F-Droid Privileged Extension（免确认安装）"],
    ),
    Task(
        id="fdroidstd_channel_matrix",
        platform="any",
        title="分发通道选择矩阵（F-Droid / Play / 国内商店）",
        category="privacy",
        risk="low",
        desc="三条通道并行不悖：①免 GMS/自由软件/内部分发 → F-Droid（能下载就能装）；②全球商业"
             "分发 → Google Play（Integrity 校验/AAB 签名/targetSdk 门槛逐年抬）；③国内公开分发 → "
             "国内商店（备案 + 国内标准合规）。工具类零依赖 App 建议 GitHub Releases + F-Droid "
             "双通道占位，国内商店视备案进度推进。",
        actions=[
            M("通道决策：按受众与合规要求逐项打勾（GMS 授权有无/商业变现/国内备案/隐私政策）"
              "→ 固定每通道的产物形态（APK 直装 / AAB / 备案包）→ 明确各通道更新责任人。",
              "分发通道选择决策指引（指引，不代执行）"),
            N("fdroidstd.fdroid_compliance_checklist", "输出通道选择检查项"),
        ],
        notes=["三通道合规口径不同：Play 看 gmsstd，国内看 androidstd，F-Droid 看 fdroidstd——三个知识库互为参照。"],
        standards=["[分发] F-Droid vs Play 对照（fdroid_vs_play）",
                   "[GMS] Play 三件套（见 gmsstd 知识库）",
                   "[法律] 国内 App 备案（见 androidstd 知识库）"],
    ),
]
