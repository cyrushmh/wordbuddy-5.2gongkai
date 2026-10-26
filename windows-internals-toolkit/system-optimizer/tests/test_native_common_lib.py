"""兼容层库（native/common.py）固化与防误判冗余测试（v0.6.88）。

三道防线，直接针对历史上「振荡/还原事故」产生的幽灵副本问题（如 sysweeper 拼写
错误的三 e 副本 sysweerer）：

1. 身份契约：common.py 必须持有唯一的 ``__role__`` / ``__canonical__`` 标记，且其
   公开 API 契约（``__all__``）全部真实存在、可调用。
2. 实际被依赖：common.py 被大量 native 子系统 ``from . import common`` 引用——
   证明它是被依赖的共享库，而非无人使用的冗余文件（引用数低于阈值即告警）。
3. 冗余侦测：全 sysweeper 包（含 native/、tasks/、顶层模块、子包）内 ``__role__``
   不得重复（重复即幽灵副本）；且不得出现 ``common`` 的编辑距离 ≤1 形似副本
   （commonn / commons / commom ...）。扫描根从 native/ 扩到整个 sysweeper 包，
   以覆盖顶层与 tasks/ 下潜在的形似副本。

运行：python3 -m pytest tests/test_native_common_lib.py -q
"""

from __future__ import annotations

import os
import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.abspath(os.path.join(HERE, "..", "src", "python"))
if PKG_ROOT not in __import__("sys").path:
    __import__("sys").path.insert(0, PKG_ROOT)

from sysweeper.native import common as common  # noqa: E402
from sysweeper import version as version  # noqa: E402

NATIVE_DIR = os.path.join(PKG_ROOT, "sysweeper", "native")
PKG_SYSWEEPER = os.path.join(PKG_ROOT, "sysweeper")  # 整个包（扩展扫描根）


def _should_skip_dir(name: str) -> bool:
    """跳过测试目录与缓存，避免把测试桩或缓存纳入冗余侦测。"""
    return name in ("tests", "__pycache__", ".git")


# ── 防线 1：身份契约 ──
def test_common_is_canonical_compat_lib():
    """common.py 必须声明自己是唯一兼容层正典。"""
    assert common.__role__ == "shared_compat_lib", "兼容层角色标记缺失或改名"
    assert common.__canonical__ is True, "兼容层正典标记缺失"
    assert version.is_valid(common.__version__), "兼容层契约版本需符合去中心化格式"


def test_common_public_api_contract():
    """__all__ 列出的公开 API 必须全部存在且可调用（契约不可悬空）。"""
    api = common.__all__
    assert isinstance(api, (list, tuple)) and len(api) > 0, "__all__ 为空或缺失"
    for name in api:
        assert hasattr(common, name), f"__all__ 列了不存在的符号: {name}"
        assert callable(getattr(common, name)), f"__all__ 符号不可调用: {name}"


# ── 防线 2：实际被依赖（证明不是冗余无人用文件） ──
def test_common_is_actually_used():
    """common.py 必须被大量子系统实际引用，证明是被依赖的共享库。"""
    pattern = re.compile(r"^\s*(from \. import common|from \.native import common|import common)\b")
    count = 0
    for root, _dirs, files in os.walk(os.path.join(PKG_ROOT, "sysweeper")):
        if "tests" in root:
            continue
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(root, fn)
            try:
                with open(path, encoding="utf-8") as fh:
                    for line in fh:
                        if pattern.match(line):
                            count += 1
                            break
            except OSError:
                continue
    # 历史基线：本模块被 40+ 个 native 子系统引用；低于 30 即视为被误删引用或成为冗余。
    assert count >= 30, f"common.py 引用数异常偏低（{count}），疑似被误删引用或沦为冗余文件"


# ── 防线 3：冗余侦测 ──
def _levenshtein(a: str, b: str) -> int:
    """标准编辑距离（用于形似名侦测）。"""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    prev = list(range(lb + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1,
                           prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[lb]


def _package_module_names():
    """收集整个 sysweeper 包（含 native/、tasks/、顶层模块与子包）的模块名，
    跳过 __init__.py、tests/ 与 __pycache__。用于全包形似副本侦测。"""
    names = []
    for root, dirs, files in os.walk(PKG_SYSWEEPER):
        dirs[:] = [d for d in dirs if not _should_skip_dir(d)]
        for fn in files:
            if not fn.endswith(".py") or fn == "__init__.py":
                continue
            names.append(fn[:-3])
    return names


def test_no_duplicate_compat_role():
    """全 sysweeper 包内 __role__ 不得重复——重复即幽灵副本。"""
    seen = {}
    for root, dirs, files in os.walk(PKG_SYSWEEPER):
        dirs[:] = [d for d in dirs if not _should_skip_dir(d)]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(root, fn)
        try:
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
        except OSError:
            continue
        m = re.search(r"^__role__\s*=\s*[\"']([^\"']+)[\"']", src, re.M)
        if not m:
            continue
        role = m.group(1)
        assert role not in seen, (
            f"兼容层角色重复（幽灵副本）: role='{role}' 同时出现在 "
            f"{seen[role]}.py 与 {fn}——后者应删除"
        )
        seen[role] = fn[:-3]


def test_no_lookalike_compat_duplicate():
    """不得出现 common 的编辑距离 ≤1 形似副本（commonn/commons/commom ...）。

    扫描根已扩到整个 sysweeper 包，能捕获 native/ 之外的形似副本
    （如 tasks/common.py 或顶层 common.py）。
    """
    names = set(_package_module_names())
    assert "common" in names, "common.py 本体缺失"
    for n in names:
        if n == "common":
            continue
        # 私有模块（前导下划线）是刻意的内部 helper（如 concepts/_common.py），
        # 不属于「公开名幽灵副本」范畴，豁免形似检查。
        if n.startswith("_"):
            continue
        if _levenshtein(n, "common") <= 1:
            pytest.fail(
                f"发现 common 的形似副本 '{n}.py'（编辑距离≤1）——疑似幽灵/冗余文件，"
                f"应删除或重命名为语义不同的模块名"
            )


def test_no_lookalike_package_duplicate():
    """包层不得出现 sysweeper 的拼写错误形似副本（如三 e 的 sysweerer）。"""
    parent = os.path.dirname(os.path.dirname(NATIVE_DIR))  # src/python
    pkgs = [d for d in os.listdir(parent)
            if os.path.isdir(os.path.join(parent, d)) and d.startswith("sysweeper")]
    for p in pkgs:
        if p == "sysweeper":
            continue
        if _levenshtein(p, "sysweeper") <= 2:
            pytest.fail(
                f"发现 sysweeper 的拼写错误形似副本 '{p}'（编辑距离≤2）——历史幽灵副本，"
                f"应删除"
            )
