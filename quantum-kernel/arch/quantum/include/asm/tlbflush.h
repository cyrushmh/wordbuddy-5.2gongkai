/* SPDX-License-Identifier: GPL-2.0 */
/*
 * arch/quantum/include/asm/tlbflush.h — TLB flush prototypes.
 *
 * 模拟架构（宿主进程承载页表，无真实 MMU/TLB）的刷新接口。函数体为
 * 空操作（见 arch/quantum/mm/tlb.c），仅满足通用内存管理代码的调用契约。
 * 真实语义由宿主承载，本架构不做任何硬件刷新。
 */
#ifndef _ASM_QUANTUM_TLBFLUSH_H
#define _ASM_QUANTUM_TLBFLUSH_H

#include <linux/mm.h>
#include <asm/processor.h>

extern void tlb_flush_all(void);
extern void flush_tlb_mm(struct mm_struct *mm);
extern void flush_tlb_page(struct vm_area_struct *vma, unsigned long addr);
extern void flush_tlb_range(struct vm_area_struct *vma,
			    unsigned long start, unsigned long end);
extern void flush_tlb_kernel_range(unsigned long start, unsigned long end);
extern void flush_tlb_one(unsigned long addr);

/* munmap 释放页表页时无需操作（宿主承载页表，无陈旧映射可被内核访问）。 */
#define flush_tlb_pgtables(mm, start, end)

#endif /* _ASM_QUANTUM_TLBFLUSH_H */
