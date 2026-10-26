"""统一 JSON 接口层（v0.6.26）——给 Deno Web 控制台 / 远端报告查看器 / 任何外部前端用的**唯一后端**。

为什么要这一层
--------------
GUI（tkinter）能做的事，浏览器里也想做：调参数与阈值、开关子系统、跑单子系统只读诊断、
导入外部内容、看变更留痕。**但不打算把这些逻辑用 TypeScript 再写一遍**——
两套实现迟早对不上，且本机硬件/sysfs/注册表的读取只有 Python 侧写全了。

所以定下架构：**Python 当逻辑层，Deno 只做 HTTP 外壳**。本模块把 GUI/CLI 已经在用的能力
（``native.settings`` / ``native.subsystems`` / ``native.sysmap`` / ``native.importio``）
按同一套 JSON 协议再暴露一次，前端只管渲染。

协议
----
请求一行一个 JSON（JSONL，便于长连接复用一个 Python 进程，省掉每次冷启动）：:

    {"action": "settings.set", "params": {"pairs": {"cmd.timeout": 300}}, "source": "web"}

响应同样一行一个 JSON：::

    {"ok": true, "action": "settings.set", "data": {...}}

失败时 ``ok=false`` 且带 ``error``；**永不抛异常打断循环**。

红线（比 GUI 更严，因为这里可能被远程/浏览器触达）
-------------------------------------------------
1. **只暴露只读诊断 + 用户自己的配置文件读写**。任何「清理/应用/启停服务/写系统位置」
   的动作都不在 ``ACTIONS`` 白名单里，传进来也只会被拒。
2. **动作白名单制**：``dispatch`` 认不出的 action 一律拒绝，**没有兜底的 getattr 动态派发**，
   杜绝「前端传个函数名就被执行」。
3. 诊断只跑 ``native.subsystems`` 登记过的只读报告函数，**不执行导入内容**、不 eval。
4. 读到的诊断正文默认截断（``max_chars``），防止超长输出灌爆前端。

用法
----
- 命令行一次性调用：``python -m sysweeper webapi --once '{"action":"ping"}'``
- 长连接（Deno 控制台用）：``python -m sysweeper webapi`` 然后从 stdin 一行行喂请求。
- 库内直接调：``from sysweeper.webapi import dispatch``
"""
from __future__ import annotations

import importlib
import json
import platform
import sys
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import __version__

__all__ = [
    "ACTIONS", "dispatch", "dispatch_text", "run_loop", "build_report", "schema_version",
]

SCHEMA = "sysweeper-webapi/1"
REPORT_SCHEMA = "sysweeper-report/1"

# 诊断正文默认截断长度（字符）；前端可传 max_chars 覆盖，上限 200000
_TEXT_CAP_DEFAULT = 20000
_TEXT_CAP_HARD = 200000

# 单次 diagnose 最多跑多少个子系统，防止前端误传全量把机器拖死
_DIAGNOSE_MAX_KEYS = 60


# ─────────────────────────────────────────────────────────────────────────────
# 基础工具
# ─────────────────────────────────────────────────────────────────────────────
def _cap(text: str, max_chars: int) -> Tuple[str, bool]:
    """按字符上限截断，返回 (正文, 是否被截断)。"""
    s = "" if text is None else str(text)
    n = max(0, int(max_chars or _TEXT_CAP_DEFAULT))
    n = min(n, _TEXT_CAP_HARD)
    if n and len(s) > n:
        return s[:n], True
    return s, False


def _status_of(ok: bool, msg: str) -> str:
    """把单个子系统的诊断结果归为 4 档：正常 / 提示 / 不适用 / 异常。

    与 ``native.sysmap._classify`` 口径一致（这里独立实现一份，避免依赖私有函数）。
    """
    na_markers = ("未安装", "未检测到", "未运行", "未启用", "未找到",
                  "不适用", "非 Windows", "非游戏平台", "无数据", "N/A", "n/d")
    if any(m in msg for m in na_markers):
        return "不适用"
    if not ok:
        return "不适用"
    if any(m in msg for m in ("警告", "注意", "需关注", "异常", "失败",
                              "缺失", "未配置", "未开启", "风险", "不可用")):
        return "提示"
    return "正常"


def _oneline(msg: str, limit: int = 120) -> str:
    """从报告正文抽第一行实质内容（跳过分隔线），截断成紧凑状态串。"""
    skip = set("─═━┄┅│+-=· ")
    raw = [l.strip() for l in str(msg or "").splitlines() if l.strip()]
    if not raw:
        return ""
    nonbox = [l for l in raw if set(l) > skip]
    return (nonbox[0] if nonbox else raw[0])[:limit]


def _host_info() -> Dict[str, Any]:
    """只读的宿主环境信息（不采集任何可识别个人的内容）。"""
    try:
        from .detect import detect
        d = detect()
    except Exception:  # noqa: BLE001 - 探测失败不该让接口挂掉
        d = {}
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "detected": d,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 动作实现
#   每个 handler: (params: dict, ctx: dict) -> Any（会被包进 {"ok":true,"data":...}）
#   登记项第三字段：readonly —— True 表示只读；False 表示「只写用户自己的配置文件」
# ─────────────────────────────────────────────────────────────────────────────
def _a_ping(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from .native import settings as st
    from .native import subsystems as subs
    return {
        "schema": SCHEMA,
        "version": __version__,
        "time": datetime.now().isoformat(timespec="seconds"),
        "settings_count": len(st.ALL_KEYS),
        "subsystem_count": len(subs.ALL_KEYS),
        "config_dir": st.CONFIG_DIR,
        "readonly_only": True,
        "host": _host_info() if p.get("host") else None,
    }


def _a_manifest(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": __version__,
        "actions": [
            {"action": name, "readonly": meta[1], "desc": meta[2]}
            for name, meta in ACTIONS.items()
        ],
    }


# ── 参数与阈值 ────────────────────────────────────────────────────────────────
def _a_settings_list(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from .native import settings as st
    return {
        "items": st.list_settings(),
        "groups": st.groups(),
        "changed": st.changed_keys(),
        "config_path": st.CONFIG_PATH,
        "history_path": st.HISTORY_PATH,
    }


def _a_settings_get(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from .native import settings as st
    key = str(p.get("key", "")).strip()
    if not key:
        raise ValueError("缺少参数 key")
    if key not in st.BY_KEY:
        raise KeyError(f"未知参数: {key}")
    return {"key": key, "value": st.get(key), "default": st.BY_KEY[key].default}


def _a_settings_set(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from .native import settings as st
    pairs = p.get("pairs")
    if not isinstance(pairs, dict) or not pairs:
        raise ValueError("缺少参数 pairs（对象，形如 {\"cmd.timeout\": 300}）")
    results = st.apply_updates(
        pairs,
        source=str(p.get("source", "") or ctx.get("source", "") or "webapi"),
        origin=str(p.get("origin", "") or "web"),
        note=str(p.get("note", "") or ""),
    )
    return {
        "results": [{"key": k, "ok": ok, "why": why, "value": st.get(k)} for k, ok, why in results],
        "changed": st.changed_keys(),
    }


def _a_settings_reset_one(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from .native import settings as st
    key = str(p.get("key", "")).strip()
    if key not in st.BY_KEY:
        raise KeyError(f"未知参数: {key}")
    ok, val, why = st.set_value(
        key, st.BY_KEY[key].default,
        source=str(p.get("source", "") or "webapi"), origin="web", note="单项复位",
    )
    return {"key": key, "ok": ok, "value": val, "why": why, "changed": st.changed_keys()}


def _a_settings_reset(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from .native import settings as st
    vals = st.reset(source=str(p.get("source", "") or "webapi"), origin="web")
    return {"values": vals, "changed": st.changed_keys()}


def _a_settings_history(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from .native import settings as st
    try:
        limit = int(p.get("limit", 50))
    except (TypeError, ValueError):
        limit = 50
    return {"rows": st.history(limit), "limit": st.HISTORY_LIMIT}


def _a_settings_history_clear(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from .native import settings as st
    st.clear_history()
    return {"cleared": True}


# ── 子系统开关 ────────────────────────────────────────────────────────────────
def _a_subsystems_list(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from .native import subsystems as subs
    return {"items": subs.list_subsystems(), "config_path": subs.CONFIG_PATH}


def _a_subsystems_set(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from .native import subsystems as subs
    key = str(p.get("key", "")).strip()
    if not key:
        raise ValueError("缺少参数 key")
    on = p.get("on", True)
    if isinstance(on, str):
        on = on.strip().lower() not in ("0", "false", "no", "off", "关", "否")
    ok = subs.set_enabled(key, bool(on))
    if not ok:
        raise KeyError(f"未知子系统: {key}")
    return {"key": key, "enabled": bool(on), "items": subs.list_subsystems()}


def _a_subsystems_set_many(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from .native import subsystems as subs
    pairs = p.get("pairs")
    if not isinstance(pairs, dict) or not pairs:
        raise ValueError("缺少参数 pairs（对象，形如 {\"tor\": false}）")
    applied, rejected = {}, []
    for k, v in pairs.items():
        if isinstance(v, str):
            v = v.strip().lower() not in ("0", "false", "no", "off", "关", "否")
        if subs.set_enabled(str(k), bool(v)):
            applied[str(k)] = bool(v)
        else:
            rejected.append(str(k))
    return {"applied": applied, "rejected": rejected, "items": subs.list_subsystems()}


def _a_subsystems_all(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from .native import subsystems as subs
    on = p.get("on", True)
    if isinstance(on, str):
        on = on.strip().lower() not in ("0", "false", "no", "off", "关", "否")
    on = bool(on)
    for s in subs.SUBSYSTEMS:
        subs.set_enabled(s.key, on)
    return {"all": on, "count": len(subs.SUBSYSTEMS), "items": subs.list_subsystems()}


# ── 只读诊断 ──────────────────────────────────────────────────────────────────
def _run_one(sub_key: str, max_chars: int) -> Dict[str, Any]:
    """跑一个在册子系统的只读报告函数；异常只标「异常」，绝不外抛。"""
    from .native import subsystems as subs
    s = subs.BY_KEY.get(sub_key)
    if s is None:
        return {"key": sub_key, "status": "异常", "summary": "未知子系统", "text": "", "truncated": False}
    try:
        mod = importlib.import_module("sysweeper.native." + s.module)
        fn = getattr(mod, s.fn)
        r = fn()
    except Exception as exc:  # noqa: BLE001 - 单个子系统炸了不能带走整张总览
        return {"key": sub_key, "label": s.label, "layer": s.layer, "status": "异常",
                "summary": f"{type(exc).__name__}: {exc}", "text": "", "truncated": False}
    if isinstance(r, tuple):
        ok = bool(r[0]) if r else False
        msg = str(r[1]) if len(r) > 1 else ""
    elif isinstance(r, list):
        ok, msg = True, "\n".join(str(x) for x in r)
    else:
        ok, msg = True, str(r)
    body, truncated = _cap(msg, max_chars)
    return {
        "key": sub_key, "label": s.label, "layer": s.layer,
        "status": _status_of(ok, msg), "summary": _oneline(msg),
        "text": body, "truncated": truncated,
    }


def _a_diagnose(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from .native import subsystems as subs
    keys = p.get("keys")
    if keys is None:
        key = str(p.get("key", "")).strip()
        keys = [key] if key else [s.key for s in subs.enabled_subsystems()]
    if isinstance(keys, str):
        keys = [k.strip() for k in keys.split(",") if k.strip()]
    keys = [str(k) for k in keys][:_DIAGNOSE_MAX_KEYS]
    try:
        max_chars = int(p.get("max_chars", _TEXT_CAP_DEFAULT))
    except (TypeError, ValueError):
        max_chars = _TEXT_CAP_DEFAULT
    items = [_run_one(k, max_chars) for k in keys]
    tally: Dict[str, int] = {}
    for it in items:
        tally[it["status"]] = tally.get(it["status"], 0) + 1
    return {"items": items, "tally": tally, "count": len(items)}


def _a_sysmap(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from .native import sysmap as sm
    try:
        max_chars = int(p.get("max_chars", _TEXT_CAP_DEFAULT))
    except (TypeError, ValueError):
        max_chars = _TEXT_CAP_DEFAULT
    ok, msg = sm.sysmap_report()
    body, truncated = _cap(msg, max_chars)
    return {"ok": bool(ok), "text": body, "truncated": truncated, "status": _status_of(bool(ok), msg)}


def _a_sysmap_capabilities(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from .native import sysmap as sm
    ok, msg = sm.capabilities_report()
    return {"ok": bool(ok), "text": str(msg)}


# ── 导入（外部内容：剪贴板 / 文件 / 图片二维码 / 摄像头）────────────────────────
def _a_import_capabilities(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from .native import importio as io_
    from .native import settings as st
    return {
        "sources": [{"key": k, "label": lab, "desc": desc} for k, lab, desc in io_.SOURCES],
        "clipboard_backends": io_.clipboard_backends(),
        "qr_backends": io_.qr_backends(),
        "max_bytes": st.get("import.max_bytes", 1048576),
    }


def _a_import_read(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from .native import importio as io_
    src = str(p.get("source", "") or io_.SRC_CLIPBOARD).strip().lower()
    path = str(p.get("path", "") or "")
    try:
        max_chars = int(p.get("max_chars", _TEXT_CAP_DEFAULT))
    except (TypeError, ValueError):
        max_chars = _TEXT_CAP_DEFAULT
    r = io_.import_from(src, path)
    body, truncated = _cap(r.text, max_chars)
    return {"source": src, "ok": r.ok, "note": r.note,
            "length": len(r.text), "text": body, "truncated": truncated}


def _a_import_load(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """把导入内容里的设置 JSON 载入为参数（**显式动作**才写配置）。

    与 CLI ``import --as-settings`` 同源：未显式调用本动作时，导入只读取展示，
    绝不落任何配置。
    """
    from .native import importio as io_
    from .native import settings as st
    src = str(p.get("source", "") or io_.SRC_CLIPBOARD).strip().lower()
    path = str(p.get("path", "") or "")
    text = p.get("text", "")
    if text is None or not str(text).strip():
        r = io_.import_from(src, path)
        if not r.ok:
            return {"ok": False, "error": r.note, "applied": [], "rejected": []}
        text = r.text
    ok, accepted, rejected, hint = io_.parse_settings_json(str(text))
    if not ok:
        return {"ok": False, "error": hint, "applied": [], "rejected": rejected}
    origin = path if src in (io_.SRC_FILE, io_.SRC_QR) else (
        f"camera#{st.get('qr.camera_index', 0)}" if src == io_.SRC_CAMERA else "剪贴板")
    results = st.apply_updates(accepted, source=src or "import", origin=origin,
                               note="由导入内容载入")
    return {
        "ok": True,
        "applied": [{"key": k, "ok": o, "why": w} for k, o, w in results if o],
        "rejected": list(rejected) + [k for k, o, _w in results if not o],
        "changed": st.changed_keys(),
        "hint": hint,
    }


# ── 快照报告（给远端报告查看器 / 留档 / 前后对比用）────────────────────────────
def build_report(include: Optional[List[str]] = None,
                 max_chars: int = _TEXT_CAP_DEFAULT) -> Dict[str, Any]:
    """生成一份可脱离本机阅读的诊断快照（纯 JSON，可直接喂给报告查看器）。

    内容：宿主信息 + 参数与阈值 + 变更留痕 + 子系统开关态 + 总览正文 +
    各已开启子系统的诊断正文。**全部只读**，不含任何可执行内容。
    """
    from .native import settings as st
    from .native import subsystems as subs
    from .native import sysmap as sm

    want = set(include) if include else {"host", "settings", "history", "subsystems",
                                         "sysmap", "diagnose", "score", "kmod", "jdk",
                                         "distcompute"}
    rep: Dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "version": __version__,
        "note": "只读诊断快照；由 sysweeper 在本机生成，不含任何可执行内容",
    }
    if "host" in want:
        rep["host"] = _host_info()
    if "settings" in want:
        rep["settings"] = {
            "items": st.list_settings(),
            "changed": st.changed_keys(),
            "config_path": st.CONFIG_PATH,
        }
    if "history" in want:
        rep["history"] = st.history(50)
    if "subsystems" in want:
        items = subs.list_subsystems()
        rep["subsystems"] = {
            "items": items,
            "enabled": [i["key"] for i in items if i["enabled"]],
            "disabled": [i["key"] for i in items if not i["enabled"]],
        }
    if "sysmap" in want:
        ok, msg = sm.sysmap_report()
        body, truncated = _cap(msg, max_chars)
        rep["sysmap"] = {"ok": bool(ok), "text": body, "truncated": truncated,
                         "status": _status_of(bool(ok), msg)}
    if "diagnose" in want:
        keys = [s.key for s in subs.enabled_subsystems()]
        rep["diagnose"] = [_run_one(k, max_chars) for k in keys]
        tally: Dict[str, int] = {}
        for it in rep["diagnose"]:
            tally[it["status"]] = tally.get(it["status"], 0) + 1
        rep["tally"] = tally
    if "score" in want:
        rep["score"] = _build_score(_platform_of({}))
    if "kmod" in want:
        rep["kmod"] = _a_kmod_report({"max_chars": max_chars}, {})
    if "jdk" in want:
        rep["jdk"] = _a_jdk_report({"max_chars": max_chars}, {})
    if "distcompute" in want:
        rep["distcompute"] = _a_distcompute_report({"max_chars": max_chars}, {})
    return rep


# ── 档位 / 量化评分 / 内核模块（只读视图：本机控制台与远端报告共用）──────────
def _platform_of(p: Dict[str, Any]) -> Tuple[str, str]:
    """取平台与版本：参数没给就用本机探测结果（"any" 视为未指定）。"""
    pf = str(p.get("platform") or "").strip()
    ver = str(p.get("version") or "").strip()
    if pf and pf != "any":
        return pf, (ver or "0")
    try:
        from .detect import detect
        d = detect() or {}
        pf = str(d.get("platform") or pf or "linux")
        ver = str(d.get("version") or ver or "0")
    except Exception:  # noqa: BLE001 - 探测失败退回 linux，不该让动作挂掉
        pf, ver = (pf or "linux"), (ver or "0")
    return pf, (ver or "0")


def _cap_of(p: Dict[str, Any]) -> int:
    """从参数取正文截断长度，非法值退回默认，绝不抛。"""
    try:
        n = int(p.get("max_chars", _TEXT_CAP_DEFAULT))
    except (TypeError, ValueError):
        return _TEXT_CAP_DEFAULT
    return max(0, min(n, _TEXT_CAP_HARD))


def _a_profiles_list(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from . import profiles as pf
    platform, version = _platform_of(p)
    items = []
    for name in pf.PROFILE_ORDER:
        spec = pf.PROFILES[name]
        items.append({
            "name": name,
            "title": spec["title"],
            "description": spec["description"],
            "max_risk": spec["max_risk"],
            "include_opt_in": bool(spec["include_opt_in"]),
            "language_agnostic": bool(spec.get("language_agnostic", False)),
            "keyword_exclude": list(spec.get("keyword_exclude") or ()),
            "count": len(pf.tasks_in_profile(name, platform, version)),
        })
    scen = []
    for name, sc in pf.SCENARIOS.items():
        scen.append({
            "name": name,
            "title": sc["title"],
            "description": sc["description"],
            "base": sc["base"],
            "count": len(pf.scenario_tasks(name, platform, version)),
        })
    return {"platform": platform, "version": version,
            "profiles": items, "scenarios": scen}


def _a_profiles_show(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from . import profiles as pf
    platform, version = _platform_of(p)
    name = str(p.get("name") or p.get("profile") or "standard").strip()
    known = list(pf.PROFILE_ORDER) + list(pf.SCENARIOS)
    if name not in known:
        raise ValueError(f"未知档位: {name}（可选 {'/'.join(known)}）")
    try:
        rows_limit = int(p.get("limit", 0) or 0)
    except (TypeError, ValueError):
        rows_limit = 0
    if name in pf.SCENARIOS:
        sc = pf.SCENARIOS[name]
        tasks = pf.scenario_tasks(name, platform, version)
        title, rule = sc["title"], {"base": sc["base"], "kind": "scenario"}
        detail = ""
    else:
        spec = pf.PROFILES[name]
        tasks = pf.tasks_in_profile(name, platform, version)
        title = spec["title"]
        rule = {k: spec[k] for k in ("max_risk", "include_opt_in", "language_agnostic")}
        rule["kind"] = "profile"
        detail, _tr = _cap(pf.profile_detail(name, platform, version), _cap_of(p))
    rows = [{"id": t.id, "title": t.display_title(), "category": t.category,
             "risk": t.risk, "opt_in": bool(t.opt_in)} for t in tasks]
    out = {
        "name": name, "title": title, "rule": rule,
        "platform": platform, "version": version,
        "count": len(tasks),
        "ids": [t.id for t in tasks],
        "detail": detail,
        "detail_truncated": (len(detail) >= _cap_of(p)) if detail else False,
    }
    if rows_limit > 0:
        out["tasks"] = rows[:max(0, min(rows_limit, 500))]
    return out


def _a_profiles_compare(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from . import profiles as pf
    platform, version = _platform_of(p)
    a = str(p.get("name") or p.get("profile") or "minimal").strip()
    b = str(p.get("against") or "full").strip()
    if a not in pf.PROFILES:
        raise ValueError(f"未知档位: {a}（可选 {'/'.join(pf.PROFILE_ORDER)}）")
    if b not in pf.PROFILES:
        raise ValueError(f"未知对照档位: {b}（可选 {'/'.join(pf.PROFILE_ORDER)}）")
    try:
        sample = int(p.get("sample", 12) or 12)
    except (TypeError, ValueError):
        sample = 12
    r = pf.compare_profiles(a, b, platform, version)
    only_a, only_b = r["only_a"], r["only_b"]
    return {
        "a": a, "b": b, "platform": platform, "version": version,
        "count_a": r["count_a"], "count_b": r["count_b"],
        "shared_count": len(r["shared"]),
        "only_a_count": len(only_a), "only_b_count": len(only_b),
        "only_a_sample": only_a[:max(0, sample)],
        "only_b_sample": only_b[:max(0, sample)],
        "jaccard": r["jaccard"],
    }


def _build_score(platform_version: Tuple[str, str]) -> Dict[str, Any]:
    """量化评分段（报告与 score.overview 动作共用）。"""
    from . import profiles as pf
    from . import registry
    from .native import metrics as mt
    platform, version = platform_version
    allt = list(registry.all_tasks())
    dist = mt.category_distribution(allt)
    by_plat: Dict[str, List[Any]] = {}
    for t in allt:
        by_plat.setdefault(str(t.platform), []).append(t)
    return {
        "platform": platform,
        "version": version,
        "total_tasks": len(allt),
        "global_score": mt.coverage_score(allt)["score"],
        "global_parts": mt.coverage_score(allt)["parts"],
        "distribution": dist,
        "entropy_bits": mt.shannon_entropy(list(dist.values())),
        "normalized_entropy": mt.normalized_entropy(list(dist.values())),
        "gini": mt.gini_index(list(dist.values())),
        "gaps": mt.coverage_gaps(allt),
        "platform_balance": mt.platform_balance(by_plat),
        "platform_counts": {k: len(v) for k, v in sorted(by_plat.items(),
                                                          key=lambda kv: -len(kv[1]))},
        "profile_counts": {
            name: len(pf.tasks_in_profile(name, platform, version))
            for name in pf.PROFILE_ORDER
        },
        "text": mt.score_report(allt, "全库覆盖度评分"),
    }


def _a_score_overview(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    return _build_score(_platform_of(p))


def _a_kmod_report(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from .native import kmod as nk
    ok, msg = nk.kmod_report()
    body, truncated = _cap(msg, _cap_of(p))
    env = list(nk.environment_report())
    # 复合报告的档位不能照抄正文关键词（正文里必然夹带「（不适用）xxx」的降级说明），
    # 改为按「可读探针占比」判定，才是这份报告真实要说的事。
    probes = [ln.strip() for ln in env if ln.strip().startswith(("✓", "✗"))]
    avail = sum(1 for ln in probes if ln.startswith("✓"))
    if not probes or avail == 0:
        status = "不适用"
    elif avail == len(probes):
        status = "正常"
    else:
        status = "提示"
    return {
        "status": status,
        "summary": f"{avail}/{len(probes)} 项只读探针可读" if probes else "无可用探针（非 Linux 平台或接口全被屏蔽）",
        "text": body,
        "truncated": truncated,
        "environment": list(nk.environment_report()),
        "docs": [ln.strip() for ln in nk.kmod_doc_list()],
        "forbidden": list(nk.FORBIDDEN_COMMANDS),
        "readonly_only": True,
    }


def _a_jdk_report(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from .native import jdk as nj
    ok, msg = nj.jdk_report()
    body, truncated = _cap(msg, _cap_of(p))
    env = list(nj.environment_report())
    # 复合报告的档位不能照抄正文关键词（没装 JDK 时正文是降级说明），
    # 改为按「可读接口占比」判定，才是这份报告真实要说的事。
    probes = [ln.strip() for ln in env if ln.strip().startswith(("✓", "✗"))]
    avail = sum(1 for ln in probes if ln.startswith("✓"))
    if not probes or avail == 0:
        status = "不适用"
    elif avail == len(probes):
        status = "正常"
    else:
        status = "提示"
    return {
        "status": status,
        "summary": f"{avail}/{len(probes)} 项只读接口可读" if probes else "无可用接口（未安装 JDK 或 java 不在 PATH）",
        "text": body,
        "truncated": truncated,
        "environment": list(nj.environment_report()),
        "docs": [ln.strip() for ln in nj.jdk_doc_list()],
        "forbidden": list(nj.FORBIDDEN_SUBCOMMANDS),
        "readonly_only": True,
    }


def _a_distcompute_report(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from .native import distcompute as ndc
    ok, msg = ndc.distcompute_report()
    body, truncated = _cap(msg, _cap_of(p))
    return {
        "status": _status_of(ok, msg),
        "summary": "分布式计算共享层总报告",
        "text": body,
        "truncated": truncated,
        "readonly_only": True,
    }


def _a_distcompute_watchdog(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from .native import distcompute as ndc
    ok, msg = ndc.watchdog_report()
    body, truncated = _cap(msg, _cap_of(p))
    return {
        "status": _status_of(ok, msg),
        "summary": "看门狗模式说明（只读，不执行重启）",
        "text": body,
        "truncated": truncated,
        "readonly_only": True,
    }


def _a_distcompute_watchdog_restart(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from .native import distcompute as ndc
    plan = ndc.watchdog_restart_plan()
    # 只回命令文本，绝不执行；与 openwrt_write 同口径（readonly=False 表示写意图，但只出文本）
    return plan


def _a_report_build(p: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    inc = p.get("include")
    if isinstance(inc, str):
        inc = [x.strip() for x in inc.split(",") if x.strip()]
    try:
        max_chars = int(p.get("max_chars", _TEXT_CAP_DEFAULT))
    except (TypeError, ValueError):
        max_chars = _TEXT_CAP_DEFAULT
    return build_report(inc, max_chars)


# ─────────────────────────────────────────────────────────────────────────────
# 动作白名单 —— 红线 2：没有动态派发，认不出的 action 一律拒绝
#   (handler, readonly, desc)
# ─────────────────────────────────────────────────────────────────────────────
ACTIONS: Dict[str, Tuple[Callable[[Dict[str, Any], Dict[str, Any]], Any], bool, str]] = {
    # 元信息
    "ping": (_a_ping, True, "连通性自检：版本、参数/子系统数量、配置目录"),
    "manifest": (_a_manifest, True, "列出全部可用动作及其读写性质"),
    # 参数与阈值
    "settings.list": (_a_settings_list, True, "列出全部参数与阈值（含当前值、已改动项）"),
    "settings.get": (_a_settings_get, True, "查一个参数的当前值"),
    "settings.set": (_a_settings_set, False, "批量设置参数（只写用户配置文件）"),
    "settings.reset_one": (_a_settings_reset_one, False, "单项恢复默认值"),
    "settings.reset": (_a_settings_reset, False, "全部恢复默认值"),
    "settings.history": (_a_settings_history, True, "参数变更留痕"),
    "settings.history.clear": (_a_settings_history_clear, False, "清空变更留痕"),
    # 子系统开关
    "subsystems.list": (_a_subsystems_list, True, "列出全部子系统与开/关状态"),
    "subsystems.set": (_a_subsystems_set, False, "开关单个子系统"),
    "subsystems.set_many": (_a_subsystems_set_many, False, "批量开关子系统"),
    "subsystems.all": (_a_subsystems_all, False, "全开/全关子系统"),
    # 只读诊断
    "diagnose": (_a_diagnose, True, "跑单个/多个已开启子系统的只读诊断"),
    "sysmap": (_a_sysmap, True, "系统统筹总览正文"),
    "sysmap.capabilities": (_a_sysmap_capabilities, True, "总览能力清单"),
    # 导入
    "import.capabilities": (_a_import_capabilities, True, "导入来源与可用后端"),
    "import.read": (_a_import_read, True, "按来源读取外部内容（只读取，不落配置）"),
    "import.load": (_a_import_load, False, "把导入的设置 JSON 载入为参数（显式才写）"),
    # 任务档位与量化评估（只读）
    "profiles.list": (_a_profiles_list, True, "列出任务档位与场景档，及当前平台的命中任务数"),
    "profiles.show": (_a_profiles_show, True, "查单个档位的规则、任务清单与覆盖度评分"),
    "profiles.compare": (_a_profiles_compare, True, "对比两个档位：Jaccard 重合度与差集"),
    "score.overview": (_a_score_overview, True, "数学化量化评估：WSM 评分 + Shannon 熵 + 平台均衡度"),
    "kmod.report": (_a_kmod_report, True, "内核 module/firmware/eBPF 只读体检（永不写 sysfs）"),
    "jdk.report": (_a_jdk_report, True, "OpenJDK/JVM 只读体检（java/属性/JPMS/GC/JIT/诊断工具，永不改动 JVM）"),
    "distcompute.report": (_a_distcompute_report, True, "分布式计算共享层总报告（能力/算子/计划/记账，只读）"),
    "distcompute.watchdog": (_a_distcompute_watchdog, True, "看门狗模式说明（只读，绝不自动重启）"),
    "distcompute.watchdog_restart": (_a_distcompute_watchdog_restart, False, "看门狗重启计划（只出命令文本，绝不执行写操作）"),
    # 快照报告
    "report.build": (_a_report_build, True, "生成可分享的只读诊断快照 JSON"),
}


def schema_version() -> str:
    """接口协议版本号（前端据此判断兼容）。"""
    return SCHEMA


# ─────────────────────────────────────────────────────────────────────────────
# 派发
# ─────────────────────────────────────────────────────────────────────────────
def dispatch(req: Any, ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """处理一个请求对象，返回响应字典（**永不抛异常**）。

    req 形如 ``{"action": "...", "params": {...}, "source": "..."}``。
    未知 action / 参数错 / 子系统炸了，一律转成 ``ok=false`` + ``error``。
    """
    ctx = dict(ctx or {})
    if not isinstance(req, dict):
        return {"ok": False, "action": "", "error": "请求必须是 JSON 对象"}
    action = str(req.get("action", "") or "").strip()
    if not action:
        return {"ok": False, "action": "", "error": "缺少 action"}
    meta = ACTIONS.get(action)
    if meta is None:
        return {"ok": False, "action": action,
                "error": f"未知动作: {action}（可用动作见 manifest）"}
    handler, readonly, _desc = meta
    params = req.get("params")
    params = params if isinstance(params, dict) else {}
    try:
        data = handler(params, ctx)
    except KeyError as exc:
        return {"ok": False, "action": action, "error": str(exc).strip("'\"")}
    except ValueError as exc:
        return {"ok": False, "action": action, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001 - 任何意外都不许打断长连接
        return {"ok": False, "action": action,
                "error": f"{type(exc).__name__}: {exc}"}
    return {"ok": True, "action": action, "readonly": readonly, "data": data}


def dispatch_text(line: str, ctx: Optional[Dict[str, Any]] = None) -> str:
    """处理一行请求文本，返回一行响应文本（JSONL 长连接用）。"""
    try:
        req = json.loads(line)
    except ValueError as exc:
        return json.dumps({"ok": False, "action": "", "error": f"JSON 解析失败: {exc}"},
                          ensure_ascii=False)
    return json.dumps(dispatch(req, ctx), ensure_ascii=False)


def run_loop(stdin=None, stdout=None, ctx: Optional[Dict[str, Any]] = None) -> int:
    """JSONL 长连接：一行请求 → 一行响应，直到 EOF。

    Deno 控制台起一个本进程常驻，逐行喂请求，省掉每次调用的解释器冷启动。
    空行跳过；单行解析失败只回一条错误，连接继续。
    """
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    for raw in stdin:
        line = raw.strip()
        if not line:
            continue
        stdout.write(dispatch_text(line, ctx) + "\n")
        stdout.flush()
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """命令行入口：``sysweeper webapi [--once JSON] [--pretty]``。"""
    import argparse
    ap = argparse.ArgumentParser(prog="sysweeper webapi",
                                 description="统一 JSON 接口（一行请求一行响应；不带 --once 则走长连接）")
    ap.add_argument("--once", metavar="JSON", default="",
                    help="只处理这一条请求（JSON 文本），输出后退出")
    ap.add_argument("--pretty", action="store_true", help="缩进输出（调试用，长连接下无效）")
    args = ap.parse_args(argv)
    if args.once:
        resp = dispatch_text(args.once)
        if args.pretty:
            try:
                resp = json.dumps(json.loads(resp), ensure_ascii=False, indent=2)
            except ValueError:
                pass
        print(resp)
        return 0
    return run_loop()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
