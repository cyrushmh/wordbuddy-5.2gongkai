/* SPDX-License-Identifier: GPL-2.0 */
/*
 * include/asm/uaccess.h — emulated user access.
 * CONFIG_UACCESS_MEMCPY：模拟架构无真实用户/内核隔离（arch/um 同型），
 * raw_copy_* 用 asm-generic 的 memcpy 实现；TASK_SIZE 边界由 access_ok 检查。
 */
#ifndef _ASM_QUANTUM_UACCESS_H
#define _ASM_QUANTUM_UACCESS_H

#include <asm/processor.h>
#include <asm-generic/uaccess.h>

#endif /* _ASM_QUANTUM_UACCESS_H */
