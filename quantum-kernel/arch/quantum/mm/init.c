// SPDX-License-Identifier: GPL-2.0
/*
 * arch/quantum/mm/init.c — emulated architecture memory init.
 * 4KiB 页纪律：与存储域 ext4 4K 对齐口径一致。
 */
#include <linux/init.h>
#include <linux/memblock.h>
#include <linux/mm.h>
#include <asm/quantum.h>

/* 全局共享零页（模拟：单页零填充占位）。 */
unsigned long empty_zero_page[PAGE_SIZE / sizeof(unsigned long)]
	__page_aligned_bss;
EXPORT_SYMBOL(empty_zero_page);

void __init paging_init(void)
{
	/* 模拟架构：页表由宿主进程承载，这里只完成框架性初始化。 */
	unsigned long zones[MAX_NR_ZONES] = { 0 };
	zones[ZONE_NORMAL] = max_pfn;
	free_area_init(zones);
}

void __init mem_init(void)
{
	/* 高内存面全部走宿主；打印页纪律即可。 */
	pr_info("quantum: mm init, %lu KiB pages, %d link slots\n",
		PAGE_SIZE >> 10, QUANTUM_LINK_SLOTS);
}

void mark_rodata_ro(void)
{
	/* 模拟架构：无独立 rodata 保护硬件，空实现满足启动链接契约。 */
}

pgprot_t vm_get_page_prot(unsigned long vm_flags)
{
	/*
	 * VMA 属性 → _PAGE_* 位面映射。
	 * 模拟架构的页保护位由宿主持有，这里按 VMA 标志组合出
	 * 一致的位面记账值（present/user/young/read/write/dirty/exec）。
	 */
	unsigned long prot = 0;

	if (vm_flags & (VM_READ | VM_EXEC))
		prot |= _PAGE_PRESENT | _PAGE_USER | _PAGE_YOUNG;
	if (vm_flags & VM_WRITE)
		prot |= _PAGE_WRITE | _PAGE_DIRTY;
	if (vm_flags & VM_EXEC)
		prot |= _PAGE_EXEC;

	return __pgprot(prot);
}
EXPORT_SYMBOL(vm_get_page_prot);
