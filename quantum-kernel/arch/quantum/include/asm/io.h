/* SPDX-License-Identifier: GPL-2.0 */
/*
 * include/asm/io.h — emulated I/O (no real MMIO; NO_DMA).
 * 模拟架构无真实总线：ioremap 退化为线性地址透传。
 */
#ifndef _ASM_QUANTUM_IO_H
#define _ASM_QUANTUM_IO_H

#include <asm/pgtable.h>

/* 模拟架构无真实 MMIO：ioremap 退化为地址透传，iounmap 为记账空操作，
 * 其余 ioremap_* 变体由 asm-generic/io.h 回退到 ioremap。 */
#ifndef ioremap
#define ioremap(offset, size)	((void __iomem *)(unsigned long)(offset))
#endif
#ifndef iounmap
#define iounmap(addr)		do { } while (0)
#endif

#include <asm-generic/io.h>

#endif /* _ASM_QUANTUM_IO_H */
