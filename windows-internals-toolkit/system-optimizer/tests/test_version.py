"""去中心化版本号体系测试（v0.6.88 重构引入，2026-10-23）。

覆盖：
  · 格式常量（CORE_RE / FULL_RE）与 ``is_valid`` / ``today_suffix`` /
    ``bump`` / ``strip_date`` 的里程表语义；
  · 整体包事实源 ``PACKAGE_VERSION`` / ``BASE_VERSION`` 合法；
  · 所有概念系统 ``_meta.version`` 合法；
  · 兼容层 ``common.__version__`` 与所有 ``Subsystem.version`` 合法（新格式）。
"""
from __future__ import annotations

import glob
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PKG_ROOT = os.path.join(ROOT, "src", "python")
if PKG_ROOT not in sys.path:
    sys.path.insert(0, PKG_ROOT)

from sysweeper import version as version  # noqa: E402
from sysweeper.native import common as common  # noqa: E402
from sysweeper.native.subsystems import SUBSYSTEMS  # noqa: E402

CONCEPTS_DIR = os.path.join(PKG_ROOT, "sysweeper", "data", "concepts")


# ── 1. 格式与工具函数（里程表语义）──
def test_core_full_regex():
    assert version.CORE_RE.match("0000.0000.0000.0000")
    assert not version.CORE_RE.match("0.0.0.0")
    assert not version.CORE_RE.match("0000.0000.0000.0000.20261023")
    assert version.FULL_RE.match("0000.0000.0000.0000")
    assert version.FULL_RE.match("9999.9999.9999.9999.99991231")
    # FULL_RE 只校验结构（日期 8 位），月/日合法性由 is_valid 负责
    assert version.FULL_RE.match("0000.0000.0000.0001.20261345")


def test_is_valid():
    assert version.is_valid(version.PACKAGE_VERSION)
    assert version.is_valid(version.BASE_VERSION)
    assert not version.is_valid("0.6.88")        # 旧三段式应判非法
    assert not version.is_valid("v0.6.64")       # 带前缀非法
    assert not version.is_valid("0000.0000.0000.0001.20261345")  # 非法日期
    assert not version.is_valid(12345)           # 非字符串一律 False


def test_today_suffix_format():
    s = version.today_suffix()
    assert len(s) == 8 and s.isdigit()


def test_bump_odometer_carry_and_cycle():
    # D 段进位 → C
    assert version.bump("0000.0000.0000.9999", date="") == "0000.0000.0001.0000"
    # 多段进位
    assert version.bump("0000.0000.9999.9999", date="") == "0000.0001.0000.0000"
    # 四段全满 → 循环归零
    assert version.bump("9999.9999.9999.9999", date="") == "0000.0000.0000.0000"


def test_bump_default_appends_date():
    out = version.bump("0000.0000.0000.0001")
    assert out.startswith("0000.0000.0000.0002.")
    assert out.endswith(version.today_suffix())


def test_bump_explicit_date_and_strip():
    assert version.bump("0000.0000.0000.0001", date="20260101") == "0000.0000.0000.0002.20260101"
    assert version.strip_date("0000.0000.0000.0001.20261023") == "0000.0000.0000.0001"


def test_to_pep440_mapping():
    # odometer → PEP 440：去前导零 + 日期作 local 段
    assert version.to_pep440("0000.0000.0000.0001.20261023") == "0.0.0.1+20261023"
    assert version.to_pep440("0000.0000.0000.0000") == "0.0.0.0"
    # 中段/前段非零也会正确去前导零
    assert version.to_pep440("0000.0000.0001.0002.20260101") == "0.0.1.2+20260101"
    # 非法版本应抛 ValueError
    import pytest
    with pytest.raises(ValueError):
        version.to_pep440("0.6.88")


# ── 2. 整体包事实源 ──
def test_package_version_is_fact_source():
    import sysweeper
    import tomllib
    with open(os.path.join(ROOT, "pyproject.toml"), "rb") as f:
        pv = tomllib.load(f)["project"]["version"]
    # 三处活版本（包 / pyproject / Go）必须等值，且符合新格式
    assert version.is_valid(sysweeper.__version__)
    assert sysweeper.__version__ == pv == version.PACKAGE_VERSION


# ── 3. 概念系统版本全合法 ──
def test_all_concept_versions_valid():
    files = sorted(glob.glob(os.path.join(CONCEPTS_DIR, "*_taxonomy.json")))
    assert files, "未找到任何概念 taxonomy 文件"
    for f in files:
        data = json.load(open(f, encoding="utf-8"))
        ver = data["_meta"]["version"]
        assert version.is_valid(ver), f"{os.path.basename(f)} 版本非法: {ver}"


# ── 4. 兼容层与子系统版本合法 ──
def test_common_contract_version_valid():
    assert version.is_valid(common.__version__)


def test_all_subsystem_versions_valid():
    assert SUBSYSTEMS, "子系统清单为空"
    for s in SUBSYSTEMS:
        assert version.is_valid(s.version), f"子系统 {s.key} 版本非法: {s.version}"
