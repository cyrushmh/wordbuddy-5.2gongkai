"""组网优化与设备协同（meshnet）：学习 Mullvad Meshnet 的 WireGuard P2P 网状组网思路，落为只读子系统。

来源缺口：Mullvad 官方页本次抓取失败（网络不可达），本子系统基于已知模型构建——WireGuard P2P
网状、设备间直连、链接权限（allow traffic / SSH / local network）、设备能力适配（算力/GPU/存储缓存）、
负载均衡与协同共享。所有判定**只读**：只读 `wg show` 拓扑、只读设备能力声明，绝不新增 peer、绝不改
wg 配置、绝不动任何设备权限。

覆盖：
  - 拓扑只读：`wg show` 各接口的 peer 列表与最新握手（有 wg 才读，无则降级为指引）
  - 权限模型：只读看哪类链接被允许（需配 wg 才判；只读不写）
  - 设备能力适配：把组网设备的「算力 / GPU / 可选存储缓存」登记为可协同资源（只列，不占用）
  - 负载均衡与协同共享：给出「流量/算力如何在设备间分摊」的只读观察与指引

红线：只读观测 ≠ 授权施工——`wg set` 加 peer、改 allowed-ips、开设备权限一律只给指引。
"""

from __future__ import annotations

import shutil
import subprocess


PROBES = (
    ("topology_report", "WireGuard 拓扑（wg show）"),
    ("capability_report", "设备能力适配（算力/GPU/存储缓存）"),
    ("balance_report", "负载均衡与协同共享"),
)

# 设备能力适配维度（只读登记，协同时按此分摊）：算力 / GPU / 可选存储缓存
CAP_DIMS = ("compute", "gpu", "storage_cache")

SOURCE_NOTE = "来源缺口：Mullvad 官方页未抓取（网络不可达），本子系统基于已知 Meshnet 模型（WireGuard P2P / 权限 / 设备能力适配）构建，已显式标注。"


def topology_report() -> tuple:
    """只读看 WireGuard 拓扑（wg show 接口与 peer 数）。"""
    if shutil.which("wg") is None:
        return False, "未安装 wireguard-tools（wg 不可用）；如未组网则不属异常"
    try:
        out = subprocess.run(["wg", "show"], capture_output=True, text=True, timeout=8).stdout
    except (OSError, subprocess.SubprocessError):
        return False, "wg show 调用失败（只读探针跳过）"
    ifaces = [l.split()[1] for l in out.splitlines() if l.startswith("interface:")]
    peers = out.count("peer:")
    if not ifaces:
        return False, "未启用任何 WireGuard 接口（wg show 无 interface）"
    return True, f"WireGuard 拓扑（只读）: 接口 {len(ifaces)} 个（{', '.join(ifaces)}），peer 共 {peers} 个"


def capability_report() -> tuple:
    """只读登记本机可作为组网协同的设备能力（算力/GPU/存储缓存）。"""
    import os
    ncpu = os.cpu_count() or 0
    gpu = "未知"
    if shutil.which("lspci"):
        try:
            pc = subprocess.run(["lspci"], capture_output=True, text=True, timeout=6).stdout.lower()
            if "vga" in pc or "3d" in pc:
                gpu = "有显示/GPU 设备（lspci 命中）"
        except (OSError, subprocess.SubprocessError):
            gpu = "GPU 探测失败"
    lines = ["设备能力适配（只读登记，协同时按此分摊，绝不占用）:"]
    lines.append(f"   · compute: 逻辑核数 {ncpu}")
    lines.append(f"   · gpu: {gpu}")
    lines.append(f"   · storage_cache: 可有可无的就近缓存（只读登记，不强制占用磁盘）")
    return True, "\n".join(lines)


def balance_report() -> tuple:
    lines = ["负载均衡与协同共享（只读观察 + 指引）:"]
    for tip in (
        "设备间直连优先于经中继，延迟最低；跨网不通才走 Exit Node",
        "算力任务按各设备 compute 维度打分分摊（核数 × 空闲度 × 供电），有预算即停",
        "GPU 任务只在登记了 gpu 能力的设备上跑，其它设备不接图形负载",
        "storage_cache 用于就近缓存共享产物，绝不共享个人数据与关键资产（与 reshare 同口径）",
    ):
        lines.append(f"   · {tip}")
    return True, "\n".join(lines)


def environment_report() -> list:
    lines = ["组网优化与设备协同（meshnet）· 本机只读探测："]
    for fn, lab in PROBES:
        ok, msg = getattr(__import__("sys").modules[__name__], fn)()
        lines.append(f"   · {lab}: {'✓ 可用' if ok else '✗ 不适用'}")
        if isinstance(msg, str) and msg.strip():
            lines.append("       " + msg.replace("\n", "\n       "))
    return lines


def meshnet_report(env_tags: list | None = None, readings: dict | None = None) -> tuple:
    lines = ["== 组网优化与设备协同报告（meshnet：WireGuard P2P 网状 + 设备能力适配 + 负载均衡/协同共享，只读不写）=="]
    lines.append(f"维度标签: {sorted(set(env_tags or [])) or '未声明（默认基线）'}")
    lines.append("")
    lines.append(f"[① 来源说明] {SOURCE_NOTE}")
    lines.append("")
    lines.append("[② 拓扑（只读）]")
    ok, msg = topology_report()
    lines.append(f"   · {'✓' if ok else '✗'} {msg}")
    lines.append("")
    lines.append("[③ 设备能力适配]")
    ok, msg = capability_report()
    for sub in msg.splitlines():
        lines.append("   " + sub)
    lines.append("")
    lines.append("[④ 负载均衡与协同共享]")
    ok, msg = balance_report()
    for sub in msg.splitlines():
        lines.append("   " + sub)
    lines.append("")
    lines.append("安全不变量：meshnet 只读观测组网与设备能力；`wg set` 加 peer / 改 allowed-ips / 开设备"
                 "权限一律只给指引；个人数据与关键资产永不共享。")
    return True, "\n".join(lines)


def guide_add_peer() -> tuple:
    lines = [
        "新增 Meshnet 设备指引（wg set，不代执行）:",
        "   1. 在两端各生成密钥对（wg genkey / wg pubkey），私钥只留本机",
        "   2. wg set <if> peer <对端公钥> allowed-ips <子网>",
        "   3. 按需开权限（allow traffic / SSH / local network），最小权限原则",
        "   4. 配置只落内存；要持久化请改 wg-quick 配置文件（由用户确认）",
    ]
    return True, "\n".join(lines)


TUNES = (
    ("guide_add_peer", "WireGuard 新增 Meshnet 设备（规范指引，不代执行）"),
)


def meshnet_tune_list() -> list:
    return [f"· {fn}() — {desc}" for fn, desc in TUNES]
