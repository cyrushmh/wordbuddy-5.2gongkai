"""浏览器与引擎检测测试（v0.6.15）。全只读，monkeypatch 喂假 which/--version。"""
import sys

import pytest

sys.path.insert(0, "src/python")
from sysweeper.native import browser


def test_browser_report_returns_tuple():
    ok, msg = browser.browser_report()
    assert isinstance(ok, bool) and isinstance(msg, str) and msg


def test_browser_compat_notes_present():
    _, msg = browser.browser_report()
    assert "WebGPU" in msg and "mdn/browser-compat-data" in msg


def test_browser_capabilities_markers():
    ok, msg = browser.capabilities_report()
    assert "能力自检" in msg and "Blink" in msg and "Gecko" in msg


def test_browsers_helper(monkeypatch):
    """喂假 which + 假 --version，验证 Blink/Gecko 识别。"""
    def fake_which(name):
        return "/usr/bin/" + name if name in ("chromium", "firefox") else None
    monkeypatch.setattr(browser.shutil, "which", fake_which)
    monkeypatch.setattr(browser.common, "run",
                        lambda cmd, timeout=8: (0, "Chromium 144.0.7559.132\n")
                        if "chromium" in cmd else (0, "Mozilla Firefox 130.0\n"))
    found = browser._browsers()
    names = {n for n, _, _ in found}
    assert "chromium" in names and "firefox" in names
    eng = {n: e for n, e, _ in found}
    assert eng["chromium"] == "Blink" and eng["firefox"] == "Gecko"


def test_compat_notes_static_subset():
    assert isinstance(browser._COMPAT_NOTES, dict) and len(browser._COMPAT_NOTES) >= 3
