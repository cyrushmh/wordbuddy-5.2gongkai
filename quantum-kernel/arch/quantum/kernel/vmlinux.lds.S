/* SPDX-License-Identifier: GPL-2.0 */
#include <asm-generic/vmlinux.lds.h>
#include <asm/page.h>
#include <asm/thread_info.h>

/* 极简链接布局（宿主模拟；真实内存布局由宿主进程承载）。
 * OUTPUT_ARCH 的机器名用 ld 原生 x86-64 记法（宿主工具链）。 */
OUTPUT_FORMAT("elf64-x86-64")
OUTPUT_ARCH(i386:x86-64)
ENTRY(quantum_start)
SECTIONS
{
	. = PAGE_OFFSET;
	__init_begin = .;
	_stext = .;
	_text = .;
	INIT_TEXT_SECTION(PAGE_SIZE)
	_sinittext = .;
	.text : {
		*(.text*)
		SCHED_TEXT
	}
	__cpuidle_text_start = .;
	.cpuidle.text : { *(.cpuidle.text) }
	__cpuidle_text_end = .;
	_etext = .;
	RO_DATA(PAGE_SIZE)
	INIT_DATA_SECTION(PAGE_SIZE)
	EXCEPTION_TABLE(8)
	_sdata = .;
	RW_DATA(PAGE_SIZE, 0, 0)
	_edata = .;
	/* 64 位架构：jiffies 取 jiffies_64 的低 32 位（同地址别名）。 */
	jiffies = jiffies_64;
	__bss_start = .;
	_bss = .;
	.bss : { *(.bss*) }
	_ebss = .;
	__bss_stop = .;
	__init_end = .;
	_end = .;
	DISCARDS
}
