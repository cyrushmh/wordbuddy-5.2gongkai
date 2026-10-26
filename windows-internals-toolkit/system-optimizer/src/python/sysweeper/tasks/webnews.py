"""新闻 / 网站优化资讯任务（platform="any"，v0.6.11 新增）。

立项：把新闻或网站「拿来」优化整体——但本层只做「拿来 + 读懂 + 当建议展示」，
**绝不**把抓来的内容当命令执行。两个任务：

1. webnews_fetch   ：抓你配置的来源 → 解析 → 抽知识点 → 缓存（只读，可联网）。
2. webnews_knowledge：读缓存 → 把知识点按分类摆出来（只读建议，不带网）。

红线：任何情况下都不自动改系统设置；要不要照着来源做由你决定。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)

SRC = ("[官方] 你自行配置的新闻/网站源（RSS 2.0 / Atom / 网页），"
       "本工具只抓 http(s)，不碰任何可执行内容")
NET = ("[国际] IETF RFC 9110（HTTP 语义；RFC 7231 的现行版）/ RSS 2.0 / Atom 1.0（订阅格式规范）")


TASKS = [
    Task(
        id="webnews_fetch",
        platform="any",
        title="优化资讯抓取（抓你配置的新闻/网站，抽知识点入缓存）",
        category="maintenance",
        risk="medium",
        desc="从你配置的来源（http/https RSS 或网页）抓取内容、解析条目、"
             "按平台/分类抽取可落地的优化知识点，写入本地缓存。只读、可联网。",
        actions=[
            N("webnews.sources_report", "先列出当前配置的来源（默认空，不默认联网）"),
            N("webnews.capabilities_report", "本层能力自检（抓取/解析/缓存可用性）"),
            N("webnews.fetch_all", "抓取全部已配置来源并抽取知识点（失败源如实报「未能获取」）"),
        ],
        standards=[NET, SRC],
        notes=[
            "默认来源为空（设计如此：不默认联网）。在 native/webnews.py 的 "
            "DEFAULT_SOURCES 里加入你信任的 http(s) 地址，再运行本任务才会去抓。",
            "抓取带 8 秒超时与 2 MiB 体积上限；单源失败不影响其它源，失败源进错误列表。",
            "抓来的永远是文本：本层没有任何执行路径，不 eval、不 subprocess、"
            "不自动改系统——知识点只是「关注方向」，不是现成操作步骤。",
            "缓存落在 XDG ~/.config/sysweeper/webnews.json，只存 URL/标题/摘要/"
            "知识点文字，损坏就回退默认，不拖垮界面。",
        ],
        caveats=[
            "可联网任务：只拉你自己填的 http(s) 地址；拉不到就报「未能获取」，绝不编造。",
            "风险 medium 仅因「会联网」，不因为任何写操作——本任务零写入。",
        ],
    ),
    Task(
        id="webnews_knowledge",
        platform="any",
        title="优化资讯知识点（读缓存，按分类摆出来，只读建议）",
        category="maintenance",
        risk="low",
        desc="读上一次抓取的缓存，把其中与系统优化相关的知识点按平台/分类整理成"
             "可读建议。不带网、不重抓。",
        actions=[
            N("webnews.knowledge_report", "读缓存输出知识点（按分类，带来源归属）"),
        ],
        standards=[SRC],
        notes=[
            "看点开来源自行核对具体做法——关键词命中只代表「这条信息可能与该分类"
            "优化有关」，不代表源里一定给了操作步骤。",
            "缓存 6 小时有效；想看最新就先跑 webnews_fetch。",
        ],
        caveats=[
            "只读任务：不联网、不写盘、不改任何设置。",
            "缓存为空时会明确说「还没有资讯」，不会把空数据包装成「已是最优」。",
        ],
    ),
]
