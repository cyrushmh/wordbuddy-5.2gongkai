"""第三方网络互联互通 / 硬件优化 / 开源下载 任务（导入仓库的可选方案）。

把用户要求「导入」的若干开源仓库作为**可选方案**登记到对应能力：

- 网络互联互通共享资源（合并到 net_reshare 的同人资源共享模型）：
  p2wlan（P2P 虚拟局域网）、dae（eBPF 透明代理）、gfw-pac（PAC 分流）、
  v2rayN（Xray/sing-box 客户端）。
- 硬件优化（由用户选择）：DLSS5-Swapper（DLSS5 一键安装/调优/还原）。
- 开源下载软件（CDN / P2P 开关）：aria2。

全部为 opt_in（默认关闭），由用户明确选择后才出现/可启用；只读引用，不打包其二进制。
安全护栏（any_interop_policy，默认开启）：同人共享只限本人授权网络与算力，
绝不盗用他人网络互联、绝不共享个人数据与关键资产。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)

TASKS = [
    Task(
        id="net_interop_refs",
        platform="any",
        title="导入第三方网络互联互通方案（合并到共享资源，只读引用）",
        category="network",
        risk="low",
        opt_in=True,
        standards=[
            "[国标] GB/T 35273《个人信息安全规范》（目的限定、最小共享）",
            "[国际] ISO/IEC 27001（访问控制与资产保护）",
            "[仓库] p2wlan(MIT) / dae(AGPL-3.0) / gfw-pac(Apache-2.0) / v2rayN(GPL-3.0)",
        ],
        desc="把 p2wlan/dae/gfw-pac/v2rayN 作为「同人设备网络互联互通」的可选方案只读登记；"
             "本工具不打包其二进制，用户自行按许可证与平台安装。",
        actions=[N("thirdparty.interop_refs_report",
                   "列出网络互联互通第三方引用（仓库/许可证/用途/启用策略）")],
        notes=[
            "p2wlan：P2P 虚拟局域网（NAT 穿透/房间组网/Relay），补强本地自组网。",
            "dae：eBPF 透明代理（Linux），用于本人设备出网分流。",
            "gfw-pac：PAC 直连/代理域名分流规则（仅规则，不传流量）。",
            "v2rayN：Xray/sing-box GUI 客户端。",
            "三者均汇入「net_reshare 同人资源共享」模型：只用于本人授权网络。",
        ],
        caveats=["这些仓库为第三方项目，各自许可证见仓库 licenses/ 文件夹与引用的许可证全文链接。"],
    ),
    Task(
        id="net_interop_cdn_p2p",
        platform="any",
        title="网络互联互通的 CDN / P2P 开关（可选）",
        category="network",
        risk="low",
        opt_in=True,
        standards=[
            "[仓库] aria2(GPL-2.0)：HTTP/FTP(CDN) + BitTorrent/Metalink(P2P) 多源下载",
            "[国际] BitTorrent 协议规范（P2P 多源分发）",
        ],
        desc="为网络互联互通提供两套开关语义：CDN 开关（走 HTTP/FTP 镜像源多连接分片）、"
             "P2P 开关（走 BitTorrent/Metalink 多源）。仅用于本人有权获取/分享的资源的。",
        actions=[N("thirdparty.cdn_p2p_report", "查看 CDN / P2P 开关说明与落地命令")],
        notes=[
            "CDN 开关：aria2c --max-connection-per-server=N --split=N <镜像URL>。",
            "P2P 开关：aria2c <*.torrent|.metalink>，关闭用 --bt-enabled=false。",
        ],
        caveats=["P2P 开关仅用于合法资源；不用于转发他人流量、不蹭用他人网络出口。"],
    ),
    Task(
        id="hw_dlss_swapper",
        platform="any",
        title="硬件优化：DLSS5 一键安装/调优/还原（由用户选择）",
        category="hardware",
        risk="medium",
        opt_in=True,
        standards=[
            "[仓库] rakanki911/DLSS5-Swapper(MIT)：DLSS5/RenoDX/OptiScaler 调优",
            "[国际] Microsoft DirectX 12 / DLSS 超分接口（仅作能力说明，本工具不调用）",
        ],
        desc="把 DLSS5-Swapper 作为「GPU 硬件优化（由用户选择）」的可选工具登记；"
             "它改写游戏内超分 DLL，需用户逐游戏确认，且自动备份原文件便于还原。",
        actions=[N("thirdparty.hw_opt_report",
                   "列出硬件优化第三方引用（DLSS5-Swapper：用途/风险/许可证）")],
        notes=[
            "支持 DLSS5、RenoDX、DLSS5-Feeder（无 DLSS 游戏注入）、OptiScaler 与多通道路由。",
            "覆盖 DirectX 8/9/11/12、Vulkan、OpenGL、DirectDraw 与模拟器；游戏内 F8 覆盖层。",
            "操作前自动备份，风险由用户自负。",
        ],
        caveats=["会修改游戏目录内的 DLL；仅在本人设备、本人拥有的游戏上操作；本工具不打包其二进制。"],
    ),
    Task(
        id="hw_dl_open_download",
        platform="any",
        title="引入开源下载软件 aria2（CDN / P2P 开关，可选）",
        category="network",
        risk="low",
        opt_in=True,
        standards=[
            "[仓库] aria2/aria2(GPL-2.0)：多协议多源命令行下载器",
            "[国际] RFC 1951/HTTP、FTP、BitTorrent、Metalink 协议族",
        ],
        desc="把 aria2 作为「开源下载软件」的可选实现登记，提供 CDN（HTTP/FTP 镜像源）与 "
             "P2P（BitTorrent/Metalink）两套开关；本工具不打包其二进制。",
        actions=[N("thirdparty.downloader_report", "列出开源下载软件引用（aria2）"),
                 N("thirdparty.cdn_p2p_report", "查看 CDN / P2P 开关说明")],
        notes=[
            "aria2 支持 HTTP/HTTPS、FTP/SFTP、BitTorrent、Metalink，可多连接加速。",
            "CDN 开关 = 启用 HTTP/FTP 镜像源；P2P 开关 = 启用 BT/Metalink 多源。",
        ],
        caveats=["GPL-2.0；若与专有代码静态链接须注意传染性；仅下载本人有权获取的资源的。"],
    ),
    Task(
        id="any_interop_policy",
        platform="any",
        title="同人资源共享安全护栏（默认，必读）",
        category="network",
        risk="low",
        opt_in=False,
        standards=[
            "[国标] GB/T 35273《个人信息安全规范》（个人数据最小化、目的限定）",
            "[国际] ISO/IEC 27001（访问控制与资产保护）",
        ],
        desc="重声安全护栏：同一人登录的多设备可共享硬件资源（CPU/GPU/NPU/TPU/内存/网络），"
             "但个人数据与关键资产数据（凭据/密钥/钱包/通讯录/文档）一律不共享，"
             "且**绝不盗用他人网络互联互通能力**（不蹭他人房间/代理出口、不转发他人流量）。",
        actions=[M("查看 net_reshare 与第三方引用的安全护栏说明（见任务与 README）",
                   "只读说明：同人共享只限本人授权网络与算力")],
        notes=[
            "共享对象：本人登录的、经身份指纹（netauth）确认的多台设备。",
            "可共享：cpu/memory/gpu/npu/tpu/network。",
            "永不共享：personal_data/contacts/credentials/crypto_keys/asset_data/biometric/storage_content。",
            "第三方网络互联工具（p2wlan/dae/v2rayN 等）只用于本人**授权**网络。",
        ],
        caveats=["任何以「共享」之名要求提供密码/密钥/证件原件的，均为盗用风险，应拒绝。"],
    ),
]
