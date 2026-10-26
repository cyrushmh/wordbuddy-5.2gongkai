"""GUI 开关状态的持久化：把「开了什么、关了什么」记住。

为什么需要它
------------
图形界面里用户勾的每一项（启用哪个优化项、停用哪个插件、用哪个档位）都是**用户偏好**。
不持久化的话，每次打开界面都要重新勾一遍——那只是演示，不是能用的产品。

设计边界
--------
- **只存标识符**：任务 id、插件 id、平台名这类字符串。**不存任何命令、不存代码、不执行**，
  与插件系统的白名单安全模型一致（见 native/plugins.py）。
- **与档位（profiles）分开**：档位是代码里定义的预设（minimal/standard/full…），
  这里存的是「用户实际选择」，用户选择**覆盖**档位默认值。
- **坏了也不许崩界面**：配置缺失/损坏/版本不认识 → 回退默认值，绝不抛异常给 GUI。

存储位置遵循 XDG Base Directory 规范：
- `$XDG_CONFIG_HOME/sysweeper/gui.json`，未设则为 `~/.config/sysweeper/gui.json`
- 若家目录不可写（受限环境），降级为内存态（本次会话有效，关闭即忘）。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

SCHEMA = 1

DEFAULT: Dict = {
    "schema": SCHEMA,
    # --- 适配当前系统 ---
    "follow_system": True,   # 启动时是否自动探测并套用当前系统（False 则用上次手动选的）
    "platform": None,        # 上次平台（None = 跟随系统）
    "version": "",           # 上次版本
    # --- 过滤条件 ---
    "category": "(全部)",
    "max_risk": "low",       # 默认保守：只列低风险
    "opt_in": False,         # 是否纳入默认关闭的网络/ITU 开关
    # --- 选择 ---
    "profile": "standard",
    "disabled_tasks": [],    # 被用户**关闭**的任务 id（默认全开，关了才记）
    "disabled_plugins": [],  # 被用户**停用**的插件 id
    "report_path": "sysweeper-report.md",
}

_MEMORY: Optional[Dict] = None  # 家目录不可写时的降级容器


def path() -> Path:
    """配置文件路径（XDG；无 XDG 则 ~/.config）。"""
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(
        os.path.expanduser("~"), ".config")
    return Path(base) / "sysweeper" / "gui.json"


def load() -> Dict:
    """读配置；任何异常都回退默认值（界面绝不因配置坏而打不开）。"""
    global _MEMORY
    if _MEMORY is not None:
        return dict(_MEMORY)
    p = path()
    try:
        if not p.exists():
            return dict(DEFAULT)
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("schema") != SCHEMA:
            return dict(DEFAULT)  # 不认识的 schema：整体回退，不做半吊子迁移
    except Exception:  # noqa: BLE001 - 配置损坏不该拖垮界面
        return dict(DEFAULT)

    out = dict(DEFAULT)
    for k, v in data.items():
        if k in DEFAULT:
            out[k] = v
    # 列表字段做类型收敛（防手工编辑成字符串）
    for k in ("disabled_tasks", "disabled_plugins"):
        if not isinstance(out.get(k), list):
            out[k] = []
    return out


def save(state: Dict) -> bool:
    """写配置。写不进去（只读家目录）就降级为内存态，返回是否落盘成功。"""
    global _MEMORY
    payload = {k: state.get(k, DEFAULT.get(k)) for k in DEFAULT}
    payload["schema"] = SCHEMA
    try:
        p = path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                     encoding="utf-8")
        _MEMORY = None
        return True
    except Exception:  # noqa: BLE001
        _MEMORY = payload
        return False


def reset() -> Dict:
    """恢复默认（界面「恢复默认」按钮用）。"""
    global _MEMORY
    _MEMORY = None
    try:
        p = path()
        if p.exists():
            p.unlink()
    except Exception:  # noqa: BLE001
        pass
    return dict(DEFAULT)


# ---------------- 任务 / 插件 启停 ----------------

def is_task_enabled(state: Dict, task_id: str) -> bool:
    """默认启用；只有被显式关掉的才返回 False。"""
    return task_id not in (state.get("disabled_tasks") or [])


def set_task_enabled(state: Dict, task_id: str, on: bool) -> Dict:
    off: List[str] = list(state.get("disabled_tasks") or [])
    if on:
        if task_id in off:
            off.remove(task_id)
    else:
        if task_id not in off:
            off.append(task_id)
    state["disabled_tasks"] = off
    return state


def is_plugin_enabled(state: Dict, plugin_id: str) -> bool:
    return plugin_id not in (state.get("disabled_plugins") or [])


def set_plugin_enabled(state: Dict, plugin_id: str, on: bool) -> Dict:
    off: List[str] = list(state.get("disabled_plugins") or [])
    if on:
        if plugin_id in off:
            off.remove(plugin_id)
    else:
        if plugin_id not in off:
            off.append(plugin_id)
    state["disabled_plugins"] = off
    return state


def summary(state: Dict) -> str:
    """给界面显示的一行状态摘要。"""
    return (f"已关闭任务 {len(state.get('disabled_tasks') or [])} 项；"
            f"停用插件 {len(state.get('disabled_plugins') or [])} 个；"
            f"风险上限 {state.get('max_risk')}；"
            f"跟随系统 {'开' if state.get('follow_system') else '关'}")
