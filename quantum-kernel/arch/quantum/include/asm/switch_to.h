/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * arch/quantum/include/asm/switch_to.h
 * 任务切换定义（宿主模拟架构：上下文切换由宿主进程承载）。
 */
#ifndef _ASM_QUANTUM_SWITCH_TO_H
#define _ASM_QUANTUM_SWITCH_TO_H

struct task_struct;
struct thread_struct;

extern struct task_struct *__switch_to(struct task_struct *prev,
				       struct task_struct *next,
				       struct task_struct *last);

#define switch_to(p, n, r) do {					\
		r = __switch_to((p), (n), (r));			\
	} while (0)

#endif /* _ASM_QUANTUM_SWITCH_TO_H */
