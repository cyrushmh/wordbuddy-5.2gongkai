"""从零造系统学习应用只读子系统（sysdev，v0.6.89）：分配器·编译器·内核·模拟器。

「导入分析学习应用」pepsipu（Sammy Hajhamid）GitHub 项目群的落地。七个仓库、
一个主题：一个人用最小依赖从零构建系统层组件——warpalloc（110 行 NASM 分配器）、
aski（约 1077 行 Rust 编译器）、xinOS-old / OSpaint（玩具 OS）、ramenbox（6502
幻想主机）、cx（zsh 多账户封装）、torus（pnpm 工作区校园 API）。

本模块做三件事（全部只读）：

1. **知识库消费**：``reference()/reference_all()`` 读 data/sysdev_docs.json——
   每个仓库的「可复用模式 + 适用边界 + 反面教材」三件套，条条回链源文件。
2. **本机工具链与内存体检**（只读探测，绝不编译、绝不运行被分析源码）：
   ``probe_toolchain()`` 盘点从零构建工具链（nasm/yasm/gcc/clang/python3/node/
   pnpm/qemu-system-i386/make/cmake，仅 ``--version`` 类只读命令）；
   ``probe_malloc_env()`` 展示 glibc malloc 环境变量与 glibc 版本；
   ``probe_memory_footprint()`` 解析 /proc/self/status 的 Vm* 字段。
3. **零参聚合报告**：``sysdev_report()`` 供任务/CLI/GUI 复用，
   ``sysdev_doc_list()`` 列主题清单。

红线（与全工具一致，本模块绝不越界）：
- **绝不编译/运行任何被分析的第三方源码**——学习应用是读，不是跑；
- **绝不修改 malloc 环境变量或任何进程环境**——只读展示，给指引不代设；
- **绝不 vendored 第三方源代码**——有许可证的（warpalloc MIT / xinOS-old BSD）
  学模式，无许可证的默认保留所有权利只学思想；所有模式总结为本仓原创表述；
- 探测命令仅限 ``--version``/``-v`` 类只读调用，零网络、零写入、零进程注入。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "sysdev_docs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:  # noqa: BLE001
        return {}


REFS = _load_refs()


def reference(key: str) -> dict:
    """返回某「从零造系统」主题的文档参考（含 protocols/interfaces/advice）。"""
    return REFS.get(key, {})


def reference_all() -> dict:
    """返回全部「从零造系统」主题文档参考。"""
    return REFS


# --------------------------------------------------------------------------- #
# 只读命令执行（仅 --version/-v 类；绝不放置任何编译/运行路径）                 #
# --------------------------------------------------------------------------- #

def _version_of(cmd: str, args: list = None, timeout: float = 8.0) -> str:
    """取一个工具的首行版本串（只读）。找不到返回空串。"""
    if not shutil.which(cmd):
        return ""
    try:
        out = subprocess.run([cmd] + (args or ["--version"]),
                             capture_output=True, text=True,
                             timeout=timeout).stdout
    except Exception:  # noqa: BLE001
        return ""
    return (out or "").strip().splitlines()[0] if out and out.strip() else ""


# --------------------------------------------------------------------------- #
# 探针一：从零构建工具链（nasm/yasm/gcc/clang/python3/node/pnpm/qemu/make）    #
# --------------------------------------------------------------------------- #

# (id, 命令, 版本参数, 中文名, 用途说明)
TOOLCHAIN = (
    ("nasm", "nasm", ["-v"], "NASM 汇编器", "warpalloc/walloc.asm 与 xinOS bootloader 的汇编器"),
    ("yasm", "yasm", ["--version"], "YASM 汇编器", "NASM 语法超集，备选汇编器"),
    ("gcc", "gcc", ["--version"], "GCC", "链接 walloc.o、编译 aski 之外的 C 侧 glue"),
    ("clang", "clang", ["--version"], "Clang/LLVM", "对照 -S 输出观察编译器分节"),
    ("python3", "python3", ["--version"], "Python 3", "ramenbox 模拟器与 gen_ops.py 的运行时"),
    ("node", "node", ["--version"], "Node.js", "torus web 侧与 Deno 控制台同源生态"),
    ("pnpm", "pnpm", ["--version"], "pnpm", "torus 的 workspace 包管理器"),
    ("qemu", "qemu-system-i386", ["--version"], "QEMU（i386）", "xinOS/OSpaint 可启动镜像的验收闭环"),
    ("make", "make", ["--version"], "GNU Make", "xinOS/OSpaint Makefile 构建驱动"),
    ("cmake", "cmake", ["--version"], "CMake", "xinOS CMakeLists.txt 构建驱动"),
)


def probe_toolchain() -> tuple:
    """只读盘点本机从零构建工具链（仅 --version 类调用）。"""
    found, missing = [], []
    for tid, cmd, args, name, use in TOOLCHAIN:
        ver = _version_of(cmd, args)
        row = {"id": tid, "name": name, "use": use, "version": ver}
        (found if ver else missing).append(row)
    return True, {
        "ok": True,
        "found": found,
        "missing": missing,
        "found_n": len(found),
        "total": len(TOOLCHAIN),
    }


# --------------------------------------------------------------------------- #
# 探针二：glibc malloc 环境变量与 glibc 版本（只读展示，绝不代设）             #
# --------------------------------------------------------------------------- #

# (环境变量, 中文说明, warpalloc/预分配视角的意义)
MALLOC_ENV = (
    ("MALLOC_ARENA_MAX", "线程 arena 上限数",
     "多线程程序的主要旋钮：arena 多则内存 footprint 涨、锁竞争降"),
    ("MALLOC_TRIM_THRESHOLD_", "归还内核的堆顶余量阈值",
     "预分配思想的 glibc 对应面：sbrk 增长后顶部留多少才 trim 还内核"),
    ("MALLOC_MMAP_THRESHOLD_", "大块改走 mmap 的阈值",
     "大分配绕过主堆的开关；warpalloc 的荒野推进在 glibc 侧由 brk/mmap 分担"),
    ("MALLOC_PERTURB_", "分配即填充扰动字节",
     "调试用：让 use-after-free 更快暴露，生产关闭"),
    ("MALLOC_CHECK_", "glibc 堆完整性检查级别",
     "调试用：0 关/1 告警/2 中止/3 中止并打印；生产关闭"),
)


def probe_malloc_env() -> tuple:
    """只读展示本机 glibc malloc 环境变量与 glibc 版本。绝不修改任何环境。"""
    rows = []
    for var, name, note in MALLOC_ENV:
        rows.append({"var": var, "name": name, "note": note,
                     "value": os.environ.get(var, "")})
    glibc = ""
    try:
        glibc = os.confstr("CS_GNU_LIBC_VERSION") or ""
    except (ValueError, OSError):  # 非 glibc 平台没有该键
        glibc = ""
    return True, {"ok": True, "glibc": glibc, "vars": rows}


# --------------------------------------------------------------------------- #
# 探针三：本进程内存足迹（/proc/self/status，仅 Linux；只读）                   #
# --------------------------------------------------------------------------- #

def probe_memory_footprint() -> dict:
    """只读解析 /proc/self/status 的 Vm* 字段。非 Linux 或不可读返回空 dict。"""
    out = {}
    try:
        with open("/proc/self/status", "r", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith(("VmSize:", "VmRSS:", "VmPeak:", "VmHWM:")):
                    key, _, val = line.partition(":")
                    out[key.strip()] = val.strip()
    except OSError:
        return {}
    return out


# --------------------------------------------------------------------------- #
# 聚合报告（零参可调用，供任务/CLI/GUI 复用）                                   #
# --------------------------------------------------------------------------- #

def sysdev_report() -> tuple:
    """从零造系统学习应用总报告：知识库 + 工具链 + malloc 环境 + 内存足迹。"""
    _, tools = probe_toolchain()
    _, malloc_env = probe_malloc_env()
    lines = [
        "══ 从零造系统学习应用总报告（sysdev，只读）══",
        "来源：pepsipu 项目群 7 仓库（warpalloc / aski / xinOS-old / OSpaint /",
        "      ramenbox / cx / torus）——学习不等于打包，模式总结均为原创表述。",
        "",
        "── 知识库主题（data/sysdev_docs.json）──",
    ]
    for key, entry in REFS.items():
        lines.append(f"· {key} — {entry.get('name', '')}")
    lines += [
        "",
        f"── 本机从零构建工具链：{tools['found_n']}/{tools['total']} 在位 ──",
    ]
    for row in tools["found"]:
        lines.append(f"· {row['name']}：{row['version']}")
    if tools["missing"]:
        lines.append("· 缺席：" + "、".join(r["name"] for r in tools["missing"]))
    lines += [
        "",
        f"── glibc：{malloc_env['glibc'] or '非 glibc / 不可读'} ──",
    ]
    for row in malloc_env["vars"]:
        val = row["value"] or "（未设置）"
        lines.append(f"· {row['var']} = {val} — {row['name']}")
    fp = probe_memory_footprint()
    if fp:
        lines += ["", "── 本进程内存足迹（/proc/self/status，只读）──"]
        for k, v in fp.items():
            lines.append(f"· {k}: {v}")
    lines += [
        "",
        "── 红线 ──",
        "· 绝不编译/运行被分析的第三方源码（学习应用是读，不是跑）；",
        "· 绝不修改 malloc 环境变量或任何进程环境（只读展示，给指引不代设）；",
        "· 绝不 vendored 第三方源代码（MIT/BSD 学模式，无许可证只学思想）。",
    ]
    return True, "\n".join(lines)


def sysdev_doc_list() -> list:
    """返回 sysdev 主题清单，供 CLI/GUI 展示。"""
    return [f"· {key} — {entry.get('name', '')}" for key, entry in REFS.items()]
