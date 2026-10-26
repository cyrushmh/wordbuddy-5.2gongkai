#!/usr/bin/env bash
# classics-rs 跨平台构建矩阵
# 维度：硬件架构(x86-64 / ARM64 / ARM32 / RISC-V / x86-32 / PowerPC64LE / IBM-Z)
#       × 系统(Linux / Windows×2 / Web-WASM)
# 复用 Rust 单一内核，一次编写、全平台产出。
#
# 不可构建（如实记录于 .cargo/config.toml 头注释）：
#   aarch64-pc-windows-gnu（Windows on ARM）——rustc target-list 无此项；
#   *-apple-darwin —— 无 macOS SDK。
set -uo pipefail
cd "$(dirname "$0")" || exit 1

DIST="dist"
mkdir -p "$DIST"

# 硬件×系统 目标矩阵（10 项；每项目标与链接器配置一一对应，见 .cargo/config.toml）
TARGETS=(
  x86_64-unknown-linux-gnu     # Linux  · x86-64    (原生)
  aarch64-unknown-linux-gnu    # Linux  · ARM64
  armv7-unknown-linux-gnueabihf # Linux · ARM32
  riscv64gc-unknown-linux-gnu  # Linux  · RISC-V
  i686-unknown-linux-gnu       # Linux  · x86-32
  powerpc64le-unknown-linux-gnu # Linux · PowerPC 64 LE
  s390x-unknown-linux-gnu      # Linux  · IBM-Z
  x86_64-pc-windows-gnu        # Windows· x86-64
  i686-pc-windows-gnu          # Windows· x86-32
  wasm32-unknown-unknown       # Web    · WASM
)

FAILED=()
SKIPPED=()

for t in "${TARGETS[@]}"; do
  # 前置检查：rust target 已安装？
  if ! rustup target list --installed 2>/dev/null | grep -qx "$t"; then
    echo ">>> 跳过 $t（rust target 未安装：rustup target add $t）"
    SKIPPED+=("$t")
    continue
  fi
  # 前置检查：交叉链接器在位？
  linker=$(awk -v tgt="[target.$t]" '
    $0 == tgt {inblk=1; next}
    inblk && /^linker/ {gsub(/[ \t"]/,"",$3); print $3; exit}
    inblk && /^\[/ {exit}
  ' .cargo/config.toml 2>/dev/null || true)
  if [ -n "$linker" ] && ! command -v "$linker" >/dev/null 2>&1; then
    echo ">>> 跳过 $t（交叉链接器 $linker 不在位）"
    SKIPPED+=("$t")
    continue
  fi

  echo ">>> 构建 $t"
  if ! cargo build --release --target "$t" 2>&1 | tail -3; then
    echo "!!! 构建失败：$t"
    FAILED+=("$t")
    continue
  fi
  if [ "$t" = "wasm32-unknown-unknown" ]; then
    src="target/$t/release/classics.wasm"; dst="$DIST/classics-$t.wasm"
  elif [[ "$t" == *windows* ]]; then
    src="target/$t/release/classics.exe"; dst="$DIST/classics-$t.exe"
  else
    src="target/$t/release/classics"; dst="$DIST/classics-$t"
  fi
  if [ ! -f "$src" ]; then
    echo "!!! 产物缺失：$src"
    FAILED+=("$t")
    continue
  fi
  cp "$src" "$dst"
  echo "    -> $dst"
done

echo ""
echo "=== 产物清单（file 验证）==="
for f in "$DIST"/*; do
  [ -f "$f" ] && printf '%-48s %s\n' "$(basename "$f")" "$(file -b "$f" | cut -c1-72)"
done

if [ ${#SKIPPED[@]} -gt 0 ]; then
  echo ""
  echo "=== 跳过（${#SKIPPED[@]}）==="
  printf '  %s\n' "${SKIPPED[@]}"
fi
if [ ${#FAILED[@]} -gt 0 ]; then
  echo ""
  echo "=== 失败（${#FAILED[@]}）==="
  printf '  %s\n' "${FAILED[@]}"
  exit 1
fi
echo ""
echo "全部 ${#TARGETS[@]} 个目标构建成功。"
