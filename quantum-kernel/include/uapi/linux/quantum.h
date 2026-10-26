/* SPDX-License-Identifier: GPL-2.0 */
/*
 * include/uapi/linux/quantum.h — QPU / QNET user API.
 *
 * /dev/qpu0（misc 字符设备）的 UAPI：把整数经 Π_k 置换矩阵门写入模拟
 * 量子寄存器、测量解码还原，并读取链路缓冲统计。
 * /dev/qnet0（misc 字符设备）的 UAPI：量子组网子系统（qnet）——链路登记、
 * Bell 对分发表、纠缠交换与隐形传态的计数记账。
 * 语义与本仓用户态量子基座一致（8q 字节宽、ceil(2π)=7 槽链路）。
 *
 * 诚实口径：量子为宿主模拟架构；qnet 是「量子力学启发的语义记账 +
 * 真实内核计数」，不是真实量子硬件（无 gcc 后端 / 无可引导镜像）。
 */
#ifndef _UAPI_LINUX_QUANTUM_H
#define _UAPI_LINUX_QUANTUM_H

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

/* ── 量子组网子系统（qnet）UAPI ───────────────────────────────────────
 * /dev/qnet0：登记 QPU 间链路、读取 Bell 对分发表与纠缠交换/隐形传态计数。
 * 设备节点与 proc 文件常量供用户态（quantum-core 守护进程）引用。 */
#define QNET_DEVICE	"/dev/qnet0"
#define QUANTUM_NET_PROC	"/proc/quantum-net"

/* 在 QPU 网络中登记一条到 peer 节点的链路。 */
#define QNET_LINK_ADD	_IOW(QPU_IOC_MAGIC, 5, __u32)
/* 在 QPU 网络中删除一条到 peer 节点的链路。 */
#define QNET_LINK_DEL	_IOW(QPU_IOC_MAGIC, 6, __u32)
/* 读取组网统计：链路数 / 活跃链路 / Bell 对总数 / 纠缠交换 / 隐形传态。 */
#define QNET_LINK_STATS	_IOR(QPU_IOC_MAGIC, 7, struct qnet_link_stats)
/* 执行一次纠缠交换（在活跃链路间中继 Bell 对，产生新 Bell 对）。 */
#define QNET_ENTANGLE_SWAP	_IO(QPU_IOC_MAGIC, 8)
/* 执行一次量子隐形传态（消耗一条活跃链路的 Bell 对 + 经典回传位）。 */
#define QNET_TELEPORT	_IO(QPU_IOC_MAGIC, 9)
/* 复位 qnet 子系统（清空链路表与全部计数）。 */
#define QNET_RESET	_IO(QPU_IOC_MAGIC, 10)

struct qnet_link_stats {
	__u32 links;		/* 链路槽总数 */
	__u32 active;		/* 当前活跃链路数 */
	__u64 bell_pairs;	/* Bell 对累计产生数 */
	__u64 swaps;		/* 纠缠交换累计次数 */
	__u64 teleports;		/* 隐形传态累计次数 */
};

#endif /* _UAPI_LINUX_QUANTUM_H */
