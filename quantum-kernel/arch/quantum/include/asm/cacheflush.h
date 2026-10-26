/* SPDX-License-Identifier: GPL-2.0 */
/*
 * arch/quantum/include/asm/cacheflush.h — 缓存与 MMU 缓存更新接口。
 *
 * 模拟架构（宿主进程承载页表与缓存一致性）无真实 cache/TLB 维护面：
 * 通用 cache 刷新接口全部采用 asm-generic 空操作兜底；本文件只提供
 * 通用头未覆盖的 MMU 缓存钩子，满足 linux/mm 与 fs/binfmt 的调用契约。
 */
#ifndef _ASM_QUANTUM_CACHEFLUSH_H
#define _ASM_QUANTUM_CACHEFLUSH_H

#include <linux/mm.h>
#include <asm-generic/cacheflush.h>

/*
 * update_mmu_cache_range()：PTE 安装后的“缓存/TLB 同步”回调。
 * 宿主承载页表，无硬件 TLB 陈旧项，记账为空。
 */
static inline void update_mmu_cache_range(struct vm_fault *vmf,
		struct vm_area_struct *vma, unsigned long address,
		pte_t *ptep, unsigned int nr)
{
	/* 模拟架构：页表由宿主承载，无陈旧 TLB 需刷新。 */
}

#define update_mmu_cache(vma, addr, ptep) \
	update_mmu_cache_range(NULL, vma, addr, ptep, 1)

/* 单一 PTE 更新（通用 tlb.h 调用）。 */
#define update_mmu_tlb(vma, addr, ptep) \
	update_mmu_cache(vma, addr, ptep)

#endif /* _ASM_QUANTUM_CACHEFLUSH_H */
