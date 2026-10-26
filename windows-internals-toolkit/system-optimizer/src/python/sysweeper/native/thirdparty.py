"""第三方网络互联互通 / 硬件优化 / 开源下载 引用注册表（只读）。

本模块把用户要求「导入」的若干开源仓库**作为只读引用与可选方案**登记到对应能力中：

- 网络互联互通共享资源：p2wlan（P2P 虚拟局域网）、dae（eBPF 透明代理）、
  gfw-pac（PAC 分流）、v2rayN（Xray/sing-box 客户端）。
- 硬件优化（由用户选择）：DLSS5-Swapper（DLSS5 一键安装/调优/还原）。
- 开源下载软件（含 CDN / P2P 开关）：aria2。

设计原则（与全局一致）：纯标准库、零依赖、离线优先；只读引用，绝不打包/运行其二进制；
所有函数返回 ``(ok, msg)``；缺数据优雅降级为 ``(False, 降级说明)``。

安全护栏（最关键，呼应 net_reshare / any_interop_policy）：
同人登录的多设备共享只限本人**授权**的网络与算力；个人数据与关键资产数据一律不共享；
**绝不盗用他人网络互联互通能力**（不蹭他人房间/代理出口、不转发他人流量）。
"""

from __future__ import annotations

import json
from typing import Dict, List, Tuple

# --------------------------------------------------------------------------- #
# 引用注册表（见 data/net_interop_refs.json）                                  #
# --------------------------------------------------------------------------- #


def _load_docs() -> dict:
    """从 data/net_interop_refs.json 载入第三方引用文档。"""
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "net_interop_refs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:  # noqa: BLE001
        return {}


REFS = _load_docs()


# --------------------------------------------------------------------------- #
# 只读引用函数（按 role 过滤 / 单条 / 全部）                                    #
# --------------------------------------------------------------------------- #


def _by_role(role: str) -> Dict[str, dict]:
    return {k: v for k, v in REFS.items()
            if isinstance(v, dict) and v.get("role") == role}


def list_interop() -> Dict[str, dict]:
    """网络互联互通共享资源相关引用（p2wlan/dae/gfw-pac/v2rayN）。"""
    return _by_role("network-interop")


def list_hw_opt() -> Dict[str, dict]:
    """硬件优化相关引用（DLSS5-Swapper）。"""
    return _by_role("hardware-opt")


def list_downloaders() -> Dict[str, dict]:
    """开源下载软件相关引用（aria2）。"""
    return _by_role("downloader")


def reference(rid: str) -> dict:
    """取单条引用；缺则返回空 dict（不抛异常）。"""
    return REFS.get(rid) or {}


def reference_all() -> Dict[str, dict]:
    """全部引用（去掉 _meta）。"""
    return {k: v for k, v in REFS.items() if k != "_meta"}


def doc_list() -> List[str]:
    """引用清单文本行（名称 + 许可证 + 用途归类）。"""
    lines = []
    for rid, d in reference_all().items():
        lines.append(f"{rid:14s} | {d.get('name',''):28s} | {d.get('license',''):10s} "
                     f"| {d.get('role','')}")
    return lines


def cdn_p2p_switches() -> Dict[str, dict]:
    """CDN / P2P 开关的落地参考（来自开源下载软件 aria2）。

    - CDN 开关  : 走 HTTP/FTP 镜像源（多连接分片），由 aria2 的 http/ftp 协议承担。
    - P2P 开关  : 走 BitTorrent / Metalink 多源，由 aria2 的 bt/metalink 协议承担。
    返回两组的说明与开关语义，供任务/CLI/GUI 展示。
    """
    return {
        "cdn": {
            "label": "CDN / 镜像源开关",
            "protocols": ["HTTP/HTTPS", "FTP/SFTP"],
            "tool": "aria2c --max-connection-per-server=N --split=N <镜像URL>",
            "meaning": "启用后从 CDN/镜像源多连接分片下载，加速且降低单一源压力。",
            "scope": "仅用于本人有权获取的资源的；镜像源须可信。",
        },
        "p2p": {
            "label": "P2P / 多源开关",
            "protocols": ["BitTorrent", "Metalink"],
            "tool": "aria2c <*.torrent|.metalink>  # 默认开启，关闭用 --bt-enabled=false",
            "meaning": "启用后从对等节点多源下载（BT/Metalink），天然具备断点续传与多源。",
            "scope": "仅用于合法、本人有权分享的资源；不开起来做流量转发。",
        },
    }


# --------------------------------------------------------------------------- #
# 报告函数（零参，供任务派发；返回 (ok, msg)）                                  #
# --------------------------------------------------------------------------- #


def _fmt(d: dict) -> str:
    lines = [
        f"· {d.get('name','')}  [{d.get('license','')}]",
        f"  仓库: {d.get('url','')}",
        f"  许可证全文: {d.get('license_url','')}",
        f"  用途: {d.get('role','')}",
        f"  协议/能力: {', '.join(d.get('protocols', []) or [])}",
        f"  接口: {', '.join(d.get('interfaces', []) or [])}",
        f"  说明: {d.get('summary','')}",
        f"  建议: {d.get('advice','')}",
        f"  启用策略: {d.get('opt_in_guidance','')}",
    ]
    return "\n".join(lines)


def interop_refs_report() -> Tuple[bool, str]:
    """网络互联互通共享资源的第三方引用（只读）。"""
    items = list_interop()
    if not items:
        return False, "未载入网络互联互通引用（data/net_interop_refs.json 缺失）"
    body = "\n\n".join(_fmt(v) for v in items.values())
    head = ("网络互联互通共享资源 · 第三方引用（只读登记，本工具不打包其二进制）\n"
            "安全护栏：同人共享只限本人授权网络与算力；绝不盗用他人网络互联、"
            "绝不共享个人数据与关键资产。\n"
            "----------------------------------------------------------------------")
    return True, head + "\n\n" + body


def hw_opt_report() -> Tuple[bool, str]:
    """硬件优化第三方引用（只读，由用户选择）。"""
    items = list_hw_opt()
    if not items:
        return False, "未载入硬件优化引用"
    body = "\n\n".join(_fmt(v) for v in items.values())
    head = ("硬件优化 · 第三方引用（由用户选择，本工具不打包其二进制）\n"
            "操作风险由用户自负；务必在本人设备、本人拥有的游戏/软件上操作。\n"
            "----------------------------------------------------------------------")
    return True, head + "\n\n" + body


def downloader_report() -> Tuple[bool, str]:
    """开源下载软件引用（只读）。"""
    items = list_downloaders()
    if not items:
        return False, "未载入开源下载软件引用"
    body = "\n\n".join(_fmt(v) for v in items.values())
    head = ("开源下载软件 · 第三方引用（只读登记）\n"
            "----------------------------------------------------------------------")
    return True, head + "\n\n" + body


def cdn_p2p_report() -> Tuple[bool, str]:
    """CDN / P2P 开关说明（只读）。"""
    sw = cdn_p2p_switches()
    lines = ["CDN / P2P 开关（落地参考：开源下载软件 aria2）", "-" * 50]
    for key, v in sw.items():
        lines.append(f"[{v['label']}] ({key})")
        lines.append(f"  协议: {', '.join(v['protocols'])}")
        lines.append(f"  示例: {v['tool']}")
        lines.append(f"  含义: {v['meaning']}")
        lines.append(f"  范围: {v['scope']}")
        lines.append("")
    lines.append("安全护栏：CDN/P2P 开关仅用于本人有权获取/分享的资源的；"
                 "不用于转发他人流量、不蹭用他人网络出口。")
    return True, "\n".join(lines)


def licenses_report() -> Tuple[bool, str]:
    """许可证引用来源汇总（只读；详见仓库 licenses/ 文件夹）。"""
    if not REFS:
        return False, "未载入引用数据"
    lines = ["第三方引用许可证汇总（完整全文见仓库 licenses/ 文件夹）", "-" * 50]
    seen = set()
    for rid, d in reference_all().items():
        lic = d.get("license", "")
        if lic in seen:
            continue
        seen.add(lic)
        lines.append(f"{lic:12s} | 全文: {d.get('license_url','')}")
    lines.append("")
    for rid, d in reference_all().items():
        lines.append(f"{rid:14s} -> {d.get('license',''):10s} | {d.get('url','')}")
    lines.append("")
    lines.append("本工具自身许可证见仓库根 LICENSE；本文档仅汇总第三方引用。")
    return True, "\n".join(lines)


def thirdparty_report(action: str = "list") -> Tuple[bool, str]:
    """统一入口（供 CLI/GUI 调用）。action ∈ list|interop|hw|download|cdn-p2p|licenses。"""
    dispatch = {
        "list": lambda: (True, "第三方引用清单：\n" + "\n".join(doc_list()) +
                         "\n（list/interop/hw/download/cdn-p2p/licenses 可分别查看）"),
        "interop": interop_refs_report,
        "hw": hw_opt_report,
        "download": downloader_report,
        "cdn-p2p": cdn_p2p_report,
        "licenses": licenses_report,
    }
    fn = dispatch.get(action, dispatch["list"])
    return fn()


__all__ = [
    "REFS", "reference", "reference_all", "doc_list",
    "list_interop", "list_hw_opt", "list_downloaders", "cdn_p2p_switches",
    "interop_refs_report", "hw_opt_report", "downloader_report",
    "cdn_p2p_report", "licenses_report", "thirdparty_report",
]
