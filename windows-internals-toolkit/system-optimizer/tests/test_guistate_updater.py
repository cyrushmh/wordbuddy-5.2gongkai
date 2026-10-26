"""图形界面的「状态持久化」与「更新检查」测试（guistate.py + updater.py）。

纪律（与 test_compress.py 一致）：
- **绝不污染真实家目录**：所有落盘都重定向到 tmp_path（XDG_CONFIG_HOME）。
- **不依赖图形环境**：本文件只测状态层与更新层，不创建 tkinter 窗口。
- **更新只检查不动手**：断言 updater 只产出命令文本，绝不执行 git 写操作。
"""

from __future__ import annotations

import json
import os

import pytest

from sysweeper import guistate
from sysweeper import updater


@pytest.fixture(autouse=True)
def _isolate_config(tmp_path, monkeypatch):
    """把配置目录重定向到临时目录，并清掉内存态降级容器。"""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    guistate._MEMORY = None
    yield
    guistate._MEMORY = None


# ---------------- guistate：持久化 ----------------

def test_default_state_is_conservative():
    """默认档位保守：只列低风险、不纳入默认关闭的网络开关、跟随系统。"""
    st = guistate.load()
    assert st["max_risk"] == "low"
    assert st["opt_in"] is False
    assert st["follow_system"] is True
    assert st["disabled_tasks"] == []
    assert st["disabled_plugins"] == []


def test_save_load_roundtrip(tmp_path):
    """存了再读应该一模一样（界面关掉再打开，勾选项还在）。"""
    st = guistate.load()
    st = guistate.set_task_enabled(st, "fs_lvm_report", False)
    st = guistate.set_plugin_enabled(st, "openwrt", False)
    st["max_risk"] = "medium"
    st["follow_system"] = False
    assert guistate.save(st) is True

    again = guistate.load()
    assert again["max_risk"] == "medium"
    assert again["follow_system"] is False
    assert guistate.is_task_enabled(again, "fs_lvm_report") is False
    assert guistate.is_plugin_enabled(again, "openwrt") is False
    # 没动过的保持默认启用
    assert guistate.is_task_enabled(again, "fs_ext4_report") is True


def test_toggle_is_idempotent():
    """重复开关不产生重复记录（列表里不该出现同一个 id 两次）。"""
    st = guistate.load()
    for _ in range(3):
        st = guistate.set_task_enabled(st, "abc", False)
    assert st["disabled_tasks"].count("abc") == 1
    for _ in range(3):
        st = guistate.set_task_enabled(st, "abc", True)
    assert st["disabled_tasks"] == []


def test_corrupted_config_falls_back_to_default(tmp_path):
    """配置写坏了不许拖垮界面：回退默认值。"""
    p = guistate.path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{ 这不是 json", encoding="utf-8")
    st = guistate.load()
    assert st == guistate.DEFAULT


def test_unknown_schema_falls_back(tmp_path):
    """不认识的 schema 版本整体回退，不做半吊子迁移。"""
    p = guistate.path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"schema": 9999, "max_risk": "high"}),
                 encoding="utf-8")
    st = guistate.load()
    assert st["max_risk"] == guistate.DEFAULT["max_risk"]


def test_bad_list_field_is_coerced(tmp_path):
    """手工把列表改成字符串时，收敛回空列表而不是让界面炸掉。"""
    p = guistate.path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"schema": guistate.SCHEMA,
                             "disabled_tasks": "oops"}), encoding="utf-8")
    st = guistate.load()
    assert st["disabled_tasks"] == []


def test_unknown_keys_are_dropped(tmp_path):
    """只认识白名单里的键；未知键不落库（防旧版本脏数据污染）。"""
    st = guistate.load()
    st["__evil__"] = "rm -rf /"
    guistate.save(st)
    raw = json.loads(guistate.path().read_text(encoding="utf-8"))
    assert "__evil__" not in raw
    assert "schema" in raw


def test_reset_clears_state(tmp_path):
    """恢复默认后，之前关掉的东西重新启用。"""
    st = guistate.set_task_enabled(guistate.load(), "abc", False)
    guistate.save(st)
    assert guistate.is_task_enabled(guistate.load(), "abc") is False
    back = guistate.reset()
    assert back["disabled_tasks"] == []
    assert guistate.is_task_enabled(guistate.load(), "abc") is True


def test_summary_reports_counts():
    """摘要行要能反映关了几项（界面底部状态栏用）。"""
    st = guistate.load()
    st = guistate.set_task_enabled(st, "t1", False)
    st = guistate.set_task_enabled(st, "t2", False)
    st = guistate.set_plugin_enabled(st, "p1", False)
    s = guistate.summary(st)
    assert "已关闭任务 2 项" in s
    assert "停用插件 1 个" in s
    assert "跟随系统 开" in s


# ---------------- updater：只读 ----------------

def test_update_commands_are_text_only():
    """只给命令文本，绝不执行——这是「不自动改用户代码」的硬边界。"""
    cmds = updater.update_commands()
    assert isinstance(cmds, list) and cmds
    assert all(isinstance(c, str) for c in cmds)
    joined = "\n".join(cmds)
    # 必须包含真正的更新动作，且必须是给人看的命令而不是已经跑完的结果
    assert ("git pull" in joined) or ("pip install --upgrade" in joined)


def test_check_returns_full_shape_and_never_raises():
    """体检结果字段齐全；任何一步失败都记进 notes 而不是抛异常。"""
    r = updater.check()
    for k in ("version", "in_git_repo", "repo", "branch", "dirty", "behind",
              "ahead", "remote_reachable", "plugin_dir", "plugins_found",
              "tasks_total", "notes"):
        assert k in r, f"缺少字段 {k}"
    assert isinstance(r["notes"], list)
    assert isinstance(r["version"], str) and r["version"]
    assert isinstance(r["tasks_total"], int)


def test_check_does_not_modify_worktree():
    """check() 是只读的：跑完之后仓库状态不应发生变化。"""
    before = updater._run_git(["status", "--porcelain"],
                              updater._git_repo_root() or ".")
    r = updater.check()
    after = updater._run_git(["status", "--porcelain"],
                             updater._git_repo_root() or ".")
    assert before == after, "check() 改动了工作树，违反只读纪律"
    assert isinstance(r, dict)


def test_refresh_is_local_and_reports_tasks():
    """本地刷新：重数任务与插件，不改代码也不拉代码。"""
    res = updater.refresh()
    assert res["ok"] is True
    assert res["tasks"] > 0
    assert isinstance(res["plugins"], int)


def test_render_check_is_displayable():
    """渲染出的中文文本可直接显示，且带「本界面不会自动改你的代码」的边界说明。"""
    text = updater.render_check()
    assert isinstance(text, str) and text.strip()
    assert "当前版本" in text
    assert "不会自动改你的代码" in text


def test_current_version_matches_package():
    from sysweeper import __version__
    assert updater.current_version() == __version__
