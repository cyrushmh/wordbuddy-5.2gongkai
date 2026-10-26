"""CPU 架构 / 指令集（ISA）原生接口层。

以「系统本身提供的接口」探测架构，并对照 data/arch.json 给出标准出处与建议。
覆盖的架构（含用户补充的龙芯与 MIPS，以及开源硬件相关开放架构）：

- loongarch : 龙芯 LoongArch（国产自主指令集，龙芯中科）
- mips      : MIPS32 / MIPS64（Release 6；含龙芯早期 Godson 与嵌入式设备）
- riscv     : RISC-V（开源指令集，RISC-V International，RVA20/22/23 profiles）
- openpower : Power ISA（OpenPOWER Foundation 开放，含 Microwatt 开源核）
- openrisc  : OpenRISC（OpenCores 开源处理器核）
- x86       : x86 / x86-64（Intel/AMD；国产兆芯、海光同属此架构）
- arm       : ARM / AArch64（Arm；国产飞腾、鲲鹏基于 ARM 授权）
- open_hardware : 开源硬件认证与许可（OSHWA / CERN OHL / DIN SPEC 3105 / CHIPS Alliance）

探测接口（原生、跨平台）
------------------------
    uname -m                : POSIX 机器硬件名（龙芯 loongarch64、MIPS mips64el…）
    /proc/cpuinfo           : Linux 的 CPU 型号、ISA 扩展（RISC-V 的 isa 行）
    sysctl hw.machine       : BSD / macOS 的机器架构
    %PROCESSOR_ARCHITECTURE%: Windows 环境变量（AMD64 / ARM64 / x86）

设计原则与其余 native 模块一致：纯标准库、零依赖、惰性守卫——
工具/文件不存在就返回空或 (False, 说明)，由上层降级为「指引」，绝不抛异常。
"""

from __future__ import annotations

import json
import os
import platform as _plat
import re

from . import common


# ------------------------------------------------------------ 数据加载


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath("arch.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:
        return {}


REFS = _load_refs()


def reference(arch_key: str) -> dict:
    """返回某架构的标准参考（name/standard/org/summary/standards…）。"""
    return REFS.get(arch_key, {})


def reference_all() -> dict:
    """返回全部架构标准参考（供 arch 命令列出）。"""
    return REFS


def all_arch_keys() -> list:
    """全部已收录的架构键（按 data/arch.json 顺序）。"""
    return list(REFS.keys())


# ------------------------------------------------------------ 原生探测


def machine() -> str:
    """返回 uname -m 的机器名（Windows 用环境变量兜底）。"""
    m = _plat.machine() or ""
    if m:
        return m
    return os.environ.get("PROCESSOR_ARCHITECTURE", "") or ""


def cpuinfo() -> str:
    """读 /proc/cpuinfo 全文（不存在返回空串）。"""
    p = "/proc/cpuinfo"
    if not os.path.exists(p):
        return ""
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def cpuinfo_field(field: str) -> str:
    """从 /proc/cpuinfo 取某个字段的首个值（取不到返回空串）。"""
    txt = cpuinfo()
    if not txt:
        return ""
    m = re.search(rf"^{re.escape(field)}\s*:\s*(.+)$", txt, re.M | re.I)
    return m.group(1).strip() if m else ""


def sysctl_machine() -> str:
    """BSD / macOS：sysctl hw.machine（拿不到返回空串）。"""
    import sys
    if sys.platform in ("darwin", "freebsd", "openbsd", "netbsd", "dragonfly"):
        from . import macos
        v = macos.sysctl("hw.machine")
        if v:
            return v
    return ""


def detect_arch_key(m: str = None) -> str:
    """把机器名/CPU 信息归一化成 data/arch.json 的架构键。

    先按 uname -m 精确匹配 uname_machines；匹配不到再用 /proc/cpuinfo 关键词兜底
    （例如某些发行版 machine 仍是 mips64 但 cpuinfo 标 Loongson）。
    """
    m = (m or machine() or "").strip().lower()
    info = cpuinfo()
    for key, ref in REFS.items():
        for um in ref.get("uname_machines", []):
            if m == um.lower():
                return key
    # cpuinfo 关键词兜底（龙芯在过渡期常以 MIPS 兼容模式报出）
    if info:
        for key, ref in REFS.items():
            for kw in ref.get("cpuinfo_keys", []):
                if re.search(re.escape(kw.strip()), info, re.I):
                    # 龙芯关键词优先于 mips（Loongson 早期基于 MIPS，但应识别为龙芯）
                    if key == "loongarch":
                        return key
                    return key
    return "unknown"


def is_arch(arch_key: str) -> bool:
    """当前是否运行在某架构上。"""
    return detect_arch_key() == arch_key


def endianness() -> str:
    """探测字节序（大端/小端）；拿不到返回空串。"""
    import sys as _sys
    b = _sys.byteorder
    return "小端 (little-endian)" if b == "little" else "大端 (big-endian)"


def arch_details(arch_key: str = None) -> dict:
    """返回某架构（默认当前）的探测详情：机器名、CPU 型号、字节序、ISA 扩展。"""
    key = arch_key or detect_arch_key()
    info = {
        "arch_key": key,
        "machine": machine() or sysctl_machine(),
        "model": cpuinfo_field("model name") or cpuinfo_field("Hardware")
                 or cpuinfo_field("cpu model"),
        "vendor": cpuinfo_field("vendor_id") or cpuinfo_field("system type"),
        "endian": endianness(),
        "isa": cpuinfo_field("isa"),          # RISC-V 的 isa 行：rv64imafdc…
        "cores": cpuinfo_field("cpu cores") or str(cpuinfo().count("processor\t:")),
    }
    ref = reference(key)
    info["name"] = ref.get("name", key)
    info["standard"] = ref.get("standard", "")
    info["org"] = ref.get("org", "")
    return {k: v for k, v in info.items() if v}


def loongarch_details() -> dict:
    """龙芯（LoongArch / 早期 Godson）细节：型号、是否含向量/虚拟化扩展。"""
    info = cpuinfo()
    d = {"machine": machine(), "model": cpuinfo_field("model name") or cpuinfo_field("cpu model")}
    d["is_loongarch"] = detect_arch_key() == "loongarch"
    d["loongson_in_cpuinfo"] = bool(re.search(r"loongson|godson|loongarch", info, re.I))
    # 向量扩展（LSX/LASX）在 flags 里通常以 lsx / lasx 出现
    flags = cpuinfo_field("flags") or cpuinfo_field("Features")
    d["lsx"] = "lsx" in flags.lower()
    d["lasx"] = "lasx" in flags.lower()
    d["lbt"] = "lbt" in flags.lower()     # 二进制翻译（LBT：x86/ARM 兼容层）
    d["lvz"] = "lvz" in flags.lower()     # 虚拟化扩展
    return d


def mips_details() -> dict:
    """MIPS 细节：端序（mips vs mipsel）、位数（32/64）、ABI。"""
    m = machine().lower()
    txt = cpuinfo()
    d = {"machine": m, "is_mips": detect_arch_key() == "mips"}
    m64 = "64" in m
    d["bits"] = "64" if m64 else ("32" if m.startswith("mips") else "")
    # mipsel/mips64el 为小端；mips/mips64 为大端
    d["endian"] = "小端 (little-endian, *el)" if m.endswith("el") else "大端 (big-endian)"
    d["abi"] = {"o32": "o32（32 位）", "n32": "n32", "n64": "n64"}.get(
        "n64" if m64 else "o32", "")
    d["loongson_legacy"] = bool(re.search(r"loongson|godson", txt, re.I))
    d["cpu_model"] = cpuinfo_field("cpu model") or cpuinfo_field("model name")
    return d


def riscv_details() -> dict:
    """RISC-V 细节：isa 字符串、扩展集合（M/A/F/D/C/V…）。"""
    d = {"machine": machine(), "is_riscv": detect_arch_key() == "riscv"}
    isa = cpuinfo_field("isa") or ""
    d["isa"] = isa
    if isa:
        m = re.match(r"rv(\d+)([a-z]+)", isa, re.I)
        if m:
            d["xlens"] = m.group(1)
            d["extensions"] = list(m.group(2).lower())
    d["mmu"] = cpuinfo_field("mmu")
    d["uarch"] = cpuinfo_field("uarch")
    return d


def open_hardware_report() -> tuple:
    """开源硬件认证与许可指引（只读，列出标准出处与核对要点）。返回 (ok, msg)。"""
    ref = reference("open_hardware")
    if not ref:
        return False, "未找到开源硬件标准条目（data/arch.json 缺失 open_hardware）"
    std = ref.get("standards", {})
    lines = [
        f"开源硬件：{ref.get('name','')}",
        f"标准: {ref.get('standard','')}（{ref.get('org','')}）",
        "国际: " + " / ".join(std.get("international", [])) if std.get("international") else "",
        "地区: " + " / ".join(std.get("regional", [])) if std.get("regional") else "",
        "国标: " + " / ".join(std.get("national", [])) if std.get("national") else "",
        f"建议: {ref.get('advice','')}",
    ]
    return True, "\n".join(x for x in lines if x)


def arch_report() -> tuple:
    """综合架构报告（机器名 + 架构 + 标准出处 + 建议）。返回 (ok, msg)。"""
    key = detect_arch_key()
    d = arch_details(key)
    ref = reference(key)
    lines = [f"机器名: {d.get('machine','?')}   归一化架构键: {key}"]
    if d.get("model"):
        lines.append(f"CPU 型号: {d['model']}")
    if d.get("vendor"):
        lines.append(f"厂商/系统类型: {d['vendor']}")
    if d.get("endian"):
        lines.append(f"字节序: {d['endian']}")
    if key == "riscv" and d.get("isa"):
        lines.append(f"RISC-V ISA: {d['isa']}")
    if key == "loongarch":
        la = loongarch_details()
        ext = [n for n in ("lsx", "lasx", "lbt", "lvz") if la.get(n)]
        lines.append(f"龙芯扩展: {', '.join(ext) if ext else '（未读到，属正常——需内核导出 flags）'}")
    if key == "mips":
        mi = mips_details()
        lines.append(f"MIPS: {mi.get('bits','')} 位 / {mi.get('endian','')}"
                     + ("（龙芯早期 MIPS 授权机型）" if mi.get("loongson_legacy") else ""))
    if not ref:
        return True, "\n".join(lines + ["（该架构未收录标准条目，可在 data/arch.json 补充）"])
    std = ref.get("standards", {})
    lines.append("")
    lines.append(f"标准: {ref.get('standard','')}（{ref.get('org','')}）")
    for tier, label in (("national", "国标"), ("international", "国际"), ("regional", "地区")):
        items = std.get(tier, [])
        if items:
            lines.append(f"{label}: " + " / ".join(items))
    if ref.get("advice"):
        lines.append(f"建议: {ref['advice']}")
    return True, "\n".join(lines)


def loongarch_report() -> tuple:
    """龙芯（LoongArch / 早期 Godson）报告：型号、扩展、工具链。返回 (ok, msg)。"""
    d = loongarch_details()
    key = detect_arch_key()
    if key != "loongarch" and not d.get("loongson_in_cpuinfo"):
        return False, (f"当前非龙芯平台（machine={d.get('machine','?')}，架构={key}）；"
                       "若在龙芯机器上请确认内核导出 /proc/cpuinfo")
    ext = [n.upper() for n in ("lsx", "lasx", "lbt", "lvz") if d.get(n)]
    lines = [
        f"龙芯平台：machine={d.get('machine','?')}  model={d.get('model','?')}",
        "指令集: LoongArch（龙架构，国产自主，含基础架构 + 向量/虚拟化扩展）",
        "扩展: " + (", ".join(ext) if ext else "（内核未导出 flags，属正常）"),
        "工具链: " + toolchain_hint("loongarch"),
        "注意: 二进制翻译（LBT）可跑 x86/ARM 程序，但有性能损耗；优先原生包。",
        "国标: 龙芯 LoongArch（国产自主架构，国家标准见全国标准信息公共服务平台 std.samr.gov.cn）",
    ]
    return True, "\n".join(lines)


def mips_report() -> tuple:
    """MIPS 报告：位数、端序、ABI、是否龙芯早期授权机型。返回 (ok, msg)。"""
    d = mips_details()
    key = detect_arch_key()
    if key != "mips":
        return False, f"当前非 MIPS 平台（machine={d.get('machine','?')}，架构={key}）"
    lines = [
        f"MIPS 平台：machine={d.get('machine','?')}  model={d.get('cpu_model','?')}",
        f"位数: {d.get('bits','?')} 位    字节序: {d.get('endian','?')}    ABI: {d.get('abi','?')}",
        "工具链: " + toolchain_hint("mips"),
    ]
    if d.get("loongson_legacy"):
        lines.append("提示: 检测到 Loongson/Godson 字样——这是龙芯早期基于 MIPS 授权的机型，"
                     "新龙芯（3A5000+）已转向自主 LoongArch。")
    lines.append("注意: 大端（mips）与小端（mipsel）ABI 不通用，装包须对应。")
    lines.append("标准: MIPS Architecture for Programmers（MIPS32/MIPS64 Release 6，MIPS Open）")
    return True, "\n".join(lines)


def riscv_report() -> tuple:
    """RISC-V 报告：ISA 字符串、扩展、profiles 规范。返回 (ok, msg)。"""
    d = riscv_details()
    if detect_arch_key() != "riscv":
        return False, f"当前非 RISC-V 平台（machine={d.get('machine','?')}）"
    lines = [
        f"RISC-V 平台：machine={d.get('machine','?')}  uarch={d.get('uarch','?')}",
        f"ISA: {d.get('isa','?')}" + (f"    扩展: {''.join(d.get('extensions', []))}"
                                      if d.get("extensions") else ""),
        "规范: RISC-V Unprivileged/Privileged ISA + RVA20/RVA22/RVA23 profiles"
        "（RISC-V International，开源 ISA）",
        "工具链: " + toolchain_hint("riscv"),
    ]
    return True, "\n".join(lines)


def toolchain_report() -> tuple:
    """当前架构的交叉工具链与 Go GOARCH 提示。返回 (ok, msg)。"""
    key = detect_arch_key()
    ga = {
        "loongarch": "loong64", "mips": "mips64le", "riscv": "riscv64",
        "openpower": "ppc64le", "openrisc": "or1k", "x86": "amd64", "arm": "arm64",
    }.get(key, "")
    lines = [
        f"架构: {key}（machine={machine()}）",
        "工具链: " + toolchain_hint(key),
        "Go 交叉构建: " + (f"GOARCH={ga} go build ./..." if ga
                        else "go build ./...（该架构未收录 GOARCH 映射）"),
    ]
    return True, "\n".join(lines)


def toolchain_hint(arch_key: str = None) -> str:
    """给出该架构的编译/工具链提示（用于构建类任务的指引文本）。"""
    key = arch_key or detect_arch_key()
    return {
        "loongarch": "loongarch64-linux-gnu-* 交叉工具链；本机编译可用 -march=loongarch64，"
                     "优先取龙芯/系统厂商提供的源与包",
        "mips": "mips64el-linux-gnuabi64-* / mipsel-linux-gnu-* 交叉工具链；"
                "注意大端（mips）与小端（mipsel）ABI 不可混用",
        "riscv": "riscv64-linux-gnu-* 交叉工具链；常用 -march=rv64gc -mabi=lp64d",
        "openpower": "powerpc64le-linux-gnu-* 交叉工具链（小端 ppc64le 为主流 ABI）",
        "openrisc": "or1k-elf-* / or1k-linux-gnu-* 工具链（FPGA / 教学场景）",
        "x86": "本机原生；可用 -march=native（便携分发慎用）",
        "arm": "aarch64-linux-gnu-* 交叉工具链；注意 arm64 与 armhf 变体区分",
    }.get(key, "未收录该架构的工具链提示；以发行版/厂商文档为准")
