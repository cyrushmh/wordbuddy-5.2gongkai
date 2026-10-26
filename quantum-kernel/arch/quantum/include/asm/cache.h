/* SPDX-License-Identifier: GPL-2.0 */
/*
 * include/asm/cache.h — cache line geometry for the emulated arch.
 * 模拟核无真实缓存分层：取宿主常见 64B 口径。
 */
#ifndef _ASM_QUANTUM_CACHE_H
#define _ASM_QUANTUM_CACHE_H

#define L1_CACHE_SHIFT		6
#define L1_CACHE_BYTES		(1 << L1_CACHE_SHIFT)
#define ARCH_DMA_MINALIGN	L1_CACHE_BYTES
#define ARCH_KMALLOC_MINALIGN	L1_CACHE_BYTES

#ifndef __ASSEMBLY__
static inline int cache_line_size(void)
{
	return L1_CACHE_BYTES;
}
#endif /* __ASSEMBLY__ */

#endif /* _ASM_QUANTUM_CACHE_H */
