"""诊断日志与脱敏（默认不信任输出）。

工程实践移植自 DiPlay（独立 CarPlay 接收端）的两个类，见仓库根
`docs/DiPlay-参考分析.md`：

* `BoundedDiagnosticWriter` —— 有界异步写入：单后台线程 + 有界队列，
  队列满时丢最旧，**调用方永不阻塞**；写盘失败不中断后续写入。
  理由：诊断绝不能反向拖垮主链路（扫描、报告、UI 回调里都会打日志）。
* `DiagnosticRedactor` —— 导出即脱敏：命中凭据关键词的行**整行丢弃**，
  MAC / UUID / 长十六进制 / IPv4 / IPv6 / 家目录一律占位符化，并截断。

与上游的两处有意差异：

1. 上游遇到含换行的消息直接丢弃（防日志注入）；这里改为**折叠成单行**，
   因为本项目的报告内容天然多行，丢弃会丢掉太多可用信息。
2. 额外脱敏家目录路径（Linux/macOS 的 `/home/<user>` 与 Windows 的
   `C:\\Users\\<user>`），因为扫描结果里满是用户路径。

安全底线：只写用户明确指定的文件，**绝不自动上传**任何内容。
"""

from __future__ import annotations

import datetime
import os
import queue
import re
import threading
import time

MAX_LINE = 700

# 命中即整行丢弃：宁可少一行，也不冒把凭据写进报告的风险
SECRET_RE = re.compile(
    r"(?i)(pass(word|phrase)?|passwd|pwd|secret|token|api[_\- ]?key|"
    r"private[_\- ]?key|credential|certificate|pair[_\- ]?record|ssid|psk|"
    r"authorization|bearer)"
)
MAC_RE = re.compile(r"(?i)(?<![0-9a-f])(?:[0-9a-f]{2}:){5}[0-9a-f]{2}(?![0-9a-f])")
UUID_RE = re.compile(
    r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
HEXID_RE = re.compile(r"(?i)\b[0-9a-f]{24,}\b")
IPV4_RE = re.compile(r"(?<![0-9.])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9.])")
IPV6_RE = re.compile(r"(?i)(?:[0-9a-f]{1,4}:){2,7}[0-9a-f]{0,4}")


def _home_patterns():
    """把真实家目录（含用户名）压成 `~`。"""
    out = []
    home = os.path.expanduser("~")
    if home and home != "~":
        out.append((re.compile(re.escape(home)), "~"))
        parent = os.path.dirname(home)          # /home、/Users、C:\Users
        if parent and os.path.basename(home):
            out.append((re.compile(re.escape(parent) + r"[\\/]" + re.escape(os.path.basename(home))), "~"))
    return out


class Redactor:
    """行级脱敏器。`redact()` 返回 None 表示这一行不该被导出。"""

    def __init__(self, max_line: int = MAX_LINE, extra_secret: str = ""):
        self.max_line = max_line
        self._secret = SECRET_RE
        if extra_secret:
            self._secret = re.compile(SECRET_RE.pattern[:-1] + "|" + extra_secret + ")", re.I)
        self._homes = _home_patterns()

    def redact(self, message) -> str:
        text = " ".join(str(message).split())   # 折叠换行/制表，防日志注入
        if not text:
            return None
        if self._secret.search(text):
            return None
        for pattern, repl in self._homes:
            text = pattern.sub(repl, text)
        text = MAC_RE.sub("[address]", text)
        text = UUID_RE.sub("[identifier]", text)
        text = HEXID_RE.sub("[identifier]", text)
        text = IPV6_RE.sub("[ip]", text)
        text = IPV4_RE.sub("[ip]", text)
        return text[: self.max_line]

    def redact_block(self, lines) -> list:
        """批量脱敏，返回保留下来的行（被丢弃的行直接消失）。"""
        out = []
        for line in lines:
            safe = self.redact(line)
            if safe is not None:
                out.append(safe)
        return out


class BoundedWriter:
    """有界异步写入器：单后台线程 + 有界队列，超载丢最旧，永不阻塞调用方。"""

    def __init__(self, write, max_pending: int = 64,
                 name: str = "sysweeper-diagnostics"):
        if max_pending <= 0:
            raise ValueError("max_pending 必须为正")
        self._write = write
        self._queue: "queue.Queue" = queue.Queue(maxsize=max_pending)
        self._cv = threading.Condition()
        self._closed = False
        self._active = False
        self._dropped = 0
        self._thread = threading.Thread(target=self._drain, name=name, daemon=True)
        self._thread.start()

    # ------------------------------------------------------------ 写入侧

    def enqueue(self, item) -> bool:
        """入队。返回 False 表示已关闭或当场被丢弃。"""
        if self._closed:
            return False
        try:
            self._queue.put_nowait(item)
            return True
        except queue.Full:
            with self._cv:
                try:                       # 队列满：丢最旧，保住最新
                    self._queue.get_nowait()
                    self._dropped += 1
                except queue.Empty:
                    pass
            try:
                self._queue.put_nowait(item)
                return True
            except queue.Full:
                return False

    @property
    def dropped_count(self) -> int:
        with self._cv:
            return self._dropped

    @property
    def pending_count(self) -> int:
        return self._queue.qsize()

    # ------------------------------------------------------------ 排空/关闭

    def flush(self, timeout: float = 5.0) -> bool:
        """尽量把队列写完；超时返回 False（不抛异常）。"""
        deadline = time.monotonic() + max(0.0, timeout)
        while True:
            with self._cv:
                if not self._active and self._queue.empty():
                    return True
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._cv.wait(min(remaining, 0.05))

    def close(self, timeout: float = 2.0) -> None:
        self._closed = True
        self.flush(timeout)

    # ------------------------------------------------------------ 后台线程

    def _drain(self) -> None:
        while True:
            item = self._queue.get()
            with self._cv:
                self._active = True
            try:
                # 写盘失败或回调抛异常都不能中断后续写入
                try:
                    self._write(item)
                except Exception:
                    pass
            finally:
                with self._cv:
                    self._active = False
                    self._cv.notify_all()


class DiagnosticLog:
    """带时间戳的行式诊断日志：默认脱敏 + 有界异步写盘。"""

    def __init__(self, path, redactor: Redactor = None, max_pending: int = 64,
                 encoding: str = "utf-8"):
        self.path = str(path)
        self.redactor = redactor or Redactor()
        self._encoding = encoding
        self._handle = open(self.path, "a", encoding=encoding)
        self._lock = threading.Lock()
        self._writer = BoundedWriter(self._write_line, max_pending=max_pending)
        self._skipped = 0
        self._written = 0

    def _write_line(self, line: str) -> None:
        with self._lock:
            self._handle.write(line + "\n")
            self._handle.flush()
            self._written += 1

    def append(self, message, now=None) -> bool:
        """追加一行；命中敏感词或被丢弃时返回 False。"""
        safe = self.redactor.redact(message)
        if safe is None:
            self._skipped += 1
            return False
        stamp = (now or datetime.datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
        return self._writer.enqueue(f"{stamp}  {safe}")

    # ------------------------------------------------------------ 状态

    @property
    def skipped_count(self) -> int:
        return self._skipped

    @property
    def written_count(self) -> int:
        return self._written

    @property
    def dropped_count(self) -> int:
        return self._writer.dropped_count

    def flush(self, timeout: float = 5.0) -> bool:
        return self._writer.flush(timeout)

    def close(self, timeout: float = 2.0) -> None:
        self._writer.close(timeout)
        try:
            self._handle.close()
        except OSError:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


# ---------------------------------------------------------------- 报告组装

HEADER = """# sysweeper 诊断报告

- 生成时间：{time}
- 版本：{version}
- 平台：{platform} {version_os}
- Python：{python}（{impl}）
- 脱敏：已开启（IP / MAC / 标识 / 家目录已占位符化；命中凭据关键词的行已整行丢弃）
- 丢弃行数：{skipped}

本报告**只写在本地，不会自动上传**。分享前请自行检查一遍。
"""

FOOTER = """
---
报告结束。若要把报告附到 issue，请确认里面没有热点密码、账号、序列号等隐私信息。
"""


def default_report_path() -> str:
    """默认落点：`~/Downloads`，没有 Downloads 就用家目录。"""
    home = os.path.expanduser("~")
    downloads = os.path.join(home, "Downloads")
    base = downloads if os.path.isdir(downloads) else home
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return os.path.join(base, f"sysweeper-diagnostics-{stamp}.txt")


def collect_environment() -> list:
    """收集只读环境信息（不执行任何修改类命令）。"""
    import platform as _platform
    import sys as _sys

    lines = [
        f"machine: {_platform.machine()}",
        f"platform: {_platform.platform()}",
        f"python: {_platform.python_version()} ({_platform.python_implementation()})",
        f"executable: {_sys.executable}",
        f"cwd: {os.getcwd()}",
    ]
    for key in ("LANG", "LC_ALL", "PATH"):
        value = os.environ.get(key)
        if value:
            lines.append(f"env {key}: {'set' if key == 'PATH' else value}")
    return lines


def build_report(version: str = "", platform_name: str = "", os_version: str = "",
                 extra_sections: dict = None) -> str:
    """组装一份脱敏后的诊断报告文本。"""
    import platform as _platform
    import sys as _sys

    redactor = Redactor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = [HEADER.format(
        time=now,
        version=version or "-",
        platform=platform_name or _platform.system().lower(),
        version_os=os_version or "",
        python=_platform.python_version(),
        impl=_platform.python_implementation(),
        skipped=0,
    )]
    text.append("## 环境\n")
    text += redactor.redact_block(collect_environment())
    for title, lines in (extra_sections or {}).items():
        text.append(f"\n## {title}\n")
        text += redactor.redact_block(lines if isinstance(lines, (list, tuple)) else [str(lines)])
    text.append(FOOTER)
    return "\n".join(str(x) for x in text)
