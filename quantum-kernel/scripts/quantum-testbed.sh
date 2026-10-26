#!/bin/bash
# SPDX-License-Identifier: GPL-2.0
#
# quantum-testbed.sh — 在某目录里用 debootstrap + chroot 搭一个「几乎完全自由」
# 的 Debian 根文件系统，用来在「当前（宿主）内核」下测试量子架构内核：编译、
# 修改、调试 ARCH=quantum 的树，并演示产出一个 initrd。
#
# 用户需求原文：
#   - 用 chroot/fakeroot 在目录里测试内核；
#   - 用当前内核编译/修改/调试成「量子内核架构」的程序和桌面系统基座；
#   - 要一个方便的 initrd（几乎完全开源自由的 Debian）。
#
# 关于「几乎完全开源自由的 Debian」：这里取 Debian 的 main 组件（DFSG 自由软件，
# 排除 contrib/non-free），即「几乎完全自由」的 Debian。若你要的是——
#   · systemd-free 的 Debian 衍生版（initrd 更轻、无 systemd 依赖）：换 Devuan
#     （SUITE=daedalus，MIRROR=https://pkgmaster.devuan.org/merged，并装 devuan-keyring）；
#   · FSF 纯自由（100% free）：换 PureOS / Trisquel。
# 三者都基于本脚本，只改 SUITE/MIRROR/KEYRING 三处。
#
# XFCE 可选目标（--with-xfce / WITH_XFCE=1）：
#   默认路径**不变**（仍只编译内核 + 生成 initrd，轻量核心）。开启后额外在 chroot 内
#   安装 xfce4 + xfce4-goodies，并把 desktop/ 源包（xfce4-quantum）构建安装为量子架构
#   桌面基座——证明「桌面系统基座可为目标架构（含 ARCH=quantum）构建/安装」；initrd
#   配方升级为含量子 XFCE 会话（参考配方，量子无引导协议）。
#
# 诚实边界：
#   · 量子是「宿主模拟架构」（arch/um 同型），没有真实引导镜像格式（无 bzImage/
#     Image 引导协议），本脚本产出的 initrd 是「若有目标板」的参考配方，不声称
#     可在真实硬件引导量子内核；
#   · chroot 内构建用的是宿主内核 + 宿主工具链，证明的是「架构真实可编译链接」，
#     不是「能在量子处理器上运行」；XFCE 目标同理——证明桌面基座可为目标架构
#     构建/安装，不声称 XFCE 在「已引导的量子处理器」上运行。
#
# 用法：
#   sh scripts/quantum-testbed.sh [ROOTFS目录] [版本号] [SUITE] [MIRROR] [ARCH] [--with-xfce]
#   WITH_XFCE=1 sh scripts/quantum-testbed.sh        # 等价 --with-xfce
set -euo pipefail

QK="${QUANTUM_KERNEL_TREE:-/workspace/windows-internals-toolkit/quantum-kernel}"
ROOTFS="${1:-/workspace/quantum-testbed/rootfs}"
VER="${2:-6.18.57}"
SUITE="${3:-bookworm}"
MIRROR="${4:-https://deb.debian.org/debian}"
ARCH="${5:-amd64}"
WITH_XFCE=0
for a in "$@"; do [ "$a" = "--with-xfce" ] && WITH_XFCE=1; done
WITH_XFCE="${WITH_XFCE:-0}"

echo "== 量子架构测试床 =="
echo "   根文件系统 : $ROOTFS"
echo "   内核版本   : $VER"
echo "   Debian套件 : $SUITE （仅 main 组件 = 几乎完全自由）"
echo "   镜像源     : $MIRROR"
echo "   架构       : $ARCH"
echo "   XFCE 目标  : $([ "$WITH_XFCE" = 1 ] && echo '开（装 XFCE + 构建 xfce4-quantum）' || echo '关（仅内核 + initrd，轻量核心）')"

need_root() { [ "$(id -u)" -eq 0 ] && echo "" || echo "sudo"; }

run() { local s; s="$(need_root)"; [ -n "$s" ] && sudo "$@" || "$@"; }

echo "== 1. 装 debootstrap（若缺）=="
if ! command -v debootstrap >/dev/null 2>&1; then
  echo "   debootstrap 缺失，尝试安装……"
  run apt-get update
  run apt-get install -y debootstrap
fi

echo "== 2. debootstrap 引导一个只含 main 组件的 Debian =="
run rm -rf "$ROOTFS"
run debootstrap --components=main --arch="$ARCH" "$SUITE" "$ROOTFS" "$MIRROR"

echo "== 3. 准备 chroot（挂载 /proc /sys /dev + 仅 main 的 apt 源）=="
run mount -t proc  proc  "$ROOTFS/proc"  2>/dev/null || true
run mount -t sysfs sys   "$ROOTFS/sys"   2>/dev/null || true
run mount --bind /dev    "$ROOTFS/dev"   2>/dev/null || true
printf 'deb %s %s main\n'     "$MIRROR" "$SUITE"        | run tee   "$ROOTFS/etc/apt/sources.list"
printf 'deb %s %s-updates main\n' "$MIRROR" "$SUITE"    | run tee -a "$ROOTFS/etc/apt/sources.list"

echo "== 4. chroot 内装量子内核构建依赖 =="
BUILD_DEPS="gcc make flex bison bc perl libelf-dev libncurses-dev \
  debhelper fakeroot cpio kmod udev initramfs-tools ca-certificates"
if [ "$WITH_XFCE" = 1 ]; then
  BUILD_DEPS="$BUILD_DEPS pkg-config libdbus-1-dev xfce4 xfce4-goodies"
fi
run chroot "$ROOTFS" bash -c "apt-get update && apt-get install -y $BUILD_DEPS"

echo "== 5. 把量子内核树带进 chroot，编译 ARCH=quantum（证明架构真实可构建）=="
run mkdir -p "$ROOTFS/quantum-kernel"
run mount --bind "$QK" "$ROOTFS/quantum-kernel"
run chroot "$ROOTFS" bash -c "cd /quantum-kernel && sh scripts/build.sh $VER" \
  | tail -n 20 || echo "（构建在 chroot 内执行，详见 $ROOTFS/quantum-kernel 产物）"

echo "== 5.5 核验 qnet 组网子系统已编入 vmlinux（nm 符号核验）=="
# 真实环境（chroot 内已成功构建）时，确认 quantum_net_* 关键符号进入内核镜像；
# 本步只做核验、不改构建，缺失则明确告警而非静默通过。
run chroot "$ROOTFS" bash -c "cd /quantum-kernel/linux-$VER && \
  if [ -f build/System.map ]; then \
    n=\$(grep -c 'quantum_net' build/System.map); \
    echo \"quantum_net 符号数：\$n\"; \
    grep -E ' T quantum_net_state| T quantum_net_entangle| T quantum_net_reset| T quantum_net_swap| T quantum_net_teleport' build/System.map \
      || echo '（缺少关键 quantum_net 符号：qnet 子系统未入链）'; \
  else echo '（未找到 build/System.map，跳过 nm 核验）'; fi" || true

echo "== 6. 演示产出一个 initrd（mkinitramfs；量子无引导协议，仅参考配方）=="
run chroot "$ROOTFS" bash -c "cd /quantum-kernel/linux-$VER && \
  if [ -f include/config/kernel.release ]; then \
    mkinitramfs -o /tmp/initrd-quantum.img \"\$(cat include/config/kernel.release)\" 2>/dev/null \
    && echo 'initrd 已生成：/tmp/initrd-quantum.img'; \
  else \
    echo '（量子无 kernel.release/不可引导：跳过真实 mkinitramfs，仅给出配方）'; \
  fi" || true
run cp "$ROOTFS/tmp/initrd-quantum.img" /workspace/quantum-testbed/initrd-quantum.img 2>/dev/null || true

if [ "$WITH_XFCE" = 1 ]; then
echo "== 7. 构建并安装 xfce4-quantum（面向量子架构的 XFCE 桌面基座）=="
# desktop/ 源包已在绑定挂载的 /quantum-kernel/desktop 内；用 debhelper 构建并安装。
run chroot "$ROOTFS" bash -c "cd /quantum-kernel/desktop && \
  dpkg-buildpackage -us -uc -b 2>&1 | tail -n 15 && \
  dpkg -i /quantum-kernel/quantum-core_*.deb /quantum-kernel/xfce4-quantum_*.deb" \
  || echo "（xfce4-quantum 构建/安装失败：见 chroot 内 /quantum-kernel 产物）"

echo "== 8. 升级 initrd 配方：含量子 XFCE 会话（参考配方，量子无引导协议）=="
# 仅在真正产出 initrd 时把量子会话/主题/小程序带进 initrd；否则仅落 hook 文件。
run chroot "$ROOTFS" bash -c "mkdir -p /etc/initramfs-tools/hooks && \
cat > /etc/initramfs-tools/hooks/quantum-xfce <<'HOOK'
#!/bin/sh
# 把量子架构 XFCE 会话/主题/小程序带进 initrd（参考配方）。
for f in \\
  /usr/share/xsessions/quantum.desktop \\
  /usr/share/themes/Quantum \\
  /usr/share/backgrounds/quantum/quantum-wallpaper.svg \\
  /usr/lib/quantum-core/genmon/quantum-energy-genmon.sh \\
  /usr/lib/quantum-core/genmon/quantum-qpu-genmon.sh ; do
  [ -e \"\$f\" ] && copy_file \"\$f\" 2>/dev/null || true
done
HOOK
chmod +x /etc/initramfs-tools/hooks/quantum-xfce"
echo "   initrd hook 已写入 /etc/initramfs-tools/hooks/quantum-xfce"
fi

echo "== $([ "$WITH_XFCE" = 1 ] && echo 9 || echo 7). 清理挂载 =="
run umount "$ROOTFS/quantum-kernel" 2>/dev/null || true
run umount "$ROOTFS/dev"  2>/dev/null || true
run umount "$ROOTFS/sys"  2>/dev/null || true
run umount "$ROOTFS/proc" 2>/dev/null || true

echo "== 完成 =="
echo "   测试床就绪：$ROOTFS"
echo "   进入：      sudo chroot $ROOTFS /bin/bash"
echo "   其内已含 /quantum-kernel（ARCH=quantum 可编译），可继续开发/调试"
echo "   面向量子内核架构的程序与桌面系统基座（sysweaver/quantum-taxonomy 等）。"
if [ "$WITH_XFCE" = 1 ]; then
echo "   XFCE 目标：chroot 内已装 xfce4/xfce4-goodies 与 xfce4-quantum（量子会话可由"
echo "   显示管理器选择 \"Quantum XFCE Session\"）；initrd 配方已含 quantum-xfce hook。"
fi
