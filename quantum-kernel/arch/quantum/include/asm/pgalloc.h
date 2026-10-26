/* SPDX-License-Identifier: GPL-2.0 */
/*
 * arch/quantum/include/asm/pgalloc.h — 页表分配接口（模拟）。
 *
 * 模拟架构的页表实体由宿主进程承载：pgd/pmd 分配退化为普通页面分配，
 * pmd 折叠项仅记账指向的页表页。pte 级分配复用通用实现
 * （asm-generic/pgalloc.h）。
 */
#ifndef _ASM_QUANTUM_PGALLOC_H
#define _ASM_QUANTUM_PGALLOC_H

#include <linux/mm.h>
#include <asm/page.h>
#include <asm/pgtable.h>

#include <asm-generic/pgalloc.h>

/* pgd 级分配/释放直接复用 asm-generic 的 ptdesc 缓存路径
 * （pagetable_alloc + pagetable_pgd_ctor + ptdesc_dtor），
 * 与内核其余部分对 ptdesc 的记账假设一致；plain pgd_alloc 在 6.18 已不由
 * 通用头提供，这里显式包一层 __pgd_alloc 供 kernel/fork.c 调用。 */
static inline pgd_t *pgd_alloc(struct mm_struct *mm)
{
	return __pgd_alloc(mm, 0);
}

/* pmd 折叠：将 pmd 项指向页表页（pfn）或内核 pte 数组（虚拟地址）。
 * 模拟架构不真正解引用这些项做地址翻译，仅保持类型/调用契约。 */
static inline void pmd_populate(struct mm_struct *mm, pmd_t *pmd,
				pgtable_t pte)
{
	set_pmd(pmd, __pmd((unsigned long)page_to_pfn(pte) << PAGE_SHIFT));
}

static inline void pmd_populate_kernel(struct mm_struct *mm, pmd_t *pmd,
				       pte_t *pte)
{
	set_pmd(pmd, __pmd((unsigned long)__pa(pte)));
}

/* 释放 pte 页表页（供 asm-generic/tlb.h 的 __pte_free_tlb 折叠路径）。 */
#define __pte_free_tlb(tlb, pte, addr) \
	tlb_remove_ptdesc((tlb), page_ptdesc(pte))

#endif /* _ASM_QUANTUM_PGALLOC_H */
