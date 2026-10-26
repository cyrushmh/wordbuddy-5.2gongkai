#!/bin/sh
# SPDX-License-Identifier: GPL-2.0
# quantum-kernel/scripts/fetch_kernel.sh — 重建路径第一步：下载并校验上游 LTS 源码。
#
# 用法： sh scripts/fetch_kernel.sh [版本号] [目标目录]
#   版本号默认 6.18.57；已实测版本矩阵见 docs/46_各LTS版本补丁矩阵.md
#   （6.18 / 6.12 / 6.6 / 6.1 / 5.15 / 5.10 六个长期分支）。
# 产物： <目标目录>/linux-<版本号>/（上游未修改树）
set -eu

VER=${1:-6.18.57}
DEST=${2:-.}
MAJ=${VER%%.*}
URL_PRIMARY="https://cdn.kernel.org/pub/linux/kernel/v${MAJ}.x/linux-${VER}.tar.xz"
URL_MIRROR="https://mirrors.tuna.tsinghua.edu.cn/kernel/v${MAJ}.x/linux-${VER}.tar.xz"

mkdir -p "$DEST"
cd "$DEST"

if [ ! -f "linux-${VER}.tar.xz" ]; then
    echo ">> 下载 linux-${VER}.tar.xz（优先官方 CDN，慢则切 TUNA 镜像）"
    curl -fSs -o "linux-${VER}.tar.xz" "$URL_PRIMARY" \
        || curl -fSs -C - -o "linux-${VER}.tar.xz" "$URL_MIRROR"
fi

echo ">> 校验（官方 sha256 见 https://kernel.org/pub/linux/kernel/v${MAJ}.x/sha256sums.asc）"
sha256sum "linux-${VER}.tar.xz"

echo ">> 解压"
tar xf "linux-${VER}.tar.xz"

echo ">> 完成：$(pwd)/linux-${VER}/"
echo ">> 下一步： cd linux-${VER} && patch -p1 < ../../patches/0001-quantum-architecture-v1.patch"
echo ">>         （若该版本有专属补丁，用 patches/0001-quantum-architecture-v1-${VER}.patch）"
echo ">>         然后 sh ../../scripts/build.sh ${VER}"
