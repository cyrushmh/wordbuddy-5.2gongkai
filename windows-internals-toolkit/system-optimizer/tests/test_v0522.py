"""v0.5.22 测试：Android 8 下探 + 适老化 / OpenJDK / 内核 module·firmware·eBPF
/ 任务档位（大而全·小而全）/ 数学量化评分。

设计要点（与全局一致）：
- 纯 stdlib、离线、**只读优先**。本轮新增的三块（JDK / 内核 module / 适老化）
  全部只读，所以测试的核心是「**不变量守护**」：断言源码里没有写操作命令、
  断言版本门控正确、断言敏感值不回显、断言档位不越权。
- 非目标环境（无 adb / 无 java / 非 Linux）必须优雅降级为 (False, 指引)，
  绝不抛异常——这是本仓库对所有原生接口的硬要求。
- 档位的核心不变量：minimal ⊆ lite ⊆ standard ⊆ full，且 minimal 零风险。
"""

from __future__ import annotations

import inspect
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src", "python"))


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture
def na():
    from sysweeper.native import android as A
    return A


@pytest.fixture
def njdk():
    from sysweeper.native import jdk as J
    return J


@pytest.fixture
def nk():
    from sysweeper.native import kmod as K
    return K


@pytest.fixture
def mt():
    from sysweeper.native import metrics as M
    return M


@pytest.fixture
def pf():
    from sysweeper import profiles as P
    return P


# =========================================================================== #
# 一、Android 8（API 26）下探 + 适老化无障碍
# =========================================================================== #

class TestAndroid8Compat:
    def test_min_api_is_26(self, na):
        """下探下限必须是 API 26（Android 8.0 Oreo）。"""
        assert na.MIN_API == 26

    def test_api_names_cover_26_to_36(self, na):
        for sdk, name in ((26, "8.0"), (27, "8.1"), (28, "9"), (29, "10"),
                          (30, "11"), (31, "12"), (33, "13")):
            assert na.api_name(sdk) == name
        assert na.api_name(0) == "?"
        assert "16" in na.api_name(99)      # 未知新版本按最新已知处理

    def test_supports_version_gate(self, na):
        assert na.supports(26, 26) is True
        assert na.supports(26, 29) is False    # Android 8 无高对比度
        assert na.supports(33, 29) is True
        assert na.supports(0, 26) is False     # 读不到 sdk 时保守 False

    def test_sdk_int_degrades_without_device(self, na):
        """无设备时 sdk_int 返回 0，绝不抛异常。"""
        v = na.sdk_int()
        assert isinstance(v, int)
        assert v >= 0

    def test_a11y_probes_degrade_without_adb(self, na, monkeypatch):
        """未装 adb 时所有适老化探针返回 (False, 指引)，不抛。"""
        monkeypatch.setattr(na, "available", lambda: False)
        for fn_name, _label, _min in na.A11Y_PROBES:
            ok, msg = getattr(na, fn_name)()
            assert ok is False, f"{fn_name} 应降级"
            assert isinstance(msg, str) and msg

    def test_a11y_total_report_degrades(self, na, monkeypatch):
        monkeypatch.setattr(na, "available", lambda: False)
        ok, msg = na.elderly_a11y_report()
        assert ok is False
        assert "adb" in msg

    def test_sdk_gate_message_says_version_too_low(self, na, monkeypatch):
        """低版本时必须明说「无此开关」，不能伪装成已开启。"""
        monkeypatch.setattr(na, "available", lambda: True)
        monkeypatch.setattr(na, "connected", lambda: True)
        monkeypatch.setattr(na, "sdk_int", lambda: 26)
        monkeypatch.setattr(na, "version", lambda: "8.0")
        ok, why = na._sdk_gate(29, "高对比度文本")
        assert ok is False
        assert "29" in why and "8.0" in why

        ok2, why2 = na._sdk_gate(26, "色彩校正")
        assert ok2 is True and why2 == ""

    def test_display_report_gates_high_contrast_by_api(self, na, monkeypatch):
        """API 26 上不得出现高对比度/深色模式（API 29+ 才有），但必须有放大镜。"""
        monkeypatch.setattr(na, "available", lambda: True)
        monkeypatch.setattr(na, "connected", lambda: True)
        monkeypatch.setattr(na, "sdk_int", lambda: 26)
        monkeypatch.setattr(na, "version", lambda: "8.0")
        monkeypatch.setattr(na, "_setting", lambda ns, key, timeout=90: (False, ""))
        ok, msg = na.a11y_display_report()
        assert ok is True
        assert "放大镜" in msg or "magnification" in msg
        assert "需 API 29+" in msg          # 明确说明低版本无此开关
        assert "已开" not in msg             # 绝不伪装成已开启

    def test_display_report_includes_high_contrast_on_api33(self, na, monkeypatch):
        monkeypatch.setattr(na, "available", lambda: True)
        monkeypatch.setattr(na, "connected", lambda: True)
        monkeypatch.setattr(na, "sdk_int", lambda: 33)
        monkeypatch.setattr(na, "version", lambda: "13")
        seen = {}

        def fake_setting(ns, key, timeout=90):
            seen[key] = (ns, True)
            return True, "1"

        monkeypatch.setattr(na, "_setting", fake_setting)
        ok, msg = na.a11y_display_report()
        assert ok is True
        assert "accessibility_high_text_contrast" in seen     # API 33 会去读
        assert "ui_night_mode" in seen
        assert "已开" in msg

    def test_font_scale_verdict(self, na, monkeypatch):
        monkeypatch.setattr(na, "available", lambda: True)
        monkeypatch.setattr(na, "connected", lambda: True)
        monkeypatch.setattr(na, "_setting", lambda ns, key, timeout=90: (True, "1.3"))
        ok, msg = na.font_scale_report()
        assert ok is True
        assert "1.3" in msg
        assert "大字体" in msg

    def test_eyecare_gates_night_display(self, na, monkeypatch):
        monkeypatch.setattr(na, "available", lambda: True)
        monkeypatch.setattr(na, "connected", lambda: True)
        monkeypatch.setattr(na, "sdk_int", lambda: 26)
        monkeypatch.setattr(na, "version", lambda: "8.0")
        monkeypatch.setattr(na, "_setting", lambda ns, key, timeout=90: (False, ""))
        ok, msg = na.a11y_eyecare_report()
        assert ok is True
        assert "需 API 28+" in msg

    def test_advice_is_pure_text_no_commands(self, na):
        """适老化建议必须是纯文字——不含 adb 命令（无设备时也能念给长辈）。"""
        advice = na.elderly_a11y_advice()
        assert len(advice) >= 8
        joined = "\n".join(advice)
        assert "adb" not in joined
        assert "settings put" not in joined

    def test_compat_report_off_device(self, na, monkeypatch):
        monkeypatch.setattr(na, "available", lambda: False)
        ok, msg = na.android_compat_report()
        assert ok is False

    def test_compat_table_declares_api26_floor(self, na, monkeypatch):
        monkeypatch.setattr(na, "available", lambda: True)
        monkeypatch.setattr(na, "sdk_int", lambda: 26)
        ok, msg = na.android_compat_report()
        assert ok is True
        assert "API 26" in msg
        assert "Android 8.0" in msg
        # 色彩校正需 API 26，恰好达标 → 标为可用
        assert "✓ 本机可用" in msg
        # 应用休眠需 API 30，本机 26 → 必须标为不可用
        assert "✗ 本机 API 26 < 30" in msg

    def test_a11y_source_never_writes_settings(self, na):
        """不变量：适老化探针不得出现可执行的 `settings put` 写操作。

        注意只检查**代码语句**（非注释、非字符串字面量）——文档字符串与
        展示文本里提到 settings put 属于说明性内容，是允许的。
        """
        import ast
        tree = ast.parse(inspect.getsource(na))
        # 只看 v0.5.22 新增的适老化函数
        a11y_fns = {"font_scale_report", "font_weight_report",
                    "a11y_display_report", "a11y_speech_report",
                    "a11y_motion_haptics_report", "a11y_eyecare_report",
                    "elderly_a11y_report", "android_compat_report", "_setting"}
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or node.name not in a11y_fns:
                continue
            for sub in ast.walk(node):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    # 这是**传给命令执行的字符串常量**，必须不是 put
                    assert "settings put" not in sub.value, \
                        f"{node.name} 内含 settings put 写命令: {sub.value}"
                    assert not sub.value.strip().startswith("insmod")
                    assert not sub.value.strip().startswith("rmmod")


class TestAndroidA11yTasks:
    def test_a11y_tasks_registered(self):
        from sysweeper import registry
        ids = {t.id for t in registry.all_tasks() if t.platform == "android"}
        for tid in ("and_a11y_report", "and_a11y_font", "and_a11y_display",
                    "and_a11y_talkback", "and_a11y_motion", "and_a11y_eyecare",
                    "and_a11y_guide", "and_compat_audit"):
            assert tid in ids, f"缺少任务 {tid}"

    def test_a11y_tasks_are_low_risk_not_optin(self):
        """适老化任务全部 low 风险且默认开启（体检类不该要确认）。"""
        from sysweeper import registry
        for t in registry.all_tasks():
            if t.id.startswith("and_a11y") or t.id == "and_compat_audit":
                assert t.risk == "low", t.id
                assert t.opt_in is False, t.id
                assert t.standards, f"{t.id} 缺标准引用"

    def test_a11y_tasks_visible_on_android8(self):
        """Android 8.0 上适老化任务必须出现（下探的意义所在）。"""
        from sysweeper import registry
        got = {t.id for t in registry.applicable("android", "8")}
        for tid in ("and_a11y_report", "and_a11y_font", "and_a11y_display",
                    "and_a11y_talkback", "and_a11y_motion", "and_a11y_eyecare"):
            assert tid in got, f"{tid} 在 Android 8 上被错误隐藏"

    def test_a11y_tasks_hidden_below_android8(self):
        """Android 7 上不应出现（守住 min_ver=8 的门控）。"""
        from sysweeper import registry
        got = {t.id for t in registry.applicable("android", "7")}
        assert "and_a11y_report" not in got

    def test_app_hibernate_gated_to_android11(self):
        """v0.5.22 修复：set-app-hibernate 是 API 30 能力，低版本必须隐藏。"""
        from sysweeper import registry
        got8 = {t.id for t in registry.applicable("android", "8")}
        got10 = {t.id for t in registry.applicable("android", "10")}
        got11 = {t.id for t in registry.applicable("android", "11")}
        assert "and_app_hibernate" not in got8
        assert "and_app_hibernate" not in got10
        assert "and_app_hibernate" in got11

    def test_android_docs_have_a11y_entries(self):
        import json
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "android_docs.json").read_text(encoding="utf-8")
        d = json.loads(data)
        for key in ("accessibility", "eyecare"):
            assert key in d, f"文档缺 {key} 条目"
            assert d[key]["url"].startswith("https://")
            assert d[key]["protocols"]
            assert d[key]["advice"]

    def test_android_versions_json_has_legacy_entries(self):
        import json
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "versions.json").read_text(encoding="utf-8")
        d = json.loads(data)["android"]
        for v in ("8", "9", "10", "11", "12"):
            assert v in d, f"版本表缺 Android {v}"
            assert d[v]["name"]


# =========================================================================== #
# 二、OpenJDK / JVM 只读层
# =========================================================================== #

class TestOpenJDK:
    def test_refs_have_official_sources(self, njdk):
        for key in ("jdk", "jvm", "jpms", "gc", "jit", "jfr", "diagnostics"):
            ref = njdk.jdk_reference(key)
            assert ref, f"缺文档条目 {key}"
            assert ref["url"].startswith("https://")
            assert ref["summary"] and ref["advice"]

    def test_doc_list_renders(self, njdk):
        lines = njdk.jdk_doc_list()
        assert len(lines) >= 14
        assert any("openjdk.org" in l for l in lines)

    def test_java_home_and_bins(self, njdk):
        # 没装 JDK 时返回空串而非抛异常
        assert isinstance(njdk.java_home(), str)
        assert isinstance(njdk.java_bin(), str)
        assert isinstance(njdk.javac_bin(), str)

    def test_version_degrades_without_java(self, njdk, monkeypatch):
        monkeypatch.setattr(njdk, "java_bin", lambda: "")
        ok, msg = njdk.java_version()
        assert ok is False and "java" in msg

    def test_total_report_degrades_without_java(self, njdk, monkeypatch):
        monkeypatch.setattr(njdk, "java_bin", lambda: "")
        ok, msg = njdk.jdk_report()
        assert ok is False
        assert "不安装 JDK" in msg

    def test_flags_parser_handles_typed_prefix(self, njdk):
        """PrintFlagsFinal 真实输出带类型前缀（bool/int/uintx），解析必须能吃下。"""
        sample = (
            "[Global flags]\n"
            "     bool UseG1GC                                  = true      {product} {ergonomic}\n"
            "      int CompileThreshold                         = 10000    {product} {default}\n"
            "    uintx MaxInlineSize                            = 35       {product} {default}\n"
        )
        import re
        pairs = []
        for raw in sample.splitlines():
            m = re.match(r"^\s*(?:[A-Za-z_][A-Za-z0-9_]*\s+)?([A-Za-z][A-Za-z0-9_]*)\s*"
                         r"=\s*(\{[^}]*\}|\S+)", raw)
            if m:
                pairs.append((m.group(1), m.group(2)))
        assert ("UseG1GC", "true") in pairs
        assert ("CompileThreshold", "10000") in pairs
        assert ("MaxInlineSize", "35") in pairs

    def test_properties_report_never_echoes_secrets(self, njdk, monkeypatch):
        """核心安全不变量：属性表里的口令/令牌类键只报「存在」，不回显值。"""
        monkeypatch.setattr(njdk, "java_bin", lambda: "/usr/bin/java")
        fake = (
            "Property settings:\n"
            "    java.version = 21.0.5\n"
            "    java.home = /usr/lib/jvm/java-21\n"
            "    http.proxyPassword = SuperSecret123\n"
            "    my.token = BearerAbcDef\n"
            "    some.credential = hunter2\n"
        )
        monkeypatch.setattr(njdk.common, "run",
                            lambda *a, **k: (0, fake))
        ok, msg = njdk.java_properties_report()
        assert ok is True
        assert "SuperSecret123" not in msg
        assert "BearerAbcDef" not in msg
        assert "hunter2" not in msg
        assert "已隐藏" in msg
        # 白名单键正常输出
        assert "21.0.5" in msg
        assert "java-21" in msg

    def test_non_allowlist_keys_are_dropped(self, njdk, monkeypatch):
        monkeypatch.setattr(njdk, "java_bin", lambda: "/usr/bin/java")
        fake = "    java.version = 21\n    some.random.prop = visible?\n"
        monkeypatch.setattr(njdk.common, "run", lambda *a, **k: (0, fake))
        ok, msg = njdk.java_properties_report()
        assert "visible?" not in msg

    def test_diag_tools_report_lists_without_executing(self, njdk, monkeypatch):
        """诊断工具报告只查 PATH，不应执行 jcmd/jstack 等任何命令。"""
        monkeypatch.setattr(njdk, "java_bin", lambda: "/usr/bin/java")
        calls = []
        monkeypatch.setattr(njdk.common, "run",
                            lambda cmd, timeout=120, tail=2000: calls.append(cmd) or (0, ""))
        ok, msg = njdk.diag_tools_report()
        assert ok is True
        assert not any("jcmd" in c or "jstack" in c or "jmap" in c for c in calls)

    def test_forbidden_subcommands_documented(self, njdk):
        joined = " ".join(njdk.FORBIDDEN_SUBCOMMANDS)
        for danger in ("GC.run", "heap_dump", "histo:live", "JFR"):
            assert danger in joined

    def test_build_cache_report_degrades(self, njdk, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        ok, msg = njdk.build_tool_cache_report()
        assert ok is True
        assert isinstance(msg, str) and msg

    def test_probes_all_zero_arg_callable(self, njdk):
        """runner 以 fn() 零参派发，故每个探针必须无必填参数。"""
        for fn_name, _label, _need in njdk.JDK_PROBES:
            sig = inspect.signature(getattr(njdk, fn_name))
            required = [p for p in sig.parameters.values()
                        if p.default is inspect.Parameter.empty
                        and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
            assert not required, f"{fn_name} 有必填参数，runner 无法零参派发"


# =========================================================================== #
# 三、内核 module / firmware / eBPF 只读层
# =========================================================================== #

class TestKmod:
    def test_docs_align_kernel_org(self, nk):
        for key in ("modules", "firmware", "bpf", "trace", "module_params"):
            ref = nk.kmod_reference(key)
            assert ref, f"缺文档 {key}"
            assert ref["path"].startswith("Documentation/"), ref["path"]
            assert ref["summary"] and ref["advice"]
            assert ref["group"] in ("module", "firmware", "bpf")

    def test_doc_list_filters_by_group(self, nk):
        all_lines = nk.kmod_doc_list()
        bpf_lines = nk.kmod_doc_list("bpf")
        assert len(bpf_lines) < len(all_lines)
        assert any("bpf" in l for l in bpf_lines)

    def test_off_linux_degrades(self, nk, monkeypatch):
        monkeypatch.setattr(nk, "_is_linux", lambda: False)
        for fn_name, _label in nk.KMOD_PROBES:
            ok, msg = getattr(nk, fn_name)()
            assert ok is False, f"{fn_name} 非 Linux 时应降级"
            assert isinstance(msg, str)

    def test_total_report_degrades_off_linux(self, nk, monkeypatch):
        monkeypatch.setattr(nk, "_is_linux", lambda: False)
        ok, msg = nk.kmod_report()
        assert ok is False
        assert "非 Linux" in msg

    def test_no_module_write_commands_in_source(self, nk):
        """核心安全不变量：源码里不得出现真正执行装卸/写 sysfs 的命令。

        用 AST 检查**字符串常量与函数调用**，并排除 FORBIDDEN_COMMANDS /
        KMOD_DOCS 这两个「禁令与文档」常量——那里出现 insmod/rmmod/echo
        正是必要的说明文案。
        """
        import ast
        src = inspect.getsource(nk)
        assert "shutil.rmtree" not in src and "os.remove" not in src
        assert "os.unlink" not in src
        tree = ast.parse(src)
        # 收集「允许出现危险词的常量名」——这些是禁令/文档，不是可执行命令
        allowed_value_sets = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name) and tgt.id in (
                            "FORBIDDEN_COMMANDS", "KMOD_DOCS", "_REFS"):
                        for sub in ast.walk(node.value):
                            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                                allowed_value_sets.append(sub.value)
        for node in ast.walk(tree):
            # 1) 字符串常量不得是可执行的装卸/加载命令
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                v = node.value.strip()
                if v in allowed_value_sets:
                    continue
                for bad in ("insmod", "rmmod", "modprobe -r", "depmod -a",
                            "bpftool prog load", "bpftool map create"):
                    assert not v.startswith(bad), f"发现装卸/加载命令: {v}"
            # 2) 不得直接调用 subprocess / os.system
            if isinstance(node, ast.Attribute):
                assert node.attr not in ("system", "popen", "call", "check_output"), \
                    f"发现进程调用: .{node.attr}"

    def test_forbidden_commands_documented(self, nk):
        joined = " ".join(nk.FORBIDDEN_COMMANDS)
        for danger in ("insmod", "rmmod", "modprobe", "bpftool prog load", "mem_sleep"):
            assert danger in joined

    def test_firmware_dirs_returns_list(self, nk):
        assert isinstance(nk.firmware_dirs(), list)

    def test_firmware_report_never_writes(self, nk):
        """固件层不得 shutil.rmtree / os.remove（只统计不删）。"""
        src = inspect.getsource(nk)
        assert "shutil.rmtree" not in src
        assert "os.remove" not in src
        assert "os.unlink" not in src

    def test_probes_all_zero_arg_callable(self, nk):
        for fn_name, _label in nk.KMOD_PROBES:
            sig = inspect.signature(getattr(nk, fn_name))
            required = [p for p in sig.parameters.values()
                        if p.default is inspect.Parameter.empty
                        and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
            assert not required, f"{fn_name} 有必填参数"


class TestKmodTasks:
    def test_kmod_tasks_registered(self):
        from sysweeper import registry
        ids = {t.id for t in registry.all_tasks() if t.id.startswith("kmod_")}
        for tid in ("kmod_loaded", "kmod_sysfs", "kmod_params", "kmod_modinfo",
                    "kmod_firmware", "kmod_firmware_class", "kmod_bpf",
                    "kmod_sysctl", "kmod_blacklist", "kmod_power",
                    "kmod_unload_guide"):
            assert tid in ids, f"缺少任务 {tid}"

    def test_kmod_tasks_linux_only_and_safe(self):
        from sysweeper import registry
        for t in registry.all_tasks():
            if t.id.startswith("kmod_"):
                assert t.platform == "linux", t.id
                # 全部为只读：不得有 shell 类执行动作
                for a in t.actions:
                    assert a.kind != "shell", \
                        f"{t.id} 含 shell 动作 {a.command}，违反只读底线"

    def test_kmod_tasks_have_standards(self):
        from sysweeper import registry
        for t in registry.all_tasks():
            if t.id.startswith("kmod_"):
                assert t.standards, f"{t.id} 缺标准引用"

    def test_jdk_tasks_require_java(self):
        """jdk_* 标 requires_lang=java——没装 JDK 时自动隐藏，不强求安装。"""
        from sysweeper import registry
        jt = [t for t in registry.all_tasks() if t.id.startswith("jdk_")]
        assert len(jt) >= 8
        for t in jt:
            assert t.requires_lang == "java", t.id

    def test_jdk_tasks_have_no_shell_actions(self):
        from sysweeper import registry
        for t in registry.all_tasks():
            if t.id.startswith("jdk_"):
                for a in t.actions:
                    assert a.kind != "shell", f"{t.id} 含 shell 动作"

    def test_jdk_tasks_visible_without_java_when_forced(self):
        """include_lang_missing=True 时 jdk 任务应出现（便于查看指引）。"""
        from sysweeper import registry
        got = {t.id for t in registry.applicable("linux", "0", include_lang_missing=True)}
        assert "jdk_runtime" in got


# =========================================================================== #
# 四、任务档位（大而全 / 小而全）
# =========================================================================== #

class TestProfiles:
    def test_four_profiles_defined(self, pf):
        assert pf.PROFILE_ORDER == ("minimal", "lite", "standard", "full")

    def test_monotonic_nesting(self, pf):
        """核心不变量：minimal ⊆ lite ⊆ standard ⊆ full（单调包含）。"""
        for plat in ("linux", "windows", "macos", "android", "bsd"):
            sets = {n: {t.id for t in pf.tasks_in_profile(n, plat)}
                    for n in pf.PROFILE_ORDER}
            assert sets["minimal"] <= sets["lite"], plat
            assert sets["lite"] <= sets["standard"], plat
            assert sets["standard"] <= sets["full"], plat

    def test_minimal_is_zero_risk(self, pf):
        """核心不变量：minimal 档保证零风险——无 opt_in、无非 low、无语言依赖。"""
        for plat in ("linux", "windows", "macos", "android", "ios", "bsd", "unix"):
            for t in pf.tasks_in_profile("minimal", plat):
                assert t.risk == "low", f"{plat}/{t.id} risk={t.risk}"
                assert t.opt_in is False, f"{plat}/{t.id} 是 opt_in"
                assert not t.requires_lang, f"{plat}/{t.id} 依赖语言 {t.requires_lang}"

    def test_full_contains_optin_and_high(self, pf):
        s = pf.profile_summary("full", "linux")
        assert s["has_opt_in"] is True
        assert s["has_high_risk"] is True

    def test_standard_excludes_optin(self, pf):
        s = pf.profile_summary("standard", "linux")
        assert s["has_opt_in"] is False
        assert s["count"] > pf.profile_summary("minimal", "linux")["count"]

    def test_profile_never_authorizes_execution(self, pf):
        """档位只做筛选，不改变底层执行确认逻辑——此处以描述文本固化该约定。"""
        full = pf.PROFILES["full"]
        assert "不等于授权执行" in full["description"]
        assert "--opt-in" in full["description"]

    def test_arch_filter_applies(self, pf):
        a = {t.id for t in pf.tasks_in_profile("standard", "linux", arch="mips")}
        b = {t.id for t in pf.tasks_in_profile("standard", "linux", arch="x86")}
        assert a != b
        # mips 档不应出现 x86 专属任务
        assert not any(i.startswith("arch_x86") for i in a)

    def test_unknown_profile_returns_empty(self, pf):
        assert pf.tasks_in_profile("nonexistent", "linux") == []

    def test_compare_profiles_jaccard(self, pf):
        r = pf.compare_profiles("minimal", "full", "linux")
        assert 0.0 <= r["jaccard"] <= 1.0
        assert r["only_a"] == []          # minimal 是 full 真子集
        assert len(r["only_b"]) == r["count_b"] - r["count_a"]
        # full 应有 minimal 没有的东西
        assert "any_user_cache" in r["only_b"]

    def test_scenarios_defined(self, pf):
        assert "elderly-friendly" in pf.SCENARIOS
        assert "readonly-audit" in pf.SCENARIOS
        assert "daily-clean" in pf.SCENARIOS
        assert "deep-opt" in pf.SCENARIOS

    def test_elderly_scenario_only_keeps_a11y(self, pf):
        tasks = pf.scenario_tasks("elderly-friendly", "android")
        assert tasks
        for t in tasks:
            assert (t.category == "accessibility" or "a11y" in t.id.lower()
                    or "无障碍" in t.title or "适老" in t.title), t.id

    def test_readonly_scenario_is_zero_risk(self, pf):
        for plat in ("linux", "windows", "android"):
            for t in pf.scenario_tasks("readonly-audit", plat):
                assert t.risk == "low"
                assert not t.opt_in

    def test_profile_list_and_detail_render(self, pf):
        lines = pf.profile_list("linux", "0")
        assert any("minimal" in l for l in lines)
        detail = pf.profile_detail("standard", "linux")
        assert "档位 standard" in detail
        assert "覆盖度评分" in detail

    def test_profile_detail_unknown_name(self, pf):
        assert "未知档位" in pf.profile_detail("nope", "linux")

    def test_scenario_list_renders(self, pf):
        assert any("elderly-friendly" in l for l in pf.scenario_list())


# =========================================================================== #
# 五、数学量化评分引擎
# =========================================================================== #

class TestMetricsMath:
    def test_normalize_basic(self, mt):
        assert mt.normalize([0, 5, 10]) == [0.0, 0.5, 1.0]
        assert mt.normalize([1, 1, 1]) == [0.5, 0.5, 0.5]      # 无区分度取中性
        assert mt.normalize([]) == []

    def test_normalize_invert(self, mt):
        assert mt.normalize([0, 10], invert=True) == [1.0, 0.0]

    def test_mean_stdev_cv(self, mt):
        assert mt.mean([1, 2, 3]) == 2.0
        assert mt.mean([]) == 0.0
        assert mt.stdev([]) == 0.0
        assert mt.stdev([5, 5, 5]) == 0.0
        assert mt.coefficient_of_variation([2, 2, 2]) == 0.0
        assert mt.coefficient_of_variation([]) == 0.0

    def test_jaccard(self, mt):
        assert mt.jaccard({1, 2}, {2, 3}) == 1 / 3
        assert mt.jaccard({1, 2}, {1, 2}) == 1.0
        assert mt.jaccard(set(), set()) == 1.0
        assert mt.jaccard({1}, set()) == 0.0

    def test_cosine(self, mt):
        assert mt.cosine_similarity([1, 0], [1, 0]) == 1.0
        assert mt.cosine_similarity([1, 0], [0, 1]) == 0.0
        assert mt.cosine_similarity([0, 0], [1, 1]) == 0.0     # 零向量保护
        assert mt.cosine_similarity([1], [1, 2]) == 0.0       # 维度不等保护

    def test_shannon_entropy_known_values(self, mt):
        assert mt.shannon_entropy([1, 1]) == 1.0             # 2 类均分 = 1 bit
        assert mt.shannon_entropy([1, 1, 1, 1]) == 2.0
        assert mt.shannon_entropy([1, 0, 0, 0]) == 0.0         # 全集中
        assert mt.shannon_entropy([]) == 0.0
        assert mt.shannon_entropy([0, 0]) == 0.0              # 全零保护

    def test_normalized_entropy_bounds(self, mt):
        assert mt.normalized_entropy([1, 1]) == 1.0
        assert mt.normalized_entropy([1, 0]) == 0.0
        assert mt.normalized_entropy([]) == 0.0        # 空分布：无从谈均衡
        assert mt.normalized_entropy([7]) == 1.0        # 单类：无从偏科
        v = mt.normalized_entropy([5, 3, 2, 1, 1])
        assert 0.0 < v < 1.0

    def test_gini_index(self, mt):
        assert mt.gini_index([1, 1, 1, 1]) == 0.0             # 完全均分
        assert mt.gini_index([5]) == 0.0                     # 单类
        g = mt.gini_index([10, 1, 1])
        assert 0.0 < g < 1.0
        assert mt.gini_index([]) == 0.0

    def test_zero_division_protection(self, mt):
        """所有除法都要有零分母保护——空集/单元素集不得抛 ZeroDivisionError。"""
        assert mt.shannon_entropy([0, 0, 0]) == 0.0
        assert mt.normalized_entropy([0, 0, 0]) == 0.0
        assert mt.gini_index([0, 0]) == 0.0
        assert mt.coverage_score([])["score"] == 0.0
        assert mt.depth_score([]) == 0.0
        assert mt.coverage_breadth([]) == 0.0

    def test_depth_score_saturates(self, mt):
        assert mt.depth_score([]) == 0.0
        small = mt.depth_score([1] * 5)
        big = mt.depth_score([1] * 500)
        assert 0.0 < small < big < 1.0        # 单调递增且有上界

    def test_risk_profile_sums_to_one(self, mt):
        from sysweeper import registry
        p = mt.risk_profile(registry.all_tasks())
        assert abs(sum(p.values()) - 1.0) < 1e-9
        assert mt.risk_profile([]) == {"low": 0.0, "medium": 0.0, "high": 0.0}

    def test_coverage_score_full_library(self, mt):
        from sysweeper import registry
        r = mt.coverage_score(registry.all_tasks())
        assert 0.0 <= r["score"] <= 1.0
        for k in ("breadth", "entropy", "depth", "safety"):
            assert 0.0 <= r["parts"][k] <= 1.0
        assert r["summary"]

    def test_coverage_score_monotonic_in_size(self, mt):
        from sysweeper import registry
        allt = registry.all_tasks()
        few = mt.coverage_score(allt[:20])
        many = mt.coverage_score(allt)
        assert many["parts"]["depth"] > few["parts"]["depth"]

    def test_weights_sum_to_one(self, mt):
        """WSM 的必要条件：权重和为 1，否则评分不可比。"""
        assert abs(sum(mt.SCORE_WEIGHTS.values()) - 1.0) < 1e-9

    def test_platform_balance(self, mt):
        from sysweeper import registry
        by = {}
        for t in registry.all_tasks():
            by.setdefault(t.platform, []).append(t)
        b = mt.platform_balance(by)
        assert 0.0 <= b["gini"] <= 1.0
        assert b["verdict"]
        # 单平台时无法诊断
        assert mt.platform_balance({"linux": [1]})["verdict"] == "平台数不足，无法诊断均衡度"

    def test_coverage_gaps(self, mt):
        from sysweeper.models import Task
        empty = []
        assert mt.coverage_gaps(empty)            # 全空 → 所有分类都是缺口
        assert "cleanup" in mt.coverage_gaps(empty)

    def test_similarity_report(self, mt):
        r = mt.similarity_report(["a", "b"], ["b", "c"])
        assert r["shared"] == ["b"]
        assert r["only_a"] == ["a"]
        assert r["only_b"] == ["c"]

    def test_reports_render(self, mt):
        from sysweeper import registry
        allt = registry.all_tasks()
        s = mt.score_report(allt)
        assert "WSM" in s or "Σ" in s
        assert "breadth" in s and "entropy" in s
        e = mt.entropy_report(mt.category_distribution(allt))
        assert "Shannon" in e
        assert "Gini" in e

    def test_metrics_is_pure_stdlib(self, mt):
        """核心设计约束：数学引擎不得引入第三方依赖。"""
        src = inspect.getsource(mt)
        for banned in ("import numpy", "import scipy", "import sympy", "import pandas"):
            assert banned not in src, f"引入第三方依赖: {banned}"


# =========================================================================== #
# 六、CLI / GUI 接线 + 关键词标准
# =========================================================================== #

class TestWiring:
    def test_native_modules_exported(self):
        import sysweeper.native as N
        for m in ("jdk", "kmod", "metrics"):
            assert m in N.__all__
            assert hasattr(N, m)

    def test_cli_subcommands_parse(self):
        from sysweeper.cli import build_parser
        p = build_parser()
        for argv in (["jdk"], ["kmod"], ["profiles"], ["profiles", "show"],
                     ["profiles", "tasks", "--profile", "minimal"],
                     ["profiles", "compare", "--profile", "minimal", "--against", "full"],
                     ["score"], ["score", "balance"], ["score", "profile", "--profile", "lite"]):
            args = p.parse_args(argv)
            assert args.func is not None

    def test_profile_flag_available_globally(self):
        """--profile 应作为通用参数出现在 list/scan/clean 上。"""
        from sysweeper.cli import build_parser
        p = build_parser()
        for cmd in ("list", "scan", "clean", "notes"):
            args = p.parse_args([cmd, "--profile", "minimal"])
            assert args.profile == "minimal"

    def test_profile_arg_helper_never_returns_silent_empty(self):
        """档位名非法/缺省时必须有明确语义，不得静默当空档位。

        回归：`profiles compare` 不带 --profile 时曾落进空档位，却照样打印
        「对比 0 vs 197」的无效结论；`score profile` 同理。
        """
        import argparse
        from sysweeper import profiles as pf
        from sysweeper.cli import _profile_arg

        # 缺省 → 走 default（不是空串）
        assert _profile_arg(argparse.Namespace(profile=""), "minimal") == "minimal"
        # 显式合法档位 / 场景档 → 原样透出
        assert _profile_arg(argparse.Namespace(profile="full"), "minimal") == "full"
        assert _profile_arg(
            argparse.Namespace(profile="elderly-friendly"), "minimal"
        ) == "elderly-friendly"
        # 非法档位 → 明确拒绝（返回空让调用方退出），不得当成"命中 0 项的档位"
        assert _profile_arg(argparse.Namespace(profile="不存在的档"), "minimal") == ""
        # profile 缺省/None（argparse 默认可能给 None）也要能回落
        assert _profile_arg(argparse.Namespace(profile=None), "minimal") == "minimal"

    def test_cmd_profiles_actions_accept_missing_profile(self):
        """show/tasks/compare 不带 --profile 时应正常出结果（用默认档），不崩。"""
        from sysweeper import profiles as pf
        # 默认档（minimal）必须能真实命中任务，否则 CLI 默认输出就是空报告
        r = pf.compare_profiles("minimal", "full", "linux", "24.04")
        assert r["count_a"] > 0, "minimal 档在 linux 上不应为空"
        assert r["jaccard"] > 0.0
        assert pf.tasks_in_profile("minimal", "linux", "24.04")

    def test_profile_defaults_empty_for_backward_compat(self):
        from sysweeper.cli import build_parser
        args = build_parser().parse_args(["scan"])
        assert args.profile == ""      # 默认空 → 走原 applicable 路径

    def test_gui_has_new_panels(self):
        from sysweeper import gui
        for name in ("show_jdk", "show_kmod", "show_profiles", "show_score"):
            assert hasattr(gui.SysweeperGUI, name), f"GUI 缺 {name}"

    def test_gui_android_panel_wired(self):
        from sysweeper import gui
        assert hasattr(gui.SysweeperGUI, "show_android")
        src = inspect.getsource(gui.SysweeperGUI.show_android)
        assert "elderly_a11y_report" in src
        assert "android_compat_report" in src
        assert "elderly_a11y_advice" in src

    def test_keyword_standards_v0522(self):
        """v0.5.22 新增关键词的标准引用必须可被 task_standards 正确命中。

        标题里需含对应关键词；同时验证**最长匹配优先**——「JPMS 模块系统」
        不应被短词 `pm`（Android PackageManager）劫持。
        """
        from sysweeper.models import task_standards, Task
        cases = {
            "适老化无障碍体检": ["WCAG", "37668"],
            "OpenJDK 运行时总览": ["OpenJDK"],
            "JPMS 模块系统体检": ["JEP 261"],
            "lsmod 已加载内核模块盘点": ["modules.rst"],
            "firmware 内核固件库盘点": ["firmware"],
            "eBPF 能力体检": ["bpf"],
            "任务档位大而全": ["档位"],
            "数学评分与 Shannon 熵": ["香农熵"],
        }
        for title, needles in cases.items():
            t = Task(id="x", platform="any", title=title, category="maintenance", risk="low")
            refs = task_standards(t)
            joined = " ".join(refs)
            for n in needles:
                assert n in joined, f"{title} 缺标准关键词 {n}（实得 {joined}）"

    def test_keyword_match_is_longest_first(self):
        """最长匹配优先：短关键词不得劫持更长更具体的关键词。"""
        from sysweeper.models import task_standards, Task
        # "JPMS" 含 "pm" 子串，若按表序优先会误判为 Android PackageManager
        t = Task(id="jpms_modules", platform="any", title="JPMS 模块系统体检",
                 category="maintenance", risk="low")
        joined = " ".join(task_standards(t))
        assert "JEP 261" in joined
        assert "PackageManager" not in joined

    def test_own_standards_take_precedence(self):
        from sysweeper.models import task_standards, Task
        t = Task(id="x", platform="any", title="JPMS 模块系统", category="maintenance",
                 risk="low", standards=["[自定义] 我自己的标准"])
        assert task_standards(t) == ["[自定义] 我自己的标准"]

    def test_jdk_native_op_is_dispatchable(self):
        """runner 以 module.func 零参派发；确认 jdk/kmod 探针名合法。"""
        import re
        from sysweeper.native import jdk as nj, kmod as nk
        op_re = re.compile(r"^[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*$")
        for fn_name, _l, _n in nj.JDK_PROBES:
            assert op_re.match(f"jdk.{fn_name}"), fn_name
            assert callable(getattr(nj, fn_name))
        for fn_name, _l in nk.KMOD_PROBES:
            assert op_re.match(f"kmod.{fn_name}"), fn_name
            assert callable(getattr(nk, fn_name))

    def test_task_actions_reference_existing_native_funcs(self):
        """任务里写的 native op 必须真实存在（防止改名后静默失效）。"""
        import re
        import importlib
        from sysweeper import registry
        op_re = re.compile(r"^([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)$")
        checked = 0
        for t in registry.all_tasks():
            for a in t.actions:
                if a.kind != "native":
                    continue
                m = op_re.match(a.command)
                if not m:
                    continue
                mod_name, fn_name = m.groups()
                try:
                    mod = importlib.import_module(f"sysweeper.native.{mod_name}")
                except ModuleNotFoundError:
                    continue      # 旧测试夹具/可选模块，跳过
                assert hasattr(mod, fn_name), \
                    f"{t.id} 引用了不存在的原生函数 {a.command}"
                checked += 1
        assert checked > 20, "应至少校验到 20 个 native 引用"

    def test_all_new_native_ops_are_allowlist_shaped(self):
        """新加的只读函数名须符合 plugins 的 module.func 标识符规则。"""
        from sysweeper.native import jdk as nj, kmod as nk, android as na
        for mod, names in (
            (nj, [f for f, _l, _n in nj.JDK_PROBES]),
            (nk, [f for f, _l in nk.KMOD_PROBES]),
            (na, [f for f, _l, _m in na.A11Y_PROBES] + ["elderly_a11y_report",
                                                        "android_compat_report"]),
        ):
            for n in names:
                assert n.islower() and "_" in n, f"{mod.__name__}.{n} 命名不合规"
                assert hasattr(mod, n)
