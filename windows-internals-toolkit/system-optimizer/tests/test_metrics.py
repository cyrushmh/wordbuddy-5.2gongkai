"""native/metrics.py 数学化量化引擎测试（v0.6.26）。

覆盖四块：
1. **纯数学原语**的正确性与边界（空集 / 单元素 / 全零 / 除零）；
2. **分布度量**（Shannon 熵 / 归一化熵 / Gini / Jaccard / 余弦）的数值性质；
3. **任务集评分**（覆盖广度 / 任务深度 / 风险画像 / WSM 总分）的取值范围与单调性；
4. **永不抛**：任何畸形输入都返回可读结果而非异常。

之所以单独成测：**评分一旦算错，给出的结论就是错的结论**——比崩溃更危险。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "python"))

from sysweeper.native import metrics as mt  # noqa: E402


class FakeTask:
    """够用即可的任务桩：评分层只依赖 category / risk / opt_in 三个字段。"""

    def __init__(self, category="cleanup", risk="low", opt_in=False, tid="t"):
        self.category = category
        self.risk = risk
        self.opt_in = opt_in
        self.id = tid


# ── 1. 归一化与基础统计量 ─────────────────────────────────────────────────────
def test_normalize_empty_and_flat():
    assert mt.normalize([]) == []
    # 全等序列无区分度，取中性值 0.5（见 normalize 文档，非 0）
    assert mt.normalize([5, 5, 5]) == [0.5, 0.5, 0.5]
    assert mt.normalize([5, 5, 5], invert=True) == [0.5, 0.5, 0.5]


def test_normalize_maps_to_unit_interval():
    got = mt.normalize([0, 5, 10])
    assert got == [0.0, 0.5, 1.0]
    assert all(0.0 <= x <= 1.0 for x in got)


def test_normalize_invert():
    got = mt.normalize([0, 5, 10], invert=True)
    assert got == [1.0, 0.5, 0.0]


def test_mean_stdev_cv_basics():
    assert mt.mean([1, 2, 3]) == pytest.approx(2.0)
    # 口径是**总体**标准差（除以 N），不是样本标准差
    assert mt.stdev([1, 2, 3]) == pytest.approx(0.8164966, abs=1e-6)
    # 单元素与空集不许抛
    assert mt.stdev([7]) == 0.0
    assert mt.stdev([]) == 0.0
    assert mt.coefficient_of_variation([2, 2, 2]) == pytest.approx(0.0)
    assert mt.coefficient_of_variation([]) == 0.0


# ── 2. 分布度量 ───────────────────────────────────────────────────────────────
def test_shannon_entropy_uniform_is_log2n():
    """n 类完全均分时 H 必须等于 log₂n —— 这是熵的定义性性质。"""
    for n in (2, 4, 8):
        assert mt.shannon_entropy([1] * n) == pytest.approx(math.log2(n))


def test_shannon_entropy_concentrated_is_zero():
    assert mt.shannon_entropy([5]) == 0.0
    assert mt.shannon_entropy([9, 0, 0]) == 0.0
    assert mt.shannon_entropy([]) == 0.0
    assert mt.shannon_entropy([0, 0]) == 0.0


def test_normalized_entropy_bounds():
    assert mt.normalized_entropy([]) == 0.0        # 空分布：无从谈均衡
    assert mt.normalized_entropy([4]) == 1.0       # 单类：无从偏科
    assert mt.normalized_entropy([1, 1, 1, 1]) == pytest.approx(1.0)
    skewed = mt.normalized_entropy([100, 1, 1, 1])
    assert 0.0 < skewed < 1.0
    # 越均分，归一化熵越大
    assert mt.normalized_entropy([5, 5]) > mt.normalized_entropy([9, 1])


def test_gini_bounds_and_direction():
    assert mt.gini_index([3, 3, 3, 3]) == pytest.approx(0.0)   # 完全均分
    assert mt.gini_index([1]) == 0.0
    assert mt.gini_index([]) == 0.0
    # 口径见 gini_index 文档：**空类别不计入 n**（避免缺任务反而把系数算低）。
    # 于是「全部集中在一个非空类」=空类不算 → 只有一个有效类 → G=0。
    assert mt.gini_index([0, 0, 0, 100]) == pytest.approx(0.0)
    extreme = mt.gini_index([1, 1, 1, 100])                    # 有分布就有不平等
    assert 0.0 < extreme <= 1.0
    # 差距越大，集中度越高
    assert mt.gini_index([1, 9]) > mt.gini_index([4, 6])


def test_jaccard_edges():
    assert mt.jaccard([], []) == 1.0            # 两空集定义一致
    assert mt.jaccard(["a"], []) == 0.0
    assert mt.jaccard(["a", "b"], ["a", "b"]) == 1.0
    disjoint = mt.jaccard(["a"], ["b"])
    assert disjoint == 0.0
    assert mt.jaccard(["a", "b"], ["b", "c"]) == pytest.approx(1 / 3)


def test_cosine_similarity_safe():
    assert mt.cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0)
    assert mt.cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)
    # 长度不等 / 零向量不许抛
    assert mt.cosine_similarity([1, 2], [1]) == 0.0
    assert mt.cosine_similarity([0, 0], [1, 1]) == 0.0


# ── 3. 任务集评分 ─────────────────────────────────────────────────────────────
def test_category_distribution_counts():
    tasks = [FakeTask("cleanup"), FakeTask("cleanup"), FakeTask("network")]
    assert mt.category_distribution(tasks) == {"cleanup": 2, "network": 1}


def test_coverage_breadth_fraction():
    seen = list(mt.CATEGORY_ORDER)
    tasks = [FakeTask(c) for c in seen]
    assert mt.coverage_breadth(tasks) == pytest.approx(1.0)
    half = [FakeTask(c) for c in seen[:len(seen) // 2]]
    assert 0.0 < mt.coverage_breadth(half) < 1.0


def test_risk_profile_sums_to_one():
    tasks = [FakeTask(risk="low")] * 4 + [FakeTask(risk="medium")] * 2 \
        + [FakeTask(risk="high")]
    p = mt.risk_profile(tasks)
    assert p["low"] == pytest.approx(4 / 7)
    assert p["medium"] == pytest.approx(2 / 7)
    assert p["high"] == pytest.approx(1 / 7)
    assert p["low"] + p["medium"] + p["high"] == pytest.approx(1.0)


def test_depth_score_monotone_saturating():
    few = mt.depth_score([FakeTask()] * 5)
    many = mt.depth_score([FakeTask()] * 60)
    huge = mt.depth_score([FakeTask()] * 500)
    enormous = mt.depth_score([FakeTask()] * 50000)
    assert 0.0 < few < many < huge < 1.0           # 单调递增、永不触 ceiling
    assert enormous <= 1.0                          # 极端量级只会在浮点上饱和
    assert mt.depth_score([]) == 0.0


def test_coverage_score_empty_is_safe():
    r = mt.coverage_score([])
    assert r["score"] == 0.0
    assert set(r["parts"]) == {"breadth", "entropy", "depth", "safety"}
    assert "空任务集" in r["summary"]


def test_coverage_score_parts_bounded_and_weights_sum_to_one():
    tasks = [FakeTask("cleanup", "low")] * 20 + [FakeTask("network", "medium")] * 10
    r = mt.coverage_score(tasks)
    assert 0.0 <= r["score"] <= 1.0
    for name, v in r["parts"].items():
        assert 0.0 <= v <= 1.0, f"分项 {name} 越界: {v}"
    assert sum(mt.SCORE_WEIGHTS.values()) == pytest.approx(1.0)
    # 总分必须能被权重与分项复算出来（防「评分与说明不一致」）
    recomputed = sum(mt.SCORE_WEIGHTS[k] * r["parts"][k] for k in mt.SCORE_WEIGHTS)
    assert r["score"] == pytest.approx(recomputed)


def test_safety_punishes_high_risk():
    safe = mt.coverage_score([FakeTask(risk="low")] * 30)
    risky = mt.coverage_score([FakeTask(risk="high")] * 30)
    assert safe["parts"]["safety"] > risky["parts"]["safety"]
    assert safe["score"] > risky["score"]


def test_score_report_and_entropy_report_render():
    txt = mt.score_report([FakeTask("cleanup")] * 10, "测试")
    assert "0" in txt and "entropy" in txt and "depth" in txt
    ent = mt.entropy_report({"cleanup": 3, "network": 1})
    assert "Shannon" in ent or "熵" in ent
    # 空分布也要能渲染
    assert isinstance(mt.entropy_report({}), str)


# ── 4. 平台均衡与缺口 ─────────────────────────────────────────────────────────
def test_platform_balance_gini_direction():
    even = {"a": [FakeTask()] * 10, "b": [FakeTask()] * 10}
    skew = {"a": [FakeTask()] * 100, "b": [FakeTask()] * 2}
    be, bs = mt.platform_balance(even), mt.platform_balance(skew)
    assert be["gini"] < bs["gini"]
    assert be["cv"] < bs["cv"]
    assert be["detail"] == {"a": 10, "b": 10}
    # 单平台无法诊断，不该抛
    assert mt.platform_balance({"a": [FakeTask()]})["cv"] == 0.0


def test_coverage_gaps_detects_missing_categories():
    base = list(mt.CATEGORY_ORDER)
    present = mt.CATEGORY_ORDER[0]
    gaps = mt.coverage_gaps([FakeTask(present)])
    assert set(gaps) == set(base) - {present}
    assert mt.coverage_gaps([FakeTask(c) for c in base]) == []


def test_similarity_report_shape():
    r = mt.similarity_report(["a", "b"], ["b", "c"])
    assert r["shared"] == ["b"]
    assert r["only_a"] == ["a"]
    assert r["only_b"] == ["c"]
    assert r["jaccard"] == pytest.approx(1 / 3)


@pytest.mark.parametrize("bad", [[], [0, 0], [-1, 2], [1, 1, 1, 1, 1]])
def test_metrics_never_raise_on_degenerate_input(bad):
    """任何畸形输入都得给出数字，不能把调用方（评分/CLI/Web）带崩。"""
    for fn in (mt.shannon_entropy, mt.normalized_entropy, mt.gini_index):
        v = fn(bad)
        assert isinstance(v, float)
        assert not math.isnan(v)
