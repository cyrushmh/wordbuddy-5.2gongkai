/* SPDX-License-Identifier: GPL-2.0 */
/*
 * src/quantum_uapi.h — 量子架构用户态接口契约（与内核
 * include/uapi/linux/quantum.h 同步 vendored 副本）。
 *
 * 诚实声明：这是「量子架构」用户态与内核态之间的接口契约副本，随
 * xfce4-quantum / quantum-core 包分发，使守护进程可独立于内核头文件编译。
 * 量子架构是宿主模拟架构（arch/um 同型），下列接口读写的都是**模拟/记账模型**，
 * 不是真实量子硬件。
 */
#ifndef QUANTUM_CORE_UAPI_H
#define QUANTUM_CORE_UAPI_H

#include <linux/ioctl.h>
#include <linux/types.h>

#define QPU_IOC_MAGIC	'q'

/* CPU -> QPU：把整数 k 经 Π_k 门写入寄存器（翻转语义：基于当前态复合）。 */
#define QPU_ENC		_IOW(QPU_IOC_MAGIC, 1, __u64)
/* QPU -> CPU：测量全部比特解码（真实坍缩模拟）。 */
#define QPU_DEC		_IOR(QPU_IOC_MAGIC, 2, __u64)
/* 读取链路统计：total_writes / overwrites / slots。 */
#define QPU_LINK_STATS	_IOR(QPU_IOC_MAGIC, 3, struct qpu_link_stats)
/* 复位量子核到 |0...0>（用户态 load() 语义）。 */
#define QPU_RESET	_IO(QPU_IOC_MAGIC, 4)

struct qpu_link_stats {
	__u32 slots;
	__u32 buffered;
	__u64 total_writes;
	__u64 overwrites;
};

#define QPU_DEVICE	"/dev/qpu0"
#define QUANTUM_ENERGY_PROC	"/proc/quantum-energy"
#define QUANTUM_NET_PROC	"/proc/quantum-net"

#endif /* QUANTUM_CORE_UAPI_H */
