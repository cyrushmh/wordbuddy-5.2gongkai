"""跨平台（platform="any"）的清理/优化/维护任务，统一复用 native/common 接口。

设计动机（分类规范整体 + 增删增强）：
- Linux / BSD / Unix 原先各自写了一份几乎相同的「用户缓存清理」「临时目录清理」，
  属于跨平台重复。这里收敛为统一的 any_* 任务，覆盖所有操作系统平台（不含 uni-app
  这类跨端目标），减少重复、保证行为一致。
- 动作一律走 native/common 的「仅列举、不删除」接口，或 manual 指引，符合
  「默认只分析不乱删」；执行需显式 --apply 且中高风险 --yes 确认。

原生接口缺失时自动降级为指引，不强求安装任何工具。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)


TASKS = [
    Task(
        id="any_user_cache",
        platform="any",
        title="用户缓存目录清点（跨平台）",
        category="cleanup",
        risk="low",
        desc="按 XDG Base Directory / Windows LocalAppData 规范列出当前用户缓存目录与体积，"
             "辅助定位可清理项（不删除）。",
        actions=[N("common.user_cache_report", "列出 ~/.cache（或 LOCALAPPDATA）体积，仅分析")],
        notes=[
            "参考规范：XDG Base Directory（~/.cache）/ Windows 用户库（LOCALAPPDATA）。",
            "仅清点，不删除；真正清理请用各平台对应的缓存清理任务（如 linux_user_cache）。",
        ],
        caveats=["不在 analyze 模式删除任何文件；清理请用对应平台任务并评估影响。"],
    ),
    Task(
        id="any_temp_report",
        platform="any",
        title="临时目录清点（跨平台）",
        category="cleanup",
        risk="low",
        desc="列出系统/用户临时目录（POSIX /tmp、Windows %TEMP%）体积，仅分析不清理。",
        actions=[N("common.temp_report", "列出 /tmp（或 %TEMP%）体积，仅分析")],
        notes=["参考规范：各平台临时目录约定（POSIX /tmp、Windows Temp）。"],
        caveats=["多数系统临时目录重启即清；analyze 仅列举遗留旧文件。"],
    ),
    Task(
        id="any_large_dirs",
        platform="any",
        title="家目录最大子目录报告（辅助瘦身）",
        category="maintenance",
        risk="low",
        desc="用 Python 标准库列出家目录下体积最大的若干子目录，辅助定位可瘦身项（只读）。",
        actions=[N("common.large_dirs_report", "列出家目录前 10 大子目录体积，仅分析")],
        notes=["纯标准库 os.walk 递归统计；不删除任何文件，可安全执行。"],
    ),
    Task(
        id="any_dns_flush",
        platform="any",
        title="刷新 DNS 解析器缓存（指引）",
        category="optimize",
        risk="low",
        desc="给出刷新本地 DNS 缓存的命令（systemd-resolved / nscd / mDNSResponder / Windows），"
             "排查 DNS 污染或解析陈旧时可用。",
        actions=[N("common.dns_flush_hint", "探测并提示对应平台的 DNS 刷新命令，仅指引")],
        notes=[
            "属优化类指引：解析器缓存（glibc nss / systemd-resolved）刷新可加速新解析生效。",
            "需 --apply 且 --yes 才会执行对应命令；部分环境需管理员权限。",
        ],
        caveats=["刷新 DNS 缓存后已解析的域名需重新查询，属正常行为。"],
    ),
]
