// SPDX-License-Identifier: GPL-2.0
/*
 * drivers/quantum/net/qnet-dev.c — emulated QNIC misc device /dev/qnet0.
 *
 * 硬件侧 QNIC 设备：用户态经 QNET_LINK_ADD / QNET_LINK_DEL / QNET_LINK_STATS /
 * QNET_ENTANGLE_SWAP / QNET_TELEPORT / QNET_RESET 与架构侧组网编排
 * （arch/quantum/kernel/quantum-net.c）交互。诚实口径：QNIC 为宿主模拟字符
 * 设备，不是真实量子硬件。
 */
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/miscdevice.h>
#include <linux/fs.h>
#include <linux/uaccess.h>
#include <uapi/linux/quantum.h>
#include <asm/quantum.h>
#include "qnic.h"

static long qnet_ioctl(struct file *filp, unsigned int cmd, unsigned long arg)
{
	__u32 peer;
	struct qnet_link_stats st;
	const struct quantum_net_state *s;

	switch (cmd) {
	case QNET_LINK_ADD:
		if (copy_from_user(&peer, (void __user *)arg, sizeof(peer)))
			return -EFAULT;
		return quantum_net_entangle(0, peer);
	case QNET_LINK_DEL:
		if (copy_from_user(&peer, (void __user *)arg, sizeof(peer)))
			return -EFAULT;
		return quantum_net_unlink(0, peer);
	case QNET_LINK_STATS:
		s = quantum_net_state();
		st.links = s->links;
		st.active = s->links;
		st.bell_pairs = s->entanglements;
		st.swaps = s->swaps;
		st.teleports = s->teleports;
		if (copy_to_user((void __user *)arg, &st, sizeof(st)))
			return -EFAULT;
		return 0;
	case QNET_ENTANGLE_SWAP:
		return quantum_net_swap();
	case QNET_TELEPORT:
		return quantum_net_teleport();
	case QNET_RESET:
		quantum_net_reset();
		return 0;
	default:
		return -ENOTTY;
	}
}

static int qnet_open(struct inode *inode, struct file *file)
{
	return 0;
}

static const struct file_operations qnet_fops = {
	.owner		= THIS_MODULE,
	.open		= qnet_open,
	.unlocked_ioctl	= qnet_ioctl,
	.compat_ioctl	= compat_ptr_ioctl,
	.llseek		= noop_llseek,
};

static struct miscdevice qnet_miscdev = {
	.minor		= MISC_DYNAMIC_MINOR,
	.name		= "qnet0",
	.fops		= &qnet_fops,
	.mode		= 0600,
};

static int __init qnet_init(void)
{
	int ret;

	ret = qnic_hw_probe();
	if (ret)
		return ret;
	ret = misc_register(&qnet_miscdev);
	if (ret) {
		qnic_hw_remove();
		return ret;
	}
	pr_info("qnet: emulated QNIC /dev/qnet0 ready (architecture mesh substrate)\n");
	return 0;
}

static void __exit qnet_exit(void)
{
	misc_deregister(&qnet_miscdev);
	qnic_hw_remove();
}

module_init(qnet_init);
module_exit(qnet_exit);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Emulated quantum network interface card (/dev/qnet0)");
MODULE_AUTHOR("quantum-kernel project");
