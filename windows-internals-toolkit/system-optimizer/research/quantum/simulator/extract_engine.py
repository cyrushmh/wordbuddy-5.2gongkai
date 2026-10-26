#!/usr/bin/env python3
"""从 quantum-viewer.html 的 <script> 中提取量子引擎片段，供 node 侧独立验证。
保证「被测引擎」与「页面引擎」同源：提取后被验证的就是交付物本身的代码。"""
import re, pathlib, sys

here = pathlib.Path(__file__).parent
html = (here / "quantum-viewer.html").read_text(encoding="utf-8")

m = re.search(r"/\* =+ 引擎.*?(?=/\* =+ 状态)", html, re.S)
if not m:
    sys.exit("未找到引擎代码块（标记 /* ===== 引擎 ... 状态 */）")
engine = m.group(0)

exports = "\nexport {amp, matVec, fullGate, permGate, CNOT, SWAPM, QFT, QFTdag, phaseGate, measureQ, bitsToTrits, tritsToBits, packTrit5, pack5ToBin, tritRegister, TRIT2PAIR, U2};\n"
(here / "html_engine.mjs").write_text(engine + exports, encoding="utf-8")
print(f"extracted {len(engine)} chars -> html_engine.mjs（含 export 尾注）")
