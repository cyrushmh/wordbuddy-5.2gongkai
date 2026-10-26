/* SPDX-License-Identifier: GPL-2.0 */
/*
 * include/asm/elf.h — ELF platform constants for the emulated arch.
 * 模拟架构以 EM_NONE 呈现（不冒充任何真实指令集）。
 */
#ifndef _ASM_QUANTUM_ELF_H
#define _ASM_QUANTUM_ELF_H

#include <asm/ptrace.h>
#include <asm/user.h>

#define ELF_ARCH	0		/* EM_NONE */
#define ELF_CLASS	ELFCLASS64
#define ELF_DATA	ELFDATA2LSB

#define ELF_NGREG	(sizeof(struct user_qregs) / sizeof(elf_greg_t))
typedef unsigned long elf_greg_t;
typedef elf_greg_t elf_gregset_t[ELF_NGREG];
typedef elf_greg_t elf_fpregset_t;

#define ELF_NFPREG	0

#define ELF_PLAT_INIT(_r, load_addr)	do { (_r)->u.gpr[0] = 0; } while (0)

#define elf_check_arch(x)	(((x)->e_machine) == ELF_ARCH)

/*
 * 模拟架构的二进制面：内核自身是宿主 ELF；用户态二进制须为量子
 * 模拟器格式（后续由 binfmt 接入），此处按 64 位小端声明。
 */
#define elf_check_arch_64(x)	1

#define ELF_EXEC_PAGESIZE	PAGE_SIZE

#define ELF_EXEC_PAGESIZE	PAGE_SIZE

/* 用户地址空间布局（模拟）：STACK_TOP 取 TASK_SIZE 上限；
 * ET_DYN 基址落在用户空间下半部，避开 brk。 */
#define STACK_TOP		TASK_SIZE
#define ELF_ET_DYN_BASE		(TASK_SIZE / 3 * 2)

/* 模拟架构不暴露真实指令集能力面：HWCAP 为 0，PLATFORM 为空。 */
#define ELF_HWCAP		(0)
#define ELF_PLATFORM		(NULL)

/* mm/vma_exec.c 的 exec 栈上限：单区间布局取 STACK_TOP。 */
#define STACK_TOP_MAX		STACK_TOP

#endif /* _ASM_QUANTUM_ELF_H */
