"""兼容层串联（v0.6.34）：把「兼容层」从四个散落的模块串成一条能回答问题的链。

此前 proton / dosbox / wsl / virtgpu / legacy 各自是一份独立报告，各说各话：
用户想知道的其实是**一件事**——「我这台机器能不能跑那个平台的软件，缺哪一层」。
这个模块就把它们按**四层依赖**串起来，给出串联结论：

| 层 | 回答什么 | 由谁供给 |
|---|---|---|
| 1 宿主底座 | 架构/内核模块/发行版撑不撑得住 | arch / kmod / distro |
| 2 设备与图形 | 有没有可用的图形与虚拟化通路 | virtgpu |
| 3 兼容运行时 | 有没有把异平台调用翻译过来的那一层 | proton(Wine) / dosbox / wsl / legacy |
| 4 供给 | 缺的东西能不能装、谁来装 | pkgmgr |

**串联**而非并列：上层能不能用，取决于下层给不给得了——比如 Proton 要 Vulkan
（第 2 层）与 32 位运行时（第 4 层），缺任何一层，第 3 层就是空转。
报告按「场景」给结论，而不是罗列四个模块各自的输出。

红线：全程**只读**，只调各模块既有的零参只读报告；**不安装、不启用、不改配置**——
缺什么只给官方指引。异常只标「异常」并跳过，不外抛。
"""

from __future__ import annotations

import importlib
from typing import Dict, List, Tuple

__all__ = ["LAYERS", "SCENARIOS", "layer_scan", "compat_chain",
           "compat_report", "capabilities_report"]

# 分隔线 / 装饰字符：抽摘要行时跳过这些「只有框没有内容」的行
_DECOR = set("─═━┄┅│+-=·╔╗╚╝║ ")


# ── 四层依赖模型：(层名, [(key, 标签, 模块, 报告函数)]) ────────────────────
LAYERS: List[Tuple[str, List[Tuple[str, str, str, str]]]] = [
    ("宿主底座", [
        ("arch", "架构/指令集", "arch", "arch_report"),
        ("kmod", "内核模块/固件", "kmod", "kmod_report"),
        ("distro", "发行版能力", "distro", "distro_report"),
    ]),
    ("设备与图形", [
        ("virtgpu", "虚拟化/GPU", "virtgpu", "virtgpu_report"),
    ]),
    ("兼容运行时", [
        ("proton", "Proton/Wine（Windows 应用）", "proton", "proton_report"),
        ("dosbox", "dosbox（DOS 程序）", "legacy", "dosbox_report"),
        ("wsl", "WSL（Windows 子系统桥）", "wsl", "wsl_report"),
        ("legacy", "遗留/嵌入式总览", "legacy", "legacy_report"),
    ]),
    ("供给", [
        ("pkgmgr", "包管理", "pkgmgr", "universal_report"),
    ]),
]

# ── 场景 → 依赖哪些层（按 key 判定）──
# 每个场景列出「必须成立」的 key；缺任一项即判「缺层」，给对应指引。
SCENARIOS: List[Tuple[str, str, Tuple[str, ...], str]] = [
    ("跑 Windows 程序/游戏", "proton", ("arch", "kmod", "proton"),
     "Proton/Wine 需要架构与内核面撑住（NT 同步原语 fsync/NTSync 受内核版本门控），"
     "再由 Wine 层翻译 Win32 调用；装 Steam/Proton 或系统 wine 包即可，本工具不代装"),
    ("跑老 DOS 程序", "dosbox", ("dosbox",),
     "dosbox 自带模拟层，主要看它装没装；真机 DOS 环境另走 DOSEMU2（见 legacy）"),
    ("在 Windows 上跑 Linux", "wsl", ("wsl",),
     "WSL 是反向桥：本机若为 Linux 则不适用，需在 Windows 宿主机上探测"),
    ("跑遗留/嵌入式用户态", "legacy", ("legacy",),
     "busybox 单二进制撑起工具集；嵌入式与路由器场景另见 OpenWrt"),
]


_NA_MARKERS = ("未识别", "不适用", "非 Windows", "未安装", "未检测到",
               "未找到", "无数据", "n/a", "N/A")


_SUBSTANCE = ("✓", "✗", "未安装", "已安装", "检测到", "未检测", "未启用",
              "已启用", "可用", "不可用", "缺失")


def _brief(msg: str, limit: int = 56) -> str:
    """从一份报告正文里抽一行「有结论」的摘要，截断成紧凑串。

    两轮取值：先在开头 12 行里找**带结论标记**的行（✓/✗/已安装/检测到…），
    找不到再退回第一个「有内容」的行（判据：这一行不是只剩装饰字符）。
    这样避开「XX 诊断报告」这种只有标题没有结论的第一行。
    """
    lines = [l.strip() for l in (msg or "").splitlines()]
    head = [l for l in lines[:12] if l and not set(l) <= _DECOR]
    for line in head:
        if any(m in line for m in _SUBSTANCE):
            return line[:limit]
    return head[0][:limit] if head else ""


def _is_na(brief: str) -> bool:
    """摘要是否明示「本机不适用」——**不适用 ≠ 已就绪**，两者必须分开。

    典型：wsl_report 在本机 Linux 上返回 ok=True，但正文是「未识别为 WSL 环境，
    其余维度不适用」。若把 ok 直接当就绪，结论就反了。
    """
    return any(m in (brief or "") for m in _NA_MARKERS)


def _probe(module: str, fn: str) -> Tuple[bool, str]:
    """调一个零参只读报告，异常只标异常不外抛。返回 (ok, 摘要)。"""
    try:
        mod = importlib.import_module(f"{__name__.rsplit('.', 1)[0]}.{module}")
        fn_obj = getattr(mod, fn, None)
        if fn_obj is None:
            return False, "报告函数不可用"
        r = fn_obj()
        if isinstance(r, tuple):
            ok, msg = bool(r[0]), str(r[1]) if len(r) > 1 else ""
        elif isinstance(r, list):
            ok, msg = True, "\n".join(str(x) for x in r)
        else:
            ok, msg = True, str(r)
        return ok, _brief(msg)
    except Exception as e:  # noqa: BLE001
        return False, f"诊断异常（已跳过）：{e}"


def layer_scan() -> List[dict]:
    """逐层只读盘点，返回 [{layer, items:[{key,label,ok,brief}]}]（纯数据，供报告与测试复用）。"""
    out: List[dict] = []
    for layer, items in LAYERS:
        rows = []
        for key, label, module, fn in items:
            ok, brief = _probe(module, fn)
            rows.append({"key": key, "label": label, "ok": ok, "brief": brief})
        out.append({"layer": layer, "items": rows})
    return out


def _status_of(scan: List[dict], key: str) -> Tuple[bool, str]:
    for layer in scan:
        for it in layer["items"]:
            if it["key"] == key:
                return it["ok"], it["brief"]
    return False, "未登记该层"


def compat_chain() -> List[dict]:
    """给出「场景 → 串联结论」的结构化结果（纯数据）。

    每项：{scene, entry, missing:[key], ready:bool, advice}
    ready 只在该场景依赖的**全部** key 都成立时才为 True——串联的意义就在这里：
    缺任何一层，上层都是空转。
    """
    scan = layer_scan()
    chains: List[dict] = []
    for scene, entry, deps, advice in SCENARIOS:
        missing, na = [], []
        for k in deps:
            ok, brief = _status_of(scan, k)
            if ok and _is_na(brief):
                na.append(k)          # 本机不适用：不是缺层，也不是就绪
            elif not ok:
                missing.append(k)     # 真缺层
        chains.append({
            "scene": scene,
            "entry": entry,
            "deps": list(deps),
            "missing": missing,
            "na": na,
            "ready": not missing and not na,
            "advice": advice,
            "brief": _status_of(scan, entry)[1],
        })
    return chains


def compat_report() -> tuple:
    """兼容层串联报告（只读）。返回 (ok, msg)。

    五段：四层盘点 / 场景串联结论 / 串联链（谁依赖谁）/ 缺层指引 / 红线说明。
    ok 为 True 表示**至少有一个场景已就绪**；全部缺层则返回 False 并列出缺什么。
    """
    scan = layer_scan()
    chains = compat_chain()

    out = ["兼容层串联（只读盘点 · 四层依赖 · 场景结论）",
           "口径：上层能不能用，取决于下层给不给得了——缺一层，上层就是空转。",
           "─" * 58]
    for layer in scan:
        out.append(f"[第 {scan.index(layer) + 1} 层 · {layer['layer']}]")
        for it in layer["items"]:
            mark = "✓" if it["ok"] else "✗"
            tail = f"  — {it['brief']}" if it["brief"] else ""
            out.append(f"  · {it['label']:<26}[{mark}]{tail}")
    out.append("─" * 58)
    out.append("[场景串联结论 · 缺一层即空转]")
    for c in chains:
        if c["ready"]:
            out.append(f"  · {c['scene']}：✓ 链路已通"
                       + (f"（{c['brief']}）" if c["brief"] else ""))
        elif c["na"]:
            na = "、".join(c["na"])
            out.append(f"  · {c['scene']}：— 本机不适用（{na} 不适用）"
                       + (f"  — {c['brief']}" if c["brief"] else ""))
        else:
            miss = "、".join(c["missing"])
            out.append(f"  · {c['scene']}：✗ 缺层（{miss}）"
                       + (f"  — {c['brief']}" if c["brief"] else ""))
    out.append("─" * 58)
    out.append("[串联链 · 谁依赖谁]（与 linkage 联动轴同口径）")
    out.append("  架构/指令集 → 内核模块/固件 → 发行版能力 → 虚拟化/GPU → "
               "Proton/Wine·dosbox·wsl → 包管理供给")
    out.append("  读法：箭头左边是右边能不能成立的前提；装运行时之前先看底座。")
    out.append("─" * 58)
    out.append("[缺层指引 · 只给官方路径，本工具不代装]")
    any_missing = False
    for c in chains:
        if c["missing"]:
            any_missing = True
            out.append(f"  · {c['scene']}：{c['advice']}")
    if not any_missing:
        out.append("  · 当前场景无缺层；其余平台按需安装即可。")
    out.append("  通用：装运行时前先确认架构与内核版本（32 位运行时、NT 同步原语、Vulkan ICD）。")
    out.append("─" * 58)
    out.append("红线：只读盘点，不安装、不启用、不改任何配置；是否安装由你决定。")

    ok = any(c["ready"] for c in chains)
    return ok, "\n".join(out)


def capabilities_report() -> tuple:
    """本层能力自检（GUI/CLI 通用）：四层覆盖 + 场景就绪数。"""
    scan = layer_scan()
    chains = compat_chain()
    total_items = sum(len(l["items"]) for l in scan)
    ready_items = sum(1 for l in scan for it in l["items"] if it["ok"])
    out = ["兼容层串联能力自检（只读）"]
    out.append(f"  · 四层依赖模型：{len(LAYERS)} 层 / {total_items} 项盘点")
    out.append(f"  · 本机可用：{ready_items}/{total_items} 项")
    out.append(f"  · 场景：{len(chains)} 个，已就绪 "
               f"{sum(1 for c in chains if c['ready'])} 个")
    for c in chains:
        if c["ready"]:
            state = "✓ 链路已通"
        elif c["na"]:
            state = "— 本机不适用（" + "、".join(c["na"]) + "）"
        else:
            state = "✗ 缺 " + "、".join(c["missing"])
        out.append(f"     · {c['scene']}：{state}")
    out.append("  · 红线：只调既有零参只读报告，不安装、不启用、不改配置")
    return True, "\n".join(out)
