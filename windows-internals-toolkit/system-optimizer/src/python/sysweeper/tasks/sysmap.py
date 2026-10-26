"""系统统筹总览任务（platform="any"，v0.6.18「统筹系统与局部、你中有我」）。

立项：把此前分散落地的只读诊断模块（网络全栈 / Tor / ZeroTier / Proton / WSL /
虚拟化-GPU / 浏览器 / 发行版 / 内核 / 单板机 / 优化资讯）织成一张系统地图。

- 整体与局部兼顾：既给「整体健康汇总」，也逐子系统给「局部本征状态」。
- 你中有我，我中有你：画出子系统之间的依赖与耦合（一个问题会传导到另一个）。
- 全面健康有序：给出「有序深入」的排查顺序，而不是堆孤岛、各看各的。

红线：本任务仅做只读聚合与关联，不启停服务、不改配置、不连控制端口、不写状态。
"""
from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)

SYS_OVERVIEW = ("[系统统筹] 只读编排既有子系统诊断，把分散模块织成系统地图"
                "（整体健康汇总 + 局部本征状态 + 关联关系 + 有序深入建议）")


TASKS = [
    Task(
        id="sysmap_overview",
        platform="any",
        title="系统统筹总览（你中有我，我中有你 · 统筹系统与局部）",
        category="maintenance",
        risk="low",
        desc="按统一清单只读编排**已开启**的子系统诊断（v0.6.22 起全量登记、可用选项开/关），"
             "输出「开关状态 + 整体健康汇总 + 局部本征状态 + 关联关系图（你中有我） + "
             "有序深入建议」，全面健康有序地看待一切。",
        actions=[
            N("sysmap.capabilities_report", "能力自检：可编排的子系统与红线声明"),
            N("sysmap.sysmap_report", "输出系统统筹总览（只读聚合 + 关联关系）"),
            M("某子系统异常时，用对应子命令钻取细节（写操作由你决定）",
              "深入排查（opt-in）"),
        ],
        standards=[SYS_OVERVIEW],
        notes=[
            "整体健康汇总：全部已登记子系统（默认全开）按 正常/提示/不适用/异常 四档收敛，"
            "先看清全局。",
            "选项开关：每个子系统可用 `sysweeper subsystems --disable <key>` 单独关闭，"
            "关闭后不诊断、不展示，关联图也不再画它那一端（配置落点 "
            "~/.config/sysweeper/subsystems.json）。",
            "局部本征状态：每个子系统只看状态，深入请用对应子命令钻取（tor/zerotier/"
            "dnshealth/proton/wsl/virtgpu/browser/...）。",
            "你中有我，我中有你：网络↔DNS、DNS↔Tor、Tor↔ZeroTier、Proton↔GPU/内核/"
            "发行版、浏览器↔DNS/字符标准 等耦合关系显式画出。",
            "有序深入：网络异常按 硬件→发行版→OSI→网络→DNS→覆盖层→虚拟组网→自组网 排序；"
            "兼容异常按 内核→GPU→发行版→Proton 排序。",
        ],
        caveats=[
            "只读总览：不启停服务、不改配置、不连控制端口、不写任何系统状态。",
            "某子系统诊断异常时只标「异常」并跳过，不影响整体总览。",
        ],
    ),
]
