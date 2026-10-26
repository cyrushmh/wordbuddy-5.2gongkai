// SPDX-License-Identifier: GPL-2.0
/*
 * arch/quantum/kernel/process.c — process/thread lifecycle stubs.
 * 宿主模拟架构：线程切换、上下文保存由宿主进程承载，
 * 内核侧只满足 exec/exit 路径的链接契约。
 */
#include <linux/sched.h>
#include <linux/sched/task.h>
#include <linux/sched/debug.h>
#include <linux/elfcore.h>
#include <linux/ptrace.h>
#include <linux/regset.h>
#include <linux/reboot.h>
#include <asm/ptrace.h>
#include <asm/switch_to.h>

void flush_thread(void)
{
	/* 模拟架构：无真实 FPU/调试寄存器状态需要丢弃。 */
}

int copy_thread(struct task_struct *p, const struct kernel_clone_args *args)
{
	/* 模拟架构：无 FPU/调试寄存器状态可复制，也无真实栈帧可清零——
	 * task_pt_regs 恒为 NULL，新任务的执行上下文由宿主进程承载。 */
	return 0;
}

void release_thread(struct task_struct *dead_task)
{
	/* 模拟架构：无架构私有资源需释放。 */
}

long arch_ptrace(struct task_struct *child, long request,
		 unsigned long addr, unsigned long data)
{
	/* 模拟架构：不暴露真实寄存器访问面。 */
	return -ENOSYS;
}

void ptrace_disable(struct task_struct *child)
{
	/* 模拟架构：无单步/断点硬件需禁用。 */
}

const struct user_regset_view *task_user_regset_view(struct task_struct *task)
{
	/* 模拟架构：无寄存器集可暴露，返回空视图。 */
	return NULL;
}

int elf_core_copy_task_fpregs(struct task_struct *t, elf_fpregset_t *fpu)
{
	/* 模拟架构：无 FPU 寄存器集，core dump 的浮点段为空段。 */
	return 0;
}

struct task_struct *__switch_to(struct task_struct *prev,
				struct task_struct *next,
				struct task_struct *last)
{
	/* 模拟架构：真实上下文切换由宿主进程承载，这里只返回上一任务。 */
	(void)prev;
	(void)next;
	return last;
}

void machine_restart(char *cmd)
{
	/* 模拟架构：无真实复位硬件。 */
}

void machine_halt(void)
{
	/* 模拟架构：无真实停机硬件。 */
}

void machine_power_off(void)
{
	/* 模拟架构：无真实断电硬件。 */
}
