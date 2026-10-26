#!/bin/sh
# SPDX-License-Identifier: GPL-2.0
# quantum-kernel/scripts/build.sh — 量子架构内核构建验收（三层如实报告）。
#
# 用法： sh scripts/build.sh [版本号] [树目录]
#   版本号默认 6.18.57；树目录默认 linux-<版本号>。
# 前置：linux-<版本号>/ 已解压且补丁已应用（见 fetch_kernel.sh）。
# 依赖：gcc make flex bison bc perl libelf-dev（host 工具链）。
set -eu

VER=${1:-6.18.57}
KDIR=${2:-linux-${VER}}
cd "$KDIR"

echo "== 第 1 层：defconfig 全解析（Kconfig 依赖图验收，linux-${VER}） =="
make ARCH=quantum O=build quantum_defconfig
grep -E "^CONFIG_QUANTUM" build/.config | sed 's/^/   /'

echo ""
echo "== 对照验收：其他架构不破坏（x86_64 defconfig 正常生成即通过） =="
make ARCH=x86_64 O=build-x86 defconfig
echo "   x86_64 配置项数： $(grep -c '^CONFIG_' build-x86/.config)"

echo ""
echo "== 第 2 层：真实全量构建（vmlinux 链接验收） =="
# 完整日志落盘（build-full.log），终端只展示尾部；|| true 让失败也进入第 3 层如实报告
make ARCH=quantum O=build -j"$(nproc)" > build-full.log 2>&1 || true
tail -25 build-full.log

echo ""
echo "== 第 3 层：产物与诚实边界 =="
if [ -f build/vmlinux ]; then
	echo "   vmlinux: $(ls -la build/vmlinux | awk '{print $5}') 字节（链接成功）"
	nm build/vmlinux | grep -c ' T quantum_' | sed 's/^/   quantum_* 导出符号数: /'
else
	echo "   vmlinux: 未生成（构建失败，见上方输出）"
fi
echo ""
echo "   诚实边界：vmlinux 在宿主工具链上真实链接（宿主机器码），但"
echo "   ① 量子处理器没有 gcc 后端，QPU 本身是宿主模拟；"
echo "   ② 没有可引导 quantum 镜像格式（无 bzImage/Image 引导协议）；"
echo "   ③ 空闲/能量模型是量子力学启发的记账语义（/proc/quantum-energy）。"
echo "   本验收承诺：defconfig 全解析 + 全量构建链接 vmlinux + 其他架构零破坏。"
