/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _ASM_QUANTUM_VDSO_PROCESSOR_H
#define _ASM_QUANTUM_VDSO_PROCESSOR_H

#ifndef __ASSEMBLY__

/* 模拟核：编译器屏障即「让出流水线」，无真实自旋优化空间。 */
static inline void cpu_relax(void)
{
	__asm__ __volatile__("" ::: "memory");
}

#endif /* __ASSEMBLY__ */

#endif /* _ASM_QUANTUM_VDSO_PROCESSOR_H */
