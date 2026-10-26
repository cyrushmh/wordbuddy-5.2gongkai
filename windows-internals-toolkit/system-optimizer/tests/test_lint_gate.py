"""lint-gate 白名单守卫自测（scripts/check_shell_lint.sh + .github/workflows/lint-shell.yml）。

守卫四类契约（#652）：
  1) 门禁脚本存在、可执行、bash shebang；
  2) 脚本内 WHITELIST 与本节 EXPECTED 一致，且覆盖「非排除」.sh 全集
     （双向：无白名单外漏网、无指向不存在文件的失效条目）；
  3) CI workflow 存在、YAML 可解析、引用门禁脚本、apt 安装 shellcheck
     （CI 侧不存在「缺席即放行」）；
  4) 门禁脚本实跑通过（shellcheck 宿主缺席时如实 skip，不伪造通过）。

排除口径（与脚本注释一致，均须真实存在、排除非空谈）：
  - quantum-kernel/**：上游 Linux 6.18.57 内核源码树（vendored）；
  - research/plang/samples/bash.sh：plang 语法样例。
hadolint / actionlint 两环宿主缺席，如实挂 needs_action——本测试断言
其配置确实尚未落地（防「伪接入」记述），不替代真实接入。
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

# 外层仓根：tests -> system-optimizer -> windows-internals-toolkit(内层) -> 外层根
REPO = Path(__file__).resolve().parents[3]
GATE = REPO / "scripts" / "check_shell_lint.sh"
WORKFLOW = REPO / ".github" / "workflows" / "lint-shell.yml"

# 与 scripts/check_shell_lint.sh 的 WHITELIST 一一对应（改任一处另一处须同步）
EXPECTED_WHITELIST = [
    "scripts/check_shell_lint.sh",
    "classics-harmony-app/build_hap.sh",
    "classics-ios-mac/build_ios_mac.sh",
    "classics-linux/build-arch.sh",
    "classics-linux/build-debs.sh",
    "classics-linux/build-mobile.sh",
    "classics-rs/build-rs.sh",
    "windows-internals-toolkit/tools/bootstrap.sh",
    "windows-internals-toolkit/tools/disposable-env.sh",
    "windows-internals-toolkit/Windows/build.sh",
    "windows-internals-toolkit/Windows/push-to-github.sh",
    "windows-internals-toolkit/system-optimizer/research/quantum/quantum-testbed.sh",
]

EXCLUDE_RE = re.compile(r"(^|/)(quantum-kernel|\.git)/|research/plang/samples/")


def _script_whitelist() -> list[str]:
    """从门禁脚本解析 WHITELIST=( ... ) 数组（单一事实来源在脚本侧）。"""
    text = GATE.read_text(encoding="utf-8")
    m = re.search(r"WHITELIST=\(\n(.*?)\n\)", text, re.S)
    assert m, "门禁脚本中未找到 WHITELIST=( ... ) 数组"
    return [ln.strip() for ln in m.group(1).splitlines() if ln.strip()]


def _repo_shell_scripts() -> list[str]:
    """全仓 .sh（排除 .git / quantum-kernel / samples），相对外层根。"""
    found = []
    for p in REPO.rglob("*.sh"):
        rel = p.relative_to(REPO).as_posix()
        if EXCLUDE_RE.search(rel):
            continue
        found.append(rel)
    return sorted(found)


def test_gate_script_exists_and_executable():
    assert GATE.is_file(), f"门禁脚本不存在: {GATE}"
    first = GATE.read_text(encoding="utf-8").splitlines()[0]
    assert first.startswith("#!") and "bash" in first, f"shebang 非 bash: {first}"
    assert GATE.stat().st_mode & 0o111, "门禁脚本无可执行位"


def test_script_whitelist_matches_expected():
    assert sorted(_script_whitelist()) == sorted(EXPECTED_WHITELIST), (
        "脚本 WHITELIST 与测试 EXPECTED 漂移——两处须同步修订")


def test_whitelist_covers_all_repo_shell_scripts():
    """双向契约：无漏网（扫描 ⊆ 白名单）、无失效条目（白名单 ⊆ 真实文件）。"""
    scanned = _repo_shell_scripts()
    wl = set(_script_whitelist())
    rogue = [f for f in scanned if f not in wl]
    assert not rogue, f"白名单外 .sh（新增脚本须显式入册）: {rogue}"
    missing = [f for f in wl if not (REPO / f).is_file()]
    assert not missing, f"白名单条目指向不存在的文件: {missing}"
    assert scanned, "扫描结果为空——排除正则可能误杀全仓"


def test_exclusions_are_real_not_vacuous():
    """排除口径须真实有料：内核树与样例都在，且排除后确有脚本被挡在门外。"""
    kernel_sh = list(REPO.glob("quantum-kernel/**/*.sh"))
    assert kernel_sh, "quantum-kernel 下无 .sh——排除口径失去意义"
    sample = REPO / "windows-internals-toolkit/system-optimizer/research/plang/samples/bash.sh"
    assert sample.is_file(), "plang 样例不存在——排除口径失去意义"
    scanned = _repo_shell_scripts()
    assert not any("quantum-kernel" in f for f in scanned)
    assert not any(f.endswith("samples/bash.sh") for f in scanned)


def test_workflow_exists_and_references_gate():
    assert WORKFLOW.is_file(), f"CI workflow 不存在: {WORKFLOW}"
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert doc.get("name") == "Lint Shell"
    # 真触发（非注释掉的 on:）；PyYAML 的 YAML 1.1 挪威问题：on: 解析为布尔键 True
    triggers = doc.get(True, doc.get("on"))
    assert triggers is not None, "workflow 无 on: 触发配置"
    assert "push" in triggers and "pull_request" in triggers, "workflow 缺 push/pull_request 触发"
    steps = doc["jobs"]["shellcheck"]["steps"]
    runs = [s.get("run", "") for s in steps]
    assert any("apt-get install" in r and "shellcheck" in r for r in runs), (
        "workflow 未安装 shellcheck——CI 侧必须保证在场（本地 SKIP 不适用于 CI）")
    assert any("check_shell_lint.sh" in r for r in runs), "workflow 未调用门禁脚本"


def test_hadolint_actionlint_not_yet_wired():
    """如实挂账：hadolint / actionlint 宿主缺席、CI 未接入（needs_action）。

    本测试是「未接入」的守卫而非「已接入」的证明——将来真实接入时，
    应改写为对相应 workflow / 配置的存在性断言，并删除本测试。
    """
    wf_dir = REPO / ".github" / "workflows"
    names = [p.name for p in wf_dir.glob("*.yml")]
    assert not any("hadolint" in n for n in names), (
        "hadolint workflow 已出现——请把本测试改写为接入态断言")
    assert not any("actionlint" in n for n in names), (
        "actionlint workflow 已出现——请把本测试改写为接入态断言")


def test_gate_script_runs_clean():
    """实跑门禁：PASS 或（宿主无 shellcheck 时）如实 SKIP。"""
    if shutil.which("shellcheck") is None:
        pytest.skip("宿主无 shellcheck——门禁实跑未评估（CI 侧由 workflow 兜底安装）")
    proc = subprocess.run(["bash", str(GATE)], capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, f"门禁实跑未过:\n{proc.stdout}\n{proc.stderr}"
    assert "[PASS]" in proc.stdout
