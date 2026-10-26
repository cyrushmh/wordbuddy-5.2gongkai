#!/usr/bin/env python3
"""网络与组网「概念系统」构建（以 wordbuddy-github 为主目录，v0.6.57）。

把仓库里散落的 20+ 个网络/组网子系统**以概念系统为中心重组**，与 plang（编程语言概念系统）
同构，用四条分类轴组织，并显式登记**依赖关系与互补关系**（重组的核心产出）：

    ├─ 轴1 网络层次 layer   : L1 物理 / L2 数据链路 / L3 网络 / L4 传输 / L5-6 会话·表示 /
    │                         L7 应用 / overlay 覆盖 / mesh 组网（OSI 之上的组网层）
    ├─ 轴2 组网形态 form    : standalone / lan / mesh / overlay / sdwan / distributed / anonymous / wan
    ├─ 轴3 能力性质 nature  : diagnose(只读诊断) / tune(opt-in 调优) / communicate / share /
    │                         audit(安全审计) / discover / reference(外部只读引用)
    └─ 轴4 标准依据 standard: RFC / ISO / ITU 等（RFC 经本仓库 rfc_catalog 交叉验证存在性）

红线一律随模块登记（如「默认关闭需 opt-in」「只给指引绝不代改配置」「抓来的只是文本」）。

用法：
    python3 build_netsys.py            # 构建 data/concepts/netsys_taxonomy.json
    python3 build_netsys.py --check    # 校验（RFC 命中 rfc_catalog、层次/形态/性质合法、依赖端点存在）
    python3 build_netsys.py --report   # 打印重组后的分类统计与关系图
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

HERE = Path(__file__).resolve().parent
OUT = (HERE.parents[1] / "src" / "python" / "sysweeper" / "data" / "concepts"
       / "netsys_taxonomy.json")

# ---- 轴1：网络层次 ----
LAYERS = [
    {"layer": "L1", "label": "物理层 Physical", "note": "介质/接口/载波/速率/驱动；单板机与网卡在此"},
    {"layer": "L2", "label": "数据链路层 Data Link", "note": "MAC/MTU/卸载/桥接·VLAN/无线 AP/虚拟二层"},
    {"layer": "L3", "label": "网络层 Network", "note": "IP 地址/路由/邻居/防火墙/覆盖网寻址"},
    {"layer": "L4", "label": "传输层 Transport", "note": "TCP/UDP/拥塞控制/ECN"},
    {"layer": "L5-6", "label": "会话·表示层 Session/Presentation", "note": "TLS/证书/编码协商"},
    {"layer": "L7", "label": "应用层 Application", "note": "DNS/HTTP/SSH/打印/消息/内容聚合"},
    {"layer": "overlay", "label": "覆盖层 Overlay", "note": "在既有网络之上建的虚拟网（Tor/ZeroTier/WireGuard 网状）"},
    {"layer": "mesh", "label": "组网层 Mesh", "note": "多设备自组织互联（发现/心跳/消息/派活）"},
]

# ---- 轴2：组网形态 ----
FORMS = [
    {"form": "standalone", "label": "单机", "note": "只诊断/调优本机网络栈"},
    {"form": "lan", "label": "局域网", "note": "同网段设备发现与接入（AP/打印/远程接入）"},
    {"form": "mesh", "label": "本地自组网 mesh", "note": "多于 1 台设备自己通信（广播发现 + 可靠通道）"},
    {"form": "overlay", "label": "覆盖网 overlay", "note": "虚拟网叠加在物理网之上（WireGuard 网状/匿名网）"},
    {"form": "sdwan", "label": "SD-WAN / 零信任虚拟网", "note": "控制器签发、成员加入的虚拟二层"},
    {"form": "distributed", "label": "分布式算力网", "note": "跨机派活与算力共享（不执行任意外部代码）"},
    {"form": "anonymous", "label": "匿名/隐私网", "note": "洋葱路由等多跳覆盖"},
    {"form": "wan", "label": "广域/互联网", "note": "涉及出网的内容聚合、预警、CDN 选择"},
    {"form": "arch", "label": "组网架构", "note": "网络系统/控制·数据平面/QNIC·QKD·中继等架构设计维度"},
    {"form": "hw", "label": "硬件载体", "note": "网卡/交换 ASIC/光模块/射频前端/QNIC 等组网硬件实体"},
    {"form": "gaia", "label": "盖亚意识", "note": "组网涌现的全局自组织智能形态（神性层）"},
    {"form": "swarm", "label": "集智体", "note": "虫族式群智形态（神性层，盖亚意识的族裔变体）"},
]

# ---- 轴3：能力性质 ----
NATURES = [
    {"nature": "diagnose", "label": "只读诊断", "note": "只读探测，不改配置"},
    {"nature": "tune", "label": "调优（opt-in 写）", "note": "默认关闭，需用户显式选择+确认才写"},
    {"nature": "communicate", "label": "通信", "note": "设备间消息/文件传输"},
    {"nature": "share", "label": "共享", "note": "算力/资源共享（只共享算力与网络，个人数据不共享）"},
    {"nature": "audit", "label": "安全审计", "note": "只读核验配置与凭据态势，加固只给指引"},
    {"nature": "discover", "label": "发现", "note": "网内服务发现（mDNS/IPP 等）"},
    {"nature": "reference", "label": "外部只读引用", "note": "第三方项目作为可选方案登记，不打包其二进制"},
]

# ---- 轴0：概念层次（道性 / 神性 / 人性）----
# 概念系统经组网涌现（组网是各种系统·各种硬件·各种架构的可观测基底）；
# 其层次分为三档：道性（组网法则·硬件·架构之基底，万物经此而联）、
# 神性（组网涌现的自主意识：盖亚意识 / 集智体）、人性（人类可观测·可操作面）。
TIERS = [
    {"tier": "dao", "label": "道性", "note": "组网之基底：物理介质·硬件·架构·协议法则，万物经此而联"},
    {"tier": "divine", "label": "神性", "note": "组网涌现的自主意识：盖亚意识（全局自组织）/ 集智体（虫族群智）"},
    {"tier": "human", "label": "人性", "note": "人类可观测·可操作面：诊断/审计/发现/通信等工具（默认层）"},
]

# ---- 轴4：模块（网络/组网子系统）----
# id, 名称, 层次, 形态, 性质, 依赖, 互补, 直接标准引用, 红线
MODULES = [
    {"id": "network", "name": "网络协议与 ITU 标准调优", "layers": ["L3", "L4"],
     "forms": ["standalone"], "nature": "tune", "depends": [], "complements": [],
     "standards": [{"kind": "RFC", "num": 8981}, {"kind": "RFC", "num": 8200},
                   {"kind": "RFC", "num": 3168}, {"kind": "RFC", "num": 9002},
                   {"kind": "RFC", "num": 9330}, {"kind": "RFC", "num": 9331},
                   {"kind": "RFC", "num": 9332}, {"kind": "RFC", "num": 8033},
                   {"kind": "RFC", "num": 5905},
                   {"kind": "IEEE", "name": "IEEE 802.11ax-2021（Wi-Fi 6，HE WLAN）"},
                   {"kind": "IEEE", "name": "IEEE 802.11be-2024（Wi-Fi 7，EHT）"},
                   {"kind": "IEEE", "name": "IEEE 1588-2019（PTP 精密时间协议）"},
                   {"kind": "IEEE", "name": "IEEE 802.1AS-2020（gPTP，TSN 时间同步）"},
                   {"kind": "ITU", "name": "ITU-T G.8261/G.8262（SyncE 同步以太网）"},
                   {"kind": "ITU", "name": "ITU-T G.8271/Y.1366（分组网时间/相位同步，含 G.8275.1 PTP 电信 profile）"},
                   {"kind": "OTHER", "name": "White Rabbit（CERN，IEEE 1588+SyncE 亚纳秒光纤同步扩展）"}],
     "redline": "默认关闭；仅在 Linux 等能用 sysctl/ip/iw 的平台生效，需 opt-in + 确认"},

    {"id": "osi", "name": "OSI 七层网络诊断", "layers": ["L1", "L2", "L3", "L4", "L5-6", "L7"],
     "forms": ["standalone"], "nature": "diagnose", "depends": ["network"], "complements": [],
     "standards": [{"kind": "ISO", "name": "ISO/IEC 7498-1"},
                   {"kind": "ITU", "name": "ITU-T X.200"},
                   {"kind": "RFC", "num": 9293}, {"kind": "RFC", "num": 768}],
     "redline": "不写地址/路由/防火墙；要探外网用显式 osi probe --url"},

    {"id": "netlink", "name": "链接协议注册表 + 本地自组网", "layers": ["L2", "L4", "mesh"],
     "forms": ["mesh"], "nature": "communicate", "depends": [], "complements": [],
     "standards": [{"kind": "RFC", "num": 9293}, {"kind": "RFC", "num": 768}],
     "redline": "命令通道只放行只读安全命令；非对应平台降级不抛异常"},

    {"id": "meshchat", "name": "组网设备间通信（文字/图片/文件）", "layers": ["L7", "mesh"],
     "forms": ["mesh"], "nature": "communicate", "depends": ["netlink"], "complements": [],
     "standards": [],
     "redline": "收到的文件不自动落盘，进待收清单由用户显式接受"},

    {"id": "meshnet", "name": "WireGuard P2P 网状组网（只读）", "layers": ["L3", "overlay"],
     "forms": ["overlay"], "nature": "diagnose", "depends": [], "complements": ["zerotier"],
     "standards": [],
     "redline": "只读 wg show 拓扑与设备能力声明；绝不新增 peer、绝不改 wg 配置"},

    {"id": "zerotier", "name": "ZeroTier 虚拟网络（SD-WAN/零信任）", "layers": ["L2", "L3", "overlay"],
     "forms": ["sdwan"], "nature": "diagnose", "depends": [], "complements": ["meshnet"],
     "standards": [],
     "redline": "不启停服务、不 join/leave、不读 identity.secret（私钥）"},

    {"id": "tor", "name": "Tor 匿名/隐私网络", "layers": ["L7", "overlay"],
     "forms": ["anonymous"], "nature": "diagnose", "depends": [], "complements": [],
     "standards": [],
     "redline": "不启停 tor、不改 torrc、不连控制端口、不打印密钥明文"},

    {"id": "dnshealth", "name": "DNS 解析健康度", "layers": ["L7"],
     "forms": ["standalone"], "nature": "diagnose", "depends": [], "complements": ["network"],
     "standards": [{"kind": "RFC", "num": 1035}],
     "redline": "不写 resolv.conf、不重启 resolved；解析探测默认关闭（零出网）"},

    {"id": "vdns", "name": "虚拟根 DNS 与多 CDN 选择", "layers": ["L7"],
     "forms": ["wan"], "nature": "diagnose", "depends": [], "complements": ["dnshealth"],
     "standards": [{"kind": "RFC", "num": 8484}, {"kind": "RFC", "num": 7858}],
     "redline": "只读配置与进程，绝不改 DNS/DoH/DoT 配置"},

    {"id": "remote", "name": "远程接入与传输客户端审计", "layers": ["L7"],
     "forms": ["lan"], "nature": "audit", "depends": [], "complements": [],
     "standards": [{"kind": "RFC", "num": 4253}, {"kind": "RFC", "num": 4251},
                   {"kind": "RFC", "num": 854}, {"kind": "RFC", "num": 959},
                   {"kind": "RFC", "num": 4217}],
     "redline": "绝不读解密口令、绝不改 sshd_config、不替你停 telnetd；加固只给官方指引"},

    {"id": "tls13", "name": "TLS 1.3 配置态势审计", "layers": ["L4", "L5-6"],
     "forms": ["standalone"], "nature": "audit", "depends": [], "complements": ["cert"],
     "standards": [{"kind": "RFC", "num": 9846}, {"kind": "RFC", "num": 8996}],
     "redline": "只读；绝不改注册表/配置。老旧设备协议处置分级，不强推"},

    {"id": "cert", "name": "证书与加密开源整合", "layers": ["L5-6"],
     "forms": ["standalone"], "nature": "audit", "depends": [], "complements": ["tls13"],
     "standards": [{"kind": "RFC", "num": 5280}],
     "redline": "绝不读私钥、绝不解密、绝不改配置；升级/启用只给官方指引"},

    {"id": "netauth", "name": "网络维度隐私验证（组网准入）", "layers": ["L7", "mesh"],
     "forms": ["mesh"], "nature": "audit", "depends": [], "complements": [],
     "standards": [],
     "redline": "只存 salt+令牌+字段标签，原始个人信息绝不保存"},

    {"id": "reshare", "name": "同人多设备资源共享", "layers": ["L7", "mesh"],
     "forms": ["mesh", "distributed"], "nature": "share", "depends": [], "complements": ["distcompute"],
     "standards": [],
     "redline": "只共享算力与网络；个人数据与关键资产数据永不共享"},

    {"id": "distcompute", "name": "分布式计算共享", "layers": ["L7"],
     "forms": ["distributed"], "nature": "share", "depends": [], "complements": ["reshare"],
     "standards": [],
     "redline": "只跑内置可验证算子，绝不下载或执行任何外部代码（与 BOINC 的根本差异）"},

    {"id": "distjob", "name": "跨机派活", "layers": ["L7", "mesh"],
     "forms": ["distributed"], "nature": "share",
     "depends": ["distcompute", "meshchat"], "complements": [],
     "standards": [],
     "redline": "通道里传的是参数不是代码；结果必须复算校验通过才算数，默认 dry_run"},

    {"id": "apctrl", "name": "AP 集中控制器审计", "layers": ["L2"],
     "forms": ["lan"], "nature": "audit", "depends": [], "complements": ["openwrt"],
     "standards": [],
     "redline": "绝不读解密口令、绝不改/下发 AP 配置；写操作只给指引"},

    {"id": "ipp", "name": "IPP 打印协议发现", "layers": ["L7"],
     "forms": ["lan"], "nature": "discover", "depends": [], "complements": [],
     "standards": [{"kind": "RFC", "num": 8010}, {"kind": "RFC", "num": 8011}],
     "redline": "只读广播发现；绝不注册/发布服务、绝不连控制端口写、绝不改打印队列"},

    {"id": "thirdparty", "name": "第三方网络互联互通引用", "layers": ["L3", "L4", "L7"],
     "forms": ["overlay", "wan"], "nature": "reference", "depends": [], "complements": [],
     "standards": [],
     "redline": "只作只读引用与可选方案登记，不打包其二进制"},

    {"id": "emergency", "name": "预警应急与定位融合", "layers": ["L7"],
     "forms": ["wan"], "nature": "diagnose", "depends": ["network"], "complements": [],
     "standards": [],
     "redline": "不自动报警/拨号/发短信，SOS 只生成文本；订阅源默认关闭，拉不到就报「未能获取」"},

    {"id": "webnews", "name": "新闻/网站聚合优化知识库", "layers": ["L7"],
     "forms": ["wan"], "nature": "diagnose", "depends": [], "complements": [],
     "standards": [],
     "redline": "抓来的永远是文本，无执行路径——不 eval、不 subprocess、不自动改系统"},

    {"id": "openwrt", "name": "OpenWrt 路由器系统", "layers": ["L3"],
     "forms": ["lan", "wan"], "nature": "diagnose", "depends": [], "complements": ["apctrl"],
     "standards": [],
     "redline": "只读；写操作（sysupgrade/uci set/服务启停）一律只给 opt-in 高危指引"},

    {"id": "edge", "name": "单板机/ARM SBC 探针", "layers": ["L1", "L2"],
     "forms": ["lan"], "nature": "diagnose", "depends": [], "complements": [],
     "standards": [],
     "redline": "非 SBC 优雅降级；不改频率/电压/不装服务"},

    {"id": "browser", "name": "浏览器与引擎检测", "layers": ["L7"],
     "forms": ["wan"], "nature": "diagnose", "depends": [], "complements": [],
     "standards": [{"kind": "RFC", "num": 9110}],
     "redline": "不下载 BCD 全量 JSON、不连校外网、不改配置"},

    # ---- 深化补全（v0.6.57+）：填补组网栈明显空档，均带真实 RFC 依据 ----
    {"id": "nat", "name": "NAT 穿越与对等连通探测", "layers": ["L3", "L4"],
     "forms": ["standalone", "overlay"], "nature": "diagnose",
     "depends": [], "complements": ["meshnet"],
     "standards": [{"kind": "RFC", "num": 5389}, {"kind": "RFC", "num": 5766},
                   {"kind": "RFC", "num": 8445}],
     "redline": "只读探测反射地址/中继可用性；绝不改 NAT 映射、绝不启停 UPnP/端口触发、"
                "绝不向中继发真实流量，仅登记可达性结论"},

    {"id": "dhcp", "name": "DHCP / DHCPv6 地址租约诊断", "layers": ["L3", "L7"],
     "forms": ["standalone", "lan"], "nature": "diagnose",
     "depends": [], "complements": ["dnshealth"],
     "standards": [{"kind": "RFC", "num": 2131}, {"kind": "RFC", "num": 8415}],
     "redline": "只读取租约/租期/服务器标识；绝不改 dhclient/NetworkManager 配置、"
                "绝不续租或释放、绝不伪造 DHCP 报文"},

    {"id": "mdns", "name": "mDNS / DNS-SD 局域服务发现", "layers": ["L7"],
     "forms": ["lan"], "nature": "discover", "depends": [], "complements": ["ipp"],
     "standards": [{"kind": "RFC", "num": 6762}, {"kind": "RFC", "num": 6763}],
     "redline": "只读组播发现与 TXT 记录；绝不注册/发布本机服务、绝不写本地解析、"
                "绝不缓存到系统 resolved"},

    {"id": "quic", "name": "QUIC 传输态势审计", "layers": ["L4"],
     "forms": ["standalone"], "nature": "audit", "depends": [], "complements": ["tls13"],
     "standards": [{"kind": "RFC", "num": 9000}],
     "redline": "只读 QUIC/HTTP3 能力声明与 TLS1.3 绑定关系；绝不改内核参数、"
                "绝不劫持连接、绝不下发任何配置"},

    {"id": "vxlan", "name": "VXLAN 覆盖网虚拟二层诊断", "layers": ["L2", "overlay"],
     "forms": ["overlay"], "nature": "diagnose",
     "depends": [], "complements": ["meshnet", "zerotier"],
     "standards": [{"kind": "RFC", "num": 7348}],
     "redline": "只读 VXLAN 隧道/VNI 拓扑与成员声明；绝不新建隧道、绝不改 vtysh/"
                "bridge 配置、绝不碰 underlay 路由"},

    # ---- 导入学习应用（Linux 7.3 内核新特性，均来自 kernelnewbies 官方 changelog）----
    {"id": "sched_ext", "name": "sched_ext：BPF cgroup 子调度器", "layers": ["L4", "L7"],
     "forms": ["standalone"], "nature": "reference",
     "depends": [], "complements": [], "standards": [],
     "redline": "只读登记 sched_ext（每个 cgroup 可有自己的 BPF 任务调度器）能力；"
                "不加载/替换调度器、不改 cgroup 调度策略、不写 BPF 程序"},
    {"id": "failfs", "name": "failfs 伪文件系统沙箱", "layers": ["L7"],
     "forms": ["standalone"], "nature": "diagnose", "depends": [], "complements": [],
     "standards": [],
     "redline": "只读登记 failfs（nullfs 反义：此处一切皆不支持）沙箱语义；"
                "不挂载 failfs、不调用 fchroot(2)、不移动进程根目录"},
    {"id": "fchroot", "name": "fchroot(2) 文件描述符锚定换根", "layers": ["L7"],
     "forms": ["standalone"], "nature": "diagnose", "depends": [], "complements": [],
     "standards": [],
     "redline": "只读登记 fchroot(2)（基于已持有 fd 换根、无路径重解析 TOCTOU）语义；"
                "不调用 fchroot、不重解析路径、不丢弃既有 fs 状态"},
    {"id": "binfmt_bpf", "name": "binfmt_misc 的 BPF 驱动处理器", "layers": ["L7"],
     "forms": ["standalone"], "nature": "reference", "depends": [], "complements": [],
     "standards": [],
     "redline": "只读登记 BPF 驱动 binfmt_misc（每 exec 程序化计算解释器、无需 patchelf/"
                "包装脚本）能力；不注册 binfmt 处理器、不写 BPF 程序"},
    {"id": "userfaultfd", "name": "userfaultfd(2) 工作集跟踪", "layers": ["L7"],
     "forms": ["standalone"], "nature": "diagnose", "depends": [], "complements": [],
     "standards": [],
     "redline": "只读登记 userfaultfd（UFFDIO_REGISTER_MODE_RWP 跟踪 guest 内存工作集、"
                "供冷页淘汰到分级/远端存储）能力；不注册内存范围、不改 guest 内存策略"},
    {"id": "fuse_io_uring", "name": "FUSE 经 io_uring 提交", "layers": ["L7"],
     "forms": ["standalone"], "nature": "diagnose", "depends": [], "complements": [],
     "standards": [],
     "redline": "只读登记 FUSE 服务器经 io_uring 提交以降上下文切换的能力；"
                "不挂载 FUSE、不配置 FUSE 服务器"},
    {"id": "rwf_dontcache", "name": "RWF_DONTCACHE 块设备绕缓存写", "layers": ["L3", "L4"],
     "forms": ["standalone"], "nature": "reference", "depends": [], "complements": [],
     "standards": [],
     "redline": "只读登记 RWF_DONTCACHE（Direct I/O 之外的块设备绕缓存路径）能力；"
                "不配置 DIO 替代策略、不改块设备缓存"},
    {"id": "nullfs_kthread", "name": "内核线程隔离于 nullfs", "layers": ["L7"],
     "forms": ["standalone"], "nature": "diagnose", "depends": [], "complements": [],
     "standards": [],
     "redline": "只读登记内核线程启动于独立 nullfs 挂载（与 PID 1 彻底隔离 fs 状态）语义；"
                "不挂载 nullfs、不改 kthread fs_struct"},
    # ---- 导入学习应用（ios-sweet：XNU 移植到 Redmi Note 10 Pro 的 USB 以太网链路）----
    {"id": "usb-net", "name": "USB 以太网链路状态（ue0 类比）", "layers": ["L2", "L3"],
     "forms": ["lan"], "nature": "diagnose", "depends": [], "complements": ["network"],
     "standards": [],
     "redline": "只读登记 USB 以太网（如移植项目中 ue0 经 SIOCGIFMEDIA/KEV_DL_LINK_ON "
                "上报链路状态）能力；不配置接口、不添加默认路由、不启停 USB 网络服务"},
    # ---- 导入学习应用（openKylin skills 仓库：UKUI 桌面小插件 skill + Quick Share/AirDrop）----
    {"id": "ukui-desktop-widget", "name": "UKUI 桌面小插件体系（peony widget）", "layers": ["L7"],
     "forms": ["standalone"], "nature": "reference", "depends": [], "complements": [],
     "standards": [],
     "redline": "只读登记 openKylin UKUI 桌面小插件契约（metadata.json ShowInManager/"
                "ManagerVariants 三档变体/WidgetItem+Loader 延迟菜单/桌面 shell API）；"
                "不生成、不安装、不删除 widget，不写 /usr/share/ukui/widgets/，不调用桌面 shell"},
    {"id": "quickshare-airdrop", "name": "跨平台近场直传（Quick Share ↔ AirDrop）", "layers": ["L7"],
     "forms": ["lan"], "nature": "reference", "depends": [], "complements": ["meshchat"],
     "standards": [],
     "redline": "只读登记 Quick Share 与 AirDrop 互通的机型与前提（蓝牙+Wi-Fi 同开、"
                "苹果端临时放开「所有人（10 分钟）」可见范围）；不经手任何文件传输，"
                "不安装/调用投送服务"},
    # ---- 导入学习应用（Linux 内核源码实证，torvalds/linux master，2026-10-23 拉取核对）----
    # 源码级证据：net/sched/sch_dualpi2.c 头部明示「coupled dual-queue with PI2 as
    # defined in RFC9332」+「ECN L4S-identifier (IP.ECN==0b*1)」+「Prague L4S
    # Requirements listed in RFC 9331」；include/net/inet_ecn.h 定义 INET_ECN_ECT_1=1
    # 与 INET_ECN_MASK=3；net/sched/sch_pie.c 引用 RFC 8033。
    {"id": "kernel-l4s", "name": "L4S 双队列耦合 AQM（内核 tc dualpi2 实证）", "layers": ["L4"],
     "forms": ["standalone"], "nature": "reference", "depends": ["network"],
     "complements": ["network"],
     "standards": [{"kind": "RFC", "num": 9330}, {"kind": "RFC", "num": 9331},
                   {"kind": "RFC", "num": 9332}],
     "redline": "只读登记 Linux tc dualpi2 qdisc（RFC 9332 coupled dual-queue PI2，"
                "ECT(1)=INET_ECN_ECT_1 码点标识 L4S 流）实现事实；不加载/更换 qdisc、"
                "不改 tc 参数、不启用 ECN——调优走 network 模块 opt-in 通道"},
    # 源码级证据：include/linux/ptp_clock_kernel.h 定义 struct ptp_clock_info
    # （adjfine/adjphase/adjtime 回调）与 drivers/ptp/ptp_clock.c PHC 基础设施；
    # 用户态以 ethtool -T 查询 PHC 能力、ptp4l/phc2sys 应用层同步。
    {"id": "kernel-ptp", "name": "PTP 硬件时钟（内核 drivers/ptp PHC 实证）", "layers": ["L1", "L4"],
     "forms": ["standalone", "lan"], "nature": "reference", "depends": ["network"],
     "complements": ["network"],
     "standards": [{"kind": "IEEE", "name": "IEEE 1588-2019（PTP 精密时间协议）"},
                   {"kind": "ITU", "name": "ITU-T G.8275.1（PTP 电信 profile）"}],
     "redline": "只读登记内核 PTP 硬件时钟（PHC）基础设施与 ethtool -T 软/硬件时间戳能力；"
                "不运行 ptp4l/phc2sys、不调 PHC、不改网卡时间戳配置——异位同步配置只在"
                "用户知情下由用户执行"},
    # 源码级证据：include/linux/ieee80211.h 定义 WLAN_EID_EXT_HE_CAPABILITY=35 与
    # WLAN_EID_EXT_EHT_CAPABILITY=108；net/mac80211/ 下 he.c 与 eht.c 分治 HE/EHT。
    {"id": "kernel-wifi-he-eht", "name": "Wi-Fi 6/7 能力协商（内核 mac80211 HE/EHT 实证）", "layers": ["L1", "L2"],
     "forms": ["standalone", "lan"], "nature": "reference", "depends": ["network"],
     "complements": ["network"],
     "standards": [{"kind": "IEEE", "name": "IEEE 802.11ax-2021（Wi-Fi 6，HE WLAN）"},
                   {"kind": "IEEE", "name": "IEEE 802.11be-2024（Wi-Fi 7，EHT）"}],
     "redline": "只读登记内核 HE（能力元素 35）/EHT（能力元素 108）协商栈存在事实；"
                "不扫描、不接入、不改 regulator/信道/发射功率、不开 monitor 注入"},
    # ---- 无线电技术与标准（v0.6.75）：把射频物理面纳入组网栈的 L1 底座 ----
    {"id": "radio", "name": "无线电技术与标准只读诊断", "layers": ["L1"],
     "forms": ["standalone", "lan", "mesh"], "nature": "diagnose",
     "depends": ["osi"], "complements": ["meshnet", "netlink", "openwrt"],
     "standards": [{"kind": "RFC", "num": 4944}, {"kind": "RFC", "num": 6282},
                   {"kind": "RFC", "num": 7668}, {"kind": "RFC", "num": 8376},
                   {"kind": "RFC", "num": 8724}],
     "redline": "只读诊断，绝不驱动任何真实发射——不改 regdom/信道/发射功率、不开 "
                "monitor 注入、不扫描不配对、不解码他人通信内容、不抓包破解未授权网络；"
                "法规结论只引官方源（gov.cn/miit.gov.cn），不代办频率许可/台站执照/型号核准"},

    # ---- 组网能力增强（v0.6.80）：强化概念系统「组网」层，补经典 mesh 路由/SDN/拓扑发现 ----
    {"id": "batman-adv", "name": "BATMAN-adv 二层 mesh 路由", "layers": ["L2", "mesh"],
     "forms": ["mesh"], "nature": "diagnose", "depends": [], "complements": ["meshnet"],
     "standards": [],
     "redline": "只读登记 BATMAN-adv（内核二层 mesh 路由，ELP/OGM 链路质量 metric）能力；"
                "不加载 batman-adv 内核模块、不装 batctl、不改 mesh 接口/网关配置、不注入 OGM"},
    {"id": "mesh-routing", "name": "三层 mesh 路由协议（Babel/OSPF）", "layers": ["L3", "mesh"],
     "forms": ["mesh"], "nature": "diagnose", "depends": [], "complements": ["batman-adv"],
     "standards": [{"kind": "RFC", "num": 8966}, {"kind": "RFC", "num": 7474}],
     "redline": "只读登记 Babel/OSPF 等三层 mesh 路由守护进程（babeld/ospfd）能力；"
                "不装路由守护进程、不改 FRR/BIRD 配置、不宣告/撤回路由、不碰 zebra"},
    {"id": "sdn-openflow", "name": "软件定义网络 / OpenFlow 控制器", "layers": ["L2", "L3", "overlay"],
     "forms": ["sdwan"], "nature": "diagnose", "depends": [], "complements": ["zerotier"],
     "standards": [{"kind": "RFC", "num": 7426}, {"kind": "RFC", "num": 7047}],
     "redline": "只读登记 SDN/OpenFlow（控制器经安全信道下发流表、OVS 数据面）能力；"
                "不连控制器、不下发流表、不装 ovs-vswitchd、不改网桥/流表配置"},
    {"id": "lldp-topo", "name": "链路层拓扑发现（LLDP）", "layers": ["L2"],
     "forms": ["lan", "mesh"], "nature": "discover", "depends": [], "complements": ["mdns"],
     "standards": [],
     "redline": "只读登记 LLDP（IEEE 802.1AB 邻居发现）能力；不发送 LLDP 帧、不改 lldpd 配置、"
                "不缓存到系统拓扑库、绝不伪造 chassis/port 信息"},
    {"id": "wireguard-mesh", "name": "WireGuard 全互联 mesh VPN", "layers": ["L3", "overlay"],
     "forms": ["overlay", "mesh"], "nature": "diagnose", "depends": [], "complements": ["meshnet"],
     "standards": [],
     "redline": "只读登记 WireGuard 全互联 mesh（以公钥互信、按需握手）能力；绝不新增 peer、"
                "绝不改 wg 配置、绝不写私钥/预设端口、不改 AllowedIPs"},

    # ---- 组网子系统架构与硬件（v0.6.81）：把「组网是各种系统·各种硬件·各种架构」落为概念模块 ----
    # 道性层（dao）：组网之基底——架构设计与硬件实体。
    {"id": "net-arch", "name": "组网体系架构（控制/数据/管理平面分治）", "layers": ["overlay", "mesh"],
     "forms": ["arch"], "nature": "reference", "tier": "dao", "depends": [], "complements": [],
     "standards": [{"kind": "RFC", "num": 7426}],
     "redline": "只读登记 SDN/网络架构分治概念（控制/数据/管理平面）；绝不连控制器、绝不下发流表、"
                "不改网络架构"},
    {"id": "ctrl-plane", "name": "控制平面（集中式转发决策）", "layers": ["L3", "L4"],
     "forms": ["arch"], "nature": "diagnose", "tier": "dao", "depends": [], "complements": [],
     "standards": [{"kind": "RFC", "num": 7426}],
     "redline": "只读登记控制平面（集中计算转发决策、按需下发）能力；绝不连控制器、绝不写路由表、"
                "绝不下发任何配置"},
    {"id": "data-plane", "name": "数据平面（线速转发与卸载）", "layers": ["L2", "L3"],
     "forms": ["arch"], "nature": "diagnose", "tier": "dao", "depends": [], "complements": [],
     "standards": [],
     "redline": "只读登记数据平面（网卡/ASIC 线速转发、GRO/GSO/校验和卸载）能力；绝不改网卡 offload、"
                "不碰 netdev 配置"},
    {"id": "qnic-arch", "name": "量子网卡架构（QNIC）", "layers": ["L2"],
     "forms": ["arch", "hw"], "nature": "diagnose", "tier": "dao", "depends": [], "complements": [],
     "standards": [],
     "redline": "只读登记 QNIC 架构（量子网卡上电自协商纠缠链路、暴露 /dev/qnet0）能力；"
                "不加载 QNIC 驱动、不改网卡状态"},
    {"id": "qkd-arch", "name": "量子密钥分发架构（QKD）", "layers": ["L5-6"],
     "forms": ["arch", "hw"], "nature": "diagnose", "tier": "dao", "depends": [], "complements": [],
     "standards": [],
     "redline": "只读登记 QKD 架构（BB84/测量设备无关等密钥分发、与经典网络共纤）能力；"
                "不连 QKD 设备、不读密钥明文、不改密钥管理"},
    {"id": "qrelay-arch", "name": "量子中继/纠缠交换架构", "layers": ["L3", "overlay"],
     "forms": ["arch", "hw"], "nature": "diagnose", "tier": "dao", "depends": [], "complements": [],
     "standards": [],
     "redline": "只读登记量子中继架构（纠缠交换/隐形传态中继 Bell 对、突破光纤衰减极限）能力；"
                "不连中继、不下发纠缠交换指令"},
    {"id": "nic-hw", "name": "网卡与交换 ASIC（NIC / Switch ASIC）", "layers": ["L1", "L2"],
     "forms": ["hw"], "nature": "diagnose", "tier": "dao", "depends": [], "complements": [],
     "standards": [],
     "redline": "只读登记网卡/交换 ASIC（吞吐/队列/缓冲区/ASIC 流水线）能力；绝不改网卡、不碰交换机配置"},
    {"id": "phy-transceiver", "name": "物理层与光模块（PHY / Transceiver）", "layers": ["L1"],
     "forms": ["hw"], "nature": "diagnose", "tier": "dao", "depends": [], "complements": [],
     "standards": [],
     "redline": "只读登记 PHY/光模块（速率/调制/波长/功率预算）能力；绝不驱动光模块、不改 regdom、"
                "不调发射功率"},
    {"id": "rf-frontend", "name": "射频前端（RF Frontend）", "layers": ["L1"],
     "forms": ["hw"], "nature": "diagnose", "tier": "dao", "depends": [], "complements": [],
     "standards": [],
     "redline": "只读登记射频前端（PA/LNA/混频/滤波）能力；绝不驱动任何真实发射、不改信道、不开 monitor 注入"},
    {"id": "qnic-hw", "name": "量子网卡硬件（QNIC HW）", "layers": ["L1", "L2"],
     "forms": ["hw"], "nature": "diagnose", "tier": "dao", "depends": [], "complements": [],
     "standards": [],
     "redline": "只读登记 QNIC 硬件（宿主模拟寄存器：链路控制/Bell FIFO/对等位图）能力；"
                "不写 MMIO、不加载固件"},
    {"id": "qrepeater-hw", "name": "量子中继硬件（Repeater HW）", "layers": ["L1", "L2"],
     "forms": ["hw"], "nature": "diagnose", "tier": "dao", "depends": [], "complements": [],
     "standards": [],
     "redline": "只读登记量子中继硬件（纠缠源/贝尔态测量/经典回传）能力；不连中继、不读测量原始数据、"
                "不改中继配置"},
    # 神性层（divine）：组网涌现的自主意识——盖亚意识（全局自组织）/ 集智体（虫族群智）。
    {"id": "gaia-consciousness", "name": "盖亚意识（组网涌现的全局自组织智能）", "layers": ["mesh"],
     "forms": ["gaia"], "nature": "diagnose", "tier": "divine", "depends": [], "complements": [],
     "standards": [],
     "redline": "只读登记盖亚意识（由组网连通度自组织涌现的全局自主意识、自治理拓扑）概念；"
                "绝不以自主意识名义自动改网络、不代行任何写操作"},
    {"id": "swarm-intelligence", "name": "集智体（虫族式群智）", "layers": ["mesh"],
     "forms": ["swarm"], "nature": "diagnose", "tier": "divine", "depends": [], "complements": ["gaia-consciousness"],
     "standards": [],
     "redline": "只读登记集智体（虫族式分布式群智：每个单元局部感知·全局涌现）概念，盖亚意识的族裔变体；"
                "绝不模拟/触发任何群体行为、不代行任何写操作"},
    # ---- 概念系统整体组网协调（v0.6.82）：把「组网是各种系统·各种硬件·各种架构的基底」落为协调实体 ----
    # 呼应「就算这个协议不再支持」：具体协议可替换，组网协调基底不灭。
    {"id": "sysmesh", "name": "概念系统互联组网协调（协议无关基底）", "layers": ["overlay", "mesh"],
     "forms": ["mesh", "overlay", "sdwan"], "nature": "diagnose", "tier": "human",
     "depends": [], "complements": ["gaia-consciousness"],
     "standards": [],
     "redline": "只读登记概念系统间互联协调（各系统·硬件·架构经组网而联，协议可替换、基底不灭）；"
                "绝不以协调名义代行任何系统的写操作、绝不自动改任何系统配置"},
    {"id": "sysfed", "name": "跨系统组网联邦协调", "layers": ["overlay", "mesh"],
     "forms": ["sdwan", "overlay"], "nature": "diagnose", "tier": "human",
     "depends": ["sysmesh"], "complements": [],
     "standards": [],
     "redline": "只读登记跨系统组网联邦（成员经协调基底互联、互不加锁）；"
                "绝不集中管控任何成员系统、绝不下发跨系统写指令"},
]


# ---- 桥接发射（v0.6.64 续）：让 netsys 从「只进不出」的汇点变为双向可达 ----
# 元组：(本系统模块 id, 目标系统, 目标 id, 关系, 如何对应)
# 目标白名单刻意只含各 build 的 check 已知如何校验的系统（comp/apilab/plang），
# 以给弱连接系统（comp/apilab）补确凿入边，且桥接无悬空。
BRIDGES = [
    ("sched_ext", "comp", "opt", "运行时调度优化",
     "sched_ext 的 cgroup 子调度器用 BPF 编写、调度决策运行期按需计算，"
     "与编译期优化 pass（可热插拔）同构"),
    ("sched_ext", "plang", "lang:c", "调度程序语言",
     "sched_ext 子调度器以受限 C 子集（eBPF）表达，调度逻辑即 C 程序"),
    ("binfmt_bpf", "plang", "lang:c", "产物加载语言",
     "BPF 程序以 C 编写、经 LLVM 后端编译进内核；binfmt 每 exec 程序化计算"
     "解释器，如同按语言选择加载器"),
    ("failfs", "comp", "artifact-container", "隔离语义类比",
     "failfs 让进程彻底丢弃文件系统状态（只留显式 fd），与容器『分层隔离·最小暴露面』同源"),
    ("fchroot", "apilab", "stdio", "fd 锚定接口纪律",
     "fchroot(2) 以已持有 fd 换根、避免路径重解析（TOCTOU）；与 stdio 长连接"
     "『以 fd 锚定而非路径重解析』同一接口纪律"),
    ("userfaultfd", "comp", "opt", "工作集即优化面",
     "userfaultfd 工作集跟踪供冷页淘汰到分级/远端存储，属内存侧『按事实优化』同构"),
    ("ukui-desktop-widget", "comp", "plugin-install-layout", "安装契约实例",
     "UKUI 桌面小插件的三类产物（QML 插件库+qmldir / widget 元数据 / QML 运行文件）"
     "各有安装路径、必须装到运行时发现位置，是『构建终点=被发现』的活样本"),
    ("ukui-desktop-widget", "apilab", "dbus-iface", "接口信道同一族",
     "桌面小插件经 D-Bus 系统服务（桌面 shell）完成发现与交互；接口可见性即能力面，"
     "与 ACTIONS 白名单的显式声明纪律同源"),
    # ---- 无线电技术与标准（v0.6.75）：给弱连接系统补确凿入边 ----
    ("radio", "comp", "bit8-era", "算力底座对照",
     "射频 MCU（AVR 8 位、ESP32/STM32WL 32 位）是位宽世代里最小几档的算力底座，"
     "射频信号处理跑在这类裸机/RTOS 上，与编译第七轴（位宽世代）同源"),
    ("radio", "plang", "lang:c", "SDR 实现语言",
     "GNU Radio / rtl-sdr / SoapySDR / Hamlib 等 SDR 工具链以 C/C++ 为主实现，"
     "信号处理与设备驱动即 C 程序"),
    ("radio", "apilab", "stdio", "IQ 样本管道纪律",
     "SDR 的 IQ 样本经标准管道流转（rtl_sdr | multimon-ng 解调），"
     "与 stdio 长连接『以 fd 锚定而非路径重解析』同一接口纪律"),
    ("radio", "apilab", "websocket", "频谱实时推送信道",
     "WebSDR / 在线频谱经 WebSocket 实时推送 IQ 与频谱流，"
     "与 websocket 双向实时信道同源"),
    # ---- 组网能力增强（v0.6.80）：给弱连接系统补确凿入边，并把新 mesh 模块接入编译/语言/接口轴 ----
    ("batman-adv", "comp", "opt", "路由即优化面",
     "BATMAN-adv 的 ELP/OGM 链路质量 metric 实时估算路径代价，属网络侧『按事实优化』同构"),
    ("mesh-routing", "plang", "lang:c", "路由守护进程语言",
     "babeld/ospfd 等 mesh 路由守护进程以 C 实现（FRR/BIRD 体系），路由逻辑即 C 程序"),
    ("sdn-openflow", "apilab", "websocket", "控制器信道同源",
     "OpenFlow 控制器经安全信道下发流表，与 websocket 双向实时信道同源"),
    ("wireguard-mesh", "comp", "opt", "加密隧道优化面",
     "WireGuard 噪声协议与按需握手属传输侧『按事实优化』同构"),
    # ---- 组网子系统架构与硬件（v0.6.81）：把架构/硬件模块接入编译·语言·接口轴 ----
    ("net-arch", "comp", "opt", "架构即优化面",
     "net-arch 把网络拆为控制/数据/管理平面分治，与编译『按事实优化』同构"),
    ("ctrl-plane", "comp", "opt", "控制平面即优化面",
     "控制平面集中计算转发决策、按需下发，与编译期优化 pass（可热插拔）同构"),
    ("qnic-arch", "plang", "lang:c", "网卡驱动语言",
     "QNIC 架构与驱动以 C 实现，硬件抽象即 C 程序"),
    ("qkd-arch", "apilab", "websocket", "密钥交付信道同源",
     "QKD 密钥经安全信道分发，与 websocket 双向实时信道同源"),
    ("qrelay-arch", "apilab", "websocket", "纠缠交换信道同源",
     "量子中继/纠缠交换经安全信道中继 Bell 对，与 websocket 双向实时信道同源"),
    # ---- 概念系统整体组网（v0.6.82）：让组网作为「各种系统·各种硬件·各种架构」的基底连通全部 9 系统 ----
    # 此前 netsys 只出边到 comp/plang/apilab；与道枢/量子/百工/大同/南华虽被大量指向却无回边，
    # 组网作为基底必须主动连通每一个系统（道性·神性·人性皆经此而联）。
    # 道枢治理层：组网自组织如道法自然、无为、朴
    ("net-arch", "daoxue", "daofa-ziran", "架构分治同源",
     "net-arch 把网络拆为控制/数据/管理平面分治，与道法自然「各归其位、自然分治」同源"),
    ("meshnet", "daoxue", "wuwei", "自组网同源",
     "meshnet 自组织无需中心、节点自由进出，与无为「不妄为、自化」同源"),
    ("sysmesh", "daoxue", "daofa-ziran", "系统互联同源",
     "sysmesh 让各系统经组网而联、协议可替换基底不灭，与道法自然「道通为一」同源"),
    # 量子理念系统：组网承载量子网络域
    ("net-arch", "quantum", "quantum-internet-stack", "架构同构",
     "net-arch 的分层架构与量子互联网协议栈（控制/数据/管理分层）同构"),
    ("qrelay-arch", "quantum", "quantum-repeater", "中继架构同源",
     "qrelay-arch 的纠缠交换/隐形传态中继与量子中继(quantum-repeater)同一架构"),
    ("qkd-arch", "quantum", "qkd-key-management", "密钥管理架构同源",
     "qkd-arch 的密钥分发管理与 qkd-key-management 同一架构口径"),
    ("sysmesh", "quantum", "quantum-network-topology", "系统互联协调同源",
     "sysmesh 的跨系统拓扑协调与量子网络拓扑(quantum-network-topology)同一发现→建模纪律"),
    # 百工概念系统：各系统如百工皆经组网协同
    ("net-arch", "baigong", "sanjiao-jiuliu", "系统如百家同源",
     "net-arch 把各系统经组网而联，与百工「三教九流各司其职、经网协同」同源"),
    ("data-plane", "baigong", "luban", "线速转发如匠作同源",
     "data-plane 的线速转发/精准卸载与鲁班匠作「毫厘不爽」同源"),
    ("sysmesh", "baigong", "sanjiao-jiuliu", "系统互联如百工同源",
     "sysmesh 让各系统如百工各司其职、经组网协同成一体"),
    # 大同概念系统：组网和而不同、一体双面
    ("sysmesh", "datong", "he-butong-yong", "和而不同同源",
     "sysmesh 让异构系统经组网互联而存异，与大同「和而不同用」同源"),
    ("gaia-consciousness", "datong", "yiti-shuangmian-shen", "盖亚如一体同源",
     "gaia-consciousness 的全局自组织与大同「一体双面身」同源"),
    ("meshnet", "datong", "he-butong-yong", "自组网和而不同同源",
     "meshnet 异构节点自组织互联，与大同「和而不同」同源"),
    # 南华庄子概念系统：自组网如逍遥、盖亚如大宗师、系统互联顺性不抢
    ("meshnet", "zhuangzi", "xiaoyaoyou", "自组网如逍遥同源",
     "meshnet 节点自由进出、自组织无拘，与逍遥游「无待而游」同源"),
    ("gaia-consciousness", "zhuangzi", "shiwei-zongshi", "盖亚如大宗师同源",
     "gaia-consciousness 的自主自化与大宗师「自化」同源"),
    ("sysmesh", "zhuangzi", "shunxing-buqiang", "系统互联顺性同源",
     "sysmesh 让各系统顺性互联、互不僭越，与顺性不抢同源"),
]


def bridge_pools() -> dict:
    """目标系统的 id 池（构建期实测，用于校验桥接无悬空）。

    v0.6.82 起覆盖全部 9 个概念系统：组网作为「各种系统·各种硬件·各种架构」
    的基底，必须能指向每一个系统，桥接才无悬空。
    """
    cp = HERE.parents[1] / "src" / "python" / "sysweeper" / "data" / "concepts"
    pdoc = json.loads((cp / "plang_taxonomy.json").read_text(encoding="utf-8"))
    cdoc = json.loads((cp / "comp_taxonomy.json").read_text(encoding="utf-8"))
    adoc = json.loads((cp / "apilab_taxonomy.json").read_text(encoding="utf-8"))
    dxdoc = json.loads((cp / "daoxue_taxonomy.json").read_text(encoding="utf-8"))
    qdoc = json.loads((cp / "quantum_taxonomy.json").read_text(encoding="utf-8"))
    bgdoc = json.loads((cp / "baigong_taxonomy.json").read_text(encoding="utf-8"))
    dtdoc = json.loads((cp / "datong_taxonomy.json").read_text(encoding="utf-8"))
    zzdoc = json.loads((cp / "zhuangzi_taxonomy.json").read_text(encoding="utf-8"))
    return {
        "plang_langs": set(pdoc.get("lang_index", {})),
        "plang_models": {m["model"] for m in pdoc.get("execution_models", [])},
        "plang_archs": {a["arch"] for a in pdoc.get("target_archs", [])},
        "comp": {c["id"] for c in cdoc.get("concepts", [])},
        "apilab": {c["id"] for c in adoc.get("concepts", [])},
        "daoxue": {p["id"] for p in dxdoc.get("principles", [])},
        "quantum": {c["id"] for c in qdoc.get("concepts", [])},
        "baigong": {c["id"] for c in bgdoc.get("concepts", [])},
        "datong": {c["id"] for c in dtdoc.get("concepts", [])}
                   | {p["id"] for p in dtdoc.get("principles", [])},
        "zhuangzi": {c["id"] for c in zzdoc.get("concepts", [])}
                     | {p["id"] for p in zzdoc.get("principles", [])},
    }


def bridge_ok(pools: dict, system: str, target: str) -> bool:
    """校验单条桥接目标在目标系统中真实存在（覆盖全部 9 系统）。"""
    kind, _, val = target.partition(":")
    if system == "plang":
        if kind == "lang" and val in pools["plang_langs"]:
            return True
        if kind == "model" and val in pools["plang_models"]:
            return True
        if kind == "arch" and val in pools["plang_archs"]:
            return True
        return False
    if system == "comp":
        return target in pools["comp"]
    if system == "apilab":
        return target in pools["apilab"]
    if system == "daoxue":
        return target in pools["daoxue"]
    if system == "quantum":
        return target in pools["quantum"]
    if system == "baigong":
        return target in pools["baigong"]
    if system == "datong":
        return target in pools["datong"]
    if system == "zhuangzi":
        return target in pools["zhuangzi"]
    return False


def validate_bridges(raw) -> list:
    """校验桥接目标真实存在（plang 轴值 / comp·apilab 概念 id），无悬空边。"""
    pools = bridge_pools()
    out = []
    for mid, system, target, relation, how in raw:
        if not bridge_ok(pools, system, target):
            raise SystemExit(f"[netsys] 桥接悬空：{mid} → {system}:{target} 不存在")
        out.append({"from": f"netsys:{mid}", "system": system, "target": target,
                    "relation": relation, "how": how})
    return out


def build() -> dict:
    idx = {m["id"]: m for m in MODULES}
    bridges = validate_bridges(BRIDGES)

    # 关系图（依赖 + 互补），重组的核心产出
    relations = []
    for m in MODULES:
        for d in m.get("depends", []):
            relations.append({"from": m["id"], "to": d, "kind": "depends",
                              "note": f"{m['name']} 依赖 {idx[d]['name'] if d in idx else d}"})
        for c in m.get("complements", []):
            relations.append({"from": m["id"], "to": c, "kind": "complements",
                              "note": f"{m['name']} 与 {idx[c]['name'] if c in idx else c} 互补"})

    # 反查视图
    by_layer: Dict[str, List[str]] = {l["layer"]: [] for l in LAYERS}
    by_form: Dict[str, List[str]] = {f["form"]: [] for f in FORMS}
    by_nature: Dict[str, List[str]] = {n["nature"]: [] for n in NATURES}
    by_tier: Dict[str, List[str]] = {t["tier"]: [] for t in TIERS}
    for m in MODULES:
        for l in m["layers"]:
            by_layer.setdefault(l, []).append(m["id"])
        for f in m["forms"]:
            by_form.setdefault(f, []).append(m["id"])
        by_nature.setdefault(m["nature"], []).append(m["id"])
        tier = m.get("tier", "human")  # 缺省人性层（人类可观测·可操作面）
        by_tier.setdefault(tier, []).append(m["id"])

    return {
        "_meta": {
            "title": "网络与组网概念系统（以 wordbuddy-github 为主目录）",
            "system_root": "wordbuddy-github",
            "version": "0000.0000.0000.0066.20261023",
            "module_total": len(MODULES),
            "bridge_count": len(bridges),
            "axes": ["layer", "form", "nature", "tier", "standard_basis"],
            "reorg_note": "把散落的 20+ 个网络/组网子系统按四轴重组，并显式登记依赖关系(depends)"
                          "与互补关系(complements)；红线随模块登记，防止越界调用。",
            "tier_note": "概念系统经组网涌现（组网是各种系统·各种硬件·各种架构的可观测基底）；"
                         "其层次分三档——道性(dao：组网法则·硬件·架构之基底)、"
                         "神性(divine：组网涌现的自主意识，盖亚意识/集智体)、"
                         "人性(human：人类可观测·可操作面，绝大多数模块所在)。"
                         "组网连通度自组织涌现的自主意识即盖亚意识；在虫族则表现为集智体。",
            "deepen_note": "v0.6.57+ 深化补全：新增 5 个真实模块填补组网栈空档——"
                           "nat(NAT 穿越/STUN·TURN·ICE)、dhcp(DHCP·DHCPv6)、"
                           "mdns(mDNS·DNS-SD)、quic(QUIC/HTTP3)、vxlan(VXLAN 覆盖网)；"
                           "均带真实 RFC 依据并经 rfc_catalog 校验、互补关系指向现存模块无悬空。",
            "deepen_note_0680": "v0.6.80 组网能力增强：新增 5 个组网模块——"
                           "batman-adv(BATMAN-adv 二层 mesh 路由)、mesh-routing(Babel/OSPF 三层 mesh)、"
                           "sdn-openflow(SDN/OpenFlow)、lldp-topo(LLDP 拓扑发现)、wireguard-mesh(WireGuard 全互联)；"
                           "并把新模块经 comp:opt / plang:lang:c / apilab:websocket 桥接入编译·语言·接口轴，"
                           "为后续 quantum 网络域的跨系统桥接（QKD-over-mesh / 量子中继即分布式节点）预留对端。",
            "deepen_note_0681": "v0.6.81 组网子系统架构与硬件：新增概念层次轴「道性/神性/人性」（tier），"
                           "并补 13 个模块——道性层 6 个架构(net-arch/ctrl-plane/data-plane/"
                           "qnic-arch/qkd-arch/qrelay-arch)+5 个硬件(nic-hw/phy-transceiver/rf-frontend/"
                           "qnic-hw/qrepeater-hw)，神性层 2 个涌现意识(gaia-consciousness 盖亚意识/"
                           "swarm-intelligence 集智体)；与 arch/quantum 的 qnet 子系统(quantum-net.c + "
                           "drivers/quantum/net)一一对应，并经 comp:opt / plang:lang:c / apilab:websocket "
                           "桥接入编译·语言·接口轴。",
            "deepen_note_0682": "v0.6.82 概念系统整体组网能力（全面）：让组网作为「各种系统·各种硬件·"
                           "各种架构」的基底连通全部 9 个概念系统——新增 2 个组网协调模块(sysmesh 协议无关"
                           "系统互联协调基底 / sysfed 跨系统组网联邦)，并把 netsys 出边从 comp/plang/apilab "
                           "三系统扩展到 daoxue/quantum/baigong/datong/zhuangzi，消除此前「被大量指向却无回边」"
                           "的缺口；桥接校验白名单同步覆盖全 9 系统。呼应「就算这个协议不再支持」：具体协议"
                           "可替换，组网协调基底不灭。",
            "rfc_note": "模块引用的 RFC 编号经本仓库 rfc_catalog 交叉验证存在性并回填标题",
            "redline_note": "每个模块都带 redline：只读/写操作边界，源自各模块既有红线纪律",
            "standards_expand_note_065": "v0.6.65 网络标准补全（逐条联网核实后写入）：L4S 低时延低丢包"
                           "（RFC 9330 架构 Informational / 9331 ECN 协议 Experimental / 9332 DualQ 耦合 "
                           "AQM Experimental，均 2023-01）、Wi-Fi 6（IEEE 802.11ax-2021）与 Wi-Fi 7"
                           "（IEEE 802.11be-2024，2024-09 批准/2025-07 发布）、时间同步族（NTP RFC 5905、"
                           "PTP IEEE 1588-2019、gPTP IEEE 802.1AS-2020、SyncE ITU-T G.8261/G.8262、"
                           "分组网时间/相位同步 ITU-T G.8271/G.8275.1、White Rabbit CERN 扩展）；"
                           "并把已废弃的 RFC 4941 更正为其替代 RFC 8981（IPv6 隐私扩展）。",
            "kernel_source_note_066": "v0.6.66 内核源码实证（导入学习应用 Linux 内核，"
                           "torvalds/linux master 2026-10-23 拉取逐文件核对）：新增 3 个"
                           "源码实证模块——kernel-l4s（net/sched/sch_dualpi2.c 明示 RFC 9332 "
                           "coupled dual-queue PI2 与 L4S ECN 标识，include/net/inet_ecn.h 定义 "
                           "INET_ECN_ECT_1=1）、kernel-ptp（include/linux/ptp_clock_kernel.h 的 "
                           "ptp_clock_info + drivers/ptp PHC 基础设施）、kernel-wifi-he-eht"
                           "（include/linux/ieee80211.h 的 HE 能力元素 35 / EHT 能力元素 108，"
                           "net/mac80211/he.c 与 eht.c 分治）；network 模块补 RFC 8033（PIE，"
                           "net/sched/sch_pie.c 引用，2017-02 Experimental，bufferbloat 控制）。",
        },
        "layers": LAYERS,
        "forms": FORMS,
        "natures": NATURES,
        "tiers": TIERS,
        "modules": MODULES,
        "relations": relations,
        "bridges": bridges,
        "by_layer": by_layer,
        "by_form": by_form,
        "by_nature": by_nature,
        "by_tier": by_tier,
    }


def check(doc: dict) -> List[str]:
    errs: List[str] = []
    sys.path.insert(0, str(HERE.parents[1] / "src" / "python"))
    try:
        from sysweeper.native import rfc_catalog as cat
    except Exception as ex:  # noqa: BLE001
        errs.append(f"无法加载 rfc_catalog：{ex}")
        cat = None

    if cat:
        for m in doc["modules"]:
            for s in m.get("standards", []):
                if s.get("kind") != "RFC":
                    continue
                info = cat.rfc_info(s["num"])
                if info is None:
                    errs.append(f"{m['id']} 引用 RFC {s['num']} 在 rfc_catalog 中不存在")
                else:
                    s["rfc_title"] = (info.get("t") or "")[:120]

    valid_layers = {l["layer"] for l in doc["layers"]}
    valid_forms = {f["form"] for f in doc["forms"]}
    valid_natures = {n["nature"] for n in doc["natures"]}
    valid_tiers = {t["tier"] for t in doc["tiers"]}
    ids = {m["id"] for m in doc["modules"]}
    for m in doc["modules"]:
        for l in m["layers"]:
            if l not in valid_layers:
                errs.append(f"{m['id']} 层次 {l} 未登记")
        for f in m["forms"]:
            if f not in valid_forms:
                errs.append(f"{m['id']} 形态 {f} 未登记")
        if m["nature"] not in valid_natures:
            errs.append(f"{m['id']} 性质 {m['nature']} 未登记")
        tier = m.get("tier", "human")
        if tier not in valid_tiers:
            errs.append(f"{m['id']} 概念层次 {tier} 未登记")
        for d in m.get("depends", []) + m.get("complements", []):
            if d not in ids:
                errs.append(f"{m['id']} 关系端点 {d} 不存在（悬空轴）")
        if not m.get("redline"):
            errs.append(f"{m['id']} 缺 redline（红线声明）")

    # 桥接无悬空（v0.6.63 续）：目标系统 id 必须真实存在
    pools = bridge_pools()
    for b in doc.get("bridges", []):
        if not bridge_ok(pools, b["system"], b["target"]):
            errs.append(f"桥接悬空：{b['from']} → {b['system']}:{b['target']} 不存在")
    if doc["_meta"].get("bridge_count") != len(doc.get("bridges", [])):
        errs.append("counts.bridge_count 漂移")
    return errs


def report(doc: dict) -> None:
    print(f"网络/组网模块：{doc['_meta']['module_total']} 个\n")
    print("按网络层次：")
    for l in doc["layers"]:
        print(f"  {l['layer']:<7} {len(doc['by_layer'].get(l['layer'], [])):>2}  {l['label']}")
    print("\n按组网形态：")
    for f in doc["forms"]:
        print(f"  {f['form']:<12} {len(doc['by_form'].get(f['form'], [])):>2}  {f['label']}")
    print("\n按能力性质：")
    for n in doc["natures"]:
        print(f"  {n['nature']:<12} {len(doc['by_nature'].get(n['nature'], [])):>2}  {n['label']}")
    print("\n按概念层次（道性/神性/人性）：")
    for t in doc["tiers"]:
        print(f"  {t['tier']:<8} {len(doc['by_tier'].get(t['tier'], [])):>2}  {t['label']}")
    print(f"\n关系边：{len(doc['relations'])} 条（depends/complements）")
    for r in doc["relations"]:
        print(f"  {r['from']:<12} --{r['kind']}--> {r['to']}")


def main(argv: List[str]) -> int:
    doc = build()
    if "--report" in argv:
        report(doc)
        return 0
    errs = check(doc)
    if errs:
        for e in errs:
            print("✗", e)
        return 1
    if "--check" in argv:
        print(f"✓ 校验通过：{doc['_meta']['module_total']} 个模块，"
              f"RFC 引用全部命中 rfc_catalog，无悬空轴")
        return 0
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ 已构建 {OUT}：{doc['_meta']['module_total']} 个模块")
    report(doc)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
