"""常态化回头看、久久为功任务（retro，platform=any，跨平台）。

把「持续演进的元能力」落为只读任务：汇总维护节奏表、长期保障要点、易漂移维度复盘提示——
提醒「久久为功」，而非一次性扫完就丢。本身不调用任何写接口。
"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="retro_report",
        platform="any",
        title="常态化回头看、久久为功（维护节奏表 + 长期保障要点 + 易漂移维度复盘）",
        category="maintenance",
        risk="low",
        desc="只读汇总「该定期回头看什么」：维护节奏表（各维按什么周期回头看）、长期保障要点"
             "（从 durability/electrical 只读汇总）、易漂移维度复盘提示（标准 EOL/后量子/驱动）。"
             "与 novel-framework「每卷末/每 20 章体检」同源思路——常态化的回头看。",
        actions=[
            N("retro.retro_report", "端到端生成常态化回头看报告（节奏表→长期保障→易漂移维度）"),
        ],
        notes=["retro 只读汇总提醒：不替你做任何操作，只把「该回头看什么」说清楚。"],
        standards=["[工程] 常态化的回头看、久久为功（持续演进元能力）",
                  "[工程] 维护节奏表（与 novel-framework 每卷末/每 20 章体检同源）",
                  "[国际] 标准 EOL 追踪（endoflife.date）/ 后量子迁移（NIST FIPS 203/204/205）"],
    ),
]
