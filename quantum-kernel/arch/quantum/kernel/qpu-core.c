// SPDX-License-Identifier: GPL-2.0
/*
 * arch/quantum/kernel/qpu-core.c — QPU link-buffer statistics core.
 * 链路统计的架构侧核心：每步交换入链，满则覆盖并计数（对齐 PiLink 语义）。
 */
#include <linux/export.h>
#include <linux/kernel.h>
#include <asm/quantum.h>

unsigned long quantum_link_total_writes;
unsigned long quantum_link_overwrites;
EXPORT_SYMBOL_GPL(quantum_link_total_writes);
EXPORT_SYMBOL_GPL(quantum_link_overwrites);

void quantum_link_push(void)
{
	/* 槽计数由调用方维护；这里只累计全局审计量。 */
	quantum_link_total_writes++;
}
EXPORT_SYMBOL_GPL(quantum_link_push);

void quantum_link_overflow(void)
{
	quantum_link_total_writes++;
	quantum_link_overwrites++;
}
EXPORT_SYMBOL_GPL(quantum_link_overflow);
