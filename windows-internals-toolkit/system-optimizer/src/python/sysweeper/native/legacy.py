"""遗留 / 嵌入式 / 兼容层只读诊断（v0.6.21「导入分析学习应用」）。

把「DOS 3.1 等遗留 DOS 环境」「busybox 嵌入式用户态」「dosbox DOS 模拟兼容层」
三件东西，按本工具的**只读诊断**口径结构化地摸一遍，并**嵌入整体系统**——
通过 sysmap 关联图与 livemedia / openwrt / proton / wsl 等既有模块产生「你中有我」关系。

技术坐标（仅把「该看什么」钉死，绝不执行写/运行）：

· DOS 3.1 等（遗留 DOS 环境）
  - MS-DOS 3.1（1984/85，x86 实模式，FAT12 软盘 360KB/1.2MB，COM/EXE，
    CONFIG.SYS / AUTOEXEC.BAT，HIMEM.SYS / EMM386.EXE，INT 21h/10h/13h/16h）。
  - 现代开源替代 FreeDOS 1.4（2025-04，Jim Hall 发起，MS-DOS 兼容）。
  - 在 Linux 上跑 DOS 的另一路径：DOSEMU2（DPMI 虚拟机，非模拟而是近原生）。
  - 与 livemedia 关联：制作 DOS 启动软盘需 mtools + syslinux + FreeDOS 基础文件，
    复用 livemedia 已覆盖的 ISO/软盘工具链知识。

· busybox（嵌入式用户态「瑞士军刀」）
  - 单文件多调用二进制，把 ls/cp/cat/mount/ps 等浓缩进一个可执行；广泛用于
    嵌入式路由器（OpenWrt 即以 busybox 为根用户态）、安装器 initrd/initramfs、
    Docker 极简镜像。
  - 与 openwrt 关联：OpenWrt 的根用户态就是 busybox；与 livemedia 关联：
    多数发行版 live ISO 的 initramfs 也靠 busybox 提供早期用户态。

· dosbox（DOS 模拟兼容层）
  - SDL 实现的 x86 实模式模拟器，把 8086/286/386 动态重编译，在现 OS 上跑老 DOS
    游戏/程序；CPU core（simple/normal/dynamic/auto）、cycles、mount C: 是核心概念。
  - 衍生：Em-DOSBox（Emscripten → 浏览器）、DOSBox-X（更准、支持 Win9x）、DBGL 前端。
  - 与 proton 关联：二者都是「在现系统上跑旧/异平台软件」的兼容层；与 wsl 关联：
    都是把旧运行环境搬到现系统的桥。

吸收「利用现有资源和连接器尽量全选」原则：本模块复用 common.run / shutil.which
等既有只读资源，并在关联图里尽量挂接既有连接器（openwrt / proton / wsl / livemedia /
thirdparty 的 CDN·P2P 开关 aria2——合法 DOS 镜像取回可走该开关，仅限本人有权获取的资源）。

红线（与全项目一致，且本层更严）：仅读——不写 DOS 镜像、不 dd、不运行 DOS/DOSEMU/
DOSBox 任何程序、不挂载/解包任何镜像、不装包、不连校外网做写。版本/安装查询只取
命令首行或只读元数据。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from typing import Dict, List, Tuple

from . import common

# --------------------------------------------------------------------------- #
# 路径与常量                                                                    #
# --------------------------------------------------------------------------- #
FREEDOS_DIRS = ("/usr/share/freedos", "/usr/lib/freedos", "/usr/share/seabios")
OPENWRT_RELEASE = "/etc/openwrt_release"
DOCKER_ENV = "/.dockerenv"
DOSBOX_HOME = os.path.expanduser("~/.dosbox")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


# --------------------------------------------------------------------------- #
# 知识库加载（v0.6.74：dos/busybox/dosbox 三个 data 层由本模块消费）              #
# --------------------------------------------------------------------------- #
def _load_refs(filename: str) -> List[dict]:
    """只读加载 data/<filename>.json 的 items；失败返回空列表（不崩）。"""
    path = os.path.join(DATA_DIR, f"{filename}.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        return list(doc.get("items") or [])
    except Exception:  # noqa: BLE001 —— 知识库缺失不拖垮探测
        return []


def _load_compat_refs(topics: Tuple[str, ...]) -> List[dict]:
    """从 compat_docs.json 取位宽/PAE 两个主题，补齐 key 字段后按 item 形态返回。"""
    path = os.path.join(DATA_DIR, "compat_docs.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except Exception:  # noqa: BLE001
        return []
    out: List[dict] = []
    for topic in topics:
        entry = doc.get(topic)
        if isinstance(entry, dict) and entry.get("name"):
            item = dict(entry)
            item.setdefault("key", topic)
            item.setdefault("evidence_status", "official_verified")
            out.append(item)
    return out


DOS_REFS: List[dict] = _load_refs("dos")
BUSYBOX_REFS: List[dict] = _load_refs("busybox")
DOSBOX_REFS: List[dict] = _load_refs("dosbox")
COMPAT_REFS: List[dict] = _load_compat_refs(("bitwidth", "pae"))
LEGACY_REFS: List[dict] = DOS_REFS + BUSYBOX_REFS + DOSBOX_REFS + COMPAT_REFS

# 只读层自查项：每项回链知识库条目 key（与 reverse/hmosstd 同范式）。
LEGACY_CHECKS: Dict[str, tuple] = {
    "dos_env": ("dos", "遗留 DOS 环境只读诊断（FreeDOS/DOSEMU2/启动盘前提）",
                ["msdos-3.1-coordinate", "freedos-1.4", "dosemu2",
                 "dos-boot-media", "dos-era-apis"]),
    "busybox_env": ("busybox", "busybox 嵌入式用户态只读诊断",
                    ["busybox-overview", "busybox-applets",
                     "busybox-embed-contexts", "busybox-version-line"]),
    "dosbox_env": ("dosbox", "dosbox DOS 模拟兼容层只读诊断",
                   ["dosbox-core", "dosbox-derived", "dosbox-limits"]),
    "bitwidth_cap": ("bitwidth", "8/16/32 位元能力矩阵诊断",
                     ["bitwidth"]),
    "pae_support": ("pae", "PAE 现状检测与开启指引（只给命令文本，不代改）",
                    ["pae"]),
}

_SELF_POSITION = (
    "本层只读诊断：不写 DOS 镜像、不 dd、不启动 DOS/DOSEMU/DOSBox/QEMU/Wine、"
    "不挂载/解包镜像、不装包、不连校外网做写、不修改任何引导配置（boot.ini/bcdedit/内核命令行）"
    "——PAE 与位宽只检测现状与给出官方命令文本，执行与否由用户决定。"
)


def doc_list() -> List[str]:
    """知识条目清单（回链 data 层 key）。"""
    out: List[str] = []
    for ref in LEGACY_REFS:
        out.append(f"· [{ref.get('key', '?')}] {ref.get('name', '?')}"
                   f"（{ref.get('org', '未注明')}）")
    return out


def reference(key: str) -> dict:
    """按 key 取知识条目；无则空 dict。"""
    for ref in LEGACY_REFS:
        if ref.get("key") == key:
            return ref
    return {}


# --------------------------------------------------------------------------- #
# 工具存在性辅助                                                                #
# --------------------------------------------------------------------------- #
def _have(cmd: str) -> bool:
    """shutil.which 命中即视为已安装（不触碰二进制本体）。"""
    return shutil.which(cmd) is not None


def _pkg_query(pkg_glob: str) -> List[str]:
    """只读查询已装包（dpkg / rpm），返回匹配包名列表；无则空。"""
    hits: List[str] = []
    if shutil.which("dpkg"):
        rc, out = common.run(f"dpkg -l 2>/dev/null | grep -i '{pkg_glob}'")
        if rc == 0:
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[0].startswith("ii"):
                    hits.append(parts[1])
    elif shutil.which("rpm"):
        rc, out = common.run(f"rpm -qa 2>/dev/null | grep -i '{pkg_glob}'")
        if rc == 0:
            hits.extend(l.strip() for l in out.splitlines() if l.strip())
    return hits


def _ver_safe(cmd: str) -> str:
    """取版本命令首行；失败返回空串（绝不因命令缺失而崩）。"""
    if not _have(cmd.split()[0]):
        return ""
    rc, out = common.run(cmd + " 2>/dev/null | head -3")
    if rc == 0 and out.strip():
        return out.strip().splitlines()[0]
    return ""


# --------------------------------------------------------------------------- #
# DOS 3.1 等 · 遗留 DOS 环境                                                    #
# --------------------------------------------------------------------------- #
def dos_report() -> Tuple[bool, str]:
    """遗留 DOS 环境只读诊断（FreeDOS / MS-DOS 基础 / DOSEMU2；DOS 3.1 为知识坐标）。"""
    lines = ["遗留 DOS 环境（只读；DOS 3.1 为坐标，FreeDOS/DOSEMU2 为现路径）："]
    lines.append("─" * 60)
    present: List[str] = []

    # 1) FreeDOS（开源 MS-DOS 替代）
    freedos_pkgs = _pkg_query("freedos")
    freedos_dir = next((d for d in FREEDOS_DIRS if os.path.isdir(d)), None)
    if _have("freedos") or freedos_pkgs or freedos_dir:
        bits = []
        if _have("freedos"):
            bits.append("freedos 命令在 PATH")
        if freedos_pkgs:
            bits.append("包：" + ", ".join(freedos_pkgs[:4]))
        if freedos_dir:
            bits.append(f"基础文件 {freedos_dir}")
        lines.append(f"   · FreeDOS（开源 MS-DOS 替代）：存在（{'；'.join(bits)}）✓")
        present.append("FreeDOS")
    else:
        lines.append("   · FreeDOS：未检测到（apt: freedos / 手工放基础文件；"
                     "packer 镜像见 osdev 社区）")

    # 2) DOSEMU2（Linux 上近原生跑 DOS，非模拟）
    if _have("dosemu") or _have("dosemu2") or _pkg_query("dosemu"):
        lines.append("   · DOSEMU2（Linux 近原生 DOS 虚拟机，DPMI）：存在 ✓")
        present.append("DOSEMU2")
    else:
        lines.append("   · DOSEMU2：未检测到（apt: dosemu2；在现 Linux 上跑实模式 DOS 的近原生路径）")

    # 3) 制作 DOS 启动盘能力（复用 livemedia 工具链知识）
    mk = _have("mtools") and _have("syslinux")
    lines.append(f"   · 制作 DOS 启动软盘前提：mtools={'✓' if _have('mtools') else '✗'} "
                 f"/ syslinux={'✓' if _have('syslinux') else '✗'}"
                 f"{'（齐备，可制 DOS 启动盘）' if mk else '（缺则不可直接制启动盘）'}")

    # 4) 知识坐标
    lines.append("─" * 60)
    lines.append("   【知识坐标】MS-DOS 3.1（1984/85）：x86 实模式 · FAT12 软盘 "
                 "360KB/1.2MB · COM/EXE · CONFIG.SYS/AUTOEXEC.BAT · HIMEM/EMM386 · "
                 "INT 21h(系统)/10h(视频)/13h(磁盘)/16h(键盘)。")
    lines.append("   【现替代】FreeDOS 1.4（2025-04）兼容 MS-DOS；DOSEMU2 在 Linux 近原生运行。")
    lines.append("   【关联】与 livemedia（可启动介质）共生：DOS 启动盘复用其 mtools/syslinux 工具链。")
    lines.append("   【取回】合法 DOS 镜像如需下载，可走第三方 CDN·P2P 开关 aria2（见 thirdparty 引用），"
                 "仅限本人有权获取的资源。")
    ok = bool(present) or mk
    return (ok, "\n".join(lines))


# --------------------------------------------------------------------------- #
# busybox · 嵌入式用户态                                                        #
# --------------------------------------------------------------------------- #
def busybox_report() -> Tuple[bool, str]:
    """busybox 只读诊断（版本 / applet 数 / 嵌入式上下文：OpenWrt·initrd·容器）。"""
    lines = ["busybox 嵌入式用户态（只读「瑞士军刀」多调用二进制）："]
    lines.append("─" * 60)
    if not _have("busybox"):
        lines.append("   · busybox：未安装（嵌入式/路由器/容器常见；OpenWrt 以此为根用户态）")
        lines.append("   【关联】OpenWrt 模块若探测到路由器系统，其根用户态即 busybox；"
                     "livemedia 的 initramfs 亦常含 busybox 早期用户态。")
        return (False, "\n".join(lines))

    ver = _ver_safe("busybox")
    lines.append(f"   · busybox 版本：{ver or '（已装，取版本失败）'} ✓")

    # applet 数量
    rc, out = common.run("busybox --list 2>/dev/null | wc -l")
    n_applets = out.strip() if (rc == 0 and out.strip()) else ""
    if n_applets and n_applets.isdigit():
        lines.append(f"   · 内置 applet 数：{n_applets}（ls/cp/cat/mount/ps 等浓缩于单文件）")

    # 嵌入式上下文判定
    ctx: List[str] = []
    if os.path.exists(OPENWRT_RELEASE) or _have("ubus"):
        ctx.append("OpenWrt 路由器系统（busybox 即其根用户态）")
    if os.path.exists(DOCKER_ENV):
        ctx.append("Docker 容器（极简镜像常以 busybox 为根）")
    # initrd/initramfs：/bin 或 /sbin 是 busybox 的软链
    for p in ("/bin/busybox", "/sbin/busybox"):
        if os.path.islink(p):
            ctx.append(f"{p} 为 busybox 软链（initramfs/嵌入式根）")
            break
    if ctx:
        lines.append("   · 嵌入式上下文：" + "；".join(ctx))
    else:
        lines.append("   · 嵌入式上下文：常规发行版上的独立 busybox（非系统根用户态）")

    lines.append("─" * 60)
    lines.append("   【关联】busybox ↔ OpenWrt（路由器根用户态）· ↔ livemedia（initramfs 早期用户态）"
                 "· ↔ 容器（极简镜像）；均为「单二进制撑起整套工具」的同一思路。")
    return (True, "\n".join(lines))


# --------------------------------------------------------------------------- #
# dosbox · DOS 模拟兼容层                                                       #
# --------------------------------------------------------------------------- #
def dosbox_report() -> Tuple[bool, str]:
    """dosbox 只读诊断（版本 / 配置 / 核心概念：core·cycles·mount）。"""
    lines = ["dosbox DOS 模拟兼容层（只读；在现 OS 上跑老 DOS 软件）："]
    lines.append("─" * 60)
    if not _have("dosbox"):
        lines.append("   · dosbox：未安装（apt: dosbox / pacman: dosbox；跑 DOS 游戏/程序）")
        lines.append("   【衍生】Em-DOSBox（浏览器/Emscripten）· DOSBox-X（更准、Win9x）· DBGL 前端。")
        lines.append("   【关联】与 proton 同属「在现系统跑旧/异平台软件」兼容层；与 wsl 同属旧环境迁移桥。")
        return (False, "\n".join(lines))

    ver = _ver_safe("dosbox --version")
    lines.append(f"   · dosbox 版本：{ver or '（已装，取版本失败）'} ✓")

    # 配置
    cfgs: List[str] = []
    if os.path.isdir(DOSBOX_HOME):
        try:
            cfgs = [f for f in os.listdir(DOSBOX_HOME) if f.endswith(".conf")]
        except OSError:
            pass
    if os.path.exists("/etc/dosbox.conf"):
        cfgs.append("/etc/dosbox.conf")
    if cfgs:
        lines.append(f"   · 配置：{', '.join(cfgs[:4])}")
    else:
        lines.append("   · 配置：未发现（默认无 ~/.dosbox/*.conf，首次运行自动生成）")

    # 核心概念
    lines.append("─" * 60)
    lines.append("   【核心概念】CPU core（simple/normal/dynamic/auto）· cycles（fixed/max 调速）· "
                 "mount C <dir>（把宿主机目录挂成 DOS 的 C:）· SDL 音频/视频。")
    lines.append("   【关联】dosbox ↔ proton（兼容层）· ↔ wsl（旧环境迁移桥）；"
                 "合法 DOS 镜像取回可走第三方 CDN·P2P 开关 aria2（见 thirdparty），仅限本人有权获取的资源。")
    lines.append("   【红线】本工具只诊断不运行：绝不启动 dosbox、不挂任何目录、不跑任何 DOS 程序。")
    return (True, "\n".join(lines))


# --------------------------------------------------------------------------- #
# 位宽世代 · 8/16/32/64 位元能力矩阵（v0.6.74）                                  #
# --------------------------------------------------------------------------- #
def _cpuinfo() -> Dict[str, str]:
    """读 /proc/cpuinfo 首个处理器段 → 字典（非 Linux 或缺失返回空）。"""
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8") as fh:
            block: Dict[str, str] = {}
            for line in fh:
                if not line.strip():
                    if block:
                        return block
                    continue
                if ":" in line:
                    k, _, v = line.partition(":")
                    block.setdefault(k.strip(), v.strip())
            return block
    except OSError:
        return {}


def _kernel_bits() -> Tuple[str, str]:
    """返回 (机器三元组, 位宽描述)：x86_64/aarch64→64 位；i386/i686→32 位。"""
    machine = os.uname().machine
    if machine in ("x86_64", "amd64", "aarch64", "arm64", "ppc64le", "s390x", "riscv64"):
        return machine, "64 位"
    if machine in ("i386", "i486", "i586", "i686", "x86"):
        return machine, "32 位"
    return machine, "未知"


def bitwidth_report() -> Tuple[bool, str]:
    """位宽世代能力矩阵（只读）：8/16/32/64 位 × 直接运行/模拟层覆盖。"""
    lines = ["位宽世代能力矩阵（只读盘点；不启动任何模拟器）："]
    lines.append("─" * 60)
    machine, kbits = _kernel_bits()
    cpu = _cpuinfo()
    flags = set((cpu.get("flags") or "").split())
    lm = "lm" in flags                       # long mode（64 位长模式）CPU 能力

    # 模拟层存在性（只问在不在 PATH，不启动）
    emu = {
        "qemu-i386": _have("qemu-system-i386"),
        "qemu-x86_64": _have("qemu-system-x86_64"),
        "dosbox": _have("dosbox"),
        "dosemu2": _have("dosemu2") or _have("dosemu"),
        "wine": _have("wine") or _have("wine64"),
        "wine32": _have("wine") and not lm,  # 仅 32 位内核上 wine 可能带 32 位 WoW 缺位
        "mame": _have("mame"),
        "fceux": _have("fceux"),
    }
    lines.append(f"   · 内核：{machine}（{kbits}）"
                 + ("；CPU 带 lm 标志（支持 64 位长模式）" if lm else "；未见 lm 标志"))
    lines.append(f"   · 用户态解释器：{sys.version.split()[0]}"
                 f"（{'64 位' if sys.maxsize > 2**32 else '32 位'}）")

    rows = [
        ("8 位世代", "8080/Z80/6502/6809",
         "本机无直接路径；专用模拟器：MAME=" + ("✓" if emu["mame"] else "✗")
         + " FCEU=" + ("✓" if emu["fceux"] else "✗")),
        ("16 位实模式", "8086/286 · DOS 实模式",
         "dosbox=" + ("✓" if emu["dosbox"] else "✗")
         + " / DOSEMU2=" + ("✓" if emu["dosemu2"] else "✗")
         + "（模拟层覆盖，非原生）"),
        ("32 位保护模式", "80386+ · Win32/PE32/DPMI",
         "qemu-i386=" + ("✓" if emu["qemu-i386"] else "✗")
         + " / wine=" + ("✓" if emu["wine"] else "✗")
         + (f"；本机内核即 {kbits} 用户态" if kbits == "32 位" else "；本机为 64 位（WoW/陪衬另计）")),
        ("32 位+PAE", ">4GB 物理寻址/DEP",
         "CPU pae 标志=" + ("✓" if "pae" in flags else "✗")
         + "；详见 pae_report（检测不代改）"),
        ("64 位长模式", "x86-64/arm64 原生",
         "CPU lm 标志=" + ("✓" if lm else "✗")
         + f"；本机内核 {kbits}" + ("（原生全寻址）" if kbits == "64 位" else "（CPU 支持但内核未用）")),
    ]
    for name, era, how in rows:
        lines.append(f"   · {name:<8}（{era}）：{how}")
    lines.append("─" * 60)
    lines.append("   【读法】直接运行 = 本机原生；模拟层覆盖 = 靠 dosbox/qemu/wine 这一层翻译，"
                 "性能与兼容各让一步。位宽是能力分档，不是「新=旧」的优劣判词。")
    lines.append("   【红线】只探测存在性；绝不启动任何模拟器、不下载镜像。")
    ready = any(emu.values())
    return (ready, "\n".join(lines))


# --------------------------------------------------------------------------- #
# PAE · 物理地址扩展（v0.6.74；只读检测 + 官方命令文本，绝不代改）                 #
# --------------------------------------------------------------------------- #
def pae_report() -> Tuple[bool, str]:
    """PAE 现状只读检测与开启指引。Linux 实测；Windows（XP/Vista/7）给官方命令文本。"""
    lines = ["PAE（物理地址扩展）现状与开启指引（只读检测；改动引导配置由你决定）："]
    lines.append("─" * 60)
    cpu = _cpuinfo()
    flags = set((cpu.get("flags") or "").split())
    machine, kbits = _kernel_bits()
    mem_total_kb = 0
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("MemTotal:"):
                    mem_total_kb = int(line.split()[1])
                    break
    except (OSError, ValueError, IndexError):
        pass
    mem_gb = mem_total_kb / 1048576 if mem_total_kb else 0.0

    pae_cpu = "pae" in flags
    lines.append(f"   · 本机：{machine}（{kbits} 内核）· CPU pae 标志="
                 + ("✓（Pentium Pro 起的 x86 即带）" if pae_cpu else "✗/不适用（非 x86 或读不到）"))
    if mem_gb:
        lines.append(f"   · 物理内存：约 {mem_gb:.1f} GB"
                     + ("（>4GB：32 位内核若无 PAE/HIGHMEM 只能用前 4GB）"
                        if mem_gb > 4.0 and kbits == "32 位" else ""))
    lines.append("─" * 60)
    if kbits == "64 位":
        lines.append("   【结论】64 位内核原生全寻址，不需要也不支持 PAE——本机即此类。")
        ok = True
    elif kbits == "32 位" and machine in ("i386", "i486", "i586", "i686", "x86"):
        lines.append("   【结论】32 位 x86 内核：CPU 支持 PAE 是前提；内核是否启用需自查：")
        lines.append("     grep -iE 'HIGHMEM|X86_PAE' /boot/config-$(uname -r) 2>/dev/null")
        lines.append("   【开启（Linux 32 位）】发行版装 -pae/`kernel-$ver-pae` 变体，或自编")
        lines.append("     选 HIGHMEM64G（Kconfig：选中后 select X86_PAE；PAE 同时是 32 位内核")
        lines.append("     NX/DEP 的前提，代价是页表查找开销与每进程页表占用变大）。")
        lines.append("   【命令仅示意】apt install linux-image-*-pae    # Debian/Ubuntu 历史口径")
        ok = pae_cpu
    else:
        lines.append("   【结论】非 x86 或位宽未知：PAE 为 x86-32 特性，此处不适用。")
        ok = False
    lines.append("─" * 60)
    lines.append("   【Windows 32 位口径（官方来源；本机为 Linux 沙箱未实测）】")
    lines.append("     · XP / Server 2003：boot.ini 对应条目加 /PAE（/NOPAE 禁用）后重启；")
    lines.append("       DEP 启用（硬件支持或 /NOEXECUTE）时 PAE 自动开启。")
    lines.append("     · Vista / Win7 32 位：bcdedit /set {当前项} pae ForceEnable；")
    lines.append("       禁用需同时 bcdedit /set nx AlwaysOff + /set pae ForceDisable。")
    lines.append("     · 诚实边界（微软官方）：XP 全版本物理地址空间上限即 4GB——开 PAE 的")
    lines.append("       意义是硬件 DEP/NX 与热插拔内存，不是突破 4GB；进程虚拟地址空间不变。")
    lines.append("   【红线】只读检测 + 给命令文本；不代改 boot.ini/bcdedit/内核命令行。")
    return (ok, "\n".join(lines))


# --------------------------------------------------------------------------- #
# 聚合报告 + 能力自检                                                           #
# --------------------------------------------------------------------------- #
def legacy_report() -> Tuple[bool, str]:
    """遗留/嵌入式/兼容层整体只读诊断。返回 (ok, 文本)。"""
    blocks = ["遗留 / 嵌入式 / 兼容层诊断（DOS 3.1 等 · busybox · dosbox · 位宽 · PAE，全部只读）",
              "════════════════════════════════════════════"]
    checks = [
        ("遗留 DOS 环境", dos_report),
        ("busybox 嵌入式用户态", busybox_report),
        ("dosbox DOS 模拟兼容层", dosbox_report),
        ("位宽世代能力矩阵", bitwidth_report),
        ("PAE 现状与开启指引", pae_report),
    ]
    any_ok = False
    for title, fn in checks:
        ok, msg = fn()
        blocks.append(f"【{title}】{'✓ 已检测' if ok else '✗ 本机无/未装'}")
        blocks.append(msg)
        any_ok = any_ok or ok
    blocks.append("════════════════════════════════════════════")
    blocks.append("结论：已把「旧/嵌入式/兼容」与「位宽/PAE」纳入整体系统的只读诊断；"
                 "嵌入方式见 sysmap 关联图（busybox↔OpenWrt、dosbox↔Proton、"
                 "DOS↔livemedia、位宽/PAE↔compat·reverse）。")
    blocks.append("红线：本工具仅读——不写 DOS 镜像、不 dd、不运行 DOS/DOSEMU/DOSBox/QEMU/Wine、"
                 "不挂载/解包镜像、不装包、不连校外网做写、不代改任何引导配置。")
    return (any_ok, "\n".join(blocks))


def capabilities_report() -> Tuple[bool, str]:
    """能力自检（只读）：本机可诊断哪些遗留/嵌入式/兼容维度 + 红线。"""
    lines = ["遗留/嵌入式/兼容层诊断能力自检（只读）："]
    for title, fn in [("遗留 DOS 环境", dos_report),
                      ("busybox 嵌入式用户态", busybox_report),
                      ("dosbox DOS 模拟兼容层", dosbox_report),
                      ("位宽世代能力矩阵", bitwidth_report),
                      ("PAE 现状与开启指引", pae_report)]:
        try:
            ok, _ = fn()
            lines.append(f"   · {title:<18} {'可诊断(本机有)' if ok else '可诊断(本机无/未装)'}")
        except Exception:  # noqa: BLE001
            lines.append(f"   · {title:<18} 诊断异常")
    lines.append(f"   · 知识条目回链：{len(LEGACY_REFS)} 条（dos/busybox/dosbox 三库 + compat 位宽/PAE）")
    lines.append("红线：仅读 which/版本首行/包管理只读查询/目录存在性/cpuinfo·meminfo 只读；"
                 "不运行任何 DOS/模拟器、不写镜像、不连校外网做写、不代改引导配置。")
    return True, "\n".join(lines)
