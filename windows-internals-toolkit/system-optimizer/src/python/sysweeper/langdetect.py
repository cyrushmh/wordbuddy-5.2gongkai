"""语言运行时探测：根据当前系统环境探测可用的语言运行时，
并据此自动启用/禁用某些以特定语言实现的优化功能（不强求用户安装）。

例如：某项大文件分析功能用 Ruby 实现，则仅在探测到 ruby 时自动启用；
未安装 Ruby 时该功能自动隐藏，不报错、不要求安装。探测纯标准库、跨平台。
"""

from __future__ import annotations

import shutil


# 每种语言：探测命令 + 友好名 + 参考标准（用于展示「按语言自动启用」的思路）
LANGUAGES = {
    "python": {"which": "python3", "name": "Python", "note": "本工具即 Python 实现，默认可用"},
    "ruby":   {"which": "ruby", "name": "Ruby", "note": "可用 Ruby 标准库做去重/大文件分析"},
    "go":     {"which": "go", "name": "Go", "note": "可 go run 一次性分析脚本，无需预编译"},
    "node":   {"which": "node", "name": "Node.js", "note": "可做项目依赖审计 / 缓存清理"},
    "perl":   {"which": "perl", "name": "Perl", "note": "UNIX 传统脚本语言，做文本/日志分析"},
    "lua":    {"which": "lua", "name": "Lua", "note": "轻量嵌入语言，做配置/日志处理"},
    "rust":   {"which": "rustc", "name": "Rust", "note": "可编译一次性系统工具"},
    "java":   {"which": "java", "name": "Java", "note": "可做跨平台分析工具"},
    "dotnet": {"which": "dotnet", "name": ".NET", "note": "可做跨平台分析工具"},
    "bun":    {"which": "bun", "name": "Bun", "note": "可作一次性诊断脚本（trae 分支引入的 sysweeper.ts 同口径组件）"},
    "c":      {"which": "cc", "name": "C", "note": "可编译一次性系统工具（sysweeper-c.c 单文件组件）"},
    "elixir": {"which": "elixir", "name": "Elixir", "note": "可作一次性诊断脚本（sysweeper.exs）"},
    "erlang": {"which": "erl", "name": "Erlang", "note": "可作一次性诊断脚本（sysweeper.erl）"},
    "kotlin": {"which": "kotlinc", "name": "Kotlin", "note": "可编译跨平台工具（SysweeperKt.kt）"},
    "swift":  {"which": "swift", "name": "Swift", "note": "可编译跨平台工具（SysweeperSwift.swift）"},
    "zig":    {"which": "zig", "name": "Zig", "note": "可编译一次性系统工具（sysweeper.zig 单文件组件）"},
    "llvm":   {"which": "llvm-config", "name": "LLVM", "note": "可 clang --target=<triple> 做交叉编译；llvm-config 读已构建目标"},
    "clang":  {"which": "clang", "name": "Clang", "note": "LLVM C/C++ 前端，可作一次性诊断/交叉编译脚本"},
    "nasm":   {"which": "nasm", "name": "NASM", "note": "x86/x86_64 汇编器，可作一次性汇编诊断/优化脚本"},
    "yasm":   {"which": "yasm", "name": "YASM", "note": "NASM 语法超集汇编器，可作一次性汇编诊断/优化脚本"},
}


def available(lang: str) -> bool:
    """当前环境是否装了某语言运行时（which 探测）。"""
    spec = LANGUAGES.get(lang)
    if not spec:
        return False
    return shutil.which(spec["which"]) is not None


def available_languages() -> list:
    """返回当前已安装的语言 key 列表。"""
    return [k for k in LANGUAGES if available(k)]


def detect_languages() -> dict:
    """探测全部语言的可用性，返回 {key: {name, available, path, note}}。"""
    out = {}
    for key, spec in LANGUAGES.items():
        path = shutil.which(spec["which"])
        out[key] = {
            "name": spec["name"],
            "available": path is not None,
            "path": path or "",
            "note": spec.get("note", ""),
        }
    return out
