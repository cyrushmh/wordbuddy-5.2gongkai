"""参数与阈值注册表（v0.6.23）——GUI/CLI 可调参数的**单一事实源**。

与 ``subsystems.py``（子系统开关）互补：那个管「哪些诊断项嵌入总览」，
本模块管「诊断与导入过程本身怎么跑」——**运行参数**与**数值阈值**。

设计要点（对齐用户要求「图形界面也必须能够调控参数，还有阈值」）：

- **两类可调项**：
  - ``数值阈值`` —— 有量纲、有上下界的数（命令超时、输出截断长度、扫描条数…）；
  - ``运行参数`` —— 枚举/路径/布尔型的运行选项（架构档位、报告落点、二维码后端…）。
- **真实生效**：每一条都登记了 ``apply``（生效点说明），并在 ``native/common.py``、
  ``native/importio.py``、``cli.py`` 中被真实消费；**不存在只显示不生效的装饰参数**。
- **配置落地**：``~/.config/sysweeper/settings.json``，键为 setting key。
  读配置时与默认值合并，未知 key 忽略、越界/类型错的值拒绝并回退默认，
  保证旧配置与手改坏的配置都不阻断工具运行。
- **零依赖**：本模块不 import 任何 sysweeper 模块（避免与 common 层循环导入），
  也不 import 第三方库，任何平台都能安全导入。

红线（与全工具一致）：本模块只读写用户自己的配置文件，**绝不**执行导入内容、
绝不写系统位置、绝不因配置异常抛错阻断诊断。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

__all__ = [
    "Setting", "SETTINGS", "BY_KEY", "ALL_KEYS",
    "GROUP_THRESHOLD", "GROUP_RUNTIME", "GROUP_IMPORT",
    "CONFIG_DIR", "CONFIG_PATH", "HISTORY_PATH", "HISTORY_LIMIT",
    "defaults", "values", "load", "save", "get", "set_value",
    "validate", "reset", "reload", "list_settings", "groups",
    "apply_updates", "settings_report",
    # v0.6.24：变更留痕与实时联动
    "on_change", "history", "record_change", "clear_history", "history_report",
    "changed_keys",
]

# 配置落点：~/.config/sysweeper/settings.json
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "sysweeper")
CONFIG_PATH = os.path.join(CONFIG_DIR, "settings.json")

# 分组标签
GROUP_THRESHOLD = "数值阈值"
GROUP_RUNTIME = "运行参数"
GROUP_IMPORT = "导入/二维码"

# 类型标签
KIND_INT = "int"
KIND_BOOL = "bool"
KIND_ENUM = "enum"
KIND_PATH = "path"
KIND_STR = "str"


@dataclass(frozen=True)
class Setting:
    """一个可在 GUI/CLI 中调控的参数或阈值。

    key     : 唯一标识（配置文件与 CLI `--set key=value` 均用 key）。
    label   : 中文展示名。
    kind    : int / bool / enum / path / str。
    default : 默认值（同时决定类型）。
    group   : 分组（数值阈值 / 运行参数 / 导入/二维码）。
    desc    : 一句话说明。
    unit    : 单位（仅数值型）。
    min/max : 数值型上下界（含端点）；None 表示不限。
    choices : 枚举可选值元组。
    apply   : 生效点（真实消费位置），用于 GUI 提示与文档对账。
    """
    key: str
    label: str
    kind: str
    default: object
    group: str
    desc: str
    unit: str = ""
    min: object = None
    max: object = None
    choices: Tuple[str, ...] = field(default_factory=tuple)
    apply: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# 单一事实源：所有可调参数与阈值（每条都有真实生效点）
# ─────────────────────────────────────────────────────────────────────────────
_ARCH_CHOICES = ("auto", "any", "loongarch", "mips", "riscv",
                 "openpower", "openrisc", "x86", "arm", "open_hardware")
_PROFILE_CHOICES = ("", "minimal", "lite", "standard", "full")
_LOCALE_CHOICES = ("", "zh_CN", "zh_TW", "en", "en_US", "fr", "fr_FR", "de", "de_DE",
                   "ru", "ru_RU", "ja", "ja_JP", "ko_KR", "es_ES", "pt_BR", "it_IT",
                   "vi_VN", "id_ID")
_QR_CHOICES = ("auto", "cv2", "pyzbar")
_CLIP_CHOICES = ("auto", "tk", "xclip", "xsel", "wl-copy", "osascript", "powershell")

SETTINGS: List[Setting] = [
    # ── 数值阈值 ──
    Setting("cmd.timeout", "命令执行超时", KIND_INT, 120, GROUP_THRESHOLD,
            "单条只读诊断命令的最长等待时间，超时按失败处理",
            unit="秒", min=1, max=3600,
            apply="native/common.py run() 的默认 timeout（显式传参优先）"),
    Setting("cmd.tail", "输出截断长度", KIND_INT, 2000, GROUP_THRESHOLD,
            "命令输出只保留末尾多少字符，防止超长输出灌爆报告；0 = 不截断",
            unit="字符", min=0, max=200000,
            apply="native/common.py run() 的默认 tail（显式传参优先）"),
    Setting("scan.limit", "扫描条数上限", KIND_INT, 10, GROUP_THRESHOLD,
            "体积榜/列表类只读扫描最多返回多少条",
            unit="条", min=1, max=1000,
            apply="common.large_dirs_report / find_large_subdirs 的默认条数"),
    Setting("import.max_bytes", "导入读入上限", KIND_INT, 1048576, GROUP_THRESHOLD,
            "从剪贴板/文件/二维码导入时最多读入多少字节，防止大文件拖死界面",
            unit="字节", min=1024, max=52428800,
            apply="native/importio.py 所有来源的统一读入上限"),
    Setting("qr.camera_timeout", "摄像头扫码超时", KIND_INT, 20, GROUP_THRESHOLD,
            "摄像头扫码最多取多少秒画面，超时即结束（不阻塞界面）",
            unit="秒", min=1, max=120,
            apply="native/importio.py 摄像头扫码循环上限"),

    # ── 运行参数 ──
    Setting("scan.root", "大目录扫描根目录", KIND_PATH, "~", GROUP_RUNTIME,
            "体积榜默认扫描哪个目录（~ 表示家目录）",
            apply="common.large_dirs_report 的默认根目录"),
    Setting("arch", "架构/指令集档位", KIND_ENUM, "auto", GROUP_RUNTIME,
            "架构维度过滤：auto=按当前运行架构，any=不过滤",
            choices=_ARCH_CHOICES, apply="cli.py --arch 的默认值"),
    Setting("profile", "任务档位", KIND_ENUM, "", GROUP_RUNTIME,
            "任务筛选档位：空=沿用命令行行为，minimal=零风险只读，full=全量含 opt-in",
            choices=_PROFILE_CHOICES, apply="cli.py --profile 的默认值"),
    Setting("channel", "版本通道", KIND_ENUM, "stable", GROUP_RUNTIME,
            "发布流选择：stable=常态稳定版，lts=长期支持版，fresh=尝鲜版；"
            "仅作更新检查标记，绝不自动切换或升级",
            choices=("stable", "lts", "fresh"),
            apply="updater.check() 的发布流标记（只看不升级；是否更新由用户确认）"),
    Setting("locale", "界面语言(i18n)", KIND_ENUM, "", GROUP_RUNTIME,
            "界面语言；空=跟随环境（SYSWEEPER_LOCALE / 系统默认）",
            choices=_LOCALE_CHOICES, apply="cli.py --locale 的默认值"),
    Setting("report.path", "报告默认落点", KIND_STR, "", GROUP_RUNTIME,
            "生成前后对比报告的默认路径；空=每次命令行指定",
            apply="cli.py --report 的默认值"),

    # ── 导入 / 二维码 ──
    Setting("qr.backend", "二维码解码后端", KIND_ENUM, "auto", GROUP_IMPORT,
            "二维码解码优先用哪个后端：auto=OpenCV→pyzbar 依次降级",
            choices=_QR_CHOICES, apply="native/importio.py 解码后端选择"),
    Setting("qr.camera_index", "摄像头编号", KIND_INT, 0, GROUP_IMPORT,
            "扫码用第几个摄像头（笔记本内置通常为 0）",
            unit="号", min=0, max=8,
            apply="native/importio.py 摄像头扫码的 VideoCapture 索引"),
    Setting("clipboard.backend", "剪贴板后端", KIND_ENUM, "auto", GROUP_IMPORT,
            "剪贴板读取方式：auto=按平台自动挑（Linux: xclip/xsel/wl-copy；"
            "macOS: osascript；Windows: powershell；都不行回退 tk）",
            choices=_CLIP_CHOICES, apply="native/importio.py 剪贴板读取后端"),
]

BY_KEY: Dict[str, Setting] = {s.key: s for s in SETTINGS}
ALL_KEYS: List[str] = [s.key for s in SETTINGS]


# ─────────────────────────────────────────────────────────────────────────────
# 校验：类型 + 范围 + 枚举；越界/类型错一律拒绝（不静默接受）
# ─────────────────────────────────────────────────────────────────────────────
def validate(key: str, value: object) -> Tuple[bool, object, str]:
    """校验一个取值，返回 (是否接受, 归一化后的值, 理由)。

    不接受时返回默认值与理由，调用方可据此提示用户（GUI 弹提示 / CLI 打印）。
    """
    s = BY_KEY.get(key)
    if s is None:
        return False, None, f"未知参数: {key}"
    try:
        if s.kind == KIND_INT:
            v = int(value)  # type: ignore[arg-type]
            if s.min is not None and v < int(s.min):
                return False, s.default, f"{s.label} 不能小于 {s.min}{s.unit}"
            if s.max is not None and v > int(s.max):
                return False, s.default, f"{s.label} 不能大于 {s.max}{s.unit}"
            return True, v, ""
        if s.kind == KIND_BOOL:
            if isinstance(value, bool):
                return True, value, ""
            if isinstance(value, str):
                low = value.strip().lower()
                if low in ("1", "true", "yes", "on", "是", "开"):
                    return True, True, ""
                if low in ("0", "false", "no", "off", "否", "关"):
                    return True, False, ""
            return True, bool(value), ""
        if s.kind == KIND_ENUM:
            v = "" if value is None else str(value).strip()
            if s.choices and v not in s.choices:
                return False, s.default, f"{s.label} 只能是: {', '.join(s.choices) or '（空）'}"
            return True, v, ""
        if s.kind == KIND_PATH:
            v = "" if value is None else str(value).strip()
            return True, v, ""
        # str
        return True, "" if value is None else str(value), ""
    except (TypeError, ValueError):
        return False, s.default, f"{s.label} 取值无法识别: {value!r}"


def defaults() -> Dict[str, object]:
    """返回全部参数的默认值。"""
    return {s.key: s.default for s in SETTINGS}


# ─────────────────────────────────────────────────────────────────────────────
# 读 / 写 / 缓存
# ─────────────────────────────────────────────────────────────────────────────
# 缓存签名按 (路径, mtime, size) 失效：同一路径内容一变即重读；
# 测试把 CONFIG_PATH 指到 tmp_path 时路径变化，缓存自然失效。
_CACHE: Optional[Tuple[str, float, int, Dict[str, object]]] = None


def _sig() -> Tuple[str, float, int]:
    try:
        st = os.stat(CONFIG_PATH)
        return (CONFIG_PATH, float(st.st_mtime), int(st.st_size))
    except OSError:
        return (CONFIG_PATH, -1.0, -1)


def reload() -> None:
    """丢弃缓存，下次读取重新解析配置文件（测试与 GUI 手动刷新用）。"""
    global _CACHE
    _CACHE = None


def load() -> Dict[str, object]:
    """读配置并与默认值合并；未知 key 忽略、非法值回退默认、损坏回退全默认。"""
    global _CACHE
    sig = _sig()
    if _CACHE is not None and _CACHE[:3] == sig:
        return dict(_CACHE[3])

    vals = defaults()
    try:
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                user = json.load(fh)
            if isinstance(user, dict):
                for k, v in user.items():
                    if k not in BY_KEY:
                        continue  # 未知 key 静默忽略（旧配置/手改残留不致命）
                    ok, norm, _why = validate(k, v)
                    if ok:
                        vals[k] = norm
    except (OSError, ValueError):
        pass  # 配置损坏：安全回退默认值
    _CACHE = (sig[0], sig[1], sig[2], dict(vals))
    return dict(vals)


# 供消费方书写的语义化别名
values = load


def save(vals: Dict[str, object]) -> None:
    """写入配置文件（仅写已知 key，未知 key 丢弃）。失败不抛（降级为仅当前进程生效）。"""
    data: Dict[str, object] = {}
    for k in ALL_KEYS:
        v = vals.get(k, BY_KEY[k].default)
        ok, norm, _why = validate(k, v)
        data[k] = norm if ok else BY_KEY[k].default
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    except OSError:
        pass
    reload()


def get(key: str, fallback: object = None) -> object:
    """取一个参数当前值；未知 key 返回 fallback（不抛）。"""
    s = BY_KEY.get(key)
    if s is None:
        return fallback
    v = load().get(key, s.default)
    return v if v is not None else s.default


def set_value(key: str, value: object, source: str = "", origin: str = "",
              note: str = "") -> Tuple[bool, object, str]:
    """设置单个参数并落盘，返回 (是否接受, 实际生效值, 理由)。

    source/origin/note 用于**变更留痕**（谁从哪改的），可省略。
    """
    ok, norm, why = validate(key, value)
    if not ok:
        return False, norm, why
    vals = load()
    old = vals.get(key, BY_KEY[key].default)
    vals[key] = norm
    save(vals)
    if old != norm:
        _commit({key: (old, norm)}, source, origin, note)
    return True, norm, ""


def apply_updates(pairs: Dict[str, object], source: str = "", origin: str = "",
                  note: str = "") -> List[Tuple[str, bool, str]]:
    """批量更新（GUI「保存」按钮一次写多项 / 导入内容载入）。

    返回逐项结果 [(key, 是否接受, 理由)]；**部分失败不影响其余项**。
    **只有值真的变了才记入留痕**，重复保存同一个值不产生噪音记录。
    """
    results: List[Tuple[str, bool, str]] = []
    vals = load()
    changed: Dict[str, Tuple[object, object]] = {}
    any_ok = False
    for k, v in pairs.items():
        ok, norm, why = validate(k, v)
        if ok:
            old = vals.get(k, BY_KEY[k].default)
            if old != norm:
                changed[k] = (old, norm)
            vals[k] = norm
            any_ok = True
        results.append((k, ok, why))
    if any_ok:
        save(vals)
    if changed:
        _commit(changed, source, origin, note)
    return results


def reset(source: str = "", origin: str = "") -> Dict[str, object]:
    """恢复全部默认值并落盘，返回恢复后的值。"""
    old = load()
    vals = defaults()
    save(vals)
    changed = {k: (old.get(k, v), v) for k, v in vals.items() if old.get(k, v) != v}
    if changed:
        _commit(changed, source or "reset", origin, "恢复默认")
    return vals


def changed_keys() -> List[str]:
    """返回当前与默认值不同的参数 key 列表（供 GUI 高亮「已改动」）。"""
    vals = load()
    return [s.key for s in SETTINGS if vals.get(s.key, s.default) != s.default]


# ─────────────────────────────────────────────────────────────────────────────
# v0.6.24：变更留痕 —— 记下「哪几项、从什么改成什么、从哪来、什么时候」
# ─────────────────────────────────────────────────────────────────────────────
# 只记**参数键与值**以及来源标识，**绝不记录导入的全文内容**
# （导入内容可能含敏感信息，留痕只需要能回答「这项谁改的」）。
HISTORY_PATH = os.path.join(CONFIG_DIR, "settings-history.json")
HISTORY_LIMIT = 200

# 变更观察者：GUI 各窗口订阅后可在他处改参数时自动刷新（实时联动）
_LISTENERS: List[Callable[[Dict[str, Tuple[object, object]]], None]] = []


def on_change(fn: Callable[[Dict[str, Tuple[object, object]]], None]) -> None:
    """订阅参数变更；回调收到 {key: (旧值, 新值)}。回调抛错不影响保存。"""
    if fn not in _LISTENERS:
        _LISTENERS.append(fn)


def _notify(changes: Dict[str, Tuple[object, object]]) -> None:
    if not changes:
        return
    for fn in list(_LISTENERS):
        try:
            fn(dict(changes))
        except Exception:  # noqa: BLE001 - 订阅方异常绝不阻断写入
            pass


def _commit(changes: Dict[str, Tuple[object, object]], source: str = "",
            origin: str = "", note: str = "") -> None:
    """落盘 + 留痕 + 通知，三件事一起做（顺序固定：先生效再通知）。"""
    record_change(changes, source=source, origin=origin, note=note)
    _notify(changes)


def _load_history() -> List[dict]:
    try:
        if os.path.isfile(HISTORY_PATH):
            with open(HISTORY_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, list):
                return [r for r in data if isinstance(r, dict)]
    except (OSError, ValueError):
        pass
    return []


def history(limit: int = 50) -> List[dict]:
    """读取变更留痕（最近 limit 条，最新在最后）。"""
    rows = _load_history()
    return rows[-limit:] if limit and limit > 0 else rows


def record_change(changes: Dict[str, Tuple[object, object]], source: str = "",
                  origin: str = "", note: str = "") -> None:
    """写入一条变更留痕：时间 + 来源 + 逐项 旧值→新值。"""
    if not changes:
        return
    rows = _load_history()
    rows.append({
        "ts": datetime.now().isoformat(timespec="seconds"),
        "source": source or "unknown",
        "origin": origin or "",
        "note": note or "",
        "changes": {k: {"from": v[0], "to": v[1]} for k, v in changes.items()},
    })
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(HISTORY_PATH, "w", encoding="utf-8") as fh:
            json.dump(rows[-HISTORY_LIMIT:], fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    except OSError:
        pass  # 留痕写不进去不影响参数本身生效


def clear_history() -> None:
    """清空变更留痕（用户主动清理；参数值本身不变）。"""
    try:
        if os.path.isfile(HISTORY_PATH):
            os.remove(HISTORY_PATH)
    except OSError:
        pass


def history_report(limit: int = 20) -> Tuple[bool, str]:
    """变更留痕报告（只读，供 GUI/CLI 展示「谁在什么时候改了什么」）。"""
    rows = history(limit)
    if not rows:
        return True, f"暂无变更留痕（落点: {HISTORY_PATH}）"
    lines = [f"参数变更留痕（最近 {len(rows)} 条，落点: {HISTORY_PATH}）:"]
    for r in rows:
        src = r.get("source", "?")
        org = r.get("origin", "")
        head = f"  · {r.get('ts', '?')}  [{src}" + (f" · {org}" if org else "") + "]"
        lines.append(head)
        for k, ch in (r.get("changes") or {}).items():
            lines.append(f"      {k}: {ch.get('from')} → {ch.get('to')}")
        if r.get("note"):
            lines.append(f"      备注: {r['note']}")
    return True, "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 查询接口（供 CLI `settings` 子命令与 GUI 参数窗口消费）
# ─────────────────────────────────────────────────────────────────────────────
def list_settings() -> List[Dict[str, object]]:
    """返回全部参数信息（含当前值），供 CLI/GUI 渲染。"""
    vals = load()
    return [
        {
            "key": s.key,
            "label": s.label,
            "kind": s.kind,
            "group": s.group,
            "default": s.default,
            "value": vals.get(s.key, s.default),
            "unit": s.unit,
            "min": s.min,
            "max": s.max,
            "choices": list(s.choices),
            "desc": s.desc,
            "apply": s.apply,
        }
        for s in SETTINGS
    ]


def groups() -> List[str]:
    """返回分组顺序（数值阈值 → 运行参数 → 导入/二维码）。"""
    order = [GROUP_THRESHOLD, GROUP_RUNTIME, GROUP_IMPORT]
    seen = [g for g in order if any(s.group == g for s in SETTINGS)]
    for s in SETTINGS:  # 兜底：未来新增分组也能列出
        if s.group not in seen:
            seen.append(s.group)
    return seen


def settings_report() -> Tuple[bool, str]:
    """参数与阈值总览报告（只读，供 sysmap/控制台展示）。"""
    vals = load()
    lines = [f"参数与阈值（共 {len(SETTINGS)} 项，配置落点: {CONFIG_PATH}）:"]
    for g in groups():
        items = [s for s in SETTINGS if s.group == g]
        lines.append(f"  [{g}] {len(items)} 项")
        for s in items:
            v = vals.get(s.key, s.default)
            unit = f" {s.unit}" if s.unit else ""
            rng = ""
            if s.min is not None or s.max is not None:
                rng = f"（{s.min if s.min is not None else '-∞'} ~ {s.max if s.max is not None else '∞'}）"
            ch = f"可选: {'/'.join(s.choices)}" if s.choices else ""
            lines.append(f"    - {s.key} = {v}{unit}  {rng}{ch}  # {s.label}")
    return True, "\n".join(lines)
