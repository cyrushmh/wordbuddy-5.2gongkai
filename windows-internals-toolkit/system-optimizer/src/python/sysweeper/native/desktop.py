"""桌面环境（GNOME / KDE / XFCE）原生接口与文档引用。

按用户要求「桌面（GNOME、KDE、x fce 等）文档也要跟踪」：本层只读探测当前桌面环境，
并对照桌面环境官方文档（dconf/gsettings、KConfig、xfconf、freedesktop XDG 规范）给出
清理/优化指引。所有探测惰性守卫：无图形环境 / 未装对应工具时返回 None/空，由上层降级。

参考文档见 data/desktop_docs.json（GNOME HIG、KDE HIG、XFCE 文档、freedesktop XDG 规范）。
"""

from __future__ import annotations

import json
import os
import shutil


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "desktop_docs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:
        return {}


REFS = _load_refs()


def reference(desktop_id: str) -> dict:
    """返回某桌面环境/规范的文档参考。"""
    return REFS.get(desktop_id, {})


def reference_all() -> dict:
    """返回全部桌面环境/规范文档参考。"""
    return REFS


def detect_desktop() -> str:
    """探测当前桌面环境键名（gnome/kde/xfce/other/unknown）。

    优先 $XDG_CURRENT_DESKTOP，其次窗口管理器/进程特征。
    """
    de = (os.environ.get("XDG_CURRENT_DESKTOP") or "").lower()
    if "gnome" in de:
        return "gnome"
    if "kde" in de or "plasma" in de:
        return "kde"
    if "xfce" in de:
        return "xfce"
    if de:
        return "other"
    # 无环境变量时按工具是否存在推断
    if shutil.which("gsettings"):
        return "gnome"
    if shutil.which("kwriteconfig5") or shutil.which("kreadconfig5"):
        return "kde"
    if shutil.which("xfconf-query"):
        return "xfce"
    return "unknown"


def desktop_env_name(key: str) -> str:
    return {
        "gnome": "GNOME", "kde": "KDE Plasma", "xfce": "XFCE",
        "other": "其他桌面环境", "unknown": "未检测到（可能无图形环境）",
    }.get(key, key)


def tools_available() -> dict:
    """返回各桌面环境配置工具是否可用。"""
    return {
        "gnome": bool(shutil.which("gsettings") or shutil.which("dconf")),
        "kde": bool(shutil.which("kwriteconfig5") or shutil.which("kreadconfig5")),
        "xfce": bool(shutil.which("xfconf-query")),
    }


def cache_dirs() -> dict:
    """返回各桌面环境已知缓存目录（XDG ~/.cache 下）。"""
    home = os.path.expanduser("~")
    cache = os.path.join(home, ".cache")
    return {
        "gnome": [os.path.join(cache, "gnome-software"), os.path.join(cache, "gdm"),
                  os.path.join(cache, "dconf")],
        "kde": [os.path.join(cache, "plasmashell"), os.path.join(cache, "krunner"),
                os.path.join(cache, "ksycoca5")],
        "xfce": [os.path.join(cache, "Thunar"), os.path.join(cache, "xfce4"),
                 os.path.join(cache, "xfce4-notifyd")],
        "xdg": [os.path.join(cache, "thumbnails"),
                os.path.join(cache, "mesa_shader_cache"),
                os.path.join(cache, "mozilla")],
    }


def cache_size_bytes(paths: list) -> int:
    """估算若干缓存目录的总字节数（不存在的跳过）。"""
    total = 0
    for p in paths:
        if not os.path.isdir(p):
            continue
        for root, _dirs, files in os.walk(p):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
    return total


def dconf_reset_preview() -> tuple:
    """提示 dconf reset 的影响范围（只读说明，不改）。参考 GNOME dconf 文档。"""
    db = os.path.expanduser("~/.config/dconf/user")
    if not shutil.which("dconf"):
        return False, "未安装 dconf（GNOME 配置后端）；无法读取 GNOME 设置库。"
    exists = os.path.exists(db)
    return True, ("dconf 用户库: " + ("存在 " + db if exists else "未找到 ~/.config/dconf/user")
                  + "；`dconf reset -f /` 将清空全部用户键回到默认（仅说明，需手动执行）。")


def xfconf_report() -> tuple:
    """读 XFCE xfconf 配置通道（参考 XFCE xfconf 文档）。"""
    if not shutil.which("xfconf-query"):
        return False, "未安装 xfconf-query（XFCE 配置接口）；无法读取 XFCE 设置。"
    rc, out = _common_run("xfconf-query -l 2>/dev/null")
    if rc != 0 or not out:
        return False, "xfconf-query 未返回通道（可能无 XFCE 会话）。"
    channels = [l.strip() for l in out.splitlines() if l.strip()]
    return True, "XFCE xfconf 通道:\n  " + "\n  ".join(channels[:20]) \
        + (f"\n  …（共 {len(channels)} 个）" if len(channels) > 20 else "")


def _common_run(cmd: str):
    from . import common
    return common.run(cmd)


def environment_report() -> list:
    """返回桌面环境跟踪报告（多行文本），供 CLI/GUI 展示。"""
    lines = []
    key = detect_desktop()
    lines.append(f"当前桌面环境: {desktop_env_name(key)}  "
                 f"($XDG_CURRENT_DESKTOP={os.environ.get('XDG_CURRENT_DESKTOP','') or '(空)'})")
    tools = tools_available()
    lines.append("配置工具可用性:")
    lines.append(f"   GNOME gsettings/dconf : {'✓' if tools['gnome'] else '✗'}")
    lines.append(f"   KDE kwriteconfig5     : {'✓' if tools['kde'] else '✗'}")
    lines.append(f"   XFCE xfconf-query     : {'✓' if tools['xfce'] else '✗'}")
    # 缓存占用估算（当前环境对应的桌面）
    if key in ("gnome", "kde", "xfce"):
        size = cache_size_bytes(cache_dirs().get(key, []))
        if size:
            lines.append(f"   {desktop_env_name(key)} 私有缓存约: {size/1024/1024:.1f} MiB")
    return lines


def _fmt_size(n: int) -> str:
    """把字节数格式化为人类可读单位（GiB/MiB/KiB/B）。"""
    if n >= 1024 * 1024 * 1024:
        return f"{n/1024/1024/1024:.2f} GiB"
    if n >= 1024 * 1024:
        return f"{n/1024/1024:.1f} MiB"
    if n >= 1024:
        return f"{n/1024:.1f} KiB"
    return f"{n} B"


def cache_report() -> tuple:
    """只读估算各桌面环境与 XDG 通用缓存的可回收量（不删除任何文件）。

    返回 (ok, 多行文本)：逐环境列出已知缓存目录与字节数，并给出合计，供清理前
    「对比报告」使用（desktop_cache_report 任务 / desktop --report / GUI 缓存对比）。
    纯标准库、惰性守卫：无图形环境 / 目录不存在时跳过，绝不修改系统。
    """
    dirs = cache_dirs()
    current = detect_desktop()
    lines = []
    total = 0
    env_label = {"gnome": "GNOME", "kde": "KDE Plasma", "xfce": "XFCE",
                 "other": "其他桌面", "unknown": "未知"}
    for env in ("gnome", "kde", "xfce"):
        sizes = [(p, cache_size_bytes([p])) for p in dirs.get(env, [])]
        env_total = sum(s for _, s in sizes)
        total += env_total
        mark = "  ◀当前桌面" if env == current else ""
        lines.append(f"  {env_label.get(env, env)}{mark}: 缓存 {_fmt_size(env_total)}")
        for p, s in sizes:
            if s:
                lines.append(f"      · {p}  ({_fmt_size(s)})")
    # XDG 通用缓存（跨桌面：缩略图/着色器/mozilla 等）
    xdg_total = 0
    xdg_lines = []
    for p in dirs.get("xdg", []):
        s = cache_size_bytes([p])
        if s:
            xdg_total += s
            xdg_lines.append(f"      · {p}  ({_fmt_size(s)})")
    total += xdg_total
    if xdg_lines:
        lines.append(f"  XDG 通用缓存（缩略图/着色器/mozilla 等）: {_fmt_size(xdg_total)}")
        lines.extend(xdg_lines)
    lines.append("")
    lines.append(f"  合计可回收（只读估算，不删除）: {_fmt_size(total)}")
    lines.append("  说明：以上为 ~/.cache 下已知缓存目录占用；执行 desktop_gnome_cache / "
                 "desktop_kde_cache / desktop_xfce_cache 等任务（需 --apply）才会真正回收。")
    return True, "\n".join(lines)


def cache_report_dict() -> dict:
    """机器可读版只读缓存估算（供导出 JSON/Markdown 对比报告）。"""
    dirs = cache_dirs()
    current = detect_desktop()
    entries = []
    total = 0
    for env in ("gnome", "kde", "xfce"):
        paths = []
        for p in dirs.get(env, []):
            s = cache_size_bytes([p])
            paths.append({"path": p, "size": s})
            total += s
        entries.append({"env": env, "current": env == current,
                        "total": sum(x["size"] for x in paths), "dirs": paths})
    xdg = []
    for p in dirs.get("xdg", []):
        s = cache_size_bytes([p])
        if s:
            xdg.append({"path": p, "size": s})
            total += s
    return {"current": current, "entries": entries, "xdg": xdg,
            "grand_total": total}
