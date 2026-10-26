"""bits —— 位与二进制层。

把"机器里最底下那层"做成可验算的纯函数：进制、端序、位域、有符号数表示、
格雷码、BCD、奇偶校验、位操作，以及 IEEE 754 浮点位模式拆解。

为什么放在这里
--------------
Python 自带 `bin()/hex()/int.to_bytes()`，但**解释不了**它们：

* `0xFF` 在小端机器上存进内存是哪几个字节？
* `-7` 的 8 位补码为什么是 `0xF9`？
* `0x3F800000` 拆成 sign/exponent/mantissa 后是多少？
* Modbus 寄存器两个字节拼成 `int16` 时符号要不要扩展？

这些是看协议文档、读驱动代码、对抓包数据时每天都要手算的东西。

标准出处（STANDARD_REFS）
------------------------
浮点给 IEEE 754-2019 / ISO/IEC 60559；字符集里的 IA5 给 ITU-T T.50；
二进制浮点交换格式给 IEEE 754 §3。端序本身没有标准（是具体实现选择），
此处如实说明并给出各架构事实表。

纯标准库、纯函数、只读。
"""

from __future__ import annotations

import struct
from typing import Dict, List, Optional

from sysweeper.i18n import _

# ---------------------------------------------------------------- 标准引用

#: key → {cn: 国内标准, intl: 国际标准, regional: 地区标准}
STANDARD_REFS = {
    "ieee754": {
        "cn": "GB/T 17966-2000《微处理器系统的二进制浮点运算》",
        "intl": "IEEE 754-2019 / ISO/IEC 60559:2020",
        "regional": "EN ISO/IEC 60559（欧洲等同采用）",
    },
    "endian": {
        "cn": "无强制标准（实现选择）；GB/T 25645 系列未规定字节序",
        "intl": "无强制标准；IETF RFC 1700 曾定义 network byte order = 大端",
        "regional": "—",
    },
    "bcd": {
        "cn": "GB/T 1988-1998（仅字符编码涉及数字位）；BCD 无独立国标",
        "intl": "IBM BCD 惯例；IEEE 754 亦定义十进制浮点（用于 decimal）",
        "regional": "—",
    },
    "gray": {
        "cn": "—",
        "intl": "Frank Gray 专利 US 2,632,058（1953，已过期）",
        "regional": "—",
    },
}

#: 常见架构的事实字节序（用于解释"为什么我这台是小端"）
ENDIAN_FACTS = [
    ("x86 / x86-64 (Intel/AMD)", "小端", "x86 全系固定小端"),
    ("ARM (AArch32/AArch64)", "可配置", "通常小端；AArch64 有 BE 模式但极少启用"),
    ("龙芯 LoongArch", "小端", "LoongArch 固定小端"),
    ("RISC-V", "小端", "主流实现小端；规范允许大端扩展"),
    ("MIPS", "可配置", "传统 MIPS 多大端，嵌入式常小端"),
    ("Power ISA / OpenPOWER", "双端", "默认大端，支持小端模式（ELFv2 用小端）"),
    ("s390x (IBM Z)", "大端", "System/360 起沿袭大端"),
    ("SPARC", "大端", "传统 SPARC 大端"),
    ("网络字节序", "大端", "RFC 1700 定义，套接字 API 用 htonl/ntohl 转换"),
]

CAPABILITIES = [
    "进制互转（bin/oct/dec/hex/任意 2-36 进制）",
    "任意宽度位串与整数互转",
    "端序打包/解包与字节交换（8/16/32/64 位）",
    "位域提取与写入（extract / deposit）",
    "有符号数表示：原码/反码/补码，符号扩展",
    "格雷码与反格雷码",
    "BCD / 压缩 BCD（packed BCD）",
    "奇偶校验位、popcount、前导零/尾随零",
    "位旋转、位反转、汉明距离",
    "IEEE 754 位模式拆解（binary16/32/64）",
]

# ---------------------------------------------------------------- 进制显示契约
#
# 设计边界（呼应「人类可读的界面显示，后台保持原样」）：
#   * 显示层 = explain / render_bases / BASE 系列 CLI：默认十进制（带千分位），
#     仅为"使用者一眼能读"，不写回、不改写任何底层数据。
#   * 后台/解析层 = 库内 from_base 默认仍为十六进制（base=16，向后兼容）；
#     机器码层（x86 / RISC-V / Java / pyc）始终按字节、小端解析，
#     不受"显示偏好十进制"影响。二者互不串味。
#   * 所有函数为纯函数（无副作用、不修改入参），可在注释里放心解释。

# ---------------------------------------------------------------- 基础工具


def mask(width: int) -> int:
    """宽度为 `width` 的全 1 掩码；width<=0 返回 0。"""
    if width <= 0:
        return 0
    return (1 << width) - 1


def bit_length(value: int) -> int:
    """表示 `value` 所需的最少位数（0 → 0）。"""
    return int(value).bit_length()


def min_width(value: int, signed: bool = False) -> int:
    """装下 `value` 所需的最少位宽（考虑符号位）。"""
    v = int(value)
    if signed:
        if v >= 0:
            return max(1, v.bit_length() + 1)
        return max(2, (~v).bit_length() + 1)
    return max(1, v.bit_length())


def to_bits(value: int, width: int = 0) -> str:
    """整数 → 二进制字符串。

    width>0 时按该宽度补码截断；width=0 时正数取最小宽度、负数取最小补码宽度。
    """
    v = int(value)
    if width > 0:
        v &= mask(width)
    elif v < 0:
        v &= mask((~v).bit_length() + 1)
    s = format(v, "b")
    if width > 0:
        s = s.rjust(width, "0")
        if len(s) > width:
            s = s[-width:]
    return s


def from_bits(bits: str) -> Optional[int]:
    """二进制字符串 → 整数。容忍空格/下划线/0b 前缀。"""
    s = str(bits).strip().replace("_", "").replace(" ", "")
    if s[:2].lower() == "0b":
        s = s[2:]
    if not s:
        return None
    if any(c not in "01" for c in s):
        return None
    return int(s, 2)


def to_base(value: int, base: int = 16, width: int = 0, upper: bool = True) -> str:
    """整数 → 任意进制（2-36）字符串。base=16 时自动按 4 位一组对齐宽度。"""
    if base < 2 or base > 36:
        return ""
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    v = int(value)
    neg = v < 0
    v = abs(v)
    if v == 0:
        s = "0"
    else:
        out = []
        while v:
            out.append(digits[v % base])
            v //= base
        s = "".join(reversed(out))
    if not upper:
        s = s.lower()
    if width > 0:
        s = s.rjust(width, "0")
    return ("-" + s) if neg else s


def from_base(text: str, base: int = 16, default_base: int = None) -> Optional[int]:
    """任意进制（2-36）字符串 → 整数。容忍前缀与分隔符。

    - 带前缀 0x/0o/0b 时按对应进制解析（覆盖 base / default_base）；
    - 无前缀时：若显式传了 base（且非 16 缺省）用 base，否则用 default_base，
      二者都未指定则退回历史默认 16（保持向后兼容）；
    - 这让「人类输入 255 默认当十进制，写 0xFF 才当十六进制」成为可选项，而不是
      反过来把裸数字当十六进制（那是机器视角，不是使用者视角）。
    """
    s = str(text).strip().replace("_", "").replace(" ", "")
    if not s:
        return None
    low = s.lower()
    detected = None
    for pfx, b in (("0x", 16), ("0o", 8), ("0b", 2)):
        if low.startswith(pfx):
            s = s[len(pfx):]
            detected = b
            break
    if detected is not None:
        base = detected
    elif default_base is not None:
        base = default_base
    try:
        return int(s, base)
    except ValueError:
        return None


BASE_NAMES = {
    2: "二进制", 3: "三进制", 4: "四进制", 5: "五进制", 6: "六进制",
    7: "七进制", 8: "八进制", 9: "九进制", 10: "十进制", 11: "十一进制",
    12: "十二进制", 16: "十六进制", 20: "二十进制", 24: "二十四进制",
    32: "三十二进制", 36: "三十六进制", 60: "六十进制",
}


def base_name(base: int) -> str:
    """进制号 → 中文名；未登记的给「N 进制」。（译文见 locales 目录）"""
    return _(BASE_NAMES.get(base, "%d 进制" % base))


def human_int(value: int) -> str:
    """人类可读十进制：每 3 位加逗号。仅用于显示，不改变数值。

    这是给使用者看的主格式——无论机器内部用几进制，屏幕上先给一眼能读的十进制。
    """
    v = int(value)
    neg = v < 0
    body = format(abs(v), ",")
    return ("-" + body) if neg else body


def _group_digits(s: str, n: int = 3, sep: str = " ") -> str:
    """从右往左每 n 位插分隔符，提升长数字可读性（如三进制 1 001 100）。"""
    neg = s.startswith("-")
    body = s[1:] if neg else s
    out = []
    while body:
        out.append(body[-n:])
        body = body[:-n]
    res = sep.join(reversed(out))
    return ("-" + res) if neg else res


def bases(value: int, bases=(2, 3, 8, 10, 16)) -> List[Dict]:
    """把同一整数按多个进制展开，返回 [{base, name, digits}]。

    进制范围限 2-36（digit 表只有 0-9A-Z）。超出范围的项会被静默跳过，
    不会抛错——符合本层「永不失败」的约定。
    """
    v = int(value)
    rows = []
    for b in bases:
        if not (2 <= b <= 36):
            continue
        rows.append({"base": b, "name": base_name(b), "digits": to_base(v, b)})
    return rows


def render_bases(value: int, base_seq=(2, 3, 8, 10, 16),
                 signed: bool = False, width: int = 0) -> List[str]:
    """多进制对照文本。**十进制标为「人类可读·默认」并排在最前**。

    设计取舍（呼应「使用者显示为一般可读，用十进制」）：
    - 屏幕第一眼是十进制（带千分位），其余进制作为底层参考排在下面；
    - 三/四/八/十二/二十/三十六/六十进制等长串用每 3 位空格分组，避免一眼数位数；
    - 二进制仍走 group_bits（按 4 位一组，和 hex 对齐），不在此处二次分组。
    """
    v = int(value)
    if signed and width > 0:
        v = from_twos(v & mask(width), width)
    rows = {r["base"]: r for r in bases(v, base_seq)}
    lines = [_("进制对照（输入 = %s）") % human_int(value)]
    dec = rows.get(10)
    if dec is not None:
        lines.append(_("  十进制（人类可读·默认）: %s") % dec["digits"])
        lines.append("  " + "─" * 38)
    order = [2, 3, 4, 8, 9, 12, 16, 20, 24, 32, 36, 60]
    shown = 0
    for b in order:
        r = rows.get(b)
        if r is None:
            continue
        shown += 1
        if b == 2:
            digits = group_bits(r["digits"], 4)
        elif b in (3, 4, 8, 9, 12, 20, 24, 32, 36, 60):
            digits = _group_digits(r["digits"], 3)
        else:
            digits = r["digits"]
        lines.append("  %s (%-2d): %s" % (r["name"], r["base"], digits))
    return lines


def convert_base(text: str, base_in: int = 0, bases_out=(2, 3, 8, 10, 16)) -> Optional[Dict]:
    """任意进制字符串 → 十进制（人类可读）并展开成多进制对照。

    base_in 为 0 时按前缀自动识别（0b/0o/0x），否则按给定进制解析。
    解析失败返回 None（不抛异常）。
    """
    n = from_base(text, base_in) if base_in else from_base(text, default_base=10)
    if n is None:
        return None
    return {"value": n, "human": human_int(n), "bases": bases(n, bases_out)}


def to_hex(value: int, width: int = 0, upper: bool = True, prefix: bool = True) -> str:
    """整数 → 十六进制字符串（width 按半字节数计，8 → 32 位）。"""
    body = to_base(value, 16, width, upper)
    return ("0x" + body) if prefix else body


def from_hex(text: str) -> Optional[int]:
    return from_base(text, 16)


def to_oct(value: int, width: int = 0, prefix: bool = True) -> str:
    body = to_base(value, 8, width, True)
    return ("0o" + body) if prefix else body


def from_oct(text: str) -> Optional[int]:
    return from_base(text, 8)


def group_bits(bits: str, group: int = 4, sep: str = " ") -> str:
    """位串分组显示，如 `0011 1010`。"""
    s = str(bits)
    if group <= 0:
        return s
    chunks = [s[i:i + group] for i in range(0, len(s), group)]
    return sep.join(chunks)


def dump(data: bytes, base: int = 16, per_line: int = 16) -> List[str]:
    """字节序列 → 十六进制转储行（偏移 + 字节 + ASCII 可打印回显）。

    形如 `00000000  48 65 6c 6c 6f  |Hello|`。纯文本，便于 CLI 打印。
    """
    lines = []
    if not isinstance(data, (bytes, bytearray, memoryview)):
        return lines
    data = bytes(data)
    for off in range(0, len(data), per_line):
        chunk = data[off:off + per_line]
        if base == 16:
            hexpart = " ".join(format(b, "02x") for b in chunk)
        elif base == 2:
            hexpart = " ".join(format(b, "08b") for b in chunk)
        elif base == 8:
            hexpart = " ".join(format(b, "03o") for b in chunk)
        else:
            hexpart = " ".join(str(b) for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append("%08x  %-*s  |%s|" % (off, per_line * 3 - 1, hexpart, ascii_part))
    return lines


# ---------------------------------------------------------------- 位统计


def popcount(value: int) -> int:
    """置位个数（Hamming weight）。

    负数按"最小补码宽度"计算（-1 → 1）。Python 3.8 无 `int.bit_count`，
    故手写，避免引入版本分支。
    """
    v = int(value)
    if v < 0:
        v &= mask((~v).bit_length() + 1)
    return bin(v).count("1")


def parity(value: int, even: bool = True) -> int:
    """返回应附加的奇偶校验位。even=True 为偶校验（含校验位后 1 的个数为偶）。"""
    ones = popcount(value)
    if even:
        return ones & 1          # 奇数个 1 → 补 1 使总数为偶
    return 1 - (ones & 1)


def parity_ok(value: int, width: int, even: bool = True) -> bool:
    """校验带校验位的 `width` 位数据：1 的个数是否符合偶/奇校验。"""
    return (popcount(value) & 1) == (0 if even else 1)


def clz(value: int, width: int) -> int:
    """前导零个数（count leading zeros），按 `width` 位计。"""
    v = int(value) & mask(width)
    if v == 0:
        return width
    return width - v.bit_length()


def ctz(value: int, width: Optional[int] = None) -> int:
    """尾随零个数（count trailing zeros）。value=0 且给了 width → width。"""
    v = int(value)
    if v == 0:
        return width if width else 0
    n = 0
    while v & 1 == 0:
        v >>= 1
        n += 1
    return n


def hamming_distance(a: int, b: int) -> int:
    """两个整数的汉明距离（不同位的个数）。"""
    return popcount(int(a) ^ int(b))


def reverse_bits(value: int, width: int) -> int:
    """在 `width` 位内反转位序。"""
    s = to_bits(value, width)
    return from_bits(s[::-1]) or 0


def rol(value: int, width: int, n: int) -> int:
    """循环左移（位旋转）。"""
    w = max(1, width)
    n %= w
    v = int(value) & mask(w)
    return ((v << n) | (v >> (w - n))) & mask(w) if n else v


def ror(value: int, width: int, n: int) -> int:
    """循环右移。"""
    return rol(value, width, (-n) % max(1, width))


# ---------------------------------------------------------------- 位域


def extract(value: int, lsb: int, count: int) -> int:
    """从 `value` 的第 `lsb` 位起取 `count` 位（lsb 从 0 计）。"""
    if count <= 0:
        return 0
    return (int(value) >> lsb) & mask(count)


def deposit(value: int, lsb: int, count: int, field: int) -> int:
    """把 `field` 写到 `value` 的第 `lsb` 位起的 `count` 位，其余位保留。"""
    if count <= 0:
        return int(value)
    m = mask(count)
    return (int(value) & ~(m << lsb)) | ((int(field) & m) << lsb)


def bitfields(value: int, layout: List) -> List[Dict]:
    """按布局拆位域。layout = [(name, lsb, count), ...]（低位在前）。

    返回每个域的 name/lsb/count/value/bin/hex。
    """
    out = []
    for item in layout:
        name, lsb, count = item[0], item[1], item[2]
        v = extract(value, lsb, count)
        out.append({"name": name, "lsb": lsb, "count": count, "value": v,
                    "bin": to_bits(v, count), "hex": to_hex(v, (count + 3) // 4 or 1)})
    return out


def render_bitfields(value: int, layout: List, width: int = 32) -> List[str]:
    """把位域画成可视行：高位在左，用域名首字母标出每段的归属。"""
    rows = []
    fields = bitfields(value, layout)
    # 逐位标注归属
    owner = ["·"] * max(width, 1)
    for f in fields:
        for i in range(f["lsb"], min(f["lsb"] + f["count"], len(owner))):
            owner[i] = f["name"][:1]
    rows.append("位   : " + "".join(str((width - 1 - i) % 10) for i in range(width)))
    rows.append("值   : " + group_bits(to_bits(value, width), 4))
    rows.append("域   : " + group_bits("".join(reversed(owner)), 4))
    for f in reversed(fields):
        rows.append("%-6s: %s = %d" % (f["name"], f["hex"], f["value"]))
    return rows


# ---------------------------------------------------------------- 有符号数


def to_twos(value: int, width: int) -> int:
    """有符号整数 → `width` 位补码的无符号表示。溢出则截断。"""
    w = max(1, width)
    return int(value) & mask(w)


def from_twos(value: int, width: int) -> int:
    """`width` 位补码 → 有符号整数。"""
    w = max(1, width)
    v = int(value) & mask(w)
    if v & (1 << (w - 1)):
        v -= 1 << w
    return v


def to_ones(value: int, width: int) -> int:
    """有符号整数 → `width` 位反码表示（负数逐位取反）。"""
    v = int(value)
    if v >= 0:
        return v & mask(width)
    return (~(-v)) & mask(width)


def from_ones(value: int, width: int) -> int:
    v = int(value) & mask(width)
    if v & (1 << (width - 1)):
        return -( (~v) & mask(width) )
    return v


def to_sign_magnitude(value: int, width: int) -> int:
    """有符号整数 → `width` 位原码（最高位符号，其余绝对值）。"""
    m = mask(width - 1)
    if int(value) < 0:
        return (1 << (width - 1)) | (abs(int(value)) & m)
    return int(value) & m


def from_sign_magnitude(value: int, width: int) -> int:
    v = int(value) & mask(width)
    sign = v >> (width - 1)
    mag = v & mask(width - 1)
    return -mag if sign else mag


def sign_extend(value: int, width: int) -> int:
    """把 `width` 位有符号数符号扩展到 Python 整数（等from_twos）。"""
    return from_twos(value, width)


def representations(value: int, width: int = 8) -> Dict:
    """同一个数在 4 种表示下的位模式对比（教学/排查用）。"""
    w = max(2, width)
    return {
        "value": int(value),
        "width": w,
        "range_twos": [-(1 << (w - 1)), (1 << (w - 1)) - 1],
        "twos": {"bin": to_bits(to_twos(value, w), w), "hex": to_hex(to_twos(value, w), (w + 3) // 4)},
        "ones": {"bin": to_bits(to_ones(value, w), w), "hex": to_hex(to_ones(value, w), (w + 3) // 4)},
        "sign_magnitude": {"bin": to_bits(to_sign_magnitude(value, w), w),
                           "hex": to_hex(to_sign_magnitude(value, w), (w + 3) // 4)},
        "unsigned": {"bin": to_bits(int(value) & mask(w), w),
                     "hex": to_hex(int(value) & mask(w), (w + 3) // 4)},
        "overflow": not (-(1 << (w - 1)) <= int(value) <= (1 << (w - 1)) - 1),
    }


# ---------------------------------------------------------------- 格雷码 / BCD


def to_gray(value: int, width: Optional[int] = None) -> int:
    """二进制 → 格雷码：g = n ^ (n >> 1)。"""
    v = int(value)
    if width:
        v &= mask(width)
    return v ^ (v >> 1)


def from_gray(gray: int, width: Optional[int] = None) -> int:
    """格雷码 → 二进制（逐位异或前缀还原）。"""
    g = int(gray)
    if width:
        g &= mask(width)
    n = g
    while g > 1:
        g >>= 1
        n ^= g
    return n


def to_bcd(value: int) -> int:
    """十进制整数 → BCD（每个十进制数字占 4 位）。1234 → 0x1234。"""
    v = abs(int(value))
    if v == 0:
        return 0
    out = 0
    shift = 0
    while v:
        out |= (v % 10) << shift
        v //= 10
        shift += 4
    return out


def from_bcd(bcd: int) -> Optional[int]:
    """BCD → 十进制整数。含非 0-9 的半字节时返回 None（非法 BCD）。"""
    v = int(bcd)
    out = 0
    mult = 1
    if v == 0:
        return 0
    while v:
        d = v & 0xF
        if d > 9:
            return None
        out += d * mult
        mult *= 10
        v >>= 4
    return out


def pack_bcd(value: int, width: int = 0) -> bytes:
    """十进制整数 → 压缩 BCD 字节串（2 位数字/字节）。"""
    s = str(abs(int(value)))
    if len(s) % 2:
        s = "0" + s
    length = max(len(s) // 2, width)
    s = s.rjust(length * 2, "0")
    return bytes(int(s[i:i + 2], 16) for i in range(0, len(s), 2))


def unpack_bcd(data: bytes) -> Optional[int]:
    """压缩 BCD 字节串 → 十进制整数。"""
    try:
        s = "".join(format(b, "02x") for b in bytes(data))
    except (TypeError, ValueError):
        return None
    if any(c not in "0123456789" for c in s):
        return None
    return int(s) if s else 0


# ---------------------------------------------------------------- 端序


def pack_int(value: int, size: int = 4, byteorder: str = "little", signed: bool = False) -> Optional[bytes]:
    """整数 → 定长字节串（size 字节）。越界返回 None。"""
    if size <= 0 or byteorder not in ("little", "big"):
        return None
    try:
        return int(value).to_bytes(size, byteorder, signed=signed)
    except OverflowError:
        return None


def unpack_int(data: bytes, byteorder: str = "little", signed: bool = False) -> Optional[int]:
    """字节串 → 整数。"""
    if not data:
        return None
    return int.from_bytes(bytes(data), byteorder, signed=signed)


def swap_bytes(data: bytes, group: int = 2) -> bytes:
    """按 `group` 字节为一组反转组内顺序（group=len → 整体反转）。"""
    b = bytes(data)
    if group <= 0:
        return b
    out = bytearray()
    for i in range(0, len(b), group):
        out.extend(b[i:i + group][::-1])
    return bytes(out)


def endian_convert(value: int, size: int = 4, src: str = "little", dst: str = "big") -> Optional[int]:
    """同一数值的字节序列被按**另一端序**读出时的值。

    例：0x12345678 以小端存成 `78 56 34 12`，把这串字节按大端读就是
    0x78563412——这正是抓包时"数值看着不对"的典型原因。字节反转是对合
    运算，因此正反向结果相同。
    """
    raw = pack_int(value, size, src)
    if raw is None:
        return None
    return unpack_int(raw, dst)


def endian_view(value: int, size: int = 4) -> Dict:
    """给出同一数值在大端/小端下的字节序列与十六进制，便于对照。"""
    big = pack_int(value, size, "big")
    little = pack_int(value, size, "little")
    if big is None:
        return {"error": "数值超出 %d 字节无符号范围" % size}
    return {
        "value": int(value),
        "size": size,
        "big": {"hex": big.hex(), "bytes": list(big),
                "msb_first": " ".join(format(b, "02x") for b in big)},
        "little": {"hex": little.hex(), "bytes": list(little),
                   "wire_order": " ".join(format(b, "02x") for b in little)},
        "swapped_value": unpack_int(big[::-1], "little"),
    }


def host_endian() -> str:
    """当前解释器所在平台的字节序（用 sys.byteorder）。"""
    import sys
    return sys.byteorder


# ---------------------------------------------------------------- IEEE 754


#: 位宽 → (指数位数, 尾数显式位数, bias)
FLOAT_FORMATS = {16: (5, 10, 15), 32: (8, 23, 127), 64: (11, 52, 1023),
                 128: (15, 112, 16383)}


def decode_float(value: int, width: int = 32) -> Dict:
    """把 IEEE 754 位模式拆成 sign / exponent / mantissa 并算出真值。

    width 支持 16（binary16，交换格式）/ 32 / 64 / 128。返回字典含
    `class` 字段：zero / subnormal / normal / infinity / nan。
    """
    if width not in FLOAT_FORMATS:
        return {"error": "不支持的位宽：%r（支持 16/32/64/128）" % width}
    e_bits, m_bits, bias = FLOAT_FORMATS[width]
    v = int(value) & mask(width)
    sign = v >> (width - 1)
    exp = extract(v, m_bits, e_bits)
    mant = v & mask(m_bits)
    out = {
        "width": width, "raw": v, "hex": to_hex(v, width // 4),
        "bin": group_bits(to_bits(v, width), (width // 8)),
        "sign": sign, "sign_char": "-" if sign else "+",
        "exponent_raw": exp, "exponent_unbiased": exp - bias, "bias": bias,
        "mantissa_raw": mant,
        "mantissa_bits": m_bits,
    }
    if exp == mask(e_bits):
        out["class"] = "nan" if mant else "infinity"
        out["value"] = float("nan") if mant else (float("-inf") if sign else float("inf"))
        return out
    if exp == 0 and mant == 0:
        out["class"] = "zero"
        out["value"] = -0.0 if sign else 0.0
        return out
    if exp == 0:
        out["class"] = "subnormal"
        significand = mant / float(1 << m_bits)
        out["value"] = (-1 if sign else 1) * significand * (2.0 ** (1 - bias))
    else:
        out["class"] = "normal"
        significand = 1.0 + mant / float(1 << m_bits)
        out["value"] = (-1 if sign else 1) * significand * (2.0 ** (exp - bias))
    out["significand"] = significand
    out["ulp"] = 2.0 ** (max(out["exponent_unbiased"], 1 - bias) - m_bits)
    return out


def encode_float(x: float, width: int = 32) -> Optional[int]:
    """Python float → IEEE 754 位模式整数。"""
    try:
        if width == 16:
            # struct 无 'e' 之外的直接支持？Python 3.6+ 有 'e'（半精度）
            raw = struct.pack(">e", float(x))
        elif width == 32:
            raw = struct.pack(">f", float(x))
        elif width == 64:
            raw = struct.pack(">d", float(x))
        else:
            return None
    except (OverflowError, ValueError, struct.error):
        return None
    return int.from_bytes(raw, "big")


def float_bits(x: float, width: int = 32) -> Dict:
    """一步到位：float → 位模式 → 拆解（含 struct 交叉校验）。"""
    raw = encode_float(x, width)
    if raw is None:
        return {"error": "无法表示为 %d 位浮点" % width}
    info = decode_float(raw, width)
    info["input"] = x
    # 交叉校验：struct 往返（binary16 用 numpy 也没有，纯 struct 即可）
    back = decode_float(raw, width).get("value")
    info["roundtrip_ok"] = (back == x) or (repr(back) == repr(float(x)))
    return info


# ---------------------------------------------------------------- 文本渲染


def explain(value: int, width: int = 32) -> List[str]:
    """对任意整数给出一份"底层档案"文本（CLI 直接打印）。"""
    v = int(value)
    w = max(1, width)
    u = v & mask(w)
    lines = [
        _("数值档案（位宽 %d）") % w,
        _("  十进制(可读): %s  (0x%s)") % (human_int(u), to_hex(u, (w + 3) // 4, prefix=False)),
        _("  有符号    : %s") % human_int(from_twos(u, w)),
        _("  二进制    : %s") % group_bits(to_bits(u, w), 4),
        _("  三进制    : %s") % _group_digits(to_base(u, 3), 3),
        _("  八进制    : %s") % to_oct(u),
        _("  位宽需求  : 无符号 %d 位 / 有符号 %d 位") % (min_width(u), min_width(from_twos(u, w), True)),
        _("  popcount  : %d（1 的个数）") % popcount(u),
        _("  前导零    : %d    尾随零: %d") % (clz(u, w), ctz(u, w)),
        _("  偶校验位  : %d    奇校验位: %d") % (parity(u, True), parity(u, False)),
        _("  格雷码    : 0x%s") % to_hex(to_gray(u, w), (w + 3) // 4, prefix=False),
        _("  位反转    : 0x%s") % to_hex(reverse_bits(u, w), (w + 3) // 4, prefix=False),
    ]
    if w >= 16:
        lines.append(_("  大端字节  : %s") % " ".join(format(b, "02x") for b in pack_int(u, w // 8, "big")))
        lines.append(_("  小端字节  : %s") % " ".join(format(b, "02x") for b in pack_int(u, w // 8, "little")))
    return lines
