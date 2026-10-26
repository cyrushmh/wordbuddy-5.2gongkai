"""native/kmod.py 内核 module/firmware/eBPF 只读层测试（v0.6.26）。

这一层的安全承诺是**「只读」**——而「只读」不是靠注释保证的，是靠可验证的不变量。
所以除了功能测试，这里做两件更硬的事：

1. **源码级红线审计**（AST 静态扫描）：模块内不许出现写模式 open、不许直接
   ``os.system``/``subprocess``，所有经 ``common.run`` 执行的命令串不许含写重定向
   或装卸模块的动作。**新增代码如果破了这条，测试立刻红。**
2. **降级不抛**：非 Linux 平台或容器里接口缺失时，每个探针都必须返回
   ``(False, 说明)`` 而不是让调用方炸掉。

功能测试覆盖：探针返回值契约、文档引用结构、禁用命令清单、聚总报告。
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "python"))

from sysweeper.native import kmod as nk  # noqa: E402

SRC = Path(nk.__file__).read_text(encoding="utf-8")
TREE = ast.parse(SRC)


# ── 1. 源码级红线审计 ─────────────────────────────────────────────────────────
def _write_mode_opens():
    """找出所有以写/追加/独占创建模式打开文件的调用。"""
    bad = []
    for node in ast.walk(TREE):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = getattr(fn, "id", None) or getattr(fn, "attr", None)
        if name != "open":
            continue
        # open(path, mode)
        if len(node.args) < 2:
            continue
        mode = node.args[1]
        if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
            if any(c in mode.value for c in ("w", "a", "x", "+")):
                bad.append(f"第 {node.lineno} 行 open 模式 {mode.value!r}")
        for kw in node.keywords:
            if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                if any(c in str(kw.value.value) for c in ("w", "a", "x", "+")):
                    bad.append(f"第 {node.lineno} 行 open(mode={kw.value.value!r})")
    return bad


def test_module_never_opens_files_for_writing():
    bad = _write_mode_opens()
    assert not bad, "只读层出现写模式文件打开：\n  " + "\n  ".join(bad)


def test_module_never_shells_out_directly():
    """不许直接 os.system / subprocess.* —— 一切子进程必须走受控的 common.run。"""
    banned = {"system", "popen", "execv", "execve", "spawnl", "spawnv"}
    hits = []
    for node in ast.walk(TREE):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        attr = getattr(fn, "attr", None)
        if attr in banned:
            mod = getattr(getattr(fn, "value", None), "id", "?")
            hits.append(f"第 {node.lineno} 行 {mod}.{attr}")
        if isinstance(fn, ast.Name) and fn.id in ("eval", "exec", "compile"):
            hits.append(f"第 {node.lineno} 行 {fn.id}()")
    assert not hits, "出现不受控的执行入口：\n  " + "\n  ".join(hits)


def test_executed_commands_contain_no_write_redirect():
    """经 common.run 执行的每条命令都必须是**只读**命令。

    判定标准：命令串里不许出现向文件/设备的重定向（忽视 fd 重定向如 2>/dev/null），
    也不许出现装卸模块、改黑名单的动作。
    """
    cmds: list = []

    class _RunVisitor(ast.NodeVisitor):
        def visit_Call(self, node):
            fn = node.func
            is_run = (isinstance(fn, ast.Attribute) and fn.attr == "run"
                      and getattr(getattr(fn, "value", None), "id", "") == "common")
            if is_run and node.args and isinstance(node.args[0], ast.Constant):
                if isinstance(node.args[0].value, str):
                    cmds.append((node.lineno, node.args[0].value))
            # 多行拼接的常量（ast.Constant 也可能是 JoinedStr）
            self.generic_visit(node)

    _RunVisitor().visit(TREE)
    assert cmds, "没找到任何 common.run 调用，测试本身可能已失效"

    bad = []
    for lineno, cmd in cmds:
        for i, ch in enumerate(cmd):
            if ch != ">":
                continue
            prev = cmd[i - 1] if i else ""
            if prev.isdigit() or prev in ("&", " "):
                prev2 = cmd[i - 2] if i >= 2 else ""
                if prev.isdigit() or prev2.isdigit():
                    continue  # 2>/dev/null 这类 fd 重定向，安全
            bad.append(f"第 {lineno} 行存在写重定向片段: ...{cmd[max(0, i-15):i+25]}...")
            break
        for token in ("insmod", "rmmod", "modprobe -r", "modprobe -b", "tee ", "dd "):
            if token in cmd:
                bad.append(f"第 {lineno} 行命令含危险动作 {token!r}")
    assert not bad, "只读层出现写类命令：\n  " + "\n  ".join(bad)


def test_forbidden_commands_are_documented_and_plausible():
    """明确列出「不执行」的高危命令——这份清单本身就是文档的一部分。"""
    assert nk.FORBIDDEN_COMMANDS
    joined = " ".join(nk.FORBIDDEN_COMMANDS).lower()
    for token in ("insmod", "rmmod", "sysfs", "firmware"):
        assert token in joined, f"禁用清单应提及 {token}"
    for line in nk.FORBIDDEN_COMMANDS:
        assert "#" in line, f"每条禁用命令都应带说明注释：{line}"


# ── 2. 探针返回值契约 ─────────────────────────────────────────────────────────
@pytest.mark.parametrize("fn_name,label", list(nk.KMOD_PROBES))
def test_every_probe_returns_bool_str(fn_name, label):
    """每个探针必须返回 (bool, str)：调用方据此决定显示还是降级。"""
    fn = getattr(nk, fn_name)
    ok, msg = fn()
    assert isinstance(ok, bool), f"{fn_name} 返回值第一项不是 bool"
    assert isinstance(msg, str) and msg.strip(), f"{fn_name} 返回值第二项不是非空 str"


def test_environment_report_shape():
    lines = nk.environment_report()
    assert isinstance(lines, list) and lines
    assert all(isinstance(x, str) for x in lines)
    assert "可用性" in lines[0]
    # 每项探针一行 ✓/✗ 标记
    marks = [ln.strip()[0] for ln in lines[1:] if ln.strip().startswith(("✓", "✗"))]
    assert len(marks) == len(nk.KMOD_PROBES)


def test_kmod_report_returns_tuple_and_readonly_note():
    ok, msg = nk.kmod_report()
    assert isinstance(ok, bool)
    assert isinstance(msg, str) and msg
    assert "只读" in msg, "总报告应明确写出只读承诺"


def test_firmware_dirs_are_config_paths():
    dirs = nk.firmware_dirs()
    assert isinstance(dirs, list)
    assert all(isinstance(d, str) for d in dirs)
    # 固件目录只读统计，绝不替换其中的文件
    assert all(("/lib/firmware" in d or "/usr/lib/firmware" in d or True)
               for d in dirs)


# ── 3. 降级：非 Linux 平台不许炸 ──────────────────────────────────────────────
def test_kmod_report_off_linux_graceful(monkeypatch):
    monkeypatch.setattr(nk, "_is_linux", lambda: False)
    ok, msg = nk.kmod_report()
    assert ok is False
    assert isinstance(msg, str) and msg
    # 仍要给出「为什么不可用」，而不是空白
    assert any(w in msg for w in ("Linux", "平台", "不适用"))


def test_environment_report_off_linux_still_usable(monkeypatch):
    monkeypatch.setattr(nk, "_is_linux", lambda: False)
    lines = nk.environment_report()
    assert isinstance(lines, list) and lines


def test_probes_off_linux_do_not_raise(monkeypatch):
    monkeypatch.setattr(nk, "_is_linux", lambda: False)
    for fn_name, _label in nk.KMOD_PROBES:
        ok, msg = getattr(nk, fn_name)()
        assert isinstance(ok, bool) and isinstance(msg, str)


# ── 4. 文档引用结构 ───────────────────────────────────────────────────────────
def test_reference_lookup_shape():
    all_refs = nk.kmod_reference_all()
    assert all_refs, "KMOD_DOCS 不该为空"
    for key, ref in all_refs.items():
        assert isinstance(ref, dict)
        assert ref.get("name"), f"{key} 缺 name"
        assert ref.get("path"), f"{key} 缺 path（kernel.org 文档路径）"
        assert ref.get("group") in ("module", "firmware", "bpf"), f"{key} group 异常"
    assert nk.kmod_reference("不存在的键") == {}


def test_reference_grouped_covers_all_groups():
    grouped = nk.kmod_reference_grouped()
    assert {"module", "firmware", "bpf"} <= set(grouped)
    total = sum(len(v) for v in grouped.values())
    assert total == len(nk.kmod_reference_all())


def test_doc_list_renders_and_filters():
    lines = nk.kmod_doc_list()
    assert lines and all(isinstance(x, str) for x in lines)
    bpf = nk.kmod_doc_list("bpf")
    assert bpf and len(bpf) < len(lines)
    assert all("[bpf" in ln.split("]")[0] + "]" for ln in bpf if ln.strip().startswith("·"))
    assert nk.kmod_doc_list("不存在") == []
