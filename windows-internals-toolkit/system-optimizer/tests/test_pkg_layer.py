"""语言底层（Python）打包与单文件分发测试。

覆盖三件事：
1. 版本号三处一致（pyproject / `sysweeper.__version__` / Go 侧）；
2. `tools/syspkg.py` 能用**纯标准库**产出 .pyz / wheel / sdist；
3. 产出的 .pyz 在**独立进程**里能跑，且包内 JSON 知识库没被静默吞掉
   （即 zip 场景下的 `importlib.resources` 兼容层有效）。

端到端构建较慢（约 1–2 MB 归档），因此只在 `test_pyz_end_to_end` 里做一次。
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PKG_ROOT = Path(__file__).resolve().parents[1] / "src" / "python"
SYSPKG = ROOT / "tools" / "syspkg.py"


def test_version_consistent_with_pyproject():
    sys.path.insert(0, str(PKG_ROOT))
    import sysweeper

    text = (ROOT / "system-optimizer" / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^\s*version\s*=\s*"([^"]+)"', text, re.M)
    assert m, "pyproject.toml 里没有 version"
    assert sysweeper.__version__ == m.group(1), "sysweeper.__version__ 与 pyproject.toml 不一致"


def test_go_version_consistent():
    text = (ROOT / "system-optimizer" / "pyproject.toml").read_text(encoding="utf-8")
    py_ver = re.search(r'^\s*version\s*=\s*"([^"]+)"', text, re.M).group(1)
    go_src = (ROOT / "system-optimizer" / "src" / "go" / "main.go").read_text(encoding="utf-8")
    m = re.search(r'const version = "([^"]+)"', go_src)
    assert m, "Go 侧没有版本常量"
    assert m.group(1) == py_ver, "Go 版本与 Python 版本不一致"


def test_syspkg_probe_reports_python_layer():
    out = subprocess.run([sys.executable, str(SYSPKG), "probe", "--json"],
                         capture_output=True, text=True, timeout=300)
    assert out.returncode == 0, out.stderr
    info = json.loads(out.stdout)
    assert info["tools"]["python3"]["found"] is True
    # 语言底层产物永远可产出
    for name in ("pyz", "wheel", "sdist"):
        assert name in info["artifacts"]
    # 缺工具链只记录不报错
    assert isinstance(info["skipped"], list)


def test_syspkg_targets_lists_hardware_matrix():
    out = subprocess.run([sys.executable, str(SYSPKG), "targets", "--json"],
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr
    rows = json.loads(out.stdout)
    names = {r["target"] for r in rows}
    assert {"pyz", "go-linux-arm64", "go-windows-arm64", "go-linux-riscv64"} <= names
    assert "android-arm64-v8a" in names


def test_zipres_install_is_noop_on_filesystem():
    """普通（非 zip）加载时 shim 必须完全不生效，避免误伤其他库。"""
    sys.path.insert(0, str(PKG_ROOT))
    from sysweeper import _zipres

    assert _zipres.install() is False


@pytest.mark.slow
def test_pyz_end_to_end(tmp_path):
    """构建 .pyz → 独立进程运行 → 校验知识库非空。"""
    out = tmp_path / "dist"
    build = subprocess.run([sys.executable, str(SYSPKG), "pyz", "--out", str(out)],
                           capture_output=True, text=True, timeout=600)
    assert build.returncode == 0, build.stdout + build.stderr

    pyz = sorted(out.glob("sysweeper-*.pyz"))
    assert pyz, "未产出 .pyz"
    target = pyz[-1]

    # 归档结构自检
    with zipfile.ZipFile(target) as z:
        names = z.namelist()
        assert "sysweeper/__main__.py" in names
        assert any(n.startswith("sysweeper/data/") and n.endswith(".json") for n in names)

    # 独立进程跑命令：detect 与依赖 JSON 的 hardware
    for args in (["detect"], ["hardware"], ["arch"]):
        run = subprocess.run([sys.executable, str(target)] + args,
                             capture_output=True, text=True, timeout=300)
        assert run.returncode == 0, run.stderr
        assert len(run.stdout.strip()) > 20, f"{args} 输出为空"

    # 强制走 shim 路径（模拟 3.9/3.10 的 zipimport 无原生资源支持）
    import os
    env = dict(os.environ, SYSWEEPER_ZIPRES_SHIM="1")
    run = subprocess.run([sys.executable, str(target), "arch"],
                         capture_output=True, text=True, timeout=300, env=env)
    assert run.returncode == 0, run.stderr
    assert "架构" in run.stdout, "shim 路径下知识库为空（arch.json 未读到）"

    # omni 接线盘点必须在 .pyz 内与源码树给出同一结论（v0.6.70 修）：
    # wiring() 原先用 pathlib 直读包内源码文本，zipapp 里读不到，把全部 82 项
    # 误报成「缺 cli/gui/task/data」（实测谎报 69 项真缺口，源码树实为 0）。
    run = subprocess.run([sys.executable, str(target), "omni", "gaps"],
                         capture_output=True, text=True, timeout=300)
    assert run.returncode == 0, run.stderr
    assert "[真缺口 · 0 项]" in run.stdout, (
        "zipapp 内 omni 接线盘点误报（包内文本/存在性读取没走 importlib.resources）")


def test_wheel_is_pep427_installable(tmp_path):
    """手写的 wheel 必须能被 pip 认：结构 + RECORD + 元数据齐全。"""
    out = tmp_path / "dist"
    build = subprocess.run([sys.executable, str(SYSPKG), "wheel", "--out", str(out)],
                           capture_output=True, text=True, timeout=600)
    assert build.returncode == 0, build.stdout + build.stderr

    whl = sorted(out.glob("sysweeper-*.whl"))
    assert whl, "未产出 wheel"
    with zipfile.ZipFile(whl[-1]) as z:
        names = z.namelist()
        assert "sysweeper/cli.py" in names
        dist_info = [n for n in names if n.endswith(".dist-info/METADATA")]
        assert dist_info, "缺少 dist-info/METADATA"
        assert any(n.endswith(".dist-info/RECORD") for n in names)
        assert any(n.endswith(".dist-info/entry_points.txt") for n in names)
        meta = z.read(dist_info[0]).decode("utf-8")
        assert "Name: sysweeper" in meta
        assert "Metadata-Version: 2.1" in meta
