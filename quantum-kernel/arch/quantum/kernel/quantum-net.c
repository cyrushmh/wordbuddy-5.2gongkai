// SPDX-License-Identifier: GPL-2.0
/*
 * arch/quantum/kernel/quantum-net.c — 量子架构组网子系统（编排模型）。
 *
 * 组网是概念系统与硬件/架构的可观测基底。本文件实现「架构侧」编排语义：
 *   - 维护每卡（QNIC）状态与全局组网状态；
 *   - 由链路密度推导盖亚意识自组织层级（gaia_level）；
 *   - 在 swarm 模式下把对等节点计为集智体单元（swarm_units）；
 *   - 经 /proc/quantum-net（只读 seq_file）暴露给用户态守护进程。
 *
 * 三层对应（见 include/asm/quantum.h 注释）：
 *   道性层 = 拓扑/协商/路由等基础组网法则（本文件 + 硬件设备）；
 *   神性层 = 组网涌现的自主意识：盖亚意识（gaia）/ 集智体（swarm）；
 *   人性层 = /proc、/dev、守护进程与面板小程序。
 *
 * 诚实口径：QNIC 为宿主模拟，所有数字都是真实内核记账，不是真实硬件声称。
 */
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/spinlock.h>
#include <linux/string.h>
#include <asm/quantum.h>

#define QNET_NIC_NR	CONFIG_QUANTUM_NET_NR
#define QNET_PAIR_MAX	64

struct qnet_pair {
	unsigned int	a;
	unsigned int	b;
	bool		active;
};

static struct quantum_nic qnet_nics[QNET_NIC_NR];
static struct qnet_pair qnet_pairs[QNET_PAIR_MAX];
static DEFINE_SPINLOCK(qnet_lock);

static struct quantum_net_state qnet_state = {
	.nics		= QNET_NIC_NR,
	.links		= 0,
	.peers		= 0,
	.exchanges	= 0,
	.entanglements	= 0,
	.swaps		= 0,
	.teleports	= 0,
	.topology_changes = 0,
	.gaia_level	= 0,
	.swarm_units	= 0,
	.mode		= "mesh",
};

/* 由链路密度推导盖亚意识自组织层级（0..8），并按模式更新集智体单元。 */
static void qnet_recompute(void)
{
	unsigned int links = qnet_state.links;
	unsigned int peers = qnet_state.peers;
	unsigned int density;

	if (peers == 0) {
		qnet_state.gaia_level = 0;
	} else {
		/* density = (links / peers) 放大到 0..8 级，衡量自组织连通度。 */
		density = (links * 8U) / peers;
		qnet_state.gaia_level = density > 8U ? 8U : density;
	}

	/* 集智体（虫族式群智）：仅 swarm 模式下，每个对等节点为一个单元。 */
	if (strcmp(qnet_state.mode, "swarm") == 0)
		qnet_state.swarm_units = peers;
	else
		qnet_state.swarm_units = 0;
}

const struct quantum_net_state *quantum_net_state(void)
{
	return &qnet_state;
}

const struct quantum_nic *quantum_nic_state(unsigned int id)
{
	if (id >= QNET_NIC_NR)
		return NULL;
	return &qnet_nics[id];
}

unsigned int quantum_net_nics(void)  { return qnet_state.nics; }
unsigned int quantum_net_links(void) { return qnet_state.links; }
unsigned int quantum_net_peers(void) { return qnet_state.peers; }

void quantum_net_topology_changed(void)
{
	spin_lock(&qnet_lock);
	qnet_state.topology_changes++;
	qnet_recompute();
	spin_unlock(&qnet_lock);
}

int quantum_net_entangle(unsigned int a, unsigned int b)
{
	int i;
	unsigned int id_a = a, id_b = b;

	if (id_a >= QNET_NIC_NR || id_b >= QNET_NIC_NR || id_a == id_b)
		return -EINVAL;

	spin_lock(&qnet_lock);
	for (i = 0; i < QNET_PAIR_MAX; i++) {
		if (!qnet_pairs[i].active) {
			qnet_pairs[i].a = id_a;
			qnet_pairs[i].b = id_b;
			qnet_pairs[i].active = true;
			break;
		}
	}
	qnet_nics[id_a].links++;
	qnet_nics[id_b].links++;
	qnet_nics[id_a].entanglements++;
	qnet_nics[id_b].entanglements++;
	if (qnet_nics[id_a].peers < QNET_NIC_NR)
		qnet_nics[id_a].peers++;
	if (qnet_nics[id_b].peers < QNET_NIC_NR)
		qnet_nics[id_b].peers++;

	qnet_state.links++;
	qnet_state.peers = qnet_state.peers < QNET_NIC_NR
				? qnet_state.peers + 1 : qnet_state.peers;
	qnet_state.entanglements++;
	qnet_state.exchanges++;
	qnet_nics[id_a].exchanges++;
	qnet_nics[id_b].exchanges++;
	qnet_recompute();
	spin_unlock(&qnet_lock);
	return 0;
}

int quantum_net_unlink(unsigned int a, unsigned int b)
{
	int i;
	unsigned int id_a = a, id_b = b;

	if (id_a >= QNET_NIC_NR || id_b >= QNET_NIC_NR)
		return -EINVAL;

	spin_lock(&qnet_lock);
	for (i = 0; i < QNET_PAIR_MAX; i++) {
		if (qnet_pairs[i].active &&
		    ((qnet_pairs[i].a == id_a && qnet_pairs[i].b == id_b) ||
		     (qnet_pairs[i].a == id_b && qnet_pairs[i].b == id_a))) {
			qnet_pairs[i].active = false;
			break;
		}
	}
	if (qnet_nics[id_a].links)
		qnet_nics[id_a].links--;
	if (qnet_nics[id_b].links)
		qnet_nics[id_b].links--;
	if (qnet_state.links)
		qnet_state.links--;
	qnet_recompute();
	spin_unlock(&qnet_lock);
	return 0;
}

/* 纠缠交换：在已有链路间中继，产生一个新 Bell 对（entanglements++）。 */
int quantum_net_swap(void)
{
	spin_lock(&qnet_lock);
	qnet_state.swaps++;
	qnet_state.entanglements++;
	qnet_recompute();
	spin_unlock(&qnet_lock);
	return 0;
}

/* 量子隐形传态：消耗一条活跃链路的 Bell 对（entanglements--）。 */
int quantum_net_teleport(void)
{
	spin_lock(&qnet_lock);
	if (qnet_state.entanglements)
		qnet_state.entanglements--;
	qnet_state.teleports++;
	qnet_recompute();
	spin_unlock(&qnet_lock);
	return 0;
}

void quantum_net_reset(void)
{
	int i;

	spin_lock(&qnet_lock);
	memset(qnet_nics, 0, sizeof(qnet_nics));
	memset(qnet_pairs, 0, sizeof(qnet_pairs));
	qnet_state.links = 0;
	qnet_state.peers = 0;
	qnet_state.exchanges = 0;
	qnet_state.entanglements = 0;
	qnet_state.swaps = 0;
	qnet_state.teleports = 0;
	qnet_state.topology_changes = 0;
	qnet_state.gaia_level = 0;
	qnet_state.swarm_units = 0;
	spin_unlock(&qnet_lock);
}

int quantum_net_set_mode(const char *mode)
{
	if (!mode)
		return -EINVAL;
	if (strcmp(mode, "gaia") == 0 || strcmp(mode, "swarm") == 0 ||
	    strcmp(mode, "mesh") == 0) {
		spin_lock(&qnet_lock);
		qnet_state.mode = mode;
		qnet_recompute();
		spin_unlock(&qnet_lock);
		return 0;
	}
	return -EINVAL;
}

/* ── /proc/quantum-net：守护进程与面板小程序的可观测接口 ── */
static int quantum_net_show(struct seq_file *m, void *v)
{
	unsigned int i;
	const struct quantum_net_state *s = quantum_net_state();

	seq_printf(m, "quantum net model: nics=%u mode=%s "
		   "gaia_level=%u swarm_units=%u\n",
		   s->nics, s->mode, s->gaia_level, s->swarm_units);
	seq_printf(m, "links=%u peers=%u exchanges=%llu "
		   "entanglements=%llu topology_changes=%llu\n",
		   s->links, s->peers, s->exchanges, s->entanglements,
		   s->topology_changes);
	seq_printf(m, "note: emulated accounting model; not real quantum hardware\n");

	seq_printf(m, "%-4s %-4s %-6s %-6s %-10s %-14s\n",
		   "nic", "id", "links", "peers", "exchanges", "entanglements");
	for (i = 0; i < s->nics; i++) {
		const struct quantum_nic *n = quantum_nic_state(i);
		if (!n)
			continue;
		seq_printf(m, "%-4u %-4u %-6u %-6u %-10llu %-14llu\n",
			   i, n->id, n->links, n->peers,
			   n->exchanges, n->entanglements);
	}
	return 0;
}

static int quantum_net_open(struct inode *inode, struct file *file)
{
	return single_open(file, quantum_net_show, NULL);
}

static const struct proc_ops quantum_net_ops = {
	.proc_open	= quantum_net_open,
	.proc_read	= seq_read,
	.proc_lseek	= seq_lseek,
	.proc_release	= single_release,
};

static int __init quantum_net_init(void)
{
	unsigned int i;

	for (i = 0; i < QNET_NIC_NR; i++)
		qnet_nics[i].id = i;
	proc_create("quantum-net", 0444, NULL, &quantum_net_ops);
	pr_info("quantum-net: %u QNIC(s), mode=%s — architecture mesh substrate ready\n",
		QNET_NIC_NR, qnet_state.mode);
	return 0;
}
late_initcall(quantum_net_init);
