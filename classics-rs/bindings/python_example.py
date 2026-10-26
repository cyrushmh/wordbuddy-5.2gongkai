#!/usr/bin/env python3
"""通过 C-ABI 调用 Rust 内核（libclassics.so），演示「同一内核、任意语言复用」。

编译内核：cargo build --release
运行本示例：python3 bindings/python_example.py
"""
import ctypes
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SO = os.path.join(HERE, "..", "target", "x86_64-unknown-linux-gnu", "release", "libclassics.so")

lib = ctypes.CDLL(os.path.abspath(SO))
lib.classics_version.restype = ctypes.c_void_p
lib.classics_decode.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t]
lib.classics_decode.restype = ctypes.c_void_p
lib.classics_free_string.argtypes = [ctypes.c_void_p]


def decode(data: bytes) -> str:
    buf = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    p = lib.classics_decode(buf, len(data))
    s = ctypes.string_at(p).decode("utf-8")
    lib.classics_free_string(p)
    return s


def main() -> int:
    ver_p = lib.classics_version()
    print("classics_version() =>", ctypes.string_at(ver_p).decode())
    lib.classics_free_string(ver_p)

    # 1) 严格 UTF-8 透传
    print("utf8 中文测试 =>", decode("中文测试——道德经".encode("utf-8")))

    # 2) GB18030 回退："中"=D6 D0，"国"=B9 FA
    print("gb18030 中国 =>", decode(bytes([0xD6, 0xD0, 0xB9, 0xFA])))

    # 3) 非法字节 -> 含 U+FFFD 的损失性替换
    lossy = decode(bytes([0xFF, 0xFE, 0x41, 0x42]))
    print("lossy 含U+FFFD =>", "是" if "�" in lossy else "否")
    return 0


if __name__ == "__main__":
    sys.exit(main())
