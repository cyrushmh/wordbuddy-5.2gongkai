#!/usr/bin/env bash
# 交叉编译 peinfo / peview 为 Windows PE，并运行跨语言一致性测试。
# 依赖: mingw-w64 (x86_64-w64-mingw32-gcc, i686-w64-mingw32-gcc)、cargo、python3
# 说明:
#   - C 源码唯一真源在 src/c/peinfo/peinfo.c，编译产物放到 tools/。
#   - 一致性测试会再用本机 gcc/cargo 编出 C/Rust 本机版，在 Linux 上比对三个实现是否一致。
set -euo pipefail
cd "$(dirname "$0")"   # Windows/

: "${CC64:=x86_64-w64-mingw32-gcc}"
: "${CC32:=i686-w64-mingw32-gcc}"
: "${CCARM64:=aarch64-w64-mingw32-gcc}"
SRC_C=src/c/peinfo/peinfo.c
SRC_GUI=src/c/win32_gui/peview.c
mkdir -p tools

echo "==> [C] 编译 PE32+ (x64) 控制台版 ..."
"$CC64" -O2 -s "$SRC_C" -o tools/peinfo.exe

echo "==> [C] 编译 PE32 (x86) 控制台版 ..."
"$CC32" -O2 -s "$SRC_C" -o tools/peinfo32.exe

echo "==> [C/Win32] 编译原生 GUI 版 PE Viewer (x64) ..."
"$CC64" -O2 -s "$SRC_GUI" -mwindows -lcomdlg32 -o tools/peview.exe

echo "==> [Rust] 交叉编译 PE 解析 CLI (x64) ..."
( cd src/rust/peinfo && cargo build --release --target x86_64-pc-windows-gnu -q )
cp src/rust/peinfo/target/x86_64-pc-windows-gnu/release/peinfo.exe tools/peinfo_rs.exe

echo "==> [C] 编译 PE (arm64) 控制台版 ..."
"$CCARM64" -O2 -s "$SRC_C" -o tools/peinfo-arm64.exe

echo "==> [Rust] 交叉编译 PE 解析 CLI (arm64) ..."
( cd src/rust/peinfo && rustup target add aarch64-pc-windows-gnu 2>/dev/null; cargo build --release --target aarch64-pc-windows-gnu -q )
cp src/rust/peinfo/target/aarch64-pc-windows-gnu/release/peinfo.exe tools/peinfo_rs_arm64.exe

echo "==> 校验产物类型"
file tools/peinfo.exe tools/peinfo32.exe tools/peview.exe tools/peinfo_rs.exe tools/peinfo-arm64.exe tools/peinfo_rs_arm64.exe

echo "==> 跨语言一致性测试（C / Rust / Python / .NET / Java / Ruby）"
python3 tests/parity_test.py

echo "完成。产物: tools/{peinfo.exe, peinfo32.exe, peview.exe, peinfo_rs.exe, peinfo-arm64.exe, peinfo_rs_arm64.exe}"
