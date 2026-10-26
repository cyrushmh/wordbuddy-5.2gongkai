#!/usr/bin/env python3
"""安卓 8 与 14 优先构建通道（personal-branch 用）。

为什么是这两个版本
------------------
- **Android 8（API 26）是下探底线**：本项目对安卓的支持从这里起步，
  再往下（7 及以下）连一批基础接口都变了形，硬撑就是在报告里写假话。
- **Android 14（API 34）是现行主流**：新机大多在这条线上，权限与后台限制
  也是最严的一档——能过 14，中间版本基本都能过。

两头卡住，中间不用逐个测：这就是"优先构建 8 和 14"的意思，
不是只支持这两个版本，而是**把力气花在能代表两端的两条线上**。

按你的要求：**其他平台只提交代码跑测试，不做构建**——本脚本只处理安卓目标，
遇到非安卓目标直接说明并退出，不假装构建了。

它做什么
--------
1. **矩阵自检**：对 API 26 / 34 分别列出适用任务数、风险分布、缺失项。
2. **生成目标配置**：写出 `build/android-<api>.json`（只存 id 与元信息，不存命令）。
3. **只跑测试**：其他目标（linux/windows/macos/…）只跑 `pytest`，不构建。

它**不做什么**
--------------
- 不下载/不调用 NDK、gradle、sdkmanager——沙箱里没有，也不会假装调用了成功。
- 不打包 APK：本工程是 Python 工具库，到安卓上跑是**在 Termux / adb shell 里
  跑脚本**，不是编译出一个 App。这条要说清楚，别让人以为能装 APK。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "python"))

# 优先构建的两个目标：8 = 下探底线，14 = 现行主流
PRIMARY = {"8": 26, "14": 34}
OUT = ROOT / "build"


def _applicable_stats(version: str) -> dict:
    from sysweeper import registry

    tasks = registry.applicable("android", version, max_risk="high")
    by_risk: dict[str, int] = {}
    by_cat: dict[str, int] = {}
    for t in tasks:
        by_risk[t.risk] = by_risk.get(t.risk, 0) + 1
        by_cat[t.category] = by_cat.get(t.category, 0) + 1
    return {"version": version, "api": PRIMARY.get(version), "count": len(tasks),
            "by_risk": by_risk, "by_category": by_cat,
            "ids": sorted(t.id for t in tasks)}


def build_target(version: str) -> int:
    """为单个安卓目标生成配置；非优先目标也支持，只是默认不跑。"""
    st = _applicable_stats(version)
    OUT.mkdir(parents=True, exist_ok=True)
    api = st["api"] or version
    out = OUT / f"android-{api}.json"
    payload = {
        "platform": "android",
        "version": version,
        "api_level": api,
        "task_count": st["count"],
        "by_risk": st["by_risk"],
        "by_category": st["by_category"],
        "task_ids": st["ids"],
        "note": "只存任务 id 与元信息，不存任何命令；构建由上层流水线消费本文件",
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Android {version} (API {api}): 适用任务 {st['count']} 项 → {out.name}")
    print(f"    风险分布 {st['by_risk']}")
    return 0


def matrix() -> int:
    """矩阵自检：8 与 14 两头卡住，看覆盖面与差异。"""
    print("安卓优先构建矩阵（8 = 下探底线，14 = 现行主流）")
    stats = {}
    for v in ("8", "14"):
        stats[v] = _applicable_stats(v)
    for v, st in stats.items():
        print(f"  Android {v} (API {st['api']}): {st['count']} 项任务；风险 {st['by_risk']}")
    only8 = set(stats["8"]["ids"]) - set(stats["14"]["ids"])
    only14 = set(stats["14"]["ids"]) - set(stats["8"]["ids"])
    print(f"  仅 8 有（老版本专属，多为向下兼容项）：{len(only8)} 项")
    print(f"  仅 14 有（新版本专属，多为新权限/新接口项）：{len(only14)} 项")
    if only14:
        print(f"    例：{sorted(only14)[:5]}")
    if only8:
        print(f"    例：{sorted(only8)[:5]}")
    return 0 if stats["8"]["count"] and stats["14"]["count"] else 1


def run_tests() -> int:
    """其他平台：只跑测试，不构建。"""
    print("其他平台：只跑测试，不构建（按你的要求）")
    r = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q"],
                       cwd=str(ROOT), capture_output=True, text=True)
    tail = (r.stdout or "").strip().splitlines()[-3:]
    for line in tail:
        print("  " + line)
    return r.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="安卓 8 / 14 优先构建通道")
    ap.add_argument("--target", default="android8,android14",
                    help="构建目标（逗号分隔）。other = 只跑测试不构建")
    ap.add_argument("--matrix", action="store_true", help="只输出矩阵自检")
    args = ap.parse_args()

    if args.matrix:
        return matrix()

    targets = [t.strip() for t in args.target.split(",") if t.strip()]
    rc = 0
    for t in targets:
        if t == "other":
            rc |= run_tests()
            continue
        v = t.replace("android", "").strip() or "8"
        if v not in PRIMARY and v not in ("9", "10", "11", "12", "13"):
            print(f"  跳过 {t}：非安卓目标，本通道只处理安卓（其他平台请跑 --target other）")
            continue
        rc |= build_target(v)
    if rc == 0:
        print("\n说明：本工程在安卓上以 Termux / adb shell 方式运行脚本，"
              "**不产出 APK**；构建产物是上面的目标配置文件。")
        print("真机验证：adb 连接后 sysweeper --platform android --version <版本>")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
