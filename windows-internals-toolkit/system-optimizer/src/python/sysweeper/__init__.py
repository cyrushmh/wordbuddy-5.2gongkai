"""sysweeper —— 万能系统优化与清理。

纯 Python 标准库实现，目标是在 Windows / macOS / Linux / Android / iOS 上
提供「按系统+版本」匹配的优化、清理、隐私与维护建议与（桌面端）实际执行。

语言底层：Python 3.8+（多数 Linux / macOS / BSD 发行版默认自带，Windows
一条命令即可装）。整个包零第三方依赖，可打成单文件 .pyz 直接跑，见
仓库根 `tools/syspkg.py`。
"""

# 注意：zip 资源 shim 必须在导入任何子模块之前安装 —— 子模块在导入期就会
# 读取包内 JSON 知识库（形如 `REFS = _load_refs()`）。
from ._zipres import install as _install_zip_resources  # noqa: F401

_install_zip_resources()

from .version import PACKAGE_VERSION as __version__  # noqa: E402

from . import registry  # noqa: F401,E402

__all__ = ["__version__", "registry"]
