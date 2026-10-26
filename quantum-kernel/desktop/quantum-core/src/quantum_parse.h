/* SPDX-License-Identifier: GPL-2.0 */
/*
 * src/quantum_parse.h — 量子架构接口数据的纯解析与格式化（可单测，无副作用）。
 */
#ifndef QUANTUM_PARSE_H
#define QUANTUM_PARSE_H

#include <stddef.h>
#include <stdint.h>

#include "quantum_uapi.h"

/* /proc/quantum-energy 解析后的快照（字段与内核 quantum_energy_show 输出对应）。 */
struct energy_state {
	int cpu;
	char idle_mode[32];
	unsigned excited;
	unsigned coherence;
	unsigned coherence_max;
	unsigned long long ticks;
	unsigned long long idle_steps;
	unsigned long long energy_absorbed;
	unsigned long long energy_emitted;
	unsigned bell_events;
	unsigned entanglements;
};

/* qpu_link_stats 定义见 quantum_uapi.h（接口契约副本）。 */

/* /proc/quantum-net 解析后的快照（字段与内核 quantum_net_show 输出对应）。 */
struct net_state {
	unsigned nics;
	char mode[16];			/* gaia / swarm / mesh */
	unsigned gaia_level;
	unsigned swarm_units;
	unsigned links;
	unsigned peers;
	unsigned long long exchanges;
	unsigned long long entanglements;
	unsigned long long topology_changes;
	unsigned nic_rows;		/* 每-NIC 明细表解析到的行数 */
};

/*
 * 解析 /proc/quantum-net 的文本到 net_state。
 * 返回 0 表示至少解析到 nics= 行（视为成功）；<0 表示文本为空或无法解析。
 * 未出现的字段保持默认 0。
 */
int parse_net(const char *text, struct net_state *out);

/*
 * 解析 /proc/quantum-energy 的文本到 energy_state。
 * 返回 0 表示至少解析到 cpu 行（视为成功）；<0 表示文本为空或无法解析 cpu。
 * 未出现的字段保持默认 0。
 */
int parse_energy(const char *text, struct energy_state *out);

/*
 * 把一次快照格式化为 state.json 内容（不含结尾换行）。
 * buf 由调用方保证不小于 STATE_JSON_MAX。energy_ok/qpu_ok 标记对应接口是否可读。
 * 返回写入长度（不含结尾 '\0'）。
 */
int format_state_json(char *buf, size_t sz,
                      const struct energy_state *e, int energy_ok,
                      const struct qpu_link_stats *q, int qpu_ok,
                      const struct net_state *n, int net_ok);

#define STATE_JSON_MAX 3072

#endif /* QUANTUM_PARSE_H */
