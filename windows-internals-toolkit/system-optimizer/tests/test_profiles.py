"""profiles.py 任务档位测试（v0.6.26）。

档位的价值全在**不变量**上——如果不变量破了，「小而全」就可能把高危项放进来，
而这是比「档位不好用」严重得多的事。所以这里测的全是硬性质：

1. **包含链** minimal ⊆ lite ⊆ standard ⊆ full（小而全必须是大而全的子集）；
2. **minimal 零风险**：不含 opt_in、不含非 low 风险、不依赖语言运行时；
3. **lite 不含删除类**动作（可逆承诺）；
4. **档位新任务自动继承**：档位规则是声明式的，改任务库不用改档位定义；
5. 未知档位**静默返回空**而不是抛异常（CLI 层另有提示，库层不该炸）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "python"))

from sysweeper import profiles as pf  # noqa: E402
from sysweeper import registry  # noqa: E402

PLATFORM, VERSION = "linux", "24.04"


@pytest.fixture(scope="module")
def ids():
    """四个基础档位在 linux 下的任务 id 集合（只读一次，供多条断言复用）。"""
    return {name: {t.id for t in pf.tasks_in_profile(name, PLATFORM, VERSION)}
            for name in pf.PROFILE_ORDER}


# ── 1. 包含链与规模单调 ───────────────────────────────────────────────────────
def test_profile_chain_is_subset(ids):
    """小而全必须是大而全的子集：否则「极简」就不成其为极简。"""
    order = pf.PROFILE_ORDER
    for i in range(len(order) - 1):
        lo, hi = order[i], order[i + 1]
        extra = ids[lo] - ids[hi]
        assert not extra, f"{lo} 不是 {hi} 的子集，多出 {len(extra)} 项：{sorted(extra)[:5]}"


def test_profile_counts_monotonic(ids):
    counts = [len(ids[n]) for n in pf.PROFILE_ORDER]
    assert counts == sorted(counts), f"档位规模应随档位递增，实际 {counts}"
    assert counts[0] > 0, "minimal 档不该为空"


def test_minimal_strictly_smaller_than_full(ids):
    """极简必须真的更小——否则「小而全」与「大而全」没有区别，档位就没意义。"""
    assert len(ids["minimal"]) < len(ids["full"])


# ── 2. minimal 的零风险承诺 ───────────────────────────────────────────────────
def test_minimal_is_zero_risk_and_no_optin():
    tasks = pf.tasks_in_profile("minimal", PLATFORM, VERSION)
    assert tasks
    highs = [t.id for t in tasks if t.risk != "low"]
    assert not highs, f"minimal 混入非低危任务: {highs[:5]}"
    optins = [t.id for t in tasks if t.opt_in]
    assert not optins, f"minimal 混入 opt_in 任务: {optins[:5]}"


def test_minimal_excludes_destructive_keywords():
    """「写/删除/卸载/重启」这类标题不该出现在极简档里。"""
    banned = set(pf.PROFILES["minimal"]["keyword_exclude"])
    assert banned, "keyword_exclude 不该为空"
    for t in pf.tasks_in_profile("minimal", PLATFORM, VERSION):
        hit = next((w for w in banned if w in t.title), None)
        assert hit is None, f"{t.id} 命中排除词「{hit}」：{t.title}"


def test_minimal_is_language_agnostic():
    """极简档不依赖特定语言运行时——陌生机器上不该因为没装某个解释器就跑不了。"""
    assert pf.PROFILES["minimal"]["language_agnostic"] is True
    for t in pf.tasks_in_profile("minimal", PLATFORM, VERSION):
        assert not getattr(t, "requires_lang", ""), \
            f"{t.id} 依赖语言运行时 {t.requires_lang}，不该进极简档"


# ── 3. lite 的可逆承诺 ────────────────────────────────────────────────────────
def test_lite_excludes_uninstall_actions():
    destroy = set(pf.PROFILES["lite"]["keyword_exclude"])
    for t in pf.tasks_in_profile("lite", PLATFORM, VERSION):
        hit = next((w for w in destroy if w in t.title), None)
        assert hit is None, f"{t.id} 命中删除类关键词「{hit}」，违背 lite 可逆承诺"
        assert t.risk == "low", f"{t.id} 风险为 {t.risk}，不该在 lite 档"


def test_full_is_the_only_profile_with_optin_default():
    """只有 full 默认放 opt_in 进来；其余档宁可少给也不越权。"""
    for name in ("minimal", "lite", "standard"):
        assert pf.PROFILES[name]["include_opt_in"] is False, f"{name} 不应默认含 opt_in"
    assert pf.PROFILES["full"]["include_opt_in"] is True


# ── 4. 场景档 ─────────────────────────────────────────────────────────────────
def test_scenarios_derive_from_base(ids):
    for name, sc in pf.SCENARIOS.items():
        got = {t.id for t in pf.scenario_tasks(name, PLATFORM, VERSION)}
        if sc.get("keep_accessibility_only"):
            assert got <= ids[sc["base"]], f"{name} 应是其基础档的子集"
        elif sc.get("categories") is None:
            assert got == ids[sc["base"]], f"{name} 无额外过滤时应等于基础档"


def test_elderly_scenario_keeps_only_accessibility():
    tasks = pf.scenario_tasks("elderly-friendly", PLATFORM, VERSION)
    assert tasks, "适老化场景档不该为空"
    for t in tasks:
        tag = (f"{t.id} {t.title}").lower()
        assert ("a11y" in tag or "accessib" in tag or "无障碍" in t.title
                or "适老" in t.title or t.category == "accessibility"), \
            f"{t.id} 与无障碍无关，不该进适老化场景档"


# ── 5. 库层边界行为：静默返回空，不抛 ─────────────────────────────────────────
def test_unknown_profile_returns_empty_not_error():
    assert pf.tasks_in_profile("nope", PLATFORM, VERSION) == []
    assert pf.profile_summary("nope", PLATFORM, VERSION) == {}
    assert "未知档位" in pf.profile_detail("nope", PLATFORM, VERSION)
    assert pf.scenario_tasks("nope", PLATFORM, VERSION) == []


def test_profile_summary_shape():
    s = pf.profile_summary("minimal", PLATFORM, VERSION)
    assert s["name"] == "minimal"
    assert s["count"] == len(s["ids"]) > 0
    assert s["has_opt_in"] is False
    assert s["has_high_risk"] is False
    assert set(s["risk"]) >= {"low", "medium", "high"}
    # 分类计数之和必须等于任务数（防「分布与总数对不上」）
    assert sum(s["categories"].values()) == s["count"]


def test_compare_profiles_reports_subset_relation():
    r = pf.compare_profiles("minimal", "full", PLATFORM, VERSION)
    assert r["count_a"] < r["count_b"]
    assert r["only_a"] == [], "minimal 里的任务必须全部能在 full 里找到"
    assert len(r["only_b"]) == r["count_b"] - r["count_a"]
    assert 0.0 < r["jaccard"] < 1.0


def test_compare_rejects_unknown_profile_by_empty_result():
    """未知档位按空集处理：相似度算得出来，但两边规模为 0（不抛）。"""
    r = pf.compare_profiles("nope", "full", PLATFORM, VERSION)
    assert r["count_a"] == 0
    assert r["jaccard"] == 0.0


def test_new_tasks_are_inherited_by_profiles():
    """声明式档位的关键收益：任务库新增任务后，符合同档规则的自动入选。

    这里用「全库任务能被 full 档覆盖到绝大多数」间接验证：如果档位是硬编码
    id 列表，新增任务就会永远进不去。
    """
    all_tasks = registry.all_tasks()
    full_ids = {t.id for t in pf.tasks_in_profile("full", PLATFORM, VERSION)}
    missing = [t.id for t in all_tasks
               if t.platform in ("any", PLATFORM) and t.id not in full_ids]
    assert len(missing) / max(1, len(all_tasks)) < 0.35, \
        f"full 档漏掉过多任务（{len(missing)}/{len(all_tasks)}），疑似硬编码清单"


def test_profile_list_and_scenario_list_render():
    lines = pf.profile_list(PLATFORM, VERSION)
    assert any("minimal" in ln for ln in lines)
    sc = pf.scenario_list(PLATFORM)
    assert any("elderly-friendly" in ln for ln in sc)
