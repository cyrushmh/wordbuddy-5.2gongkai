#!/usr/bin/env python3
"""标准知识库版本/新鲜度只读巡检（D11 借鉴 docker-easyconnect 版本巡检 CI）。

只读、不写：扫描 sysweeper 的 data/*.json 标准知识库，做两件事——
  1) 结构校验：每个 json 必须可解析、且顶层为 dict（已有知识库的事实源不损坏）；
  2) 新鲜度提示：尽力取每个文件的最近提交时间（git 可用时），距今天数过大即提示「可能陈旧，需复核 EOL」。

本脚本**绝不**修改任何标准库、绝不联网改写——深 EOL 比对可借 endoflife.date 类数据源在
人工复核时进行。仅输出报告（exit 0 通过；--strict 时陈旧超阈值才 exit 1，便于 CI 卡点）。

用法：
  python3 scripts/audit_standards_eol.py [--data-dir system-optimizer/src/python/sysweeper/data] [--stale-days 180] [--strict]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone


def _git_mtime(path: str) -> int | None:
    """尽力取文件最近提交时间（Unix 秒）；git 不可用/无历史即返回 None。"""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", path],
            cwd=os.path.dirname(os.path.abspath(path)),
            capture_output=True, text=True, timeout=20,
        )
        if out.returncode == 0 and out.stdout.strip().isdigit():
            return int(out.stdout.strip())
    except Exception:  # noqa: BLE001
        pass
    return None


def audit(data_dir: str, stale_days: int, strict: bool) -> int:
    if not os.path.isdir(data_dir):
        print(f"[ERR] 数据目录不存在: {data_dir}", file=sys.stderr)
        return 2

    files = sorted(f for f in os.listdir(data_dir) if f.endswith(".json"))
    if not files:
        print(f"[WARN] 数据目录无 json: {data_dir}")
        return 0

    now = datetime.now(timezone.utc).timestamp()
    problems = 0
    print(f"标准知识库版本/新鲜度巡检（data-dir={data_dir}, stale_days={stale_days}）\n")
    for fn in files:
        path = os.path.join(data_dir, fn)
        # 1) 结构校验
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                print(f"  ✗ {fn}: 顶层不是 dict（知识库结构异常）")
                problems += 1
                continue
            n_keys = len(data)
        except (OSError, ValueError) as e:
            print(f"  ✗ {fn}: 解析失败 {e}")
            problems += 1
            continue

        # 2) 新鲜度提示
        mtime = _git_mtime(path)
        if mtime is None:
            age = "未知(git 不可用)"
            stale = False
        else:
            age_days = int((now - mtime) / 86400)
            age = f"{age_days} 天前"
            stale = age_days > stale_days

        mark = "⚠" if stale else "✓"
        if stale:
            problems += 1
            print(f"  {mark} {fn}: {n_keys} 项标准 | 最近提交 {age} | 可能陈旧，建议复核 EOL/版本")
        else:
            print(f"  {mark} {fn}: {n_keys} 项标准 | 最近提交 {age}")

    print(f"\n知识库总数: {len(files)} | 需复核: {problems}")
    if problems and strict:
        print("[STRICT] 存在需复核项，exit 1（非阻塞：仅提示，不自动改库）")
        return 1
    print("[OK] 结构校验通过；陈旧项仅提示，不自动修改任何标准库。")
    return 0


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    default_data = os.path.join(
        here, "..", "system-optimizer", "src", "python", "sysweeper", "data")
    ap = argparse.ArgumentParser(description="标准知识库版本/新鲜度只读巡检")
    ap.add_argument("--data-dir", default=os.path.normpath(default_data))
    ap.add_argument("--stale-days", type=int, default=180)
    ap.add_argument("--strict", action="store_true",
                    help="陈旧超阈值时 exit 1（仅卡点提示，不自动改库）")
    args = ap.parse_args()
    return audit(args.data_dir, args.stale_days, args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
