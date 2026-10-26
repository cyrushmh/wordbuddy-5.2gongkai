"""概念系统共享加载器（v0.6.59）。

所有概念系统的数据层统一落在 ``data/concepts/`` 目录：

    data/concepts/<系统>_taxonomy.json

构建脚本在 ``research/<系统>/build_*.py``（``--check`` 防漂移）。本模块是
这些数据文件的唯一只读入口：优先 ``importlib.resources``（随包分发），
源码树内直跑时回退到相对路径；结果经 ``lru_cache`` 缓存，全程不写盘。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

#: 数据子目录名（相对 ``sysweeper.data``）
CONCEPTS_DIR = "concepts"


@lru_cache(maxsize=None)
def load_taxonomy(filename: str) -> Dict[str, Any]:
    """按文件名加载概念系统数据（``data/concepts/<filename>``），带缓存。"""
    try:
        from importlib import resources

        data = resources.files("sysweeper.data").joinpath(
            CONCEPTS_DIR, filename).read_text(encoding="utf-8")
    except Exception:
        here = (Path(__file__).resolve().parent.parent / "data" / CONCEPTS_DIR
                / filename)
        data = here.read_text(encoding="utf-8")
    return json.loads(data)


def data_path(filename: str) -> Path:
    """返回源码树内数据文件的绝对路径（供构建/测试引用）。"""
    return (Path(__file__).resolve().parent.parent / "data" / CONCEPTS_DIR
            / filename)
