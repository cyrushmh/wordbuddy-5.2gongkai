// SPDX-License-Identifier: GPL-2.0
/*
 * arch/quantum/mm/tlb.c — TLB flush 空操作实现。
 *
 * 模拟架构没有真实 MMU/TLB：页表由宿主进程承载，地址翻译与缓存一致性
 * 由宿主负责。此处仅提供满足通用 MM 代码链接契约的空函数体。
 */

#include <linux/mm.h>
#include <asm/tlbflush.h>

void tlb_flush_all(void)
{
}

void flush_tlb_mm(struct mm_struct *mm)
{
}

void flush_tlb_page(struct vm_area_struct *vma, unsigned long addr)
{
}

void flush_tlb_range(struct vm_area_struct *vma,
		     unsigned long start, unsigned long end)
{
}

void flush_tlb_kernel_range(unsigned long start, unsigned long end)
{
}

void flush_tlb_one(unsigned long addr)
{
}
