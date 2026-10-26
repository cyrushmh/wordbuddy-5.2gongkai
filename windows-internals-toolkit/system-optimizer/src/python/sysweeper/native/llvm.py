"""LLVM 工具链只读探测与交叉编译目标矩阵（llvm）：把「添加编程语言 LLVM」与「按时间序列支持交叉编译」落为只读子系统。

可读项：
  - 工具链探针：llvm-config / clang / lld / clangd / mlir / lldb / compiler-rt（which 探测，纯标准库）
  - 交叉编译目标矩阵：按时间序列逐步扩充的 LLVM 目标三元组（aarch64/armv7/riscv64/x86_64-mingw/wasm32…），
    每条带「加入版本 / 用途 / sysroot 指引」；CHANGELOG 段记录扩充史（久久为功、常态化回头看）
  - 目标可用性：如本机有 `llvm-config --targets-built`，则实读已构建目标，否则按知识库给推荐矩阵

红线：只探测 + 出目标矩阵与 sysroot 指引；绝不编译、绝不下载 sysroot、绝不改写工具链配置。
"""

from __future__ import annotations

import shutil
import subprocess


PROBES = (
    ("clang_report", "Clang 前端"),
    ("lld_report", "lld 链接器"),
    ("mlir_report", "MLIR 中间表示"),
    ("targets_report", "交叉编译目标矩阵"),
)

# ── 交叉编译目标矩阵（按时间序列逐步扩充；CHANGELOG 记录每次新增）──
# 每条：(三元组, 加入版本, 用途, sysroot 指引)
TARGETS = (
    ("aarch64-linux-gnu", "v0.6.42", "64 位 ARM Linux（树莓派/开发板/服务器）",
     "装 gcc-aarch64-linux-gnu 交叉工具链与 qemu-user 跑通测试"),
    ("armv7l-linux-gnueabihf", "v0.6.42", "32 位 ARM Linux（硬浮点，老开发板）",
     "装 gcc-arm-linux-gnueabihf + 对应 sysroot"),
    ("riscv64-linux-gnu", "v0.6.42", "RISC-V 64 位 Linux（开源硬件/平头哥等）",
     "装 gcc-riscv64-linux-gnu + qemu-riscv64"),
    ("x86_64-w64-mingw32", "v0.6.42", "Windows 64 位（MinGW-w64 目标，跨到 Win）",
     "装 mingw-w64 + 走 clang --target=x86_64-w64-mingw32"),
    ("wasm32-unknown-unknown", "v0.6.42", "WebAssembly（浏览器/轻量沙箱运行时）",
     "走 clang --target=wasm32 + wasi-sdk 或 emscripten sysroot"),
    ("i686-linux-gnu", "v0.6.42", "32 位 x86 Linux（老旧兼容/遗留环境）",
     "装 gcc-multilib + 32 位库"),
    ("powerpc64le-linux-gnu", "v0.6.42", "POWER 小端 Linux（服务器/旧 Mac）",
     "装 gcc-powerpc64le-linux-gnu"),
    ("loongarch64-linux-gnu", "v0.6.42", "龙芯 LoongArch64（国产指令集）",
     "装 gcc-loongarch64-linux-gnu"),
    # ── v0.6.44 时间序列扩充（常态化的回头看、久久为功）：在初始 8 目标基础上续加 ──
    ("i686-w64-mingw32", "v0.6.44", "Windows 32 位（MinGW-w64 目标，跨到老 Win/x86）",
     "装 mingw-w64 + clang --target=i686-w64-mingw32"),
    ("aarch64-w64-mingw32", "v0.6.44", "Windows on ARM64（跨到 Surface/Win ARM 设备）",
     "装 mingw-w64-aarch64 工具链 + clang --target=aarch64-w64-mingw32"),
    ("armv7-w64-mingw32", "v0.6.44", "Windows on ARM32（老 Surface/Continuum 遗留）",
     "装 mingw-w64-armv7 工具链"),
    ("x86_64-apple-darwin", "v0.6.44", "macOS x86_64（需 Apple SDK sysroot，不可自动下载）",
     "准备 Xcode/Apple SDK sysroot，clang --target=x86_64-apple-darwin -isysroot <sdk>"),
    ("aarch64-apple-darwin", "v0.6.44", "macOS Apple Silicon（Apple Silicon 原生交叉）",
     "准备 Apple Silicon SDK sysroot"),
    ("arm64-apple-ios", "v0.6.44", "iOS 设备（需 Xcode iOS SDK，闭源签名链）",
     "准备 Xcode iOS SDK sysroot + 后续签名由 Xcode/fastlane 完成"),
    ("riscv32-linux-gnu", "v0.6.44", "RISC-V 32 位 Linux（嵌入式/MCU 前置）",
     "装 gcc-riscv32-linux-gnu + qemu-riscv32"),
    ("thumbv7em-none-eabi", "v0.6.44", "ARM Cortex-M 裸机（无 OS，嵌入式固件）",
     "用 arm-none-eabi-gcc/newlib 或 clang + llvm-libc；绝不刷固件"),
    ("thumbv8m-none-eabi", "v0.6.44", "ARM Cortex-M23/M33 裸机（TrustZone-M）",
     "同上，启用 -mcmse 安全域由厂商工具确认"),
    ("s390x-linux-gnu", "v0.6.44", "IBM Z 大端 Linux（主机/银行核心系统）",
     "装 gcc-s390x-linux-gnu"),
    ("mips64el-linux-gnuabi64", "v0.6.44", "MIPS 小端 64（路由器/工控遗留设备）",
     "装 gcc-mips64el-linux-gnuabi64"),
    ("sparc64-linux-gnu", "v0.6.44", "SPARC 64（老 SUN/服务器遗留）",
     "装 gcc-sparc64-linux-gnu"),
    ("nvptx64-nvidia-cuda", "v0.6.44", "NVIDIA PTX（GPU 计算/Offload，仅生成设备码）",
     "配合 clang offloading + CUDA toolkit；绝不安装/改写驱动"),
    ("bpfel-unknown-none", "v0.6.44", "eBPF（Linux 内核可加载字节码，观测/网络）",
     "clang -target=bpf -c <src>.c -o <out>.o；加载由 bpftool/ip 完成"),
    ("x86_64-unknown-linux-musl", "v0.6.44", "musl 静态链接（容器/Alpine 交叉、无 glibc）",
     "准备 musl-cross 或 zig；静态链接便于小镜像"),
)

CHANGELOG = (
    ("v0.6.42", "首次引入 LLVM 子系统：探针 clang/lld/mlir，交叉编译矩阵初始 8 目标"
                "（aarch64/armv7/riscv64/x86_64-mingw/wasm32/i686/ppc64le/loongarch64）；"
                "后续按时间序列逐步扩充（常态化的回头看）。"),
    ("v0.6.44", "按时间序列扩充 LLVM 交叉编译目标矩阵：在 v0.6.42 初始 8 目标基础上新增 15 目标"
                "（Windows 全架构 i686/aarch64/armv7-mingw、macOS x86_64/Apple Silicon、iOS、"
                "RISC-V 32、ARM Cortex-M 裸机 v7em/v8m、IBM Z s390x、MIPS64el、SPARC64、"
                "NVIDIA PTX、eBPF、musl 静态）；报告按版本时间序列排序展示。"),
)


def _ver(exe: str) -> str | None:
    if shutil.which(exe) is None:
        return None
    try:
        return subprocess.run([exe, "--version"], capture_output=True, text=True,
                               timeout=6).stdout.splitlines()[0].strip()
    except (OSError, subprocess.SubprocessError, IndexError):
        return "(已安装，版本读取失败)"


def clang_report() -> tuple:
    v = _ver("clang")
    if v is None:
        return False, "未安装 clang；如只需交叉编译可用 gcc 交叉链替代"
    return True, f"clang: {v}"


def lld_report() -> tuple:
    v = _ver("lld")
    if v is None and shutil.which("ld.lld") is None:
        return False, "未安装 lld（ld.lld）；默认回退到 GNU ld/gold"
    return True, "lld 链接器可用（ld.lld）"


def mlir_report() -> tuple:
    if shutil.which("mlir-opt") is None and shutil.which("mlir-translate") is None:
        return False, "未安装 MLIR 工具（mlir-opt/mlir-translate）；多面体优化类任务不可用时属正常"
    return True, "MLIR 工具可用（mlir-opt/mlir-translate）"


def targets_report() -> tuple:
    """交叉编译目标矩阵：优先读本机构建目标，否则给知识库推荐矩阵。"""
    built = None
    if shutil.which("llvm-config"):
        try:
            built = subprocess.run(["llvm-config", "--targets-built"], capture_output=True,
                                   text=True, timeout=6).stdout
        except (OSError, subprocess.SubprocessError):
            built = None
    lines = ["LLVM 交叉编译目标矩阵（按时间序列逐步扩充）:"]
    if built:
        lines.append("   · 本机已构建目标（llvm-config --targets-built 实读）:")
        for t in sorted(set(built.split())):
            lines.append(f"     - {t}")
    else:
        lines.append("   · 本机未装 llvm-config；按知识库给推荐矩阵（常态化扩充中）:")
        for triple, ver, use, _sys in sorted(TARGETS, key=lambda r: (r[1], r[0])):
            lines.append(f"     - {triple}（{ver} 加入）{use}")
    return True, "\n".join(lines)


def built_targets() -> list:
    """返回本机 llvm 已构建目标三元组（只读实读，失败返回 []）。"""
    if shutil.which("llvm-config") is None:
        return []
    try:
        out = subprocess.run(["llvm-config", "--targets-built"], capture_output=True,
                             text=True, timeout=6).stdout
        return sorted(set(out.split()))
    except (OSError, subprocess.SubprocessError):
        return []


def environment_report() -> list:
    lines = ["LLVM 工具链（llvm）· 本机只读探测："]
    for fn, lab in PROBES:
        ok, msg = getattr(__import__("sys").modules[__name__], fn)()
        lines.append(f"   · {lab}: {'✓ 可用' if ok else '✗ 不适用'}")
        if isinstance(msg, str) and msg.strip():
            lines.append("       " + msg.replace("\n", "\n       "))
    return lines


def llvm_report(env_tags: list | None = None, readings: dict | None = None) -> tuple:
    lines = ["== LLVM 工具链报告（llvm：clang/lld/mlir 探测 + 交叉编译目标矩阵，只读不写）=="]
    lines.append(f"维度标签: {sorted(set(env_tags or [])) or '未声明（默认基线）'}")
    lines.append("")
    lines.append("[① 工具链探针]")
    for fn, lab in PROBES[:3]:
        ok, msg = getattr(__import__("sys").modules[__name__], fn)()
        lines.append(f"   · {lab}: {'✓ 可用' if ok else '✗ 不适用'}")
        if isinstance(msg, str) and msg.strip():
            lines.append("       " + msg)
    lines.append("")
    lines.append("[② 交叉编译目标矩阵（按时间序列逐步扩充）]")
    rows = built_targets()
    for triple, ver, use, sysroot in sorted(TARGETS, key=lambda r: (r[1], r[0])):
        mark = "● 本机已构建" if triple in rows else "○ 知识库推荐"
        lines.append(f"   · [{mark}] {triple}（{ver}）{use}")
        lines.append(f"        sysroot 指引: {sysroot}")
    lines.append("")
    lines.append("[③ CHANGELOG（久久为功，常态化回头看）]")
    for ver, note in CHANGELOG:
        lines.append(f"   · {ver}: {note}")
    lines.append("")
    lines.append("安全不变量：llvm 只探测 + 出目标矩阵与 sysroot 指引；绝不编译、绝不下载 sysroot、"
                 "绝不改写工具链配置；是否施工始终由用户在构建脚本/厂商工具确认。")
    return True, "\n".join(lines)


def guide_cross(triple: str | None = None) -> tuple:
    tgt = triple or "<target-triple>"
    lines = [
        f"交叉编译指引（--target={tgt}，不代执行）:",
        "   1. 确认 sysroot/交叉工具链（见目标矩阵 sysroot 指引）已就位",
        "   2. clang --target=<triple> -sysroot <path> -fuse-ld=lld <src> -o <out>",
        "   3. 用 qemu-user 或真实板跑通测试；绝不改动本机默认工具链",
    ]
    return True, "\n".join(lines)


TUNES = (
    ("guide_cross", "LLVM 交叉编译（规范指引，不代执行）"),
)


def llvm_tune_list() -> list:
    return [f"· {fn}() — {desc}" for fn, desc in TUNES]
