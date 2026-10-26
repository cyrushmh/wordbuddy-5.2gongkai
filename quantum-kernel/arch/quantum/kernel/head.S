/* SPDX-License-Identifier: GPL-2.0 */
/*
 * arch/quantum/kernel/head.S — emulated architecture entry stub.
 * 宿主模拟架构无真实引导代码：入口桩仅保留占位符号。
 */
	.text
	.globl	quantum_start
quantum_start:
	ret
