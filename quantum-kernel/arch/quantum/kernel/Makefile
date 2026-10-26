# SPDX-License-Identifier: GPL-2.0
#
# arch/quantum/kernel Makefile — minimal emulated-architecture core.

extra-y := head.o vmlinux.lds

obj-y := head.o setup.o qpu-core.o quantum-energy.o irq.o time.o asm-offsets.o traps.o process.o
# 量子组网子系统核心（Bell 对分发表 + /proc/quantum-net）；随 QUANTUM_NET 可选。
obj-$(CONFIG_QUANTUM_NET) += quantum-net.o
obj-$(CONFIG_MODULES) += module.o
# ≤6.11 分支 VGA_CONSOLE 旧式默认开启（default y），vgacon.o 引用 screen_info；
# 本架构无真实显示硬件，符号恒零（见 screen_info.c 说明）。
obj-$(CONFIG_VGA_CONSOLE) += screen_info.o
