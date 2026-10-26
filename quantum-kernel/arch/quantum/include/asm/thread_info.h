/* SPDX-License-Identifier: GPL-2.0 */
/*
 * include/asm/thread_info.h — minimal thread info for the emulated arch.
 */
#ifndef _ASM_QUANTUM_THREAD_INFO_H
#define _ASM_QUANTUM_THREAD_INFO_H

#ifdef __KERNEL__

#ifndef __ASSEMBLY__
#include <asm/page.h>
#include <asm/processor.h>
#endif

#define THREAD_SHIFT		13
#define THREAD_SIZE		(1 << THREAD_SHIFT)	/* int：lds 里 ld 不认 UL 后缀 */
#define THREAD_SIZE_ORDER	(THREAD_SHIFT - PAGE_SHIFT)

#ifndef __ASSEMBLY__

struct thread_info {
	struct task_struct	*task;		/* main task structure */
	unsigned long		flags;		/* low level flags */
	unsigned long		syscall_work;	/* syscall workload */
	int			preempt_count;	/* 0 => preemptable */
	__u32			cpu;		/* current CPU (always 0) */
	unsigned long		syscall;	/* syscall number */
};

#define INIT_THREAD_INFO(tsk)						\
{									\
	.task		= &tsk,						\
	.flags		= 0,						\
	.preempt_count	= INIT_PREEMPT_COUNT,				\
	.cpu		= 0,						\
}

/* TIF 位定义（模拟架构：与通用语义对齐的最小集）。 */
#define TIF_NOTIFY_SIGNAL	0	/* signal notifications exist */
#define TIF_NOTIFY_RESUME	1	/* callback before returning to user */
#define TIF_SIGPENDING		2	/* signal pending */
#define TIF_NEED_RESCHED	3	/* rescheduling necessary */
#define TIF_NEED_RESCHED_LAZY	4	/* lazy rescheduling */
#define TIF_RESTORE_SIGMASK	5	/* restore signal mask in do_signal */
#define TIF_SECCOMP		6	/* seccomp filtering active */
#define TIF_SYSCALL_TRACE	7	/* syscall trace active */
#define TIF_SYSCALL_AUDIT	8	/* syscall auditing active */
#define TIF_SYSCALL_TRACEPOINT	9	/* syscall tracepoint instrumentation */
#define TIF_NOHZ		12	/* adaptive tickless */
#define TIF_MEMDIE		13	/* is terminating due to OOM killer */
#define TIF_POLLING_NRFLAG	16	/* idle is polling for TIF_NEED_RESCHED */

#define _TIF_NOTIFY_SIGNAL	(1 << TIF_NOTIFY_SIGNAL)
#define _TIF_NOTIFY_RESUME	(1 << TIF_NOTIFY_RESUME)
#define _TIF_SECCOMP		(1 << TIF_SECCOMP)
#define _TIF_SYSCALL_TRACE	(1 << TIF_SYSCALL_TRACE)
#define _TIF_SYSCALL_AUDIT	(1 << TIF_SYSCALL_AUDIT)
#define _TIF_SYSCALL_TRACEPOINT (1 << TIF_SYSCALL_TRACEPOINT)
#define _TIF_NOHZ		(1 << TIF_NOHZ)
#define _TIF_SIGPENDING		(1 << TIF_SIGPENDING)
#define _TIF_NEED_RESCHED	(1 << TIF_NEED_RESCHED)
#define _TIF_NEED_RESCHED_LAZY	(1 << TIF_NEED_RESCHED_LAZY)
#define _TIF_POLLING_NRFLAG	(1 << TIF_POLLING_NRFLAG)

#define _TIF_WORK_MASK		(_TIF_NEED_RESCHED | _TIF_SIGPENDING | \
				 _TIF_NOTIFY_RESUME)

/*
 * current_thread_info()：模拟架构没有真实的内核栈底对齐——
 * 单核模拟以静态 thread_info 承载（诚实标注：不可 SMP）。
 */
static inline struct thread_info *current_thread_info(void)
{
	static struct thread_info _quantum_ti
		__attribute__((section(".data..quantum_ti")));
	return &_quantum_ti;
}

#endif /* __ASSEMBLY__ */

#endif /* __KERNEL__ */

#endif /* _ASM_QUANTUM_THREAD_INFO_H */
