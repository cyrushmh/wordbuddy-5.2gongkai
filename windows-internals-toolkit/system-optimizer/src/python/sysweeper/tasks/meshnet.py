"""组网优化与设备协同任务（meshnet，platform=any，跨平台）。

学习 Mullvad Meshnet 的 WireGuard P2P 网状组网思路，只读观测组网拓扑、设备能力适配
（算力/GPU/存储缓存）与负载均衡/协同共享。任何 `wg set` 加 peer、改权限一律只给指引，
不代执行——严守只读红线。
"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="meshnet_report",
        platform="any",
        title="组网优化与设备协同只读报告（WireGuard P2P + 设备能力适配）",
        category="maintenance",
        risk="low",
        desc="只读观测组网：WireGuard 拓扑（wg show）、设备能力适配（算力/GPU/存储缓存）、"
             "负载均衡与协同共享。来源缺口：Mullvad 官方页未抓取，基于已知 Meshnet 模型。"
             "绝不新增 peer、绝不改 wg 配置、绝不动设备权限。",
        actions=[
            N("meshnet.meshnet_report", "端到端生成组网优化与设备协同报告（拓扑→能力适配→负载均衡）"),
        ],
        notes=["Meshnet 只读观测：只观测、只给指引、绝不写 wg 配置、绝不共享个人数据。"],
        standards=["[国际] WireGuard（现行协议规范见 wireguard.com 论文；截至 2026-10 "
                   "IETF 无 WireGuard RFC，所用密码原语为 RFC 7748 Curve25519、"
                   "RFC 7693 BLAKE2s、RFC 8439 ChaCha20-Poly1305、RFC 5869 HKDF）",
                  "[学习] Mullvad Meshnet：P2P 网状、设备链接权限、设备能力适配（模型，来源缺口已标注）",
                  "[国际] 负载均衡与算力协同（与 reshare 同口径：只共享算力/网络，不共享个人数据）"],
    ),
    Task(
        id="meshnet_add_peer_guidance",
        platform="any",
        title="WireGuard 新增 Meshnet 设备（规范指引）",
        category="maintenance",
        risk="low",
        desc="给出用 wg set 新增 Meshnet 设备的规范指引（双端密钥、allowed-ips、权限），绝不自动执行。",
        actions=[
            M("wg genkey/wg pubkey 各生成密钥对；wg set <if> peer <公钥> allowed-ips <子网>；"
              "按需开 allow traffic/SSH/local network，最小权限。",
              "WireGuard 新增 Meshnet 设备（规范指引，不代执行）"),
            N("meshnet.guide_add_peer", "输出新增 Meshnet 设备指引（只给步骤，不改 wg 配置）"),
        ],
        notes=["加 peer 属于写操作，一律只给规范指引；是否施工由用户在设备/厂商工具确认。"],
        standards=["[国际] WireGuard 配置（wg-quick / wg set）"],
    ),
]
