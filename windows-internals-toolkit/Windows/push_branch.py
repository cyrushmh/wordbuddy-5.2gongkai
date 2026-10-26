#!/usr/bin/env python3
# 通过 GitHub Git Data API 把本地工作区提交到【指定分支】（绕过 git 协议网络问题）
# 体现 branch 工作流：新功能在 feature/* 分支开发，推到远端后 PR 合并 main，无需 fork。
# 用法: python3 push_branch.py <TOKEN> [BRANCH_NAME] [REPO_NAME]
import base64, json, os, subprocess, sys
import requests

TOKEN = sys.argv[1]
BRANCH = sys.argv[2] if len(sys.argv) > 2 else "feature/multi-lang-tools"
REPO = sys.argv[3] if len(sys.argv) > 3 else "wordbuddy-github"
OWNER = "cyrushmh"
API = "https://api.github.com"
LOCAL = "/workspace/windows-internals-toolkit"
H = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

def get(url):
    return requests.get(f"{API}{url}", headers=H, timeout=60)
def post(url, payload):
    return requests.post(f"{API}{url}", headers=H, json=payload, timeout=120)
def patch(url, payload):
    return requests.patch(f"{API}{url}", headers=H, json=payload, timeout=60)

print(f"=== 目标: {OWNER}/{REPO}  分支: {BRANCH} ===")

# 基础 parent：以远端 main 当前 head 为准，保证 fast-forward 不冲突
r = get(f"/repos/{OWNER}/{REPO}/git/ref/heads/main")
if r.status_code != 200:
    print("✗ 读取 main 失败:", r.status_code); sys.exit(1)
sha0 = r.json()["object"]["sha"]
print(f"✓ base main = {sha0[:7]}")

# 本地待推送文件
files = subprocess.run(["git", "ls-files"], cwd=LOCAL, capture_output=True, text=True).stdout.split()
print(f"✓ 本地待推送 {len(files)} 个文件")

# 为每个文件创建 blob
tree = []
for f in files:
    data = open(os.path.join(LOCAL, f), "rb").read()
    b64 = base64.b64encode(data).decode("ascii")
    mode = "100755" if f.endswith(".sh") else "100644"
    rr = post(f"/repos/{OWNER}/{REPO}/git/blobs", {"content": b64, "encoding": "base64"})
    if rr.status_code not in (200, 201):
        print(f"✗ blob 失败 {f}: {rr.status_code} {rr.text[:200]}"); sys.exit(1)
    tree.append({"path": f, "mode": mode, "type": "blob", "sha": rr.json()["sha"]})

rr = post(f"/repos/{OWNER}/{REPO}/git/trees", {"tree": tree})
if rr.status_code not in (200, 201):
    print("✗ tree 失败:", rr.status_code); sys.exit(1)
tree_sha = rr.json()["sha"]

rr = post(f"/repos/{OWNER}/{REPO}/git/commits",
          {"message": f"feat: Rust 子项目 + 多种 Windows GUI 的 PE Viewer + 稳定版/LTS 版本策略 (branch {BRANCH})",
           "tree": tree_sha, "parents": [sha0]})
if rr.status_code not in (200, 201):
    print("✗ commit 失败:", rr.status_code); sys.exit(1)
commit_sha = rr.json()["sha"]
print(f"✓ commit = {commit_sha[:7]}")

# 创建或更新分支 ref
ref_path = BRANCH.replace("/", "%2F")
r = get(f"/repos/{OWNER}/{REPO}/git/ref/heads/{ref_path}")
if r.status_code == 200:
    # 分支已存在：以最新工作区刷新（非快进，强制更新）
    rr = patch(f"/repos/{OWNER}/{REPO}/git/refs/heads/{ref_path}", {"sha": commit_sha, "force": True})
    print(f"✓ 分支已强制更新 -> {rr.status_code}")
else:
    rr = post(f"/repos/{OWNER}/{REPO}/git/refs", {"ref": f"refs/heads/{BRANCH}", "sha": commit_sha})
    print(f"✓ 分支已创建 -> {rr.status_code}")

print(f"\n🔗 分支: https://github.com/{OWNER}/{REPO}/tree/{BRANCH}")
print(f"🔗 开 PR 合并 main: https://github.com/{OWNER}/{REPO}/compare/main...{BRANCH}")
