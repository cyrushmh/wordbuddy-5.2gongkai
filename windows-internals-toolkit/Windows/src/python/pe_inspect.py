#!/usr/bin/env python3
# pe_inspect.py — 纯标准库 PE(Portable Executable) 结构解析器
# 无第三方依赖（不依赖 pefile），用于离线审计 PE 文件结构。
# 对应仓库 docs/pe_format_doc.html 与 src/c/peinfo/peinfo.c 的 Python 版。
#
# 用法:
#   python3 pe_inspect.py file.exe          # 打印完整头信息
#   python3 pe_inspect.py file.dll -v       # 含数据目录/节特征位
#   python3 pe_inspect.py file.exe --json   # 输出机器可读 JSON（便于自动化/跨语言对齐）
#   python3 pe_inspect.py self              # 解析本脚本自身（若为 PE；否则提示）
import argparse
import json
import struct
import sys

MACHINES = {
    0x14C: "x86 (Intel 386+)", 0x8664: "x64 (AMD64)", 0xAA64: "ARM64",
    0x1C0: "ARM (32-bit)", 0x14D: "ARM (Thumb/Thumb-2)", 0x200: "IA64",
    0x9041: "ARM64X",
}
SUBSYSTEMS = {
    1: "Native (驱动/系统)", 2: "Windows GUI", 3: "Windows CUI (控制台)",
    7: "POSIX", 9: "Windows CE", 10: "EFI 应用程序", 12: "EFI ROM",
}
CHAR_FLAGS = {
    0x0002: "EXECUTABLE_IMAGE", 0x2000: "DLL", 0x0100: "32BIT_MACHINE",
    0x0020: "LARGE_ADDRESS_AWARE", 0x0001: "RELOCS_STRIPPED",
    0x0080: "BYTES_REVERSED_LO", 0x0200: "DEBUG_STRIPPED",
}
SEC_FLAGS = {
    0x00000020: "CNT_CODE", 0x00000040: "CNT_INITIALIZED_DATA",
    0x00000080: "CNT_UNINITIALIZED_DATA", 0x20000000: "MEM_EXECUTE",
    0x40000000: "MEM_READ", 0x80000000: "MEM_WRITE", 0x10000000: "MEM_SHARED",
}
DATA_DIR_NAMES = ["导出表", "导入表", "资源表", "异常表", "安全表", "重定位表", "调试表",
                  "版权表", "全局指针", "TLS 表", "加载配置", "绑定导入", "IAT",
                  "延迟导入", "COM 描述符", "保留"]


def u16(b, off):
    return struct.unpack_from("<H", b, off)[0]


def u32(b, off):
    return struct.unpack_from("<I", b, off)[0]


def u64(b, off):
    return struct.unpack_from("<Q", b, off)[0]


def parse(data: bytes):
    """解析 PE 返回结构化 dict；失败时返回 (None, 错误信息)。"""
    if data[:2] != b"MZ":
        return None, "不是有效 PE：缺少 MZ 头"
    e_lfanew = u32(data, 0x3C)
    if data[e_lfanew:e_lfanew + 4] != b"PE\x00\x00":
        return None, f"不是有效 PE：偏移 0x{e_lfanew:X} 处缺少 PE\\0\\0 签名"
    off = e_lfanew + 4

    # COFF 文件头
    machine, nsec, tds, psym, nsym, size_opt, chars = struct.unpack_from("<HHIIIHH", data, off)
    opt_off = off + 20
    magic = u16(data, opt_off)
    is_pe32plus = (magic == 0x20B)
    entry = u32(data, opt_off + 16)
    num_rva = u32(data, opt_off + (108 if is_pe32plus else 92))
    if is_pe32plus:
        image_base = u64(data, opt_off + 24)
        sec_align = u32(data, opt_off + 32)
        file_align = u32(data, opt_off + 36)
        subsystem = u16(data, opt_off + 68)
        img_size = u32(data, opt_off + 56)
        hdr_size = u32(data, opt_off + 60)
        dd_off = opt_off + 112
    else:
        image_base = u32(data, opt_off + 28)
        sec_align = u32(data, opt_off + 32)
        file_align = u32(data, opt_off + 36)
        subsystem = u16(data, opt_off + 68)
        img_size = u32(data, opt_off + 56)
        hdr_size = u32(data, opt_off + 60)
        dd_off = opt_off + 96

    data_dirs = []
    for i in range(min(num_rva, 16)):
        rva = u32(data, dd_off + i * 8)
        size = u32(data, dd_off + i * 8 + 4)
        nm = DATA_DIR_NAMES[i] if i < len(DATA_DIR_NAMES) else f"#{i}"
        data_dirs.append({"index": i, "name": nm, "rva": rva, "size": size})

    sec_tbl = opt_off + size_opt
    sections = []
    for i in range(nsec):
        s = sec_tbl + i * 40
        if s + 40 > len(data):
            break
        name = data[s:s + 8].split(b"\x00")[0].decode("latin1", "ignore")
        sections.append({
            "index": i,
            "name": name,
            "virtual_size": u32(data, s + 8),
            "virtual_address": u32(data, s + 12),
            "size_of_raw_data": u32(data, s + 16),
            "pointer_to_raw_data": u32(data, s + 20),
            "characteristics": u32(data, s + 36),
        })

    return {
        "e_lfanew": e_lfanew,
        "machine": machine,
        "machine_name": MACHINES.get(machine, "未知"),
        "number_of_sections": nsec,
        "time_date_stamp": tds,
        "size_of_optional_header": size_opt,
        "characteristics": chars,
        "optional": {
            "magic": magic,
            "magic_name": "PE32+ (64位)" if is_pe32plus else "PE32 (32位)",
            "entry_point": entry,
            "image_base": image_base,
            "section_alignment": sec_align,
            "file_alignment": file_align,
            "size_of_image": img_size,
            "size_of_headers": hdr_size,
            "subsystem": subsystem,
            "subsystem_name": SUBSYSTEMS.get(subsystem, "未知"),
            "number_of_rva_and_sizes": num_rva,
        },
        "data_directories": data_dirs,
        "sections": sections,
    }, None


def to_text(d):
    lines = []
    add = lines.append
    add("=" * 52)
    add(" PE 结构解析 (Python 版)")
    add("=" * 52)
    add("[DOS 头]")
    add("  e_magic  = MZ (0x5A4D)")
    add(f"  e_lfanew = 0x{d['e_lfanew']:X}  -> NT 头位置")
    add("[COFF 文件头]")
    add(f"  Machine           = 0x{d['machine']:04X}  ({d['machine_name']})")
    add(f"  NumberOfSections  = {d['number_of_sections']}")
    add(f"  TimeDateStamp      = 0x{d['time_date_stamp']:X}")
    add(f"  SizeOfOptionalHdr = {d['size_of_optional_header']}")
    add(f"  Characteristics   = 0x{d['characteristics']:04X}")
    for bit, name in CHAR_FLAGS.items():
        if d['characteristics'] & bit:
            add(f"      {name}")
    o = d["optional"]
    add("[可选头]")
    add(f"  Magic             = 0x{o['magic']:04X}  ({o['magic_name']})")
    add(f"  EntryPoint (RVA)  = 0x{o['entry_point']:X}")
    add(f"  ImageBase         = 0x{o['image_base']:X}")
    add(f"  SectionAlignment  = 0x{o['section_alignment']:X}")
    add(f"  FileAlignment     = 0x{o['file_alignment']:X}")
    add(f"  SizeOfImage       = 0x{o['size_of_image']:X}")
    add(f"  SizeOfHeaders     = 0x{o['size_of_headers']:X}")
    add(f"  Subsystem         = {o['subsystem']}  ({o['subsystem_name']})")
    add("[数据目录]")
    for dd in d["data_directories"]:
        add(f"  [{dd['index']:2}] {dd['name']:12} RVA=0x{dd['rva']:X} Size=0x{dd['size']:X}")
    add(f"[节表]  共 {d['number_of_sections']} 节")
    for sec in d["sections"]:
        add(f"  #{sec['index']:2}  {sec['name']:8}  VSize=0x{sec['virtual_size']:05X} "
            f"VAddr=0x{sec['virtual_address']:05X} "
            f"Raw=0x{sec['size_of_raw_data']:05X}@{sec['pointer_to_raw_data']:05X}")
        if d.get("verbose"):
            fl = [n for bit, n in SEC_FLAGS.items() if sec["characteristics"] & bit]
            if fl:
                add(f"       特征: {' '.join(fl)}")
    add("=" * 52)
    add("  ✅ 这是一个结构合法的 PE 文件。")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="纯标准库 PE 结构解析器")
    ap.add_argument("path", help="PE 文件路径，或 'self' 解析本脚本")
    ap.add_argument("-v", "--verbose", action="store_true", help="打印数据目录与节特征位（文本模式）")
    ap.add_argument("--json", action="store_true", help="输出机器可读 JSON 而非文本")
    args = ap.parse_args()

    if args.path == "self":
        with open(sys.argv[0], "rb") as f:
            data = f.read()
        d, err = parse(data)
        if err:
            print("本脚本不是 PE（这是正常的，它是 .py 源文件）。请用真实 .exe/.dll 测试。")
            return
        print(json.dumps(d, ensure_ascii=False, indent=2) if args.json else to_text(d))
        return

    try:
        with open(args.path, "rb") as f:
            data = f.read()
    except OSError as e:
        print(f"无法读取文件: {e}")
        sys.exit(1)

    d, err = parse(data)
    if err:
        print(err)
        sys.exit(1)
    if args.verbose:
        d["verbose"] = True
    out = json.dumps(d, ensure_ascii=False, indent=2) if args.json else to_text(d)
    print(out)


if __name__ == "__main__":
    main()
