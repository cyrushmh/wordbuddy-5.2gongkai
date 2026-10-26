/* SPDX-License-Identifier: GPL-2.0 */
/*
 * src/test_parse.c — quantum_parse 的单元测试（宿主即可运行，无需量子内核）。
 * 用内嵌的 mock /proc/quantum-energy 文本验证解析，并验证 state.json 格式化。
 */
#include "quantum_parse.h"

#include <stdio.h>
#include <string.h>

static const char SAMPLE[] =
	"quantum energy model: levels=20 step=1 coherence_ticks=4 decohere_steps=8\n"
	"cpu0: idle_mode=active excited=0 coherence=0/20 ticks=123456 idle_steps=1000\n"
	"level  energy  phase        pop\n"
	"0      1       0x0          64\n"
	"1      1       0x15555555   0\n"
	"interference(0,1) = 123456 (2^30 fixed, [-2, +2])\n"
	"events: excitations=10 relaxations=5 allowed=100 forbidden=0 collapses=2 photons=8\n"
	"energy: absorbed=50 emitted=30 (planck units)\n"
	"entangled: 0 <-> 1\n"
	"bell_events: 3\n";

static int failures = 0;

#define CHECK(cond, msg) do { \
	if (!(cond)) { fprintf(stderr, "✗ %s\n", msg); failures++; } \
	else { fprintf(stderr, "✓ %s\n", msg); } \
} while (0)

/* 与内核 quantum_net_show 输出同构的 mock 文本。 */
static const char NET_SAMPLE[] =
	"quantum net model: nics=2 mode=mesh gaia_level=3 swarm_units=0\n"
	"links=4 peers=3 exchanges=100 entanglements=7 topology_changes=2\n"
	"note: emulated accounting model; not real quantum hardware\n"
	"nic  id   links   peers  exchanges  entanglements\n"
	"0    0    2       1      50         4\n"
	"1    1    2       2      50         3\n";

int main(void)
{
	struct energy_state e;
	memset(&e, 0, sizeof(e));
	CHECK(parse_energy(SAMPLE, &e) == 0, "parse_energy 返回 0");
	CHECK(e.cpu == 0, "cpu == 0");
	CHECK(strcmp(e.idle_mode, "active") == 0, "idle_mode == active");
	CHECK(e.excited == 0, "excited == 0");
	CHECK(e.coherence == 0, "coherence == 0");
	CHECK(e.coherence_max == 20, "coherence_max == 20");
	CHECK(e.ticks == 123456, "ticks == 123456");
	CHECK(e.idle_steps == 1000, "idle_steps == 1000");
	CHECK(e.energy_absorbed == 50, "energy_absorbed == 50");
	CHECK(e.energy_emitted == 30, "energy_emitted == 30");
	CHECK(e.bell_events == 3, "bell_events == 3");
	CHECK(e.entanglements == 1, "entanglements == 1");

	/* 无 cpu 行的坏文本应返回 <0 */
	CHECK(parse_energy("garbage without cpu line", &e) < 0,
	      "坏文本返回 <0");

	/* ---- /proc/quantum-net 解析（先于 json 格式化，供三段断言共用） ---- */
	struct net_state n;
	memset(&n, 0, sizeof(n));
	CHECK(parse_net(NET_SAMPLE, &n) == 0, "parse_net 返回 0");
	CHECK(n.nics == 2, "nics == 2");
	CHECK(strcmp(n.mode, "mesh") == 0, "mode == mesh");
	CHECK(n.gaia_level == 3, "gaia_level == 3");
	CHECK(n.swarm_units == 0, "swarm_units == 0");
	CHECK(n.links == 4, "links == 4");
	CHECK(n.peers == 3, "peers == 3");
	CHECK(n.exchanges == 100, "exchanges == 100");
	CHECK(n.entanglements == 7, "entanglements == 7");
	CHECK(n.topology_changes == 2, "topology_changes == 2");
	CHECK(n.nic_rows == 2, "nic_rows == 2（表头/note 行不误计）");
	/* 坏文本用临时变量：parse_net 入口即 memset，不可复用 n */
	struct net_state bad;
	CHECK(parse_net("garbage without nics line", &bad) < 0,
	      "坏文本返回 <0");

	/* state.json 格式化（energy/qpu/net 均可读） */
	struct qpu_link_stats q = { .slots = 7, .buffered = 2,
				    .total_writes = 100, .overwrites = 5 };
	char buf[STATE_JSON_MAX];
	int nj = format_state_json(buf, sizeof(buf), &e, 1, &q, 1, &n, 1);
	CHECK(nj > 0 && nj < (int)sizeof(buf), "format_state_json 长度合理");
	CHECK(strstr(buf, "\"quantum_core\": \"0.1\"") != NULL,
	      "json 含 quantum_core 版本");
	CHECK(strstr(buf, "\"available\": true") != NULL,
	      "json 标记接口 available");
	CHECK(strstr(buf, "\"total_writes\": 100") != NULL,
	      "json 含 qpu total_writes=100");
	CHECK(strstr(buf, "\"overwrites\": 5") != NULL,
	      "json 含 qpu overwrites=5");
	CHECK(strstr(buf, "\"net\": {") != NULL, "json 含 net 段");
	CHECK(strstr(buf, "\"mode\": \"mesh\"") != NULL, "net mode == mesh");
	CHECK(strstr(buf, "\"topology_changes\": 2") != NULL,
	      "net topology_changes == 2");
	CHECK(strstr(buf, "\"nic_rows\": 2") != NULL, "net nic_rows == 2");

	/* 接口不可读时 available=false */
	char buf2[STATE_JSON_MAX];
	format_state_json(buf2, sizeof(buf2), &e, 0, NULL, 0, NULL, 0);
	CHECK(strstr(buf2, "\"available\": false") != NULL,
	      "接口缺失时 available=false");
	CHECK(strstr(buf2, "\"nics\": 0") != NULL, "net 缺失时 nics=0");
	CHECK(strstr(buf2, "\"mode\": \"-\"") != NULL, "net 缺失时 mode=-");

	if (failures == 0) {
		printf("ALL TESTS PASSED\n");
		return 0;
	}
	fprintf(stderr, "%d TEST(S) FAILED\n", failures);
	return 1;
}
