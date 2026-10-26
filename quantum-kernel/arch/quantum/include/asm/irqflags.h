/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * arch/quantum/include/asm/irqflags.h
 *
 * IRQ flags 接口（宿主模拟的单核量子架构）。
 *
 * 模拟语义：没有真实的中断硬件，中断使能状态由进程内静态变量
 * 表达；arch_local_* 系列只做状态保存/恢复，不做真实的 CPU 指令。
 * 这完全满足内核通用 IRQ 子系统的编译与链接契约。
 */
#ifndef _ASM_QUANTUM_IRQFLAGS_H
#define _ASM_QUANTUM_IRQFLAGS_H

#include <linux/types.h>

/* 宿主模拟：中断使能状态由单一进程内标志位承载。 */
extern unsigned long quantum_irq_flags;

static inline unsigned long arch_local_save_flags(void)
{
	return quantum_irq_flags;
}

static inline unsigned long arch_local_irq_save(void)
{
	unsigned long flags = quantum_irq_flags;

	quantum_irq_flags = 0;	/* 0 = 中断禁用 */
	return flags;
}

static inline void arch_local_irq_restore(unsigned long flags)
{
	quantum_irq_flags = flags;
}

static inline bool arch_irqs_disabled_flags(unsigned long flags)
{
	return !flags;
}

static inline bool arch_irqs_disabled(void)
{
	return !quantum_irq_flags;
}

static inline void arch_local_irq_enable(void)
{
	quantum_irq_flags = 1;	/* 1 = 中断使能 */
}

static inline void arch_local_irq_disable(void)
{
	quantum_irq_flags = 0;
}

#define ARCH_IRQ_DISABLED	0
#define ARCH_IRQ_ENABLED		1

#endif /* _ASM_QUANTUM_IRQFLAGS_H */
