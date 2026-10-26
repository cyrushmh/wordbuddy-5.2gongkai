// SPDX-License-Identifier: GPL-2.0
/*
 * arch/quantum/kernel/asm-offsets.c — generate asm constants.
 * 模拟架构：只导出最小偏移集（task_struct 的常用字段与页常数）。
 */
#define COMPILE_OFFSETS
#include <linux/kbuild.h>
#include <asm/pgtable.h>
#include <asm/thread_info.h>
#include <asm/quantum.h>
#include <linux/sched.h>
#include <linux/mm_types.h>
#include <asm/quantum.h>

int main(void)
{
	DEFINE(QUANTUM_QUBITS_V, QUANTUM_QUBITS);
	DEFINE(QUANTUM_LINK_SLOTS_V, QUANTUM_LINK_SLOTS);
	DEFINE(TI_TASK, offsetof(struct thread_info, task));
	BLANK();
	return 0;
}
