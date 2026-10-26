"""浏览器与引擎检测 + Web 兼容知识参考任务（platform="any"，v0.6.15「导入 mdn/bcd」）。

立项：把 mdn/browser-compat-data（Web 平台特性跨浏览器支持度的 JSON 数据集）的
「结构化兼容知识」思路吸收进本工具——本任务只读做两件事：① 探测本机装了哪些
浏览器/引擎及版本；② 提供小型兼容知识参考（演示 BCD「特性→支持等级」结构）。

参照（权威文档，仅用于把「该看什么」钉死）：
- github.com/mdn/browser-compat-data —— Web 平台特性跨浏览器支持度数据集
 （@mdn/browser-compat-data；按浏览器/引擎/版本组织，是 caniuse 等工具的数据源）
"""
from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)

BCD = ("[MDN] mdn/browser-compat-data（Web 平台特性跨浏览器支持度 JSON 数据集；"
       "@mdn/browser-compat-data；caniuse 等工具的数据源，按浏览器/引擎/版本组织）")


TASKS = [
    Task(
        id="browser_report",
        platform="any",
        title="浏览器与引擎检测 + Web 兼容知识参考（mdn/bcd 坐标系，只读）",
        category="network",
        risk="low",
        desc="只读探测本机已装浏览器与渲染引擎（Blink/Gecko）及版本，并给出一份小型 Web "
             "平台特性兼容知识参考（结构性子集，演示 mdn/bcd 的数据组织方式）。",
        actions=[
            N("browser.capabilities_report", "能力自检：各维度是否可诊断 + 红线声明"),
            N("browser.browser_report", "输出浏览器/引擎检测 + Web 兼容知识参考"),
            M("需查完整跨浏览器特性矩阵时，引用 @mdn/browser-compat-data 数据集"
              "（不自动下载，由你决定做不做）", "引用完整 BCD 数据（写操作，opt-in）"),
        ],
        standards=[BCD],
        notes=[
            "浏览器探测：which chromium/chrome/firefox + --version；引擎 Blink(Chromium 系) "
            "/ Gecko(Firefox)。",
            "兼容知识参考：演示 mdn/bcd 的「特性→支持等级」结构（WebGPU / Container queries "
            "/ :has() / Top-level await / SharedArrayBuffer 等），为极简静态子集。",
            "完整数据：@mdn/browser-compat-data 是权威跨浏览器支持度数据源，按需引用。",
        ],
        caveats=[
            "只读任务：不下载 BCD 全量 JSON、不连校外网、不自动改浏览器配置。",
            "兼容知识为结构性子集，非实时数据库；精确支持度以 @mdn/browser-compat-data 为准。",
        ],
    ),
]
