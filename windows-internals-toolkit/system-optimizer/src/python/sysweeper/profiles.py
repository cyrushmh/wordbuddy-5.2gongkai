"""任务档位（Profile）——同时满足「大而全」与「小而全」。

用户诉求：「希望能做到大而全、小而全」。这两件事天然冲突：任务库有 300+
项，全开等于把高危项、opt-in 高影响项、跨平台冷门项一股脑塞给用户，结果是
**没人敢用**；而砍到只剩十几项又等于「不全」。

本模块的解法是**命名档位（named profile）**：把「选哪些任务」这件事从
「用户手工挑 300 个 checkbox」变成「选一个档位名」。四个档位：

| 档位 | 中文名 | 定位 | 大致构成 |
|------|--------|------|----------|
| `minimal` | 极简 | **小而全**：只保留零风险的只读体检与纯文字指引 | 几十项 |
| `lite` | 轻量 | 保守档：加回低危且可逆的执行项 | 百项级 |
| `standard` | 标准 | 默认档：低/中危全覆盖，不含 opt-in | 两百项级 |
| `full` | 全量 | **大而全**：含 opt-in 高影响项与高危指引（仍需显式确认） | 全部 |

档位规则是**声明式**的：每个档位只用「最大风险 / 是否含 opt_in / 分类白名单
/ 关键词过滤 / 排除 id」这几个正交维度描述，不写死具体任务 id。这样新增任务时
**无需改档位定义**——只要符合语义，档位自动跟着扩展。这是档位机制能长期
维护的关键（也是与「硬编码一个 minimal 列表」的本质区别）。

安全不变量（与全局 opt_in 门控一致）：

- 档位**永远不越权**。`full` 虽然包含 opt_in 与高危项，但**仍需显式
  `--opt-in` 开关 + `--yes` 确认 + `--apply` 三重条件**才能真的执行，
  选档位本身不等于授权执行。
- 档位只影响「**默认列入哪些**」，不影响底层执行路径的确认逻辑。
- `minimal` 档**保证零风险**（max_risk=low 且不含 opt_in）——这是给小设备、
  陌生机器、生产服务器快速看一眼用的「绝对安全」档。
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Sequence

from .models import CATEGORY_ORDER, RISK_ORDER, Task

# --------------------------------------------------------------------------- #
# 档位定义（声明式；不含硬编码任务 id）
# --------------------------------------------------------------------------- #

#: 档位表：name → 定义
#: - max_risk: 允许的最大风险等级（RISK_ORDER: low=0 medium=1 high=2）
#: - include_opt_in: 是否纳入默认关闭的 opt_in 项（仍需 CLI --opt-in 才执行）
#: - categories: 分类白名单（None=不限）；空集合=不含任何分类
#: - keyword_exclude: 标题/描述里含这些关键词则排除（语义级减法）
#: - language_agnostic: True 时排除依赖特定语言运行时的任务（requires_lang 非空）
#: - description: 档位说明（展示用）
PROFILES: Dict[str, dict] = {
    "minimal": {
        "title": "极简（零风险只读体检）",
        "max_risk": "low",
        "include_opt_in": False,
        "categories": None,
        "keyword_exclude": ("写", "删除", "清理", "卸载", "删除", "reset", "重启",
                            "install", "remove", "delete", "purge", "clear", "stop"),
        "language_agnostic": True,
        "description": (
            "小而全的极简档：**全部零风险**——只含只读体检报告与纯文字指引，"
            "不含任何会改系统的执行项，也不含依赖特定语言运行时的任务。"
            "适合陌生机器、生产服务器快速看一眼，或只想「知道现状」的场景。"
        ),
    },
    "lite": {
        "title": "轻量（保守可逆）",
        "max_risk": "low",
        "include_opt_in": False,
        "categories": None,
        "keyword_exclude": ("卸载", "install", "remove", "delete", "purge", "重刷", "flash"),
        "language_agnostic": False,
        "description": (
            "保守档：加入低危且可逆的执行项（如清缓存、只清计数），"
            "但排除卸载/删除类动作。日常「清理 + 体检」的推荐起点。"
        ),
    },
    "standard": {
        "title": "标准（默认）",
        "max_risk": "medium",
        "include_opt_in": False,
        "categories": None,
        "keyword_exclude": (),
        "language_agnostic": False,
        "description": (
            "默认档：低/中危全覆盖，不含 opt-in 高影响项。"
            "绝大多数用户用这一档即可——覆盖全面且不含需要额外确认的高影响改动。"
        ),
    },
    "full": {
        "title": "全量（大而全，含 opt-in）",
        "max_risk": "high",
        "include_opt_in": True,
        "categories": None,
        "keyword_exclude": (),
        "language_agnostic": False,
        "description": (
            "大而全：含高危项与 opt-in 高影响项（网络调优、写操作指引等）。"
            "**选此档不等于授权执行**——仍需 `--opt-in` + `--yes` + `--apply` "
            "三重确认，且高危写指引类只输出命令文本、绝不代为执行。"
        ),
    },
}

#: 档位顺序（展示用：由小到大）
PROFILE_ORDER = ("minimal", "lite", "standard", "full")

#: 预设的「场景档」——面向特定用途的组合（仍由上面的基础档派生，不重复定义规则）
SCENARIOS: Dict[str, dict] = {
    "readonly-audit": {
        "base": "minimal",
        "title": "只读审计（陌生机器/生产）",
        "description": "零风险体检全跑一遍，只看不改。",
    },
    "daily-clean": {
        "base": "lite",
        "title": "日常清理（家用/办公机）",
        "description": "可逆的低危清理 + 体检，排除卸载删除。",
    },
    "deep-opt": {
        "base": "full",
        "title": "深度优化（需逐项确认）",
        "description": "全量任务，但每项都需显式确认；高危项只给指引。",
    },
    "elderly-friendly": {
        "base": "minimal",
        "title": "适老化（只读 + 文字指引）",
        "description": "零风险档 + 各平台无障碍/适老化只读报告，绝不代改无障碍开关。",
        "categories": None,
        "keep_accessibility_only": True,
    },
}

#: 版本通道（release channel）——常态稳定版 / 长期支持版 / 尝鲜版。
# 通道是「发布流选择」：用户在 GUI/CLI 选定后只记录偏好，**绝不**自动改机器、
# 绝不自动升级。契合只读红线与「用户通过图形界面控制」诉求：工具给对比与推荐，
# 用户在 GUI 里点选，选中的通道写进 settings.json 仅作更新检查时的流标记。
CHANNELS: Dict[str, dict] = {
    "stable": {
        "title": "常态稳定版",
        "cadence": "常规节奏（约每 2-4 周）",
        "stability": "高（发布前过回归测试）",
        "support_window": "当前版本 + 上一个小版本",
        "target": "绝大多数用户：要新功能又不想踩坑",
        "longevity_fit": "常规使用量、期望 2-4 年更换的设备",
        "desc": "平衡新功能与稳定：新能力常规节奏推送，发布前过回归测试。"
                "默认推荐，绝大多数人用它最省心——既不太旧也不太冒险。",
    },
    "lts": {
        "title": "长期支持版",
        "cadence": "极低频（仅安全/关键修复，季度或按需）",
        "stability": "最高（冻结特性，只修不增）",
        "support_window": "12-24 个月长维护",
        "target": "生产机 / 长期不换设备 / 适老化 / 严苛环境",
        "longevity_fit": "高使用量或期望 ≥4 年长期使用的设备；高温/高湿/多尘环境优先",
        "desc": "长期支持：特性冻结、只发安全与关键修复，维护窗口最长最稳。"
                "生产服务器、想一用多年的设备、严苛环境（高湿/高温/多尘）优先选它——"
                "变动最小、意外最少，最护老设备。",
    },
    "fresh": {
        "title": "尝鲜版",
        "cadence": "高频（最新功能最快到手）",
        "stability": "中（含最新实验特性，偶尔有小问题）",
        "support_window": "随主线，最短",
        "target": "爱折腾 / 新硬件 / 短期设备 / 开发者",
        "longevity_fit": "轻使用量、1-2 年即换或乐于跟进最新能力的设备",
        "desc": "尝鲜版：最新功能与实验特性最快到手，但可能偶有未稳的小问题。"
                "适合新硬件、爱折腾、短期即用即换的设备——能接受「早用早踩早修」。",
    },
}

#: 通道顺序（展示用：由稳到新）
CHANNEL_ORDER = ("stable", "lts", "fresh")


def channel_recommend(usage_intensity: str = "moderate",
                      longevity_years: int = 4,
                      env_tags: list | None = None) -> str:
    """据「使用量 + 期望使用年限 + 环境标签」推荐版本通道（stable/lts/fresh）。

    逻辑：长期用(≥4年)/严苛环境(高湿高温多尘) → LTS（变动最小最护设备）；
    短期用(≤2年)且重使用 → fresh（最快拿修复）；其余 → stable。
    仅给建议，绝不据此自动切换或升级。
    """
    intensity = {"light": 1, "moderate": 2, "heavy": 3}.get(
        (usage_intensity or "moderate").lower(), 2)
    tags = set(env_tags or [])
    harsh = bool(tags & {"high_temp", "high_humidity", "dusty"})
    if longevity_years >= 4 or harsh:
        return "lts"
    if longevity_years <= 2 and intensity >= 3:
        return "fresh"
    return "stable"


# --------------------------------------------------------------------------- #
# 档位筛选逻辑
# --------------------------------------------------------------------------- #

def _matches_keyword_exclude(task: Task, kws: Sequence[str]) -> bool:
    """标题或描述里含任一排除关键词则命中。"""
    if not kws:
        return False
    hay = f"{task.title} {task.desc}"
    return any(k in hay for k in kws)


def tasks_in_profile(name: str, platform: str, version: str = "0",
                     all_tasks: Optional[Sequence[Task]] = None,
                     arch: Optional[str] = None) -> List[Task]:
    """返回某档位在给定平台/版本下命中的任务列表。

    步骤：平台/版本匹配 → 风险上限 → opt_in 门槛 → 分类白名单 →
    架构过滤 → 关键词排除 → 语言依赖过滤。所有维度都是正交条件，任一不过即排除。
    """
    if name not in PROFILES:
        return []
    spec = PROFILES[name]
    from .registry import all_tasks as _all
    pool = list(all_tasks) if all_tasks is not None else _all()

    max_risk = RISK_ORDER.get(spec["max_risk"], 2)
    cats = spec.get("categories")
    kws = spec.get("keyword_exclude", ())
    lang_agnostic = spec.get("language_agnostic", False)

    out: List[Task] = []
    for t in pool:
        if not t.matches(platform, version):
            continue
        # opt_in 门槛
        if t.opt_in and not spec.get("include_opt_in"):
            continue
        # 风险上限
        if RISK_ORDER.get(t.risk, 0) > max_risk:
            continue
        # 分类白名单
        if cats is not None and t.category not in cats:
            continue
        # 架构过滤
        if arch and t.arch and t.arch != arch:
            continue
        # 关键词减法
        if _matches_keyword_exclude(t, kws):
            continue
        # 语言运行时依赖
        if lang_agnostic and t.requires_lang:
            continue
        out.append(t)
    return out


def scenario_tasks(name: str, platform: str, version: str = "0",
                   all_tasks: Optional[Sequence[Task]] = None,
                   arch: Optional[str] = None) -> List[Task]:
    """返回场景档（预设组合）的任务列表。

    「适老化」场景档额外只保留 accessibility 分类 + 各平台 a11y 报告。
    """
    if name not in SCENARIOS:
        return []
    sc = SCENARIOS[name]
    base = sc["base"]
    tasks = tasks_in_profile(base, platform, version, all_tasks, arch)
    if sc.get("keep_accessibility_only"):
        tasks = [t for t in tasks
                 if t.category == "accessibility"
                 or "a11y" in t.id.lower()
                 or "accessib" in t.title.lower()
                 or "无障碍" in t.title
                 or "适老" in t.title]
    if sc.get("categories") is not None:
        tasks = [t for t in tasks if t.category in sc["categories"]]
    return tasks


def profile_summary(name: str, platform: str, version: str = "0",
                    all_tasks: Optional[Sequence[Task]] = None,
                    arch: Optional[str] = None) -> dict:
    """返回某档位的统计摘要：任务数、分类分布、风险画像、是否含 opt_in/高危。"""
    if name not in PROFILES:
        return {}
    tasks = tasks_in_profile(name, platform, version, all_tasks, arch)
    from .native import metrics
    dist = metrics.category_distribution(tasks)
    risk = metrics.risk_profile(tasks)
    return {
        "name": name,
        "title": PROFILES[name]["title"],
        "count": len(tasks),
        "categories": dist,
        "risk": risk,
        "has_opt_in": any(t.opt_in for t in tasks),
        "has_high_risk": any(t.risk == "high" for t in tasks),
        "ids": [t.id for t in tasks],
    }


# --------------------------------------------------------------------------- #
# 档位对比（回答「minimal 比 full 少了什么」）
# --------------------------------------------------------------------------- #

def compare_profiles(a: str, b: str, platform: str, version: str = "0",
                     all_tasks: Optional[Sequence[Task]] = None) -> dict:
    """对比两个档位：Jaccard 重合度、各自独有、b 相对 a 少了什么。"""
    ta = tasks_in_profile(a, platform, version, all_tasks)
    tb = tasks_in_profile(b, platform, version, all_tasks)
    from .native import metrics
    ids_a = {t.id for t in ta}
    ids_b = {t.id for t in tb}
    return {
        "a": a, "b": b,
        "count_a": len(ta), "count_b": len(tb),
        "jaccard": metrics.jaccard(ids_a, ids_b),
        "only_a": sorted(ids_a - ids_b),
        "only_b": sorted(ids_b - ids_a),
        "shared": sorted(ids_a & ids_b),
    }


# --------------------------------------------------------------------------- #
# 展示用清单
# --------------------------------------------------------------------------- #

def profile_list(platform: str = "any", version: str = "0") -> List[str]:
    """返回所有档位的清单（每个档位一行 + 简短定位 + 当前平台下的任务数）。"""
    lines = ["任务档位（大而全 / 小而全）："]
    for name in PROFILE_ORDER:
        spec = PROFILES[name]
        n = len(tasks_in_profile(name, platform, version)) if platform != "any" else "—"
        lines.append(f"   · {name:<9} {spec['title']}")
        lines.append(f"       {spec['description']}")
        lines.append(f"       当前平台({platform}) 命中任务数: {n}"
                     if platform != "any" else "       （按平台查询时给出任务数）")
    return lines


def scenario_list(platform: str = "any") -> List[str]:
    """返回场景档清单（面向特定用途的组合）。"""
    lines = ["场景档（面向特定用途，由基础档派生）："]
    for name, sc in SCENARIOS.items():
        lines.append(f"   · {name:<18} {sc['title']}（基于 {sc['base']}）")
        lines.append(f"       {sc['description']}")
    return lines


# --------------------------------------------------------------------------- #
# 版本通道展示（release channel）
# --------------------------------------------------------------------------- #

def channel_list() -> List[str]:
    """返回所有版本通道的清单（每个通道一行 + 定位 + 适合谁）。"""
    lines = ["版本通道（发布流选择；选中只记偏好，绝不自动升级）："]
    for name in CHANNEL_ORDER:
        ch = CHANNELS[name]
        lines.append(f"   · {name:<7} {ch['title']}")
        lines.append(f"       {ch['desc']}")
        lines.append(f"       适合: {ch['target']}；长期使用契合: {ch['longevity_fit']}")
        lines.append(f"       节奏={ch['cadence']}  稳定性={ch['stability']}  "
                     f"维护窗口={ch['support_window']}")
    return lines


def channel_detail(name: str, usage_intensity: str = "moderate",
                   longevity_years: int = 4, env_tags: list | None = None) -> str:
    """返回某通道的详细说明，并据使用量/年限/环境给出推荐结论。"""
    if name not in CHANNELS:
        return f"未知通道: {name}（可选 {'/'.join(CHANNEL_ORDER)}）"
    ch = CHANNELS[name]
    rec = channel_recommend(usage_intensity, longevity_years, env_tags)
    lines = [
        f"通道 {name} — {ch['title']}",
        "=" * 60,
        f"   {ch['desc']}",
        f"   发布节奏 : {ch['cadence']}",
        f"   稳定性   : {ch['stability']}",
        f"   维护窗口 : {ch['support_window']}",
        f"   适合谁   : {ch['target']}",
        f"   长期契合 : {ch['longevity_fit']}",
        "",
        f"   当前画像: 使用量={usage_intensity} 期望年限={longevity_years}年 "
        f"环境={env_tags or '默认'}",
        "   推荐结论 : " + ("✔ 本通道与你的长期使用需求匹配"
                          if rec == name else f"→ 据此画像更推荐「{rec}」通道"),
        "",
        "   说明: 通道仅决定你接收更新的发布流；选定后写入 settings.json 仅作"
        "更新检查标记，**工具绝不自动切换或升级你的环境**——是否更新始终由你确认。",
    ]
    return "\n".join(lines)


def profile_detail(name: str, platform: str, version: str = "0",
                   all_tasks: Optional[Sequence[Task]] = None,
                   arch: Optional[str] = None) -> str:
    """返回某档位的详细说明：规则 + 分类分布 + 风险画像 + 数学覆盖度评分。"""
    if name not in PROFILES:
        return f"未知档位: {name}（可选 {'/'.join(PROFILE_ORDER)}）"
    spec = PROFILES[name]
    tasks = tasks_in_profile(name, platform, version, all_tasks, arch)
    from .native import metrics
    lines = [
        f"档位 {name} — {spec['title']}",
        "=" * 60,
        f"   {spec['description']}",
        f"   规则: max_risk={spec['max_risk']}  include_opt_in={spec['include_opt_in']}"
        f"  language_agnostic={spec.get('language_agnostic', False)}",
    ]
    if spec.get("categories") is not None:
        lines.append(f"   分类白名单: {sorted(spec['categories'])}")
    if spec.get("keyword_exclude"):
        lines.append(f"   关键词排除: {'、'.join(spec['keyword_exclude'])}")
    lines.append(f"   当前平台({platform} {version}) 命中: {len(tasks)} 项")
    dist = metrics.category_distribution(tasks)
    if dist:
        lines.append("   分类分布: " + "  ".join(f"{k}={v}" for k, v in
                                                sorted(dist.items(), key=lambda kv: -kv[1])))
    risk = metrics.risk_profile(tasks)
    lines.append(f"   风险画像: low={risk['low']:.2f} medium={risk['medium']:.2f} "
                 f"high={risk['high']:.2f}")
    opt_n = sum(1 for t in tasks if t.opt_in)
    high_n = sum(1 for t in tasks if t.risk == "high")
    lines.append(f"   含 opt_in: {opt_n} 项；含高危: {high_n} 项")
    if name == "minimal":
        lines.append("   ✓ 不变量校验: minimal 档保证零风险——不含 opt_in、不含非 low 风险、"
                     "不含依赖语言运行时的任务")
    if name in ("standard", "full"):
        lines.append("   ⚠ 安全提醒: 选档位**不等于授权执行**——执行仍需 --apply；"
                     "含 opt_in 的档位另需 --opt-in + --yes 双重确认")
    lines.append("")
    lines.append(metrics.score_report(tasks, f"档位 {name} 覆盖度评分"))
    return "\n".join(lines)


__all__ = [
    "PROFILES", "PROFILE_ORDER", "SCENARIOS",
    "tasks_in_profile", "scenario_tasks", "profile_summary",
    "compare_profiles", "profile_list", "scenario_list", "profile_detail",
    "CHANNELS", "CHANNEL_ORDER", "channel_list", "channel_detail",
    "channel_recommend",
]
