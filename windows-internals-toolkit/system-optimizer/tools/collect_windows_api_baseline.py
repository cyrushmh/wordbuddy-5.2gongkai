#!/usr/bin/env python3
"""离线采集 Windows API 可用性基线（只读、零网络）。

对应 supermium 的「离线采集」思路：把「这台机到底能调哪些 Win32 API」
落成一份可机器消费的 JSON，回传给 sysweeper 的 diagnose / kmod 做版本门控降级，
避免把「目标版本太老、API 不存在」误报成「异常」。

做法：逐个尝试 `ctypes.windll.<dll>.<func>`（不调用、只查导出是否存在），
对照 docs/windows-api-version-matrix.md 的 min_version 标注。

- **只读**：只查 DLL 导出表，不调用任何函数、不改任何状态。
- **零网络**：纯标准库，不连任何外部地址。
- **跨平台**：非 Windows 上只输出 os 信息并优雅跳过 API 探测，绝不崩。

用法：
    python3 tools/collect_windows_api_baseline.py            # 打印 JSON 到 stdout
    python3 tools/collect_windows_api_baseline.py --out b.json  # 写到文件
"""
from __future__ import annotations

import argparse
import ctypes
import json
import platform
import sys
from pathlib import Path

# (dll, func, min_windows) —— min_windows 与 docs/windows-api-version-matrix.md 对齐
# 标 "约" 的版本在真实机上以导出表为准（本脚本即做这件事）。
PROBES = [
    ("kernel32", "GetModuleHandleExW", "5.0"),
    ("kernel32", "InitializeCriticalSectionAndSpinCount", "5.0"),
    ("kernel32", "CreateToolhelp32Snapshot", "5.0"),
    ("kernel32", "RegGetValueW", "6.0"),
    ("kernel32", "CreateEventExW", "6.0"),
    ("kernel32", "CreateSemaphoreExW", "6.0"),
    ("kernel32", "InitializeConditionVariable", "6.0"),
    ("kernel32", "InitOnceExecuteOnce", "6.0"),
    ("kernel32", "GetTickCount64", "6.0"),
    ("kernel32", "GetSystemTimePreciseAsFileTime", "6.2"),
    ("kernel32", "WaitOnAddress", "6.2"),
    ("kernel32", "GetDpiForSystem", "10.0.14393"),
    ("kernel32", "SetProcessDpiAwareness", "6.3"),
    ("kernel32", "SetProcessDpiAwarenessContext", "10.0.15063"),
    ("kernel32", "GetThreadDescription", "10.0.14393"),
    ("user32", "IsThemeActive", "5.1"),
    ("user32", "SetWindowTheme", "5.1"),
    ("user32", "TaskDialogIndirect", "6.0"),
    ("user32", "SetProcessDPIAware", "5.1"),
    ("uxtheme", "OpenThemeData", "5.1"),
    ("uxtheme", "DrawThemeBackground", "5.1"),
    ("dwmapi", "DwmIsCompositionEnabled", "6.0"),
    ("dwmapi", "DwmSetWindowAttribute", "6.0"),
    ("gdi32", "GdipCreateFromHDC", "5.1"),
    ("setupapi", "SetupDiGetClassDevsW", "5.0"),
    ("wlanapi", "WlanOpenHandle", "5.1"),
    ("wtsapi32", "WTSQuerySessionInformationW", "5.0"),
]


def _probe() -> dict:
    rows = []
    for dll, func, min_ver in PROBES:
        status = "absent"
        try:
            lib = getattr(ctypes.windll, dll)
            getattr(lib, func)  # 只查导出，不调用
            status = "present"
        except AttributeError:
            status = "absent"          # DLL 或函数未导出
        except Exception:  # noqa: BLE001 - 任何异常都按不可探测处理
            status = "error"
        rows.append({"dll": dll, "func": func, "min_version": min_ver, "status": status})
    return {"platform": "windows", "probe_count": len(rows), "apis": rows}


def _non_windows(os_name: str) -> dict:
    return {"platform": os_name.lower(), "probe_count": 0,
            "apis": [], "note": "非 Windows 平台，跳过 Win32 API 探测（仅记录 os 信息）"}


def collect() -> dict:
    os_name = platform.system()
    if os_name != "Windows":
        return _non_windows(os_name)
    return _probe()


def main() -> int:
    ap = argparse.ArgumentParser(description="离线采集 Windows API 可用性基线")
    ap.add_argument("--out", help="写 JSON 到该路径（默认打印到 stdout）")
    args = ap.parse_args()
    data = collect()
    data["python"] = platform.python_version()
    data["os_release"] = platform.platform()
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"written {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
