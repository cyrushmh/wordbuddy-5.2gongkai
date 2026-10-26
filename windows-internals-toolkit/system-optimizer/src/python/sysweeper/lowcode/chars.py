"""chars —— 字符编码层。

从"一个字符"到"一串字节"之间到底发生了什么，是本模块要讲清楚的事：

* ASCII / IA5 那张表到底长什么样（含 33 个控制字符的名字）；
* 一个汉字在 UTF-8 / UTF-16 / GB18030 下分别是几个字节；
* Base64 为什么每 3 字节变 4 字符、urlsafe 变体改了哪两个字符；
* 百分号编码、HTML 实体、C 转义各自转义谁；
* 摩尔斯电码（ITU-R M.1677-1）；
* 编码互转时哪些字符会丢（乱码的真正原因）。

设计原则与 bits.py 一致：纯标准库、纯函数、只读、非法入参返回带 `error`
的字典而非抛异常。

标准出处（STANDARD_REFS）
------------------------
按「国内优先 / 国际 / 地区」三层给出，与 models.CATEGORY_STANDARDS 同口径。
关键几条：GB 18030-2022（国内强制）、ISO/IEC 10646 + Unicode（国际）、
ITU-T T.50（IA5，ASCII 的国际电信侧出处）、RFC 3629（UTF-8）、
RFC 4648（Base16/32/64）、RFC 3986（百分号编码）、ITU-R M.1677-1（摩尔斯）。
"""

from __future__ import annotations
from sysweeper.i18n import _

import base64
import codecs
import html
import unicodedata
import urllib.parse
from typing import Dict, List, Optional, Tuple

STANDARD_REFS = {
    "ascii": {
        "cn": "GB/T 1988-1998《信息技术 信息交换用七位编码字符集》",
        "intl": "ANSI X3.4-1986 / ISO/IEC 646 / ECMA-6；ITU-T T.50（IA5）",
        "regional": "EN 792-4（欧洲 ISO 646 变体族）",
    },
    "unicode": {
        "cn": "GB 13000-2010（等同 ISO/IEC 10646）",
        "intl": "ISO/IEC 10646 / The Unicode Standard 15.1",
        "regional": "—",
    },
    "utf8": {
        "cn": "GB/T 36377-2018（UTF-8 编码字符集）",
        "intl": "RFC 3629 / ISO/IEC 10646 Annex D",
        "regional": "—",
    },
    "gb18030": {
        "cn": "GB 18030-2022（强制性国家标准，中文信息处理必支持）",
        "intl": "—（Unicode 之外的中国国家编码，IANA 注册名 gb18030）",
        "regional": "—",
    },
    "base": {
        "cn": "—",
        "intl": "RFC 4648（Base16/Base32/Base64）；RFC 1924（Base85 趣文）",
        "regional": "—",
    },
    "percent": {
        "cn": "—",
        "intl": "RFC 3986（URI 通用语法）；WHATWG URL（浏览器实际行为）",
        "regional": "—",
    },
    "html": {
        "cn": "—",
        "intl": "WHATWG HTML Living Standard（命名字符引用表）",
        "regional": "—",
    },
    "morse": {
        "cn": "—",
        "intl": "ITU-R M.1677-1《国际摩尔斯电码》",
        "regional": "—",
    },
    "idna": {
        "cn": "—",
        "intl": "RFC 5891（IDNA2008）/ RFC 3492（Punycode）",
        "regional": "—",
    },
}

CAPABILITIES = [
    "ASCII / IA5 全表（含 33 个控制字符名称）",
    "Unicode 码点查询与字符档案（名称、类别、双向类、分解）",
    "UTF-8 / UTF-16 / UTF-32 字节序列与手工解码",
    "BOM 识别（UTF-8/16LE/16BE/32LE/32BE/GB18030）",
    "Base16 / 32 / 64 / 64url / 85 / Ascii85 编解码",
    "百分号编码（URI）与 HTML 实体转义",
    "C / JSON 风格转义与 \\x 十六进制转义",
    "摩尔斯电码（ITU-R M.1677-1）编解码",
    "Punycode / IDNA 域名编解码",
    "Unicode 规范化（NFC/NFD/NFKC/NFKD）",
    "字符集互转与「有损」检测（UTF-8 / GB18030 / Big5 / Shift-JIS …）",
]

# ---------------------------------------------------------------- ASCII 表

#: 0x00-0x1F + 0x7F 的控制字符名（ITU-T T.50 / Unicode 名称）
ASCII_CONTROL_NAMES = {
    0: "NUL Null 空字符", 1: "SOH Start of Heading 标题开始",
    2: "STX Start of Text 正文开始", 3: "ETX End of Text 正文结束",
    4: "EOT End of Transmission 传输结束", 5: "ENQ Enquiry 询问",
    6: "ACK Acknowledge 确认", 7: "BEL Bell 响铃",
    8: "BS Backspace 退格", 9: "HT Horizontal Tab 水平制表",
    10: "LF Line Feed 换行", 11: "VT Vertical Tab 垂直制表",
    12: "FF Form Feed 换页", 13: "CR Carriage Return 回车",
    14: "SO Shift Out 移出", 15: "SI Shift In 移入",
    16: "DLE Data Link Escape 数据链路转义", 17: "DC1 Device Control 1 (XON)",
    18: "DC2 Device Control 2", 19: "DC3 Device Control 3 (XOFF)",
    20: "DC4 Device Control 4", 21: "NAK Negative Acknowledge 否认",
    22: "SYN Synchronous Idle 同步空闲", 23: "ETB End of Transmission Block",
    24: "CAN Cancel 取消", 25: "EM End of Medium 介质结束",
    26: "SUB Substitute 替换", 27: "ESC Escape 转义",
    28: "FS File Separator 文件分隔符", 29: "GS Group Separator 组分隔符",
    30: "RS Record Separator 记录分隔符", 31: "US Unit Separator 单元分隔符",
    127: "DEL Delete 删除",
}

#: C 语言转义写法（源码里怎么写这个字符）
CONTROL_ESCAPES = {
    0: "\\0", 7: "\\a", 8: "\\b", 9: "\\t", 10: "\\n", 11: "\\v",
    12: "\\f", 13: "\\r", 27: "\\e", 92: "\\\\", 34: "\\\"", 39: "\\'",
}

#: 日常最有用的那几个（CLI 默认只印这些，全表按需）
KEY_CONTROLS = (0, 7, 8, 9, 10, 11, 12, 13, 26, 27, 127)


def ascii_table(start: int = 0, end: int = 128) -> List[Dict]:
    """返回 ASCII 区间内每个码点的档案。end 不含。"""
    out = []
    for cp in range(max(0, start), min(end, 128)):
        ch = chr(cp)
        out.append({
            "dec": cp,
            "hex": "0x%02X" % cp,
            "oct": "0o%02o" % cp,
            "bin": format(cp, "08b"),
            "char": ch if 32 <= cp < 127 else "",
            "display": _display(cp),
            "name": ASCII_CONTROL_NAMES.get(cp, ""),
            "escape": CONTROL_ESCAPES.get(cp, ""),
            "printable": 32 <= cp < 127,
        })
    return out


def _display(cp: int) -> str:
    if 32 <= cp < 127:
        return chr(cp)
    if cp in ASCII_CONTROL_NAMES:
        return ASCII_CONTROL_NAMES[cp].split(" ")[0]
    return "?"


def render_ascii_table(cols: int = 4, start: int = 32, end: int = 128) -> List[str]:
    """把 ASCII 表渲染成整齐的多列文本。"""
    rows = []
    cp_list = [c for c in range(max(0, start), min(end, 128))]
    per_col = (len(cp_list) + cols - 1) // cols
    grid = [cp_list[i:i + per_col] for i in range(0, len(cp_list), per_col)]
    header = []
    for _ in grid:
        header.append(_("dec hex  字符"))
    rows.append("   ".join(header).rstrip())
    for r in range(per_col):
        cells = []
        for col in grid:
            if r < len(col):
                cp = col[r]
                cells.append("%3d %02X  %s" % (cp, cp, _display(cp)))
            else:
                cells.append("")
        rows.append("   ".join(cells).rstrip())
    return rows


def render_controls() -> List[str]:
    """控制字符速查（日常排错用得到的那些）。"""
    lines = ["控制字符速查（ITU-T T.50 / GB/T 1988）"]
    for cp in KEY_CONTROLS:
        esc = CONTROL_ESCAPES.get(cp, "")
        lines.append("  0x%02X  %3d  %-4s  %-38s %s" % (
            cp, cp, _display(cp), ASCII_CONTROL_NAMES.get(cp, ""), esc))
    return lines


# ---------------------------------------------------------------- 字符档案


def char_info(ch: str) -> Dict:
    """单个字符的完整档案：码点、名称、类别、UTF-8/16/32 字节、转义。"""
    if not ch:
        return {"error": _("空输入")}
    cp = ord(ch[0])
    try:
        name = unicodedata.name(ch[0])
    except ValueError:
        name = "（无 Unicode 名称）"
    return {
        "char": ch[0],
        "codepoint": cp,
        "uplus": "U+%04X" % cp,
        "name": name,
        "category": unicodedata.category(ch[0]),
        "category_name": _category_name(unicodedata.category(ch[0])),
        "bidi": unicodedata.bidirectional(ch[0]),
        "decomposition": unicodedata.decomposition(ch[0]),
        "numeric": unicodedata.numeric(ch[0]) if unicodedata.category(ch[0]).startswith("N") else None,
        "utf8": utf8_info(ch[0]),
        "utf16": ch[0].encode("utf-16-le", "replace").hex(),
        "utf32": ch[0].encode("utf-32-le", "replace").hex(),
        "html": "&#%d;" % cp,
        "json_escape": json_escape(ch[0]),
        "python_escape": ch[0].encode("unicode_escape").decode("ascii", "replace"),
        "percent": percent_encode(ch[0]),
    }


def _category_name(cat: str) -> str:
    return {
        "Lu": "大写字母", "Ll": "小写字母", "Lt": "标题字母", "Lm": "修饰字母",
        "Lo": "其他字母", "Mn": "非间距标记", "Mc": "间距组合标记",
        "Me": "封闭组合标记", "Nd": "十进制数字", "Nl": "字母数字",
        "No": "其他数字", "Pc": "连接标点", "Pd": "破折号标点",
        "Ps": "开始标点", "Pe": "结束标点", "Pi": "前引号", "Pf": "后引号",
        "Po": "其他标点", "Sm": "数学符号", "Sc": "货币符号",
        "Sk": "修饰符号", "So": "其他符号", "Zs": "空格分隔符",
        "Zl": "行分隔符", "Zp": "段分隔符", "Cc": "控制字符",
        "Cf": "格式字符", "Cs": "代理项", "Co": "私用区", "Cn": "未分配",
    }.get(cat, cat)


def describe_text(text: str, limit: int = 16) -> List[Dict]:
    """对一段文本的每个字符给出简要档案（默认最多 16 个）。"""
    out = []
    for ch in str(text)[:max(0, limit)]:
        cp = ord(ch)
        out.append({
            "char": ch if ch.isprintable() else "",
            "uplus": "U+%04X" % cp,
            "dec": cp,
            "utf8_hex": ch.encode("utf-8", "replace").hex(),
            "utf8_len": len(ch.encode("utf-8", "replace")),
            "category": unicodedata.category(ch),
        })
    return out


def render_text_bytes(text: str) -> List[str]:
    """把一段文本按字符 / 码点 / UTF-8 字节逐行画出来。"""
    lines = ["字符  码点    UTF-8 字节"]
    for ch in str(text):
        raw = ch.encode("utf-8", "replace")
        lines.append("  %s   U+%04X  %s" % (
            ch if ch.isprintable() else "·", ord(ch),
            " ".join(format(b, "02X") for b in raw)))
    return lines


# ---------------------------------------------------------------- UTF-8


def utf8_info(ch: str) -> Dict:
    """单个字符的 UTF-8 编码细节：几字节、模板、实际字节。"""
    cp = ord(ch[0]) if ch else 0
    if cp < 0x80:
        n, tmpl = 1, "0xxxxxxx"
    elif cp < 0x800:
        n, tmpl = 2, "110xxxxx 10xxxxxx"
    elif cp < 0x10000:
        n, tmpl = 3, "1110xxxx 10xxxxxx 10xxxxxx"
    else:
        n, tmpl = 4, "11110xxx 10xxxxxx 10xxxxxx 10xxxxxx"
    raw = (ch or "").encode("utf-8", "replace")
    return {
        "codepoint": cp, "uplus": "U+%04X" % cp, "bytes": n,
        "template": tmpl,
        "hex": raw.hex(),
        "hex_spaced": " ".join(format(b, "02X") for b in raw),
        "bin": " ".join(format(b, "08b") for b in raw),
    }


def utf8_decode_bytes(data: bytes) -> List[Dict]:
    """手工逐序列解析 UTF-8：标出每字节是首字节还是续字节。

    非法序列标 invalid，不抛异常——这正是排查"乱码"时要看的东西。
    """
    out = []
    b = bytes(data)
    i = 0
    while i < len(b):
        x = b[i]
        if x < 0x80:
            n, cp, ok = 1, x, True
        elif x >> 5 == 0b110:
            n, cp, ok = 2, x & 0x1F, i + 1 < len(b)
        elif x >> 4 == 0b1110:
            n, cp, ok = 3, x & 0x0F, i + 2 < len(b)
        elif x >> 3 == 0b11110:
            n, cp, ok = 4, x & 0x07, i + 3 < len(b)
        else:
            out.append({"offset": i, "bytes": [x], "kind": "invalid",
                        "note": "非法的 UTF-8 首字节 0x%02X" % x})
            i += 1
            continue
        seq = b[i:i + n]
        if len(seq) < n:
            out.append({"offset": i, "bytes": list(seq), "kind": "truncated",
                        "note": _("序列被截断（需要 %d 字节，只有 %d）") % (n, len(seq))})
            i += len(seq)
            continue
        for k in range(1, n):
            if seq[k] >> 6 != 0b10:
                ok = False
                break
            cp = (cp << 6) | (seq[k] & 0x3F)
        if not ok:
            out.append({"offset": i, "bytes": list(seq), "kind": "invalid",
                        "note": _("续字节不符合 10xxxxxx 模板")})
            i += 1
            continue
        out.append({"offset": i, "bytes": list(seq), "kind": "valid",
                    "codepoint": cp, "uplus": "U+%04X" % cp,
                    "char": chr(cp) if cp <= 0x10FFFF else "",
                    "note": _("%d 字节序列") % n})
        i += n
    return out


BOMS = [
    (codecs.BOM_UTF8, "UTF-8", "EF BB BF"),
    (codecs.BOM_UTF32_LE, "UTF-32LE", "FF FE 00 00"),
    (codecs.BOM_UTF32_BE, "UTF-32BE", "00 00 FE FF"),
    (codecs.BOM_UTF16_LE, "UTF-16LE", "FF FE"),
    (codecs.BOM_UTF16_BE, "UTF-16BE", "FE FF"),
    (b"\x84\x31\x95\x33", "GB18030", "84 31 95 33"),
]


def detect_bom(data: bytes) -> Optional[Dict]:
    """识别字节串开头的 BOM（注意 UTF-32LE 要先于 UTF-16LE 判）。"""
    b = bytes(data)
    for sig, name, hexstr in BOMS:
        if b.startswith(sig):
            return {"encoding": name, "bom_hex": hexstr,
                    "length": len(sig),
                    "note": "UTF-32LE 与 UTF-16LE 前两字节相同，本函数按最长匹配判定"}
    return None


# ---------------------------------------------------------------- Base 系列

#: scheme → (编码器, 解码器, 标准出处, 膨胀率说明)
BASE_SCHEMES = {
    "base64": (base64.b64encode, base64.b64decode, "RFC 4648 §4", "4/3 ≈ +33%"),
    "base64url": (base64.urlsafe_b64encode, base64.urlsafe_b64decode,
                  "RFC 4648 §5", "4/3，把 +/ 换成 -_"),
    "base32": (base64.b32encode, base64.b32decode, "RFC 4648 §6", "8/5 = +60%"),
    "base16": (base64.b16encode, base64.b16decode, "RFC 4648 §8", "2/1 = +100%"),
    "base85": (base64.b85encode, base64.b85decode, "RFC 1924 / git 用此变体", "5/4 = +25%"),
    "ascii85": (base64.a85encode, base64.a85decode, "Adobe Ascii85（PDF/PS）", "5/4 = +25%"),
}


def base_encode(data: bytes, scheme: str = "base64") -> Dict:
    """字节 → Base 系列文本。"""
    if scheme not in BASE_SCHEMES:
        return {"error": _("未知方案 %r（支持 %s）") % (scheme, "/".join(BASE_SCHEMES))}
    enc, _dec, std, ratio = BASE_SCHEMES[scheme]
    try:
        out = enc(bytes(data))
    except Exception as exc:  # noqa: BLE001 - 纯展示，不因异常中断
        return {"error": "%s: %s" % (type(exc).__name__, exc)}
    text = out.decode("ascii", "replace") if isinstance(out, bytes) else str(out)
    return {"scheme": scheme, "text": text, "input_len": len(data),
            "output_len": len(text), "expansion": ratio,
            "padding": text.count("="), "standard": std}


def base_decode(text: str, scheme: str = "base64") -> Dict:
    """Base 系列文本 → 字节（失败返回 error，不抛异常）。"""
    if scheme not in BASE_SCHEMES:
        return {"error": _("未知方案 %r（支持 %s）") % (scheme, "/".join(BASE_SCHEMES))}
    _enc, dec, std, _ratio = BASE_SCHEMES[scheme]
    raw = str(text).strip().encode("ascii", "ignore")
    try:
        out = dec(raw)
    except Exception as exc:  # noqa: BLE001
        return {"error": "%s: %s" % (type(exc).__name__, exc)}
    return {"scheme": scheme, "data": out, "hex": out.hex(),
            "length": len(out), "standard": std,
            "utf8_guess": out.decode("utf-8", "replace")}


def render_base_compare(data: bytes) -> List[str]:
    """同一份字节在各 Base 方案下的结果与长度对比。"""
    lines = ["%-10s %-6s %-6s  %s" % (_("方案"), _("输入"), _("输出"), _("编码结果（截断 48 字符）"))]
    for scheme in ("base16", "base32", "base64", "base64url", "base85", "ascii85"):
        r = base_encode(data, scheme)
        if "error" in r:
            lines.append("%-10s  %s" % (scheme, r["error"]))
            continue
        lines.append("%-10s %-6d %-6d  %s" % (
            scheme, r["input_len"], r["output_len"], r["text"][:48]))
    return lines


# ---------------------------------------------------------------- 转义


def percent_encode(text: str, safe: str = "", encoding: str = "utf-8") -> str:
    """URI 百分号编码（RFC 3986）。safe 为不转义的字符集。"""
    return urllib.parse.quote(str(text), safe=safe, encoding=encoding)


def percent_decode(text: str, encoding: str = "utf-8") -> Dict:
    """百分号解码；解码失败按 replace 给出可读结果并标注。"""
    s = str(text)
    try:
        out = urllib.parse.unquote(s, encoding=encoding, errors="strict")
        ok = True
    except UnicodeDecodeError:
        out = urllib.parse.unquote(s, encoding=encoding, errors="replace")
        ok = False
    return {"text": out, "roundtrip_ok": ok,
            "note": "" if ok else _("字节序列不是合法 %s，已按 U+FFFD 替换") % encoding}


def html_escape(text: str, quote: bool = True) -> str:
    """HTML 实体转义（& < > 与可选引号）。"""
    return html.escape(str(text), quote=quote)


def html_unescape(text: str) -> str:
    """HTML 实体反转义（含命名实体如 &amp;）。"""
    return html.unescape(str(text))


def c_escape(text: str, encoding: str = "utf-8") -> str:
    """C 风格转义：控制字符用 \\n 等，非 ASCII 用 \\xNN / \\uXXXX。"""
    out = []
    for ch in str(text):
        cp = ord(ch)
        if cp in CONTROL_ESCAPES:
            out.append(CONTROL_ESCAPES[cp])
        elif 32 <= cp < 127:
            out.append(ch)
        elif cp < 0x100:
            out.append("\\x%02x" % cp)
        elif cp < 0x10000:
            out.append("\\u%04x" % cp)
        else:
            out.append("\\U%08x" % cp)
    return "".join(out)


def hex_escape(data: bytes, sep: str = " ", upper: bool = False) -> str:
    """字节 → \\xNN 形式的转义串。"""
    fmt = "%02X" if upper else "%02x"
    return sep.join("\\x" + fmt % b for b in bytes(data))


def json_escape(text: str, ensure_ascii: bool = True) -> str:
    """JSON 字符串转义（用 json 模块保证与规范一致）。"""
    import json
    return json.dumps(str(text), ensure_ascii=ensure_ascii)


def render_escape_compare(text: str, encoding: str = "utf-8") -> List[str]:
    """同一段文本在各种转义规则下的样子。"""
    raw = str(text).encode(encoding, "replace")
    lines = [
        _("原文        : %s") % text,
        _("字节(%s) : %s") % (encoding, raw.hex()),
        _("百分号编码  : %s") % percent_encode(text, encoding=encoding),
        "HTML 实体   : %s" % html_escape(text),
        _("C 转义      : %s") % c_escape(text, encoding),
        _("\\x 转义    : %s") % hex_escape(raw),
        _("JSON 转义   : %s") % json_escape(text),
        "Base64      : %s" % base_encode(raw, "base64").get("text", ""),
    ]
    return lines


# ---------------------------------------------------------------- 摩尔斯电码

#: ITU-R M.1677-1 国际摩尔斯电码
MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
    "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
    "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
    ".": ".-.-.-", ",": "--..--", "?": "..--..", "'": ".----.", "!": "-.-.--",
    "/": "-..-.", "(": "-.--.", ")": "-.--.-", "&": ".-...", ":": "---...",
    ";": "-.-.-.", "=": "-...-", "+": ".-.-.", "-": "-....-", "_": "..--.-",
    '"': ".-..-.", "$": "...-..-", "@": ".--.-.",
}
MORSE_REVERSE = {v: k for k, v in MORSE.items()}


def morse_encode(text: str, sep: str = " ", word_sep: str = " / ") -> Dict:
    """文本 → 摩尔斯电码。未知字符用 `#` 占位并统计。"""
    words = str(text).upper().split()
    parts = []
    unknown = 0
    for w in words:
        codes = []
        for ch in w:
            if ch in MORSE:
                codes.append(MORSE[ch])
            else:
                codes.append("#")
                unknown += 1
        parts.append(sep.join(codes))
    return {"morse": word_sep.join(parts), "unknown": unknown,
            "standard": "ITU-R M.1677-1"}


def morse_decode(code: str, word_sep: str = "/") -> Dict:
    """摩尔斯电码 → 文本。"""
    out = []
    unknown = 0
    for word in str(code).replace(word_sep, "|").split("|"):
        chars = []
        for token in word.split():
            if token in MORSE_REVERSE:
                chars.append(MORSE_REVERSE[token])
            else:
                chars.append("#")
                unknown += 1
        out.append("".join(chars))
    return {"text": " ".join(out), "unknown": unknown}


# ---------------------------------------------------------------- IDNA / 规范化


def punycode_encode(text: str) -> Dict:
    """域名 → Punycode（IDNA）。"""
    try:
        out = str(text).encode("idna").decode("ascii")
        return {"ascii": out, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"ascii": "", "error": "%s: %s" % (type(exc).__name__, exc)}


def punycode_decode(text: str) -> Dict:
    """Punycode → Unicode 域名。"""
    try:
        out = str(text).encode("ascii").decode("idna")
        return {"unicode": out, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"unicode": "", "error": "%s: %s" % (type(exc).__name__, exc)}


def normalize(text: str, form: str = "NFC") -> Dict:
    """Unicode 规范化；返回各形式对照与是否稳定。"""
    forms = ("NFC", "NFD", "NFKC", "NFKD")
    src = str(text)
    out = {"input": src, "length": len(src)}
    for f in forms:
        out[f] = unicodedata.normalize(f, src)
    out["is_nfc"] = src == unicodedata.normalize("NFC", src)
    out["codepoints"] = [ord(c) for c in src][:32]
    return out


# ---------------------------------------------------------------- 字符集互转

#: 常见编码 → (中文名, 标准出处)
CHARSETS = {
    "utf-8": ("UTF-8（Unicode 变长）", "RFC 3629 / GB/T 36377-2018"),
    "utf-16": ("UTF-16（带 BOM）", "ISO/IEC 10646 / RFC 2781"),
    "utf-32": ("UTF-32（定长 4 字节）", "ISO/IEC 10646"),
    "gb18030": ("GB 18030（中国强制）", "GB 18030-2022"),
    "gbk": ("GBK（GB 18030 子集）", "GB/T 2312 扩展"),
    "gb2312": ("GB 2312-1980（简体基础）", "GB 2312-1980"),
    "big5": ("Big5（繁体）", "台湾地区业界事实标准"),
    "shift_jis": ("Shift_JIS（日文）", "JIS X 0208"),
    "euc-kr": ("EUC-KR（韩文）", "KS X 1001"),
    "koi8-r": ("KOI8-R（俄文）", "RFC 1489"),
    "latin-1": ("ISO-8859-1 / Latin-1", "ISO/IEC 8859-1"),
    "cp1252": ("Windows-1252（西欧）", "微软事实标准"),
    "ascii": ("ASCII（7 位）", "GB/T 1988-1998 / ITU-T T.50"),
}


def encode_text(text: str, encoding: str = "utf-8") -> Dict:
    """文本 → 字节，并给出能否无损表示。"""
    src = str(text)
    try:
        codecs.lookup(encoding)
    except LookupError:
        return {"error": _("未知编码 %r") % encoding, "encoding": encoding}
    try:
        raw = src.encode(encoding)
        return {"encoding": encoding, "data": raw, "hex": raw.hex(),
                "bytes": len(raw), "lossless": True, "dropped": 0, "error": None}
    except UnicodeEncodeError as exc:
        raw = src.encode(encoding, "replace")
        return {"encoding": encoding, "data": raw, "hex": raw.hex(),
                "bytes": len(raw), "lossless": False,
                "dropped": sum(1 for c in src if _cannot_encode(c, encoding)),
                "error": _("位置 %d 的字符无法表示：%s") % (exc.start, exc.reason)}


def _cannot_encode(ch: str, encoding: str) -> bool:
    try:
        ch.encode(encoding)
        return False
    except (UnicodeEncodeError, LookupError):
        return True


def decode_bytes(data: bytes, encoding: str = "utf-8") -> Dict:
    """字节 → 文本，失败时给出 replace 结果与出错位置。"""
    try:
        codecs.lookup(encoding)
    except LookupError:
        return {"error": _("未知编码 %r") % encoding, "encoding": encoding}
    try:
        out = bytes(data).decode(encoding)
        return {"encoding": encoding, "text": out, "lossless": True, "error": None}
    except UnicodeDecodeError as exc:
        out = bytes(data).decode(encoding, "replace")
        return {"encoding": encoding, "text": out, "lossless": False,
                "error": _("位置 %d 起始的字节 %r 非法：%s") % (
                    exc.start, bytes(data)[exc.start:exc.end], exc.reason)}


def convert(text: str, src: str = "utf-8", dst: str = "gb18030") -> Dict:
    """字符集互转：源字节 → Unicode（中间层）→ 目标字节。

    注意入参 `text` 是**字节序列的十六进制或原始字节**时才有意义；这里按
    "src 编码读入 → dst 编码写出"处理，任何一步有损都会在结果里标出。
    """
    raw = text if isinstance(text, (bytes, bytearray)) else str(text).encode("utf-8", "replace")
    mid = decode_bytes(bytes(raw), src)
    if mid.get("error") and not mid.get("lossless"):
        return {"src": src, "dst": dst, "text": "", "lossless": False,
                "error": _("源编码解码失败：") + mid["error"]}
    uni = mid.get("text", "")
    out = encode_text(uni, dst)
    if "data" not in out:
        return {"src": src, "dst": dst, "text": "", "lossless": False,
                "error": out.get("error", _("编码失败"))}
    return {"src": src, "dst": dst,
            "unicode": uni,
            "unicode_len": len(uni),
            "text": out["data"].decode(dst, "replace"),
            "bytes": out["bytes"], "hex": out["hex"],
            "lossless": bool(mid.get("lossless")) and bool(out.get("lossless")),
            "error": out.get("error")}


def charset_matrix(text: str, encodings: Optional[List[str]] = None) -> List[Dict]:
    """同一段文本在各编码下的字节数与是否可无损表示（乱码排查表）。"""
    src = str(text)
    encs = encodings or ["ascii", "utf-8", "utf-16", "utf-32", "gb18030",
                         "gbk", "gb2312", "big5", "shift_jis", "euc-kr",
                         "koi8-r", "latin-1", "cp1252"]
    rows = []
    for enc in encs:
        r = encode_text(src, enc)
        if "error" in r and r.get("error") and "data" not in r:
            rows.append({"encoding": enc, "name": CHARSETS.get(enc, (enc, ""))[0],
                         "bytes": None, "lossless": False, "note": r["error"]})
            continue
        rows.append({
            "encoding": enc, "name": CHARSETS.get(enc, (enc, ""))[0],
            "bytes": r.get("bytes"), "hex": r.get("hex", ""),
            "lossless": r.get("lossless", False),
            "dropped": r.get("dropped", 0), "note": r.get("error") or "",
        })
    return rows


def render_charset_matrix(text: str) -> List[str]:
    """把字符集对照渲染成表格文本。"""
    lines = [_("输入：%s（%d 个字符）") % (text, len(text)),
             "%-12s %-8s %-8s %s" % (_("编码"), _("字节数"), _("无损"), _("十六进制（截断 30）"))]
    for row in charset_matrix(text):
        lines.append("%-12s %-8s %-8s %s" % (
            row["encoding"],
            "-" if row["bytes"] is None else row["bytes"],
            "是" if row["lossless"] else "否",
            row.get("hex", "")[:30]))
    return lines


def render_mojibake(data: bytes) -> List[str]:
    """给一段"来路不明"的字节：逐个编码尝试解码，看哪个读得通。

    这是排查"乱码"的第一步——每个候选编码都试一遍，看得懂的那个就是答案。
    """
    lines = [_("字节：%s（%d 字节）") % (data.hex(), len(data))]
    for enc, (name, _std) in CHARSETS.items():
        r = decode_bytes(data, enc)
        txt = r.get("text", "")
        flag = "✓" if r.get("lossless") else "✗"
        lines.append("  %s %-10s %-22s %s" % (
            flag, enc, name, txt[:40].replace("\n", "\\n")))
    return lines
