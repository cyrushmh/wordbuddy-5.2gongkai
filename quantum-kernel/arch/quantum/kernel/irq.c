// SPDX-License-Identifier: GPL-2.0
/*
 * arch/quantum/kernel/irq.c — emulated interrupt reporting.
 * GENERIC_IRQ_SHOW 的架构侧回调：模拟核无真实中断控制器。
 */
#include <linux/init.h>
#include <linux/seq_file.h>
#include <asm/irq.h>
#include <asm/irqflags.h>

/* 宿主模拟：中断使能状态（见 asm/irqflags.h）。 */
unsigned long quantum_irq_flags = ARCH_IRQ_ENABLED;
EXPORT_SYMBOL(quantum_irq_flags);

/* 宿主模拟：中断由宿主进程承载，无中断控制器可初始化；
 * init_IRQ 保持空实现满足 start_kernel 链接契约。 */
void __init init_IRQ(void)
{
}

int arch_show_interrupts(struct seq_file *p, int prec)
{
	seq_printf(p, "%*s: emulated QPU: no hardware interrupt controller\n",
		   prec + 3, "QPU");
	return 0;
}
