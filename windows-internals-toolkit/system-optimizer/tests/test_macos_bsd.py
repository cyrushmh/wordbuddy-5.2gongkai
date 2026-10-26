"""macOS / BSD 原生接口与文档层：跨平台安全 + 文档完整性 + CLI 可跑。

验证这两个「个体」平台模块：
- 在非目标平台（如 Linux 沙箱）下不崩、能安全降级；
- 文档参考（data/macos_docs.json / data/bsd_docs.json）结构完整；
- CLI 子命令 `sysweeper macos` / `sysweeper bsd` 能正常产出。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from sysweeper.native import macos as nm
from sysweeper.native import bsd as nb

REPO = Path(__file__).resolve().parents[1]
PY = str(REPO / "src" / "python")


def _env() -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = PY
    return env


def test_macos_doc_loaded():
    refs = nm.reference_all()
    assert isinstance(refs, dict) and refs, "macos_docs.json 应已加载且非空"


def test_bsd_doc_loaded():
    refs = nb.reference_all()
    assert isinstance(refs, dict) and refs, "bsd_docs.json 应已加载且非空"


def test_macos_reference_shape():
    for key, ref in nm.reference_all().items():
        assert "protocols" in ref and "interfaces" in ref, (
            f"macOS 接口 {key} 缺 protocols/interfaces")
        assert isinstance(ref["protocols"], list) and ref["protocols"]
        assert isinstance(ref["interfaces"], list) and ref["interfaces"]


def test_bsd_reference_shape():
    for key, ref in nb.reference_all().items():
        assert "protocols" in ref and "interfaces" in ref, (
            f"BSD 接口 {key} 缺 protocols/interfaces")
        assert isinstance(ref["protocols"], list) and ref["protocols"]
        assert isinstance(ref["interfaces"], list) and ref["interfaces"]


def test_macos_doc_list_nonempty():
    assert list(nm.macos_doc_list())


def test_bsd_doc_list_nonempty():
    assert list(nb.bsd_doc_list())


def test_macos_tune_list_nonempty():
    assert list(nm.macos_tune_list())


def test_bsd_tune_list_nonempty():
    assert list(nb.bsd_tune_list())


def test_cross_platform_safe():
    # 非 macOS / 非 BSD 环境：原生探测应安全返回（依平台而定），绝不抛异常
    nm.sysctl("hw.ncpu")
    nb.sysctl("hw.ncpu")
    # 文档层在无目标平台时仍可正常产出
    nm.macos_doc_list(); nm.macos_tune_list()
    nb.bsd_doc_list(); nb.bsd_tune_list()


def test_cli_macos_runs():
    r = subprocess.run([sys.executable, "-m", "sysweeper", "macos"],
                       cwd=REPO, capture_output=True, text=True, env=_env())
    assert r.returncode == 0, r.stderr
    assert "macOS" in r.stdout


def test_cli_bsd_runs():
    r = subprocess.run([sys.executable, "-m", "sysweeper", "bsd"],
                       cwd=REPO, capture_output=True, text=True, env=_env())
    assert r.returncode == 0, r.stderr
    assert "BSD" in r.stdout
