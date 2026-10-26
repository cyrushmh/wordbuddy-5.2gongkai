"""32 位 DOS DJGPP C 闭环测试（#690 DJGPP GCC 缺口闭合批次）。

32 位 DOS 档此前只有 as/ld 手写链（hello32.exe 7628B），C 编译路径缺位
（DJGPP GCC/libc/stub 不在 apt，needs_verify 挂号）。本批以 andrewwutw/build-djgpp
v3.4 预构建工具链（Linux64，GCC 12.2.0）闭合。

仓内可复验部分（不依赖 DOS 环境）：
  1. hello32c.c 以宿主 gcc -std=c89 -pedantic 零警告编译——ANSI C 纪律可验；
  2. 运行 stdout/Z32C.TXT/退出码三面断言——程序逻辑与设计值 0xFB 可验；
  3. DOS 侧实跑证据（hello32c.exe + hello32c_evidence.txt）归档存在且口径一致。
"""

import os
import subprocess
import sys
import tempfile

COMP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "research", "comp"
)
SRC = os.path.join(COMP_DIR, "hello32c.c")
EVIDENCE = os.path.join(COMP_DIR, "hello32c_evidence.txt")
EXE = os.path.join(COMP_DIR, "hello32c.exe")

MSG = "Z32C-RT-OK"
EXPECTED_STDOUT = "Z32C-RT-OK55\nFB\n"


def _design_value():
    """独立复算设计值：0x55 + 消息字符和 + 0x0A（与 8 位档同构，消息 10 字符）。"""
    v = 0x55
    for ch in MSG:
        v += ord(ch)
    v += 0x0A
    return v & 0xFF


def test_design_value_independent():
    # 独立复算（非抄录被测程序）钉死设计值 0xFB
    assert _design_value() == 0xFB
    assert len(MSG) == 10  # Z32C-RT-OK：10 字符（8 位档 Z80-RT-OK 为 9 字符 → 0x68）


def test_host_gcc_roundtrip():
    # 宿主 gcc 编译运行：stdout / Z32C.TXT / 退出码三面断言
    with tempfile.TemporaryDirectory() as td:
        exe = os.path.join(td, "h32c")
        r = subprocess.run(
            ["gcc", "-std=c89", "-pedantic", "-Wall", "-Wextra", "-O2",
             "-o", exe, SRC],
            capture_output=True, text=True, timeout=120,
        )
        assert r.returncode == 0, r.stderr
        assert r.stderr.strip() == "", "pedantic 下应零警告：%s" % r.stderr
        assert os.path.exists(exe)

        p = subprocess.run([exe], capture_output=True, text=True,
                           cwd=td, timeout=60)
        assert p.returncode == 0
        assert p.stdout == EXPECTED_STDOUT

        rt = os.path.join(td, "Z32C.TXT")
        assert os.path.exists(rt)
        with open(rt, "rb") as f:
            assert f.read() == EXPECTED_STDOUT.encode("ascii")


def test_dos_side_evidence_archived():
    # DOS 侧（DJGPP 交叉编译 + dosbox 实跑）证据归档存在且口径一致
    assert os.path.exists(EXE), "hello32c.exe（DJGPP go32 产物）应归档"
    assert os.path.exists(EVIDENCE), "DOS 实跑证据应归档"
    with open(EXE, "rb") as f:
        head = f.read(2)
    assert head == b"MZ", "DJGPP 产物应为 MZ（STUB）头"
    with open(EVIDENCE, "r", encoding="utf-8", errors="replace") as f:
        ev = f.read()
    assert "Z32C-RT-OK55" in ev
    assert "FB" in ev
    assert "12.2.0" in ev, "证据应含 DJGPP GCC 版本口径"
