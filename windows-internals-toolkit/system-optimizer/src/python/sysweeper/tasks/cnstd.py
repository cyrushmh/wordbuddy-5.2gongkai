"""国内标准资源任务（cnstd，platform=any，跨平台）。

把 14 个国内标准资源（2026-10-25 逐只读抓取）落成任务层：官方三平台检索
分工 + 协议规范选用 + 第三方渠道风险 + 概念科普边界。全部只读知识消费——
不联网代查、不代下载、不破解任何付费/受限资源；判定与取用始终留给用户。

引用分层（与 native/cnstd.py 知识库一致）：
  官方源（openstd / std.samr / hbba / CCSA / 合同示范文本库）
  > 协议规范（Modbus 六规范 / MQTT）
  > 第三方渠道（spc 商业付费 / biaozhuns 分享站 / RFC 中文翻译）
  > 概念科普三篇（非规范源）。
JS 渲染未取到的内容统一挂 needs_verify，不臆造。
"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="cnstd_standards_overview",
        platform="any",
        title="国内标准资源总览（14 源：官方/协议/第三方/概念四层）",
        category="standards",
        risk="low",
        desc="国内标准资源知识库全量总览：官方源五平台（openstd 国标全文公开 "
             "6188 强标 + 61615 推标、std.samr 行标 88751/76 行业 + 地标 49114、"
             "hbba 行标备案、CCSA 通信协会、合同示范文本库）+ 协议规范两组"
             "（Modbus 六规范 / MQTT）+ 第三方三家（spc 付费 / biaozhuns 分享站 / "
             "RFC 中文翻译）+ 概念科普三篇。规模数字为 2026-10-25 检索日实测。",
        actions=[
            N("cnstd.cnstd_report", "生成国内标准资源总览（只读知识库，不联网、不代查）"),
            N("cnstd.cnstd_doc_list", "列出 14 源清单（逐条回链知识库）"),
        ],
        notes=["规模数字（6188/61615/88751/49114）为 2026-10-25 官方源实测，"
               "随官方收录增长会变，引用时以检索日为准。"],
        standards=["[官方] 国家标准全文公开系统 openstd.samr.gov.cn（GB 6188 / GB/T 61615，实测）",
                   "[官方] 全国标准信息公共服务平台 std.samr.gov.cn（行标 88751/76 行业、地标 49114，实测）",
                   "[官方] 行业标准信息服务平台 hbba.sacinfo.org.cn（行标备案公示 + 月报）"],
    ),
    Task(
        id="cnstd_official_lookup",
        platform="any",
        title="官方标准检索路径（全文/状态/备案三平台分工）",
        category="standards",
        risk="low",
        desc="国内查标准的三平台分工：全文找 openstd（GB/GB/T 免费全文公开，"
             "条目含标准号/采标/状态/发布与实施日期）；状态与归属找 std.samr"
             "（立项/备案/复审/废止全生命周期 + 专利公示）；行标备案与废止找 "
             "hbba（备案公示 + 逐月月报，如 2026 年第 9 号/总第 317 号）。"
             "已废止标准不得作为现行依据。",
        actions=[
            N("cnstd.cnstd_lookup_guide", "输出三平台检索路径与入口（含实测规模数字）"),
            M("按需检索：GB/GB/T 全文 → openstd；行标/地标/团标状态 → std.samr；"
              "YD/T 等行标备案与废止 → hbba 备案公示与月报。",
              "官方检索路径使用指引（指引，不代查）"),
        ],
        notes=["第三方『免费下载』站不能替代官方源——真伪与版权风险见 cnstd_third_party_caution。"],
        standards=["[官方] openstd.samr.gov.cn/bzgk/std/std_list_type（强标/推标全文公开）",
                   "[官方] std.samr.gov.cn/gb、/noc/nocHB、/noc/nocDB（国标/行标备案月报/地标备案月报）",
                   "[官方] hbba.sacinfo.org.cn/stdList、/snList?snType=pub（行标列表/发布公告）"],
    ),
    Task(
        id="cnstd_protocol_specs",
        platform="any",
        title="工业/物联网协议规范选用（Modbus 六规范 + MQTT）",
        category="standards",
        risk="low",
        desc="Modbus 六规范（应用层 V1.1b3 / 安全 TLS 802 端口 / 串行线 V1.02 / "
             "TCP / 实现指南等，Modbus Organization 维护、非 IEC 标准）与 MQTT "
             "发布订阅架构（三档 QoS：遥测 0 / 指令 1 / 计费 2，持久会话适应"
             "不可靠网络）。选用建议：新项目 V1.1b3 应用层 + V1.02 串行线或 TCP；"
             "安全场景走 TLS；国内行标落地状态以 hbba 备案为权威。",
        actions=[
            N("cnstd.cnstd_protocol_guide", "输出 Modbus 六规范与 MQTT 要点及选用建议"),
            M("协议落地核对：Modbus/MQTT 的国内对应行标（YD/T 等）是否现行有效，"
              "以 hbba 备案公示为准；不要拿第三方转载页当规范依据。",
              "协议规范国内落地核对（指引，不代查）"),
        ],
        notes=["modbus.cn / mqtt.org.cn 为规范中文转载站；正式引用以 Modbus Organization / "
               "OASIS 一手规范为准。"],
        standards=["[规范转载] Modbus 六规范（modbus.cn，Modbus Organization 原版转载）",
                   "[规范] MQTT 协议（OASIS 标准，mqtt.org.cn 中文站）",
                   "[官方] hbba.sacinfo.org.cn（协议类行标备案状态权威口径）"],
    ),
    Task(
        id="cnstd_third_party_caution",
        platform="any",
        title="第三方标准渠道风险（付费/分享站/RFC 翻译的版权边界）",
        category="standards",
        risk="low",
        desc="第三方渠道三类风险面：① spc.org.cn 商业付费——先查 openstd 免费"
             "全文，仅当官方未收录或需印刷版时再考虑并自行核验商家资质；"
             "② biaozhuns.com 分享站——国标合法免费渠道只有 openstd，分享站"
             "运营主体/授权来源/收录总量均未确认（needs_verify 挂牌），正式用途"
             "必须走官方源；③ RFC 中文翻译（gitcode daa7f，约 300 份）——学习"
             "可借中文，正式引用一律回 RFC 英文原版。",
        actions=[
            M("风险自检：是否在用第三方站的『免费标准』做正式依据？→ 是则改走 "
              "openstd 官方全文；是否在商业用途使用 RFC 中文翻译？→ 是则回英文原版。",
              "第三方渠道风险自检（指引，不代取用）"),
            N("cnstd.cnstd_report", "对照知识库第三方层条目（含 needs_verify 挂牌明细）"),
        ],
        notes=["本工具只登记第三方渠道存在性与风险，不提供下载方法、不代为取用、不代购。"],
        standards=["[官方] openstd.samr.gov.cn（国标全文唯一合法免费渠道）",
                   "[第三方] spc.org.cn（商业付费，存在性登记）",
                   "[第三方] biaozhuns.com（分享站，版权合规性 needs_verify）",
                   "[第三方] gitcode Premium-Resources/daa7f（RFC 中文翻译，授权限个人学习）"],
    ),
    Task(
        id="cnstd_concept_layer",
        platform="any",
        title="标准 vs 协议概念辨析（科普层，非规范源）",
        category="standards",
        risk="low",
        desc="三篇科普给出的概念框架：标准（规定结构/信号）vs 协议（规定行为/"
             "消息交换）；专有 vs 开放（开放标准 = 公开透明非专利制定，促互操作）。"
             "用于引用具体标准号前的概念打底——技术细节仍以 RFC/OASIS/GB 等"
             "一手规范为准，引用文章时注明科普层。",
        actions=[
            N("cnstd.cnstd_report", "对照知识库概念层条目（三篇科普的定位与边界）"),
            M("概念自测：手头的『标准』是技术规范（GB/RFC/OASIS）还是科普文章？"
              "引用链路是否最终落到一手规范？",
              "概念层引用边界自测（指引）"),
        ],
        notes=["科普层概念可用、结论不可直接引用；正式场景回一手规范（RFC/IETF、OASIS、GB）。"],
        standards=["[科普] 《探索网络协议的标准化过程与开放标准的重要性》（腾讯云，2023-11-27）",
                   "[科普] 《通信标准 vs 通讯协议》（techphant.cn）",
                   "[科普] 华为云开发者社区相关博文（bbs.huaweicloud.com/blogs/437347）"],
    ),
]
