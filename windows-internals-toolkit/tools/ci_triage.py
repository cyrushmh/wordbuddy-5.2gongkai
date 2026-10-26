#!/usr/bin/env python3
"""GitHub Actions 排错：一条命令拿到「哪个 job 的哪一步、为什么红的」。

为什么要有这个脚本
------------------
Actions 的日志有个很坑的特点：**最后几行通常不是原因**。典型的一次事故里，
日志末尾是

    ##[warning]Node.js 20 is deprecated. ... actions/download-artifact@v4

看着像是它把构建搞挂了，实际上那个 step 状态是 `success`——它只是路过刷了条警告。
真正的 `##[error]` 在往上十几行。手工翻日志很容易被结尾误导，于是固化成脚本：

    python3 tools/ci_triage.py                 # 最新一次失败的 run
    python3 tools/ci_triage.py --last          # 最新一次 run（不论成败）
    python3 tools/ci_triage.py --run 37682971131
    python3 tools/ci_triage.py --context 12    # 错误前后多打几行

输出顺序：**错误先行，警告靠后**，并且明确标注「警告不是失败原因」。

还有一类失败**根本没有日志可看**：job 秒败、`steps` 为空数组、`runner_id=0`、
日志下载 404 `BlobNotFound` —— 作业从未分配到 runner，在编排/排队阶段就被中止。
脚本会自动识别这个签名并给出专门诊断（私有仓库最常见原因是
**Actions 分钟额度耗尽/支付失败**，属账户级问题而非代码缺陷），不会再像
早期版本那样撞一个未捕获的 `HTTPError` 崩溃退出。

细节方法论见 [`docs/CI-排错.md`](../docs/CI-排错.md)。

依赖：仅标准库。token 从 `GH_TOKEN` 取，或从 origin 的 URL 里提取。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
_TOKEN_IN_URL = re.compile(r"x-access-token:([^@]+)@")


def git(*args: str) -> str:
    r = subprocess.run(["git", "-c", "core.quotePath=false"] + list(args),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, encoding="utf-8")
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} 失败：{r.stderr.strip()}")
    return r.stdout.strip()


def api(path: str, token: str):
    url = f"{API}{path}" if path.startswith("/") else path
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "sysweeper-ci-triage",
    })
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"API GET {path} → {e.code}\n{e.read().decode('utf-8', 'replace')[:600]}")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None      # 不跟随：让 302 变成可捕获的 HTTPError，好拿到 Location


def api_log(path: str, token: str):
    """拉 job 日志。有个坑：GitHub 会 302 到 Azure blob 存储。

    urllib 默认跟随重定向时会把 Authorization 头一起带过去，Azure 那边不认
    GitHub 的 token，直接回 401 `InvalidAuthenticationInfo`。所以这里手动接管：
    先拿 302 的 Location，再用**不带凭据**的请求去真正下载。

    返回 `(text, reason)`：正常时 `reason` 为 None；拿不到日志时返回
    `(None, 原因)`——**不抛异常**。最典型的原因是 404 `BlobNotFound`：
    作业从未进入执行阶段（没分配 runner），压根没产生日志归档。
    """
    req = urllib.request.Request(f"{API}{path}", headers={
        "Authorization": f"Bearer {token}",
        # 拉日志也得用 json 的 Accept，传 text/plain 会被拒（415）。
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "sysweeper-ci-triage",
    })
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        try:
            with opener.open(req, timeout=120) as resp:
                return resp.read().decode("utf-8", "replace"), None
        except urllib.error.HTTPError as e:
            if e.code not in (301, 302, 303, 307, 308):
                body = e.read().decode("utf-8", "replace")
                if e.code == 404 and "blob" in body.lower():
                    return None, f"日志不存在（{e.code} BlobNotFound）：作业没产生日志归档"
                return None, f"API GET {path} → {e.code} {body[:200]}"
            location = e.headers.get("Location")
            if not location:
                return None, f"API GET {path} → {e.code} 但没有 Location 头"
            plain = urllib.request.Request(location, headers={"User-Agent": "sysweeper-ci-triage"})
            try:
                with urllib.request.urlopen(plain, timeout=180) as resp:
                    return resp.read().decode("utf-8", "replace"), None
            except urllib.error.HTTPError as e2:
                return None, f"下载日志 → {e2.code} {e2.read().decode('utf-8', 'replace')[:200]}"
    except (urllib.error.URLError, OSError) as e:
        return None, f"网络错误：{e}"


def parse_remote() -> str:
    url = git("remote", "get-url", "origin")
    m = re.match(r"https?://[^/]+/([^/]+)/(.+?)(\.git)?$", url)
    if not m:
        raise SystemExit(f"认不出 origin 的 owner/repo：{url}")
    return f"{m.group(1)}/{m.group(2)}"


def resolve_token() -> str:
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if tok:
        return tok.strip()
    m = _TOKEN_IN_URL.search(git("remote", "get-url", "origin"))
    if m:
        return m.group(1)
    raise SystemExit("没有凭据：请设置 GH_TOKEN，或让 origin 形如 "
                     "https://x-access-token:<TOKEN>@github.com/o/r.git")


def pick_run(repo: str, token: str, run_id: str, last: bool):
    if run_id:
        return api(f"/repos/{repo}/actions/runs/{run_id}", token)
    runs = api(f"/repos/{repo}/actions/runs?per_page=15", token).get("workflow_runs", [])
    if not runs:
        raise SystemExit("这个仓库没有任何 Actions 运行记录")
    if last:
        return runs[0]
    failed = [r for r in runs if r.get("conclusion") not in ("success",)]
    return failed[0] if failed else runs[0]


def error_context(log: str, width: int, limit: int = 4) -> list[str]:
    """抓 ##[error] 及其前后若干行 —— 这才是真相所在。"""
    lines = log.splitlines()
    blocks = []
    for i, line in enumerate(lines):
        if "##[error]" not in line:
            continue
        lo = max(0, i - width)
        hi = min(len(lines), i + 3)
        blocks.append("\n".join(lines[lo:hi]))
        if len(blocks) >= limit:
            break
    return blocks


def _parse_ts(s: str):
    """解析 GitHub 的 ISO 时间戳；失败返回 None。"""
    if not s:
        return None
    try:
        from datetime import datetime, timezone
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def preflight_failure(job: dict) -> str | None:
    """识别「作业从未跑起来」的签名；命中返回人类可读的时长说明，否则 None。

    签名（2026-10-22 本仓库实测复盘固化）：
      - steps 为空数组 —— 一步都没执行；
      - 没有 runner（runner_id 为 0 / runner_name 为空）；
      - started_at 到 completed_at 只有几秒。
    满足这三条的失败发生在 runner 编排/排队阶段，与工作流 YAML、
    仓库代码都无关。私有仓库最常见原因：Actions 分钟额度耗尽或
    支付失败（硬性预算墙），作业代理直接拒派 runner。
    """
    if job.get("steps"):
        return None
    if job.get("runner_name") or job.get("runner_id"):
        return None
    started, completed = _parse_ts(job.get("started_at", "")), _parse_ts(job.get("completed_at", ""))
    if started and completed:
        secs = (completed - started).total_seconds()
        if secs > 60:
            return None
        return f"{secs:.0f} 秒"
    return "时长未知"


def print_quota_wall(job: dict, secs: str) -> None:
    """打印「分钟额度墙 / 编排层中止」的完整诊断与处置建议。"""
    print("\n   ┌──────────────────────────────────────────────────────────────┐")
    print("   │ 判定：作业在排队阶段即被中止 —— 不是代码/工作流的问题        │")
    print("   └──────────────────────────────────────────────────────────────┘")
    print(f"   · 签名：steps 为空数组（一步未执行）+ 无 runner（runner_id=0）"
          f"+ 仅 {secs} 就结束")
    print("   · 日志必然取不到（404 BlobNotFound）：没跑步骤就没有日志归档")
    print("\n   私有仓库最常见原因（按概率排序）：")
    print("     1. Actions 分钟额度耗尽，或支付失败/消费限额为 0（硬性预算墙）")
    print("        —— 作业代理直接拒派 runner。个人账户免费额度 2000 分钟/月。")
    print("     2. 仓库/组织策略禁用了对应 runner 或 action")
    print("     3. GitHub 侧 runner 供给的临时故障（会自愈，可重试）")
    print("\n   怎么坐实（都不需要改代码）：")
    print("     · 本地把该工作流的每一条命令原样跑一遍 —— 全绿即可排除代码因素")
    print("     · 看同期 GitHub 托管的 Graph Update 作业：不耗分钟，若它仍成功，")
    print("       而所有消耗 runner 的工作流齐败，即为额度墙")
    print("     · Settings → Billing → Plans & usage 看剩余分钟（PAT 读不到计费）")
    print("\n   处置（账户级，任选其一）：")
    print("     · 绑定支付方式 / 提高消费限额（Settings → Billing）")
    print("     · 等待月度重置（按账期日重置）")
    print("     · 仓库转公开：公开仓库的 Linux runner 分钟免费且不限量")
    print("     · 注册自托管 runner：零计费分钟，checks 照常上报")
    print("\n   代码侧能做的只有省分钟（已做/可做）：")
    print("     · 工作流加 concurrency: cancel-in-progress（同 ref 取消被顶掉的旧跑）")
    print("     · 收窄 pull_request 触发路径；把重活挪到 tag/dispatch")


def main() -> int:
    ap = argparse.ArgumentParser(description="GitHub Actions 排错：定位真正失败的 step")
    ap.add_argument("--run", default="", help="run id（默认：最近一次失败的运行）")
    ap.add_argument("--last", action="store_true", help="看最近一次运行，不论成败")
    ap.add_argument("--context", type=int, default=8, help="错误前后打印的行数（默认 8）")
    ap.add_argument("--show-warnings", action="store_true", help="同时列出警告（默认只报数量）")
    args = ap.parse_args()

    repo = parse_remote()
    token = resolve_token()
    run = pick_run(repo, token, args.run, args.last)

    rid = run["id"]
    print("=" * 72)
    print(f"工作流  : {run.get('name')}")
    print(f"结论    : {run.get('conclusion') or run.get('status')}    "
          f"分支 {run.get('head_branch')}    commit {run.get('head_sha', '')[:12]}")
    print(f"链接    : {run.get('html_url')}")
    print("=" * 72)

    jobs = api(f"/repos/{repo}/actions/runs/{rid}/jobs?per_page=100", token).get("jobs", [])
    bad = [j for j in jobs if j.get("conclusion") not in ("success", "skipped")]
    for j in jobs:
        flag = "✗" if j in bad else "✓"
        print(f"  {flag} {j.get('name')} → {j.get('conclusion')}")

    if not bad:
        print("\n没有失败的 job。")
        return 0

    print("\n" + "#" * 72)
    print("# 失败原因（按 ##[error] 定位；日志末尾的 warning 通常不是原因）")
    print("#" * 72)

    for j in bad:
        print(f"\n■ {j.get('name')}  (job {j.get('id')})")

        # 先识别「从未跑起来」的签名：steps 空 + 无 runner + 秒败。
        # 这种失败没有日志可看，按额度墙/编排层中止诊断，不要再去拉日志。
        secs = preflight_failure(j)
        if secs:
            for s in j.get("steps", []):
                print(f"   {s.get('number')}. {s.get('name')} => {s.get('conclusion')}")
            print("   （steps 为空 —— 一步都没执行）")
            print_quota_wall(j, secs)
            continue

        for s in j.get("steps", []):
            mark = "✗" if s.get("conclusion") not in ("success", "skipped") else " "
            print(f"   {mark} {s.get('number')}. {s.get('name')} => {s.get('conclusion')}")
        log, reason = api_log(f"/repos/{repo}/actions/jobs/{j['id']}/logs", token)
        if log is None:
            print(f"\n   （拿不到日志：{reason}）")
            print("   若 job 有步骤但日志缺失，可能是日志保留期已过或归档损坏。")
            continue
        errs = error_context(log, args.context)
        if errs:
            for blk in errs:
                print("\n   ---- 错误上下文 ----")
                for line in blk.splitlines():
                    print("   " + line)
        else:
            print("\n   （日志里没有 ##[error] 标记 —— 可能是超时/取消，看 job 结论与耗时）")

        warns = [l for l in log.splitlines() if "##[warning]" in l]
        print(f"\n   警告 {len(warns)} 条（不是失败原因，别被末尾那条误导）：")
        seen = set()
        for w in warns:
            text = re.sub(r"^\S+Z?\s*", "", w)
            key = text[:60]
            if key in seen:
                continue
            seen.add(key)
            print(f"     · {text[:160]}")
            if not args.show_warnings and len(seen) >= 3:
                print(f"     · ...（共 {len(warns)} 条，加 --show-warnings 看全部）")
                break

    print("\n" + "=" * 72)
    print("下一步：对照 docs/CI-排错.md 的退出码表（120=管道断开、141=SIGPIPE、")
    print("1=脚本异常），并注意 runner 给 bash 自动加了 -e 与 pipefail，")
    print("本机交互式 shell 没有这两个选项，所以「本机好好的」很常见。")
    print("若上面出现了「排队阶段即被中止」的判定，那是账户级额度墙——")
    print("按打印出来的清单到 Billing 里处理，别改代码。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
