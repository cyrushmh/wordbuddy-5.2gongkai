// SPDX-License-Identifier: GPL-2.0
/*
 * arch/quantum/kernel/setup.c — quantum architecture platform setup.
 *
 * 量子架构平台初始化：QPU 为宿主模拟设备，无真实 MMU/中断控制器；
 * 页粒度 4KiB，链路缓冲 CONFIG_QUANTUM_LINK_SLOTS 槽。
 */
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/cpu.h>
#include <linux/mm.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/delay.h>
#include <asm/setup.h>
#include <asm/quantum.h>
#include <asm/sections.h>

static char __initdata cmd_line[COMMAND_LINE_SIZE];

void __init early_qpu_setup(void)
{
	/* QPU 模拟核就位：寄存器宽度与链路深度来自 Kconfig。 */
	pr_info("quantum: QPU emulated core, %d qubits, link %d slots\n",
		CONFIG_QUANTUM_QUBITS, CONFIG_QUANTUM_LINK_SLOTS);
}

void __init setup_arch(char **cmdline_p)
{
	early_qpu_setup();
	*cmdline_p = cmd_line;
	/* 单核模拟：boot cpu 即全部（用 CPU 热插拔 API，不直接赋 mask）。 */
	set_cpu_possible(0, true);
	set_cpu_online(0, true);
	set_cpu_present(0, true);
	set_cpu_active(0, true);
}

void __init calibrate_delay(void)
{
	/* 宿主模拟：无真实忙等标定可做。loops_per_jiffy 固定为 1，
	 * 所有 udelay 均走 __const_udelay（空实现，时基由宿主提供）。 */
	loops_per_jiffy = 1;
}

void arch_cpu_finalize_init(void)
{
	/* 模拟架构：无架构私有的 CPU 收尾步骤（如 FPU/特性开关）。 */
}

static int __init quantum_arch_init(void)
{
	pr_info("quantum: architecture initialized (page %lu KiB)\n",
		PAGE_SIZE >> 10);
	return 0;
}
arch_initcall(quantum_arch_init);

static int qpu_info_show(struct seq_file *m, void *v)
{
	seq_printf(m, "arch\t\t: quantum (host-emulated)\n");
	seq_printf(m, "qubits\t\t: %d\n", CONFIG_QUANTUM_QUBITS);
	seq_printf(m, "link_slots\t: %d (ceil(2*pi))\n", CONFIG_QUANTUM_LINK_SLOTS);
	seq_printf(m, "page_size\t: %lu\n", PAGE_SIZE);
	seq_printf(m, "gates\t\t: permutation Pi_k (X-composite), h, cx, cz, measure\n");
	return 0;
}

static int __init qpu_info_init(void)
{
	proc_create_single("qpuinfo", 0444, NULL, qpu_info_show);
	return 0;
}
fs_initcall(qpu_info_init);
/* 模拟架构页操作：无 cache 维护，memset/memcpy 语义。 */
void clear_page(void *to)
{
	memset(to, 0, PAGE_SIZE);
}
EXPORT_SYMBOL(clear_page);

void copy_page(void *to, void *from)
{
	memcpy(to, from, PAGE_SIZE);
}
EXPORT_SYMBOL(copy_page);

unsigned long __get_wchan(struct task_struct *p)
{
	/* 模拟架构：无真实栈回溯，返回 0（诚实口径）。 */
	return 0;
}

/* 根页目录占位（模拟：线性映射由宿主承载）。 */
pgd_t swapper_pg_dir[PTRS_PER_PGD] __page_aligned_bss;

/* ── /proc/cpuinfo 支持（模拟架构：单核 QPU 宿主模拟核）────────────── */

static void *c_start(struct seq_file *m, loff_t *pos)
{
#ifdef CONFIG_SMP
	if (*pos >= num_online_cpus())
		return NULL;
#else
	if (*pos > 0)
		return NULL;
#endif
	return (void *)((unsigned long)*pos + 1);
}

static void *c_next(struct seq_file *m, void *v, loff_t *pos)
{
	++*pos;
	return c_start(m, pos);
}

static void c_stop(struct seq_file *m, void *v)
{
}

static int show_cpuinfo(struct seq_file *m, void *v)
{
	int cpu = (unsigned long)v - 1;

#ifdef CONFIG_SMP
	if (!cpu_online(cpu))
		return 0;
#endif
	seq_printf(m, "processor\t: %d\n", cpu);
	seq_printf(m, "model name\t: Quantum host-emulated QPU core\n");
	seq_printf(m, "qubits\t\t: %d\n", CONFIG_QUANTUM_QUBITS);
	seq_printf(m, "link_slots\t: %d\n", CONFIG_QUANTUM_LINK_SLOTS);
	seq_printf(m, "BogoMIPS\t: %lu.%02lu\n",
		   (loops_per_jiffy * HZ) / 500000,
		   ((loops_per_jiffy * HZ) / 5000) % 100);
	seq_printf(m, "\n");
	return 0;
}

const struct seq_operations cpuinfo_op = {
	.start	= &c_start,
	.next	= &c_next,
	.stop	= &c_stop,
	.show	= &show_cpuinfo,
};

