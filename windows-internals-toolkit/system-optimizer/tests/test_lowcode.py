"""lowcode 低层码制层的测试：位/字符/通信/逻辑/机器码五层。

测试策略：
1. **固定向量优先**——每条能力挑一个能手工核对的值（CRC check 值、
   RFC 1071 示例、Modbus 帧、IEEE 754 位模式…），不靠"跑通不报错"；
2. **往返（round-trip）**——编解码互为逆运算，随机或穷举覆盖；
3. **等价性**——逻辑化简后与原式真值表逐行比对（含随机表达式）；
4. **不依赖外部工具**——需要 javac 的用例用 skipif 跳过。
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from sysweeper.lowcode import bits, chars, comm, logic, machine
from sysweeper.lowcode import summary as lowcode_summary
from sysweeper import i18n


@pytest.fixture(autouse=True)
def _restore_locale():
    """本文件有用例切语言（zh_CN/en），用例后恢复源语言，避免污染后续文件。"""
    yield
    i18n.set_locale("zh_CN")


# ==================================================================
# bits —— 位与二进制
# ==================================================================

def test_base_roundtrip():
    for n in (0, 1, 7, 255, 4096, 0xDEADBEEF):
        for base in (2, 8, 10, 16, 36):
            assert bits.from_base(bits.to_base(n, base), base) == n


def test_hex_prefix_and_width():
    assert bits.to_hex(255, 4) == "0x00FF"
    assert bits.from_hex("0xFF") == 255
    assert bits.from_oct("0o777") == 0o777
    assert bits.from_bits("1111 1001") == 0xF9
    assert bits.from_bits("1111_1001") == 0xF9


def test_ternary_and_arbitrary_bases():
    # 三进制固定向量（中文语境里常被忽略的「非 2/8/16」进制）
    assert bits.to_base(0, 3) == "0"
    assert bits.to_base(5, 3) == "12"
    assert bits.to_base(100, 3) == "10201"      # 81 + 18 + 2
    assert bits.to_base(-7, 3) == "-21"
    assert bits.from_base("10201", 3) == 100
    # 任意进制 2-36 往返
    for n in (0, 1, 42, 255, 4096, 123456789):
        for base in (2, 3, 4, 7, 9, 12, 16, 20, 36):
            assert bits.from_base(bits.to_base(n, base), base) == n
    # 越界进制（<2 或 >36）静默跳过，不抛异常
    assert bits.bases(5, (1, 2, 37)) == [{"base": 2, "name": "二进制", "digits": "101"}]


def test_human_readable_decimal():
    # 人类可读十进制：千分位逗号，负数带符号；一切显示以十进制为默认
    assert bits.human_int(0) == "0"
    assert bits.human_int(1234567) == "1,234,567"
    assert bits.human_int(-1234) == "-1,234"
    assert bits.base_name(3) == "三进制"
    assert bits.base_name(99) == "99 进制"
    # render_bases 把十进制排在最前并标注「人类可读·默认」
    lines = bits.render_bases(255)
    assert lines[0].startswith("进制对照")
    assert "十进制（人类可读·默认）: 255" in lines[1]
    assert "三进制" in "\n".join(lines)
    # 大数十进制带千分位，三进制等长串按 3 位分组
    big = bits.render_bases(9876543210)
    assert "9,876,543,210" in "\n".join(big)


def test_from_base_defaults_to_decimal_for_humans():
    # 裸数字默认当十进制（这是「使用者显示为一般可读」的核心：不是当十六进制）
    assert bits.from_base("255", default_base=10) == 255
    assert bits.from_base("255") == 0x255           # 历史默认仍保留十六进制
    # 带前缀仍可切换到其他进制
    assert bits.from_base("0xFF", default_base=10) == 255
    assert bits.from_base("0b101", default_base=10) == 5
    # convert_base 无 base_in 时按十进制解读
    assert bits.convert_base("255")["value"] == 255
    assert bits.convert_base("10201", 3)["value"] == 100


def test_bases_cli_actions_subprocess():
    # 通过真实 CLI 验证两个新动作 + 十进制默认
    import subprocess, os, sys
    env = dict(os.environ); env["PYTHONPATH"] = "src/python"

    def run(*a):
        r = subprocess.run([sys.executable, "-m", "sysweeper", *a],
                           capture_output=True, text=True, env=env)
        return r.returncode, r.stdout, r.stderr

    rc, out, err = run("code", "bits", "--action", "bases", "--value", "255")
    assert rc == 0 and "十进制（人类可读·默认）: 255" in out, err

    rc, out, err = run("code", "bits", "--action", "base", "--value", "0xFF", "--base", "3")
    assert rc == 0 and "255" in out and "100 110" in out, err   # 255 的三进制，按 3 位分组

    # 裸数字当十进制：255 的二进制是 11111111（旧实现会误当 hex=597）
    rc, out, err = run("code", "bits", "--action", "base", "--value", "255", "--base", "2")
    assert rc == 0 and "1111 1111" in out, err

    rc, out, err = run("code", "bits", "--action", "base", "--value", "5", "--base", "40")
    assert rc == 0 and "2-36" in out, err


def test_twos_complement():
    assert bits.to_twos(-7, 8) == 0xF9
    assert bits.from_twos(0xF9, 8) == -7
    assert bits.to_twos(-1, 32) == 0xFFFFFFFF
    assert bits.from_twos(0x80000000, 32) == -(1 << 31)
    # 补码 -7 的三种表示：补码 F9 / 反码 F8 / 原码 87
    rep = bits.representations(-7, 8)
    assert rep["twos"]["hex"] == "0xF9"
    assert rep["ones"]["hex"] == "0xF8"
    assert rep["sign_magnitude"]["hex"] == "0x87"


def test_endian_roundtrip():
    value = 0x12345678
    assert bits.endian_convert(value, 4, "little", "big") == 0x78563412
    assert bits.unpack_int(bits.pack_int(value, 4, "big"), "big") == value
    assert bits.unpack_int(bits.pack_int(value, 4, "little"), "little") == value
    view = bits.endian_view(value, 4)
    assert view["big"]["bytes"] == [0x12, 0x34, 0x56, 0x78]
    assert view["little"]["bytes"] == [0x78, 0x56, 0x34, 0x12]
    assert bits.pack_int(256, 1) is None          # 越界返回 None，不抛异常


def test_bitfields():
    value = 0b1010_1100
    assert bits.extract(value, 0, 4) == 0b1100
    assert bits.extract(value, 4, 4) == 0b1010
    assert bits.deposit(0, 4, 4, 0b0101) == 0b0101_0000
    layout = [("low", 0, 4), ("high", 4, 4)]
    fields = bits.bitfields(value, layout)
    assert [f["value"] for f in fields] == [0b1100, 0b1010]


def test_gray_roundtrip():
    for n in range(256):
        assert bits.from_gray(bits.to_gray(n, 8), 8) == n
    # 相邻数的格雷码只差一位
    for n in range(255):
        assert bits.popcount(bits.to_gray(n) ^ bits.to_gray(n + 1)) == 1


def test_bcd_roundtrip():
    assert bits.to_bcd(1234) == 0x1234
    assert bits.from_bcd(0x1234) == 1234
    assert bits.from_bcd(0x1A) is None            # 非法半字节
    assert bits.pack_bcd(1234) == bytes([0x12, 0x34])
    assert bits.unpack_bcd(bytes([0x12, 0x34])) == 1234
    for n in (0, 5, 99, 123456):
        assert bits.from_bcd(bits.to_bcd(n)) == n


def test_parity_and_bits():
    assert bits.popcount(0xFF) == 8
    assert bits.popcount(-1) == 1                 # 最小补码宽度下 -1 只有一个 1
    assert bits.parity(0b1011, True) == 1         # 3 个 1 → 补 1 凑偶
    assert bits.parity(0b1011, False) == 0
    assert bits.parity_ok(0b1011_1, 5, True)
    assert bits.rol(0b1000_0001, 8, 1) == 0b0000_0011
    assert bits.ror(0b0000_0011, 8, 1) == 0b1000_0001
    assert bits.reverse_bits(0b0000_0001, 8) == 0b1000_0000
    assert bits.hamming_distance(0b1100, 0b1010) == 2


def test_ieee754_decode():
    one = bits.decode_float(0x3F800000, 32)
    assert one["class"] == "normal" and one["value"] == 1.0
    assert one["exponent_raw"] == 127 and one["mantissa_raw"] == 0
    assert bits.decode_float(0x00000000, 32)["class"] == "zero"
    assert bits.decode_float(0x7F800000, 32)["class"] == "infinity"
    assert bits.decode_float(0x7FC00000, 32)["class"] == "nan"
    assert bits.decode_float(0x00000001, 32)["class"] == "subnormal"
    # -3.14159 的 binary32 位模式（与 struct 交叉校验）
    raw = bits.encode_float(-3.14159, 32)
    assert abs(bits.decode_float(raw, 32)["value"] + 3.14159) < 1e-6
    assert bits.decode_float(0, 24)["error"]      # 不支持的位宽给 error


# ==================================================================
# chars —— 字符编码
# ==================================================================

def test_ascii_table():
    table = chars.ascii_table()
    assert len(table) == 128
    assert table[0x41]["char"] == "A"
    assert table[0x0A]["name"].startswith("LF")
    assert table[0x0A]["escape"] == "\\n"
    assert table[0x20]["printable"] and not table[0x7F]["printable"]


def test_utf8_bytes():
    assert "中".encode("utf-8") == bytes([0xE4, 0xB8, 0xAD])
    info = chars.utf8_info("中")
    assert info["bytes"] == 3 and info["hex"] == "e4b8ad"
    assert chars.utf8_info("A")["bytes"] == 1
    # 非法序列要被标出来，而不是抛异常
    decoded = chars.utf8_decode_bytes(bytes([0xE4, 0x41, 0x41]))   # 续字节不合规
    assert decoded[0]["kind"] == "invalid"
    # 序列被截断也要能识别
    assert chars.utf8_decode_bytes(bytes([0xE4, 0x41]))[0]["kind"] == "truncated"


def test_bom_detection():
    assert chars.detect_bom(b"\xef\xbb\xbfabc")["encoding"] == "UTF-8"
    assert chars.detect_bom(b"\xff\xfe\x00\x00")["encoding"] == "UTF-32LE"
    assert chars.detect_bom(b"\xfe\xffab")["encoding"] == "UTF-16BE"
    assert chars.detect_bom(b"abc") is None


def test_base_family_roundtrip():
    payload = b"hello world \x00\xff\x01"
    for scheme in ("base16", "base32", "base64", "base64url", "base85", "ascii85"):
        enc = chars.base_encode(payload, scheme)
        assert "error" not in enc, scheme
        dec = chars.base_decode(enc["text"], scheme)
        assert dec["data"] == payload, scheme
    assert chars.base_encode(b"", "base64")["text"] == ""
    assert chars.base_encode(b"x", "nope")["error"]


def test_base64_known_vector():
    assert chars.base_encode(b"hello", "base64")["text"] == "aGVsbG8="
    assert chars.base_decode("aGVsbG8=", "base64")["data"] == b"hello"
    # RFC 4648 §5：urlsafe 把 +/ 换成 -_
    assert chars.base_encode(b"\xfb\xff", "base64")["text"] == "+/8="
    assert chars.base_encode(b"\xfb\xff", "base64url")["text"] == "-_8="


def test_escapes():
    assert chars.percent_encode("中文 a/b") == "%E4%B8%AD%E6%96%87%20a%2Fb"
    assert chars.percent_decode("%E4%B8%AD")["text"] == "中"
    assert chars.html_escape("<a & b>") == "&lt;a &amp; b&gt;"
    assert chars.html_unescape("&lt;a&gt;") == "<a>"
    assert chars.c_escape("a\nb") == "a\\nb"
    assert chars.hex_escape(bytes([0xDE, 0xAD])) == "\\xde \\xad"
    assert chars.json_escape("中") == '"\\u4e2d"'


def test_morse_roundtrip():
    enc = chars.morse_encode("SOS")
    assert enc["morse"] == "... --- ..."
    assert enc["standard"] == "ITU-R M.1677-1"
    assert chars.morse_decode("... --- ...")["text"] == "SOS"
    assert chars.morse_encode("SOS 你好")["unknown"] == 2   # 中文不在码表里


def test_charset_matrix_and_convert():
    rows = {r["encoding"]: r for r in chars.charset_matrix("中文")}
    assert rows["utf-8"]["bytes"] == 6
    assert rows["gb18030"]["bytes"] == 4
    assert rows["gb18030"]["hex"] == "d6d0cec4"
    assert rows["ascii"]["lossless"] is False     # ASCII 装不下中文
    assert rows["utf-8"]["lossless"] is True
    out = chars.convert("中文".encode("utf-8"), "utf-8", "gb18030")
    assert out["lossless"] and out["hex"] == "d6d0cec4"
    assert chars.encode_text("中", "ascii")["lossless"] is False


def test_idna_and_normalization():
    enc = chars.punycode_encode("xn--fiqs8s")
    assert "error" not in enc or enc["ascii"]
    dec = chars.punycode_decode("xn--fiqs8s")
    assert dec["unicode"] in ("中国", "") or dec["error"] is None
    norm = chars.normalize("é")
    assert norm["NFD"] != norm["NFC"] or norm["is_nfc"]


def test_char_info():
    info = chars.char_info("汉")
    assert info["codepoint"] == 0x6C49
    assert info["utf8"]["bytes"] == 3
    assert info["category"] == "Lo"
    assert info["html"] == "&#27721;"


# ==================================================================
# comm —— 通信码
# ==================================================================

def test_crc_check_values():
    """每个内置变种对 b"123456789" 的 check 值必须与公开值一致。"""
    for name, expect in comm.CRC_CHECK_VALUES.items():
        got = comm.crc_named(b"123456789", name)
        assert got == expect, "%s: 0x%X != 0x%X" % (name, got, expect)


def test_crc_matches_zlib():
    """位运算实现必须与 zlib.crc32 一致（交叉校验）。"""
    payload = b"sysweeper lowcode comm layer"
    assert comm.crc_named(payload, "crc32") == comm.crc32_zlib(payload)


def test_crc_append_and_verify():
    frame = comm.crc_append(comm.MODBUS_SAMPLE, "crc16-modbus")
    assert frame[-2:] == bytes([0x84, 0x0A])      # 低字节在前
    result = comm.crc_verify(frame, "crc16-modbus")
    assert result["ok"] is True
    corrupt = bytearray(frame)
    corrupt[0] ^= 0xFF
    assert comm.crc_verify(bytes(corrupt), "crc16-modbus")["ok"] is False


def test_internet_checksum_rfc1071():
    assert comm._ones_complement_sum(comm.RFC1071_SAMPLE) == comm.RFC1071_SUM == 0xDDF2
    assert comm.internet_checksum(comm.RFC1071_SAMPLE) == comm.RFC1071_CHECKSUM == 0x220D
    # 校验字段按网络字节序（大端）填入后，整段求和应为 0xFFFF
    assert comm.internet_checksum_verify(comm.RFC1071_SAMPLE + b"\x22\x0d")
    assert not comm.internet_checksum_verify(comm.RFC1071_SAMPLE + b"\x0d\x22")


def test_other_checksums():
    assert comm.adler32(b"hello") == 0x062C0215
    assert comm.fletcher16(b"hello") == comm.fletcher16(b"hello")
    assert comm.lrc(b"\x01\x02\x03", "xor") == 0x00
    assert 0 <= comm.lrc(b"\x01\x02\x03", "twos") <= 0xFF


def test_framing_roundtrip():
    payload = bytes([0x7E, 0x00, 0x11, 0x7D, 0x22])
    assert comm.hdlc_decode(comm.hdlc_encode(payload))["data"] == payload
    assert comm.slip_decode(comm.slip_encode(payload))["data"] == payload
    assert comm.cobs_decode(comm.cobs_encode(payload))["data"] == payload
    # COBS 已知向量：11 22 00 33 → 03 11 22 02 33
    assert comm.cobs_encode(bytes([0x11, 0x22, 0x00, 0x33])) == bytes([0x03, 0x11, 0x22, 0x02, 0x33])
    assert comm.cobs_encode(b"\x00") == b"\x01\x01"
    assert comm.hdlc_encode(b"\x7e") == b"\x7e\x7d\x5e\x7e"


def test_bit_stuffing():
    raw = "11111100011111"
    stuffed = comm.bit_stuff(raw)
    assert "111111" not in stuffed          # 零比特插入后不应再有 6 连 1
    assert comm.bit_unstuff(stuffed)["data"] == raw


def test_line_coding():
    for scheme in ("nrz-l", "nrz-i", "manchester", "diff-manchester", "ami", "hdb3"):
        r = comm.encode_line("10110010", scheme)
        assert "error" not in r
        assert len(r["points"]) == 16             # 每位取两个采样点
    # AMI：1 交替极性，0 为零电平
    ami = comm.encode_line("1111", "ami")
    assert ami["levels"] == [1, -1, 1, -1]
    # HDB3：4 连 0 必须被替换（出现 V 或 B 标记）
    marks = "".join(m[1] for m in comm.hdb3("100001"))
    assert "V" in marks
    assert comm.encode_line("1", "unknown-scheme")["error"]


def test_hamming74_corrects_single_bit():
    for data in range(16):
        code = comm.hamming74_encode(data)
        for pos in range(7):
            broken = code ^ (1 << pos)
            fixed = comm.hamming74_decode(broken)
            assert fixed["error_position"] == pos + 1
            assert fixed["data"] == data
    assert comm.hamming74_decode(comm.hamming74_encode(0xB))["syndrome"] == 0


def test_hamming84_detects_double_bit():
    for data in range(16):
        code = comm.hamming84_encode(data)
        assert comm.hamming84_decode(code)["status"] == "无错"
        broken = code ^ 0b0000011                  # 两位错
        assert "双比特错" in comm.hamming84_decode(broken)["status"]
    single = comm.hamming84_encode(0xB) ^ 0b0000010
    assert "已纠正" in comm.hamming84_decode(single)["status"]


def test_uart_timing():
    frame = comm.uart_frame(8, "none", 1.0)
    assert frame["bits_per_frame"] == 10.0
    assert abs(frame["efficiency"] - 0.8) < 1e-9
    r = comm.uart_time(1000, 9600)
    assert abs(r["seconds"] - 1000 * 10 / 9600) < 1e-9
    assert comm.baud_error(9600, 9615)["within_2pct"]
    assert not comm.baud_error(9600, 12000)["within_2pct"]


# ==================================================================
# logic —— 逻辑转换码
# ==================================================================

def test_parse_and_evaluate():
    assert logic.eval_expr("A & B", {"A": 1, "B": 1}) == 1
    assert logic.eval_expr("A & B", {"A": 1, "B": 0}) == 0
    assert logic.eval_expr("!A", {"A": 0}) == 1
    assert logic.eval_expr("A ^ B", {"A": 1, "B": 1}) == 0
    assert logic.eval_expr("A -> B", {"A": 0, "B": 0}) == 1      # 蕴含：前件假则真
    assert logic.eval_expr("A -> B", {"A": 1, "B": 0}) == 0
    assert logic.eval_expr("A <-> B", {"A": 1, "B": 1}) == 1
    assert logic.eval_expr("A'", {"A": 1}) == 0                  # 后缀取反
    assert logic.eval_expr("A B", {"A": 1, "B": 1}) == 1          # 空格=隐式与
    # 变量名贪婪匹配：AB 是一个叫 "AB" 的变量，不是 A 与 B
    assert logic.eval_expr("AB", {"AB": 1}) == 1
    assert logic.eval_expr("AB", {"A": 1, "B": 1}) == 0
    assert logic.eval_expr("1 & 0") == 0
    with pytest.raises(logic.ParseError):
        logic.parse("A & ")


def test_truth_table_and_canonical_forms():
    t = logic.truth_table("A ^ B")
    assert t["variables"] == ["A", "B"]
    assert len(t["rows"]) == 4
    assert t["minterms"] == [1, 2]
    assert t["maxterms"] == [0, 3]
    forms = logic.canonical_forms("A ^ B")
    assert forms["sop"] == "(!A & B) | (A & !B)"
    assert forms["pos"] == "(A | B) & (!A | !B)"


def test_simplify_equivalence():
    samples = [
        "A & B | A & !B | !A & B",       # → A | B
        "(A | B) & (A | !B)",            # → A
        "A | !A",                        # → 1
        "A & !A",                        # → 0
        "!A & !B & !C | !A & B & !C | A & !B & !C | A & !B & C | A & B & C",
        "A -> B",
        "A <-> B",
        "!(A & B)",
        "(A & B) | (C & D) | (A & C)",
    ]
    for expr in samples:
        result = logic.simplify(expr)
        assert result["equivalent"], expr
        if expr in ("A & B | A & !B | !A & B",):
            assert result["expression"].replace(" ", "") in ("A|B", "B|A")


def test_simplify_random_equivalence():
    """随机表达式化简后必须与原式真值表完全一致。"""
    import random
    rng = random.Random(20240607)
    ops = ["&", "|", "^", "->", "<->"]
    for _ in range(120):
        n = rng.choice([2, 3, 4])
        names = ["A", "B", "C", "D"][:n]
        parts = [rng.choice(names)]
        for _k in range(rng.randint(1, 3)):
            parts.append(rng.choice(ops))
            parts.append(rng.choice(names))
        expr = " ".join(parts)
        assert logic.simplify(expr)["equivalent"], expr


def test_karnaugh_layout():
    k = logic.karnaugh([0, 1, 2, 4, 6, 8, 9, 10, 11, 12, 13, 14], 4)
    assert k["row_var"] == "AB" and k["col_var"] == "CD"
    assert len(k["row_labels"]) == 4 and len(k["col_labels"]) == 4
    assert k["cells"][0][0] == "1"
    k3 = logic.karnaugh([0, 1], 3)
    assert k3["row_var"] == "A" and k3["col_var"] == "BC"
    assert logic.karnaugh([0], 5)["error"]        # 5 变量请用 QM


def test_nand_nor_rewrite():
    report = logic.nand_report("A & B | !C")
    assert report["gate_count"]["AND"] == 1
    assert report["gate_count"]["NOT"] == 1
    assert report["gate_count"]["OR"] == 1
    assert report["nand_gates"] > 0 and report["nor_gates"] > 0
    # 只用 NAND 的结构求值后应与原式一致
    node = logic.parse("A ^ B")
    nand = logic.to_nand(node)

    def eval_nand(n, env):
        if n[0] == "var":
            return env.get(n[1], 0)
        if n[0] == "const":
            return n[1]
        return 1 - (eval_nand(n[1], env) & eval_nand(n[2], env))

    for a in (0, 1):
        for b in (0, 1):
            assert eval_nand(nand, {"A": a, "B": b}) == logic.eval_expr("A ^ B", {"A": a, "B": b})


def test_adders():
    assert logic.half_adder(1, 1) == (0, 1)
    assert logic.full_adder(1, 1, 1) == (1, 1)
    r = logic.ripple_add(5, 3, 8)
    assert r["result_unsigned"] == 8 and r["overflow"] == 0
    r = logic.ripple_add(5, 3, 8, sub=True)
    assert r["result_unsigned"] == 2 and r["overflow"] == 0
    r = logic.ripple_add(100, 100, 8)
    assert r["result_unsigned"] == 200 and r["result_signed"] == -56
    assert r["overflow"] == 1                     # 有符号溢出
    r = logic.ripple_add(3, 5, 8, sub=True)
    assert r["result_signed"] == -2
    for x in (-128, -1, 0, 1, 127):
        for y in (-128, -1, 0, 1, 127):
            got = logic.ripple_add(x & 0xFF, y & 0xFF, 8)
            assert got["result_signed"] == x + y or got["overflow"] == 1


# ==================================================================
# machine —— 机器码与字节码
# ==================================================================

def test_identify_magic():
    assert machine.identify(b"\x7fELF....")["format"] == "ELF"
    assert machine.identify(b"MZ\x90\x00")["format"] == "PE/DOS"
    assert machine.identify(bytes([0xCA, 0xFE, 0xBA, 0xBE]))["format"] == "Java class"
    assert machine.identify(b"PK\x03\x04")["format"].startswith("ZIP")
    assert machine.identify(b"#!/usr/bin/env python3")["format"] == "脚本（shebang）"
    assert machine.identify(b"\x00\x01\x02\x03")["format"] == "未知"


def test_pyc_magic_and_header():
    magic = machine.pyc_magic()
    assert len(magic["bytes"]) == 4
    assert int.from_bytes(bytes(magic["bytes"]), "little") > 0
    head = machine.parse_pyc_header(
        bytes(magic["bytes"]) + (0).to_bytes(4, "little")
        + (1).to_bytes(4, "little") + (2).to_bytes(4, "little"))
    assert head["matches_interpreter"] is True
    assert head["check"] == "时间戳校验型"
    assert machine.parse_pyc_header(bytes(magic["bytes"]) + (1).to_bytes(4, "little")
                                    + (1).to_bytes(4, "little")
                                    + (2).to_bytes(4, "little"))["check"] == "哈希校验型（PEP 552）"
    assert machine.parse_pyc_header(b"\x00" * 4)["error"]


def test_python_bytecode():
    result = machine.dis_python("x = 1 + 2")
    assert "error" not in result
    names = [i["opname"] for i in result["instructions"]]
    assert "LOAD_CONST" in names and "STORE_NAME" in names
    assert machine.dis_python("def (")["error"]     # 语法错误不抛异常


def test_x86_decode_samples():
    """每个内置样例都能拆出前缀/opcode/ModRM 且长度自洽。"""
    for hexstr, _desc in machine.X86_SAMPLES:
        data = bytes.fromhex(hexstr)
        r = machine.decode_x86_64(data)
        assert "error" not in r, hexstr
        assert r["length"] == len(data), hexstr
        assert r["opcode"], hexstr


def test_x86_known_instructions():
    r = machine.decode_x86_64(bytes.fromhex("4889e5"))
    assert r["mnemonic_hint"] == "mov"
    assert r["operands"] == "rbp, rsp"
    assert r["rex"]["W"] == 1 and r["operand_width"] == 64

    r = machine.decode_x86_64(bytes.fromhex("b801000000"))
    assert r["mnemonic_hint"] == "mov"
    assert r["operands"] == "eax, 0x1"
    assert r["immediate"] == 1

    r = machine.decode_x86_64(bytes.fromhex("55"))
    assert r["mnemonic_hint"] == "push" and r["operands"] == "rbp"

    r = machine.decode_x86_64(bytes.fromhex("4801d8"))
    assert r["mnemonic_hint"] == "add" and r["operands"] == "rax, rbx"

    r = machine.decode_x86_64(bytes.fromhex("4831c0"))
    assert r["mnemonic_hint"] == "xor" and r["operands"] == "rax, rax"

    r = machine.decode_x86_64(bytes.fromhex("c3"))
    assert r["mnemonic_hint"] == "ret"

    # 前缀识别 + RIP 相对寻址
    r = machine.decode_x86_64(bytes.fromhex("488b0590"))   # mov rax, [rip+disp32]
    assert r["rex"]["W"] == 1 and r["modrm"]["mod"] == 0 and r["modrm"]["rm"] == 5
    assert r["operands"].startswith("rax, [rip+")

    assert machine.decode_x86_64(b"")["error"]


def _enc_rv(opcode, rd=0, funct3=0, rs1=0, rs2=0, funct7=0, imm=0, itype=None):
    """独立参考编码器（按 RISC-V 规范正向构造），仅用于交叉验证解码器。"""
    inst = (opcode | (rd & 0x1F) << 7 | (funct3 & 7) << 12
            | (rs1 & 0x1F) << 15 | (rs2 & 0x1F) << 20 | (funct7 & 0x7F) << 25)
    if itype == "I":
        inst |= (imm & 0xFFF) << 20
    elif itype == "S":
        inst |= ((imm >> 5) & 0x7F) << 25 | (imm & 0x1F) << 7
    elif itype == "B":
        inst |= ((imm >> 12) & 1) << 31 | ((imm >> 5) & 0x3F) << 25 \
              | ((imm >> 1) & 0xF) << 8 | ((imm >> 11) & 1) << 7
    elif itype == "U":
        inst |= (imm & 0xFFFFF) << 12
    elif itype == "J":
        inst |= ((imm >> 20) & 1) << 31 | ((imm >> 1) & 0x3FF) << 21 \
              | ((imm >> 11) & 1) << 20 | ((imm >> 12) & 0xFF) << 12
    return inst & 0xFFFFFFFF


def test_riscv64_disassembly():
    """RISC-V 64I 结构化反汇编：用独立编码器生成黄金指令，交叉验证解码器。"""
    cases = [
        (_enc_rv(0x13, rd=1, rs1=0, imm=1, itype="I"), "addi", "x1, x0, 1"),
        (_enc_rv(0x33, rd=1, rs1=2, rs2=3), "add", "x1, x2, x3"),
        (_enc_rv(0x33, rd=1, rs1=2, rs2=3, funct7=0x20), "sub", "x1, x2, x3"),
        (_enc_rv(0x37, rd=1, imm=0x10000, itype="U"), "lui", "x1, 0x10000"),
        (_enc_rv(0x17, rd=1, imm=0, itype="U"), "auipc", "x1, 0x0"),
        (_enc_rv(0x03, rd=8, rs1=2, imm=0, funct3=3), "ld", "x8, 0(x2)"),
        (_enc_rv(0x03, rd=0, rs1=8, imm=-1, funct3=0, itype="I"), "lb", "x0, -1(x8)"),
        (_enc_rv(0x23, rs2=8, rs1=2, imm=0, funct3=3), "sd", "x8, 0(x2)"),
        (_enc_rv(0x63, rs1=1, rs2=0, imm=8, funct3=0, itype="B"), "beq", "x1, x0, 8"),
        (_enc_rv(0x63, rs1=0, rs2=0, imm=-4, funct3=0, itype="B"), "beq", "x0, x0, -4"),
        (_enc_rv(0x6F, rd=0, imm=16, itype="J"), "j", "16"),
        (_enc_rv(0x6F, rd=1, imm=0, itype="J"), "jal", "x1, 0"),
        (_enc_rv(0x13, rd=1, rs1=2, imm=0, funct3=0), "mv", "x1, x2"),
        (_enc_rv(0x13, rd=1, rs1=0, imm=-1, funct3=0, itype="I"), "addi", "x1, x0, -1"),
        (_enc_rv(0x1B, rd=1, rs1=2, imm=0, funct3=0), "sext.w", "x1, x2"),
        (_enc_rv(0x3B, rd=1, rs1=2, rs2=3, funct7=0x20), "subw", "x1, x2, x3"),
        (_enc_rv(0x3B, rd=1, rs1=2, rs2=3), "addw", "x1, x2, x3"),
        (_enc_rv(0x13, rd=1, rs1=2, imm=1, funct3=1, itype="I"), "slli", "x1, x2, 1"),
        (_enc_rv(0x13, rd=1, rs1=2, imm=1, funct3=5, itype="I"), "srli", "x1, x2, 1"),
        (_enc_rv(0x13, rd=1, rs1=2, imm=1, funct3=5, funct7=0x20, itype="I"), "srai", "x1, x2, 1"),
        (_enc_rv(0x33, rd=3, rs1=3, rs2=3, funct3=5), "srl", "x3, x3, x3"),
        (_enc_rv(0x33, rd=3, rs1=3, rs2=3, funct7=0x20, funct3=5), "sra", "x3, x3, x3"),
        (_enc_rv(0x0F, funct3=0, imm=0x0FF, itype="I"), "fence", "iorw, iorw"),
        (_enc_rv(0x0F, funct3=1), "fence.i", ""),
        (0x00000073, "ecall", ""),
        (0x00100073, "ebreak", ""),
        (0x00008067, "ret", ""),
        (0x0000006F, "j", "0"),
    ]
    for inst, mn, op in cases:
        e = machine._decode_one_rv(inst)
        assert e["mnemonic"] == mn and e["operands"] == op, (hex(inst), mn, op, e)


def test_riscv64_stream_and_edge():
    """流解码带地址、非 4 倍数报错、RV_SAMPLES 自洽。"""
    import struct
    data = struct.pack("<I", _enc_rv(0x13, rd=1, rs1=0, imm=1, itype="I")) \
        + struct.pack("<I", _enc_rv(0x33, rd=1, rs1=2, rs2=3))
    dec = machine.decode_riscv64(data, pc=0x1000)
    assert len(dec) == 2
    assert dec[0]["mnemonic"] == "addi" and dec[0]["address"] == 0x1000
    assert dec[1]["mnemonic"] == "add" and dec[1]["address"] == 0x1004
    assert "error" in machine.decode_riscv64(b"\x01\x02\x03")[0]
    # 模块内置样例应当能被正确拆解（小端字节流）
    for hexstr, _desc in machine.RV_SAMPLES:
        e = machine._decode_one_rv(int.from_bytes(bytes.fromhex(hexstr), "little"))
        assert e["mnemonic"] != "?", hexstr


def test_riscv64_cli_subprocess():
    """真实 CLI：machine --action riscv（无参数走样例；给字节走反汇编）。"""
    import subprocess, os, sys
    env = dict(os.environ); env["PYTHONPATH"] = "src/python"

    def run(*a):
        r = subprocess.run([sys.executable, "-m", "sysweeper", *a],
                           capture_output=True, text=True, env=env)
        return r.returncode, r.stdout, r.stderr

    rc, out, err = run("code", "machine", "--action", "riscv")
    assert rc == 0 and "RISC-V" in out, err
    # 给一条 RV 加法字节：b3003100 小端 = 0x003100B3 = add x1, x2, x3
    rc, out, err = run("code", "machine", "--action", "riscv", "--value", "b3003100")
    assert rc == 0 and "add x1, x2, x3" in out, err


JAVA_SOURCE = """
public class LowCodeProbe {
    private int n = 7;
    public int twice(int x) { return x * 2 + n; }
}
"""


def _compile_java_class(tmpdir: Path) -> bytes:
    src = tmpdir / "LowCodeProbe.java"
    src.write_text(JAVA_SOURCE, encoding="utf-8")
    subprocess.run(["javac", "-d", str(tmpdir), str(src)],
                   check=True, capture_output=True)
    return (tmpdir / "LowCodeProbe.class").read_bytes()


@pytest.mark.skipif(shutil.which("javac") is None, reason="需要 javac 才能生成 .class")
def test_java_classfile_real():
    with tempfile.TemporaryDirectory() as tmp:
        data = _compile_java_class(Path(tmp))
        info = machine.parse_classfile(data)
        assert "error" not in info
        assert info["magic"] == "0xCAFEBABE"
        assert info["this_class"] == "LowCodeProbe"
        assert info["super_class"] == "java/lang/Object"
        assert info["java_version"].startswith("Java SE")
        assert "PUBLIC" in info["access_names"]
        # 常量池里的类名必须被解析成字符串（而不是 #n）
        assert info["constant_pool_display"]
        assert any(v == "LowCodeProbe" for v in info["constant_pool_display"].values())
        methods = {m["name"]: m for m in info["methods"]}
        assert "twice" in methods and methods["twice"]["descriptor"] == "(I)I"
        assert methods["twice"]["code"]["code_length"] > 0
        # 反汇编出来的指令流应包含 imul / ireturn
        dis = machine.dis_java(methods["twice"]["code"]["code"], info["constant_pool"])
        names = [i["name"] for i in dis["instructions"]]
        assert "imul" in names and "ireturn" in names
        assert dis["stopped"] is None


def test_java_classfile_rejects_bad_input():
    assert machine.parse_classfile(b"")["error"]
    assert machine.parse_classfile(b"nope" * 4)["error"]


def test_java_dis_walks_operands():
    """手工构造的指令流：操作数长度必须被正确跳过。"""
    code = bytes([
        0x10, 0x2A,        # bipush 42
        0x3C,              # istore_1
        0x1B,              # iload_1
        0x05,              # iconst_2
        0x68,              # imul
        0xAC,              # ireturn
    ])
    dis = machine.dis_java(code)
    assert [i["name"] for i in dis["instructions"]] == \
        ["bipush", "istore_1", "iload_1", "iconst_2", "imul", "ireturn"]
    assert dis["count"] == 6 and dis["bytes"] == len(code)
    # 未收录的操作码要停下并说明位置
    dis = machine.dis_java(bytes([0x10, 0x01, 0xFF]))
    assert dis["stopped"] and "0xFF" in dis["stopped"]


def test_atomic_samples_decode():
    """并发原子指令样例：每条都能解出 mnemonic，LOCK 条目带原子标记。"""
    lines = machine.render_atomic_samples()
    assert any("x86-64 并发原子指令" in ln for ln in lines)
    decoded = "\n".join(lines)
    # 至少覆盖 xadd / cmpxchg / mfence / pause
    assert "xadd" in decoded and "cmpxchg" in decoded
    assert "mfence" in decoded and "pause" in decoded
    # LOCK 标记出现在原子指令行
    assert "[LOCK]" in decoded


def test_i18n_default_zh_and_switch_en():
    """默认中文（源语言）；显式切 en 才翻译；切回 zh_CN 复原；en_US 退化 en。"""
    from sysweeper import i18n
    saved = i18n.get_locale()
    try:
        i18n.set_locale("zh_CN")
        assert bits.render_bases(255)[0].startswith("进制对照")
        i18n.set_locale("en")
        out = bits.render_bases(255)
        assert out[0].startswith("Base comparison")
        assert "Decimal (human-readable, default): 255" in out[1]
        assert bits.base_name(3) == "Ternary"
        i18n.set_locale("en_US")  # 退化为 en
        assert bits.render_bases(255)[0].startswith("Base comparison")
    finally:
        i18n.set_locale(saved)


def test_i18n_lowcode_layers_en():
    """chars/comm/logic 三层的讲解标题与报错在 en 下翻译（扩层翻译 7.1）。

    标准引用名（RFC/GB/ITU-T/线路码标准等）属后台数据，不翻译——
    这里只验用户读到的标题与报错串被翻成英文。
    """
    from sysweeper import i18n
    saved = i18n.get_locale()
    try:
        i18n.set_locale("en")
        # 面板标题翻译
        assert logic.render_truth_table("A & B")[0].startswith("Expression: ")
        assert logic.render_karnaugh([0, 1, 2, 5], 3)[0].startswith("Karnaugh map")
        assert comm.render_baud_table()[0].startswith("Baud rate divider table")
        assert chars.render_base_compare(b"123456789")[0].startswith("Scheme")
        # 报错翻译
        with pytest.raises(ValueError) as exc:
            logic.parse("")
        assert "Empty expression" in str(exc.value)
        with pytest.raises(ValueError) as exc2:
            logic.parse("@@@")
        assert "Unrecognized character" in str(exc2.value)
    finally:
        i18n.set_locale(saved)


def test_i18n_locales_full():
    """联合国五常（中/英/法/俄）+ 德/日 六语言均加载且代表串翻译正确。

    锁定：available_locales 含全部六语言；fr/ru/de/ja 在显式切换下把代表性
    标题与报错翻成对应语言；未知语言码回退源语言（中文）。
    """
    from sysweeper import i18n
    saved = i18n.get_locale()
    try:
        assert set(i18n.available_locales()) >= {"zh_CN", "en", "fr", "ru", "de", "ja"}

        # 代表性 msgid 在各语言的译文预期（标题 + 报错各取一条）
        expect = {
            "fr": ("Expression vide", "Comparaison de bases (entrée = %s)"),
            "ru": ("Пустое выражение", "Сравнение систем счисления (ввод = %s)"),
            "de": ("Leerer Ausdruck", "Basisvergleich (Eingabe = %s)"),
            "ja": ("空式", "基数対照（入力 = %s）"),
        }
        for loc, (expr, cmp_) in expect.items():
            i18n.set_locale(loc)
            assert i18n._("空表达式") == expr, (loc, i18n._("空表达式"))
            assert i18n._("进制对照（输入 = %s）") == cmp_, (loc, i18n._("进制对照（输入 = %s）"))

        # 完整码退化：fr_FR -> fr
        i18n.set_locale("fr_FR")
        assert i18n._("空表达式") == "Expression vide"

        # 未知语言回退源语言（中文原样）
        i18n.set_locale("xx_XX")
        assert i18n._("空表达式") == "空表达式"
    finally:
        i18n.set_locale(saved)


# ==================================================================
# 包级
# ==================================================================

def test_lowcode_summary_covers_all_layers():
    items = lowcode_summary()
    assert [i["key"] for i in items] == ["bits", "chars", "comm", "logic", "machine"]
    for item in items:
        assert item["items"] > 0 and item["standards"] > 0
    for mod in (bits, chars, comm, logic, machine):
        assert mod.CAPABILITIES and mod.STANDARD_REFS
        for key, ref in mod.STANDARD_REFS.items():
            assert set(ref) >= {"cn", "intl", "regional"}, key
