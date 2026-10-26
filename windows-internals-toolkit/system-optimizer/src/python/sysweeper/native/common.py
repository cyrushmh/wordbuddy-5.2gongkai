"""跨平台共享兼容层（单一事实源 / single source of truth）。

本模块是 sysweeper **唯一的**跨子系统共享工具库（兼容层）：为各 native 子系统
（windows / linux / macos / bsd / unix / android / ios / ...）提供共同的、与特定 OS
无关的只读辅助——命令执行、字节格式化、磁盘用量、缓存/临时/大目录盘点、DNS 缓存
指引、多系统无障碍探测。

⚠️ 防误判冗余（重要）：本模块**就是**兼容层，不是任何文件的副本或冗余。请勿另建
`common.py` 的同名/形似副本（commonn / commons / commom / commpn ...）——若需扩展，
请在本文件内新增函数并更新 ``__all__``，或新建**语义不同**的模块。
``__role__ = "shared_compat_lib"`` 是机器可读的唯一性标记（见
``tests/test_native_common_lib.py`` 的冗余侦测），同名角色出现两次即视为幽灵副本。

公开 API（契约见 ``__all__``）：
- 命令执行 : ``run``
- 字节格式化 : ``human``
- 磁盘/体积 : ``disk_usage`` / ``free_space`` / ``list_dir_size`` / ``find_large_subdirs``
- 只读盘点 : ``user_cache_report`` / ``temp_report`` / ``large_dirs_report`` / ``dns_flush_hint``
- 多系统无障碍 : ``a11y_report`` / ``a11y_atspi_bus`` / ``a11y_orca_status`` /
  ``a11y_multi_report`` / ``a11y_docs_report``

设计：纯标准库、零第三方依赖；所有函数失败不抛（返回 ``(False/None, 说明)``），
让上层决定降级；绝不修改系统（不安装 / 不删除 / 不写系统目录）。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import List, Optional, Tuple

from . import settings as _settings

# ---- 库身份标记：机器可读的唯一性契约（冗余侦测依赖此）----
__role__ = "shared_compat_lib"   # 全 native 包内唯一；重复即幽灵副本
__canonical__ = True             # 本模块是兼容层正典，非冗余
__version__ = "0000.0000.0000.0088.20261023"  # 兼容层独立契约版本（去中心化：不再与包版本同步）

__all__ = [
    # 命令执行
    "run",
    # 字节格式化
    "human",
    # 磁盘/体积
    "disk_usage", "free_space", "list_dir_size", "find_large_subdirs",
    # 只读盘点
    "user_cache_report", "temp_report", "large_dirs_report", "dns_flush_hint",
    # 多系统无障碍
    "a11y_report", "a11y_atspi_bus", "a11y_orca_status",
    "a11y_multi_report", "a11y_docs_report",
]


def _setting_int(key: str, fallback: int) -> int:
    """取一个数值阈值；配置缺失/损坏时回退 fallback（绝不因配置问题阻断诊断）。"""
    try:
        return int(_settings.get(key, fallback))
    except (TypeError, ValueError):
        return fallback


def _setting_str(key: str, fallback: str) -> str:
    try:
        v = _settings.get(key, fallback)
        return fallback if v is None else str(v)
    except (TypeError, ValueError):
        return fallback


def run(cmd, timeout: int = None, tail: int = None) -> Tuple[int, str]:
    """跑一条命令，返回 (returncode, 合并输出)。失败也返回，不抛。

    timeout: 最长等待秒数。**不传时取可调阈值 ``cmd.timeout``**（GUI/CLI 可改，默认 120）。
    tail:    只保留输出末尾多少字符（默认取阈值 ``cmd.tail``，默认 2000，防止超长输出
             灌爆上下文/报告）。需要解析完整输出的场景（如
             `java -XX:+PrintFlagsFinal` 有数百行标志）传 tail=0 表示不截断。
    显式传参始终优先于配置值（向后兼容既有调用）。
    """
    if timeout is None:
        timeout = _setting_int("cmd.timeout", 120)
    if tail is None:
        tail = _setting_int("cmd.tail", 2000)
    try:
        r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True,
                           text=True, timeout=timeout)
        out = (r.stdout + r.stderr).strip()
        if tail and tail > 0:
            out = out[-tail:]
        return r.returncode, out
    except Exception as e:  # noqa: BLE001
        return -1, f"执行失败: {e}"


def human(n: int) -> str:
    """把字节数转人类可读字符串。"""
    n = int(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def disk_usage(path: str = ".") -> Optional[dict]:
    """返回 {total, used, free}（字节），拿不到返回 None。"""
    try:
        s = shutil.disk_usage(path)
        return {"total": s.total, "used": s.used, "free": s.free}
    except Exception:
        return None


def free_space(path: str = ".") -> Optional[int]:
    u = disk_usage(path)
    return u["free"] if u else None


def list_dir_size(path: str) -> Optional[int]:
    """递归统计目录字节数（只读，不修改）。失败返回 None。"""
    if not path or not os.path.isdir(path):
        return None
    try:
        total = 0
        for root, _dirs, files in os.walk(path):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
        return total
    except Exception:
        return None


def find_large_subdirs(root: str, top: int = None) -> List[Tuple[str, int]]:
    """列出 root 下体积最大的若干子目录 (path, bytes)。

    top 不传时取可调阈值 ``scan.limit``（默认 10；GUI/CLI 可改）。
    """
    if top is None:
        top = _setting_int("scan.limit", 10)
    out: List[Tuple[str, int]] = []
    try:
        for name in os.listdir(root):
            p = os.path.join(root, name)
            if os.path.isdir(p):
                sz = list_dir_size(p)
                if sz:
                    out.append((p, sz))
    except Exception:
        pass
    out.sort(key=lambda x: x[1], reverse=True)
    return out[:top]


def user_cache_report() -> Tuple[bool, str]:
    """汇总当前用户可清理的缓存目录（跨平台：POSIX ~/.cache + Windows LocalAppData）。

    返回 (ok, msg)。仅列举体积、不删除，符合「默认只分析不乱删」。
    """
    dirs: List[str] = []
    if os.name == "nt":
        la = os.environ.get("LOCALAPPDATA")
        if la:
            dirs.append(la)
    else:
        c = os.path.join(os.path.expanduser("~"), ".cache")
        if os.path.isdir(c):
            dirs.append(c)
    if not dirs:
        return True, "未发现标准用户缓存目录（无 ~/.cache 或 LOCALAPPDATA）"
    parts = []
    for d in dirs:
        sz = list_dir_size(d)
        parts.append(f"{d}（{human(sz) if sz else '无法读取'}）")
    return True, "用户缓存目录: " + "; ".join(parts) + "（analyze 仅列出，清理请用对应平台任务）"


def temp_report() -> Tuple[bool, str]:
    """汇总系统/用户临时目录体积（跨平台），仅列举不删除。"""
    paths: List[str] = []
    if os.name == "nt":
        t = os.environ.get("TEMP") or os.environ.get("TMP")
        if t:
            paths.append(t)
    else:
        paths.append("/tmp")
    parts = []
    for p in paths:
        if os.path.isdir(p):
            parts.append(f"{p}（{human(list_dir_size(p) or 0)}）")
    if not parts:
        return True, "未发现标准临时目录"
    return True, "临时目录: " + "; ".join(parts) + "（analyze 仅列出，清理请用对应平台任务）"


def large_dirs_report(top: str = None, limit: int = None) -> Tuple[bool, str]:
    """列出某根目录下体积最大的子目录（analyze 只读、辅助定位可瘦身项）。

    top   不传时取运行参数 ``scan.root``（默认 ~，即家目录）；支持 ~ 展开。
    limit 不传时取可调阈值 ``scan.limit``（默认 10）。两者 GUI/CLI 均可改。
    """
    root = top or _setting_str("scan.root", "~")
    root = os.path.expanduser(root) if root.startswith("~") else root
    if limit is None:
        limit = _setting_int("scan.limit", 10)
    if not os.path.isdir(root):
        return True, f"目录不存在: {root}"
    rows = find_large_subdirs(root, limit)
    if not rows:
        return True, f"{root} 下无子目录或无法读取"
    lines = "; ".join(f"{p} {human(sz)}" for p, sz in rows)
    return True, f"{root} 下最大子目录（前{limit}）: {lines}"


def dns_flush_hint() -> Tuple[bool, str]:
    """给出刷新本地 DNS 解析器缓存的可执行命令（跨平台探测），仅指引不自动执行。

    返回 (ok, msg)。DNS 缓存刷新属系统级、且各 OS 命令不同，默认只提示，
    需用户确认（--apply 且 --yes）才执行。
    """
    cmds: List[str] = []
    if os.name == "nt":
        cmds = ["ipconfig /flushdns"]
    elif sys.platform == "darwin":
        cmds = ["dscacheutil -flushcache", "killall -HUP mDNSResponder"]
    elif shutil.which("resolvectl"):
        cmds = ["resolvectl flush-caches"]
    elif shutil.which("systemd-resolve"):
        cmds = ["systemd-resolve --flush-caches"]
    elif shutil.which("nscd"):
        cmds = ["nscd -i hosts"]
    if not cmds:
        return False, "未识别到 DNS 缓存刷新命令（systemd-resolved/nscd/mDNSResponder）；属指引项"
    return True, "可刷新 DNS 缓存的命令: " + " ; ".join(cmds) + "（需 --apply 且 --yes）"


def a11y_report() -> Tuple[bool, str]:
    """无障碍环境报告（ORCA / AT-SPI2）：探测读屏器、辅助技术总线与语音后端。

    纯只读探测，跨平台 graceful；本机缺少 orca / dbus / gsettings 时返回
    (False, 说明)，不抛异常。返回 (ok, msg)。
    """
    try:
        from ..a11y import environment_report, accessible_text
        return True, accessible_text("\n".join(environment_report()))
    except Exception as e:  # noqa: BLE001
        return False, f"无障碍报告不可用: {e}"


def a11y_atspi_bus() -> Tuple[bool, str]:
    """探测 AT-SPI2 辅助技术总线（org.a11y.Bus）是否响应。返回 (ok, msg)。"""
    try:
        from ..a11y import atspi_bus_available
        return atspi_bus_available()
    except Exception as e:  # noqa: BLE001
        return False, f"AT-SPI2 探测不可用: {e}"


def a11y_orca_status() -> Tuple[bool, str]:
    """ORCA 屏幕阅读器状态：是否安装 + 版本 + 是否随会话自启动。返回 (ok, msg)。"""
    try:
        from ..a11y import orca_version, screen_reader_enabled
        ok_v, ver = orca_version()
        ok_e, en = screen_reader_enabled()
        msg = f"ORCA: {ver}；自启动: {en}"
        return (ok_v or ok_e), msg
    except Exception as e:  # noqa: BLE001
        return False, f"ORCA 状态不可用: {e}"


def a11y_multi_report() -> Tuple[bool, str]:
    """**多系统**无障碍适配报告（Windows / macOS / Linux / Android / iOS / 鸿蒙）。

    按各自协议与接口只读探测：Windows 讲述人+UIA、macOS VoiceOver+AX、
    Linux ORCA+AT-SPI2、Android TalkBack+AccessibilityService、iOS VoiceOver、
    鸿蒙屏幕朗读+AccessibilityExtensionAbility。返回 (ok, msg)。
    """
    try:
        from ..a11y import a11y_probe_all, accessible_text
        lines = a11y_probe_all("any")
        return True, accessible_text("\n".join(lines))
    except Exception as e:  # noqa: BLE001
        return False, f"多系统无障碍报告不可用: {e}"


def a11y_docs_report() -> Tuple[bool, str]:
    """多系统无障碍**权威文档**清单（含协议 protocols 与接口 interfaces）。返回 (ok, msg)。"""
    try:
        from ..a11y import a11y_doc_list, accessible_text
        return True, accessible_text("\n".join(a11y_doc_list()))
    except Exception as e:  # noqa: BLE001
        return False, f"无障碍文档清单不可用: {e}"
