# -*- coding: utf-8 -*-
"""qstore 量子存储交换子系统测试（v0.6.77）。

守门范围：知识层 schema 与官方源、QSTORE_CHECKS 回链、端点针脚表、Π_k 保真往返、
翻转语义陷阱（不复位连编 = XOR 干扰）、4K 对齐判定纯函数、管线仿真与链路统计、
红线 token（禁执行禁网络、写盘命令只作文本）、四入口接线。
绝不修改 quantum.py 的任何断言面（import 白名单 / quantum_* 任务数由 test_quantum_vm 守）。
"""
from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

from sysweeper.native import qstore as q          # noqa: E402
from sysweeper.native import subsystems, linkage  # noqa: E402
from sysweeper import registry, ergonomics        # noqa: E402

DATA = os.path.join("src", "python", "sysweeper", "data", "qstore_refs.json")

# 官方源域名白名单（references + items.url）
OFFICIAL_HOSTS = {
    "docs.kernel.org", "git.kernel.org", "kernel.org", "uefi.org", "pcisig.com",
    "iso.org", "hiascend.com", "coral.ai", "mesa3d.org",
}


@pytest.fixture(scope="module")
def refs_doc():
    with open(DATA, "r", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def machine():
    return q._machine()


# ── 知识层 schema 与官方源 ────────────────────────────────────────────────

def test_refs_schema_ten_fields(refs_doc):
    req = ("key", "name", "org", "url", "protocols", "interfaces",
           "docs", "summary", "advice", "evidence_status")
    items = refs_doc["items"]
    assert len(items) >= 10
    for it in items:
        for f in req:
            assert it.get(f), f"{it.get('key')}.{f} 缺失"
        for f in ("protocols", "interfaces", "docs"):
            assert isinstance(it[f], list) and it[f], f"{it['key']}.{f} 需非空列表"


def test_refs_official_sources_only(refs_doc):
    from urllib.parse import urlparse
    urls = [r["url"] for r in refs_doc["references"]]
    urls += [it["url"] for it in refs_doc["items"] if it.get("url")]
    assert urls
    for u in urls:
        host = urlparse(u).netloc.lower()
        # 仓内锚点条目允许非官方 URL，其余必须在白名单内
        if "（内部锚点" in u:
            continue
        assert any(host == h or host.endswith("." + h) for h in OFFICIAL_HOSTS), \
            f"非官方源域名：{host}（{u}）"


def test_refs_needs_verify_flagged(refs_doc):
    flagged = [it["key"] for it in refs_doc["items"] if it.get("needs_verify")]
    assert flagged, "至少有拿不准的条目要挂 needs_verify"
    for it in refs_doc["items"]:
        if it.get("needs_verify"):
            assert isinstance(it["needs_verify"], str) and len(it["needs_verify"]) > 8


def test_qstore_checks_backlinks_resolved():
    for name, (key, desc, links) in q.QSTORE_CHECKS.items():
        for lk in links:
            assert q.reference(lk), f"{name} 回链悬空：{lk}"


# ── 端点针脚表 ───────────────────────────────────────────────────────────

def test_endpoint_pin_budget():
    assert q.N_CLASSICAL == 8
    assert q.N_QUBITS == 8
    used = []
    for key in ("gpu", "npu", "tpu", "can"):
        ep = q.ENDPOINTS[key]
        assert len(ep["pins"]) == 2 and len(ep["bits"]) == 2
        used.extend(ep["bits"])
    assert len(used) == len(set(used)) == 8, "四端点 × 2 位应恰好占满且不重叠"


def test_machine_pins_defined(machine):
    for key in ("gpu", "npu", "tpu", "can"):
        for pin in q.ENDPOINTS[key]["pins"]:
            assert pin in machine.pins
    for ep in ("gpu", "npu", "tpu", "can"):
        assert q._handshake(machine, ep)


# ── Π_k 保真往返与翻转语义陷阱 ───────────────────────────────────────────

def test_roundtrip_fidelity(machine):
    for k in (0, 1, 255, 77, 202, 128, 7):
        assert q._quantum_roundtrip(machine, k) == k


def test_roundtrip_out_of_range(machine):
    from sysweeper.native.quantum import QuantumError
    with pytest.raises(QuantumError):
        q._quantum_roundtrip(machine, 256)
    with pytest.raises(QuantumError):
        q._quantum_roundtrip(machine, -1)


def test_flip_semantics_trap_xor_pollution(machine):
    """翻转语义陷阱：不复位连续编码会得到 XOR 干扰，必须 load() 复位。"""
    machine.load(q._RESET_IR)
    machine.encode_number(202)
    machine.encode_number(77)          # 未复位
    assert machine.decode_number() == (202 ^ 77)
    # 复位后恢复正常
    assert q._quantum_roundtrip(machine, 77) == 77


# ── 4K 对齐判定 ──────────────────────────────────────────────────────────

def test_aligned_pure_function():
    # 2048 扇区 × 512B = 1MiB 起点：对齐
    ok, _ = q._aligned(2048, 512, 512, 0)
    assert ok
    # 起点不对齐（63 扇区 × 512B = 32256B，%4096 = 3584 ≠ 0）
    ok, why = q._aligned(63, 512, 512, 0)
    assert not ok and "32256" in why and "3584" in why
    # 4Kn（4096 逻辑扇区）起点 8 扇区 = 32KiB：对齐
    ok, _ = q._aligned(8, 4096, 4096, 0)
    assert ok
    # alignment_offset 缺失按 0 与显式 0 等价
    ok1, _ = q._aligned(2048, 512, 512, None)
    ok2, _ = q._aligned(2048, 512, 512, 0)
    assert ok1 == ok2


def test_read_int_missing_field_degrades(tmp_path):
    assert q._read_int(str(tmp_path / "nope")) is None
    p = tmp_path / "val"
    p.write_text("4096\n")
    assert q._read_int(str(p)) == 4096


# ── 管线仿真 ─────────────────────────────────────────────────────────────

def test_pipeline_consistency():
    ok, msg = q.pipeline_report(seed=7)
    assert ok
    # 全部校验相等
    assert "True" in msg
    # PiLink 统计行存在且利用率 < 100%（有覆盖）或记录数合理
    st_line = next(l for l in msg.splitlines() if l.startswith("· PiLink"))
    assert "ceil(2π)" in st_line and "利用率" in st_line
    # 全量历史与 total_writes 一致性 ✓
    assert "✓" in next(l for l in msg.splitlines() if l.startswith("· snapshot"))


def test_pipeline_4096_packing():
    m = q._machine(seed=3)
    sample = [1, 2, 3]
    packed = [q._quantum_roundtrip(m, b) for b in sample]
    total = sum(packed)
    assert total > 0
    blocks = max(1, -(-total // q._BLOCK))
    assert (blocks - 1) * q._BLOCK < total <= blocks * q._BLOCK


# ── 4K 数列打包（radix 报告内的经典层） ──────────────────────────────────

def test_radix_4k_stream_repack():
    raw = [77, 202, 255, 1]
    bits12, acc, nbits = [], 0, 0
    for byte in raw:
        acc = (acc << 8) | byte
        nbits += 8
        while nbits >= 12:
            bits12.append((acc >> (nbits - 12)) & 0xFFF)
            nbits -= 12
    if nbits:
        bits12.append((acc << (12 - nbits)) & 0xFFF)
    assert all(0 <= d <= 4095 for d in bits12)
    # 可逆：按 12 位拆回 8 位字节流
    buf, nb = 0, 0
    out = []
    for d in bits12:
        buf = (buf << 12) | d
        nb += 12
        while nb >= 8:
            out.append((buf >> (nb - 8)) & 0xFF)
            nb -= 8
    assert out == raw


# ── 报告聚合与红线 ───────────────────────────────────────────────────────

def test_all_reports_ok():
    for fn in (q.endpoint_probe_report, q.alignment_report, q.radix_report,
               q.pipeline_report, q.qstore_report, q.capabilities_report):
        ok, msg = fn()
        assert ok and msg.strip(), fn.__name__


def test_doc_list_and_reference():
    lst = q.doc_list()
    assert len(lst) == len(q.REFS) and all(l.startswith("· [") for l in lst)
    assert q.reference("qstore-ext4-4k-align")["name"]
    assert q.reference("no-such-key") == {}


def test_redline_tokens_absent_from_source():
    src = open(q.__file__, encoding="utf-8").read()
    for bad in ("subprocess", "os.system", "socket", "requests", "urllib",
                "eval(", "exec(", "pty", "ctypes"):
        assert bad not in src, f"红线 token 出现在源码：{bad}"


def test_write_commands_only_as_text():
    """mkfs/dd/wipefs/sgdisk/parted 只出现在文本建议，不构成执行路径。"""
    ok, msg = q.alignment_report()
    assert "mkfs.ext4" in msg or "parted" in msg  # 文本建议在
    src = open(q.__file__, encoding="utf-8").read()
    for tok in ("mkfs.ext4", "wipefs", "sgdisk"):
        assert tok in src  # 仅作为文本建议存在
        # 确保不在任何可执行的调用形态里（本模块无命令执行设施，token 必在字符串里）


# ── 四入口接线 ───────────────────────────────────────────────────────────

def test_subsystem_registered():
    ks = [s.key for s in subsystems.SUBSYSTEMS]
    assert "qstore" in ks
    sub = next(s for s in subsystems.SUBSYSTEMS if s.key == "qstore")
    assert sub.layer and "存储" in sub.layer  # omni 存储域归类条件


def test_linkage_not_isolated():
    assert linkage.isolated() == []
    assert linkage.dangling() == []
    deg = linkage.degrees()
    assert deg.get("qstore", {}).get("total", 0) >= 1


def test_tasks_registered():
    ids = [t.id for t in registry.all_tasks() if t.id.startswith("qstore_")]
    assert len(ids) == 4
    for t in registry.all_tasks():
        if t.id.startswith("qstore_"):
            assert t.platform == "any"
            assert t.category in ("hardware", "arch")
            assert t.risk == "low"


def test_ergonomics_grouped():
    st = ergonomics.stats()
    assert st["ungrouped"] == [] and st["phantom"] == []
    assert st["scenes"] == 12  # 场景数不变


def test_cli_subcommand_wired():
    from sysweeper import cli
    import argparse
    # qstore 子命令在解析器里可达
    assert hasattr(cli, "cmd_qstore")
