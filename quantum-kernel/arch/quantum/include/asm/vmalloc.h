/* SPDX-License-Identifier: GPL-2.0 */
/*
 * include/asm/vmalloc.h — vmalloc layout for the emulated arch.
 */
#ifndef _ASM_QUANTUM_VMALLOC_H
#define _ASM_QUANTUM_VMALLOC_H

#define VMALLOC_OFFSET	(8 * 1024 * 1024)
#define VMALLOC_START	((unsigned long)high_memory + VMALLOC_OFFSET)
#define VMALLOC_END	(PAGE_OFFSET + 0x40000000UL)

#endif /* _ASM_QUANTUM_VMALLOC_H */
