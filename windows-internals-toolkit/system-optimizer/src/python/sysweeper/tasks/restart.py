"""人类文明重启计划场景透镜任务（restart · 洪荒重启，platform=any，跨平台）。

把用户导入的「对话人类文明重启计划」（别名洪荒重启）收口为只读场景透镜：维度清单、保命优先级
（不可再生优先）、知识库离线沉淀指引。只帮你想清楚「重启要保什么、按什么序」，绝不替你做任何施工。
"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="restart_report",
        platform="any",
        title="人类文明重启计划场景透镜（维度清单 + 保命优先级 + 知识库沉淀）",
        category="maintenance",
        risk="low",
        desc="只读场景透镜：文明重启维度清单（计算/网络/供电/存储与知识库/制造与供应链/人才与训练）、"
             "保命优先级（不可再生优先——知识库>制造>人才>供电>计算网络）、知识库离线沉淀指引"
             "（与 sysweeper 知识库同口径，优先开放许可）。绝不替你做任何施工/搬运。",
        actions=[
            N("restart.restart_report", "端到端生成人类文明重启计划场景透镜（维度→保命优先级→知识库沉淀）"),
        ],
        notes=["restart 只读场景透镜：只帮你想清楚「重启要保什么、按什么序」，不做任何施工。"],
        standards=["[导入] 对话人类文明重启计划（别名「洪荒重启」）场景透镜",
                  "[工程] 知识库优先沉淀（与 sysweeper data/ 知识库同口径，开放许可优先）",
                  "[工程] 保命优先级：不可再生资产（知识/制造/人才）优先于可替代设备"],
    ),
]
