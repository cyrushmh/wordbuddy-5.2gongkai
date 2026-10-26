"""概念系统中心测试（v0.6.66，CLI 子命令 `concepts`）。

覆盖注册表不变量：
  · 十一系统登记 —— plang/netsys/daoxue/quantum/comp/apilab/zhuangzi/baigong/
    datong/protec/sciences 全部在 REGISTRY，且 data/concepts/ 下都有对应数据
    文件、concepts/ 下有只读层模块；
  · 各系统 API 同构 —— info/domains/orstats 可用、search 可代问；
  · 概览与跨系统检索 —— overview() 十一条、search_all() 命中带 system 字段。
"""
from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "python"))

from sysweeper import concepts as C  # noqa: E402
from sysweeper import version as version  # noqa: E402

EXPECTED = ["plang", "netsys", "daoxue", "quantum", "comp", "apilab",
            "zhuangzi", "baigong", "datong", "protec", "sciences"]


def test_registry_eleven_systems():
    """十一个概念系统全部登记，且数据文件与只读层成对存在。"""
    assert C.systems() == EXPECTED
    data_dir = ROOT / "src" / "python" / "sysweeper" / "data" / "concepts"
    pkg_dir = ROOT / "src" / "python" / "sysweeper" / "concepts"
    for name in EXPECTED:
        assert (data_dir / f"{name}_taxonomy.json").exists(), f"{name} 缺数据文件"
        assert (pkg_dir / f"{name}.py").exists(), f"{name} 缺只读层"
        mod = C.module(name)
        assert mod is importlib.import_module(f"sysweeper.concepts.{name}")


def test_load_and_module():
    """load() 返回原始数据；module() 返回只读层；未登记名抛 KeyError。"""
    doc = C.load("quantum")
    assert doc["_meta"]["schema"].startswith("quantum_taxonomy")
    for name in EXPECTED:
        mod = C.module(name)
        info = mod.info()
        root = info.get("main_root") or info.get("system_root")
        assert root == "wordbuddy-github", f"{name} 主目录口径缺失：{root!r}"
        assert callable(mod.stats)
    for bad in ("nope", ""):
        try:
            C.module(bad)
        except KeyError:
            pass
        else:
            raise AssertionError(f"未登记系统应抛 KeyError: {bad!r}")


def test_overview_eleven_entries():
    """overview() 覆盖全部系统（tagline/version/title/stats）。"""
    ov = C.overview()
    assert [e["system"] for e in ov] == EXPECTED
    for e in ov:
        assert e["tagline"]
        assert version.is_valid(e["version"]), "概念系统版本需符合去中心化格式"
        assert e["title"]
        assert isinstance(e["stats"], dict) and e["stats"]


def test_fields_complete_across_axis_systems():
    """v0.6.62 字段齐备：六个轴型概念系统的每个概念必备
    gist（纲宗）/ detail（详述）/ engineering（工程落法）三件套。

    （plang 用 lang_index 六字段、netsys 用 modules、daoxue 用 principles，
    结构不同，由各自 build --check 覆盖，此处只管 concept 型的六个系统。）
    """
    for name in ("apilab", "baigong", "comp", "datong", "quantum", "zhuangzi"):
        doc = C.load(name)
        for c in doc.get("concepts", []):
            miss = [k for k in ("gist", "detail", "engineering") if not c.get(k)]
            assert not miss, f"{name}/{c['id']} 缺字段：{miss}"


def test_search_all_cross_system():
    """跨系统检索：命中带 system 字段，来源系统均已登记。"""
    hits = C.search_all("门")
    assert hits
    for h in hits:
        assert h["system"] in EXPECTED
    assert C.search_all("") == []


def test_axis_api_aliases_aligned():
    """v0.6.66 API 归一：五个带原则的系统（datong/zhuangzi/baigong/protec/sciences）
    必须同时提供 principles_of 与 principles_of_canon 两个名字（原名保留，向后兼容）。"""
    for name in ("datong", "zhuangzi", "baigong", "protec", "sciences"):
        mod = C.module(name)
        assert callable(getattr(mod, "principles_of", None)), f"{name} 缺 principles_of"
        assert callable(getattr(mod, "principles_of_canon", None)), f"{name} 缺 principles_of_canon"


def test_taglines_match_reality():
    """TAGLINES 的关键数字与各系统 stats 一致（防文案漂移）。"""
    ov = {e["system"]: e for e in C.overview()}
    assert "82" in C.TAGLINES["quantum"]
    assert ov["quantum"]["stats"]["concept_total"] == 82  # 0031 轮增 qudit/level-dissipation/log-value-exchange（78→81）/ 0032 轮增 qudit-register（81→82）
    # netsys tagline 的模块数须与 stats 一致（v0.6.82：61 模块 + 系统互联协调基底 sysmesh/sysfed，覆盖全 9 概念系统）
    assert f"{ov['netsys']['stats']['module_total']} 个模块" in C.TAGLINES["netsys"]
    assert ov["netsys"]["stats"]["module_total"] == 64
    assert ov["comp"]["stats"]["concept_total"] == 87  # 0028 轮 bitwidth 域增 simd-128（128 位 SIMD 向量档）
    assert ov["apilab"]["stats"]["concept_total"] == 36
    assert ov["comp"]["stats"]["lang_need_verified"] == 15
    assert ov["apilab"]["stats"]["bridge_count"] == 19  # v0.6.63 续 +3 条 / v0.6.64 续 +1 条（dbus-iface）/ v0.6.67 整体指导桥 +1 条
    # baigong tagline 的四偶/三教九流/七原则数字与 stats 一致
    assert ov["baigong"]["stats"]["concepts"] == 27
    assert ov["baigong"]["stats"]["bridges"] == 50   # v0.6.62 补 5 条 + v0.6.57+ datong 回边 1 条 + v0.6.67 整体指导桥 1 条
    assert ov["baigong"]["stats"]["principles"] == 7
    # datong tagline 的五轴规模与 stats 一致（15 传统 + 21 命题 + 6 六象 + 12 实践 = 63）
    assert "正道六象" in C.TAGLINES["datong"]
    assert ov["datong"]["stats"]["concepts"] == 63
    assert ov["datong"]["stats"]["bridges"] == 51
    assert ov["datong"]["stats"]["principles"] == 9
    assert ov["datong"]["stats"]["by_domain"] == {"traditions": 15, "theses": 21,
                                                 "six": 6, "practices": 12,
                                                 "ethics": 9}
    # datong 用户端面为第十一系统（concept_systems 与注册表一致）
    assert C.module("datong").user_face()["concept_systems"] == len(EXPECTED) == 11
    # apilab tagline 的 CLI 子命令数须与登记值一致
    n_cli = C.module("apilab").repo_facts()["cli_subcommands"]
    assert str(n_cli) in C.TAGLINES["apilab"]


def test_cli_smoke():
    """CLI `concepts` 冒烟：overview / search。"""
    def run(*a):
        return subprocess.run(
            [sys.executable, "-m", "sysweeper.cli", *a],
            capture_output=True, text=True, timeout=120, cwd=str(ROOT / "src" / "python"))
    r = run("concepts")
    assert r.returncode == 0, r.stderr
    for name in EXPECTED:
        assert name in r.stdout
    r = run("concepts", "search", "编译")
    assert r.returncode == 0


def test_audit_concepts_clean():
    """tools/audit_concepts.py --strict 必须零不一致（文件/字段/命名/API 四层体检）。

    这条是「全量概念整体检测」的守门员：日后新增概念、改名、加桥接，
    只要破坏了命名与字段的一致性，这里就会先失败。
    """
    import subprocess
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "audit_concepts.py"), "--strict"],
        capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "不一致项合计：0" in r.stdout
