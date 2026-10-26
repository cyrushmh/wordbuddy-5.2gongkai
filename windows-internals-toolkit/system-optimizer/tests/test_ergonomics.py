"""用户端人体工程学测试（v0.6.60，CLI 子命令 `guide` / GUI confirm_risky / ergonomics）。

南华三理念（逍遥游·无待一步 / 应帝王·顺性不抢 / 大宗师·意图宗师）的
可审计落法：
  · 入口地图双向完整 —— 全部子命令被场景组收录（无漏），地图无幻影命令（无错）；
  · 失败指路 —— next_hint 成功态给下一步、失败态给原因+回退路径；
  · 预测式默认 —— followup_hints 只给建议不强制；
  · GUI 破坏性确认三段式 —— 后果 + 回退指路（无显示环境保守拒绝）；
  · 原则摘要转发 concepts/zhuangzi 数据层（八条，不臆造）。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "python"))

from sysweeper import ergonomics as erg  # noqa: E402
from sysweeper import gui  # noqa: E402


def test_entry_map_two_way_complete():
    """入口地图双向校验：无漏分组、无幻影命令（与 argparse 实测对齐）。"""
    st = erg.stats()
    assert st["cli_subcommands"] >= 104
    assert st["ungrouped"] == [], f"漏分组子命令：{st['ungrouped']}"
    assert st["phantom"] == [], f"幻影命令：{st['phantom']}"
    assert st["scenes"] == 12


def test_entry_map_expressions_valid():
    """带参表达式（scan --report x.json 等）首词必须是真实子命令。"""
    from sysweeper import cli
    parser = cli.build_parser()
    choices = [a for a in parser._actions
               if a.__class__.__name__ == "_SubParsersAction"][0].choices
    for c in erg.grouped_commands():
        assert c.split()[0] in choices, f"入口地图首词不存在：{c}"


def test_next_hint_success_and_failure():
    """成功给下一步；失败给原因 + 回退路径（大宗师：失败指路可回退）。"""
    ok = erg.next_hint("scan", ok=True, note="探测完成")
    assert "下一步可试" in ok and "guide" in ok
    bad = erg.next_hint("scan", ok=False, note="探测超时",
                        rollback="snapshot capture 可留痕")
    assert "未完成" in bad and "探测超时" in bad and "回退/恢复" in bad
    # 失败提示必带回退路径（养生主：不伤）
    assert "回退" in bad
    # 单独失败无 rollback 时不静默：仍给格式完整的一行
    bad2 = erg.next_hint("scan", ok=False)
    assert "未完成" in bad2 and bad2.endswith("。")


def test_followups_are_suggestions():
    """预测式默认只给建议，未知命令返回空列表（不强制、不编造）。"""
    assert erg.followup_hints("scan") == ["scan --report x.json", "snapshot capture", "guide"]
    assert erg.followup_hints("不存在的命令") == []
    assert isinstance(erg.followup_hints("gui"), list)


def test_rollback_note_points_to_snapshot():
    """回退统一指向快照机制（养生主：先留痕后动手）。"""
    assert "snapshot" in erg.ROLLBACK_NOTE


def test_principles_brief_relays_zhuangzi():
    """八原则摘要转发 concepts/zhuangzi 数据层（不另造一套）。"""
    ps = erg.principles_brief()
    assert len(ps) == 8
    assert ps[0]["name"] == "无待一步"
    assert ps[0]["canon"] == "逍遥游"
    assert ps[0]["engineering"]


def test_gui_confirm_risky_three_parts(monkeypatch):
    """GUI 确认三段式：后果 + 回退指路；无显示环境保守拒绝（不确认即不执行）。"""
    seen = {}

    class FakeBox:
        def askyesno(self, title, msg, parent=None):
            seen["title"] = title
            seen["msg"] = msg
            seen["parent"] = parent
            return True

    def fake_tk():
        return None, None, FakeBox(), None

    monkeypatch.setattr(gui, "_tk", fake_tk)
    assert gui.confirm_risky(None, "恢复默认", "覆盖当前设置", "可导出备份") is True
    assert "后果" in seen["msg"] and "覆盖当前设置" in seen["msg"]
    assert "回退" in seen["msg"] and "可导出备份" in seen["msg"]
    assert seen["title"] == "请确认：恢复默认"
    # 无回退说明时明示不可逆
    seen.clear()
    assert gui.confirm_risky(None, "清空留痕", "删除历史") is True
    assert "不可逆" in seen["msg"]

    def boom_tk():
        raise RuntimeError("no tkinter / no display")

    monkeypatch.setattr(gui, "_tk", boom_tk)
    assert gui.confirm_risky(None, "恢复默认", "x", "y") is False


def test_cli_guide_smoke():
    """CLI guide 子命令冒烟：一屏入口地图 + --principles 八原则。"""
    env = {"PYTHONPATH": str(ROOT / "src" / "python"), "PATH": "/usr/bin:/bin"}
    r = subprocess.run([sys.executable, "-m", "sysweeper", "guide"],
                       capture_output=True, text=True, timeout=120, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "入口地图" in r.stdout and "巡检与诊断" in r.stdout
    r2 = subprocess.run([sys.executable, "-m", "sysweeper", "guide", "--principles"],
                        capture_output=True, text=True, timeout=120, env=env)
    assert r2.returncode == 0
    assert "无待一步" in r2.stdout and "德充于内" in r2.stdout
    assert "南华真经" in r2.stdout
