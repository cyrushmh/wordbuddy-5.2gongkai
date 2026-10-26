/* SPDX-License-Identifier: GPL-2.0 */
/*
 * include/asm/processor.h — minimal CPU description for the emulated arch.
 */
#ifndef _ASM_QUANTUM_PROCESSOR_H
#define _ASM_QUANTUM_PROCESSOR_H

#ifdef __KERNEL__

#include <linux/threads.h>
#include <asm/quantum.h>
#include <asm/pgtable.h>	/* pgtable_t/pgprot_t 早于 mm_types */
#include <asm/vdso/processor.h>	/* cpu_relax */

/* 模拟核的基本 CPU 面：单核、无浮点/SIMD 特征面。 */
struct cpuinfo_quantum {
	unsigned int	qubits;
	unsigned int	link_slots;
	const char	*model;
};

extern struct cpuinfo_quantum cpu_data[NR_CPUS];

/* 无浮点状态面。 */
struct thread_struct { };

#define INIT_THREAD { }

/* 前向声明：start_thread/task_pt_regs 的签名在 struct pt_regs 完整定义
 * （asm/ptrace.h）之前就要可用。 */
struct pt_regs;

unsigned long thread_saved_pc(struct task_struct *tsk);
unsigned long __get_wchan(struct task_struct *p);

/* 模拟架构：无真实寄存器上下文可暴露（宿主承载执行）。 */
#define task_pt_regs(tsk)	((struct pt_regs *)NULL)

/* 模拟架构：启动新用户态上下文无需设置真实寄存器（宿主承载执行）。
 * 空实现满足 include/linux/elf.h 与 binfmt 的调用契约。 */
static inline void start_thread(struct pt_regs *regs, unsigned long new_ip,
				unsigned long new_sp)
{
	(void)regs; (void)new_ip; (void)new_sp;
}

/* 用户地址空间布局（模拟）：给 QPU 模拟面预留独立窗口。 */
#define TASK_SIZE		(PAGE_OFFSET)
#define TASK_UNMAPPED_BASE	(PAGE_OFFSET / 3)

/* proc 面的栈指针口径（模拟：无真实内核栈，返回 0 记账）。 */
#define KSTK_EIP(tsk)		(0UL)
#define KSTK_ESP(tsk)		(0UL)

#endif /* __KERNEL__ */

#endif /* _ASM_QUANTUM_PROCESSOR_H */
