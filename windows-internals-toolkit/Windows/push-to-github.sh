#!/usr/bin/env bash
# 一键把本仓库推送到 GitHub: cyrushmh/windows-internals-toolkit
#
# 用法:
#   bash push-to-github.sh <GitHub PAT>
#   TOKEN=<GitHub PAT> bash push-to-github.sh
#
# 令牌要求（二选一）:
#   A. 经典 PAT: 勾 repo 作用域（推荐，最省事）
#   B. 细粒度 PAT: Repository access = All repositories
#                  Contents = Read and write
#                  Repository creation = Read and write（仓库尚未建时需要）
set -uo pipefail
cd "$(dirname "$0")" || exit 1

TOKEN="${1:-${TOKEN:-}}"
if [ -z "$TOKEN" ]; then
  echo "用法: bash push-to-github.sh <GitHub PAT>   或   TOKEN=<PAT> bash push-to-github.sh"
  exit 1
fi

REPO_NAME="${REPO_NAME:-wordbuddy-github}"
REPO="cyrushmh/$REPO_NAME"
API="https://api.github.com"
step() { echo; echo "==> $*"; }

step "验证令牌"
CODE=$(curl -sS -m 30 -o /tmp/p_who.json -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$API/user" 2>/dev/null || echo "000")
if [ "$CODE" != "200" ]; then
  echo "✗ 令牌无效或网络不通 (HTTP $CODE)"
  head -c 200 /tmp/p_who.json 2>/dev/null; echo
  exit 1
fi
python3 -c "import json;print('✓ 已登录为', json.load(open('/tmp/p_who.json'))['login'])"

step "检查仓库 $REPO"
EXISTS=$(curl -sS -m 30 -o /tmp/p_repo.json -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$API/repos/$REPO" 2>/dev/null || echo "000")
case "$EXISTS" in
  200) echo "✓ 仓库已存在" ;;
  404)
    echo "仓库不存在，尝试创建 public 仓库..."
    C=$(curl -sS -m 30 -o /tmp/p_create.json -w "%{http_code}" -X POST \
         -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
         "$API/user/repos" \
         -d "{\"name\":\"$REPO_NAME\",\"private\":false,\"auto_init\":false,\"description\":\"Windows Internals 分析系列：磁盘/Win10 优化 + PE 程序格式文档与 PE 头查看器\"}")
    if [ "$C" = "201" ]; then
      echo "✓ 仓库已创建"
    elif [ "$C" = "422" ]; then
      echo "✗ 仓库已存在，但当前令牌看不到它（HTTP 422 name already exists）"
      echo "  修复: 细粒度 PAT 的 Repository access 改为 All repositories（或把该仓加入授权列表）"
      exit 1
    else
      echo "✗ 建仓失败 (HTTP $C)：令牌缺少 Repository creation 权限"
      head -c 300 /tmp/p_create.json 2>/dev/null; echo
      exit 1
    fi
    curl -sS -m 30 -o /tmp/p_repo.json -H "Authorization: Bearer $TOKEN" "$API/repos/$REPO"
    ;;
  *) echo "✗ 无法读取仓库信息 (HTTP $EXISTS)"; exit 1 ;;
esac

step "校验对该仓的写权限"
PUSH=$(python3 - <<'PY'
import json
try:
    d = json.load(open('/tmp/p_repo.json'))
    print(str(d.get('permissions', {}).get('push', False)).lower())
except Exception:
    print('false')
PY
)
if [ "$PUSH" != "true" ]; then
  echo "✗ 令牌对该仓库没有 push 权限"
  echo "  修复: GitHub → Settings → Developer settings → Personal access tokens → 编辑该令牌"
  echo "       • Repository access = All repositories"
  echo "       • Contents = Read and write"
  echo "  或改用经典 PAT（只勾 repo 作用域）"
  exit 1
fi
echo "✓ 具备 push 权限"

step "推送 main 分支"
git remote remove origin 2>/dev/null
git remote add origin "https://x-access-token:${TOKEN}@github.com/${REPO}.git"
git branch -M main
if ! git push -u origin main; then
  echo "✗ 推送失败（多为网络不通或令牌权限不足）"
  exit 1
fi

step "关闭 fork（保持公开，但不允许他人 fork）"
curl -sS -m 30 -o /dev/null -X PATCH \
  -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
  "$API/repos/$REPO" -d '{"allow_forking":false}'

step "完成"
echo "🔗 https://github.com/$REPO"
