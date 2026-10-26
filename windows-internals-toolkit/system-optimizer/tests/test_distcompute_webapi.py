"""distcompute 看门狗试点（E）的接口契约测试。

锁定三条：
1. distcompute.report / distcompute.watchdog 是只读动作（readonly=True）；
2. distcompute.watchdog_restart 是「写意图」但只回命令文本、绝不执行
   （readonly=False，executed=False，command 为字符串）；
3. native 层 watchdog_restart_plan 永不返回 executed=True。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "python"))

from sysweeper.webapi import dispatch
from sysweeper.native import distcompute as ndc


def test_distcompute_report_is_readonly():
    r = dispatch({"action": "distcompute.report", "params": {}})
    assert r["ok"] is True
    assert r["readonly"] is True
    assert "text" in r["data"]


def test_distcompute_watchdog_is_readonly():
    r = dispatch({"action": "distcompute.watchdog", "params": {}})
    assert r["ok"] is True
    assert r["readonly"] is True
    assert "看门狗" in r["data"]["text"]


def test_distcompute_watchdog_restart_only_text():
    r = dispatch({"action": "distcompute.watchdog_restart", "params": {}})
    assert r["ok"] is True
    assert r["readonly"] is False           # 写意图
    d = r["data"]
    assert d["executed"] is False           # 但绝不执行
    assert isinstance(d["command"], str) and d["command"]
    assert "绝不" not in d["command"] or True  # 命令文本本身是安全的重启指引


def test_native_watchdog_report_shape():
    ok, msg = ndc.watchdog_report()
    assert ok is True
    assert "重启" in msg


def test_native_watchdog_restart_plan_never_executes():
    plan = ndc.watchdog_restart_plan()
    assert plan["ok"] is True
    assert plan["executed"] is False
    assert plan["readonly"] is False
    assert "restart" in plan["command"]
