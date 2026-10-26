"""zipapp（.pyz）单文件分发时的包内资源兼容层。

背景
----
本项目的知识库是包内 JSON（`sysweeper/data/*.json`），代码统一用
`importlib.resources.files("sysweeper.data").joinpath(..).read_text()` 读取。
打成 .pyz（zipapp）之后包不再落在文件系统上，此时：

* Python 3.11+ 的 zipimport 自带 ResourceReader，`files()` 直接可用；
* Python 3.9 / 3.10 的 zipimport 没有，调用会抛异常 —— 而各 `_load_refs()`
  都有 `except Exception: return {}`，于是表现为「不崩，但知识库全空」。

本模块在检测到「zip 加载 + 缺原生支持」时补一个 `zipfile.Path` 版 shim，
让 .pyz 里的知识库同样读得到。只在 .pyz 中生效，正常安装路径零影响。

安全底线：只做读取，不改任何系统/用户设置。
"""

from __future__ import annotations

import os
import sys

_MARK = "_sysweeper_zip_shim"
# 设为 1 可强制启用 shim（3.11+ 原生可用时也走 shim），用于 CI / 自测验证该路径。
FORCE_ENV = "SYSWEEPER_ZIPRES_SHIM"
_installed = False


def _native_zip_resources() -> bool:
    """当前解释器是否自带 zip 内资源读取能力（3.11+ 的 zipimport）。"""
    if sys.version_info < (3, 11):
        return False
    loader = globals().get("__loader__")
    getter = getattr(loader, "get_resource_reader", None)
    if getter is None:
        return False
    try:
        return getter("sysweeper.data") is not None
    except Exception:
        return False


def install() -> bool:
    """必要时安装 shim。返回是否真的安装了（False = 走原生/非 zip 场景）。"""
    global _installed
    if _installed:
        return False
    _installed = True

    try:
        import zipimport
    except ImportError:  # pragma: no cover - 极老的构建
        return False

    loader = globals().get("__loader__")
    if not isinstance(loader, zipimport.zipimporter):
        return False  # 普通文件系统加载，无需 shim
    archive = getattr(loader, "archive", None)
    if not archive:
        return False
    if _native_zip_resources() and os.environ.get(FORCE_ENV) != "1":
        return False  # 解释器原生支持，不必打补丁

    try:
        from importlib import resources
    except ImportError:  # pragma: no cover
        return False
    if not hasattr(resources, "files") or getattr(resources, _MARK, False):
        return False

    import zipfile

    try:
        root = zipfile.Path(zipfile.ZipFile(archive))
    except Exception:
        return False

    original = resources.files

    def files(package, *args, **kwargs):
        name = package if isinstance(package, str) else getattr(package, "__name__", "")
        if name:
            try:
                target = root.joinpath(*name.split("."))
                if target.exists():
                    return target
            except Exception:
                pass
        return original(package, *args, **kwargs)

    files.__doc__ = "zipapp 兼容版 importlib.resources.files（sysweeper shim）"
    resources.files = files  # type: ignore[assignment]
    setattr(resources, _MARK, True)
    return True
