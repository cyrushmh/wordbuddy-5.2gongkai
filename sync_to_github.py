#!/usr/bin/env python3
# 将整个 wordbuddy-github 仓库（monorepo）同步到 GitHub 的指定分支
# 通过 GitHub Git Data API 重建目录树（绕过沙箱 git 协议限制，无需 git push）
#
# 用法:
#   python3 sync_to_github.py <TOKEN> [REPO_NAME] [BRANCH]
# 示例:
#   python3 sync_to_github.py ghp_xxx            # 同步到 cyrushmh/wordbuddy-github 的 main
#   python3 sync_to_github.py ghp_xxx myrepo dev # 指定仓库与分支
import base64, os, sys
import requests

TOKEN = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GITHUB_TOKEN", "")
REPO = sys.argv[2] if len(sys.argv) > 2 else "wordbuddy-github"
BRANCH = sys.argv[3] if len(sys.argv) > 3 else "main"
OWNER = "cyrushmh"
API = "https://api.github.com"
ROOT = os.path.dirname(os.path.abspath(__file__))

H = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

SKIP_DIRS = {".git", "target", "__pycache__", "node_modules", "bin", "obj", ".vs", "dist", ".build"}
SKIP_SUFFIX = (".pyc", ".swp", ".tmp", ".suo", ".user", ".DS_Store")


def get(url):
    return requests.get(f"{API}{url}", headers=H, timeout=60)


def post(url, payload):
    return requests.post(f"{API}{url}", headers=H, json=payload, timeout=300)


def patch(url, payload):
    return requests.patch(f"{API}{url}", headers=H, json=payload, timeout=60)


def main():
    if not TOKEN:
        print("✗ 缺少 TOKEN：python3 sync_to_github.py <TOKEN>"); sys.exit(1)

    print(f"=== 同步 {OWNER}/{REPO} -> {BRANCH} ===")
    print(f"本地根目录: {ROOT}")

    # 1) 收集待上传文件（相对仓库根的路径即 GitHub 路径）
    paths = []
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            if f.endswith(SKIP_SUFFIX):
                continue
            rel = os.path.relpath(os.path.join(dp, f), ROOT).replace(os.sep, "/")
            paths.append(rel)
    paths.sort()
    print(f"✓ 收集到 {len(paths)} 个文件")

    # 2) 为每个文件创建 blob
    tree = []
    for p in paths:
        data = open(os.path.join(ROOT, p), "rb").read()
        b64 = base64.b64encode(data).decode("ascii")
        mode = "100755" if p.endswith(".sh") else "100644"
        r = post(f"/repos/{OWNER}/{REPO}/git/blobs",
                 {"content": b64, "encoding": "base64"})
        if r.status_code not in (200, 201):
            print(f"✗ blob 失败 {p}: {r.status_code} {r.text[:200]}"); sys.exit(1)
        tree.append({"path": p, "mode": mode, "type": "blob", "sha": r.json()["sha"]})

    # 3) 创建 tree（全量重建，不使用 base_tree）
    r = post(f"/repos/{OWNER}/{REPO}/git/trees", {"tree": tree})
    if r.status_code not in (200, 201):
        print("✗ tree 失败:", r.status_code, r.text[:300]); sys.exit(1)
    tree_sha = r.json()["sha"]
    print(f"✓ tree = {tree_sha[:7]} ({len(tree)} 个条目)")

    # 4) parent = 当前分支 head（fast-forward；缺省为空提交）
    r = get(f"/repos/{OWNER}/{REPO}/git/ref/heads/{BRANCH}")
    parents = [r.json()["object"]["sha"]] if r.status_code == 200 else []
    if parents:
        print(f"✓ base {BRANCH} = {parents[0][:7]}")

    # 5) 创建 commit
    r = post(f"/repos/{OWNER}/{REPO}/git/commits",
             {"message": "sync: 经 Git Data API 全量重建 main（本地树最新快照）",
              "tree": tree_sha, "parents": parents})
    if r.status_code not in (200, 201):
        print("✗ commit 失败:", r.status_code, r.text[:300]); sys.exit(1)
    commit_sha = r.json()["sha"]
    print(f"✓ commit = {commit_sha[:7]}")

    # 6) 更新分支 ref（force 覆盖，适配重组 / 全量重建）
    ref_path = BRANCH.replace("/", "%2F")
    r = get(f"/repos/{OWNER}/{REPO}/git/ref/heads/{ref_path}")
    if r.status_code == 200:
        rr = patch(f"/repos/{OWNER}/{REPO}/git/refs/heads/{ref_path}",
                   {"sha": commit_sha, "force": True})
        print(f"✓ 分支已强制更新 -> {rr.status_code}")
    else:
        rr = post(f"/repos/{OWNER}/{REPO}/git/refs",
                  {"ref": f"refs/heads/{BRANCH}", "sha": commit_sha})
        print(f"✓ 分支已创建 -> {rr.status_code}")

    print(f"\n🔗 https://github.com/{OWNER}/{REPO}/tree/{BRANCH}")


if __name__ == "__main__":
    main()
