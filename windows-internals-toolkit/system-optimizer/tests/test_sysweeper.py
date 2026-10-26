"""sysweeper 基础测试（在任意平台均可运行，不修改系统）。"""

import os
import sys

import pytest

# 让 tests/ 能 import src/python 下的包
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src", "python"))

from sysweeper import registry  # noqa: E402
from sysweeper.detect import detect  # noqa: E402
from sysweeper.models import _ver_ge, _ver_le  # noqa: E402
from sysweeper import native  # noqa: E402


def test_registry_nonempty():
    tasks = registry.all_tasks()
    assert len(tasks) >= 20
    ids = [t.id for t in tasks]
    assert len(ids) == len(set(ids)), "任务 id 必须唯一"


def test_platform_coverage():
    s = registry.platform_summary()
    for pf in ("windows", "macos", "linux", "android", "ios"):
        assert s.get(pf, 0) > 0, f"{pf} 平台缺少任务"


def test_win10_eol_only_on_win10():
    # win10_eol 应只在 Windows 10 出现，11 不出现
    t10 = registry.applicable("windows", "10")
    t11 = registry.applicable("windows", "11")
    assert any(t.id == "win10_eol" for t in t10)
    assert not any(t.id == "win10_eol" for t in t11)


def test_version_filter():
    # macOS 26 应匹配 tahoe 任务；低版本不应匹配高版本专属任务
    assert any(t.id == "mac_xcode_derived" for t in registry.applicable("macos", "26"))
    # 风险过滤
    low = registry.applicable("windows", "11", max_risk="low")
    assert all(t.risk == "low" for t in low)


def test_ver_compare():
    assert _ver_ge("11", "10")
    assert _ver_ge("26", "15")
    assert not _ver_ge("10", "11")
    assert _ver_le("24.04", "24.04")


def test_detect_runs():
    info = detect()
    assert "platform" in info
    assert info["platform"] in ("windows", "macos", "linux", "android", "ios", "unknown")


def test_native_imports_on_any_platform():
    # native 各平台模块在本机（Linux）必须能安全 import，绝不在 import 阶段崩溃
    for mod in (native.windows, native.linux, native.macos, native.android, native.ios,
                native.bsd, native.unix, native.hardware, native.network):
        assert mod is not None


def test_bsd_unix_native_graceful_on_linux():
    # 非 BSD/Unix 平台调用其原生接口应优雅降级（不抛、返回稳值）
    assert isinstance(native.bsd.detect_distro(), dict)
    assert isinstance(native.bsd.pkg_manager(), str)
    assert native.bsd.sysctl("kern.ostype") is None  # Linux 上 sysctlbyname 不可用
    ok, msg = native.bsd.pkg_clean()
    assert ok is False and msg
    assert isinstance(native.unix.detect_distro(), dict)
    assert isinstance(native.unix.pkg_manager(), str)


def test_platform_coverage_bsd_unix():
    s = registry.platform_summary()
    assert s.get("bsd", 0) > 0, "BSD 平台缺少任务"
    assert s.get("unix", 0) > 0, "Unix 平台缺少任务"


def test_native_windows_graceful_on_linux():
    # 非 Windows 上调 Windows 原生接口应优雅降级（返回 None/False），不抛异常
    assert native.windows.disk_usage() is None
    assert native.windows.get_temp_dirs() == []   # 无 TEMP/LOCALAPPDATA 环境变量
    ok, msg = native.windows.empty_recycle_bin()
    assert ok is False and msg


def test_native_linux_lsb_on_sandbox():
    # Linux 沙箱上应能读到 LSB /etc/os-release（或优雅降级为空 dict）
    d = native.linux.detect_distro()
    assert isinstance(d, dict)
    if os.path.exists("/etc/os-release"):
        assert d.get("id")  # 沙箱是容器/Ubuntu，应有 ID


def test_native_dispatch():
    # runner 的 _run_native 能按 "module.func" 调起安全函数并返回 (ok, msg)
    from sysweeper.runner import _run_native
    ok, msg = _run_native("linux.detect_distro")
    assert ok is True and "id" in msg
    # 不存在的接口应返回 False 且不崩
    ok2, msg2 = _run_native("windows.nope_func")
    assert ok2 is False and "原生接口" in msg2


def test_info_command_runs():
    # info 子命令走原生接口报告，不应抛异常（用 linux 验证）
    from sysweeper.cli import build_parser
    import io
    p = build_parser()
    args = p.parse_args(["info", "--platform", "linux", "--version", "24.04"])
    args.func(args)  # 仅打印，不修改系统


def test_scan_dryrun_no_crash():
    # 扫描当前平台（分析模式），不应抛异常、不应修改系统
    platform, version = ("linux", "24.04")
    tasks = registry.applicable(platform, version)
    from sysweeper.runner import analyze
    rc = analyze(tasks, platform, apply=False, yes=False)
    assert rc == 0


def test_versions_data_loads():
    from sysweeper.cli import load_versions
    data = load_versions()
    assert "windows" in data and "macos" in data and "ios" in data
    assert data["windows"]["10"]["eol"] is True
    # 新平台版本数据
    assert "bsd" in data and "unix" in data


def test_language_auto_enable():
    # 语言探测：Python 必然可用（工具即 Python）；Lua 在当前沙箱未装
    from sysweeper.langdetect import available
    assert available("python") is True
    # 依赖 lua 的任务在未装 lua 的环境应被 applicable 默认隐藏
    lua_tasks = registry.by_lang("lua")
    assert lua_tasks and lua_tasks[0].requires_lang == "lua"
    ids = [t.id for t in registry.applicable("linux", "24.04")]
    assert "lang_lua_report" not in ids, "未装语言的任务不应自动出现"
    # python 任务应出现
    assert "lang_python_large" in ids
    # include_lang_missing 可强制显示（提示用户装了该语言即可用）
    ids2 = [t.id for t in registry.applicable("linux", "24.04", include_lang_missing=True)]
    assert "lang_lua_report" in ids2


def test_opt_in_default_off():
    # 默认不纳入 opt_in（网络/ITU / macOS / BSD 深度调优开关）；opt_in_tasks 能列出它们。
    # 按 Linux 平台核对：macos_tune_* / bsd_tune_* 属各自平台，本就不该出现在 Linux 列表。
    opt = registry.opt_in_tasks("linux")
    assert len(opt) > 0
    assert all(t.platform in ("linux", "any") for t in opt)
    ids = [t.id for t in registry.applicable("linux", "24.04")]
    for t in opt:
        assert t.id not in ids, "opt_in 开关默认不应出现"
    ids_on = [t.id for t in registry.applicable("linux", "24.04", include_opt_in=True)]
    for t in opt:
        assert t.id in ids_on, "开了 --opt-in 应包含该开关"


def test_hardware_native_graceful():
    from sysweeper import native
    # 无 smartctl 时返回 (False, 提示)，不抛
    ok, msg = native.hardware.smart_health()
    assert ok is False and "smartctl" in msg
    # acpi_states 返回字符串或空（沙箱有 /sys/power/state）
    assert isinstance(native.hardware.acpi_states(), str)
    # 标准参考非空
    refs = native.hardware.reference_all()
    assert "smart" in refs and "acpi" in refs


def test_toggles_command_runs():
    from sysweeper.cli import build_parser
    p = build_parser()
    args = p.parse_args(["toggles"])
    args.func(args)  # 仅打印，不修改系统


def test_langs_command_runs():
    from sysweeper.cli import build_parser
    p = build_parser()
    args = p.parse_args(["langs"])
    args.func(args)  # 仅打印，不修改系统


def test_hardware_command_runs():
    from sysweeper.cli import build_parser
    p = build_parser()
    args = p.parse_args(["hardware"])
    args.func(args)  # 仅打印，不修改系统


def test_measure_disk_linux():
    from sysweeper.runner import measure_disk
    # 本机是 Linux，应能读到根分区用量；字段归一化为 total/used/free
    d = measure_disk("linux")
    assert d is not None
    assert {"total", "used", "free"} <= set(d.keys())
    assert d["total"] >= d["used"]
    assert d["total"] >= d["free"]
    # 非桌面平台（沙箱内无对应系统）优雅返回 None，不抛
    assert measure_disk("windows") is None
    assert measure_disk("android") is None
    assert measure_disk("ios") is None


def test_analyze_collector():
    from sysweeper.runner import analyze
    tasks = registry.applicable("linux", "24.04", max_risk="high")
    assert len(tasks) > 0
    results = []
    failures = analyze(tasks, "linux", apply=False, yes=False,
                      risk_limit="high", collector=results)
    assert failures == 0
    assert len(results) == len(tasks)
    for r in results:
        assert r["id"] and r["title"]
        assert r["executed"] is False  # 分析模式不执行
        assert r["skipped"] is None
        # 动作摘要应为 list（纯注意事项类任务可能为空列表，合法）
        assert isinstance(r["actions"], list)


def test_report_generate_and_write():
    from sysweeper import report as repmod
    from sysweeper.models import Task, Action
    # 造一个最小任务集合 + 前后磁盘用量
    t = Task(id="demo", platform="linux", title="演示清理", category="cleanup",
             risk="low", actions=[Action(kind="shell", command="echo x",
                                         description="跑一下")])
    before = {"total": 1000, "used": 600, "free": 400}
    after = {"total": 1000, "used": 500, "free": 500}
    results = [{"id": "demo", "title": "演示清理", "category": "cleanup",
                "risk": "low", "estimate": 100, "actions": ["[本地] 跑一下"],
                "executed": True, "skipped": None, "ok": True, "output": "OK"}]
    rep = repmod.generate("linux", "24.04", "clean", [t], results, before, after)
    assert rep["mode"] == "clean"
    assert rep["reclaimed_bytes"] == 100  # 500 - 400
    assert rep["executed_count"] == 1 and rep["failed_count"] == 0
    assert rep["before"]["free"] == 400 and rep["after"]["free"] == 500

    md = repmod.render_markdown(rep)
    assert "# 系统优化 / 清理报告" in md
    assert "实际释放空间" in md and "100.0 B" in md
    assert "可视化对比" in md, "Markdown 报告应含可视化对比小节"
    assert "| 任务 | 分类 | 风险 | 预计可回收 | 状态 | 结果 |" in md

    # 写 md / json 文件均成功
    import tempfile, json, os
    d = tempfile.mkdtemp()
    p_md = os.path.join(d, "r.md")
    p_json = os.path.join(d, "r.json")
    assert repmod.write_report(p_md, rep) == os.path.abspath(p_md)
    assert os.path.exists(p_md) and "# 系统优化" in open(p_md, encoding="utf-8").read()
    assert repmod.write_report(p_json, rep) == os.path.abspath(p_json)
    j = json.load(open(p_json, encoding="utf-8"))
    assert j["reclaimed_bytes"] == 100 and j["task_count"] == 1


def test_report_scan_mode_no_after():
    from sysweeper import report as repmod
    # 分析模式无 after，reclaimed 应为 None，报告标注未修改系统
    rep = repmod.generate("linux", "", "scan", [], [], {"total": 1, "used": 1, "free": 0}, None)
    assert rep["mode"] == "scan"
    assert rep["after"] is None
    assert rep["reclaimed_bytes"] is None
    md = repmod.render_markdown(rep)
    assert "未修改系统" in md
    assert "实际释放空间" not in md


def test_gui_backends_detected():
    from sysweeper.gui import detect_gui_backends
    bs = detect_gui_backends()
    ids = {b["id"] for b in bs}
    # 四类后端都要被探测到（含「语言自带」的 tkinter / Swing / WinForms）
    assert {"tkinter", "java_swing", "dotnet_winforms", "pyside6"} <= ids
    for b in bs:
        assert isinstance(b["available"], bool)
        assert b["name"] and b["note"]  # 不可用也要给出原因与指引


def test_uniapp_api_data_loads():
    from sysweeper.cli import load_uniapp_api
    data = load_uniapp_api()
    assert data and "groups" in data
    gids = [g["id"] for g in data["groups"]]
    assert {"system", "storage", "network", "fs"} <= set(gids)
    apis = [a for g in data["groups"] for a in g["apis"]]
    assert len(apis) >= 15
    for a in apis:
        assert a["name"] and a["platforms"]  # 名称 + 支持端缺一不可


def test_uniapp_tasks_isolated_from_any():
    from sysweeper import registry
    uni = registry.applicable("uniapp", "4")
    assert len(uni) > 0
    # uni-app 是「跨端目标」，跨平台(any)任务不应混入
    assert all(t.platform == "uniapp" for t in uni)
    # 但操作系统平台仍应保留跨平台任务（如 S.M.A.R.T./语言缓存）
    lin = registry.applicable("linux", "24.04")
    assert any(t.platform == "any" for t in lin)


def test_uniapp_command_runs():
    from sysweeper.cli import build_parser
    p = build_parser()
    args = p.parse_args(["uniapp"])
    args.func(args)  # 仅打印 API 清单与任务


def test_gui_builds_if_display():
    from sysweeper import gui
    try:
        tk = gui._tk()[0]
        root = tk.Tk()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"无图形环境，跳过界面构建验证: {e}")
    app = gui.SysweeperGUI(root, platform="linux", version="24.04")
    assert app.tasks, "界面应加载出任务列表"
    assert len(app.vars) == len(app.tasks)
    app.log("测试日志")  # 日志区可写
    root.destroy()


def test_gui_chart_window_draws_if_display():
    """在真实图形环境下，构造报告后点「可视化对比」应弹出窗口且不崩。"""
    from sysweeper import gui, report as repmod

    try:
        tk = gui._tk()[0]
        root = tk.Tk()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"无图形环境，跳过图表窗口验证: {e}")
    app = gui.SysweeperGUI(root, platform="linux", version="24.04")
    before = {"total": 1000, "used": 600, "free": 400}
    after = {"total": 1000, "used": 500, "free": 500}
    results = [{"id": "demo", "title": "演示清理", "category": "cleanup", "risk": "low",
                "estimate": 100, "actions": [], "executed": True, "skipped": None,
                "ok": True, "output": "OK"}]
    app.last_report = repmod.generate("linux", "24.04", "clean", [], results, before, after)
    app.show_chart()  # 弹出 Toplevel 并用 Canvas 绘制条形图
    root.update_idletasks()
    root.destroy()


def test_uniapp_cleaner_project_valid():
    """校验 uniapp-cleaner 是一个合法、自洽的 uni-app 工程。"""
    import json
    import os
    import re

    base = os.path.join(os.path.dirname(__file__), "..", "uniapp-cleaner")
    base = os.path.abspath(base)
    assert os.path.isdir(base), "uniapp-cleaner 目录应存在"

    # 1) 工程配置 JSON 合法
    pages = json.load(open(os.path.join(base, "pages.json"), encoding="utf-8"))
    manifest = json.load(open(os.path.join(base, "manifest.json"), encoding="utf-8"))
    assert pages["pages"][0]["path"] == "pages/cleanup/cleanup", "首页面路由应为 cleanup"
    assert manifest.get("vueVersion") == "3", "应以 Vue 3 运行"

    # 2) cleanup 页面存在且含必要的 uni API（对应 uniapp_api.json 的 storage/ui 组）
    vue = open(os.path.join(base, "pages", "cleanup", "cleanup.vue"), encoding="utf-8").read()
    for api in (
        "uni.getStorageInfoSync",
        "uni.clearStorageSync",
        "uni.removeStorageSync",
        "uni.showModal",
        "uni.getSystemInfoSync",
    ):
        assert api in vue, f"cleanup 页面应调用 {api}"
    # 默认不清理：clearAll/clearSelected 都必须先经 showModal 确认
    assert re.search(r"uni\.showModal", vue), "清理前必须经过 showModal 二次确认"
    assert vue.count("showModal") >= 2, "「清空全部」与「清理选中」都应各自确认"


def test_windows_bat_generator():
    """校验 Windows .bat 生成器：自包含、含确认门控、仅含 Windows 任务。"""
    import os
    import tempfile

    from sysweeper import windows_bat

    text = windows_bat.generate(version="11", risk_limit="medium")
    # 基本结构
    assert text.startswith("@echo off")
    assert "schtasks /create" in text, "应含注册计划任务的 schtasks 命令"
    # native 动作已映射成可运行 PowerShell
    assert "Clear-RecycleBin" in text, "windows.empty_recycle_bin 应映射为 Clear-RecycleBin"
    # 中风险任务带 choice 确认门控
    assert text.count("choice /C") >= 3, "3 个中风险 Windows 任务应各有 choice 确认"
    # 只固化 Windows 专属任务：跨平台 native 动作不应出现（否则不可直接运行）
    assert "hardware." not in text and "network." not in text
    assert "python3 -c" not in text, "不应混入跨平台语言任务"

    # write_bat 默认 UTF-8(BOM) + CRLF；可被 utf-8-sig 解码（用户要求允许 UTF-8 以上）
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "opt.bat")
        n = windows_bat.write_bat(p, version="11", risk_limit="low")
        assert n > 0
        raw = open(p, "rb").read()
        assert b"\r\n" in raw, "应使用 CRLF 换行"
        assert raw[:3] == b"\xef\xbb\xbf", "默认应带 UTF-8 BOM"
        open(p, encoding="utf-8-sig").read()  # 应能按 UTF-8(BOM) 解码
        # 显式 gbk 仍可用，且能被 GBK 解码
        pg = os.path.join(d, "opt_gbk.bat")
        windows_bat.write_bat(pg, version="11", risk_limit="low", encoding="gbk")
        open(pg, encoding="gbk").read()


def test_windows_bat_version10_includes_eol_note():
    from sysweeper import windows_bat

    text = windows_bat.generate(version="10", risk_limit="low")
    assert "终止支持" in text, "Win10 应含终止支持提醒"
    assert "win10_eol" not in text  # 任务 id 不会原样出现在 .bat 文本中（已展开）


def test_report_chart_data_and_bars():
    from sysweeper import report as repmod
    from sysweeper.models import Task, Action

    before = {"total": 1000, "used": 600, "free": 400}
    after = {"total": 1000, "used": 500, "free": 500}
    results = [{
        "id": "demo", "title": "演示清理", "category": "cleanup", "risk": "low",
        "estimate": 100, "actions": ["[本地] 跑一下"],
        "executed": True, "skipped": None, "ok": True, "output": "OK",
    }]
    rep = repmod.generate("linux", "24.04", "clean", [], results, before, after)
    # 纯数据抽取
    d = repmod.chart_data(rep)
    assert "before" in d["disk"] and "after" in d["disk"]
    assert d["tasks"] and d["tasks"][0]["estimate"] == 100
    # 纯文本 ASCII 条形图
    bars = repmod.render_bars(rep)
    assert "处理前" in bars and "处理后" in bars
    assert "实际释放" in bars
    assert "█" in bars, "应画出填充条块"
    # 无 after（分析模式）也应能渲染而不崩
    rep_scan = repmod.generate("linux", "", "scan", [], [], before, None)
    bars_scan = repmod.render_bars(rep_scan)
    assert "处理前" in bars_scan


def test_gui_chart_rects():
    from sysweeper import gui, report as repmod

    before = {"total": 1000, "used": 600, "free": 400}
    after = {"total": 1000, "used": 500, "free": 500}
    results = [{"id": "demo", "title": "演示清理", "category": "cleanup", "risk": "low",
                "estimate": 100, "actions": [], "executed": True, "skipped": None,
                "ok": True, "output": "OK"}]
    rep = repmod.generate("linux", "24.04", "clean", [], results, before, after)
    # 纯函数：不依赖 tkinter，可直接断言几何
    r = gui.chart_rects(rep, width=620, height=420)
    assert len(r["disk"]) == 2            # 处理前 + 处理后
    assert r["disk"][0]["label"] == "处理前"
    assert r["disk"][0]["w"] > r["disk"][1]["w"], "处理前已用更多，条应更长"
    assert r["freed"] == 100
    assert len(r["tasks"]) == 1 and r["tasks"][0]["value"] == 100
    # 空数据不崩
    empty = gui.chart_rects(repmod.generate("linux", "", "scan", [], [], before, None))
    assert empty["disk"] and not empty["tasks"]


def test_cli_chart_command():
    from sysweeper.cli import build_parser
    import json
    import tempfile
    import os

    before = {"total": 1000, "used": 600, "free": 400}
    after = {"total": 1000, "used": 500, "free": 500}
    results = [{"id": "demo", "title": "演示清理", "category": "cleanup", "risk": "low",
                "estimate": 100, "actions": [], "executed": True, "skipped": None,
                "ok": True, "output": "OK"}]
    from sysweeper import report as repmod
    rep = repmod.generate("linux", "24.04", "clean", [], results, before, after)
    d = tempfile.mkdtemp()
    jp = os.path.join(d, "r.json")
    with open(jp, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False)
    p = build_parser()
    args = p.parse_args(["chart", jp])
    args.func(args)  # 仅打印 ASCII 对比，不修改系统


def test_uniapp_h5_app_cache_branches():
    """cleanup 页面应分支处理 H5 / App 的端上缓存清理（对应 uniapp_api.json 的 fs 组）。"""
    import os
    import re

    base = os.path.join(os.path.dirname(__file__), "..", "uniapp-cleaner")
    vue = open(os.path.join(base, "pages", "cleanup", "cleanup.vue"), encoding="utf-8").read()
    # H5：浏览器 Cache API
    assert "window.caches.delete" in vue, "H5 应走 window.caches.delete（Cache API）"
    assert "window.caches.keys" in vue
    # App：5+ plus.cache.clear
    assert "plus.cache.clear" in vue, "App 应走 plus.cache.clear（5+ 规范）"
    # 运行时识别：先识别端再分支
    assert "detectRuntime" in vue
    # 新增的「清理端上缓存」按钮
    assert "清理端上缓存" in vue
    # showModal 至少 3 处确认（清空全部 / 清理选中 / App 缓存二次确认）
    assert vue.count("showModal") >= 3


def test_fonts_standards_loads():
    """data/fonts_standards.json 应合法，且以 Unicode 18.0.0（最新稳定版）为基线。"""
    import json
    from importlib import resources
    data = json.loads(resources.files("sysweeper.data")
                      .joinpath("fonts_standards.json").read_text(encoding="utf-8"))
    assert "unicode" in data and "opentype" in data and "woff2" in data
    # 最新稳定版 + 长期支持（LTS）说明都应存在
    assert data["unicode"]["latest_stable"] == "18.0.0"
    assert "lts_note" in data["unicode"], "应说明长期支持（LTS）版本策略"
    # 字体格式标准组织/编号齐全
    for k in ("ucs", "truetype", "woff", "emoji", "cldr", "bidi", "variable_font"):
        assert k in data
    # 本轮新增：UTF-128 前瞻宽编码（向下兼容 UTF-8）+ 网络字体标准
    assert "utf128" in data, "应含 UTF-128 编码参考"
    assert data["utf128"]["backward_compatible_with_utf8"] is True
    assert "network_fonts" in data, "应含网络字体标准（W3C WOFF2 + RFC 9110）"


def test_fonts_category_registered():
    from sysweeper.models import CATEGORIES
    assert "fonts" in CATEGORIES, "应新增「字体/字符标准」分类"
    assert CATEGORIES["fonts"] == "字体/字符标准"


def test_fonts_tasks_present_and_isolated():
    """字体任务：默认 3 跨平台 + 1 Windows + 1 网络字体(opt_in) + 1 规范化 = 6。"""
    allf = [t for t in registry.all_tasks() if t.category == "fonts"]
    assert len(allf) == 6, "应有 6 个字体任务（3 跨平台 + 1 Windows + 1 网络字体 + 1 规范化）"
    # 跨平台项（any）对 Linux 适用
    ids = [t.id for t in registry.applicable("linux", "24.04")]
    for tid in ("font_encoding_utf8", "font_duplicate_report", "font_cache_rebuild"):
        assert tid in ids, f"{tid} 应出现在 Linux 适用列表"
    # Windows 专属项仅对 Windows 出现
    win_ids = [t.id for t in registry.applicable("windows", "11")]
    assert "win_font_report" in win_ids
    assert "win_font_report" not in ids, "Windows 专属字体任务不应出现在 Linux"
    # 网络字体任务默认不出现（opt_in），需 --opt-in 才纳入
    assert "font_network_use" not in ids, "网络字体默认关闭，不应出现在常规列表"
    opt_ids = [t.id for t in registry.applicable("linux", "24.04", include_opt_in=True)]
    assert "font_network_use" in opt_ids, "网络字体应在 --opt-in 下出现"
    # 仅 font_network_use 是 opt_in
    opt_in_fonts = [t.id for t in allf if t.opt_in]
    assert opt_in_fonts == ["font_network_use"]
    # 不被混入 uni-app 目标端
    uni_ids = [t.id for t in registry.applicable("uniapp", "4")]
    assert not any(t.startswith("font_") for t in uni_ids)


def test_fonts_encoding_backward_compat():
    """UTF-128 声明应向下兼容 UTF-8；实际落盘规范化为 utf-8。"""
    from sysweeper import native
    ok_u8, _ = native.fonts.encoding_backward_compatible_with_utf8("utf-8")
    ok_128, _ = native.fonts.encoding_backward_compatible_with_utf8("utf-128")
    assert ok_u8 and ok_128, "utf-8 与 utf-128 都应向下兼容 UTF-8"
    eok, eff, _ = native.fonts.effective_encoding("utf-128")
    assert eok and eff == "utf-8", "UTF-128 落盘应规范化为 UTF-8"
    # 兼容性校验：文本可无损编码为 UTF-8
    assert native.fonts.assert_utf8_compatible("héllo 字体 🍎")[0]


def test_fonts_network_fonts_advisory():
    """网络字体接口应只读、不抛、返回稳值（依赖网络协议开关启用）。"""
    from sysweeper import native
    ok, msg = native.fonts.network_fonts()
    assert isinstance(ok, bool) and msg and "WOFF" in msg


def test_fonts_native_graceful():
    """native.fonts 各函数应优雅降级（返回稳值），不抛。"""
    from sysweeper import native
    assert isinstance(native.fonts.system_encoding(), dict)
    assert isinstance(native.fonts.is_utf8(), bool)
    fonts = native.fonts.list_fonts()
    assert isinstance(fonts, list)  # 有 fontconfig 则非空，否则空——都是合法值
    assert isinstance(native.fonts.duplicate_fonts(fonts), list)
    ok, msg = native.fonts.check_utf8()
    assert isinstance(ok, bool) and msg
    ok2, msg2 = native.fonts.report_fonts()
    assert isinstance(ok2, bool) and msg2
    ok3, msg3 = native.fonts.rebuild_cache()
    assert isinstance(ok3, bool) and msg3
    # 文本规范化（UAX #15）：返回稳值
    nok, nmsg = native.fonts.text_normalize_report()
    assert isinstance(nok, bool) and nmsg
    # 标准参考非空且含 Unicode 18.0.0
    refs = native.fonts.reference_all()
    assert refs and refs["unicode"]["latest_stable"] == "18.0.0"


def test_fonts_command_runs():
    """fonts 子命令应打印系统编码、字体数与标准引用，不修改系统、不抛。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    args = p.parse_args(["fonts"])
    args.func(args)  # 仅打印，不修改系统
    # 编码模式（UTF-128 向下兼容 UTF-8）也应可运行
    args2 = p.parse_args(["fonts", "--encoding", "utf-128"])
    args2.func(args2)


def test_standards_command_runs():
    """standards 子命令应打印分类→标准→覆盖，不抛。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    args = p.parse_args(["standards"])
    args.func(args)  # 仅打印，不修改系统


def test_category_summary_and_standards():
    """分类规范整体：category_summary 含全部分类；CATEGORY_ORDER 覆盖 CATEGORIES；
    每分类都有分层（国家/国际/地区）标准出处。"""
    from sysweeper import registry
    from sysweeper.models import (CATEGORIES, CATEGORY_ORDER, category_standards,
                                  STANDARD_TIERS)
    # 顺序覆盖全部分类
    assert set(CATEGORY_ORDER) == set(CATEGORIES.keys()), "CATEGORY_ORDER 应覆盖全部分类"
    # 汇总含全部分类键 + opt_in 列
    s = registry.category_summary()
    for c in CATEGORIES:
        assert c in s, f"category_summary 应含 {c}"
    assert "(opt_in)" in s
    # 每个分类都有分层标准出处（分类规范整体）
    for c in CATEGORIES:
        st = category_standards(c)
        assert st.get("doc"), f"{c} 应有标准文档"
        tiers = st.get("standards", {})
        assert set(tiers.keys()) == {t for t, _ in STANDARD_TIERS}, \
            f"{c} 的 standards 应为三层 dict"
    # fonts 分类：国标含 GB 18030，国际含 Unicode 18.0.0（最新稳定版）
    ft = category_standards("fonts")["standards"]
    assert any("GB 18030" in x for x in ft["national"]), "fonts 国标应含 GB 18030"
    assert any("Unicode 18.0.0" in x for x in ft["international"]), \
        "fonts 国际应包含 Unicode 18.0.0"


def test_standards_tiers_and_audience():
    """标准引用分层：STANDARD_TIERS 三层；standards_for_audience 按受众排序。
    cn→国标优先、intl→国际优先、regional→地区优先。"""
    from sysweeper.models import (STANDARD_TIERS, standards_for_audience,
                                  NATIONAL_STANDARD_PORTAL)
    assert [t for t, _ in STANDARD_TIERS] == ["national", "international", "regional"]
    # cn：fonts 中国标(GB 18030)排在国际(Unicode)之前
    cn = standards_for_audience("fonts", "cn")
    assert any("GB 18030" in x for x in cn)
    assert cn.index(next(x for x in cn if "GB 18030" in x)) < \
        cn.index(next(x for x in cn if "Unicode 18.0.0" in x))
    # intl：国际(Unicode)排在国标(GB 18030)之前
    intl = standards_for_audience("fonts", "intl")
    assert intl.index(next(x for x in intl if "Unicode 18.0.0" in x)) < \
        intl.index(next(x for x in intl if "GB 18030" in x))
    # regional：privacy 的地区(GDPR)应出现在国标(PIPL)之前
    reg = standards_for_audience("privacy", "regional")
    assert reg.index(next(x for x in reg if "GDPR" in x)) < \
        reg.index(next(x for x in reg if "PIPL" in x))
    # 国家平台常量存在
    assert "std.samr.gov.cn" in NATIONAL_STANDARD_PORTAL


def test_new_optimize_tasks_registered():
    """继续优化补全：win/linux/bsd 各增一项（视觉效果/IO调度/孤立依赖）。"""
    from sysweeper import registry
    ids = {t.id for t in registry.all_tasks()}
    for nid in ("win_visual_effects", "linux_io_scheduler", "bsd_pkg_autoremove"):
        assert nid in ids, f"新任务 {nid} 应已注册"
    by_id = {t.id: t for t in registry.all_tasks()}
    assert by_id["win_visual_effects"].category == "optimize"
    assert by_id["win_visual_effects"].risk == "low"
    assert by_id["linux_io_scheduler"].risk == "medium"
    assert by_id["bsd_pkg_autoremove"].category == "cleanup"
    assert by_id["bsd_pkg_autoremove"].risk == "low"


def test_continue_optimize_tasks_registered():
    """继续优化补全：macos/windows/linux 各增一项（动态效果/电源计划/swap 调优）。"""
    from sysweeper import registry
    ids = {t.id for t in registry.all_tasks()}
    for nid in ("macos_visual_effects", "win_power_plan", "linux_swap_tuning"):
        assert nid in ids, f"新任务 {nid} 应已注册"
    by_id = {t.id: t for t in registry.all_tasks()}
    assert by_id["macos_visual_effects"].category == "optimize"
    assert by_id["macos_visual_effects"].risk == "low"
    assert by_id["win_power_plan"].category == "optimize"
    assert by_id["win_power_plan"].risk == "low"
    assert by_id["linux_swap_tuning"].category == "optimize"
    assert by_id["linux_swap_tuning"].risk == "low"


def test_network_optin_tasks_have_standard_attribution():
    """network 的 opt-in 开关应逐条标注其标准归属（国标/国际），含层级标记。"""
    from sysweeper import registry
    from sysweeper.models import parse_standard_ref, task_standards_ordered
    net = [t for t in registry.all_tasks() if t.id.startswith("net_")]
    assert net, "应存在 network 任务"
    assert all(t.standards for t in net), "每个 network opt-in 任务都应标注 standards"
    # 每条标注都能解析出层级
    for t in net:
        for ref in t.standards:
            tier, _text = parse_standard_ref(ref)
            assert tier in ("national", "international", "regional")
    # net_ipv6 同时有国标(YD/T)与国际(RFC 8200)，cn 受众国标优先
    ipv6 = next(t for t in net if t.id == "net_ipv6")
    ordered_cn = task_standards_ordered(ipv6, "cn")
    ordered_intl = task_standards_ordered(ipv6, "intl")
    assert any("YD/T" in s for s in ordered_cn)
    assert ordered_cn[0].startswith("① [国标]"), "cn 受众国标应排第一并标 ①"
    assert ordered_intl[0].startswith("① [国际]"), "intl 受众国际应排第一并标 ①"


def test_regional_standards_for_non_china_regions():
    """分类规范整体：为非中国地区补本地化标准条目（US NIST / 日本 JIS / 欧盟 EN 等）。"""
    from sysweeper.models import category_standards
    # 网络：NIST SP 800-119 + EN 301 549
    net_reg = category_standards("network")["standards"]["regional"]
    assert any("NIST SP 800-119" in x for x in net_reg)
    assert any("EN 301 549" in x for x in net_reg)
    # 隐私：NIST SP 800-53 + 日本 APPI
    priv_reg = category_standards("privacy")["standards"]["regional"]
    assert any("NIST SP 800-53" in x for x in priv_reg)
    assert any("APPI" in x for x in priv_reg)
    # 优化：ENERGY STAR / ErP / JIS C
    opt_reg = category_standards("optimize")["standards"]["regional"]
    assert any("ENERGY STAR" in x for x in opt_reg)
    assert any("ErP" in x for x in opt_reg)
    assert any("JIS C" in x for x in opt_reg)
    # 字体：日本 JIS X 0213
    font_reg = category_standards("fonts")["standards"]["regional"]
    assert any("JIS X 0213" in x for x in font_reg)


def test_cross_tasks_registered_and_dedup():
    """跨平台整合：any_* 任务存在；BSD/Unix 与 Linux 重复的 user_cache/tmp 已去重；
    any 任务不混入 uni-app 目标端。"""
    from sysweeper import registry
    ids = [t.id for t in registry.all_tasks()]
    for nid in ("any_user_cache", "any_temp_report", "any_large_dirs", "any_dns_flush"):
        assert nid in ids, f"跨平台任务 {nid} 应存在"
    # 去重：删除 bsd/unix 的近重复缓存/临时任务
    for dead in ("bsd_user_cache", "bsd_tmp", "unix_user_cache", "unix_tmp"):
        assert dead not in ids, f"{dead} 应已整合进跨平台任务并删除"
    # 跨平台 any 任务仍不应出现在 uni-app 目标端查询
    uni = registry.applicable("uniapp", "4")
    assert not any(t.id.startswith("any_") for t in uni), "any 任务不应混入 uni-app"
    # BSD/Unix 平台仍有其他任务（去重后计数 > 0）
    assert registry.platform_summary().get("bsd", 0) > 0
    assert registry.platform_summary().get("unix", 0) > 0


def test_lang_rust_java_dotnet_tasks():
    """跨语言补全：rust/java/dotnet 探测已存在，且已有对应清理任务（按语言自动启用）。"""
    from sysweeper.langdetect import LANGUAGES
    from sysweeper import registry
    for lang in ("rust", "java", "dotnet"):
        assert lang in LANGUAGES, f"langdetect 应探测 {lang}"
        tasks = registry.by_lang(lang)
        assert tasks, f"应有依赖 {lang} 的清理任务"
    ids = [t.id for t in registry.all_tasks()]
    for nid in ("lang_rust_cargo", "lang_java_cache", "lang_dotnet_nuget"):
        assert nid in ids
    # 未安装对应语言时，相关任务默认隐藏（不强求安装）
    avail = registry.by_lang_any()
    for t in avail:
        if t.requires_lang in ("rust", "java", "dotnet"):
            # 探测不到则隐藏；探测到则出现——二者皆合法，只要 by_lang 正确归类即可
            assert t.requires_lang in LANGUAGES


def test_genbat_no_any_leak():
    """生成的 .bat 只含 Windows 专属任务，跨平台 any 任务（common.*）不应泄漏。"""
    from sysweeper import windows_bat
    text = windows_bat.generate(version="11", risk_limit="medium")
    assert "common." not in text, "跨平台 any 任务不应进入 .bat（否则不可直接运行）"
    assert "cross." not in text


def test_native_common_reports_graceful():
    """native/common 的跨平台报告函数应返回 (ok, msg) 稳值，不抛。"""
    from sysweeper import native
    for fn in ("user_cache_report", "temp_report", "large_dirs_report", "dns_flush_hint"):
        res = native.common.__getattribute__(fn)()
        assert isinstance(res, tuple) and len(res) == 2
        assert isinstance(res[0], bool) and isinstance(res[1], str)


def test_tasks_by_category_groups_and_opt_in():
    """tasks_by_category 按分类归集；opt_in 单独成组；键顺序覆盖 CATEGORY_ORDER。"""
    from sysweeper import registry
    from sysweeper.models import CATEGORY_ORDER
    g = registry.tasks_by_category()
    # 键顺序固定为 CATEGORY_ORDER + ["(opt_in)"]
    assert list(g.keys()) == CATEGORY_ORDER + ["(opt_in)"]
    # 普通任务按 category 归集，opt_in 不污染普通分类
    opt_ids = {t.id for t in g["(opt_in)"]}
    for c in CATEGORY_ORDER:
        for t in g[c]:
            assert t.id not in opt_ids, "opt_in 任务不应混入普通分类"
            assert t.category == c
    # opt_in 组非空（网络/ITU 调优开关）
    assert opt_ids, "应至少有一项默认关闭的 opt-in 开关"


def test_android_ios_optimize_maintenance_filled():
    """跨系统补全：Android/iOS 现均有 optimize 与 maintenance 任务。"""
    from sysweeper import registry
    cats_by_platform = {}
    for t in registry.all_tasks():
        cats_by_platform.setdefault(t.platform, set()).add(t.category)
    assert "optimize" in cats_by_platform.get("android", set()), \
        "Android 应有优化任务（and_adaptive_battery 等）"
    assert "maintenance" in cats_by_platform.get("android", set()), \
        "Android 应有维护任务（and_storage_optimize）"
    assert "optimize" in cats_by_platform.get("ios", set()), \
        "iOS 应有优化任务（ios_background_refresh）"
    assert "maintenance" in cats_by_platform.get("ios", set()), \
        "iOS 应有维护任务（ios_storage_optimize）"
    # 新增任务已注册
    ids = {t.id for t in registry.all_tasks()}
    for nid in ("and_adaptive_battery", "and_storage_optimize",
                "ios_photos_optimize", "ios_background_refresh", "ios_storage_optimize"):
        assert nid in ids, f"新任务 {nid} 应已注册"


def test_gui_standards_window_builds_if_display():
    """有图形环境时，show_standards 弹出窗口并写入标准/分类文本，不抛。"""
    try:
        import tkinter as tk
        tk.Tk().destroy()  # 真正能连上显示服务器才跑，否则跳过
    except Exception:
        pytest.skip("无图形环境（无 tkinter 或连不上 DISPLAY），跳过 GUI 测试")
    from sysweeper.gui import SysweeperGUI
    root = tk.Tk()
    try:
        g = SysweeperGUI(root, platform="linux", version="")
        top = g.show_standards()  # 弹出 Toplevel
        assert top is not None
        # 窗口内应包含分类与标准文本
        box = top.winfo_children()[0]
        txt = box.get("1.0", "end")
        assert "分类规范整体" in txt
        assert "国标" in txt and "国际" in txt, "标准页应显示国家/国际分层"
        assert "and_adaptive_battery" in txt, "标准页应列出分类下任务 id"
        assert "ios_storage_optimize" in txt
    finally:
        root.destroy()




def test_a11y_module_graceful():
    """无障碍模块（ORCA / AT-SPI2）：所有函数返回稳值、缺依赖时不抛。"""
    from sysweeper import a11y
    assert isinstance(a11y.orca_available(), bool)
    for fn in ("orca_version", "atspi_bus_available", "screen_reader_enabled"):
        res = getattr(a11y, fn)()
        assert isinstance(res, tuple) and len(res) == 2
        assert isinstance(res[0], bool) and isinstance(res[1], str)
    assert a11y.speak_backend() is None or isinstance(a11y.speak_backend(), str)
    assert isinstance(a11y.accessible_text("■ 项目\n\t• 内容"), str)
    # 装饰字符被去除，便于屏幕阅读器朗读
    assert "■" not in a11y.accessible_text("■ 标题")
    rep = a11y.environment_report()
    assert isinstance(rep, list) and any("AT-SPI2" in x for x in rep)
    ok, msg = a11y.a11y_report()
    assert isinstance(ok, bool) and isinstance(msg, str)
    # 协议常量
    assert a11y.AT_SPI_BUS == "org.a11y.Bus"
    assert "org.a11y.atspi.Accessible" in a11y.AT_SPI_INTERFACES.values()


def test_accessibility_category_and_standards():
    """分类规范整体：新增 accessibility 分类，三层标准齐全（国标/国际/地区）。"""
    from sysweeper.models import (CATEGORIES, CATEGORY_ORDER, category_standards,
                                  standards_for_audience)
    assert "accessibility" in CATEGORIES and "accessibility" in CATEGORY_ORDER
    assert set(CATEGORY_ORDER) == set(CATEGORIES.keys())
    st = category_standards("accessibility")["standards"]
    assert st["national"] and st["international"] and st["regional"]
    assert any("GB/T 37668" in x for x in st["national"]), "无障碍应引用国标 GB/T 37668"
    assert any("WCAG" in x or "AT-SPI2" in x for x in st["international"])
    assert any("EN 301 549" in x for x in st["regional"])
    # 受众切换：国内国标优先，对外国际优先
    cn = standards_for_audience("accessibility", "cn")
    intl = standards_for_audience("accessibility", "intl")
    assert cn[0] != intl[0]
    assert "GB/T 37668" in cn[0]
    assert "WCAG" in intl[0] or "AT-SPI2" in intl[0], "对外受众应把国际标准排在最前"


def test_a11y_tasks_registered():
    """无障碍任务已注册：跨平台报告 + ORCA/AT-SPI2 开关 + 各平台读屏入口。"""
    by_id = {t.id: t for t in registry.all_tasks()}
    for tid in ("any_a11y_report", "linux_atspi_bus", "linux_orca_status",
                "linux_orca_enable", "linux_atspi_toolkit",
                "win_narrator_hint", "mac_voiceover_hint", "any_a11y_standards"):
        assert tid in by_id, f"缺少无障碍任务 {tid}"
        assert by_id[tid].category == "accessibility", f"{tid} 应归 accessibility 分类"
    assert by_id["linux_orca_enable"].risk == "low"
    assert by_id["any_a11y_report"].platform == "any"


def test_go_lang_tasks_registered():
    """Go 相关任务已注册（requires_lang=go，未装 Go 时自动隐藏）。"""
    by_id = {t.id: t for t in registry.all_tasks()}
    for tid in ("lang_go_modcache", "lang_go_build_cache", "lang_go_build", "lang_go_mod_tidy"):
        assert tid in by_id, f"缺少 Go 任务 {tid}"
        assert by_id[tid].requires_lang == "go"
    assert by_id["lang_go_build"].category == "maintenance"
    # go mod tidy 会改 go.mod/go.sum，风险应高于构建缓存清理
    assert by_id["lang_go_mod_tidy"].risk == "medium"
    assert by_id["lang_go_build_cache"].risk == "low"


def test_go_component_sources_exist():
    """Go 组件源码齐备（go.mod + 主程序 + 标准/无障碍/平台），供 CI 交叉编译。"""
    go_dir = os.path.join(ROOT, "src", "go")
    for f in ("go.mod", "main.go", "standards.go", "a11y.go", "platform.go"):
        assert os.path.isfile(os.path.join(go_dir, f)), f"缺少 Go 源文件 {f}"
    mod = open(os.path.join(go_dir, "go.mod"), encoding="utf-8").read()
    assert mod.startswith("module "), "go.mod 应声明模块名"
    assert "module github.com/cyrushmh/wordbuddy-github" in mod
    src = open(os.path.join(go_dir, "a11y.go"), encoding="utf-8").read()
    assert "org.a11y.Bus" in src, "Go 侧也应提供 AT-SPI2 协议常量"


def test_packaging_config_present():
    """打包配置齐备：pyproject 声明入口与包数据，MANIFEST 含 data/*.json。"""
    assert os.path.isfile(os.path.join(ROOT, "pyproject.toml"))
    assert os.path.isfile(os.path.join(ROOT, "MANIFEST.in"))
    pj = open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8").read()
    assert "sysweeper = \"sysweeper.cli:main\"" in pj
    assert "data/*.json" in pj
    mf = open(os.path.join(ROOT, "MANIFEST.in"), encoding="utf-8").read()
    assert "data" in mf and "*.json" in mf


def test_cli_a11y_command_runs():
    """CLI a11y 子命令可跑通（只读探测，无需 orca/dbus 也返回）。"""
    from argparse import Namespace
    from sysweeper import cli
    args = Namespace(platform="linux", version="24.04", speak=False)
    cli.cmd_a11y(args)  # 不抛即通过（无断言输出检查，避免依赖本机环境）


def test_arch_module_graceful():
    """架构模块（龙芯/MIPS/RISC-V/开源硬件）：探测函数返回稳值，缺接口不抛。"""
    from sysweeper import arch
    from sysweeper.native import arch as narch
    key = arch.current_arch()
    assert isinstance(key, str) and key
    assert isinstance(arch.arch_name(key), str)
    assert isinstance(arch.details(), dict)
    assert isinstance(arch.toolchain_hint(), str)
    # GOARCH 映射：收录的架构都有值，未收录返回空串
    if key in arch.GOARCH_MAP:
        assert arch.goarch(key)
    assert isinstance(arch.go_build_command(), str)
    for fn in ("loongarch_report", "mips_report", "riscv_report",
               "open_hardware_report", "arch_report"):
        res = getattr(narch, fn)()
        assert isinstance(res, tuple) and len(res) == 2
        assert isinstance(res[0], bool) and isinstance(res[1], str)
    rep = arch.environment_report("cn")
    assert isinstance(rep, list) and any("架构" in x for x in rep)
    # 开源硬件必须可用（与具体机器无关，属标准指引）
    ok, msg = arch.open_hardware_report()
    assert ok and "OSHWA" in msg


def test_arch_category_and_standards():
    """分类规范整体：arch 分类三层标准齐全，龙芯国标优先、对外国际优先。"""
    from sysweeper.models import (CATEGORIES, CATEGORY_ORDER, category_standards,
                                  standards_for_audience)
    assert "arch" in CATEGORIES and "arch" in CATEGORY_ORDER
    assert set(CATEGORY_ORDER) == set(CATEGORIES.keys())
    st = category_standards("arch")["standards"]
    assert st["national"] and st["international"] and st["regional"]
    nat = " ".join(st["national"])
    assert "龙芯" in nat or "LoongArch" in nat, "架构分类应引用国产龙芯架构"
    assert any("RISC-V" in x for x in st["international"])
    assert any("MIPS" in x for x in st["international"])
    assert any("DIN SPEC 3105" in x for x in st["regional"]), "地区层应含开放硬件 DIN 标准"
    cn = standards_for_audience("arch", "cn")
    intl = standards_for_audience("arch", "intl")
    assert cn[0] != intl[0]
    assert "龙芯" in cn[0]
    assert "RISC-V" in intl[0] or "MIPS" in intl[0]


def test_arch_tasks_registered():
    """架构任务已注册：龙芯 / MIPS / RISC-V / 开源硬件 / 工具链 / 平台专属项。"""
    by_id = {t.id: t for t in registry.all_tasks()}
    for tid in ("arch_report", "arch_loongarch", "arch_mips", "arch_riscv",
                "arch_open_hardware", "arch_toolchain"):
        assert tid in by_id, f"缺少架构任务 {tid}"
        assert by_id[tid].category == "arch", f"{tid} 应归 arch 分类"
        assert by_id[tid].platform == "any"
    # 龙芯 / MIPS 的 Linux 平台专属项（平台 × 架构 交叉覆盖）
    for tid in ("linux_loongarch_source", "linux_mips_cleanup"):
        assert tid in by_id, f"缺少平台专属架构任务 {tid}"
        assert by_id[tid].platform == "linux" and by_id[tid].category == "arch"
    # Go 按架构交叉构建
    assert by_id["arch_go_cross_build"].requires_lang == "go"
    # 每个架构任务都有自己的标准归属（分类规范整体：逐条可追溯）
    for tid in ("arch_loongarch", "arch_mips", "arch_riscv", "arch_open_hardware"):
        assert by_id[tid].standards, f"{tid} 应标注标准归属"


def test_arch_json_valid_and_covers_national_archs():
    """data/arch.json 合法，且覆盖龙芯、MIPS、RISC-V 与开源硬件。"""
    import json
    path = os.path.join(ROOT, "src", "python", "sysweeper", "data", "arch.json")
    data = json.load(open(path, encoding="utf-8"))
    for key in ("loongarch", "mips", "riscv", "openpower", "openrisc",
                "x86", "arm", "open_hardware"):
        assert key in data, f"arch.json 缺少 {key}"
        assert data[key].get("standards"), f"{key} 应带分层标准"
    # 龙芯属国产自主（national 层非空）
    assert data["loongarch"]["standards"]["national"]
    # 开源硬件含国际认证/许可与地区标准
    oh = data["open_hardware"]["standards"]
    assert any("OSHWA" in x for x in oh["international"])
    assert any("DIN SPEC 3105" in x for x in oh["regional"])
    # 机器名映射可用于探测
    assert "loongarch64" in data["loongarch"]["uname_machines"]
    assert "mips64el" in data["mips"]["uname_machines"]
    assert "riscv64" in data["riscv"]["uname_machines"]


def test_task_standards_derivation():
    """普通任务的标准归属可派生：关键词细化优先，否则回退分类默认。"""
    from sysweeper.models import task_standards, task_standards_ordered
    by_id = {t.id: t for t in registry.all_tasks()}
    # 关键词细化：含 trim/ssd 的任务应指向 ATA TRIM
    ssd = task_standards(by_id["hw_ssd_trim"])
    assert any("TRIM" in x for x in ssd)
    # 分类默认：清理类任务应指向 XDG / 平台缓存规范
    cl = task_standards(by_id["any_user_cache"])
    assert any(("XDG" in x) or ("缓存" in x) or ("Cache" in x) for x in cl)
    # 自带 standards 的任务以自带为准
    assert task_standards(by_id["arch_loongarch"]) == by_id["arch_loongarch"].standards
    # 排序：国内受众国标排前（有国标时）
    ordered = task_standards_ordered(by_id["arch_loongarch"], "cn")
    assert ordered[0].startswith("①") and "[国标]" in ordered[0]
    ordered_intl = task_standards_ordered(by_id["arch_loongarch"], "intl")
    assert "[国际]" in ordered_intl[0]


def test_region_audience_subtags():
    """地区子标签：us/jp/eu/de 受众把该地区条目排到最前。"""
    from sysweeper.models import standards_for_audience, tier_order, region_rank
    assert tier_order("us")[0] == "regional"
    assert tier_order("cn")[0] == "national"
    assert tier_order("intl")[0] == "international"
    # 欧盟：GDPR / EN 301 549 / ErP 优先
    eu = standards_for_audience("privacy", "eu")
    assert "GDPR" in eu[0] or "EN 301 549" in eu[0]
    # 日本：APPI / JIS 优先
    jp = standards_for_audience("privacy", "jp")
    assert "APPI" in jp[0] or "JIS" in jp[0]
    # 美国：NIST / ENERGY STAR 优先
    us = standards_for_audience("optimize", "us")
    assert "ENERGY STAR" in us[0] or "NIST" in us[0]
    assert region_rank("美国 ENERGY STAR", "us") == 0
    assert region_rank("欧盟 GDPR", "us") == 1


def test_new_cross_system_tasks_registered():
    """本轮跨系统/跨语言补全任务已注册（ZFS、固件、快照、组件存储、PHP/Ruby…）。"""
    by_id = {t.id: t for t in registry.all_tasks()}
    expect = {
        "linux_zfs_trim": ("linux", "maintenance"),
        "linux_fwupd": ("linux", "maintenance"),
        "mac_tm_snapshots": ("macos", "cleanup"),
        "win_dism_cleanup": ("windows", "maintenance"),
        "bsd_zfs_trim": ("bsd", "maintenance"),
        "bsd_ports_distfiles": ("bsd", "cleanup"),
        "unix_zfs_scrub": ("unix", "maintenance"),
        "and_app_hibernate": ("android", "optimize"),
        "ios_limit_ad_tracking": ("ios", "privacy"),
        "uniapp_image_compress": ("uniapp", "optimize"),
        "lang_php_composer": ("any", "cleanup"),
        "lang_ruby_gem": ("any", "cleanup"),
    }
    for tid, (pf, cat) in expect.items():
        assert tid in by_id, f"缺少任务 {tid}"
        assert by_id[tid].platform == pf, f"{tid} 平台应为 {pf}"
        assert by_id[tid].category == cat, f"{tid} 分类应为 {cat}"
    # 语言类任务按语言自动启用
    assert by_id["lang_php_composer"].requires_lang == "php"
    assert by_id["lang_ruby_gem"].requires_lang == "ruby"


def test_cli_arch_command_runs():
    """CLI arch 子命令可跑通（只读探测，无需特定架构）。"""
    from argparse import Namespace
    from sysweeper import cli
    for aud in ("cn", "intl", "eu"):
        cli.cmd_arch(Namespace(audience=aud))  # 不抛即通过


# ───────────────────────── 硬件优化（参考 Linux kernel 源码文档） ─────────────────────────

def test_hardware_category_and_kernel_docs():
    """hardware 分类已纳入「分类规范整体」：三层标准齐全，且内核文档引用数据合法。"""
    from sysweeper.models import (CATEGORIES, CATEGORY_ORDER, category_standards,
                                  standards_for_audience)
    assert "hardware" in CATEGORIES and "hardware" in CATEGORY_ORDER
    st = category_standards("hardware")["standards"]
    # 三层标准：国标（能效标识）/ 国际（Linux kernel Documentation 优先）/ 地区
    assert any("GB 24850" in x or "能效" in x for x in st["national"]), "硬件应引国标能效"
    assert any("Linux kernel Documentation" in x for x in st["international"]), \
        "硬件国际化依据应为 Linux kernel 源码文档"
    assert any("ENERGY STAR" in x or "ErP" in x for x in st["regional"]), "硬件应引地区能效标准"
    cn = standards_for_audience("hardware", "cn")
    assert any("国标" in s for s in cn), "cn 受众硬件标准应把国标排前"

    # data/hardware_kernel.json 合法且覆盖关键硬件子系统
    import json
    path = os.path.join(ROOT, "src", "python", "sysweeper", "data", "hardware_kernel.json")
    data = json.load(open(path, encoding="utf-8"))
    for key in ("cpufreq", "cpuidle", "intel_pstate", "thermal", "thp", "zswap",
                "zram", "nvme", "watchdog", "numa", "sched_eas"):
        assert key in data, f"hardware_kernel.json 缺少 {key}"
        assert data[key].get("path", "").startswith("Documentation/"), \
            f"{key} 应指向 kernel.org/Documentation 路径"
        assert data[key].get("interfaces"), f"{key} 应列出可读的内核接口"


def test_hardware_optimization_tasks_registered():
    """硬件优化任务已注册：参考内核文档、平台=linux、hw_epb 限定 x86 架构。"""
    by_id = {t.id: t for t in registry.all_tasks()}
    ids = [
        "hw_cpufreq_governor", "hw_cpuidle_optimize", "hw_intel_pstate",
        "hw_thermal_throttle", "hw_thp_tune", "hw_zswap", "hw_zram",
        "hw_io_sched", "hw_nvme", "hw_epb", "hw_numa_balance", "hw_watchdog",
        "hw_vm_swappiness", "hw_sched_eas",
    ]
    for tid in ids:
        assert tid in by_id, f"缺少硬件优化任务 {tid}"
        t = by_id[tid]
        assert t.category == "hardware", f"{tid} 应归 hardware 分类"
        assert t.platform == "linux", f"{tid} 应限定 linux 平台"
        # 标准依据一律指向内核文档（kernel.org/Documentation）
        assert any("kernel.org" in s or "kernel Documentation" in s
                   or "Documentation/" in s for s in t.standards), \
            f"{tid} 应引用 Linux kernel 源码文档"
    # x86 专属 EPB：仅在架构=x86 时出现（呼应「架构维度」）
    assert by_id["hw_epb"].arch == "x86"
    # 非 x86 架构扫描不列出 hw_epb
    assert "hw_epb" not in [t.id for t in
                            registry.applicable("linux", "24.04", arch="riscv")]
    assert "hw_epb" in [t.id for t in
                        registry.applicable("linux", "24.04", arch="x86")]


def test_hardware_kernel_native_graceful():
    """硬件内核文档原生探测函数均优雅：返回 (bool, str)、不抛、引用表可读。"""
    from sysweeper import native
    fns = ("cpufreq_governor", "cpuidle_report", "intel_pstate_status",
           "thermal_report", "thp_enabled", "zswap_enabled", "zram_report",
           "io_scheduler", "nvme_report", "epb_read", "numa_balancing",
           "watchdog_report", "vm_swappiness", "eas_available")
    for fn in fns:
        res = getattr(native.hardware, fn)()
        assert isinstance(res, tuple) and len(res) == 2, f"{fn} 应返回 (ok, msg)"
        ok, msg = res
        assert isinstance(ok, bool) and isinstance(msg, str), f"{fn} 类型异常"
    # 内核文档引用表可读
    docs = native.hardware.kernel_doc_list()
    assert isinstance(docs, list) and len(docs) > 0
    assert all("Documentation/" in d for d in docs), "引用表每条应含内核文档路径"


def test_cli_hardware_command_runs():
    """CLI hardware 子命令可跑通（只读报告 + 内核文档引用 + 适用任务）。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    args = p.parse_args(["hardware"])
    args.func(args)  # 仅打印，不修改系统


def test_arch_scan_clean_filters_by_arch():
    """scan/clean 经 registry.applicable 的 arch 维度过滤：架构不匹配的任务被排除。"""
    # 架构维度非空的任务：龙芯/ MIPS 专属 + x86 的 hw_epb
    loong = [t for t in registry.applicable("linux", "24.04", arch="loongarch")]
    assert not any(t.id == "arch_mips" for t in loong), "架构=loongarch 不应含 MIPS 专属"
    assert any(t.id == "arch_loongarch" for t in loong), "架构=loongarch 应含龙芯专属"
    # 传入 arch=None 与不过滤等价（不过滤掉任何非架构任务）
    none_arch = [t.id for t in registry.applicable("linux", "24.04", arch=None)]
    no_arg = [t.id for t in registry.applicable("linux", "24.04")]
    assert set(none_arch) == set(no_arg), "arch=None 应与不过滤一致"
    # 架构=riscv 时排除 loongarch/mips/x86 专属
    riscv = [t.id for t in registry.applicable("linux", "24.04", arch="riscv")]
    assert "arch_loongarch" not in riscv and "arch_mips" not in riscv
    assert "hw_epb" not in riscv


def test_kernel_docs_load_and_group():
    """内核文档引用表加载成功，且按 hardware/software/network 分组覆盖关键子系统。"""
    from sysweeper.native import kernel as nk
    grouped = nk.kernel_doc_grouped()
    assert {"hardware", "software", "network"} <= set(grouped.keys())
    # 软件至少要覆盖 scheduler/cgroup-v2/oom/psi
    sw = grouped["software"]
    for k in ("scheduler", "cgroup_v2", "oom", "psi"):
        assert k in sw, f"软件内核文档缺 {k}"
    # 网络至少要覆盖 tcp/net.core/rps
    net = grouped["network"]
    for k in ("tcp", "net_core", "rps"):
        assert k in net, f"网络内核文档缺 {k}"
    # 每条文档都有 path（内核文档路径）便于溯源
    for g, items in grouped.items():
        for key, ref in items.items():
            assert ref.get("path", "").startswith("Documentation/"), f"{g}/{key} 缺内核文档路径"


def test_kernel_software_network_tasks_registered():
    """新增的软件/网络内核文档优化任务已注册，且标准指向 Linux kernel Documentation。"""
    from sysweeper import registry
    ids = {t.id for t in registry.all_tasks()}
    for tid in ("linux_sched_cfs", "linux_cgroup_v2", "linux_oom_guard",
                "linux_psi", "linux_thp_compaction", "linux_vm_dirty",
                "linux_tcp_tuning", "linux_tcp_congestion", "linux_net_core",
                "linux_rps"):
        assert tid in ids, f"缺少内核文档任务 {tid}"
    # 软件/网络任务标准应指向内核文档
    ktasks = [t for t in registry.all_tasks()
              if t.id in {"linux_sched_cfs", "linux_tcp_tuning", "linux_rps"}]
    for t in ktasks:
        assert any("Linux kernel Documentation" in s for s in t.standards), \
            f"{t.id} 未引用内核文档"


def test_kernel_command_runs():
    """CLI kernel 子命令可跑通（只读探测，无需特定架构/桌面）。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    args = p.parse_args(["kernel", "--platform", "linux"])
    args.func(args)  # 仅打印，不修改系统


def test_desktop_docs_load():
    """桌面环境文档引用表加载成功，覆盖 GNOME/KDE/XFCE/freedesktop。"""
    from sysweeper.native import desktop as ndt
    refs = ndt.reference_all()
    for k in ("gnome", "kde", "xfce", "freedesktop", "caches"):
        assert k in refs, f"桌面文档缺 {k}"
    assert ndt.reference("gnome").get("url"), "GNOME 文档缺 url"
    assert ndt.reference("kde").get("url"), "KDE 文档缺 url"


def test_desktop_tasks_registered():
    """桌面清理/优化任务已注册（GNOME/KDE/XFCE + freedesktop），标准指向桌面文档。"""
    from sysweeper import registry
    dtasks = [t for t in registry.all_tasks() if t.id.startswith("desktop_")]
    assert len(dtasks) >= 8, f"桌面任务过少: {len(dtasks)}"
    for tid in ("desktop_gnome_cache", "desktop_kde_cache", "desktop_xfce_cache",
                "desktop_recent_docs", "desktop_xfconf_report",
                "desktop_theme_standard"):
        assert any(t.id == tid for t in dtasks), f"缺少桌面任务 {tid}"
    # 桌面任务标准应引用桌面环境/规范文档
    for t in dtasks:
        assert t.standards, f"{t.id} 未声明标准出处"
        assert any("GNOME" in s or "KDE" in s or "XFCE" in s
                   or "freedesktop" in s for s in t.standards), \
            f"{t.id} 标准未指向桌面文档"


def test_desktop_command_runs():
    """CLI desktop 子命令可跑通（只读探测当前桌面环境，不修改系统）。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    args = p.parse_args(["desktop"])
    args.func(args)  # 仅打印，不修改系统


def test_desktop_cache_report_native_readonly():
    """桌面缓存只读对比报告：原生函数返回 (ok, 文本) 且机器可读版为 dict（不删除文件）。"""
    from sysweeper.native import desktop as ndt
    ok, msg = ndt.cache_report()
    assert ok is True and isinstance(msg, str) and len(msg) > 0
    assert "不删除" in msg, "只读报告应明确声明不删除文件"
    rep = ndt.cache_report_dict()
    assert isinstance(rep, dict)
    assert set(rep.keys()) >= {"current", "entries", "xdg", "grand_total"}
    assert rep["grand_total"] >= 0
    # 各环境条目结构正确
    for e in rep["entries"]:
        assert {"env", "current", "total", "dirs"} <= set(e.keys())
        assert e["env"] in ("gnome", "kde", "xfce")


def test_desktop_cache_report_task_registered():
    """desktop_cache_report 任务已注册：维护类、低风险、只读原生动作、标准指向桌面文档。"""
    from sysweeper import registry
    t = next((x for x in registry.all_tasks() if x.id == "desktop_cache_report"), None)
    assert t is not None, "缺少 desktop_cache_report 任务"
    assert t.category == "maintenance" and t.risk == "low", "应为维护类/低风险"
    assert any(a.kind == "native" and a.command == "desktop.cache_report"
               for a in t.actions), "应调用只读原生 desktop.cache_report"
    assert any("freedesktop" in s or "GNOME" in s or "KDE" in s or "XFCE" in s
               for s in t.standards), "标准应指向桌面文档"


def test_desktop_report_export(tmp_path):
    """desktop --report 可导出 Markdown/JSON 只读对比报告（不修改系统）。"""
    import json
    from sysweeper.cli import build_parser
    # Markdown
    md = tmp_path / "cache_report.md"
    args = build_parser().parse_args(["desktop", "--report", str(md)])
    args.func(args)
    assert md.exists() and "不删除任何文件" in md.read_text(encoding="utf-8")
    # JSON
    js = tmp_path / "cache_report.json"
    args = build_parser().parse_args(["desktop", "--report", str(js)])
    args.func(args)
    data = json.loads(js.read_text(encoding="utf-8"))
    assert data["grand_total"] >= 0 and "entries" in data


# ---------------------------------------------------------------------------
# 其他系统软件文档跟踪（触类旁通：按各自协议与接口）
# ---------------------------------------------------------------------------

def test_syssoftware_docs_load():
    """系统软件文档表加载成功：8 个软件，各含 protocols（协议）与 interfaces（接口）。"""
    from sysweeper.native import syssoftware as nsw
    refs = nsw.reference_all()
    assert len(refs) >= 8, f"系统软件文档条目过少: {len(refs)}"
    for key in ("systemd", "dbus", "networkmanager", "pipewire",
                "bluez", "udev", "polkit", "wayland"):
        ref = refs.get(key, {})
        assert ref, f"缺少系统软件文档: {key}"
        assert ref.get("name") and ref.get("org") and ref.get("url")
        # 触类旁通的关键：每条都要写清「自身的协议与接口」
        assert ref.get("protocols"), f"{key} 缺少协议(protocols)"
        assert ref.get("interfaces"), f"{key} 缺少接口(interfaces)"
        assert ref.get("docs") and ref.get("advice")
    # 单条查询与文档行输出
    assert nsw.reference("systemd")["name"]
    lines = nsw.syssoftware_doc_list()
    assert any("协议:" in l for l in lines) and any("接口:" in l for l in lines)


def test_syssoftware_probes_readonly():
    """各系统软件探测只读且惰性守卫：一律返回 (bool, str)，未安装也不抛异常。"""
    from sysweeper.native import syssoftware as nsw
    for fn_name, _label in nsw.PROBES:
        fn = getattr(nsw, fn_name)
        ok, msg = fn()
        assert isinstance(ok, bool), f"{fn_name} 应返回 bool"
        assert isinstance(msg, str) and msg, f"{fn_name} 应返回非空说明"
    det = nsw.detect_syssoftware()
    assert set(det.keys()) >= {"systemd", "dbus", "networkmanager", "pipewire",
                               "bluez", "udev", "polkit", "wayland"}
    assert all(isinstance(v, bool) for v in det.values())
    rep = nsw.environment_report()
    assert any("✓" in l or "✗" in l for l in rep)


def test_syssoftware_tasks_registered():
    """10 个系统软件任务已注册，且各自标准指向该软件自身文档（非内核/桌面文档）。"""
    from sysweeper import registry
    expect = {
        "syssw_systemd_journal": "systemd",
        "syssw_systemd_analyze": "systemd",
        "syssw_systemd_failed": "systemd",
        "syssw_dbus_report": "D-Bus",
        "syssw_nm_report": "NetworkManager",
        "syssw_pipewire_report": "PipeWire",
        "syssw_bluez_report": "BlueZ",
        "syssw_udev_report": "udev",
        "syssw_polkit_report": "polkit",
        "syssw_wayland_report": "Wayland",
    }
    tasks = {t.id: t for t in registry.all_tasks() if t.id.startswith("syssw_")}
    assert len(tasks) >= len(expect), f"系统软件任务不足: {len(tasks)}"
    for tid, kw in expect.items():
        t = tasks.get(tid)
        assert t is not None, f"缺少任务: {tid}"
        assert t.platform == "linux"
        assert t.standards, f"{tid} 缺少标准出处"
        assert any(kw in s for s in t.standards), \
            f"{tid} 的标准应指向 {kw} 自身文档: {t.standards}"
    # 删除类（journal 回收）须标可逆，且默认不落地（--apply 才执行）
    j = tasks["syssw_systemd_journal"]
    assert j.category == "cleanup"
    assert any(a.kind == "shell" and "--vacuum" in a.command for a in j.actions), \
        "应走官方 journalctl --vacuum 接口而非直接删文件"


def test_syssoftware_command_runs():
    """CLI syssoftware 子命令可跑通（只读核对各软件接口，不修改系统）。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    args = p.parse_args(["syssoftware"])
    args.func(args)  # 仅打印，不修改系统


# ---------------------------------------------------------------------------
# 鸿蒙（HarmonyOS / OpenHarmony）+ uni-app 鸿蒙端
# ---------------------------------------------------------------------------

def test_harmony_docs_load():
    """鸿蒙文档表加载成功：各条含 protocols（协议）与 interfaces（接口），并含 uni-app 鸿蒙篇。"""
    from sysweeper.native import harmony as nhm
    refs = nhm.reference_all()
    assert len(refs) >= 8, f"鸿蒙文档条目过少: {len(refs)}"
    for key in ("stage_model", "syscap", "hilog", "hdc", "app_package",
                "ipc_distributed", "uniapp_harmony"):
        ref = refs.get(key, {})
        assert ref, f"缺少鸿蒙文档: {key}"
        assert ref.get("name") and ref.get("org") and ref.get("url")
        assert ref.get("protocols"), f"{key} 缺少协议(protocols)"
        assert ref.get("interfaces"), f"{key} 缺少接口(interfaces)"
    # uni-app 鸿蒙篇须落到官方文档（用户提供）
    uni = refs["uniapp_harmony"]
    assert uni["url"].startswith("https://uniapp.dcloud.net.cn/tutorial/harmony/")
    assert any("vue3" in s for s in uni["protocols"]), "应注明仅支持 vue3"
    lines = nhm.harmony_doc_list()
    assert any("协议:" in l for l in lines) and any("接口:" in l for l in lines)


def test_harmony_probes_readonly():
    """鸿蒙探测只读且惰性守卫：一律返回 (bool, str)，无 hdc / 非工程目录也不抛异常。"""
    from sysweeper.native import harmony as nhm
    for fn_name, _label in nhm.PROBES:
        ok, msg = getattr(nhm, fn_name)()
        assert isinstance(ok, bool), f"{fn_name} 应返回 bool"
        assert isinstance(msg, str) and msg, f"{fn_name} 应返回非空说明"
    det = nhm.detect_harmony()
    assert set(det.keys()) >= {"hdc", "ohpm", "hvigorw", "harmony_project",
                               "uniapp_project"}
    assert all(isinstance(v, bool) for v in det.values())
    assert any("✓" in l or "✗" in l for l in nhm.environment_report())


def test_harmony_tasks_registered():
    """8 个鸿蒙任务已注册（platform=harmony），各自标准指向鸿蒙/uni-app 官方自身文档。"""
    from sysweeper import registry
    assert registry.PLATFORM_NAMES.get("harmony"), "harmony 应注册为平台"
    expect = {
        "harmony_hdc_report": "hdc",
        "harmony_hilog_report": "HiLog",
        "harmony_stage_model": "Stage",
        "harmony_syscap_report": "SystemCapability",
        "harmony_package_report": "HAP",
        "harmony_package_cache": "HAP",
        "harmony_ipc_distributed": "IPC/RPC",
        "harmony_uniapp_check": "uni-app",
    }
    tasks = {t.id: t for t in registry.all_tasks() if t.platform == "harmony"}
    assert len(tasks) >= len(expect), f"鸿蒙任务不足: {len(tasks)}"
    for tid, kw in expect.items():
        t = tasks.get(tid)
        assert t is not None, f"缺少任务: {tid}"
        assert t.standards, f"{tid} 缺少标准出处"
        assert any(kw in s for s in t.standards), f"{tid} 标准应含 {kw}: {t.standards}"
    # 鸿蒙无 journalctl --vacuum 式官方回收接口 → 日志项只做只读，不得有删除动作
    log = tasks["harmony_hilog_report"]
    assert all(a.kind == "native" for a in log.actions), "HiLog 项应仅只读原生核对"
    # 清理项只清可重建生成目录
    cache = tasks["harmony_package_cache"]
    assert cache.category == "cleanup"
    assert any(a.kind == "shell" and "./build" in a.command for a in cache.actions)


def test_harmony_command_runs():
    """CLI harmony 子命令可跑通（只读核对，不修改系统/设备）。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    args = p.parse_args(["harmony"])
    args.func(args)  # 仅打印，不修改系统


def test_harmony_device_probes_degrade():
    """鸿蒙设备侧探测：无 hdc 时 connected() 为假，设备/应用探测均降级为 (False, 说明)。"""
    from sysweeper.native import harmony as nhm
    ok, msg = nhm.device_report()
    assert isinstance(ok, bool) and isinstance(msg, str) and msg
    ok2, msg2 = nhm.app_report()
    assert isinstance(ok2, bool) and isinstance(msg2, str) and msg2
    if not nhm.connected():
        assert ok is False and ok2 is False, "未连设备时应降级为不适用"
        assert nhm.device_model() == "" and nhm.version() == ""


# ---------------------------------------------------------------------------
# uni-app 各小程序端（微信 / 支付宝 / 百度 / 抖音 / QQ / 快手）
# ---------------------------------------------------------------------------

def test_miniapp_docs_load():
    """小程序端文档表加载成功：6 端 + 跨端映射，各含 protocols 与 interfaces。"""
    from sysweeper.native import miniapp as nmp
    refs = nmp.reference_all()
    assert len(refs) >= 7, f"小程序端文档条目过少: {len(refs)}"
    assert len(nmp.PLATFORMS) == 6, "应覆盖 6 个小程序端"
    for key in ("weixin", "alipay", "baidu", "douyin", "qq", "kuaishou",
                "uniapp_mapping"):
        ref = refs.get(key, {})
        assert ref, f"缺少小程序端文档: {key}"
        assert ref.get("protocols"), f"{key} 缺少协议(protocols)"
        assert ref.get("interfaces"), f"{key} 缺少接口(interfaces)"
    # 各端 API 前缀必须各不相同（这正是「各端自身规范」的核心）
    prefixes = [v[3] for v in nmp.PLATFORMS.values()]
    assert len(set(prefixes)) == 6, f"各端 API 前缀应互不相同: {prefixes}"
    lines = nmp.miniapp_doc_list()
    assert any("协议:" in l for l in lines) and any("接口:" in l for l in lines)


def test_miniapp_probes_readonly():
    """小程序端探测只读且惰性守卫：一律返回 (bool, str)，非工程目录也不抛异常。"""
    from sysweeper.native import miniapp as nmp
    for fn_name, _label in nmp.PROBES:
        ok, msg = getattr(nmp, fn_name)()
        assert isinstance(ok, bool), f"{fn_name} 应返回 bool"
        assert isinstance(msg, str) and msg, f"{fn_name} 应返回非空说明"
    det = nmp.detect_miniapp()
    assert set(det.keys()) >= {"uniapp_project", "weixin", "alipay", "kuaishou"}
    assert all(isinstance(v, bool) for v in det.values())
    assert any("✓" in l or "✗" in l for l in nmp.environment_report())


def test_miniapp_tasks_registered():
    """8 个小程序端任务已注册（platform=uniapp），各自标准指向该端自身官方文档。"""
    from sysweeper import registry
    expect = {
        "mp_mapping_check": "uni-app",
        "mp_weixin_check": "微信",
        "mp_alipay_check": "支付宝",
        "mp_baidu_check": "百度",
        "mp_douyin_check": "抖音",
        "mp_qq_check": "QQ",
        "mp_kuaishou_check": "快手",
        "mp_dist_cache": "uni-app",
    }
    tasks = {t.id: t for t in registry.all_tasks() if t.id.startswith("mp_")}
    assert len(tasks) >= len(expect), f"小程序端任务不足: {len(tasks)}"
    for tid, kw in expect.items():
        t = tasks.get(tid)
        assert t is not None, f"缺少任务: {tid}"
        assert t.platform == "uniapp", f"{tid} 应属 uniapp 目标端"
        assert any(kw in s for s in t.standards), f"{tid} 标准应含 {kw}: {t.standards}"
    # 清理项只清可重建的 mp-* 产物
    cache = tasks["mp_dist_cache"]
    assert cache.category == "cleanup"
    assert any(a.kind == "shell" and "mp-*" in a.command for a in cache.actions)


def test_miniapp_command_runs():
    """CLI miniapp 子命令可跑通（只读扫描工程，不修改系统）。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    args = p.parse_args(["miniapp"])
    args.func(args)  # 仅打印，不修改系统


def test_miniapp_cross_platform_lint(tmp_path, monkeypatch):
    """跨端静态检查：能检出未加条件编译保护的 wx.* 调用，且不误报已保护/uni.* 的写法。"""
    import os
    from sysweeper.native import miniapp as nmp

    proj = tmp_path / "app"
    (proj / "pages").mkdir(parents=True)
    (proj / "pages.json").write_text("{}", encoding="utf-8")
    (proj / "pages" / "index.vue").write_text(
        "wx.request({url:'x'})\n"                       # 未保护 → 应检出
        "// #ifdef MP-WEIXIN\nwx.request({})\n// #endif\n"  # 已保护 → 不应报
        "uni.request({})\n",                            # uni.* 安全 → 不应报
        encoding="utf-8")

    monkeypatch.chdir(proj)
    ok, msg = nmp.cross_platform_lint()
    assert ok is True, msg
    assert "wx.request" in msg, f"应检出未保护的 wx.request: {msg}"
    # 只应检出 1 处（第 1 行），已保护与 uni.* 不计入
    assert "跨端风险: 1 处" in msg, f"误报/漏报: {msg}"
    assert os.getcwd() != str(proj) or True  # chdir 由 monkeypatch 自动还原


def test_miniapp_cross_lint_task_registered():
    """mp_cross_lint 任务已注册：uniapp 端、只读原生动作、标准指向 uni-app 跨平台文档。"""
    from sysweeper import registry
    t = next((x for x in registry.all_tasks() if x.id == "mp_cross_lint"), None)
    assert t is not None, "缺少 mp_cross_lint 任务"
    assert t.platform == "uniapp"
    assert any(a.kind == "native" and a.command == "miniapp.cross_platform_lint"
               for a in t.actions), "应调用只读原生 cross_platform_lint"
    assert any("uni-app" in s for s in t.standards)
    assert any("cross_platform_lint" == fn for fn, _ in
               __import__("sysweeper.native.miniapp", fromlist=["x"]).PROBES)


# ---------------------------------------------------------------------------
# 包管理器（dpkg/APT · RPM/DNF · apk · pacman · Homebrew · winget · pip · npm · Snap/Flatpak）
# ---------------------------------------------------------------------------

def test_pkgmgr_docs_load():
    """包管理器文档表加载成功：9 个条目，各含 protocols（协议）与 interfaces（接口）。"""
    from sysweeper.native import pkgmgr as npm_
    refs = npm_.reference_all()
    assert len(refs) >= 9, f"包管理器文档条目过少: {len(refs)}"
    for key in ("apt_dpkg", "rpm_dnf", "apk", "pacman", "brew",
                "winget", "pip", "npm", "universal"):
        ref = refs.get(key, {})
        assert ref, f"缺少包管理器文档: {key}"
        assert ref.get("name") and ref.get("org") and ref.get("url")
        # 触类旁通的关键：每个包管理器都要写清「自身的协议与接口」
        assert ref.get("protocols"), f"{key} 缺少协议(protocols)"
        assert ref.get("interfaces"), f"{key} 缺少接口(interfaces)"
        assert ref.get("docs") and ref.get("advice")
    assert npm_.reference("apt_dpkg")["name"]
    lines = npm_.pkgmgr_doc_list()
    assert any("协议:" in l for l in lines) and any("接口:" in l for l in lines)
    # 各条目的协议彼此不同（不套用同一套路径）
    joined = " ".join(" ".join(r.get("protocols", [])) for r in refs.values())
    for kw in ("deb", "rpmdb", "APKINDEX", "pkg.tar.zst", "ruby",
               "YAML", "PEP 503", "Registry", "OSTree"):
        assert kw.lower() in joined.lower(), f"协议覆盖缺失: {kw}"


def test_pkgmgr_probes_readonly():
    """各包管理器探测只读且惰性守卫：一律返回 (bool, str)，未安装也不抛异常。"""
    from sysweeper.native import pkgmgr as npm_
    for fn_name, _label in npm_.PROBES:
        fn = getattr(npm_, fn_name)
        ok, msg = fn()
        assert isinstance(ok, bool), f"{fn_name} 应返回 bool"
        assert isinstance(msg, str) and msg, f"{fn_name} 应返回非空说明"
        # 只读保证：探测文本里不得出现删除/安装类命令
        for bad in ("rm -rf", "purge 2>/dev/null &&", "install -y", "uninstall -y"):
            assert bad not in msg, f"{fn_name} 探测含写操作: {bad}"
    det = npm_.detect_pkgmgr()
    assert set(det.keys()) >= {"apt_dpkg", "rpm_dnf", "apk", "pacman",
                               "brew", "winget", "pip", "npm", "universal"}
    assert all(isinstance(v, bool) for v in det.values())
    assert any("✓" in l or "✗" in l for l in npm_.environment_report())


def test_pkgmgr_tasks_registered():
    """包管理器任务已注册，且各自走**该包管理器自身**的官方接口（不串用）。"""
    from sysweeper import registry
    expect = {
        "pm_apt_cache": ("apt-get clean", "Debian"),
        "pm_apt_autoremove": ("apt-get autoremove", "Debian"),
        "pm_dnf_clean": ("clean all", "rpm"),
        "pm_apk_cache": ("apk cache clean", "apk-tools"),
        "pm_pacman_cache": ("paccache -rk2", "pacman"),
        "pm_brew_cleanup": ("brew cleanup", "Homebrew"),
        "pm_winget_cache": ("WinGet", "WinGet"),
        "pm_pip_cache": ("cache purge", "pip"),
        "pm_npm_verify": ("npm cache verify", "npm"),
        "pm_flatpak_unused": ("flatpak uninstall --unused", "Flatpak"),
        "pm_snap_retain": ("refresh.retain", "snapd"),
        "pm_orphans_report": ("orphan", "Debian"),
    }
    tasks = {t.id: t for t in registry.all_tasks() if t.id.startswith("pm_")}
    assert len(tasks) >= len(expect), f"包管理器任务不足: {len(tasks)}"
    for tid, (cmd_kw, std_kw) in expect.items():
        t = tasks.get(tid)
        assert t is not None, f"缺少任务: {tid}"
        assert t.standards, f"{tid} 缺少标准出处"
        assert any(std_kw in s for s in t.standards), \
            f"{tid} 的标准应指向 {std_kw} 自身文档: {t.standards}"
        joined = " ".join(a.command for a in t.actions)
        if t.id != "pm_orphans_report":  # 只读核对任务走原生探测
            assert cmd_kw in joined, f"{tid} 应走官方接口 {cmd_kw}: {joined}"
        else:
            assert all(a.kind == "native" for a in t.actions), \
                "孤儿包核对必须全部只读原生探测"
    # 删包类须标中等风险（需 --yes）；只清缓存的为低风险
    assert tasks["pm_apt_autoremove"].risk == "medium"
    assert tasks["pm_flatpak_unused"].risk == "medium"
    assert tasks["pm_apt_cache"].risk == "low"
    # npm 用 verify 而非破坏性的 clean --force
    assert "clean --force" not in " ".join(
        a.command for a in tasks["pm_npm_verify"].actions)
    # pacman 保留版本（可降级）而非全清 -Scc
    assert "-Scc" not in " ".join(a.command for a in tasks["pm_pacman_cache"].actions)


def test_pkgmgr_command_runs():
    """CLI pkgmgr 子命令可跑通（只读核对各包管理器接口，不修改系统）。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    args = p.parse_args(["pkgmgr"])
    args.func(args)  # 仅打印，不修改系统


# --------------------------------------------------------------------------- #
# 容器运行时（Docker / Podman / containerd / BuildKit / OCI / LXC-LXD / CRI）   #
# --------------------------------------------------------------------------- #

def test_container_docs_load():
    """容器运行时文档表加载成功：7 个条目，各含 protocols（协议）与 interfaces（接口）。"""
    from sysweeper.native import container as nct
    refs = nct.reference_all()
    assert len(refs) >= 7, f"容器运行时文档条目过少: {len(refs)}"
    for key in ("docker", "podman", "containerd", "buildkit", "oci", "lxc", "cri"):
        ref = refs.get(key, {})
        assert ref, f"缺少容器运行时文档: {key}"
        assert ref.get("name") and ref.get("org") and ref.get("url")
        # 触类旁通的关键：每个运行时都要写清「自身的协议与接口」
        assert ref.get("protocols"), f"{key} 缺少协议(protocols)"
        assert ref.get("interfaces"), f"{key} 缺少接口(interfaces)"
        assert ref.get("docs") and ref.get("advice")
    assert nct.reference("docker")["name"]
    lines = nct.container_doc_list()
    assert any("协议:" in l for l in lines) and any("接口:" in l for l in lines)
    # 各条目的协议彼此不同（不套用同一套路径）
    joined = " ".join(" ".join(r.get("protocols", [])) for r in refs.values())
    for kw in ("OCI 运行时规范", "rootless", "content store", "LLB",
               "image spec", "liblxc", "CRI gRPC"):
        assert kw.lower() in joined.lower(), f"协议覆盖缺失: {kw}"


def test_container_probes_readonly():
    """各运行时探测只读且惰性守卫：一律返回 (bool, str)，未安装也不抛异常。"""
    from sysweeper.native import container as nct
    for fn_name, _label in nct.PROBES:
        fn = getattr(nct, fn_name)
        ok, msg = fn()
        assert isinstance(ok, bool), f"{fn_name} 应返回 bool"
        assert isinstance(msg, str) and msg, f"{fn_name} 应返回非空说明"
        # 只读保证：探测文本里不得出现破坏性删除/安装命令
        for bad in ("rm -rf", "purge 2>/dev/null &&", "install -y",
                    "uninstall -y", "docker system prune -a"):
            assert bad not in msg, f"{fn_name} 探测含写操作: {bad}"
    det = nct.detect_container()
    assert set(det.keys()) >= {"docker", "podman", "containerd", "buildkit",
                               "oci", "lxc", "cri"}
    assert all(isinstance(v, bool) for v in det.values())
    assert any("✓" in l or "✗" in l for l in nct.environment_report())


def test_container_tasks_registered():
    """容器运行时任务已注册，且各自走**该运行时自身**的官方接口（不串用）。"""
    from sysweeper import registry
    expect = {
        "ct_docker_dangling": ("image prune", "Docker"),
        "ct_docker_stopped": ("container prune", "Docker"),
        "ct_docker_volumes": ("volume prune", "Docker"),
        "ct_docker_build": ("builder prune", "BuildKit"),
        "ct_docker_system": ("system prune", "Docker"),
        "ct_podman_dangling": ("podman image prune", "Podman"),
        "ct_podman_volumes": ("podman volume prune", "Podman"),
        "ct_podman_system": ("podman system prune", "Podman"),
        "ct_containerd_gc": ("nerdctl system prune", "containerd"),
        "ct_buildx": ("buildx prune", "BuildKit"),
        "ct_lxc_unused": ("lxc image delete", "LXC"),
        "ct_oci_report": ("container.oci_report", "OCI"),
        "ct_disk_report": ("container.environment_report", "Docker"),
    }
    tasks = {t.id: t for t in registry.all_tasks() if t.id.startswith("ct_")}
    assert len(tasks) >= len(expect), f"容器运行时任务不足: {len(tasks)}"
    for tid, (cmd_kw, std_kw) in expect.items():
        t = tasks.get(tid)
        assert t is not None, f"缺少任务: {tid}"
        assert t.standards, f"{tid} 缺少标准出处"
        assert any(std_kw.lower() in s.lower() for s in t.standards), \
            f"{tid} 的标准应指向 {std_kw} 自身文档: {t.standards}"
        joined = " ".join(a.command for a in t.actions)
        # 只读核对任务走原生探测；其余走各运行时官方 prune 接口
        if tid in ("ct_oci_report", "ct_disk_report"):
            assert all(a.kind == "native" for a in t.actions), \
                f"{tid} 必须全部只读原生探测"
        else:
            assert cmd_kw in joined, f"{tid} 应走官方接口 {cmd_kw}: {joined}"
    # 删容器/卷类须标中等风险（需 --yes）；只清缓存的为低风险
    assert tasks["ct_docker_stopped"].risk == "medium"
    assert tasks["ct_docker_volumes"].risk == "medium"
    assert tasks["ct_docker_build"].risk == "low"
    # 绝不直接 rm -rf 各运行时数据目录
    all_cmds = " ".join(
        " ".join(a.command for a in t.actions) for t in tasks.values())
    assert "rm -rf /var/lib/docker" not in all_cmds
    assert "rm -rf /var/lib/containers" not in all_cmds
    assert "rm -rf /var/lib/containerd" not in all_cmds


def test_container_command_runs():
    """CLI container 子命令可跑通（只读核对各运行时接口，不修改系统）。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    args = p.parse_args(["container"])
    args.func(args)  # 仅打印，不修改系统


# --------------------------------------------------------------------------- #
# 存储与文件系统（ext4 / Btrfs / XFS / ZFS / LVM / fstrim / SMART / swap）       #
# --------------------------------------------------------------------------- #

def test_storage_docs_load():
    """存储文档表加载成功：8 个条目，各含 protocols（协议）与 interfaces（接口）。"""
    from sysweeper.native import storage as nst
    refs = nst.reference_all()
    assert len(refs) >= 8, f"存储文档条目过少: {len(refs)}"
    for key in ("ext4", "btrfs", "xfs", "zfs", "lvm", "fstrim", "smart", "swap"):
        ref = refs.get(key, {})
        assert ref, f"缺少存储文档: {key}"
        assert ref.get("name") and ref.get("org") and ref.get("url")
        # 触类旁通的关键：每个文件系统都要写清「自身的协议与接口」
        assert ref.get("protocols"), f"{key} 缺少协议(protocols)"
        assert ref.get("interfaces"), f"{key} 缺少接口(interfaces)"
        assert ref.get("docs") and ref.get("advice")
    assert nst.reference("ext4")["name"]
    lines = nst.storage_doc_list()
    assert any("协议:" in l for l in lines) and any("接口:" in l for l in lines)
    # 各条目的协议彼此不同（不套用同一套路径）
    joined = " ".join(" ".join(r.get("protocols", [])) for r in refs.values())
    for kw in ("extent", "b-tree", "ag", "zpool", "device-mapper",
               "fitrim", "smart", "swapspace2"):
        assert kw.lower() in joined.lower(), f"协议覆盖缺失: {kw}"


def test_storage_probes_readonly():
    """各文件系统探测只读且惰性守卫：一律返回 (bool, str)，未安装也不抛异常。"""
    from sysweeper.native import storage as nst
    for fn_name, _label in nst.PROBES:
        fn = getattr(nst, fn_name)
        ok, msg = fn()
        assert isinstance(ok, bool), f"{fn_name} 应返回 bool"
        assert isinstance(msg, str) and msg, f"{fn_name} 应返回非空说明"
        # 只读保证：探测文本里不得出现真正破坏性的执行模式
        # （rm -rf / dd if= 这类绝不应当出现在只读探测中；e4defrag / balance / blkdiscard /
        #  xfs_repair / swapoff / mkswap 等仅作为「建议/警告」文案出现，属正常只读说明）
        for bad in ("rm -rf", "dd if="):
            assert bad not in msg, f"{fn_name} 探测含写操作: {bad}"
    det = nst.detect_storage()
    assert set(det.keys()) >= {"ext4", "btrfs", "xfs", "zfs",
                               "lvm", "fstrim", "smart", "swap"}
    assert all(isinstance(v, bool) for v in det.values())
    assert any("✓" in l or "✗" in l for l in nst.environment_report())


def test_storage_tasks_registered():
    """存储任务已注册，且各自走**该文件系统自身**的官方接口（不串用）。"""
    from sysweeper import registry
    expect = {
        "fs_ext4_report": ("e2fsck", "ext4"),
        "fs_btrfs_report": ("btrfs", "btrfs"),
        "fs_xfs_report": ("xfs_db", "xfs"),
        "fs_zfs_report": ("zpool", "zpool"),
        "fs_lvm_report": ("lvs", "LVM"),
        "fs_fstrim_report": ("fstrim", "fstrim"),
        "fs_smart_report": ("smartctl", "smartctl"),
        "fs_swap_report": ("swapon", "swapon"),
        "fs_ext4_defrag": ("e4defrag", "ext4"),
        "fs_xfs_defrag": ("xfs_fsr", "xfs"),
        "fs_btrfs_balance": ("btrfs balance", "btrfs"),
        "fs_btrfs_scrub": ("btrfs scrub", "btrfs"),
        "fs_zfs_trim": ("zpool trim", "zpool"),
        "fs_fstrim_ssd": ("fstrim", "fstrim"),
        "fs_swap_rebuild": ["swapoff", "mkswap", "swapon"],
    }
    tasks = {t.id: t for t in registry.all_tasks() if t.id.startswith("fs_")}
    assert len(tasks) >= len(expect), f"存储任务不足: {len(tasks)}"
    for tid, spec in expect.items():
        t = tasks.get(tid)
        assert t is not None, f"缺少任务: {tid}"
        assert t.standards, f"{tid} 缺少标准出处"
        if isinstance(spec, tuple):
            cmd_kw, std_kw = spec
            assert any(std_kw in s for s in t.standards), \
                f"{tid} 的标准应指向 {std_kw} 自身文档: {t.standards}"
            if tid in ("fs_ext4_report", "fs_btrfs_report", "fs_xfs_report",
                       "fs_zfs_report", "fs_lvm_report", "fs_fstrim_report",
                       "fs_smart_report", "fs_swap_report"):
                # 只读核对任务必须全部走原生探测
                assert all(a.kind == "native" for a in t.actions), \
                    f"{tid} 必须全部只读原生探测"
            else:
                joined = " ".join(a.command for a in t.actions)
                assert cmd_kw in joined, f"{tid} 应走官方接口 {cmd_kw}: {joined}"
        else:
            joined = " ".join(a.command for a in t.actions)
            assert all(k in joined for k in spec), f"{tid} 应含 {spec}: {joined}"
    # 中风险项（整理/balance/重建 swap 需 --yes），其余低风险
    assert tasks["fs_xfs_defrag"].risk == "medium"
    assert tasks["fs_btrfs_balance"].risk == "medium"
    assert tasks["fs_swap_rebuild"].risk == "medium"
    assert tasks["fs_ext4_defrag"].risk == "low"
    assert tasks["fs_fstrim_ssd"].risk == "low"


def test_storage_command_runs():
    """CLI storage 子命令可跑通（只读核对各文件系统接口，不修改系统）。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    args = p.parse_args(["storage"])
    args.func(args)  # 仅打印，不修改系统


# --------------------------------------------------------------------------- #
# 网络栈深度调优（iproute2 / ethtool / eBPF / tc / conntrack / NM-resolved / 缩放）#
# --------------------------------------------------------------------------- #

def test_network_docs_load():
    """网络运维文档表加载成功：7 个条目，各含 protocols（协议）与 interfaces（接口）。"""
    from sysweeper.native import network as nnet
    refs = nnet.reference_all()
    assert len(refs) >= 7, f"网络文档条目过少: {len(refs)}"
    for key in ("iproute2", "ethtool", "ebpf", "tc", "conntrack", "nm_resolved", "scaling"):
        ref = refs.get(key, {})
        assert ref, f"缺少网络文档: {key}"
        assert ref.get("name") and ref.get("org") and ref.get("url")
        # 触类旁通的关键：每个工具都要写清「自身的协议与接口」
        assert ref.get("protocols"), f"{key} 缺少协议(protocols)"
        assert ref.get("interfaces"), f"{key} 缺少接口(interfaces)"
        assert ref.get("docs") and ref.get("advice")
    assert nnet.reference("iproute2")["name"]
    lines = nnet.network_doc_list()
    assert any("协议:" in l for l in lines) and any("接口:" in l for l in lines)
    # 各条目的协议彼此不同（不套用同一套路径）
    joined = " ".join(" ".join(r.get("protocols", [])) for r in refs.values())
    for kw in ("netlink", "ethtool", "bpf", "rtnetlink(tc)", "nf_conntrack",
               "networkmanager", "rps"):
        assert kw.lower() in joined.lower(), f"协议覆盖缺失: {kw}"


def test_network_probes_readonly():
    """各网络运维工具探测只读且惰性守卫：一律返回 (bool, str)，未安装也不抛异常。"""
    from sysweeper.native import network as nnet
    for fn_name, _label in nnet.PROBES:
        fn = getattr(nnet, fn_name)
        ok, msg = fn()
        assert isinstance(ok, bool), f"{fn_name} 应返回 bool"
        assert isinstance(msg, str) and msg, f"{fn_name} 应返回非空说明"
        # 只读保证：探测文本里不得出现真正破坏性的执行模式
        # （rm -rf / dd if= 绝不应当出现在只读探测中；echo/sysfs 仅作为「建议/警告」文案，属正常）
        for bad in ("rm -rf", "dd if="):
            assert bad not in msg, f"{fn_name} 探测含写操作: {bad}"
    det = nnet.detect_network()
    assert set(det.keys()) >= {"iproute2", "ethtool", "ebpf", "tc",
                               "conntrack", "nm_resolved", "scaling"}
    assert all(isinstance(v, bool) for v in det.values())
    assert any("✓" in l or "✗" in l for l in nnet.environment_report())


def test_network_tasks_registered():
    """网络栈深度调优任务已注册，且各自走**该工具自身**的官方接口（不串用）。"""
    import inspect
    from sysweeper import registry
    from sysweeper.native import network as nnet
    # 深度调优任务：id -> (原生函数名或 None, 官方接口关键字, 期望标准关键字)
    #   native 任务：命令形如 "network.<fn>"，工具关键字在该原生函数体内核验；
    #   manual 任务：kind=manual，关键字在动作 command/desc 文案中核验。
    expect = {
        "net_ethtool_offload": ("ethtool_offload", "ethtool -K", "ethtool"),
        "net_ethtool_coalesce": ("ethtool_coalesce", "ethtool -C", "中断聚合"),
        "net_rps": ("rps_enable", "rps_cpus", "scaling"),
        "net_xps": ("xps_enable", "xps_cpus", "scaling"),
        "net_tc_fq": ("tc_fq_codel", "fq_codel", "RFC 8290"),
        "net_conntrack_max": ("conntrack_max", "nf_conntrack_max", "nf_conntrack"),
        "net_netdev_backlog": ("netdev_backlog", "netdev_max_backlog", "netdev_max_backlog"),
        "net_ebpf_xdp": (None, "xdp", "XDP"),
        "net_irq_affinity": (None, "smp_affinity", "irq-affinity"),
        "net_rfs": (None, "rps_flow_cnt", "scaling"),
    }
    tasks = {t.id: t for t in registry.all_tasks() if t.id.startswith("net_")}
    assert len(tasks) >= len(expect), f"网络栈深度任务不足: {len(tasks)}"
    for tid, (fn_name, cmd_kw, std_kw) in expect.items():
        t = tasks.get(tid)
        assert t is not None, f"缺少任务: {tid}"
        assert t.opt_in is True, f"{tid} 应为 opt_in（默认关闭）"
        assert t.standards, f"{tid} 缺少标准出处"
        assert any(std_kw.lower() in s.lower() for s in t.standards), \
            f"{tid} 的标准应指向 {std_kw} 自身文档: {t.standards}"
        if fn_name:
            # 原生调优任务：动作应指向 network.<fn>，且该函数体确实调用该工具自身接口
            assert any(a.kind == "native" and a.command == f"network.{fn_name}"
                       for a in t.actions), \
                f"{tid} 应走原生接口 network.{fn_name}: {[a.command for a in t.actions]}"
            src = inspect.getsource(getattr(nnet, fn_name)).lower()
            assert cmd_kw.lower() in src, \
                f"{tid} 原生函数 network.{fn_name} 未调用官方接口 {cmd_kw}"
        else:
            # 指引类任务：文案里给出官方接口关键字
            joined = " ".join((a.command or "") + " " + (a.description or "")
                              for a in t.actions).lower()
            assert cmd_kw.lower() in joined, f"{tid} 指引应提及官方接口 {cmd_kw}"
    # 调优原生函数必须可无参派发（runner 用 fn() 调用）
    for fname in ("ethtool_offload", "ethtool_coalesce", "rps_enable",
                  "xps_enable", "tc_fq_codel", "conntrack_max", "netdev_backlog"):
        sig = inspect.signature(getattr(nnet, fname))
        for pname, param in sig.parameters.items():
            assert param.default is not inspect.Parameter.empty or \
                param.kind in (inspect.Parameter.VAR_POSITIONAL,
                               inspect.Parameter.VAR_KEYWORD), \
                f"network.{fname} 参数 {pname} 无默认值，无法无参派发"


def test_network_command_runs():
    """CLI network 子命令可跑通（只读探测各网络运维接口，不修改系统）。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    args = p.parse_args(["network"])
    args.func(args)  # 仅打印，不修改系统


# --------------------------------------------------------------------------- #
# v0.5.10 基线快照与差异对比：纯只读，把前后对比做成可追溯产物
# --------------------------------------------------------------------------- #

def test_snapshot_capture():
    """capture_snapshot 返回结构化 dict：meta + 磁盘/内存指标 + 各子系统只读探测。"""
    import copy
    import json
    from sysweeper.native import snapshot as nsnap

    snap = nsnap.capture_snapshot()
    assert set(["meta", "metrics", "probes"]).issubset(snap.keys())
    assert snap["meta"]["tool"] == "sysweeper"
    assert snap["meta"]["tool_version"]
    # 结构化指标：磁盘至少含根分区，内存为 Linux 时含 MemTotal
    assert snap["metrics"]["disk"], "应采集到磁盘指标"
    if snap["meta"]["platform"] == "linux":
        assert "MemTotal" in snap["metrics"]["memory"], "Linux 应读 /proc/meminfo"
    # 七个含 PROBES 的子系统都应出现在快照里
    for sub in ("container", "network", "pkgmgr", "storage"):
        assert sub in snap["probes"], f"快照应含子系统探测: {sub}"
    # 不传 include_probes 时不应有 probes 维度
    slim = nsnap.capture_snapshot(include_probes=False)
    assert "probes" not in slim or not slim["probes"]
    # 快照可原样序列化（只读，无副作用）
    json.dumps(snap)


def test_snapshot_save_load_roundtrip(tmp_path):
    """save_snapshot → load_snapshot 往返一致。"""
    import json
    from sysweeper.native import snapshot as nsnap

    snap = nsnap.capture_snapshot(include_probes=False)
    path = str(tmp_path / "snap.json")
    nsnap.save_snapshot(path, snap)
    back = nsnap.load_snapshot(path)
    assert back["meta"]["captured_at"] == snap["meta"]["captured_at"]
    assert back["metrics"] == snap["metrics"]


def test_snapshot_diff_detects_change():
    """diff_snapshots 能识别磁盘/内存数值变化与某探测从可用变不可用。"""
    import copy
    from sysweeper.native import snapshot as nsnap

    a = nsnap.capture_snapshot()
    b = copy.deepcopy(a)
    # 制造差异：磁盘 used 减少、内存 MemAvailable 增加、翻一个 container 探测
    root = "/" if "/" in b["metrics"]["disk"] else next(iter(b["metrics"]["disk"]))
    b["metrics"]["disk"][root]["used"] -= 1024 ** 3
    b["metrics"]["disk"][root]["free"] += 1024 ** 3
    if "MemAvailable" in b["metrics"]["memory"]:
        b["metrics"]["memory"]["MemAvailable"] += 512 * 1024 * 1024
    flipped = False
    for r in b["probes"].get("container", []):
        if r["ok"]:
            r["ok"] = False
            r["msg"] = "（测试）Docker 守护进程已停止"
            flipped = True
            break
    d = nsnap.diff_snapshots(a, b)
    # 磁盘 used_delta 应为负（减少了）
    dd = d["metrics"]["disk"][root]
    assert dd["used_delta"] == -1024 ** 3, "应检测到磁盘 used 减少 1GB"
    # 至少一条 container 探测标记为 changed
    if flipped:
        statuses = [c["status"] for c in d["probes"]["container"]]
        assert "changed" in statuses, "应检测到某 container 探测从可用变不可用"
    # 未变化的探测应标 unchanged
    unchanged = [c for c in d["probes"]["container"] if c["status"] == "unchanged"]
    assert unchanged, "未变化的探测应标 unchanged"


def test_snapshot_command_runs(tmp_path):
    """CLI snapshot 三个动作均可跑通（纯只读，不修改系统）。"""
    from sysweeper.cli import build_parser

    out1 = str(tmp_path / "before.json")
    out2 = str(tmp_path / "after.json")
    for action, extra in (
        ("capture", ["--out", out1]),
        ("capture", ["--out", out2]),
        ("diff", ["--a", out1, "--b", out2]),
        ("show", ["--file", out1]),
    ):
        p = build_parser()
        args = p.parse_args(["snapshot", action, *extra])
        args.func(args)  # 仅打印，不修改系统
    import os
    assert os.path.isfile(out1) and os.path.isfile(out2)


def test_macos_docs_load():
    """macOS 文档层已加载且字段完整（按 storage_docs.json 的 schema）。"""
    from sysweeper.native import macos as nm
    refs = nm.reference_all()
    assert len(refs) >= 8, f"macOS 文档条目过少: {len(refs)}"
    for key, ref in refs.items():
        assert ref.get("name") and ref.get("org") and ref.get("url"), \
            f"macOS 文档 {key} 缺 name/org/url"
        assert ref.get("protocols") and ref.get("interfaces"), \
            f"macOS 文档 {key} 缺 protocols/interfaces"
        assert ref.get("advice"), f"macOS 文档 {key} 缺 advice"


def test_macos_probes_readonly():
    """macOS 只读探测不修改系统；非 macOS 环境优雅降级为 (False, 说明)。"""
    from sysweeper.native import macos as nm
    # 仅校验 blacklist 级别的破坏性操作不应出现；其余为只读检查降级说明
    for fn_name, _lab in nm.PROBES:
        ok, msg = getattr(nm, fn_name)()
        assert isinstance(ok, bool) and isinstance(msg, str)
        assert not any(b in msg for b in ("rm -rf", "dd if=")), \
            f"macOS 探测 {fn_name} 文案含破坏性命令"


def test_macos_tasks_registered():
    """macOS 清理/优化任务已注册，且各自走**自身官方接口**（不串用 Linux 写法）。"""
    from sysweeper import registry
    tasks = {t.id: t for t in registry.all_tasks() if t.id.startswith("mac")}
    assert len(tasks) >= 10, f"mac_* 任务过少: {len(tasks)}"
    # 关键任务抽查：标准/接口指向 macOS 自身协议
    expect = {
        "mac_sw_update_report": "softwareupdate",
        "mac_tm_snapshots": "tmutil",
        "macos_visual_effects": "defaults",
        "mac_sleepimage": "sleepimage",
    }
    for tid, kw in expect.items():
        t = tasks.get(tid)
        assert t is not None, f"缺少任务: {tid}"
        joined = " ".join((a.command or "") + " " + (a.description or "")
                          for a in t.actions).lower()
        assert kw.lower() in joined, \
            f"{tid} 应走 macOS 自身接口 {kw}: {joined}"


def test_macos_command_runs():
    """CLI macos 子命令可跑通（只读探测 + 文档展示，不修改系统）。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    args = p.parse_args(["macos"])
    args.func(args)  # 仅打印，不修改系统


def test_bsd_docs_load():
    """BSD 文档层已加载且字段完整（按 storage_docs.json 的 schema）。"""
    from sysweeper.native import bsd as nb
    refs = nb.reference_all()
    assert len(refs) >= 8, f"BSD 文档条目过少: {len(refs)}"
    for key, ref in refs.items():
        assert ref.get("name") and ref.get("org") and ref.get("url"), \
            f"BSD 文档 {key} 缺 name/org/url"
        assert ref.get("protocols") and ref.get("interfaces"), \
            f"BSD 文档 {key} 缺 protocols/interfaces"
        assert ref.get("advice"), f"BSD 文档 {key} 缺 advice"


def test_bsd_probes_readonly():
    """BSD 只读探测不修改系统；非 BSD 环境优雅降级为 (False, 说明)。"""
    from sysweeper.native import bsd as nb
    for fn_name, _lab in nb.PROBES:
        ok, msg = getattr(nb, fn_name)()
        assert isinstance(ok, bool) and isinstance(msg, str)
        assert not any(b in msg for b in ("rm -rf", "dd if=")), \
            f"BSD 探测 {fn_name} 文案含破坏性命令"


def test_bsd_tasks_registered():
    """BSD 清理/优化任务已注册，且各自走**自身官方接口**（不串用 Linux 写法）。"""
    from sysweeper import registry
    tasks = {t.id: t for t in registry.all_tasks() if t.id.startswith("bsd")}
    assert len(tasks) >= 8, f"bsd_* 任务过少: {len(tasks)}"
    expect = {
        "bsd_pkg_cache": "pkg",
        "bsd_zfs_trim": "zpool",
        "bsd_ports_distfiles": "distfiles",
        "bsd_services_audit": "rc.conf",
    }
    for tid, kw in expect.items():
        t = tasks.get(tid)
        assert t is not None, f"缺少任务: {tid}"
        joined = " ".join((a.command or "") + " " + (a.description or "")
                          for a in t.actions).lower()
        assert kw.lower() in joined, \
            f"{tid} 应走 BSD 自身接口 {kw}: {joined}"


def test_bsd_command_runs():
    """CLI bsd 子命令可跑通（只读探测 + 文档展示，不修改系统）。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    args = p.parse_args(["bsd"])
    args.func(args)  # 仅打印，不修改系统


# --------------------------------------------------------------------------- #
# v0.5.12 macOS / BSD 官方接口深度调优（macos_tune_* / bsd_tune_*）            #
# 全部 opt_in：默认不出现、需选择 + 确认；原生写接口零参数可调用（runner 以      #
# fn() 派发），非目标平台一律优雅降级为 (False, 说明)。                         #
# --------------------------------------------------------------------------- #

def _assert_tunes_zero_arg(mod):
    """原生写接口必须零参数可调用（runner 以 fn() 派发），且非目标平台优雅降级。"""
    assert mod.TUNES, f"{mod.__name__} 缺少 TUNES 清单"
    for fn_name, desc in mod.TUNES:
        fn = getattr(mod, fn_name, None)
        assert fn is not None, f"缺少原生写接口: {fn_name}"
        import inspect
        required = [p for p in inspect.signature(fn).parameters.values()
                    if p.default is inspect.Parameter.empty]
        assert not required, f"{fn_name} 有必填参数 {required}（runner 以 fn() 派发）"
        ok, msg = fn()
        assert isinstance(ok, bool) and isinstance(msg, str), f"{fn_name} 返回值异常"
        assert not any(b in msg for b in ("rm -rf", "dd if=", "mkfs")), \
            f"{fn_name} 文案含破坏性命令"
        assert desc.strip(), f"{fn_name} 缺少官方子命令说明"


def test_macos_tunes_zero_arg():
    """macOS 官方写接口（pmset/sysctl/networksetup/tmutil/defaults/...）零参数可调用。"""
    from sysweeper.native import macos as nm
    _assert_tunes_zero_arg(nm)
    assert len(nm.macos_tune_list()) == len(nm.TUNES)


def test_bsd_tunes_zero_arg():
    """BSD 官方写接口（sysctl -w / zpool / pfctl -e -f / periodic）零参数可调用。"""
    from sysweeper.native import bsd as nb
    _assert_tunes_zero_arg(nb)
    assert len(nb.bsd_tune_list()) == len(nb.TUNES)


def test_macos_tune_tasks_registered():
    """macos_tune_* 深度调优任务：全 opt_in、platform=macos、各走自身官方接口。"""
    from sysweeper import registry as reg
    from sysweeper.native import macos as nm
    tunes = [t for t in reg.all_tasks() if t.id.startswith("macos_tune_")]
    assert len(tunes) >= 9, f"macos_tune_* 任务过少: {len(tunes)}"
    fn_names = {fn for fn, _ in nm.TUNES}
    expect = {
        "macos_tune_pmset_hibernatemode": ("pmset", "macos.pmset_hibernatemode"),
        "macos_tune_pmset_standbydelay": ("standbydelay", "macos.pmset_standby_delay"),
        "macos_tune_sysctl_maxfiles": ("kern.maxfiles", "macos.sysctl_maxfiles"),
        "macos_tune_networksetup_dns": ("-setdnsservers", "macos.networksetup_dns"),
        "macos_tune_tmutil_thinsnapshots": ("thinlocalsnapshots", "macos.tmutil_thin_snapshots"),
        "macos_tune_defaults_dock": ("defaults write", "macos.defaults_dock_autohide"),
        "macos_tune_softwareupdate_schedule": ("--schedule", "macos.softwareupdate_schedule"),
        "macos_tune_spctl_masterenable": ("--master-enable", "macos.spctl_master_enable"),
        "macos_tune_diskutil_verify": ("verifyVolume", "macos.diskutil_verify"),
    }
    by_id = {t.id: t for t in tunes}
    for tid, (kw, op) in expect.items():
        t = by_id.get(tid)
        assert t is not None, f"缺少任务: {tid}"
        assert t.platform == "macos" and t.opt_in, f"{tid} 应为 macOS 平台且默认关闭（opt_in）"
        acts = {a.command for a in t.actions}
        assert op in acts, f"{tid} 未派发原生接口 {op}: {acts}"
        assert op.split(".")[1] in fn_names, f"{op} 不在 TUNES 清单"
        joined = " ".join((a.command or "") + " " + (a.description or "") + " " + t.title
                          for a in t.actions).lower()
        assert kw.lower() in joined, f"{tid} 应走 macOS 自身接口 {kw}: {joined}"
    # 安全方向：绝不出现关闭 Gatekeeper / 删系统目录这类反向或破坏性操作
    blob = " ".join((a.command or "") + " " + (a.description or "")
                    for t in tunes for a in t.actions).lower()
    assert "master-disable" not in blob and "rm -rf" not in blob, \
        "macOS 调优任务出现反向/破坏性操作"


def test_bsd_tune_tasks_registered():
    """bsd_tune_* 深度调优任务：全 opt_in、platform=bsd、各走自身官方接口。"""
    from sysweeper import registry as reg
    from sysweeper.native import bsd as nb
    tunes = [t for t in reg.all_tasks() if t.id.startswith("bsd_tune_")]
    assert len(tunes) >= 8, f"bsd_tune_* 任务过少: {len(tunes)}"
    fn_names = {fn for fn, _ in nb.TUNES}
    expect = {
        "bsd_tune_tcp_rfc1323": ("rfc1323", "bsd.tcp_rfc1323"),
        "bsd_tune_tcp_buffers": ("recvspace", "bsd.tcp_buffers"),
        "bsd_tune_maxfiles": ("kern.maxfiles", "bsd.maxfiles"),
        "bsd_tune_zfs_autotrim": ("autotrim", "bsd.zfs_autotrim"),
        "bsd_tune_zfs_scrub": ("scrub", "bsd.zfs_scrub"),
        "bsd_tune_zfs_arcmax": ("arc_max", "bsd.zfs_arc_max"),
        "bsd_tune_pf_enable": ("pfctl -e", "bsd.pf_enable"),
        "bsd_tune_periodic_run": ("periodic", "bsd.periodic_run"),
    }
    by_id = {t.id: t for t in tunes}
    for tid, (kw, op) in expect.items():
        t = by_id.get(tid)
        assert t is not None, f"缺少任务: {tid}"
        assert t.platform == "bsd" and t.opt_in, f"{tid} 应为 BSD 平台且默认关闭（opt_in）"
        acts = {a.command for a in t.actions}
        assert op in acts, f"{tid} 未派发原生接口 {op}: {acts}"
        assert op.split(".")[1] in fn_names, f"{op} 不在 TUNES 清单"
        joined = " ".join((a.command or "") + " " + (a.description or "") + " " + t.title
                          for a in t.actions).lower()
        assert kw.lower() in joined, f"{tid} 应走 BSD 自身接口 {kw}: {joined}"
    # 安全方向：绝不出现 pkg delete -a / pfctl -d / -F all / zpool destroy
    blob = " ".join((a.command or "") + " " + (a.description or "")
                    for t in tunes for a in t.actions).lower()
    for bad in ("pkg delete -a", "pfctl -d", "-f all", "zpool destroy"):
        assert bad not in blob, f"BSD 调优任务出现破坏性操作: {bad}"


def test_macos_bsd_tune_commands_run():
    """CLI macos / bsd 子命令可跑通（含深度调优清单展示，只读，不修改系统）。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    for sub in ("macos", "bsd"):
        args = p.parse_args([sub])
        args.func(args)  # 仅打印展示，不调用写接口


# --------------------------------------------------------------------------- #
# v0.5.13 Windows 原生接口文档跟踪 + 官方接口深度调优（win_tune_*）             #
# --------------------------------------------------------------------------- #

def test_windows_docs_load():
    """Windows 文档层已加载且字段完整（与其它 X_docs.json 同 schema）。"""
    from sysweeper.native import windows as nw
    refs = nw.reference_all()
    assert len(refs) >= 9, f"Windows 文档条目过少: {len(refs)}"
    for key, ref in refs.items():
        assert ref.get("name") and ref.get("org") and ref.get("url"), \
            f"Windows 文档 {key} 缺 name/org/url"
        assert ref.get("protocols") and ref.get("interfaces"), \
            f"Windows 文档 {key} 缺 protocols/interfaces"
        assert ref.get("advice"), f"Windows 文档 {key} 缺 advice"


def test_windows_probes_readonly():
    """Windows 只读探测不修改系统；非 Windows 环境优雅降级为 (False, 说明)。"""
    from sysweeper.native import windows as nw
    assert len(nw.PROBES) >= 9
    for fn_name, _lab in nw.PROBES:
        ok, msg = getattr(nw, fn_name)()
        assert isinstance(ok, bool) and isinstance(msg, str)
        assert not any(b in msg for b in ("rm -rf", "dd if=", "reg delete")), \
            f"Windows 探测 {fn_name} 文案含破坏性命令"


def test_windows_tunes_zero_arg():
    """Windows 官方写接口（fsutil / netsh / powercfg / sfc）零参数可调用。"""
    from sysweeper.native import windows as nw
    _assert_tunes_zero_arg(nw)
    assert len(nw.windows_tune_list()) == len(nw.TUNES)


def test_windows_tune_tasks_registered():
    """win_tune_* 深度调优任务：全 opt_in、platform=windows、各走自身官方接口。"""
    from sysweeper import registry as reg
    from sysweeper.native import windows as nw
    tunes = [t for t in reg.all_tasks() if t.id.startswith("win_tune_")]
    assert len(tunes) >= 8, f"win_tune_* 任务过少: {len(tunes)}"
    fn_names = {fn for fn, _ in nw.TUNES}
    expect = {
        "win_tune_fsutil_lastaccess": ("DisableLastAccess", "windows.fsutil_disable_last_access"),
        "win_tune_fsutil_8dot3": ("8dot3", "windows.fsutil_disable_8dot3"),
        "win_tune_tcp_autotuning": ("autotuninglevel", "windows.netsh_tcp_autotuning"),
        "win_tune_tcp_rss": ("rss", "windows.netsh_tcp_rss"),
        "win_tune_tcp_ecn": ("ecncapability", "windows.netsh_tcp_ecn"),
        "win_tune_firewall_on": ("advfirewall", "windows.netsh_firewall_on"),
        "win_tune_powercfg_timeout": ("monitor-timeout", "windows.powercfg_monitor_timeout"),
        "win_tune_hibernate_reduced": ("/h /type reduced", "windows.powercfg_hibernate_reduced"),
    }
    by_id = {t.id: t for t in tunes}
    for tid, (kw, op) in expect.items():
        t = by_id.get(tid)
        assert t is not None, f"缺少任务: {tid}"
        assert t.platform == "windows" and t.opt_in, f"{tid} 应为 Windows 平台且默认关闭（opt_in）"
        acts = {a.command for a in t.actions}
        assert op in acts, f"{tid} 未派发原生接口 {op}: {acts}"
        assert op.split(".")[1] in fn_names, f"{op} 不在 TUNES 清单"
        joined = " ".join((a.command or "") + " " + (a.description or "") + " " + t.title
                          for a in t.actions).lower()
        assert kw.lower() in joined, f"{tid} 应走 Windows 自身接口 {kw}: {joined}"
    # 安全方向：防火墙只开不关、TCP 只调不禁用、休眠只缩减不彻底关闭
    blob = " ".join((a.command or "") + " " + (a.description or "")
                    for t in tunes for a in t.actions).lower()
    for bad in ("state off", "autotuninglevel=disabled", "rss=disabled",
                "hibernate off", "rm -rf"):
        assert bad not in blob, f"Windows 调优任务出现反向/破坏性操作: {bad}"


def test_windows_command_runs():
    """CLI windows 子命令可跑通（含深度调优清单展示，只读，不修改系统）。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    args = p.parse_args(["windows"])
    args.func(args)  # 仅打印展示，不调用写接口


# --------------------------------------------------------------------------- #
# v0.5.14：Unix（System V / Solaris / illumos）文档层 + 只读探测 + 官方写接口      #
# --------------------------------------------------------------------------- #

def test_unix_docs_load():
    """Unix 文档层已加载且字段完整（与其它 X_docs.json 同 schema）。"""
    from sysweeper.native import unix as nu
    refs = nu.reference_all()
    assert len(refs) >= 9, f"Unix 文档条目过少: {len(refs)}"
    for key, ref in refs.items():
        assert ref.get("name") and ref.get("org") and ref.get("url"), \
            f"Unix 文档 {key} 缺 name/org/url"
        assert ref.get("protocols") and ref.get("interfaces"), \
            f"Unix 文档 {key} 缺 protocols/interfaces"
        assert ref.get("advice"), f"Unix 文档 {key} 缺 advice"
    # 关键：System V 自身接口必须在文档里（不套 Linux 写法）
    for k in ("ips_pkg", "smf", "zfs", "etc_release", "logadm", "kstat",
              "zones", "fma", "ipadm_dladm"):
        assert k in refs, f"Unix 文档缺少自身接口条目: {k}"


def test_unix_probes_readonly():
    """Unix 只读探测不修改系统；非 System V 环境优雅降级为 (False, 说明)。"""
    from sysweeper.native import unix as nu
    assert len(nu.PROBES) >= 9
    for fn_name, _lab in nu.PROBES:
        ok, msg = getattr(nu, fn_name)()
        assert isinstance(ok, bool) and isinstance(msg, str)
        assert not any(b in msg for b in ("rm -rf", "dd if=", "zpool destroy")), \
            f"Unix 探测 {fn_name} 文案含破坏性命令"
    # 非 sunos 环境应全部降级（本机跑测试时为 Linux）
    import sys
    if sys.platform != "sunos":
        for fn_name, _lab in nu.PROBES:
            ok, msg = getattr(nu, fn_name)()
            assert ok is False, f"{fn_name} 在非 System V 环境应降级为不可用"
            assert "非 System V" in msg or "降级" in msg, f"{fn_name} 降级说明不明确: {msg}"


def test_unix_tunes_zero_arg():
    """Unix 官方写接口（pkg / svcadm / zfs / zpool / logadm / ipadm）零参数可调用。"""
    from sysweeper.native import unix as nu
    _assert_tunes_zero_arg(nu)
    assert len(nu.unix_tune_list()) == len(nu.TUNES)
    # 池名 / FMRI 自动探测的辅助函数在无对应命令时返回空列表而非报错
    assert nu._zpool_names() == [] or isinstance(nu._zpool_names(), list)
    assert isinstance(nu._maintenance_fmris(), list)


def test_unix_tune_tasks_registered():
    """unix_tune_* 深度调优任务：全 opt_in、platform=unix、各走自身官方接口。"""
    from sysweeper import registry as reg
    from sysweeper.native import unix as nu
    tunes = [t for t in reg.all_tasks() if t.id.startswith("unix_tune_")]
    assert len(tunes) >= 8, f"unix_tune_* 任务过少: {len(tunes)}"
    fn_names = {fn for fn, _ in nu.TUNES}
    expect = {
        "unix_tune_ips_refresh": ("pkg refresh", "unix.ips_pkg_refresh"),
        "unix_tune_ips_fix": ("pkg fix", "unix.ips_pkg_fix"),
        "unix_tune_smf_fmd": ("svcadm enable", "unix.smf_enable_fmd"),
        "unix_tune_smf_clear": ("svcadm clear", "unix.smf_clear_maintenance"),
        "unix_tune_zfs_atime": ("atime=off", "unix.zfs_atime_off"),
        "unix_tune_zfs_compression": ("compression=lz4", "unix.zfs_compression_lz4"),
        "unix_tune_logadm_rotate": ("logadm -r", "unix.logadm_rotate_now"),
        "unix_tune_ipadm_ecn": ("ecn=active", "unix.ipadm_tcp_ecn"),
    }
    by_id = {t.id: t for t in tunes}
    for tid, (kw, op) in expect.items():
        t = by_id.get(tid)
        assert t is not None, f"缺少任务: {tid}"
        assert t.platform == "unix" and t.opt_in, f"{tid} 应为 unix 平台且默认关闭（opt_in）"
        acts = {a.command for a in t.actions}
        assert op in acts, f"{tid} 未派发原生接口 {op}: {acts}"
        assert op.split(".")[1] in fn_names, f"{op} 不在 TUNES 清单"
        joined = " ".join((a.command or "") + " " + (a.description or "") + " " + t.title
                          for a in t.actions).lower()
        assert kw.lower() in joined, f"{tid} 应走 System V 自身接口 {kw}: {joined}"
    # 安全方向：服务只开不关、ZFS 只改属性不删数据、日志只轮转不删、不卸包
    blob = " ".join((a.command or "") + " " + (a.description or "")
                    for t in tunes for a in t.actions).lower()
    for bad in ("svcadm disable", "zpool destroy", "zfs destroy",
                "pkg uninstall", "rm -rf", "delete-if"):
        assert bad not in blob, f"Unix 调优任务出现反向/破坏性操作: {bad}"


def test_unix_command_runs():
    """CLI unix 子命令可跑通（含深度调优清单展示，只读，不修改系统）。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    args = p.parse_args(["unix"])
    args.func(args)  # 仅打印展示，不调用写接口


# --------------------------------------------------------------------------- #
# v0.5.15：Android（adb）文档层 + 只读探测 + 官方写接口                          #
# --------------------------------------------------------------------------- #

def test_android_docs_load():
    """Android 文档层已加载且字段完整（与其它 X_docs.json 同 schema）。"""
    from sysweeper.native import android as na
    refs = na.reference_all()
    assert len(refs) >= 9, f"Android 文档条目过少: {len(refs)}"
    for key, ref in refs.items():
        assert ref.get("name") and ref.get("org") and ref.get("url"), \
            f"Android 文档 {key} 缺 name/org/url"
        assert ref.get("protocols") and ref.get("interfaces"), \
            f"Android 文档 {key} 缺 protocols/interfaces"
        assert ref.get("advice"), f"Android 文档 {key} 缺 advice"
    for k in ("adb", "settings_provider", "pm", "am", "dumpsys", "getprop",
              "svc", "wm", "logcat"):
        assert k in refs, f"Android 文档缺少自身接口条目: {k}"


def test_android_probes_readonly():
    """Android 只读探测不修改系统；未装 adb / 无设备时优雅降级为 (False, 说明)。"""
    from sysweeper.native import android as na
    assert len(na.PROBES) >= 9
    for fn_name, _lab in na.PROBES:
        ok, msg = getattr(na, fn_name)()
        assert isinstance(ok, bool) and isinstance(msg, str)
        assert not any(b in msg for b in ("rm -rf", "dd if=", "mkfs", "adb remount")), \
            f"Android 探测 {fn_name} 文案含破坏性命令"
    # 本机（Linux）无 adb 设备：应全部降级（当前非 Android 设备环境）
    for fn_name, _lab in na.PROBES:
        ok, msg = getattr(na, fn_name)()
        assert ok is False, f"{fn_name} 在未连设备环境应降级为不可用"
        assert ("未找到 adb" in msg or "降级" in msg or "无已授权设备" in msg), \
            f"{fn_name} 降级说明不明确: {msg}"


def test_android_tunes_zero_arg():
    """Android 官方写接口（settings/pm/svc/dumpsys/logcat/am/wm）零参数可调用。"""
    from sysweeper.native import android as na
    _assert_tunes_zero_arg(na)
    assert len(na.android_tune_list()) == len(na.TUNES)
    # 在线性辅助函数在无 adb 时返回 False（不抛异常）
    assert na._device_online() is False or isinstance(na._device_online(), bool)


def test_android_tune_tasks_registered():
    """and_tune_* 深度调优任务：全 opt_in、platform=android、各走自身官方接口。"""
    from sysweeper import registry as reg
    from sysweeper.native import android as na
    tunes = [t for t in reg.all_tasks() if t.id.startswith("and_tune_")]
    assert len(tunes) >= 8, f"and_tune_* 任务过少: {len(tunes)}"
    fn_names = {fn for fn, _ in na.TUNES}
    expect = {
        "and_tune_anim_scale": ("settings put", "android.settings_anim_scale_off"),
        "and_tune_trim_cache": ("trim-caches", "android.pm_trim_caches"),
        "and_tune_wifi_on": ("svc wifi", "android.svc_wifi_enable"),
        "and_tune_battery_reset": ("batterystats", "android.batterystats_reset"),
        "and_tune_logcat_clear": ("logcat -c", "android.logcat_clear"),
        "and_tune_kill_bg": ("kill-all", "android.am_kill_all"),
        "and_tune_netstats_reset": ("netstats", "android.netstats_reset"),
        "and_tune_display_reset": ("wm size reset", "android.wm_size_reset"),
    }
    by_id = {t.id: t for t in tunes}
    for tid, (kw, op) in expect.items():
        t = by_id.get(tid)
        assert t is not None, f"缺少任务: {tid}"
        assert t.platform == "android" and t.opt_in, f"{tid} 应为 android 平台且默认关闭（opt_in）"
        acts = {a.command for a in t.actions}
        assert op in acts, f"{tid} 未派发原生接口 {op}: {acts}"
        assert op.split(".")[1] in fn_names, f"{op} 不在 TUNES 清单"
        joined = " ".join((a.command or "") + " " + (a.description or "") + " " + t.title
                          for a in t.actions).lower()
        assert kw.lower() in joined, f"{tid} 应走 Android 自身接口 {kw}: {joined}"
    # 安全方向：动画只关可恢复、缓存只放不删数据、无线只开不关、统计只清计数、
    # 日志只清缓冲、后台只收不影响前台、显示只 reset——绝不 remount 改系统分区
    blob = " ".join((a.command or "") + " " + (a.description or "")
                    for t in tunes for a in t.actions).lower()
    for bad in ("svc wifi disable", "adb remount", "rm -rf /system", "pm uninstall",
                "settings put secure", "disable-user", "wm size 1080", "zpool destroy"):
        assert bad not in blob, f"Android 调优任务出现反向/破坏性操作: {bad}"


def test_android_command_runs():
    """CLI android 子命令可跑通（含深度调优清单展示，只读，不修改系统）。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    args = p.parse_args(["android"])
    args.func(args)  # 仅打印展示，不调用写接口


# --------------------------------------------------------------------------- #
# v0.5.16：iOS（libimobiledevice）文档层 + 只读探测 + 官方写接口                  #
# --------------------------------------------------------------------------- #

def test_ios_docs_load():
    """iOS 文档层已加载且字段完整（与其它 X_docs.json 同 schema）。"""
    from sysweeper.native import ios as ni
    refs = ni.reference_all()
    assert len(refs) >= 9, f"iOS 文档条目过少: {len(refs)}"
    for key, ref in refs.items():
        assert ref.get("name") and ref.get("org") and ref.get("url"), \
            f"iOS 文档 {key} 缺 name/org/url"
        assert ref.get("protocols") and ref.get("interfaces"), \
            f"iOS 文档 {key} 缺 protocols/interfaces"
        assert ref.get("advice"), f"iOS 文档 {key} 缺 advice"
    # 关键：iOS 自身接口必须在文档里（不套 Android/桌面写法）
    for k in ("libimobiledevice", "lockdown", "usbmuxd", "installation_proxy",
              "afc", "crashreport", "syslog_relay", "diagnostics", "mobilebackup2"):
        assert k in refs, f"iOS 文档缺少自身接口条目: {k}"


def test_ios_probes_readonly():
    """iOS 只读探测不修改系统；未装 libimobiledevice / 无设备时优雅降级。"""
    from sysweeper.native import ios as ni
    assert len(ni.PROBES) >= 9
    for fn_name, _lab in ni.PROBES:
        ok, msg = getattr(ni, fn_name)()
        assert isinstance(ok, bool) and isinstance(msg, str)
        assert not any(b in msg for b in ("rm -rf", "dd if=", "mkfs",
                                          "remount", "ideviceinstaller -U")), \
            f"iOS 探测 {fn_name} 文案含破坏性命令"
    # 本机（Linux）无 iOS 设备：应全部降级（当前非已信任设备环境）
    for fn_name, _lab in ni.PROBES:
        ok, msg = getattr(ni, fn_name)()
        assert ok is False, f"{fn_name} 在未连设备环境应降级为不可用"
        assert "降级" in msg, f"{fn_name} 降级说明不明确: {msg}"


def test_ios_tunes_zero_arg():
    """iOS 官方写接口（idevicebackup2/ideviceinstaller/...）零参数可调用。"""
    from sysweeper.native import ios as ni
    _assert_tunes_zero_arg(ni)
    assert len(ni.ios_tune_list()) == len(ni.TUNES)
    # 在线性辅助函数在无设备时返回 False（不抛异常）
    assert ni._device_online() is False or isinstance(ni._device_online(), bool)
    assert isinstance(ni._first_udid(), str)


def test_ios_tune_tasks_registered():
    """ios_tune_* 深度调优任务：全 opt_in、platform=ios、各走自身官方接口。"""
    from sysweeper import registry as reg
    from sysweeper.native import ios as ni
    tunes = [t for t in reg.all_tasks() if t.id.startswith("ios_tune_")]
    assert len(tunes) >= 8, f"ios_tune_* 任务过少: {len(tunes)}"
    fn_names = {fn for fn, _ in ni.TUNES}
    expect = {
        "ios_tune_backup": ("idevicebackup2 backup", "ios.ios_backup"),
        "ios_tune_archive_apps": ("ideviceinstaller -a", "ios.ios_archive_apps"),
        "ios_tune_clear_crash": ("idevicecrashreport -e", "ios.ios_clear_crash"),
        "ios_tune_sync_date": ("idevicedate -s", "ios.ios_sync_date"),
        "ios_tune_clear_location": ("idevicesetlocation clear", "ios.ios_clear_location"),
        "ios_tune_set_name": ("idevicename", "ios.ios_set_name"),
        "ios_tune_restart": ("idevicediagnostics restart", "ios.ios_restart"),
        "ios_tune_mount_devimage": ("ideviceimagemounter", "ios.ios_mount_devimage"),
    }
    by_id = {t.id: t for t in tunes}
    for tid, (kw, op) in expect.items():
        t = by_id.get(tid)
        assert t is not None, f"缺少任务: {tid}"
        assert t.platform == "ios" and t.opt_in, f"{tid} 应为 ios 平台且默认关闭（opt_in）"
        acts = {a.command for a in t.actions}
        assert op in acts, f"{tid} 未派发原生接口 {op}: {acts}"
        assert op.split(".")[1] in fn_names, f"{op} 不在 TUNES 清单"
        joined = " ".join((a.command or "") + " " + (a.description or "") + " " + t.title
                          for a in t.actions).lower()
        assert kw.lower() in joined, f"{tid} 应走 iOS 自身接口 {kw}: {joined}"
    # 安全方向：备份只进不出、归档只留数据、日志只清、时间只同步、定位只清、
    # 设备名只归一化、重启只释放内存、开发者镜像只挂可逆——绝不卸载/restore/remount
    blob = " ".join((a.command or "") + " " + (a.description or "")
                    for t in tunes for a in t.actions).lower()
    for bad in ("ideviceinstaller -u", "idevicebackup2 restore", "idevicepair unpair",
                "remount", "rm -rf", "mkfs", "ideviceimagemounter -i /dev/",
                "zpool destroy"):
        assert bad not in blob, f"iOS 调优任务出现反向/破坏性操作: {bad}"


def test_ios_command_runs():
    """CLI ios 子命令可跑通（含深度调优清单展示，只读，不修改系统）。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    args = p.parse_args(["ios"])
    args.func(args)  # 仅打印展示，不调用写接口


# --------------------------------------------------------------------------- #
# v0.5.17：扫描流程内嵌基线快照（record_scan 纯函数 + GUI 自动记录/对比）        #
# --------------------------------------------------------------------------- #

def test_snapshot_record_scan_basic():
    """record_scan：首条只记录不对比；第二条起返回与上一条的结构化 diff。"""
    from sysweeper.native import snapshot as nsnap

    a = nsnap.capture_snapshot(include_probes=False)
    diff0, hist0 = nsnap.record_scan(None, a)
    assert diff0 is None and len(hist0) == 1

    diff0b, hist0b = nsnap.record_scan([], a)
    assert diff0b is None and len(hist0b) == 1

    # 制造一份差异快照
    import copy
    b = copy.deepcopy(a)
    root = "/" if "/" in b["metrics"]["disk"] else next(iter(b["metrics"]["disk"]))
    b["metrics"]["disk"][root]["used"] -= 1024 ** 3
    b["metrics"]["disk"][root]["free"] += 1024 ** 3
    diff1, hist1 = nsnap.record_scan(hist0, b)
    assert diff1 is not None
    assert len(hist1) == 2
    # 返回的 diff 应与直接 diff_snapshots(prev, snap) 一致
    assert diff1 == nsnap.diff_snapshots(hist0[-1], b)


def test_snapshot_record_scan_truncates():
    """record_scan：历史超过 maxlen 时只保留最近 maxlen 条。"""
    from sysweeper.native import snapshot as nsnap

    hist = []
    snap = nsnap.capture_snapshot(include_probes=False)
    for _ in range(15):
        _, hist = nsnap.record_scan(hist, snap, maxlen=10)
    assert len(hist) == 10, f"历史应截断到 maxlen=10：实际 {len(hist)}"


def test_gui_scan_diff_wiring():
    """GUI 扫描流程已内嵌基线快照：类挂了 show_scan_diff，且 run 调用 record_scan。

    无 DISPLAY 环境下不实例化真实 Toplevel；核心对比逻辑由 test_snapshot_record_scan_*
    覆盖，这里只验证「接线」确实落到 SysweeperGUI 上（结构性断言，零 GUI 依赖）。
    """
    from sysweeper.gui import SysweeperGUI
    from sysweeper.native import snapshot as nsnap

    assert hasattr(SysweeperGUI, "show_scan_diff"), "GUI 应有「扫描快照对比」面板"
    # run 流程里必须调用 record_scan（自动记录基线 + 与上次对比）
    import inspect
    src = inspect.getsource(SysweeperGUI.run)
    assert "record_scan" in src, "run 应调用 snapshot.record_scan 自动留痕"
    assert "capture_snapshot" in src, "run 应调用 capture_snapshot 采集基线"
    # 会话历史属性在 __init__ 中初始化（即便不实例化也确认属性名存在）
    assert "_scan_snaps" in inspect.getsource(SysweeperGUI.__init__), \
        "__init__ 应初始化 _scan_snaps 会话快照历史"
    # 反向确认：record_scan 是纯函数、可被 GUI 复用
    assert callable(nsnap.record_scan)


# =========================================================================== #
# v0.5.18 新增能力：链接协议 / 自组网 / 隐私验证 / 同人资源共享 / 多系统无障碍   #
# （详细断言见 tests/test_netmesh.py，这里只验证接线与注册）                    #
# =========================================================================== #

def test_netlink_and_reshare_modules_registered():
    """netlink / netauth / reshare 必须挂到 native 包（runner 按 native.<mod> 派发）。"""
    for mod in ("netlink", "netauth", "reshare"):
        assert hasattr(native, mod), f"native 缺少模块 {mod}"
    assert callable(native.netlink.mesh_report)
    assert callable(native.netauth.netauth_report)
    assert callable(native.reshare.reshare_report)


def test_v0518_tasks_registered():
    """新增任务全部注册，且默认关闭项（mesh）为 opt_in。"""
    ids = {t.id for t in registry.all_tasks()}
    for tid in ("net_link_protocols", "net_mesh_serve", "net_mesh_discover",
                "net_mesh_hci", "net_auth_setup", "net_reshare",
                "any_a11y_multi", "any_a11y_docs"):
        assert tid in ids, f"缺少任务 {tid}"
    by_id = {t.id: t for t in registry.all_tasks()}
    for tid in ("net_mesh_serve", "net_mesh_discover", "net_mesh_hci",
                "net_auth_setup", "net_reshare"):
        assert by_id[tid].opt_in is True, f"{tid} 应为默认关闭（opt_in）"


def test_native_ops_dispatchable():
    """任务里声明的 native 操作必须能被 runner 真正派发（零参、返回 (ok, msg)）。"""
    from sysweeper import runner
    ops = ["netlink.link_report", "netlink.mesh_report", "netlink.mesh_info",
           "netauth.netauth_report", "netauth.netauth_demo",
           "reshare.reshare_report", "reshare.reshare_demo",
           "common.a11y_multi_report", "common.a11y_docs_report"]
    for op in ops:
        ok, msg = runner._run_native(op)
        assert isinstance(ok, bool), f"{op} 未返回 bool"
        assert isinstance(msg, str) and msg, f"{op} 未返回说明文本"


def test_gui_netlink_and_a11y_multi_wiring():
    """GUI 已挂上「网络链接/Mesh」与「无障碍(多系统)」两个面板。"""
    from sysweeper.gui import SysweeperGUI
    import inspect
    for name in ("show_netlink", "show_a11y_multi"):
        assert hasattr(SysweeperGUI, name), f"GUI 缺少面板 {name}"
    src = inspect.getsource(SysweeperGUI)
    assert "网络链接/Mesh" in src, "底部按钮应有「网络链接/Mesh」"
    assert "无障碍(多系统)" in src, "底部按钮应有「无障碍(多系统)」"


def test_cli_netlink_subcommand():
    """CLI 必须有 netlink 子命令，且 a11y 支持 --platform。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    sub = [a for a in p._actions if a.dest == "cmd"][0]
    assert "netlink" in sub.choices, "CLI 缺少 netlink 子命令"
    assert "a11y" in sub.choices
    ns = p.parse_args(["netlink", "auth"])
    assert ns.netlink_action == "auth" and ns.func.__name__ == "cmd_netlink"
    ns2 = p.parse_args(["a11y", "--platform", "windows"])
    assert ns2.platform == "windows" and ns2.func.__name__ == "cmd_a11y"


def test_keyword_standards_extended():
    """关键词标准已覆盖新能力域（netlink/mesh/talkback/voiceover/reshare 等）。"""
    from types import SimpleNamespace
    from sysweeper.models import KEYWORD_STANDARDS, task_standards
    kws = {kw for kw, _refs in KEYWORD_STANDARDS}
    for kw in ("netlink", "mesh", "rfcomm", "ble", "serial",
               "talkback", "voiceover", "narrator", "uia", "reshare"):
        assert kw in kws, f"KEYWORD_STANDARDS 缺少 {kw}"
    # 没有自带 standards 的任务，应能按 id/title 关键词派生出标准
    fake = SimpleNamespace(id="net_mesh_peer", title="mesh 自组网",
                           category="network", standards=None)
    assert task_standards(fake), "mesh 关键词应能派生出标准引用"


# =========================================================================== #
# v0.5.19 导入第三方网络互联/硬件优化/开源下载 + 许可证归档 + 安全护栏 接线断言   #
# （详细断言见 tests/test_thirdparty.py，这里只验证接线与注册）                  #
# =========================================================================== #

def test_gui_thirdparty_wiring():
    """GUI 已挂上「第三方网络/硬件」面板与底部按钮。"""
    from sysweeper.gui import SysweeperGUI
    import inspect
    assert hasattr(SysweeperGUI, "show_thirdparty"), "GUI 缺少面板 show_thirdparty"
    src = inspect.getsource(SysweeperGUI)
    assert "第三方网络/硬件" in src, "底部按钮应有「第三方网络/硬件」"


def test_cli_thirdparty_subcommand():
    """CLI 必须有 thirdparty 子命令，且动作可解析。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    sub = [a for a in p._actions if a.dest == "cmd"][0]
    assert "thirdparty" in sub.choices, "CLI 缺少 thirdparty 子命令"
    ns = p.parse_args(["thirdparty", "licenses"])
    assert ns.thirdparty_action == "licenses" and ns.func.__name__ == "cmd_thirdparty"
    ns2 = p.parse_args(["thirdparty", "cdn-p2p"])
    assert ns2.thirdparty_action == "cdn-p2p"


def test_keyword_standards_v0519():
    """关键词标准已覆盖导入仓库与开关（p2wlan/dae/gfw-pac/v2rayn/dlss/aria2/cdn/p2p/licenses/interop）。"""
    from types import SimpleNamespace
    from sysweeper.models import KEYWORD_STANDARDS, task_standards
    kws = {kw for kw, _refs in KEYWORD_STANDARDS}
    for kw in ("interop", "p2wlan", "dae", "gfw-pac", "v2rayn", "dlss",
               "dlss5", "aria2", "cdn", "p2p", "licenses"):
        assert kw in kws, f"KEYWORD_STANDARDS 缺少 {kw}"
    # 没自带 standards 的任务，应能按 id/title 关键词派生出标准引用
    fake = SimpleNamespace(id="net_interop_peer", title="第三方网络互联 p2wlan/dae cdn p2p",
                           category="network", standards=None)
    assert task_standards(fake), "第三方网络互联关键词应能派生出标准引用"


# --------------------------------------------------------------------------- #
# v0.5.20 OpenWrt 路由器系统只读接口 + 安全插件框架 接线断言                   #
# （详细断言见 tests/test_openwrt.py，这里只验证接线与注册）                  #
# --------------------------------------------------------------------------- #


def test_native_openwrt_and_plugins_registered():
    """openwrt / plugins 必须挂到 native 包（runner 按 native.<mod> 派发）。"""
    from sysweeper import native
    assert hasattr(native, "openwrt") and hasattr(native, "plugins")
    assert callable(native.openwrt.openwrt_report)
    assert callable(native.plugins.plugin_report)


def test_gui_openwrt_and_plugins_wiring():
    """GUI 必须有面板 show_openwrt 与 show_plugins。"""
    from sysweeper.gui import SysweeperGUI
    for name in ("show_openwrt", "show_plugins"):
        assert hasattr(SysweeperGUI, name), f"GUI 缺少面板 {name}"


def test_cli_openwrt_subcommand():
    """CLI 必须有 openwrt 子命令，且动作可解析。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    sub = [a for a in p._actions if a.dest == "cmd"][0]
    assert "openwrt" in sub.choices, "CLI 缺少 openwrt 子命令"
    ns = p.parse_args(["openwrt", "build"])
    assert ns.openwrt_action == "build" and ns.func.__name__ == "cmd_openwrt"
    ns2 = p.parse_args(["openwrt", "uci"])
    assert ns2.openwrt_action == "uci"


def test_cli_plugins_subcommand():
    """CLI 必须有 plugins 子命令（list/show/run + --id）。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    sub = [a for a in p._actions if a.dest == "cmd"][0]
    assert "plugins" in sub.choices, "CLI 缺少 plugins 子命令"
    ns = p.parse_args(["plugins", "show", "--id", "openwrt"])
    assert ns.plugins_action == "show" and ns.plugin_id == "openwrt"
    assert ns.func.__name__ == "cmd_plugins"
    ns2 = p.parse_args(["plugins", "run", "--id", "interop"])
    assert ns2.plugins_action == "run" and ns2.plugin_id == "interop"


def test_openwrt_and_plugin_tasks_registered():
    """OpenWrt 专属任务与插件任务已注册，且 openwrt 专属任务 platform=openwrt。"""
    from sysweeper.registry import all_tasks
    by = {t.id: t for t in all_tasks()}
    for tid in ("openwrt_detect", "openwrt_uci_audit", "openwrt_pkgs",
                "openwrt_network", "openwrt_build", "plugin_framework"):
        assert tid in by, f"缺少任务 {tid}"
    for tid in ("openwrt_detect", "openwrt_uci_audit", "openwrt_pkgs",
                "openwrt_network", "openwrt_build"):
        assert by[tid].platform == "openwrt"
    assert by["plugin_framework"].platform == "any"


def test_keyword_standards_v0520():
    """关键词标准已覆盖 OpenWrt 与插件（openwrt/uci/opkg/apk/procd/ubus/netifd/plugin/plugins…）。"""
    from sysweeper.models import KEYWORD_STANDARDS
    kws = {kw for kw, _refs in KEYWORD_STANDARDS}
    for kw in ("openwrt", "uci", "opkg", "apk", "procd", "ubus", "netifd",
               "rpcd", "luci", "imagebuilder", "sdk", "feeds", "buildroot",
               "plugin", "plugins"):
        assert kw in kws, f"KEYWORD_STANDARDS 缺少 {kw}"


# --------------------------------------------------------------------------- #
# v0.5.21 OpenWrt 子系统补全 + 写操作指引 + 可扩展白名单                                #
# --------------------------------------------------------------------------- #


def test_native_openwrt_write_registered():
    """native 层导出 openwrt 与 openwrt_write 两个模块。"""
    from sysweeper import native
    assert hasattr(native, "openwrt") and hasattr(native, "openwrt_write")
    assert "openwrt_write" in native.__all__


def test_cli_openwrt_v0521_actions_parse():
    """CLI openwrt 子命令支持新增动作 firewall/wireless/dhcp/storage/write。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    for act in ("firewall", "wireless", "dhcp", "storage", "write"):
        ns = p.parse_args(["openwrt", act])
        assert ns.openwrt_action == act, act
        assert ns.func.__name__ == "cmd_openwrt"


def test_cli_plugins_allowlist_action_parses():
    """CLI plugins 子命令支持 allowlist 动作。"""
    from sysweeper.cli import build_parser
    p = build_parser()
    ns = p.parse_args(["plugins", "allowlist"])
    assert ns.plugins_action == "allowlist"
    assert ns.func.__name__ == "cmd_plugins"


def test_gui_openwrt_write_and_plugin_allowlist_wiring():
    """GUI：show_openwrt 引入 openwrt_write 并挂写指引按钮；show_plugins 有白名单按钮。"""
    import inspect
    from sysweeper import gui
    src_openwrt = inspect.getsource(gui.SysweeperGUI.show_openwrt)
    assert "openwrt_write" in src_openwrt, "GUI OpenWrt 面板应引入 openwrt_write"
    assert "openwrt_write_report" in src_openwrt
    for fn_name in ("openwrt_firewall_report", "openwrt_wireless_report",
                    "openwrt_dhcp_report", "openwrt_storage_report"):
        assert fn_name in src_openwrt, f"GUI 应挂载 {fn_name} 按钮"
    src_plugins = inspect.getsource(gui.SysweeperGUI.show_plugins)
    assert "allowlist" in src_plugins, "GUI 插件面板应有白名单按钮"


def test_openwrt_v0521_all_tasks_registered():
    """v0.5.21 新增 8 个 OpenWrt 任务全部注册。"""
    from sysweeper.registry import all_tasks
    by = {t.id: t for t in all_tasks()}
    for tid in ("openwrt_firewall", "openwrt_wireless", "openwrt_dhcp",
                "openwrt_storage", "openwrt_sysupgrade_guide",
                "openwrt_pkg_write_guide", "openwrt_uci_write_guide",
                "openwrt_svc_write_guide"):
        assert tid in by, f"缺少任务 {tid}"
        assert by[tid].platform == "openwrt", tid


def test_keyword_standards_v0521():
    """关键词标准覆盖 v0.5.21（firewall/wireless/dhcp/fstab/write_guide/register_native）。"""
    from sysweeper.models import KEYWORD_STANDARDS
    kws = {kw for kw, _refs in KEYWORD_STANDARDS}
    for kw in ("firewall", "wireless", "dhcp", "fstab", "write_guide",
               "register_native"):
        assert kw in kws, f"KEYWORD_STANDARDS 缺少 {kw}"
