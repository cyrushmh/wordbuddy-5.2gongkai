/* SPDX-License-Identifier: GPL-2.0 WITH Linux-syscall-note */
#ifndef _UAPI__ASM_QUANTUM_BITS_PER_LONG
#define _UAPI__ASM_QUANTUM_BITS_PER_LONG

/*
 * quantum 是 64 位架构（CONFIG_64BIT，宿主 64 位工具链承载，
 * 见 arch/quantum/Kconfig）。asm-generic 的 bitsperlong.h 在
 * 5.15/5.10 硬编码 32（无 __CHAR_BIT__*__SIZEOF_LONG__ 自动探测，
 * 该探测 6.6 起才有），会让 __kernel_size_t 落成 unsigned int——
 * 64 位指针架构上 size_t 只有 32 位，触发 -Wint-to-pointer-cast
 * 与 -Wbuiltin-declaration-mismatch（-Werror 即构建失败）。
 * 显式声明 64，与 6.6+ 自动探测结果一致；对齐 x86/arm64 惯例
 * （64 位架构自备 bitsperlong.h，不走 generic-y）。
 */
#define __BITS_PER_LONG 64

#ifndef __BITS_PER_LONG_LONG
#define __BITS_PER_LONG_LONG 64
#endif

#endif /* _UAPI__ASM_QUANTUM_BITS_PER_LONG */
