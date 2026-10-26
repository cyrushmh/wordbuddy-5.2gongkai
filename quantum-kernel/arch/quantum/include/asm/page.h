/* SPDX-License-Identifier: GPL-2.0 */
/*
 * include/asm/page.h — 4KiB page discipline for the quantum architecture.
 * 页粒度固定 4KiB：与存储域 ext4 默认块大小/4K 对齐纪律一致。
 */
#ifndef _ASM_QUANTUM_PAGE_H
#define _ASM_QUANTUM_PAGE_H

#include <linux/const.h>

#define PAGE_SHIFT	12
#define PAGE_SIZE	(_AC(1, UL) << PAGE_SHIFT)
#define PAGE_MASK	(~(PAGE_SIZE - 1))

/* 宿主模拟：内核虚拟基址取一个宿主可承载的低位。 */
#define PAGE_OFFSET	_AC(0x40000000, UL)

#ifndef __ASSEMBLY__
#define __pa(x)		((unsigned long)(x))
#define __va(x)		((void *)(unsigned long)(x))
#define virt_to_page(kaddr) (mem_map + (((unsigned long)(kaddr) - PAGE_OFFSET) >> PAGE_SHIFT))
#define pfn_valid(pfn)	((pfn) < max_mapnr)
#define virt_addr_valid(kaddr)	pfn_valid(__pa(kaddr) >> PAGE_SHIFT)

#include <asm-generic/memory_model.h>
#include <asm-generic/getorder.h>

/* 页操作（模拟）：清/拷页即 memset/memcpy，无 cache 维护面。 */
struct page;
extern void clear_page(void *to);
extern void copy_page(void *to, void *from);
#define clear_user_page(pg, vaddr, addr)	clear_page(page_address(pg))
#define copy_user_page(to, from, vaddr, pg)	copy_page(to, from)

#endif /* __ASSEMBLY__ */

#endif /* _ASM_QUANTUM_PAGE_H */
