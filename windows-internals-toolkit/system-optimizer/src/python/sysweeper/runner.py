"""执行器：分析（dry-run，默认）与真正执行（--apply）。

安全模型：
- 默认只「分析」：打印将要执行的命令、估算可回收空间、列出风险与注意事项，不做任何修改。
- 真正执行需显式 --apply；medium/high 风险还需 --yes（或交互确认）。
- 每个动作独立 try/except，单点失败不影响其余。
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import List, Optional, Tuple

from . import native
from .models import Action, Task, RISK_ORDER


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def _probe_size_linux(cmd: str) -> Optional[int]:
    """尽力估算 Linux 上 shell 动作可回收空间（只读 du）。"""
    paths = re.findall(r"(/[^\s\"'|;&<>]+)", cmd)
    total = 0
    found = False
    for p in paths:
        if os.path.isdir(p):
            try:
                out = subprocess.run(
                    ["du", "-sb", "--max-depth=0", p],
                    capture_output=True, text=True, timeout=20,
                ).stdout
                total += int(out.split()[0])
                found = True
            except Exception:
                pass
    return total if found else None


def estimate(task: Task, platform: str) -> Optional[int]:
    if platform != "linux":
        return None
    total = None
    for a in task.actions:
        if a.kind == "shell":
            s = _probe_size_linux(a.command)
            if s:
                total = (total or 0) + s
        elif a.kind == "native" and a.command.startswith("linux."):
            # 原生 Linux 动作若带可估路径，用标准库递归统计
            for p in re.findall(r"/[^\s\"'|;&<>]+", a.command):
                if os.path.isdir(p):
                    sz = native.common.list_dir_size(p)
                    if sz:
                        total = (total or 0) + sz
    return total


def _run_shell(command: str) -> Tuple[int, str]:
    try:
        r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
        return r.returncode, (r.stdout + r.stderr).strip()[-2000:]
    except Exception as e:  # noqa: BLE001
        return -1, f"执行失败: {e}"


def _run_adb(command: str) -> Tuple[int, str]:
    # command 形如 "adb shell pm clear com.x" —— 去掉前缀 "adb " 后用列表执行
    args = command.split()
    if args and args[0] == "adb":
        args = args[1:]
    try:
        r = subprocess.run(["adb", *args], capture_output=True, text=True, timeout=120)
        return r.returncode, (r.stdout + r.stderr).strip()[-2000:]
    except Exception as e:  # noqa: BLE001
        return -1, f"执行失败: {e}"


def _run_native(op_name: str) -> Tuple[bool, str]:
    """调用 sysweeper.native 下的函数，形如 'windows.empty_recycle_bin'。
    函数返回 (ok, msg) 或单 bool。失败/找不到返回 (False, 原因)。"""
    try:
        module_name, func_name = op_name.split(".", 1)
        mod = getattr(native, module_name)
        fn = getattr(mod, func_name)
    except Exception as e:  # noqa: BLE001
        return False, f"找不到原生接口 {op_name}: {e}"
    try:
        res = fn()
    except Exception as e:  # noqa: BLE001
        return False, f"调用 {op_name} 失败: {e}"
    if isinstance(res, tuple) and len(res) == 2:
        ok, msg = res
        return bool(ok), str(msg)
    return bool(res), f"{op_name} -> {res}"


def run_action(a: Action) -> Tuple[bool, str]:
    if a.kind == "shell":
        code, out = _run_shell(a.command)
        return code == 0, out
    if a.kind == "adb":
        code, out = _run_adb(a.command)
        return code == 0, out
    if a.kind == "native":
        return _run_native(a.command)
    # manual / python：不自动执行
    return True, "（指引类动作，需手动执行）"


def analyze(tasks: List[Task], platform: str, apply: bool, yes: bool,
            risk_limit: str = "high", collector: list = None) -> int:
    """展示/执行一组任务。返回失败数。

    若传 collector（一个 list），则把每个任务的结构化结果追加进去，供
    --report 生成「处理前/后对比」报告：
      {id,title,category,risk,estimate,actions,executed,skipped,ok,output}
    """
    failures = 0
    for t in tasks:
        print(f"\n{'='*64}")
        print(f"◆ {t.display_title()}   [{t.category}]  风险: {t.risk}")
        if t.display_desc():
            print(f"  说明: {t.display_desc()}")
        size = estimate(t, platform)
        if size:
            print(f"  预计可回收: {human(size)}")
        for a in t.actions:
            print(f"    - {a.summarize()}")
            if a.kind in ("shell", "adb", "native") and not apply:
                print(f"        $ {a.command}")
        for c in t.display_caveats():
            print(f"    ⚠ 风险: {c}")
        for n in t.display_notes():
            print(f"    ★ 注意: {n}")

        result = {
            "id": t.id, "title": t.display_title(), "category": t.category,
            "risk": t.risk, "estimate": size,
            "actions": [a.summarize() for a in t.actions],
            "executed": False, "skipped": None, "ok": None, "output": "",
        }
        if collector is not None:
            collector.append(result)

        if not apply:
            print("    （分析模式，未做任何修改；加 --apply 执行）")
            continue

        if RISK_ORDER.get(t.risk, 0) > RISK_ORDER.get(risk_limit, 2):
            result["skipped"] = f"风险 {t.risk} 超过 --risk 上限 {risk_limit}"
            print(f"    ✗ 跳过：{result['skipped']}")
            continue
        # opt_in 开关（网络/ITU 调优）：默认关闭，必须显式 --yes 确认才执行
        if t.opt_in and not yes:
            result["skipped"] = "默认关闭的开关，需 --yes 确认"
            print("    ✗ 跳过：默认关闭的开关，需 --yes 确认（选择+确认）后方可执行")
            continue
        if t.risk != "low" and not yes:
            result["skipped"] = "中/高风险需 --yes 确认"
            print("    ✗ 跳过：中/高风险需 --yes 确认")
            continue
        if t.opt_in:
            print("    ★ 已确认执行 opt-in 开关（用户显式选择 + 确认）")

        result["executed"] = True
        outs = []
        task_failed = False
        for a in t.actions:
            if a.kind in ("manual", "python"):
                print(f"    → {a.kind} 动作，请手动执行: {a.command}")
                outs.append(f"[{a.kind}] 需手动执行: {a.command}")
                continue
            ok, out = run_action(a)
            mark = "✓" if ok else "✗"
            print(f"    {mark} {a.description or a.command}")
            if out:
                print(f"        {out}")
            outs.append(f"{'OK' if ok else 'FAIL'}: {a.description or a.command} :: {out}")
            if not ok:
                task_failed = True
                failures += 1
        result["ok"] = not task_failed
        result["output"] = "\n".join(outs)
    return failures


def measure_disk(platform: str) -> dict | None:
    """跨平台测量「主盘」用量，返回 {total, used, free}（字节），读不到返回 None。

    - Windows : 系统盘（ctypes GetDiskFreeSpaceEx）
    - Linux/macOS/BSD/Unix : 根分区 "/"
    - Android/iOS : 无可靠结构化磁盘用量，返回 None
    """
    try:
        if platform == "windows":
            from .native import windows as nw
            d = nw.disk_usage()
            if not d or d.get("total") is None:
                return None
            total = d["total"]
            free = d.get("free") or 0
            return {"total": total, "used": total - free, "free": free}
        if platform in ("linux", "macos", "bsd", "unix"):
            return native.common.disk_usage("/")
    except Exception:
        return None
    return None
