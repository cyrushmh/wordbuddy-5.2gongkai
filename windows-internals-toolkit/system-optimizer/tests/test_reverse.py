"""reverse 子系统测试（v0.6.73）：黑箱扫描器（合成 PE/ELF）+ 知识库 + 边界不变量。

沙箱实测基准（v0.6.73 固化，minGW GCC 13 / UPX 4.2.2 / GDB 15）：
- PE32+ 样本 249562B / 19 节 / 整体熵 5.898；UPX --best --lzma 后 121050B / 3 节 /
  整体熵 7.035 / UPX! @0x205 / UPX1 节熵 7.985
- PE32 样本 237482B / 17 节；UPX --best 后 126378B（53.22%）
- ELF x86-64 strip 前后 16000→14472B、熵 1.522→1.235
本文件用合成最小字节测解析器（不依赖外部二进制），实测基准以常量固化断言。"""

from __future__ import annotations

import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

from sysweeper.native import reverse as nr  # noqa: E402
from sysweeper import registry  # noqa: E402


REQUIRED_KEYS = {
    "upx_packer_signature", "entropy_packing_signal", "pe_section_anatomy",
    "mingw_cross_toolchain", "gdb_blackbox_basics", "elf_vs_pe_tradeoffs",
    "strip_static_analysis", "readonly_reverse_ethics", "rea_mcp_reverse",
    "hexeditor_010_templates",
}


def _min_pe(sec_name=b".text", raw=b"ABCD" * 64) -> bytes:
    """造最小合法 PE：MZ + e_lfanew + PE + COFF(1 节) + 可选头 + 节表。"""
    optsz = 0xE0
    coff = b"PE\x00\x00"
    coff += struct.pack("<HHIIIHH", 0x8664, 1, 0, 0, 0, optsz, 0x22)
    optional = struct.pack("<H", 0x20B) + b"\x00" * (optsz - 2)
    secs = sec_name.ljust(8, b"\x00")
    secs += struct.pack("<IIII", len(raw), 0x1000, len(raw), 0x200)
    secs += b"\x00" * 16 + struct.pack("<I", 0x60000020)
    body = coff + optional + secs
    pe_off = 0x80
    dos = b"MZ" + b"\x00" * 0x3A + struct.pack("<I", pe_off) + b"\x00" * (pe_off - 0x40)
    return dos + body.ljust(0x200, b"\x00") + raw


def test_refs_loaded_10():
    refs = nr.reference_all()
    assert set(refs) == REQUIRED_KEYS
    assert len(refs) == 10


def test_measured_baseline_frozen():
    """沙箱实测基准固化进知识条目——换口径必须显式改这里。"""
    doc = nr.reference("upx_packer_signature")
    joined = " ".join(doc["protocols"])
    for fact in ("249562", "121050", "48.50", "237482", "126378", "53.22"):
        assert fact in joined, fact
    ent = nr.reference("entropy_packing_signal")
    joined = " ".join(ent["protocols"])
    for fact in ("5.898", "7.035", "7.985", "1.522", "1.235"):
        assert fact in joined, fact


def test_scan_min_pe(tmp_path):
    p = tmp_path / "min.exe"
    p.write_bytes(_min_pe())
    r = nr.binary_scan(str(p))
    assert r["ok"] is True
    assert r["format"] == "PE32+"
    assert len(r["sections"]) == 1
    assert r["sections"][0]["name"] == ".text"
    assert r["upx_marker_offset"] == -1


def test_scan_upx_marker_detected(tmp_path):
    p = tmp_path / "packed.exe"
    blob = _min_pe()
    # 在 DOS 头后的填充区嵌入 UPX! 标记（黑箱扫描只定位不改内容）
    blob = bytearray(blob)
    blob[0x50:0x54] = b"UPX!"
    p.write_bytes(bytes(blob))
    r = nr.binary_scan(str(p))
    assert r["upx_marker_offset"] == 0x50


def test_scan_pe32_detected(tmp_path):
    p = tmp_path / "pe32.exe"
    blob = bytearray(_min_pe())
    # 可选头 magic 0x10b=PE32（COFF 起于 pe_off+4，magic 在 COFF+20）
    struct.pack_into("<H", blob, 0x80 + 4 + 20, 0x10B)
    p.write_bytes(bytes(blob))
    r = nr.binary_scan(str(p))
    assert r["format"] == "PE32"


def test_scan_elf_detected(tmp_path):
    p = tmp_path / "prog.elf"
    elf = bytearray(b"\x7fELF" + b"\x00" * 60)
    struct.pack_into("<H", elf, 18, 62)  # e_machine = x86-64
    p.write_bytes(bytes(elf))
    r = nr.binary_scan(str(p))
    assert r["format"] == "ELF(machine=62)"
    assert r["sections"] == []  # ELF 节表未展开，只认格式（诚实边界）


def test_scan_entropy_high_and_low(tmp_path):
    """高熵块（伪随机）与低熵块（常量）分居两端——判据表两端锚定。"""
    hi = tmp_path / "hi.bin"
    hi.write_bytes(bytes((i * 37 + 11) % 256 for i in range(4096)))
    lo = tmp_path / "lo.bin"
    lo.write_bytes(b"\x00" * 4096)
    r_hi = nr.binary_scan(str(hi))
    r_lo = nr.binary_scan(str(lo))
    assert r_hi["whole_entropy"] > 7.0
    assert r_lo["whole_entropy"] == 0.0
    assert r_hi["format"] == "unknown"


def test_scan_missing_file():
    r = nr.binary_scan("/nonexistent/definitely-missing.bin")
    assert r["ok"] is False
    assert r["error"]


def test_checks_link_to_refs():
    for cid, (kb, _t, sev) in nr.REVERSE_CHECKS.items():
        assert kb in REQUIRED_KEYS, (cid, kb)


def test_checklist_counts():
    cl = nr.reverse_checklist()
    assert len(cl) == len(nr.REVERSE_CHECKS) == 9
    assert all(c["action_type"] == "guidance" for c in cl)


def test_report_readonly_boundary():
    ok, rep = nr.reverse_report()
    assert ok is True
    for seg in ("UPX", "GDB", "MinGW", "只读边界", "不 patch", "不 hook"):
        assert seg in rep, seg


def test_no_execute_or_network_in_layer():
    """只读不变量：native 层不得出现执行/网络类调用。"""
    src = open(nr.__file__, encoding="utf-8").read()
    for bad in ("subprocess", "os.system", "socket.", "requests",
                "urllib", "eval(", "exec(", "pty", "ctypes"):
        assert bad not in src, bad


def test_tasks_registered():
    ids = {t.id for t in registry.all_tasks()}
    for tid in ("reverse_blackbox_scan", "reverse_entropy_reading",
                "reverse_gdb_playbook"):
        assert tid in ids, tid
    assert len({t for t in ids if t.startswith("reverse_")}) == 3


def test_task_native_actions_resolvable():
    for t in registry.all_tasks():
        if not t.id.startswith("reverse_"):
            continue
        for a in t.actions:
            if a.kind == "native":
                fn_name = a.command.split(".", 1)[1]
                assert hasattr(nr, fn_name), (t.id, fn_name)


def test_subsystem_registered():
    from sysweeper.native.subsystems import BY_KEY
    sub = BY_KEY.get("reverse")
    assert sub is not None
    assert sub.fn == "reverse_report"
    _, rep = getattr(nr, sub.fn)()
    assert "UPX" in rep


def test_axes_include_reverse():
    """reverse 不得成孤岛（联动轴接入自检）。"""
    from sysweeper.native import linkage
    keys = {a.from_key for a in linkage.AXES_EXTRA} | {
        a.to_key for a in linkage.AXES_EXTRA}
    assert "reverse" in keys
