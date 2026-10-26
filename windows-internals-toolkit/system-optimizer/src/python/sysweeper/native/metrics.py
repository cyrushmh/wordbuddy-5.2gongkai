r"""数学化量化评估引擎（借鉴 openai/math 的「数学即文档」思路，工程化落地）。

用户诉求是「利用数学 https://github.com/openai/math.git 完善优化整体」。
先说清一件事，避免误解与浪费：`openai/math` 是**LaTeX 数学宏的集合**
（`\frac`、`\sum`…），服务于 KaTeX / MathJax 这类数学公式渲染库，本身不含
任何与「系统优化」相关的内容。所以「把 math.git 引入本工具」有两条路：

- **不采用的路**：把上千个 LaTeX 宏 vendor 进来。那会让本工具从「零第三方依赖的
  系统优化器」变成「带字体/宏解析的排版工具」，与功能零增益，且违背本仓库
  「纯标准库、离线、零依赖」的第一原则。
- **采用的路（本模块）**：把 openai/math 背后的真正理念——**「用数学把话说精确」
  ——落到工程上。数学公式的价值在于把模糊判断变成可计算、可比较、可复现的量。
  本模块就提供这套量：

  1. **归一化（min-max normalization）**——把不同量纲的指标压到 [0,1]，
     使加权求和成为可能：x' = (x − min) / (max − min)。
  2. **加权评分（weighted sum model, WSM）**——经典多准则决策方法：
     S = Σ wᵢ · x̂ᵢ，Σwᵢ = 1。用于「一个系统优化工具覆盖得够不够全」的评分。
  3. **Shannon 熵（香农熵）**——H = −Σ pᵢ·log₂pᵢ，衡量任务在分类上的**分布均衡度**：
     熵高说明覆盖面广而不偏科，熵低说明扎堆在某一类。归一化后 H/log₂n ∈ [0,1]，
     即「归一化熵（normalized entropy）」，用来量化「大而全」而非「多而杂」。
  4. **Jaccard 相似度**——J(A,B) = |A∩B| / |A∪B|，量化两个档位/平台的
     任务集重合度（用来回答「minimal 档到底比 full 档少了什么」）。
  5. **Gini 系数 / 基尼不平等度**——G = Σ(2i−n−1)pᵢ/n ∈ [0,1]，
     衡量平台任务分布是否过度集中（1 = 全压在一处）。
  6. **余弦相似度（cosine similarity）**——用于「平台间能力画像」比较。
  7. **变异系数（CV = σ/μ）**——衡量各平台任务数的不均衡程度。
  8. **对数/幂律与覆盖缺口**——用类别基线检测「某类任务为 0」的盲区。

全部纯标准库（`math` 即可），无第三方依赖；输入是任务清单，输出是**可解释的
数字 + 一句人话结论**。所有除法都做零分母保护，任何空集/单元素集都不炸。
"""

from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from ..models import CATEGORY_ORDER, RISK_ORDER

# --------------------------------------------------------------------------- #
# 基础数学工具：归一化 / 统计量
# --------------------------------------------------------------------------- #


def normalize(xs: Sequence[float], invert: bool = False) -> List[float]:
    """min-max 归一化：x' = (x − min)/(max − min)，落到 [0,1]。

    - 全等序列（全为同一值）返回全 0.5（无区分度时取中性）。
    - invert=True 时反向（越小越好 → 越大越好），如「高危任务数」。
    """
    vals = [float(x) for x in xs]
    if not vals:
        return []
    lo, hi = min(vals), max(vals)
    if hi == lo:
        base = [0.5] * len(vals)
    else:
        base = [(x - lo) / (hi - lo) for x in vals]
    return [1.0 - b for b in base] if invert else base


def mean(xs: Sequence[float]) -> float:
    """算术平均；空序列返回 0.0。"""
    return sum(xs) / len(xs) if xs else 0.0


def stdev(xs: Sequence[float]) -> float:
    """总体标准差（除以 N）；空/单元素返回 0.0。"""
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def coefficient_of_variation(xs: Sequence[float]) -> float:
    """变异系数 CV = σ/μ（μ=0 时返回 0.0）。衡量相对离散度，量纲无关。"""
    m = mean(xs)
    if m == 0:
        return 0.0
    return stdev(xs) / abs(m)


def jaccard(a: Iterable, b: Iterable) -> float:
    """Jaccard 相似度 |A∩B|/|A∪B| ∈ [0,1]；两空集定义为 1.0（完全一致）。"""
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    union = sa | sb
    if not union:
        return 1.0
    return len(sa & sb) / len(union)


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """余弦相似度 ∈ [−1,1]；任一为零向量时返回 0.0（无定义但不出错）。"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# --------------------------------------------------------------------------- #
# 分布度量：Shannon 熵 / 归一化熵 / Gini
# --------------------------------------------------------------------------- #


def shannon_entropy(counts: Sequence[float]) -> float:
    """Shannon 熵 H = −Σ pᵢ·log₂ pᵢ（单位 bit）。零项按 0 处理（0·log0 = 0）。

    直觉：分布越均匀熵越大；全压在一处熵为 0。用于判断任务在分类上
    是否「广泛覆盖」还是「扎堆某一类」。
    """
    total = float(sum(counts))
    if total <= 0:
        return 0.0
    h = 0.0
    for c in counts:
        p = float(c) / total
        if p > 0:
            h -= p * math.log2(p)
    return h


def normalized_entropy(counts: Sequence[float]) -> float:
    """归一化熵 H / log₂ n ∈ [0,1]（n=len(counts)）。

    边界定义：
    - 空分布（n=0）→ 0.0：什么都没有，不存在「均不均」的问题；
    - 单一类别（n=1）→ 1.0：只有一类，无从偏科。
    """
    n = len(counts)
    if n == 0:
        return 0.0
    if n == 1:
        return 1.0
    total = float(sum(counts))
    if total <= 0:
        return 0.0
    return shannon_entropy(counts) / math.log2(n)


def gini_index(counts: Sequence[float]) -> float:
    """Gini 系数 G ∈ [0,1]（已按升序口径计算）。0=完全均分，1=全部集中在一项。

    公式（升序 p₁..pₙ，n 为类别数）：G = Σ(2i−n−1)·pᵢ / (n·Σpᵢ)。
    用「非零项数」作 n，避免空类别把系数算低。
    """
    vals = sorted(float(c) for c in counts if float(c) > 0)
    n = len(vals)
    total = sum(vals)
    if n <= 1 or total <= 0:
        return 0.0
    acc = 0.0
    for i, v in enumerate(vals, start=1):
        acc += (2 * i - n - 1) * v
    return acc / (n * total)


# --------------------------------------------------------------------------- #
# 任务集度量：覆盖广度 / 深度 / 风险画像
# --------------------------------------------------------------------------- #

#: 各分类的「理想权重」——体现「大而全」的价值取向：
#: 清理/维护是基础盘，网络/隐私/优化是延伸盘。（可按需调整，纯数值权重）
CATEGORY_WEIGHTS: Dict[str, float] = {
    "cleanup": 1.0,
    "maintenance": 0.9,
    "optimize": 0.8,
    "network": 0.7,
    "privacy": 0.7,
    "accessibility": 0.6,
}

#: 风险越高，视为「越危险」——评分里做惩罚项（负权）
RISK_PENALTY: Dict[str, float] = {"low": 0.0, "medium": 0.5, "high": 1.0}


def category_distribution(tasks: Sequence) -> Dict[str, int]:
    """任务按 category 计数（不含 opt_in 的特殊处理——这里只做纯分布）。"""
    d: Dict[str, int] = {}
    for t in tasks:
        d[t.category] = d.get(t.category, 0) + 1
    return d


def coverage_breadth(tasks: Sequence, baseline: Optional[Sequence[str]] = None) -> float:
    """覆盖广度 = 命中的分类数 / 基线分类数 ∈ [0,1]。

    baseline 默认取 CATEGORY_ORDER。用于「大小都要有」的第一个维度。
    """
    base = list(baseline or CATEGORY_ORDER)
    if not base:
        return 0.0
    hit = {t.category for t in tasks}
    return len(hit & set(base)) / len(base)


def risk_profile(tasks: Sequence) -> Dict[str, float]:
    """风险画像：low/medium/high 各占比（和为 1，空集全 0）。"""
    out = {"low": 0.0, "medium": 0.0, "high": 0.0}
    if not tasks:
        return out
    for t in tasks:
        r = t.risk if t.risk in out else "low"
        out[r] += 1
    n = float(len(tasks))
    return {k: v / n for k, v in out.items()}


def depth_score(tasks: Sequence, saturate: float = 40.0) -> float:
    """深度分 = 1 − e^(−n/saturate) ∈ [0,1)，n 为任务数。

    用饱和指数而非线性：20 个任务和 200 个任务的边际价值不同，
    指数曲线给「先快速涨、后趋缓」，符合「覆盖够用即可」的工程直觉。
    """
    n = len(tasks)
    if n <= 0:
        return 0.0
    return 1.0 - math.exp(-n / max(saturate, 1e-9))


# --------------------------------------------------------------------------- #
# 加权评分（WSM）——多准则决策
# --------------------------------------------------------------------------- #

#: 工具覆盖度评分（WSM）的权重。四个维度各司其职，和为 1。
SCORE_WEIGHTS: Dict[str, float] = {
    "breadth": 0.30,     # 分类覆盖广度（大而全）
    "entropy": 0.25,     # 分类分布均衡度（不偏科）
    "depth": 0.25,       # 任务数量深度（小而全的底座）
    "safety": 0.20,      # 安全性（低危占比高、无 opt_in 混入 = 更可用）
}


def coverage_score(tasks: Sequence) -> dict:
    """计算一个任务集的工具覆盖度评分（WSM），返回 {score, parts, summary}。

    score ∈ [0,1]，四部分：覆盖广度 / 分布均衡 / 任务深度 / 安全性。
    任何空集安全返回 score=0.0 与可读原因，绝不抛异常。
    """
    if not tasks:
        return {
            "score": 0.0,
            "parts": {"breadth": 0.0, "entropy": 0.0, "depth": 0.0, "safety": 0.0},
            "summary": "空任务集：无法评分（各维度均为 0）",
        }

    dist = category_distribution(tasks)
    # 分布均衡：按 CATEGORY_ORDER 全量计数（缺席类别算 0，熵自然变低）
    counts_all = [dist.get(c, 0) for c in CATEGORY_ORDER]
    breadth = coverage_breadth(tasks)
    entropy = normalized_entropy(counts_all)
    depth = depth_score(tasks)
    profile = risk_profile(tasks)
    # 安全性：低危占比（high 惩罚大）
    safety = 1.0 - (profile["high"] * RISK_PENALTY["high"]
                    + profile["medium"] * RISK_PENALTY["medium"] * 0.5)

    parts = {
        "breadth": breadth,
        "entropy": entropy,
        "depth": depth,
        "safety": safety,
    }
    score = sum(SCORE_WEIGHTS[k] * parts[k] for k in SCORE_WEIGHTS)
    # 一句人话结论
    if score >= 0.75:
        verdict = "覆盖相当充分（既广又深，且分布均衡）"
    elif score >= 0.55:
        verdict = "覆盖良好（广度或深度有一项偏弱）"
    elif score >= 0.35:
        verdict = "覆盖中等（存在明显短板，建议看 parts 定位）"
    else:
        verdict = "覆盖偏薄（小而全的极简集，或维度严重失衡）"
    return {
        "score": score,
        "parts": parts,
        "counts": dist,
        "risk": profile,
        "summary": f"{verdict}；任务数 {len(tasks)}，"
                   f"覆盖 {len(dist)}/{len(CATEGORY_ORDER)} 个分类",
    }


# --------------------------------------------------------------------------- #
# 平台间对比：画像向量 / 距离 / 盲区
# --------------------------------------------------------------------------- #


def platform_vector(tasks_by_platform: Dict[str, Sequence]) -> List[float]:
    """把「各平台任务数」变成向量（用于 CV / 均衡度诊断）。"""
    return [float(len(t)) for t in tasks_by_platform.values()]


def platform_balance(tasks_by_platform: Dict[str, Sequence]) -> dict:
    """平台任务分布均衡度诊断：返回 {cv, gini, verdict, detail}。

    Gini 高 = 某些平台任务扎堆、另一些被冷落；CV 同理（量纲无关）。
    """
    vec = platform_vector(tasks_by_platform)
    if len(vec) < 2:
        return {"cv": 0.0, "gini": 0.0, "verdict": "平台数不足，无法诊断均衡度", "detail": {}}
    cv = coefficient_of_variation(vec)
    gini = gini_index(vec)
    if gini >= 0.5:
        verdict = "分布明显不均：部分平台任务堆得过多，另一些偏少（可考虑补齐弱势平台）"
    elif gini >= 0.3:
        verdict = "分布略不均：主流平台较全，冷门平台相对薄"
    else:
        verdict = "分布较均衡：各平台覆盖量级接近"
    detail = {k: len(v) for k, v in tasks_by_platform.items()}
    return {"cv": cv, "gini": gini, "verdict": verdict, "detail": detail}


def coverage_gaps(all_tasks: Sequence, baseline: Optional[Sequence[str]] = None) -> List[str]:
    """覆盖缺口：全库完全没有任务的分类（baseline 默认 CATEGORY_ORDER）。"""
    base = list(baseline or CATEGORY_ORDER)
    present = {t.category for t in all_tasks}
    return [c for c in base if c not in present]


def similarity_report(ids_a: Iterable[str], ids_b: Iterable[str]) -> dict:
    """两个任务 id 集合的 Jaccard 对比：{jaccard, only_a, only_b, shared}。"""
    sa, sb = set(ids_a), set(ids_b)
    shared = sorted(sa & sb)
    return {
        "jaccard": jaccard(sa, sb),
        "shared": shared,
        "only_a": sorted(sa - sb),
        "only_b": sorted(sb - sa),
    }


# --------------------------------------------------------------------------- #
# 可读输出
# --------------------------------------------------------------------------- #


def score_report(tasks: Sequence, title: str = "覆盖度评分") -> str:
    """把 coverage_score 结果渲染成可读文本（含 WSM 公式与各分项）。"""
    r = coverage_score(tasks)
    parts = r["parts"]
    lines = [
        f"{title}：",
        f"   总分 = Σ wᵢ·x̂ᵢ = {r['score']:.4f}（0–1，越大覆盖越充分）",
        f"   权重: " + "  ".join(f"{k}={v}" for k, v in SCORE_WEIGHTS.items()),
        f"   覆盖广度 breadth = {parts['breadth']:.3f}"
        f"（命中分类 / 全部 {len(CATEGORY_ORDER)} 分类）",
        f"   分布均衡 entropy = {parts['entropy']:.3f}"
        f"（归一化 Shannon 熵 H/log₂n，越高越不偏科）",
        f"   任务深度 depth   = {parts['depth']:.3f}"
        f"（1 − e^(−n/{int(40)})，n=任务数）",
        f"   安全性 safety    = {parts['safety']:.3f}"
        f"（低危占比为主，高危按 {RISK_PENALTY['high']} 惩罚）",
        f"   结论: {r['summary']}",
    ]
    if "counts" in r and r["counts"]:
        cnt = r["counts"]
        lines.append("   分类分布: " + "  ".join(f"{k}={v}" for k, v in
                                                sorted(cnt.items(), key=lambda kv: -kv[1])))
    return "\n".join(lines)


def entropy_report(dist: Dict[str, int]) -> str:
    """把某分类分布渲染成 Shannon 熵 / 归一化熵 / Gini 的可读报告。"""
    keys = sorted(dist.keys())
    counts = [dist[k] for k in keys]
    h = shannon_entropy(counts)
    ne = normalized_entropy(counts)
    g = gini_index(counts)
    lines = [
        "分类分布熵分析（Shannon / 归一化熵 / Gini）：",
        f"   分类数 n = {len(keys)}，任务总数 = {sum(counts)}",
        f"   Shannon 熵 H = {h:.4f} bit（上限 log₂({len(keys)})"
        f" = {math.log2(len(keys)) if keys else 0:.4f}）",
        f"   归一化熵 H/log₂n = {ne:.4f}（1=完全均分，0=全压一处）",
        f"   Gini 系数 = {g:.4f}（0=均分，1=极端集中）",
    ]
    if keys:
        lines.append("   明细: " + "  ".join(f"{k}={dist[k]}" for k in keys))
    if ne >= 0.85:
        lines.append("   结论: 分布很均衡，覆盖不偏科（典型「大而全」形态）")
    elif ne >= 0.6:
        lines.append("   结论: 分布较均衡，个别分类偏多/偏少")
    else:
        lines.append("   结论: 分布偏斜——任务扎堆在少数分类，考虑向空白分类补齐")
    return "\n".join(lines)


__all__ = [
    "normalize", "mean", "stdev", "coefficient_of_variation",
    "jaccard", "cosine_similarity",
    "shannon_entropy", "normalized_entropy", "gini_index",
    "category_distribution", "coverage_breadth", "risk_profile", "depth_score",
    "coverage_score", "platform_vector", "platform_balance",
    "coverage_gaps", "similarity_report",
    "score_report", "entropy_report",
    "CATEGORY_WEIGHTS", "RISK_PENALTY", "SCORE_WEIGHTS",
]
