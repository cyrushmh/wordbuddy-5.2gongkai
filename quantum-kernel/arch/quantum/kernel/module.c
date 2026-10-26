// SPDX-License-Identifier: GPL-2.0
/* arch/quantum/kernel/module.c — module support stub (host-emulated). */
#include <linux/module.h>
#include <asm/module.h>

int module_frob_arch_sections(Elf_Ehdr *hdr, Elf_Shdr *sechdrs,
			      char *secstrings, struct module *me)
{
	return 0;
}
