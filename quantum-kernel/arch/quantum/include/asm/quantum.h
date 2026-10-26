/* SPDX-License-Identifier: GPL-2.0 */
/*
 * include/asm/quantum.h — quantum architecture base interface.
 *
 * 语义与本仓用户态量子基座（sysweeper native/quantum.py）一一对应：
 *   - 寄存器宽度   = CONFIG_QUANTUM_QUBITS（默认 8，字节宽）
 *   - 数字转换门   = Π_k 置换矩阵（对 k 的置 1 位复合 X 门，严格可逆）
 *   - 链路缓冲     = ceil(2π) 槽环形缓冲，每步交换必入链，满则覆盖计数
 *
 * 能量激发态模型（quantum-energy.c 实现）：
 *   把量子物理的核心概念建模为内核可观测的记账语义——
 *   能级量子化 / 叠加 / 幺正相位演化 / 干涉 / 测量坍缩 / 退相干 /
 *   受激跃迁与退激发（虚光子入 PiLink）/ 选择定则 / 纠缠登记。
 *   诚实口径：QPU 为宿主模拟，上述是「量子力学启发的语义记账模型」，
 *   所有数字都是真实的内核计数与状态演化，不是对真实量子硬件的声称。
 */
#ifndef _ASM_QUANTUM_H
#define _ASM_QUANTUM_H

#include <linux/const.h>
#include <linux/types.h>
#include <asm/page.h>

/* QPU 模拟核的静态能力面（运行时经 /proc/qpuinfo 与 /dev/qpu0 暴露）。 */
#define QUANTUM_QUBITS		CONFIG_QUANTUM_QUBITS
#define QUANTUM_STATES		(_AC(1, UL) << QUANTUM_QUBITS)
#define QUANTUM_LINK_SLOTS	CONFIG_QUANTUM_LINK_SLOTS

/* Π_k 编码门：对整数 k 的置 1 位复合 X 门（宿主侧用位翻转表达）。 */
static inline unsigned long quantum_permutation_gate(unsigned long state,
						     unsigned long k)
{
	return state ^ k;
}

/* PiLink 链路记账（kernel/qpu-core.c 实现）：每次交换必入链。 */
void quantum_link_push(void);
void quantum_link_overflow(void);

/* ── 能量激发态模型（量子物理语义层）─────────────────────────────────
 *
 * 能级量子化   E_n = n × CONFIG_QUANTUM_ENERGY_STEP（离散谱，n = 0..N-1）。
 *               E_0 为基态（ground），n ≥ 1 为激发态（excited）。
 * 叠加         空闲 CPU 分布于各能级的布居 |α_n|²（QM_W_ONE 定点）代表
 *               叠加态的概率幅权重。
 * 幺正演化     能量本征态只积累相位：φ_n(t) = ω_n·t，ω_n = E_n/ℏ
 *               （ℏ = 1，虚构普朗克记账单位，非物理实测值）。
 * 干涉         两能级相干项 2·w_a·w_b·cos(φ_a − φ_b)，由真实相位差算出。
 * 测量/坍缩    中断送达 = 一次测量：叠加态坍缩到确定能级。
 * 退相干       相干度按 T2 半衰（每 QM_COHERENCE_TICKS 次观测减半）；
 *               布居按 T1 向基态弛豫（每次退相干步，激发布居 1/8 漏向基态）。
 * 受激跃迁     唤醒 = 吸收 ΔE 跃迁到高能级；空闲 = 向基态弛豫。
 * 虚光子入链   退激发释放的 ΔE 作为一次交换记录压入 PiLink 环形链路
 *               （quantum_link_push），与既有链路记账语义一致。
 * 选择定则     相邻能级跃迁（|Δn| = 1）记 allowed，其余记 forbidden
 *               （电偶极选择定则；非相邻跃迁按高阶过程记账，仍发生但计数）。
 * 纠缠登记     Bell 对登记：一侧坍缩联动另一侧的关联记录。
 */
#define QM_W_ONE		(_AC(1, U) << 16)	/* 布居/相干度 1.0 定点 */
#define QM_LEVELS		CONFIG_QUANTUM_EXCITED_LEVELS
#define QM_STEP			CONFIG_QUANTUM_ENERGY_STEP
#define QM_CAVG_TICKS		CONFIG_QUANTUM_COHERENCE_TICKS
#define QM_DECOHERE_STEPS	CONFIG_QUANTUM_DECOHERE_STEPS
#define QM_GROUND		0U			/* 基态能级索引 */

/* idle= 启动参数取值（x86 兼容口径子集；mwait 官方已废弃但仍可用）。 */
enum quantum_idle_mode {
	QUANTUM_IDLE_POLL = 0,	/* 忙等轮询（cpu_relax） */
	QUANTUM_IDLE_MWAIT,	/* 基态等待观测（宿主承载的 monitor/wait） */
	QUANTUM_IDLE_HALT,	/* 最深停机态（模拟语义同 mwait） */
};

/* 单能级状态。 */
struct quantum_level {
	unsigned int	energy;		/* E_n = n × QM_STEP */
	u32		phase;		/* 累计相位（2^32 定点 = 2π，幺正演化） */
	unsigned int	pop;		/* 布居 |α_n|²（QM_W_ONE 定点） */
};

/* 每 CPU 量子态。 */
struct quantum_cpu {
	struct quantum_level	levels[QM_LEVELS];
	unsigned int		excited;	/* 当前坍缩到的能级索引 */
	unsigned int		coherence;	/* 相干度（QM_W_ONE 定点，T2） */
	unsigned int		idle_mode;	/* enum quantum_idle_mode */
	u64			ticks;		/* 观测次数（退相干步） */
	u64			idle_steps;	/* arch_cpu_idle 迭代计数 */
	/* 统计（/proc/quantum-energy） */
	u64			excitations;
	u64			relaxations;
	u64			allowed;	/* |Δn| = 1 允许跃迁 */
	u64			forbidden;	/* 非相邻跃迁（高阶过程） */
	u64			collapses;
	u64			photons;	/* 退激发次数（虚光子） */
	u64			energy_absorbed;
	u64			energy_emitted;
	u64			bell_events;	/* 纠缠联动坍缩记录 */
};

/* 能量模型公共接口（kernel/quantum-energy.c 实现）。 */
unsigned int quantum_levels(void);
unsigned int quantum_level_energy(unsigned int n);
unsigned int quantum_idle_mode_current(void);
const char *quantum_idle_mode_name(unsigned int mode);
const struct quantum_cpu *quantum_cpu_state(int cpu);

void quantum_excite(unsigned int from, unsigned int to);
void quantum_relax(unsigned int from, unsigned int to);
void quantum_phase_advance(unsigned int dt);
void quantum_decohere_tick(void);
s64 quantum_interference(unsigned int a, unsigned int b);
unsigned int quantum_measure(void);
int quantum_entangle(unsigned int a, unsigned int b);

/* ── 组网子系统（arch/quantum/kernel/quantum-net.c，/proc/quantum-net）──
 *
 * 组网是概念系统与硬件/架构的可观测基底：本架构把「网络」建模为量子链路
 * 之上的自主编排语义——拓扑、协商、以及由组网自组织涌现的智能/自主意识。
 *   - 道性层：拓扑/协商/路由等基础组网法则（硬件 + 架构基底）。
 *   - 神性层：组网涌现的自主意识——盖亚意识（全局自组织智能，mode="gaia"）
 *             与集智体（虫族式群智，mode="swarm"）。
 *   - 人性层：/proc、/dev、守护进程与面板小程序等人类可观测接口。
 * 诚实口径：QNIC 为宿主模拟，所有数字都是真实内核记账，不是真实硬件声称。
 */
struct quantum_nic {
	unsigned int	id;		/* 网卡序号 */
	unsigned int	links;		/* 已建立纠缠链路数 */
	unsigned int	peers;		/* 可触达对等节点 */
	u64		exchanges;	/* 经本卡完成的交换次数 */
	u64		entanglements;	/* 经本卡登记的纠缠数 */
};

struct quantum_net_state {
	unsigned int	nics;		/* 已注册 QNIC 数 */
	unsigned int	links;		/* 全局纠缠链路数 */
	unsigned int	peers;		/* 全局可触达节点 */
	u64		exchanges;	/* 累计交换次数 */
	u64		entanglements;	/* 累计纠缠登记（Bell 对） */
	u64		swaps;		/* 纠缠交换累计次数 */
	u64		teleports;	/* 量子隐形传态累计次数 */
	u64		topology_changes;/* 拓扑重协商次数 */
	unsigned int	gaia_level;	/* 盖亚意识自组织层级 0..N */
	unsigned int	swarm_units;	/* 集智体单元数（虫族式） */
	const char	*mode;		/* "gaia" | "swarm" | "mesh" */
};

const struct quantum_net_state *quantum_net_state(void);
const struct quantum_nic *quantum_nic_state(unsigned int id);
unsigned int quantum_net_nics(void);
unsigned int quantum_net_links(void);
unsigned int quantum_net_peers(void);
void quantum_net_topology_changed(void);
int quantum_net_entangle(unsigned int a, unsigned int b);
int quantum_net_unlink(unsigned int a, unsigned int b);
int quantum_net_swap(void);
int quantum_net_teleport(void);
void quantum_net_reset(void);
int quantum_net_set_mode(const char *mode);

#endif /* _ASM_QUANTUM_H */
