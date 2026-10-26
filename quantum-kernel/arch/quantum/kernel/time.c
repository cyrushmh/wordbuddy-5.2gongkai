// SPDX-License-Identifier: GPL-2.0
/*
 * arch/quantum/kernel/time.c — emulated clock events.
 * 时基由宿主提供：模拟架构注册一个 always-on broadcast 事件源即可。
 */
#include <linux/clockchips.h>
#include <linux/delay.h>
#include <linux/init.h>
#include <linux/timekeeper_internal.h>

static int quantum_timer_set_next_event(unsigned long delta,
					struct clock_event_device *dev)
{
	return 0;
}

static struct clock_event_device quantum_timer = {
	.name			= "quantum_timer",
	.features		= CLOCK_EVT_FEAT_ONESHOT,
	.set_next_event		= quantum_timer_set_next_event,
	.rating			= 200,
};

void __init time_init(void)
{
	clockevents_config_and_register(&quantum_timer, 1000000, 1, 0xffffffff);
}

/* 延迟原语（宿主模拟：无真实忙等需求，空实现满足 udelay 链接契约）。 */
void __const_udelay(unsigned long xloops)
{
}
EXPORT_SYMBOL(__const_udelay);

/* vsyscall tz 更新（模拟架构：无真实 vsyscall 页，空实现）。 */
void update_vsyscall_tz(void)
{
}

/* vsyscall 更新（模拟架构：无真实 vsyscall 页，空实现）。 */
void update_vsyscall(struct timekeeper *tk)
{
}
