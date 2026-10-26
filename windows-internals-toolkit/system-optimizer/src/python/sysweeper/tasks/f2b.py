"""fail2ban 学习应用任务（f2b，platform=any，v0.6.84）——十二都天神煞大阵 task 侧。

学习 fail2ban 的架构模式与分级响应思想（单一守护进程统观全部日志源、按规则集中
响应，如十二神煞环绕一周），落为只读咨询。fail2ban 为 GPL-2.0（强拷贝左）项目，
本仓库不 vendored 其源代码，只引用官方源并做原创模式总结。

任何配置建议仅以文本交还用户，由用户沿原路执行——绝不代写 jail.local、
绝不重启 fail2ban、绝不代行封禁/解封。

指导理念：道法自然 · 活在当下 · 只有生存才能发展 · 在发展中能更好的生存 · 如此循环，亦复如是。
"""

from __future__ import annotations

from ..models import Action, Task

M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="f2b_report",
        platform="any",
        title="fail2ban 学习应用只读咨询（十二都天神煞大阵：探测/解析/模式学习，只读不写）",
        category="maintenance",
        risk="low",
        desc="只读探测本机 fail2ban 安装状态、只读解析 jail.local/jail.d 配置、"
             "学习其六层架构模式（jail/filter/action/threshold/daemon/client）与分级响应思想，"
             "并给出常见 jail 对照。未安装则降级为模式学习，不虚构战果。",
        actions=[
            N("f2b.f2b_report", "端到端生成十二都天神煞大阵只读咨询报告（探测→jail 登记→模式学习→建议）"),
            N("f2b.environment_report", "环境概览：安装判定与配置目录（只读）"),
        ],
        notes=[
            "不 vendored fail2ban 源代码（GPL-2.0 强拷贝左）：只引用官方源、只做原创模式总结。",
            "fail2ban-client 仅调用白名单只读子命令（status/version/get），写操作子命令一律不碰。",
            "活在当下：本机未安装则降级为模式学习，不虚构战果。",
            "只有生存才能发展：先设 ignoreip 白名单再启用任何 jail——把自己封在门外是生存事故。",
        ],
        standards=["[学习] fail2ban 官方源 https://github.com/fail2ban/fail2ban（GPL-2.0，不 vendored 源码）",
                   "[理念] 十二都天神煞大阵：集中观测/分级响应/白名单防误封/循环上升"],
    ),
    Task(
        id="f2b_jail_guidance",
        platform="any",
        title="fail2ban jail 配置规范指引（仅文本，沿原路返回）",
        category="maintenance",
        risk="low",
        desc="给出 jail 配置建议文本（SSH 基础防护/白名单防误封/累犯分级升级），"
             "含 maxretry/findtime/bantime 语义说明；是否写入配置由用户执行。",
        actions=[
            M("[DEFAULT] ignoreip = 127.0.0.1/8 ::1（先白名单再启用 jail）；"
              "[sshd] enabled=true maxretry=3 findtime=600 bantime=3600；"
              "[recidive] 一天内被封 3 次者升级为一周——bantime 递增优于一次性永久封禁。",
              "fail2ban jail 配置规范指引（不代写、不重启、不代行封禁）"),
            N("f2b.consult", "输出 jail 配置建议文本（只读咨询，沿原路返回）"),
        ],
        notes=[
            "配置是写操作，一律只给文本；fail2ban 服务重启与封禁/解封由用户执行。",
            "道法自然：阈值分级、退避递进，不一刀切、不骤然绝杀。",
        ],
        standards=["[理念] 原路返回：建议仅以文本交还用户，不代行写操作"],
    ),
]
