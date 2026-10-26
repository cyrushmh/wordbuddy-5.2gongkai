#!/usr/bin/env python3
"""PE Viewer —— tkinter 图形界面（标准库，跨平台，Windows 原生可运行）。"""
import struct
import tkinter as tk
from tkinter import filedialog, scrolledtext

ARCH = {0x14C: "x86", 0x8664: "x64", 0x1C0: "ARM", 0xAA64: "ARM64"}


def parse_pe(path: str) -> str:
    with open(path, "rb") as f:
        d = f.read()
    if len(d) < 0x40 or d[:2] != b"MZ":
        return "不是合法 PE（缺少 MZ 头）\n"
    e_lfanew = struct.unpack_from("<I", d, 0x3C)[0]
    if e_lfanew + 4 > len(d) or d[e_lfanew:e_lfanew + 4] != b"PE\x00\x00":
        return "缺少 PE\\0\\0 签名\n"
    coff = e_lfanew + 4
    machine = struct.unpack_from("<H", d, coff)[0]
    nsec = struct.unpack_from("<H", d, coff + 2)[0]
    optsize = struct.unpack_from("<H", d, coff + 16)[0]
    opt = coff + 20
    magic = struct.unpack_from("<H", d, opt)[0]
    pe32p = magic == 0x20B
    entry = struct.unpack_from("<I", d, opt + 16)[0]
    ib = struct.unpack_from("<Q", d, opt + 24)[0] if pe32p else struct.unpack_from("<I", d, opt + 28)[0]
    subsys = struct.unpack_from("<H", d, opt + 68)[0]
    lines = [
        f"文件: {path}",
        f"架构: {ARCH.get(machine, '其它')} (machine={machine:#06x})",
        f"节数: {nsec}",
        f"Magic: {'PE32+' if pe32p else 'PE32'} ({magic:#06x})",
        f"入口点: {entry:#010x}",
        f"ImageBase: {ib:#010x}",
        f"子系统: {subsys}",
    ]
    sec = opt + optsize
    for i in range(nsec):
        s = sec + i * 40
        if s + 40 > len(d):
            break
        name = d[s:s + 8].split(b"\x00")[0].decode("latin1", "replace")
        vaddr, vsize = struct.unpack_from("<II", d, s + 12)
        rawptr, rawsize = struct.unpack_from("<II", d, s + 16)
        lines.append(f"  节 {i}: {name:<8} VA={vaddr:#010x} VSize={vsize:#x} Raw={rawptr:#x}/{rawsize:#x}")
    return "\n".join(lines)


def open_file():
    p = filedialog.askopenfilename(
        filetypes=[("PE 文件", "*.exe;*.dll;*.sys;*.ocx"), ("所有文件", "*.*")]
    )
    if p:
        txt.delete(1.0, tk.END)
        txt.insert(tk.END, parse_pe(p))


if __name__ == "__main__":
    root = tk.Tk()
    root.title("PE Viewer (tkinter)")
    root.geometry("640x480")
    tk.Button(root, text="打开 PE 文件...", command=open_file).pack(pady=6)
    txt = scrolledtext.ScrolledText(root, wrap=tk.WORD)
    txt.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
    txt.insert(tk.END, "点击「打开 PE 文件...」选择一个 .exe/.dll 查看 PE 头信息。")
    root.mainloop()
