"""Tor（洋葱路由）匿名/隐私网络只读诊断任务（platform="any"，v0.6.17「优化网络模块」）。

立项：把 Tor（The Onion Router，应用层洋葱加密覆盖网络）的「该看什么」钉进本工具——
tor 安装/版本、守护进程状态、torrc 关键配置（SOCKS/控制端口、桥接、可插拔传输、
中继/出口角色）、可插拔传输二进制就位情况。本任务只读，与 OSI/DNS/ZeroTier 共同
构成网络模块的「覆盖层/隐私层」视图。

参照（权威资料，仅用于把诊断维度钉死）：
- gitlab.torproject.org/tpo/core/tor —— Tor 源码（C/Rust；SOCKS 9050/9150、
  控制端口 9051/9151、torrc、Bridge、可插拔传输 obfs4/snowflake/meek/lyrebird）
- Tor 官方文档（FAQ / Relay 文档）—— 中继/出口节点的带宽与法务责任
"""
from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)

TOR = ("[上游] Tor（gitlab.torproject.org/tpo/core/tor；应用层洋葱加密覆盖网络，C/Rust；"
       "SOCKS 9050/9150、控制端口 9051/9151、torrc、Bridge、可插拔传输 obfs4/snowflake/meek）")


TASKS = [
    Task(
        id="tor_report",
        platform="any",
        title="Tor（洋葱路由）匿名/隐私网络只读诊断",
        category="network",
        risk="low",
        desc="只读核验 Tor 是否安装、版本、守护进程状态、torrc 关键配置（SOCKS/控制端口、"
             "桥接、可插拔传输、中继/出口角色）、可插拔传输二进制（obfs4/snowflake/meek/"
             "lyrebird）就位情况。与 OSI/DNS/ZeroTier 共同构成网络模块的覆盖层/隐私层视图。",
        actions=[
            N("tor.capabilities_report", "能力自检：各维度是否可诊断 + 红线声明"),
            N("tor.tor_report", "输出 Tor 匿名/隐私网络只读诊断"),
            M("做中继/出口、配桥接、改 torrc 等写操作由你决定（本工具不开此路径）",
              "改 Tor 配置（写操作，opt-in）"),
        ],
        standards=[TOR],
        notes=[
            "SOCKS 端口：客户端默认 9050，Tor 浏览器默认 9150；是本地代理入口。",
            "控制端口：默认 9051（浏览器 9151），可下发写命令——本工具只读、不连。",
            "桥接 + 可插拔传输（obfs4/snowflake/meek/lyrebird）：受审查网络靠它绕过封锁。",
            "中继/出口角色：做出口节点能看明文目的、有带宽与法务责任，需读懂 Relay 文档再定。",
            "torrc 中密钥/密码类敏感项只报存在、不打印明文。",
        ],
        caveats=[
            "只读任务：不启动/停止 tor、不改 torrc、不连控制端口、不连校外网做写操作。",
            "torrc 敏感配置（HashedControlPassword/HiddenServiceDir 等）只报存在，绝不回显。",
        ],
    ),
]
