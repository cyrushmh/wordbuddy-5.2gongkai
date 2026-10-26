"""IPP 打印协议发现任务（ipp，platform=any，跨平台）。

只读发现 IPP 打印设备（CUPS / Avahi mDNS / 本地管理页），绝不 lpadmin 加打印机、绝不改 CUPS 配置、
绝不发布 mDNS 服务——严守只读红线。
"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="ipp_report",
        platform="any",
        title="IPP 打印协议发现只读报告（CUPS / mDNS / 本地管理页）",
        category="maintenance",
        risk="low",
        desc="只读发现 IPP 打印设备：CUPS 队列（lpstat -v）、网内 mDNS（avahi-browse _ipp._tcp）、"
             "CUPS 管理页 localhost:631 可达性、协议标准（RFC 8010/8011/IPP Everywhere）。"
             "绝不改打印队列、绝不连控制端口写。",
        actions=[
            N("ipp.ipp_report", "端到端生成 IPP 打印协议发现报告（CUPS→mDNS→本地管理页→协议标准）"),
        ],
        notes=["IPP 只读发现：只发现、只给指引、绝不写打印配置。"],
        standards=["[国际] RFC 8010（IPP 编码）/ RFC 8011（IPP 模型与语义）",
                  "[国际] IPP Everywhere（PWG 5100.14，驱动无关打印）",
                  "[国际] PWG 标准打印（AirPrint / IPP-over-USB 同源思路）"],
    ),
    Task(
        id="ipp_add_guidance",
        platform="any",
        title="添加 IPP 打印机（规范指引）",
        category="maintenance",
        risk="low",
        desc="给出用 lpadmin 添加 IPP 打印机的规范指引（IPP Everywhere 驱动无关），绝不自动加打印机。",
        actions=[
            M("先经 mDNS 或 CUPS Web 拿打印机 URI（ipp://...）；lpadmin -p <队列> -E -v <URI> -m everywhere。",
              "添加 IPP 打印机（规范指引，不代执行）"),
            N("ipp.guide_add_printer", "输出添加 IPP 打印机指引（只给步骤，不改 CUPS 配置）"),
        ],
        notes=["加打印机属于写操作，一律只给规范指引；是否施工由用户在系统设置或 CUPS 管理页确认。"],
        standards=["[国际] IPP Everywhere（PWG 5100.14）驱动无关模型"],
    ),
]
