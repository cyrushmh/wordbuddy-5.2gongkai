"""comm —— 通信码层。

数据在"线上"要经历四件事，本模块各给一组可验算的纯函数：

1. **检错**——CRC 系列（CRC-8/16/32/32C…）、校验和（Internet / LRC /
   Fletcher / Adler / XOR）；
2. **成帧**——怎么让接收方知道一帧从哪开始、到哪结束：HDLC 字节填充、
   SLIP、COBS、HDLC 比特填充（零比特插入）；
3. **线路编码**——NRZ / NRZI / 曼彻斯特 / 差分曼彻斯特 / AMI / HDB3；
4. **纠错与时序**——汉明(7,4) 与 SECDED(8,4)、UART 帧时间、波特率误差。

CRC 用**通用位运算模型**实现（宽度/多项式/初值/输入反转/输出反转/异或输出
六个参数），而不是给每个变种糊一段 magic number——这样任何一份协议文档上
写的参数都能直接喂进来。每个内置变种都带标准测试向量（`"123456789"` 的
check 值），并由单元测试独立核验。

标准出处（STANDARD_REFS）
------------------------
仅用于定位规范；**实现的正确性由本仓库单测独立验证**，不依赖任何外部文档
的可信度。出处按「国内 / 国际 / 地区」三层给出。

纯标准库、纯函数、只读。
"""

from __future__ import annotations
from sysweeper.i18n import _

import zlib
from typing import Dict, List, Optional, Tuple

STANDARD_REFS = {
    "crc16ccitt": {
        "cn": "GB/T 34520-2017（工业通信相关）；CRC 本身无独立国标",
        "intl": "ITU-T 建议中 CCITT CRC-16；ISO/IEC 13239（HDLC 规程）",
        "regional": "—",
    },
    "crc32": {
        "cn": "—",
        "intl": "IEEE 802.3-2018 Clause 3（FCS）；ITU-T V.42（LAPM）",
        "regional": "—",
    },
    "modbus": {
        "cn": "GB/T 19582-2008《基于 Modbus 协议的工业自动化网络规范》",
        "intl": "Modbus over serial line V1.02；IEC 61158 系列",
        "regional": "—",
    },
    "internet_checksum": {
        "cn": "—",
        "intl": "RFC 1071（计算）；RFC 791 / RFC 793（IPv4/TCP 头部使用）",
        "regional": "—",
    },
    "adler": {
        "cn": "—",
        "intl": "RFC 1950（zlib 规格）；Fletcher 见 RFC 905 附录",
        "regional": "—",
    },
    "hdlc": {
        "cn": "GB/T 7421-1987（高级数据链路控制规程，等同 ISO/IEC 3309 体系）",
        "intl": "ISO/IEC 13239；RFC 1662（PPP 异步 HDLC 成帧）",
        "regional": "—",
    },
    "slip": {
        "cn": "—",
        "intl": "RFC 1055（SLIP）",
        "regional": "—",
    },
    "cobs": {
        "cn": "—",
        "intl": "Cheshire & Baker, ACM SIGCOMM 1997（COBS 论文）",
        "regional": "—",
    },
    "manchester": {
        "cn": "GB/T 20540 系列（工业现场总线，含曼彻斯特编码物理层）",
        "intl": "IEEE 802.3-2018 Clause 1（10BASE-T 曼彻斯特编码）",
        "regional": "—",
    },
    "hdb3": {
        "cn": "GB/T 7611-2016（数字网系列接口，脉冲编码调制）",
        "intl": "ITU-T G.703（HDB3 为 E1 2.048 Mbit/s 接口码型）",
        "regional": "ETSI EN 300 687（接入网接口）",
    },
    "uart": {
        "cn": "GB/T 6107（数据终端设备与数据电路终接设备间的串行接口，等同 ITU-T V.24）",
        "intl": "TIA/EIA-232-F；ITU-T V.24 / V.28",
        "regional": "—",
    },
    "hamming": {
        "cn": "—",
        "intl": "R. W. Hamming, Bell System Technical Journal 1950",
        "regional": "—",
    },
}

CAPABILITIES = [
    "通用 CRC 模型（宽度/多项式/初值/双反转/异或输出）与内置变种表",
    "CRC 附加与校验（含 Modbus RTU 帧实测）",
    "校验和：Internet（RFC 1071）/ LRC / XOR / Fletcher-16-32 / Adler-32",
    "成帧：HDLC 字节填充、PPP 异步(AHDLC)、SLIP、COBS、HDLC 零比特插入",
    "线路编码：NRZ-L / NRZ-I / 曼彻斯特 / 差分曼彻斯特 / AMI / HDB3",
    "汉明(7,4) 编解码与 SECDED(8,4) 单错纠正双错检测",
    "UART 帧结构、每字节位数与传输耗时估算",
    "波特率误差与常见波特率表",
]

# ---------------------------------------------------------------- 位工具


def _mask(width: int) -> int:
    return (1 << width) - 1 if width > 0 else 0


def _reverse(value: int, width: int) -> int:
    s = format(int(value) & _mask(width), "0%db" % width)
    return int(s[::-1], 2) if s else 0


# ---------------------------------------------------------------- CRC


def crc_spec(name: str, width: int, poly: int, init: int = 0,
             refin: bool = False, refout: bool = False,
             xorout: int = 0, standard: str = "", note: str = "") -> Dict:
    """构造一份 CRC 参数（六参数模型，见 RevEng / Rocksoft 命名法）。"""
    return {"name": name, "width": width, "poly": poly & _mask(width),
            "init": init & _mask(width), "refin": refin, "refout": refout,
            "xorout": xorout & _mask(width), "standard": standard, "note": note}


#: 内置 CRC 变种表。check = 对 b"123456789" 的标准校验值（由单测核验）
CRC_CATALOG = {
    "crc8": crc_spec("CRC-8/SMBUS", 8, 0x07, 0x00, False, False, 0x00,
                     "SMBus / I2C 常用", "check=0xF4"),
    "crc8-maxim": crc_spec("CRC-8/MAXIM", 8, 0x31, 0x00, True, True, 0x00,
                           "Dallas/Maxim 1-Wire", "check=0xA1"),
    "crc16-ccitt": crc_spec("CRC-16/CCITT-FALSE", 16, 0x1021, 0xFFFF,
                            False, False, 0x0000,
                            "ISO/IEC 13239；X.25 早期实现", "check=0x29B1"),
    "crc16-xmodem": crc_spec("CRC-16/XMODEM", 16, 0x1021, 0x0000,
                             False, False, 0x0000,
                             "XMODEM 文件传输", "check=0x31C3"),
    "crc16-modbus": crc_spec("CRC-16/MODBUS", 16, 0x8005, 0xFFFF,
                             True, True, 0x0000,
                             "GB/T 19582-2008；Modbus RTU", "check=0x4B37"),
    "crc16-usb": crc_spec("CRC-16/USB", 16, 0x8005, 0xFFFF, True, True, 0xFFFF,
                          "USB 令牌包 CRC", "check=0xB4C8"),
    "crc32": crc_spec("CRC-32/ISO-HDLC", 32, 0x04C11DB7, 0xFFFFFFFF,
                      True, True, 0xFFFFFFFF,
                      "IEEE 802.3 FCS / ITU-T V.42 / zlib", "check=0xCBF43926"),
    "crc32c": crc_spec("CRC-32C", 32, 0x1EDC6F41, 0xFFFFFFFF, True, True,
                       0xFFFFFFFF,
                       "Castagnoli；iSCSI / SCTP / ext4", "check=0xE3069283"),
}

#: name → 对 b"123456789" 的期望值（测试用，来源：各变种公开 check 值）
CRC_CHECK_VALUES = {
    "crc8": 0xF4, "crc8-maxim": 0xA1,
    "crc16-ccitt": 0x29B1, "crc16-xmodem": 0x31C3,
    "crc16-modbus": 0x4B37, "crc16-usb": 0xB4C8,
    "crc32": 0xCBF43926, "crc32c": 0xE3069283,
}

#: Modbus RTU 请求帧经典示例：01 03 00 00 00 01 → CRC 应为 0x84 0x0A
MODBUS_SAMPLE = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x01])
MODBUS_SAMPLE_CRC = 0x0A84  # 线上字节序 低字节在前：84 0A


def crc(data: bytes, spec: Dict) -> int:
    """按六参数模型逐位计算 CRC（教学优先：慢但和文档一一对应）。"""
    width = int(spec["width"])
    poly = int(spec["poly"])
    mask = _mask(width)
    reg = int(spec["init"]) & mask
    top = 1 << (width - 1)
    refin = bool(spec["refin"])
    for byte in bytes(data):
        b = _reverse(byte, 8) if refin else byte
        if width >= 8:
            reg ^= b << (width - 8)
        else:
            reg ^= b >> (8 - width)
        reg &= mask
        for _ in range(8):
            if reg & top:
                reg = ((reg << 1) ^ poly) & mask
            else:
                reg = (reg << 1) & mask
    if spec["refout"]:
        reg = _reverse(reg, width)
    return (reg ^ int(spec["xorout"])) & mask


def crc_table(spec: Dict) -> List[int]:
    """生成 256 项查表（宽度 8 时长度 256；更宽则按高字节表）。"""
    width = int(spec["width"])
    poly = int(spec["poly"])
    mask = _mask(width)
    top = 1 << (width - 1)
    if width >= 8:
        size = 256
        def entry(i): return i << (width - 8)
    else:
        size = 2 ** width
        def entry(i): return i
    table = []
    for i in range(size):
        reg = entry(i) & mask
        for _ in range(8):
            if reg & top:
                reg = ((reg << 1) ^ poly) & mask
            else:
                reg = (reg << 1) & mask
        table.append(reg & mask)
    return table


def crc_named(data: bytes, name: str = "crc32") -> Optional[int]:
    """按内置名称计算。未知名称返回 None。"""
    spec = CRC_CATALOG.get(name)
    if spec is None:
        return None
    return crc(data, spec)


def crc_report(data: bytes, name: str = "crc32") -> Dict:
    """算 CRC 并给出参数回显，便于与协议文档逐项核对。"""
    spec = CRC_CATALOG.get(name)
    if spec is None:
        return {"error": "未知 CRC 变种 %r（支持 %s）" % (name, "/".join(CRC_CATALOG))}
    value = crc(data, spec)
    width = spec["width"]
    return {
        "name": spec["name"], "key": name, "width": width,
        "poly": "0x%X" % spec["poly"], "init": "0x%X" % spec["init"],
        "refin": spec["refin"], "refout": spec["refout"],
        "xorout": "0x%X" % spec["xorout"],
        "value": value,
        "hex": "0x%0*X" % (width // 4, value),
        "standard": spec["standard"], "note": spec["note"],
    }


def crc_append(data: bytes, name: str = "crc16-modbus") -> Optional[bytes]:
    """把 CRC 追加到数据尾部。宽度 > 8 时按**小端字节序**追加（Modbus 惯例）。"""
    spec = CRC_CATALOG.get(name)
    if spec is None:
        return None
    value = crc(data, spec)
    nbytes = (spec["width"] + 7) // 8
    if nbytes <= 1:
        return bytes(data) + bytes([value])
    return bytes(data) + value.to_bytes(nbytes, "little")


def crc_verify(frame: bytes, name: str = "crc16-modbus") -> Dict:
    """校验"数据+CRC"的帧：分离、重算、比对。"""
    spec = CRC_CATALOG.get(name)
    if spec is None:
        return {"error": "未知 CRC 变种 %r" % name}
    nbytes = (spec["width"] + 7) // 8
    if len(frame) <= nbytes:
        return {"error": "帧太短（%d 字节，CRC 占 %d 字节）" % (len(frame), nbytes)}
    body, tail = frame[:-nbytes], frame[-nbytes:]
    got = int.from_bytes(tail, "little")
    want = crc(body, spec)
    return {"ok": got == want, "received": got, "computed": want,
            "received_hex": "0x%0*X" % (nbytes * 2, got),
            "computed_hex": "0x%0*X" % (nbytes * 2, want),
            "payload": body, "payload_hex": body.hex()}


def render_crc_catalog(data: bytes = b"123456789") -> List[str]:
    """把所有内置变种在同一份数据上的结果列成表（含 check 值比对）。"""
    lines = ["CRC 变种对照（数据 %s，%d 字节）" % (data.hex(), len(data)),
             "%-14s %-22s %-6s %-12s %s" % ("键名", "规范名", "宽度", "结果", "标准 check")]
    for key, spec in CRC_CATALOG.items():
        r = crc_report(data, key)
        expect = CRC_CHECK_VALUES.get(key)
        sample = b"123456789"
        if data == sample and expect is not None:
            ok = "✓" if r["value"] == expect else "✗(期望 0x%X)" % expect
        else:
            ok = "—"
        lines.append("%-14s %-22s %-6d %-12s %s" % (
            key, r["name"], r["width"], r["hex"], ok))
    return lines


# ---------------------------------------------------------------- 校验和


#: RFC 1071 第 3 节的示例字节：00 01 f2 03 f4 f5 f6 f7
RFC1071_SAMPLE = bytes([0x00, 0x01, 0xF2, 0x03, 0xF4, 0xF5, 0xF6, 0xF7])
#: 该示例的 16 位反码**和**（RFC 原文给出的中间结果）
RFC1071_SUM = 0xDDF2
#: 填入校验字段的值 = 和的反码。常被误记成 0xDDF2，实为 0x220D
RFC1071_CHECKSUM = 0x220D


def _ones_complement_sum(data: bytes, init: int = 0) -> int:
    """16 位反码和（进位回卷），不取反——即 RFC 1071 示例中的 0xDDF2。"""
    b = bytes(data)
    if len(b) % 2:
        b += b"\x00"
    total = int(init) & 0xFFFF
    for i in range(0, len(b), 2):
        total += (b[i] << 8) | b[i + 1]
        total = (total & 0xFFFF) + (total >> 16)
    return total & 0xFFFF


def internet_checksum(data: bytes, init: int = 0) -> int:
    """Internet 校验和（RFC 1071）：16 位反码和再取反。

    注意区分两个量：反码**和**（`_ones_complement_sum`）与填入头部的
    **校验和**（本函数，= 和的反码）。RFC 1071 示例里 0xDDF2 是前者，
    0x220D 才是后者；接收端把含校验字段的整段重新求和应得 0xFFFF。
    """
    return (~_ones_complement_sum(data, init)) & 0xFFFF


def internet_checksum_verify(data_with_checksum: bytes) -> bool:
    """接收端校验：含校验字段的整段反码和应为 0xFFFF。

    校验字段按**网络字节序（大端）**填入——RFC 1071 里即 `22 0d`；
    若写成 `0d 22` 本函数返回 False，这正是排查"校验和对不上"时最常见的原因。
    """
    return _ones_complement_sum(data_with_checksum) == 0xFFFF


def lrc(data: bytes, method: str = "twos") -> int:
    """纵向冗余校验。method=twos 取反加一；xor 为逐字节异或。"""
    if method == "xor":
        out = 0
        for byte in bytes(data):
            out ^= byte
        return out & 0xFF
    total = sum(bytes(data)) & 0xFF
    return ((-total) & 0xFF) if method == "twos" else total


def xor_checksum(data: bytes, width: int = 8) -> int:
    """按 `width` 位分组异或（8 → 逐字节 XOR）。"""
    mask = _mask(width)
    step = max(1, width // 8)
    out = 0
    b = bytes(data)
    for i in range(0, len(b), step):
        chunk = b[i:i + step]
        out ^= int.from_bytes(chunk, "big") & mask
    return out & mask


def fletcher16(data: bytes) -> int:
    """Fletcher-16：两个 8 位累加器模 255，常用于串行通信。"""
    s1 = s2 = 0
    for byte in bytes(data):
        s1 = (s1 + byte) % 255
        s2 = (s2 + s1) % 255
    return (s2 << 8) | s1


def fletcher32(data: bytes) -> int:
    """Fletcher-32：两个 16 位累加器模 65535。"""
    s1 = s2 = 0
    b = bytes(data)
    if len(b) % 2:
        b += b"\x00"
    for i in range(0, len(b), 2):
        word = (b[i] << 8) | b[i + 1]
        s1 = (s1 + word) % 65535
        s2 = (s2 + s1) % 65535
    return (s2 << 16) | s1


def adler32(data: bytes, init: int = 1) -> int:
    """Adler-32（RFC 1950）。用 zlib 保证与规范一致。"""
    return zlib.adler32(bytes(data), init) & 0xFFFFFFFF


def crc32_zlib(data: bytes) -> int:
    """zlib.crc32 —— 用作 CRC-32 位运算实现的交叉校验。"""
    return zlib.crc32(bytes(data)) & 0xFFFFFFFF


def checksum_report(data: bytes) -> List[Dict]:
    """同一份数据在各类校验算法下的结果。"""
    return [
        {"name": "Internet 校验和 (RFC 1071)", "value": internet_checksum(data),
         "hex": "0x%04X" % internet_checksum(data),
         "standard": "RFC 1071 / RFC 791"},
        {"name": "LRC（反码+1）", "value": lrc(data), "hex": "0x%02X" % lrc(data),
         "standard": "ISO 1155 / 串行帧常用"},
        {"name": "XOR 校验和（8 位）", "value": xor_checksum(data),
         "hex": "0x%02X" % xor_checksum(data), "standard": "简单协议常用"},
        {"name": "Fletcher-16", "value": fletcher16(data),
         "hex": "0x%04X" % fletcher16(data), "standard": "RFC 905 附录"},
        {"name": "Fletcher-32", "value": fletcher32(data),
         "hex": "0x%08X" % fletcher32(data), "standard": "RFC 905 附录"},
        {"name": "Adler-32", "value": adler32(data), "hex": "0x%08X" % adler32(data),
         "standard": "RFC 1950"},
        {"name": "CRC-32（zlib 交叉校验）", "value": crc32_zlib(data),
         "hex": "0x%08X" % crc32_zlib(data), "standard": "IEEE 802.3 / ITU-T V.42"},
    ]


def render_checksums(data: bytes) -> List[str]:
    lines = [_("校验和对照（%d 字节）") % len(data), "%-28s %-12s %s" % (_("算法"), _("结果"), _("出处"))]
    for row in checksum_report(data):
        lines.append("%-28s %-12s %s" % (row["name"], row["hex"], row["standard"]))
    return lines


# ---------------------------------------------------------------- 成帧

HDLC_FLAG = 0x7E
HDLC_ESCAPE = 0x7D
HDLC_XOR = 0x20


def hdlc_encode(data: bytes, flag: bool = True) -> bytes:
    """HDLC 字节填充：0x7E → 7D 5E，0x7D → 7D 5D，首尾加 0x7E 标志。"""
    out = bytearray()
    if flag:
        out.append(HDLC_FLAG)
    for byte in bytes(data):
        if byte in (HDLC_FLAG, HDLC_ESCAPE):
            out.append(HDLC_ESCAPE)
            out.append(byte ^ HDLC_XOR)
        else:
            out.append(byte)
    if flag:
        out.append(HDLC_FLAG)
    return bytes(out)


def hdlc_decode(frame: bytes) -> Dict:
    """HDLC 解帧：剥标志、去转义。异常返回 error 而不抛。"""
    b = bytes(frame)
    if b[:1] == bytes([HDLC_FLAG]):
        b = b[1:]
    if b[-1:] == bytes([HDLC_FLAG]):
        b = b[:-1]
    out = bytearray()
    i = 0
    while i < len(b):
        if b[i] == HDLC_ESCAPE:
            if i + 1 >= len(b):
                return {"error": _("转义字节 0x7D 后无数据（第 %d 字节）") % i, "data": bytes(out)}
            out.append(b[i + 1] ^ HDLC_XOR)
            i += 2
        elif b[i] == HDLC_FLAG:
            return {"error": _("帧内出现未转义的标志字节 0x7E（第 %d 字节）") % i,
                    "data": bytes(out)}
        else:
            out.append(b[i])
            i += 1
    return {"data": bytes(out), "error": None}


def ahdlc_encode(data: bytes) -> bytes:
    """PPP 异步 HDLC（RFC 1662）：额外转义 < 0x20 的控制字符。"""
    out = bytearray()
    for byte in bytes(data):
        if byte < 0x20 or byte in (HDLC_FLAG, HDLC_ESCAPE):
            out.append(HDLC_ESCAPE)
            out.append(byte ^ HDLC_XOR)
        else:
            out.append(byte)
    return bytes(out)


SLIP_END = 0xC0
SLIP_ESC = 0xDB
SLIP_ESC_END = 0xDC
SLIP_ESC_ESC = 0xDD


def slip_encode(data: bytes) -> bytes:
    """SLIP（RFC 1055）：END→ESC+ESC_END，ESC→ESC+ESC_ESC，首尾加 END。"""
    out = bytearray([SLIP_END])
    for byte in bytes(data):
        if byte == SLIP_END:
            out += bytes([SLIP_ESC, SLIP_ESC_END])
        elif byte == SLIP_ESC:
            out += bytes([SLIP_ESC, SLIP_ESC_ESC])
        else:
            out.append(byte)
    out.append(SLIP_END)
    return bytes(out)


def slip_decode(frame: bytes) -> Dict:
    """SLIP 解帧。"""
    b = bytes(frame)
    if b[:1] == bytes([SLIP_END]):
        b = b[1:]
    if b[-1:] == bytes([SLIP_END]):
        b = b[:-1]
    out = bytearray()
    i = 0
    while i < len(b):
        if b[i] == SLIP_ESC:
            if i + 1 >= len(b):
                return {"error": _("ESC 后无数据（第 %d 字节）") % i, "data": bytes(out)}
            nxt = b[i + 1]
            if nxt == SLIP_ESC_END:
                out.append(SLIP_END)
            elif nxt == SLIP_ESC_ESC:
                out.append(SLIP_ESC)
            else:
                return {"error": _("非法转义序列 DB %02X（第 %d 字节）") % (nxt, i),
                        "data": bytes(out)}
            i += 2
        else:
            out.append(b[i])
            i += 1
    return {"data": bytes(out), "error": None}


def cobs_encode(data: bytes) -> bytes:
    """COBS：把 0x00 替换为"到下个 0x00 的距离"，开销恒定（≤1/254）。"""
    b = bytes(data)
    out = bytearray()
    start = 0
    idx = 0
    while idx < len(b):
        if b[idx] == 0:
            out.append(idx - start + 1)
            out += b[start:idx]
            start = idx + 1
            idx += 1
        else:
            idx += 1
            if idx - start == 0xFE:
                out.append(0xFF)
                out += b[start:idx]
                start = idx
    out.append(idx - start + 1)
    out += b[start:idx]
    return bytes(out)


def cobs_decode(frame: bytes) -> Dict:
    """COBS 解码。"""
    b = bytes(frame)
    if not b:
        return {"data": b"", "error": None}
    out = bytearray()
    idx = 0
    while idx < len(b):
        code = b[idx]
        if code == 0:
            return {"error": _("第 %d 字节出现非法的 0x00 分组码") % idx, "data": bytes(out)}
        idx += 1
        end = idx + code - 1
        if end > len(b):
            return {"error": _("分组码 %d 越界（偏移 %d）") % (code, idx - 1),
                    "data": bytes(out)}
        block = b[idx:end]
        if 0 in block:
            return {"error": _("分组内出现 0x00"), "data": bytes(out)}
        out += block
        idx = end
        if code < 0xFF and idx < len(b):
            out.append(0)
    return {"data": bytes(out), "error": None}


def bit_stuff(data_bits: str, run: int = 5) -> str:
    """HDLC 零比特插入：连续 `run` 个 1 后自动插一个 0（位级成帧）。"""
    out = []
    count = 0
    for ch in str(data_bits):
        if ch == "1":
            count += 1
            out.append("1")
            if count == run:
                out.append("0")
                count = 0
        else:
            count = 0
            out.append(ch)
    return "".join(out)


def bit_unstuff(stuffed: str, run: int = 5) -> Dict:
    """零比特删除。"""
    out = []
    count = 0
    i = 0
    s = str(stuffed)
    while i < len(s):
        ch = s[i]
        if ch == "1":
            count += 1
            out.append("1")
            if count == run:
                if i + 1 < len(s) and s[i + 1] == "0":
                    i += 1      # 吃掉插入的 0
                    count = 0
        else:
            count = 0
            out.append(ch)
        i += 1
    return {"data": "".join(out), "error": None}


def framing_report(data: bytes) -> List[Dict]:
    """同一份数据在各成帧方案下的字节数与开销。"""
    rows = []
    h = hdlc_encode(data)
    rows.append({"scheme": "HDLC 字节填充", "bytes": len(h),
                 "overhead": len(h) - len(data), "hex": h.hex(),
                 "standard": "ISO/IEC 13239"})
    a = ahdlc_encode(data)
    rows.append({"scheme": "PPP 异步 HDLC", "bytes": len(a),
                 "overhead": len(a) - len(data), "hex": a.hex(),
                 "standard": "RFC 1662"})
    s = slip_encode(data)
    rows.append({"scheme": "SLIP", "bytes": len(s),
                 "overhead": len(s) - len(data), "hex": s.hex(),
                 "standard": "RFC 1055"})
    c = cobs_encode(data)
    rows.append({"scheme": "COBS", "bytes": len(c),
                 "overhead": len(c) - len(data), "hex": c.hex(),
                 "standard": "SIGCOMM 1997"})
    return rows


def render_framing(data: bytes) -> List[str]:
    lines = [_("成帧方案对比（原始 %d 字节：%s）") % (len(data), data.hex()),
             "%-16s %-8s %-8s %-40s %s" % (_("方案"), _("字节数"), _("开销"), _("结果"), _("出处"))]
    for row in framing_report(data):
        lines.append("%-16s %-8d %-8d %-40s %s" % (
            row["scheme"], row["bytes"], row["overhead"],
            row["hex"][:40], row["standard"]))
    return lines


# ---------------------------------------------------------------- 线路编码

#: scheme → (中文名, 标准出处, 一句话说明)
LINE_CODES = {
    "nrz-l": ("NRZ-L 不归零电平", "通用", "1=高电平，0=低电平，位内不变"),
    "nrz-i": ("NRZ-I 不归零反转", "USB / HDLC 位级", "1=位边界跳变，0=保持"),
    "manchester": ("曼彻斯特", "IEEE 802.3 Clause 1",
                   "每位中点必跳变：0=高→低，1=低→高（自同步，带宽翻倍）"),
    "diff-manchester": ("差分曼彻斯特", "IEEE 802.5（令牌环）",
                        "每位中点必跳变；0=位起始处跳变，1=不跳变"),
    "ami": ("AMI 传号交替反转", "ITU-T G.703", "0=零电平，1=交替 +1/-1（无直流分量）"),
    "hdb3": ("HDB3 三阶高密度双极性", "ITU-T G.703（E1）",
             "AMI 基础上把 4 连 0 换成 000V 或 B00V（保证定时恢复）"),
}


def encode_line(data_bits: str, scheme: str = "manchester") -> Dict:
    """把 0/1 位串编码为线路电平序列（2 倍采样：每位取 2 个电平点）。"""
    s = "".join(c for c in str(data_bits) if c in "01")
    if scheme not in LINE_CODES:
        return {"error": _("未知线路编码 %r（支持 %s）") % (scheme, "/".join(LINE_CODES))}
    if scheme == "nrz-l":
        levels = [1 if c == "1" else -1 for c in s]
        points = []
        for lv in levels:
            points += [lv, lv]
    elif scheme == "nrz-i":
        cur = -1
        points = []
        for c in s:
            if c == "1":
                cur = -cur
            points += [cur, cur]
    elif scheme == "manchester":
        points = []
        for c in s:
            # IEEE 802.3 约定：0 = 前半高后半低（下降沿），1 = 前半低后半高
            points += ([1, -1] if c == "0" else [-1, 1])
    elif scheme == "diff-manchester":
        # 每位中点必跳变；0 在"位起始处"额外跳变一次，1 不跳变
        cur = 1
        points = []
        for c in s:
            if c == "0":
                cur = -cur
            points += [cur, -cur]
            cur = -cur
    elif scheme == "ami":
        pol = 1
        levels = []
        for c in s:
            if c == "1":
                levels.append(pol)
                pol = -pol
            else:
                levels.append(0)
        points = []
        for lv in levels:
            points += [lv, lv]
    else:  # hdb3
        marks = hdb3(s)
        points = []
        for lv in marks:
            points += [lv[0], lv[0]]
        return {"scheme": scheme, "name": LINE_CODES[scheme][0],
                "standard": LINE_CODES[scheme][1],
                "input": s, "points": points, "levels": [lv[0] for lv in marks],
                "marks": "".join(m[1] for m in marks),
                "note": LINE_CODES[scheme][2]}
    return {"scheme": scheme, "name": LINE_CODES[scheme][0],
            "standard": LINE_CODES[scheme][1], "input": s,
            "points": points, "levels": [points[i] for i in range(0, len(points), 2)],
            "note": LINE_CODES[scheme][2]}


def hdb3(data_bits: str) -> List[Tuple[int, str]]:
    """HDB3 编码：返回 [(电平, 标记), ...]，标记为 1/0/B/V。

    规则（ITU-T G.703）：4 连 0 用 000V（距上次 V 的脉冲数为奇）或 B00V（偶）
    替换；V 与前一脉冲同极性（破坏交替），B 与前一脉冲反极性（维持交替）。
    """
    s = "".join(c for c in str(data_bits) if c in "01")
    out: List[Tuple[int, str]] = []
    last = -1            # 上一个脉冲的极性（初始为 -1 → 第一个 1 编成 +1）
    pulses = 0           # 距上次替换的脉冲数
    i = 0
    while i < len(s):
        if s[i] == "1":
            last = -last
            out.append((last, "1"))
            pulses += 1
            i += 1
            continue
        j = i
        while j < len(s) and s[j] == "0":
            j += 1
        zeros = j - i
        if zeros < 4:
            out.extend((0, "0") for _ in range(zeros))
            i = j
            continue
        for _ in range(zeros // 4):
            if pulses % 2 == 1:          # 000V
                out.extend((0, "0") for _ in range(3))
                out.append((last, "V"))
            else:                        # B00V
                last = -last
                out.append((last, "B"))
                out.extend((0, "0") for _ in range(2))
                out.append((last, "V"))
            pulses = 0
            i += 4
        out.extend((0, "0") for _ in range(zeros % 4))
        i += zeros % 4
    return out


def render_waveform(data_bits: str, scheme: str = "manchester",
                    high: str = "▔", low: str = "▁", zero: str = "─") -> List[str]:
    """把编码结果画成 ASCII 波形（每个位取两个采样点）。"""
    r = encode_line(data_bits, scheme)
    if "error" in r:
        return [r["error"]]
    pts = r["points"]
    glyph = {1: high, -1: low, 0: zero}
    wave = "".join(glyph.get(p, "?") for p in pts)
    lines = [
        "%s（%s）" % (r["name"], r["standard"]),
        _("位串 : ") + " ".join(r["input"]),
    ]
    if r.get("marks"):
        lines.append(_("标记 : ") + " ".join(r["marks"]))
    lines.append(_("波形 : ") + wave)
    lines.append(_("说明 : ") + r["note"])
    return lines


def render_line_compare(data_bits: str = "10110010") -> List[str]:
    """同一位串在各线路编码下的波形对照。"""
    lines = [_("线路编码对照（位串 %s）") % data_bits]
    for scheme in ("nrz-l", "nrz-i", "manchester", "diff-manchester", "ami", "hdb3"):
        r = encode_line(data_bits, scheme)
        if "error" in r:
            continue
        glyph = {1: "▔", -1: "▁", 0: "─"}
        wave = "".join(glyph.get(p, "?") for p in r["points"])
        lines.append("  %-16s %s" % (scheme, wave))
    return lines


# ---------------------------------------------------------------- 汉明码


def hamming74_encode(nibble: int) -> int:
    """4 位数据 → 汉明(7,4) 码字（位 1/2/4 为校验位，1 起始编号）。"""
    d = int(nibble) & 0xF
    d3 = (d >> 0) & 1   # → 位置 3
    d5 = (d >> 1) & 1   # → 位置 5
    d6 = (d >> 2) & 1   # → 位置 6
    d7 = (d >> 3) & 1   # → 位置 7
    p1 = d3 ^ d5 ^ d7
    p2 = d3 ^ d6 ^ d7
    p4 = d5 ^ d6 ^ d7
    return (p1 << 0) | (p2 << 1) | (d3 << 2) | (p4 << 3) | (d5 << 4) | (d6 << 5) | (d7 << 6)


def hamming74_syndrome(code: int) -> int:
    """计算伴随式：0 表示无错，非 0 即出错位号（1 起始）。"""
    c = int(code) & 0x7F
    bits = [(c >> i) & 1 for i in range(7)]   # bits[0] = 位置 1
    s1 = bits[0] ^ bits[2] ^ bits[4] ^ bits[6]
    s2 = bits[1] ^ bits[2] ^ bits[5] ^ bits[6]
    s4 = bits[3] ^ bits[4] ^ bits[5] ^ bits[6]
    return s1 | (s2 << 1) | (s4 << 2)


def hamming74_decode(code: int) -> Dict:
    """汉明(7,4) 解码：纠正单比特错，返回数据与错误位号。"""
    c = int(code) & 0x7F
    syn = hamming74_syndrome(c)
    fixed = c
    if syn:
        fixed = c ^ (1 << (syn - 1))
    b = [(fixed >> i) & 1 for i in range(7)]
    data = b[2] | (b[4] << 1) | (b[5] << 2) | (b[6] << 3)
    return {"data": data, "syndrome": syn,
            "error_position": syn if syn else 0,
            "corrected": fixed != c, "corrected_code": fixed,
            "status": _("无错") if syn == 0 else _("已纠正第 %d 位") % syn}


def hamming84_encode(nibble: int) -> int:
    """SECDED(8,4)：汉明(7,4) + 整体奇偶位（位 8）。"""
    c7 = hamming74_encode(nibble)
    p8 = bin(c7).count("1") & 1      # 偶校验：使 8 位中 1 的个数为偶
    return c7 | (p8 << 7)


def hamming84_decode(code: int) -> Dict:
    """SECDED(8,4) 解码：单错纠正 + 双错检测。"""
    c = int(code) & 0xFF
    syn = hamming74_syndrome(c & 0x7F)
    parity = bin(c).count("1") & 1
    b = [(c >> i) & 1 for i in range(7)]
    if syn == 0 and parity == 0:
        status = _("无错")
        fixed = c
    elif syn != 0 and parity == 1:
        fixed = (c & 0x80) | ((c & 0x7F) ^ (1 << (syn - 1)))
        status = _("单比特错，已纠正第 %d 位") % syn
    elif syn != 0 and parity == 0:
        status = _("双比特错，不可纠正（仅检测）")
        fixed = c
    else:  # syn == 0 and parity == 1
        status = _("整体奇偶位出错，已纠正第 8 位")
        fixed = c ^ 0x80
    fb = [(fixed >> i) & 1 for i in range(7)]
    data = fb[2] | (fb[4] << 1) | (fb[5] << 2) | (fb[6] << 3)
    return {"data": data, "syndrome": syn, "parity": parity,
            "status": status, "corrected_code": fixed}


def render_hamming_table() -> List[str]:
    """汉明(7,4) 全部 16 个码字（含最小距离说明）。"""
    lines = ["汉明(7,4)：数据 → 码字（最小距离 d=3，可纠 1 位错）",
             _("数据  二进制    码字")]
    for d in range(16):
        c = hamming74_encode(d)
        lines.append("  %X     %s    %s" % (
            d, format(d, "04b"), format(c, "07b")))
    return lines


# ---------------------------------------------------------------- 串口时序


def uart_frame(data_bits: int = 8, parity: str = "none", stop_bits: float = 1.0) -> Dict:
    """UART 一帧的结构：起始位 + 数据位 + 校验位 + 停止位。"""
    p = 1 if parity in ("even", "odd", "mark", "space") else 0
    total = 1 + int(data_bits) + p + float(stop_bits)
    return {"start_bits": 1, "data_bits": int(data_bits),
            "parity_bits": p, "parity": parity,
            "stop_bits": float(stop_bits),
            "bits_per_frame": total,
            "efficiency": (int(data_bits) / total) if total else 0.0,
            "standard": "TIA/EIA-232-F / ITU-T V.24"}


def uart_time(n_bytes: int, baud: int = 9600, data_bits: int = 8,
              parity: str = "none", stop_bits: float = 1.0) -> Dict:
    """传输 n 字节所需时间与吞吐。"""
    f = uart_frame(data_bits, parity, stop_bits)
    bits = f["bits_per_frame"] * max(0, int(n_bytes))
    seconds = bits / float(baud) if baud > 0 else 0.0
    return {"bytes": int(n_bytes), "baud": int(baud),
            "bits_per_frame": f["bits_per_frame"],
            "total_bits": bits, "seconds": seconds,
            "ms": seconds * 1000.0,
            "throughput_Bps": (n_bytes / seconds) if seconds > 0 else 0.0,
            "frame": f}


def baud_error(desired: int, actual: int) -> Dict:
    """波特率误差。UART 通常要求收发双方总误差 < 2%（含两端各半）。"""
    if desired <= 0:
        return {"error": _("目标波特率必须为正")}
    err = (float(actual) - float(desired)) / float(desired) * 100.0
    return {"desired": desired, "actual": actual,
            "error_percent": err, "abs_percent": abs(err),
            "within_2pct": abs(err) < 2.0,
            "note": "UART 采样裕度一般按 ±2% 掌握（收发两端累计）"}


COMMON_BAUDS = [300, 600, 1200, 2400, 4800, 9600, 19200, 38400,
                57600, 115200, 230400, 460800, 921600]


def baud_table(clock_hz: float = 16000000.0, divisor: int = 16) -> List[Dict]:
    """给定时钟与分频，算各常见波特率的实际分频值与误差（MCU 配串口用）。"""
    rows = []
    for b in COMMON_BAUDS:
        ideal = float(clock_hz) / (divisor * b)
        ubrr = int(round(ideal))
        if ubrr <= 0:
            rows.append({"baud": b, "note": "时钟过低，无法分频"})
            continue
        actual = float(clock_hz) / (divisor * ubrr)
        rows.append({"baud": b, "ideal_divisor": ideal, "divisor": ubrr,
                     "actual_baud": actual,
                     "error_percent": (actual - b) / b * 100.0})
    return rows


def render_baud_table(clock_hz: float = 16000000.0, divisor: int = 16) -> List[str]:
    lines = [_("波特率分频表（时钟 %s Hz，分频 %d）") % (
        format(clock_hz, ",.0f"), divisor),
        "%-10s %-14s %-10s %-14s %s" % (_("目标"), _("理想分频"), _("取整"), _("实际波特率"), _("误差"))]
    for row in baud_table(clock_hz, divisor):
        if "note" in row:
            lines.append("%-10d %s" % (row["baud"], row["note"]))
            continue
        lines.append("%-10d %-14.2f %-10d %-14.1f %+.2f%%" % (
            row["baud"], row["ideal_divisor"], row["divisor"],
            row["actual_baud"], row["error_percent"]))
    return lines
