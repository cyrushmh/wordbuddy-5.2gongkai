"""去中心化版本号体系（v0.6.88 重构引入，2026-10-23 批准）。

格式（用户定义）
================
    NNNN.NNNN.NNNN.NNNN[.YYYYMMDD]

- 核心计数为 4 段，每段 4 位零填充（``0000``–``9999``），**里程表式**：
  最右段 D 为主序号，溢出时向左进位（D → C → B → A）；四段全满
  （``9999.9999.9999.9999``）再 ``bump`` 即**循环归零**回到 ``0000.0000.0000.0000``。
- 文化隐喻：每段每位封顶恰为 ``9``（十进制「数之极」，《易》以九为老阳之终），
  满 ``9999`` 即向左进位、四段全满则「极则归零」——进位逻辑正是
  「九尽则变、物极必反」的数字化体现（双九 ``99`` 犹胜「九五之尊」，``9999`` 即数之极）。
- 末尾可选 8 位日期后缀 ``YYYYMMDD``（≤ ``99991231``），标识该版本的定版 /
  发行日期；省略日期后缀即基值形态 ``0000.0000.0000.0000``（"没有后面"）。
- 首发示例：``0000.0000.0000.0001.20261023``；上限：``9999.9999.9999.9999.99991231``。

去中心化原则（用户定义）
========================
整体包 / 兼容层 ``common`` / 各概念系统 / 各子系统**各自持有独立版本号**，互不同步。
本模块只提供：

- 整体包单一事实源 ``PACKAGE_VERSION`` 与基值 ``BASE_VERSION``；
- 一组无状态工具：``is_valid``（校验）/ ``today_suffix``（当日日期）/
  ``bump``（里程表进位 + 循环归零 + 默认追加日期）/ ``strip_date``（取基值）。

本模块**不**替其他层做版本决策——其他层各自维护自己的版本号即可。

约束：纯标准库，零依赖，无循环导入风险（本模块不 import 包内任何其他模块）。
"""
from __future__ import annotations

import re
from datetime import date

# 核心计数：4 段各 4 位（0000–9999）
CORE_RE = re.compile(r"^\d{4}\.\d{4}\.\d{4}\.\d{4}$")
# 完整形态：核心 + 可选 8 位日期后缀
FULL_RE = re.compile(r"^\d{4}\.\d{4}\.\d{4}\.\d{4}(?:\.(\d{8}))?$")

MAX_SEG = 9999

# 整体包首发版本（去中心化：仅代表整体包自身，不复用作其他层的版本）
PACKAGE_VERSION = "0000.0000.0000.0034.20261026"
# 基值（无日期后缀形态）
BASE_VERSION = "0000.0000.0000.0000"

# 各层版本迁移映射（仅记录，便于审计；本模块不强制其他层使用）
_MATURITY = {
    "common": "0088",   # 兼容层：保留原 0.6.88 的成熟度 88
}
_CONCEPTS = {
    "apilab": "0064", "baigong": "0061", "comp": "0065", "daoxue": "0058",
    "datong": "0062", "netsys": "0066", "plang": "0061", "quantum": "0066",
    "zhuangzi": "0060",
}


def _valid_date(s: str) -> bool:
    """校验 8 位 ``YYYYMMDD``：月份 01–12、日期合法（含闰年 2 月）、年份 ≤ 9999。"""
    if not s.isdigit() or len(s) != 8:
        return False
    y, m, d = int(s[0:4]), int(s[4:6]), int(s[6:8])
    if y > 9999 or m < 1 or m > 12 or d < 1:
        return False
    days = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    if m == 2 and (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)):
        max_d = 29
    else:
        max_d = days[m - 1]
    return d <= max_d


def is_valid(v) -> bool:
    """版本串是否合法：匹配 ``FULL_RE`` 且（若带日期）月/日合理。

    接受核心基值（无后缀）与完整形态（带 8 位日期）。非字符串一律 False。
    """
    if not isinstance(v, str):
        return False
    m = FULL_RE.match(v)
    if not m:
        return False
    date_part = m.group(1)
    if date_part is not None and not _valid_date(date_part):
        return False
    return True


def strip_date(v: str) -> str:
    """取下日期后缀的基值（核心 4 段）。非法串原样返回。"""
    parts = v.split(".")
    if len(parts) == 5 and len(parts[4]) == 8 and parts[4].isdigit():
        return ".".join(parts[:4])
    return v


def core_segments(v: str):
    """解析核心 4 段为整数元组；非法返回 ``None``。"""
    core = strip_date(v)
    if not CORE_RE.match(core):
        return None
    return tuple(int(x) for x in core.split("."))


def today_suffix() -> str:
    """返回当日 ``YYYYMMDD``（用作版本日期后缀）。"""
    return date.today().strftime("%Y%m%d")


def bump(v, *, date=None) -> str:
    """里程表式进位 + 循环归零 + 默认追加当日日期。

    - 最右段 D +1；溢出向左进位（D → C → B → A）；
    - 四段全满后再 ``bump`` → 循环归零到 ``0000.0000.0000.0000``；
    - ``date`` 为 ``None`` 时取当日 ``YYYYMMDD``；可显式传入合法 8 位日期，
      或传 ``""``（空串）去掉日期后缀、只推进核心计数。
    """
    segs = core_segments(v)
    if segs is None:
        raise ValueError(f"无法对非法版本进位: {v!r}")
    a, b, c, d = segs
    d += 1
    if d > MAX_SEG:
        d, c = 0, c + 1
    if c > MAX_SEG:
        c, b = 0, b + 1
    if b > MAX_SEG:
        b, a = 0, a + 1
    if a > MAX_SEG:
        a = b = c = d = 0  # 循环归零
    core = f"{a:04d}.{b:04d}.{c:04d}.{d:04d}"
    # date 为 None → 默认追加当日日期；传空串 "" 则只推进核心计数（去掉日期）
    if date is None:
        date = today_suffix()
    if date:
        return f"{core}.{date}"
    return core


def fmt(maturity: str, date_part: str = "") -> str:
    """按迁移约定构造一段概念/层的版本：``0000.0000.0000.<maturity>[.date]``。

    仅是便捷构造器，不强制任何层使用；各层可自行决定自己的版本。
    """
    core = f"0000.0000.0000.{maturity}"
    if date_part:
        return f"{core}.{date_part}"
    return core


def to_pep440(v: str) -> str:
    """将去中心化版本映射为合规 PEP 440 串（仅供需要 PEP 440 的外部工具使用）。

    本项目内部一律使用 odometer 格式；仅在必须对接要求 PEP 440 的外部系统
    （如 PyPI 发布）时才用本函数转换，避免有人为"合规"把三处活版本直接改回
    PEP 440 而破坏三处一致约束。

    规则：核心四段各去前导零（全零段保留为 ``0``）；日期后缀转为 local version
    段（``+YYYYMMDD``）。例：
        ``0000.0000.0000.0001.20261023`` → ``0.0.0.1+20261023``
        ``0000.0000.0000.0000``         → ``0.0.0.0``
    """
    core = strip_date(v)
    if not CORE_RE.match(core):
        raise ValueError(f"无法映射非法版本: {v!r}")
    segs = ".".join(str(int(x)) for x in core.split("."))
    m = FULL_RE.match(v)
    date_part = m.group(1) if m and m.group(1) else None
    if date_part:
        segs += "+" + date_part
    return segs


def to_semver(v: str) -> str:
    """将去中心化版本映射为 CalVer semver 串（供 Cargo/npm 等 semver 强制场景）。

    本项目内部一律使用 odometer 格式；凡强制 3 段 semver 的工具
    （Cargo.toml / package.json 等）改用 **CalVer** ``YYYY.MM.DD``，
    与 odometer 的日期后缀同源，年份打头显长青。例：
        ``0000.0000.0000.0001.20261023`` → ``2026.10.23``
    无日期后缀时取当日。
    """
    m = FULL_RE.match(v) if isinstance(v, str) else None
    date_part = m.group(1) if m and m.group(1) else today_suffix()
    y, mo, d = date_part[0:4], date_part[4:6], date_part[6:8]
    return f"{int(y)}.{int(mo)}.{int(d)}"


# 自检：模块导入即验证核心不变量（仅标准库，零成本，失败即早暴露）
def _self_check() -> None:
    assert is_valid(PACKAGE_VERSION) and is_valid(BASE_VERSION)
    assert not is_valid("0.6.88")
    assert not is_valid("v0.6.64")
    # 进位 / 循环归零测试（date="" 仅推进核心计数，剥离日期后缀）
    assert bump("0000.0000.0000.9999", date="") == "0000.0000.0001.0000"
    assert bump("0000.0000.9999.9999", date="") == "0000.0001.0000.0000"
    assert bump("9999.9999.9999.9999", date="") == "0000.0000.0000.0000"  # 循环归零
    # 默认 bump 追加当日日期
    assert bump("0000.0000.0000.0001") == f"0000.0000.0000.0002.{today_suffix()}"
    assert strip_date("0000.0000.0000.0001.20261023") == "0000.0000.0000.0001"
    # to_pep440：odometer → PEP 440（仅供外部 PEP 440 工具，不改三处活版本）
    assert to_pep440("0000.0000.0000.0001.20261023") == "0.0.0.1+20261023"
    assert to_pep440("0000.0000.0000.0000") == "0.0.0.0"
    # to_semver：odometer → CalVer（供 Cargo/npm 等 semver 强制场景，年份打头）
    assert to_semver("0000.0000.0000.0001.20261023") == "2026.10.23"


_self_check()
