"""reverse：黑箱逆向与调试工具链只读层（v0.6.73）。

把 UPX/GDB/MinGW 黑箱实战沉淀为只读能力：

- ``binary_scan(path)``  —— PE/ELF 头解析 + 节区清单 + 香农熵 + UPX! 标记定位
  （纯标准库，与沙箱实测口径一致；实测基准见 data/reverse_docs.json）
- ``REVERSE_CHECKS``    —— 黑箱对照检查项（每条回链知识库 key）
- ``reverse_report()``  —— 知识总报告（无参可调用，供任务/CLI/GUI）

边界（与知识库 readonly_reverse_ethics 一致）：只读分析、只观察；
不 patch 内存、不 hook 调用、不生成任何绕过/破解手段。
所有检测函数零网络、零写入、零进程注入。
"""

from __future__ import annotations

from importlib import resources
import json
import math
import struct


def _load_refs() -> dict:
    try:
        text = (resources.files("sysweeper.data")
                .joinpath("reverse_docs.json")
                .read_text(encoding="utf-8"))
        return json.loads(text)
    except Exception:
        return {}


REFS = _load_refs()

#: 知识条目 key 序列（跳过 _note/_position 等下划线字段）
ENTRY_KEYS = tuple(k for k in REFS if not k.startswith("_"))


def reference(key: str) -> dict:
    """返回某黑箱主题的知识条目（含 protocols/interfaces/advice）。"""
    return dict(REFS.get(key, {}))


def reference_all() -> dict:
    """返回全部知识条目（跳过 _note/_position）。"""
    return {k: v for k, v in REFS.items() if not k.startswith("_")}


def reverse_doc_list() -> list:
    """返回黑箱知识清单（供 CLI/GUI 展示），逐条回链知识库。"""
    lines = []
    for key, ref in reference_all().items():
        lines.append(f"· [{key}] {ref.get('name', '')}")
        lines.append(f"    {ref.get('org', '')}")
        lines.append(f"    要点: {ref.get('advice', '')}")
    return lines


# --------------------------------------------------------------------------- #
# 黑箱扫描器（纯函数，只读文件字节；不执行、不写入、不联网）。                   #
# 与沙箱实测口径一致：二进制按 256 直方图算香农熵；                            #
# PE 走 e_lfanew→COFF→节表；UPX 识别 = UPX! marker + UPX0/1/2 节名 + 节熵。     #
# --------------------------------------------------------------------------- #

def _entropy(blob: bytes) -> float:
    """256 直方图香农熵（bits/byte，0-8）。"""
    if not blob:
        return 0.0
    freq = [0] * 256
    for x in blob:
        freq[x] += 1
    ent = 0.0
    for f in freq:
        if f:
            p = f / len(blob)
            ent -= p * math.log2(p)
    return round(ent, 3)


def _pe_sections(data: bytes) -> list | None:
    """解析 PE 节表，返回 [(name, vsize, rawsz, rawptr, entropy)]；非 PE 返回 None。"""
    if data[:2] != b"MZ" or len(data) < 0x40:
        return None
    try:
        e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
        if data[e_lfanew:e_lfanew + 4] != b"PE\x00\x00":
            return None
        coff = e_lfanew + 4
        nsec = struct.unpack_from("<H", data, coff + 2)[0]
        optsz = struct.unpack_from("<H", data, coff + 16)[0]
        magic = struct.unpack_from("<H", data, coff + 20)[0]
        pe32p = magic == 0x20B
        secbase = coff + 20 + optsz
        out = []
        for i in range(nsec):
            off = secbase + i * 40
            name = data[off:off + 8].rstrip(b"\x00").decode("ascii", "replace")
            vsize, _vaddr, rawsz, rawptr = struct.unpack_from("<IIII", data, off + 8)
            blob = data[rawptr:rawptr + rawsz]
            out.append((name, vsize, rawsz, rawptr, _entropy(blob)))
        return out, ("PE32+" if pe32p else "PE32")
    except (struct.error, ValueError, UnicodeDecodeError):
        return None


def binary_scan(path: str) -> dict:
    """黑箱只读扫描：PE/ELF 格式 + 节区清单 + 整体/节熵 + UPX! 标记。

    返回 dict：{ok, path, size, whole_entropy, format, upx_marker_offset,
               sections: [{name, vsize, rawsz, rawptr, entropy}], packed_guess}
    packed_guess：按三特征（UPX! marker / UPX* 节名 / 节熵>7.5）给保守判断，
    仅「黑箱观察结论」，不是恶意/安全判定。
    """
    out = {
        "ok": False, "path": path, "size": 0, "whole_entropy": 0.0,
        "format": "unknown", "upx_marker_offset": -1, "sections": [],
        "packed_guess": False, "error": "",
    }
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        out["error"] = f"read failed: {exc}"
        return out
    out.update(ok=True, size=len(data), whole_entropy=_entropy(data))
    upx_off = data.find(b"UPX!")
    if upx_off >= 0:
        out["upx_marker_offset"] = upx_off
    pe = _pe_sections(data)
    if pe:
        secs, fmt = pe
        out["format"] = fmt
        out["sections"] = [
            {"name": n, "vsize": vs, "rawsz": rs, "rawptr": rp, "entropy": e}
            for (n, vs, rs, rp, e) in secs]
        upx_named = [s for s in out["sections"] if s["name"].startswith("UPX")]
        hi_ent = [s for s in out["sections"] if s["entropy"] > 7.5
                  and s["rawsz"] > 0]
        out["packed_guess"] = bool(
            upx_off >= 0 or upx_named or (hi_ent and len(secs) <= 5))
    elif data[:4] == b"\x7fELF":
        machine = struct.unpack_from("<H", data, 18)[0]
        out["format"] = f"ELF(machine={machine})"
        out["packed_guess"] = out["whole_entropy"] > 7.5
    return out


# --------------------------------------------------------------------------- #
# 黑箱对照检查清单（纯函数；每项回链知识库 key，action_type=guidance）。        #
# --------------------------------------------------------------------------- #

REVERSE_CHECKS = {
    "format_identify_first": ("pe_section_anatomy",
        "黑箱第一步先认格式：MZ→PE 或 \\x7fELF，格式不明即停，不硬解",
        "notice"),
    "upx_triple_match": ("upx_packer_signature",
        "判 UPX 要三证据齐出：UPX! marker、UPX0/1/2 节名、数据节熵>7.5——单证据不下结论",
        "notice"),
    "entropy_reading": ("entropy_packing_signal",
        "逐节 + 整体两级读熵：>7.5 疑似压缩/加密载荷，<1 是常量/零页，1.5-7.0 常规",
        "info"),
    "symbol_visibility_check": ("strip_static_analysis",
        "先看 gdb info functions 能看到多少符号；本地符号缺失即改用 PLT/导入表外部面还原",
        "notice"),
    "mingw_build_sample": ("mingw_cross_toolchain",
        "需要分析 PE 样本时用 MinGW 自造可控样本，不下载来路不明二进制",
        "info"),
    "gdb_four_step": ("gdb_blackbox_basics",
        "GDB 黑箱四连：info functions → disassemble → info proc mappings（需运行期）→ break/bt",
        "notice"),
    "wine_unavailable_note": ("gdb_blackbox_basics",
        "沙箱 wine 实测启动 PE 失败（ExecuteEx failed）：PE 动态分析需目标环境，本环境走静态路径",
        "info"),
    "template_structural_reading": ("hexeditor_010_templates",
        "结构级细读两步走：binary_scan 认格式 → Binary Template 读字段；模板是人写断言，须与原始字节抽查对照",
        "info"),
    "readonly_boundary": ("readonly_reverse_ethics",
        "只读只观察：不 patch、不 hook、不生成绕过手段；目标须为自己/己方/已授权产物",
        "warn"),
}


def reverse_checklist() -> list:
    """黑箱对照检查清单（人工执行；每项回链知识库 key）。"""
    return [
        {"id": cid, "title": title, "severity": sev,
         "action_type": "guidance", "rationale": kb}
        for cid, (kb, title, sev) in REVERSE_CHECKS.items()
    ]


_SELF_POSITION = (
    "只读边界：本工具只做格式解析、节区清单、熵计算、命令模板指引——"
    "不执行目标程序、不 patch 内存、不 hook 调用、不生成注册机/破解补丁；"
    "逆向目标限自己/己方/已授权产物，判定权与授权责任在用户。"
)


def reverse_report(checks: list | None = None) -> tuple:
    """生成黑箱逆向与调试工具链知识总报告（无参可调用，供任务/CLI/GUI）。"""
    lines = [
        "== 黑箱逆向与调试工具链（只读知识库，不执行、不绕过） ==",
        "  UPX 壳识别 → 熵判据 → PE/ELF 解剖 → MinGW 造样本 → GDB 黑箱四连 →",
        "  010 Editor 模板结构细读 → strip 前后对比 → 只读边界",
    ]
    lines.append("")
    lines.append("-- 知识条目（data/reverse_docs.json："
                 f"{len(ENTRY_KEYS)} 条，沙箱实测口径）--")
    for key in ENTRY_KEYS:
        ref = REFS[key]
        lines.append(f"· [{key}] {ref.get('name', '')}")
        lines.append(f"    {ref.get('org', '')}")

    lines.append("")
    lines.append("-- 黑箱对照清单（人工执行；每项回链知识库）--")
    for i, c in enumerate(reverse_checklist(), 1):
        lines.append(f"  {i:>2}. [{c['severity']}] {c['title']}")
        lines.append(f"      依据: {c['rationale']}")

    lines.append("")
    lines.append(_SELF_POSITION)
    lines.append("工具出口：upx（github.com/upx）· gdb（sourceware.org/gdb）· "
                 "MinGW-w64（mingw-w64.org）· binutils objdump；"
                 "分析产物不出本机。")
    return True, "\n".join(lines)
