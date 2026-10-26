"""lowcode —— 低层码制：机器码 / 编译码 / 字符编码 / 通信码 / 逻辑转换码。

这是 sysweeper 的「底层视图」子包，把平时散落在各处、靠人肉心算的东西
变成**可验证的纯函数**：

    bits     位与二进制：端序、位域、补码、格雷码、BCD、奇偶、IEEE 754
    chars    字符编码：ASCII/IA5、Unicode 码点、UTF-8/16/32、Base 系列、
             百分号/HTML 转义、摩尔斯电码、字符集互转
    comm     通信码：CRC 系列、校验和、成帧（HDLC/SLIP/COBS）、线路编码、
             汉明纠错、波特率误差
    logic    逻辑转换码：真值表、SOP/POS、卡诺图、Quine-McCluskey、
             NAND 变换、加法器
    machine  机器码与字节码：Python 字节码、Java class、x86-64 与 RISC-V 指令拆解

设计约束（与全包一致）
--------------------
1. **纯标准库、零第三方依赖**——有 python3 就能跑；
2. **只读、纯函数**——不碰文件系统（除 `machine` 解析调用方传入的字节外）、
   不联网、不改系统；
3. **graceful**——入参非法返回 `None` / 空结构并带 `error` 说明，不抛异常；
4. **给标准出处**——每个模块都有 `STANDARD_REFS`，按「国内优先 / 国际 /
   地区」三层标注，与 models.CATEGORY_STANDARDS 同口径；
5. **都带文本渲染函数**——CLI/GUI 直接吃，不重复写格式化逻辑。

这些能力本身不"优化"任何东西，它们的价值在于：排查编码乱码、核对通信
帧校验、看懂反汇编、手工验算补码时，不用再去翻网页计算器。
"""

from __future__ import annotations

from sysweeper.i18n import _

__all__ = ["bits", "chars", "comm", "logic", "machine", "LAYERS"]

# 分层清单：key → (中文名, 一句话说明)
LAYERS = [
    ("bits", "位与二进制", "端序 / 位域 / 补码 / 格雷码 / BCD / 奇偶 / IEEE 754"),
    ("chars", "字符编码", "ASCII / Unicode / UTF-8 / Base 系列 / 转义 / 摩尔斯"),
    ("comm", "通信码", "CRC / 校验和 / 成帧 / 线路编码 / 汉明码 / 波特率"),
    ("logic", "逻辑转换码", "真值表 / SOP-POS / 卡诺图 / QM 化简 / NAND / 加法器"),
    ("machine", "机器码与字节码", "Python 字节码 / Java class / x86-64 与 RISC-V 指令"),
]


def summary() -> list:
    """返回各层的能力摘要（供 `sysweeper code` 概览面板）。"""
    from . import bits, chars, comm, logic, machine

    return [
        {"key": "bits", "name": _("位与二进制"), "desc": _("端序/位域/补码/格雷码/BCD/奇偶/IEEE 754"),
         "items": len(bits.CAPABILITIES), "standards": len(bits.STANDARD_REFS)},
        {"key": "chars", "name": _("字符编码"), "desc": _("ASCII/Unicode/UTF-8/Base 系列/转义/摩尔斯"),
         "items": len(chars.CAPABILITIES), "standards": len(chars.STANDARD_REFS)},
        {"key": "comm", "name": _("通信码"), "desc": _("CRC/校验和/成帧/线路编码/汉明码/波特率"),
         "items": len(comm.CAPABILITIES), "standards": len(comm.STANDARD_REFS)},
        {"key": "logic", "name": _("逻辑转换码"), "desc": _("真值表/SOP-POS/卡诺图/QM/NAND/加法器"),
         "items": len(logic.CAPABILITIES), "standards": len(logic.STANDARD_REFS)},
        {"key": "machine", "name": _("机器码与字节码"),
         "desc": _("Python 字节码/Java class/x86-64 与 RISC-V 指令"),
         "items": len(machine.CAPABILITIES), "standards": len(machine.STANDARD_REFS)},
    ]
