#!/usr/bin/env bash
# check_shell_lint.sh —— shellcheck 本地门禁（lint-gate 落地一环，#652）
#
# 机制：白名单制。只 lint 本仓自有的 .sh 脚本（下方 WHITELIST 十条），
# 显式排除两类非本仓资产：
#   1) quantum-kernel/** —— 上游 Linux 6.18.57 内核源码树（vendored，
#      其 .sh 由上游维护，lint 口径不属于本仓）
#   2) research/plang/samples/bash.sh —— 语法样例（plang 语言示例，
#      非构建脚本）
#
# 防漏网：脚本末尾再全仓扫描一遍「非排除」.sh，凡不在白名单者直接失败——
# 新增脚本必须显式入册（并同步 system-optimizer/tests/test_lint_gate.py
# 的白名单守卫），否则本门禁与 CI 都会红。
#
# 纪律：
#   - shellcheck 缺席时如实 SKIP（exit 0，打印说明），不假装通过；
#     CI 侧由 .github/workflows/lint-shell.yml 负责先安装 shellcheck
#     再跑本脚本，故 CI 不存在「缺席即放行」。
#   - 默认严重级别（含 style/note）零告警才算过——门禁取最严口径。
set -uo pipefail

# 切到仓库根（本脚本位于 scripts/ 下）
cd "$(dirname "$0")/.." || exit 1

# —— 白名单（相对仓库根，与 test_lint_gate.py 守卫保持一致）——
WHITELIST=(
  scripts/check_shell_lint.sh
  classics-harmony-app/build_hap.sh
  classics-ios-mac/build_ios_mac.sh
  classics-linux/build-arch.sh
  classics-linux/build-debs.sh
  classics-linux/build-mobile.sh
  classics-rs/build-rs.sh
  windows-internals-toolkit/tools/bootstrap.sh
  windows-internals-toolkit/tools/disposable-env.sh
  windows-internals-toolkit/Windows/build.sh
  windows-internals-toolkit/Windows/push-to-github.sh
  windows-internals-toolkit/system-optimizer/research/quantum/quantum-testbed.sh
)

if ! command -v shellcheck >/dev/null 2>&1; then
  echo "[SKIP] shellcheck 未安装——lint 门禁未评估（宿主可 'apt install shellcheck'；CI 由 lint-shell.yml 保证在场）"
  exit 0
fi

fail=0

# 1) 白名单逐条 lint
for f in "${WHITELIST[@]}"; do
  if [ ! -f "$f" ]; then
    echo "[FAIL] 白名单条目不存在（被误删或移名？）: $f"
    fail=1
    continue
  fi
  if ! out=$(shellcheck -f gcc "$f" 2>&1); then
    echo "--- $f"
    echo "$out"
    fail=1
  fi
done

# 2) 防漏网：非排除 .sh 必须全部在白名单内
EXCLUDE_RE='(^|/)(quantum-kernel|\.git)/|research/plang/samples/'
while IFS= read -r f; do
  [ -n "$f" ] || continue
  if ! printf '%s\n' "${WHITELIST[@]}" | grep -qxF "$f"; then
    echo "[FAIL] 发现白名单外 .sh（新增脚本须显式入册并同步守卫测试）: $f"
    fail=1
  fi
done < <(find . -name '*.sh' -not -path './.git/*' 2>/dev/null | sed 's|^\./||' | grep -Ev "$EXCLUDE_RE" | sort)

if [ "$fail" -ne 0 ]; then
  echo "[FAIL] shellcheck 门禁未过（见上文逐条告警）"
  exit 1
fi

echo "[PASS] shellcheck 零告警：白名单 ${#WHITELIST[@]} 个脚本，且无白名单外漏网 .sh"
exit 0
