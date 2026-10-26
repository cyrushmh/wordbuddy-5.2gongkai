/* SPDX-License-Identifier: GPL-2.0 */
/*
 * include/uapi/asm/sigcontext.h — signal context for the emulated arch.
 * 信号交付时保存通用寄存器组与 QPU 访问句柄。
 */
#ifndef _UAPI_ASM_QUANTUM_SIGCONTEXT_H
#define _UAPI_ASM_QUANTUM_SIGCONTEXT_H

#include <linux/types.h>

struct sigcontext {
	__u64 gpr[16];
	__u64 pc;
	__u64 flags;
	__u64 qacc;
	/* FP/SIMD 面在模拟架构中不存在，留空。 */
};

#endif /* _UAPI_ASM_QUANTUM_SIGCONTEXT_H */
