"""更新检查与本地刷新（图形界面的「更新」按钮背后）。

纪律：默认**只检查，不动手**
----------------------------
与整个项目的「只读优先、需 --yes 才动作」一致：
- `check()`：只读体检——当前版本、是否 git 工作树、有无本地改动、远端是否有新提交
  （网络不通就明说「查不到」，绝不假装查到）、插件清单与任务库规模。
- `refresh()`：**本地**刷新——重新扫描插件目录、重新统计任务数。不改代码、不拉代码。
- 真正的代码更新**不给按钮自动做**：只把该跑的命令显示出来，由用户自己去终端执行。
  理由：自动改用户机器上的代码是越权，且失败会留下半吊子状态。

网络处理：`git fetch` 有超时且失败可容忍——沙箱/离线环境常见，必须优雅降级。
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

_FETCH_TIMEOUT = 12  # 秒；网络不通就别拖着界面


def current_version() -> str:
    from . import __version__
    return __version__


def _git_repo_root() -> Path | None:
    """找本包所在的 git 仓库根；不在仓库里就返回 None。"""
    try:
        here = Path(__file__).resolve().parent
        for base in (here, *here.parents[:4]):
            if (base / ".git").exists():
                return base
    except Exception:  # noqa: BLE001
        pass
    return None


def _run_git(args: List[str], cwd: Path) -> Tuple[bool, str]:
    if not shutil.which("git"):
        return False, "未安装 git"
    try:
        p = subprocess.run(["git", *args], cwd=str(cwd), timeout=_FETCH_TIMEOUT,
                           capture_output=True, text=True, errors="replace")
        return p.returncode == 0, (p.stdout or p.stderr or "").strip()
    except subprocess.TimeoutExpired:
        return False, f"git {args[0]} 超时（{_FETCH_TIMEOUT}s）"
    except Exception as e:  # noqa: BLE001
        return False, f"git {args[0]} 失败: {e}"


def check() -> Dict:
    """只读体检：版本、仓库状态、远端更新、插件与任务库规模。

    返回 dict，字段齐全，界面直接渲染；任何一步失败都记进 `notes` 而不是抛异常。
    """
    notes: List[str] = []
    repo = _git_repo_root()

    out: Dict = {
        "version": current_version(),
        "in_git_repo": repo is not None,
        "repo": str(repo) if repo else "",
        "branch": "",
        "dirty": None,          # 有无未提交改动（None = 未知）
        "behind": None,         # 落后远端几个提交（None = 未知）
        "ahead": None,
        "remote_reachable": None,
        "plugin_dir": "",
        "plugins_found": 0,
        "tasks_total": 0,
        "notes": notes,
    }

    # --- 任务库规模 ---
    try:
        from .registry import all_tasks
        out["tasks_total"] = len(all_tasks())
    except Exception as e:  # noqa: BLE001
        notes.append(f"任务库统计失败: {e}")

    # --- 插件目录 ---
    try:
        from .native import plugins
        d = getattr(plugins, "PLUGIN_DIRS", None) or []
        out["plugin_dir"] = ", ".join(str(x) for x in d) if d else \
            os.environ.get("SYSWEEPER_PLUGINS_DIR", "（未设置）")
        ok, msg = plugins.plugin_report("list")
        if ok:
            # 清单行数粗估插件数量（只读报告，不做严格解析）
            out["plugins_found"] = msg.count("\n") and len(
                [l for l in msg.splitlines() if l.strip().startswith("-")]) or 0
        else:
            notes.append(f"插件清单读取失败: {msg}")
    except Exception as e:  # noqa: BLE001
        notes.append(f"插件模块不可用: {e}")

    # --- git 仓库状态 ---
    if not repo:
        notes.append("当前不在 git 工作树内（安装版/打包版），无法检查代码更新")
        return out

    ok, msg = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo)
    out["branch"] = msg if ok else ""

    ok, msg = _run_git(["status", "--porcelain"], repo)
    if ok:
        out["dirty"] = bool(msg.strip())
        if msg.strip():
            notes.append(f"有 {len(msg.strip().splitlines())} 个文件未提交（本地改动）")

    # 远端可达性（网络不稳是常态，超时即降级）
    ok, _ = _run_git(["ls-remote", "--exit-code", "--heads", "origin"], repo)
    if not ok:
        out["remote_reachable"] = False
        notes.append("连不上远端（离线或网络受限）——无法判断是否有新版本，非故障")
        return out
    out["remote_reachable"] = True

    ok, _ = _run_git(["fetch", "origin"], repo)
    if not ok:
        notes.append("远端可达但 fetch 未完成（权限或超时），按本地状态报告")

    ok, msg = _run_git(["rev-list", "--left-right", "--count", "HEAD...@{upstream}"],
                       repo)
    if ok and msg:
        parts = msg.split()
        if len(parts) == 2:
            out["ahead"] = int(parts[0])
            out["behind"] = int(parts[1])
    else:
        notes.append("未配置上游分支（@{{upstream}}），跳过领先/落后统计")

    return out


def refresh() -> Dict:
    """本地刷新：重新扫描插件目录、重新统计任务与语言可用性。

    **不改代码、不拉代码、不动用户文件**——只是让界面看到最新的本地状态。
    """
    res: Dict = {"ok": True, "tasks": 0, "plugins": 0, "notes": []}
    try:
        from .registry import all_tasks
        res["tasks"] = len(all_tasks())
    except Exception as e:  # noqa: BLE001
        res["ok"] = False
        res["notes"].append(f"任务库刷新失败: {e}")

    try:
        from .native import plugins
        ok, msg = plugins.plugin_report("list")
        if ok:
            res["plugins"] = len([l for l in msg.splitlines()
                                  if l.strip().startswith("-")])
        else:
            res["notes"].append(f"插件重新扫描失败: {msg}")
    except Exception as e:  # noqa: BLE001
        res["notes"].append(f"插件模块不可用: {e}")

    try:
        from .langdetect import available as _avail  # noqa: F401
        res["notes"].append("语言运行时已重新探测")
    except Exception:  # noqa: BLE001
        pass
    return res


def update_commands() -> List[str]:
    """真正要更新时该跑的命令——**只显示给用户，本模块绝不执行**。"""
    repo = _git_repo_root()
    if not repo:
        return [
            "# 当前不在 git 工作树内；按你的安装方式更新，例如：",
            "pip install --upgrade sysweeper     # pip 安装版",
        ]
    return [
        f"cd {repo}",
        "git fetch origin",
        "git status            # 先看本地有没有未提交改动",
        "git pull --ff-only    # 只有干净时才快进；有改动先 stash 或提交",
        "# 更新后如需重新编译译文：",
        "python3 tools/make_mo.py",
    ]


def render_check() -> str:
    """把 check() 渲染成可直接显示的中文文本（界面与命令行共用）。"""
    r = check()
    lines = [
        f"当前版本：{r['version']}",
        f"任务库：{r['tasks_total']} 项",
        f"插件：{r['plugins_found']} 个（目录 {r['plugin_dir'] or '—'}）",
    ]
    if not r["in_git_repo"]:
        lines.append("代码更新：不在 git 工作树内，无法检查")
    else:
        lines.append(f"仓库：{r['repo']}（分支 {r['branch'] or '—'}）")
        if r["dirty"] is True:
            lines.append("本地改动：有未提交文件（更新前请先处理）")
        elif r["dirty"] is False:
            lines.append("本地改动：干净")
        if r["remote_reachable"] is False:
            lines.append("远端：连不上（离线/受限），无法判断新版本")
        elif r["behind"] is not None:
            if r["behind"] > 0:
                lines.append(f"远端：落后 {r['behind']} 个提交（有新版本）")
            else:
                lines.append("远端：已是最新")
        if r["ahead"]:
            lines.append(f"本地领先 {r['ahead']} 个提交（尚未推送）")
    for n in r["notes"]:
        lines.append(f"· {n}")
    lines.append("")
    lines.append("要真正更新，请在终端执行（本界面不会自动改你的代码）：")
    for c in update_commands():
        lines.append(f"  {c}")
    return "\n".join(lines)
