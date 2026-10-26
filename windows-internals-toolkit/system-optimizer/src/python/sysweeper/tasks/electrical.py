"""供电与环境安全任务（platform=any，跨平台）。

全部只读探针 + 规范/官方指引；任何「测接触电阻/碰配电箱/换线/装 RCD」的高危动作
一律只给规范指引，不代执行——严守本项目只读红线，也契合用户「个人行为在完全
图形界面控制操作」：工具出风险识别与方案，用户请持证电工按规范施工。

引擎（assess_hazard_chain / adapt_by_env / electrical_safety_report）是纯函数，
由 electrical_safety_report 串联；GUI 可让用户勾选供电环境标签后即时看到自适应报告。
本子系统与「设备长期使用保护（durability）」并列，共同支撑「依据设备外部和内部
环境自适应、保持长期保障运行」。"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="electrical_safety_report",
        platform="any",
        title="供电与环境安全评估（只读 + 自适应）",
        category="maintenance",
        risk="low",
        desc="由供电环境标签（旧线/铜铝/无接地/木座/松动插座/高发热负载）+ 本机可读温度，识别"
             "电气火灾事故前兆链条与风险级，给自适应运行建议；每条回链知识库。",
        actions=[
            N("electrical.electrical_safety_report", "端到端生成供电与环境安全报告（识别隐患链→自适应建议）"),
        ],
        notes=["软件不可测插座接触电阻、绝不碰配电箱；环境标签由用户据实声明（目检/电工排查）。"],
        standards=["[国家] GB/T 16895 系列（等同 IEC 60364，低压电气装置）",
                  "[国家] GB/T 2099.1（家用插头插座，等同 IEC 60884-1）",
                  "[国家] GB 13955（剩余电流动作保护装置安装和运行）"],
    ),
    Task(
        id="electrical_rewire_guidance",
        platform="any",
        title="重拉全程阻燃铜芯线（规范指引）",
        category="maintenance",
        risk="low",
        desc="铜铝直接混接属建筑电气火灾主因：指引从配电箱重拉全程贯通阻燃铜芯线，接头用铜铝"
             "过渡端子+抗氧化膏；绝不在含铝回路接高发热连续负载。",
        actions=[
            M("请持证电工确认全程线径一致为铜芯（严禁中间夹铝线），铜铝连接点用铜铝过渡端子"
              "（摩擦焊/钎焊）并涂抗氧化导电膏，规范扭矩压接+定期复紧。",
              "重拉全程阻燃铜芯线（规范指引，不代执行）"),
            N("electrical.guide_rewire_full_copper", "输出重拉全程铜线操作指引（只给步骤，不碰配电箱）"),
        ],
        notes=["墙内暗埋『麻花拧+胶布』接头是定时炸弹；本工具只读风险提示，施工由持证电工完成。"],
        caveats=["电气改造必须由持证电工按规范执行；本工具绝不测量接触电阻、绝不下发任何电气写命令。"],
        standards=["[国家] GB/T 16895.7（特殊装置或场所，接线要求）",
                  "[国家] GB 50303（建筑电气工程施工质量验收规范）"],
    ),
    Task(
        id="electrical_rcd_guidance",
        platform="any",
        title="装设接地 + ≤30mA RCD/RCBO（规范指引）",
        category="maintenance",
        risk="low",
        desc="无可靠接地缺失 RCD 配合时，设备碰壳即触电；指引检查 PE 有效性并装设额定动作电流"
             "≤30mA 的 RCD/RCBO，定期验证动作。",
        actions=[
            M("配电箱确保配备额定动作电流 ≤30mA 的 RCD（IEC 61008）或 RCBO（IEC 61009），"
              "确认保护接地 PE 有效，定期按试验钮验证动作。",
              "装设接地+RCD（规范指引，不代执行）"),
            N("electrical.guide_install_rcd", "输出 RCD/RCBO 装设指引（只给步骤，不碰配电箱）"),
        ],
        notes=["RCD 是防触电最后一道闸，须在心室颤动前（≤30mA）切断；老式无接地布线缺此配合。"],
        standards=["[国家] GB 13955（剩余电流动作保护装置安装和运行）",
                  "[国际] IEC 61008（RCCB）/ IEC 61009（RCBO，等同 GB/T 16917）"],
    ),
    Task(
        id="electrical_outlet_replacement",
        platform="any",
        title="更换老化插座 + 加装 AFDD（规范指引）",
        category="maintenance",
        risk="low",
        desc="松动/老化插座弹片疲劳、接触电阻倍增且易激发串联电弧（需 AFDD 检测）；指引更换"
             "GB/T 2099 阻燃 PC 插座+标准底盒，并在配电箱加装 AFDD。",
        actions=[
            M("淘汰老旧插座/木底座，更换符合 GB/T 2099 的阻燃 PC 插座+标准阻燃底盒；规范配线清灰；"
              "配电箱加装 AFDD（GB/T 31143 等同 IEC 62606）防串联电弧。",
              "更换插座+加装 AFDD（规范指引，不代执行）"),
            N("electrical.guide_replace_outlet", "输出换插座+AFDD 指引（只给步骤，不碰配电箱）"),
        ],
        notes=["普通保险丝/空开对串联电弧完全失明，只有 AFDD 能识别；消除松动接头即除电弧源。"],
        standards=["[国家] GB/T 2099.1（家用插头插座，灼热丝耐燃）",
                  "[国家] GB/T 31143（AFDD，等同 IEC 62606）"],
    ),
]
