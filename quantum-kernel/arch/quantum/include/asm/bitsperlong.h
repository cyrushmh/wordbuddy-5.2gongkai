/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _ASM_QUANTUM_BITS_PER_LONG
#define _ASM_QUANTUM_BITS_PER_LONG

/*
 * quantum 是 64 位架构（CONFIG_64BIT，宿主 64 位工具链承载，见
 * arch/quantum/Kconfig）。
 *
 * 内核 C 编译时 arch/quantum/include/asm 优先于 .../include/uapi/asm，
 * 故 #include <asm/bitsperlong.h> 命中本文件（非 uapi）。本文件需同时
 * 给出内核内部用的 BITS_PER_LONG 与 uapi 头（signal.h / posix_types.h）
 * 用的 __BITS_PER_LONG；并把原本位于 asm-generic/bitsperlong.h 的
 * small_const_nbits 也在此自备——因为本架构不走 generic-y wrapper
 * （5.15/5.10 的 asm-generic/bitsperlong.h 在 64 位下不一定落到 64，
 * 且其 small_const_nbits 依赖该文件被间接包含，而我们不复用 wrapper）。
 *
 * 显式声明 64，与 6.6+ 的 __CHAR_BIT__*__SIZEOF_LONG__ 自动探测一致，
 * 对齐 x86/arm64 惯例（64 位架构自备 asm/bitsperlong.h，不走 generic-y）。
 */
#define BITS_PER_LONG 64
#define __BITS_PER_LONG 64
#define BITS_PER_LONG_LONG 64
#define __BITS_PER_LONG_LONG 64

#define small_const_nbits(nbits) \
	(__builtin_constant_p(nbits) && (nbits) <= BITS_PER_LONG && (nbits) > 0)

#endif /* _ASM_QUANTUM_BITS_PER_LONG */
