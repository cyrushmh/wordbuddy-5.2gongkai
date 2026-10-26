/* SPDX-License-Identifier: GPL-2.0 */
/*
 * src/quantum_parse.c — /proc/quantum-energy 文本解析与 state.json 格式化。
 * 纯函数、无 I/O、无副作用，便于单元测试（mock 文本即可验证）。
 */
#include "quantum_parse.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int parse_energy(const char *text, struct energy_state *out)
{
	memset(out, 0, sizeof(*out));
	if (!text)
		return -1;

	const char *p;

	/* cpu<digit>: —— 取首个 "cpu" 后跟数字再跟 ':' 的实例。 */
	int found_cpu = 0;
	p = strstr(text, "cpu");
	while (p) {
		if (isdigit((unsigned char)p[3]) && p[4] == ':') {
			out->cpu = p[3] - '0';
			found_cpu = 1;
			break;
		}
		p = strstr(p + 1, "cpu");
	}

	/* idle_mode=<value> （值到空格/换行结束）。 */
	if ((p = strstr(text, "idle_mode=")) != NULL) {
		p += 10; /* strlen("idle_mode=") */
		int i = 0;
		while (*p && *p != ' ' && *p != '\n' &&
		       i < (int)sizeof(out->idle_mode) - 1)
			out->idle_mode[i++] = *p++;
		out->idle_mode[i] = '\0';
	}

	if ((p = strstr(text, "excited=")) != NULL)
		out->excited = (unsigned)strtoul(p + 9, NULL, 10);

	if ((p = strstr(text, "coherence=")) != NULL) {
		out->coherence = (unsigned)strtoul(p + 10, NULL, 10);
		const char *slash = strchr(p, '/');
		if (slash)
			out->coherence_max = (unsigned)strtoul(slash + 1, NULL, 10);
	}

	/* 注意：模型行有 "coherence_ticks="，必须带前导空格避免误匹配。 */
	if ((p = strstr(text, " ticks=")) != NULL)
		out->ticks = strtoull(p + 7, NULL, 10);
	if ((p = strstr(text, "idle_steps=")) != NULL)
		out->idle_steps = strtoull(p + 11, NULL, 10);

	if ((p = strstr(text, "absorbed=")) != NULL)
		out->energy_absorbed = strtoull(p + 9, NULL, 10);
	if ((p = strstr(text, "emitted=")) != NULL)
		out->energy_emitted = strtoull(p + 8, NULL, 10);

	if ((p = strstr(text, "bell_events:")) != NULL)
		out->bell_events = (unsigned)strtoul(p + 12, NULL, 10);

	unsigned cnt = 0;
	const char *q = text;
	while ((q = strstr(q, "entangled:")) != NULL) {
		cnt++;
		q += 10; /* strlen("entangled:") */
	}
	out->entanglements = cnt;

	return found_cpu ? 0 : -1;
}

int parse_net(const char *text, struct net_state *out)
{
	memset(out, 0, sizeof(*out));
	if (!text)
		return -1;

	const char *p;

	if ((p = strstr(text, "nics=")) != NULL)
		out->nics = (unsigned)strtoul(p + 5, NULL, 10);
	else
		return -1;

	/* mode=<value>（gaia/swarm/mesh，到空格/换行结束）。 */
	if ((p = strstr(text, "mode=")) != NULL) {
		p += 5; /* strlen("mode=") */
		int i = 0;
		while (*p && *p != ' ' && *p != '\n' &&
		       i < (int)sizeof(out->mode) - 1)
			out->mode[i++] = *p++;
		out->mode[i] = '\0';
	}

	if ((p = strstr(text, "gaia_level=")) != NULL)
		out->gaia_level = (unsigned)strtoul(p + 11, NULL, 10);
	if ((p = strstr(text, "swarm_units=")) != NULL)
		out->swarm_units = (unsigned)strtoul(p + 12, NULL, 10);
	if ((p = strstr(text, "links=")) != NULL)
		out->links = (unsigned)strtoul(p + 6, NULL, 10);
	if ((p = strstr(text, "peers=")) != NULL)
		out->peers = (unsigned)strtoul(p + 6, NULL, 10);
	if ((p = strstr(text, "exchanges=")) != NULL)
		out->exchanges = strtoull(p + 10, NULL, 10);
	if ((p = strstr(text, "entanglements=")) != NULL)
		out->entanglements = strtoull(p + 14, NULL, 10);
	if ((p = strstr(text, "topology_changes=")) != NULL)
		out->topology_changes = strtoull(p + 17, NULL, 10);

	/*
	 * 每-NIC 明细行：以两个数字开头的行（"<nic> <id> <links> ..."）。
	 * 摘要行/note 行/表头行均不以数字开头，不会误计。
	 */
	const char *line = text;
	while (line && *line) {
		const char *nl = strchr(line, '\n');
		size_t len = nl ? (size_t)(nl - line) : strlen(line);
		char tmp[256];
		if (len && len < sizeof(tmp)) {
			memcpy(tmp, line, len);
			tmp[len] = '\0';
			char *end = NULL;
			unsigned long a = strtoul(tmp, &end, 10);
			if (end != tmp && a <= 64) {
				char *end2 = NULL;
				unsigned long b = strtoul(end, &end2, 10);
				if (end2 != end && b <= 64)
					out->nic_rows++;
			}
		}
		line = nl ? nl + 1 : NULL;
	}

	return 0;
}

int format_state_json(char *buf, size_t sz,
		      const struct energy_state *e, int energy_ok,
		      const struct qpu_link_stats *q, int qpu_ok,
		      const struct net_state *n, int net_ok)
{
	return snprintf(buf, sz,
		"{\n"
		"  \"quantum_core\": \"0.1\",\n"
		"  \"model\": \"emulated-accounting\",\n"
		"  \"energy\": {\n"
		"    \"available\": %s,\n"
		"    \"cpu\": %d,\n"
		"    \"idle_mode\": \"%s\",\n"
		"    \"excited\": %u,\n"
		"    \"coherence\": \"%u/%u\",\n"
		"    \"ticks\": %llu,\n"
		"    \"idle_steps\": %llu,\n"
		"    \"energy_absorbed\": %llu,\n"
		"    \"energy_emitted\": %llu,\n"
		"    \"bell_events\": %u,\n"
		"    \"entanglements\": %u\n"
		"  },\n"
		"  \"qpu\": {\n"
		"    \"available\": %s,\n"
		"    \"slots\": %u,\n"
		"    \"buffered\": %u,\n"
		"    \"total_writes\": %llu,\n"
		"    \"overwrites\": %llu\n"
		"  },\n"
		"  \"net\": {\n"
		"    \"available\": %s,\n"
		"    \"nics\": %u,\n"
		"    \"mode\": \"%s\",\n"
		"    \"gaia_level\": %u,\n"
		"    \"swarm_units\": %u,\n"
		"    \"links\": %u,\n"
		"    \"peers\": %u,\n"
		"    \"exchanges\": %llu,\n"
		"    \"entanglements\": %llu,\n"
		"    \"topology_changes\": %llu,\n"
		"    \"nic_rows\": %u\n"
		"  },\n"
		"  \"note\": \"emulated accounting model; not real quantum hardware\"\n"
		"}\n",
		energy_ok ? "true" : "false",
		e->cpu, e->idle_mode, e->excited,
		e->coherence, e->coherence_max, e->ticks, e->idle_steps,
		e->energy_absorbed, e->energy_emitted, e->bell_events,
		e->entanglements,
		qpu_ok ? "true" : "false",
		q ? q->slots : 0, q ? q->buffered : 0,
		(unsigned long long)(q ? q->total_writes : 0),
		(unsigned long long)(q ? q->overwrites : 0),
		net_ok ? "true" : "false",
		n ? n->nics : 0, n ? n->mode : "-", n ? n->gaia_level : 0,
		n ? n->swarm_units : 0, n ? n->links : 0, n ? n->peers : 0,
		(unsigned long long)(n ? n->exchanges : 0),
		(unsigned long long)(n ? n->entanglements : 0),
		(unsigned long long)(n ? n->topology_changes : 0),
		n ? n->nic_rows : 0);
}
