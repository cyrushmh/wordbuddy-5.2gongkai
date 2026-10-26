"""系统统筹总览（v0.6.18）测试：你中有我，我中有你；统筹系统与局部；只读红线。"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

from sysweeper.native import sysmap
from sysweeper import native as native_pkg


def test_sysmap_report_returns_tuple():
    ok, msg = sysmap.sysmap_report()
    assert isinstance(ok, bool) and isinstance(msg, str) and msg
    # 四段结构齐全
    for seg in ("整体健康汇总", "局部本征状态", "你中有我", "统筹建议"):
        assert seg in msg, f"总览缺少段落：{seg}"


def test_sysmap_report_redline_no_write():
    ok, msg = sysmap.sysmap_report()
    assert "只读" in msg
    assert "不启停" in msg
    assert "不写状态" in msg or "不写入任何状态" in msg


def test_sysmap_classify():
    # 不适用：报告明示未安装（无论 ok 与否）
    assert sysmap._classify(False, "未安装 tor") == "不适用"
    assert sysmap._classify(True, "tor 未安装（可跳过）") == "不适用"
    assert sysmap._classify(True, "本机为常规 Linux，非 Windows Subsystem") == "不适用"
    # 正常：ok 且无告警措辞
    assert sysmap._classify(True, "已诊断：接口 eth0 正常") == "正常"
    # 提示：ok 但含告警/风险措辞
    assert sysmap._classify(True, "检测到警告：解析延迟偏高") == "提示"
    assert sysmap._classify(True, "风险：NTSync 内核过低") == "提示"


def test_sysmap_probes_reference_real_funcs():
    # 每个探测项都指向真实存在的只读函数（防「引用了不存在的函数」）
    for key, label, layer, mod_name, fn_name in sysmap.PROBES:
        mod = getattr(native_pkg, mod_name, None)
        assert mod is not None, f"模块不存在：{mod_name}"
        fn = getattr(mod, fn_name, None)
        assert callable(fn), f"函数不可调用：{mod_name}.{fn_name}"


def test_sysmap_relations_present():
    # 你中有我：至少覆盖网络↔DNS、Tor↔ZeroTier、Proton↔GPU 等关键耦合
    pairs = {(a, b) for a, b, _ in sysmap.RELATIONS}
    assert ("网络接口/路由", "DNS 解析") in pairs or ("DNS 解析", "网络接口/路由") in pairs
    assert ("Tor 覆盖层", "ZeroTier 虚拟组网") in pairs
    assert ("Proton 兼容层", "虚拟化/GPU") in pairs
    # v0.6.19 新增耦合：KaihongOS⊂OpenHarmony 生态、图像编解码⇄浏览器/发行版
    assert ("KaihongOS 发行版", "发行版能力") in pairs
    assert ("图像编解码能力", "浏览器引擎") in pairs
    assert len(sysmap.RELATIONS) >= 12


def test_sysmap_new_probes_v0619():
    # v0.6.19 新增探针已纳入统筹总览：KaihongOS 发行版 + 图像编解码能力
    probes = {(k, lab, mod, fn) for k, lab, _layer, mod, fn in sysmap.PROBES}
    assert ("kaihong", "KaihongOS 发行版", "harmony", "kaihong_report") in probes
    assert ("imagefmt", "图像编解码能力", "media", "image_capability_report") in probes


def test_capabilities_report_redline():
    ok, msg = sysmap.capabilities_report()
    assert isinstance(ok, bool) and isinstance(msg, str) and msg
    assert "红线" in msg
    # 列出可编排的子系统
    for _, label, _, _, _ in sysmap.PROBES[:3]:
        assert label in msg
