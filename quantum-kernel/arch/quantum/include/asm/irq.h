/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _ASM_QUANTUM_IRQ_H
#define _ASM_QUANTUM_IRQ_H

/* 模拟架构：无硬件中断控制器；irq 起始向量取 16（惯例保留区之上）。 */
#define NR_IRQS			16
#define ARCH_IRQ_INIT_FLAGS	0

int arch_show_interrupts(struct seq_file *p, int prec);

#endif /* _ASM_QUANTUM_IRQ_H */
