"""网络链接协议与多设备自组网任务定义（v0.6.66；原 network.py 拆分）。

按 omni 子系统「按 key 归位」原则，本文件 ↔ `netlink` 子系统；原
`network.py` 中的 net_* 相关任务迁到此处（id 不变——`sysweaver netlink
list` 命令按 id 列举，cli.py 不关心任务定义在哪个文件）。

链路层/传输层协议注册与本机只读能力探测；mesh 自组网（UDP 发现 +
TCP 命令通道，命令白名单 info/ping/probe/msg，**绝不执行对端发来的
任意命令**）；人机交互 msg 仅回显。

对应 native 层：`native/netlink.py`（link_report / mesh_serve /
mesh_discover / mesh_info / mesh_send_msg / environment_report）。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)
S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)


TASKS = [
    # ------------------------------------------------------------------ #
    # 链接协议注册表 + 本机能力（只读）                                    #
    # ------------------------------------------------------------------ #
    Task(
        id="net_link_protocols",
        platform="any",
        title="导入多种网络链接协议（注册表 + 本机能力）",
        category="network",
        risk="low",
        opt_in=False,
        standards=[
            "[国际] IETF RFC 9293（TCP）/ RFC 768（UDP）",
            "[国际] IEEE 802.15.1（蓝牙）/ IEEE 802.15.4（低速率无线个域网）",
            "[国际] Bluetooth SIG RFCOMM / GATT（串口模拟与属性协议）",
        ],
        desc="按各协议自身的规范登记链接层/传输层协议（TCP、UDP、蓝牙 RFCOMM、串口 UART、"
             "BLE 低功耗蓝牙、802.15.4），并只读探测本机是否具备对应能力。",
        actions=[N("netlink.link_report", "列出链接协议注册表与本机能力（只读）")],
        notes=[
            "注册表：TCP(RFC 9293)、UDP(RFC 768)、RFCOMM(蓝牙串口模拟)、"
            "串口(UART/RS-232)、BLE(GATT)、802.15.4(低速率无线个域网，如 Zigbee/Thread 底层)。",
            "每项自带官方组织与文档出处，能力探测只读，非本机具备的协议优雅降级为「未探测到」。",
        ],
        caveats=["探测只判断接口可用性，不代表已配对/已授权设备。"],
    ),
    Task(
        id="net_link_env",
        platform="any",
        title="链接子系统环境总览（IPv4/IPv6 双栈与外网连通，只读）",
        category="network",
        risk="low",
        desc="读本机网络命名空间的接口/地址概要与 IPv4/IPv6 双栈外网连通性，定位「能发现但不能通信」的层。",
        actions=[N("netlink.environment_report", "链接子系统环境总览（接口/地址/双栈连通，只读）")],
        standards=[
            "[国际] IETF RFC 791（IPv4）/ RFC 8200（IPv6）",
            "[国际] IETF RFC 4291（IPv6 寻址架构，::1/fe80::/ULA/全球单播）",
            "[国际] ICMPv6（RFC 4443） Echo Request（连通性只读探测）",
        ],
        notes=[
            "mesh 自组网跑在 UDP/TCP 之上，先确认双栈基础连通再排组网故障。",
            "本机概要与外网连通均只读探测，不发送任何业务数据。",
            "macOS 用 ifconfig/netstat 等价只读命令，Windows 走 ipconfig，保证跨平台一致口径。",
        ],
        caveats=["输出含本机 IP/MAC 地址，属本机自检，勿外传。"],
    ),
    # ------------------------------------------------------------------ #
    # 多设备自组网（mesh）：发现 + 命令通道 + 人机交互                     #
    # ------------------------------------------------------------------ #
    Task(
        id="net_mesh_serve",
        platform="any",
        title="启用本地自组网（多设备自通信 + 人机交互）",
        category="network",
        risk="low",
        opt_in=True,
        standards=["[国际] IETF RFC 1112（IP 组播）/ RFC 768（UDP 广播发现）",
                   "[国际] IETF RFC 9293（TCP 可靠命令通道）"],
        desc="启用网络后让多于 1 台设备自己通信：UDP 广播发现邻居 + TCP 可靠命令通道；"
             "命令通道只有 info/ping/probe/msg 四个只读安全命令，"
             "**绝不执行对端发来的任意命令**。",
        actions=[N("netlink.mesh_serve", "启动本地自组网节点（守护线程，可重复调用）")],
        notes=[
            "发现：UDP 受限广播信标；可靠通道：TCP；命令白名单：info/ping/probe/msg。",
            "人机交互：msg 通道仅回显并记录到会话收件箱，不触发任何写操作。",
            "握手自带 share 字段：宣告愿共享的算力（CPU/GPU/NPU/TPU/内存/网络）"
            "与永不共享的数据（个人数据/关键资产）。",
        ],
        caveats=["需在可信局域网内启用；跨公网暴露需自行做访问控制。"],
    ),
    Task(
        id="net_mesh_discover",
        platform="any",
        title="发现本网段内的其他设备（只读）",
        category="network",
        risk="low",
        opt_in=True,
        desc="广播发现本网段内同样启用自组网的设备，列出名称/地址/版本/链接能力。",
        standards=["[国际] IETF RFC 1112（IP 组播）/ RFC 768（UDP 发现信标）"],
        actions=[N("netlink.mesh_discover", "发现 mesh 节点（只读）")],
        notes=["只在本地网段发信标，不向外网发送数据。"],
    ),
    Task(
        id="net_mesh_hci",
        platform="any",
        title="设备间人机交互消息（msg 通道）",
        category="network",
        risk="low",
        opt_in=True,
        desc="通过 mesh 的消息通道与已发现设备互发文本（人机交互）；"
             "仅回显与记录到会话收件箱，不执行、不落盘。",
        standards=["[国际] ISO 9241-171（人机交互无障碍与交互通道）",
                   "[国际] IETF RFC 9293（TCP 可靠传输）"],
        actions=[N("netlink.mesh_send_msg", "发送一条人机交互消息（仅回显）")],
        notes=["消息通道属于只读安全白名单内的命令；对端任何非白名单命令一律被忽略。"],
    ),
]
