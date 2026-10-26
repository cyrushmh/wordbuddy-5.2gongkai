"""开源 Windows 分析·学习应用只读诊断（v0.6.76 新建）。

把一批开源 Windows 分析与学习类应用（System Informer / ReactOS / Ghidra / x64dbg /
radare2·Cutter / dnSpyEx / Volatility3 / MemProcFS / Wine / Windows Driver Samples 等）
按本工具的**只读诊断**口径结构化摸一遍，并嵌入整体系统。与 radio 子系统同一范式：

- **先定系统，再谈目录**：读任何目标之前先判定眼前的环境属于哪一套（Windows 原生 /
  WSL 内 / Linux / macOS / Android），然后**只按那一套的规矩**去看它的文件系统、目录
  约定、路径分隔与保留名限制。绝不拿本机 Linux 沙箱的 FHS 习俗去套 Windows 目标，
  也绝不反过来——这条是本模块的第一原则（回链 `winternals-fs-layout`）。
- **运行语言环境两头看**：一边是**目标**的映像格式与 ABI（PE/PE32+ 还是 ELF 还是
  Mach-O，依赖哪个 CRT、有没有 CLR），一边是**工具链自己**的语言环境（Ghidra 要 JVM、
  Volatility3 要 Python 3、dnSpyEx 要 CLR）。两头缺一，盘点结论都不成立
  （回链 `winternals-runtime-envs`）。
- **工具链只问在不在**：SDR/逆向/取证工具一律 `shutil.which` 探测路径，
  **绝不启动、绝不下载、绝不 attach**。
- **存在性即终点**：PCILeech 一类具备 DMA 写入能力的工具只回答「有没有」，
  不提供任何操作入口。

红线（比全项目更严，与 radio 同级）：本层绝不驱动任何真实的写入与注入——不改文件系统与
注册表、不 DMA 读写物理内存、不装载驱动、不注入进程、不 patch 内存、不编译不签名；
对上述工具仅登记存在性与法律边界；attack 与内核写类工具仅登记存在性。
"""

from __future__ import annotations

import os
import shutil
import sys
from typing import Dict, List, Tuple

from . import common

# --------------------------------------------------------------------------- #
# 路径与常量                                                                    #
# --------------------------------------------------------------------------- #
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PROC_MOUNTS = "/proc/mounts"

# 开源 Windows 分析·学习工具链：key → (可执行名, 说明)。仅做存在性盘点。
WINTOOLS = [
    ("ghidra", "ghidraRun", "Ghidra 反汇编/反编译（Apache-2.0，需 JVM）"),
    ("radare2", "r2", "radare2 逆向框架（LGPL 库 / GPL 工具）"),
    ("cutter", "cutter", "Cutter 图形前端（GPL，radare2 配套）"),
    ("volatility3", "vol", "Volatility 3 内存取证（GPL-2.0，Python 3）"),
    ("volatility3_py", "vol.py", "Volatility 3 脚本形态入口"),
    ("systeminformer", "SystemInformer", "System Informer 进程/句柄检视（GPL-3.0）"),
    ("x64dbg", "x64dbg", "x64dbg 用户态调试器（GPL-3.0，Windows 原生）"),
    ("dnspy", "dnspy", "dnSpyEx IL 反编译（GPL 系）"),
    ("gdb", "gdb", "GNU 调试器（支持 PE 目标，GPL）"),
    ("objdump", "objdump", "binutils 目标文件分析（支持 PE，GPL）"),
    ("upx", "upx", "UPX 壳打包/识别（GPL）"),
    ("dotnet", "dotnet", ".NET 运行时与 SDK（自 Kestrel 起 MIT/Apache 混合）"),
    ("mono", "mono", "Mono CLR 跨平台实现（MIT 系）"),
    ("wine_rt", "wine", "Wine Win32 兼容层（LGPL-2.1）"),
    ("mingw64", "x86_64-w64-mingw32-gcc", "MinGW-w64 交叉工具链（生成 PE）"),
    ("ntfsinfo", "ntfsinfo", "ntfsprogs NTFS 元数据只读查询"),
    ("tsk_fls", "fls", "The Sleuth Kit 文件系统层列举（取证）"),
    ("qemu_img", "qemu-img", "磁盘映像转换与检查（GPL）"),
    ("winpmem", "winpmem", "内存获取工具（仅登记存在性，不执行）"),
    ("pcileech", "pcileech", "PCILeech DMA 工具（AGPL-3.0，仅登记存在性）"),
]

# 目标环境所属族的候补 Windows 挂载点（宿主机非 Windows 时，只读探查是否被挂载）
_WIN_MOUNTS = ["/mnt/c", "/media/c", "/mnt/windows", "/media/Windows"]

# 各套环境的文件系统/目录/路径约定（先看 TREATY，再看本领）
TARGET_FS = {
    "windows": {
        "fs": ["NTFS（日志 / MFT / USN）", "ReFS（完整性流）", "exFAT / FAT32（移动介质）"],
        "dirs": [r"C:\Windows", r"C:\Windows\System32", r"C:\Windows\SysWOW64",
                 r"C:\Program Files", r"C:\Program Files (x86)", r"C:\ProgramData",
                 r"C:\Users"],
        "sep": "\\",
        "note": "盘符 + 反斜杠；大小写不敏感但保留大小写；System32 放原生位宽映像",
    },
    "wsl": {
        "fs": ["宿主 NTFS 经 9P / Plan 9 协议或 virtio 透传", "Linux 侧 ext4（WSL2 虚拟磁盘）"],
        "dirs": ["/etc", "/proc", "/sys", "/usr", "/var", "/mnt/c/Windows"],
        "sep": "/",
        "note": "同时可及 Windows 盘符（/mnt/c）与 Linux FHS，两套约定并存",
    },
    "linux": {
        "fs": ["ext4（日志，最常见）", "btrfs / xfs（写时复制或大文件场景）",
               "overlayfs（容器层叠）"],
        "dirs": ["/etc", "/usr", "/var", "/proc", "/sys", "/home", "/tmp"],
        "sep": "/",
        "note": "FHS 单根树，一切见挂挂载点；/proc 与 /sys 是内核的只读投影",
    },
    "macos": {
        "fs": ["APFS（快照/克隆，现代默认）", "HFS+（旧）"],
        "dirs": ["/System/Library", "/Library", "/Users", "/Applications",
                 "/private/var", "/usr"],
        "sep": "/",
        "note": "单根树但系统卷与数据卷分离（SIP 加固，只读侧影响可被读的方向）",
    },
    "android": {
        "fs": ["ext4 / f2fs（闪存友好）", "系统分区常为只读挂载"],
        "dirs": ["/system", "/vendor", "/data", "/proc", "/sdcard"],
        "sep": "/",
        "note": "分区语义与桌面 Linux 不同：/system 常为只读，/data 需权限",
    },
}

# 各目标环境的运行语言/ABI 口径
TARGET_RUNTIME = {
    "windows": ["映像：PE / PE32+（.exe / .dll / .sys）",
                "ABI：Win32 / COM / WinRT；内核侧 NT Native API（ntdll）",
                "CRT：MSVC CRT（vcruntime / ucrt）与 MinGW-w64 CRT 互不兼容",
                "托管：.NET CLR / CoreCLR / NativeAOT"],
    "wsl": ["Linux 侧：ELF + glibc，走 FHS 动态库搜索",
            "Windows 侧：PE 映像经 lxss 管理器装载（异体互操作）"],
    "linux": ["映像：ELF", "ABI：LSB / SysV / glibc 与 musl 之别",
              "运行：解释型脚本走 shebang，二进制走动态链接器"],
    "macos": ["映像：Mach-O", "ABI：dyld + Objective-C 运行时 + Cocoa 框架"],
    "android": ["映像：DEX / OAT（ART 托管为主）", "原生库：ELF + bionic libc"],
}


# --------------------------------------------------------------------------- #
# 知识库加载（consumes data/winternals_refs.json；与 radio / reverse 同范式）   #
# --------------------------------------------------------------------------- #
def _load_refs() -> List[dict]:
    """只读加载 data/winternals_refs.json 的 items；失败返回空列表（不崩）。"""
    import json
    path = os.path.join(DATA_DIR, "winternals_refs.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        return list(doc.get("items") or [])
    except Exception:  # noqa: BLE001 —— 知识库缺失不拖垮探测
        return []


REFS: List[dict] = _load_refs()

# 只读层自查项：每项回链知识库条目 key。
WINTERNALS_CHECKS: Dict[str, tuple] = {
    "target_env": ("winternals", "目标环境与宿主判定（先看是什么系统，再谈目录）",
                   ["winternals-fs-layout"]),
    "fs_layout": ("winternals", "文件系统与目录约定核验（各按各家习俗，不套一种）",
                  ["winternals-fs-layout"]),
    "runtime_env": ("winternals", "运行语言环境与工具链自身依赖核验",
                    ["winternals-runtime-envs"]),
    "toolchain": ("winternals", "开源分析工具链存在性盘点（只问在不在，不启动）",
                  ["winternals-tools-monitor", "winternals-tools-reverse",
                   "winternals-tools-forensics"]),
    "anchors": ("winternals", "Windows 内核原理可对读锚点与许可纯度",
                ["winternals-os-reactos", "winternals-os-wine",
                 "winternals-driver-samples", "winternals-internals-books",
                 "winternals-license-purity"]),
    "redline": ("winternals", "DMA 与内核写类工具红线（仅登记存在性）",
                ["winternals-redline-dma", "winternals-self-anchors"]),
}

_SELF_POSITION = (
    "本层只读诊断：绝不驱动任何真实的写入与注入——不改文件系统与注册表、不 DMA 读写"
    "物理内存、不装载驱动、不注入进程、不 patch 内存、不编译不签名、不启动任何分析目标。"
    "PCILeech 等具备写能力的工具仅登记存在性与法律边界；面向其他系统与硬件时，先判定"
    "目标所属环境再按该环境的文件系统、目录约定与运行语言标准读数，不以本机习俗臆造。"
)


def doc_list() -> List[str]:
    """知识条目清单（回链 data 层 key）。"""
    out: List[str] = []
    for ref in REFS:
        out.append(f"· [{ref.get('key', '?')}] {ref.get('name', '?')}"
                   f"（{ref.get('org', '未注明')}）")
    return out


def reference(key: str) -> dict:
    """按 key 取知识条目；无则空 dict。"""
    for ref in REFS:
        if ref.get("key") == key:
            return ref
    return {}


# --------------------------------------------------------------------------- #
# 只读探测辅助                                                                #
# --------------------------------------------------------------------------- #
def _have(cmd: str) -> bool:
    """shutil.which 命中即视为已安装（不触碰二进制本体）。"""
    return shutil.which(cmd) is not None


def _read_text(path: str, tail: int = 8000) -> str:
    """只读读文本文件；读不到返回空串（不抛）。"""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(tail)
    except OSError:
        return ""


def detect_target_env() -> str:
    """判定当前诊断机所处的目标环境，返回其中一个 key。

    windows / wsl / linux / macos / android。**先判再做**是后续一切的前提：
    不同环境的文件系统、目录根、路径分隔与保留名限制都不一样。
    """
    platform_sys = str(getattr(sys, "platform", "") or "")
    if platform_sys.startswith("win") or os.name == "nt":
        return "windows"
    # WSL：内核版本字符串里带 Microsoft / WSL 字样（只读读 /proc/version）
    ver = _read_text("/proc/version", 2000).lower()
    if "microsoft" in ver or "wsl" in ver:
        return "wsl"
    if platform_sys.startswith("darwin") or platform_sys.startswith("mac"):
        return "macos"
    # Android：/system/build.prop 存在且 /proc 存在（只读存在性）
    if os.path.isdir("/system/build.prop") or os.path.isfile("/system/build.prop"):
        return "android"
    return "linux"


def root_fs_types() -> List[str]:
    """从 /proc/mounts 只读解析本机已挂载的文件系统类型（去重排序）。"""
    raw = _read_text(PROC_MOUNTS)
    kinds: List[str] = []
    for line in raw.splitlines():
        parts = line.split()
        # /proc/mounts 的列：设备 挂载点 文件系统类型 选项 dump pass
        if len(parts) >= 3 and parts[2]:
            kinds.append(parts[2])
    uniq = sorted({k for k in kinds if k and k != "none"})
    return uniq


def _root_fs_type() -> str:
    """根『/』的文件系统类型；读不到返回空串。"""
    raw = _read_text(PROC_MOUNTS)
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1] == "/":
            return parts[2]
    return ""


def _existing_dirs(paths: List[str]) -> Tuple[List[str], List[str]]:
    """只读核验一批目录的存在性，返回 (存在, 缺失)。"""
    have, miss = [], []
    for p in paths:
        try:
            (have if os.path.isdir(p) else miss).append(p)
        except OSError:
            miss.append(p)
    return have, miss


def _windows_mount() -> str:
    """宿主机非 Windows 时，找一处被挂载进来的 Windows 系统根；无则返回空串。"""
    for base in _WIN_MOUNTS:
        for cand in (base, os.path.join(base, "Windows")):
            if os.path.isdir(cand):
                return cand
    return ""


# --------------------------------------------------------------------------- #
# 六段只读报告                                                                #
# --------------------------------------------------------------------------- #
def target_env_report() -> Tuple[bool, str]:
    """目标环境判定：先看是什么系统，再决定按谁的规矩读它的目录。"""
    lines = ["目标环境与宿主判定（跨境只读诊断的第一步）："]
    lines.append("─" * 60)
    env = detect_target_env()
    spec = TARGET_FS.get(env, {})
    label = {"windows": "Windows 原生", "wsl": "WSL（Windows 子系统）",
             "linux": "Linux", "macos": "macOS", "android": "Android"}.get(env, env)
    lines.append(f"   · 判定结果：{label}（key={env}）")
    lines.append(f"   · 路径分隔符：{spec.get('sep', '未知')}")
    lines.append(f"   · 该环境的文件系统口径：{' / '.join(spec.get('fs', [])) or '未登记'}")
    lines.append(f"   · 约定要点：{spec.get('note', '未登记')}")
    lines.append("   · 【读法】目录名会骗人——Windows 的 System32 放原生位宽映像、")
    lines.append("     SysWOW64 反而放 32 位映像；Linux 的 /proc 与 /sys 是内核投影而非磁盘文件。")
    lines.append("     不先判定环境就照抄路径，结论必然错。")
    lines.append("   · 【红线】只读存在性与类型；不改不建任何目录、不挂载卸载")
    return True, "\n".join(lines)


def fs_layout_report() -> Tuple[bool, str]:
    """文件系统与目录约定核验：按判定的目标环境，逐条核对它的标准目录。"""
    lines = ["文件系统与目录约定核验（按目标所属环境的规矩，不套一种）："]
    lines.append("─" * 60)
    env = detect_target_env()
    spec = TARGET_FS.get(env, {})
    dirs = list(spec.get("dirs") or [])

    # Windows 目标：若宿主不是 Windows，退而找挂载进来的 Windows 根
    if env == "windows":
        # 原生 Windows 直接按约定查
        pass
    else:
        mount = _windows_mount()
        if mount:
            lines.append(f"   · 检出挂载的 Windows 系统根：{mount}")
        else:
            lines.append("   · 本机未挂载 Windows 系统根（/mnt/c 等常见挂载点均无）")

    fs_kind = _root_fs_type()
    if fs_kind:
        lines.append(f"   · 本机根分区文件系统：{fs_kind}")
    kinds = root_fs_types()
    if kinds:
        lines.append(f"   · 本机已挂载文件系统种类（去重 {len(kinds)} 种）："
                     + " ".join(kinds[:12])
                     + ("…" if len(kinds) > 12 else ""))

    have, miss = _existing_dirs(dirs)
    lines.append(f"   · 该环境标准目录核验：命中 {len(have)}/{len(dirs)} 项")
    for p in have:
        lines.append(f"     ✓ {p}")
    for p in miss:
        lines.append(f"     ✗ {p}（该环境未见，或本机为其子集/容器）")
    lines.append("   · 【读法】目录命中率低不等于能力缺失——容器与精简镜像本来就少，")
    lines.append("     关键是看**这套环境的约定**是否被遵循，而不是拿另一套去套。")
    lines.append("   · 【红线】只读目录列表与 /proc/mounts；不建目录、不改权限、不挂载")
    return bool(dirs), "\n".join(lines)


def runtime_env_report() -> Tuple[bool, str]:
    """运行语言环境核验：目标的映像格式与 ABI，加上工具链自身的语言依赖。"""
    lines = ["运行语言环境与运行时依赖核验（两头都要看）："]
    lines.append("─" * 60)
    env = detect_target_env()
    for ln in TARGET_RUNTIME.get(env, []):
        lines.append(f"   · {ln}")

    lines.append("─" * 60)
    lines.append("   · 工具链自身的语言环境（决定 Ghidra / Volatility3 这类能否实际跑起来）：")
    own = [("JVM（Ghidra 需要）", "java"), ("Python 3（Volatility3 需要）", "python3"),
           ("CLR（dnSpyEx / 托管目标需要）", "dotnet"),
           ("交叉编译器（本机生成 PE 目标）", "x86_64-w64-mingw32-gcc")]
    hit = 0
    for desc, cmd in own:
        ok = _have(cmd)
        hit += 1 if ok else 0
        lines.append(f"     {'✓' if ok else '✗'} {cmd:<26} {desc}")
    lines.append(f"   · 语言环境命中 {hit}/{len(own)} 项")
    lines.append("   · 【读法】目标侧看 ABI（PE 还是 ELF、哪个 CRT、有没有 CLR），")
    lines.append("     工具侧看自己够不够——Ghidra 装了但没 JVM 一样跑不起来。")
    lines.append("   · 【红线】只探测路径存在性；不安装任何运行时、不改 JAVA_HOME/PYTHONPATH")
    return True, "\n".join(lines)


def toolchain_report() -> Tuple[bool, str]:
    """开源 Windows 分析工具链存在性盘点（只问在不在，绝不启动任何一个）。"""
    lines = ["开源 Windows 分析工具链存在性盘点（只 which，绝不启动）："]
    lines.append("─" * 60)
    present = [(k, c, d) for k, c, d in WINTOOLS if _have(c)]
    for k, c, d in WINTOOLS:
        mark = "✓" if _have(c) else "✗"
        lines.append(f"   · {mark} {c:<26} {d}")
    lines.append("─" * 60)
    lines.append(f"   · 命中 {len(present)}/{len(WINTOOLS)} 项")
    lines.append("   · 【读法】有反编译器没有调试器 = 只能做静态；有 Volatility3 却缺")
    lines.append("     符号表 = 只能枚举不能还原结构；PCILeech 存在不代表可以用——")
    lines.append("     那是双重用途工具，合法与否取决于授权而非工具本身。")
    lines.append("   · 【红线】只登记存在性与许可边界；不下载、不调用、不 attach、不 DMA")
    return bool(present), "\n".join(lines)


def internals_anchors_report() -> Tuple[bool, str]:
    """Windows 内核原理可对读锚点 + 许可纯度（引用知识层官方源）。"""
    lines = ["Windows 内核原理可对读锚点与许可纯度（官方源登记；只读引用）："]
    lines.append("─" * 60)
    if not REFS:
        lines.append("   · 知识库未加载（data/winternals_refs.json 缺失）")
        return False, "\n".join(lines)
    for ln in doc_list():
        lines.append("   " + ln)
    lines.append("─" * 60)
    lines.append("   · 三条可对读路径：")
    lines.append("     ① ReactOS 源码树读 NT 内核的实现（GPL-2.0-or-later，只读参考）")
    lines.append("     ② Wine 源码看 Win32 API 如何落到 POSIX（LGPL-2.1）")
    lines.append("     ③ Windows Driver Samples 的 MIT 示例读内核态写法")
    lines.append("   · 许可纯度：本仓取向 MIT / Apache-2.0 优先；GPL 与 AGPL 系工具")
    lines.append("     （System Informer / MemProcFS / x64dbg / dnSpyEx / PCILeech）")
    lines.append("     只登记不吸收；非开源体（Sysinternals / WinDbg）仅作能力对照。")
    lines.append("   · 【诚实边界】各项目许可以其仓库 LICENSE 文件为准；是否构成派生")
    lines.append("     作品或传达因司法辖区而异，本工具不下法律结论。")
    return True, "\n".join(lines)


def winternals_report() -> Tuple[bool, str]:
    """开源 Windows 分析学习应用整体只读诊断。返回 (ok, 文本)。"""
    blocks = ["开源 Windows 分析学习应用诊断（目标环境·文件系统·运行时·工具链，全部只读）",
              "════════════════════════════════════════════"]
    any_ok = False
    for title, fn in REPORTS:
        ok, msg = fn()
        blocks.append(f"【{title}】{'✓ 已检测' if ok else '✗ 本机无/未装'}")
        blocks.append(msg)
        any_ok = any_ok or ok
    blocks.append("════════════════════════════════════════════")
    blocks.append(_SELF_POSITION)
    return (any_ok, "\n".join(blocks))


REPORTS = [
    ("目标环境判定", target_env_report),
    ("文件系统与目录约定", fs_layout_report),
    ("运行语言环境", runtime_env_report),
    ("分析工具链存在性", toolchain_report),
    ("内核锚点与许可纯度", internals_anchors_report),
]


def capabilities_report() -> Tuple[bool, str]:
    """能力自检（只读）：本机可诊断哪些维度 + 红线。"""
    lines = ["开源 Windows 分析学习应用只读诊断能力自检："]
    for title, fn in REPORTS:
        try:
            ok, _ = fn()
            lines.append(f"   · {title:<18} {'可诊断(本机有)' if ok else '可诊断(本机无/未装)'}")
        except Exception:  # noqa: BLE001
            lines.append(f"   · {title:<18} 诊断异常")
    lines.append(f"   · 知识条目回链：{len(REFS)} 条（winternals_refs.json）")
    lines.append(_SELF_POSITION)
    return True, "\n".join(lines)
