/* SPDX-License-Identifier: GPL-2.0 */
/*
 * include/asm/ptrace.h — emulated register file (kernel side).
 * 与 UAPI 侧 user_qregs 对齐：pt_regs 即用户可见寄存器组。
 */
#ifndef _ASM_QUANTUM_PTRACE_H
#define _ASM_QUANTUM_PTRACE_H

#include <uapi/asm/ptrace.h>

#define PTRACE_USER_REGS_SIZE	sizeof(struct user_qregs)

#ifndef __ASSEMBLY__

struct pt_regs {
	struct user_qregs u;
};

#define user_mode(regs)		(((regs)->u.flags) & 0x1)
#define instruction_pointer(regs) ((regs)->u.pc)
#define user_stack_pointer(regs)  ((regs)->u.gpr[15])
#define regs_return_value(regs)	  ((regs)->u.gpr[0])
#define instruction_pointer_set(regs, val) ((regs)->u.pc = (val))
#define current_user_stack_pointer() (0UL)

#define ELF_CORE_COPY_REGS(dest, regs)		do { } while (0);

#endif /* __ASSEMBLY__ */

#endif /* _ASM_QUANTUM_PTRACE_H */
