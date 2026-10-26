"""数字矩阵冗余数据任务（matrix，platform=any，v0.6.84）——周天星斗大阵 task 侧。

只读观测散落全盘的冗余数据（缓存/临时/包管理缓存/回收站/日志轮转）如满天星斗；
denylist（个人数据与关键资产）是系统生存根基，清理永不涉足。任何清理动作一律
只给文本指引，由用户沿原路执行——本任务集不删除、不移动、不改写任何数据。

指导理念：道法自然 · 活在当下 · 只有生存才能发展 · 在发展中能更好的生存 · 如此循环，亦复如是。
"""

from __future__ import annotations

from ..models import Action, Task

M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="matrix_report",
        platform="any",
        title="数字矩阵冗余数据只读观测（周天星斗大阵：缓存/临时/回收站/日志，只读不删）",
        category="maintenance",
        risk="low",
        desc="只读统计 allowlist 内冗余数据目录的存在性与体积（用户缓存/临时/包管理器缓存/"
             "回收站/日志轮转），denylist（个人数据与关键资产）完全不扫描、不统计、不清理。"
             "allowlist 与 denylist 展开后无交集由模块加载即校验。清理建议仅以文本交还用户。",
        actions=[
            N("matrix.matrix_report", "端到端生成周天星斗大阵只读观测报告（星斗分布→合计→清理指引）"),
            N("matrix.environment_report", "环境概览：HOME/XDG_CACHE_HOME 与扫描面存在性（只读）"),
        ],
        notes=[
            "只读观测 ≠ 授权清理：本任务不删除、不移动、不改写任何数据，清理动作由用户沿原路执行。",
            "denylist（~/.ssh、~/Documents、浏览器 profile 等个人数据与关键资产）完全不触碰——"
            "只有生存才能发展，误删关键资产危及生存，宁可不清。",
            "构建产物目录（node_modules/target 等）误伤风险高，只作文本指引不进扫描面。",
            "体积统计不跟随符号链接（防软链越界到 denylist），深度/条目超上限即截断，宁少算不拖死。",
        ],
        standards=["[国际] XDG Base Directory Specification（XDG_CACHE_HOME 缓存约定）",
                   "[国际] freedesktop Trash 规范（~/.local/share/Trash）",
                   "[理念] 周天星斗大阵：道法自然/活在当下/只有生存才能发展/在发展中更好的生存/循环上升"],
    ),
    Task(
        id="matrix_reclaim_guidance",
        platform="any",
        title="冗余数据清理规范指引（仅文本，沿原路返回）",
        category="maintenance",
        risk="low",
        desc="给出冗余数据清理的规范指引（先用只读报告确认、用包管理器自带接口、回收站先确认、"
             "日志交给 logrotate/journalctl），绝不自动执行任何删除。",
        actions=[
            M("清理前先用只读报告确认目录与体积，不要凭记忆 rm -rf；"
              "包管理器用 apt clean / pacman -Sc / dnf clean all；"
              "回收站清空不可逆，先确认无待恢复文件；日志交给 logrotate / journalctl --vacuum。",
              "冗余数据清理规范指引（不代执行）"),
        ],
        notes=["清理是写操作，一律只给指引；是否施工由用户确认后自行执行。"],
        standards=["[理念] 原路返回：建议仅以文本交还用户，不代行写操作"],
    ),
]
