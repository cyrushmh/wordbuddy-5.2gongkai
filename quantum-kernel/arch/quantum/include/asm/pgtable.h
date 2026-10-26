/* SPDX-License-Identifier: GPL-2.0 */
/*
 * arch/quantum/include/asm/pgtable.h — minimal page-table types.
 * 模拟架构无真实 MMU：类型面齐备（pgd/pmd/pud/pte/pgprot），实体页表由
 * 宿主进程承载。采用 nopmd/nopud/nop4d 折叠的两级布局（PGD → PTE），
 * shift 从 PGDIR_SHIFT 向下递推，避免循环定义。
 */
#ifndef _ASM_QUANTUM_PGTABLE_H
#define _ASM_QUANTUM_PGTABLE_H

#include <asm/page.h>

/* 架构专属类型：先定义 pgd/pte/pgprot（pud/pmd 由 generic 折叠提供）。
 * pgd_t 必须在 nop4d include 之前定义——generic 用它构造 p4d_t。 */
typedef struct { unsigned long pgd; } pgd_t;
typedef struct { unsigned long pte; } pte_t;
typedef struct { unsigned long prot; } pgprot_t;
struct page;
typedef struct page *pgtable_t;	/* 页表页由 struct page 承载（模拟） */

#define pgd_val(x)	((x).pgd)
#define pte_val(x)	((x).pte)
#define pgprot_val(x)	((x).prot)

#define __pgd(x)	((pgd_t) { (x) })
#define __pte(x)	((pte_t) { (x) })
#define __pgprot(x)	((pgprot_t) { (x) })

/* 折叠宏：引入 p4d/pud/pmd 类型与访问宏（nop4d → nopud → nopmd）。
 * 它们从 pgd_t 构造上层类型，并把 shift 链推到 PGDIR_SHIFT。 */
#include <asm-generic/pgtable-nop4d.h>
#include <asm-generic/pgtable-nopud.h>
#include <asm-generic/pgtable-nopmd.h>

/* ── 折叠级访问器（pmd/pud/p4d 均折叠进 pgd）────────────────────────
 * 模拟架构无真实多级页表，所有上层项最终落在 pgd_val；page_vaddr
 * 取该值即「页表虚拟地址」，保护位/存在位按折叠语义恒为 1/0。 */
#define pmd_page_vaddr(pmd)	((unsigned long)(pmd_val(pmd)))
#define pud_page_vaddr(pud)	((unsigned long)(pud_val(pud)))
#define p4d_page_vaddr(p4d)	((unsigned long)(p4d_val(p4d)))

#define pmd_none(pmd)		(0)
#define pmd_present(pmd)	(1)
#define pmd_bad(pmd)		(0)
#define pmd_clear(pmdp)		do { } while (0)
#define set_pmd(pmdp, pmd)	(*(pmdp) = (pmd))
/* pmd_page 由本架构定义；pud_page/p4d_page/pgd_page 由 generic 折叠头
 * （nopmd/nopud/nop4d）逐级下推到 pmd_page，不重复定义。 */
#define pmd_page(pmd)		virt_to_page((void *)pmd_page_vaddr(pmd))
#define pmd_pfn(pmd)		((unsigned long)(pmd_val(pmd)) >> PAGE_SHIFT)

#define PFN_PTE_SHIFT		PAGE_SHIFT

/* ── 折叠的两级页表（PGD → PTE）────────────────────────────────────
 * 页粒度固定 4KiB（与存储域 ext4 4K 对齐口径一致）。 */
#define PTE_BITS	9		/* log2(PTRS_PER_PTE) = 512 项 */
#define PTRS_PER_PTE	(1 << PTE_BITS)
#define PTRS_PER_PGD	(1 << (PAGE_SHIFT - 3))	/* 512 */

#define PGDIR_SHIFT	(PAGE_SHIFT + PTE_BITS)	/* 21 */
/* PUD_SHIFT / PMD_SHIFT / P4D_SHIFT 由 generic 折叠头从 PGDIR_SHIFT 推导 */

/* 地址区间面（供 linux/pgtable.h 与 mm/ 子系统的区间掩码计算）。 */
#define PGDIR_SIZE	(1UL << PGDIR_SHIFT)
#define PGDIR_MASK	(~(PGDIR_SIZE - 1))

#ifndef __ASSEMBLY__
#define pgd_index(addr)		(((addr) >> PGDIR_SHIFT) & (PTRS_PER_PGD - 1))

/* 架构内存初始化入口（openrisc 同型口径：由 arch 的 pgtable.h 声明）。 */
extern void paging_init(void);

#define pfn_pte(pfn, prot) \
	__pte(((unsigned long)(pfn) << PAGE_SHIFT) | pgprot_val(prot))
#define pte_pfn(pte)		((unsigned long)(pte_val(pte) >> PAGE_SHIFT))
#define pfn_pmd(pfn, prot) \
	__pmd(((unsigned long)(pfn) << PAGE_SHIFT) | pgprot_val(prot))

/* ── 页表项位访问面（模拟：位仅记账，无真实 TLB 行为）──────────── */
#define _PAGE_PRESENT	(1UL << 0)
#define _PAGE_WRITE	(1UL << 1)
#define _PAGE_DIRTY	(1UL << 2)
#define _PAGE_YOUNG	(1UL << 3)
#define _PAGE_SPECIAL	(1UL << 4)
#define _PAGE_USER	(1UL << 5)
#define _PAGE_EXEC	(1UL << 6)

#define pte_present(pte)	(!!(pte_val(pte) & _PAGE_PRESENT))
#define pte_none(pte)		(!pte_val(pte))
#define pte_write(pte)		(!!(pte_val(pte) & _PAGE_WRITE))
#define pte_dirty(pte)		(!!(pte_val(pte) & _PAGE_DIRTY))
#define pte_young(pte)		(!!(pte_val(pte) & _PAGE_YOUNG))
#define pte_user(pte)		(!!(pte_val(pte) & _PAGE_USER))
#define pte_accessible(mm, pte)	pte_present(pte)

/* 以下由通用头（linux/pgtable.h、linux/mm.h）以静态内联提供，
 * 它们复用本文件的 _PAGE_* 位与 pte_val/__pte：
 *   pte_young / pte_same / pte_mkwrite（pgtable.h）
 *   pte_special / pte_mkspecial（mm.h）
 * 本架构只需提供 _PAGE_* 位面与 pte_mkyoung/mkold/mkdirty/wrprotect/mkclean。 */
#define pte_wrprotect(pte)	__pte(pte_val(pte) & ~_PAGE_WRITE)
#define pte_mkclean(pte)	__pte(pte_val(pte) & ~_PAGE_DIRTY)
#define pte_mkold(pte)		__pte(pte_val(pte) & ~_PAGE_YOUNG)
#define pte_mkyoung(pte)	__pte(pte_val(pte) | _PAGE_YOUNG)
#define pte_mkdirty(pte)	__pte(pte_val(pte) | _PAGE_DIRTY)
/* pte_mkwrite 由通用头（linux/pgtable.h）提供，它调用 arch 专属的
 * pte_mkwrite_novma；两者都置 _PAGE_WRITE 位。 */
#define pte_mkwrite_novma(pte)	__pte(pte_val(pte) | _PAGE_WRITE)

/* ── 修改类/反向查询（供 mm/mprotect.c、mm/memory.c 等）─────────────
 * _PAGE_CHG_MASK：pte_modify 保留的权限位面；其余位由新保护值覆盖。 */
#define _PAGE_CHG_MASK	(_PAGE_PRESENT | _PAGE_WRITE | _PAGE_DIRTY | \
			 _PAGE_YOUNG | _PAGE_SPECIAL | _PAGE_USER | _PAGE_EXEC)

#define pte_modify(pte, prot) \
	__pte((pte_val(pte) & _PAGE_CHG_MASK) | pgprot_val(prot))

/* pte_page：反向查询 PTE 指向的 struct page（供 gup/vmalloc 等）。 */
#define pte_page(pte)		pfn_to_page(pte_pfn(pte))

#define set_pte(ptep, pte)	(*(ptep) = (pte))
#define pte_clear(mm, addr, ptep)	set_pte(ptep, __pte(0))

/* pgd_ERROR：通用 pgtable-generic.c 在 pgd 校验失败时调用，且折叠路径
 * （asm-generic/pgtable-nop4d.h 的 p4d_ERROR）要求其为「表达式」形式。
 * 模拟架构仅占位（无真实页表不一致可报），保持记账空表达式。 */
#define pgd_ERROR(e)			((void)(e))

/* 内核根页目录（模拟：线性映射由宿主承载，占位记账）。 */
extern pgd_t swapper_pg_dir[PTRS_PER_PGD];

/* ── 交换项（swap entry）编解码 ─────────────────────────────────────
 * 模拟架构无真实交换设备：交换 PTE 直接复用 pte 值往返，类型/偏移仅占位。
 * 交换 PTE 的 _PAGE_PRESENT 必须为 0（通用层保证），其余位重新解释。
 * 专有位 _PAGE_SWP_EXCLUSIVE 置于 _PAGE_* 面之上的位 7，避免冲突。 */
#define _PAGE_SWP_EXCLUSIVE	(1UL << 7)

#define __pte_to_swp_entry(pte)	((swp_entry_t) { pte_val(pte) })
#define __swp_entry_to_pte(x)	((pte_t) { (x).val })

#define __swp_type(swp_pte)	(((swp_pte).val >> 1) & 0x3f)
#define __swp_offset(swp_pte)	(((swp_pte).val >> 8) & ((1UL << 24) - 1))
#define __swp_entry(type, offset) \
	((swp_entry_t) { \
		(((type) & 0x3f) << 1) | (((offset) & ((1UL << 24) - 1)) << 8) })

static inline bool pte_swp_exclusive(pte_t pte)
{
	return pte_val(pte) & _PAGE_SWP_EXCLUSIVE;
}

static inline pte_t pte_swp_mkexclusive(pte_t pte)
{
	pte_val(pte) |= _PAGE_SWP_EXCLUSIVE;
	return pte;
}

static inline pte_t pte_swp_clear_exclusive(pte_t pte)
{
	pte_val(pte) &= ~_PAGE_SWP_EXCLUSIVE;
	return pte;
}
#endif

/* 零页（模拟）：共享一个静态零页占位。 */
extern unsigned long empty_zero_page[PAGE_SIZE / sizeof(unsigned long)];
#define ZERO_PAGE(vaddr)	(virt_to_page(empty_zero_page))

/* 页保护面（模拟：无真实 TLB，保护位仅记账）。 */
#define PAGE_NONE	__pgprot(0)
#define PAGE_SHARED	__pgprot(0x1)
#define PAGE_COPY	__pgprot(0x2)
#define PAGE_READONLY	__pgprot(0x3)
#define PAGE_KERNEL	__pgprot(0x4)
#define PAGE_KERNEL_RO	__pgprot(0x5)
#define PAGE_KERNEL_EXEC	__pgprot(0x6)

#endif /* _ASM_QUANTUM_PGTABLE_H */
