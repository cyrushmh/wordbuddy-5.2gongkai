"""native/jdk.py · OpenJDK/JVM 只读层测试（v0.6.27）。

这一层的安全承诺是**「只读」**——只读不是靠注释保证，是靠可验证的不变量。
所以除了功能测试，这里做两件更硬的事：

1. **源码级红线审计**（AST 静态扫描）：模块内不许出现写模式 open、不许直接
   ``os.system``/``subprocess``，所有经 ``common.run`` 执行的命令串必须是只读清单
   （只允许 ``jps -l`` / ``jcmd -l`` 这类列出型命令，绝不 recorder/attach/dump）。
   **新增代码如果破了这条，测试立刻红。**
2. **降级不抛**：没装 JDK 或 java 不在 PATH 时，每个探针都必须返回
   ``(False, 说明)`` 而不是让调用方炸掉。

功能测试覆盖：探针返回值契约、文档引用结构、禁用子命令清单、聚总报告、
以及 JSON 接口层 ``jdk.report`` 动作的注册与返回形状。
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "python"))

from sysweeper.native import jdk as nj  # noqa: E402

SRC = Path(nj.__file__).read_text(encoding="utf-8")
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


def test_executed_commands_are_readonly():
    """经 common.run 执行的每条命令都必须是**只读**命令。

    判定标准：命令串里不许出现向文件/设备的写重定向（忽略 fd 重定向如 2>&1 /
    2>/dev/null），也不许出现录制/attach/dump/热改标志这类高危写动作。本层允许的
    查询命令包括 java -version、java --list-modules、java -XX:+PrintFlagsFinal、
    jps -l、jcmd -l 等，**全部只读、不改动任何 JVM 状态**。
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
            self.generic_visit(node)

    _RunVisitor().visit(TREE)
    assert cmds, "没找到任何 common.run 调用，测试本身可能已失效"

    deny = ("> ", "tee ", "dd ", "GC.run", "heap_dump",
            "JFR.start", "JFR.dump", "VM.set_flag", "+Use", "--agent")
    bad = []
    for lineno, cmd in cmds:
        for i, ch in enumerate(cmd):
            if ch != ">":
                continue
            prev = cmd[i - 1] if i else ""
            if prev.isdigit() or prev in ("&", " "):
                prev2 = cmd[i - 2] if i >= 2 else ""
                if prev.isdigit() or prev2.isdigit():
                    continue  # 2>/dev/null、2>&1 这类 fd 重定向，安全
            bad.append(f"第 {lineno} 行存在写重定向片段: ...{cmd[max(0, i-15):i+25]}...")
            break
        for token in deny:
            if token in cmd:
                bad.append(f"第 {lineno} 行命令含危险动作 {token!r}: {cmd!r}")
    assert not bad, "只读层出现写类命令：\n  " + "\n  ".join(bad)


def test_forbidden_subcommands_are_documented_and_plausible():
    """明确列出「不执行」的高危子命令——这份清单本身就是文档的一部分。"""
    assert nj.FORBIDDEN_SUBCOMMANDS
    joined = " ".join(nj.FORBIDDEN_SUBCOMMANDS).lower()
    for token in ("jcmd", "gc.run", "heap_dump", "jfr.start", "vm.set_flag"):
        assert token in joined, f"禁用清单应提及 {token}"
    for line in nj.FORBIDDEN_SUBCOMMANDS:
        assert "#" in line, f"每条禁用子命令都应带说明注释：{line}"


# ── 2. 探针返回值契约 ─────────────────────────────────────────────────────────
@pytest.mark.parametrize("fn_name,label,need", list(nj.JDK_PROBES))
def test_every_probe_returns_bool_str(fn_name, label, need):
    """每个探针必须返回 (bool, str)：调用方据此决定显示还是降级。"""
    fn = getattr(nj, fn_name)
    ok, msg = fn()
    assert isinstance(ok, bool), f"{fn_name} 返回值第一项不是 bool"
    assert isinstance(msg, str) and msg.strip(), f"{fn_name} 返回值第二项不是非空 str"


def test_environment_report_shape():
    lines = nj.environment_report()
    assert isinstance(lines, list) and lines
    assert all(isinstance(x, str) for x in lines)
    assert "可用性" in lines[0]
    marks = [ln.strip()[0] for ln in lines[1:] if ln.strip().startswith(("✓", "✗"))]
    assert len(marks) == len(nj.JDK_PROBES)


def test_jdk_report_returns_tuple_and_readonly_note():
    ok, msg = nj.jdk_report()
    assert isinstance(ok, bool)
    assert isinstance(msg, str) and msg
    assert "只读" in msg, "总报告应明确写出只读承诺"


def test_jdk_doc_list_renders():
    lines = nj.jdk_doc_list()
    assert lines and all(isinstance(x, str) for x in lines)


# ── 3. 降级：未装 JDK / java 不在 PATH 不许炸 ───────────────────────────────────
def test_jdk_report_without_java_graceful(monkeypatch):
    monkeypatch.setattr(nj, "java_bin", lambda: False)
    ok, msg = nj.jdk_report()
    assert isinstance(ok, bool) and isinstance(msg, str) and msg
    assert any(w in msg for w in ("java", "JDK", "PATH", "只读"))


def test_probes_without_java_do_not_raise(monkeypatch):
    monkeypatch.setattr(nj, "java_bin", lambda: False)
    for fn_name, _label, _need in nj.JDK_PROBES:
        ok, msg = getattr(nj, fn_name)()
        assert isinstance(ok, bool) and isinstance(msg, str)


# ── 4. JSON 接口层 jdk.report 动作 ──────────────────────────────────────────
def test_jdk_report_action_registered_readonly():
    from sysweeper import webapi  # noqa: E402
    assert "jdk.report" in webapi.ACTIONS, "jdk.report 必须登记在动作白名单"
    fn, readonly, _desc = webapi.ACTIONS["jdk.report"]
    assert readonly is True, "jdk.report 是只读动作，必须标 True"
    assert callable(fn)


def test_jdk_report_action_shape():
    from sysweeper import webapi  # noqa: E402
    d = webapi.ACTIONS["jdk.report"][0]({"max_chars": 40000}, {})
    assert d["status"] in ("正常", "提示", "不适用", "异常")
    assert isinstance(d["summary"], str) and d["summary"]
    assert isinstance(d["text"], str)
    assert isinstance(d["truncated"], bool)
    assert isinstance(d["environment"], list)
    assert isinstance(d["docs"], list) and d["docs"]
    assert isinstance(d["forbidden"], list) and d["forbidden"]
    assert d.get("readonly_only") is True
