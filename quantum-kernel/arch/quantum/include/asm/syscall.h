/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * arch/quantum/include/asm/syscall.h
 *
 * 系统调用寄存器访问面（宿主模拟架构）。
 * ptrace 的 syscall 注入/观测路径需要完整的 syscall_* 钩子。模拟架构下
 * 寄存器上下文是占位结构，这些钩子以最小语义（空操作/占位值）满足链接，
 * 诚实声明：不暴露真实寄存器面。
 *
 * 架构审计类别沿用宿主 x86-64（OUTPUT_ARCH 为 x86-64）。
 */
#ifndef _ASM_QUANTUM_SYSCALL_H
#define _ASM_QUANTUM_SYSCALL_H

#include <linux/sched.h>
#include <linux/audit.h>
#include <linux/string.h>
#include <asm/ptrace.h>

/* ptrace 的 entry.args 固定 6 槽（struct ptrace_syscall_info 口径）。 */
#define SYSCALL_MAX_ARGS	6

static inline int syscall_get_nr(struct task_struct *task,
				 struct pt_regs *regs)
{
	return -ENOSYS;
}

static inline void syscall_set_nr(struct task_struct *task,
				  struct pt_regs *regs, int nr)
{
}

static inline void syscall_rollback(struct task_struct *task,
				    struct pt_regs *regs)
{
}

static inline long syscall_get_error(struct task_struct *task,
				     struct pt_regs *regs)
{
	return -ENOSYS;
}

static inline long syscall_get_return_value(struct task_struct *task,
					    struct pt_regs *regs)
{
	return -ENOSYS;
}

static inline void syscall_set_return_value(struct task_struct *task,
					    struct pt_regs *regs,
					    int error, long val)
{
}

static inline void syscall_get_arguments(struct task_struct *task,
					 struct pt_regs *regs,
					 unsigned long *args)
{
	/* 模拟架构：无真实参数槽可读，按 6 槽口径清零填充（诚实占位）。 */
	memset(args, 0, SYSCALL_MAX_ARGS * sizeof(unsigned long));
}

static inline void syscall_set_arguments(struct task_struct *task,
					 struct pt_regs *regs,
					 unsigned long *args)
{
}

static inline int syscall_get_arch(struct task_struct *task)
{
	return AUDIT_ARCH_X86_64;
}

#endif /* _ASM_QUANTUM_SYSCALL_H */
