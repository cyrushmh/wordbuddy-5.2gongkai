"""AP 集中控制器审计任务（platform=any，跨平台）。

只读审计本机/网内 AP 栈（hostapd / NetworkManager 共享热点 / dnsmasq / apcontroller 思路），
给出集中管理 WiFi 的合规指引。任何改 hostapd/dnsmasq、用 apcontroller 下发 AP Group 配置一律只给
规范指引，不代执行——严守只读红线。
"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="apctrl_report",
        platform="any",
        title="AP 集中控制器只读审计（hostapd/NetworkManager/dnsmasq/apcontroller）",
        category="maintenance",
        risk="low",
        desc="只读审计本机/网内有哪些 AP 栈与集中管理痕迹：hostapd 配置（不回显口令）、"
             "NetworkManager 共享热点、dnsmasq DHCP/DNS、apcontroller 思路的脚本/配置目录；"
             "给出集中下发 WiFi 配置的合规指引。绝不读解密口令、绝不改任何 AP 配置。",
        actions=[
            N("apctrl.apctrl_report", "端到端生成 AP 集中控制器审计报告（各 AP 栈探测→集中管理思路→合规指引）"),
        ],
        notes=["AP 只读审计：只探测、只给指引、绝不下发配置、绝不读解密口令。"],
        standards=["[国际] hostapd（IEEE 802.11 AP 守护进程）",
                  "[国际] NetworkManager / dnsmasq（AP/热点/DHCP-DNS）",
                  "[学习] obsy/apcontroller：cron 轮询 + scp/ssh 取数 + AP Group 下发 + known_hosts 防 MITM"],
    ),
    Task(
        id="apctrl_push_guidance",
        platform="any",
        title="AP Group 下发 WiFi 配置（规范指引）",
        category="maintenance",
        risk="low",
        desc="给出按 AP Group 集中下发 WiFi 配置的规范指引（obsy/apcontroller 思路），绝不自动下发。",
        actions=[
            M("cron 驱动、scp 取现状快照、key-based（dropbear）+ known_hosts 固定指纹连 AP；"
              "只下发增量，现有未纳入模板的配置不触碰。",
              "AP Group 下发 WiFi 配置（规范指引，不代执行）"),
            N("apctrl.guide_push_apgroup", "输出 AP Group 下发 WiFi 配置指引（只给步骤，不改任何 AP）"),
        ],
        notes=["下发属于写操作，一律只给规范指引；是否施工由用户在控制器或厂商工具确认。"],
        standards=["[学习] obsy/apcontroller：不读不改现有配置、known_hosts 防 MITM、key-based 免密"],
    ),
]
