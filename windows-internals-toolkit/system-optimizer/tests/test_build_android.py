"""安卓 8 / 14 优先构建通道测试。

纪律：临时目录 + 只断言"两头卡住"这件事本身——
8 是下探底线、14 是现行主流，两端都能列出任务才叫覆盖住了。
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "python"))

import pytest  # noqa: E402


def _tool():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "build_android",
        Path(__file__).resolve().parents[1] / "tools" / "build_android.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_primary_targets_are_8_and_14():
    t = _tool()
    assert t.PRIMARY == {"8": 26, "14": 34}


def test_both_ends_have_tasks():
    """8 与 14 两端都得有任务——两头卡住，中间才不用逐个测。"""
    t = _tool()
    s8, s14 = t._applicable_stats("8"), t._applicable_stats("14")
    assert s8["count"] > 0 and s14["count"] > 0
    assert s8["api"] == 26 and s14["api"] == 34


def test_newer_version_has_equal_or_more_tasks():
    """新版本不会比老版本任务更少（能力单调增加，除非有版本上限项）。"""
    t = _tool()
    s8, s14 = t._applicable_stats("8"), t._applicable_stats("14")
    assert s14["count"] >= s8["count"]


def test_build_writes_config_without_commands(tmp_path, monkeypatch):
    """构建产物只存 id 与元信息，**不存任何命令**——与插件安全模型同口径。"""
    t = _tool()
    monkeypatch.setattr(t, "OUT", tmp_path)
    assert t.build_target("14") == 0
    f = tmp_path / "android-34.json"
    assert f.exists()
    data = json.loads(f.read_text(encoding="utf-8"))
    assert data["platform"] == "android" and data["api_level"] == 34
    assert isinstance(data["task_ids"], list) and data["task_ids"]
    blob = json.dumps(data, ensure_ascii=False)
    for bad in ("shell", "adb ", "rm -", "sudo", "&&"):
        assert bad not in blob, f"配置里不该出现命令片段 {bad}"


def test_other_target_runs_tests_not_build(tmp_path, monkeypatch):
    """其他平台只跑测试不构建——按你的要求，不假装构建了。"""
    t = _tool()
    monkeypatch.setattr(t, "OUT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["build_android.py", "--target", "linux"])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = t.main()
    out = buf.getvalue()
    assert rc == 0
    assert "跳过" in out and "非安卓目标" in out
    assert not list(tmp_path.glob("linux*.json"))   # 确实没生成任何构建产物


def test_matrix_reports_differences():
    t = _tool()
    s8, s14 = t._applicable_stats("8"), t._applicable_stats("14")
    only14 = set(s14["ids"]) - set(s8["ids"])
    # 14 上至少有一项是老版本没有的（新权限/新接口类），否则说明版本门控没生效
    assert len(only14) >= 1
