/* SPDX-License-Identifier: GPL-2.0 */
/*
 * include/asm/mmu_context.h — emulated MMU context.
 * 单核模拟：地址空间切换即计数递增（无真实 TLB）。
 */
#ifndef _ASM_QUANTUM_MMU_CONTEXT_H
#define _ASM_QUANTUM_MMU_CONTEXT_H

#include <linux/mm_types.h>
#include <linux/smp.h>
#include <asm/pgtable.h>

/* 通用 mmap 生命周期钩子：arch_dup_mmap / arch_exit_mmap /
 * arch_unmap / arch_bprm_mm_init / arch_vma_access_permitted。
 * 模拟架构均取通用空实现。 */
#include <asm-generic/mm_hooks.h>

/* 模拟架构：根页目录占位（线性映射由宿主承载）。 */
extern pgd_t swapper_pg_dir[];

static inline void switch_mm(struct mm_struct *prev, struct mm_struct *next,
			     struct task_struct *tsk)
{
	/* 模拟架构：无 TLB，切换是记账操作。 */
	(void)prev; (void)next; (void)tsk;
}

#define activate_mm(prev, next)	switch_mm(prev, next, NULL)
#define deactivate_mm(tsk, mm)	do { } while (0)
#define enter_lazy_tlb(mm, tsk)	do { } while (0)
#define init_new_context(tsk, mm) (0)
#define destroy_context(mm)	do { } while (0)

#endif /* _ASM_QUANTUM_MMU_CONTEXT_H */
