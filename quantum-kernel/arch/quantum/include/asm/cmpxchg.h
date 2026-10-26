/* SPDX-License-Identifier: GPL-2.0 */
/*
 * include/asm/cmpxchg.h — compare-and-exchange for the emulated arch.
 * 单核模拟：无并发争用，比较后写即原子语义（诚实口径）。
 */
#ifndef _ASM_QUANTUM_CMPXCHG_H
#define _ASM_QUANTUM_CMPXCHG_H

#include <linux/types.h>

#ifndef __ASSEMBLY__

static inline unsigned long
__quantum_cmpxchg(volatile void *ptr, unsigned long old,
		  unsigned long new, int size)
{
	unsigned long prev;

	switch (size) {
	case 1:
		prev = *(volatile unsigned char *)ptr;
		if (prev == old)
			*(volatile unsigned char *)ptr = (unsigned char)new;
		break;
	case 2:
		prev = *(volatile unsigned short *)ptr;
		if (prev == old)
			*(volatile unsigned short *)ptr = (unsigned short)new;
		break;
	case 4:
		prev = *(volatile unsigned int *)ptr;
		if (prev == old)
			*(volatile unsigned int *)ptr = (unsigned int)new;
		break;
	case 8:
		prev = *(volatile unsigned long *)ptr;
		if (prev == old)
			*(volatile unsigned long *)ptr = new;
		break;
	default:
		__builtin_trap();
	}
	return prev;
}

/* 保持表达式类型（typeof）：rcu/llist 对指针 xchg 依赖此性质。 */
#define arch_cmpxchg(ptr, o, n)						\
({									\
	__typeof__(*(ptr)) __ret;					\
	__ret = (__typeof__(*(ptr)))__quantum_cmpxchg((ptr),		\
			(unsigned long)(o), (unsigned long)(n),		\
			sizeof(*(ptr)));				\
	__ret;								\
})

#ifndef arch_cmpxchg64
#define arch_cmpxchg64(ptr, o, n)	arch_cmpxchg((ptr), (o), (n))
#endif

/*
 * _local 变体：单核模拟架构的中断内/中断外语义一致（宿主进程承载
 * 执行，无真实并发窗口），直接映射到本架构实现。
 * 不包含 asm-generic/cmpxchg.h：其 arch_cmpxchg/arch_cmpxchg64 为
 * 无守卫重定义，会把本架构实现覆盖掉并触发 redefined 警告。
 */
#define arch_cmpxchg_local(ptr, o, n)		arch_cmpxchg((ptr), (o), (n))
#define arch_cmpxchg64_local(ptr, o, n)		arch_cmpxchg64((ptr), (o), (n))

static inline unsigned long __quantum_xchg(volatile void *ptr,
					   unsigned long x, int size)
{
	unsigned long prev;

	switch (size) {
	case 1:
		prev = *(volatile unsigned char *)ptr;
		*(volatile unsigned char *)ptr = (unsigned char)x;
		break;
	case 2:
		prev = *(volatile unsigned short *)ptr;
		*(volatile unsigned short *)ptr = (unsigned short)x;
		break;
	case 4:
		prev = *(volatile unsigned int *)ptr;
		*(volatile unsigned int *)ptr = (unsigned int)x;
		break;
	case 8:
		prev = *(volatile unsigned long *)ptr;
		*(volatile unsigned long *)ptr = x;
		break;
	default:
		__builtin_trap();
	}
	return prev;
}

#define arch_xchg(ptr, x)						\
({									\
	__typeof__(*(ptr)) __ret;					\
	__ret = (__typeof__(*(ptr)))__quantum_xchg((ptr),		\
			(unsigned long)(x), sizeof(*(ptr)));		\
	__ret;								\
})

#endif /* __ASSEMBLY__ */

#endif /* _ASM_QUANTUM_CMPXCHG_H */
