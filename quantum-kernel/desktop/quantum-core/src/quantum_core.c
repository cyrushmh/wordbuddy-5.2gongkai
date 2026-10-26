/* SPDX-License-Identifier: GPL-2.0 */
/*
 * src/quantum_core.c — 量子架构用户态守护进程。
 *
 * 职责：周期性读取量子架构内核暴露的诚实接口——
 *   · /proc/quantum-energy  （能级/相干/纠缠/Bell 事件/Planck 能量记账，只读 seq_file）
 *   · /proc/quantum-net     （QNIC 链路/对等/纠缠交换/盖亚层观测，只读 seq_file）
 *   · /dev/qpu0            （misc 字符设备，ioctl QPU_LINK_STATS/ENC/DEC/RESET）
 * 并产出 /run/quantum-core/state.json（genmon 小程序直接消费），可选经 DBus
 * session bus 暴露 org.quantum.Core 接口。
 *
 * 诚实边界：以上读写都是**模拟/记账模型**，不是真实量子硬件。在普通宿主机器上
 * /dev/qpu0 与 /proc/quantum-energy 不存在时，守护进程照常运行并把接口标记为
 * unavailable——它只是一个监控器，不会因接口缺失而崩溃，也不会伪造数据。
 */
#include "quantum_parse.h"
#include "quantum_uapi.h"

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <sys/ioctl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>

#ifdef HAVE_DBUS
#include <dbus/dbus.h>
#endif

#define STATE_PATH "/run/quantum-core/state.json"

static volatile sig_atomic_t g_running = 1;
static int g_qpu_fd = -1; /* 供 DBus 处理函数使用 */

#ifdef HAVE_DBUS
static DBusConnection *g_conn = NULL;
static char g_state_json[STATE_JSON_MAX];
#endif

static void on_signal(int sig)
{
	(void)sig;
	g_running = 0;
}

static int read_energy_text(char *buf, size_t sz)
{
	int fd = open(QUANTUM_ENERGY_PROC, O_RDONLY);
	if (fd < 0)
		return -1;
	ssize_t n = read(fd, buf, sz - 1);
	close(fd);
	if (n < 0)
		return -1;
	buf[n] = '\0';
	return 0;
}

static int read_net_text(char *buf, size_t sz)
{
	int fd = open(QUANTUM_NET_PROC, O_RDONLY);
	if (fd < 0)
		return -1;
	ssize_t n = read(fd, buf, sz - 1);
	close(fd);
	if (n < 0)
		return -1;
	buf[n] = '\0';
	return 0;
}

static void write_state_json(const char *json)
{
	mkdir("/run/quantum-core", 0755); /* 最佳努力；宿主 /run 已存在 */
	int fd = open(STATE_PATH, O_WRONLY | O_CREAT | O_TRUNC, 0644);
	if (fd < 0)
		return;
	size_t len = strlen(json);
	ssize_t w = write(fd, json, len);
	(void)w;
	close(fd);
}

#ifdef HAVE_DBUS
static DBusHandlerResult obj_handler(DBusConnection *c, DBusMessage *msg, void *ud)
{
	(void)c;
	(void)ud;
	if (dbus_message_get_type(msg) != DBUS_MESSAGE_TYPE_METHOD_CALL)
		return DBUS_HANDLER_RESULT_NOT_YET_HANDLED;
	const char *iface = dbus_message_get_interface(msg);
	const char *member = dbus_message_get_member(msg);
	if (!iface || strcmp(iface, "org.quantum.Core") != 0)
		return DBUS_HANDLER_RESULT_NOT_YET_HANDLED;

	DBusMessage *reply = NULL;
	if (strcmp(member, "GetState") == 0 || strcmp(member, "GetEnergy") == 0 ||
	    strcmp(member, "GetQpuStats") == 0 ||
	    strcmp(member, "GetNetStats") == 0) {
		reply = dbus_message_new_method_return(msg);
		const char *s = g_state_json;
		dbus_message_append_args(reply, DBUS_TYPE_STRING, &s,
					DBUS_TYPE_INVALID);
	} else if (strcmp(member, "Encode") == 0) {
		unsigned long long k = 0;
		DBusMessageIter it;
		if (dbus_message_iter_init(msg, &it) &&
		    dbus_message_iter_get_arg_type(&it) == DBUS_TYPE_UINT64)
			dbus_message_iter_get_basic(&it, &k);
		if (g_qpu_fd >= 0)
			ioctl(g_qpu_fd, QPU_ENC, &k);
		reply = dbus_message_new_method_return(msg);
		DBusMessageIter a;
		dbus_message_iter_init_append(reply, &a);
		dbus_message_iter_append_basic(&a, DBUS_TYPE_UINT64, &k);
	} else if (strcmp(member, "Decode") == 0) {
		unsigned long long k = 0;
		if (g_qpu_fd >= 0)
			ioctl(g_qpu_fd, QPU_DEC, &k);
		reply = dbus_message_new_method_return(msg);
		DBusMessageIter a;
		dbus_message_iter_init_append(reply, &a);
		dbus_message_iter_append_basic(&a, DBUS_TYPE_UINT64, &k);
	} else if (strcmp(member, "Reset") == 0) {
		if (g_qpu_fd >= 0)
			ioctl(g_qpu_fd, QPU_RESET);
		reply = dbus_message_new_method_return(msg);
	}

	if (reply) {
		dbus_connection_send(g_conn, reply, NULL);
		dbus_message_unref(reply);
	}
	return DBUS_HANDLER_RESULT_HANDLED;
}

static int dbus_setup(void)
{
	DBusError err;
	dbus_error_init(&err);
	g_conn = dbus_bus_get(DBUS_BUS_SESSION, &err);
	if (!g_conn) {
		fprintf(stderr, "quantum-core: DBus session bus 不可用（降级为 state.json）：%s\n",
			err.message);
		dbus_error_free(&err);
		return -1;
	}
	dbus_bus_request_name(g_conn, "org.quantum.Core",
			      DBUS_NAME_FLAG_REPLACE_EXISTING, &err);
	if (dbus_error_is_set(&err)) {
		fprintf(stderr, "quantum-core: 名称请求失败：%s\n", err.message);
		dbus_error_free(&err);
	}
	static DBusObjectPathVTable vt = { NULL, obj_handler, NULL, NULL,
					   NULL, NULL };
	if (!dbus_connection_register_object_path(g_conn, "/org/quantum/Core",
						      &vt, NULL)) {
		fprintf(stderr, "quantum-core: 注册对象路径失败\n");
		return -1;
	}
	printf("quantum-core: DBus org.quantum.Core 就绪\n");
	return 0;
}
#endif /* HAVE_DBUS */

int main(int argc, char **argv)
{
	int interval = 1;
	int once = 0;
	for (int i = 1; i < argc; i++) {
		if (!strcmp(argv[i], "--once"))
			once = 1;
		else if (!strcmp(argv[i], "--interval") && i + 1 < argc)
			interval = atoi(argv[++i]);
	}

	int qpu_fd = open(QPU_DEVICE, O_RDWR);
	if (qpu_fd < 0)
		fprintf(stderr,
			"quantum-core: %s 不可用（host 模式）：%s\n",
			QPU_DEVICE, strerror(errno));
	g_qpu_fd = qpu_fd;

#ifdef HAVE_DBUS
	if (dbus_setup() != 0)
		g_conn = NULL;
#endif

	signal(SIGTERM, on_signal);
	signal(SIGINT, on_signal);

	while (g_running) {
		struct energy_state e;
		memset(&e, 0, sizeof(e));
		char text[8192];
		int energy_ok = 0;
		if (read_energy_text(text, sizeof(text)) == 0 &&
		    parse_energy(text, &e) == 0)
			energy_ok = 1;

		struct qpu_link_stats qs;
		memset(&qs, 0, sizeof(qs));
		int qpu_ok = 0;
		if (qpu_fd >= 0 && ioctl(qpu_fd, QPU_LINK_STATS, &qs) == 0)
			qpu_ok = 1;

		struct net_state ns;
		memset(&ns, 0, sizeof(ns));
		char net_text[8192];
		int net_ok = 0;
		if (read_net_text(net_text, sizeof(net_text)) == 0 &&
		    parse_net(net_text, &ns) == 0)
			net_ok = 1;

		char json[STATE_JSON_MAX];
		format_state_json(json, sizeof(json), &e, energy_ok,
				  qpu_ok ? &qs : NULL, qpu_ok,
				  net_ok ? &ns : NULL, net_ok);

#ifdef HAVE_DBUS
		if (g_conn) {
			snprintf(g_state_json, sizeof(g_state_json), "%s", json);
			dbus_connection_read_write_dispatch(g_conn, 0);
		}
#endif
		write_state_json(json);

		if (once)
			break;
		sleep(interval);
	}

	if (qpu_fd >= 0)
		close(qpu_fd);
	return 0;
}
