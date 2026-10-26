"""网络与组网「概念系统」测试（v0.6.57+，CLI 子命令 `netsys`）。

覆盖四轴重组只读层（concepts/netsys）与三条硬性不变量：
  · RFC 依据真实性 —— 模块引用的每个 RFC 编号都能在**本仓库 rfc_catalog** 中查到；
  · 无悬空轴      —— 依赖/互补关系的两端模块都必须存在；
  · 红线齐备      —— 每个模块都必须声明红线（越界防线）。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "python"))

from sysweeper.concepts import netsys as ns  # noqa: E402
from sysweeper.native import rfc_catalog as rfc  # noqa: E402

BUILD = ROOT / "research" / "netsys" / "build_netsys.py"


def test_info_and_stats():
    m = ns.info()
    assert m["system_root"] == "wordbuddy-github"
    s = ns.stats()
    assert s["module_total"] == 64
    assert s["layer_count"] == 8
    assert s["form_count"] == 12
    assert s["nature_count"] == 7
    assert s["relation_count"] == 41
    assert s["depends_count"] == 10
    assert s["complements_count"] == 31


def test_axes_complete():
    """四轴的取值必须齐备（层次含 overlay/mesh，形态含分布式/匿名，性质含 7 类）。"""
    assert {l["layer"] for l in ns.layers()} == {"L1", "L2", "L3", "L4", "L5-6",
                                                 "L7", "overlay", "mesh"}
    assert {f["form"] for f in ns.forms()} == {"standalone", "lan", "mesh",
                                               "overlay", "sdwan", "distributed",
                                               "anonymous", "wan", "arch", "hw",
                                               "gaia", "swarm"}
    assert {n["nature"] for n in ns.natures()} == {"diagnose", "tune", "communicate",
                                                   "share", "audit", "discover",
                                                   "reference"}


def test_form_mesh_and_nature_audit():
    assert {"netlink", "meshchat", "netauth", "reshare", "radio",
            "batman-adv", "mesh-routing", "lldp-topo",
            "wireguard-mesh", "sysmesh"} == set(ns.by_form("mesh"))
    # 审计类：原有 remote/tls13/cert/netauth/apctrl + 深化补 quic（QUIC 态势审计）
    assert {"remote", "tls13", "cert", "netauth", "apctrl", "quic"} == set(
        ns.by_nature("audit"))
    # 调优类只有 network（默认关闭、需 opt-in）——写操作面必须极窄
    assert ns.by_nature("tune") == ["network"]


def test_of_distjob_dependencies():
    m = ns.of("distjob")
    assert m["nature"] == "share"
    assert {d["id"] for d in m["depends_detail"]} == {"distcompute", "meshchat"}
    assert "mesh" in m["layers"] and "distributed" in m["forms"]
    assert "复算校验" in m["redline"]


def test_no_dangling_relations():
    """关系两端必须都是已登记模块（悬空轴会让重组视图静默失效）。"""
    ids = {m["id"] for m in ns.modules()}
    for r in ns.relations():
        assert r["from"] in ids and r["to"] in ids, f"悬空轴：{r}"


def test_every_module_has_redline():
    for m in ns.modules():
        assert m.get("redline"), f"{m['id']} 缺红线声明"
    assert len(ns.redlines()) == 64


def test_every_rfc_ref_exists_in_rfc_catalog():
    """硬性不变量：模块引用的每个 RFC 编号都必须能在 rfc_catalog 中查到。"""
    seen = set()
    checked = 0
    for m in ns.modules():
        for s in m.get("standards", []):
            if s.get("kind") != "RFC":
                continue
            if s["num"] in seen:
                continue
            seen.add(s["num"])
            assert rfc.rfc_info(s["num"]) is not None, \
                f"RFC {s['num']}（{m['id']}）不在 rfc_catalog 中"
            checked += 1
    assert checked >= 15, f"RFC 依据过少：{checked}"


def test_of_unknown_returns_none():
    assert ns.of("__nonexistent__") is None
    assert ns.standards_of("__nonexistent__") == []
    assert ns.rfc_refs("__nonexistent__") == []


def test_build_netsys_check_passes():
    """build_netsys.py --check 应零错误（RFC 命中 + 轴合法 + 无悬空轴 + 红线齐备）。"""
    r = subprocess.run([sys.executable, str(BUILD), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_deepened_modules():
    """v0.6.57+ 深化补全的 5 个真实模块：id/层次/性质/互补端点/真实 RFC 依据齐备。"""
    expect = {
        "nat":    (["L3", "L4"], "diagnose", ["meshnet"], [5389, 5766, 8445]),
        "dhcp":   (["L3", "L7"], "diagnose", ["dnshealth"], [2131, 8415]),
        "mdns":   (["L7"], "discover", ["ipp"], [6762, 6763]),
        "quic":   (["L4"], "audit", ["tls13"], [9000]),
        "vxlan":  (["L2", "overlay"], "diagnose", ["meshnet", "zerotier"], [7348]),
    }
    ids = {m["id"] for m in ns.modules()}
    for mid, (layers, nature, comps, rfcs) in expect.items():
        m = ns.of(mid)
        assert m is not None, f"深化模块缺失：{mid}"
        assert m["layers"] == layers, f"{mid} 层次不符"
        assert m["nature"] == nature, f"{mid} 性质不符"
        assert set(m["complements"]) == set(comps), f"{mid} 互补端点不符"
        for c in comps:
            assert c in ids, f"{mid} 互补端点悬空：{c}"
        got = sorted(s["num"] for s in m["rfc_refs"])
        assert got == sorted(rfcs), f"{mid} RFC 依据不符：{got}"
        for n in rfcs:
            assert rfc.rfc_info(n) is not None, f"{mid} RFC {n} 不在 rfc_catalog"


def test_imported_okskills_modules():
    """v0.6.64 续导入 openKylin skills 仓库的 2 个模块：reference 性质 + 只读红线。"""
    # UKUI 桌面小插件：第三方项目作只读引用登记（不打包二进制/不安装）
    w = ns.of("ukui-desktop-widget")
    assert w is not None and w["nature"] == "reference"
    assert w["layers"] == ["L7"] and w["forms"] == ["standalone"]
    assert "metadata.json" in w["redline"] and "不安装" in w["redline"]
    # Quick Share ↔ AirDrop：近场直传与 meshchat 互补（同为设备间传输），但只读登记
    q = ns.of("quickshare-airdrop")
    assert q is not None and q["nature"] == "reference"
    assert set(q["complements"]) == {"meshchat"}
    assert "蓝牙" in q["redline"] and "不经手" in q["redline"]
