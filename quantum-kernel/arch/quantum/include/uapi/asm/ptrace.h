/* SPDX-License-Identifier: GPL-2.0 */
/*
 * include/uapi/asm/ptrace.h — emulated register file for ptrace.
 * 宿主模拟：寄存器组以「量子通用寄存器 + PC + 标志」极简建模。
 */
#ifndef _UAPI_ASM_QUANTUM_PTRACE_H
#define _UAPI_ASM_QUANTUM_PTRACE_H

#include <linux/types.h>

struct user_qregs {
	__u64 gpr[16];	/* 通用寄存器 r0..r15 */
	__u64 pc;	/* 程序计数器 */
	__u64 flags;	/* 状态标志 */
	__u64 qacc;	/* QPU 访问句柄（最近一次 enc/dec 的链路序号） */
};

/* GPR 索引别名（ptrace PTRACE_GETREGSET 用 NT_PRSTATUS 传 user_qregs）。 */
#define QREG_R0		0
#define QREG_R15	15
#define QREG_PC		16
#define QREG_FLAGS	17
#define QREG_QACC	18

#endif /* _UAPI_ASM_QUANTUM_PTRACE_H */
