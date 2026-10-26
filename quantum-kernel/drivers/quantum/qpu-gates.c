// SPDX-License-Identifier: GPL-2.0
/*
 * drivers/quantum/qpu-gates.c — gate semantics table.
 * 门集导出：置换矩阵 Π_k（数字转换门）+ 受控翻转（cx）+ 相位观测。
 */
#include <linux/module.h>
#include <linux/stringify.h>
#include <asm/quantum.h>
#include "qpu-gates.h"

/* 门集清单（与用户态量子基座 GATES 对齐的子集）。 */
static const char *const qpu_gates[] = {
	"x", "cx", "cz", "h", "measure", "enc", "dec", "reset", "barrier",
};

const char *qpu_gate_name(unsigned int idx)
{
	if (idx >= ARRAY_SIZE(qpu_gates))
		return NULL;
	return qpu_gates[idx];
}
EXPORT_SYMBOL_GPL(qpu_gate_name);

unsigned int qpu_gate_count(void)
{
	return ARRAY_SIZE(qpu_gates);
}
EXPORT_SYMBOL_GPL(qpu_gate_count);

MODULE_LICENSE("GPL");
