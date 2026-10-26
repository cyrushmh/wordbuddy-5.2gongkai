/* SPDX-License-Identifier: GPL-2.0 */
/*
 * drivers/quantum/qpu-gates.h — internal gate table interface.
 * 门集清单的模块内声明（qpu-gates.c 实现，EXPORT_SYMBOL_GPL 导出）。
 */
#ifndef _QPU_GATES_H
#define _QPU_GATES_H

const char *qpu_gate_name(unsigned int idx);
unsigned int qpu_gate_count(void);

#endif /* _QPU_GATES_H */
