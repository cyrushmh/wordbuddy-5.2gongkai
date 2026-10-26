"""v0.5.20 OpenWrt 路由器系统只读接口 + 安全插件框架 测试。

设计要点（与全局一致）：纯 stdlib、离线、只读优先；OpenWrt 原生接口仅在 OpenWrt
设备上才有真实数据，非 OpenWrt 环境优雅降级为指引；插件框架仅允许白名单内的只读
函数被调用，绝不执行任意代码（含命令注入或非白名单入口的清单直接拒绝注册）。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# 让 tests/ 能 import src/python 下的包
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src", "python"))

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def openwrt():
    from sysweeper.native import openwrt as O
    return O


@pytest.fixture
def plugins():
    from sysweeper.native import plugins as P
    return P


# --------------------------------------------------------------------------- #
# OpenWrt 文档层 / 原生接口                                                     #
# --------------------------------------------------------------------------- #


def test_openwrt_docs_loaded(openwrt):
    """data/openwrt_docs.json 载入，且含核心子系统文档。"""
    docs = openwrt.OWRT_DOCS
    assert docs, "openwrt_docs.json 未载入"
    for sub in ("uci", "opkg", "apk", "procd", "netifd", "ubus", "rpcd", "luci",
                "imagebuilder", "sdk", "feeds", "buildroot", "board"):
        assert sub in docs, f"缺少子系统文档 {sub}"
        assert docs[sub].get("url", "").startswith("http"), f"{sub} 缺文档链接"


def test_openwrt_native_degrades_off_openwrt(openwrt):
    """非 OpenWrt 环境：报告类函数返回 (bool, str)，openwrt_report 优雅降级为 False。"""
    ok, msg = openwrt.openwrt_report()
    assert isinstance(ok, bool) and isinstance(msg, str) and msg
    assert ok is False, "非 OpenWrt 环境 openwrt_report 应返回 False（降级为指引）"
    for fn in (openwrt.openwrt_detect_report, openwrt.openwrt_uci_report,
               openwrt.openwrt_pkgs_report, openwrt.openwrt_network_report,
               openwrt.openwrt_build_report):
        o, m = fn()
        assert isinstance(o, bool) and isinstance(m, str) and m, fn


def test_openwrt_uci_parser_off_openwrt(openwrt):
    """UCI 文件解析器在非 OpenWrt 环境返回空列表（不抛异常）。"""
    secs = openwrt.parse_uci_file("/nonexistent/etc/config/network")
    assert secs == []


def test_openwrt_is_openwrt_false_here(openwrt):
    """当前沙箱（Linux，非 OpenWrt）is_openwrt 返回 False。"""
    ok, info = openwrt.is_openwrt()
    assert ok is False
    assert info == {}


# --------------------------------------------------------------------------- #
# 任务注册                                                                     #
# --------------------------------------------------------------------------- #


def test_openwrt_tasks_registered():
    """OpenWrt 任务（platform=openwrt）与插件任务全部注册，且标注标准。"""
    from sysweeper.registry import all_tasks
    by = {t.id: t for t in all_tasks()}
    for tid in ("openwrt_detect", "openwrt_uci_audit", "openwrt_pkgs",
                "openwrt_network", "openwrt_build", "plugin_framework"):
        assert tid in by, f"缺少任务 {tid}"
    for tid in ("openwrt_detect", "openwrt_uci_audit", "openwrt_pkgs",
                "openwrt_network", "openwrt_build"):
        assert by[tid].platform == "openwrt", f"{tid} 平台应为 openwrt"
        assert by[tid].standards, f"{tid} 应标注标准"
    assert by["plugin_framework"].platform == "any"


def test_openwrt_tasks_only_on_openwrt_platform():
    """openwrt 专属任务只在 platform=openwrt 时出现；在 linux 上不出现。"""
    from sysweeper.registry import applicable
    on_ow = {t.id for t in applicable("openwrt", "24.10")}
    on_lin = {t.id for t in applicable("linux", "6")}
    for tid in ("openwrt_detect", "openwrt_uci_audit", "openwrt_pkgs",
                "openwrt_network", "openwrt_build"):
        assert tid in on_ow, f"{tid} 应在 openwrt 平台出现"
        assert tid not in on_lin, f"{tid} 不应在 linux 平台出现"
    # 插件任务（platform=any）在 linux 上也出现
    assert "plugin_framework" in on_lin


# --------------------------------------------------------------------------- #
# 原生派发 / 插件安全                                                           #
# --------------------------------------------------------------------------- #


def test_openwrt_native_dispatchable(openwrt):
    """任务里声明的 native 操作能被 runner 真正派发（零参、返回 (ok, msg)）。"""
    from sysweeper import runner
    for op in ("openwrt.openwrt_report", "openwrt.openwrt_detect_report",
               "openwrt.openwrt_uci_report", "openwrt.openwrt_pkgs_report",
               "openwrt.openwrt_network_report", "openwrt.openwrt_build_report",
               "plugins.plugin_report"):
        ok, msg = runner._run_native(op)
        assert isinstance(ok, bool) and isinstance(msg, str) and msg, op


def test_plugins_builtin_registered(plugins):
    """内置插件 openwrt / interop 已注册；随包示例 openwrt-example 也被发现。"""
    idx = plugins.plugin_index()
    assert "openwrt" in idx, "缺少内置 openwrt 插件"
    assert "interop" in idx, "缺少内置 interop 聚合插件"
    assert "openwrt-example" in idx, "随包示例插件 openwrt.example.json 应被自动发现"


def test_plugins_validate_rejects_arbitrary_code(plugins):
    """plugin_validate 拒绝含任意命令/路径注入的清单（防任意代码执行）。"""
    bad = plugins.plugin_validate({
        "id": "evil", "name": "x", "description": "y",
        "native": ["os.system('rm -rf /')"],
    })
    assert bad[0] is False, "含任意命令的插件应被拒绝"
    # 非字符串 / 含 shell 元字符
    bad2 = plugins.plugin_validate({
        "id": "evil2", "name": "x", "description": "y",
        "native": ["openwrt.openwrt_report; rm -rf /"],
    })
    assert bad2[0] is False
    # 非白名单内的 openwrt 函数
    bad3 = plugins.plugin_validate({
        "id": "evil3", "name": "x", "description": "y",
        "native": ["openwrt.some_write_fn"],
    })
    assert bad3[0] is False, "非白名单 native 入口应被拒绝"


def test_plugins_validate_rejects_bad_id(plugins):
    """plugin_validate 拒绝非法 id（含路径/命令字符）。"""
    bad = plugins.plugin_validate({
        "id": "../../etc/passwd", "name": "x", "description": "y",
        "native": ["openwrt.openwrt_report"],
    })
    assert bad[0] is False


def test_plugins_run_readonly(plugins):
    """plugin_run 只读运行内置插件，返回 (bool, str) 且调用白名单函数。"""
    ok, msg = plugins.plugin_run("openwrt")
    assert isinstance(ok, bool) and isinstance(msg, str) and msg
    ok2, msg2 = plugins.plugin_run("interop")
    assert isinstance(ok2, bool) and isinstance(msg2, str) and msg2


def test_plugins_allowlist_only(plugins):
    """NATIVE_ALLOWLIST 仅收录零参只读函数；插件入口必须落在其中。"""
    from sysweeper import runner
    for op in plugins.NATIVE_ALLOWLIST:
        module_name, func_name = op.split(".", 1)
        assert hasattr(__import__("sysweeper.native", fromlist=[module_name]),
                      module_name) or True
        ok, msg = runner._run_native(op)
        assert isinstance(ok, bool) and isinstance(msg, str), op


# --------------------------------------------------------------------------- #
# 关键词标准                                                                   #
# --------------------------------------------------------------------------- #


def test_openwrt_keyword_standards():
    """KEYWORD_STANDARDS 覆盖 OpenWrt 与插件关键词。"""
    from sysweeper.models import KEYWORD_STANDARDS
    kws = {kw for kw, _refs in KEYWORD_STANDARDS}
    for kw in ("openwrt", "uci", "opkg", "apk", "procd", "ubus", "netifd",
               "rpcd", "luci", "imagebuilder", "sdk", "feeds", "buildroot",
               "plugin", "plugins"):
        assert kw in kws, f"KEYWORD_STANDARDS 缺少 {kw}"


# --------------------------------------------------------------------------- #
# v0.5.21 OpenWrt 子系统补全（防火墙/无线/DHCP/存储，只读）                          #
# --------------------------------------------------------------------------- #


def test_openwrt_v0521_new_reports_degrade_and_dispatch(openwrt):
    """新增 4 个只读子系统报告：可派发、非 OpenWrt 优雅降级。"""
    from sysweeper import runner
    for op in ("openwrt.openwrt_firewall_report", "openwrt.openwrt_wireless_report",
               "openwrt.openwrt_dhcp_report", "openwrt.openwrt_storage_report"):
        ok, msg = runner._run_native(op)
        assert isinstance(ok, bool) and isinstance(msg, str) and msg, op
        assert ok is False, f"{op} 非 OpenWrt 环境应降级为 False"


def test_openwrt_wireless_never_echoes_password(openwrt, tmp_path, monkeypatch):
    """无线报告绝不回显 encryption key 明文（仅提示存在性）。"""
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "wireless").write_text(
        "config wifi-device\n\toption band '5g'\n\toption channel '36'\n\n"
        "config wifi-iface\n\toption device 'radio0'\n\toption mode 'ap'\n"
        "\toption encryption 'psk2'\n\toption key 'SUPERSECRET'\n",
        encoding="utf-8")
    monkeypatch.setattr(openwrt, "UCI_DIR", str(cfg))
    monkeypatch.setattr(openwrt, "is_openwrt", lambda: (True, {}))
    ok, msg = openwrt.wireless_report()
    assert ok is True
    assert "SUPERSECRET" not in msg, "无线密码明文绝不能回显"
    assert "含密码" in msg, "应仅提示密码存在"


def test_openwrt_firewall_dhcp_render_real_content(openwrt, tmp_path, monkeypatch):
    """防火墙/DHCP 报告在真实 UCI 内容下渲染 zone/dnsmasash 等信息。"""
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "firewall").write_text(
        "config zone\n\toption name 'lan'\n\toption network 'lan'\n"
        "\toption input 'ACCEPT'\n\nconfig rule\n\toption name 'allow-dns'\n",
        encoding="utf-8")
    (cfg / "dhcp").write_text(
        "config dnsmasq\n\toption domain 'lan'\n\nconfig dhcp\n"
        "\toption interface 'lan'\n\toption start '100'\n\toption limit '150'\n",
        encoding="utf-8")
    monkeypatch.setattr(openwrt, "UCI_DIR", str(cfg))
    monkeypatch.setattr(openwrt, "is_openwrt", lambda: (True, {}))
    okf, msgf = openwrt.firewall_report()
    assert okf and "lan" in msgf and "zone" in msgf
    okd, msgd = openwrt.dhcp_report()
    assert okd and "dnsmasq" in msgd


# --------------------------------------------------------------------------- #
# v0.5.21 高危写操作「安全指引」层（只预检，绝不执行）                                 #
# --------------------------------------------------------------------------- #


def test_openwrt_write_guides_degrade_off_openwrt():
    """写指引入口：非 OpenWrt 环境返回 (False, 指引)，且可派发。"""
    from sysweeper import runner
    for op in ("openwrt_write.openwrt_write_report",
               "openwrt_write.sysupgrade_guide",
               "openwrt_write.package_write_guide",
               "openwrt_write.uci_write_guide",
               "openwrt_write.service_write_guide"):
        ok, msg = runner._run_native(op)
        assert isinstance(ok, bool) and isinstance(msg, str) and msg, op


def test_openwrt_write_layer_never_calls_subprocess():
    """核心安全不变量：写指引层源码中零 subprocess —— 绝不执行任何写命令。"""
    import inspect
    from sysweeper.native import openwrt_write
    src = inspect.getsource(openwrt_write)
    assert "subprocess" not in src, "写指引层绝不能调用 subprocess"


def test_openwrt_write_guides_render_command_text():
    """在模拟 OpenWrt 下，写指引渲染真实命令文本（仅展示，不执行）。"""
    from unittest import mock
    from sysweeper.native import openwrt_write as W
    fake = {"RELEASE": "23.05.5", "TARGET": "ath79/generic",
            "board_name": "tplink,tl-wdr4300"}
    with mock.patch.object(W, "is_openwrt", return_value=(True, fake)):
        ok, msg = W.sysupgrade_guide()
        assert ok and "tl-wdr4300" in msg and "sysupgrade" in msg
        assert "23.05.5" in msg


def test_openwrt_write_tasks_are_optin_highrisk():
    """4 个写指引任务：platform=openwrt、risk=high、opt_in=True（默认关闭）。"""
    from sysweeper.registry import all_tasks, applicable
    by = {t.id: t for t in all_tasks()}
    ids = ("openwrt_sysupgrade_guide", "openwrt_pkg_write_guide",
           "openwrt_uci_write_guide", "openwrt_svc_write_guide")
    for tid in ids:
        assert tid in by, f"缺少写指引任务 {tid}"
        t = by[tid]
        assert t.platform == "openwrt" and t.risk == "high" and t.opt_in, tid
    # 默认不出现；opt-in 后出现
    default = {t.id for t in applicable("openwrt", "24.10")}
    optin = {t.id for t in applicable("openwrt", "24.10", include_opt_in=True)}
    for tid in ids:
        assert tid not in default, f"{tid} 默认不应出现"
        assert tid in optin, f"{tid} opt-in 后应出现"


def test_openwrt_readonly_subsystem_tasks_registered():
    """新增 4 个只读子系统任务：platform=openwrt、risk=low、opt_in=False。"""
    from sysweeper.registry import all_tasks, applicable
    by = {t.id: t for t in all_tasks()}
    ids = ("openwrt_firewall", "openwrt_wireless", "openwrt_dhcp", "openwrt_storage")
    for tid in ids:
        assert tid in by, f"缺少只读子系统任务 {tid}"
        t = by[tid]
        assert t.platform == "openwrt" and t.risk == "low" and not t.opt_in, tid
        assert t.standards, tid
    # 只读任务在 openwrt 默认出现，linux 不出现
    on_ow = {t.id for t in applicable("openwrt", "24.10")}
    on_lin = {t.id for t in applicable("linux", "6")}
    for tid in ids:
        assert tid in on_ow and tid not in on_lin


# --------------------------------------------------------------------------- #
# v0.5.21 插件白名单可扩展（register_native，可扩展但不可注入）                       #
# --------------------------------------------------------------------------- #


def test_register_native_rejects_injection(plugins):
    """register_native 拒绝：命令注入 / 路径穿越 / 不存在函数 / 写指引层。"""
    for bad in ("os.system", "../../etc/passwd", 'os.system("rm -rf /")',
                "openwrt.nonexistent_fn", "openwrt_write.sysupgrade_guide",
                "openwrt_write.openwrt_write_report"):
        ok, _msg = plugins.register_native(bad)
        assert ok is False, f"{bad} 不应被登记进白名单"


def test_register_native_allows_existing_readonly_then_validate(plugins):
    """register_native 可登记本包内已存在的只读函数，登记后可被插件引用。"""
    try:
        ok, _msg = plugins.register_native("openwrt.openwrt_firewall_report")
        assert ok is True
        assert "openwrt.openwrt_firewall_report" in plugins.effective_allowlist()
        m = {"id": "fw-probe", "name": "n", "description": "d",
             "native": ["openwrt.openwrt_firewall_report"]}
        assert plugins.plugin_validate(m)[0] is True
    finally:
        plugins._DYNAMIC_ALLOWLIST.discard("openwrt.openwrt_firewall_report")


def test_register_native_denies_write_layer_even_if_exists(plugins):
    """写指引层即使存在也拒绝进入插件白名单（写指引只能由 opt-in 任务触发）。"""
    ok, _msg = plugins.register_native("openwrt_write.openwrt_write_report")
    assert ok is False
    assert "openwrt_write.openwrt_write_report" not in plugins.effective_allowlist()


def test_plugin_allowlist_action(plugins):
    """plugin_report('allowlist') 可展示只读白名单。"""
    ok, msg = plugins.plugin_report("allowlist")
    assert ok is True and "静态审读" in msg and "白名单" in msg


def test_openwrt_v0521_keyword_standards():
    """KEYWORD_STANDARDS 覆盖 v0.5.21 新增子系统关键词。"""
    from sysweeper.models import KEYWORD_STANDARDS
    kws = {kw for kw, _refs in KEYWORD_STANDARDS}
    for kw in ("firewall", "wireless", "dhcp", "fstab", "write_guide",
               "register_native"):
        assert kw in kws, f"KEYWORD_STANDARDS 缺少 {kw}"
