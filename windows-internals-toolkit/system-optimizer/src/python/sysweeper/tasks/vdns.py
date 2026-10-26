"""虚拟根 DNS 与多 CDN 任务（vdns，platform=any，跨平台）。

只读观测根 DNS（resolv.conf / DoH-DoT）、多 CDN 选择与健康；绝不改 resolv.conf、绝不切 DoH/DoT、
绝不改 hosts——严守只读红线。
"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="vdns_report",
        platform="any",
        title="虚拟根 DNS 与多 CDN 只读报告",
        category="maintenance",
        risk="low",
        desc="只读观测虚拟根 DNS（/etc/resolv.conf nameserver、DoH/DoT 是否可用）、多 CDN 选择"
             "（/etc/hosts 与常见 CDN 域名）与一次良性解析健康。绝不改 DNS、绝不切 DoH/DoT。",
        actions=[
            N("vdns.vdns_report", "端到端生成虚拟根 DNS 与多 CDN 报告（根 DNS→多 CDN→解析健康）"),
        ],
        notes=["vdns 只读观测：只观测、只给指引、绝不写 DNS 配置。"],
        standards=["[国际] RFC 1035（DNS）/ RFC 7858（DoT）/ RFC 8484（DoH）",
                  "[国际] resolv.conf（/etc/resolv.conf 解析顺序）",
                  "[国际] 常见 CDN（Cloudfront/Fastly/Akamai/AliCDN…）"],
    ),
    Task(
        id="vdns_doh_guidance",
        platform="any",
        title="启用 DoT/DoH（规范指引）",
        category="maintenance",
        risk="low",
        desc="给出启用 DoT/DoH 的规范指引（systemd-resolved / stubby / cloudflared），绝不自动改 DNS。",
        actions=[
            M("systemd-resolved 写 DNSOverTLS=opportunistic + DNS=<DoT 服务>；或装 stubby/cloudflared "
              "作本地 stub，resolv.conf 指向 127.0.0.1#53。",
              "启用 DoT/DoH（规范指引，不代执行）"),
            N("vdns.guide_doh", "输出启用 DoT/DoH 指引（只给步骤，不改 DNS 配置）"),
        ],
        notes=["改 DNS 属于写操作，一律只给规范指引；是否施工由用户在网络管理或厂商工具确认。"],
        standards=["[国际] RFC 7858（DNS over TLS）/ RFC 8484（DNS over HTTPS）"],
    ),
]
