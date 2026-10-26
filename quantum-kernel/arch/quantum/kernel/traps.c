// SPDX-License-Identifier: GPL-2.0
/*
 * arch/quantum/kernel/traps.c
 *
 * 极简栈回溯（宿主模拟架构）。
 * 没有真实栈帧布局可回溯，show_stack 仅打印进程信息与提示——
 * 这是诚实的模拟语义，满足 dump_stack() 的链接契约。
 */
#include <linux/sched.h>
#include <linux/sched/debug.h>
#include <linux/printk.h>
#include <linux/ptrace.h>

void show_stack(struct task_struct *task, unsigned long *sp,
		const char *loglvl)
{
	if (!task)
		task = current;
	printk("%s%s: emulated quantum stack (no real frame unwind)\n",
	       loglvl, task ? task->comm : "<null>");
	dump_stack_print_info(loglvl);
}

void show_regs(struct pt_regs *regs)
{
	/* 模拟架构：无真实寄存器上下文可转储。 */
	show_regs_print_info(KERN_DEFAULT);
	pr_info("quantum: emulated pt_regs dump skipped (host-emulated arch)\n");
}
