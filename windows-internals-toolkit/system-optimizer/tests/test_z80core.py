from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "research" / "comp" / "z80core.py"
RUNNER = ROOT / "research" / "comp" / "z80_runner.py"


def test_z80core_selftest():
    """Z80 执行内核已知答案自测全过（8 位运行层闭合的回归锁）。"""
    r = subprocess.run([sys.executable, str(CORE), "--selftest"],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    # 'selftest: N/N passed' 且两侧数字相等
    line = [ln for ln in r.stdout.splitlines() if ln.startswith("selftest:")][-1]
    total, _, passed = line.removeprefix("selftest:").strip().partition(" ")
    n_total = int(total.split("/")[0])
    n_passed = int(total.split("/")[1].rstrip(" passed"))
    assert n_total == n_passed >= 20, line


def test_z80_runner_roundtrip():
    """ihx 端到端：端口流/内存回读/HALT 停机/dz80 交叉核对（依赖 sdcc 产物
    hello8run.ihx 已入库；dz80 缺失时降级为跳过其核对而非失败）。"""
    ihx = RUNNER.parent / "hello8run.ihx"
    mp = RUNNER.parent / "hello8run.map"
    assert ihx.exists(), "hello8run.ihx 应随仓库提交"
    r = subprocess.run(
        [sys.executable, str(RUNNER), "run", str(ihx), "--map", str(mp),
         "--symbol", "_counter", "--port", "1"],
        capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Z80-RT-OK68" in r.stdout, r.stdout
    assert "_counter@8000 = 68h" in r.stdout, r.stdout
    assert "halted     : YES" in r.stdout, r.stdout
    assert "ROUNDTRIP-OK-8BIT" in r.stdout, r.stdout
