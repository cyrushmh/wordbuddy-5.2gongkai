#!/bin/bash
# SPDX-License-Identifier: GPL-2.0
#
# 轻量 Debian 打包（不依赖 debhelper）：编译 quantum-core 后用 dpkg-deb -b
# 直接构建两个二进制包 quantum-core 与 xfce4-quantum。
#
# 用途：
#   · 在最小构建环境（沙箱、交叉编译根）也能产出可安装 .deb；
#   · 证明「桌面系统基座可为目标架构构建」——Architecture 取自 dpkg --print-architecture，
#     在 ARCH=quantum 目标上用对应工具链构建即得到该架构的包。
#
# 用法：  ./build_deb.sh            # 产出到 ../  (quantum-kernel/)
#        OUT=/tmp/foo ./build_deb.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
VER="${VER:-0.6.84}"
ARCH="$(dpkg --print-architecture)"
OUT="${OUT:-$HERE/../}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "==> 架构 $ARCH  版本 $VER  输出 $OUT"

# 1) 编译守护进程
echo "==> 编译 quantum-core"
make -C "$HERE/quantum-core" clean >/dev/null 2>&1 || true
make -C "$HERE/quantum-core"
BIN="$HERE/quantum-core/quantum-core"
[ -x "$BIN" ] || { echo "编译失败：未生成 $BIN" >&2; exit 1; }

# 计算共享库依赖（优先 dpkg-shlibdeps，失败回退 ldd）
SHLIBS=""
if command -v dpkg-shlibdeps >/dev/null 2>&1; then
	SHLIBS="$(dpkg-shlibdeps -O "$BIN" 2>/dev/null | sed 's/^shlibs:Depends=//')" || true
fi
if [ -z "$SHLIBS" ]; then
	SHLIBS="libc6"
	if ldd "$BIN" 2>/dev/null | grep -q libdbus-1; then SHLIBS="$SHLIBS, libdbus-1-3"; fi
fi
echo "    quantum-core 依赖: $SHLIBS, dbus"

stage_pkg() {  # stage_pkg <pkgdir> <arch>
	local d="$1" a="$2"
	mkdir -p "$d/DEBIAN"
}

# 2) 暂存 quantum-core
QC="$WORK/quantum-core"
mkdir -p "$QC/DEBIAN" "$QC/usr/bin" "$QC/usr/lib/systemd/user" "$QC/usr/share/quantum-core"
cp "$BIN" "$QC/usr/bin/quantum-core"
cp "$HERE/quantum-core/quantum-core.service" "$QC/usr/lib/systemd/user/quantum-core.service"
cp "$HERE/quantum-core/quantum-core.init"    "$QC/usr/share/quantum-core/quantum-core.init"
chmod 0755 "$QC/usr/bin/quantum-core"
chmod 0644 "$QC/usr/lib/systemd/user/quantum-core.service" "$QC/usr/share/quantum-core/quantum-core.init"
cat > "$QC/DEBIAN/control" <<EOF
Package: quantum-core
Version: $VER
Section: x11
Priority: optional
Architecture: $ARCH
Depends: $SHLIBS, dbus
Maintainer: Quantum Packaging <packaging@quantum-arch.local>
Description: 量子架构用户态守护进程
 量子架构(ARCH=quantum)内核暴露的诚实接口（/proc/quantum-energy、
 /proc/quantum-net、/dev/qpu0）的用户态监控守护进程：周期读取能级/相干/纠缠/
 Bell 事件、量子组网(QNIC 链路/对等/纠缠交换/盖亚层)与 QPU 链路统计。
 .
 这是「模拟/记账模型」，不是真实量子硬件；接口缺失时照常运行并标记不可用。
EOF

# 3) 暂存 xfce4-quantum（架构无关）
XQ="$WORK/xfce4-quantum"
mkdir -p "$XQ/DEBIAN" "$XQ/usr/share/xsessions" "$XQ/etc/xdg/autostart" \
         "$XQ/usr/bin" "$XQ/usr/lib/quantum-core/genmon" \
         "$XQ/usr/share/themes/Quantum/gtk-3.0" \
         "$XQ/usr/share/backgrounds/quantum" "$XQ/usr/share/applications"
cp "$HERE/xsessions/quantum.desktop"                  "$XQ/usr/share/xsessions/quantum.desktop"
cp "$HERE/xsessions/autostart-quantum-core.desktop"   "$XQ/etc/xdg/autostart/autostart-quantum-core.desktop"
cp "$HERE/session/quantum-session"                    "$XQ/usr/bin/quantum-session"
cp "$HERE/session/quantum-panel-add-genmon.sh"        "$XQ/usr/lib/quantum-core/quantum-panel-add-genmon.sh"
cp "$HERE/genmon/quantum-energy-genmon.sh"            "$XQ/usr/lib/quantum-core/genmon/quantum-energy-genmon.sh"
cp "$HERE/genmon/quantum-qpu-genmon.sh"               "$XQ/usr/lib/quantum-core/genmon/quantum-qpu-genmon.sh"
cp "$HERE/genmon/quantum-net-genmon.sh"               "$XQ/usr/lib/quantum-core/genmon/quantum-net-genmon.sh"
cp "$HERE/theme/Quantum/index.theme"                  "$XQ/usr/share/themes/Quantum/index.theme"
cp "$HERE/theme/Quantum/gtk-3.0/gtk.css"              "$XQ/usr/share/themes/Quantum/gtk-3.0/gtk.css"
cp "$HERE/theme/quantum-wallpaper.svg"                "$XQ/usr/share/backgrounds/quantum/quantum-wallpaper.svg"
cp "$HERE/quantum-settings/quantum-settings.desktop"  "$XQ/usr/share/applications/quantum-settings.desktop"
cp "$HERE/quantum-settings/quantum-settings.sh"       "$XQ/usr/bin/quantum-settings"
chmod 0755 "$XQ/usr/bin/quantum-session" "$XQ/usr/bin/quantum-settings" \
           "$XQ/usr/lib/quantum-core/quantum-panel-add-genmon.sh" \
           "$XQ/usr/lib/quantum-core/genmon/quantum-energy-genmon.sh" \
           "$XQ/usr/lib/quantum-core/genmon/quantum-qpu-genmon.sh" \
           "$XQ/usr/lib/quantum-core/genmon/quantum-net-genmon.sh"
chmod 0644 "$XQ/usr/share/xsessions/quantum.desktop" \
           "$XQ/etc/xdg/autostart/autostart-quantum-core.desktop" \
           "$XQ/usr/share/themes/Quantum/index.theme" \
           "$XQ/usr/share/themes/Quantum/gtk-3.0/gtk.css" \
           "$XQ/usr/share/backgrounds/quantum/quantum-wallpaper.svg" \
           "$XQ/usr/share/applications/quantum-settings.desktop"
cat > "$XQ/DEBIAN/control" <<EOF
Package: xfce4-quantum
Version: $VER
Section: x11
Priority: optional
Architecture: all
Depends: xfce4, xfce4-goodies, quantum-core, dbus
Provides: quantum-desktop-base
Maintainer: Quantum Packaging <packaging@quantum-arch.local>
Description: 面向量子架构的 XFCE 桌面基座
 XFCE 会话变体、量子色系 GTK 主题与壁纸、Genmon 面板小程序与设置入口，
 接线量子架构内核的诚实接口；可作为 quantum-desktop-base 提供方。
EOF

# 4) 构建
mkdir -p "$OUT"
dpkg-deb -b --root-owner-group "$QC" "$OUT/quantum-core_${VER}_${ARCH}.deb"
dpkg-deb -b --root-owner-group "$XQ" "$OUT/xfce4-quantum_${VER}_all.deb"
echo "==> 已产出："
ls -1 "$OUT"/quantum-core_"$VER"_*.deb "$OUT"/xfce4-quantum_"$VER"_*.deb
