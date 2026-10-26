/* SPDX-License-Identifier: GPL-2.0 */
/*
 * include/asm/setup.h — command line size for the emulated arch.
 */
#ifndef _ASM_QUANTUM_SETUP_H
#define _ASM_QUANTUM_SETUP_H

#define COMMAND_LINE_SIZE	2048

#ifdef __KERNEL__
/* 早期 QPU 就位（kernel/setup.c，start_kernel 之前的 arch 钩子）。 */
void early_qpu_setup(void);
#endif

#endif /* _ASM_QUANTUM_SETUP_H */
