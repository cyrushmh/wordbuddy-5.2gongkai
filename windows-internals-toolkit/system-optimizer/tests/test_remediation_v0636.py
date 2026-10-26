"""v0.6.36 闭环测试：缺口分类（设计如此 / 真缺口）+ 按需脚手架（gen-stub）。

守住三条：
1. 元能力/机制项（subsystems/linkage/omni/settings/importio/snapshot/distjob）
   必须被标成「设计如此」，不能算半截能力。
2. `omni gen-stub KEY` 默认 dry-run 不落盘；--write 才创建；已存在则跳过不覆盖。
3. 真缺口的 data 项能生成占位 JSON；未知 key / 完整项 / 设计如此项都安全拒做。
"""

import os

import pytest

from sysweeper.native import omni


BY_DESIGN = {"subsystems", "linkage", "omni", "settings", "importio", "snapshot", "distjob",
              # 运行期数据/机制类：data 是运行期生成（peer/offer/审计/资讯聚合/插件白名单），
              # 不是包内静态知识库，故「缺 data」属设计如此
              "webnews", "plugins", "plugins_allowlist",
              "distcompute", "reshare", "meshchat"}


def test_by_design_classified():
    plan = {p["key"]: p for p in omni.remediation_plan()}
    for k in BY_DESIGN:
        assert plan[k]["by_design"] is True, f"{k} 应标为设计如此"
        assert "设计如此" in plan[k]["action"]


def test_data_alias_resolves_semantic_names():
    # v0.6.37 修正：netlink/thirdparty 的 data 文件按语义命名
    # （link_protocols.json / net_interop_refs.json），接线盘点须正确判成「有 data」
    for k in ("netlink", "thirdparty"):
        row = next(r for r in omni.wiring() if r["key"] == k)
        assert row["wiring"]["data"] is True, f"{k} 应借 DATA_FILE_ALIASES 判成有 data"
    # harmony 三子项共用 harmony_docs.json，也应判成有 data（不再漏报）
    for k in ("kaihong", "harmony_hdc", "harmony_device"):
        row = next(r for r in omni.wiring() if r["key"] == k)
        assert row["wiring"]["data"] is True, f"{k} 应借别名判成有 data"


def test_real_gaps_are_diagnostic_only():
    # 真缺口不应再混入运行期数据/机制类（webnews/plugins/distcompute/reshare/meshchat）
    real = {p["key"]: p for p in omni.real_gaps()}
    for k in ("webnews", "plugins", "plugins_allowlist", "distcompute", "reshare", "meshchat"):
        assert k not in real, f"{k} 是设计如此，不应出现在真缺口"
    # 真缺口只剩需补 task 的诊断能力（netlink/netauth/jdk/kernel/kmod/firmware/modules）
    # 以及本应带知识库的诊断维度——这里只断言「真实缺口都是非 by-design」
    assert all(not p["by_design"] for p in omni.real_gaps())


def test_real_gaps_excludes_by_design():
    real = {p["key"]: p for p in omni.real_gaps()}
    for k in BY_DESIGN:
        assert k not in real, f"{k} 不该出现在真缺口里"


def test_fonts_now_fully_wired():
    # v0.6.36 修掉了 omni 自检暴露的那 1 个真 GUI 缺口
    row = next(r for r in omni.wiring() if r["key"] == "fonts")
    assert all(row["wiring"].values()), "fonts 四处入口应已接全"
    # fonts 不应再出现在任何缺口清单
    assert "fonts" not in {p["key"] for p in omni.remediation_plan()}


def test_gen_stub_unknown_key():
    ok, msg = omni.gen_stub("__no_such_key__")
    assert ok is False
    assert "未知子系统" in msg


def test_gen_stub_complete_item_rejected():
    # fonts 已齐全（含 data），不应生成占位
    ok, msg = omni.gen_stub("fonts")
    assert ok is False
    assert "未缺 data" in msg or "设计如此" in msg


def test_gen_stub_by_design_rejected():
    ok, msg = omni.gen_stub("subsystems")
    assert ok is False
    assert "设计如此" in msg


def _with_osi_absent(fn):
    """临时把已生成的 osi.json 移开，跑完再复原（不破坏已交付的占位）。"""
    target = omni._pkg_dir() / "data" / "osi.json"
    backed = target.exists()
    tmp = target.with_name("__osi_test_bak__.json")
    if backed:
        target.replace(tmp)
    try:
        return fn(target)
    finally:
        if backed and tmp.exists():
            tmp.replace(target)


def test_gen_stub_dry_run_no_write():
    # data 层补全后，osi 已是真实占位；临时移开以验证 dry-run 不落盘
    def run(target):
        ok, msg = omni.gen_stub("osi", write=False)
        assert ok is True
        assert "dry-run" in msg
        assert not target.exists(), "dry-run 绝不能创建文件"
    _with_osi_absent(run)


def test_gen_stub_write_then_idempotent():
    def run(target):
        ok, msg = omni.gen_stub("osi", write=True)
        assert ok is True
        assert target.exists(), "write=True 应创建文件"
        content = target.read_text(encoding="utf-8")
        # 第二次调用：文件已存在，应安全拒做（不覆盖、不动已有文件）
        ok2, msg2 = omni.gen_stub("osi", write=True)
        assert ok2 is False
        assert target.read_text(encoding="utf-8") == content, "已存在文件绝不可被改写"
    _with_osi_absent(run)


def test_cli_gaps_and_genstub_modes():
    from sysweeper import cli

    class _A:
        action = "gaps"
        extra = []
        deep = False
        write = False

    # gaps 模式应正常产出补齐清单文本（不报错即可）
    cli.cmd_omni(_A())

    class _B:
        action = "gen-stub"
        extra = ["osi"]
        deep = False
        write = False

    # gen-stub 模式：osi 若存在则临时移开，验证 dry-run 不落盘
    def run(target):
        cli.cmd_omni(_B())  # dry-run，不落盘
        assert not target.exists(), "dry-run 绝不能创建文件"
    _with_osi_absent(run)
