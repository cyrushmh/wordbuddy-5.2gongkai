# SPDX-License-Identifier: GPL-2.0
#
# arch/quantum/Makefile — included by the global makefile for ARCH=quantum.
#
# 量子架构构建入口。SRCARCH=quantum 由顶层 Makefile 的默认映射
# （SRCARCH := $(ARCH)）自动落地，无需修改任何既有文件。

KBUILD_DEFCONFIG := quantum_defconfig

# 量子核在宿主上软件模拟：直接使用宿主编译器（x86-64 工具链生成宿主码），
# 不设 CROSS_COMPILE；量子语义以协处理器子系统（drivers/quantum）呈现。

head-y := arch/quantum/kernel/head.o

core-y += arch/quantum/kernel/ \
	  arch/quantum/mm/


all: vmlinux
