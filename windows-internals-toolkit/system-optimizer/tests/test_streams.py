"""CLI 标准流的健壮性测试：窄编码控制台 + 管道提前断开。

这两个用例都是从 GitHub Actions 真实跑挂的日志里捞出来的回归，
不是"想当然加的"：

1. **Windows / exit code 1** —— windows-latest runner 的 Git Bash 把 stdout 编码
   设成控制台 ANSI 代码页（英文镜像 cp1252，中文 Windows 常见 cp936/gbk）。
   CLI 输出的中文与 `→` `✓` 在窄编码下直接
   ``UnicodeEncodeError: 'charmap' codec can't encode``，进程 exit 1。
   见 docs/VALIDATION.md「2026-10-08 · CI 失败复盘」。
2. **Linux / exit code 120** —— `sysweeper hardware | head -6`，head 读完就关管道，
   Python 在**解释器退出阶段**那次 flush 抛 BrokenPipeError，退出码被抬成 120，
   再配上 runner 的 `set -o pipefail`，整步判失败。

测试策略：单元级（替换 sys.stdout，确定性触发）+ 子进程级（`PYTHONIOENCODING`、
真实 `| head`，端到端），两层都覆盖。
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
import textwrap

import pytest

from sysweeper import cli


SRC_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY_SRC = os.path.join(SRC_ROOT, "src", "python")


def _run_subprocess(args, env_extra=None, cwd=PY_SRC):
    """在独立进程里跑一段 Python，带上指定的环境变量。"""
    env = dict(os.environ)
    env["PYTHONPATH"] = PY_SRC
    env.pop("PYTHONIOENCODING", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable] + args, cwd=cwd, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)


# ==================================================================
# 一、窄编码控制台（Windows exit 1 回归）
# ==================================================================

def test_harden_streams_switches_to_utf8():
    """harden_streams 应把窄编码的 stdout 切成 UTF-8，之后写中文不炸。"""
    fake = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
    saved = sys.stdout
    sys.stdout = fake
    try:
        cli.harden_streams()
        assert sys.stdout.encoding.lower().replace("-", "") == "utf8"
        sys.stdout.write("探测结果：平台=linux → ✓\n")   # 不该抛
        sys.stdout.flush()
    finally:
        sys.stdout = saved


def test_harden_streams_falls_back_when_reconfigure_unsupported():
    """reconfigure 不可用时（老 Python / 被接管的流）不许抛，静默降级。"""

    class NoReconfigure(io.StringIO):
        def reconfigure(self, *a, **k):      # 存在但一律失败
            raise ValueError("this stream is not reconfigurable")

    fake = NoReconfigure()
    saved = sys.stdout
    sys.stdout = fake
    try:
        cli.harden_streams()                 # 内层 reconfigure 也失败，必须吞掉
    finally:
        sys.stdout = saved


@pytest.mark.parametrize("enc", ["cp1252", "ascii"])
def test_cli_survives_narrow_console_encoding(enc):
    """端到端：PYTHONIOENCODING 是窄编码时，CLI 必须正常退出 0。

    ascii 是最坏情况——任何非 ASCII 都编不出来，harden 一旦失效必挂。
    """
    script = textwrap.dedent(
        """
        import sys
        from sysweeper.cli import main
        sys.exit(main(["detect"]))
        """
    )
    r = _run_subprocess(["-c", script], env_extra={"PYTHONIOENCODING": enc})
    assert r.returncode == 0, f"PYTHONIOENCODING={enc} 退出码 {r.returncode}\n{r.stderr.decode('utf-8', 'replace')}"


# ==================================================================
# 二、管道提前断开（Linux exit 120 回归）
# ==================================================================

class _BrokenPipeStream(io.StringIO):
    """一个写/flush 就抛 BrokenPipeError 的假 stdout。"""

    def write(self, s):
        raise BrokenPipeError(32, "Broken pipe")

    def flush(self):
        raise BrokenPipeError(32, "Broken pipe")


def test_broken_pipe_during_command_returns_zero():
    """命令执行过程中写炸：main 必须吞掉并返回 0（不能是 120）。"""
    saved = sys.stdout
    sys.stdout = _BrokenPipeStream()
    try:
        assert cli.main(["detect"]) == 0
    finally:
        sys.stdout = saved


def test_broken_pipe_during_exit_flush_returns_zero():
    """最阴的一种：print 一路成功，只在退出前 flush 才炸 —— 也要返回 0。

    这正是 CI 日志里那两行：
        Exception ignored in: <_io.TextIOWrapper name='<stdout>' ...>
        BrokenPipeError: [Errno 32] Broken pipe
    """
    saved_out, saved_err = sys.stdout, sys.stderr

    class LateBoom(io.StringIO):
        def __init__(self):
            super().__init__()
            self.flushed = False

        def flush(self):
            if not self.flushed:
                self.flushed = True
                raise BrokenPipeError(32, "Broken pipe")

    sys.stdout, sys.stderr = LateBoom(), LateBoom()
    try:
        assert cli.main(["detect"]) == 0
    finally:
        sys.stdout, sys.stderr = saved_out, saved_err


def test_piped_to_head_is_not_exit_120():
    """真实端到端：`... | head -n` 在 pipefail 下不许出现 120。"""
    script = f'"{sys.executable}" -m sysweeper hardware | head -1'
    r = subprocess.run(["bash", "-o", "pipefail", "-c", script], cwd=PY_SRC,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
    # 即使某平台没触发 EPIPE 也是 0；关键是绝不能是 120（Python 断管的特征码）。
    assert r.returncode != 120, r.stderr.decode("utf-8", "replace")
    assert "BrokenPipeError" not in r.stderr.decode("utf-8", "replace")
    assert r.returncode == 0, f"rc={r.returncode}\n{r.stderr.decode('utf-8', 'replace')}"


# ==================================================================
# 三、退出码契约
# ==================================================================

def test_main_returns_zero_on_success():
    """main 现在有返回类型 int：成功路径必须是 0，好让 `sys.exit(main())` 有意义。"""
    assert cli.main(["detect"]) == 0


def test_pyz_entry_propagates_exit_code():
    """`.pyz` 的入口必须把退出码传出去。

    zipapp 生成的 shim 是写死的 `import sysweeper.__main__; sysweeper.__main__.main()`，
    **不会** sys.exit 返回值 —— 所以包级 main 只能靠抛 SystemExit 把退出码送出去。
    这条守住这个契约，否则 KeyboardInterrupt 的 130 在 .pyz 里会退化成 0。
    """
    from sysweeper import __main__ as pyz_entry

    saved = sys.stdout
    sys.stdout = io.StringIO()
    try:
        with pytest.raises(SystemExit) as excinfo:
            pyz_entry.main(["detect"])
    finally:
        sys.stdout = saved
    assert excinfo.value.code == 0


def test_main_interrupted_returns_130():
    """Ctrl-C 走 130（shell 惯例），不是 1。"""

    def boom(_args):
        raise KeyboardInterrupt

    saved = sys.stdout
    sys.stdout = io.StringIO()
    try:
        import argparse
        args = argparse.Namespace()
        args.func = boom
        orig_build = cli.build_parser

        class _P:
            def parse_args(self, argv=None):
                return args

        cli.build_parser = lambda: _P()
        try:
            assert cli.main(["detect"]) == 130
        finally:
            cli.build_parser = orig_build
    finally:
        sys.stdout = saved
