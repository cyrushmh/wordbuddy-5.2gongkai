"""插件框架（安全优先的只读插件注册表）。

本模块为「插件支持」提供一套**安全**机制：插件把一项能力（如 OpenWrt 路由器接口）
登记为一份清单（manifest），声明它依赖哪些**已审读**的只读原生函数、暴露哪些能力、
对应哪些任务。插件**不能执行任意代码**——其唯一可被调用的「执行入口」`native` 必须是
``sysweeper.native`` 下、且落在 `NATIVE_ALLOWLIST` 白名单里的零参只读函数（返回 (ok, msg)）。

设计原则（与全局一致）：纯标准库、零依赖、离线优先；插件清单为只读登记；
**绝不导入/执行插件自带代码**，绝不允许 shell 注入。

- 内置插件（BUILTIN_PLUGINS）：随工具发布，由代码直接声明（openwrt / interop 聚合）。
- 用户插件：扫描 `$SYSWEEPER_PLUGINS_DIR` 或仓库 `plugins/` 目录下的 `*.json` 清单；
  每个清单经 `plugin_validate` 校验后才注册，非白名单入口一律拒绝。

安全护栏（最关键）：
- manifest 的 `native` 字段只能是 effective_allowlist()（静态审读 + register_native
  运行时安全登记）中的 "module.func" 字符串；含任意命令、路径、shell 元字符或
  非白名单函数的清单**直接拒绝注册**。
- 插件不持有可写入口；所有调用最终都回到 runner._run_native 的只读函数。
- ``register_native`` 只能登记**本包内已存在**的零参只读函数（严格标识符校验），
  是「可扩展」而非「可注入」；写指引层 openwrt_write 显式拒绝进入白名单。
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# 原生只读函数白名单（插件唯一可被调用的执行入口）                              #
# 仅收录「零参、返回 (ok, msg)、只读、不执行写操作」的函数。新增可调用能力时，     #
# 必须在此显式登记（即「审读」），插件清单才能引用。                              #
# --------------------------------------------------------------------------- #

NATIVE_ALLOWLIST = {
    # OpenWrt 只读报告
    "openwrt.openwrt_report",
    "openwrt.openwrt_detect_report",
    "openwrt.openwrt_uci_report",
    "openwrt.openwrt_pkgs_report",
    "openwrt.openwrt_network_report",
    "openwrt.openwrt_build_report",
    # 第三方引用只读报告（用于「interop 聚合」插件演示）
    "thirdparty.interop_refs_report",
    "thirdparty.hw_opt_report",
    "thirdparty.downloader_report",
    "thirdparty.cdn_p2p_report",
    "thirdparty.licenses_report",
    # 插件系统自身
    "plugins.plugin_report",
}

# manifest id 允许字符（杜绝路径/命令注入）
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,47}$")

# native 入口名（"module.func"）允许字符：严格的 Python 标识符，杜绝路径/命令/元字符
_NATIVE_OP_RE = re.compile(r"^[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*$")

# 明确**禁止**进入插件白名单的模块：openwrt_write 是「写操作指引」层，
# 写指引必须经用户显式选择的 opt-in 高危任务触发，绝不允许被插件间接驱动。
_DENIED_MODULES = frozenset({"openwrt_write"})

# 运行时动态登记的白名单条目（经 register_native 审读后可被插件引用）
_DYNAMIC_ALLOWLIST: set = set()


def effective_allowlist() -> set:
    """当前生效的只读白名单 = 静态审读条目 + 运行时安全登记条目。"""
    return set(NATIVE_ALLOWLIST) | set(_DYNAMIC_ALLOWLIST)


def _resolve_native(op: str):
    """把 "module.func" 解析为 sysweeper.native 下的可调用对象。

    安全：仅允许严格标识符形式；模块必须真实存在于 sysweeper.native 包内
    （杜绝路径穿越/任意模块加载），函数必须可调用。
    """
    import importlib
    if not _NATIVE_OP_RE.match(op or ""):
        raise ValueError(f"native 入口名非法（仅 module.func 标识符）: {op!r}")
    module_name, func_name = op.split(".", 1)
    if module_name in _DENIED_MODULES:
        raise ValueError(f"模块 {module_name!r} 为写指引层，禁止进入插件白名单")
    mod = importlib.import_module(f"{__package__}.{module_name}")
    fn = getattr(mod, func_name, None)
    if fn is None or not callable(fn):
        raise ValueError(f"原生函数不存在或不可调用: {op}")
    return fn


def register_native(*names: str) -> Tuple[bool, str]:
    """把 sysweeper.native 下**已存在**的零参只读函数动态加入插件白名单。

    这是「可扩展」而**非**「可注入」——插件框架的安全底线不变：
    - 只能登记本包内**已审读、已存在**的 module.func，无法引入任意外部代码；
    - 入口名必须是严格标识符（module.func），杜绝路径/命令/shell 元字符；
    - 写指引层（openwrt_write）被显式拒绝——写指引只能由 opt-in 任务触发，
      不允许插件间接驱动；
    - 登记的函数经 runner 以零参 fn() 调用，与静态白名单同等对待。

    返回 (ok, 说明)。names 为空或全部无效时返回 (False, 原因)。
    """
    added, rejected = [], []
    for op in names:
        if not isinstance(op, str):
            rejected.append(f"{op!r}（非字符串）")
            continue
        try:
            _resolve_native(op)
        except Exception as e:  # noqa: BLE001
            rejected.append(f"{op}（{e}）")
            continue
        _DYNAMIC_ALLOWLIST.add(op)
        added.append(op)
    if not added:
        return False, ("未能登记任何原生入口；已拒绝: "
                       + ("; ".join(rejected) if rejected else "(无输入)"))
    msg = f"已登记 {len(added)} 个只读原生入口: " + ", ".join(added)
    if rejected:
        msg += f"（拒绝 {len(rejected)} 个: " + "; ".join(rejected) + "）"
    return True, msg


# --------------------------------------------------------------------------- #
# 内置插件（随工具发布，由代码声明，经同一套 plugin_validate 校验）              #
# --------------------------------------------------------------------------- #

BUILTIN_PLUGINS: Dict[str, dict] = {
    "openwrt": {
        "id": "openwrt",
        "name": "OpenWrt 路由器系统接口",
        "platform": "openwrt",
        "version": "1.0",
        "license": "GPL-2.0（OpenWrt 自身；本工具仅只读引用）",
        "description": "OpenWrt 原生的只读接口：UCI 配置、opkg/apk 包管理、netifd/ubus、"
                       "procd、LuCI、固件与板型信息、ImageBuilder/SDK 构建系统。",
        "docs": ["https://openwrt.org/docs/guide-user/",
                 "https://openwrt.org/docs/techref/"],
        "capabilities": [
            {"id": "firmware", "name": "固件与板型识别",
             "interfaces": ["/etc/openwrt_release", "/etc/os-release", "/tmp/sysinfo/*"]},
            {"id": "uci", "name": "UCI 统一配置（只读审计）",
             "interfaces": ["/etc/config/*", "uci show"]},
            {"id": "pkgs", "name": "包管理盘点（opkg/apk）",
             "interfaces": ["opkg list-installed", "apk info", "/usr/lib/opkg/status",
                            "/usr/lib/apk/db/installed"]},
            {"id": "network", "name": "网络接口（netifd/ubus）",
             "interfaces": ["/etc/config/network", "ubus call network.interface dump"]},
            {"id": "procd", "name": "服务与进程（procd/ubus）",
             "interfaces": ["/etc/init.d/*", "ubus call service list"]},
            {"id": "build", "name": "构建系统参考（ImageBuilder/SDK/feeds）",
             "interfaces": ["ImageBuilder make image", "SDK make", "feeds"]},
        ],
        "native": [
            "openwrt.openwrt_report", "openwrt.openwrt_detect_report",
            "openwrt.openwrt_uci_report", "openwrt.openwrt_pkgs_report",
            "openwrt.openwrt_network_report", "openwrt.openwrt_build_report",
        ],
        "task_ids": ["openwrt_detect", "openwrt_uci_audit", "openwrt_pkgs",
                     "openwrt_network", "openwrt_build"],
    },
    "interop": {
        "id": "interop",
        "name": "网络互联互通（第三方引用聚合插件）",
        "platform": "any",
        "version": "1.0",
        "license": "各自许可证（见仓库 licenses/ 文件夹）",
        "description": "把 v0.5.19 导入的第三方网络互联互通/硬件优化/开源下载引用聚合为一个"
                       "插件，演示「插件支持」可统一承载既有能力。",
        "docs": ["https://github.com/cyrushmh/wordbuddy-github"],
        "capabilities": [
            {"id": "network-interop", "name": "网络互联互通方案",
             "interfaces": ["p2wlan", "dae", "gfw-pac", "v2rayN"]},
            {"id": "hardware-opt", "name": "硬件优化（用户选择）",
             "interfaces": ["DLSS5-Swapper"]},
            {"id": "downloader", "name": "开源下载（CDN/P2P 开关）",
             "interfaces": ["aria2"]},
        ],
        "native": [
            "thirdparty.interop_refs_report", "thirdparty.hw_opt_report",
            "thirdparty.downloader_report", "thirdparty.cdn_p2p_report",
            "thirdparty.licenses_report",
        ],
        "task_ids": ["net_interop_refs", "net_interop_cdn_p2p", "hw_dlss_swapper",
                     "hw_dl_open_download", "any_interop_policy"],
    },
}


# --------------------------------------------------------------------------- #
# 校验（安全核心）                                                              #
# --------------------------------------------------------------------------- #


def plugin_validate(m: dict) -> Tuple[bool, str]:
    """校验一份插件清单是否可安全注册。返回 (ok, 原因)。

    拒绝情形：
    - 非 dict / 缺 id / id 非法（含路径或命令字符）；
    - `native` 任一入口不在 effective_allowlist()（静态白名单 + register_native
      运行时安全登记；可能执行任意代码的一律拒绝）；
    - `native` 不是字符串列表。
    通过则返回 (True, "ok")。
    """
    if not isinstance(m, dict):
        return False, "插件清单必须是 JSON 对象"
    pid = m.get("id")
    if not isinstance(pid, str) or not _ID_RE.match(pid):
        return False, f"插件 id 非法（仅允许小写字母/数字/_-，且 2-48 字符）: {pid!r}"
    if not m.get("name") or not m.get("description"):
        return False, "插件缺少 name / description"
    # 安全：native 入口必须是白名单内的只读函数（静态 + 动态登记）
    allowed = effective_allowlist()
    native_entries = m.get("native") or []
    if not isinstance(native_entries, list):
        return False, "`native` 必须是字符串列表"
    for op in native_entries:
        if not isinstance(op, str) or op not in allowed:
            return False, (f"插件 {pid} 的 native 入口 {op!r} 不在只读白名单"
                           "（拒绝注册，防任意代码执行）")
    # capabilities / task_ids 仅为元数据，弱校验
    caps = m.get("capabilities")
    if caps is not None and not isinstance(caps, list):
        return False, "`capabilities` 必须是列表"
    tids = m.get("task_ids")
    if tids is not None and not isinstance(tids, list):
        return False, "`task_ids` 必须是列表"
    return True, "ok"


# --------------------------------------------------------------------------- #
# 加载：内置 + 用户目录（扫描 *.json）                                          #
# --------------------------------------------------------------------------- #


def _shipped_plugin_paths() -> List[Path]:
    """扫描随包发布的 plugins/ 示例清单（用户drop-in 风格，需经校验）。"""
    out: List[Path] = []
    try:
        from importlib import resources
        pkg = resources.files("sysweeper.plugins")
        for f in pkg.iterdir():
            if str(f).endswith(".json"):
                out.append(Path(str(f)))
    except Exception:  # noqa: BLE001
        return out
    return out


def _user_plugin_paths(plugins_dir: Optional[str]) -> List[Path]:
    d = plugins_dir or os.environ.get("SYSWEEPER_PLUGINS_DIR")
    if not d:
        return []
    p = Path(d)
    if not p.is_dir():
        return []
    return sorted(p.glob("*.json"))


def load_plugins(plugins_dir: Optional[str] = None) -> Dict[str, dict]:
    """合并内置插件与用户插件，返回 {id: manifest}。

    - 内置插件先入；
    - 用户清单（shipped + $SYSWEEPER_PLUGINS_DIR）逐个经 plugin_validate 校验，
      通过的才注册；非白名单/非法的直接跳过（绝不允许注入）。
    """
    reg: Dict[str, dict] = {}
    for pid, m in BUILTIN_PLUGINS.items():
        ok, _why = plugin_validate(m)
        if ok:
            reg[pid] = m
    for p in _shipped_plugin_paths() + _user_plugin_paths(plugins_dir):
        try:
            m = json.loads(Path(p).read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        ok, _why = plugin_validate(m)
        if ok and m.get("id"):
            reg[m["id"]] = m
    return reg


def plugin_index() -> Dict[str, dict]:
    """返回当前已注册的插件清单（内置 + 用户）。"""
    return load_plugins()


# --------------------------------------------------------------------------- #
# 查询 / 执行（只读）                                                           #
# --------------------------------------------------------------------------- #


def list_plugins(plugins_dir: Optional[str] = None) -> List[str]:
    """全部已注册插件的文本行。"""
    reg = load_plugins(plugins_dir)
    if not reg:
        return ["（未注册任何插件）"]
    lines = ["已注册插件（安全只读注册表）：", "-" * 52]
    for pid, m in reg.items():
        caps = m.get("capabilities") or []
        lines.append(f"  · {pid:<14} | {m.get('name','')}")
        lines.append(f"      平台: {m.get('platform','')}  版本: {m.get('version','')}"
                     f"  许可证: {m.get('license','')}")
        lines.append(f"      能力: {len(caps)} 项  原生入口: {len(m.get('native') or [])} 个"
                     f"  任务: {len(m.get('task_ids') or [])} 个")
        lines.append(f"      说明: {m.get('description','')}")
    return lines


def plugin_capabilities(pid: str, plugins_dir: Optional[str] = None) -> List[dict]:
    """某插件的能力清单（capabilities 列表）。"""
    reg = load_plugins(plugins_dir)
    m = reg.get(pid)
    if not m:
        return []
    return list(m.get("capabilities") or [])


def plugin_run(pid: str, plugins_dir: Optional[str] = None) -> Tuple[bool, str]:
    """运行某插件声明的全部只读原生函数（经白名单，绝不执行写操作）。

    返回 (ok, 合并报告)。任一入口失败仅记录、不中断；全部失败返回 (False, ...)。
    """
    from .. import runner  # noqa: E402  (延迟导入，避免循环)
    reg = load_plugins(plugins_dir)
    m = reg.get(pid)
    if not m:
        return False, f"未找到插件 {pid!r}"
    blocks = [f"插件 {pid}（{m.get('name','')}）· 只读执行："]
    failed = 0
    for op in m.get("native") or []:
        ok, msg = runner._run_native(op)
        mark = "✓" if ok else "✗"
        if not ok:
            failed += 1
        blocks.append(f"\n[{mark}] {op}\n{msg}")
    ok = failed < len(m.get("native") or [1])
    return ok, "\n".join(blocks)


def allowlist_report() -> Tuple[bool, str]:
    """展示当前生效的只读白名单（静态审读 + 运行时安全登记），供 CLI/GUI 检视。"""
    allowed = effective_allowlist()
    static = sorted(NATIVE_ALLOWLIST)
    dynamic = sorted(set(_DYNAMIC_ALLOWLIST))
    lines = [f"插件只读白名单（生效 {len(allowed)} 条）：",
             f"  静态审读条目: {len(static)}",
             f"  运行时登记条目(register_native): {len(dynamic)}",
             "- " * 22,
             "-- 静态审读（随工具发布）--"]
    lines += [f"    · {op}" for op in static]
    if dynamic:
        lines.append("-- 运行时登记（register_native，已审读存在性）--")
        lines += [f"    · {op}" for op in dynamic]
    lines.append("")
    lines.append("写指引层（openwrt_write.*）刻意不在白名单内——写操作指引只能由"
                 "opt-in 高危任务触发，不允许插件间接驱动。")
    return True, "\n".join(lines)


def plugin_report(action: str = "list", pid: Optional[str] = None,
                  plugins_dir: Optional[str] = None) -> Tuple[bool, str]:
    """统一入口（供 CLI/GUI 调用）。action ∈ list|show|run|allowlist。"""
    if action == "list":
        return True, "\n".join(list_plugins(plugins_dir))
    if action == "allowlist":
        return allowlist_report()
    reg = load_plugins(plugins_dir)
    if action == "show":
        if not pid:
            return False, "show 需要 --id <插件id>（可用 `plugins` 查看清单）"
        m = reg.get(pid)
        if not m:
            return False, f"未找到插件 {pid!r}"
        caps = m.get("capabilities") or []
        lines = [f"插件 {pid} 清单：", "-" * 50,
                 f"  名称: {m.get('name','')}", f"  平台: {m.get('platform','')}",
                 f"  版本: {m.get('version','')}", f"  许可证: {m.get('license','')}",
                 f"  说明: {m.get('description','')}", f"  文档: {'; '.join(m.get('docs', []) or [])}"]
        lines.append(f"  原生入口({len(m.get('native') or [])}):")
        for op in m.get("native") or []:
            lines.append(f"    - {op}")
        lines.append(f"  能力({len(caps)}):")
        for c in caps:
            lines.append(f"    · {c.get('id','')} | {c.get('name','')} "
                         f"| {', '.join(c.get('interfaces', []) or [])}")
        lines.append(f"  关联任务({len(m.get('task_ids') or [])}): "
                     + ", ".join(m.get("task_ids") or []))
        return True, "\n".join(lines)
    if action == "run":
        if not pid:
            return False, "run 需要 --id <插件id>"
        return plugin_run(pid, plugins_dir)
    return False, f"未知动作 {action!r}（list|show|run|allowlist）"


__all__ = [
    "NATIVE_ALLOWLIST", "BUILTIN_PLUGINS", "effective_allowlist",
    "register_native", "allowlist_report",
    "plugin_validate", "load_plugins",
    "plugin_index", "list_plugins", "plugin_capabilities", "plugin_run",
    "plugin_report",
]
