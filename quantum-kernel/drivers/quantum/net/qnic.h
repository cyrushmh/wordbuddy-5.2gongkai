/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _DRIVERS_QUANTUM_NET_QNIC_H
#define _DRIVERS_QUANTUM_NET_QNIC_H

#include <linux/types.h>

/* 模拟量子网卡（QNIC）寄存器面——宿主记账，非真实 MMIO。
 *
 * 硬件层即「道性」基底：拓扑/协商/路由等基础组网法则由硬件寄存器表达，
 * 上电自协商出对等节点并登记到架构侧组网编排（arch/quantum/kernel/quantum-net.c）。
 */
struct qnic_hw {
	__u32 link_ctrl;	/* 链路建立/断开控制 */
	__u32 bell_fifo;	/* Bell 对 FIFO 深度 */
	__u32 peer_map;		/* 对等节点位图（每 bit = 一个可触达 peer） */
	__u32 qos;		/* 服务等级（纠缠保真度阈值，定点） */
};

/* 上电自协商默认 Mesh；退出时清空。返回发现的链路数（<0 为错误）。 */
int qnic_hw_probe(void);
void qnic_hw_remove(void);

#endif /* _DRIVERS_QUANTUM_NET_QNIC_H */
