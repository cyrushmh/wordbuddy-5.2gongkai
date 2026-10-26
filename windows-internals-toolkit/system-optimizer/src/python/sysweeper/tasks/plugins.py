"""插件框架任务（只读展示「插件支持」）。

把 v0.5.20 新增的「插件支持」登记为一项任务：列出当前已注册的安全只读插件
（内置 openwrt / interop 聚合，以及用户通过 plugins/ 目录 drop-in 的清单），
并说明插件安全模型（native 入口仅限白名单只读函数，绝不执行任意代码）。

任务 platform="any"（任意平台都可读到插件系统本身），低风险、非 opt_in；
只读展示，不修改系统。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)

TASKS = [
    Task(
        id="plugin_framework",
        platform="any",
        title="插件支持：已注册的安全只读插件清单（只读）",
        category="maintenance",
        risk="low",
        opt_in=False,
        standards=[
            "[仓库] OpenWrt（GPL-2.0，作为 openwrt 内置插件只读引用）",
            "[官方] OpenWrt 各子系统文档（UCI/procd/netifd/ubus/LuCI/ImageBuilder…）",
        ],
        desc="展示「插件支持」：当前已注册的安全只读插件（内置 openwrt / interop 聚合，"
             "以及用户通过 $SYSWEEPER_PLUGINS_DIR 或仓库 plugins/ 目录 drop-in 的清单）。"
             "插件 native 入口仅限 NATIVE_ALLOWLIST 白名单内的只读函数，绝不执行任意代码。",
        actions=[N("plugins.plugin_report",
                   "列出已注册插件与能力（安全只读注册表）")],
        notes=[
            "内置插件：openwrt（路由器系统只读接口）、interop（第三方网络互联引用聚合）。",
            "用户插件：把一枚 *.json 清单放到 $SYSWEEPER_PLUGINS_DIR 或仓库 plugins/ 目录即被自动发现；",
            "清单须通过 plugin_validate：id 合法、native 入口全部在只读白名单内，否则拒绝注册。",
        ],
        caveats=[
            "插件不能执行任意代码：其 native 入口只能是 sysweeper.native 下已审读的零参只读函数；",
            "含任意命令/路径/shell 元字符或非白名单函数的清单会被直接拒绝（防注入）。",
        ],
    ),
]
