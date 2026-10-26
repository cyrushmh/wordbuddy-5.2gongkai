// SPDX-License-Identifier: GPL-2.0
/*
 * arch/quantum/kernel/quantum-energy.c — 能量激发态模型（量子物理语义层）。
 *
 * 内核侧记账模型（诚实口径：QPU 为宿主模拟，本模型是「量子力学启发的
 * 语义记账」，所有数字都是真实的内核计数与状态演化）：
 *   - 能级量子化：E_n = n × ΔE 的离散谱；E_0 基态，n ≥ 1 激发态；
 *   - 叠加/布居：空闲 CPU 以布居权重分布于各能级；
 *   - 幺正相位演化：能量本征态只积累相位 φ_n(t) = E_n·t（ℏ = 1，虚构单位）；
 *   - 干涉：2·w_a·w_b·cos(φ_a − φ_b)（定点 sin 表查算，乘相干度衰减）；
 *   - 测量/坍缩：中断送达（arch_cpu_idle_exit）= 一次测量，叠加态坍缩；
 *   - 退相干：相干度按 T2 半衰；布居按 T1 向基态弛豫；
 *   - 受激跃迁/退激发：唤醒吸收 ΔE，空闲弛豫放出 ΔE；
 *   - 虚光子入链：退激发的 ΔE 作为一次交换压入 PiLink 环形链路；
 *   - 选择定则：|Δn| = 1 记 allowed，其余记 forbidden；
 *   - 纠缠登记：Bell 对一侧坍缩联动另一侧关联记录。
 *
 * idle= 启动参数（x86 兼容口径子集；mwait 官方已废弃但仍可用）：
 *   idle=poll   强制轮询（cpu_idle_poll_ctrl + cpu_relax 忙等）；
 *   idle=mwait  基态等待观测——宿主承载的 monitor/wait 语义（默认）；
 *   idle=halt   最深停机态（模拟语义同 mwait，无真实停机指令）。
 */
#include <linux/cpu.h>
#include <linux/export.h>
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/percpu.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/smp.h>
#include <linux/spinlock.h>
#include <asm/processor.h>
#include <asm/quantum.h>

/* arch_cpu_idle 内相位演进的步长（虚构时间记账单位）。 */
#define QM_IDLE_DT		64

/* 纠缠对（Bell pair）登记表。 */
#define QM_ENTANGLE_MAX		8

struct quantum_pair {
	unsigned int	a;
	unsigned int	b;
	bool		active;
	u64		collapses;
};

static DEFINE_PER_CPU(struct quantum_cpu, quantum_cpus);
static DEFINE_SPINLOCK(quantum_pair_lock);
static struct quantum_pair quantum_pairs[QM_ENTANGLE_MAX];

/* idle= 覆盖值（-EINVAL = 未指定，用默认）。 */
static int quantum_idle_override = -EINVAL;

/* ── 定点三角函数（256 段线性表，sin ×2^15）────────────────────────── */

/* 定点 sin 表：256 段线性插值，值域 ×2^15（sin(2πk/256)）。 */
static const s16 qm_sin_tab[256] = {
	     0,    804,   1608,   2410,   3212,   4011,   4808,   5602,
	  6393,   7179,   7962,   8739,   9512,  10278,  11039,  11793,
	 12539,  13279,  14010,  14732,  15446,  16151,  16846,  17530,
	 18204,  18868,  19519,  20159,  20787,  21403,  22005,  22594,
	 23170,  23731,  24279,  24811,  25329,  25832,  26319,  26790,
	 27245,  27683,  28105,  28510,  28898,  29268,  29621,  29956,
	 30273,  30571,  30852,  31113,  31356,  31580,  31785,  31971,
	 32137,  32285,  32412,  32521,  32609,  32678,  32728,  32757,
	 32767,  32757,  32728,  32678,  32609,  32521,  32412,  32285,
	 32137,  31971,  31785,  31580,  31356,  31113,  30852,  30571,
	 30273,  29956,  29621,  29268,  28898,  28510,  28105,  27683,
	 27245,  26790,  26319,  25832,  25329,  24811,  24279,  23731,
	 23170,  22594,  22005,  21403,  20787,  20159,  19519,  18868,
	 18204,  17530,  16846,  16151,  15446,  14732,  14010,  13279,
	 12539,  11793,  11039,  10278,   9512,   8739,   7962,   7179,
	  6393,   5602,   4808,   4011,   3212,   2410,   1608,    804,
	     0,   -804,  -1608,  -2410,  -3212,  -4011,  -4808,  -5602,
	 -6393,  -7179,  -7962,  -8739,  -9512, -10278, -11039, -11793,
	-12539, -13279, -14010, -14732, -15446, -16151, -16846, -17530,
	-18204, -18868, -19519, -20159, -20787, -21403, -22005, -22594,
	-23170, -23731, -24279, -24811, -25329, -25832, -26319, -26790,
	-27245, -27683, -28105, -28510, -28898, -29268, -29621, -29956,
	-30273, -30571, -30852, -31113, -31356, -31580, -31785, -31971,
	-32137, -32285, -32412, -32521, -32609, -32678, -32728, -32757,
	-32767, -32757, -32728, -32678, -32609, -32521, -32412, -32285,
	-32137, -31971, -31785, -31580, -31356, -31113, -30852, -30571,
	-30273, -29956, -29621, -29268, -28898, -28510, -28105, -27683,
	-27245, -26790, -26319, -25832, -25329, -24811, -24279, -23731,
	-23170, -22594, -22005, -21403, -20787, -20159, -19519, -18868,
	-18204, -17530, -16846, -16151, -15446, -14732, -14010, -13279,
	-12539, -11793, -11039, -10278,  -9512,  -8739,  -7962,  -7179,
	 -6393,  -5602,  -4808,  -4011,  -3212,  -2410,  -1608,   -804,
};

static s32 qm_sin(u32 phase)
{
	unsigned int idx = phase >> 24;		/* 256 段 */
	unsigned int frac = (phase >> 16) & 0xff;
	s32 a = qm_sin_tab[idx];
	s32 b = qm_sin_tab[(idx + 1) & 0xff];

	return a + (((b - a) * (s32)frac) >> 8);
}

static s32 qm_cos(u32 phase)
{
	/* cos(x) = sin(x + π/2)。 */
	return qm_sin(phase + (1U << 30));
}

/* ── 状态初始化与不变量 ───────────────────────────────────────────── */

static void qm_reset(struct quantum_cpu *qm, unsigned int idle_mode)
{
	unsigned int n, share;

	memset(qm, 0, sizeof(*qm));
	qm->idle_mode = idle_mode;
	qm->excited = QM_GROUND;
	qm->coherence = QM_W_ONE;

	/* 模型先验：基态布居 3/4，余量在激发态间均分。 */
	share = QM_W_ONE / 4 / (QM_LEVELS - 1);
	qm->levels[QM_GROUND].pop = QM_W_ONE - share * (QM_LEVELS - 1);
	for (n = 1; n < QM_LEVELS; n++)
		qm->levels[n].pop = share;

	for (n = 0; n < QM_LEVELS; n++)
		qm->levels[n].energy = n * QM_STEP;
}

/* 惰性初始化兜底（正常路径由 core_initcall 完成，早于任何空闲调用）。 */
static void qm_ensure(struct quantum_cpu *qm)
{
	if (unlikely(!qm->levels[QM_GROUND].pop))
		qm_reset(qm, quantum_idle_override >= 0 ?
			      quantum_idle_override : QUANTUM_IDLE_MWAIT);
}

/* 跃迁布居迁移：from 侧 1/4 布居移向 to，并部分恢复相干度。 */
static void qm_settle(struct quantum_cpu *qm, unsigned int from,
		      unsigned int to)
{
	unsigned int move = qm->levels[from].pop >> 2;

	if (move) {
		qm->levels[from].pop -= move;
		qm->levels[to].pop =
			min(qm->levels[to].pop + move, QM_W_ONE);
	}
	qm->coherence = max(qm->coherence, QM_W_ONE / 2);
}

/* 选择定则记账：|Δn| = 1 为电偶极允许，其余为非相邻（高阶）跃迁。 */
static void qm_selection(struct quantum_cpu *qm, int from, int to)
{
	if (abs(to - from) == 1)
		qm->allowed++;
	else
		qm->forbidden++;
}

/* ── 公共接口（EXPORT_SYMBOL_GPL，供 /dev/qpuN 与模块观测）────────── */

unsigned int quantum_levels(void)
{
	return QM_LEVELS;
}
EXPORT_SYMBOL_GPL(quantum_levels);

unsigned int quantum_level_energy(unsigned int n)
{
	return n < QM_LEVELS ? n * QM_STEP : 0;
}

unsigned int quantum_idle_mode_current(void)
{
	struct quantum_cpu *qm = this_cpu_ptr(&quantum_cpus);

	qm_ensure(qm);
	return qm->idle_mode;
}
EXPORT_SYMBOL_GPL(quantum_idle_mode_current);

const char *quantum_idle_mode_name(unsigned int mode)
{
	switch (mode) {
	case QUANTUM_IDLE_POLL:
		return "poll";
	case QUANTUM_IDLE_MWAIT:
		return "mwait";
	case QUANTUM_IDLE_HALT:
		return "halt";
	default:
		return "unknown";
	}
}
EXPORT_SYMBOL_GPL(quantum_idle_mode_name);

const struct quantum_cpu *quantum_cpu_state(int cpu)
{
	return per_cpu_ptr(&quantum_cpus, cpu);
}
EXPORT_SYMBOL_GPL(quantum_cpu_state);

void quantum_excite(unsigned int from, unsigned int to)
{
	struct quantum_cpu *qm = this_cpu_ptr(&quantum_cpus);
	unsigned int de;

	if (from >= QM_LEVELS || to >= QM_LEVELS || from == to)
		return;

	qm_ensure(qm);
	de = qm->levels[to].energy - qm->levels[from].energy;
	qm_selection(qm, from, to);
	qm->excitations++;
	qm->energy_absorbed += de;
	qm_settle(qm, from, to);
}
EXPORT_SYMBOL_GPL(quantum_excite);

void quantum_relax(unsigned int from, unsigned int to)
{
	struct quantum_cpu *qm = this_cpu_ptr(&quantum_cpus);
	unsigned int de;

	if (from >= QM_LEVELS || to >= QM_LEVELS || from == to)
		return;

	qm_ensure(qm);
	de = qm->levels[from].energy - qm->levels[to].energy;
	qm_selection(qm, from, to);
	qm->relaxations++;
	qm->energy_emitted += de;
	qm->photons++;
	/* 退激发放出的虚光子作为一次交换压入 PiLink 环形链路。 */
	quantum_link_push();
	qm_settle(qm, from, to);
}
EXPORT_SYMBOL_GPL(quantum_relax);

void quantum_phase_advance(unsigned int dt)
{
	struct quantum_cpu *qm = this_cpu_ptr(&quantum_cpus);
	unsigned int n;

	qm_ensure(qm);
	/* 能量本征态只积累相位：φ_n += E_n·dt（ℏ = 1，虚构记账单位）。
	 * u32 自然回绕即 2π 周期性。 */
	for (n = 0; n < QM_LEVELS; n++)
		qm->levels[n].phase += qm->levels[n].energy * dt;
}
EXPORT_SYMBOL_GPL(quantum_phase_advance);

void quantum_decohere_tick(void)
{
	struct quantum_cpu *qm = this_cpu_ptr(&quantum_cpus);
	unsigned int n, drain = 0;

	qm_ensure(qm);
	/* T1（振幅阻尼）：激发布居 1/8 漏向基态。 */
	for (n = 1; n < QM_LEVELS; n++) {
		unsigned int d = qm->levels[n].pop >> 3;

		qm->levels[n].pop -= d;
		drain += d;
	}
	if (drain)
		qm->levels[QM_GROUND].pop =
			min(qm->levels[QM_GROUND].pop + drain, QM_W_ONE);

	/* T2（相干衰减）：每 QM_CAVG_TICKS 次观测相干度减半。 */
	qm->ticks++;
	if (qm->ticks % QM_CAVG_TICKS == 0)
		qm->coherence >>= 1;
}
EXPORT_SYMBOL_GPL(quantum_decohere_tick);

s64 quantum_interference(unsigned int a, unsigned int b)
{
	struct quantum_cpu *qm = this_cpu_ptr(&quantum_cpus);
	s64 t;

	if (a >= QM_LEVELS || b >= QM_LEVELS)
		return 0;

	qm_ensure(qm);
	/* 干涉项 2·w_a·w_b·cos(φ_a − φ_b)·coherence。
	 * 定点换算：w 为 2^16，cos 为 2^15，相干度为 2^16；
	 * 最终返回 2^30 定点，理论区间 [−2, +2]。 */
	t = ((s64)2 * qm->levels[a].pop * qm->levels[b].pop *
	     qm_cos(qm->levels[a].phase - qm->levels[b].phase)) >> 17;
	return (t * qm->coherence) >> 16;
}
EXPORT_SYMBOL_GPL(quantum_interference);

unsigned int quantum_measure(void)
{
	struct quantum_cpu *qm = this_cpu_ptr(&quantum_cpus);
	unsigned int n, best = QM_GROUND;
	unsigned long flags;
	int i;

	qm_ensure(qm);
	/* 测量：按布居权重取最大者（确定性口径，无 RNG 依赖）。 */
	for (n = 1; n < QM_LEVELS; n++)
		if (qm->levels[n].pop > qm->levels[best].pop)
			best = n;

	qm->excited = best;
	qm->collapses++;
	/* 坍缩到确定本征态，相干相位基准重建（相干度恢复）。 */
	for (n = 0; n < QM_LEVELS; n++)
		qm->levels[n].pop = 0;
	qm->levels[best].pop = QM_W_ONE;
	qm->coherence = QM_W_ONE;

	/* Bell 对联动：登记了 (best, partner) 的一侧坍缩，
	 * 伙伴侧关联记录坍缩事件（纠缠对检验后消耗）。 */
	spin_lock_irqsave(&quantum_pair_lock, flags);
	for (i = 0; i < QM_ENTANGLE_MAX; i++) {
		if (quantum_pairs[i].active && quantum_pairs[i].a == best) {
			quantum_pairs[i].collapses++;
			quantum_pairs[i].active = false;
			qm->bell_events++;
		}
	}
	spin_unlock_irqrestore(&quantum_pair_lock, flags);

	return best;
}
EXPORT_SYMBOL_GPL(quantum_measure);

int quantum_entangle(unsigned int a, unsigned int b)
{
	unsigned long flags;
	int i, ret = -ENOMEM;

	if (a >= QM_LEVELS || b >= QM_LEVELS)
		return -EINVAL;

	spin_lock_irqsave(&quantum_pair_lock, flags);
	for (i = 0; i < QM_ENTANGLE_MAX; i++) {
		if (!quantum_pairs[i].active) {
			quantum_pairs[i].a = a;
			quantum_pairs[i].b = b;
			quantum_pairs[i].active = true;
			quantum_pairs[i].collapses = 0;
			ret = 0;
			break;
		}
	}
	spin_unlock_irqrestore(&quantum_pair_lock, flags);
	return ret;
}
EXPORT_SYMBOL_GPL(quantum_entangle);

/* ── 空闲钩子（覆盖 kernel/sched/idle.c 的 weak 定义）──────────────── */

void arch_cpu_idle_enter(void)
{
	struct quantum_cpu *qm = this_cpu_ptr(&quantum_cpus);

	qm_ensure(qm);
	/* 进入空闲 = 向基态弛豫一步：退激发释放 ΔE，
	 * 虚光子作为一次交换压入 PiLink 环形链路。 */
	if (qm->excited > QM_GROUND)
		quantum_relax(qm->excited, qm->excited - 1);
}

void arch_cpu_idle(void)
{
	struct quantum_cpu *qm = this_cpu_ptr(&quantum_cpus);

	qm_ensure(qm);
	/* 两次观测（中断）之间的幺正相位演化。 */
	quantum_phase_advance(QM_IDLE_DT);
	qm->idle_steps++;
	/* T1/T2 退相干按步长节流（记账单位，非真实时间）。 */
	if (qm->idle_steps % QM_DECOHERE_STEPS == 0)
		quantum_decohere_tick();

	switch (qm->idle_mode) {
	case QUANTUM_IDLE_POLL:
		/* 强制轮询：忙等（对应 x86 idle=poll 语义）。 */
		cpu_relax();
		break;
	case QUANTUM_IDLE_MWAIT:
		/* 基态等待观测：宿主承载的 monitor/wait 语义。
		 * 无真实功耗可变——「等待」由宿主进程模拟，立即返回。 */
		break;
	case QUANTUM_IDLE_HALT:
		/* 最深停机态：模拟语义同 mwait（无真实停机指令）。 */
		break;
	default:
		cpu_relax();
		break;
	}
}

void arch_cpu_idle_exit(void)
{
	struct quantum_cpu *qm = this_cpu_ptr(&quantum_cpus);
	unsigned int measured;

	qm_ensure(qm);
	/* 中断送达 = 一次测量：空闲叠加态坍缩到确定能级。 */
	measured = quantum_measure();
	/* 随后 CPU 受激跃迁到运行能级（吸收 ΔE 记账）。 */
	if (measured < QM_LEVELS - 1)
		quantum_excite(measured, measured + 1);
}

/* ── idle= 启动参数（x86 兼容口径子集）──────────────────────────────── */

static int __init quantum_idle_setup(char *str)
{
	if (!str)
		return -EINVAL;

	if (!strcmp(str, "poll")) {
		pr_info("quantum: using polling idle threads\n");
		quantum_idle_override = QUANTUM_IDLE_POLL;
		cpu_idle_poll_ctrl(true);
	} else if (!strcmp(str, "mwait")) {
		/* x86 官方文档已删除 mwait 取值（deprecated），但参数仍可用：
		 * 量子模拟架构保留 mwait 的「基态等待观测」语义。 */
		pr_info("quantum: using mwait idle (ground-state wait)\n");
		quantum_idle_override = QUANTUM_IDLE_MWAIT;
	} else if (!strcmp(str, "halt")) {
		pr_info("quantum: using halt idle\n");
		quantum_idle_override = QUANTUM_IDLE_HALT;
	} else {
		pr_warn("quantum: unknown idle=%s (supported: poll, mwait, halt)\n",
			str);
		return -EINVAL;
	}

	return 0;
}
early_param("idle", quantum_idle_setup);

/* ── /proc/quantum-energy ─────────────────────────────────────────── */

static int quantum_energy_show(struct seq_file *m, void *v)
{
	struct quantum_cpu *qm = this_cpu_ptr(&quantum_cpus);
	unsigned int n;
	int i;
	unsigned long flags;

	qm_ensure(qm);
	seq_printf(m, "quantum energy model: levels=%u step=%u "
		   "coherence_ticks=%u decohere_steps=%u\n",
		   QM_LEVELS, QM_STEP, QM_CAVG_TICKS, QM_DECOHERE_STEPS);
	seq_printf(m, "cpu%d: idle_mode=%s excited=%u coherence=%u/%u "
		   "ticks=%llu idle_steps=%llu\n",
		   smp_processor_id(),
		   quantum_idle_mode_name(qm->idle_mode),
		   qm->excited, qm->coherence, QM_W_ONE,
		   qm->ticks, qm->idle_steps);

	seq_printf(m, "level  energy  phase        pop\n");
	for (n = 0; n < QM_LEVELS; n++)
		seq_printf(m, "%-6u %-7u %-#13x %u\n",
			   n, qm->levels[n].energy, qm->levels[n].phase,
			   qm->levels[n].pop);

	seq_printf(m, "interference(0,1) = %lld (2^30 fixed, [-2, +2])\n",
		   quantum_interference(0, 1));

	seq_printf(m, "events: excitations=%llu relaxations=%llu "
		   "allowed=%llu forbidden=%llu collapses=%llu photons=%llu\n",
		   qm->excitations, qm->relaxations, qm->allowed,
		   qm->forbidden, qm->collapses, qm->photons);
	seq_printf(m, "energy: absorbed=%llu emitted=%llu (planck units)\n",
		   qm->energy_absorbed, qm->energy_emitted);

	spin_lock_irqsave(&quantum_pair_lock, flags);
	for (i = 0; i < QM_ENTANGLE_MAX; i++) {
		if (quantum_pairs[i].active)
			seq_printf(m, "entangled: %u <-> %u\n",
				   quantum_pairs[i].a, quantum_pairs[i].b);
	}
	spin_unlock_irqrestore(&quantum_pair_lock, flags);
	seq_printf(m, "bell_events: %llu\n", qm->bell_events);

	return 0;
}

static int quantum_energy_open(struct inode *inode, struct file *file)
{
	return single_open(file, quantum_energy_show, NULL);
}

static const struct proc_ops quantum_energy_ops = {
	.proc_open	= quantum_energy_open,
	.proc_read	= seq_read,
	.proc_lseek	= seq_lseek,
	.proc_release	= single_release,
};

static int __init quantum_energy_init(void)
{
	int cpu;

	/* early_param 已完成覆盖分发；给每颗 CPU 落定初态。 */
	for_each_possible_cpu(cpu)
		qm_reset(per_cpu_ptr(&quantum_cpus, cpu),
			 quantum_idle_override >= 0 ?
				 quantum_idle_override : QUANTUM_IDLE_MWAIT);

	proc_create("quantum-energy", 0444, NULL, &quantum_energy_ops);
	return 0;
}
core_initcall(quantum_energy_init);
