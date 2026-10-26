"""人类文明重启计划场景透镜（restart）：把「洪荒重启 / 人类文明重启计划」落为只读子系统。

来源：用户导入的「对话人类文明重启计划」（别名「洪荒重启」）。本子系统把它收口成一面**只读场景透镜**——
当讨论「从零重建技术栈 / 文明重启」时，把必须保住的维度与优先级清单化、可复盘，而不是给施工脚本。

只读项：
  - 维度清单：计算 / 网络 / 供电 / 存储与知识库 / 制造与供应链 / 人才与训练，每条给「重启时为何关键」
  - 优先级：先保「不可再生的」（知识库/制造能力）再保「可替代的」（具体设备）
  - 知识库落点：强调把规范/标准/源码/教材离线沉淀（与 sysweeper 知识库同口径，只读指引用）

红线：只读场景透镜——它只帮你想清楚「重启要保什么、按什么序」，绝不替你做任何施工/搬运。
"""

from __future__ import annotations


PROBES = (
    ("dimensions_report", "文明重启维度清单"),
    ("priority_report", "保命优先级（不可再生优先）"),
    ("knowledge_report", "知识库离线沉淀指引"),
)

# 维度清单（维度 → 重启时为何关键）
DIMENSIONS = (
    ("计算", "没有通用计算就没有任何自动化/模拟/设计；先保可自维护的最小算力"),
    ("网络", "没有互联就没有协同与知识分发；先保局部可信组网（Meshnet 思路）"),
    ("供电", "没有稳定电就没有上面一切；先保可再生与储能（electrical 同口径）"),
    ("存储与知识库", "规范/标准/源码/教材是文明的可复制资产；比单台设备更不可再生"),
    ("制造与供应链", "芯片/机床/化工能力决定能否本地造，而非只消费"),
    ("人才与训练", "会造的人比造出来的东西更不可再生；训练体系要同步保"),
)

# 保命优先级（不可再生 → 可替代）
PRIORITY = (
    "① 知识库（规范/标准/源码/教材）离线沉淀 —— 最不可再生",
    "② 制造与供应链能力（含机床/化工/半导体） —— 重建极慢",
    "③ 人才与训练体系 —— 比设备更不可再生",
    "④ 供电与储能 —— 无电一切停摆，但可逐步自建",
    "⑤ 计算与网络 —— 重要但设备可被替代/重建",
)

# 知识库落点（只读指引，与 sysweeper 知识库同口径）
KNOWLEDGE_NOTE = ("把规范/标准/源码/教材离线沉淀到可自托管的知识库（类本工具 data/ 知识库思路）；"
                   "优先存开放许可（MIT/Apache/BSD/CC-BY）内容，强拷贝左（GPL 类）只作「被分析」不带入自建栈。")


def dimensions_report() -> tuple:
    lines = ["文明重启维度清单（场景透镜，只读）:"]
    for dim, why in DIMENSIONS:
        lines.append(f"   · {dim}: {why}")
    return True, "\n".join(lines)


def priority_report() -> tuple:
    lines = ["保命优先级（不可再生优先，可替代在后）:"]
    for p in PRIORITY:
        lines.append(f"   · {p}")
    return True, "\n".join(lines)


def knowledge_report() -> tuple:
    lines = ["知识库离线沉淀指引（只读）:"]
    lines.append(f"   · {KNOWLEDGE_NOTE}")
    lines.append("   · 与 sysweeper 知识库同口径：知识是「可复制资产」，优先沉淀、可离线查")
    return True, "\n".join(lines)


def environment_report() -> list:
    lines = ["人类文明重启计划（restart · 洪荒重启）· 场景透镜："]
    for fn, lab in PROBES:
        ok, msg = getattr(__import__("sys").modules[__name__], fn)()
        lines.append(f"   · {lab}: {'✓' if ok else '✗'}")
        if isinstance(msg, str) and msg.strip():
            lines.append("       " + msg.replace("\n", "\n       "))
    return lines


def restart_report(env_tags: list | None = None, readings: dict | None = None) -> tuple:
    lines = ["== 人类文明重启计划场景透镜（restart · 洪荒重启：维度清单 + 保命优先级 + 知识库沉淀，只读不写）=="]
    lines.append(f"维度标签: {sorted(set(env_tags or [])) or '未声明（默认基线）'}")
    lines.append("")
    for fn, lab in PROBES:
        ok, msg = getattr(__import__("sys").modules[__name__], fn)()
        lines.append(f"[· {lab}]")
        for sub in (msg.splitlines() if isinstance(msg, str) else [msg]):
            lines.append("   " + sub)
        lines.append("")
    lines.append("安全不变量：restart 只读场景透镜——只帮你想清楚「重启要保什么、按什么序」；"
                 "绝不替你做任何施工/搬运/固件刷写。")
    return True, "\n".join(lines)


TUNES = ()


def restart_tune_list() -> list:
    return []
