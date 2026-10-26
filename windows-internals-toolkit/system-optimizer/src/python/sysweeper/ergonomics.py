"""用户端人体工程学（v0.6.60）——以《南华真经》核心理念为用户端的操作层指导。

与 ``concepts/zhuangzi`` 数据层同口径，本模块把理念落成**三端共用**的操作层：

    * 逍遥游 → **无待一步**：入口唯一、一屏直达（``entry_map``/``render_guide``，
      CLI `sysweeper guide` 消费）。
    * 应帝王 → **顺性不抢**：默认即最佳、零配置可用（``followup_hints`` 只给
      顺手的下一步，不强制流程；各端默认路径即安全档）。
    * 大宗师 → **意图宗师**：预测式默认、失败指路可回退（``next_hint`` 统一
      「原因 + 下一步（含回退）」格式）。
    * 养生主 → **不伤**：破坏性动作先留痕再动手；调用方按 ``rollback_note``
      提示快照回退路径。

只读、不联网；不复制经典原文（理念登记见 concepts/zhuangzi 数据层）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 入口地图（逍遥游·无待一步）：把全部子命令按「场景」分组，一屏全览。
# 命令名以 argparse 实测为准；``ungrouped_commands()`` 双向校验：
#   1) 地图里的命令必须真实存在（防写错名字）；
#   2) 实测子命令必须全部被地图收录（防漏分组）。
# ---------------------------------------------------------------------------
SCENES: List[Dict[str, Any]] = [
    {"scene": "巡检与诊断", "why": "先看状态，再谈动手",
     "commands": ["scan", "detect", "info", "diag", "score", "syssoftware", "guide"]},
    {"scene": "报告与留痕", "why": "有据可查，前后可比（报告由 scan --report 生成）",
     "commands": ["scan --report x.json", "chart <x.json>", "snapshot", "notes",
                  "chrono"]},
    {"scene": "清理与维护", "why": "只清可清，先想后做",
     "commands": ["clean", "compress", "restart", "storage", "durability"]},
    {"scene": "设置与模块", "why": "按需调整，总装可查",
     "commands": ["settings", "profiles", "import", "versions", "toggles",
                  "subsystems", "sysmap", "plugins", "omni"]},
    {"scene": "硬件与显示", "why": "保平安、看得清",
     "commands": ["hardware", "kernel", "arch", "electrical", "peripheral",
                  "acoustics", "sysbase", "emergency", "fonts", "display", "retro", "desktop"]},
    {"scene": "平台与系统", "why": "各回各家，只给可用子集",
     "commands": ["linux", "windows", "macos", "bsd", "unix", "wsl",
                  "virt", "virtgpu", "container", "packages", "pkgmgr",
                  "distro", "proton"]},
    {"scene": "网络与组网", "why": "连起来，先体检",
     "commands": ["network", "dnshealth", "cert", "tor", "zerotier", "mesh",
                  "meshnet", "netlink", "remote", "browser", "openwrt",
                  "apctrl", "ipp", "vdns", "thirdparty", "osi", "radio",
                  "nettransfer"]},
    {"scene": "语言与编译", "why": "知识登记，只读不驱动",
     "commands": ["langs", "langref", "jdk", "kmod", "asm", "llvm", "toolchain", "plang",
                  "comp", "code", "legacy", "sysdev"]},
    {"scene": "概念与知识", "why": "十一个概念系统同构检索",
     "commands": ["concepts", "daoxue", "zhuangzi", "baigong", "datong", "quantum", "apilab",
                  "netsys", "protec", "sciences", "standards", "rfc", "mongo", "caudit", "recert",
                  "xiuzhen", "webnews", "androidstd", "gmsstd", "fdroidstd", "hmoseco", "hmosstd", "reverse", "winternals", "qstore", "qarch", "matrix", "f2b", "cnstd", "docs"]},
    {"scene": "移动与端上", "why": "小屏同样逍遥",
     "commands": ["android", "ios", "uniapp", "miniapp", "harmony",
                  "kaihong", "channels", "media", "livemedia", "linkage"]},
    {"scene": "门户与交付", "why": "同一个后端，多副面孔",
     "commands": ["gui", "webapi", "web", "genbat", "compat", "edge", "a11y"]},
    {"scene": "其他", "why": "杂项入口",
     "commands": ["list"]},
]

#: 预测式默认：当前命令 → 顺手的下一步（大宗师：意图先行，非流程先行）
FOLLOWUPS: Dict[str, List[str]] = {
    "scan": ["scan --report x.json", "snapshot capture", "guide"],
    "detect": ["scan", "guide"],
    "scan --report x.json": ["chart <x.json>", "snapshot capture"],
    "chart <x.json>": ["snapshot capture"],
    "snapshot capture": ["snapshot diff", "report"],
    "snapshot diff": ["snapshot show", "report"],
    "snapshot show": ["snapshot capture"],
    "settings": ["profiles", "report"],
    "concepts": ["concepts search <词>", "daoxue", "zhuangzi"],
    "guide": ["scan"],
    "gui": ["webapi", "web"],
    "webapi": ["gui"],
    "clean": ["report"],
    "import": ["settings", "profiles"],
    "notes": ["report"],
}

#: 破坏性动作的回退提示（养生主·不伤；调用方按需附在确认语后）
ROLLBACK_NOTE = ("已按默认策略为您留痕：可用 `python -m sysweeper snapshot "
                 "capture` 建立基线、`snapshot diff` 前后对比；若需还原，"
                 "按提示回退对应步骤即可。")


def _cli_subcommands() -> List[str]:
    """argparse 实测子命令集（避免在模块层硬编码数量）。"""
    try:
        import sys as _sys
        from pathlib import Path as _Path
        _sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
        from sysweeper import cli as _cli
        parser = _cli.build_parser()
        for a in parser._actions:
            if a.__class__.__name__ == "_SubParsersAction":
                return sorted(a.choices)
    except Exception:  # noqa: BLE001 - 防御：解析失败时调用方按未分组处理
        return []
    return []


def grouped_commands() -> List[str]:
    """入口地图已收录的命令（按场景顺序展平；带参表达式保留整串）。"""
    return [c for s in SCENES for c in s["commands"]]


def ungrouped_commands() -> List[str]:
    """地图漏收的子命令（双向校验：非空即地图需补）。"""
    have = {c.split()[0] for c in grouped_commands()}
    return [c for c in _cli_subcommands() if c not in have]


def phantom_commands() -> List[str]:
    """地图里写了、但 argparse 中不存在的命令（防写错名字；带参表达式取首词）。"""
    live = set(_cli_subcommands())
    return sorted({c.split()[0] for c in grouped_commands() if c.split()[0] not in live})


def entry_map() -> List[Dict[str, Any]]:
    """入口地图副本（场景 / 理由 / 命令清单）。"""
    return [dict(s) for s in SCENES]


def next_hint(step: str, *, ok: bool = True, note: str = "",
              rollback: str = "") -> str:
    """统一格式的「下一步」提示（大宗师：失败指路可回退）。

    成功：给顺手的下一步；失败：给原因摘要 + 可回退路径。
    """
    parts: List[str] = []
    head = f"【{step}】"
    if ok:
        parts.append(f"{head}完成。{note}".rstrip("。"))
        nxt = followup_hints(step)
        if nxt:
            parts.append("下一步可试：" + " / ".join(nxt))
        hint = "；".join(parts)
        return hint if hint.endswith("。") else hint + "。"
    parts.append(f"{head}未完成" + (f"：{note}" if note else "。"))
    if rollback:
        parts.append(f"回退/恢复：{rollback}")
    hint = "；".join(parts)
    return hint if hint.endswith("。") else hint + "。"


def followup_hints(current: str) -> List[str]:
    """按当前命令给预测式的下一步（应帝王：建议而非强制）。"""
    q = (current or "").strip()
    return list(FOLLOWUPS.get(q, []))


def render_guide() -> str:
    """一屏入口地图（CLI `guide` 子命令消费；逍遥游：无待一步）。"""
    subs = _cli_subcommands()
    lines: List[str] = [
        "操作入口地图（南华·逍遥游：无待一步——入口唯一，一屏直达）",
        "=" * 60,
        f"共 {len(subs)} 个子命令，按场景分组；详细参数：python -m sysweeper <命令> --help",
        "",
    ]
    for s in SCENES:
        lines.append(f"■ {s['scene']}（{s['why']}）")
        lines.append("    " + "  ".join(s["commands"]))
        lines.append("")
    bad = ungrouped_commands()
    phantom = phantom_commands()
    if bad:
        lines.append(f"[地图待补] 未分组子命令：{' '.join(bad)}")
    if phantom:
        lines.append(f"[地图有误] 不存在的命令：{' '.join(phantom)}")
    lines.append("理念口径（《南华真经》，详见 concepts zhuangzi）：")
    lines.append("  逍遥游=无待一步（本页）/ 应帝王=默认即最佳（安全档开箱即用）/ "
                 "大宗师=意图宗师（失败指路可回退）")
    lines.append("  养生主=不伤（破坏性操作先 snapshot capture 留痕再动手）")
    return "\n".join(lines)


def principles_brief() -> List[Dict[str, str]]:
    """七条用户端人体工程学原则摘要（转发 concepts/zhuangzi 数据层）。"""
    try:
        import sys as _sys
        from pathlib import Path as _Path
        _sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
        from sysweeper.concepts import zhuangzi as _z
    except Exception:  # noqa: BLE001 - 数据层缺失时不臆造
        return []
    out: List[Dict[str, str]] = []
    for p in _z.principles():
        out.append({
            "id": p.get("id", ""),
            "name": p.get("name", ""),
            "canon": "/".join(p.get("canon_refs", [])),
            "gist": p.get("gist", ""),
            "engineering": (p.get("engineering", "") or "")[:160],
        })
    return out


def stats() -> Dict[str, Any]:
    """入口地图规模与双向校验状态（中心/测试消费）。"""
    subs = _cli_subcommands()
    return {
        "cli_subcommands": len(subs),
        "scenes": len(SCENES),
        "grouped": len(grouped_commands()),
        "ungrouped": ungrouped_commands(),
        "phantom": phantom_commands(),
    }
