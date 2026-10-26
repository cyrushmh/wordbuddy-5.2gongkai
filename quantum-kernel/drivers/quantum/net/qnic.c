// SPDX-License-Identifier: GPL-2.0
/*
 * drivers/quantum/net/qnic.c — 模拟量子网卡（QNIC）硬件抽象。
 *
 * 硬件层（概念系统「道性」基底）：在探测时把一组默认 Mesh 链路自动协商
 * 入架构侧组网状态（arch/quantum/kernel/quantum-net.c），代表 QNIC 上电后
 * 自发现对等节点。诚实口径：纯宿主模拟寄存器，不是真实硬件。
 */
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/init.h>
#include <asm/quantum.h>
#include "qnic.h"

/* 上电自协商的默认 Mesh：3 节点环（0-1, 1-2, 2-0）。 */
static const unsigned int qnic_ring[][2] = {
	{ 0, 1 }, { 1, 2 }, { 2, 0 },
};

int qnic_hw_probe(void)
{
	unsigned int i;

	for (i = 0; i < ARRAY_SIZE(qnic_ring); i++)
		quantum_net_entangle(qnic_ring[i][0], qnic_ring[i][1]);
	quantum_net_topology_changed();
	pr_info("qnic: hardware mesh brought up (%zu links auto-negotiated)\n",
		ARRAY_SIZE(qnic_ring));
	return 0;
}

void qnic_hw_remove(void)
{
	quantum_net_reset();
}

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Emulated quantum NIC hardware abstraction");
MODULE_AUTHOR("quantum-kernel project");
