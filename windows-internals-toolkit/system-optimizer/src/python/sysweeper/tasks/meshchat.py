"""组网通信任务（platform="any"）：iptux / 飞鸽传书（IPMsg）兼容 + wall 式全体广播。

立项三句话：

1. **同网段的设备，不需要经过外网就能互相说话。** 断网、隔离网、野外作业、
   家里宽带断了——只要还在同一个局域网，消息就应该能到。
2. **兼容现成的协议，而不是自创一套。** IPMsg（飞鸽传书）是 1996 年 Shirouzu
   定下的公开协议，Linux 上的 iptux 就是它的开源实现。按它的包格式走，
   网里已有的飞鸽 / iptux 客户端能直接收到我们的消息——**不用说服所有人装新软件**。
3. **收到的东西不自动落盘。** 图片、视频、文件一律进**待收清单**，由你显式接受。
   自动接收 = 别人能往你机器里塞东西，这条口子绝不开。

消息类型覆盖：文字 / 图片 / 视频 / 文件 / emoji / 颜文字——**只是载荷类型不同**，
通道是同一条，不需要为每种类型造一套协议。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)

IPMSG = ("[国际] IPMsg（飞鸽传书）协议：UDP/TCP 2425，包格式 `版本:序号:用户:主机:命令字:附加`")
IPTUX = ("[开源] iptux —— Linux 下的 IPMsg 协议开源实现（GPL）")
WALL = ("[国际] POSIX `wall` —— 向所有登录终端广播消息（IEEE Std 1003.1）")
EMOJI = ("[国际] Unicode Emoji（UTS #51）与 Unicode 全角符号区（颜文字素材）")
BROADCAST = ("[国际] RFC 919 / RFC 922 IP 广播与受限广播（局域网发现机制）")


TASKS = [
    # ---- 只读：协议兼容核对 ----
    Task(
        id="meshchat_protocol",
        platform="any",
        title="组网通信协议核对（IPMsg / 飞鸽传书 / iptux 兼容）",
        category="network",
        risk="low",
        desc="核对本机对 IPMsg（飞鸽传书）协议的编解码能力：命令字、选项位、附件属性串、"
             "UDP 2425 消息 / TCP 2425 文件。只读核对，不发包。",
        actions=[
            N("meshchat.protocol_report", "列出命令字 / 选项位 / 端口与包格式核对结果（只读）"),
        ],
        standards=[IPMSG, IPTUX, WALL, BROADCAST],
        notes=[
            "包格式是六个字段：`版本:序号:用户:主机:命令字:附加`，命令字 = 基本命令 | 选项位，"
            "全部十进制。端口 2425（0x0979），消息走 UDP，文件走 TCP。",
            "为什么要兼容现成协议而不是自创：网里已有的飞鸽 / iptux 客户端能直接收到消息，"
            "**不用说服所有人装新软件**——自创协议在真实环境里等于没人可用。",
            "字段里的冒号用转义（`:` 在文件属性串里很常见），解析按转义切分，"
            "不按裸 split(':')——后者遇到 `a:photo.png` 这种名字就会解析错。",
        ],
        caveats=[
            "只读任务：只核对编解码与常量表，不发包、不监听。",
            "IPMsg 是明文协议且默认无认证，只适合可信局域网；跨公网请走加密通道。",
        ],
    ),
    # ---- 只读：表情与颜文字 ----
    Task(
        id="meshchat_emoji",
        platform="any",
        title="表情与颜文字支持核对（emoji / kaomoji）",
        category="network",
        risk="low",
        desc="核对 emoji（Unicode Emoji，UTS #51）与颜文字（全角符号拼组）的分类与显示支持，"
             "确认哪些能在对端正常显示。",
        actions=[
            N("meshchat.emoji_report", "emoji 分类与显示核对（只读）"),
            N("meshchat.kaomoji_report", "颜文字素材核对（只读）"),
        ],
        standards=[EMOJI, IPMSG],
        notes=[
            "emoji 走 Unicode 标准码位（UTS #51），只要两端字库有就能显示；"
            "颜文字是**普通字符拼组**（＾▽＾ 之类），零依赖、任何终端都能显示——"
            "在老设备和纯文本环境里比 emoji 更可靠。",
            "消息类型（文字/图片/视频/文件/emoji/颜文字）**只是载荷类型不同**，"
            "通道是同一条，不需要为每种类型各造一套协议。",
        ],
        caveats=[
            "只读任务：只核对，不发送。",
            "emoji 显示依赖对端字库；颜文字依赖等宽字体，否则可能错位。",
        ],
    ),
    # ---- 只读：收件箱与待收文件 ----
    Task(
        id="meshchat_inbox",
        platform="any",
        title="收件箱与待收文件核对（收到的东西不自动落盘）",
        category="network",
        risk="low",
        desc="列出已收消息与**待收文件清单**。收到的图片/视频/文件一律不自动落盘，"
             "需你显式接受——自动接收等于别人能往你机器里塞东西。",
        actions=[
            N("meshchat.inbox_report", "列出收件箱与待收文件清单（只读）"),
        ],
        standards=[IPMSG, IPTUX],
        notes=[
            "处置纪律：文件类载荷进**待收清单**并给出大小与来源，接受才落盘——"
            "这是本层最重要的一条安全边界。",
            "对超大载荷设上限，超限直接拒绝并在清单里标注，不硬扛（防止内存被吃光）。",
        ],
        caveats=[
            "只读任务：只列清单，不接收、不落盘、不打开任何文件。",
            "来源只显示 IP:端口，不做主机名反解（避免 DNS 侧信道与伪造 PTR）。",
        ],
    ),
    # ---- 动作：发送（medium，需 --apply --yes）----
    Task(
        id="meshchat_send",
        platform="any",
        title="组网通信发送（单播 / 全体广播 / 带附件，需 --apply）",
        category="network",
        risk="medium",
        desc="向同网段设备发送文字、图片、视频、文件，或用 wall 式全体广播通知所有终端。"
             "**这是会发包的实际动作，需 --apply 且 --yes 才执行。**",
        actions=[
            N("meshchat.wall_text", "全体广播：向网段内所有设备发一条通知（wall 语义）"),
            M("单播：meshchat.send_text(目标IP, 文本)   "
              "（UDP 2425；要回执就带 SENDCHECK 选项位）", "向指定设备发文字"),
            M("带附件：meshchat.send_files(目标IP, [文件...], 文本)   "
              "（附件走 TCP 2425，需对端接受）", "发图片 / 视频 / 文件"),
            M("上下线：meshchat.announce() / meshchat.say_goodbye()   "
              "（BR_ENTRY / BR_EXIT，让网内设备看到你）", "广播上线 / 下线"),
        ],
        standards=[IPMSG, IPTUX, WALL, BROADCAST],
        notes=[
            "全体广播（wall 语义）用受限广播地址，同网段的终端都能收到——断网时这是"
            "**最可靠的通知方式**，不依赖任何外部服务器。",
            "要回执就带 SENDCHECK 选项位（0x0100）：对端收到会回 RECVMSG，"
            "你才知道消息到了；不要回执就不带，省一次往返。",
            "带附件时先发消息包（含 FILEATTACHOPT 与文件属性串），对端主动来 TCP 2425 取——"
            "**是对方拉，不是我们推**，这样对端可以拒绝。",
            "IPMsg 明文且无认证，只适合可信局域网；跨公网请另走加密通道。",
        ],
        caveats=[
            "**会实际发包**：需 --apply 且 --yes 才执行，默认只打印计划。",
            "广播会影响网段内所有设备；公共网络慎用，勿用于打扰他人。",
            "附件是对端来取，你这边要保持在线直到对端取完。",
        ],
    ),
]
