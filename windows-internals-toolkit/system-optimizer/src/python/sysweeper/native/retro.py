"""常态化回头看、久久为功（retro）：把「持续演进的元能力」落为只读子系统。

这不是一个新的探针，而是一面「定期回头看」的镜子：把已登记子系统的维护节奏、长期保障要点、
需要周期性复盘的维度汇总成一份只读清单，提醒「久久为功」——而非一次性扫完就丢。

只读项：
  - 维护节奏表：哪些维度应按什么周期回头看（设备长期保障/供电环境/网络/兼容/知识库）
  - 长期保障要点：从 durability/electrical 抽「该持续关注」的清单（只读汇总，不调接口写）
  - 复盘提示：哪些子系统易随版本演进漂移（标准 EOL/后量子/驱动），需定期复检

红线：只读汇总提醒；它不替你做任何操作，只是把「该回头看什么」说清楚。
"""

from __future__ import annotations

import importlib


PROBES = (
    ("cadence_report", "维护节奏表（按周期回头看）"),
    ("longevity_report", "长期保障要点汇总"),
    ("drift_report", "易漂移维度复盘提示"),
)

# 维护节奏表（维 → 建议周期/要点），与 novel-framework 的「每卷末/每 20 章体检」同源思路
CADENCE = (
    ("设备长期使用保护", "每次大版本/电量异常时回头看：电池/温度/SMART/运行时长"),
    ("供电与环境安全", "换环境/增负载时回头看：回路质量/接地/温湿度降载"),
    ("网络与组网", "换地点/加设备时回头看：DNS/DoH-DoT/Meshnet 拓扑与权限"),
    ("兼容层", "系统升级后回头看：Proton/Wine/dosbox/WSL 运行时与驱动"),
    ("知识库与标准", "季度回头看：标准 EOL/后量子迁移/新发行版规范"),
    ("虚拟机环境", "迁移宿主/换 Hypervisor 时回头看：退化档位是否仍合适"),
)

# 易随版本演进漂移、需定期复检的维度
DRIFT = (
    "标准 EOL（endoflife.date）：近 EOL 的运行时/库须优先前向迁移",
    "后量子算法（NIST FIPS 203/204/205）：加密库与证书链需跟踪支持进度",
    "内核与驱动：升级后重核 virtgpu/display 的渲染后端是否仍可用",
    "包规范：新发行版/新包管理器的审计口径需补进 packages 知识库",
)


def cadence_report() -> tuple:
    lines = ["维护节奏表（常态化回头看，久久为功）:"]
    for dim, tip in CADENCE:
        lines.append(f"   · {dim}: {tip}")
    return True, "\n".join(lines)


def longevity_report() -> tuple:
    """只读汇总 durability/electrical 的「长期保障」要点（惰性 import，失败降级）。"""
    lines = ["长期保障要点（只读汇总，不调写接口）:"]
    try:
        dur = importlib.import_module(".durability", __package__)
        ok, msg = dur.durability_report()
        for sub in str(msg).splitlines()[:6]:
            if sub.strip():
                lines.append("   · 设备保护: " + sub.strip())
    except Exception:  # noqa: BLE001
        lines.append("   · 设备保护: 模块未就绪（降级为指引）")
    try:
        ele = importlib.import_module(".electrical", __package__)
        ok, msg = ele.electrical_safety_report()
        for sub in str(msg).splitlines()[:4]:
            if sub.strip():
                lines.append("   · 供电环境: " + sub.strip())
    except Exception:  # noqa: BLE001
        lines.append("   · 供电环境: 模块未就绪（降级为指引）")
    return True, "\n".join(lines)


def drift_report() -> tuple:
    lines = ["易漂移维度（需定期复检）:"]
    for d in DRIFT:
        lines.append(f"   · {d}")
    return True, "\n".join(lines)


def environment_report() -> list:
    lines = ["常态化回头看、久久为功（retro）· 本机只读汇总："]
    for fn, lab in PROBES:
        ok, msg = getattr(__import__("sys").modules[__name__], fn)()
        lines.append(f"   · {lab}: {'✓' if ok else '✗'}")
        if isinstance(msg, str) and msg.strip():
            lines.append("       " + msg.replace("\n", "\n       "))
    return lines


def retro_report(env_tags: list | None = None, readings: dict | None = None) -> tuple:
    lines = ["== 常态化回头看、久久为功报告（retro：维护节奏表 + 长期保障要点 + 易漂移维度复盘，只读不写）=="]
    lines.append(f"维度标签: {sorted(set(env_tags or [])) or '未声明（默认基线）'}")
    lines.append("")
    for fn, lab in PROBES:
        ok, msg = getattr(__import__("sys").modules[__name__], fn)()
        lines.append(f"[· {lab}]")
        for sub in (msg.splitlines() if isinstance(msg, str) else [msg]):
            lines.append("   " + sub)
        lines.append("")
    lines.append("安全不变量：retro 只读汇总维护节奏与复盘提示；它不替你做任何操作，只把「该回头看什么」说清楚。")
    return True, "\n".join(lines)


TUNES = ()


def retro_tune_list() -> list:
    return []
