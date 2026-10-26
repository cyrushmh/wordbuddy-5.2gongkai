"""OSI 七层网络诊断任务（platform="any"，v0.6.13「以 OSI 为基础整体补全」）。

立项：network.py 已有零散只读报告（iproute2/ethtool/tc/conntrack…）与调优开关，
但缺一个「按 OSI 七层把本机网络栈整体读一遍」的只读入口。本任务把 L1–L7
结构化、只读地覆盖，复用 network 只读报告与 common.run，绝不写系统。

参照（权威文档，仅用于把「该看什么」钉死）：
- ISO/IEC 7498-1:1994 / ITU-T X.200           —— 七层模型与每层服务定义
- RFC 1122 / 1123                              —— TCP/IP 各层实现与运维要求
- RFC 791/2460/792 · 9293/768 · 8446/7858/8484 —— 各层核心协议
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)

X200 = ("[国际] ISO/IEC 7498-1:1994 / ITU-T X.200（OSI 七层参考模型，分层与服务定义）")
RFC1122 = ("[国际] IETF RFC 1122 / RFC 1123（TCP/IP 各层的实现与运维要求）")
RFCSTACK = ("[国际] RFC 791(IP)/2460(IPv6)/792(ICMP) · 9293(TCP)/768(UDP) · "
            "8446(TLS)/7858(DoT)/8484(DoH)/1035(DNS)")


TASKS = [
    Task(
        id="osi_report",
        platform="any",
        title="OSI 七层网络诊断（L1 物理→L7 应用，整体只读）",
        category="network",
        risk="low",
        desc="以 OSI 参考模型为骨架，把本机网络栈按 L1 物理层到 L7 应用层结构化、"
             "只读地摸一遍：接口/载波/速率、MAC/MTU/卸载、IP/路由/防火墙、监听/"
             "拥塞/连接跟踪、会话保活/隧道、TLS/DoT·DoH、DNS/可达性。",
        actions=[
            N("osi.capabilities_report", "能力自检：每层是否可诊断 + 红线声明"),
            N("osi.osi_report", "输出 L1–L7 整体只读诊断（每层附参照文档）"),
            M("要探外网可达性：osi probe --url https://<host>（显式、可审计、不默认开）",
              "L7 外网探测（只读，由你决定要不要做）"),
        ],
        standards=[X200, RFC1122, RFCSTACK],
        notes=[
            "L1 物理层读 /sys/class/net 的 carrier/operstate/speed/duplex/device 软链，"
            "据此判断总线后端是 PCIe/USB/虚拟——不依赖任何外部命令。",
            "L2–L4 复用 ip/ss/ethtool/conntrack 的只读项；写操作（ethtool -K、tc qdisc add）"
            "一律留在 network 模块的 opt-in 任务里，本任务不碰。",
            "L5–L6 读 sysctl 保活、WireGuard/VTI 隧道特征、openssl 密码套件与解析器配置"
            "（/etc/resolv.conf、systemd-resolved）。",
            "L7 默认只做 DNS 解析与本地回环监听自检，绝不默认连校外网；要探外网用 "
            "probe_http（仅 http/https + 短超时）。",
        ],
        caveats=[
            "只读任务：不增删地址、不改路由、不 reload 防火墙、不连校外网做写操作。",
            "报告里的「参照」是文档来源，不是命令；照着优化是 opt-in 的下游动作。",
        ],
    ),
]
