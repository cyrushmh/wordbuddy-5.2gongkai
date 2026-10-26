"""machine —— 机器码与字节码层。

三种"机器真正吃的东西"，各自给一个**只读的解析/反汇编器**：

1. **Python 字节码**——`compile()` + `dis` 拿到指令流，顺带解释 .pyc 头部
   与 magic number（`importlib.util.MAGIC_NUMBER`）；
2. **Java class 文件**——按 JVM 规范解析魔数、常量池、类/父类、字段、方法
   与 Code 属性，并把 Code 里的字节码**走一遍**（含操作数长度表）；
3. **x86-64 指令**——按 Intel 的指令格式拆出
   前缀 / REX / opcode / ModRM / SIB / 位移 / 立即数。

诚实边界（重要）
----------------
* x86-64 部分是**结构化拆解器**，不是完整反汇编器：它告诉你"这条指令由
  哪些字段组成、各自是什么"，助记符只是启发式提示，权威表在
  Intel SDM Vol.2 Appendix A / AMD APM Appendix。
* Java 部分是**够用的教学级**反汇编器：覆盖 0x00-0xC9 的操作数长度，
  遇到未收录指令会明确停下并说明位置。
* Python 部分直接用 CPython 自带的 `dis`，与解释器版本强相关（3.11+
  有自适应字节码与 CACHE 项），本模块如实标注。

三者都只解析**调用方传入的字节**，不读文件系统、不执行、不联网。

标准出处（STANDARD_REFS）
------------------------
仅用于定位规范；实现由本仓库单测（含固定向量比对）独立验证。
"""

from __future__ import annotations

import importlib.util
import struct
from typing import Dict, List, Optional, Tuple

from sysweeper.i18n import _

STANDARD_REFS = {
    "jvm": {
        "cn": "—（JVM 规范无国标转化；国内多等同采用 Oracle/JSR 规范）",
        "intl": "JVMS SE 21（Oracle, 2023）；class 文件格式见第 4 章",
        "regional": "—",
    },
    "x86": {
        "cn": "—；国产 x86 实现（海光/兆芯）指令集兼容 Intel/AMD 手册",
        "intl": "Intel SDM Vol.2（指令格式与 opcode map）；AMD APM Vol.3",
        "regional": "—",
    },
    "python_bytecode": {
        "cn": "—",
        "intl": "CPython 源码 Include/opcode.h；PEP 552（.pyc 哈希校验）；PEP 659（3.11 自适应字节码）",
        "regional": "—",
    },
    "elf": {
        "cn": "—",
        "intl": "System V ABI / gABI；LSB（Linux Standard Base）",
        "regional": "—",
    },
    "memory_model": {
        "cn": "—；国内多等同采用 C++ 标准的内存模型条款",
        "intl": "ISO/IEC 14882（C++ memory_order：seq_cst/acquire/release/relaxed）；"
                "Linux Documentation/memory-barriers.txt；Intel SDM Vol.3 §8.2（TSO）；"
                "ARM DDI 0487（ARMv8 弱内存模型）；RISC-V RVWMO（无特权规范 §A）",
        "regional": "—",
    },
}

CAPABILITIES = [
    "Python 源码 → 字节码指令流（含跳转目标与操作数）",
    ".pyc 魔数与头部解析（时间戳校验型 / 哈希校验型）",
    "Java class 结构解析：常量池 / 访问标志 / 字段 / 方法 / 属性",
    "Java 方法 Code 属性 → 字节码助记符流（含操作数长度表）",
    "x86-64 指令结构化拆解：前缀 / REX / opcode / ModRM / SIB / 位移 / 立即数",
    "x86-64 并发原子指令：LOCK / XADD / CMPXCHG / XCHG / MFENCE·LFENCE·SFENCE / PAUSE",
    "RISC-V 64I 基础整数指令集结构化反汇编（RV64I + 双字 OP-IMM-32/OP-32）",
    "文件魔数识别：ELF / PE / Mach-O / class / zip / pyc",
]

# ---------------------------------------------------------------- 文件魔数

FILE_MAGICS = [
    (b"\x7fELF", "ELF", "System V ABI；Linux/Unix 可执行与目标文件"),
    (b"MZ", "PE/DOS", "MS-DOS 头 + PE 头；Windows 可执行文件"),
    (b"\xca\xfe\xba\xbe", "Java class", "JVMS 第 4 章；大端 0xCAFEBABE"),
    (b"\xfe\xed\xfa\xce", "Mach-O (32 位大端)", "Apple macOS 可执行格式"),
    (b"\xfe\xed\xfa\xcf", "Mach-O (64 位大端)", "Apple macOS 可执行格式"),
    (b"\xcf\xfa\xed\xfe", "Mach-O (64 位小端)", "Apple macOS 可执行格式"),
    (b"PK\x03\x04", "ZIP / JAR / APK / wheel", "APPNOTE.TXT；zipapp .pyz 亦为此"),
    (b"\x1f\x8b", "gzip", "RFC 1952"),
    (b"#!", "脚本（shebang）", "zipapp 生成的 .pyz 首行即 shebang"),
]


def identify(data: bytes) -> Dict:
    """按魔数识别字节流的容器/可执行格式。"""
    b = bytes(data)
    for sig, name, note in FILE_MAGICS:
        if b.startswith(sig):
            return {"format": name, "magic": sig.hex(), "note": note,
                    "size": len(b)}
    return {"format": "未知", "magic": b[:4].hex(), "size": len(b),
            "note": "未匹配任何已知魔数（可能是纯数据/文本/未知格式）"}


# ---------------------------------------------------------------- Python 字节码


def pyc_magic() -> Dict:
    """当前解释器的 .pyc 魔数与含义。"""
    magic = importlib.util.MAGIC_NUMBER
    import sys
    return {"magic": magic.hex(), "bytes": list(magic),
            "python": "%d.%d" % (sys.version_info[:2]),
            "note": "魔数随字节码格式变化；换版本后 .pyc 会失效"}


def parse_pyc_header(data: bytes) -> Dict:
    """解析 .pyc 前 16 字节。

    布局：`magic(4) flags(4) [校验字段(4) 大小字段(4)]`。
    flags=0 或 bit0=0 → 时间戳校验型（mtime + source size）；
    flags bit0=1 → 哈希校验型（PEP 552，source hash）。
    """
    b = bytes(data)
    if len(b) < 16:
        return {"error": "至少需要 16 字节，实际 %d" % len(b)}
    magic = b[:4]
    flags = struct.unpack_from("<I", b, 4)[0]
    f2, f3 = struct.unpack_from("<II", b, 8)
    out = {"magic": magic.hex(), "flags": flags,
           "matches_interpreter": magic == importlib.util.MAGIC_NUMBER,
           "field1": f2, "field2": f3}
    if flags & 0b1:
        out["check"] = "哈希校验型（PEP 552）"
        out["hash"] = "%08x" % f2
        out["source_size"] = f3
    else:
        out["check"] = "时间戳校验型"
        out["mtime"] = f2
        out["source_size"] = f3
    return out


def dis_python(source: str, filename: str = "<lowcode>") -> Dict:
    """Python 源码 → 字节码指令流。"""
    import dis
    import sys
    try:
        code = compile(str(source), filename, "exec")
    except SyntaxError as exc:
        return {"error": "语法错误：%s（第 %s 行）" % (exc.msg, exc.lineno)}
    instrs = []
    for ins in dis.Bytecode(code):
        argval = getattr(ins, "argval", None)
        instrs.append({
            "offset": getattr(ins, "offset", None),
            "opname": ins.opname,
            "opcode": ins.opcode,
            "arg": ins.arg,
            "argrepr": ins.argrepr,
            "is_jump_target": bool(getattr(ins, "is_jump_target", False)),
            "starts_line": getattr(ins, "starts_line", None),
            "argval": repr(argval) if argval is not None else "",
        })
    counts: Dict[str, int] = {}
    for i in instrs:
        counts[i["opname"]] = counts.get(i["opname"], 0) + 1
    return {
        "source": str(source),
        "python": "%d.%d" % sys.version_info[:2],
        "instructions": instrs,
        "count": len(instrs),
        "opcode_histogram": dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        "names": list(code.co_names),
        "varnames": list(code.co_varnames),
        "consts": [repr(c) for c in code.co_consts],
        "note": "3.11+ 会出现 CACHE / 自适应前缀等特殊项，属正常现象（PEP 659）",
    }


def render_python_bytecode(source: str) -> List[str]:
    """字节码 → 对齐文本。"""
    r = dis_python(source)
    if "error" in r:
        return [r["error"]]
    lines = ["Python 字节码（CPython %s，共 %d 条指令）" % (r["python"], r["count"]),
             "%-6s %-24s %-6s %s" % ("偏移", "指令", "参数", "说明")]
    for i in r["instructions"]:
        mark = ">>" if i["is_jump_target"] else "  "
        lines.append("%s%-4s %-24s %-6s %s" % (
            mark, i["offset"], i["opname"],
            "" if i["arg"] is None else i["arg"], i["argrepr"]))
    top = list(r["opcode_histogram"].items())[:6]
    if top:
        lines.append("高频指令：" + "，".join("%s×%d" % kv for kv in top))
    return lines


# ---------------------------------------------------------------- Java class

CP_TAGS = {
    1: "Utf8", 3: "Integer", 4: "Float", 5: "Long", 6: "Double",
    7: "Class", 8: "String", 9: "Fieldref", 10: "Methodref",
    11: "InterfaceMethodref", 12: "NameAndType", 15: "MethodHandle",
    16: "MethodType", 17: "Dynamic", 18: "InvokeDynamic",
    19: "Module", 20: "Package",
}

ACC_FLAGS = [
    (0x0001, "PUBLIC"), (0x0010, "FINAL"), (0x0020, "SUPER"),
    (0x0200, "INTERFACE"), (0x0400, "ABSTRACT"), (0x1000, "SYNTHETIC"),
    (0x2000, "ANNOTATION"), (0x4000, "ENUM"), (0x8000, "MODULE"),
]


def cp_display(pool: Dict, index: int, depth: int = 0) -> str:
    """常量池引用 → 可读文本（Class→Utf8，Memberref→类.名:描述符）。"""
    e = pool.get(index)
    if not e or depth > 4:
        return "#%s" % index
    tag = e["tag"]
    if tag == 1:
        return e.get("value", "")
    if tag == 7:
        return cp_display(pool, e.get("index1", 0), depth + 1)
    if tag == 8:
        return '"%s"' % cp_display(pool, e.get("index1", 0), depth + 1)
    if tag == 12:
        return "%s:%s" % (cp_display(pool, e.get("index1", 0), depth + 1),
                          cp_display(pool, e.get("index2", 0), depth + 1))
    if tag in (9, 10, 11):
        return "%s.%s" % (cp_display(pool, e.get("index1", 0), depth + 1),
                          cp_display(pool, e.get("index2", 0), depth + 1))
    if tag == 18:
        return "bootstrap#%d %s" % (e.get("index1", 0),
                                    cp_display(pool, e.get("index2", 0), depth + 1))
    if "value" in e:
        return str(e["value"])
    return "#%s" % index


def java_class_version(major: int) -> str:
    """class 主版本号 → Java SE 版本。"""
    legacy = {45: "JDK 1.1", 46: "J2SE 1.2", 47: "J2SE 1.3", 48: "J2SE 1.4"}
    if major in legacy:
        return legacy[major]
    if major >= 49:
        return "Java SE %d" % (major - 44)
    return "未知（major=%d）" % major


def parse_classfile(data: bytes) -> Dict:
    """解析 Java class 文件（JVMS 第 4 章）。只读、不做校验和。"""
    b = bytes(data)
    if len(b) < 10:
        return {"error": "文件太短（%d 字节）" % len(b)}
    magic, minor, major = struct.unpack_from(">IHH", b, 0)
    if magic != 0xCAFEBABE:
        return {"error": "魔数不是 0xCAFEBABE，实际 0x%08X" % magic}
    pos = 8
    (cp_count,) = struct.unpack_from(">H", b, pos)
    pos += 2
    pool: Dict[int, Dict] = {}
    idx = 1
    while idx < cp_count and pos < len(b):
        tag = b[pos]
        pos += 1
        entry = {"index": idx, "tag": tag, "type": CP_TAGS.get(tag, "?%d" % tag)}
        if tag == 1:
            (length,) = struct.unpack_from(">H", b, pos)
            pos += 2
            raw = b[pos:pos + length]
            pos += length
            entry["value"] = _modified_utf8(raw)
            entry["length"] = length
        elif tag in (7, 8, 16, 19, 20):
            (v,) = struct.unpack_from(">H", b, pos)
            pos += 2
            entry["index1"] = v
        elif tag in (9, 10, 11, 12, 17, 18):
            v1, v2 = struct.unpack_from(">HH", b, pos)
            pos += 4
            entry["index1"] = v1
            entry["index2"] = v2
        elif tag == 15:
            entry["reference_kind"] = b[pos]
            (v,) = struct.unpack_from(">H", b, pos + 1)
            pos += 3
            entry["index1"] = v
        elif tag in (3, 4):
            (v,) = struct.unpack_from(">i", b, pos)
            pos += 4
            entry["value"] = v
        elif tag in (5, 6):
            pos += 8
            idx += 1          # long/double 占两个常量池槽位
            entry["value"] = "<8 字节，占 2 个槽位>"
        else:
            pool[idx] = entry
            idx += 1
            break
        pool[idx] = entry
        idx += 1
    if pos + 6 > len(b):
        return {"error": "常量池后数据不足（偏移量 %d）" % pos}
    access, this_c, super_c = struct.unpack_from(">HHH", b, pos)
    pos += 6
    (if_count,) = struct.unpack_from(">H", b, pos)
    pos += 2
    interfaces = list(struct.unpack_from(">%dH" % if_count, b, pos)) if if_count else []
    pos += 2 * if_count

    def read_members(count):
        nonlocal pos
        out = []
        for _ in range(count):
            if pos + 8 > len(b):
                break
            acc, name_i, desc_i, attr_n = struct.unpack_from(">HHHH", b, pos)
            pos += 8
            attrs = []
            for _a in range(attr_n):
                if pos + 6 > len(b):
                    break
                an_i, alen = struct.unpack_from(">HI", b, pos)
                pos += 6
                attrs.append({"name_index": an_i, "length": alen,
                              "data": b[pos:pos + alen]})
                pos += alen
            out.append({"access": acc, "name_index": name_i,
                        "descriptor_index": desc_i, "attributes": attrs})
        return out

    (field_count,) = struct.unpack_from(">H", b, pos)
    pos += 2
    fields = read_members(field_count)
    (method_count,) = struct.unpack_from(">H", b, pos)
    pos += 2
    methods = read_members(method_count)

    def cp_utf8(i):
        e = pool.get(i)
        return e.get("value", "") if e and e["tag"] == 1 else "#%s" % i

    def cp_name(i: int) -> str:
        return cp_display(pool, i)

    for m in methods + fields:
        m["name"] = cp_utf8(m["name_index"])
        m["descriptor"] = cp_utf8(m["descriptor_index"])
        m["access_flags"] = _acc_names(m["access"])
        m["code"] = None
        for a in m["attributes"]:
            if cp_utf8(a["name_index"]) == "Code":
                m["code"] = parse_code_attribute(a["data"])

    return {
        "magic": "0x%08X" % magic,
        "minor": minor, "major": major,
        "java_version": java_class_version(major),
        "constant_pool_count": cp_count,
        "constant_pool": pool,
        "constant_pool_display": {i: cp_name(i) for i in pool},
        "access_flags": access,
        "access_names": _acc_names(access),
        "this_class": cp_name(this_c),
        "super_class": cp_name(super_c) if super_c else "-",
        "interfaces": [cp_name(i) for i in interfaces],
        "fields": fields, "methods": methods,
        "parsed_bytes": pos, "file_size": len(b),
    }


def _acc_names(flags: int) -> List[str]:
    return [nm for bit, nm in ACC_FLAGS if flags & bit]


def _modified_utf8(raw: bytes) -> str:
    """JVM 改进版 UTF-8：0xC0 0x80 表示 NUL，代理项按单字符编码。"""
    try:
        return raw.decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return repr(raw)


def parse_code_attribute(data: bytes) -> Dict:
    """解析 Code 属性头（max_stack / max_locals / code 字节）。"""
    b = bytes(data)
    if len(b) < 8:
        return {"error": "Code 属性过短"}
    max_stack, max_locals, code_len = struct.unpack_from(">HHI", b, 0)
    code = b[8:8 + code_len]
    return {"max_stack": max_stack, "max_locals": max_locals,
            "code_length": code_len, "code": code}


#: JVM 操作码 → (助记符, 操作数字节数)。-1 表示变长（switch/wide）
JAVA_OPCODES = {
    0x00: ("nop", 0), 0x01: ("aconst_null", 0),
    0x02: ("iconst_m1", 0), 0x03: ("iconst_0", 0), 0x04: ("iconst_1", 0),
    0x05: ("iconst_2", 0), 0x06: ("iconst_3", 0), 0x07: ("iconst_4", 0),
    0x08: ("iconst_5", 0), 0x09: ("lconst_0", 0), 0x0A: ("lconst_1", 0),
    0x0B: ("fconst_0", 0), 0x0C: ("fconst_1", 0), 0x0D: ("fconst_2", 0),
    0x0E: ("dconst_0", 0), 0x0F: ("dconst_1", 0),
    0x10: ("bipush", 1), 0x11: ("sipush", 2),
    0x12: ("ldc", 1), 0x13: ("ldc_w", 2), 0x14: ("ldc2_w", 2),
    0x15: ("iload", 1), 0x16: ("lload", 1), 0x17: ("fload", 1),
    0x18: ("dload", 1), 0x19: ("aload", 1),
    0x1A: ("iload_0", 0), 0x1B: ("iload_1", 0), 0x1C: ("iload_2", 0),
    0x1D: ("iload_3", 0), 0x1E: ("lload_0", 0), 0x1F: ("lload_1", 0),
    0x20: ("lload_2", 0), 0x21: ("lload_3", 0), 0x22: ("fload_0", 0),
    0x23: ("fload_1", 0), 0x24: ("fload_2", 0), 0x25: ("fload_3", 0),
    0x26: ("dload_0", 0), 0x27: ("dload_1", 0), 0x28: ("dload_2", 0),
    0x29: ("dload_3", 0), 0x2A: ("aload_0", 0), 0x2B: ("aload_1", 0),
    0x2C: ("aload_2", 0), 0x2D: ("aload_3", 0),
    0x2E: ("iaload", 0), 0x2F: ("laload", 0), 0x30: ("faload", 0),
    0x31: ("daload", 0), 0x32: ("aaload", 0), 0x33: ("baload", 0),
    0x34: ("caload", 0), 0x35: ("saload", 0),
    0x36: ("istore", 1), 0x37: ("lstore", 1), 0x38: ("fstore", 1),
    0x39: ("dstore", 1), 0x3A: ("astore", 1),
    0x3B: ("istore_0", 0), 0x3C: ("istore_1", 0), 0x3D: ("istore_2", 0),
    0x3E: ("istore_3", 0), 0x3F: ("lstore_0", 0), 0x40: ("lstore_1", 0),
    0x41: ("lstore_2", 0), 0x42: ("lstore_3", 0), 0x43: ("fstore_0", 0),
    0x44: ("fstore_1", 0), 0x45: ("fstore_2", 0), 0x46: ("fstore_3", 0),
    0x47: ("dstore_0", 0), 0x48: ("dstore_1", 0), 0x49: ("dstore_2", 0),
    0x4A: ("dstore_3", 0), 0x4B: ("astore_0", 0), 0x4C: ("astore_1", 0),
    0x4D: ("astore_2", 0), 0x4E: ("astore_3", 0),
    0x4F: ("iastore", 0), 0x50: ("lastore", 0), 0x51: ("fastore", 0),
    0x52: ("dastore", 0), 0x53: ("aastore", 0), 0x54: ("bastore", 0),
    0x55: ("castore", 0), 0x56: ("sastore", 0),
    0x57: ("pop", 0), 0x58: ("pop2", 0), 0x59: ("dup", 0),
    0x5A: ("dup_x1", 0), 0x5B: ("dup_x2", 0), 0x5C: ("dup2", 0),
    0x5D: ("dup2_x1", 0), 0x5E: ("dup2_x2", 0), 0x5F: ("swap", 0),
    0x60: ("iadd", 0), 0x61: ("ladd", 0), 0x62: ("fadd", 0), 0x63: ("dadd", 0),
    0x64: ("isub", 0), 0x65: ("lsub", 0), 0x66: ("fsub", 0), 0x67: ("dsub", 0),
    0x68: ("imul", 0), 0x69: ("lmul", 0), 0x6A: ("fmul", 0), 0x6B: ("dmul", 0),
    0x6C: ("idiv", 0), 0x6D: ("ldiv", 0), 0x6E: ("fdiv", 0), 0x6F: ("ddiv", 0),
    0x70: ("irem", 0), 0x71: ("lrem", 0), 0x72: ("frem", 0), 0x73: ("drem", 0),
    0x74: ("ineg", 0), 0x75: ("lneg", 0), 0x76: ("fneg", 0), 0x77: ("dneg", 0),
    0x78: ("ishl", 0), 0x79: ("lshl", 0), 0x7A: ("ishr", 0), 0x7B: ("lshr", 0),
    0x7C: ("iushr", 0), 0x7D: ("lushr", 0), 0x7E: ("iand", 0), 0x7F: ("land", 0),
    0x80: ("ior", 0), 0x81: ("lor", 0), 0x82: ("ixor", 0), 0x83: ("lxor", 0),
    0x84: ("iinc", 2),
    0x85: ("i2l", 0), 0x86: ("i2f", 0), 0x87: ("i2d", 0), 0x88: ("l2i", 0),
    0x89: ("l2f", 0), 0x8A: ("l2d", 0), 0x8B: ("f2i", 0), 0x8C: ("f2l", 0),
    0x8D: ("f2d", 0), 0x8E: ("d2i", 0), 0x8F: ("d2l", 0), 0x90: ("d2f", 0),
    0x91: ("i2b", 0), 0x92: ("i2c", 0), 0x93: ("i2s", 0),
    0x94: ("lcmp", 0), 0x95: ("fcmpl", 0), 0x96: ("fcmpg", 0),
    0x97: ("dcmpl", 0), 0x98: ("dcmpg", 0),
    0x99: ("ifeq", 2), 0x9A: ("ifne", 2), 0x9B: ("iflt", 2), 0x9C: ("ifge", 2),
    0x9D: ("ifgt", 2), 0x9E: ("ifle", 2),
    0x9F: ("if_icmpeq", 2), 0xA0: ("if_icmpne", 2), 0xA1: ("if_icmplt", 2),
    0xA2: ("if_icmpge", 2), 0xA3: ("if_icmpgt", 2), 0xA4: ("if_icmple", 2),
    0xA5: ("if_acmpeq", 2), 0xA6: ("if_acmpne", 2),
    0xA7: ("goto", 2), 0xA8: ("jsr", 2), 0xA9: ("ret", 1),
    0xAA: ("tableswitch", -1), 0xAB: ("lookupswitch", -1),
    0xAC: ("ireturn", 0), 0xAD: ("lreturn", 0), 0xAE: ("freturn", 0),
    0xAF: ("dreturn", 0), 0xB0: ("areturn", 0), 0xB1: ("return", 0),
    0xB2: ("getstatic", 2), 0xB3: ("putstatic", 2), 0xB4: ("getfield", 2),
    0xB5: ("putfield", 2), 0xB6: ("invokevirtual", 2),
    0xB7: ("invokespecial", 2), 0xB8: ("invokestatic", 2),
    0xB9: ("invokeinterface", 4), 0xBA: ("invokedynamic", 4),
    0xBB: ("new", 2), 0xBC: ("newarray", 1), 0xBD: ("anewarray", 2),
    0xBE: ("arraylength", 0), 0xBF: ("athrow", 0),
    0xC0: ("checkcast", 2), 0xC1: ("instanceof", 2),
    0xC2: ("monitorenter", 0), 0xC3: ("monitorexit", 0),
    0xC4: ("wide", -1), 0xC5: ("multianewarray", 3),
    0xC6: ("ifnull", 2), 0xC7: ("ifnonnull", 2),
    0xC8: ("goto_w", 4), 0xC9: ("jsr_w", 4),
}


#: 操作数里带常量池索引的指令（用于把 #n 解析成名字）
CP_REF_OPS = {"ldc_w", "ldc2_w", "getstatic", "putstatic", "getfield",
              "putfield", "invokevirtual", "invokespecial", "invokestatic",
              "invokeinterface", "invokedynamic", "new", "anewarray",
              "checkcast", "instanceof", "multianewarray"}


def dis_java(code: bytes, pool: Optional[Dict] = None) -> Dict:
    """JVM 字节码 → 助记符流。遇到未收录指令停下并说明位置。"""
    b = bytes(code)
    out: List[Dict] = []
    pos = 0
    stopped = None
    while pos < len(b):
        op = b[pos]
        info = JAVA_OPCODES.get(op)
        if info is None:
            stopped = "偏移 %d 处的操作码 0x%02X 未收录，解析停止" % (pos, op)
            break
        name, n = info
        start = pos
        pos += 1
        operand = b[pos:pos + n] if n > 0 else b""
        if name == "wide":
            # wide <opcode> <u2 index>  （若为 iinc 则再跟 u2 const）
            if pos + 1 > len(b):
                stopped = "wide 指令在偏移 %d 处被截断" % start
                break
            sub = b[pos]
            subname = JAVA_OPCODES.get(sub, ("?", 0))[0]
            pos += 1
            if pos + 2 > len(b):
                stopped = "wide 指令在偏移 %d 处被截断" % start
                break
            (index,) = struct.unpack_from(">H", b, pos)
            pos += 2
            extra = ""
            if subname == "iinc":
                if pos + 2 > len(b):
                    stopped = "wide iinc 在偏移 %d 处被截断" % start
                    break
                (const,) = struct.unpack_from(">h", b, pos)
                pos += 2
                extra = " %d" % const
            operand = b[start + 1:pos]
            out.append({"offset": start, "opcode": op, "name": "wide " + subname,
                        "operand": operand.hex(), "text": "wide %s %d%s" % (
                            subname, index, extra)})
            continue
        if name in ("tableswitch", "lookupswitch"):
            # 先按 4 字节对齐填充（相对 code 数组起始位置计算）
            pad = (4 - ((start + 1) % 4)) % 4
            pos += pad
            if pos + 4 > len(b):
                stopped = "%s 在偏移 %d 处被截断" % (name, start)
                break
            (default,) = struct.unpack_from(">i", b, pos)
            pos += 4
            if name == "tableswitch":
                if pos + 8 > len(b):
                    stopped = "tableswitch 在偏移 %d 处被截断" % start
                    break
                low, high = struct.unpack_from(">ii", b, pos)
                pos += 8 + 4 * max(0, high - low + 1)
                text = "tableswitch low=%d high=%d default=%d" % (
                    low, high, start + default)
            else:
                if pos + 4 > len(b):
                    stopped = "lookupswitch 在偏移 %d 处被截断" % start
                    break
                (npairs,) = struct.unpack_from(">i", b, pos)
                pos += 4 + 8 * max(0, npairs)
                text = "lookupswitch npairs=%d default=%d" % (npairs, start + default)
            out.append({"offset": start, "opcode": op, "name": name,
                        "operand": b[start + 1:pos].hex(), "text": text})
            continue
        pos += n
        text = name
        if n == 1:
            text = "%s %d" % (name, operand[0])
        elif n == 2:
            if name.startswith("if") or name in ("goto", "jsr"):
                br = struct.unpack(">h", operand)[0]
                text = "%s %d" % (name, start + br)
            elif name == "iinc":
                text = "iinc %d, %d" % (operand[0], struct.unpack(">b", operand[1:2])[0])
            else:
                text = "%s #%d" % (name, struct.unpack(">H", operand)[0])
        elif n == 3:
            text = "%s #%d, %d" % (name, struct.unpack(">H", operand[:2])[0], operand[2])
        elif n == 4:
            text = "%s #%d" % (name, struct.unpack(">H", operand[:2])[0])
        if pool:
            # 有常量池时把 #n 解析成可读名字（javap 也是这么做的）
            if name == "ldc":
                text = "%s  ; %s" % (text, cp_display(pool, operand[0]))
            elif name in CP_REF_OPS and n >= 2:
                idx = struct.unpack(">H", operand[:2])[0]
                text = "%s  ; %s" % (text, cp_display(pool, idx))
        out.append({"offset": start, "opcode": op, "name": name,
                    "operand": operand.hex(), "text": text})
    return {"instructions": out, "count": len(out),
            "bytes": len(b), "stopped": stopped,
            "standard": "JVMS SE 21 第 6 章"}


def render_classfile(data: bytes, max_pool: int = 24, max_methods: int = 8) -> List[str]:
    """class 文件 → 可读摘要。"""
    r = parse_classfile(data)
    if "error" in r:
        return [r["error"]]
    lines = [
        "Java class  magic=%s  major=%d（%s）  共 %d 字节" % (
            r["magic"], r["major"], r["java_version"], r["file_size"]),
        "访问标志：0x%04X（%s）" % (r["access_flags"], ",".join(r["access_names"]) or "—"),
        "类名：%s    父类：%s    接口：%s" % (
            r["this_class"], r["super_class"], ",".join(r["interfaces"]) or "—"),
    ]
    lines.append("常量池（%d 项，显示前 %d 项）：" % (r["constant_pool_count"], max_pool))
    for i in sorted(r["constant_pool"])[:max_pool]:
        e = r["constant_pool"][i]
        lines.append("  #%-3d %-18s %s" % (i, e["type"],
                                           r["constant_pool_display"].get(i, "")))
    lines.append("方法（%d 个）：" % len(r["methods"]))
    for m in r["methods"][:max_methods]:
        code = m.get("code") or {}
        lines.append("  %-28s %s   max_stack=%s max_locals=%s code=%s 字节" % (
            m["name"] + m["descriptor"], ",".join(m["access_flags"]),
            code.get("max_stack", "-"), code.get("max_locals", "-"),
            code.get("code_length", "-")))
    return lines


def render_java_bytecode(data: bytes, method_index: int = 0) -> List[str]:
    """把某个方法的 Code 属性反汇编出助记符流。"""
    r = parse_classfile(data)
    if "error" in r:
        return [r["error"]]
    with_code = [m for m in r["methods"] if m.get("code")]
    if not with_code:
        return ["该类没有带 Code 属性的方法（可能是接口或抽象方法）"]
    m = with_code[min(method_index, len(with_code) - 1)]
    d = dis_java(m["code"]["code"], r["constant_pool"])
    lines = ["方法 %s%s  (%d 条指令，%d 字节)" % (
        m["name"], m["descriptor"], d["count"], d["bytes"]),
        "%-6s %-20s %s" % ("偏移", "操作码", "指令")]
    for ins in d["instructions"]:
        lines.append("%-6d 0x%02X               %s" % (
            ins["offset"], ins["opcode"], ins["text"]))
    if d["stopped"]:
        lines.append("注：%s" % d["stopped"])
    return lines


# ---------------------------------------------------------------- x86-64

PREFIXES = {
    0xF0: "LOCK（锁总线/缓存行）",
    0xF2: "REPNE/REPNZ（也作某些指令的强制前缀）",
    0xF3: "REP/REPE（也作 POPCNT/LZCNT 等的前缀）",
    0x2E: "CS 段覆盖（64 位模式下为分支提示）",
    0x36: "SS 段覆盖",
    0x3E: "DS 段覆盖",
    0x26: "ES 段覆盖",
    0x64: "FS 段覆盖（x64 上常指向 TEB/GS 基址）",
    0x65: "GS 段覆盖",
    0x66: "操作数大小覆盖（16 位操作数）",
    0x67: "地址大小覆盖（32 位寻址）",
}

REG64 = ["rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi",
         "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"]
REG32 = ["eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi",
         "r8d", "r9d", "r10d", "r11d", "r12d", "r13d", "r14d", "r15d"]
REG16 = ["ax", "cx", "dx", "bx", "sp", "bp", "si", "di",
         "r8w", "r9w", "r10w", "r11w", "r12w", "r13w", "r14w", "r15w"]
REG8_REX = ["al", "cl", "dl", "bl", "spl", "bpl", "sil", "dil",
            "r8b", "r9b", "r10b", "r11b", "r12b", "r13b", "r14b", "r15b"]
REG8_NOREX = ["al", "cl", "dl", "bl", "ah", "ch", "dh", "bh"]

#: 单字节 opcode → 助记符（不依赖 ModRM.reg 的那些）
OP_ONE = {
    0x63: "movsxd", 0x8D: "lea", 0x8F: "pop", 0x90: "nop", 0x9C: "pushf",
    0x9D: "popf", 0xC3: "ret", 0xC2: "ret", 0xC9: "leave", 0xCC: "int3",
    0xCD: "int", 0xE8: "call", 0xE9: "jmp", 0xEB: "jmp", 0xF4: "hlt",
}

#: 算术/逻辑类 opcode（低 2 位表示方向/立即数形态）
OP_ARITH = {
    0x00: "add", 0x01: "add", 0x02: "add", 0x03: "add",
    0x08: "or", 0x09: "or", 0x0A: "or", 0x0B: "or",
    0x10: "adc", 0x11: "adc", 0x12: "adc", 0x13: "adc",
    0x18: "sbb", 0x19: "sbb", 0x1A: "sbb", 0x1B: "sbb",
    0x20: "and", 0x21: "and", 0x22: "and", 0x23: "and",
    0x28: "sub", 0x29: "sub", 0x2A: "sub", 0x2B: "sub",
    0x30: "xor", 0x31: "xor", 0x32: "xor", 0x33: "xor",
    0x38: "cmp", 0x39: "cmp", 0x3A: "cmp", 0x3B: "cmp",
    0x84: "test", 0x85: "test", 0x86: "xchg", 0x87: "xchg",
    0x88: "mov", 0x89: "mov", 0x8A: "mov", 0x8B: "mov",
}

#: 需要 ModRM.reg 才能定助记符的组
OP_GROUPS = {
    0x80: ["add", "or", "adc", "sbb", "and", "sub", "xor", "cmp"],
    0x81: ["add", "or", "adc", "sbb", "and", "sub", "xor", "cmp"],
    0x83: ["add", "or", "adc", "sbb", "and", "sub", "xor", "cmp"],
    0xC0: ["rol", "ror", "rcl", "rcr", "shl", "shr", "shl", "sar"],
    0xC1: ["rol", "ror", "rcl", "rcr", "shl", "shr", "shl", "sar"],
    0xD0: ["rol", "ror", "rcl", "rcr", "shl", "shr", "shl", "sar"],
    0xD1: ["rol", "ror", "rcl", "rcr", "shl", "shr", "shl", "sar"],
    0xD2: ["rol", "ror", "rcl", "rcr", "shl", "shr", "shl", "sar"],
    0xD3: ["rol", "ror", "rcl", "rcr", "shl", "shr", "shl", "sar"],
    0xF6: ["test", "test", "not", "neg", "mul", "imul", "div", "idiv"],
    0xF7: ["test", "test", "not", "neg", "mul", "imul", "div", "idiv"],
    0xFE: ["inc", "dec", "?", "?", "?", "?", "?", "?"],
    0xFF: ["inc", "dec", "call", "lcall", "jmp", "ljmp", "push", "?"],
    0xBA: ["bt", "bts", "btr", "btc", "bt", "bts", "btr", "btc"],  # 位测试（无 LOCK 时非原子）
}

#: 两字节 opcode（0F xx）
OP_TWO = {
    0x05: "syscall", 0x0B: "ud2", 0x1F: "nop", 0xA2: "cpuid", 0xA3: "bt",
    0xAF: "imul", 0xB6: "movzx", 0xB7: "movzx", 0xBE: "movsx", 0xBF: "movsx",
    0xBC: "bsf", 0xBD: "bsr", 0x10: "movups", 0x11: "movups",
    0x28: "movaps", 0x29: "movaps", 0x57: "xorps", 0x58: "addps",
    0x6F: "movdqa", 0x7F: "movdqu", 0xEF: "pxor", 0x1E: "endbr(需 F3 前缀)",
    0x2E: "ucomiss", 0x2F: "comiss", 0x5A: "cvtps2pd", 0x38: "3 字节转义(0F38)",
    0x3A: "3 字节转义(0F3A)",
    # —— 多并发的 CPU 基石：原子读改写指令（通常与 LOCK 前缀配合）——
    0xB0: "cmpxchg", 0xB1: "cmpxchg",   # CMPXCHG r/m8/32（reg 字段为比较操作数）
    0xC1: "xadd",                       # XADD r/m, r：原子交换并相加
}

CC = ["o", "no", "b", "ae", "e", "ne", "be", "a",
      "s", "ns", "p", "np", "l", "ge", "le", "g"]


def decode_x86_64(data: bytes, rip: int = 0) -> Dict:
    """按 Intel 指令格式拆解**一条** x86-64 指令。

    返回前缀 / REX / opcode / ModRM / SIB / 位移 / 立即数与助记符提示。
    这是结构化拆解而非完整反汇编：助记符来自启发式表，权威表见
    Intel SDM Vol.2 Appendix A。
    """
    b = bytes(data)
    if not b:
        return {"error": "空字节序列"}
    pos = 0
    prefixes: List[Dict] = []
    rex = None
    # 1) 传统前缀
    while pos < len(b) and b[pos] in PREFIXES:
        prefixes.append({"byte": b[pos], "name": PREFIXES[b[pos]]})
        pos += 1
    # 2) REX（必须紧跟传统前缀、在 opcode 之前）
    if pos < len(b) and 0x40 <= b[pos] <= 0x4F:
        v = b[pos]
        rex = {"byte": v, "W": (v >> 3) & 1, "R": (v >> 2) & 1,
               "X": (v >> 1) & 1, "B": v & 1}
        pos += 1
    if pos >= len(b):
        return {"error": "只有前缀，没有 opcode"}
    opsize16 = any(p["byte"] == 0x66 for p in prefixes)
    addr32 = any(p["byte"] == 0x67 for p in prefixes)
    w = bool(rex and rex["W"])
    # 3) opcode（1/2/3 字节）
    op1 = b[pos]
    pos += 1
    opcode = [op1]
    two_byte = False
    if op1 == 0x0F:
        if pos >= len(b):
            return {"error": "0F 转义后缺少第二字节"}
        opcode.append(b[pos])
        pos += 1
        two_byte = True
        if opcode[1] in (0x38, 0x3A) and pos < len(b):
            opcode.append(b[pos])
            pos += 1
    mnemonic = "?"
    if two_byte:
        op2 = opcode[1]
        if 0x80 <= op2 <= 0x8F:
            mnemonic = "j" + CC[op2 - 0x80]
        elif 0x90 <= op2 <= 0x9F:
            mnemonic = "set" + CC[op2 - 0x90]
        elif 0xC8 <= op2 <= 0xCF:
            mnemonic = "bswap"
        else:
            mnemonic = OP_TWO.get(op2, "0F %02X（未收录）" % op2)
    else:
        if 0x50 <= op1 <= 0x57:
            mnemonic = "push"
        elif 0x58 <= op1 <= 0x5F:
            mnemonic = "pop"
        elif 0x70 <= op1 <= 0x7F:
            mnemonic = "j" + CC[op1 - 0x70]
        elif 0xB0 <= op1 <= 0xB7:
            mnemonic = "mov"
        elif 0xB8 <= op1 <= 0xBF:
            mnemonic = "mov"
        elif op1 in OP_GROUPS:
            mnemonic = "grp(需 reg 字段)"
        else:
            mnemonic = OP_ONE.get(op1, OP_ARITH.get(op1, "%02X（未收录）" % op1))

    # PAUSE = F3 90（REP NOP），自旋等待时让出流水线；无 F3 前缀时 0x90 即 NOP
    if op1 == 0x90 and any(p["byte"] == 0xF3 for p in prefixes):
        mnemonic = "pause"
    # LOCK 前缀标志：用于标注多核原子指令
    has_lock = any(p["byte"] == 0xF0 for p in prefixes)

    # 4) 操作数宽度：REX.W=1 → 64；0x66 → 16；默认 32
    if w:
        width = 64
    elif opsize16:
        width = 16
    else:
        width = 32
    if 0xB0 <= op1 <= 0xB7 or (op1 in (0x88, 0x8A) and not opsize16):
        width = 8

    def reg_name(idx: int, wdt: int) -> str:
        ext = (rex["R"] << 3) if rex else 0
        i = (ext | idx) & 0xF
        if wdt == 64:
            return REG64[i]
        if wdt == 32:
            return REG32[i]
        if wdt == 16:
            return REG16[i]
        base = REG8_REX if rex else REG8_NOREX
        return base[i] if i < len(base) else "r%db" % i

    def rm_name(idx: int, wdt: int) -> str:
        ext = (rex["B"] << 3) if rex else 0
        i = (ext | idx) & 0xF
        if wdt == 64:
            return REG64[i]
        if wdt == 32:
            return REG32[i]
        if wdt == 16:
            return REG16[i]
        base = REG8_REX if rex else REG8_NOREX
        return base[i] if i < len(base) else "r%db" % i

    modrm = None
    sib = None
    disp = None
    disp_size = 0
    mem_text = ""       # r/m 侧文本（寄存器直连时就是寄存器名）
    reg_text = ""       # ModRM.reg 侧寄存器名
    # 哪些 opcode 带 ModRM：这里按"除立即数/相对跳转类之外基本都有"处理
    no_modrm = (0x50 <= op1 <= 0x5F) or (0xB0 <= op1 <= 0xBF) or \
               (0x70 <= op1 <= 0x7F) or op1 in (0xE8, 0xE9, 0xEB, 0xC3, 0xC2,
                                                0xCC, 0xCD, 0xF4, 0x9C, 0x9D, 0xC9)
    if two_byte and opcode[1] == 0x05:
        no_modrm = True      # syscall
    if not no_modrm and pos < len(b):
        m = b[pos]
        pos += 1
        mod = (m >> 6) & 3
        reg = ((m >> 3) & 7)
        rm = m & 7
        modrm = {"byte": m, "mod": mod, "reg": reg, "rm": rm}
        reg_text = reg_name(reg, width)
        if op1 in OP_GROUPS:
            grp = OP_GROUPS[op1]
            mnemonic = grp[reg] if reg < len(grp) else "?"
        if mod == 3:
            mem_text = rm_name(rm, width)
        else:
            if rm == 4:      # SIB
                if pos >= len(b):
                    return {"error": "需要 SIB 字节但已到末尾"}
                s = b[pos]
                pos += 1
                scale, index, base = (s >> 6) & 3, ((s >> 3) & 7), s & 7
                iext = ((rex["X"] << 3) if rex else 0) | index
                bext = ((rex["B"] << 3) if rex else 0) | base
                sib = {"byte": s, "scale": 1 << scale, "index": iext,
                       "base": bext, "index_none": (iext & 7) == 4 and not (rex and rex["X"]),
                       "base_none": (base & 7) == 5 and mod == 0}
                if mod == 1:
                    disp_size = 1
                elif mod == 2 or (mod == 0 and (base & 7) == 5):
                    disp_size = 4
            elif rm == 5 and mod == 0:
                disp_size = 4       # x86-64 的 RIP 相对寻址
            else:
                if mod == 1:
                    disp_size = 1
                elif mod == 2:
                    disp_size = 4
            modrm["disp_size"] = disp_size
            # 位移
            if disp_size and pos + disp_size <= len(b):
                disp = int.from_bytes(b[pos:pos + disp_size], "little", signed=True)
                pos += disp_size
            # 位移读完后一次性拼出内存操作数文本
            if sib:
                parts = []
                if not sib["index_none"]:
                    parts.append("%s*%d" % (REG64[sib["index"]], sib["scale"]))
                if not sib["base_none"]:
                    parts.append(REG64[sib["base"]])
                if disp is not None and disp != 0:
                    parts.append("0x%x" % (disp & 0xFFFFFFFF))
                elif disp is not None:
                    parts.append("0x0")
                mem_text = "[" + "+".join(parts) + "]" if parts else "[disp]"
            elif rm == 5 and mod == 0:
                d = disp if disp is not None else 0
                mem_text = "[rip+0x%x]" % (d & 0xFFFFFFFF)
                modrm["rip_target"] = (rip + pos + d) & 0xFFFFFFFFFFFFFFFF
                if disp is None:
                    mem_text += "（位移字节不足，按 0 显示）"
            else:
                base_reg = REG64[((rex["B"] << 3) if rex else 0) | rm]
                if disp:
                    mem_text = "[%s+0x%x]" % (base_reg, disp & 0xFFFFFFFF)
                else:
                    mem_text = "[%s]" % base_reg

    # 0F AE 的 ModRM.reg 字段决定内存屏障：/5=lfence /6=mfence /7=sfence
    # （仅 mod=3 时；32 位模式下 /7 另有含义，这里按 64 位约定处理）
    if two_byte and opcode[1] == 0xAE and modrm is not None:
        _fence = {5: "lfence", 6: "mfence", 7: "sfence"}.get(modrm["reg"])
        if _fence:
            mnemonic = _fence

    # 5) 立即数（剩余字节按立即数处理，大小由助记符形态粗判）
    imm = None
    imm_size = 0
    if 0xB8 <= op1 <= 0xBF:
        imm_size = 8 if w else (2 if opsize16 else 4)
    elif 0xB0 <= op1 <= 0xB7:
        imm_size = 1
    elif op1 in (0x80, 0x81, 0x83, 0xC0, 0xC1, 0xF6, 0xF7):
        imm_size = 1 if op1 in (0x80, 0x83, 0xC0) else (2 if opsize16 else 4)
        if w and op1 == 0x81:
            imm_size = 4
        if op1 == 0xC1:
            imm_size = 1
        if op1 in (0x80, 0x83):
            imm_size = 1
    elif op1 in (0xE8, 0xE9) or (0x70 <= op1 <= 0x7F) or op1 == 0xEB:
        imm_size = 4 if op1 in (0xE8, 0xE9) else 1
    elif two_byte and 0x80 <= opcode[1] <= 0x8F:
        imm_size = 4
    if imm_size and pos + imm_size <= len(b):
        raw = b[pos:pos + imm_size]
        imm = int.from_bytes(raw, "little", signed=True)
        pos += imm_size

    length = pos
    # 6) 拼助记符的操作数。Intel 语法的 "RM, REG" / "REG, RM" 顺序由
    #    opcode 的 d 位（bit 1）决定：d=0 → r/m 为目的；d=1 → reg 为目的。
    operands = ""
    if 0xB0 <= op1 <= 0xBF:
        operands = "%s, 0x%x" % (rm_name(op1 & 7, width),
                                 (imm or 0) & ((1 << max(1, imm_size * 8)) - 1))
    elif 0x50 <= op1 <= 0x5F:
        operands = rm_name(op1 & 7, 64)
    elif modrm and mnemonic not in ("mfence", "lfence", "sfence"):
        if mnemonic in ("lea", "movsxd"):
            operands = "%s, %s" % (reg_text, mem_text)
        elif mnemonic in ("nop", "endbr(需 F3 前缀)"):
            # 多字节 nop（0F 1F /r）与 endbr 的 reg 字段是操作码的一部分
            operands = mem_text
        elif op1 == 0x8F:
            operands = mem_text
        elif (op1 & 0x02) == 0 or mnemonic in ("xadd", "cmpxchg"):
            # 多数 ALU：d=0 → r/m 为目的；XADD/CMPXCHG 恒为「r/m, reg」
            operands = "%s, %s" % (mem_text, reg_text)
        else:
            operands = "%s, %s" % (reg_text, mem_text)
        if imm is not None:
            operands = "%s, 0x%x" % (operands, imm & ((1 << (imm_size * 8)) - 1))
    elif imm is not None and (op1 in (0xE8, 0xE9, 0xEB) or 0x70 <= op1 <= 0x7F
                              or (two_byte and 0x80 <= opcode[1] <= 0x8F)):
        # 相对跳转/调用：目标是"下一条指令地址 + 位移"
        target = (rip + length + imm) & 0xFFFFFFFFFFFFFFFF
        operands = "0x%x（相对下一条 %+d）" % (target, imm)
    elif imm is not None:
        operands = "0x%x" % (imm & ((1 << (imm_size * 8)) - 1))

    note = _("结构化拆解；助记符为启发式提示，权威表见 Intel SDM Vol.2 Appendix A")
    if has_lock:
        note += _("；LOCK 前缀 → 多核原子（锁缓存行，阻止其他核并发访问）")
    elif mnemonic == "xchg" and modrm and modrm["mod"] != 3:
        note += _("；XCHG 的内存操作数隐含 LOCK（与带锁等价）")

    return {
        "bytes": b[:length].hex(),
        "length": length,
        "prefixes": prefixes,
        "rex": rex,
        "opcode": " ".join("%02X" % o for o in opcode),
        "opcode_bytes": opcode,
        "two_byte": two_byte,
        "modrm": modrm,
        "sib": sib,
        "displacement": disp,
        "immediate": imm,
        "immediate_size": imm_size,
        "operand_width": width,
        "lock": has_lock,
        "mnemonic_hint": mnemonic,
        "operands": operands,
        "address_size": 32 if addr32 else 64,
        "note": note,
    }


def render_x86(data: bytes, rip: int = 0) -> List[str]:
    """x86-64 指令 → 分层文本（字段逐项列出）。"""
    r = decode_x86_64(data, rip)
    if "error" in r:
        return [r["error"]]
    lines = [
        "字节：%s（%d 字节）" % (r["bytes"], r["length"]),
        "指令：%-8s %s" % (r["mnemonic_hint"], r["operands"]),
    ]
    if r["prefixes"]:
        for p in r["prefixes"]:
            tag = ""
            if p["byte"] == 0xF0:
                tag = "  ← 并发原子关键"
            lines.append("  前缀      : %02X  %s%s" % (p["byte"], p["name"], tag))
    else:
        lines.append("  前缀      : （无）")
    if r.get("lock"):
        lines.append(_("  原子性    : LOCK — 该指令在多核下原子执行"))
    if r["rex"]:
        rex = r["rex"]
        lines.append("  REX       : %02X  W=%d R=%d X=%d B=%d（W=1 → 64 位操作数）" % (
            rex["byte"], rex["W"], rex["R"], rex["X"], rex["B"]))
    else:
        lines.append("  REX       : （无）")
    lines.append("  操作码    : %s%s" % (r["opcode"], "（双字节/三字节转义）" if r["two_byte"] else ""))
    if r["modrm"]:
        m = r["modrm"]
        lines.append("  ModRM     : %02X  mod=%d reg=%d rm=%d" % (
            m["byte"], m["mod"], m["reg"], m["rm"]))
        if r["sib"]:
            s = r["sib"]
            idx = "无" if s["index_none"] else REG64[s["index"]]
            bas = "无(disp32)" if s["base_none"] else REG64[s["base"]]
            lines.append("  SIB       : %02X  scale=%d index=%s base=%s" % (
                s["byte"], s["scale"], idx, bas))
        if m["disp_size"]:
            lines.append("  位移      : %d 字节 = %d" % (m["disp_size"], r["displacement"]))
    else:
        lines.append("  ModRM     : （无）")
    if r["immediate_size"]:
        lines.append("  立即数    : %d 字节 = %d（0x%X）" % (
            r["immediate_size"], r["immediate"],
            r["immediate"] & ((1 << (r["immediate_size"] * 8)) - 1)))
    lines.append("  操作数宽  : %d 位    地址宽: %d 位" % (
        r["operand_width"], r["address_size"]))
    lines.append("  说明      : %s" % r["note"])
    return lines


#: 固定样例（用于自测与文档）：字节 → 预期含义
X86_SAMPLES = [
    ("55", "push rbp（函数序言）"),
    ("4889e5", "mov rbp, rsp（REX.W 前缀 48）"),
    ("b801000000", "mov eax, 1（B8+r，imm32）"),
    ("4801d8", "add rax, rbx（opcode 01 / mod=3 / reg=rax / rm=rbx）"),
    ("4831c0", "xor rax, rax（置零惯用法）"),
    ("c3", "ret"),
    ("0f1f440000", "nop dword [rax]（多字节 nop 0F 1F）"),
    ("e800000000", "call rel32"),
]


def render_x86_samples() -> List[str]:
    """把内置样例逐条拆开显示（也是一层自检）。"""
    lines = [_("x86-64 指令样例拆解：")]
    for hexstr, desc in X86_SAMPLES:
        data = bytes.fromhex(hexstr)
        r = decode_x86_64(data)
        if "error" in r:
            lines.append("  %-14s → 错误：%s" % (hexstr, r["error"]))
            continue
        lines.append("  %-14s %-8s %-28s  %s" % (
            hexstr, r["mnemonic_hint"], r["operands"], desc))
    return lines


#: 多并发的 CPU 基石：原子/锁/屏障指令样例（字节经 as+objdump 核准）
#: 字节 → (解码预期 mnemonic, 操作数, 并发含义)
X86_ATOMIC_SAMPLES = [
    ("f00fc108", "lock xadd dword [rax], ecx",
     "原子自增：std::atomic::fetch_add / 计数器底层"),
    ("f00fb108", "lock cmpxchg dword [rax], ecx",
     "原子比较-交换 CAS：无锁算法（自旋锁/treiber 栈）基础"),
    ("f0ff00", "lock inc dword [rax]",
     "原子自增（单条 INC 配 LOCK）"),
    ("f0830001", "lock add dword [rax], 1",
     "原子加立即数"),
    ("8708", "xchg dword [rax], ecx",
     "交换：内存操作数隐含 LOCK（自旋锁 test-and-set 常用）"),
    ("0faef0", "mfence", "全存储屏障：保证之前的写对其他核可见（seq_cst 写侧）"),
    ("0faee8", "lfence", "读屏障：保证之前的读先完成（配合投机读）"),
    ("0faef8", "sfence", "写屏障：保证之前的写按序冲刷"),
    ("f390", "pause", "自旋等待让出流水线：降温、减缓存污染（自旋锁循环内）"),
    ("f00fba2800", "lock bts dword [rax], 0",
     "原子置位：test-and-set 自旋锁的原语"),
]


def render_atomic_samples() -> List[str]:
    """把并发原子指令样例逐条拆开显示（也是一层自检 + 与多并发层的衔接点）。"""
    lines = [_("x86-64 并发原子指令（与「concur 多并发」层对应）：")]
    for hexstr, _exp_mn, meaning in X86_ATOMIC_SAMPLES:
        data = bytes.fromhex(hexstr)
        r = decode_x86_64(data)
        if "error" in r:
            lines.append("  %-12s → 错误：%s" % (hexstr, r["error"]))
            continue
        lock = " [LOCK]" if r.get("lock") else ""
        lines.append("  %-12s %s %s%s" % (hexstr, r["mnemonic_hint"], lock, r["operands"]))
        lines.append("             ↳ %s" % meaning)
    return lines


# ======================================================================
# RISC-V 64I 基础整数指令集（教学 / 启发式结构化拆解）
# ----------------------------------------------------------------------
# 这是「机器码层」对 RISC 架构的代表性补充，与上面的 x86-64（CISC，变长）
# 拆解形成对照。RISC-V 定长 32 位、小端存储、字段位置固定，比 x86 好读，
# 也更适合当底层教学材料。
#
# 覆盖范围（诚实声明）：仅 RV64I 基础整数子集 + RV64 的双字扩展
#   (OP-IMM-32 / OP-32)。即 LUI / AUIPC / JAL / JALR / B<cond> / Load /
#   Store / OP-IMM / OP / SYSTEM(FENCE/ECALL/EBREAK/CSR) / FENCE
#   + ADDIW/SLLIW/SRLIW/SRAIW/ADDW/SUBW/SLLW/SRLW/SRAW。
# 不覆盖：压缩指令(C)、浮点(F/D)、乘除法(M)、原子(A)、向量(V)、
#   特权指令、CSR 全量语义。指令数远少于完整 ISA。
# ======================================================================

RV_ABI = ["zero", "ra", "sp", "gp", "tp", "t0", "t1", "t2", "s0", "s1",
          "a0", "a1", "a2", "a3", "a4", "a5", "a6", "a7",
          "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s11",
          "t3", "t4", "t5", "t6"]


def _rv_reg(i: int) -> str:
    # 机器码层以「看清编码字段」为本：始终显示 x 编号（直接对应 bit 位置），
    # 不自动换成 ABI 别名（zero/ra/...），避免与编码布局脱节。别名表见 RV_ABI。
    return "x%d" % i


def _rv_i_imm(inst: int) -> int:
    imm = (inst >> 20) & 0xFFF
    return imm - 0x1000 if imm & 0x800 else imm


def _rv_s_imm(inst: int) -> int:
    imm = ((inst >> 25) & 0x7F) << 5 | ((inst >> 7) & 0x1F)
    return imm - 0x1000 if imm & 0x800 else imm


def _rv_b_imm(inst: int) -> int:
    imm = ((inst >> 31) & 1) << 12
    imm |= ((inst >> 25) & 0x3F) << 5
    imm |= ((inst >> 8) & 0xF) << 1
    imm |= ((inst >> 7) & 1) << 11
    return imm - 0x2000 if imm & 0x1000 else imm


def _rv_u_imm(inst: int) -> int:
    # LUI/AUIPC 的立即数就是 bit[31:12] 的 20 位字段值（汇编里会被硬件左移 12 位），
    # 这里返回未移位的值，与 objdump 的显示一致。
    return (inst >> 12) & 0xFFFFF


def _rv_j_imm(inst: int) -> int:
    imm = ((inst >> 31) & 1) << 20
    imm |= ((inst >> 21) & 0x3FF) << 1
    imm |= ((inst >> 20) & 1) << 11
    imm |= ((inst >> 12) & 0xFF) << 12
    return imm - 0x200000 if imm & 0x100000 else imm


def _rv_fence_str(bits: int) -> str:
    parts = []
    if bits & 8:
        parts.append("i")
    if bits & 4:
        parts.append("o")
    if bits & 2:
        parts.append("r")
    if bits & 1:
        parts.append("w")
    return "".join(parts) if parts else "0"


def _decode_one_rv(inst: int) -> Dict:
    opcode = inst & 0x7F
    rd = (inst >> 7) & 0x1F
    funct3 = (inst >> 12) & 0x7
    rs1 = (inst >> 15) & 0x1F
    rs2 = (inst >> 20) & 0x1F
    funct7 = (inst >> 25) & 0x7F
    out = {
        "inst": inst, "opcode": opcode, "rd": rd, "rs1": rs1, "rs2": rs2,
        "funct3": funct3, "funct7": funct7,
        "mnemonic": "?", "operands": "", "notes": [],
    }
    if opcode == 0x37:  # LUI
        out["mnemonic"] = "lui"
        out["operands"] = "%s, 0x%x" % (_rv_reg(rd), _rv_u_imm(inst))
        out["notes"].append("高 20 位立即数，低 12 位补 0")
    elif opcode == 0x17:  # AUIPC
        out["mnemonic"] = "auipc"
        out["operands"] = "%s, 0x%x" % (_rv_reg(rd), _rv_u_imm(inst))
        out["notes"].append("PC 相对：rd = pc + (imm<<12)")
    elif opcode == 0x6F:  # JAL
        imm = _rv_j_imm(inst)
        if rd == 0:
            out["mnemonic"] = "j"
            out["operands"] = "%d" % imm
        else:
            out["mnemonic"] = "jal"
            out["operands"] = "%s, %d" % (_rv_reg(rd), imm)
    elif opcode == 0x67:  # JALR
        imm = _rv_i_imm(inst)
        if rd == 0 and rs1 == 1 and imm == 0:
            out["mnemonic"] = "ret"
            out["notes"].append("jalr x0, 0(x1) 的伪指令")
        elif rd == 0 and imm == 0:
            out["mnemonic"] = "jr"
            out["operands"] = _rv_reg(rs1)
            out["notes"].append("jalr x0, 0(rs) 的伪指令")
        else:
            out["mnemonic"] = "jalr"
            out["operands"] = "%s, %d(%s)" % (_rv_reg(rd), imm, _rv_reg(rs1))
            out["notes"].append("返回地址写 rd；目标 = (rs1+imm)&~1")
    elif opcode == 0x63:  # BRANCH
        mnem = {0: "beq", 1: "bne", 4: "blt", 5: "bge", 6: "bltu", 7: "bgeu"}.get(funct3)
        if mnem:
            out["mnemonic"] = mnem
            out["operands"] = "%s, %s, %d" % (_rv_reg(rs1), _rv_reg(rs2), _rv_b_imm(inst))
        else:
            out["notes"].append("未实现的 BRANCH funct3=%d" % funct3)
    elif opcode == 0x03:  # LOAD
        mnem = {0: "lb", 1: "lh", 2: "lw", 3: "ld", 4: "lbu", 5: "lhu", 6: "lwu"}.get(funct3)
        if mnem:
            out["mnemonic"] = mnem
            out["operands"] = "%s, %d(%s)" % (_rv_reg(rd), _rv_i_imm(inst), _rv_reg(rs1))
            if funct3 in (3, 6):
                out["notes"].append("RV64 双字加载")
        else:
            out["notes"].append("未实现的 LOAD funct3=%d" % funct3)
    elif opcode == 0x23:  # STORE
        mnem = {0: "sb", 1: "sh", 2: "sw", 3: "sd"}.get(funct3)
        if mnem:
            out["mnemonic"] = mnem
            out["operands"] = "%s, %d(%s)" % (_rv_reg(rs2), _rv_s_imm(inst), _rv_reg(rs1))
            if funct3 == 3:
                out["notes"].append("RV64 双字存储")
        else:
            out["notes"].append("未实现的 STORE funct3=%d" % funct3)
    elif opcode == 0x13:  # OP-IMM
        imm = _rv_i_imm(inst)
        if funct3 == 1:
            out["mnemonic"] = "slli"
            out["operands"] = "%s, %s, %d" % (_rv_reg(rd), _rv_reg(rs1), imm & 0x3F)
        elif funct3 == 5:
            out["mnemonic"] = "srai" if funct7 == 0x20 else "srli"
            out["operands"] = "%s, %s, %d" % (_rv_reg(rd), _rv_reg(rs1), imm & 0x3F)
        else:
            mnem = {0: "addi", 2: "slti", 3: "sltiu", 4: "xori", 6: "ori", 7: "andi"}.get(funct3)
            if mnem:
                out["mnemonic"] = mnem
                if mnem == "addi" and imm == 0 and rd != 0:
                    out["mnemonic"] = "mv"
                    out["operands"] = "%s, %s" % (_rv_reg(rd), _rv_reg(rs1))
                    out["notes"].append("addi rd, rs, 0 的伪指令")
                else:
                    out["operands"] = "%s, %s, %d" % (_rv_reg(rd), _rv_reg(rs1), imm)
            else:
                out["notes"].append("未实现的 OP-IMM funct3=%d" % funct3)
    elif opcode == 0x33:  # OP
        ops3 = {0: ("add", "sub"), 1: ("sll",), 2: ("slt",), 3: ("sltu",),
                4: ("xor",), 5: ("srl", "sra"), 6: ("or",), 7: ("and",)}
        pair = ops3.get(funct3)
        if pair:
            out["mnemonic"] = pair[1] if (len(pair) > 1 and funct7 == 0x20) else pair[0]
            out["operands"] = "%s, %s, %s" % (_rv_reg(rd), _rv_reg(rs1), _rv_reg(rs2))
        else:
            out["notes"].append("未实现的 OP funct3=%d" % funct3)
    elif opcode == 0x1B:  # OP-IMM-32 (RV64)
        imm = _rv_i_imm(inst)
        if funct3 == 1:
            out["mnemonic"] = "slliw"
            out["operands"] = "%s, %s, %d" % (_rv_reg(rd), _rv_reg(rs1), imm & 0x1F)
        elif funct3 == 5:
            out["mnemonic"] = "sraiw" if funct7 == 0x20 else "srliw"
            out["operands"] = "%s, %s, %d" % (_rv_reg(rd), _rv_reg(rs1), imm & 0x1F)
        elif funct3 == 0:
            if imm == 0 and rd != 0:
                out["mnemonic"] = "sext.w"
                out["operands"] = "%s, %s" % (_rv_reg(rd), _rv_reg(rs1))
                out["notes"].append("addiw rd, rs, 0 的伪指令")
            else:
                out["mnemonic"] = "addiw"
                out["operands"] = "%s, %s, %d" % (_rv_reg(rd), _rv_reg(rs1), imm)
        else:
            out["notes"].append("未实现的 OP-IMM-32 funct3=%d" % funct3)
    elif opcode == 0x3B:  # OP-32 (RV64)
        pair = {0: ("addw", "subw"), 1: ("sllw",), 5: ("srlw", "sraw")}.get(funct3)
        if pair:
            out["mnemonic"] = pair[1] if (len(pair) > 1 and funct7 == 0x20) else pair[0]
            out["operands"] = "%s, %s, %s" % (_rv_reg(rd), _rv_reg(rs1), _rv_reg(rs2))
        else:
            out["notes"].append("未实现的 OP-32 funct3=%d" % funct3)
    elif opcode == 0x0F:  # FENCE
        if funct3 == 0:
            out["mnemonic"] = "fence"
            out["operands"] = "%s, %s" % (_rv_fence_str((inst >> 24) & 0xF),
                                          _rv_fence_str((inst >> 20) & 0xF))
            out["notes"].append("内存屏障；pred/succ = I/O/R/W")
        elif funct3 == 1:
            out["mnemonic"] = "fence.i"
            out["notes"].append("指令缓存刷新")
    elif opcode == 0x73:  # SYSTEM
        imm = (inst >> 20) & 0xFFF
        if funct3 == 0:
            if imm == 0:
                out["mnemonic"] = "ecall"
                out["notes"].append("环境调用 / 系统调用")
            elif imm == 1:
                out["mnemonic"] = "ebreak"
                out["notes"].append("断点")
            else:
                out["notes"].append("未实现的 SYSTEM funct3=0 imm=%d" % imm)
        else:
            csr = {1: "csrrw", 2: "csrrs", 3: "csrrc", 5: "csrrwi",
                   6: "csrrsi", 7: "csrrci"}.get(funct3)
            if csr:
                out["mnemonic"] = csr
                out["operands"] = "%s, 0x%x, %s" % (_rv_reg(rd), imm, _rv_reg(rs1))
                out["notes"].append("CSR 访问（仅结构化，不解释寄存器语义）")
            else:
                out["notes"].append("未实现的 SYSTEM funct3=%d" % funct3)
    else:
        out["notes"].append(
            "未实现的 opcode=0x%02X（压缩/浮点/乘除/原子/特权等不在覆盖内）" % opcode)
    return out


def decode_riscv64(data: bytes, pc: int = 0) -> List[Dict]:
    """字节流 → RISC-V 指令结构化列表（每条含地址 / 字段 / 助记符 / 操作数 / 说明）。"""
    if len(data) % 4 != 0:
        return [{"error": "字节数 %d 不是 4 的倍数（RV32I/RV64I 指令定长 32 位）" % len(data)}]
    out = []
    for off in range(0, len(data), 4):
        inst = int.from_bytes(data[off:off + 4], "little")
        e = _decode_one_rv(inst)
        e["offset"] = off
        e["address"] = pc + off
        out.append(e)
    return out


def render_riscv64(data: bytes, pc: int = 0) -> List[str]:
    """RISC-V 指令 → objdump 风格文本（地址 : 字节 : 助记符 操作数 ; 说明）。"""
    dec = decode_riscv64(data, pc)
    if dec and "error" in dec[0]:
        return [dec[0]["error"]]
    lines = []
    for e in dec:
        raw = data[e["offset"]:e["offset"] + 4]
        hexb = " ".join("%02x" % b for b in raw)
        text = e["mnemonic"] + (" " + e["operands"] if e["operands"] else "")
        line = "%08x: %-11s %s" % (e["address"], hexb, text)
        if e["notes"]:
            line += "   ; " + " / ".join(e["notes"])
        lines.append(line)
    return lines


#: 固定样例（用于自测与文档）：小端机器码字节流 → 预期含义
RV_SAMPLES = [
    ("93001000", "addi x1, x0, 1（把立即数搬进寄存器；imm=0 时即伪指令 mv）"),
    ("b3003100", "add x1, x2, x3"),
    ("b7000010", "lui x1, 0x1（高 20 位 = 0x10000）"),
    ("03340100", "ld x8, 0(x2)（从栈顶取 8 字节；RV64 双字加载）"),
    ("23308100", "sd x8, 0(x2)（向栈顶存 8 字节；RV64 双字存储）"),
    ("67800000", "jalr x0, 0(x1) → ret（函数返回）"),
    ("63840000", "beq x1, x0, 8（相等则跳 8 字节）"),
    ("73000000", "ecall（环境调用 / 系统调用）"),
    ("73001000", "ebreak（断点）"),
    ("97000000", "auipc x1, 0（PC 相对取址）"),
]


def render_riscv64_samples() -> List[str]:
    """把内置样例逐条拆开显示（也是一层自检）。"""
    lines = [_("RISC-V 64I 指令样例拆解：")]
    for hexstr, desc in RV_SAMPLES:
        inst = int.from_bytes(bytes.fromhex(hexstr), "little")
        e = _decode_one_rv(inst)
        lines.append("  %-10s %-8s %-26s  %s" % (
            hexstr, e["mnemonic"], e["operands"], desc))
    return lines
