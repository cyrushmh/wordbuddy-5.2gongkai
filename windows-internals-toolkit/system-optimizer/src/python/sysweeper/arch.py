"""架构 / 指令集（ISA）支持：龙芯 LoongArch、MIPS、开源硬件（RISC-V 等）。

本模块是 native/arch.py（原生探测）之上的封装，负责：

1. **识别当前架构**——龙芯 LoongArch、MIPS、RISC-V、OpenPOWER、OpenRISC、
   x86、ARM 与未知架构；
2. **给出标准出处**——按「国家优先 / 国际给外人 / 地区按需」三层引用
   （与 models.CATEGORY_STANDARDS 同口径），可切换受众；
3. **开源硬件**——OSHWA 认证、CERN OHL 许可、DIN SPEC 3105（地区标准）、
   CHIPS Alliance 等，说明复用硬件设计时的许可与认证核对点；
4. **构建提示**——为交叉编译给出 GOARCH / 工具链三元组（呼应 Go 构建支持）。

架构键 → Go 的 GOARCH（用于交叉构建）
------------------------------------
    loongarch → loong64        mips → mips64le / mipsle（按端序）
    riscv     → riscv64        openpower → ppc64le
    x86       → amd64 / 386    arm → arm64 / arm

设计原则（与 a11y.py 一致）：纯标准库、零依赖、graceful——
探测失败返回 (False, 说明) 或空值，绝不因缺少接口而抛异常。
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from .native import arch as _n

# 架构键 → 中文名（data/arch.json 之外的兜底展示名）
ARCH_NAMES = {
    "loongarch": "龙芯 LoongArch",
    "mips": "MIPS",
    "riscv": "RISC-V",
    "openpower": "OpenPOWER / Power ISA",
    "openrisc": "OpenRISC",
    "x86": "x86 / x86-64",
    "arm": "ARM / AArch64",
    "open_hardware": "开源硬件",
    "unknown": "未知架构",
}

# 架构键 → Go GOARCH（交叉构建用；多个值时首选第一个）
GOARCH_MAP = {
    "loongarch": "loong64",
    "mips": "mips64le",
    "riscv": "riscv64",
    "openpower": "ppc64le",
    "openrisc": "or1k",
    "x86": "amd64",
    "arm": "arm64",
}

# 国产 / 自主架构（国内场景优先关注）
NATIONAL_ARCHS = ("loongarch",)

# 开源 / 开放架构（开源硬件生态）
OPEN_ARCHS = ("riscv", "openpower", "openrisc")

AUDIENCES = ("cn", "intl", "regional")


def current_arch() -> str:
    """当前运行的架构键（loongarch / mips / riscv / x86 / arm / …）。"""
    return _n.detect_arch_key()


def arch_name(key: str = None) -> str:
    """架构的中文展示名。"""
    k = key or current_arch()
    ref = _n.reference(k)
    return ref.get("name") or ARCH_NAMES.get(k, k)


def details(key: str = None) -> dict:
    """架构探测详情（机器名/型号/字节序/ISA 等）。"""
    return _n.arch_details(key or current_arch())


def standards(key: str = None) -> dict:
    """某架构的三层标准出处 {"national":[], "international":[], "regional":[]}。"""
    ref = _n.reference(key or current_arch())
    std = ref.get("standards", {}) or {}
    return {
        "national": list(std.get("national", [])),
        "international": list(std.get("international", [])),
        "regional": list(std.get("regional", [])),
    }


def standards_for_audience(key: str = None, audience: str = "cn") -> List[str]:
    """按受众返回优先级排序的标准清单。

    - cn       : 国标/国家平台优先 → 国际 → 地区
    - intl     : 国际优先 → 国标 → 地区（面向外国用户）
    - regional : 地区优先 → 国标 → 国际（按所在国家/地区执行）
    """
    st = standards(key)
    if audience == "intl":
        order = ["international", "national", "regional"]
    elif audience in ("regional", "region"):
        order = ["regional", "national", "international"]
    else:
        order = ["national", "international", "regional"]
    out: List[str] = []
    for tier in order:
        for item in st.get(tier, []):
            out.append(f"[{ {'national': '国标', 'international': '国际', 'regional': '地区'}[tier] }] {item}")
    return out


def is_national_arch(key: str = None) -> bool:
    """是否为国产/自主指令集架构（如龙芯 LoongArch）。"""
    return (key or current_arch()) in NATIONAL_ARCHS


def is_open_arch(key: str = None) -> bool:
    """是否为开源/开放指令集架构（RISC-V、OpenPOWER、OpenRISC）。"""
    return (key or current_arch()) in OPEN_ARCHS


def goarch(key: str = None) -> str:
    """该架构对应的 Go GOARCH（交叉构建用）。"""
    return GOARCH_MAP.get(key or current_arch(), "")


def go_build_command(key: str = None, goos: str = "") -> str:
    """给出该架构的 Go 交叉构建命令示例（供构建类任务/文档引用）。"""
    k = key or current_arch()
    ga = goarch(k)
    if not ga:
        return "go build ./...（架构未收录 GOARCH 映射，按默认目标构建）"
    goos = goos or ("windows" if _n.machine().lower().find("win") >= 0 else "linux")
    return f"GOOS={goos} GOARCH={ga} go build ./..."


def toolchain_hint(key: str = None) -> str:
    """该架构的交叉工具链三元组提示。"""
    return _n.toolchain_hint(key or current_arch())


def open_hardware_report() -> Tuple[bool, str]:
    """开源硬件认证与许可指引（OSHWA / CERN OHL / DIN SPEC 3105）。"""
    return _n.open_hardware_report()


def loongarch_report() -> Tuple[bool, str]:
    """龙芯（LoongArch）专项报告：型号、向量/虚拟化/二进制翻译扩展、工具链。"""
    return _n.loongarch_report()


def mips_report() -> Tuple[bool, str]:
    """MIPS 专项报告：位数、端序、ABI、是否龙芯早期授权机型。"""
    return _n.mips_report()


def riscv_report() -> Tuple[bool, str]:
    """RISC-V 专项报告：ISA 字符串、扩展、profiles 规范。"""
    return _n.riscv_report()


def environment_report(audience: str = "cn") -> List[str]:
    """完整架构环境报告（供 CLI arch 命令 / GUI 架构页展示）。"""
    key = current_arch()
    d = details(key)
    lines: List[str] = [
        "=" * 68,
        f"架构/指令集报告：{arch_name(key)}（key={key}）",
        "=" * 68,
        f"机器名: {d.get('machine','?')}",
    ]
    for label, field in (("CPU 型号", "model"), ("厂商/系统类型", "vendor"),
                         ("字节序", "endian"), ("ISA", "isa"), ("核心数", "cores")):
        if d.get(field):
            lines.append(f"{label}: {d[field]}")
    if is_national_arch(key):
        lines.append("属性: 国产自主指令集架构（国内场景优先）")
    if is_open_arch(key):
        lines.append("属性: 开源/开放指令集架构（开源硬件生态）")
    lines.append("")
    lines.append("标准出处（三层，按受众 %s 排序）：" % audience)
    for s in standards_for_audience(key, audience):
        lines.append(f"  · {s}")
    lines.append("")
    lines.append("构建提示: " + toolchain_hint(key))
    lines.append("Go 交叉构建: " + go_build_command(key))
    lines.append("")
    lines.append("已收录架构：" + ", ".join(ARCH_NAMES.get(k, k) for k in _n.all_arch_keys()))
    return lines


def arch_report(audience: str = "cn") -> Tuple[bool, str]:
    """架构报告主入口：返回 (ok, 文本)。"""
    try:
        return True, "\n".join(environment_report(audience))
    except Exception as e:  # noqa: BLE001
        return False, f"架构探测失败: {e}"
