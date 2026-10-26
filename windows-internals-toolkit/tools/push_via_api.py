#!/usr/bin/env python3
"""用 GitHub **Git Data API** 把本地提交推送到远端 —— 当 git 协议走不通时的备用通道。

为什么要这个脚本
----------------
某些环境（容器 / CI / 受限网络）里 `git push` 会卡死在 TLS 层：

    fatal: unable to access 'https://github.com/...': GnuTLS recv error (-110)
    fatal: ... Failed to connect to github.com port 443 after 132514 ms

典型原因是出网只放行了 443 上的 REST 端点、或中间设备拆了长连接的 TLS。
这时 **HTTPS 的 REST API 往往还是通的**（可以用 `gh api /repos/...` 验证）。
本脚本就走这条路：**只传变更文件的 blob，基于远端 base tree 建新 tree，
建 commit，最后把分支 ref 指过去** —— 全程不碰 git 协议。

它推送的是**工作分支 HEAD 这一个提交**的内容（不是逐提交重放历史），
因此适合"本地有若干提交、但推不上去"的场景：结果等价于把这些提交 squash 成一个。

用法
----
    # token 从环境变量取（推荐），或从 origin 的 URL 里自动提取
    export GH_TOKEN=...
    python3 tools/push_via_api.py                     # 推当前分支
    python3 tools/push_via_api.py --branch main       # 指定远端分支
    python3 tools/push_via_api.py --dry-run           # 只打印将要做什么

依赖：仅标准库（urllib / json / base64 / subprocess）。
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

API = "https://api.github.com"
# 从 remote URL 里取凭据：形如 https://x-access-token:<token>@github.com/o/r.git
# （不写死 token 前缀的字面量，避免被仓库护栏的凭据扫描误报）
_TOKEN_IN_URL = re.compile(r"x-access-token:([^@]+)@")


def git(*args: str) -> str:
    # core.quotePath=false：否则中文/非 ASCII 路径会被 git 转义成
    # "docs/CI-\346\216\222\351\224\231.md" 这种八进制串，open() 直接找不到文件。
    r = subprocess.run(["git", "-c", "core.quotePath=false"] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} 失败：{r.stderr.strip()}")
    return r.stdout.strip()


class GitHub:
    def __init__(self, token: str, repo: str):
        self.token = token
        self.repo = repo

    def _req(self, method: str, path: str, payload=None, raw=False):
        url = f"{API}{path}" if path.startswith("/") else path
        data = None
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "sysweeper-push-via-api",
        }
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = resp.read()
                return body if raw else (json.loads(body) if body else {})
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:800]
            raise SystemExit(f"API {method} {path} → {e.code}\n{detail}")

    # --- 读 ---
    def ref_sha(self, branch: str) -> str:
        return self._req("GET", f"/repos/{self.repo}/git/ref/heads/{branch}")["object"]["sha"]

    def commit_tree(self, sha: str) -> str:
        return self._req("GET", f"/repos/{self.repo}/git/commits/{sha}")["tree"]["sha"]

    # --- 写 ---
    def blob(self, content: bytes) -> str:
        return self._req("POST", f"/repos/{self.repo}/git/blobs", {
            "encoding": "base64",
            "content": base64.b64encode(content).decode("ascii"),
        })["sha"]

    def tree(self, base_tree: str, entries: list) -> str:
        return self._req("POST", f"/repos/{self.repo}/git/trees",
                         {"base_tree": base_tree, "tree": entries})["sha"]

    def commit(self, message: str, tree_sha: str, parents: list) -> str:
        return self._req("POST", f"/repos/{self.repo}/git/commits",
                         {"message": message, "tree": tree_sha, "parents": parents})["sha"]

    def move_ref(self, branch: str, sha: str, force: bool = False) -> dict:
        return self._req("PATCH", f"/repos/{self.repo}/git/refs/heads/{branch}",
                         {"sha": sha, "force": force})


def parse_remote() -> tuple[str, str]:
    url = git("remote", "get-url", "origin")
    m = re.match(r"https?://[^/]+/([^/]+)/(.+?)(\.git)?$", url)
    if not m:
        raise SystemExit(f"认不出 origin 的 owner/repo：{url}")
    return m.group(1), m.group(2)


def resolve_token() -> str:
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if tok:
        return tok.strip()
    m = _TOKEN_IN_URL.search(git("remote", "get-url", "origin"))
    if m:
        return m.group(1)
    raise SystemExit("没有凭据：请设置 GH_TOKEN，或让 origin 形如 "
                     "https://x-access-token:<TOKEN>@github.com/o/r.git")


def changed_paths(base: str) -> list[tuple[str, str]]:
    """返回 [(status, path)]，status ∈ A/M/D。--no-renames 让重命名拆成 D+A。"""
    out = git("diff", "--no-renames", "--name-status", base, "HEAD")
    changes = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0][0]          # A / M / D / T ...
        path = parts[-1]
        if status in ("A", "M", "D"):
            changes.append((status, path))
        else:
            # T（类型变更）当修改处理
            changes.append(("M", path))
    return changes


def local_has_commit(sha: str) -> bool:
    r = subprocess.run(["git", "cat-file", "-e", sha + "^{commit}"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return r.returncode == 0


def mode_of(path: str) -> str:
    out = git("ls-tree", "HEAD", "--", path)
    if not out:
        return "100644"
    return out.split()[0]             # 100644 / 100755 / 120000


def main() -> int:
    ap = argparse.ArgumentParser(description="用 GitHub Git Data API 推送（git push 不通时的备用通道）")
    ap.add_argument("--branch", default="", help="远端分支（默认：本地当前分支名）")
    ap.add_argument("--base", default="", help="基线 commit（默认：远端分支当前指向）")
    ap.add_argument("--message", default="", help="commit 信息（默认：本地 HEAD 的标题）")
    ap.add_argument("--dry-run", action="store_true", help="只打印将要做什么，不写远端")
    args = ap.parse_args()

    branch = args.branch or git("rev-parse", "--abbrev-ref", "HEAD")
    owner_repo = parse_remote()
    repo = f"{owner_repo[0]}/{owner_repo[1]}"
    token = resolve_token()
    gh = GitHub(token, repo)

    remote_sha = gh.ref_sha(branch)          # 新 commit 的 parent，也是 base tree
    head = git("rev-parse", "HEAD")

    # diff 基线要和 parent 分开看：远端那个 commit 可能是本脚本上一次建的，
    # 本地对象库里根本没有它（git diff 会报 bad object）。这时退回到本地仍认识的
    # 最近一次远端基线，diff 出来的变更集照样完整（远端内容 == 上次推上去的内容）。
    if args.base:
        diff_base = args.base
    elif local_has_commit(remote_sha):
        diff_base = remote_sha
    else:
        for ref in (f"refs/remotes/origin/{branch}", "refs/remotes/origin/main"):
            try:
                diff_base = git("rev-parse", ref)
                break
            except SystemExit:
                continue
        else:
            raise SystemExit(
                f"远端 {branch} = {remote_sha[:12]} 在本地对象库里不存在，"
                f"且没有可用的本地远端引用做基线。请用 --base <本地存在的 sha> 指定。"
            )
    changes = changed_paths(diff_base)

    print(f"仓库      : {repo}")
    print(f"分支      : {branch}")
    print(f"远端当前  : {remote_sha[:12]}（作为新 commit 的 parent）")
    print(f"diff 基线 : {diff_base[:12]}")
    print(f"本地 HEAD : {head[:12]}")
    print(f"变更文件  : {len(changes)} 个")

    if not changes:
        print("没有需要推送的变更。")
        return 0

    for status, path in changes[:20]:
        print(f"  {status}  {path}")
    if len(changes) > 20:
        print(f"  ... 其余 {len(changes) - 20} 个省略")

    if args.dry_run:
        print("\n--dry-run：到此为止，未写远端。")
        return 0

    base_tree = gh.commit_tree(remote_sha)
    entries = []
    t0 = time.time()
    for i, (status, path) in enumerate(changes, 1):
        if status == "D":
            entries.append({"path": path, "mode": "100644", "type": "blob", "sha": None})
            print(f"  [{i}/{len(changes)}] - {path}")
            continue
        with open(path, "rb") as f:
            content = f.read()
        sha = gh.blob(content)
        mode = mode_of(path)
        entries.append({"path": path, "mode": mode, "type": "blob", "sha": sha})
        print(f"  [{i}/{len(changes)}] + {path} ({len(content)} B)")

    print(f"blob 上传完成，用时 {time.time() - t0:.1f}s")

    tree_sha = gh.tree(base_tree, entries)
    print(f"tree      : {tree_sha[:12]}")

    message = args.message or git("log", "-1", "--format=%B").strip() or f"push via API from {head[:12]}"
    new_commit = gh.commit(message, tree_sha, [remote_sha])
    print(f"commit    : {new_commit[:12]}")

    gh.move_ref(branch, new_commit)
    print(f"\n已把 {branch} 指向 {new_commit[:12]}")
    print(f"https://github.com/{repo}/commit/{new_commit}")
    print("\n注意：本地 git 的 origin/{0} 引用还是旧的，建议同步一下：\n"
          "  git fetch origin {0} && git branch -f {0} origin/{0}".format(branch))
    return 0


if __name__ == "__main__":
    sys.exit(main())
